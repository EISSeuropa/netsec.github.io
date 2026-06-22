#!/usr/bin/env python3
"""Test suite for scripts/publish-news.py (pure functions, no IO mutation).

Run standalone:  /usr/bin/python3 scripts/test-publish-news.py
Or under pytest: python3 -m pytest scripts/test-publish-news.py -q
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import types
from pathlib import Path

_MOD = Path(__file__).resolve().parent / "publish-news.py"
_spec = importlib.util.spec_from_file_location("publish_news", _MOD)
pn = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pn)


def test_parse_headers_and_excerpt():
    body = "Type: Announcement\nURL: https://x.org\nDate: 2026-06-20\n\nFirst para.\n\nSecond para."
    p = pn.parse_issue("A title", body)
    assert p["type"] == "Announcement"
    assert p["url"] == "https://x.org"
    assert p["date"] == "2026-06-20"
    assert p["excerpt"] == "First para."  # only the first paragraph, collapsed


def test_parse_no_headers():
    p = pn.parse_issue("T", "Just an excerpt, no headers at all.")
    assert p["type"] == "" and p["url"] == "" and p["date"] == ""
    assert p["excerpt"] == "Just an excerpt, no headers at all."


def test_parse_headers_case_insensitive_and_collapses_whitespace():
    p = pn.parse_issue("T", "type: News\n\nLine one\nwrapped onto two.")
    assert p["type"] == "News"
    assert p["excerpt"] == "Line one wrapped onto two."


def test_build_item_shape_with_cta():
    p = pn.parse_issue("New partner", "URL: https://x.org\n\nWe welcome a partner.")
    item = pn.build_item(p, "634", dt.date(2026, 6, 20))
    assert item["id"] == "new-partner-20260620"
    assert item["pubDate"].startswith("2026-06-20T")
    assert item["_source_issue"] == 634
    assert item["title"]["en"] == "New partner"
    assert item["body"]["en"] == "We welcome a partner."
    assert item["cta"]["href"] == "https://x.org" and item["cta"]["external"] is True


def test_build_item_no_cta_and_default_date():
    p = pn.parse_issue("Milestone", "Something happened.")
    item = pn.build_item(p, "10", dt.date(2026, 1, 2))
    assert "cta" not in item
    assert item["pubDate"].startswith("2026-01-02T")
    assert item["displayDate"]["en"] == "2 January 2026"  # falls back to formatted date


def test_build_item_emits_type_and_wg_tags():
    p = pn.parse_issue("Prize", "Type: Publication\nWG: 3\nDate: 2026-06-17\n\nA paper won.")
    item = pn.build_item(p, "1", dt.date(2026, 1, 1))
    assert item["type"] == "publication"                # lowercased structured tag
    assert item["wg"] == 3                              # int, in range
    assert item["displayDate"]["en"] == "17 June 2026"  # date kept, not replaced


def test_build_item_drops_out_of_range_wg():
    p = pn.parse_issue("X", "WG: 9\n\nBody.")
    item = pn.build_item(p, "1", dt.date(2026, 1, 1))
    assert "wg" not in item


def test_display_date_formats_iso():
    assert pn.display_date("2026-06-09") == "9 June 2026"
    assert pn.display_date("not-a-date") == "not-a-date"


def test_committed_news_json_valid():
    assert pn.check() == 0


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
