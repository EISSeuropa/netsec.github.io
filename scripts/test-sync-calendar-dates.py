"""Unit tests for scripts/sync-calendar-dates.py and scripts/_event_dates.py.

Everything runs on in-memory fixtures. Nothing fetches the calendar or
writes data/events.json.
"""
import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import _event_dates  # noqa: E402

_spec = importlib.util.spec_from_file_location("sync_calendar_dates", _HERE / "sync-calendar-dates.py")
sync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sync)

_DOC = {"events": [
    {"uid": "school@x", "start": "2027-06-08T09:00", "end": "2027-06-11T18:00",
     "applicationDeadline": "2026-12-07",
     "displayDate": {"en": "8–11 June 2027", "fr": "8–11 juin 2027", "de": "8.–11. Juni 2027"}},
    {"uid": "conf@x", "indicoEventId": 30, "start": "2027-06-10T09:00", "end": "2027-06-11T18:00",
     "displayDate": {"en": "10–11 June 2027"}},
]}


def _run(dates):
    doc = copy.deepcopy(_DOC)
    changes, warnings = sync.apply_calendar_dates(doc, dates)
    return doc["events"][0], changes, warnings


# ── _event_dates ─────────────────────────────────────────────────

@pytest.mark.parametrize("start,end,want", [
    ("2027-06-08", "2027-06-11", {"en": "8–11 June 2027", "fr": "8–11 juin 2027", "de": "8.–11. Juni 2027"}),
    ("2026-09-13", "2026-09-13", {"en": "13 September 2026", "fr": "13 septembre 2026", "de": "13. September 2026"}),
    ("2026-06-30", "2026-07-02", {"en": "30 June – 2 July 2026", "fr": "30 juin – 2 juillet 2026", "de": "30. Juni – 2. Juli 2026"}),
    ("2026-12-30", "2027-01-01", {"en": "30 December 2026 – 1 January 2027", "fr": "30 décembre 2026 – 1er janvier 2027",
                                  "de": "30. Dezember 2026 – 1. Januar 2027"}),
])
def test_display_dates(start, end, want):
    assert _event_dates.display_dates(start + "T09:00", end + "T18:00") == want


def test_every_display_date_in_events_json_is_the_written_form():
    import json
    doc = json.loads((_HERE.parent / "data" / "events.json").read_text(encoding="utf-8"))
    for ev in doc["events"]:
        assert ev["displayDate"] == _event_dates.display_dates(ev["start"], ev["end"]), ev["uid"]


# ── apply_calendar_dates ─────────────────────────────────────────

def test_a_moved_event_takes_the_calendar_days_and_keeps_its_times():
    ev, changes, warnings = _run([{"date": "2027-06-15", "end": "2027-06-18", "label": "Training School", "uid": "school@x"}])
    assert (ev["start"], ev["end"]) == ("2027-06-15T09:00", "2027-06-18T18:00")
    assert ev["displayDate"] == {"en": "15–18 June 2027", "fr": "15–18 juin 2027", "de": "15.–18. Juni 2027"}
    assert len(changes) == 1 and not warnings


def test_a_one_day_calendar_date_sets_start_and_end_on_that_day():
    ev, _, _ = _run([{"date": "2027-06-09", "label": "x", "uid": "school@x"}])
    assert (ev["start"], ev["end"]) == ("2027-06-09T09:00", "2027-06-09T18:00")


def test_matching_dates_change_nothing():
    ev, changes, warnings = _run([
        {"date": "2027-06-08", "end": "2027-06-11", "label": "x", "uid": "school@x"},
        {"date": "2026-12-07", "label": "Applications close", "deadline": "school@x"},
    ])
    assert ev == _DOC["events"][0] and changes == [] and warnings == []


def test_the_deadline_line_sets_the_application_deadline():
    ev, changes, _ = _run([{"date": "2026-12-14", "label": "Applications close", "deadline": "school@x"}])
    assert ev["applicationDeadline"] == "2026-12-14"
    assert (ev["start"], ev["end"]) == ("2027-06-08T09:00", "2027-06-11T18:00")
    assert len(changes) == 1


def test_an_event_on_indico_is_left_to_indico():
    doc = copy.deepcopy(_DOC)
    changes, warnings = sync.apply_calendar_dates(doc, [{"date": "2027-06-20", "label": "x", "uid": "conf@x"}])
    assert doc["events"][1]["start"] == "2027-06-10T09:00"
    assert changes == [] and "Indico" in warnings[0]


def test_two_dates_naming_one_event_are_both_ignored():
    ev, changes, warnings = _run([{"date": "2027-06-15", "label": "a", "uid": "school@x"},
                                  {"date": "2027-06-16", "label": "b", "uid": "school@x"}])
    assert ev["start"] == "2027-06-08T09:00" and changes == [] and len(warnings) == 1


@pytest.mark.parametrize("cal", [
    {"date": "2027-06-15", "end": "2027-06-12", "label": "x", "uid": "school@x"},
    {"date": "15 June", "label": "x", "uid": "school@x"},
])
def test_an_invalid_calendar_range_is_reported_and_ignored(cal):
    ev, changes, warnings = _run([cal])
    assert ev["start"] == "2027-06-08T09:00" and changes == [] and len(warnings) == 1


def test_an_unknown_uid_is_reported():
    _, changes, warnings = _run([{"date": "2027-01-01", "label": "x", "uid": "nope@x"}])
    assert changes == [] and "nope@x" in warnings[0]


def test_dates_without_a_uid_line_are_not_used():
    ev, changes, warnings = _run([{"date": "2027-06-20", "label": "NetSec Training School", "site": "netsec"}])
    assert ev == _DOC["events"][0] and changes == [] and warnings == []
