import os
import pandas as pd

# Paths
folder_path = 'dbworker'
master_file = 'PCDB-Database.csv'

# Load master file with UTF-8 encoding
master_df = pd.read_csv(master_file, encoding='utf-8')
master_pairs = set(zip(master_df['brand_name'], master_df['color_name']))
existing_product_ids = set(master_df['product_id']) if 'product_id' in master_df.columns else set()

# Manufacturer and material code mappings
manufacturer_ids = {
    'Polymaker': '2', 'BambuLab': '3', 'Prusa': '4', 'Overture': '5',
    'eSUN': '6', 'AmazonBasics': '7', 'VOXELPLA': '8', 'SUNLU': '9',
    'ERYONE': '10', 'HATCHBOX': '11', 'Unknown': '999'
}

material_code_ids = {
    'PLA': '1', 'PETG': '2', 'ASA': '3', 'ABS': '4', 'TPU': '5', 'TPE': '6',
    'PA': '7', 'PC': '8', 'PP': '9', 'PEEK': '10', 'PVA': '11', 'PVB': '12',
    'COPE': '13', 'PET': '14', 'PPS': '15', 'COPA': '16', 'PPA': '18', 'HIPS': '19',
    'UNKNOWN': '999'
}

# Manufacturer name inference from filename
manufacturer_map = {
    'polymaker': 'Polymaker',
    'voxel': 'VOXELPLA',
    'hatchbox': "HATCHBOX"
}

# Clean trademark symbols and unwanted characters
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

# Material code extraction logic
def extract_material_code(brand):
    brand = str(brand).upper()
    if 'SUPPORT' in brand:
        return 'UNKNOWN'
    if 'PA6' in brand or 'PA12' in brand:
        return 'PA'
    for material in material_code_ids:
        if material in brand:
            return material
    return 'UNKNOWN'

# Count existing (manufacturer, material_code) combinations
existing_counts = (
    master_df.groupby(['manufacturer_name', 'material_code'])
    .size()
    .to_dict()
)

# Generate unique product_id
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

# Track summary stats
new_rows = []
skipped_files = []
processed_files = 0
total_new_rows = 0

# Process each CSV file
for filename in os.listdir(folder_path):
    if filename.endswith('.csv'):
        processed_files += 1
        file_path = os.path.join(folder_path, filename)
        df = pd.read_csv(file_path, encoding='utf-8')

        # Normalize column names
        df.columns = [col.lower() for col in df.columns]

        if 'brand_name' in df.columns and 'color_name' in df.columns:
            df['brand_name'] = df['brand_name'].apply(clean_text)
            df['color_name'] = df['color_name'].apply(clean_text)

            unmatched_mask = df.apply(lambda row: (row['brand_name'], row['color_name']) not in master_pairs, axis=1)
            unmatched_df = df[unmatched_mask]

            if not unmatched_df.empty:
                print(f"➕ Found {len(unmatched_df)} unmatched rows in {filename}")
                unmatched_df = unmatched_df[['brand_name', 'color_name']].copy()
                unmatched_df['source_file'] = filename

                # Assign manufacturer_name
                for prefix, manufacturer in manufacturer_map.items():
                    if filename.lower().startswith(prefix):
                        unmatched_df['manufacturer_name'] = manufacturer
                        break
                else:
                    unmatched_df['manufacturer_name'] = 'Unknown'

                # Assign material_code
                unmatched_df['material_code'] = unmatched_df['brand_name'].apply(extract_material_code)

                # Assign product_id
                unmatched_df['product_id'] = unmatched_df.apply(generate_product_id, axis=1)

                new_rows.append(unmatched_df)
                total_new_rows += len(unmatched_df)
        else:
            skipped_files.append(filename)
            print(f"⚠️ Skipping {filename}: Missing required columns.")

# Append to master file
if new_rows:
    combined_new_rows = pd.concat(new_rows, ignore_index=True)
    updated_master_df = pd.concat([master_df, combined_new_rows], ignore_index=True)
    updated_master_df.to_csv(master_file, index=False, encoding='utf-8')
    print(f"\n✅ Appended {total_new_rows} new rows to {master_file} with full enrichment.")
else:
    print("\n🎉 No unmatched rows found in any file.")

# Summary
print("\n📊 Summary:")
print(f"• Files processed: {processed_files}")
print(f"• Files skipped due to missing columns: {len(skipped_files)}")
if skipped_files:
    print("• Skipped files:")
    for fname in skipped_files:
        print(f"   - {fname}")
print(f"• New rows added: {total_new_rows}")

