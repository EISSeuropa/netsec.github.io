#!/usr/bin/env python3
"""
One-shot HTML sweep that swaps placeholder brand references for the
new logo across every locale and page.

Three targeted replacements per file:

  1. Favicon link chain — replace the single `favicon.svg` link with
     the full per-size PNG chain + Apple touch + manifest reference.
  2. Header brand element — replace the `<span class="brand-mark">NS</span>`
     placeholder + hidden `<span>NetSec</span>` text with a `<picture>`
     element that ships the full lockup PNG (with a dark-mode variant
     and a mobile mark-only variant).
  3. JSON-LD `Organization.logo` URL — point at the new mark file.

Idempotent: re-running over already-updated HTML is a no-op (the
replacements look for the placeholder strings, which won't exist
after the first pass).

Usage:
    python3 scripts/update-brand-html.py        # dry-run, lists files + diffs
    python3 scripts/update-brand-html.py --apply

Tracked in #220.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ── Replacement 1: favicon chain ──
# Old: a single line referencing the placeholder SVG (+ optional PNG
# fallback). We keep `<link rel="canonical">` and other meta untouched.
OLD_FAVICON_BLOCK = (
    '<link rel="icon" href="assets/images/favicon.svg" type="image/svg+xml">\n'
    '<link rel="alternate icon" href="assets/images/logo.png" type="image/png">'
)
NEW_FAVICON_BLOCK = (
    '<link rel="icon" type="image/png" sizes="32x32" href="assets/images/brand/favicon-32.png">\n'
    '<link rel="icon" type="image/png" sizes="16x16" href="assets/images/brand/favicon-16.png">\n'
    '<link rel="apple-touch-icon" sizes="180x180" href="assets/images/brand/apple-touch-icon.png">\n'
    '<link rel="manifest" href="manifest.webmanifest">\n'
    '<link rel="shortcut icon" href="assets/images/brand/favicon.ico">'
)

# Fallback: if only the SVG line exists (no PNG alternate), accept that too.
OLD_FAVICON_BLOCK_FALLBACK = (
    '<link rel="icon" href="assets/images/favicon.svg" type="image/svg+xml">'
)

# ── Replacement 2: header brand element ──
# The site keys dark mode off `<html class="dark">` (its own theme
# toggle), NOT off `prefers-color-scheme: dark` (OS). So `<picture
# media="prefers-color-scheme: dark">` would desync — the logo would
# follow the OS while the rest of the page follows the user's site
# choice. We ship two <img>s instead and let CSS toggle visibility
# via the `.dark` class. Slightly more bytes per page (both images
# in the DOM, browser fetches both — though they're small) but the
# visual stays consistent with the rest of the theme.
OLD_BRAND = (
    '      <span class="brand-mark">NS</span>\n'
    '      <span>NetSec</span>'
)
# Second pass: the picture-element form we shipped in the first
# sweep is now replaced with the dual-<img> form. The OLD here is
# the previous NEW.
OLD_BRAND_V1 = (
    '      <picture class="brand-logo">\n'
    '        <source srcset="assets/images/brand/netsec-lockup-white.png" media="(prefers-color-scheme: dark)">\n'
    '        <img src="assets/images/brand/netsec-lockup-primary.png" alt="" width="120" height="38" decoding="async">\n'
    '      </picture>\n'
    '      <picture class="brand-mark-only" aria-hidden="true">\n'
    '        <img src="assets/images/brand/netsec-mark.png" alt="" width="32" height="32" decoding="async">\n'
    '      </picture>'
)
NEW_BRAND = (
    '      <img class="brand-logo brand-logo--light" src="assets/images/brand/netsec-lockup-primary.png" alt="" width="120" height="38" decoding="async">\n'
    '      <img class="brand-logo brand-logo--dark" src="assets/images/brand/netsec-lockup-white.png" alt="" width="120" height="38" decoding="async">\n'
    '      <img class="brand-mark-only" src="assets/images/brand/netsec-mark.png" alt="" width="32" height="32" decoding="async" aria-hidden="true">'
)

# ── Replacement 3: JSON-LD logo URL ──
# Historical: this one-shot v1.8.0 migration is complete and the OLD
# placeholder files (favicon.svg, logo.png) have since been removed from
# the repo. The OLD_* strings below are retained only as the record of
# what was migrated; inject-seo.py now owns the JSON-LD logo and reads it
# from data/brand.json.
OLD_LOGO_URL = '"logo": "https://netsec-cost.eu/assets/images/logo.png"'
NEW_LOGO_URL = '"logo": "https://netsec-cost.eu/assets/images/brand/android-chrome-512.png"'


# ──────────────────────────── runner ────────────────────────────

def patch_file(path: Path, *, apply: bool) -> tuple[bool, list[str]]:
    """Apply the three replacements to a file. Returns (changed, log)."""
    text = path.read_text(encoding="utf-8")
    log: list[str] = []
    changed = False

    # 1. Favicon
    if OLD_FAVICON_BLOCK in text:
        text = text.replace(OLD_FAVICON_BLOCK, NEW_FAVICON_BLOCK)
        log.append("favicon chain replaced (with alternate)")
        changed = True
    elif OLD_FAVICON_BLOCK_FALLBACK in text:
        text = text.replace(OLD_FAVICON_BLOCK_FALLBACK, NEW_FAVICON_BLOCK)
        log.append("favicon chain replaced (svg-only)")
        changed = True

    # 2. Brand element
    if OLD_BRAND in text:
        text = text.replace(OLD_BRAND, NEW_BRAND)
        log.append("brand element replaced (from NS placeholder)")
        changed = True
    elif OLD_BRAND_V1 in text:
        # First-pass already ran; swap the picture-element form for
        # the dual-<img> form so dark-mode follows the site theme.
        text = text.replace(OLD_BRAND_V1, NEW_BRAND)
        log.append("brand element migrated (picture → dual-img)")
        changed = True

    # 3. JSON-LD logo
    if OLD_LOGO_URL in text:
        text = text.replace(OLD_LOGO_URL, NEW_LOGO_URL)
        log.append("Organization.logo updated")
        changed = True

    if changed and apply:
        path.write_text(text, encoding="utf-8")
    return changed, log


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--apply", action="store_true",
                   help="Actually rewrite the files. Default is dry-run.")
    args = p.parse_args()

    targets = sorted(ROOT.glob("*.html"))
    print(f"{'Apply' if args.apply else 'Dry-run'}: {len(targets)} HTML files")

    changed_files = 0
    no_change_files = 0
    for path in targets:
        changed, log = patch_file(path, apply=args.apply)
        if changed:
            print(f"  {path.name}:")
            for entry in log:
                print(f"    - {entry}")
            changed_files += 1
        else:
            no_change_files += 1

    print(f"\n{changed_files} file(s) {'updated' if args.apply else 'would change'}, "
          f"{no_change_files} unchanged.")
    if not args.apply:
        print("Run with --apply to write changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
