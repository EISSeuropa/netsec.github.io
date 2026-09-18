#!/usr/bin/env python3
"""
Fail if a top-level page is missing from inject-seo's PAGES or from
build-sitemap's TOP_LEVEL.

Both lists are hand-kept, and a page added to the tree but left out of
either one passes every other check: inject-seo --check only looks at the
pages it manages, and build-sitemap --check only at the pages it lists.
That is how slides and essc-2027 went unmanaged (#1850).

Usage:
    python3 scripts/check-page-registration.py

Run from the repo root. Stdlib only. CI runs it in seo-asset-check.yml.
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Top-level pages deliberately outside both lists, with the reason.
EXEMPT = {
    "404": "single error page, not indexed; inject-seo handles it by name",
    "essc-2027": "parked with noindex until #1560 un-parks it",
}


def load(name: str):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT / "scripts"))
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    bases = {re.sub(r"\.(fr|de)$", "", p.stem) for p in ROOT.glob("*.html")}
    lists = {
        "scripts/inject-seo.py PAGES": set(load("inject-seo").PAGES),
        "scripts/build-sitemap.py TOP_LEVEL": {row[0] for row in load("build-sitemap").TOP_LEVEL},
    }
    failed = False
    for label, listed in lists.items():
        missing = sorted(bases - listed - EXEMPT.keys())
        stale = sorted(listed - bases)
        for b in missing:
            print(f"✗ {b}.html is not in {label}")
        for b in stale:
            print(f"✗ {label} lists {b}, which has no {b}.html")
        failed |= bool(missing or stale)
    if failed:
        print("Register the page, or add it to EXEMPT in this script with the reason.")
        return 1
    print(f"✓ {len(bases)} top-level pages registered ({len(EXEMPT)} exempt).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
