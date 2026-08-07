"""
Per-manufacturer parsing rules for the shared Shopify engine.

Every Shopify store structures product/variant titles a little
differently, so this is the one bit of code that has to stay
manufacturer-specific. Everything else (fetching, retrying, de-duping,
writing CSVs) lives in shopify_engine.py.

Each function takes (product: dict, exclude_set: set) and returns a
list of row-dicts matching that manufacturer's `fieldnames` in
manufacturers.yaml.
"""
import re
from shopify_engine import clean_text, is_excluded


# ---------------------------------------------------------------- Polymaker
def parse_polymaker(product, exclude_set):
    vendor = clean_text(product.get("vendor"))
    brand_name = clean_text(product.get("title"), strip_parens=True)

    if brand_name.lower() == "polylite pla":
        return []

    def valid_option1(v):
        s = v.lower()
        bad = ["(old packaging)", "(old formula)", "2.85mm", "2.85 mm",
               "sample box", "refill"]
        return not any(b in s for b in bad)

    def valid_option2(v):
        if not v:
            return False
        s = v.lower()
        if "kg" in s:
            try:
                return float(s.replace("kg", "").strip()) <= 1
            except ValueError:
                return False
        return True

    rows = []
    for variant in product.get("variants", []):
        option1 = clean_text(variant.get("option1"), strip_parens=True)
        option2 = clean_text(variant.get("option2"), strip_parens=True)
        color_name = clean_text(variant.get("option3"), strip_parens=True)

        if not valid_option1(option1) or not valid_option2(option2):
            continue
        if is_excluded(brand_name, color_name, exclude_set):
            continue

        rows.append({
            "brand_name": brand_name,
            "color_name": color_name,
            "variant_title": clean_text(variant.get("title")),
            "vendor": vendor,
            "price": clean_text(variant.get("price")),
            "grams": clean_text(variant.get("grams")),
            "inventory_quantity": clean_text(variant.get("inventory_quantity")),
            "option1": option1,
            "option2": option2,
            "product_url": f"https://us.polymaker.com/products/{product.get('handle', '')}",
        })
    return rows


# ----------------------------------------------------------------- Hatchbox
def parse_hatchbox(product, exclude_set):
    title = clean_text(product.get("title"))
    vendor = clean_text(product.get("vendor"))
    product_type = clean_text(product.get("product_type"))
    title_upper = title.upper()

    m = re.search(r"\b(PLA|ABS|PETG|WOOD)\b\s+FILAMENT", title_upper)
    filament_type = m.group(1) if m else ""
    brand_name = filament_type

    color_name = ""
    if filament_type:
        pm = re.search(r"^(.*?)\b" + re.escape(filament_type) + r"\b\s+FILAMENT", title_upper)
        color_name = pm.group(1).strip().title() if pm else ""

    if is_excluded(brand_name, color_name, exclude_set):
        return []

    rows = []
    for variant in product.get("variants", []):
        rows.append({
            "Title": title,
            "Vendor": vendor,
            "Product Type": product_type,
            "Variant Title": clean_text(variant.get("title")),
            "Price": clean_text(variant.get("price")),
            "SKU": clean_text(variant.get("sku")),
            "Available": variant.get("available", ""),
            "brand_name": brand_name,
            "color_name": color_name,
            "product_url": f"https://www.hatchbox3d.com/products/{product.get('handle', '')}",
        })
    return rows


# ------------------------------------------------------------------ VoxelPLA
def parse_voxelpla(product, exclude_set):
    title = clean_text(product.get("title"))
    title_lower = title.lower()
    if "filament" not in title_lower or "bundle" in title_lower:
        return []

    diameter_m = re.search(r"\d+\.?\d*mm", title, re.IGNORECASE)
    diameter = diameter_m.group(0) if diameter_m else ""
    weight_m = re.search(r"\((\d+\.?\d*kg)\)", title, re.IGNORECASE)
    weight = weight_m.group(1) if weight_m else ""

    material = ""
    if "pla" in title_lower:
        material = "PLA"
    elif "petg" in title_lower:
        material = "PETG"

    clean_title = re.sub(r"\((?!\d+\.?\d*kg\)).*?\)", "", title)
    clean_title = clean_title.replace(diameter, "").replace(weight, "")
    clean_title = clean_title.replace("Filament", "").strip(" -")
    clean_lower = clean_title.lower()

    patterns = [
        (r"voxel\s*galaxy\s*petg\+?\s*hs", "Voxel Galaxy PETG+ HS"),
        (r"voxelpetg\+?\s*hs", "VOXEL PETG+ HS"),
        (r"voxelpla\s*pla\+?\s*hs", "Voxel PLA+ HS"),
    ]
    brand_name = color_name = None
    for pattern, name in patterns:
        if re.search(pattern, clean_lower):
            brand_name = name
            color_name = re.sub(pattern, "", clean_lower, flags=re.IGNORECASE).strip()
            break
    if brand_name is None:
        parts = clean_title.split()
        brand_name = " ".join(parts[:2])
        color_name = " ".join(parts[2:])

    color_name = re.sub(r"[()]", "", color_name).strip()
    color_name = " ".join(w.title() for w in color_name.split())

    if is_excluded(brand_name, color_name, exclude_set):
        return []

    variants = product.get("variants", [])
    price = clean_text(variants[0].get("price")) if variants else ""

    return [{
        "brand_name": brand_name,
        "color_name": color_name,
        "diameter": diameter,
        "weight": weight,
        "material": material,
        "price": price,
        "product_url": f"https://voxelpla.com/products/{product.get('handle', '')}",
    }]


# ------------------------------------------------------------------ Overture
def parse_overture(product, exclude_set):
    raw_name = product.get("title", "")
    if "refill" in raw_name.lower():
        return []
    product_name = raw_name.replace("Overture", "").replace("3D Printer Filament", "").strip()
    product_url = f"https://overture3d.com/products/{product.get('handle', '')}"

    rows = []
    for variant in product.get("variants", []):
        variant_title = variant.get("title", "")
        if "refill" in variant_title.lower():
            continue

        price_raw = variant.get("price", "")
        try:
            price = "{:.2f}".format(float(price_raw))
        except (TypeError, ValueError):
            price = price_raw

        color = variant.get("option1") or variant.get("option2") or variant.get("option3") or ""
        brand_name = clean_text(product_name)
        color_name = clean_text(color)

        if is_excluded(brand_name, color_name, exclude_set):
            continue

        rows.append({
            "Product": product_name,
            "Variant": variant_title,
            "SKU": variant.get("sku", ""),
            "Price": price,
            "Available": variant.get("available", ""),
            "Color": color,
            "URL": product_url,
            "brand_name": brand_name,
            "color_name": color_name,
        })
    return rows


# ------------------------------------------------------------------- Coex3D
def parse_coex3d(product, exclude_set):
    title = clean_text(product.get("title"))
    tags = [t.strip().lower() for t in str(product.get("tags", "")).split(",") if t.strip()]
    if "filament" not in tags:
        return []

    vendor = clean_text(product.get("vendor"))
    excl_kw = ["mystery", "gift card"]
    haystack = f"{title} {' '.join(tags)} {vendor}".lower()
    if any(k in haystack for k in excl_kw):
        return []

    brand_name = clean_text(product.get("product_type"))
    color_name = re.sub(re.escape(brand_name), "", title, flags=re.IGNORECASE).strip() if brand_name else title

    if is_excluded(brand_name, color_name, exclude_set):
        return []

    rows = []
    for variant in product.get("variants", []):
        rows.append({
            "brand_name": brand_name,
            "color_name": color_name,
            "vendor": vendor,
            "variant_title": clean_text(variant.get("title")),
            "price": clean_text(variant.get("price")),
            "sku": clean_text(variant.get("sku")),
            "available": variant.get("available", ""),
            "product_url": f"https://coex3d.com/products/{product.get('handle', '')}",
        })
    return rows


# --------------------------------------------------------------- Bambu Lab
# Bambu's product/variant titles follow a recognizable pattern on their
# official store, e.g. "Jade White (10100) / Filament with spool / 1kg"
# -- a color name, Bambu's own internal color code in parentheses, the
# packaging format, and the spool weight, slash-separated. Not every
# variant follows this exactly (some products only have one or two of
# these segments), so the regex pieces are all optional and we fall
# back to the raw variant title when nothing matches.
BAMBU_VARIANT_RE = re.compile(
    r"^\s*(?P<color>[^(/]+?)\s*"
    r"(?:\((?P<code>[A-Za-z0-9]+)\)\s*)?"
    r"(?:/\s*(?P<format>[^/]+?)\s*)?"
    r"(?:/\s*(?P<weight>[\d.]+\s*(?:kg|g))\s*)?$",
    re.IGNORECASE,
)


def _parse_bambu_variant_title(raw_title):
    """Pull color name / Bambu color code / packaging format / weight out
    of a variant title. Returns a dict with any fields it found; missing
    fields are empty strings rather than raising, since not every
    product's variants follow the full pattern."""
    text = clean_text(raw_title)
    m = BAMBU_VARIANT_RE.match(text)
    if not m:
        return {"color_name": text, "bambu_color_code": "", "filament_format": "", "weight": ""}
    return {
        "color_name": clean_text(m.group("color") or text),
        "bambu_color_code": clean_text(m.group("code") or ""),
        "filament_format": clean_text(m.group("format") or ""),
        "weight": clean_text(m.group("weight") or ""),
    }


def parse_bambu(product, exclude_set):
    """Bambu Lab's official storefront (us.store.bambulab.com, with
    bambulab-us.myshopify.com as a same-catalog fallback -- see
    manufacturers.yaml) is Shopify under the hood, exposing the same
    products.json feed used by every other brand here. This replaces
    the old Selenium scraper that drove a real Chrome browser through a
    hardcoded list of ~50 product pages with a 15s sleep after each one.

    No title-based filtering is needed: base_url already scopes the
    fetch to the "bambu-lab-3d-printer-filament" collection, so
    everything returned belongs in the index (unlike e.g. coex3d's
    storefront, which mixes filament with unrelated products and has
    to be filtered by tag)."""
    title = clean_text(product.get("title"))
    product_url = f"https://us.store.bambulab.com/products/{product.get('handle', '')}"

    rows = []
    for variant in product.get("variants", []):
        raw_variant_title = (variant.get("title") or "").strip()
        option_fallback = (
            variant.get("option1") or variant.get("option2") or variant.get("option3") or ""
        )
        # Shopify's placeholder title for a product with only one variant
        # -- prefer the actual option value (real color) if there is one.
        if raw_variant_title.lower() in ("", "default title", "(default)") and option_fallback:
            raw_variant_title = option_fallback
        parsed = _parse_bambu_variant_title(raw_variant_title or option_fallback)
        brand_name = title

        if is_excluded(brand_name, parsed["color_name"], exclude_set):
            continue

        rows.append({
            "brand_name": brand_name,
            "variant_title": clean_text(raw_variant_title),
            "color_name": parsed["color_name"],
            "bambu_color_code": parsed["bambu_color_code"],
            "filament_format": parsed["filament_format"],
            "weight": parsed["weight"],
            "price": clean_text(variant.get("price")),
            "sku": clean_text(variant.get("sku")),
            "available": variant.get("available", ""),
            "product_url": product_url,
        })
    return rows


PARSERS = {
    "polymaker": parse_polymaker,
    "hatchbox": parse_hatchbox,
    "voxelpla": parse_voxelpla,
    "overture": parse_overture,
    "coex3d": parse_coex3d,
    "bambu": parse_bambu,
}
