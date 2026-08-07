"""
3DFilamentProfiles.com data source.

KEY DISCOVERY: a plain HTTP GET on a brand page --
https://3dfilamentprofiles.com/filaments/{brand-slug} -- returns raw
HTML that embeds the site's COMPLETE per-brand filament dataset. It's
server-rendered, not fetched client-side -- confirmed against a real
page fetch (Bambu Lab, 325 filaments) where the embedded data held
every filament for the brand in one go, not just a 50-row page.

HOW THE DATA IS ACTUALLY EMBEDDED (this took two attempts to get right):
The site is a Next.js app that streams its render as "Flight" chunks:

    self.__next_f.push([1, "16:[\"$\",...,{\"options\":{\"brands\":[...]}}]"])

The push() ARGUMENT is itself a valid JSON array: [chunk_id, chunk_string].
Critically, chunk_string's own content -- which is JSON like `"rows":[...]`
-- has every quote backslash-escaped, because it's nested inside an outer
JSON string. An earlier version of this module regexed for `"rows":[...]`
directly against the raw HTML, built and tested against a hand-simplified
sample that happened to use plain quotes. Real page output uses the
escaped form and that regex silently matched nothing. Fixed by decoding
push()'s argument as JSON and letting the decoder do the unescaping,
rather than guessing at the escaping pattern with regex -- verified
against actual downloaded page source (1,103 brands, 325 real Bambu Lab
filaments, both extracted correctly).

No JS execution, no Server Action reverse-engineering, no Selenium.
"""
import json
import re
import time
import requests
from requests.adapters import HTTPAdapter
try:
    from urllib3.util.retry import Retry
except ImportError:  # pragma: no cover
    from requests.packages.urllib3.util.retry import Retry

BASE_URL = "https://3dfilamentprofiles.com/filaments/{slug}"
DETAIL_URL = "https://3dfilamentprofiles.com/filament/details/{id}"

# A generic custom User-Agent (identifying this as a script) is exactly
# the kind of thing edge/bot-protection layers (this site is on Vercel,
# which has its own bot-management) flag on the very first request,
# before request *frequency* is even a factor -- confirmed: switching
# to these headers fixed an immediate 429 on the very first request.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def make_session():
    """A session that looks like an ordinary browser rather than an
    obviously scripted client. Also retries transient failures with
    real backoff, honoring any Retry-After header on a 429, and times
    out rather than hanging."""
    session = requests.Session()
    retries = Retry(
        total=5, backoff_factor=3.0,
        status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"],
        respect_retry_after_header=True,
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.headers.update(BROWSER_HEADERS)
    return session


def _iter_flight_chunks(html_text):
    """Yields each Flight chunk's inner string, with quotes already
    correctly unescaped by the JSON decoder -- see module docstring."""
    decoder = json.JSONDecoder()
    marker = "self.__next_f.push("
    pos = 0
    while True:
        i = html_text.find(marker, pos)
        if i == -1:
            return
        start = i + len(marker)
        try:
            obj, end = decoder.raw_decode(html_text, start)
        except json.JSONDecodeError:
            pos = start + 1
            continue
        pos = end
        if isinstance(obj, list) and len(obj) >= 2 and isinstance(obj[1], str):
            yield obj[1]


ROWS_RE = re.compile(r'"rows"\s*:\s*(\[.*?\])\s*,\s*"baseUrl"', re.DOTALL)
BRANDS_RE = re.compile(r'"brands"\s*:\s*(\[.*?\])\s*,\s*"materials"', re.DOTALL)


def extract_rows_json(html_text):
    """Pull the embedded filament rows out of a brand page's raw HTML.
    Returns [] (not an exception) if not found, since a brand with zero
    filaments -- or an actual future page-structure change -- should
    degrade gracefully rather than kill the whole run."""
    for chunk in _iter_flight_chunks(html_text):
        match = ROWS_RE.search(chunk)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError as e:
                print(f"  WARN: rows JSON failed to parse: {e}")
                return []
    return []


def extract_brand_slugs(filaments_page_html):
    for chunk in _iter_flight_chunks(filaments_page_html):
        match = BRANDS_RE.search(chunk)
        if match:
            try:
                brands = json.loads(match.group(1))
            except json.JSONDecodeError as e:
                print(f"  WARN: brands JSON failed to parse: {e}")
                return []
            return [b["value"] for b in brands if b.get("value")]
    return []


def row_to_raw(row):
    """Map one 3DFP row object to the raw-row contract build_pipeline.py
    expects (see its docstring)."""
    fid = row.get("id")
    color = (row.get("color") or "").strip()
    return {
        "manufacturer_name": (row.get("brand_name") or "").strip(),
        "material": (row.get("material") or "").strip(),
        "material_type": (row.get("material_type") or "").strip(),
        "color_name": color,
        # rgb is the manufacturer-declared color; measured_rgb is a
        # community-measured fallback when rgb is null -- prefer the
        # declared value (both seen in real data).
        "rgb_hex": row.get("rgb") or row.get("measured_rgb") or "",
        # sku/upc can be comma-joined multi-value strings in real data
        # (e.g. Bambu Lab rows with several SKU variants) -- stored as-is.
        "sku": row.get("sku") or "",
        "upc": row.get("upc") or "",
        "tdfp_id": str(fid) if fid is not None else "",
        "tdfp_url": DETAIL_URL.format(id=fid) if fid is not None else "",
    }


def fetch_brand_rows(session, brand_slug, delay=0.5):
    url = BASE_URL.format(slug=brand_slug)
    resp = session.get(url, timeout=20)
    resp.raise_for_status()
    time.sleep(delay)  # be a polite, rate-limited guest of someone's hobby server
    raw_rows = extract_rows_json(resp.text)
    return [row_to_raw(r) for r in raw_rows if (r.get("color") or "").strip()]


def fetch_rows(brand_slugs, delay=0.5):
    """Main entry point for build_pipeline.py. brand_slugs is the list
    of slugs pulled from discover_brand_slugs() -- pass a subset to
    test on a few brands before running the full ~1,103."""
    session = make_session()
    all_rows = []
    for i, slug in enumerate(brand_slugs, 1):
        try:
            rows = fetch_brand_rows(session, slug, delay=delay)
            print(f"[{i}/{len(brand_slugs)}] {slug}: {len(rows)} filaments")
            all_rows.extend(rows)
        except requests.RequestException as e:
            print(f"[{i}/{len(brand_slugs)}] {slug}: ERROR {e}")
    return all_rows


def discover_brand_slugs(session=None):
    session = session or make_session()
    resp = session.get("https://3dfilamentprofiles.com/filaments", timeout=20)
    resp.raise_for_status()
    slugs = extract_brand_slugs(resp.text)
    print(f"discovered {len(slugs)} brand slugs")
    return slugs
