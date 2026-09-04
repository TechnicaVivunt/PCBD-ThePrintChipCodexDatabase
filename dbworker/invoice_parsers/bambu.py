"""
Bambu Lab order-confirmation invoice (PDF) parser.

Built and tested against a real invoice PDF, not a guess at the
structure -- text extracted via pdfplumber turned out messier than
expected in ways worth documenting, since the next person maintaining
this needs to know why the regex looks the way it does:

  - Multi-page invoices repeat a "Product Tax Items / Items Qty
    Price(excl.tax) Tax / discount amount SubTotal" header block at
    the top of every page after the first. Stripped before parsing --
    otherwise it gets swallowed into whatever field is mid-match when
    a page breaks (confirmed: it corrupted a Variant field this way).
  - A line item CAN span a page break. The qty/price/tax row for one
    real item landed on page 2 while its "Variant: ..." line landed on
    page 3, with nothing else in between once the header noise above
    is stripped. Parsing must concatenate all pages before matching,
    never parse page-by-page.
  - The SKU column wraps onto a second line for any SKU that doesn't
    fit, e.g. "G00-R00-1.75-1000-\nSPLFREE". Usually that wrapped
    fragment appears BEFORE the qty/price/tax numbers in extracted
    text, but for at least one real item it appeared AFTER them
    instead ("...KENTUCKY(6%) $0.72 $11.99\nSPLFREE\nVariant: ...").
    The regex tolerates the fragment landing on either side.
  - The Variant line itself wraps arbitrarily, sometimes mid-token
    (a real example split "1kg" into "1\nkg" across the line break).
    Whitespace in the captured variant text is normalized to single
    spaces after extraction rather than assumed away in the regex.
  - Bambu's own internal color code is always a plain integer in
    parens directly after the color name, e.g. "Red(30201)" or
    "Turquoise (10605)" (space before the paren is inconsistent).
    That numeric-parens pattern is what distinguishes an actual
    filament line item from a non-filament one (AMS hub units, PTFE
    tubes, etc. have a Variant field but never that numeric-code
    shape) -- used as the filter instead of a hardcoded product list.

Usage:
    from invoice_parsers import bambu
    text = bambu.extract_pdf_text("invoice.pdf")   # requires pdfplumber
    line_items = bambu.parse(text)
"""
import re

HEADER_NOISE_RE = re.compile(
    r"Product\s+Tax\s+Items\s*\n?"
    r"Items\s+Qty\s+Price\(excl\.tax\)\s+Tax\s*\n?"
    r"discount\s+amount\s+SubTotal\s*\n?",
)

ITEM_RE = re.compile(
    r"(?P<name>[A-Za-z][A-Za-z0-9 /+\-]*?)\s*\n"
    r"SKU:\s*(?P<sku>.*?)\s+"
    r"(?P<qty>\d+)\s+\$(?P<price>[\d.]+)\s+"
    r"(?:\$(?P<discount>[\d.]+)\s+)?"
    r"(?P<tax_state>[A-Z]+)\((?P<tax_pct>[\d.]+)%\)\s+"
    r"\$(?P<tax_amt>[\d.]+)\s+\$(?P<subtotal>[\d.]+)"
    r"(?:\s*\n?(?P<sku_tail>[A-Z0-9]+))?\s*\n"  # wrapped SKU fragment, either side of the numbers
    r"Variant:\s*(?P<variant>.*?)"
    r"(?=\n[A-Za-z][A-Za-z0-9 /+\-]*\s*\nSKU:|\nItems Subtotal|\Z)",
    re.DOTALL,
)

# A real filament variant always has the manufacturer's numeric color
# code in parens right after the color name -- "Red(30201) / Refill /
# 1kg", "Turquoise (10605) / Refill / 1kg". Non-filament line items
# (AMS hubs, PTFE tubes, etc.) have a Variant field but never this
# specific shape, so it doubles as the filter for "is this filament".
VARIANT_RE = re.compile(
    r"^(?P<color>.+?)\s*\((?P<code>\d+)\)\s*/\s*(?P<format>[^/]+?)\s*/\s*(?P<weight>.+)$"
)


def extract_pdf_text(pdf_path):
    """Concatenates every page's text -- never parse page-by-page, see
    the module docstring for why (a real item spanned a page break)."""
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() for page in pdf.pages)


def parse(raw_text):
    text = HEADER_NOISE_RE.sub("", raw_text)

    order_id_m = re.search(r"Order Number:\s*(\S+)", text)
    order_id = order_id_m.group(1) if order_id_m else ""
    order_date_m = re.search(r"Invoice Date:\s*([\d-]+)", text)
    order_date = order_date_m.group(1) if order_date_m else ""

    line_items = []
    for m in ITEM_RE.finditer(text):
        variant_raw = re.sub(r"\s+", " ", m.group("variant")).strip()
        vm = VARIANT_RE.match(variant_raw)
        if not vm:
            continue  # not a filament line item (AMS hub, PTFE tubes, etc.)

        product_name = m.group("name").strip()
        parts = product_name.split(" ", 1)
        material = parts[0]
        material_type_hint = parts[1] if len(parts) > 1 else None

        line_items.append({
            "manufacturer_name": "Bambu Lab",
            "material": material,
            "material_type_hint": material_type_hint,
            "color_hint": vm.group("color").strip(),
            "quantity": int(m.group("qty")),
            "unit_price": m.group("price"),
            "currency": "USD",
            "order_id": order_id,
            "order_date": order_date,
        })

    return line_items
