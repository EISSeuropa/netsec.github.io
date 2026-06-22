#!/usr/bin/env python3
"""
Turn a GitHub issue labelled `news` into a news item (#634 parallel from EISS).

The news-publish workflow runs this when an issue gains the `news` label. It
reads the issue title + body, prepends a new item to data/news.json, and bumps
lastBuildDate. The workflow then regenerates news.xml (build-news-rss.py) and
opens an auto-merging PR that `Closes` the issue.

Issue format
------------
The issue TITLE becomes the news headline. The BODY becomes the excerpt, with
optional header lines at the very top (any order, case-insensitive):

    Type: Announcement          # free-text label, shown as the date-pill prefix
    URL: https://example.org    # adds a "Read more" CTA (external)
    Date: 2026-06-20            # ISO date; defaults to today

    The first paragraph after the headers is the excerpt shown on the card.

Items are authored in English only (like the EISS Anthology): the home and
archive renderers fall back to EN for FR/DE, so a hand translation can be added
to data/news.json later without blocking publication. The data change touches no
HTML, so it does not trip the i18n drift checker.

Usage (env-driven, as the workflow calls it):
    ISSUE_NUMBER=634 ISSUE_TITLE="..." ISSUE_BODY="..." python3 scripts/publish-news.py

    python3 scripts/publish-news.py --check   # validate news.json round-trips

Stdlib only; runs under /usr/bin/python3.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEWS = ROOT / "data" / "news.json"

HEADER_RE = re.compile(r"^\s*(type|url|date|wg)\s*:\s*(.+?)\s*$", re.IGNORECASE)
_MONTHS = ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"]


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:60] or "news-item"


def parse_issue(title: str, body: str) -> dict:
    """Pure parse: (title, body) -> {type, url, date, wg, excerpt}. No IO."""
    lines = (body or "").replace("\r\n", "\n").split("\n")
    headers = {}
    i = 0
    # Consume contiguous leading header lines (skipping blank lines between).
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        m = HEADER_RE.match(lines[i])
        if not m:
            break
        headers[m.group(1).lower()] = m.group(2).strip()
        i += 1
    excerpt = "\n".join(lines[i:]).strip()
    # First paragraph only, collapsed to one line.
    excerpt = re.split(r"\n\s*\n", excerpt, maxsplit=1)[0].strip()
    excerpt = re.sub(r"\s+", " ", excerpt)
    return {
        "title": (title or "").strip(),
        "type": headers.get("type", "").strip(),
        "url": headers.get("url", "").strip(),
        "date": headers.get("date", "").strip(),
        "wg": headers.get("wg", "").strip(),
        "excerpt": excerpt,
    }


def display_date(iso: str) -> str:
    try:
        d = dt.date.fromisoformat(iso)
        return f"{d.day} {_MONTHS[d.month - 1]} {d.year}"
    except ValueError:
        return iso


def build_item(parsed: dict, issue_number: str, today: dt.date) -> dict:
    date_iso = parsed["date"] or today.isoformat()
    try:
        date_obj = dt.date.fromisoformat(date_iso)
    except ValueError:
        date_iso = today.isoformat()
        date_obj = today
    pub = f"{date_iso}T09:00:00+02:00"
    item = {
        "id": f"{slugify(parsed['title'])}-{date_obj.strftime('%Y%m%d')}",
        "pubDate": pub,
        "_source_issue": int(issue_number) if str(issue_number).isdigit() else issue_number,
        "displayDate": {"en": display_date(date_iso)},
        "title": {"en": parsed["title"]},
        "body": {"en": parsed["excerpt"]},
    }
    # Optional category tag (rendered as a pill beside the date; the home and
    # archive renderers Title-case and translate it).
    if parsed.get("type"):
        item["type"] = parsed["type"].lower()
    # Optional Working-Group activity tag (1-4); ignored if out of range.
    if parsed.get("wg", "").isdigit() and 1 <= int(parsed["wg"]) <= 4:
        item["wg"] = int(parsed["wg"])
    if parsed["url"]:
        item["cta"] = {
            "href": parsed["url"],
            "external": True,
            "i18n": {"en": "Read more"},
        }
    return item


def check() -> int:
    try:
        data = json.loads(NEWS.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"✗ data/news.json invalid: {exc}", file=sys.stderr)
        return 1
    if not isinstance(data.get("items"), list):
        print("✗ data/news.json has no items array", file=sys.stderr)
        return 1
    print(f"✓ data/news.json valid ({len(data['items'])} items).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Publish a news item from a labelled issue.")
    ap.add_argument("--check", action="store_true", help="validate news.json and exit")
    ap.add_argument("--title", help="override ISSUE_TITLE (testing)")
    ap.add_argument("--body", help="override ISSUE_BODY (testing)")
    ap.add_argument("--number", help="override ISSUE_NUMBER (testing)")
    args = ap.parse_args()
    if args.check:
        return check()

    title = args.title if args.title is not None else os.environ.get("ISSUE_TITLE", "")
    body = args.body if args.body is not None else os.environ.get("ISSUE_BODY", "")
    number = args.number if args.number is not None else os.environ.get("ISSUE_NUMBER", "")
    if not title.strip():
        print("✗ no issue title provided (ISSUE_TITLE)", file=sys.stderr)
        return 1

    parsed = parse_issue(title, body)
    if not parsed["excerpt"]:
        print("✗ the issue body has no excerpt paragraph", file=sys.stderr)
        return 1

    today = dt.datetime.now(dt.timezone.utc).date()
    item = build_item(parsed, number, today)

    data = json.loads(NEWS.read_text(encoding="utf-8"))
    # Idempotency: if this issue already produced an item, replace it.
    data["items"] = [it for it in data["items"] if it.get("_source_issue") != item["_source_issue"]]
    data["items"].insert(0, item)
    # Newest first by pubDate.
    data["items"].sort(key=lambda it: it.get("pubDate", ""), reverse=True)
    data["lastBuildDate"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

    NEWS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"✓ Added news item {item['id']!r} from issue #{number}.")
    print("  Run: python3 scripts/build-news-rss.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
