#!/usr/bin/env python3
"""Standalone tests for scripts/rotate-spotlight.py.

No network, no file IO: drives the pure `rotate()` core with synthetic
bios. Run: python3 scripts/test-spotlight.py
"""
from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "rotate_spotlight", Path(__file__).resolve().parent / "rotate-spotlight.py"
)
rs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rs)


def expect(label, got, want) -> None:
    if got != want:
        print(f"FAIL: {label}\n  got:  {got!r}\n  want: {want!r}", file=sys.stderr)
        sys.exit(1)
    print(f"  ok  {label}")


def expect_true(label, cond) -> None:
    expect(label, bool(cond), True)


def mk(mid, photo=True, bio=True, name="Dr Person", position="", wgs=None, cc="de"):
    return {
        "id": mid,
        "name": name,
        "photo": "p.jpg" if photo else "",
        "bio": "A bio." if bio else "",
        "position": position,
        "wgs": list(wgs or []),
        "country_code": cc,
    }


def pool(n, **kw):
    return {"members": [mk(f"m{i}", **kw) for i in range(n)]}


def base_state():
    return {"minEligible": 10, "active": False, "current": None, "history": [], "pinned": None}


TODAY = date(2026, 7, 6)  # a Monday


def test_career_stage():
    print("\ncareer_stage():")
    expect("Prof prefix -> senior", rs.career_stage("Prof Filip Ejdus", ""), "senior")
    expect("position professor -> senior", rs.career_stage("Dr X", "Professor of IR"), "senior")
    expect("PhD Researcher -> early", rs.career_stage("Mr E", "PhD Researcher"), "early")
    expect("PhD candidate -> early", rs.career_stage("Dr F", "PhD candidate; Research Fellow"), "early")
    expect("doctorant (FR) -> early", rs.career_stage("Dr Y", "doctorant en relations internationales"), "early")
    expect("senior lecturer -> neutral", rs.career_stage("Dr M", "Senior lecturer"), "neutral")
    expect("bare Dr, no position -> neutral", rs.career_stage("Dr W", ""), "neutral")


def test_eligibility():
    print("\nis_eligible():")
    expect("photo + bio -> eligible", rs.is_eligible(mk("a")), True)
    expect("no photo -> not eligible", rs.is_eligible(mk("a", photo=False)), False)
    expect("no bio -> not eligible", rs.is_eligible(mk("a", bio=False)), False)


def test_dormant_below_threshold():
    print("\ndormant below threshold:")
    bios = {"members": [mk("e0"), mk("e1"), mk("e2"), mk("e3")]}  # 4 eligible
    st, changed, _ = rs.rotate(bios, base_state(), TODAY)
    expect("active false", st["active"], False)
    expect("current none", st["current"], None)


def test_activates_at_threshold():
    print("\nactivates at threshold:")
    st, changed, _ = rs.rotate(pool(10), base_state(), TODAY)
    expect("changed", changed, True)
    expect("active true", st["active"], True)
    expect_true("current is an eligible member", st["current"] in {f"m{i}" for i in range(10)})
    expect("history has one entry", len(st["history"]), 1)
    expect("pin cleared", st["pinned"], None)


def test_pin_override():
    print("\npin override:")
    state = base_state()
    state["pinned"] = "m7"
    st, changed, _ = rs.rotate(pool(10), state, TODAY)
    expect("pinned member featured", st["current"], "m7")
    expect("pin consumed", st["pinned"], None)
    # pin to an ineligible id is ignored
    state2 = base_state()
    state2["pinned"] = "ghost"
    st2, _, _ = rs.rotate(pool(10), state2, TODAY)
    expect_true("ineligible pin ignored, still picks someone", st2["current"] in {f"m{i}" for i in range(10)})


def test_same_week_noop():
    print("\nsame-week no-op:")
    st1, _, _ = rs.rotate(pool(10), base_state(), TODAY)
    first = st1["current"]
    st2, changed2, _ = rs.rotate(pool(10), st1, TODAY)
    expect("second run same week is no change", changed2, False)
    expect("current unchanged", st2["current"], first)


def test_recency_holdout():
    print("\nrecency hold-out:")
    state = base_state()
    # six members featured last six weeks (window default 6)
    state["history"] = [{"id": f"m{i}", "week": f"2026-W{20+i:02d}", "date": "2026-06-01"} for i in range(6)]
    st, _, _ = rs.rotate(pool(10), state, TODAY)
    expect_true("does not re-pick a recently featured member", st["current"] not in {f"m{i}" for i in range(6)})


def test_ineligible_current_refreshes():
    print("\nineligible current refreshes:")
    state = base_state()
    state["current"] = "gone"
    state["history"] = [{"id": "gone", "week": rs.week_key(TODAY), "date": TODAY.isoformat()}]
    st, changed, _ = rs.rotate(pool(10), state, TODAY)
    expect("re-rotates when current ineligible", changed, True)
    expect_true("new current is eligible", st["current"] in {f"m{i}" for i in range(10)})


def test_inclusiveness_preference():
    print("\ninclusiveness preference:")
    # 9 senior non-ITC professors + 1 ITC early-career PhD; the latter should win.
    members = [mk(f"p{i}", name="Prof Senior", position="Professor", cc="de") for i in range(9)]
    members.append(mk("star", name="Ms Star", position="PhD candidate", cc="rs"))  # rs is ITC
    st, _, log = rs.rotate({"members": members}, base_state(), TODAY)
    expect("ITC early-career member wins over senior non-ITC", st["current"], "star")


def main():
    test_career_stage()
    test_eligibility()
    test_dormant_below_threshold()
    test_activates_at_threshold()
    test_pin_override()
    test_same_week_noop()
    test_recency_holdout()
    test_ineligible_current_refreshes()
    test_inclusiveness_preference()
    print("\nAll spotlight tests passed.")


if __name__ == "__main__":
    main()
