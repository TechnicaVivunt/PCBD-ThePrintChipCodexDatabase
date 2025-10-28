import requests
import csv
import time
import os
import re

BASE_URL = "https://us.polymaker.com/collections/all/products.json"

def safe_str(value):
    """Convert None to empty string, strip whitespace, remove garbled symbols and parentheses."""
    if value is None:
        return ""
    s = str(value)
    # Normalize non-breaking spaces and garbled characters
    s = s.replace("\u00A0", " ").replace("™", "").replace("Â", "").strip()
    # Remove text in parentheses
    s = re.sub(r"\s*\([^)]*\)", "", s).strip()
    return s

def fetch_page(page):
    """Fetch one page of products."""
    url = f"{BASE_URL}?page={page}"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    return data.get("products", [])

def is_valid_option2(value):
    """Return True if option2 is valid (not blank, not above 1kg)."""
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
    """Return False if option1 contains unwanted text."""
    s = value.lower()
    if "(old packaging)" in s:
        return False
    if "(old formula)" in s:
        return False
    if "2.85mm" in s or "2.85 mm" in s:
        return False
    if "sample box" in s:
        return False
    return True

def flatten_product(product):
    """Flatten each product and its variants into filtered, cleaned rows."""
    rows = []
    vendor = safe_str(product.get("vendor"))
    brand_name_raw = safe_str(product.get("title"))

    # Skip deprecated brand
    if brand_name_raw.lower() == "polylite pla":
        return []

    brand_name = brand_name_raw

    for variant in product.get("variants", []):
        option1 = safe_str(variant.get("option1"))
        option2 = safe_str(variant.get("option2"))
        color_name = safe_str(variant.get("option3"))

        # --- Apply filters ---
        if not is_valid_option1(option1):
            continue
        if not is_valid_option2(option2):
            continue

        # --- Build clean record ---
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
    all_rows = []
    page = 1

    while True:
        products = fetch_page(page)
        if not products:
            break
        print(f"Fetched page {page}: {len(products)} products")
        for product in products:
            all_rows.extend(flatten_product(product))
        page += 1
        time.sleep(0.5)

    # --- Deduplicate by brand_name + color_name ---
    unique = {}
    for row in all_rows:
        key = (row["brand_name"], row["color_name"])
        if key not in unique:
            unique[key] = row

    unique_rows = list(unique.values())

    # --- Write everything to CSV ---
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

    print(f"\n✅ Saved {len(unique_rows)} unique filtered variants to '{filename}' (UTF-8 encoded)")

if __name__ == "__main__":
    main()
