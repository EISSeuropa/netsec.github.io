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
summarise_changes = sync_indico.summarise_changes
should_carry_over = sync_indico.should_carry_over


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
    expect("presenter emailHash stripped",
           "emailHash" in out["people"][0], False)
    expect("sole presenter flagged as speaker",
           out["people"][0]["speaker"], True)
    expect("relative contribution url absolutised",
           out["url"], "https://indico.eiss-europa.com/event/22/contributions/521/")


def test_normalise_contribution_coauthors() -> None:
    """The byline merges speakers + primaryauthors + coauthors into one
    ordered `people` list (authors first), de-dupes the same person
    across lists, and flags only the presenters as speakers."""
    print("\n_normalise_contribution() — co-authors merged + speaker-flagged:")
    c = {
        "title": "Co-authored paper",
        "startDate": {"time": "11:00:00"},
        "endDate":   {"time": "11:20:00"},
        # Presenter is also a primary author; a second primary author
        # and a co-author do not present.
        "speakers":       [{"name": "Alice Speaker", "affiliation": "Uni A"}],
        "primaryauthors": [{"name": "Alice Speaker", "affiliation": "Uni A"},
                           {"name": "Bob Author", "affiliation": "Uni B"}],
        "coauthors":      [{"name": "Carol Coauthor", "affiliation": "Uni C"}],
        "description": "",
        "url": "",
    }
    out = _normalise_contribution(c)
    names = [p["name"] for p in out["people"]]
    expect("all three people present, authors first, de-duped",
           names, ["Alice Speaker", "Bob Author", "Carol Coauthor"])
    flags = {p["name"]: p["speaker"] for p in out["people"]}
    expect("presenter flagged", flags["Alice Speaker"], True)
    expect("non-presenting primary author not flagged", flags["Bob Author"], False)
    expect("co-author not flagged", flags["Carol Coauthor"], False)


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


def test_summarise_changes() -> None:
    print("\nsummarise_changes() — reports session + paper diffs:")

    def conf(sessions):
        return {"annualConferences": {"2026": {"programme": {"days": [
            {"date": "2026-06-11", "rows": [
                {"startTime": s["startTime"], "parallel": False, "items": [s]}
                for s in sessions
            ]},
        ]}}}}

    old = conf([
        {"id": "s1", "kind": "session", "title": "Panel A",
         "startTime": "11:00", "endTime": "12:15", "room": "LH8",
         "contributions": [{"title": "Paper One", "people": [{"name": "Alice"}]}]},
        {"id": "s2", "kind": "session", "title": "Panel B",
         "startTime": "14:00", "endTime": "15:00", "room": "LH9", "contributions": []},
    ])
    new = conf([
        {"id": "s1", "kind": "session", "title": "Panel A (revised)",
         "startTime": "11:15", "endTime": "12:30", "room": "LH8",
         "contributions": [
             {"title": "Paper One", "people": [{"name": "Alice"}, {"name": "Bob"}]},
             {"title": "Paper Two", "people": [{"name": "Carol"}]},
         ]},
        {"id": "s3", "kind": "session", "title": "Panel C",
         "startTime": "16:00", "endTime": "17:00", "room": "LH8", "contributions": []},
    ])
    out = "\n".join(summarise_changes(old, new))
    expect("retime reported", "Retimed" in out and "11:00" in out and "11:15" in out, True)
    expect("rename reported", "Panel A (revised)" in out, True)
    expect("added session reported", "Added" in out and "Panel C" in out, True)
    expect("removed session reported", "Removed" in out and "Panel B" in out, True)
    expect("new paper reported", "Paper Two" in out, True)
    expect("author-byline change reported", "Authors" in out and "Bob" in out, True)
    expect("no-change yields empty list", summarise_changes(old, old), [])


def test_should_carry_over() -> None:
    """Post-conference carry-over: when a finished edition drops out of
    Indico the sync must keep the snapshot, not overwrite the programme
    with an empty map. Regression for the daily empty-data PR that the
    data-shape guard (annualConferences non-empty) rejected once ESSC
    2026 ended."""
    print("\nshould_carry_over() — keep the snapshot when a finished conference drops out:")
    existing = {"annualConferences": {"2026": {"title": "ESSC 2026"}}}
    expect("empty fetch + existing programme -> carry over",
           should_carry_over({}, existing), True)
    expect("non-empty fetch -> write it, no carry-over",
           should_carry_over({"2026": {"title": "x"}}, existing), False)
    expect("empty fetch + no prior data -> no carry-over (first run)",
           should_carry_over({}, None), False)
    expect("empty fetch + empty prior -> no carry-over",
           should_carry_over({}, {"annualConferences": {}}), False)


def main() -> None:
    test_normalise_person_drops_email_hash()
    test_absolutize_indico_url()
    test_looks_like_break()
    test_normalise_contribution_truncates_abstract()
    test_normalise_contribution_coauthors()
    test_extract_programme_shape()
    test_extract_programme_parallel_rows()
    test_extract_programme_empty_timetable()
    test_summarise_changes()
    test_should_carry_over()
    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
