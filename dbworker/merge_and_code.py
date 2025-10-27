import pandas as pd
import sys
import os

# ---------------- Filament type derivation ----------------
def derive_filament_type(material_name: str) -> str:
    if not isinstance(material_name, str):
        return "Unknown"
    material_name = material_name.upper()

    patterns = {
        "PA6-GF": "(PA) NYLON",
        "PA6": "(PA) NYLON",
        "NYLON": "(PA) NYLON",
        "PETG": "PETG",
        "PLA": "PLA",
        "ASA": "ASA",
        "ABS": "ABS",
        "TPU": "TPU",
        "TPE": "TPE",
        "PC": "PC",
        "PP": "PP",
        "PEEK": "PEEK",
        "PVA": "PVA",
        "PVB": "PVB",
        "COPE": "CoPE",
        "PET": "PET",
        "PPS": "PPS",
        "COPA": "CoPA",
        "PPA": "PPA",
        "HIPS": "HIPS",
    }

    for key, filament in patterns.items():
        if key in material_name:
            return filament
    return "Unknown"

# ---------------- Filament and Vendor mappings ----------------
filament_types = {
    "PLA": 1, "PETG": 2, "ASA": 3, "ABS": 4, "TPU": 5,
    "TPE": 6, "(PA) NYLON": 7, "PC": 8, "PP": 9, "PEEK": 10,
    "PVA": 11, "PVB": 12, "CoPE": 13, "PET": 14, "PPS": 15,
    "CoPA": 16, "PET": 17, "PPA": 18, "HIPS": 19
}

vendor_map = {
    "PolyMaker": 2,
    "BambuLab": 3,
    "Prusa": 4,
    "Overture": 5,
    "eSUN": 6,
    "AmazonBasics": 7,
    "VOXELPLA": 8,
    "SUNLU": 9,
    "ERYONE": 10
}

# ---------------- Load master CSV ----------------
MASTER_FILE = "PCDB-Database.csv"
if not os.path.exists(MASTER_FILE):
    print(f"{MASTER_FILE} not found. Creating empty master file.")
    master = pd.DataFrame()
else:
    master = pd.read_csv(MASTER_FILE)

if "product_code" not in master.columns:
    master["product_code"] = ""

# ---------------- Utility functions ----------------
def extract_sequence(code: str) -> int:
    try:
        return int(code.split("-")[2])
    except:
        return -1

def assign_product_code(row, max_sequences):
    filament_name = row["filament_type"]
    filament_num = filament_types.get(filament_name)
    if filament_num is None:
        raise ValueError(f"Unknown filament type: {filament_name}")

    vendor_name = row["vendor"]
    vendor_num = vendor_map.get(vendor_name)
    if vendor_num is None:
        raise ValueError(f"Unknown vendor: {vendor_name}")

    max_sequences[vendor_num] += 1
    seq_str = str(max_sequences[vendor_num]).zfill(3)
    vendor_str = str(vendor_num).zfill(3)
    return f"PCDB-{vendor_str}-{seq_str}-{filament_num}"

# ---------------- Process each new CSV ----------------
csv_files = sys.argv[1:]
if not csv_files:
    print("No CSV files provided. Usage: python merge_and_code.py new_file1.csv [new_file2.csv ...]")
    sys.exit(1)

total_added = 0

for new_file in csv_files:
    if not os.path.exists(new_file):
        print(f"{new_file} does not exist, skipping.")
        continue

    print(f"Processing {new_file} ...")
    new_df = pd.read_csv(new_file)

    # Keep only columns existing in master
    new_filtered = new_df[master.columns.intersection(new_df.columns)].copy() if not master.empty else new_df.copy()

    if "product_code" not in new_filtered.columns:
        new_filtered["product_code"] = ""

    # Derive filament_type if missing
    if "filament_type" not in new_filtered.columns or new_filtered["filament_type"].isnull().all() or (new_filtered["filament_type"] == "Unknown").all():
        if "brand_name" not in new_filtered.columns:
            raise ValueError(f"{new_file} missing 'brand_name' column needed to derive filament_type")
        new_filtered["filament_type"] = new_filtered["brand_name"].apply(derive_filament_type)

    # Find missing rows
    compare_cols = master.columns.drop("product_code") if not master.empty else new_filtered.columns
    missing = new_filtered.merge(master[compare_cols], how='outer', indicator=True, on=list(compare_cols) if not master.empty else None).query('_merge=="left_only"').drop('_merge', axis=1)

    if missing.empty:
        print(f"No new rows in {new_file}, skipping.")
        continue  # Skip this CSV entirely

    # Track max sequences per vendor
    max_sequences = {}
    for vendor_num in vendor_map.values():
        if master.empty:
            max_sequences[vendor_num] = 0
            continue
        codes = master.loc[master["product_code"].str.contains(f"-{str(vendor_num).zfill(3)}-", na=False), "product_code"]
        seqs = codes.map(extract_sequence)
        max_sequences[vendor_num] = seqs.max() if not seqs.empty else 0

    # Assign product codes
    for idx in missing.index:
        missing.at[idx, "product_code"] = assign_product_code(missing.loc[idx], max_sequences)

    # Append missing rows
    master = pd.concat([master, missing], ignore_index=True)
    total_added += len(missing)

# ---------------- Save master CSV ----------------
if total_added > 0:
    master.to_csv(MASTER_FILE, index=False)
    print(f"Added {total_added} new rows to {MASTER_FILE}")
else:
    print("No new rows to add from any CSVs")
