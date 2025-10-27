import os
import csv
import re
import requests

# Create output directory
os.makedirs("dbworker", exist_ok=True)
csv_path = os.path.join("dbworker", "voxel_filament_index.csv")

# Base URL for products JSON
base_url = "https://voxelpla.com/collections/all/products.json"

products = []
page = 1

print("Fetching product data...")

# Fetch all pages
while True:
    url = f"{base_url}?page={page}"
    resp = requests.get(url)
    if resp.status_code != 200:
        print(f"Request failed on page {page}: {resp.status_code}")
        break
    data = resp.json()
    items = data.get("products", [])
    if not items:
        break
    products.extend(items)
    print(f"Fetched page {page} with {len(items)} products...")
    page += 1

print(f"\nTotal products fetched: {len(products)}")

# CSV fields
fields = ["brand_name", "color_name", "diameter", "weight", "material", "price"]

# Function to parse product titles
def parse_product_title(title):
    title_lower = title.lower()
    if "filament" not in title_lower or "bundle" in title_lower:
        return None

    diameter_match = re.search(r"\d+\.?\d*mm", title, re.IGNORECASE)
    diameter = diameter_match.group(0) if diameter_match else ""
    weight_match = re.search(r"\((\d+\.?\d*kg)\)", title, re.IGNORECASE)
    weight = weight_match.group(1) if weight_match else ""

    material = ""
    if "pla" in title_lower:
        material = "PLA"
    elif "petg" in title_lower:
        material = "PETG"

    clean_title = re.sub(r"\((?!\d+\.?\d*kg\)).*?\)", "", title)
    clean_title = clean_title.replace(diameter, "").replace(weight, "").replace("Filament", "").strip(" -")
    clean_title_lower = clean_title.lower()

    if re.search(r"voxel\s*galaxy\s*petg\+?\s*hs", clean_title_lower):
        brand_name = "Voxel Galaxy PETG+ HS"
        color_name = re.sub(r"voxel\s*galaxy\s*petg\+?\s*hs", "", clean_title_lower, flags=re.IGNORECASE).strip()
    elif re.search(r"voxelpetg\+?\s*hs", clean_title_lower):
        brand_name = "VOXEL PETG+ HS"
        color_name = re.sub(r"voxelpetg\+?\s*hs", "", clean_title_lower, flags=re.IGNORECASE).strip()
    elif re.search(r"voxelpla\s*pla\+?\s*hs", clean_title_lower):
        brand_name = "Voxel PLA+ HS"
        color_name = re.sub(r"voxelpla\s*pla\+?\s*hs", "", clean_title_lower, flags=re.IGNORECASE).strip()
    else:
        parts = clean_title.split()
        brand_name = " ".join(parts[:2])
        color_name = " ".join(parts[2:])

    color_name = re.sub(r"[()]", "", color_name).strip()
    color_name = " ".join([word.title() for word in color_name.split()])

    return {
        "brand_name": brand_name,
        "color_name": color_name,
        "diameter": diameter,
        "weight": weight,
        "material": material
    }

# Parse products
parsed_rows = []
for p in products:
    title = p.get("title", "")
    parsed = parse_product_title(title)
    if not parsed:
        continue
    variants = p.get("variants", [])
    price = variants[0].get("price") if variants else ""
    parsed["price"] = price
    parsed_rows.append(parsed)

# Sort rows for consistent CSV output
parsed_rows.sort(key=lambda x: (x["brand_name"], x["color_name"]))

# Write CSV with normalized line endings
with open(csv_path, "w", newline="\n", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in parsed_rows:
        writer.writerow(row)

print(f"\n✅ Export complete: {csv_path} ({len(parsed_rows)} filament products)")
