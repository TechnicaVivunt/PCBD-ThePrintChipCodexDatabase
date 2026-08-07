"""
Full sync entrypoint: pulls every brand from 3DFilamentProfiles and
rebuilds PCDB-Database.csv + PCDB-PTouch-Import.csv.

Checkpointed: raw rows are written to a JSON Lines file as each brand
finishes, so a run interrupted partway through (network blip, rate
limit, CI timeout) can resume with --resume instead of re-fetching
every brand from scratch. This matters here specifically because it's
~1,100 requests against one person's server -- restarting from zero
after a late failure would be a second full pass for no reason.

Usage:
    python dbworker/run_full_sync.py                  # fresh full run
    python dbworker/run_full_sync.py --resume          # continue a partial run
    python dbworker/run_full_sync.py --limit 10        # smoke-test on a few brands
    python dbworker/run_full_sync.py --delay 1.0        # slower than default
"""
import argparse
import json
import os
import sys

from source_3dfp import discover_brand_slugs, fetch_brand_rows, make_session
from build_pipeline import run_pipeline

CHECKPOINT_PATH = "dbworker/.sync_checkpoint.jsonl"
DONE_BRANDS_PATH = "dbworker/.sync_done_brands.txt"


def load_checkpoint():
    """Returns (raw_rows, done_brand_slugs) from any prior partial run."""
    rows = []
    done = set()
    if os.path.exists(CHECKPOINT_PATH):
        with open(CHECKPOINT_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    if os.path.exists(DONE_BRANDS_PATH):
        with open(DONE_BRANDS_PATH, encoding="utf-8") as f:
            done = {line.strip() for line in f if line.strip()}
    return rows, done


def append_checkpoint(brand_slug, rows):
    os.makedirs(os.path.dirname(CHECKPOINT_PATH), exist_ok=True)
    with open(CHECKPOINT_PATH, "a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    with open(DONE_BRANDS_PATH, "a", encoding="utf-8") as f:
        f.write(brand_slug + "\n")


def clear_checkpoint():
    for path in (CHECKPOINT_PATH, DONE_BRANDS_PATH):
        if os.path.exists(path):
            os.remove(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resume", action="store_true",
                     help="continue a partial run instead of starting fresh")
    ap.add_argument("--limit", type=int, default=None,
                     help="only process the first N brands (for testing)")
    ap.add_argument("--delay", type=float, default=0.5,
                     help="seconds to wait between brand page requests")
    ap.add_argument("--allow-partial", action="store_true",
                     help="build CSVs even if some brands failed to fetch "
                          "(default: abort and preserve checkpoint for --resume)")
    args = ap.parse_args()

    if args.resume:
        raw_rows, done_slugs = load_checkpoint()
        print(f"[resume] {len(raw_rows)} rows already collected from {len(done_slugs)} brands")
    else:
        clear_checkpoint()
        raw_rows, done_slugs = [], set()

    session = make_session()
    print("Discovering brand slugs...")
    slugs = discover_brand_slugs(session=session)
    if args.limit:
        slugs = slugs[:args.limit]
    remaining = [s for s in slugs if s not in done_slugs]
    print(f"{len(remaining)} of {len(slugs)} brands left to fetch")

    failed_slugs = []
    for i, slug in enumerate(remaining, 1):
        try:
            rows = fetch_brand_rows(session, slug, delay=args.delay)
            print(f"[{i}/{len(remaining)}] {slug}: {len(rows)} filaments")
            append_checkpoint(slug, rows)
            raw_rows.extend(rows)
        except Exception as e:
            print(f"[{i}/{len(remaining)}] {slug}: ERROR {e}")
            failed_slugs.append(slug)
            # Deliberately not marked done -- --resume will retry it.
            continue

    print(f"\nTotal rows collected: {len(raw_rows)}")
    if not raw_rows:
        print("Nothing collected -- aborting without touching PCDB-Database.csv")
        sys.exit(1)

    if failed_slugs:
        print(f"\n{len(failed_slugs)} brand(s) failed and were NOT included: {failed_slugs}")
        print("Checkpoint preserved -- run again with --resume to retry just these, "
              "or pass --allow-partial to build the CSVs anyway from what succeeded.")
        if not args.allow_partial:
            sys.exit(1)
        print("--allow-partial set: proceeding with partial data.")

    run_pipeline(raw_rows)
    if not failed_slugs:
        clear_checkpoint()  # only fully clear on a completely successful run
        print("Done. Checkpoint cleared.")
    else:
        print("Done, but checkpoint kept (partial run) -- resume later to fill in the rest.")


if __name__ == "__main__":
    main()
