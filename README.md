# PCDB Swatch Reference DB

Generates a print-ready CSV for Brother P-Touch, matching the
[PCX Color Chip](https://www.printables.com/model/440526-pcx-color-chip)
label format -- one label per **catalog entry** (a brand/material/color
combination), for a physical reference drawer of filament swatches.

This is the type-level reference catalog only. It has no knowledge of
which filaments you actually own or how much of each -- for that
(inventory tracking synced with Bambuddy, individual spool labels),
that's a separate, not-yet-built companion project.

# PCDB v2 pipeline — sourced from 3DFilamentProfiles

## Status: working, verified against the live site
Confirmed pulling correct data from the live site: 1,103 brand slugs
discovered, real per-brand filament rows extracted (e.g. 325 filaments
for Bambu Lab with real colors like `Jade White (10100)`, correct
SKUs/UPCs, and RGB hex codes).

## What's here
- `dbworker/manufacturer_registry.py` — append-only manufacturer code
  registry. First run seeds codes alphabetically; every run after that
  only ever *appends* new brands at the next free code. Existing codes
  never change, so anything already printed on a label stays valid.
- `dbworker/product_id.py` — generates `PCDB-<mfg>-<tdfp_id>-<material>`
  IDs. The middle segment is 3DFilamentProfiles' own filament ID
  (`tdfp_id`), not a self-assigned sequence -- the same number that's
  in their QR codes (`spooldb.com/f/<id>`), so the ID printed on a
  label is a direct, one-step lookup on their site. Falls back to an
  auto-incremented sequence only if a row somehow lacks a tdfp_id.
- `dbworker/writers.py` — writes two files:
  - `PCDB-Database.csv` — the full rich record (material, material
    type, RGB hex, SKU/UPC, and the 3DFilamentProfiles cross-reference
    ID/URL).
  - `PCDB-PTouch-Import.csv` — **exactly** the 4 columns the PCX Color
    Chip's Brother P-Touch template expects, in that order:
    `Manufacturer, Brand Name, Color Name, ID number`.
- `dbworker/build_pipeline.py` — orchestrates the above from a list of
  raw row-dicts (see its docstring for the exact shape).
- `dbworker/source_3dfp.py` — the data source. See "How the data is
  fetched" below.
- `dbworker/run_full_sync.py` — the full-run entrypoint. Checkpoints
  progress to `dbworker/.sync_checkpoint.jsonl` as each brand finishes.
  If some brands fail, it aborts without touching `PCDB-Database.csv`
  and preserves the checkpoint so `--resume` retries only what failed.
- `dbworker/debug_fetch.py` — diagnostic script; fetches a couple of
  live pages and reports on the embedded data structure. Useful if the
  site's structure ever changes and extraction breaks.
- `dbworker/sync_and_publish.py` — the scheduled entrypoint. Runs the
  full sync, then commits and pushes directly to `main` if anything
  actually changed. See "Keeping it current automatically" below.

## How the data is fetched
A plain `GET /filaments/{brand-slug}` on 3dfilamentprofiles.com
returns raw HTML that embeds that brand's **complete** filament list
directly in the page — no client-side JS, no pagination within a
brand, no browser automation. `discover_brand_slugs()` pulls the full
~1,103-brand slug list the same way from `/filaments`.

The data is embedded as a Next.js "Flight" stream chunk:

```
self.__next_f.push([1, "16:[\"$\",...,{\"options\":{\"brands\":[...]}}]"])
```

`push()`'s argument is itself valid JSON: `[chunk_id, chunk_string]`.
`chunk_string`'s own content is JSON too (e.g. `"rows":[...]`), but
with every quote backslash-escaped, since it's nested inside an outer
JSON string. `source_3dfp.py` decodes `push()`'s argument as JSON and
lets the decoder handle the unescaping, then regexes the now-plain
`"rows":[...]` / `"brands":[...]` blob out of the result.

Two things worth knowing if you're maintaining this:
- **Headers matter.** An unrecognized custom User-Agent triggers an
  immediate 429 (this site's hosting has its own bot-management layer)
  before request frequency is even a factor. `source_3dfp.py` sends
  ordinary browser headers instead.
- **Most of the 1,103 brands have very few filaments.** A lot of the
  alphabetically-clustered "3D-something" names early in a run (3D
  Aura, 3D Best, 3D Club, etc.) are real, distinct catalog entries,
  just sparsely filled in — not a scraper bug. Possible optimization:
  skip brands with `popularity: 0` in the discovery step, since that's
  known upfront without fetching each brand's page.

## Running it locally
```
python dbworker/run_full_sync.py                # fresh full run, all ~1,100 brands
python dbworker/run_full_sync.py --resume        # continue a partial run
python dbworker/run_full_sync.py --limit 10      # smoke-test on a few brands first
python dbworker/run_full_sync.py --allow-partial # build CSVs even if some brands failed
```

If extraction ever silently returns 0 rows/brands (e.g. after a site
redesign), run `dbworker/debug_fetch.py` first — it saves raw page
HTML and reports where the expected keys do/don't show up.

## Keeping it current automatically
This deliberately does NOT run through GitHub Actions. GitHub-hosted
runner IPs get 429'd by 3dfilamentprofiles.com's bot protection --
confirmed via a real failed run, not a guess -- and a self-hosted
runner fixes that but means installing and babysitting one more
always-on service. Since a plain local run already works fine (same
IP as everything else you run by hand), the simplest fix is to run it
locally on a schedule instead.

```
python dbworker/sync_and_publish.py                # full run, commit + push if changed
python dbworker/sync_and_publish.py --limit 10      # smoke-test
python dbworker/sync_and_publish.py --no-push       # commit locally, review before pushing
```

It only commits when `PCDB-Database.csv`, `PCDB-PTouch-Import.csv`, or
`registry/manufacturers.csv` actually changed -- a run that finds
nothing new does nothing, no empty commits. Uses your existing local
git identity and credentials, the same ones a manual `git push`
already needs -- nothing extra to configure beyond having push access
to the repo.

**To run it on a schedule (Windows Task Scheduler):**
1. Task Scheduler → Create Task
2. Trigger: Weekly, whatever day/time you want
3. Action: Start a program
   - Program: `python` (or the full path from `where python`)
   - Arguments: `dbworker\sync_and_publish.py`
   - Start in: the repo's root folder (this matters -- it's how the
     script finds its own paths)
4. Under Conditions, uncheck "Start the task only if the computer is
   on AC power" if this is a laptop, so it still runs on battery.

The machine just needs to be on and unlocked at the scheduled time --
no service to install, nothing else running in the background.

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
