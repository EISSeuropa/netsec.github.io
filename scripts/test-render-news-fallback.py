"""Tests for render-news-fallback.py.

Covers the selection rule it shares with home-news.js (newest first,
`homeUntil` expiry, the cap of three) and that the rewrite replaces only the
news-list block.
"""

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "render_news_fallback", REPO / "scripts" / "render-news-fallback.py"
)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

NOW = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)


def _item(i, pub, **over):
    d = {"id": i, "pubDate": pub, "title": {"en": i.upper(), "fr": "FR " + i}, "body": {"en": "b & c"}}
    d.update(over)
    return d


def test_select_drops_expired_and_caps():
    items = [
        _item("old", "2026-06-01T09:00:00+02:00"),
        _item("call", "2026-07-24T09:00:00+02:00", homeUntil="2026-09-13T18:00:00+03:00"),
        _item("a", "2026-09-13T18:00:00+03:00"),
        _item("b", "2026-09-11T11:00:00+02:00"),
        _item("ancient", "2024-01-01T09:00:00+01:00"),
    ]
    assert [it["id"] for it in mod.select(items, NOW)] == ["a", "b", "old"]


def test_render_replaces_only_the_list():
    page = ('<p>before</p>\n    <div class="news-list reveal">\n      <article>stale</article>'
            '\n    </div>\n<p>after</p>')
    item = _item("a", "2026-09-13T18:00:00+03:00",
                 cta={"href": "x.html", "i18n": {"en": "More", "fr": "Plus"}})
    out = mod.render(page, [item], "fr")
    assert "stale" not in out and "<p>before</p>" in out and "<p>after</p>" in out
    assert "<h3>FR a</h3>" in out and "<p>b &amp; c</p>" in out
    assert 'class="news-card glass card-clickable"' in out and ">Plus</a>" in out


def test_real_pages_have_the_block():
    for path in mod.PAGES.values():
        assert mod.LIST.search(path.read_text(encoding="utf-8")), path.name
