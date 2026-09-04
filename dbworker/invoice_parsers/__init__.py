"""
Registry of invoice parsers, one per manufacturer.

Each parser module exposes a single function:

    parse(raw_text_or_html: str) -> list[dict]

returning line items shaped like:

    {
        "manufacturer_name": "Bambu Lab",
        "material": "PLA",                # OpenPrintTag abbreviation
        "material_type_hint": "Basic",    # optional, helps disambiguate
        "color_hint": "Jade White",       # as named on the invoice
        "quantity": 2,
        "unit_price": "19.99",
        "currency": "USD",
        "order_id": "US770642294654164992",
        "order_date": "2026-08-31",
        "order_url": "https://store.bambulab.com/account/orders/...",
    }

Add a new manufacturer by dropping a new module in this package and
registering it here -- nothing else in the pipeline needs to change.
"""
from . import bambu

PARSERS = {
    "bambu lab": bambu.parse,
}


def get_parser(manufacturer_name):
    return PARSERS.get(manufacturer_name.strip().lower())
