"""
Single entrypoint for all filament indexers.

Usage:
    python dbworker/run_indexers.py --all
    python dbworker/run_indexers.py --only polymaker,bambu
    python dbworker/run_indexers.py --only prusa

Shopify-backed manufacturers (see manufacturers.yaml) are run through the
shared engine. Prusa uses its own GraphQL fetcher since it's not a
Shopify store. Add new non-Shopify brands the same way: a small fetch_*
function in bespoke_indexers.py, registered in BESPOKE below.
"""
import argparse
import sys
import yaml

from shopify_engine import run_shopify_indexer
from parsers import PARSERS
from bespoke_indexers import BESPOKE

CONFIG_PATH = "dbworker/manufacturers.yaml"


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="run every configured indexer")
    ap.add_argument("--only", help="comma-separated manufacturer keys to run")
    args = ap.parse_args()

    shopify_config = load_config()
    all_keys = list(shopify_config.keys()) + list(BESPOKE.keys())

    if args.only:
        keys = [k.strip() for k in args.only.split(",") if k.strip()]
    elif args.all:
        keys = all_keys
    else:
        ap.error("pass --all or --only key1,key2")
        return

    unknown = [k for k in keys if k not in all_keys]
    if unknown:
        print(f"Unknown manufacturer key(s): {unknown}. Known: {all_keys}")
        sys.exit(1)

    summary = {}
    for key in keys:
        if key in shopify_config:
            n = run_shopify_indexer(shopify_config[key], PARSERS[key])
        else:
            n = BESPOKE[key]()
        summary[key] = n

    print("\n=== Summary ===")
    for key, n in summary.items():
        print(f"  {key}: {n} rows")


if __name__ == "__main__":
    main()
