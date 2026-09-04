"""
PCDB v2 pipeline orchestrator.

Expects a `fetch_rows()` function (see source_3dfp.py) that yields raw
dicts with AT MINIMUM:
    manufacturer_name  -- the company, e.g. "Bambu Lab" (3DFP's "Brand" column)
    material            -- e.g. "PLA" (must be an OpenPrintTag abbreviation)
    color_name           -- e.g. "Jade White"

and optionally any of:
    material_type (e.g. "Basic", "Silk", "CF" -- 3DFP's "Type" column),
    rgb_hex, sku, upc, nozzle_temp_min/max, bed_temp_min/max, density,
    k_value, ams_compat, build_plate_compat, tdfp_id, tdfp_url

`brand_name` in the PCDB sense (a product-LINE name, e.g. "PLA Basic")
has no direct equivalent in 3DFP's schema -- it's synthesized here from
material + material_type, which mirrors what the physical PCX chips
already deboss on their face ("brand and material").

`material` must be an abbreviation OpenPrintTag recognizes (PLA, PETG,
ABS, ...) -- anything else falls back to material_code "999" (Unknown)
in the generated product_id, same as the original PCDB behavior.

This module doesn't care HOW those rows were obtained -- HTML scrape,
a real JSON API, or a manual CSV export from the maintainer would all
plug in here identically.
"""
from manufacturer_registry import assign_codes
from material_normalization import normalize_material
from product_id import ProductIdGenerator, fetch_material_codes
from writers import write_master_csv, write_ptouch_csv


def _synthesize_brand_name(material, material_type):
    material = (material or "").strip()
    material_type = (material_type or "").strip()
    if material_type and material_type.lower() not in ("basic", "standard", ""):
        return f"{material} {material_type}".strip()
    return material or "Unknown"


def run_pipeline(raw_rows, master_path=None, ptouch_path=None):
    """master_path/ptouch_path default to writers.py's repo-root-anchored
    paths -- pass None (the default) rather than a bare relative string
    like "PCDB-Database.csv" unless you specifically want output relative
    to the current working directory."""
    raw_rows = list(raw_rows)
    if not raw_rows:
        print("No rows to process.")
        return []

    # Filter out incomplete rows BEFORE touching the registry, so a bad
    # row (missing manufacturer/color) can never burn a manufacturer code.
    valid_rows, skipped = [], []
    for row in raw_rows:
        if row.get("manufacturer_name", "").strip() and row.get("color_name", "").strip():
            valid_rows.append(row)
        else:
            skipped.append(row)
    if skipped:
        print(f"[pipeline] skipped {len(skipped)} row(s) missing manufacturer_name/color_name")

    if not valid_rows:
        print("No valid rows to process.")
        return []

    manufacturer_names = {r["manufacturer_name"].strip() for r in valid_rows}
    mfg_codes = assign_codes(manufacturer_names)

    material_codes = fetch_material_codes()
    id_gen = ProductIdGenerator(material_codes)

    # Stable output ordering: manufacturer code, then material, then color --
    # keeps sequence numbers assigned in a predictable, reviewable order
    # rather than whatever order the source happened to return rows in.
    valid_rows.sort(key=lambda r: (
        mfg_codes[r["manufacturer_name"].strip()], r.get("material", ""), r.get("color_name", "")
    ))

    output_rows = []
    for row in valid_rows:
        manufacturer = row["manufacturer_name"].strip()
        color = row["color_name"].strip()
        material = normalize_material(row.get("material", ""), row.get("material_type", ""))

        mfg_code = mfg_codes[manufacturer]
        product_id = id_gen.next_id(mfg_code, material, lookup_id=row.get("tdfp_id", ""))
        brand_name = _synthesize_brand_name(material, row.get("material_type", ""))

        output_rows.append({
            "product_id": product_id,
            "manufacturer_name": manufacturer,
            "manufacturer_code": mfg_code,
            "brand_name": brand_name,
            "color_name": color,
            "material": material,
            "material_type": row.get("material_type", ""),
            "rgb_hex": row.get("rgb_hex", ""),
            "sku": row.get("sku", ""),
            "upc": row.get("upc", ""),
            "nozzle_temp_min": row.get("nozzle_temp_min", ""),
            "nozzle_temp_max": row.get("nozzle_temp_max", ""),
            "bed_temp_min": row.get("bed_temp_min", ""),
            "bed_temp_max": row.get("bed_temp_max", ""),
            "density": row.get("density", ""),
            "k_value": row.get("k_value", ""),
            "ams_compat": row.get("ams_compat", ""),
            "build_plate_compat": row.get("build_plate_compat", ""),
            "tdfp_id": row.get("tdfp_id", ""),
            "tdfp_url": row.get("tdfp_url", ""),
        })

    write_master_csv(output_rows, master_path)
    write_ptouch_csv(output_rows, ptouch_path)
    return output_rows

