import requests
import pandas as pd
import re
from collections import Counter

# Step 1: Fetch all products via pagination
base_url = "https://coex3d.com/collections/all/products.json"
all_products = []
page = 1

while True:
    print(f"Fetching page {page}...")
    response = requests.get(base_url, params={"page": page})
    response.encoding = 'utf-8'
    if response.status_code != 200:
        print(f"Failed to fetch page {page}")
        break

    data = response.json()
    products = data.get("products", [])
    if not products:
        print("No more products found.")
        break

    all_products.extend(products)
    page += 1

# Step 2: Normalize and drop oversized column
df = pd.json_normalize(all_products)
df.drop(columns=['body_html'], errors='ignore', inplace=True)

# Step 3: Extract and count tags
tag_counter = Counter()
df['tags'] = df['tags'].fillna('').astype(str)

for tag_string in df['tags']:
    tags = [t.strip().lower() for t in tag_string.split(',') if t.strip()]
    tag_counter.update(tags)

# Step 4: Display tag counts
print("\n📦 Unique Tags and Product Counts:")
for tag, count in tag_counter.most_common():
    print(f"{tag}: {count}")

# Step 5: Filter by desired tag
target_tag = "filament"
filtered_df = df[df['tags'].str.contains(rf'\b{target_tag}\b', case=False, na=False)]

# Step 6: Remove entries with "mystery" or "gift card" in title, tags, or vendor
exclusion_keywords = ['mystery', 'gift card']
for keyword in exclusion_keywords:
    filtered_df = filtered_df[
        ~filtered_df['title'].str.contains(keyword, case=False, na=False) &
        ~filtered_df['tags'].str.contains(keyword, case=False, na=False) &
        ~filtered_df['vendor'].str.contains(keyword, case=False, na=False)
    ]

# Step 7: Rename columns
filtered_df.rename(columns={
    'product_type': 'brand_name',
    'title': 'color_name'
}, inplace=True)

# Step 8: Remove brand_name from color_name if present (case-insensitive)
filtered_df['color_name'] = filtered_df.apply(
    lambda row: re.sub(re.escape(row['brand_name']), '', row['color_name'], flags=re.IGNORECASE).strip()
    if pd.notnull(row['color_name']) and pd.notnull(row['brand_name']) else row['color_name'],
    axis=1
)

# Step 9: Strip trademark symbols from all string columns
trademark_pattern = re.compile(r'[™®]')
for col in filtered_df.select_dtypes(include='object').columns:
    filtered_df[col] = filtered_df[col].str.replace(trademark_pattern, '', regex=True)

print(f"\n✅ Final count after exclusions and cleanup: {len(filtered_df)}")

# Step 10: Export filtered results
filtered_df.to_csv("dbworker/coex3d_filament_index.csv", index=False, encoding='utf-8-sig')
print("Exported to coex3d_filament_index.csv")
