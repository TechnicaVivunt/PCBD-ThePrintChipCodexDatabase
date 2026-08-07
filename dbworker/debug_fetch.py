"""
One-off debug helper: fetches the live /filaments page and a live brand
page, saves the raw HTML, and prints the context immediately around the
"brands" / "rows" keys (if found at all) so we can see exactly how the
live site structures things and fix source_3dfp.py's regexes to match.

Run from the repo root:
    python dbworker/debug_fetch.py

Then share the console output back (the saved .html files are useful
too if you want to send the whole thing, but the printed snippets
should be enough).
"""
import sys
sys.path.insert(0, "dbworker")
from source_3dfp import make_session

session = make_session()

# --- /filaments page: looking for the "brands" key ---
resp = session.get("https://3dfilamentprofiles.com/filaments", timeout=20)
print(f"[/filaments] status: {resp.status_code}, length: {len(resp.text)} chars")

with open("_debug_filaments_page.html", "w", encoding="utf-8") as f:
    f.write(resp.text)
print("saved to _debug_filaments_page.html")

idx = resp.text.find('"brands"')
if idx == -1:
    print('\n"brands" key NOT found anywhere in the response.')
    print("First 500 chars of response, to see what we actually got back:")
    print(resp.text[:500])
else:
    print(f'\n"brands" key found at index {idx}. Context (300 chars before/after):\n')
    print(resp.text[max(0, idx - 300): idx + 300])

# --- a known brand page: looking for the "rows" key ---
print("\n\n" + "=" * 60)
resp2 = session.get("https://3dfilamentprofiles.com/filaments/bambu-lab", timeout=20)
print(f"[/filaments/bambu-lab] status: {resp2.status_code}, length: {len(resp2.text)} chars")

with open("_debug_brand_page.html", "w", encoding="utf-8") as f:
    f.write(resp2.text)
print("saved to _debug_brand_page.html")

idx2 = resp2.text.find('"rows"')
if idx2 == -1:
    print('\n"rows" key NOT found on the bambu-lab page either.')
    print("First 500 chars of response:")
    print(resp2.text[:500])
else:
    print(f'\n"rows" key found at index {idx2}. Context (200 before / 500 after):\n')
    print(resp2.text[max(0, idx2 - 200): idx2 + 500])
