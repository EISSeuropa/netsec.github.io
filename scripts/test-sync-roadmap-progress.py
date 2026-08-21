#!/usr/bin/env python3
"""Pytest suite for scripts/sync-roadmap-progress.py.

The filename is hyphenated, so it is loaded via importlib from a path
relative to this test file. The script's only side effects are a gh
subprocess call (fetch_milestones) and a write to the module-level OUT
path; both are monkeypatched so no test hits the network or touches a
tracked repo file.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_MODULE_PATH = Path(__file__).resolve().parent / "sync-roadmap-progress.py"


def _load():
    spec = importlib.util.spec_from_file_location("sync_roadmap_progress", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


srp = _load()


def _ms(title, closed=0, opened=0, state="open", due="2026-07-06T00:00:00Z"):
    return {
        "title": title,
        "closed_issues": closed,
        "open_issues": opened,
        "state": state,
        "due_on": due,
    }


# ───────────────────────── build(): filtering ─────────────────────────

def test_build_keeps_only_version_titles():
    ms = [
        _ms("v1.11.0", closed=2, opened=5),
        _ms("Backlog — Under watch", closed=1, opened=9),
        _ms("Year 1 wrap-up"),
        _ms("v1.12.0", closed=0, opened=1),
    ]
    out = srp.build(ms, "2026-06-02")
    assert set(out["milestones"]) == {"v1.11.0", "v1.12.0"}


def test_build_keeps_event_cycle_titles():
    ms = [
        _ms("ESSC 2027: call for papers", closed=1, opened=4),
        _ms("Backlog — Under watch", closed=1, opened=9),
        _ms("Directory Page and Workflow"),
    ]
    out = srp.build(ms, "2026-08-21")
    assert set(out["milestones"]) == {"ESSC 2027: call for papers"}


def test_build_sorts_releases_before_events_and_events_by_due():
    ms = [
        _ms("ESSC 2027: conference", due="2027-06-11T00:00:00Z"),
        _ms("v1.15.0", due="2026-12-08T00:00:00Z"),
        _ms("ESSC 2027: save the date", due="2026-09-30T00:00:00Z"),
    ]
    out = srp.build(ms, "2026-08-21")
    assert list(out["milestones"]) == [
        "v1.15.0", "ESSC 2027: save the date", "ESSC 2027: conference",
    ]


def test_build_rejects_two_component_version():
    out = srp.build([_ms("v1.11")], "2026-06-02")
    assert out["milestones"] == {}


def test_build_rejects_empty_and_none_title():
    out = srp.build([_ms(""), {"closed_issues": 1, "open_issues": 0}], "2026-06-02")
    assert out["milestones"] == {}


# ───────────────────────── build(): metrics ───────────────────────────

def test_build_percent_rounds_half_up_proxy():
    # 2 of 7 closed -> round(28.57) -> 29 (GitHub's milestone metric).
    out = srp.build([_ms("v1.11.0", closed=2, opened=5)], "2026-06-02")
    assert out["milestones"]["v1.11.0"]["percent"] == 29


def test_build_percent_none_when_no_issues():
    out = srp.build([_ms("v2.0.0", closed=0, opened=0)], "2026-06-02")
    entry = out["milestones"]["v2.0.0"]
    assert entry["percent"] is None
    assert entry["total"] == 0


def test_build_total_is_open_plus_closed():
    out = srp.build([_ms("v1.11.0", closed=3, opened=4)], "2026-06-02")
    assert out["milestones"]["v1.11.0"]["total"] == 7
    assert out["milestones"]["v1.11.0"]["closed"] == 3


def test_build_full_progress_is_100():
    out = srp.build([_ms("v1.11.0", closed=5, opened=0)], "2026-06-02")
    assert out["milestones"]["v1.11.0"]["percent"] == 100


# ───────────────────────── build(): due + state ───────────────────────

def test_build_due_truncated_to_date():
    out = srp.build([_ms("v1.11.0", due="2026-07-06T00:00:00Z")], "2026-06-02")
    assert out["milestones"]["v1.11.0"]["due"] == "2026-07-06"


def test_build_due_none_when_absent():
    out = srp.build([_ms("v1.11.0", due=None)], "2026-06-02")
    assert out["milestones"]["v1.11.0"]["due"] is None


def test_build_due_empty_string_becomes_none():
    out = srp.build([_ms("v1.11.0", due="")], "2026-06-02")
    assert out["milestones"]["v1.11.0"]["due"] is None


def test_build_state_passthrough():
    out = srp.build([_ms("v1.10.0", state="closed"), _ms("v1.11.0", state="open")], "2026-06-02")
    assert out["milestones"]["v1.10.0"]["state"] == "closed"
    assert out["milestones"]["v1.11.0"]["state"] == "open"


# ───────────────────────── build(): ordering + envelope ───────────────

def test_build_sorts_versions_numerically_not_lexically():
    # Lexical sort would place v1.10.0 before v1.2.0; numeric must not.
    ms = [_ms("v1.10.0"), _ms("v1.2.0"), _ms("v1.9.0"), _ms("v2.0.0")]
    out = srp.build(ms, "2026-06-02")
    assert list(out["milestones"]) == ["v1.2.0", "v1.9.0", "v1.10.0", "v2.0.0"]


def test_build_envelope_fields():
    out = srp.build([_ms("v1.11.0")], "2026-06-02")
    assert out["generatedAt"] == "2026-06-02"
    assert "_documentation" in out
    assert out["source"].endswith("/milestones")
    assert "EISSeuropa/netsec.github.io" in out["source"]


# ───────────────────────── _data_only ─────────────────────────────────

def test_data_only_returns_milestones():
    payload = {"generatedAt": "x", "milestones": {"v1.11.0": {"closed": 1}}}
    assert srp._data_only(payload) == {"v1.11.0": {"closed": 1}}


def test_data_only_missing_key_returns_empty():
    assert srp._data_only({"generatedAt": "x"}) == {}


# ───────────────────────── main(): write / idempotency ────────────────

@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    out = tmp_path / "roadmap-progress.json"
    monkeypatch.setattr(srp, "OUT", out)
    return out


def test_main_writes_when_file_absent(sandbox, monkeypatch):
    monkeypatch.setattr(srp, "fetch_milestones", lambda: [_ms("v1.11.0", closed=2, opened=5)])
    rc = srp.main()
    assert rc == 0
    assert sandbox.exists()
    data = json.loads(sandbox.read_text())
    assert data["milestones"]["v1.11.0"]["percent"] == 29


def test_main_idempotent_no_rewrite_when_data_unchanged(sandbox, monkeypatch):
    monkeypatch.setattr(srp, "fetch_milestones", lambda: [_ms("v1.11.0", closed=2, opened=5)])
    srp.main()
    # Hand-edit generatedAt to an old date; a re-run with identical
    # milestone data must NOT rewrite the file (data-only comparison).
    payload = json.loads(sandbox.read_text())
    payload["generatedAt"] = "2000-01-01"
    sandbox.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    before = sandbox.read_text()
    rc = srp.main()
    assert rc == 0
    assert sandbox.read_text() == before  # untouched, stale date preserved


def test_main_rewrites_when_data_changes(sandbox, monkeypatch):
    monkeypatch.setattr(srp, "fetch_milestones", lambda: [_ms("v1.11.0", closed=2, opened=5)])
    srp.main()
    monkeypatch.setattr(srp, "fetch_milestones", lambda: [_ms("v1.11.0", closed=3, opened=4)])
    srp.main()
    data = json.loads(sandbox.read_text())
    assert data["milestones"]["v1.11.0"]["closed"] == 3


def test_main_corrupt_existing_file_is_treated_as_empty(sandbox, monkeypatch):
    sandbox.write_text("{ not json")
    monkeypatch.setattr(srp, "fetch_milestones", lambda: [_ms("v1.11.0", closed=1, opened=1)])
    rc = srp.main()
    assert rc == 0
    assert json.loads(sandbox.read_text())["milestones"]["v1.11.0"]["closed"] == 1
