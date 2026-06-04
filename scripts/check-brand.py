#!/usr/bin/env python3
"""
Brand-consistency lint.

data/brand.json is the single source of truth for the brand primitives.
scripts/inject-seo.py reads the theme-color and the Organization.logo
from it directly, so those can never drift. The other places a brand
value lives are static files a browser reads at runtime, which cannot
read brand.json themselves:

  * manifest.webmanifest  -> theme_color must equal brand.colours.primary
  * assets/css/site.css   -> the light :root --accent / --accent-2 tokens
                             must equal brand.colours.primary / .secondary

This script asserts those mirrors match, and that no page still emits
the pre-brand placeholder logo in its JSON-LD. It is wired into CI on
every PR that touches HTML, the stylesheet, the manifest, brand.json, or
inject-seo.py, so a hand-patch or a forgotten value is caught at PR time
instead of shipping.

Run from the repo root. Exits non-zero (and prints each problem) on drift.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRAND = json.loads((ROOT / "data" / "brand.json").read_text(encoding="utf-8"))
PRIMARY = BRAND["colours"]["primary"].lower()
SECONDARY = BRAND["colours"]["secondary"].lower()
ORG_LOGO = BRAND["assets"]["org_logo"]
LEGACY_LOGO = "assets/images/logo.png"

errors: list[str] = []


def check_manifest() -> None:
    manifest = json.loads((ROOT / "manifest.webmanifest").read_text(encoding="utf-8"))
    tc = (manifest.get("theme_color") or "").lower()
    if tc != PRIMARY:
        errors.append(
            f"manifest.webmanifest theme_color {tc!r} != brand.json colours.primary {PRIMARY!r}"
        )


def check_css_tokens() -> None:
    css = (ROOT / "assets" / "css" / "site.css").read_text(encoding="utf-8")
    # The first occurrence of each token is the light :root value; the
    # .dark override comes later in the file.
    for token, want in (("--accent", PRIMARY), ("--accent-2", SECONDARY)):
        m = re.search(re.escape(token) + r":\s*(#[0-9a-fA-F]{6})", css)
        if not m:
            errors.append(f"site.css: token {token} not found")
            continue
        got = m.group(1).lower()
        if got != want:
            errors.append(
                f"site.css {token} {got!r} != brand.json {want!r} (the :root light value must match brand.json)"
            )


def check_no_placeholder_logo() -> None:
    # No generated page should reference the pre-brand placeholder as its
    # structured-data logo. The placeholder file may still exist on disk
    # (script sentinels), but it must not appear in any page's JSON-LD.
    offenders = []
    for html in sorted(ROOT.glob("*.html")):
        text = html.read_text(encoding="utf-8")
        for m in re.finditer(r'"logo"\s*:\s*"([^"]+)"', text):
            if LEGACY_LOGO in m.group(1):
                offenders.append(html.name)
                break
    if offenders:
        errors.append(
            "JSON-LD Organization.logo still points at the pre-brand "
            f"{LEGACY_LOGO} on: {', '.join(offenders)}. Re-run scripts/inject-seo.py."
        )


def main() -> int:
    check_manifest()
    check_css_tokens()
    check_no_placeholder_logo()
    if errors:
        print("Brand-consistency check FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  ✗ {e}", file=sys.stderr)
        print(
            "\nThe single source of truth is data/brand.json. Update it and the "
            "static mirrors (manifest.webmanifest, the :root tokens in site.css) "
            "together, and re-run scripts/inject-seo.py.",
            file=sys.stderr,
        )
        return 1
    print("Brand-consistency check passed:")
    print(f"  ✓ primary {PRIMARY} consistent across brand.json, manifest, --accent")
    print(f"  ✓ secondary {SECONDARY} consistent with --accent-2")
    print(f"  ✓ Organization.logo is {ORG_LOGO}; no page emits the placeholder")
    return 0


if __name__ == "__main__":
    sys.exit(main())
