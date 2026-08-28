#!/usr/bin/env python3
"""Check what the Indico sync *means*, not only its shape (#1718).

`check-data-shape.py` validates types, required fields and referential
integrity: the "would this blank a page?" set. It passes a conference held in
Stockholm carrying a Paris timezone, because that value is well-formed.

That is #1310, and it is invisible today only because Paris and Stockholm share
an offset year-round. It becomes a wrong `TZID` in an exported calendar the
moment the personal-programme export in #855 is built.

Indico is an upstream nobody here controls, edited through a web interface by
people who are not thinking about the website, so a field that is well-formed
and wrong is exactly the failure a shape check cannot see. Each finding names
what to fix **in Indico**, because that is where the fix goes: `sync-indico.py`
rewrites this file every night and a hand edit does not survive.

Four checks:

  1. The timezone names a city the venue does not mention.
  2. A programme day falls outside the event's own start and end dates.
  3. A programme item has no room, once the programme is published.
  4. The year key disagrees with the dates or the title.

Usage:
    python3 scripts/check-indico-semantics.py            # every synced file
    python3 scripts/check-indico-semantics.py --strict    # rooms become errors

Exit 0 when clean, 1 on any finding. Stdlib only.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# data/indico.json is the live sync. Each frozen essc-<year>-programme.json is
# a snapshot taken at conference close, and is checked too: a bad value frozen
# into the record is worse than one the next sync could correct.
SOURCES = [REPO / "data" / "indico.json"] + sorted(
    REPO.glob("data/essc-*-programme.json")
)

# A timezone identifier ends in the city it is named for. If that city is not
# in the venue string, either the venue is somewhere else or the event is in a
# city that is not its zone's namesake, which is common and legitimate: an
# event in Lyon is correctly Europe/Paris.
#
# So this is a prompt, not a verdict, and an event that is genuinely fine goes
# in KNOWN_GOOD_TZ keyed by its Indico event id, with the reason. A list of
# exceptions somebody had to justify is worth more than a check nobody runs.
KNOWN_GOOD_TZ: dict[str, str] = {
    # "22": "the venue is in Lyon; Europe/Paris is correct",
}

# A finding that is real, upstream, and already tracked. The check stays
# enforceable while it is open: the finding still prints, it just does not fail
# the run. Each entry is a substring matched against the finding text, so it is
# specific enough to expire on its own.
#
# An entry that stops matching is reported as stale, because an exception
# nobody removes is how a gate quietly stops checking anything.
KNOWN_UPSTREAM: dict[str, str] = {
    "timezone 'Europe/Paris' names 'Paris'":
        "#1310 — the ESSC 2026 Indico event was created with a Paris default; "
        "only the maintainer can change it upstream",
}


def _tz_city(tz: str) -> str:
    return (tz or "").split("/")[-1].replace("_", " ")


def check_timezone(event_id: str, conf: dict, findings: list) -> None:
    tz = conf.get("startTz") or ""
    location = conf.get("location") or ""
    if not tz or not location:
        return
    if event_id in KNOWN_GOOD_TZ:
        return
    city = _tz_city(tz)
    if city and city.lower() not in location.lower():
        findings.append(
            f"timezone {tz!r} names {city!r}, which is not in the venue "
            f"{location!r}.\n"
            f"      Fix in Indico: event {event_id} → Settings → Timezone. A "
            f"hand edit here is overwritten by the next sync.\n"
            f"      If the venue really is in a different city from its zone's "
            f"namesake, add {event_id!r} to KNOWN_GOOD_TZ in this script with "
            f"the reason."
        )


def check_days_inside_the_event(event_id: str, conf: dict, findings: list) -> None:
    start, end = conf.get("startDateOnly"), conf.get("endDateOnly")
    if not start or not end:
        return
    for day in (conf.get("programme") or {}).get("days") or []:
        date = day.get("date")
        if date and not (start <= date <= end):
            findings.append(
                f"programme day {date} falls outside the event's own "
                f"{start} to {end}.\n"
                f"      Fix in Indico: event {event_id} → the session dated "
                f"{date}, or the event's own start and end."
            )


def check_rooms(event_id: str, conf: dict, findings: list, warnings: list, strict: bool) -> None:
    missing = [
        item.get("title", "(untitled)")
        for day in (conf.get("programme") or {}).get("days") or []
        for row in day.get("rows") or []
        for item in row.get("items") or []
        if not (item.get("room") or "").strip()
    ]
    if not missing:
        return
    where = ", ".join(sorted(set(missing))[:4])
    more = f" and {len(missing) - 4} more" if len(missing) > 4 else ""
    line = (
        f"{len(missing)} programme item(s) have no room: {where}{more}.\n"
        f"      A blank room is invisible on the page and matters most on the "
        f"day. Fix in Indico: event {event_id} → the contribution → Room."
    )
    # Not an error by default: a programme is often published before the rooms
    # are assigned, and failing the daily sync for that would train people to
    # ignore it. --strict is for the week before the conference.
    (findings if strict else warnings).append(line)


def check_edition(event_id: str, year_key: str, conf: dict, findings: list) -> None:
    start = conf.get("startDateOnly") or ""
    if start and not start.startswith(year_key):
        findings.append(
            f"filed under {year_key} but starts {start}. A sync that suddenly "
            f"returns a different year is a category or event-id change "
            f"upstream.\n"
            f"      Check in Indico: event {event_id} is still the "
            f"{year_key} edition."
        )
    title = conf.get("title") or ""
    if title and year_key not in title and re.search(r"\b(19|20)\d{2}\b", title):
        findings.append(
            f"filed under {year_key} but the title says {title!r}."
        )


def main(argv: list) -> int:
    strict = "--strict" in argv
    findings: list[str] = []
    warnings: list[str] = []
    checked = 0

    for path in SOURCES:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            findings.append(f"{path.name}: not valid JSON ({exc})")
            continue
        for year_key, conf in sorted((data.get("annualConferences") or {}).items()):
            if not isinstance(conf, dict):
                continue
            checked += 1
            event_id = str(conf.get("id", "?"))
            local: list[str] = []
            check_timezone(event_id, conf, local)
            check_days_inside_the_event(event_id, conf, local)
            check_rooms(event_id, conf, local, warnings, strict)
            check_edition(event_id, year_key, conf, local)
            findings += [f"{path.name} · {year_key}: {f}" for f in local]

    for w in warnings:
        print(f"  ⚠ {w}", file=sys.stderr)

    known, new = [], []
    matched: set[str] = set()
    for f in findings:
        hit = next((k for k in KNOWN_UPSTREAM if k in f), None)
        if hit:
            matched.add(hit)
            known.append((f, KNOWN_UPSTREAM[hit]))
        else:
            new.append(f)

    for f, why in known:
        print(f"  · known: {f}\n      Tracked: {why}", file=sys.stderr)

    stale = sorted(set(KNOWN_UPSTREAM) - matched)
    for k in stale:
        print(f"  ! the allowance for {k!r} no longer matches anything. "
              f"Remove it from KNOWN_UPSTREAM in this script.", file=sys.stderr)

    if new:
        print(f"✗ {len(new)} new semantic problem(s) in the synced Indico data:",
              file=sys.stderr)
        for f in new:
            print(f"  ✗ {f}", file=sys.stderr)
        print("\n  These are values Indico returned that are well-formed and "
              "wrong, so the fix is upstream rather than in this repository.",
              file=sys.stderr)
        return 1
    if stale:
        return 1

    tail = []
    if known:
        tail.append(f"{len(known)} known and tracked")
    if warnings:
        tail.append(f"{len(warnings)} warning(s)")
    print(f"✓ {checked} conference edition(s) check out semantically"
          + (f" ({', '.join(tail)})" if tail else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
