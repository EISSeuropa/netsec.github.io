#!/usr/bin/env python3
"""Assemble one Year in Review edition into data/year-review.json.

The Action's year runs 10 October to 9 October, so year 1 is
2025-10-10 to 2026-10-09 and the page publishes near each anniversary
(#765). This script gathers the facts for one such window from the
data files that already hold them, and writes them as one edition in
an array so a second October is additive.

It composes no prose. Every number, title and date here is copied from
data/news.json, data/events.json, data/publications.json,
data/bios.json's git history, or CHANGELOG.md's release headers. The
narrative sentences on the page come from whole-sentence locale
templates in assets/js/year-review.js, and the lede and outlook
paragraphs come from the `hand` block, which the maintainer writes in
three locales each October. A regeneration carries the existing `hand`
block forward untouched, so the prose cannot be overwritten by a
rebuild.

Regeneration is deliberate, not gated in CI. An edition covers a
closed window: once 9 October passes the numbers are final and a
rebuild changes nothing, and before then a drift check would fail
every news and bios sync PR for a page nobody is reading yet. Run it
when preparing the edition, and again at publish time.

Usage:
    python3 scripts/build-year-review.py            # year 1
    python3 scripts/build-year-review.py --year 2
    python3 scripts/build-year-review.py --print    # stdout, no write

Needs the full git history for the member series (`fetch-depth: 0` in
any workflow), see scripts/_member_series.py.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _member_series import monthly_member_counts, shallow  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "year-review.json"

# The Action's grant agreement start. Year n runs from this date plus
# (n-1) years to the day before the following anniversary.
ACTION_START = date(2025, 10, 10)

LOCALES = ("en", "fr", "de")

DOCUMENTATION = (
    "Year in Review editions (#765), assembled by "
    "scripts/build-year-review.py from data/news.json, data/events.json, "
    "data/publications.json, the git history of data/bios.json and "
    "CHANGELOG.md. Rendered at runtime by assets/js/year-review.js on "
    "/year-in-review.html (+ FR + DE). Everything outside the `hand` "
    "block is generated and a rebuild overwrites it. The `hand` block is "
    "written by the maintainer in all three locales, one lede and one "
    "optional outlook paragraph per edition, and the builder carries it "
    "forward on every run rather than regenerating it. Editions are "
    "regenerated deliberately (when preparing an edition and again at "
    "publish time), not by a CI drift gate: the window is closed by "
    "publication day, so the numbers are final."
)

# `## [1.14.0] · 2026-08-29 — The NetSec Network Map`. The separators
# have been stable since 1.0.0. The hyphen and en dash variants are
# accepted too, so an older or hand-typed header still parses.
RELEASE_RE = re.compile(
    r"^## \[(\d+)\.(\d+)\.(\d+)\]\s*[·-]\s*(\d{4}-\d{2}-\d{2})\s*[—–-]\s*(.+?)\s*$"
)


def _add_months(d: date, months: int) -> date:
    """Same day-of-month, `months` later. Only used on the 10th, so no
    end-of-month clamping is needed."""
    total = (d.year * 12 + d.month - 1) + months
    return date(total // 12, total % 12 + 1, d.day)


def window(year: int) -> tuple[str, str]:
    """Inclusive ISO bounds of Action year `year` (1-based)."""
    start = _add_months(ACTION_START, 12 * (year - 1))
    end = _add_months(start, 12) - timedelta(days=1)
    return start.isoformat(), end.isoformat()


def quarters(start: str, end: str) -> list[dict]:
    """Four three-month spans covering the Action year."""
    first = date.fromisoformat(start)
    spans = []
    for n in range(4):
        q_from = _add_months(first, 3 * n)
        q_to = _add_months(first, 3 * (n + 1)) - timedelta(days=1)
        spans.append(
            {
                "n": n + 1,
                "from": q_from.isoformat(),
                "to": min(q_to.isoformat(), end),
            }
        )
    return spans


def _load(name: str) -> dict:
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def _locale_map(value, fallback: str = "") -> dict:
    """Normalise a field that may be a locale map or a bare string."""
    if isinstance(value, dict):
        return {loc: value.get(loc, value.get("en", fallback)) for loc in LOCALES}
    text = value if isinstance(value, str) else fallback
    return {loc: text for loc in LOCALES}


def news_items(start: str, end: str) -> list[dict]:
    items = []
    for it in _load("news.json").get("items", []):
        day = (it.get("pubDate") or "")[:10]
        if not (start <= day <= end):
            continue
        items.append(
            {
                "id": it.get("id", ""),
                "date": day,
                "displayDate": _locale_map(it.get("displayDate"), day),
                "title": _locale_map(it.get("title")),
                "type": it.get("type", ""),
                "wg": it.get("wg"),
            }
        )
    items.sort(key=lambda i: i["date"])
    return items


def events_held(start: str, end: str) -> list[dict]:
    held = []
    for ev in _load("events.json").get("events", []):
        day = (ev.get("start") or "")[:10]
        if not (start <= day <= end):
            continue
        held.append(
            {
                "uid": ev.get("uid", ""),
                "date": day,
                "displayDate": _locale_map(ev.get("displayDate"), day),
                "title": _locale_map(ev.get("cardTitle") or ev.get("summary")),
                "location": _locale_map(ev.get("cardLocation") or ev.get("location")),
                "eventType": ev.get("eventType", ""),
                "status": ev.get("status", ""),
            }
        )
    held.sort(key=lambda e: e["date"])
    return held


def outputs(start: str, end: str) -> list[dict]:
    """Publications in the window. `date` is an ISO year-month, so the
    comparison is on the month: an output dated 2026-10 counts in the
    year whose window contains that month."""
    pubs = []
    for p in _load("publications.json").get("publications", []):
        month = (p.get("date") or "")[:7]
        if not (start[:7] <= month <= end[:7]):
            continue
        pubs.append(
            {
                "date": month,
                "title": _locale_map(p.get("title")),
                "type": p.get("type", ""),
                "authors": p.get("authors") or [],
                "url": p.get("url") or p.get("doi") or "",
            }
        )
    pubs.sort(key=lambda p: p["date"])
    return pubs


def releases(start: str, end: str) -> tuple[int, list[dict]]:
    """(count of all releases in the window, the minor ones).

    Patch releases carry the count; a minor is the one a reader can be
    told about, so only those reach the page.
    """
    total = 0
    minors = []
    for line in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8").splitlines():
        m = RELEASE_RE.match(line)
        if not m:
            continue
        major, minor, patch, day, title = m.groups()
        if not (start <= day <= end):
            continue
        total += 1
        if patch == "0":
            minors.append(
                {
                    "version": f"{major}.{minor}.{patch}",
                    "date": day,
                    "title": title,
                }
            )
    # Two minors can share a release date, so order by version rather
    # than by date.
    minors.sort(key=lambda r: [int(n) for n in r["version"].split(".")])
    return total, minors


def directory_snapshot() -> dict:
    """Members, distinct countries and the theme spread, as the
    Directory stands now. A per-window snapshot is not recoverable for
    themes without replaying every bios.json revision, and the
    retrospective reads as of publication day."""
    members = _load("bios.json").get("members", [])
    countries = {
        (m.get("country_code") or m.get("country") or "").strip()
        for m in members
    }
    countries.discard("")
    themes: dict[str, int] = {}
    for m in members:
        for t in m.get("themes") or []:
            themes[t] = themes.get(t, 0) + 1
    return {
        "members": len(members),
        "countries": len(countries),
        "themes": [
            {"name": name, "members": n}
            for name, n in sorted(themes.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
    }


def empty_hand() -> dict:
    return {
        "lede": {loc: "" for loc in LOCALES},
        "outlook": {loc: "" for loc in LOCALES},
    }


def existing_hand(year: int) -> dict:
    """The hand-authored block already on disk for this edition."""
    if not OUT.exists():
        return empty_hand()
    try:
        data = json.loads(OUT.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return empty_hand()
    for ed in data.get("editions", []):
        if ed.get("year") == year:
            hand = ed.get("hand") or {}
            out = empty_hand()
            for field in out:
                for loc in LOCALES:
                    out[field][loc] = (hand.get(field) or {}).get(loc, "")
            return out
    return empty_hand()


def build_edition(year: int) -> dict:
    start, end = window(year)
    news = news_items(start, end)
    events = events_held(start, end)
    pubs = outputs(start, end)
    release_count, minors = releases(start, end)
    snapshot = directory_snapshot()

    spans = quarters(start, end)
    for q in spans:
        q["news"] = [n["id"] for n in news if q["from"] <= n["date"] <= q["to"]]
        q["events"] = [e["uid"] for e in events if q["from"] <= e["date"] <= q["to"]]

    return {
        "year": year,
        "window": {"from": start, "to": end},
        "stats": {
            "members": snapshot["members"],
            "countries": snapshot["countries"],
            "events": len(events),
            "outputs": len(pubs),
            "news": len(news),
            "releases": release_count,
        },
        "memberSeries": monthly_member_counts(ROOT, until=end),
        "themes": snapshot["themes"],
        "quarters": spans,
        "news": news,
        "events": events,
        "outputs": pubs,
        "releases": minors,
        "hand": existing_hand(year),
    }


def build(year: int) -> dict:
    """The whole file: the requested edition merged into any others."""
    editions = []
    if OUT.exists():
        try:
            editions = json.loads(OUT.read_text(encoding="utf-8")).get(
                "editions", []
            )
        except json.JSONDecodeError:
            editions = []
    editions = [ed for ed in editions if ed.get("year") != year]
    editions.append(build_edition(year))
    editions.sort(key=lambda ed: ed.get("year", 0))
    return {
        "_documentation": DOCUMENTATION,
        "actionStart": ACTION_START.isoformat(),
        "generatedAt": date.today().isoformat(),
        "editions": editions,
    }


def main(argv: list) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--year", type=int, default=1, help="Action year (default 1)")
    p.add_argument(
        "--print",
        action="store_true",
        dest="to_stdout",
        help="Write to stdout instead of data/year-review.json.",
    )
    args = p.parse_args(argv)

    if args.year < 1:
        print("✗ --year must be 1 or more.", file=sys.stderr)
        return 1
    if shallow(ROOT):
        print(
            "⚠ Shallow clone: the member series will be truncated. "
            "Use fetch-depth: 0.",
            file=sys.stderr,
        )

    data = build(args.year)
    rendered = json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    if args.to_stdout:
        sys.stdout.write(rendered)
        return 0

    OUT.write_text(rendered, encoding="utf-8")
    ed = next(e for e in data["editions"] if e["year"] == args.year)
    s = ed["stats"]
    print(
        f"✓ Wrote {OUT.relative_to(ROOT)} year {args.year} "
        f"({ed['window']['from']} to {ed['window']['to']}): "
        f"{s['members']} members, {s['countries']} countries, "
        f"{s['events']} events, {s['outputs']} outputs, "
        f"{s['news']} news items, {s['releases']} releases."
    )
    if not any(ed["hand"]["lede"].values()):
        print("  The lede is still empty. Write it in all three locales.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
