# PCDB scraper refactor — what changed and why

## The problem with the old setup
- **6 near-identical scraper scripts.** Polymaker, Hatchbox, VOXELPLA,
  Overture, and Coex3D each reimplemented pagination, cleaning, and CSV
  writing for the same kind of endpoint (Shopify `/products.json`).
  Bambu Lab used Selenium to drive a real headless Chrome browser through
  a hardcoded list of ~50 product URLs with a 15-second sleep after each
  one — 13+ minutes minimum, and it breaks the moment Bambu changes a
  CSS class.
- **6 near-identical GitHub Actions workflows** (checkout → install →
  run → diff → PR → auto-merge label → Discord ping), each requiring
  the same edit if you wanted to change any shared behavior.
- **Coex3D was orphaned** — it had a working scraper but no entry in
  `update_master.py`'s manufacturer map and no workflow, so its output
  never made it into the master database.
- **Exact-string matching** in `update_master.py` meant a stray
  trademark symbol or extra space between a scraper's output and the
  master file created a silent duplicate instead of updating the
  existing row.
- No timeouts or retries anywhere, so a slow endpoint could hang a
  GitHub Actions job indefinitely.

## What's here instead
- **`dbworker/shopify_engine.py`** — the shared machinery (pagination,
  retries/timeouts, text cleaning, exclude-list handling, de-duping,
  CSV writing) used by every Shopify-backed brand.
- **`dbworker/parsers.py`** — the one genuinely manufacturer-specific
  bit: a small function per brand that turns one Shopify product into
  rows. **Bambu Lab is now rewritten to hit `us.store.bambulab.com`'s**
  (Bambu's official, branded storefront domain — confirmed live) **own
  `products.json` feed**, with `bambulab-us.myshopify.com` (the
  underlying Shopify domain, same catalog) as an automatic fallback if
  the custom domain ever blocks scraper traffic — `shopify_engine.py`
  now supports a list of candidate URLs for exactly this case. This
  replaces Selenium entirely.

  Bambu's real variant titles follow a pattern like
  `Jade White (10100) / Filament with spool / 1kg` — I found this on
  the live site, and `parse_bambu` now extracts the color name,
  Bambu's own internal color code, packaging format, and weight into
  separate columns instead of leaving it as one blob of text.

  **One honest limitation I can't fully rule out:** on some Shopify
  stores, a product that's only offered in one packaging option but
  shown with multiple *colors* on the page uses a single generic
  Shopify variant (titled `Default Title`) and drives the color swatch
  purely through front-end JS/metafields rather than real product
  variants — which is presumably why the original script resorted to
  Selenium in the first place. I've handled the case where Shopify
  labels a single variant `Default Title` or `(default)` by falling
  back to the variant's `option1`/`option2`/`option3` value instead,
  but if Bambu's actual live catalog turns out to encode color *only*
  in JS/metafields with no variant-level signal at all, no static-JSON
  scraper (this one included) can recover it — that would be a real
  reason to keep a lightweight Selenium fallback for that specific
  product. **I couldn't confirm which case applies** because every
  live fetch of `us.store.bambulab.com` from this sandbox returned an
  anti-bot block (HTTP 402), so this needs a real test run before you
  trust it in CI — see step 2 below.
- **`dbworker/manufacturers.yaml`** — one registry entry per brand.
  Adding a new Shopify-backed manufacturer is now: add a config block
  here + a parser function, no new script.
- **`dbworker/run_indexers.py`** — single CLI (`--all` or
  `--only polymaker,bambu`) instead of running six separate scripts.
- **`dbworker/update_master.py`** — normalized (case/whitespace-
  insensitive) matching instead of exact string equality, and the
  manufacturer-name lookup now comes from `manufacturers.yaml` instead
  of a hardcoded prefix dict — so nothing can silently go unmapped the
  way Coex3D did.
- **`.github/workflows/update_filaments.yml`** — one matrix-based
  workflow instead of six. `fail-fast: false` so one manufacturer
  breaking doesn't block the others; a final `merge-master` job runs
  `update_master.py` once after all scrapes finish, rather than each
  manufacturer's workflow separately racing to merge into main.

## Migrating
1. Drop these files into the existing repo, replacing
   `dbworker/update_master.py` and deleting the old per-manufacturer
   scraper scripts + their workflow files (`polymaker_workflow.yml`,
   `hatchbox_workflow.yml`, `prusa_workflow.yml`,
   `bambu_workflow.yml`, `fetch_overture_filaments.yml`) once the new
   ones are confirmed working.
2. Run `pip install requests pyyaml pandas`, then
   `python dbworker/run_indexers.py --all` locally and diff the output
   CSVs against the current ones in `dbworker/` to sanity-check the
   parsers before trusting them in CI.
3. Everything I could test offline (all 6 parsers against representative
   sample payloads, and `update_master.py` against your real
   `PCDB-Database.csv` and existing `dbworker/*.csv` files) ran clean.
   What I couldn't test — because this sandbox can't reach arbitrary
   manufacturer websites — is the live HTTP responses themselves, so
   treat the first real run as a dry run and check the diffs.
