import os
import pandas as pd
import re
import requests
import yaml

# Paths
folder_path = 'dbworker'
master_file = 'PCDB-Database.csv'
dry_run = False  # Set to True to simulate without writing changes

# Manufacturer and material code mappings
manufacturer_ids = {
    'Polymaker': '2', 'Bambu Lab': '3', 'Prusa': '4', 'Overture': '5',
    'eSUN': '6', 'AmazonBasics': '7', 'VOXELPLA': '8', 'SUNLU': '9',
    'ERYONE': '10', 'HATCHBOX': '11', 'Unknown': '999'
}

# ✅ Fetch material codes dynamically from OpenPrintTag
OPENPRINTTAG_YAML_URL = "https://raw.githubusercontent.com/prusa3d/OpenPrintTag/main/data/material_type_enum.yaml"

def fetch_material_codes():
    response = requests.get(OPENPRINTTAG_YAML_URL)
    response.raise_for_status()
    data = yaml.safe_load(response.text)
    # Build dict: abbreviation → key (string)
    return {item["abbreviation"]: str(item["key"]) for item in data}

material_code_ids = fetch_material_codes()

manufacturer_map = {
    'polymaker': 'Polymaker',
    'voxel': 'VOXELPLA',
    'hatchbox': "HATCHBOX",
    'bambu': "Bambu Lab",
    'prusament': "Prusa"
}

def clean_text(text):
    if isinstance(text, str):
        return (
            text.replace('™', '')
                .replace('®', '')
                .replace('©', '')
                .replace('Â', '')
                .strip()
        )
    return text

# Track material code corrections
material_corrections = []

def debug_material_inference(row):
    brand = str(row['brand_name'])
    fallback = str(row.get('material_code', '')).strip()
    tokens = re.findall(r'\b[A-Z0-9]+\b', brand.upper())

    inferred = None
    if 'SUPPORT' in tokens:
        inferred = 'UNKNOWN'
    elif 'NYLON' in tokens or 'CoPA' in tokens or ('PA' in tokens and not any(pa in tokens for pa in ['PA12', 'PA11', 'PA66'])):
        inferred = 'PA6'
    elif 'PLA' in tokens or 'rPLA' in tokens:
        inferred = 'PLA'
    elif 'CoPE' in tokens:
        inferred = 'CPE'        
    else:
        for key in material_code_ids:
            if key in tokens:
                inferred = key
                break

    if inferred and inferred != 'UNKNOWN':
        if inferred != fallback and fallback:
            material_corrections.append(row.to_dict())
        return inferred
    else:
        return fallback if fallback else 'UNKNOWN'

# Load master file
master_df = pd.read_csv(master_file, encoding='utf-8')
master_df['brand_name'] = master_df['brand_name'].apply(clean_text)
master_df['color_name'] = master_df['color_name'].apply(clean_text)

# Refresh manufacturer_name and material_code
master_df['manufacturer_name'] = master_df.get('manufacturer_name', pd.Series(['Unknown'] * len(master_df)))
master_df['material_code'] = master_df.apply(debug_material_inference, axis=1)

# Track changed product_ids
changed_ids = []

def update_product_id(row):
    original_id = str(row['product_id'])
    if pd.isna(original_id) or not original_id.startswith("PCDB-"):
        return original_id

    match = re.match(r'^PCDB-(\d{3})-(\d{3})-(\d+)$', original_id)
    if not match:
        return original_id

    old_mfg_id, seq, old_mat_id = match.groups()
    mfg = row['manufacturer_name']
    mat = row['material_code']
    new_mfg_id = manufacturer_ids.get(mfg, '999')
    new_mat_id = material_code_ids.get(mat, '999')

    new_id = f"PCDB-{new_mfg_id.zfill(3)}-{seq}-{new_mat_id}"
    if new_id != original_id:
        changed_ids.append((original_id, new_id))
    return new_id

print("🔧 Checking and correcting product_id codes in master file...")
master_df['product_id'] = master_df.apply(update_product_id, axis=1)

if changed_ids:
    print(f"\n🔁 Updated {len(changed_ids)} product_id values:")
    for old, new in changed_ids:
        print(f"• {old} → {new}")
else:
    print("\n✅ All product_id values are already correct.")

if material_corrections:
    print(f"\n🧪 Corrected {len(material_corrections)} material_code values based on brand_name:")
    for row in material_corrections:
        print("•", row)

master_pairs = set(zip(master_df['brand_name'], master_df['color_name']))

# Count existing (manufacturer, material_code) combinations
existing_counts = (
    master_df.groupby(['manufacturer_name', 'material_code'])
    .size()
    .to_dict()
)
existing_product_ids = set(master_df['product_id'])

def generate_product_id(row):
    mfg = row['manufacturer_name']
    mat = row['material_code']
    mfg_id = manufacturer_ids.get(mfg, '999')
    mat_id = material_code_ids.get(mat, '999')
    key = (mfg, mat)
    count = existing_counts.get(key, 0) + 1

    while True:
        product_id = f"PCDB-{mfg_id.zfill(3)}-{count:03d}-{mat_id}"
        if product_id not in existing_product_ids:
            existing_product_ids.add(product_id)
            existing_counts[key] = count
            return product_id
        count += 1

# Process new rows from folder
new_rows = []
skipped_files = []
processed_files = 0
total_new_rows = 0

for filename in os.listdir(folder_path):
    if filename.endswith('.csv'):
        processed_files += 1
        file_path = os.path.join(folder_path, filename)
        df = pd.read_csv(file_path, encoding='utf-8')
        df.columns = [col.lower() for col in df.columns]

        required_cols = ['brand_name', 'color_name']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            skipped_files.append((filename, missing_cols))
            print(f"⚠️ Skipping {filename}: Missing columns {missing_cols}")
            continue

        df['brand_name'] = df['brand_name'].apply(clean_text)
        df['color_name'] = df['color_name'].apply(clean_text)

        unmatched_mask = df.apply(lambda row: (row['brand_name'], row['color_name']) not in master_pairs, axis=1)
        unmatched_df = df[unmatched_mask]

        if not unmatched_df.empty:
            print(f"➕ Found {len(unmatched_df)} unmatched rows in {filename}")
            unmatched_df = unmatched_df[['brand_name', 'color_name']].copy()
            unmatched_df['source_file'] = filename

            for prefix, manufacturer in manufacturer_map.items():
                if filename.lower().startswith(prefix):
                    unmatched_df['manufacturer_name'] = manufacturer
                    break
            else:
                unmatched_df['manufacturer_name'] = 'Unknown'

            unmatched_df['material_code'] = unmatched_df.apply(debug_material_inference, axis=1)
            unmatched_df['product_id'] = unmatched_df.apply(generate_product_id, axis=1)

            new_rows.append(unmatched_df)
            total_new_rows += len(unmatched_df)

# Combine and write updated master file
if new_rows:
    combined_new_rows = pd.concat(new_rows, ignore_index=True)
    updated_master_df = pd.concat([master_df, combined_new_rows], ignore_index=True)
else:
    updated_master_df = master_df  # Ensure corrections are saved even if no new rows

if not dry_run:
    try:
        updated_master_df.to_csv(master_file, index=False, encoding='utf-8')
        print(f"\n✅ Saved all changes to {master_file}")
    except Exception as e:
        print(f"\n❌ Failed to write to {master_file}: {e}")
else:
    print(f"\n🧪 Dry run mode: No changes written to {master_file}")

print("\n📊 Summary:")
print(f"• Files processed: {processed_files}")
print(f"• New rows added: {total_new_rows}")
print(f"• Product ID corrections: {len(changed_ids)}")
print(f"• Material code corrections: {len(material_corrections)}")
print(f"• Files skipped: {len(skipped_files)}")
