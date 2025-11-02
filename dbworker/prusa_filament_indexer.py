import requests
import csv
import re
import os

# Ensure dbworker folder exists
os.makedirs("dbworker", exist_ok=True)

# GraphQL endpoint and headers
url = "https://www.prusa3d.com/graphql/"
headers = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}

# GraphQL query
query = """
query getCategory($urlSlug: String!, $first: Int!, $afterCursor: String, $currency: String!, $country: String!, $productsOrder: ProductOrderingModeEnum = PRIORITY, $filter: ProductFilter) {
  category(urlSlug: $urlSlug) {
    products(first: $first, after: $afterCursor, orderingMode: $productsOrder, filter: $filter) {
      pageInfo {
        endCursor
      }
      edges {
        node {
          name
          slug
          availability {
            name
          }
          price(priceOptionInput: {currencyCode: $currency, vatCountryCode: $country}) {
            priceWithVat
          }
          images(countryCode: $country) {
            url
          }
        }
      }
    }
  }
}
"""

# Refined parsing function
def parse_name(full_name):
    # Remove parentheses and suffixes
    cleaned = re.sub(r"\s*\(.*?\)", "", full_name)
    cleaned = re.sub(r"\s*Refill|\s*sample", "", cleaned).strip()

    # Extract weight
    weight_match = re.search(r"(\d+(?:kg|g))", cleaned)
    weight = weight_match.group(1) if weight_match else ""

    # Remove weight
    name_wo_weight = re.sub(re.escape(weight), "", cleaned).strip()

    # Tokenize
    tokens = name_wo_weight.split()

    # Must start with "Prusament"
    if not tokens or tokens[0] != "Prusament":
        return "Unknown", cleaned, "", weight

    # Extract material
    material = tokens[1] if len(tokens) > 1 else "Unknown"

    # Material override rules
    if "Woodfill" in name_wo_weight or "Premium PLA" in name_wo_weight:
        material = "PLA"

    # Build brand: Prusament + material + optional modifiers
    brand_tokens = [tokens[0], tokens[1]]
    i = 2
    while i < len(tokens) and tokens[i] in {"Blend", "Premium", "95A", "Space", "V0", "1010"}:
        brand_tokens.append(tokens[i])
        i += 1
    brand = " ".join(brand_tokens)

    # Remaining tokens are color
    color = " ".join(tokens[i:]).strip()

    return material, brand, color, weight

# Pagination loop
all_products = []
seen_pairs = set()
after_cursor = None
batch_size = 50

while True:
    variables = {
        "country": "US",
        "currency": "USD",
        "filter": {
            "priceOptionInput": {
                "currencyCode": "USD",
                "vatCountryCode": "US"
            }
        },
        "first": batch_size,
        "productsOrder": "PRIORITY",
        "urlSlug": "category/prusament",
        "afterCursor": after_cursor
    }

    response = requests.post(url, headers=headers, json={"operationName": "getCategory", "query": query, "variables": variables})
    data = response.json()

    if "errors" in data:
        print("❌ GraphQL error:")
        print(data["errors"])
        break
    elif "data" not in data:
        print("❌ No 'data' field in response. Full response:")
        print(data)
        break

    edges = data['data']['category']['products']['edges']
    page_info = data['data']['category']['products']['pageInfo']

    for edge in edges:
        product = edge['node']
        full_name = product['name']

        # Skip bundles
        if "bundle" in product['slug']:
            continue

        material, brand, color, weight = parse_name(full_name)
        pair_key = (brand.lower(), color.lower())

        # Skip duplicates based on brand + color
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)

        price = product['price']['priceWithVat']
        availability = product['availability']['name']
        image_url = product['images'][0]['url'] if product['images'] else ""
        product_url = f"https://www.prusa3d.com/product/{product['slug']}/"

        all_products.append([material, brand, color, weight, price, availability, image_url, product_url])

    if not page_info['endCursor']:
        break
    after_cursor = page_info['endCursor']

# Sort by material
all_products.sort(key=lambda x: x[0])

# Export to CSV in dbworker folder
with open("dbworker/prusament_filament_index.csv", mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(["Material", "Brand", "Color", "Weight", "Price (USD)", "Availability", "Image URL", "Product URL"])
    writer.writerows(all_products)

print(f"✅ Exported {len(all_products)} unique products to 'dbworker/prusament_filament_index.csv'")
