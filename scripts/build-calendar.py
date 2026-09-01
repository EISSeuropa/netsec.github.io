#!/usr/bin/env python3
"""
Generate calendar.ics + per-event /calendar/<slug>.ics files from
data/events.json.

Two output classes share the same source-of-truth JSON:
  1. `calendar.ics` at the repo root — the public *subscribable* feed
     (RFC 5545 with `REFRESH-INTERVAL` / `X-PUBLISHED-TTL`). Surfaced
     as `webcal://netsec-cost.eu/calendar.ics`.
  2. `calendar/<slug>.ics` per event — one-shot *download* files
     intended for the "Add to calendar" buttons on each event card.
     Same VTIMEZONE block as the aggregate, but no REFRESH-INTERVAL
     since these aren't meant to be subscribed to.

`<slug>` is derived from the event's `uid` by stripping the
`@netsec-cost.eu` tail. Slugs must match `^[a-z0-9-]+$`; the
generator refuses non-conforming slugs to keep URLs predictable.

Usage:
    python3 scripts/build-calendar.py           # write all .ics files
    python3 scripts/build-calendar.py --check   # exit 1 if anything would change

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
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVENTS = ROOT / "data" / "events.json"
ICS = ROOT / "calendar.ics"
CALENDAR_DIR = ROOT / "calendar"

# Slug shape: lowercase alphanumeric + hyphens. Keeps the on-disk
# filename + the public URL predictable; refuses anything that would
# need escaping in either.
SLUG_RE = re.compile(r"^[a-z0-9-]+$")


def slug_for(uid: str) -> str:
    """Derive the per-event .ics slug from the event UID.

    UIDs look like ``summer-school-2026@netsec-cost.eu``; we keep the
    part to the left of ``@``. Raises if the result wouldn't match
    ``SLUG_RE`` so a bad UID surfaces at generation time rather than
    as a 404 later.
    """
    slug = uid.split("@", 1)[0]
    if not SLUG_RE.fullmatch(slug):
        raise ValueError(
            f"event uid {uid!r} yields slug {slug!r} which doesn't "
            f"match {SLUG_RE.pattern}. Fix the uid in data/events.json."
        )
    return slug


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


# VTIMEZONE blocks, keyed by TZID. An event carries its own `tzid` when the
# venue is not in the calendar's default zone, matching what
# assets/js/home-events.js already does for the Google and Outlook links.
# Adding a venue in a new zone means adding its block here.
VTIMEZONES: dict[str, list[str]] = {
    "Europe/Stockholm": [
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
    ],
    # Türkiye has been on UTC+3 year-round since September 2016, so there is
    # one component and no RRULE.
    "Europe/Istanbul": [
        "X-LIC-LOCATION:Europe/Istanbul",
        "BEGIN:STANDARD",
        "DTSTART:19700101T000000",
        "TZOFFSETFROM:+0300",
        "TZOFFSETTO:+0300",
        "TZNAME:+03",
        "END:STANDARD",
    ],
}


def event_tzid(ev: dict, default: str) -> str:
    """The zone an event's wall-clock times are in.

    Venue-local, so an event outside the calendar's default zone carries its
    own `tzid`. Without this every event inherited Europe/Stockholm, and the
    Ankara policy workshop's 09:00 start imported an hour late for anyone
    who added it to their calendar.
    """
    return ev.get("tzid") or default


def render_vtimezone(tzid: str) -> list[str]:
    """Inline one VTIMEZONE block."""
    body = VTIMEZONES.get(tzid)
    if body is None:
        raise SystemExit(
            f"VTIMEZONE for {tzid!r} not defined in {__file__}. "
            "Add a block for the new zone."
        )
    return ["BEGIN:VTIMEZONE", f"TZID:{tzid}"] + body + ["END:VTIMEZONE"]


def render_vtimezones(tzids) -> list[str]:
    """Inline a VTIMEZONE for each zone used, in first-seen order, so every
    TZID an event references resolves inside the file."""
    out: list[str] = []
    for tzid in dict.fromkeys(tzids):
        out.extend(render_vtimezone(tzid))
    return out


def render_vevent(ev: dict, dtstamp: str, tzid: str) -> list[str]:
    """Render one VEVENT. `tzid` is the calendar default; the event's own
    `tzid` wins where it has one.

    Keys honoured on `ev` (the rest are silently ignored):
      uid, summary, description, location, url, start, end,
      organizer{cn,mailto}, categories[], status.
    """
    ev_tzid = event_tzid(ev, tzid)
    out = [
        "BEGIN:VEVENT",
        f"UID:{ev['uid']}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART;TZID={ev_tzid}:{fmt_local(ev['start'])}",
        f"DTEND;TZID={ev_tzid}:{fmt_local(ev['end'])}",
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
    lines.extend(render_vtimezones(
        [tzid] + [event_tzid(ev, tzid) for ev in data["events"]]))
    for ev in data["events"]:
        lines.extend(render_vevent(ev, dtstamp, tzid))
    lines.append("END:VCALENDAR")
    return "\n".join(lines) + "\n"


def build_single_event_ics(ev: dict, data: dict) -> str:
    """Render a one-shot .ics for a single event.

    Same VTIMEZONE block as the aggregate so the TZID reference
    resolves, but no `REFRESH-INTERVAL` / `X-PUBLISHED-TTL` — these
    files are downloaded once and imported, not subscribed to.
    """
    tzid = data["tzid"]
    dtstamp = data["dtstamp"]
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//NetSec//CA24154 Events//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    lines.extend(render_vtimezone(event_tzid(ev, tzid)))
    lines.extend(render_vevent(ev, dtstamp, tzid))
    lines.append("END:VCALENDAR")
    return "\n".join(lines) + "\n"


def per_event_targets(data: dict) -> dict[Path, str]:
    """Map each per-event .ics path to its rendered content.

    Stable ordering for predictable diffs.
    """
    out: dict[Path, str] = {}
    for ev in data["events"]:
        slug = slug_for(ev["uid"])
        out[CALENDAR_DIR / f"{slug}.ics"] = build_single_event_ics(ev, data)
    return out


# ─── Main ─────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--check",
        action="store_true",
        help=(
            "Exit 1 if any output file (calendar.ics or any "
            "calendar/<slug>.ics) would change, or if there's a stale "
            "calendar/*.ics no longer referenced by data/events.json. "
            "Don't write."
        ),
    )
    args = p.parse_args()

    data = json.loads(EVENTS.read_text(encoding="utf-8"))
    rendered_agg = build_ics(data)
    rendered_per_event = per_event_targets(data)
    expected_per_event_files = set(rendered_per_event.keys())

    # Any extra .ics files in calendar/ that aren't expected this run
    # are stale (an event was removed from JSON). On write, we delete
    # them; on --check, we flag them as drift.
    existing_per_event_files = (
        set(CALENDAR_DIR.glob("*.ics")) if CALENDAR_DIR.exists() else set()
    )
    stale = sorted(existing_per_event_files - expected_per_event_files)

    if args.check:
        drift: list[str] = []
        existing_agg = ICS.read_text(encoding="utf-8") if ICS.exists() else ""
        if rendered_agg != existing_agg:
            drift.append("  · calendar.ics out of sync")
        for path, content in sorted(rendered_per_event.items()):
            current = path.read_text(encoding="utf-8") if path.exists() else ""
            if content != current:
                drift.append(f"  · {path.relative_to(ROOT)} out of sync")
        for path in stale:
            drift.append(
                f"  · {path.relative_to(ROOT)} stale (no matching event)"
            )
        if drift:
            print(
                "✗ Calendar files are out of sync with data/events.json:",
                file=sys.stderr,
            )
            for line in drift:
                print(line, file=sys.stderr)
            print(
                "  Run `python3 scripts/build-calendar.py` and commit "
                "the result.",
                file=sys.stderr,
            )
            return 1
        print(
            f"✓ calendar.ics + {len(rendered_per_event)} per-event files "
            f"match data/events.json."
        )
        return 0

    # Write the aggregate, then the per-event files, then clean up.
    ICS.write_text(rendered_agg, encoding="utf-8")
    CALENDAR_DIR.mkdir(exist_ok=True)
    for path, content in rendered_per_event.items():
        path.write_text(content, encoding="utf-8")
    for path in stale:
        path.unlink()

    print(
        f"✓ Wrote {ICS.relative_to(ROOT)} + "
        f"{len(rendered_per_event)} per-event files under "
        f"{CALENDAR_DIR.relative_to(ROOT)}/."
    )
    if stale:
        print(f"  removed {len(stale)} stale file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
