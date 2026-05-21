#!/usr/bin/env python3
"""
Generate calendar.ics from data/events.json.

The .ics file is the public calendar feed at
https://netsec-cost.eu/calendar.ics; the JSON is the
single source of truth for what goes in it.

Usage:
    python3 scripts/build-calendar.py           # write calendar.ics
    python3 scripts/build-calendar.py --check   # exit 1 if file would change

Run from the repo root.

Why a generator at all
----------------------
The HTML event cards in index.html (+ FR/DE) are still hand-authored —
they carry rich locale-specific copy that doesn't trivially derive from
JSON. But the .ics feed *is* fully derivable, and was previously also
hand-maintained alongside the cards. Two-place edits drift; one-source
+ generator + CI check doesn't.

CI runs `--check` on every PR touching data/events.json or calendar.ics
and fails the build if the committed calendar.ics doesn't match what
this script would produce. That guarantees the JSON and the .ics stay
in step. The HTML cards stay manual; the architecture doc reminds
maintainers to edit both at once.

Output format
-------------
Targets RFC 5545 with the practical leniency modern calendar clients
expect:
  - LF line endings (RFC says CRLF; every client I've tested handles
    LF). Matches the previously hand-authored file byte-for-byte.
  - No long-line folding. Long DESCRIPTION fields stay on one line.
    Apple Calendar, Google Calendar, Outlook, Thunderbird Lightning
    all accept this.
  - Commas / semicolons / backslashes / newlines in TEXT-type fields
    are escaped per RFC 5545 §3.3.11.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVENTS = ROOT / "data" / "events.json"
ICS = ROOT / "calendar.ics"


# ─── Helpers ──────────────────────────────────────────────────────

def escape_text(s: str) -> str:
    """RFC 5545 §3.3.11 TEXT escape.

    Order matters: backslash first so we don't double-escape the
    backslashes we're about to introduce.
    """
    return (
        s.replace("\\", "\\\\")
         .replace(",", "\\,")
         .replace(";", "\\;")
         .replace("\n", "\\n")
    )


def fmt_local(stamp: str) -> str:
    """Convert '2026-06-09T09:00' → '20260609T090000'.

    We don't carry timezone info in the value itself — the TZID
    parameter on DTSTART/DTEND attaches it.
    """
    date, time = stamp.split("T")
    y, m, d = date.split("-")
    hh, mm = time.split(":")
    return f"{y}{m}{d}T{hh}{mm}00"


def render_vtimezone(tzid: str) -> list[str]:
    """Inline the Europe/Stockholm VTIMEZONE.

    For now we only ship the one zone (Stockholm is the venue for
    the current events). If a future event sits elsewhere, add the
    matching VTIMEZONE block here keyed off `tzid`.
    """
    if tzid != "Europe/Stockholm":
        raise SystemExit(
            f"VTIMEZONE for {tzid!r} not defined in {__file__}. "
            "Add a block for the new zone."
        )
    return [
        "BEGIN:VTIMEZONE",
        "TZID:Europe/Stockholm",
        "X-LIC-LOCATION:Europe/Stockholm",
        "BEGIN:STANDARD",
        "DTSTART:19701025T030000",
        "TZOFFSETFROM:+0200",
        "TZOFFSETTO:+0100",
        "TZNAME:CET",
        "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU",
        "END:STANDARD",
        "BEGIN:DAYLIGHT",
        "DTSTART:19700329T020000",
        "TZOFFSETFROM:+0100",
        "TZOFFSETTO:+0200",
        "TZNAME:CEST",
        "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU",
        "END:DAYLIGHT",
        "END:VTIMEZONE",
    ]


def render_vevent(ev: dict, dtstamp: str, tzid: str) -> list[str]:
    """Render one VEVENT.

    Keys honoured on `ev` (the rest are silently ignored):
      uid, summary, description, location, url, start, end,
      organizer{cn,mailto}, categories[], status.
    """
    out = [
        "BEGIN:VEVENT",
        f"UID:{ev['uid']}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART;TZID={tzid}:{fmt_local(ev['start'])}",
        f"DTEND;TZID={tzid}:{fmt_local(ev['end'])}",
        f"SUMMARY:{escape_text(ev['summary'])}",
        f"DESCRIPTION:{escape_text(ev['description'])}",
        f"LOCATION:{escape_text(ev['location'])}",
        f"URL;VALUE=URI:{ev['url']}",
    ]
    org = ev.get("organizer")
    if org:
        out.append(
            f"ORGANIZER;CN={escape_text(org['cn'])}:"
            f"mailto:{org['mailto']}"
        )
    cats = ev.get("categories", [])
    if cats:
        # CATEGORIES is a single line, comma-separated. Each category
        # is a TEXT type, so we escape per-item but join with literal
        # commas (the separator) — that's the spec.
        out.append("CATEGORIES:" + ",".join(escape_text(c) for c in cats))
    status = ev.get("status")
    if status:
        out.append(f"STATUS:{status}")
    out.append("END:VEVENT")
    return out


def build_ics(data: dict) -> str:
    tzid = data["tzid"]
    dtstamp = data["dtstamp"]

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//NetSec//CA24154 Events//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_text(data['calname'])}",
        f"X-WR-CALDESC:{escape_text(data['caldesc'])}",
        f"X-WR-TIMEZONE:{tzid}",
        f"REFRESH-INTERVAL;VALUE=DURATION:P{data['refresh_days']}D",
        f"X-PUBLISHED-TTL:P{data['refresh_days']}D",
    ]
    lines.extend(render_vtimezone(tzid))
    for ev in data["events"]:
        lines.extend(render_vevent(ev, dtstamp, tzid))
    lines.append("END:VCALENDAR")
    return "\n".join(lines) + "\n"


# ─── Main ─────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if calendar.ics would change. Don't write.",
    )
    args = p.parse_args()

    data = json.loads(EVENTS.read_text(encoding="utf-8"))
    rendered = build_ics(data)

    if args.check:
        existing = ICS.read_text(encoding="utf-8") if ICS.exists() else ""
        if rendered != existing:
            print(
                f"✗ calendar.ics is out of sync with data/events.json.",
                file=sys.stderr,
            )
            print(
                "  Run `python3 scripts/build-calendar.py` and commit "
                "the result.",
                file=sys.stderr,
            )
            return 1
        print("✓ calendar.ics matches data/events.json.")
        return 0

    ICS.write_text(rendered, encoding="utf-8")
    print(f"✓ Wrote {ICS.relative_to(ROOT)} "
          f"({len(data['events'])} events).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
