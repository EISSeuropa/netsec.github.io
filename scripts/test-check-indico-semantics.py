"""Tests for check-indico-semantics.py (#1718).

The point of this check is to catch a value that is well-formed and wrong, so
the tests are about what it flags rather than what it parses.
"""

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "check_indico_semantics", REPO / "scripts" / "check-indico-semantics.py"
)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def _conf(**over):
    base = {
        "id": 22,
        "title": "2026 European Security Studies Conference",
        "startTz": "Europe/Stockholm",
        "location": "Stockholm University",
        "startDateOnly": "2026-06-11",
        "endDateOnly": "2026-06-12",
        "programme": {"days": [{"date": "2026-06-11", "rows": [
            {"items": [{"title": "Opening", "room": "D House"}]}]}]},
    }
    base.update(over)
    return base


def test_timezone_matching_the_venue_is_silent():
    f = []
    mod.check_timezone("22", _conf(), f)
    assert f == []


def test_timezone_naming_another_city_is_flagged():
    """#1310: a Stockholm venue carrying Europe/Paris. Invisible today only
    because the two share an offset, and a wrong TZID the moment #855 ships."""
    f = []
    mod.check_timezone("22", _conf(startTz="Europe/Paris"), f)
    assert len(f) == 1
    assert "Europe/Paris" in f[0] and "Stockholm University" in f[0]
    # The fix is upstream, so the message has to say where.
    assert "Fix in Indico" in f[0]


def test_a_known_good_event_is_exempt():
    """An event in a city that is not its zone's namesake is legitimate."""
    mod.KNOWN_GOOD_TZ["22"] = "the venue is in Lyon"
    try:
        f = []
        mod.check_timezone("22", _conf(startTz="Europe/Paris"), f)
        assert f == []
    finally:
        del mod.KNOWN_GOOD_TZ["22"]


def test_a_day_outside_the_event_window_is_flagged():
    f = []
    conf = _conf()
    conf["programme"]["days"][0]["date"] = "2026-07-04"
    mod.check_days_inside_the_event("22", conf, f)
    assert len(f) == 1 and "2026-07-04" in f[0]


def test_a_missing_room_warns_but_does_not_fail():
    """A programme is often published before rooms are assigned. Failing the
    daily sync for that trains people to ignore it."""
    conf = _conf()
    conf["programme"]["days"][0]["rows"][0]["items"][0]["room"] = ""
    findings, warnings = [], []
    mod.check_rooms("22", conf, findings, warnings, strict=False)
    assert findings == [] and len(warnings) == 1
    findings, warnings = [], []
    mod.check_rooms("22", conf, findings, warnings, strict=True)
    assert len(findings) == 1 and warnings == []


def test_a_year_key_disagreeing_with_the_dates_is_flagged():
    """A sync that suddenly returns a different year is a category or event-id
    change upstream, not a programme update."""
    f = []
    mod.check_edition("22", "2027", _conf(), f)
    assert any("filed under 2027" in x for x in f)
