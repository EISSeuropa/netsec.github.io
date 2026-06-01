"""Tests for scripts/rotate-spotlight.py.

The module name contains a hyphen, so it cannot be imported by name; it is
loaded from its relative path via importlib. All file IO in the tests uses
tmp_path; no tracked repo file is read or mutated, and there are no network
or subprocess side-effects (the script itself makes none).
"""
from __future__ import annotations

import importlib.util
import json
from datetime import date
from pathlib import Path

import pytest

# --- load the hyphenated module under test --------------------------------

_HERE = Path(__file__).resolve().parent
_MODULE_PATH = _HERE / "rotate-spotlight.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("rotate_spotlight", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rs = _load_module()


# --- helpers --------------------------------------------------------------

def member(mid, **kw):
    m = {
        "id": mid,
        "name": kw.get("name", f"Name {mid}"),
        "position": kw.get("position", "Researcher"),
        "photo": kw.get("photo", "photo.jpg"),
        "bio": kw.get("bio", "A bio."),
        "country_code": kw.get("country_code", "de"),
        "wgs": kw.get("wgs", [1]),
    }
    # allow explicit override to remove keys / set falsy
    for k, v in kw.items():
        m[k] = v
    return m


def pool(n, **kw):
    """n eligible members with distinct ids."""
    return [member(f"m{i}", **kw) for i in range(n)]


# --- career_stage ---------------------------------------------------------

def test_career_stage_senior_by_name_prefix():
    assert rs.career_stage("Prof. Jane Doe", "Researcher") == "senior"


def test_career_stage_senior_by_position_keywords():
    for pos in ["Full Professor", "Professeur", "Head of Lab", "Director",
                "Directeur de recherche", "Dean of Science", "Emeritus"]:
        assert rs.career_stage("Jane Doe", pos) == "senior", pos


def test_career_stage_early_by_position():
    for pos in ["PhD candidate", "PhD student", "Postdoc", "post-doc",
                "Doctoral researcher", "Doctorant", "Early-career fellow",
                "Junior analyst"]:
        assert rs.career_stage("Jane Doe", pos) == "early", pos


def test_career_stage_neutral_default():
    assert rs.career_stage("Jane Doe", "Research Engineer") == "neutral"


def test_career_stage_senior_wins_over_early_when_both_present():
    # name prefix triggers senior even if position would read early.
    assert rs.career_stage("Prof. Doe", "Postdoc") == "senior"
    # position senior keyword also wins (checked before early branch).
    assert rs.career_stage("Doe", "Professor and postdoc supervisor") == "senior"


def test_career_stage_handles_none_inputs():
    assert rs.career_stage(None, None) == "neutral"


def test_career_stage_prof_must_be_at_start_for_name_rule():
    # "prof" mid-name should not trigger the name rule (it anchors at ^).
    assert rs.career_stage("Jane Proffit", "Engineer") == "neutral"


# --- is_eligible ----------------------------------------------------------

def test_is_eligible_true_with_photo_and_bio():
    assert rs.is_eligible(member("x")) is True


def test_is_eligible_false_missing_photo():
    assert rs.is_eligible(member("x", photo="")) is False
    assert rs.is_eligible(member("x", photo="   ")) is False


def test_is_eligible_false_missing_bio():
    assert rs.is_eligible(member("x", bio="")) is False
    assert rs.is_eligible(member("x", bio="  \n ")) is False


def test_is_eligible_handles_missing_keys_and_none():
    assert rs.is_eligible({}) is False
    assert rs.is_eligible({"photo": None, "bio": None}) is False


# --- week_key -------------------------------------------------------------

def test_week_key_format_and_value():
    # 2026-06-01 is ISO week 23 of 2026.
    assert rs.week_key(date(2026, 6, 1)) == "2026-W23"


def test_week_key_zero_pads_week():
    # Early January, week 1.
    assert rs.week_key(date(2026, 1, 5)) == "2026-W02"
    assert rs.week_key(date(2025, 1, 1)) == "2025-W01"


def test_week_key_iso_year_can_differ_from_calendar_year():
    # 2026-12-31 falls in ISO week 53 of 2026.
    assert rs.week_key(date(2026, 12, 31)) == "2026-W53"


# --- _jitter --------------------------------------------------------------

def test_jitter_range():
    for mid in ["a", "member-42", "", "zzz"]:
        for wk in ["2026-W01", "2026-W23"]:
            j = rs._jitter(mid, wk)
            assert 0.0 <= j < 0.5


def test_jitter_deterministic_same_inputs():
    assert rs._jitter("m1", "2026-W23") == rs._jitter("m1", "2026-W23")


def test_jitter_varies_by_week():
    # Same member, different weeks -> generally different jitter.
    vals = {rs._jitter("m1", f"2026-W{w:02d}") for w in range(1, 40)}
    assert len(vals) > 1


# --- _score ---------------------------------------------------------------

def test_score_early_career_boost_vs_senior_penalty():
    w = dict(rs.DEFAULT_WEIGHTS)
    early = member("e", position="Postdoc", country_code="xx", wgs=[])
    senior = member("s", position="Professor", country_code="xx", wgs=[])
    s_early = rs._score(early, "2026-W23", set(), {}, w)
    s_senior = rs._score(senior, "2026-W23", set(), {}, w)
    # early gets +2.0 (minus jitter offset cancels roughly); senior -1.5.
    assert s_early > s_senior


def test_score_itc_boost_applied():
    w = dict(rs.DEFAULT_WEIGHTS)
    m_itc = member("a", position="Engineer", country_code="pl", wgs=[])
    m_non = member("a", position="Engineer", country_code="de", wgs=[])
    # Same id+week -> same jitter, so the delta is purely the ITC weight.
    delta = rs._score(m_itc, "2026-W23", {"pl"}, {}, w) - rs._score(
        m_non, "2026-W23", set(), {}, w
    )
    assert delta == pytest.approx(w["itc"])


def test_score_wg_balance_favours_underrepresented():
    w = dict(rs.DEFAULT_WEIGHTS)
    fresh = member("a", position="Engineer", country_code="xx", wgs=[1])
    seen = member("a", position="Engineer", country_code="xx", wgs=[1])
    # WG 1 already featured 5 times -> lower boost than an unseen WG.
    s_fresh = rs._score(fresh, "2026-W23", set(), {}, w)
    s_seen = rs._score(seen, "2026-W23", set(), {1: 5}, w)
    assert s_fresh > s_seen


def test_score_wg_boost_averages_over_multiple_wgs():
    w = dict(rs.DEFAULT_WEIGHTS)
    m = member("a", position="Engineer", country_code="xx", wgs=[1, 2])
    counts = {1: 0, 2: 0}
    s = rs._score(m, "2026-W23", set(), counts, w)
    expected_jitter = rs._jitter("a", "2026-W23")
    # both WGs unseen -> boost == w["wg"] * (1+1)/2 == w["wg"].
    assert s - expected_jitter == pytest.approx(w["wg"])


# --- rotate: dormancy -----------------------------------------------------

def test_rotate_dormant_below_threshold():
    bios = {"members": pool(3)}
    state = {}
    new_state, changed, log = rs.rotate(bios, state, date(2026, 6, 1))
    assert new_state["active"] is False
    assert new_state["current"] is None
    assert new_state["featuredSince"] is None
    assert changed is True
    assert any("dormant" in line.lower() for line in log)


def test_rotate_dormant_respects_custom_min_eligible():
    bios = {"members": pool(5)}
    state = {"minEligible": 4}
    new_state, changed, log = rs.rotate(bios, state, date(2026, 6, 1))
    # 5 eligible >= 4 -> should feature someone, not go dormant.
    assert new_state["active"] is True
    assert new_state["current"] is not None


def test_rotate_dormant_no_change_when_already_dormant():
    bios = {"members": pool(2)}
    state = {"active": False, "current": None, "featuredSince": None,
             "pinned": None, "history": []}
    new_state, changed, log = rs.rotate(bios, state, date(2026, 6, 1))
    assert changed is False


def test_rotate_ineligible_members_excluded_from_count():
    # 12 members but only 3 have photo+bio -> dormant at default threshold.
    elig = pool(3)
    inelig = [member(f"x{i}", photo="") for i in range(9)]
    bios = {"members": elig + inelig}
    new_state, changed, log = rs.rotate(bios, {}, date(2026, 6, 1))
    assert new_state["active"] is False
    assert "3 eligible of 12" in log[0]


# --- rotate: normal selection ---------------------------------------------

def test_rotate_features_a_member_when_pool_sufficient():
    bios = {"members": pool(10)}
    new_state, changed, log = rs.rotate(bios, {}, date(2026, 6, 1))
    assert new_state["active"] is True
    assert new_state["current"] in {m["id"] for m in bios["members"]}
    assert new_state["featuredSince"] == "2026-06-01"
    assert changed is True


def test_rotate_writes_history_entry():
    bios = {"members": pool(10)}
    new_state, _, _ = rs.rotate(bios, {}, date(2026, 6, 1))
    hist = new_state["history"]
    assert hist[0]["week"] == "2026-W23"
    assert hist[0]["date"] == "2026-06-01"
    assert hist[0]["id"] == new_state["current"]


def test_rotate_is_deterministic():
    bios = {"members": pool(10)}
    s1, _, _ = rs.rotate(bios, {}, date(2026, 6, 1))
    s2, _, _ = rs.rotate(bios, {}, date(2026, 6, 1))
    assert s1["current"] == s2["current"]


def test_rotate_does_not_mutate_input_state():
    bios = {"members": pool(10)}
    state = {"history": []}
    rs.rotate(bios, state, date(2026, 6, 1))
    assert state == {"history": []}


def test_rotate_prefers_early_itc_member():
    # One stand-out candidate: early-career + ITC + only one WG that is unseen.
    members = pool(9, position="Professor", country_code="de", wgs=[1])
    star = member("star", position="Postdoc", country_code="pl", wgs=[2])
    bios = {"members": members + [star]}
    new_state, _, _ = rs.rotate(bios, {}, date(2026, 6, 1))
    assert new_state["current"] == "star"


# --- rotate: same-week no-op ----------------------------------------------

def test_rotate_no_op_same_week_when_current_still_eligible():
    bios = {"members": pool(10)}
    first, _, _ = rs.rotate(bios, {}, date(2026, 6, 1))
    # Re-run in same week with the produced state.
    second, changed, log = rs.rotate(bios, first, date(2026, 6, 2))
    assert changed is False
    assert second["current"] == first["current"]
    assert any("no change" in line.lower() for line in log)


def test_rotate_refreshes_if_current_became_ineligible_same_week():
    bios = {"members": pool(10)}
    first, _, _ = rs.rotate(bios, {}, date(2026, 6, 1))
    cur = first["current"]
    # Strip the current member's photo -> ineligible.
    for m in bios["members"]:
        if m["id"] == cur:
            m["photo"] = ""
    second, changed, _ = rs.rotate(bios, first, date(2026, 6, 2))
    assert changed is True
    assert second["current"] != cur


# --- rotate: pinned override ----------------------------------------------

def test_rotate_pinned_override_features_pinned_and_consumes_pin():
    bios = {"members": pool(10)}
    state = {"pinned": "m7", "history": []}
    new_state, changed, log = rs.rotate(bios, state, date(2026, 6, 1))
    assert new_state["current"] == "m7"
    assert new_state["pinned"] is None  # consumed
    assert changed is True
    assert any("pinned override" in line.lower() for line in log)


def test_rotate_pinned_ignored_when_ineligible():
    members = pool(10)
    members.append(member("ghost", photo=""))  # ineligible
    bios = {"members": members}
    state = {"pinned": "ghost", "history": []}
    new_state, _, log = rs.rotate(bios, state, date(2026, 6, 1))
    assert new_state["current"] != "ghost"
    assert any("ignoring pin" in line.lower() for line in log)


def test_rotate_pin_consumed_even_on_normal_selection():
    bios = {"members": pool(10)}
    state = {"pinned": "nonexistent", "history": []}
    new_state, _, _ = rs.rotate(bios, state, date(2026, 6, 1))
    # pin pointed at unknown id -> ignored, normal pick, pin cleared.
    assert new_state["pinned"] is None


# --- rotate: recency window -----------------------------------------------

def test_rotate_holds_out_recently_featured():
    bios = {"members": pool(10)}
    # Build a history where m0..m5 were featured recently (window default 6),
    # all in past weeks so the same-week no-op does not trigger.
    history = [
        {"id": f"m{i}", "week": f"2026-W{17 + i:02d}", "date": "2026-04-01"}
        for i in range(6)
    ]
    state = {"history": history, "current": "m5"}
    new_state, _, _ = rs.rotate(bios, state, date(2026, 6, 1))
    # Chosen must be outside the recency window {m0..m5}.
    assert new_state["current"] not in {f"m{i}" for i in range(6)}


def test_rotate_recency_never_empties_pool():
    # Exactly minEligible members, all in recent history -> pool would be
    # empty; the code falls back to the full eligible list.
    bios = {"members": pool(10)}
    history = [
        {"id": f"m{i}", "week": f"2026-W{10 + i:02d}", "date": "2026-03-01"}
        for i in range(10)
    ]
    state = {"history": history, "current": "m9"}
    new_state, changed, _ = rs.rotate(bios, state, date(2026, 6, 1))
    assert new_state["current"] is not None
    assert changed is True


def test_rotate_history_dedup_on_same_week_and_capped_at_52():
    bios = {"members": pool(10)}
    # 60 past-week history entries plus one stale same-week entry to dedup.
    history = [{"id": "stale", "week": "2026-W23", "date": "2026-06-01"}]
    history += [
        {"id": f"old{i}", "week": f"2025-W{(i % 52) + 1:02d}", "date": "2025-01-01"}
        for i in range(60)
    ]
    state = {"history": history, "current": "someoneelse"}
    new_state, _, _ = rs.rotate(bios, state, date(2026, 6, 1))
    weeks = [h["week"] for h in new_state["history"]]
    # Only one entry for the current week (the new one, stale removed).
    assert weeks.count("2026-W23") == 1
    assert new_state["history"][0]["id"] == new_state["current"]
    assert len(new_state["history"]) <= 52


# --- rotate: custom weights -----------------------------------------------

def test_rotate_custom_weights_merge_over_defaults():
    bios = {"members": pool(10)}
    state = {"weights": {"itc": 99.0}, "history": []}
    # An ITC member should dominate with a huge itc weight.
    bios["members"].append(member("itcwin", country_code="pl", wgs=[]))
    state2 = {"weights": {"itc": 99.0}, "history": []}
    new_state, _, _ = rs.rotate(bios, state2, date(2026, 6, 1))
    assert new_state["current"] == "itcwin"


# --- main() integration (file IO via monkeypatched module paths) ----------

def test_main_writes_state_file(tmp_path, monkeypatch, capsys):
    bios_path = tmp_path / "bios.json"
    state_path = tmp_path / "spotlight.json"
    bios_path.write_text(json.dumps({"members": [member(f"m{i}") for i in range(10)]}))
    monkeypatch.setattr(rs, "BIOS", bios_path)
    monkeypatch.setattr(rs, "STATE", state_path)
    monkeypatch.setattr(rs, "ROOT", tmp_path)

    rs.main()

    assert state_path.exists()
    written = json.loads(state_path.read_text())
    assert written["active"] is True
    assert written["current"] is not None


def test_main_no_state_file_treated_as_empty(tmp_path, monkeypatch, capsys):
    bios_path = tmp_path / "bios.json"
    state_path = tmp_path / "spotlight.json"
    # Only 2 eligible -> dormant; with no prior state file the dormant
    # commit is still a change (active flips to False from absent).
    bios_path.write_text(json.dumps({"members": [member(f"m{i}") for i in range(2)]}))
    monkeypatch.setattr(rs, "BIOS", bios_path)
    monkeypatch.setattr(rs, "STATE", state_path)
    monkeypatch.setattr(rs, "ROOT", tmp_path)

    rs.main()
    out = capsys.readouterr().out
    assert "dormant" in out.lower()


def test_main_writes_pr_helper_files(tmp_path, monkeypatch):
    bios_path = tmp_path / "bios.json"
    state_path = tmp_path / "spotlight.json"
    title_path = tmp_path / "title.txt"
    overview_path = tmp_path / "overview.md"
    bios_path.write_text(json.dumps({"members": [member(f"m{i}") for i in range(10)]}))
    monkeypatch.setattr(rs, "BIOS", bios_path)
    monkeypatch.setattr(rs, "STATE", state_path)
    monkeypatch.setattr(rs, "ROOT", tmp_path)
    monkeypatch.setenv("SPOTLIGHT_PR_TITLE_PATH", str(title_path))
    monkeypatch.setenv("SPOTLIGHT_PR_OVERVIEW_PATH", str(overview_path))

    rs.main()

    assert title_path.exists()
    assert overview_path.exists()
    assert "weekly member spotlight" in title_path.read_text()
    assert "Member spotlight rotation" in overview_path.read_text()
