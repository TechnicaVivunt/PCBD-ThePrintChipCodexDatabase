"""
Normalizes material names that 3DFilamentProfiles records as their own
distinct "material" values, but which are really just a marketing
label, variant name, or blend name for a material OpenPrintTag already
recognizes. Left un-normalized, these fall back to material_code "999"
(Unknown) in the generated product_id and produce odd brand_name
values (e.g. "PLA+/Pro" instead of "PLA").

Deliberately NOT auto-normalized: materials OpenPrintTag genuinely has
no code for (PE, SAN, SMP, PIPG, ...) -- those staying "Unknown" is
correct, not a bug, and guessing a code for them would be worse than
leaving them alone. Only rename here once you're sure what the real
underlying material is.
"""

MATERIAL_RENAMES = {
    "PC-ABS": "ABS",
    "PC-PBT": "PBT",
    "PLA+/Pro": "PLA",
    "PETG+": "PETG",
    "ASA+": "ASA",
    "ABS+": "ABS",
    "PA (Nylon)": "PA6",   # generic "Nylon" listings are PA6 in practice
    "PAHT": "PA6",          # High-Temp Nylon
    "APLA": "PLA",          # PLA with anti-stringing additive
    "HT-PLA": "PLA",         # High-Temp PLA
    "MABS": "ABS",          # acrylic-modified ABS
    "CoPA": "PA6",          # co-polyamide
}


def normalize_material(material, material_type=None):
    material = (material or "").strip()
    return MATERIAL_RENAMES.get(material, material)
