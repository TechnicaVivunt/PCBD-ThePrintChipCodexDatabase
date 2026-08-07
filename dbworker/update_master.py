import os
import re
import pandas as pd
import requests
import yaml

# Paths
FOLDER_PATH = "dbworker"
MASTER_FILE = "PCDB-Database.csv"
MANUFACTURERS_YAML = "dbworker/manufacturers.yaml"
DRY_RUN = False  # Set True to simulate without writing changes

# Manufacturer codes for the PCDB-<mfg>-<seq>-<mat> id scheme
manufacturer_ids = {
    "Polymaker": "2", "Bambu Lab": "3", "Prusa": "4", "Overture": "5",
    "eSUN": "6", "AmazonBasics": "7", "VOXELPLA": "8", "SUNLU": "9",
    "ERYONE": "10", "HATCHBOX": "11", "Coex3D": "12", "Unknown": "999",
}

OPENPRINTTAG_YAML_URL = "https://raw.githubusercontent.com/prusa3d/OpenPrintTag/main/data/material_type_enum.yaml"


def fetch_material_codes():
    response = requests.get(OPENPRINTTAG_YAML_URL, timeout=20)
    response.raise_for_status()
    data = yaml.safe_load(response.text)
    return {item["abbreviation"]: str(item["key"]) for item in data}


def load_manufacturer_map():
    """Which output CSV belongs to which manufacturer -- now sourced
    from manufacturers.yaml (single source of truth) instead of a
    hardcoded filename-prefix dict that silently drops any brand you
    forget to add (this is how Coex3D previously went unmatched)."""
    mapping = {}
    if os.path.exists(MANUFACTURERS_YAML):
        with open(MANUFACTURERS_YAML, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        for key, entry in cfg.items():
            filename = os.path.basename(entry["output_file"]).lower()
            mapping[filename] = entry["manufacturer_name"]
    # Non-Shopify / bespoke indexers not present in manufacturers.yaml
    mapping.setdefault("prusament_filament_index.csv", "Prusa")
    return mapping


def clean_text(text):
    if isinstance(text, str):
        return text.replace("™", "").replace("®", "").replace("©", "").replace("Â", "").strip()
    return text


def normalize_key(brand, color):
    """Case/whitespace-insensitive comparison key. Previously this was
    an exact string tuple, so 'Jet Black' vs 'jet black ' (or a stray
    trademark symbol) would slip through as a 'new' duplicate row
    instead of matching the existing entry."""
    def norm(s):
        s = clean_text(str(s) if s is not None else "")
        return re.sub(r"\s+", " ", s).strip().lower()
    return (norm(brand), norm(color))


material_corrections = []


def debug_material_inference(row, material_code_ids):
    brand = str(row["brand_name"])
    fallback = str(row.get("material_code", "")).strip()
    tokens = re.findall(r"\b[A-Z0-9]+\b", brand.upper())

    inferred = None
    if "SUPPORT" in tokens:
        inferred = "UNKNOWN"
    elif "NYLON" in tokens or "CoPA" in tokens or ("PA" in tokens and not any(pa in tokens for pa in ["PA12", "PA11", "PA66"])):
        inferred = "PA6"
    elif "PLA" in tokens or "rPLA" in tokens:
        inferred = "PLA"
    elif "CoPE" in tokens:
        inferred = "CPE"
    else:
        for key in material_code_ids:
            if key in tokens:
                inferred = key
                break

    if inferred and inferred != "UNKNOWN":
        if inferred != fallback and fallback:
            material_corrections.append(row.to_dict())
        return inferred
    return fallback if fallback else "UNKNOWN"


def main():
    material_code_ids = fetch_material_codes()
    manufacturer_map = load_manufacturer_map()

    master_df = pd.read_csv(MASTER_FILE, encoding="utf-8")
    master_df["brand_name"] = master_df["brand_name"].apply(clean_text)
    master_df["color_name"] = master_df["color_name"].apply(clean_text)
    master_df["manufacturer_name"] = master_df.get("manufacturer_name", pd.Series(["Unknown"] * len(master_df)))
    master_df["material_code"] = master_df.apply(lambda r: debug_material_inference(r, material_code_ids), axis=1)

    changed_ids = []

    def update_product_id(row):
        original_id = str(row["product_id"])
        if pd.isna(original_id) or not original_id.startswith("PCDB-"):
            return original_id
        match = re.match(r"^PCDB-(\d{3})-(\d{3})-(\d+)$", original_id)
        if not match:
            return original_id
        _old_mfg_id, seq, _old_mat_id = match.groups()
        mfg, mat = row["manufacturer_name"], row["material_code"]
        new_mfg_id = manufacturer_ids.get(mfg, "999")
        new_mat_id = material_code_ids.get(mat, "999")
        new_id = f"PCDB-{new_mfg_id.zfill(3)}-{seq}-{new_mat_id}"
        if new_id != original_id:
            changed_ids.append((original_id, new_id))
        return new_id

    print("Checking and correcting product_id codes in master file...")
    master_df["product_id"] = master_df.apply(update_product_id, axis=1)

    # Normalized lookup set for matching against incoming rows
    master_keys = {normalize_key(b, c) for b, c in zip(master_df["brand_name"], master_df["color_name"])}

    existing_counts = master_df.groupby(["manufacturer_name", "material_code"]).size().to_dict()
    existing_product_ids = set(master_df["product_id"])

    def generate_product_id(row):
        mfg, mat = row["manufacturer_name"], row["material_code"]
        mfg_id = manufacturer_ids.get(mfg, "999")
        mat_id = material_code_ids.get(mat, "999")
        key = (mfg, mat)
        count = existing_counts.get(key, 0) + 1
        while True:
            pid = f"PCDB-{mfg_id.zfill(3)}-{count:03d}-{mat_id}"
            if pid not in existing_product_ids:
                existing_product_ids.add(pid)
                existing_counts[key] = count
                return pid
            count += 1

    new_rows, skipped_files, processed_files, total_new_rows = [], [], 0, 0

    for filename in os.listdir(FOLDER_PATH):
        if not filename.endswith(".csv"):
            continue
        processed_files += 1
        df = pd.read_csv(os.path.join(FOLDER_PATH, filename), encoding="utf-8")
        df.columns = [c.lower() for c in df.columns]

        missing = [c for c in ["brand_name", "color_name"] if c not in df.columns]
        if missing:
            skipped_files.append((filename, missing))
            print(f"Skipping {filename}: missing columns {missing}")
            continue

        df["brand_name"] = df["brand_name"].apply(clean_text)
        df["color_name"] = df["color_name"].apply(clean_text)

        unmatched_mask = df.apply(
            lambda row: normalize_key(row["brand_name"], row["color_name"]) not in master_keys, axis=1
        )
        unmatched_df = df[unmatched_mask]
        if unmatched_df.empty:
            continue

        print(f"Found {len(unmatched_df)} unmatched rows in {filename}")
        unmatched_df = unmatched_df[["brand_name", "color_name"]].copy()
        unmatched_df["source_file"] = filename
        unmatched_df["manufacturer_name"] = manufacturer_map.get(filename.lower(), "Unknown")
        unmatched_df["material_code"] = unmatched_df.apply(lambda r: debug_material_inference(r, material_code_ids), axis=1)
        unmatched_df["product_id"] = unmatched_df.apply(generate_product_id, axis=1)

        # Keep new rows out of future duplicate checks within this same run
        for b, c in zip(unmatched_df["brand_name"], unmatched_df["color_name"]):
            master_keys.add(normalize_key(b, c))

        new_rows.append(unmatched_df)
        total_new_rows += len(unmatched_df)

    updated_master_df = pd.concat([master_df] + new_rows, ignore_index=True) if new_rows else master_df

    if not DRY_RUN:
        try:
            updated_master_df.to_csv(MASTER_FILE, index=False, encoding="utf-8")
            print(f"Saved all changes to {MASTER_FILE}")
        except Exception as e:
            print(f"Failed to write to {MASTER_FILE}: {e}")
    else:
        print(f"Dry run: no changes written to {MASTER_FILE}")

    print("\nSummary:")
    print(f"  Files processed: {processed_files}")
    print(f"  New rows added: {total_new_rows}")
    print(f"  Product ID corrections: {len(changed_ids)}")
    print(f"  Material code corrections: {len(material_corrections)}")
    print(f"  Files skipped: {len(skipped_files)}")


if __name__ == "__main__":
    main()
