"""
Indexers for manufacturers that aren't plain Shopify products.json feeds.
Registered in BESPOKE so run_indexers.py can dispatch to them the same
way it dispatches Shopify-backed brands.
"""
import csv
import os
import re
import requests

from shopify_engine import make_session

PRUSA_URL = "https://www.prusa3d.com/graphql/"
PRUSA_OUT = "dbworker/prusament_filament_index.csv"

PRUSA_QUERY = """
query getCategory($urlSlug: String!, $first: Int!, $afterCursor: String, $currency: String!, $country: String!, $productsOrder: ProductOrderingModeEnum = PRIORITY, $filter: ProductFilter) {
  category(urlSlug: $urlSlug) {
    products(first: $first, after: $afterCursor, orderingMode: $productsOrder, filter: $filter) {
      pageInfo { endCursor }
      edges {
        node {
          name
          slug
          availability { name }
          price(priceOptionInput: {currencyCode: $currency, vatCountryCode: $country}) { priceWithVat }
          images(countryCode: $country) { url }
        }
      }
    }
  }
}
"""


def _parse_prusa_name(full_name):
    cleaned = re.sub(r"\s*\(.*?\)", "", full_name)
    cleaned = re.sub(r"\s*Refill|\s*sample", "", cleaned).strip()

    weight_match = re.search(r"(\d+(?:kg|g))", cleaned)
    weight = weight_match.group(1) if weight_match else ""
    name_wo_weight = re.sub(re.escape(weight), "", cleaned).strip() if weight else cleaned

    tokens = name_wo_weight.split()
    if not tokens or tokens[0] != "Prusament":
        return "Unknown", cleaned, "", weight

    material = tokens[1] if len(tokens) > 1 else "Unknown"
    if "Woodfill" in name_wo_weight or "Premium PLA" in name_wo_weight:
        material = "PLA"

    brand_tokens = [tokens[0], tokens[1]]
    i = 2
    while i < len(tokens) and tokens[i] in {"Blend", "Premium", "95A", "Space", "V0", "1010"}:
        brand_tokens.append(tokens[i])
        i += 1
    brand = " ".join(brand_tokens)
    color = " ".join(tokens[i:]).strip()
    return material, brand, color, weight


def fetch_prusa():
    session = make_session()
    all_products, seen_pairs = [], set()
    after_cursor = None
    batch_size = 50

    while True:
        variables = {
            "country": "US", "currency": "USD",
            "filter": {"priceOptionInput": {"currencyCode": "USD", "vatCountryCode": "US"}},
            "first": batch_size, "productsOrder": "PRIORITY",
            "urlSlug": "category/prusament", "afterCursor": after_cursor,
        }
        try:
            resp = session.post(
                PRUSA_URL, timeout=20,
                json={"operationName": "getCategory", "query": PRUSA_QUERY, "variables": variables},
            )
            data = resp.json()
        except (requests.RequestException, ValueError) as e:
            print(f"[prusa] ERROR: {e}")
            break

        if "data" not in data:
            print(f"[prusa] ERROR: unexpected response: {data}")
            break

        edges = data["data"]["category"]["products"]["edges"]
        page_info = data["data"]["category"]["products"]["pageInfo"]

        for edge in edges:
            product = edge["node"]
            if "bundle" in product["slug"]:
                continue
            material, brand, color, weight = _parse_prusa_name(product["name"])
            pair_key = (brand.lower(), color.lower())
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            price = product["price"]["priceWithVat"]
            availability = product["availability"]["name"]
            image_url = product["images"][0]["url"] if product["images"] else ""
            product_url = f"https://www.prusa3d.com/product/{product['slug']}/"
            all_products.append({
                "Material": material, "brand_name": brand, "color_name": color,
                "Weight": weight, "Price (USD)": price, "Availability": availability,
                "Image URL": image_url, "Product URL": product_url,
            })

        if not page_info["endCursor"]:
            break
        after_cursor = page_info["endCursor"]

    all_products.sort(key=lambda x: x["Material"])
    os.makedirs(os.path.dirname(PRUSA_OUT), exist_ok=True)
    with open(PRUSA_OUT, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["Material", "brand_name", "color_name", "Weight",
                      "Price (USD)", "Availability", "Image URL", "Product URL"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_products)

    print(f"[prusa] wrote {len(all_products)} rows -> {PRUSA_OUT}")
    return len(all_products)


BESPOKE = {
    "prusa": fetch_prusa,
}
