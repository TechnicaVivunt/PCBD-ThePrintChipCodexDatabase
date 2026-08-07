"""
Generic Shopify /products.json scraping engine for PCDB.

Five of PCDB's manufacturer scrapers (Polymaker, Hatchbox, VOXELPLA,
Overture, Coex3D) hit the same kind of endpoint -- a Shopify storefront's
public products.json feed -- and each reimplemented pagination, retries,
text cleaning, exclude-list handling, and CSV writing from scratch.

This module is that shared machinery. Each manufacturer only supplies:
  1. An entry in manufacturers.yaml (base_url, output path, columns, ...)
  2. A small parser function in parsers.py that turns one Shopify
     `product` dict into zero or more output rows.

Everything else -- fetching, retrying on failure, de-duping, writing the
CSV -- is handled once, here.
"""
import csv
import os
import re
import time
import requests
from requests.adapters import HTTPAdapter
try:
    from urllib3.util.retry import Retry
except ImportError:  # pragma: no cover
    from requests.packages.urllib3.util.retry import Retry

TRADEMARK_RE = re.compile(r"[™®©]")
NBSP_RE = re.compile(r"\u00A0")
PAREN_RE = re.compile(r"\s*\([^)]*\)")

USER_AGENT = (
    "PCDB-Indexer/2.0 "
    "(+https://github.com/TechnicaVivunt/PCBD-ThePrintChipCodexDatabase)"
)


def make_session():
    """A requests session with sane timeouts/retries -- none of the
    original scrapers had either, so a slow or flaky response would hang
    a GitHub Actions job or silently write a truncated CSV."""
    session = requests.Session()
    retries = Retry(
        total=4,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def clean_text(value, strip_parens=False):
    """Normalize the recurring junk seen across every manufacturer's
    product titles: non-breaking spaces, trademark symbols, mojibake."""
    if value is None:
        return ""
    s = str(value)
    s = NBSP_RE.sub(" ", s)
    s = TRADEMARK_RE.sub("", s)
    s = s.replace("Â", "")
    if strip_parens:
        s = PAREN_RE.sub("", s)
    return s.strip()


def normalize_key(*parts):
    """Case/whitespace-insensitive key for de-duping and for matching
    against the master database, so 'Jet Black ' and 'jet black' don't
    become two separate rows."""
    return tuple(re.sub(r"\s+", " ", clean_text(p)).strip().lower() for p in parts)


def _paginate(session, base_url, page_limit, delay, max_pages):
    products = []
    for page in range(1, max_pages + 1):
        resp = session.get(base_url, params={"limit": page_limit, "page": page}, timeout=20)
        resp.raise_for_status()
        batch = resp.json().get("products", [])
        if not batch:
            break
        products.extend(batch)
        print(f"  page {page}: {len(batch)} products")
        if len(batch) < page_limit:
            break
        time.sleep(delay)
    return products


def fetch_all_products(session, base_url, page_limit=250, delay=0.4, max_pages=200):
    """Paginate a Shopify products.json endpoint until it stops returning
    products (or we hit max_pages, as a safety valve against an endpoint
    that never terminates).

    base_url may be a single URL or a list of candidate URLs to try in
    order -- useful when a brand's storefront is reachable at more than
    one domain (e.g. a store's official custom domain vs. its underlying
    *.myshopify.com domain) and you're not certain in advance which one
    a given scraping environment will get a clean response from."""
    candidates = base_url if isinstance(base_url, list) else [base_url]
    last_error = None
    for i, url in enumerate(candidates):
        try:
            products = _paginate(session, url, page_limit, delay, max_pages)
            if products:
                if i > 0:
                    print(f"  (used fallback URL #{i + 1}: {url})")
                return products
            last_error = f"no products returned from {url}"
        except requests.RequestException as e:
            last_error = f"{url} -> {e}"
            print(f"  candidate URL failed: {last_error}")
    if last_error:
        print(f"  all candidate URLs exhausted; last error: {last_error}")
    return []


def load_exclude_list(path):
    exclude = set()
    if not path or not os.path.exists(path):
        return exclude
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            brand = row.get("brand_name", "")
            color = row.get("color_name", "")
            if brand and color:
                exclude.add(normalize_key(brand, color))
    return exclude


def is_excluded(brand, color, exclude_set):
    return normalize_key(brand, color) in exclude_set


def run_shopify_indexer(config, parser_fn):
    """
    config keys:
        key            short manufacturer id, e.g. "polymaker"
        base_url       Shopify products.json URL
        output_file    where to write the CSV
        fieldnames     CSV column order
        exclude_file   optional path to a brand/color exclude CSV
    parser_fn(product, exclude_set) -> list[dict] (using config['fieldnames'])
    """
    session = make_session()
    exclude_set = load_exclude_list(config.get("exclude_file"))

    print(f"[{config['key']}] fetching {config['base_url']}")
    products = fetch_all_products(session, config["base_url"])
    if not products:
        print(f"[{config['key']}] ERROR: no products fetched from any candidate URL, aborting")
        return 0

    print(f"[{config['key']}] {len(products)} products fetched, parsing...")

    rows = []
    for product in products:
        try:
            rows.extend(parser_fn(product, exclude_set))
        except Exception as e:  # a single malformed product shouldn't kill the run
            print(f"[{config['key']}] WARN failed to parse product "
                  f"{product.get('id', '?')}: {e}")

    unique = {}
    for row in rows:
        key = normalize_key(row.get("brand_name", ""), row.get("color_name", ""))
        unique.setdefault(key, row)
    unique_rows = list(unique.values())
    unique_rows.sort(key=lambda r: (r.get("brand_name", ""), r.get("color_name", "")))

    out_path = config["output_file"]
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=config["fieldnames"])
        writer.writeheader()
        writer.writerows(unique_rows)

    print(f"[{config['key']}] wrote {len(unique_rows)} unique rows -> {out_path}")
    return len(unique_rows)
