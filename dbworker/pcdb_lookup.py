"""
Looks up invoice line items against PCDB-Database.csv to find the exact
matching filament record -- specifically its tdfp_id, since that's what
lets a purchased item get the same PCDB-<mfg>-<tdfp_id>-<material> ID
that appears on the label and in spooldb's own QR codes.

An invoice usually names a color without the manufacturer's internal
swatch code ("Jade White") while PCDB's color_name -- taken straight
from 3DFilamentProfiles -- often carries it ("Jade White (10100)", per
real data seen from Bambu Lab). Matching therefore tries progressively
looser comparisons rather than requiring an exact string match.
"""
import csv
import os
import re
from collections import defaultdict

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MASTER_PATH = os.path.join(_REPO_ROOT, "PCDB-Database.csv")

_CODE_SUFFIX_RE = re.compile(r"\s*\([^)]*\)\s*$")


def _normalize_color(color):
    """Strip a trailing '(code)' suffix and normalize whitespace/case,
    so "Jade White (10100)" and "jade white" compare equal."""
    color = _CODE_SUFFIX_RE.sub("", color or "")
    return re.sub(r"\s+", " ", color).strip().lower()


class PCDBLookup:
    def __init__(self, master_path=None):
        master_path = master_path or DEFAULT_MASTER_PATH
        self.rows = []
        with open(master_path, encoding="utf-8-sig") as f:
            self.rows = list(csv.DictReader(f))

        # Index by (manufacturer, material) -> list of rows, for fast filtering
        # before the color comparison.
        self._by_mfg_material = defaultdict(list)
        for row in self.rows:
            key = (row["manufacturer_name"].strip().lower(), row["material"].strip().lower())
            self._by_mfg_material[key].append(row)

    def find_match(self, manufacturer, material, color_hint, material_type_hint=None):
        """
        Returns (matched_row, candidates) where:
          - matched_row is the single best match, or None if zero or
            more than one candidate remained after narrowing
          - candidates is the full list considered, for diagnosing a
            miss or an ambiguous match
        """
        key = (manufacturer.strip().lower(), material.strip().lower())
        pool = self._by_mfg_material.get(key, [])
        if not pool:
            return None, []

        target_color = _normalize_color(color_hint)

        # Pass 1: exact color_name match (including any code suffix, in
        # case the invoice happens to include it).
        exact = [r for r in pool if r["color_name"].strip().lower() == (color_hint or "").strip().lower()]
        if len(exact) == 1:
            return exact[0], exact

        # Pass 2: normalized match, ignoring a "(code)" suffix on either side.
        normalized = [r for r in pool if _normalize_color(r["color_name"]) == target_color]
        if material_type_hint:
            type_filtered = [r for r in normalized
                              if r.get("material_type", "").strip().lower() == material_type_hint.strip().lower()]
            if len(type_filtered) == 1:
                return type_filtered[0], type_filtered
            if type_filtered:
                normalized = type_filtered  # narrow further passes to this set

        if len(normalized) == 1:
            return normalized[0], normalized

        # Ambiguous (0 or 2+ candidates) -- caller should flag this rather
        # than guess.
        return None, normalized or pool
