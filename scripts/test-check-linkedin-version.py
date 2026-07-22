#!/usr/bin/env python3
"""Tests for scripts/check-linkedin-version.py (pure logic; no network)."""

import importlib.util
import json
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "check_linkedin_version",
    Path(__file__).resolve().parent / "check-linkedin-version.py",
)
clv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(clv)

# LinkedIn's real active window in mid-2026, deliberately including the gap at
# 202512 (LinkedIn skipped that month) so the tests exercise it.
ACTIVE = {
    "202508", "202509", "202510", "202511",
    "202601", "202602", "202603", "202604", "202605", "202606", "202607",
}


def test_latest_pin_is_left_alone():
    assert clv.decide_target("202607", ACTIVE) is None


def test_comfortably_current_pin_is_left_alone():
    # 202603 sits well inside the window, nowhere near the oldest two.
    assert clv.decide_target("202603", ACTIVE) is None


def test_sunset_pin_bumps_to_latest():
    # The actual bug: 202506 is long gone from the active set.
    assert clv.decide_target("202506", ACTIVE) == "202607"


def test_pin_among_the_two_oldest_bumps_early():
    assert clv.decide_target("202508", ACTIVE) == "202607"  # oldest
    assert clv.decide_target("202509", ACTIVE) == "202607"  # second oldest


def test_third_oldest_is_not_yet_bumped():
    assert clv.decide_target("202510", ACTIVE) is None


def test_gap_month_does_not_confuse_positioning():
    # 202512 is absent from LinkedIn's line; position logic must not care.
    assert "202512" not in ACTIVE
    assert clv.decide_target("202601", ACTIVE) is None  # comfortably mid-list


def test_empty_active_never_bumps():
    assert clv.decide_target("202506", set()) is None


def test_active_window_drops_historical_strays():
    # The real page leaves 202206/202207 in prose; they must not count as
    # active, or the "two oldest" early-bump logic anchors on 2022.
    parsed = ACTIVE | {"202206", "202207"}
    assert clv.active_window(parsed) == ACTIVE


def test_active_window_keeps_a_full_year():
    assert "202607" in clv.active_window(ACTIVE | {"202206"})
    assert "202508" in clv.active_window(ACTIVE | {"202206"})


def test_parse_versions_extracts_monikers():
    html = 'x li-lms-2026-07 y li-lms-2025-08 z li-lms-2026-07 q'
    assert clv.parse_versions(html) == {"202607", "202508"}


def test_windowed_strays_do_not_defeat_early_bump():
    # With 2022 strays filtered out, the real oldest (202508) is flagged early.
    active = clv.active_window(ACTIVE | {"202206", "202207"})
    assert clv.decide_target("202508", active) == "202607"


def test_write_pin_preserves_comment(tmp_path):
    f = tmp_path / "pin.json"
    f.write_text(json.dumps({"_comment": "keep me", "version": "202506"}), encoding="utf-8")
    clv.write_pin("202607", f)
    data = json.loads(f.read_text(encoding="utf-8"))
    assert data["version"] == "202607"
    assert data["_comment"] == "keep me"
    assert f.read_text(encoding="utf-8").endswith("\n")


def test_read_pin_round_trips(tmp_path):
    f = tmp_path / "pin.json"
    f.write_text(json.dumps({"version": "202606"}), encoding="utf-8")
    assert clv.read_pin(f) == "202606"


def test_committed_pin_file_is_valid_and_active():
    """The pin shipped in the repo must be a real, currently-active version.

    Guards against committing a typo'd or already-sunset pin. Uses the static
    ACTIVE window above rather than the network, so it stays offline; update
    ACTIVE when this list is refreshed."""
    pin = clv.read_pin()
    assert pin in ACTIVE, f"committed pin {pin} is not in the known active window"
