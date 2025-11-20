import requests
import csv
import time
import os
import re

BASE_URL = "https://us.polymaker.com/collections/all/products.json"
EXCLUDE_FILE = "exclude_list/exclude_list_polymaker.csv"

def safe_str(value):
    if value is None:
        return ""
    s = str(value)
    s = s.replace("\u00A0", " ").replace("™", "").replace("Â", "").strip()
    s = re.sub(r"\s*\([^)]*\)", "", s).strip()
    return s

def normalize_key(brand, color):
    return (brand.strip().lower(), color.strip().lower())

def load_exclude_list(filename):
    exclude = set()
    if not os.path.exists(filename):
        print(f"⚠️ Exclude file '{filename}' not found. Continuing without exclusions.")
        return exclude
    with open(filename, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            brand = row.get("brand_name", "").strip()
            color = row.get("color_name", "").strip()
            if brand and color:
                exclude.add(normalize_key(brand, color))
    return exclude

def fetch_page(page):
    url = f"{BASE_URL}?page={page}"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    return data.get("products", [])

def is_valid_option2(value):
    if not value:
        return False
    s = value.lower()
    if "kg" in s:
        try:
            num = float(s.replace("kg", "").strip())
            if num > 1:
                return False
        except ValueError:
            return False
    return True

def is_valid_option1(value):
    s = value.lower()
    if "(old packaging)" in s:
        return False
    if "(old formula)" in s:
        return False
    if "2.85mm" in s or "2.85 mm" in s:
        return False
    if "sample box" in s:
        return False
    if "refill" in s:   # exclude refill variants
        return False
    return True

def flatten_product(product, exclude_set):
    rows = []
    vendor = safe_str(product.get("vendor"))
    brand_name_raw = safe_str(product.get("title"))

    if brand_name_raw.lower() == "polylite pla":
        return []

    brand_name = brand_name_raw

    for variant in product.get("variants", []):
        option1 = safe_str(variant.get("option1"))
        option2 = safe_str(variant.get("option2"))
        color_name = safe_str(variant.get("option3"))

        if not is_valid_option1(option1):
            continue
        if not is_valid_option2(option2):
            continue

        key = normalize_key(brand_name, color_name)
        if key in exclude_set:
            continue

        rows.append({
            "brand_name": brand_name,
            "color_name": color_name,
            "variant_title": safe_str(variant.get("title")),
            "vendor": vendor,
            "price": safe_str(variant.get("price")),
            "grams": safe_str(variant.get("grams")),
            "inventory_quantity": safe_str(variant.get("inventory_quantity")),
            "option1": option1,
            "option2": option2
        })
    return rows

def main():
    exclude_set = load_exclude_list(EXCLUDE_FILE)
    all_rows = []
    page = 1

    while True:
        try:
            products = fetch_page(page)
        except requests.RequestException as e:
            print(f"❌ Error fetching page {page}: {e}")
            break

        if not products:
            break
        print(f"Fetched page {page}: {len(products)} products")
        for product in products:
            all_rows.extend(flatten_product(product, exclude_set))
        page += 1
        time.sleep(0.5)

    unique = {}
    for row in all_rows:
        key = (row["brand_name"], row["color_name"])
        if key not in unique:
            unique[key] = row

    unique_rows = list(unique.values())

    os.makedirs("dbworker", exist_ok=True)
    filename = os.path.join("dbworker", "polymaker_filament_index.csv")

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        fieldnames = [
            "brand_name", "color_name", "variant_title", "vendor",
            "price", "grams", "inventory_quantity",
            "option1", "option2"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(unique_rows)

    print(f"\n✅ Saved {len(unique_rows)} unique filtered variants to '{filename}'")

if __name__ == "__main__":
    main()

