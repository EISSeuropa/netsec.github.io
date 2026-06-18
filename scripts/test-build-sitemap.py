#!/usr/bin/env python3
"""Test suite for scripts/build-sitemap.py.

Loaded via importlib from its hyphenated path. Validates the rendered
sitemap without touching the committed file:
  * the output is well-formed XML
  * XML comments contain no '--' (illegal, and an easy regression)
  * every top-level page and every member profile page appears once
  * each <url> carries the four hreflang alternates (en/fr/de/x-default)
  * --check is consistent with the committed sitemap.xml

Run standalone:  /usr/bin/python3 scripts/test-build-sitemap.py
Or under pytest: python3 -m pytest scripts/test-build-sitemap.py -q
"""
from __future__ import annotations

import importlib.util
import re
import types
import xml.dom.minidom
from pathlib import Path

_MOD_PATH = Path(__file__).resolve().parent / "build-sitemap.py"
_spec = importlib.util.spec_from_file_location("build_sitemap", _MOD_PATH)
bsm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bsm)


def test_output_is_well_formed_xml():
    xml.dom.minidom.parseString(bsm.render())


def test_no_double_hyphen_in_comments():
    # XML comments may not contain '--'; the literal "--check" once slipped
    # into the header and broke parsing. Guard it.
    for c in re.findall(r"<!--(.*?)-->", bsm.render(), re.S):
        assert "--" not in c, "double hyphen inside an XML comment"


def test_top_level_and_members_present():
    out = bsm.render()
    for base, *_ in bsm.TOP_LEVEL:
        loc = f"{bsm.SITE}/" if base == "index" else f"{bsm.SITE}/{base}.html"
        assert f"<loc>{loc}</loc>" in out, f"missing top-level {loc}"
    slugs = bsm.member_slugs()
    assert slugs, "expected at least one member profile page"
    for slug in slugs:
        assert f"<loc>{bsm.SITE}/people/{slug}.html</loc>" in out, f"missing member {slug}"


def test_every_url_has_four_hreflang_alternates():
    out = bsm.render()
    blocks = re.findall(r"<url>(.*?)</url>", out, re.S)
    assert len(blocks) == len(bsm.TOP_LEVEL) + len(bsm.member_slugs())
    for b in blocks:
        for lang in ("en", "fr", "de", "x-default"):
            assert f'hreflang="{lang}"' in b, f"url block missing hreflang={lang}"


def test_check_matches_committed_file():
    # The committed sitemap.xml must equal the generator's output.
    committed = bsm.OUT.read_text(encoding="utf-8")
    assert committed == bsm.render(), "run: python3 scripts/build-sitemap.py"


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
