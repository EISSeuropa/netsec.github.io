#!/usr/bin/env python3
"""Rewrite the home page's fallback news cards from data/news.json.

The cards in `#news .news-list` are what a reader sees when
`assets/js/home-news.js` does not run, and what Pagefind indexes. They were
hand-written and nothing refreshed them, so the fallback lagged the JSON by
months. The companion to prune-past-event-cards.py, and it runs at deploy for
the same reason: `homeUntil` makes the right set of cards a function of the
date, not only of the file.

The selection mirrors renderHomeNews in home-news.js: newest first, drop items
past their `homeUntil` or older than the decay window, keep three.

Usage:
  python3 scripts/render-news-fallback.py            # rewrite in place
  python3 scripts/render-news-fallback.py --dry-run  # report, change nothing
"""
from __future__ import annotations

import html
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEWS = ROOT / "data" / "news.json"
PAGES = {"en": ROOT / "index.html", "fr": ROOT / "index.fr.html", "de": ROOT / "index.de.html"}
HOME_MAX = 3
DECAY = timedelta(days=548)  # ponytail: ~18 months, the JS uses calendar months
LIST = re.compile(r'(<div class="news-list[^"]*">)(.*?)(\n    </div>)', re.S)


def _stamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def select(items: list[dict], now: datetime) -> list[dict]:
    def on_home(it: dict) -> bool:
        if it.get("homeUntil") and _stamp(it["homeUntil"]) < now:
            return False
        return not it.get("pubDate") or _stamp(it["pubDate"]) >= now - DECAY
    ordered = sorted(items, key=lambda it: it.get("pubDate") or "", reverse=True)
    return [it for it in ordered if on_home(it)][:HOME_MAX]


def _pick(value, locale: str) -> str:
    if isinstance(value, dict):
        return value.get(locale) or value.get("en") or ""
    return value or ""


def card(item: dict, locale: str) -> str:
    e = lambda s: html.escape(s, quote=True)
    cta = item.get("cta") or {}
    cls = "news-card glass" + (" card-clickable" if cta.get("href") else "")
    lines = [f'      <article class="{cls}" data-news-id="{e(item["id"])}" data-tilt>']
    date = _pick(item.get("displayDate"), locale)
    if date:
        lines.append(f'        <span class="news-date">{e(date)}</span>')
    lines.append(f'        <h3>{e(_pick(item.get("title"), locale))}</h3>')
    lines.append(f'        <p>{e(_pick(item.get("body"), locale))}</p>')
    if cta.get("href"):
        ext = ' target="_blank" rel="noopener"' if cta.get("external") else ""
        lines.append(f'        <a class="card-stretch" href="{e(_pick(cta["href"], locale))}"{ext}>'
                     f'{e(_pick(cta.get("i18n"), locale))}</a>')
    lines.append("      </article>")
    return "\n".join(lines)


def render(page: str, items: list[dict], locale: str) -> str:
    body = "\n" + "\n".join(card(it, locale) for it in items)
    return LIST.sub(lambda m: m.group(1) + body + m.group(3), page, count=1)


def main(argv: list[str]) -> int:
    items = select(json.loads(NEWS.read_text(encoding="utf-8"))["items"],
                   datetime.now(timezone.utc))
    for locale, path in PAGES.items():
        page = path.read_text(encoding="utf-8")
        if not LIST.search(page):
            print(f"✗ no news-list block in {path.name}")
            return 1
        new = render(page, items, locale)
        if new != page and "--dry-run" not in argv:
            path.write_text(new, encoding="utf-8")
        print(f"  {path.name}: {'unchanged' if new == page else 'rewritten'}")
    print("✓ fallback news: " + ", ".join(it["id"] for it in items))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
