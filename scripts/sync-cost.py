#!/usr/bin/env python3
"""
Sync helper: refresh the WG_MAP embedded in index.html from
https://www.cost.eu/actions/CA24154/

Usage:
    python3 scripts/sync-cost.py

What it does:
  1. Fetches the COST Action page.
  2. Parses the Membership table to build a {name: [WGs]} map.
  3. Re-writes the WG_MAP literal inside index.html in-place.
  4. Prints a diff summary (added / removed / changed members).

Run from the repo root. Requires: requests, beautifulsoup4.
"""
import json, re, sys, unicodedata, difflib
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("Install deps: pip install requests beautifulsoup4")

URL = "https://www.cost.eu/actions/CA24154/"
INDEX = Path(__file__).resolve().parent.parent / "index.html"

def norm(name: str) -> str:
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"^(Dr|Prof|Mr|Ms|Mrs)\.?\s+", "", s)
    return re.sub(r"\s+", " ", s).strip().lower()

def fetch_map() -> dict:
    r = requests.get(URL, headers={"User-Agent": "netsec-sync/1.0"}, timeout=30)
    r.raise_for_status()
    bs = BeautifulSoup(r.text, "html.parser")
    out: dict[str, list[int]] = {}
    for tr in bs.find_all("tr"):
        cells = [" ".join(c.stripped_strings) for c in tr.find_all(["td", "th"])]
        if len(cells) >= 3 and re.search(r"WG\s*\d", cells[1] or ""):
            k = norm(cells[0])
            if not k or k.isdigit() or k == "name":
                continue
            out[k] = sorted({int(d) for d in re.findall(r"WG\s*(\d)", cells[1])})
    return dict(sorted(out.items()))

def rewrite(new_map: dict) -> tuple[dict, dict]:
    html = INDEX.read_text(encoding="utf-8")
    m = re.search(r"const WG_MAP = (\{.*?\});", html, re.S)
    if not m:
        raise SystemExit("Could not find WG_MAP literal in index.html")
    old_map = json.loads(m.group(1))
    new_json = json.dumps(new_map, ensure_ascii=False)
    new_html = html[:m.start()] + f"const WG_MAP = {new_json};" + html[m.end():]
    INDEX.write_text(new_html, encoding="utf-8")
    return old_map, new_map

def report(old: dict, new: dict) -> None:
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = sorted(k for k in (set(old) & set(new)) if old[k] != new[k])
    print(f"Members: {len(new)} (was {len(old)})")
    if added:   print("Added:");   [print(f"  + {k}: WG {new[k]}") for k in added]
    if removed: print("Removed:"); [print(f"  - {k}: WG {old[k]}") for k in removed]
    if changed: print("Changed:"); [print(f"  ~ {k}: {old[k]} -> {new[k]}") for k in changed]
    if not (added or removed or changed):
        print("No changes.")

if __name__ == "__main__":
    new_map = fetch_map()
    old_map, _ = rewrite(new_map)
    report(old_map, new_map)
