#!/usr/bin/env python3
"""Test suite for scripts/build-og-cards.py (browser-free).

Loaded via importlib from its hyphenated path. Covers the pure logic and
the committed-state invariants without rendering (no Chrome needed):
  * card_hash is deterministic and input-sensitive
  * card_markup escapes member text and includes the bundled flag
  * a flag SVG exists for every country_code used in bios.json
  * --check passes against the committed cards + manifest

Run standalone:  /usr/bin/python3 scripts/test-build-og-cards.py
Or under pytest: python3 -m pytest scripts/test-build-og-cards.py -q
"""
from __future__ import annotations

import importlib.util
import json
import types
from pathlib import Path

_MOD_PATH = Path(__file__).resolve().parent / "build-og-cards.py"
_spec = importlib.util.spec_from_file_location("build_og_cards", _MOD_PATH)
boc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(boc)


def test_card_hash_deterministic_and_sensitive():
    a = {"name": "Dr Ada Lovelace", "position": "Prof", "affiliation": "X Uni",
         "country": "United Kingdom", "country_code": "gb"}
    assert boc.card_hash(a) == boc.card_hash(dict(a))
    b = dict(a, affiliation="Y Uni")
    assert boc.card_hash(a) != boc.card_hash(b)


def test_card_markup_escapes_and_includes_flag():
    inp = {"name": "Dr <Ada> & Co", "position": "Prof", "affiliation": "X & Y",
           "country": "Netherlands", "country_code": "nl"}
    html = boc.card_markup(inp)
    assert "&lt;Ada&gt;" in html and "&amp;" in html  # escaped, not raw
    assert "<Ada>" not in html
    assert "/assets/og/flags/nl.svg" in html
    assert "Netherlands" in html


def test_card_markup_omits_flag_when_missing():
    inp = {"name": "X", "position": "", "affiliation": "", "country": "Nowhere", "country_code": "zz"}
    html = boc.card_markup(inp)
    assert "flags/zz.svg" not in html  # no bundled flag for zz -> omitted


def test_every_country_code_has_a_bundled_flag():
    for m in boc.members():
        cc = (m.get("country_code") or "").strip().lower()
        if cc:
            assert (boc.FLAGS_DIR / f"{cc}.svg").exists(), f"missing bundled flag for {cc}"


def test_check_passes_against_committed_cards():
    assert boc.check() == 0


def _standalone() -> int:
    failures = []
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and isinstance(f, types.FunctionType)]
    for name, fn in tests:
        try:
            fn()
            print(f"  ok  {name}")
        except Exception as exc:  # noqa: BLE001
            failures.append((name, exc))
            print(f"FAIL  {name}: {exc}")
    print(f"\n{len(tests) - len(failures)}/{len(tests)} passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    import sys

    sys.exit(_standalone())
