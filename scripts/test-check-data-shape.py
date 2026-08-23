#!/usr/bin/env python3
"""Pytest suite for scripts/check-data-shape.py.

The module is loaded via importlib from its hyphenated path. The
per-file validators are pure functions over parsed JSON, so the tests
feed them minimal dicts; main() is exercised against the repo's real
data files (which must always validate, that is the point of the gate)
plus a tmp_path round-trip for the unparseable-JSON branch.

Run: python3 -m pytest scripts/test-check-data-shape.py -q
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("check_data_shape", HERE / "check-data-shape.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


# ── minimal valid fixtures ──────────────────────────────────────────

def valid_indico():
    return {
        "syncedAt": "2026-06-09T01:00:00Z",
        "annualConferences": {
            "2026": {
                "title": "ESSC 2026",
                "url": "https://indico.example/e/1",
                "programme": {
                    "days": [
                        {
                            "date": "2026-06-11",
                            "slots": [{"id": "s1", "kind": "session", "title": "Opening"}],
                            "rows": [],
                        }
                    ]
                },
            }
        },
    }


def valid_bios():
    return {"members": [{"id": "a-laudrain", "name": "Arthur Laudrain"}]}


def valid_events():
    return {
        "tzid": "Europe/Brussels",
        "events": [
            {
                "start": "2026-06-11T09:00:00",
                "end": "2026-06-12T18:00:00",
                "status": "confirmed",
                "eventType": "conference",
                "cardTitle": {"en": "ESSC 2026", "fr": "ESSC 2026", "de": "ESSC 2026"},
            }
        ],
    }


# ── indico ──────────────────────────────────────────────────────────

def test_indico_valid():
    assert mod.check_indico(valid_indico()) == []


def test_indico_empty_conferences():
    data = valid_indico()
    data["annualConferences"] = {}
    assert any("annualConferences" in e for e in mod.check_indico(data))


def test_indico_no_renderable_slots():
    data = valid_indico()
    data["annualConferences"]["2026"]["programme"]["days"][0]["slots"] = []
    errs = mod.check_indico(data)
    assert any("no renderable" in e for e in errs)


def test_indico_row_items_count_as_renderable():
    data = valid_indico()
    day = data["annualConferences"]["2026"]["programme"]["days"][0]
    day["slots"] = []
    day["rows"] = [{"parallel": True, "items": [{"id": "p1"}]}]
    assert mod.check_indico(data) == []


def test_indico_missing_programme_days():
    data = valid_indico()
    data["annualConferences"]["2026"]["programme"] = {"days": []}
    assert any("'days' is empty" in e for e in mod.check_indico(data))


def test_indico_not_a_dict():
    assert mod.check_indico([]) == ["indico: top level must be an object"]


# ── bios ────────────────────────────────────────────────────────────

def test_bios_valid():
    assert mod.check_bios(valid_bios()) == []


def test_bios_empty_members():
    assert any("'members' is empty" in e for e in mod.check_bios({"members": []}))


def test_bios_member_missing_name():
    errs = mod.check_bios({"members": [{"id": "x"}]})
    assert any("missing key 'name'" in e for e in errs)


def test_bios_member_blank_id():
    errs = mod.check_bios({"members": [{"id": "", "name": "X"}]})
    assert any("'id' is empty" in e for e in errs)


def test_bios_member_bare_handle_website_rejected():
    errs = mod.check_bios({"members": [{"id": "x", "name": "X", "website": "itsallcyber.baby"}]})
    assert any("'website' must be an absolute" in e for e in errs)


def test_bios_member_bare_bluesky_handle_rejected():
    errs = mod.check_bios({"members": [{"id": "x", "name": "X", "bluesky": "@handle.com"}]})
    assert any("'bluesky' must be an absolute" in e for e in errs)


def test_bios_member_absolute_links_pass():
    errs = mod.check_bios({"members": [{
        "id": "x", "name": "X",
        "website": "https://example.org",
        "bluesky": "https://bsky.app/profile/x.com",
        "linkedin": "", "mastodon": "",
    }]})
    assert errs == []


# ── wg / mc-members ─────────────────────────────────────────────────

def test_wg_valid():
    data = {"groups": [{"number": 1, "name": "WG1", "members": []}]}
    assert mod.check_wg(data) == []


def test_wg_group_missing_members_list():
    errs = mod.check_wg({"groups": [{"number": 1, "name": "WG1"}]})
    assert any("missing key 'members'" in e for e in errs)


def test_mc_members_valid():
    data = {"members": [{"name": "A B", "country": "Belgium"}]}
    assert mod.check_mc_members(data) == []


def test_mc_members_empty():
    assert any("'members' is empty" in e for e in mod.check_mc_members({"members": []}))


# ── events ──────────────────────────────────────────────────────────

def test_events_valid():
    assert mod.check_events(valid_events()) == []


def test_events_missing_card_title():
    data = valid_events()
    del data["events"][0]["cardTitle"]
    assert any("missing key 'cardTitle'" in e for e in mod.check_events(data))


def test_events_card_title_missing_en_fallback():
    data = valid_events()
    data["events"][0]["cardTitle"] = {"fr": "ESSC 2026"}
    assert any("cardTitle: missing key 'en'" in e for e in mod.check_events(data))


def test_events_missing_tzid():
    data = valid_events()
    del data["tzid"]
    assert any("missing key 'tzid'" in e for e in mod.check_events(data))


# ── roadmap-progress ────────────────────────────────────────────────

def test_roadmap_progress_valid():
    data = {"milestones": {"v1.12.0": {"closed": 17, "total": 17, "state": "open"}}}
    assert mod.check_roadmap_progress(data) == []


def test_roadmap_progress_bad_total_type():
    data = {"milestones": {"v1.12.0": {"closed": 1, "total": "17", "state": "open"}}}
    assert any("'total' should be int" in e for e in mod.check_roadmap_progress(data))


def test_spotlight_current_must_exist_in_bios():
    errs = mod.check_spotlight({"active": True, "current": "ghost-member", "history": []})
    assert any("not a member id" in e for e in errs)


def test_spotlight_valid_current_passes():
    # arthur-laudrain is a stable seed member id in the real bios.json.
    assert mod.check_spotlight(
        {"active": True, "current": "arthur-laudrain", "history": []}) == []


# ── main() against the real repo data ───────────────────────────────

def test_main_real_data_files_all_valid(capsys):
    assert mod.main([]) == 0
    out = capsys.readouterr().out
    assert out.count("✓") == len(mod.CHECKS)


def test_main_subset_selection(capsys):
    assert mod.main(["data/bios.json"]) == 0
    out = capsys.readouterr().out
    assert "✓ data/bios.json" in out
    assert "indico" not in out


def test_main_unknown_file_is_skipped_not_failed(capsys):
    assert mod.main(["data/unknown.json"]) == 0
    assert "skipping" in capsys.readouterr().out


def test_main_invalid_json(tmp_path, monkeypatch):
    repo = tmp_path
    (repo / "data").mkdir()
    (repo / "data" / "bios.json").write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(mod, "REPO", repo)
    assert mod.main(["data/bios.json"]) == 1


def test_main_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "REPO", tmp_path)
    assert mod.main(["data/bios.json"]) == 1


# ── Network Map edition fields (#1600) ───────────────────────────────

def valid_network_map():
    """Two people, one WG hub, and a panel tie between them at one edition."""
    return {
        "stats": {"panel_editions": ["2026"], "authors_unmatched": []},
        "nodes": [
            {"id": "wg-1", "type": "wg"},
            {"id": "ada-lovelace", "type": "person"},
            {"id": "alan-turing", "type": "person"},
        ],
        "edges": [
            {"source": "ada-lovelace", "target": "wg-1"},
            {"source": "ada-lovelace", "target": "alan-turing",
             "type": "panel", "weight": 1, "year": "2026"},
        ],
    }


def test_valid_network_map_passes():
    assert mod.check_network_map(valid_network_map()) == []


def test_panel_edge_without_a_year_is_caught():
    d = valid_network_map()
    del d["edges"][1]["year"]
    assert any("year" in e for e in mod.check_network_map(d))


def test_panel_year_must_be_a_string():
    """The renderer filters with strict equality against the strings in
    panel_editions, so an int year matches nothing and draws no arcs."""
    d = valid_network_map()
    d["edges"][1]["year"] = 2026
    assert any("year" in e for e in mod.check_network_map(d))


def test_panel_editions_must_match_the_edge_years():
    d = valid_network_map()
    d["stats"]["panel_editions"] = ["2026", "2027"]
    errs = mod.check_network_map(d)
    assert any("does not match the years" in e for e in errs)


def test_panel_editions_must_be_sorted():
    d = valid_network_map()
    d["edges"].append(dict(d["edges"][1], year="2027"))
    d["stats"]["panel_editions"] = ["2027", "2026"]
    assert any("must be sorted" in e for e in mod.check_network_map(d))


def test_authors_unmatched_must_be_sorted_strings():
    d = valid_network_map()
    d["stats"]["authors_unmatched"] = ["Zed A", "Ada B"]
    assert any("authors_unmatched" in e for e in mod.check_network_map(d))
    d["stats"]["authors_unmatched"] = [1, 2]
    assert any("authors_unmatched" in e for e in mod.check_network_map(d))


def test_stats_block_is_optional():
    """The pure build() path omits stats keys when its optional inputs are
    absent, and those graphs must still validate."""
    d = valid_network_map()
    del d["stats"]
    assert mod.check_network_map(d) == []
