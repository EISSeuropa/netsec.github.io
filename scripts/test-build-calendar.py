"""Tests for scripts/build-calendar.py.

The module name contains a hyphen, so it can't be imported by name; we
load it via importlib from its relative path. All filesystem side
effects are redirected into tmp_path by monkeypatching the module-level
ROOT-derived path constants. No network is involved anywhere in the
script, so nothing to stub there.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

# ─── Load the hyphenated module ───────────────────────────────────
_HERE = Path(__file__).resolve().parent
_SCRIPT = _HERE / "build-calendar.py"

spec = importlib.util.spec_from_file_location("build_calendar", _SCRIPT)
bc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bc)


# ─── Fixtures ─────────────────────────────────────────────────────

def make_event(**overrides):
    ev = {
        "uid": "summer-school-2026@netsec-cost.eu",
        "summary": "NetSec Summer School",
        "description": "A description.",
        "location": "Stockholm, Sweden",
        "url": "https://example.com/event",
        "start": "2026-06-09T09:00",
        "end": "2026-06-11T18:00",
    }
    ev.update(overrides)
    return ev


def make_data(events=None, **overrides):
    data = {
        "calname": "NetSec, COST Action CA24154",
        "caldesc": "Events from NetSec.",
        "tzid": "Europe/Stockholm",
        "refresh_days": 7,
        "dtstamp": "20260528T120000Z",
        "events": events if events is not None else [make_event()],
    }
    data.update(overrides)
    return data


# ─── slug_for ─────────────────────────────────────────────────────

def test_slug_for_strips_domain_tail():
    assert bc.slug_for("summer-school-2026@netsec-cost.eu") == "summer-school-2026"


def test_slug_for_no_at_sign_returns_whole():
    assert bc.slug_for("plain-slug") == "plain-slug"


def test_slug_for_only_first_at_is_split():
    # split("@", 1) keeps everything left of the *first* @
    assert bc.slug_for("a-b@x@y") == "a-b"


def test_slug_for_rejects_uppercase():
    with pytest.raises(ValueError):
        bc.slug_for("Summer-School@netsec-cost.eu")


def test_slug_for_rejects_underscore():
    with pytest.raises(ValueError):
        bc.slug_for("summer_school@netsec-cost.eu")


def test_slug_for_rejects_empty_slug():
    with pytest.raises(ValueError):
        bc.slug_for("@netsec-cost.eu")


def test_slug_for_rejects_space():
    with pytest.raises(ValueError):
        bc.slug_for("summer school@netsec-cost.eu")


def test_slug_for_allows_digits_and_hyphens():
    assert bc.slug_for("essc-2026@netsec-cost.eu") == "essc-2026"


# ─── escape_text ──────────────────────────────────────────────────

def test_escape_text_plain_unchanged():
    assert bc.escape_text("Plain text") == "Plain text"


def test_escape_text_comma():
    assert bc.escape_text("a,b") == "a\\,b"


def test_escape_text_semicolon():
    assert bc.escape_text("a;b") == "a\\;b"


def test_escape_text_newline():
    assert bc.escape_text("a\nb") == "a\\nb"


def test_escape_text_backslash_first():
    # A literal backslash must be doubled, and must not double-escape
    # the escapes we then introduce.
    assert bc.escape_text("a\\b") == "a\\\\b"


def test_escape_text_backslash_before_comma():
    # Order matters: "\," in input -> backslash doubled, comma escaped.
    assert bc.escape_text("\\,") == "\\\\\\,"


def test_escape_text_all_together():
    assert bc.escape_text("x\\y,z;w\nq") == "x\\\\y\\,z\\;w\\nq"


# ─── fmt_local ────────────────────────────────────────────────────

def test_fmt_local_basic():
    assert bc.fmt_local("2026-06-09T09:00") == "20260609T090000"


def test_fmt_local_midnight():
    assert bc.fmt_local("2026-12-31T00:00") == "20261231T000000"


def test_fmt_local_preserves_zero_padding():
    assert bc.fmt_local("2026-01-05T08:07") == "20260105T080700"


def test_fmt_local_appends_seconds():
    # seconds are always forced to 00
    assert bc.fmt_local("2026-06-09T23:59").endswith("235900")


def test_fmt_local_missing_time_raises():
    with pytest.raises(ValueError):
        bc.fmt_local("2026-06-09")


# ─── render_vtimezone ─────────────────────────────────────────────

def test_render_vtimezone_stockholm_structure():
    lines = bc.render_vtimezone("Europe/Stockholm")
    assert lines[0] == "BEGIN:VTIMEZONE"
    assert lines[-1] == "END:VTIMEZONE"
    assert "TZID:Europe/Stockholm" in lines
    assert "BEGIN:STANDARD" in lines and "END:STANDARD" in lines
    assert "BEGIN:DAYLIGHT" in lines and "END:DAYLIGHT" in lines


def test_render_vtimezone_unknown_raises_systemexit():
    with pytest.raises(SystemExit):
        bc.render_vtimezone("America/New_York")


# ─── render_vevent ────────────────────────────────────────────────

def test_render_vevent_required_lines():
    ev = make_event()
    out = bc.render_vevent(ev, "20260528T120000Z", "Europe/Stockholm")
    assert out[0] == "BEGIN:VEVENT"
    assert out[-1] == "END:VEVENT"
    assert "UID:summer-school-2026@netsec-cost.eu" in out
    assert "DTSTAMP:20260528T120000Z" in out
    assert "DTSTART;TZID=Europe/Stockholm:20260609T090000" in out
    assert "DTEND;TZID=Europe/Stockholm:20260611T180000" in out
    assert "SUMMARY:NetSec Summer School" in out
    assert "URL;VALUE=URI:https://example.com/event" in out


def test_render_vevent_escapes_summary():
    ev = make_event(summary="A, B; C")
    out = bc.render_vevent(ev, "STAMP", "Europe/Stockholm")
    assert "SUMMARY:A\\, B\\; C" in out


def test_render_vevent_optional_fields_omitted_by_default():
    ev = make_event()
    out = bc.render_vevent(ev, "STAMP", "Europe/Stockholm")
    assert not any(line.startswith("ORGANIZER") for line in out)
    assert not any(line.startswith("CATEGORIES") for line in out)
    assert not any(line.startswith("STATUS") for line in out)


def test_render_vevent_organizer():
    ev = make_event(organizer={"cn": "NetSec School", "mailto": "x@example.com"})
    out = bc.render_vevent(ev, "STAMP", "Europe/Stockholm")
    assert "ORGANIZER;CN=NetSec School:mailto:x@example.com" in out


def test_render_vevent_organizer_cn_escaped():
    ev = make_event(organizer={"cn": "A, B", "mailto": "x@example.com"})
    out = bc.render_vevent(ev, "STAMP", "Europe/Stockholm")
    assert "ORGANIZER;CN=A\\, B:mailto:x@example.com" in out


def test_render_vevent_categories_joined_and_escaped():
    ev = make_event(categories=["Training, School", "NetSec"])
    out = bc.render_vevent(ev, "STAMP", "Europe/Stockholm")
    # per-item escaping, joined by literal comma separator
    assert "CATEGORIES:Training\\, School,NetSec" in out


def test_render_vevent_empty_categories_omitted():
    ev = make_event(categories=[])
    out = bc.render_vevent(ev, "STAMP", "Europe/Stockholm")
    assert not any(line.startswith("CATEGORIES") for line in out)


def test_render_vevent_status():
    ev = make_event(status="CONFIRMED")
    out = bc.render_vevent(ev, "STAMP", "Europe/Stockholm")
    assert "STATUS:CONFIRMED" in out


def test_render_vevent_status_not_escaped():
    # STATUS is emitted verbatim (no escape_text call). Document the
    # current behaviour even for an odd value with a comma.
    ev = make_event(status="A,B")
    out = bc.render_vevent(ev, "STAMP", "Europe/Stockholm")
    assert "STATUS:A,B" in out


# ─── build_ics ────────────────────────────────────────────────────

def test_build_ics_envelope():
    out = bc.build_ics(make_data())
    assert out.startswith("BEGIN:VCALENDAR\n")
    assert out.endswith("END:VCALENDAR\n")
    assert "VERSION:2.0" in out
    assert "PRODID:-//NetSec//CA24154 Events//EN" in out


def test_build_ics_includes_refresh_interval():
    out = bc.build_ics(make_data(refresh_days=7))
    assert "REFRESH-INTERVAL;VALUE=DURATION:P7D" in out
    assert "X-PUBLISHED-TTL:P7D" in out


def test_build_ics_calname_escaped():
    out = bc.build_ics(make_data(calname="NetSec, COST"))
    assert "X-WR-CALNAME:NetSec\\, COST" in out


def test_build_ics_includes_vtimezone_and_events():
    out = bc.build_ics(make_data())
    assert "BEGIN:VTIMEZONE" in out
    assert "BEGIN:VEVENT" in out


def test_build_ics_multiple_events():
    events = [
        make_event(uid="a@netsec-cost.eu"),
        make_event(uid="b@netsec-cost.eu"),
    ]
    out = bc.build_ics(make_data(events=events))
    assert out.count("BEGIN:VEVENT") == 2


def test_build_ics_trailing_newline():
    out = bc.build_ics(make_data())
    assert out.endswith("\n")
    # exactly one trailing newline
    assert not out.endswith("\n\n")


# ─── build_single_event_ics ───────────────────────────────────────

def test_build_single_event_ics_no_refresh_interval():
    out = bc.build_single_event_ics(make_event(), make_data())
    assert "REFRESH-INTERVAL" not in out
    assert "X-PUBLISHED-TTL" not in out


def test_build_single_event_ics_has_vtimezone_and_one_event():
    out = bc.build_single_event_ics(make_event(), make_data())
    assert "BEGIN:VTIMEZONE" in out
    assert out.count("BEGIN:VEVENT") == 1
    assert out.startswith("BEGIN:VCALENDAR\n")
    assert out.endswith("END:VCALENDAR\n")


def test_build_single_event_ics_no_calname_headers():
    # Single-event files skip the X-WR-CALNAME / CALDESC headers.
    out = bc.build_single_event_ics(make_event(), make_data())
    assert "X-WR-CALNAME" not in out
    assert "X-WR-CALDESC" not in out


# ─── per_event_targets ────────────────────────────────────────────

def test_per_event_targets_paths_and_content():
    data = make_data(events=[
        make_event(uid="essc-2026@netsec-cost.eu"),
        make_event(uid="summer-school-2026@netsec-cost.eu"),
    ])
    targets = bc.per_event_targets(data)
    names = {p.name for p in targets}
    assert names == {"essc-2026.ics", "summer-school-2026.ics"}
    for path, content in targets.items():
        assert content.startswith("BEGIN:VCALENDAR\n")
        assert path.parent == bc.CALENDAR_DIR


def test_per_event_targets_bad_uid_raises():
    data = make_data(events=[make_event(uid="Bad_UID@netsec-cost.eu")])
    with pytest.raises(ValueError):
        bc.per_event_targets(data)


# ─── main() integration ───────────────────────────────────────────

@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Redirect all module path constants into tmp_path."""
    root = tmp_path
    data_dir = root / "data"
    data_dir.mkdir()
    events = data_dir / "events.json"
    ics = root / "calendar.ics"
    cal_dir = root / "calendar"

    monkeypatch.setattr(bc, "ROOT", root)
    monkeypatch.setattr(bc, "EVENTS", events)
    monkeypatch.setattr(bc, "ICS", ics)
    monkeypatch.setattr(bc, "CALENDAR_DIR", cal_dir)

    return {
        "root": root,
        "events": events,
        "ics": ics,
        "cal_dir": cal_dir,
    }


def write_events(sandbox, data):
    sandbox["events"].write_text(json.dumps(data), encoding="utf-8")


def test_main_write_creates_files(sandbox, monkeypatch):
    data = make_data(events=[
        make_event(uid="essc-2026@netsec-cost.eu"),
        make_event(uid="summer-school-2026@netsec-cost.eu"),
    ])
    write_events(sandbox, data)
    monkeypatch.setattr(bc.sys, "argv", ["build-calendar.py"])

    rc = bc.main()
    assert rc == 0
    assert sandbox["ics"].exists()
    assert (sandbox["cal_dir"] / "essc-2026.ics").exists()
    assert (sandbox["cal_dir"] / "summer-school-2026.ics").exists()


def test_main_check_passes_when_in_sync(sandbox, monkeypatch):
    data = make_data()
    write_events(sandbox, data)

    # First write everything out.
    monkeypatch.setattr(bc.sys, "argv", ["build-calendar.py"])
    assert bc.main() == 0

    # Now --check should report in-sync.
    monkeypatch.setattr(bc.sys, "argv", ["build-calendar.py", "--check"])
    assert bc.main() == 0


def test_main_check_detects_aggregate_drift(sandbox, monkeypatch, capsys):
    data = make_data()
    write_events(sandbox, data)

    monkeypatch.setattr(bc.sys, "argv", ["build-calendar.py"])
    assert bc.main() == 0

    # Corrupt the committed aggregate.
    sandbox["ics"].write_text("BEGIN:VCALENDAR\nEND:VCALENDAR\n", encoding="utf-8")

    monkeypatch.setattr(bc.sys, "argv", ["build-calendar.py", "--check"])
    assert bc.main() == 1
    err = capsys.readouterr().err
    assert "calendar.ics out of sync" in err


def test_main_check_detects_missing_per_event(sandbox, monkeypatch, capsys):
    data = make_data()
    write_events(sandbox, data)
    # Write only the aggregate by hand; no per-event files exist yet.
    sandbox["ics"].write_text(bc.build_ics(data), encoding="utf-8")

    monkeypatch.setattr(bc.sys, "argv", ["build-calendar.py", "--check"])
    assert bc.main() == 1
    err = capsys.readouterr().err
    assert "out of sync" in err


def test_main_check_detects_stale_file(sandbox, monkeypatch, capsys):
    data = make_data()
    write_events(sandbox, data)

    monkeypatch.setattr(bc.sys, "argv", ["build-calendar.py"])
    assert bc.main() == 0

    # Plant a stale per-event file not referenced by any event.
    stale = sandbox["cal_dir"] / "removed-event.ics"
    stale.write_text("BEGIN:VCALENDAR\n", encoding="utf-8")

    monkeypatch.setattr(bc.sys, "argv", ["build-calendar.py", "--check"])
    assert bc.main() == 1
    err = capsys.readouterr().err
    assert "stale" in err


def test_main_write_removes_stale(sandbox, monkeypatch):
    data = make_data()
    write_events(sandbox, data)

    monkeypatch.setattr(bc.sys, "argv", ["build-calendar.py"])
    assert bc.main() == 0

    stale = sandbox["cal_dir"] / "removed-event.ics"
    stale.write_text("BEGIN:VCALENDAR\n", encoding="utf-8")
    assert stale.exists()

    # Re-run write; stale file should be unlinked.
    assert bc.main() == 0
    assert not stale.exists()


def test_main_write_then_check_roundtrip_clean(sandbox, monkeypatch):
    # The canonical CI invariant: write, then --check is green.
    data = make_data(events=[
        make_event(uid="a@netsec-cost.eu", categories=["X"], status="CONFIRMED"),
        make_event(uid="b@netsec-cost.eu",
                   organizer={"cn": "Org", "mailto": "o@e.com"}),
    ])
    write_events(sandbox, data)

    monkeypatch.setattr(bc.sys, "argv", ["build-calendar.py"])
    assert bc.main() == 0
    monkeypatch.setattr(bc.sys, "argv", ["build-calendar.py", "--check"])
    assert bc.main() == 0


# ─── per-event time zones ─────────────────────────────────────────

def test_event_without_a_tzid_takes_the_calendar_default():
    assert bc.event_tzid(make_event(), "Europe/Stockholm") == "Europe/Stockholm"


def test_event_tzid_wins_over_the_calendar_default():
    ev = make_event(tzid="Europe/Istanbul")
    assert bc.event_tzid(ev, "Europe/Stockholm") == "Europe/Istanbul"


def test_vevent_stamps_the_events_own_zone():
    """The Ankara policy workshop starts at 09:00 local. Emitted under the
    calendar-wide Europe/Stockholm it resolved to 10:00 Ankara, an hour
    late for anyone who added it to their calendar."""
    ev = make_event(tzid="Europe/Istanbul", start="2026-09-13T09:00",
                    end="2026-09-13T18:00")
    lines = bc.render_vevent(ev, "20260528T120000Z", "Europe/Stockholm")
    assert "DTSTART;TZID=Europe/Istanbul:20260913T090000" in lines
    assert "DTEND;TZID=Europe/Istanbul:20260913T180000" in lines
    assert not [ln for ln in lines if "Europe/Stockholm" in ln]


def test_aggregate_inlines_a_vtimezone_for_every_zone_used():
    """Every TZID an event references has to resolve inside the file, or a
    calendar client falls back to its own guess."""
    data = make_data(events=[
        make_event(uid="a@netsec-cost.eu"),
        make_event(uid="b@netsec-cost.eu", tzid="Europe/Istanbul"),
    ])
    ics = bc.build_ics(data)
    assert "TZID:Europe/Stockholm" in ics
    assert "TZID:Europe/Istanbul" in ics
    assert ics.count("BEGIN:VTIMEZONE") == 2


def test_aggregate_does_not_repeat_a_zone_two_events_share():
    data = make_data(events=[
        make_event(uid="a@netsec-cost.eu", tzid="Europe/Istanbul"),
        make_event(uid="b@netsec-cost.eu", tzid="Europe/Istanbul"),
    ])
    ics = bc.build_ics(data)
    assert ics.count("BEGIN:VTIMEZONE") == 2  # the default plus Istanbul, once


def test_single_event_file_carries_only_its_own_zone():
    data = make_data()
    ev = make_event(tzid="Europe/Istanbul")
    ics = bc.build_single_event_ics(ev, data)
    assert "TZID:Europe/Istanbul" in ics
    assert "Europe/Stockholm" not in ics


def test_unknown_zone_is_refused_rather_than_guessed():
    with pytest.raises(SystemExit):
        bc.render_vtimezone("Mars/Olympus_Mons")
