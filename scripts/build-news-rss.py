#!/usr/bin/env python3
"""
Generate news.xml (RSS 2.0) from data/news.json.

The RSS feed is the public, machine-readable mirror of the home-page
news block. Aggregators (Feedly, Inoreader, NetNewsWire) subscribe
to https://netsec-cost.eu/news.xml; the home-page cards and the feed
both derive from the same JSON, so they can't drift.

Single-language (EN) by convention — per-locale feeds (news.fr.xml,
news.de.xml) are a deferred follow-up if reader demand surfaces. The
EN feed reads `item.title.en`, `item.body.en`, etc.

Usage:
    python3 scripts/build-news-rss.py           # write news.xml
    python3 scripts/build-news-rss.py --check   # exit 1 if file would change

Run from the repo root. CI runs `--check` on every PR touching
data/news.json, news.xml, or this script.
"""
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
NEWS = ROOT / "data" / "news.json"
RSS = ROOT / "news.xml"
SITE = "https://netsec-cost.eu"
FEED_URL = SITE + "/news.xml"


def to_rfc822(iso: str) -> str:
    """ISO 8601 with offset → RFC 822 (RSS pubDate format)."""
    dt = datetime.fromisoformat(iso)
    return format_datetime(dt)


def cdata(text: str) -> str:
    """Wrap arbitrary text (incl. HTML) in CDATA so the feed reader
    treats it as literal markup. RSS 2.0 description fields are
    routinely HTML; CDATA avoids double-encoding."""
    # CDATA can't contain the literal "]]>". Split it if it appears.
    return "<![CDATA[" + text.replace("]]>", "]]]]><![CDATA[>") + "]]>"


def item_link(item: dict) -> str:
    """Per-item canonical URL.

    Prefer the EN CTA href if it's a same-site path; otherwise fall
    back to the home-page #news anchor with a #-fragment carrying the
    item id. That keeps the feed entries clickable without leaking
    locale-specific paths to feed readers.
    """
    cta = item.get("cta") or {}
    href = cta.get("href")
    if isinstance(href, dict):
        href = href.get("en", "")
    if isinstance(href, str) and href:
        if href.startswith("http://") or href.startswith("https://"):
            return href
        return SITE + "/" + href.lstrip("/")
    return SITE + "/#news"


def render(data: dict) -> str:
    chan_title = data["channelTitle"]
    chan_desc = data["channelDescription"]
    chan_link = data["channelLink"]
    chan_lang = data.get("channelLanguage", "en-GB")
    build_dt = to_rfc822(data["lastBuildDate"])

    out = []
    out.append('<?xml version="1.0" encoding="UTF-8"?>')
    out.append('<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">')
    out.append("  <channel>")
    out.append(f"    <title>{escape(chan_title)}</title>")
    out.append(f"    <link>{escape(chan_link)}</link>")
    out.append(f"    <description>{escape(chan_desc)}</description>")
    out.append(f"    <language>{escape(chan_lang)}</language>")
    out.append(f"    <lastBuildDate>{build_dt}</lastBuildDate>")
    out.append("    <generator>scripts/build-news-rss.py</generator>")
    out.append(
        f'    <atom:link href="{escape(FEED_URL)}" rel="self"'
        ' type="application/rss+xml"/>'
    )

    # Items: newest first per RSS convention. Sort by pubDate desc.
    items = sorted(
        data.get("items", []),
        key=lambda it: it["pubDate"],
        reverse=True,
    )
    for it in items:
        title = it["title"]["en"]
        body = it["body"]["en"]
        link = item_link(it)
        guid = it["id"]
        pub = to_rfc822(it["pubDate"])

        out.append("    <item>")
        out.append(f"      <title>{escape(title)}</title>")
        out.append(f"      <link>{escape(link)}</link>")
        out.append(f"      <description>{cdata(body)}</description>")
        out.append(f"      <pubDate>{pub}</pubDate>")
        out.append(
            f'      <guid isPermaLink="false">{escape(guid)}</guid>'
        )
        out.append("    </item>")

    out.append("  </channel>")
    out.append("</rss>")
    return "\n".join(out) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if news.xml would change. Don't write.",
    )
    args = p.parse_args()

    data = json.loads(NEWS.read_text(encoding="utf-8"))
    rendered = render(data)

    if args.check:
        existing = RSS.read_text(encoding="utf-8") if RSS.exists() else ""
        if rendered != existing:
            print(
                "✗ news.xml is out of sync with data/news.json.",
                file=sys.stderr,
            )
            print(
                "  Run `python3 scripts/build-news-rss.py` and commit "
                "the result.",
                file=sys.stderr,
            )
            return 1
        print("✓ news.xml matches data/news.json.")
        return 0

    RSS.write_text(rendered, encoding="utf-8")
    print(
        f"✓ Wrote {RSS.relative_to(ROOT)} "
        f"({len(data.get('items', []))} items)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
