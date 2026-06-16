#!/usr/bin/env python3
"""Shape validator for the synced data/ JSON files.

The sync workflows (Indico daily, bios + COST weekly, roadmap-progress
on issue events) open auto-merged PRs that rewrite files under data/.
The pages that consume those files render at runtime in the browser,
so a malformed upstream shape change would ship a blank page with
every other CI check green. This script is the gate: it validates the
structural invariants each consuming renderer relies on, and fails the
PR before a shape break reaches main. See issue #724.

Dependency-free by design (stdlib json only), same as the other
check-* lints, so CI needs nothing beyond setup-python.

Per-file invariants (the "would this blank a page?" set, not a full
schema):

  indico.json            syncedAt stamp, at least one annual conference
                         carrying title/url and a programme with >= 1
                         day and >= 1 renderable slot or row item.
  bios.json              non-empty members list, every member has a
                         non-empty id and name (the directory grid and
                         every name-matched card resolves through these).
  wg.json                non-empty groups list with number, name and a
                         members list per group.
  mc-members.json        non-empty members list with name + country.
  events.json            tzid present, non-empty events list, every
                         event has start/end/status/eventType/cardTitle
                         (the home banner and calendar builder read all
                         five).
  roadmap-progress.json  non-empty milestones map, every entry carries
                         integer closed/total and a state string.

Usage:
  python3 scripts/check-data-shape.py            # validate all six
  python3 scripts/check-data-shape.py data/bios.json   # subset

Exit codes: 0 all valid, 1 any violation (or unparseable JSON).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _req(obj: dict, key: str, types, errs: list, ctx: str, non_empty: bool = False) -> bool:
    """Append an error unless obj[key] exists, matches types, and (optionally) is non-empty."""
    if key not in obj:
        errs.append(f"{ctx}: missing key '{key}'")
        return False
    val = obj[key]
    if not isinstance(val, types):
        tname = types.__name__ if isinstance(types, type) else "/".join(t.__name__ for t in types)
        errs.append(f"{ctx}: '{key}' should be {tname}, got {type(val).__name__}")
        return False
    if non_empty and not val:
        errs.append(f"{ctx}: '{key}' is empty")
        return False
    return True


def check_indico(data) -> list:
    errs: list = []
    if not isinstance(data, dict):
        return ["indico: top level must be an object"]
    _req(data, "syncedAt", str, errs, "indico", non_empty=True)
    if not _req(data, "annualConferences", dict, errs, "indico", non_empty=True):
        return errs
    for year, conf in data["annualConferences"].items():
        ctx = f"indico.annualConferences[{year}]"
        if not isinstance(conf, dict):
            errs.append(f"{ctx}: must be an object")
            continue
        _req(conf, "title", str, errs, ctx, non_empty=True)
        _req(conf, "url", str, errs, ctx, non_empty=True)
        if not _req(conf, "programme", dict, errs, ctx):
            continue
        prog = conf["programme"]
        if not _req(prog, "days", list, errs, f"{ctx}.programme", non_empty=True):
            continue
        renderable = 0
        for i, day in enumerate(prog["days"]):
            dctx = f"{ctx}.programme.days[{i}]"
            if not isinstance(day, dict):
                errs.append(f"{dctx}: must be an object")
                continue
            _req(day, "date", str, errs, dctx, non_empty=True)
            slots = day.get("slots")
            rows = day.get("rows")
            if not isinstance(slots, list) and not isinstance(rows, list):
                errs.append(f"{dctx}: needs a 'slots' or 'rows' list")
                continue
            renderable += len(slots or [])
            for row in rows or []:
                if isinstance(row, dict):
                    renderable += len(row.get("items") or [])
        if renderable == 0:
            errs.append(f"{ctx}: programme contains no renderable slots or row items")
    return errs


def check_bios(data) -> list:
    errs: list = []
    if not isinstance(data, dict):
        return ["bios: top level must be an object"]
    if not _req(data, "members", list, errs, "bios", non_empty=True):
        return errs
    for i, m in enumerate(data["members"]):
        ctx = f"bios.members[{i}]"
        if not isinstance(m, dict):
            errs.append(f"{ctx}: must be an object")
            continue
        _req(m, "id", str, errs, ctx, non_empty=True)
        _req(m, "name", str, errs, ctx, non_empty=True)
        # Link fields are dropped straight into an <a href> by the directory
        # renderers, so a bare handle ("@x") or scheme-less domain ("x.eu")
        # becomes a broken *relative* link. sync-bios.py normalises these to
        # absolute URLs; this gate stops a non-absolute value reaching the
        # site if that normalisation is ever bypassed. (email is excluded:
        # the renderer builds its mailto: itself from a bare address.)
        for field in ("website", "linkedin", "twitter", "bluesky", "mastodon"):
            val = m.get(field)
            if isinstance(val, str) and val and not val.lower().startswith(("http://", "https://")):
                errs.append(
                    f"{ctx}: '{field}' must be an absolute http(s) URL, got {val!r}"
                )
        # STSM hosting (#760) is a tri-state scalar; the renderer keys the
        # badge + filter off the exact values, so a stray value would
        # render an empty or mislabelled badge.
        sh = m.get("stsm_hosting")
        if sh is not None and sh not in ("yes", "ask"):
            errs.append(
                f"{ctx}: 'stsm_hosting' must be 'yes' or 'ask' (or absent), got {sh!r}"
            )
    return errs


def check_wg(data) -> list:
    errs: list = []
    if not isinstance(data, dict):
        return ["wg: top level must be an object"]
    if not _req(data, "groups", list, errs, "wg", non_empty=True):
        return errs
    for i, g in enumerate(data["groups"]):
        ctx = f"wg.groups[{i}]"
        if not isinstance(g, dict):
            errs.append(f"{ctx}: must be an object")
            continue
        _req(g, "number", int, errs, ctx)
        _req(g, "name", str, errs, ctx, non_empty=True)
        _req(g, "members", list, errs, ctx)
    return errs


def check_mc_members(data) -> list:
    errs: list = []
    if not isinstance(data, dict):
        return ["mc-members: top level must be an object"]
    if not _req(data, "members", list, errs, "mc-members", non_empty=True):
        return errs
    for i, m in enumerate(data["members"]):
        ctx = f"mc-members.members[{i}]"
        if not isinstance(m, dict):
            errs.append(f"{ctx}: must be an object")
            continue
        _req(m, "name", str, errs, ctx, non_empty=True)
        _req(m, "country", str, errs, ctx, non_empty=True)
    return errs


def check_events(data) -> list:
    errs: list = []
    if not isinstance(data, dict):
        return ["events: top level must be an object"]
    _req(data, "tzid", str, errs, "events", non_empty=True)
    if not _req(data, "events", list, errs, "events", non_empty=True):
        return errs
    for i, ev in enumerate(data["events"]):
        ctx = f"events.events[{i}]"
        if not isinstance(ev, dict):
            errs.append(f"{ctx}: must be an object")
            continue
        for key in ("start", "end", "status", "eventType"):
            _req(ev, key, str, errs, ctx, non_empty=True)
        # cardTitle is a locale map ({en, fr, de}); the renderers fall
        # back to 'en', so that key is the load-bearing one.
        if _req(ev, "cardTitle", dict, errs, ctx, non_empty=True):
            _req(ev["cardTitle"], "en", str, errs, f"{ctx}.cardTitle", non_empty=True)
    return errs


def check_roadmap_progress(data) -> list:
    errs: list = []
    if not isinstance(data, dict):
        return ["roadmap-progress: top level must be an object"]
    if not _req(data, "milestones", dict, errs, "roadmap-progress", non_empty=True):
        return errs
    for version, ms in data["milestones"].items():
        ctx = f"roadmap-progress.milestones[{version}]"
        if not isinstance(ms, dict):
            errs.append(f"{ctx}: must be an object")
            continue
        _req(ms, "closed", int, errs, ctx)
        _req(ms, "total", int, errs, ctx)
        _req(ms, "state", str, errs, ctx, non_empty=True)
    return errs


def check_field_guide(data) -> list:
    errs: list = []
    if not isinstance(data, dict):
        return ["field-guide: top level must be an object"]
    if not _req(data, "concepts", list, errs, "field-guide", non_empty=True):
        return errs
    for i, c in enumerate(data["concepts"]):
        ctx = f"field-guide.concepts[{i}]"
        if not isinstance(c, dict):
            errs.append(f"{ctx}: must be an object")
            continue
        _req(c, "term", str, errs, ctx, non_empty=True)
        if _req(c, "definition", dict, errs, ctx):
            _req(c["definition"], "en", str, errs, f"{ctx}.definition", non_empty=True)
    return errs


def check_orcid_works(data) -> list:
    """data/orcid-works.json: a top-level object with a `works` map keyed
    by member slug, each value a list of {title, year, journal, doi}
    records. Generated by sync-orcid.py (#761); the renderer lazy-loads it
    on card expansion, so a malformed record would surface as a broken
    publications list, not a build failure. An empty `works` map is valid
    (no member carries an ORCID iD yet)."""
    errs: list = []
    if not isinstance(data, dict):
        return ["orcid-works: top level must be an object"]
    if not _req(data, "works", dict, errs, "orcid-works"):
        return errs
    for slug, works in data["works"].items():
        ctx = f"orcid-works.works[{slug!r}]"
        if not isinstance(works, list):
            errs.append(f"{ctx}: must be a list")
            continue
        for i, w in enumerate(works):
            wctx = f"{ctx}[{i}]"
            if not isinstance(w, dict):
                errs.append(f"{wctx}: must be an object")
                continue
            _req(w, "title", str, errs, wctx, non_empty=True)
            _req(w, "year", str, errs, wctx)
    return errs


def check_spotlight(data) -> list:
    """data/spotlight.json: the weekly member-spotlight rotation state
    (#341). `current` (and each `history[].id`) must point at a member id
    that still exists in data/bios.json — otherwise the home-page and
    directory spotlights silently render nothing, which is exactly what
    happens when a member is removed or re-slugged without updating this
    file. Cross-references bios.json so that gap is caught in CI, not on
    the live site."""
    errs: list = []
    if not isinstance(data, dict):
        return ["spotlight: top level must be an object"]
    if "active" in data and not isinstance(data["active"], bool):
        errs.append("spotlight: 'active' must be a boolean")
    try:
        bios = json.loads((REPO / "data/bios.json").read_text(encoding="utf-8"))
        ids = {m.get("id") for m in bios.get("members", [])}
    except Exception as exc:  # bios.json checked separately; don't double-fail
        errs.append(f"spotlight: could not read bios.json to validate ids ({exc})")
        return errs
    cur = data.get("current")
    if cur and cur not in ids:
        errs.append(f"spotlight: 'current' = {cur!r} is not a member id in bios.json")
    for i, h in enumerate(data.get("history") or []):
        hid = h.get("id") if isinstance(h, dict) else None
        if hid and hid not in ids:
            errs.append(f"spotlight.history[{i}]: id {hid!r} is not a member id in bios.json")
    return errs


CHECKS = {
    "data/indico.json": check_indico,
    "data/bios.json": check_bios,
    "data/wg.json": check_wg,
    "data/mc-members.json": check_mc_members,
    "data/events.json": check_events,
    "data/roadmap-progress.json": check_roadmap_progress,
    "data/field-guide.json": check_field_guide,
    "data/orcid-works.json": check_orcid_works,
    "data/spotlight.json": check_spotlight,
}


def main(argv: list) -> int:
    targets = argv or sorted(CHECKS)
    failed = False
    for target in targets:
        rel = str(Path(target))
        if rel not in CHECKS:
            print(f"⚠ {rel}: no shape check registered, skipping")
            continue
        path = REPO / rel
        if not path.exists():
            print(f"✗ {rel}: file not found")
            failed = True
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"✗ {rel}: invalid JSON ({exc})")
            failed = True
            continue
        errs = CHECKS[rel](data)
        if errs:
            failed = True
            print(f"✗ {rel}: {len(errs)} violation(s)")
            for e in errs:
                print(f"    {e}")
        else:
            print(f"✓ {rel}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
