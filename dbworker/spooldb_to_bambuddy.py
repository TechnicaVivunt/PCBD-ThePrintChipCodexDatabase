"""
Bridge: spooldb.com "My Spools" export -> bambuddy_spoolimport CSV.

Workflow this fits into:
  1. You buy filament; a Bambu Lab order confirmation email arrives.
  2. spooldb.com's own invoice-import feature parses it into "My Spools"
     -- nothing to build here, it already works.
  3. Periodically, export that list: spooldb.com/my/spools -> Export ->
     "Export My Spools (CSV)".
  4. Run this script on that export. It writes a CSV in the format
     bambuddy_spoolimport (https://github.com/bsaunder/bambuddy_spoolimport)
     expects, with the spooldb filament_id embedded in the `note` field
     as the cross-reference key -- the same number that appears on the
     PCX label (PCDB-<mfg>-<tdfp_id>-<material>) and in spooldb's own
     QR codes (spooldb.com/f/<id>). Scan/read any one of the three and
     the same number gets you to the other two.
  5. Run bambuddy_spoolimport's own import_spools.py against that CSV
     to actually create the spools in Bambuddy.

Field mapping, and what's deliberately left blank:
  - filament_brand   <- spooldb "brand" (the manufacturer, e.g. "Bambu Lab")
  - filament_type    <- spooldb "material"
  - filament_line    <- spooldb "material_type" (e.g. "Basic", "Silk")
    NOTE: bambuddy_spoolimport maps filament_line to Bambuddy's "subtype"
    field, which in practice holds material-type-ish values ("Basic")
    rather than manufacturer product lines ("PolyLite") -- confirmed
    against a real Bambuddy inventory export. filament_line here follows
    that, not PCDB's own "brand_name" (product-line) convention.
  - filament_color / filament_color_hex <- spooldb "color" / "rgb"
    (spooldb's color already carries Bambu's internal swatch code in
    parens, e.g. "Black (30101)" -- passed through as-is)
  - filament_used, starting_size_g <- derived from remaining_grams,
    assuming a 1000g spool (spooldb's export doesn't include a
    starting-weight column; flagged below if a row implies otherwise)
  - note <- "spooldb:<filament_id>" plus spool_url and any purchase
    info spooldb captured (invoice number, price, date), since
    Bambuddy's schema has no dedicated fields for those
  - filament_sku, filament_print_temp, spool_id, tray_uuid, roll_id
    are left blank -- not present in spooldb's My Spools export, and
    spool_id/SPOOL_CATALOG_MAP is optional in bambuddy_spoolimport
    (confirmed by reading its source: a spool imports fine standalone,
    with no pre-existing Bambuddy catalog entry required)

Usage:
    python spooldb_to_bambuddy.py my_spools_export.csv bambuddy_import.csv
"""
import csv
import sys

ASSUMED_STARTING_WEIGHT_G = 1000


def convert_row(row, warnings, row_number):
    filament_id = (row.get("filament_id") or "").strip()
    remaining_raw = (row.get("remaining_grams") or "").strip()

    try:
        remaining = float(remaining_raw) if remaining_raw else ASSUMED_STARTING_WEIGHT_G
    except ValueError:
        remaining = ASSUMED_STARTING_WEIGHT_G

    if remaining > ASSUMED_STARTING_WEIGHT_G:
        warnings.append(
            f"row {row_number} ({row.get('short_code', '?')}): remaining_grams "
            f"({remaining}) exceeds the assumed {ASSUMED_STARTING_WEIGHT_G}g starting "
            f"weight -- filament_used will be clamped to 0, check this spool manually"
        )
    filament_used = max(0, ASSUMED_STARTING_WEIGHT_G - remaining)

    note_parts = []
    if filament_id:
        note_parts.append(f"spooldb:{filament_id}")
    if row.get("spool_url"):
        note_parts.append(row["spool_url"])
    if row.get("spool_purchase_invoice"):
        price = row.get("spool_purchase_price", "")
        currency = row.get("spool_purchase_currency", "")
        date = row.get("spool_purchase_date", "")
        price_str = f"{currency} {price}".strip() if price else ""
        purchase_bits = [b for b in [f"Invoice {row['spool_purchase_invoice']}", date, price_str] if b]
        note_parts.append(" / ".join(purchase_bits))
    if row.get("notes"):
        note_parts.append(row["notes"])

    return {
        "filament_brand": row.get("brand", ""),
        "filament_type": row.get("material", ""),
        "filament_line": row.get("material_type", ""),
        "filament_color": row.get("color", ""),
        "filament_color_hex": (row.get("rgb") or "").lstrip("#"),
        "filament_sku": "",
        "filament_print_temp": "",
        "filament_used": f"{filament_used:.2f}",
        "spool_id": "",
        "tray_uuid": "",
        "starting_size_g": str(ASSUMED_STARTING_WEIGHT_G),
        "note": " | ".join(note_parts),
        "roll_id": "",
    }


BAMBUDDY_FIELDNAMES = [
    "filament_brand", "filament_type", "filament_line", "filament_color",
    "filament_color_hex", "filament_sku", "filament_print_temp", "filament_used",
    "spool_id", "tray_uuid", "starting_size_g", "note", "roll_id",
]


def convert(input_path, output_path):
    warnings = []
    out_rows = []
    skipped = 0

    with open(input_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            if not (row.get("material") or "").strip():
                print(f"[skip] row {i}: no material, skipping")
                skipped += 1
                continue
            out_rows.append(convert_row(row, warnings, i))

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=BAMBUDDY_FIELDNAMES)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"wrote {len(out_rows)} spool(s) -> {output_path}  ({skipped} skipped)")
    for w in warnings:
        print(f"  [WARN] {w}")
    return out_rows


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python spooldb_to_bambuddy.py <spooldb_export.csv> <bambuddy_import.csv>")
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])
