"""
Manufacturer code registry for PCDB v2.

The registry is a simple CSV (registry/manufacturers.csv) mapping each
brand name to a stable numeric code. It is APPEND-ONLY by design:

  - First build: every distinct brand found in the source data is
    sorted alphabetically and assigned codes 1, 2, 3, ... in that order.
  - Every later run: any brand not already in the registry gets the
    next unused code, tacked onto the end. Existing codes never change,
    so product_ids already printed on labels stay valid forever.

This intentionally does NOT re-sort or re-number on subsequent runs --
"alphabetical" only describes how the *initial* registry is seeded.
"""
import csv
import os

# Anchored to the repo root regardless of the caller's working directory
# -- this module lives in dbworker/, so its parent is the repo root.
# Using bare relative paths here previously meant running the script
# from inside dbworker/ (e.g. via IDLE, whose working directory is the
# script's own folder) silently wrote output one directory too deep.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY_PATH = os.path.join(_REPO_ROOT, "registry", "manufacturers.csv")


def load_registry(path=REGISTRY_PATH):
    """Returns dict[brand_name] -> int code, and the next free code."""
    mapping = {}
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                mapping[row["manufacturer_name"]] = int(row["manufacturer_code"])
    next_code = max(mapping.values(), default=0) + 1
    return mapping, next_code


def save_registry(mapping, path=REGISTRY_PATH):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    rows = sorted(mapping.items(), key=lambda kv: kv[1])  # order by code, not name
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["manufacturer_code", "manufacturer_name"])
        for name, code in rows:
            writer.writerow([code, name])


def assign_codes(brand_names, path=REGISTRY_PATH):
    """
    Ensures every brand in `brand_names` has a code in the registry,
    seeding new (first-run) entries alphabetically and appending any
    brand not already present without disturbing existing codes.
    Returns the full up-to-date mapping.
    """
    mapping, next_code = load_registry(path)
    is_first_run = len(mapping) == 0

    unseen = sorted(b for b in set(brand_names) if b not in mapping)
    for brand in unseen:
        mapping[brand] = next_code
        next_code += 1

    save_registry(mapping, path)
    if is_first_run:
        print(f"[registry] seeded {len(mapping)} manufacturer codes alphabetically")
    elif unseen:
        print(f"[registry] appended {len(unseen)} new manufacturer(s): {unseen}")
    return mapping
