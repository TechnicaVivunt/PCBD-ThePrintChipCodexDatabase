"""
PCDB v2 output writers.

Two files come out of every pipeline run:

1. PCDB-Database.csv -- the full master record: everything we know
   about each filament, including the 3DFilamentProfiles cross-
   reference. This is PCDB's own source of truth.

2. PCDB-PTouch-Import.csv -- exactly the 4 columns the Brother P-Touch
   "Connect to Database" workflow expects, in the order the PCX Color
   Chip template's instructions specify:

       Manufacturer, Brand Name, Color Name, ID number

   Nothing else. This is the file you actually point P-Touch at.
"""
import csv
import os

# Anchored to the repo root regardless of the caller's working directory
# -- see manufacturer_registry.py for why this matters (a script run
# from inside dbworker/ previously wrote output one directory too deep).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MASTER_PATH = os.path.join(_REPO_ROOT, "PCDB-Database.csv")
DEFAULT_PTOUCH_PATH = os.path.join(_REPO_ROOT, "PCDB-PTouch-Import.csv")

MASTER_FIELDNAMES = [
    "product_id",
    "manufacturer_name",
    "manufacturer_code",
    "brand_name",
    "color_name",
    "material",
    "material_type",
    "rgb_hex",
    "sku",
    "upc",
    "nozzle_temp_min",
    "nozzle_temp_max",
    "bed_temp_min",
    "bed_temp_max",
    "density",
    "k_value",
    "ams_compat",
    "build_plate_compat",
    "tdfp_id",
    "tdfp_url",
]

PTOUCH_FIELDNAMES = ["manufacturer_name", "brand_name", "color_name", "product_id"]


def write_master_csv(rows, path=None):
    path = path or DEFAULT_MASTER_PATH
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=MASTER_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"[master] wrote {len(rows)} rows -> {path}")


def write_ptouch_csv(rows, path=None):
    """Column order matters here -- P-Touch maps fields positionally
    (left to right: Manufacturer, Brand Name, Color Name, ID number)
    per the PCX Color Chip template instructions."""
    path = path or DEFAULT_PTOUCH_PATH
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Manufacturer", "Brand Name", "Color Name", "ID number"])
        for row in rows:
            writer.writerow([
                row.get("manufacturer_name", ""),
                row.get("brand_name", ""),
                row.get("color_name", ""),
                row.get("product_id", ""),
            ])
    print(f"[ptouch] wrote {len(rows)} rows -> {path}")
