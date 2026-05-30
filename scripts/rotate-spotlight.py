#!/usr/bin/env python3
"""Rotate the weekly member spotlight.

Reads `data/bios.json` and the rotation state in `data/spotlight.json`,
picks the member to feature this ISO week using a balanced-rotation
score, and writes the updated state back. Designed to run once a week
from `.github/workflows/spotlight-rotate.yml`, opening an auto-PR (the
same pattern as the bios / indico / cost syncs).

Design (see issue #341):

  * Eligibility: a member needs a photo AND a non-empty bio.
  * Dormant until the pool reaches `minEligible` (default 10). Below
    that the block stays hidden and this script no-ops, so nothing
    publishes while the network is small.
  * One rotation per ISO week. A second run in the same week is a
    no-op unless the current member has become ineligible (left the
    network, lost their photo or bio), in which case it refreshes.
  * Balanced-rotation score, NOT hard quotas:
        score = early/senior career delta   (PhD/postdoc up, Prof down)
              + ITC boost                    (Inclusiveness Target Country)
              + WG-balance boost             (under-featured WGs up)
              + deterministic tie-break jitter
    Recently-featured members are held out of the candidate pool.
  * `pinned` override: set `pinned` to a member id in spotlight.json to
    feature them next run regardless of score; the script consumes it.
  * Gender is deliberately NOT scored (no gender data is stored); the
    maintainer corrects any imbalance via `pinned`. Career stage is
    inferred from the already-public title, never from name or photo
    for gender.

Run locally (no writes to PR-helper paths unless the env vars are set):

    python3 scripts/rotate-spotlight.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIOS = ROOT / "data" / "bios.json"
STATE = ROOT / "data" / "spotlight.json"

# COST Inclusiveness Target Countries, ISO 3166-1 alpha-2 (lowercase to
# match bios.json `country_code`). Source: COST ITC list. Kept here
# rather than in a data file because it changes rarely and only this
# script consumes it; revisit if COST revises the list.
ITC_COUNTRIES = {
    "al", "ba", "bg", "hr", "cy", "cz", "ee", "gr", "hu", "lv", "lt",
    "lu", "mt", "me", "mk", "pl", "pt", "ro", "rs", "sk", "si", "tr",
}

# Default weights; overridable via the `weights` block in spotlight.json.
DEFAULT_WEIGHTS = {
    "earlyCareer": 2.0,
    "seniorPenalty": 1.5,
    "itc": 2.0,
    "wg": 1.5,
    "recencyWindow": 6,
}
DEFAULT_MIN_ELIGIBLE = 10

# Career-stage signals read from the public job title (`position`) and
# the name prefix. Conservative on purpose: only the clear cases move
# the weight, everything else stays neutral. `position` is free text and
# multilingual, so a few common FR/DE forms are included.
_SENIOR_NAME = re.compile(r"^\s*prof\b", re.I)
_SENIOR_POS = re.compile(
    r"\b(professor|professeur|chair|head of|director|directeur|dean|emerit)\w*", re.I
)
_EARLY_POS = re.compile(
    r"\b(phd candidate|phd student|phd researcher|phd fellow|doctoral|"
    r"doctorand|doctorant|postdoc|post-doc|postdoctoral|early[- ]career|junior)\b",
    re.I,
)


def career_stage(name: str, position: str) -> str:
    """Return 'early', 'senior', or 'neutral' from the public title."""
    name = name or ""
    position = position or ""
    if _SENIOR_NAME.match(name) or _SENIOR_POS.search(position):
        return "senior"
    if _EARLY_POS.search(position):
        return "early"
    return "neutral"


def is_eligible(member: dict) -> bool:
    """A member can be featured if they have a photo and a written bio."""
    return bool((member.get("photo") or "").strip()) and bool(
        (member.get("bio") or "").strip()
    )


def week_key(d: date) -> str:
    """ISO-week label, e.g. '2026-W23'."""
    y, w, _ = d.isocalendar()
    return f"{y:04d}-W{w:02d}"


def _jitter(member_id: str, wk: str) -> float:
    """Small deterministic tie-break in [0, 0.5). Stable per (member,
    week) so reruns are reproducible, but varies week to week so the
    order is not a fixed alphabetical march. Avoids Math.random-style
    nondeterminism that would make the weekly PR unreviewable."""
    h = 0
    for ch in f"{member_id}|{wk}":
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return (h % 1000) / 2000.0


def _score(member, wk, itc_set, wg_recent_counts, weights) -> float:
    s = 0.0
    stage = career_stage(member.get("name", ""), member.get("position", ""))
    if stage == "early":
        s += weights["earlyCareer"]
    elif stage == "senior":
        s -= weights["seniorPenalty"]
    if (member.get("country_code") or "").lower() in itc_set:
        s += weights["itc"]
    wgs = member.get("wgs") or []
    if wgs:
        # Favour members whose Working Groups have been featured least
        # recently; the 1/(1+count) shape rewards under-represented WGs
        # without hard quotas.
        s += weights["wg"] * sum(
            1.0 / (1.0 + wg_recent_counts.get(w, 0)) for w in wgs
        ) / len(wgs)
    s += _jitter(member.get("id", ""), wk)
    return s


def rotate(bios: dict, state: dict, today: date) -> tuple[dict, bool, list[str]]:
    """Pure core: given bios, current state, and today's date, return
    (new_state, changed, log_lines). No file IO, so it is unit-testable."""
    log: list[str] = []
    state = json.loads(json.dumps(state))  # deep copy; never mutate input
    weights = {**DEFAULT_WEIGHTS, **(state.get("weights") or {})}
    min_eligible = int(state.get("minEligible", DEFAULT_MIN_ELIGIBLE))
    members = bios.get("members") or []
    by_id = {m.get("id"): m for m in members}

    eligible = [m for m in members if is_eligible(m)]
    elig_ids = {m["id"] for m in eligible}
    log.append(f"{len(eligible)} eligible of {len(members)} members (need {min_eligible}).")

    wk = week_key(today)
    history = state.get("history") or []

    def commit_state(chosen_id, became_active):
        before = json.dumps(state, sort_keys=True)
        state["active"] = became_active
        state["current"] = chosen_id
        if chosen_id is None:
            state["featuredSince"] = None
        else:
            # newest-first history, de-duplicated on same week
            entry = {"id": chosen_id, "week": wk, "date": today.isoformat()}
            hist = [h for h in history if h.get("week") != wk]
            state["history"] = ([entry] + hist)[:52]
            state["featuredSince"] = today.isoformat()
        state["pinned"] = None
        return json.dumps(state, sort_keys=True) != before

    # Dormant: not enough eligible members yet.
    if len(eligible) < min_eligible:
        changed = commit_state(None, False)
        log.append("Below threshold: spotlight stays dormant (block hidden).")
        return state, changed, log

    current = state.get("current")
    current_week = history[0].get("week") if history else None

    # Already rotated this week and the current member is still eligible:
    # nothing to do (a manual re-run is a no-op).
    if current and current in elig_ids and current_week == wk:
        log.append(f"Already featured {current} for {wk}; no change.")
        return state, False, log

    # Pin override takes precedence when it points at an eligible member.
    pinned = state.get("pinned")
    if pinned and pinned in elig_ids:
        changed = commit_state(pinned, True)
        log.append(f"Pinned override: featuring {pinned} ({by_id[pinned].get('name')}).")
        return state, changed, log
    if pinned:
        log.append(f"Ignoring pin {pinned!r}: not currently eligible.")

    # Hold out the most recently featured members so we don't repeat too
    # soon, but never empty the pool.
    window = min(int(weights["recencyWindow"]), len(eligible) - 1)
    recent = {h.get("id") for h in history[:window]}
    candidates = [m for m in eligible if m["id"] not in recent] or eligible

    # Recent feature counts per WG, for the balance boost.
    wg_recent_counts: dict[int, int] = {}
    for h in history[:window]:
        for w in (by_id.get(h.get("id"), {}).get("wgs") or []):
            wg_recent_counts[w] = wg_recent_counts.get(w, 0) + 1

    chosen = max(
        candidates,
        key=lambda m: _score(m, wk, ITC_COUNTRIES, wg_recent_counts, weights),
    )
    changed = commit_state(chosen["id"], True)
    stage = career_stage(chosen.get("name", ""), chosen.get("position", ""))
    itc = (chosen.get("country_code") or "").lower() in ITC_COUNTRIES
    log.append(
        f"Featuring {chosen['id']} ({chosen.get('name')}): "
        f"stage={stage}, itc={itc}, wgs={chosen.get('wgs') or []}."
    )
    return state, changed, log


def main() -> None:
    bios = json.loads(BIOS.read_text(encoding="utf-8"))
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    new_state, changed, log = rotate(bios, state, date.today())

    for line in log:
        print(line)

    if changed:
        STATE.write_text(
            json.dumps(new_state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"Wrote {STATE.relative_to(ROOT)}.")
    else:
        print("No change; spotlight state left as-is.")

    # PR helper outputs for the workflow (optional; unset locally).
    title_path = os.environ.get("SPOTLIGHT_PR_TITLE_PATH")
    overview_path = os.environ.get("SPOTLIGHT_PR_OVERVIEW_PATH")
    if changed and title_path and overview_path:
        cur = new_state.get("current")
        name = next(
            (m.get("name") for m in bios.get("members", []) if m.get("id") == cur),
            cur,
        )
        title = (
            f"data: weekly member spotlight — {name}" if cur
            else "data: weekly member spotlight — dormant"
        )
        Path(title_path).write_text(title + "\n", encoding="utf-8")
        Path(overview_path).write_text(
            "## Member spotlight rotation\n\n"
            + "\n".join(f"- {line}" for line in log)
            + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    sys.exit(main())
