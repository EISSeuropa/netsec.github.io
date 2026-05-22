#!/usr/bin/env python3
"""
Smoke tests for scripts/sync-indico.py.

Same shape as scripts/test-sync-bios.py — standalone runnable, no
pytest, no live network. Loads fixture Indico responses from in-line
constants and asserts on the normalised output.

Usage:
    python3 scripts/test-sync-indico.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Import the module under test as a sibling.
sys.path.insert(0, str(Path(__file__).resolve().parent))
sync_indico = __import__("sync-indico")
extract_programme = sync_indico.extract_programme
_normalise_person = sync_indico._normalise_person
_normalise_contribution = sync_indico._normalise_contribution
_absolutize_indico_url = sync_indico._absolutize_indico_url
_looks_like_break = sync_indico._looks_like_break


def expect(label: str, got, want) -> None:
    if got != want:
        print(f"FAIL: {label}\n  got:  {got!r}\n  want: {want!r}", file=sys.stderr)
        sys.exit(1)
    print(f"  ok  {label}")


# ──────────────────────────── unit tests ────────────────────────────


def test_normalise_person_drops_email_hash() -> None:
    print("\n_normalise_person() — strips emailHash + db_id:")
    raw = {
        "name": "Dr Arthur Laudrain",
        "affiliation": "ETH Zurich",
        "emailHash": "abc123deadbeef",
        "db_id": 4711,
        "person_id": 7,
    }
    p = _normalise_person(raw)
    expect("name kept",          p["name"],            "Dr Arthur Laudrain")
    expect("affiliation kept",   p["affiliation"],     "ETH Zurich")
    expect("emailHash dropped",  "emailHash" in p,     False)
    expect("db_id dropped",      "db_id" in p,         False)
    expect("person_id dropped",  "person_id" in p,     False)


def test_absolutize_indico_url() -> None:
    print("\n_absolutize_indico_url() — fixes relative paths:")
    expect("absolute url passes through",
           _absolutize_indico_url("https://indico.eiss-europa.com/event/22/"),
           "https://indico.eiss-europa.com/event/22/")
    expect("relative path gets base prepended",
           _absolutize_indico_url("/event/22/contributions/521/"),
           "https://indico.eiss-europa.com/event/22/contributions/521/")
    expect("empty stays empty",
           _absolutize_indico_url(""),
           "")


def test_looks_like_break() -> None:
    print("\n_looks_like_break() — recognises break slot titles:")
    expect("coffee", _looks_like_break("Coffee break"), True)
    expect("tea break", _looks_like_break("Tea break"), True)
    expect("lunch", _looks_like_break("Lunch"), True)
    expect("session is not a break", _looks_like_break("Panel: European Defence"), False)
    expect("empty", _looks_like_break(""), False)


def test_normalise_contribution_truncates_abstract() -> None:
    print("\n_normalise_contribution() — truncates long abstracts to teaser:")
    long_abstract = "This paper examines " + "European security " * 50  # ~1000 chars
    c = {
        "title": "European deterrence in the 2020s",
        "startDate": {"time": "14:00:00"},
        "endDate":   {"time": "14:20:00"},
        "presenters": [
            {"name": "Dr Test Speaker", "affiliation": "Some University",
             "emailHash": "shouldbestripped"},
        ],
        "description": f"<p>{long_abstract}</p>",
        "url": "/event/22/contributions/521/",
    }
    out = _normalise_contribution(c)
    expect("title kept",
           out["title"], "European deterrence in the 2020s")
    expect("abstract is teaser-truncated (≤360+ellipsis)",
           len(out["abstract"]) <= 361, True)
    expect("teaser ends with ellipsis when truncated",
           out["abstract"].endswith("…"), True)
    expect("hasFullAbstract flag",
           out["hasFullAbstract"], True)
    expect("speaker emailHash stripped",
           "emailHash" in out["speakers"][0], False)
    expect("relative contribution url absolutised",
           out["url"], "https://indico.eiss-europa.com/event/22/contributions/521/")


# ──────────────────────────── integration ────────────────────────────


def _build_timetable_fixture() -> dict:
    """A minimal but realistic timetable shape that exercises sessions,
    parallel sessions, breaks, and roundtable-subtype detection. The
    `results` dict is keyed by event id, then by YYYYMMDD."""
    return {
        "22": {
            "20260611": {
                "s100": {
                    "id": "s100",
                    "entryType": "Session",
                    "title": "Welcome and registration",
                    "startDate": {"time": "08:30:00", "date": "2026-06-11"},
                    "endDate":   {"time": "09:00:00", "date": "2026-06-11"},
                    "room": "‘D House’",
                    "url": "https://indico.eiss-europa.com/event/22/sessions/1/",
                    "entries": {},
                },
                "s200": {
                    "id": "s200",
                    "entryType": "Session",
                    "title": "Roundtable: European Security in 2026",
                    "sessionCode": "RT",
                    "startDate": {"time": "09:45:00", "date": "2026-06-11"},
                    "endDate":   {"time": "10:45:00", "date": "2026-06-11"},
                    "room": "Hall A",
                    "url": "https://indico.eiss-europa.com/event/22/sessions/2/",
                    "conveners": [
                        {"name": "Dr Convener One", "affiliation": "Uni A",
                         "emailHash": "should-be-dropped"},
                    ],
                    "entries": {
                        "c500": {
                            "id": "c500",
                            "entryType": "Contribution",
                            "title": "Contributors",
                            "startDate": {"time": "09:45:00", "date": "2026-06-11"},
                            "endDate":   {"time": "10:45:00", "date": "2026-06-11"},
                            "presenters": [
                                {"name": "Discussant A", "affiliation": "Uni X"},
                                {"name": "Discussant B", "affiliation": "Uni Y"},
                            ],
                            "description": "",
                            "url": "/event/22/contributions/500/",
                        },
                    },
                },
                # Two parallel panels at 11:00 — same startTime,
                # different rooms.
                "s301": {
                    "id": "s301",
                    "entryType": "Session",
                    "title": "Panel: Deterrence",
                    "startDate": {"time": "11:00:00", "date": "2026-06-11"},
                    "endDate":   {"time": "12:30:00", "date": "2026-06-11"},
                    "room": "Hall A",
                    "url": "/event/22/sessions/3/",
                    "entries": {},
                    "conveners": [],
                },
                "s302": {
                    "id": "s302",
                    "entryType": "Session",
                    "title": "Panel: Cybersecurity",
                    "startDate": {"time": "11:00:00", "date": "2026-06-11"},
                    "endDate":   {"time": "12:30:00", "date": "2026-06-11"},
                    "room": "Hall B",
                    "url": "/event/22/sessions/4/",
                    "entries": {},
                    "conveners": [],
                },
                "s400": {
                    "id": "s400",
                    "entryType": "Session",
                    "title": "Coffee break",
                    "startDate": {"time": "10:45:00", "date": "2026-06-11"},
                    "endDate":   {"time": "11:00:00", "date": "2026-06-11"},
                    "room": "",
                    "url": "",
                    "entries": {},  # empty → reclassified as break
                },
            },
        },
    }


def test_extract_programme_shape() -> None:
    print("\nextract_programme() — overall shape:")
    p = extract_programme(_build_timetable_fixture(), event_id="22")
    expect("one day",             len(p["days"]),               1)
    expect("day label",           p["days"][0]["label"],        "Day 1")
    expect("date string",         p["days"][0]["date"],         "2026-06-11")
    # slots get sorted by startTime; coffee break at 10:45 should
    # sit between the roundtable (09:45) and the parallel panels (11:00).
    slots = p["days"][0]["slots"]
    expect("number of slots",     len(slots),                   5)
    expect("first slot is welcome session",
           slots[0]["title"], "Welcome and registration")
    expect("roundtable subtype detected",
           slots[1]["subtype"], "roundtable")
    expect("roundtable contributors → discussants",
           len(slots[1]["discussants"]), 2)
    expect("roundtable inner contribution flattened away",
           slots[1]["contributions"], [])
    expect("coffee break reclassified",
           slots[2]["kind"], "break")
    expect("convener emailHash stripped from session",
           "emailHash" in slots[1]["conveners"][0], False)


def test_extract_programme_parallel_rows() -> None:
    print("\nextract_programme() — parallel sessions grouped into one row:")
    p = extract_programme(_build_timetable_fixture(), event_id="22")
    rows = p["days"][0]["rows"]
    # Day 1 has 4 rows: welcome (08:30) → roundtable (09:45) → break
    # (10:45) → parallel panels (11:00 grouped).
    expect("4 rows",                  len(rows),                       4)
    expect("welcome row is not parallel",
           rows[0]["parallel"], False)
    expect("parallel panels row IS parallel",
           rows[3]["parallel"], True)
    expect("parallel row groups 2 items",
           len(rows[3]["items"]), 2)
    expect("parallel row endTime is max of grouped items",
           rows[3]["endTime"], "12:30")


def test_extract_programme_empty_timetable() -> None:
    print("\nextract_programme() — empty timetable produces no days, no crash:")
    p = extract_programme({}, event_id="22")
    expect("empty days", p["days"], [])


# ──────────────────────────── main ────────────────────────────


def main() -> None:
    test_normalise_person_drops_email_hash()
    test_absolutize_indico_url()
    test_looks_like_break()
    test_normalise_contribution_truncates_abstract()
    test_extract_programme_shape()
    test_extract_programme_parallel_rows()
    test_extract_programme_empty_timetable()
    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
