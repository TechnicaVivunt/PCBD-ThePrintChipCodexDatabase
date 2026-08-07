# PCDB v2 pipeline — exclusively sourced from 3DFilamentProfiles

## What's here and tested
- `dbworker/manufacturer_registry.py` — append-only manufacturer code
  registry. First run seeds codes alphabetically; every run after that
  only ever *appends* new brands at the next free code. Existing codes
  never change, so anything already printed on a label stays valid.
- `dbworker/product_id.py` — generates `PCDB-<mfg>-<seq>-<material>`
  IDs exactly per the original scheme, using OpenPrintTag's material
  codes (fetched live).
- `dbworker/writers.py` — writes two files:
  - `PCDB-Database.csv` — the full rich record (material, material
    type, RGB hex, SKU/UPC, and the 3DFilamentProfiles cross-reference
    ID/URL).
  - `PCDB-PTouch-Import.csv` — **exactly** the 4 columns the PCX Color
    Chip's Brother P-Touch template expects, in that order:
    `Manufacturer, Brand Name, Color Name, ID number`.
- `dbworker/build_pipeline.py` — orchestrates the above from a list of
  raw row-dicts (see its docstring for the exact shape).
- `dbworker/source_3dfp.py` — the real data source. A plain
  `GET /filaments/{brand-slug}` on 3dfilamentprofiles.com returns raw
  HTML that embeds that brand's **complete** filament list as a plain
  JSON array, server-rendered directly into the page (a Next.js
  streamed script chunk) — no JS execution, no pagination within a
  brand, no Selenium. `discover_brand_slugs()` pulls the full
  ~1,103-brand slug list the same way, from `/filaments`'s embedded
  `options.brands` array. Both extraction functions are tested against
  real objects copied out of actual page source (the `rgb`/
  `measured_rgb` fallback and comma-joined SKU cases included).
- `dbworker/run_full_sync.py` — the full-run entrypoint. Checkpoints
  progress to `dbworker/.sync_checkpoint.jsonl` as each brand
  finishes. If some brands fail, it **aborts without touching
  `PCDB-Database.csv`** and preserves the checkpoint so `--resume`
  retries only what failed — verified against a simulated mid-run
  failure (round 1 aborted cleanly with the checkpoint intact; round 2
  with `--resume` skipped the completed brands and retried only the
  failed one, then produced a correct final CSV).
- `.github/workflows/sync_3dfp.yml` — one weekly scheduled workflow,
  replacing the six per-manufacturer Shopify workflows from the
  earlier version of this project. Always passes `--resume`, so a
  checkpoint committed by a partial run gets picked back up
  automatically the following week.

## Running it
```
python dbworker/run_full_sync.py                # fresh full run, all ~1,100 brands
python dbworker/run_full_sync.py --resume        # continue a partial run
python dbworker/run_full_sync.py --limit 10      # smoke-test on a few brands first
python dbworker/run_full_sync.py --allow-partial # build CSVs even if some brands failed
```

**Start with `--limit 10`** and spot-check `PCDB-Database.csv` against
a couple of known filaments (e.g. Bambu PLA Basic colors) before
trusting a full run or turning on the scheduled workflow — I couldn't
verify any of this against the live site myself, since
`3dfilamentprofiles.com` isn't reachable from this sandbox. Everything
here is tested against real page source and simulated network
failures, not against a live end-to-end run.

## Before turning on the scheduled workflow
Send the maintainer a quick note first. A one-off manual pull is a few
minutes of load on a hobbyist's server; a weekly automated job hitting
~1,100 pages is a different kind of ask, and it costs nothing to let
them know it exists — they've shown they're responsive to this kind of
thing. Worth asking whether they'd rather provide a bulk export at
that point too.

## Row shape (for reference / if you ever add another source)
```python
{
    "manufacturer_name": "Bambu Lab",   # required — 3DFP's "Brand" column
    "material": "PLA",                  # required — must be an OpenPrintTag abbreviation
    "color_name": "Jade White",         # required
    "material_type": "Basic",           # optional — 3DFP's "Type" column
    "rgb_hex": "#FFFFFF",               # optional
    "sku": "...", "upc": "...",         # optional
    "tdfp_id": "101",                   # optional — their internal ID, for cross-reference
    "tdfp_url": "https://3dfilamentprofiles.com/filament/details/101",
}
```
