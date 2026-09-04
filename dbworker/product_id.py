"""
PCDB product ID generation: PCDB-<manufacturer_code>-<lookup_id>-<material_code>

- manufacturer_code: from manufacturer_registry (3-digit, zero-padded)
- lookup_id: the 3DFilamentProfiles filament ID (their "tdfp_id") for this
  exact filament, unpadded. This is the whole point of the scheme change:
  the same number is (a) what's printed on the PCX chip, (b) what
  spooldb.com's own QR codes point to (spooldb.com/f/<id>), and (c) what
  goes in a Bambuddy spool's note field as "spooldb:<id>" -- one number,
  three lookups, no separate cross-reference table to maintain.
  Falls back to an auto-incremented per-(manufacturer,material) sequence
  (the original scheme) only for rows that somehow lack a tdfp_id --
  shouldn't happen with the 3DFP source, but kept as a safety net for
  any future data source that doesn't carry an external ID.
- material_code: numeric key from OpenPrintTag's material_type_enum.yaml
"""
import requests
import yaml

OPENPRINTTAG_YAML_URL = "https://raw.githubusercontent.com/prusa3d/OpenPrintTag/main/data/material_type_enum.yaml"


def fetch_material_codes():
    """abbreviation (e.g. 'PLA') -> numeric key (e.g. '0')"""
    response = requests.get(OPENPRINTTAG_YAML_URL, timeout=20)
    response.raise_for_status()
    data = yaml.safe_load(response.text)
    return {item["abbreviation"]: str(item["key"]) for item in data}


class ProductIdGenerator:
    def __init__(self, material_codes):
        self.material_codes = material_codes
        self._counters = {}  # (mfg_code, material_code) -> last used fallback sequence
        self._seen_lookup_ids = {}  # lookup_id -> product_id, to catch real collisions

    def next_id(self, manufacturer_code, material_abbreviation, lookup_id=None):
        material_code = self.material_codes.get(material_abbreviation, "999")

        lookup_id = (lookup_id or "").strip()
        if lookup_id:
            product_id = f"PCDB-{manufacturer_code:03d}-{lookup_id}-{material_code}"
            # 3DFP filament IDs are globally unique, so a collision here would
            # mean two different rows carrying the same tdfp_id -- a real data
            # problem worth surfacing rather than silently overwriting.
            prior = self._seen_lookup_ids.get(lookup_id)
            if prior and prior != product_id:
                print(f"[product_id] WARNING: tdfp_id {lookup_id} produced two "
                      f"different product_ids ({prior} vs {product_id}) -- check "
                      f"for a duplicate/misassigned row")
            self._seen_lookup_ids[lookup_id] = product_id
            return product_id

        # Fallback: no external ID available, use the original auto-increment scheme.
        key = (manufacturer_code, material_code)
        seq = self._counters.get(key, 0) + 1
        self._counters[key] = seq
        return f"PCDB-{manufacturer_code:03d}-{seq:03d}-{material_code}"
