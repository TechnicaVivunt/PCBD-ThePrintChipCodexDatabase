"""
Re-runs the pipeline against the ALREADY-FETCHED PCDB-Database.csv --
zero calls to 3dfilamentprofiles.com. Use this whenever a change only
affects local transformation logic (material normalization,
brand_name synthesis, etc.) and doesn't need fresh data from the site.

Reads the existing PCDB-Database.csv as input, feeds it back through
the normal pipeline (which re-derives product_id/brand_name/material
using current logic, including material_normalization.py), and
overwrites both output files with the corrected version.

registry/manufacturers.csv is left untouched and reused as-is --
assign_codes() only appends brand-new manufacturers, and every
manufacturer here already has a code, so nothing there changes.

The only network call this makes at all is OpenPrintTag's material
code list (raw.githubusercontent.com, inside product_id.py) -- a
single lightweight GitHub fetch, unrelated to and separate from
3DFilamentProfiles.

Usage:
    python dbworker/renormalize_existing.py
"""
import csv

from build_pipeline import run_pipeline
from writers import DEFAULT_MASTER_PATH

# Every column PCDB-Database.csv actually has, mapped straight through
# as the raw-row shape build_pipeline.py expects.
PASSTHROUGH_FIELDS = [
    "manufacturer_name", "material", "material_type", "color_name",
    "rgb_hex", "sku", "upc", "nozzle_temp_min", "nozzle_temp_max",
    "bed_temp_min", "bed_temp_max", "density", "k_value",
    "ams_compat", "build_plate_compat", "tdfp_id", "tdfp_url",
]


def load_existing_rows(path=None):
    path = path or DEFAULT_MASTER_PATH
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    existing = load_existing_rows()
    print(f"Loaded {len(existing)} existing rows from PCDB-Database.csv -- no site calls made")

    raw_rows = [{field: r.get(field, "") for field in PASSTHROUGH_FIELDS} for r in existing]
    run_pipeline(raw_rows)


if __name__ == "__main__":
    main()
