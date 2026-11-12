#!/usr/bin/env python3
"""
Rewrite event dates in data/events.json from the "EISS dates" calendar (#2133).

The "EISS dates" Google Calendar holds every public EISS and NetSec date. The
EISS status web app (workspace-ops/status) publishes it at ?view=dates as
{ dates: [{ date, end, label, site, indico, url, uid, deadline, ... }] }.

Events on Indico take their dates from Indico through sync-indico.py. This
script covers what Indico does not give:

  - a calendar date whose description has the line `uid: <uid>` sets that
    entry's `start` and `end` days, for entries with no `indicoEventId`.
    The times of day stay as they are.
  - a calendar date whose description has the line `deadline: <uid>` sets
    that entry's `applicationDeadline`, whether or not it is on Indico.

When `start` or `end` moves, `displayDate` is rewritten in every locale, and
calendar.ics is rebuilt. An entry no calendar date names is left alone, so an
empty or unreachable calendar changes nothing.

Prose dates on the pages are not rewritten. `inject-seo.py --check` flags
them on the sync's pull request, and a person edits them there.

Usage:
    python3 scripts/sync-calendar-dates.py            # fetch and write
    python3 scripts/sync-calendar-dates.py --dry-run  # report only

Operational messages go to stderr, a markdown summary of the changes to
stdout (the workflow puts it in the pull request body). The script exits 0
when the calendar cannot be reached, so the Indico sync in the same workflow
still runs.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _event_dates import display_dates  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
EVENTS_JSON = ROOT / "data" / "events.json"
# The EISS status web app (workspace-ops/status/README.md, "Dates"). The same
# address is in the EISS site's src/_data/systemHealth.js.
STATUS_APP = ("https://script.google.com/macros/s/AKfycbyUPZHKz0SQ0eNN6jfvy7TWvS_LtVFMnir2Q4D-QJEjjJXoGS7VbK63m7MIhUFBp4QN"
              "/exec?view=dates")


def _named(dates: list[dict], key: str) -> tuple[dict[str, dict], list[str]]:
    """The calendar dates by the uid on their `key` line, and a warning for
    each uid that more than one date names (those are skipped)."""
    seen: dict[str, list[dict]] = {}
    for d in dates:
        uid = str(d.get(key) or "").strip()
        if uid:
            seen.setdefault(uid, []).append(d)
    warnings = [f"{len(v)} calendar dates carry `{key}: {uid}`, so none is used" for uid, v in seen.items() if len(v) > 1]
    return {uid: v[0] for uid, v in seen.items() if len(v) == 1}, warnings


def _valid_day(s) -> bool:
    try:
        dt.date.fromisoformat(str(s))
        return len(str(s)) == 10
    except ValueError:
        return False


def apply_calendar_dates(doc: dict, dates: list[dict]) -> tuple[list[str], list[str]]:
    """Patch doc in place. Returns (changes, warnings), each a list of lines."""
    by_uid, warnings = _named(dates, "uid")
    deadlines, more = _named(dates, "deadline")
    warnings += more
    changes: list[str] = []
    known = {ev["uid"] for ev in doc.get("events", [])}
    for uid in sorted((set(by_uid) | set(deadlines)) - known):
        warnings.append(f"the calendar names `{uid}`, which is not in data/events.json")

    for ev in doc.get("events", []):
        uid = ev["uid"]
        on_indico = ev.get("indicoEventId") is not None
        if on_indico and uid in by_uid:
            warnings.append(f"`{uid}` is on Indico, which sets its dates, so its calendar line is ignored")

        cal = None if on_indico else by_uid.get(uid)
        if cal:
            first, last = cal.get("date"), cal.get("end") or cal.get("date")
            if not (_valid_day(first) and _valid_day(last)) or last < first:
                warnings.append(f"`{uid}`: the calendar date {first!r} to {last!r} is not a valid range")
            else:
                start = first + ev["start"][10:]
                end = last + ev["end"][10:]
                if (start, end) != (ev["start"], ev["end"]):
                    changes.append(f"`{uid}`: {ev['start']} to {ev['end']} → {start} to {end}")
                    ev["start"], ev["end"] = start, end
                    ev["displayDate"] = display_dates(start, end)

        cal = deadlines.get(uid)
        if cal:
            day = cal.get("date")
            if not _valid_day(day):
                warnings.append(f"`{uid}`: the calendar deadline {day!r} is not a date")
            elif ev.get("applicationDeadline") != day:
                changes.append(f"`{uid}`: application deadline {ev.get('applicationDeadline') or 'none'} → {day}")
                ev["applicationDeadline"] = day
    return changes, warnings


def fetch_dates() -> list[dict] | None:
    try:
        res = requests.get(STATUS_APP, timeout=30)
        res.raise_for_status()
        dates = res.json().get("dates")
    except (requests.RequestException, ValueError) as exc:
        print(f"  ! the dates calendar is unavailable ({exc}); data/events.json left as it is", file=sys.stderr)
        return None
    return dates if isinstance(dates, list) else []


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("--dry-run", action="store_true", help="Report what would change but don't write.")
    args = p.parse_args()

    dates = fetch_dates()
    if dates is None:
        return 0
    doc = json.loads(EVENTS_JSON.read_text(encoding="utf-8"))
    changes, warnings = apply_calendar_dates(doc, dates)
    for w in warnings:
        print(f"  ! {w}", file=sys.stderr)
    print(f"  {len(dates)} calendar dates read, {len(changes)} changes to data/events.json", file=sys.stderr)
    if not changes:
        return 0

    print("### Dates from the \"EISS dates\" calendar\n")
    for c in changes:
        print(f"- {c}")
    print("\nProse dates on the pages are not rewritten. Where `inject-seo.py --check` flags one, edit it on this pull request.\n")
    if args.dry_run:
        return 0

    doc["dtstamp"] = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    EVENTS_JSON.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build-calendar.py")], check=True, cwd=ROOT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
