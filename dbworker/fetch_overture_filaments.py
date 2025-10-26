import requests
import csv
import time
import os
import hashlib
import json

COLLECTION_JSON_URL = "https://overture3d.com/collections/all-filaments/products.json"
PAGE_LIMIT = 250
OUTPUT_DIR = "dbworker"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "overture_filament_index.csv")
HASH_FILE = os.path.join(OUTPUT_DIR, "overture_filament_index.hash")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_all_products():
    all_products = []
    seen_ids = set()
    page = 1

    while True:
        params = {"limit": PAGE_LIMIT, "page": page}
        resp = requests.get(COLLECTION_JSON_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

        products = data.get("products", [])
        if not products:
            break

        new_products = [p for p in products if p["id"] not in seen_ids]
        for p in new_products:
            seen_ids.add(p["id"])

        all_products.extend(new_products)

        if len(products) < PAGE_LIMIT:
            break

        page += 1
        time.sleep(0.5)

    return all_products


def contains_refill(text):
    return "refill" in text.lower()


def clean_product_name(name):
    name = name.replace("Overture", "").replace("3D Printer Filament", "").strip()
    return name


def build_csv_rows(products):
    rows = []
    for product in products:
        raw_product_name = product.get("title", "")
        if contains_refill(raw_product_name):
            continue

        product_name = clean_product_name(raw_product_name)
        product_url = f"https://overture3d.com/products/{product.get('handle', '')}"

        for variant in product.get("variants", []):
            variant_title = variant.get("title", "")
            if contains_refill(variant_title):
                continue

            sku = variant.get("sku", "")
            price_raw = variant.get("price", "")
            try:
                price = "{:.2f}".format(float(price_raw))
            except Exception:
                price = price_raw

            available = variant.get("available", "")
            color = variant.get("option1") or variant.get("option2") or variant.get("option3") or ""

            rows.append({
                "Product": product_name,
                "Variant": variant_title,
                "SKU": sku,
                "Price": price,
                "Available": available,
                "Color": color,
                "URL": product_url
            })
    return rows


def write_csv(rows):
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["Product", "Variant", "SKU", "Price", "Available", "Color", "URL"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def compute_hash(file_path):
    if not os.path.exists(file_path):
        return None
    with open(file_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def main():
    products = fetch_all_products()
    rows = build_csv_rows(products)
    write_csv(rows)

    new_hash = compute_hash(OUTPUT_FILE)
    old_hash = None
    if os.path.exists(HASH_FILE):
        with open(HASH_FILE, "r") as f:
            old_hash = f.read().strip()

    changed = new_hash != old_hash

    if changed:
        with open(HASH_FILE, "w") as f:
            f.write(new_hash)

    # Return dict for GitHub Actions to parse with jq
    return {"rows": len(rows), "changed": changed}


if __name__ == "__main__":
    result = main()
    # Print only JSON, no extra prints
    print(json.dumps(result))
