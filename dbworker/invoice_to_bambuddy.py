"""
Turns parsed invoice line items into a bambuddy_spoolimport-ready CSV.

Manufacturer-agnostic by design -- it doesn't know or care whether the
line items came from a Bambu Lab email, a Polymaker order, or anything
else, as long as they're shaped per invoice_parsers/__init__.py's
docstring. Add a new manufacturer's parser and this file needs no
changes.

Usage:
    python invoice_to_bambuddy.py bambu_lab_order.eml bambuddy_import.csv
"""
import csv
import sys

from pcdb_lookup import PCDBLookup
from invoice_parsers import get_parser

BAMBUDDY_FIELDNAMES = [
    "filament_brand", "filament_type", "filament_line", "filament_color",
    "filament_color_hex", "filament_sku", "filament_print_temp", "filament_used",
    "spool_id", "tray_uuid", "starting_size_g", "note", "roll_id",
]


def line_item_to_rows(item, lookup, unmatched):
    """One invoice line item can represent multiple physical spools
    (quantity > 1) -- expand it into that many identical spool rows,
    all sharing the same tdfp_id/note, since they're genuinely the
    same product purchased more than once."""
    matched, candidates = lookup.find_match(
        item["manufacturer_name"], item["material"], item["color_hint"],
        material_type_hint=item.get("material_type_hint"),
    )

    if not matched:
        unmatched.append({**item, "candidate_count": len(candidates)})
        return []

    note_parts = [f"spooldb:{matched['tdfp_id']}"]
    if matched.get("tdfp_url"):
        note_parts.append(matched["tdfp_url"])
    if item.get("order_id"):
        price = item.get("unit_price", "")
        currency = item.get("currency", "")
        date = item.get("order_date", "")
        price_str = f"{currency} {price}".strip() if price else ""
        purchase_bits = [b for b in [f"Invoice {item['order_id']}", date, price_str] if b]
        note_parts.append(" / ".join(purchase_bits))
    note = " | ".join(note_parts)

    row = {
        "filament_brand": matched["manufacturer_name"],
        "filament_type": matched["material"],
        "filament_line": matched.get("material_type", ""),
        "filament_color": matched["color_name"],
        "filament_color_hex": (matched.get("rgb_hex") or "").lstrip("#"),
        "filament_sku": matched.get("sku", ""),
        "filament_print_temp": "",
        "filament_used": "0",
        "spool_id": "",
        "tray_uuid": "",
        "starting_size_g": "1000",
        "note": note,
        "roll_id": "",
    }
    quantity = int(item.get("quantity", 1) or 1)
    return [dict(row) for _ in range(quantity)]


def convert(raw_input, manufacturer_name, output_path, master_path=None):
    parser = get_parser(manufacturer_name)
    if parser is None:
        print(f"No invoice parser registered for '{manufacturer_name}'. "
              f"See dbworker/invoice_parsers/__init__.py to add one.")
        sys.exit(1)

    line_items = parser(raw_input)
    lookup = PCDBLookup(master_path)

    unmatched = []
    out_rows = []
    for item in line_items:
        out_rows.extend(line_item_to_rows(item, lookup, unmatched))

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=BAMBUDDY_FIELDNAMES)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"wrote {len(out_rows)} spool(s) -> {output_path}")
    if unmatched:
        print(f"\n{len(unmatched)} line item(s) could NOT be matched -- not included in the output:")
        for u in unmatched:
            reason = "no candidates" if u["candidate_count"] == 0 else f"{u['candidate_count']} ambiguous candidates"
            print(f"  [{reason}] {u['manufacturer_name']} {u['material']} \"{u['color_hint']}\" x{u.get('quantity', 1)}")
        print("Check these manually against PCDB-Database.csv rather than guessing.")

    return out_rows, unmatched


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python invoice_to_bambuddy.py <invoice_file> <manufacturer_name> <output.csv>")
        print("  invoice_file: a .pdf (extracted automatically) or a .txt of already-extracted text")
        sys.exit(1)

    invoice_path = sys.argv[1]
    if invoice_path.lower().endswith(".pdf"):
        from invoice_parsers import bambu  # only module with PDF extraction so far
        raw = bambu.extract_pdf_text(invoice_path)
    else:
        with open(invoice_path, encoding="utf-8", errors="replace") as f:
            raw = f.read()
    convert(raw, sys.argv[2], sys.argv[3])
