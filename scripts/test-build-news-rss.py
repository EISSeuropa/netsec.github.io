#!/usr/bin/env python3
"""Comprehensive pytest suite for scripts/build-news-rss.py.

The module is loaded via importlib from its hyphenated path (hyphens
block import-by-name). All IO is routed through tmp_path by
monkeypatching the module-level NEWS / RSS path globals; no network,
no mutation of tracked files.

Covered logic:
  * to_rfc822      ISO-8601-with-offset -> RFC 822 conversion
  * cdata          CDATA wrapping incl. the "]]>" split edge case
  * item_link      per-item URL: dict href, string-path href, absolute
                   href, missing/empty cta fallback
  * render         channel block, XML escaping, pubDate-desc ordering,
                   CDATA bodies, GUID emission, trailing newline
  * main           --check (in-sync / drift / missing-file) and the
                   write path

Run: python3 -m pytest scripts/test-build-news-rss.py -q
"""
from __future__ import annotations

import importlib.util
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

_MOD_PATH = Path(__file__).resolve().parent / "build-news-rss.py"
_spec = importlib.util.spec_from_file_location("build_news_rss", _MOD_PATH)
brss = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(brss)


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------
def _item(iid, pub, title="T", body="B", cta=None):
    it = {
        "id": iid,
        "pubDate": pub,
        "title": {"en": title, "fr": "FR", "de": "DE"},
        "body": {"en": body, "fr": "FRb", "de": "DEb"},
    }
    if cta is not None:
        it["cta"] = cta
    return it


def _data(items):
    return {
        "channelTitle": "NetSec — Latest news",
        "channelDescription": "Announcements & milestones.",
        "channelLink": "https://netsec-cost.eu/#news",
        "channelLanguage": "en-GB",
        "lastBuildDate": "2026-05-28T12:00:00+02:00",
        "items": items,
    }


@pytest.fixture
def sample_data():
    return _data(
        [
            _item(
                "older",
                "2026-05-15T09:00:00+02:00",
                title="Older item",
                body="Body of older.",
                cta={"href": {"en": "grants.html"}},
            ),
            _item(
                "newer",
                "2026-05-20T09:00:00+02:00",
                title="Newer item",
                body="Body of newer.",
                cta={"href": "https://eiss-europa.com/x.html"},
            ),
        ]
    )


# --------------------------------------------------------------------------
# to_rfc822
# --------------------------------------------------------------------------
def test_to_rfc822_preserves_offset():
    out = brss.to_rfc822("2026-05-15T09:00:00+02:00")
    # RFC 822 format ends with the numeric offset.
    assert out == "Fri, 15 May 2026 09:00:00 +0200"


def test_to_rfc822_matches_stdlib_format():
    iso = "2026-01-02T03:04:05+00:00"
    dt = datetime.fromisoformat(iso)
    from email.utils import format_datetime

    assert brss.to_rfc822(iso) == format_datetime(dt)


def test_to_rfc822_utc():
    out = brss.to_rfc822("2026-12-25T00:00:00+00:00")
    assert out.startswith("Fri, 25 Dec 2026 00:00:00")
    assert out.endswith("+0000")


def test_to_rfc822_invalid_raises():
    with pytest.raises(ValueError):
        brss.to_rfc822("not-a-date")


# --------------------------------------------------------------------------
# cdata
# --------------------------------------------------------------------------
def test_cdata_wraps_plain_text():
    assert brss.cdata("hello") == "<![CDATA[hello]]>"


def test_cdata_keeps_html_literal():
    out = brss.cdata("<b>bold</b> & <a href='x'>l</a>")
    assert out == "<![CDATA[<b>bold</b> & <a href='x'>l</a>]]>"


def test_cdata_splits_terminator_sequence():
    # The literal "]]>" must be split so it can't close the CDATA early.
    out = brss.cdata("danger ]]> here")
    assert "]]]]><![CDATA[>" in out
    assert out == "<![CDATA[danger ]]]]><![CDATA[> here]]>"
    # No raw "]]>" survives except the final closer.
    assert out.count("]]>") == out.rstrip().count("]]>")
    # Stripping the outer wrapper leaves no premature terminator.
    inner = out[len("<![CDATA[") : -len("]]>")]
    assert "]]>" not in inner.replace("<![CDATA[", "").replace("]]]]>", "")


def test_cdata_multiple_terminators():
    out = brss.cdata("a]]>b]]>c")
    assert out.count("<![CDATA[") == 3  # 1 opener + 2 re-openers


# --------------------------------------------------------------------------
# item_link
# --------------------------------------------------------------------------
def test_item_link_dict_relative_href():
    link = brss.item_link({"cta": {"href": {"en": "grants.html"}}})
    assert link == "https://netsec-cost.eu/grants.html"


def test_item_link_dict_strips_leading_slash():
    link = brss.item_link({"cta": {"href": {"en": "/grants.html"}}})
    assert link == "https://netsec-cost.eu/grants.html"


def test_item_link_dict_with_anchor():
    link = brss.item_link({"cta": {"href": {"en": "about.html#leadership"}}})
    assert link == "https://netsec-cost.eu/about.html#leadership"


def test_item_link_string_absolute_href_passthrough():
    link = brss.item_link({"cta": {"href": "https://eiss-europa.com/x.html"}})
    assert link == "https://eiss-europa.com/x.html"


def test_item_link_string_http_passthrough():
    link = brss.item_link({"cta": {"href": "http://example.org/p"}})
    assert link == "http://example.org/p"


def test_item_link_string_relative_href():
    link = brss.item_link({"cta": {"href": "grants.html"}})
    assert link == "https://netsec-cost.eu/grants.html"


def test_item_link_no_cta_falls_back():
    assert brss.item_link({}) == "https://netsec-cost.eu/#news"


def test_item_link_null_cta_falls_back():
    assert brss.item_link({"cta": None}) == "https://netsec-cost.eu/#news"


def test_item_link_empty_href_falls_back():
    assert brss.item_link({"cta": {"href": ""}}) == "https://netsec-cost.eu/#news"


def test_item_link_dict_missing_en_falls_back():
    # href dict without "en" -> "" -> fallback anchor.
    link = brss.item_link({"cta": {"href": {"fr": "grants.fr.html"}}})
    assert link == "https://netsec-cost.eu/#news"


# --------------------------------------------------------------------------
# render
# --------------------------------------------------------------------------
def test_render_has_xml_prolog_and_rss_root(sample_data):
    out = brss.render(sample_data)
    assert out.startswith('<?xml version="1.0" encoding="UTF-8"?>\n')
    assert '<rss version="2.0"' in out
    assert out.endswith("\n")


def test_render_channel_metadata(sample_data):
    out = brss.render(sample_data)
    assert "<title>NetSec — Latest news</title>" in out
    assert "<link>https://netsec-cost.eu/#news</link>" in out
    assert "<description>Announcements &amp; milestones.</description>" in out
    assert "<language>en-GB</language>" in out
    assert "<lastBuildDate>Thu, 28 May 2026 12:00:00 +0200</lastBuildDate>" in out
    assert "<generator>scripts/build-news-rss.py</generator>" in out


def test_render_atom_self_link(sample_data):
    out = brss.render(sample_data)
    assert (
        '<atom:link href="https://netsec-cost.eu/news.xml" rel="self"'
        ' type="application/rss+xml"/>'
    ) in out


def test_render_default_language_when_absent():
    data = _data([_item("a", "2026-05-15T09:00:00+02:00")])
    del data["channelLanguage"]
    out = brss.render(data)
    assert "<language>en-GB</language>" in out


def test_render_orders_items_newest_first(sample_data):
    out = brss.render(sample_data)
    # "newer" pubDate is later, so it must appear before "older".
    assert out.index("Newer item") < out.index("Older item")
    assert out.index("guid isPermaLink=\"false\">newer") < out.index(
        "guid isPermaLink=\"false\">older"
    )


def test_render_item_count(sample_data):
    out = brss.render(sample_data)
    assert out.count("<item>") == 2
    assert out.count("</item>") == 2


def test_render_body_in_cdata(sample_data):
    out = brss.render(sample_data)
    assert "<description><![CDATA[Body of newer.]]></description>" in out


def test_render_escapes_title_special_chars():
    data = _data(
        [_item("a", "2026-05-15T09:00:00+02:00", title="A & B < C > D")]
    )
    out = brss.render(data)
    assert "<title>A &amp; B &lt; C &gt; D</title>" in out


def test_render_guid_is_item_id():
    data = _data([_item("my-id-123", "2026-05-15T09:00:00+02:00")])
    out = brss.render(data)
    assert '<guid isPermaLink="false">my-id-123</guid>' in out


def test_render_item_pubdate_rfc822():
    data = _data([_item("a", "2026-05-15T09:00:00+02:00")])
    out = brss.render(data)
    assert "<pubDate>Fri, 15 May 2026 09:00:00 +0200</pubDate>" in out


def test_render_item_link_from_cta(sample_data):
    out = brss.render(sample_data)
    assert "<link>https://netsec-cost.eu/grants.html</link>" in out
    assert "<link>https://eiss-europa.com/x.html</link>" in out


def test_render_empty_items():
    data = _data([])
    out = brss.render(data)
    assert "<item>" not in out
    assert "<channel>" in out and "</channel>" in out


def test_render_is_well_formed_xml(sample_data):
    import xml.dom.minidom as minidom

    out = brss.render(sample_data)
    # Parses without raising -> structurally valid XML.
    doc = minidom.parseString(out)
    items = doc.getElementsByTagName("item")
    assert len(items) == 2
    titles = doc.getElementsByTagName("title")
    # 1 channel title + 2 item titles.
    assert len(titles) == 3


def test_render_missing_required_channel_key_raises():
    data = _data([])
    del data["channelTitle"]
    with pytest.raises(KeyError):
        brss.render(data)


# --------------------------------------------------------------------------
# main: --check and write paths (globals monkeypatched to tmp_path)
# --------------------------------------------------------------------------
def _wire_tmp(monkeypatch, tmp_path, data):
    news = tmp_path / "news.json"
    rss = tmp_path / "news.xml"
    news.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(brss, "NEWS", news)
    monkeypatch.setattr(brss, "RSS", rss)
    monkeypatch.setattr(brss, "ROOT", tmp_path)
    return news, rss


def test_main_write_creates_file(monkeypatch, tmp_path, sample_data):
    news, rss = _wire_tmp(monkeypatch, tmp_path, sample_data)
    monkeypatch.setattr("sys.argv", ["build-news-rss.py"])
    rc = brss.main()
    assert rc == 0
    assert rss.exists()
    assert rss.read_text(encoding="utf-8") == brss.render(sample_data)


def test_main_check_passes_when_in_sync(monkeypatch, tmp_path, sample_data, capsys):
    news, rss = _wire_tmp(monkeypatch, tmp_path, sample_data)
    rss.write_text(brss.render(sample_data), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["build-news-rss.py", "--check"])
    rc = brss.main()
    assert rc == 0
    assert "matches" in capsys.readouterr().out


def test_main_check_fails_on_drift(monkeypatch, tmp_path, sample_data, capsys):
    news, rss = _wire_tmp(monkeypatch, tmp_path, sample_data)
    rss.write_text("stale content", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["build-news-rss.py", "--check"])
    rc = brss.main()
    assert rc == 1
    assert "out of sync" in capsys.readouterr().err


def test_main_check_fails_when_file_missing(monkeypatch, tmp_path, sample_data):
    news, rss = _wire_tmp(monkeypatch, tmp_path, sample_data)
    assert not rss.exists()
    monkeypatch.setattr("sys.argv", ["build-news-rss.py", "--check"])
    rc = brss.main()
    assert rc == 1


def test_main_write_then_check_roundtrip(monkeypatch, tmp_path, sample_data):
    news, rss = _wire_tmp(monkeypatch, tmp_path, sample_data)
    monkeypatch.setattr("sys.argv", ["build-news-rss.py"])
    assert brss.main() == 0
    # A subsequent --check against the just-written file must pass.
    monkeypatch.setattr("sys.argv", ["build-news-rss.py", "--check"])
    assert brss.main() == 0


def test_main_does_not_touch_tracked_news_json():
    # Sanity: the real module globals point at the repo, not tmp.
    # The tests only ever rebind via monkeypatch, so the tracked
    # data/news.json is never written. RSS write path is gated on
    # --check absence and writes RSS, never NEWS.
    src = _MOD_PATH.read_text(encoding="utf-8")
    assert "NEWS.write_text" not in src


# --------------------------------------------------------------------------
# Real-fixture smoke: render the actual data/news.json (read-only).
# --------------------------------------------------------------------------
def test_real_news_json_renders_and_is_wellformed():
    repo_news = _MOD_PATH.resolve().parent.parent / "data" / "news.json"
    if not repo_news.exists():
        pytest.skip("data/news.json not present in this checkout")
    import xml.dom.minidom as minidom

    data = json.loads(repo_news.read_text(encoding="utf-8"))
    out = brss.render(data)
    minidom.parseString(out)  # must not raise
    # Items are sorted newest-first; verify monotonic non-increasing.
    pubs = re.findall(r"<pubDate>(.*?)</pubDate>", out)
    parsed = [datetime.strptime(p, "%a, %d %b %Y %H:%M:%S %z") for p in pubs[1:]]
    assert parsed == sorted(parsed, reverse=True)