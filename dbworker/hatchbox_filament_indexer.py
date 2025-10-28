import requests
import json
import csv
import re

# Fetch JSON from Hatchbox3D
url = "https://www.hatchbox3d.com/collections/shop-all/products.json"
response = requests.get(url)
data = response.json()

# Open CSV for writing
with open('dbworker/hatchbox_filament_index.csv', 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)

    # Write header
    writer.writerow([
        'Title', 'Vendor', 'Product Type', 'Variant Title',
        'Price', 'SKU', 'Available', 'brand_name', 'color_name'
    ])

    # Process each product
    for product in data['products']:
        title = product.get('title', '')
        vendor = product.get('vendor', '')
        product_type = product.get('product_type', '')
        variants = product.get('variants', [])

        # Normalize title
        title_upper = title.upper()

        # Match filament type
        filament_match = re.search(r'\b(PLA|ABS|PETG|WOOD)\b\s+FILAMENT', title_upper)
        filament_type = filament_match.group(1).upper() if filament_match else ''

        # Extract everything before filament type as color name
        prefix_match = re.search(r'^(.*?)\b' + re.escape(filament_type) + r'\b\s+FILAMENT', title_upper)
        color_name = prefix_match.group(1).strip().title() if prefix_match else ''

        # Brand name is always just the filament type in uppercase
        brand_name = filament_type

        for variant in variants:
            writer.writerow([
                title, vendor, product_type,
                variant.get('title', ''),
                variant.get('price', ''),
                variant.get('sku', ''),
                variant.get('available', ''),
                brand_name, color_name
            ])
