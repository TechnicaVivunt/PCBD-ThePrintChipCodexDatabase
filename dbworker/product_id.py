"""
PCDB product ID generation: PCDB-<manufacturer_code>-<sequence>-<material_code>

- manufacturer_code: from manufacturer_registry (3-digit, zero-padded)
- sequence: restarts at 001 for each (manufacturer, material) pair,
  same behavior as the original schema
- material_code: numeric key from OpenPrintTag's material_type_enum.yaml
  (kept as-is -- this is the one part of the original schema that
  wasn't manufacturer-specific and doesn't need rebuilding)
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
        self._counters = {}  # (mfg_code, material_code) -> last used sequence

    def next_id(self, manufacturer_code, material_abbreviation):
        material_code = self.material_codes.get(material_abbreviation, "999")
        key = (manufacturer_code, material_code)
        seq = self._counters.get(key, 0) + 1
        self._counters[key] = seq
        return f"PCDB-{manufacturer_code:03d}-{seq:03d}-{material_code}"
