#!/usr/bin/env python3
"""
Smoke tests for scripts/sync-cost.py.

Not a pytest test tree — the rest of the repo doesn't have one and the
sync script doesn't need that ceremony. Just a standalone runnable that
asserts on a handful of representative cases.

Usage:
    python3 scripts/test-sync-cost.py

Exits non-zero on the first failed assertion. No network calls — uses
in-memory fixtures, never fetches the live cost.eu page.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# Import the module under test as a sibling. The filename has a
# hyphen so the normal `import sync-cost` would be a SyntaxError;
# go via __import__ instead.
sys.path.insert(0, str(Path(__file__).resolve().parent))
sync_cost = __import__("sync-cost")
norm = sync_cost.norm
slugify = sync_cost.slugify
extract_leadership = sync_cost.extract_leadership
apply_leadership = sync_cost.apply_leadership


def expect(label: str, got, want) -> None:
    if got != want:
        print(f"FAIL: {label}\n  got:  {got!r}\n  want: {want!r}", file=sys.stderr)
        sys.exit(1)
    print(f"  ok  {label}")


# ─── norm() ────────────────────────────────────────────────────────

def test_norm() -> None:
    print("\nnorm() — drops salutations + diacritics, lowercases:")
    expect("plain", norm("Arthur Laudrain"), "arthur laudrain")
    expect("Dr.",   norm("Dr. Arthur Laudrain"), "arthur laudrain")
    expect("Dr",    norm("Dr Arthur Laudrain"), "arthur laudrain")
    expect("Prof.", norm("Prof. Filip Ejdus"), "filip ejdus")
    # NFKD strips combining marks (the ñ → n, ó → o) but leaves
    # composed special letters like ø untouched. Spot-check with a
    # synthetic name that exercises both paths.
    expect("diacritics + ø", norm("Søren Ñoñó"), "søren nono")
    expect("Ejdus", norm("Prof Filip Ejdus"), "filip ejdus")


# ─── apply_wgs_to_bios() ───────────────────────────────────────────

def _seed_bios(tmp: Path, members: list[dict]) -> Path:
    """Write a minimal bios.json fixture to tmp and return its path."""
    path = tmp / "bios.json"
    path.write_text(
        json.dumps({"members": members}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def _read_bios(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["members"]


def _with_paths(td: Path, members: list):
    """Point sync_cost.BIOS and WG_STATE into the tempdir."""
    path = _seed_bios(td, members)
    return path, td / "cost-wg-state.json"


def _run(new_map, today="2026-06-10"):
    return sync_cost.reconcile_wgs(new_map, today)


def test_reconcile_applies_cost_addition() -> None:
    """A WG on cost.eu that the form set lacks, observed no earlier
    than the form's last change, is applied (additions are safe)."""
    print("\nreconcile_wgs() — cost.eu addition applies:")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        path, state = _with_paths(tmp, [
            {"id": "arthur-laudrain", "name": "Dr Arthur Laudrain",
             "wgs": [2, 3], "source": "form"},
        ])
        saved = sync_cost.BIOS, sync_cost.WG_STATE
        sync_cost.BIOS, sync_cost.WG_STATE = path, state
        try:
            lines, eff = _run({"arthur laudrain": [1, 2, 3]})
        finally:
            sync_cost.BIOS, sync_cost.WG_STATE = saved
        expect("WG1 applied", _read_bios(path)[0]["wgs"], [1, 2, 3])
        expect("effective map carries the merge", eff["arthur laudrain"], [1, 2, 3])
        expect("addition reported",
               any("WG1 added" in line for line in lines), True)
        expect("state file written", state.exists(), True)


def test_reconcile_keeps_form_extra_as_pending() -> None:
    """A WG on the form that cost.eu has not published yet is kept on
    the card and flagged as pending catch-up, never stripped."""
    print("\nreconcile_wgs() — form-side WG pending cost.eu catch-up:")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        path, state = _with_paths(tmp, [
            {"id": "maria-fresh", "name": "Dr Maria Fresh",
             "wgs": [1, 3], "source": "form"},
        ])
        saved = sync_cost.BIOS, sync_cost.WG_STATE
        sync_cost.BIOS, sync_cost.WG_STATE = path, state
        try:
            lines, eff = _run({"maria fresh": [1]})
        finally:
            sync_cost.BIOS, sync_cost.WG_STATE = saved
        expect("form WG kept", _read_bios(path)[0]["wgs"], [1, 3])
        expect("effective map keeps it too", eff["maria fresh"], [1, 3])
        expect("flagged as pending",
               any("pending formal catch-up" in line for line in lines), True)


def test_reconcile_holds_deliberate_removal() -> None:
    """A WG long-standing on cost.eu that the member's NEWER form
    submission dropped is held (not re-added) and flagged for a human."""
    print("\nreconcile_wgs() — newer form removal is held, not re-added:")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        path, state = _with_paths(tmp, [
            {"id": "joe-dropper", "name": "Dr Joe Dropper",
             "wgs": [1], "source": "form"},
        ])
        # snapshot: WG2 first seen on cost.eu long ago; form set then
        # still carried it. The bio above (without WG2) is a NEWER edit.
        state.write_text(json.dumps({"members": {"joe dropper": {
            "cost_first_seen": {"1": "2026-05-01", "2": "2026-05-01"},
            "form_wgs": [1, 2],
            "form_changed_on": "2026-05-01",
        }}}), encoding="utf-8")
        saved = sync_cost.BIOS, sync_cost.WG_STATE
        sync_cost.BIOS, sync_cost.WG_STATE = path, state
        try:
            lines, eff = _run({"joe dropper": [1, 2]}, today="2026-06-10")
        finally:
            sync_cost.BIOS, sync_cost.WG_STATE = saved
        expect("removal held", _read_bios(path)[0]["wgs"], [1])
        expect("effective map honours the hold", eff["joe dropper"], [1])
        expect("hold flagged for a human",
               any("newer form submission omits it" in line for line in lines), True)


def test_reconcile_cost_newer_readds_after_form_change() -> None:
    """The recency tie-break in the other direction: cost.eu adds a WG
    AFTER the member's last form change, so it applies even though the
    form set lacks it."""
    print("\nreconcile_wgs() — later cost.eu addition wins over older form:")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        path, state = _with_paths(tmp, [
            {"id": "ann-promoted", "name": "Dr Ann Promoted",
             "wgs": [1], "source": "form"},
        ])
        state.write_text(json.dumps({"members": {"ann promoted": {
            "cost_first_seen": {"1": "2026-05-01"},
            "form_wgs": [1],
            "form_changed_on": "2026-05-01",
        }}}), encoding="utf-8")
        saved = sync_cost.BIOS, sync_cost.WG_STATE
        sync_cost.BIOS, sync_cost.WG_STATE = path, state
        try:
            lines, eff = _run({"ann promoted": [1, 4]}, today="2026-06-10")
        finally:
            sync_cost.BIOS, sync_cost.WG_STATE = saved
        expect("new formal WG applied", _read_bios(path)[0]["wgs"], [1, 4])
        expect("addition reported",
               any("WG4 added" in line for line in lines), True)


def test_reconcile_idempotent_when_in_agreement() -> None:
    """Sources agree: no diff, bios file untouched, second state write
    is a no-op."""
    print("\nreconcile_wgs() — idempotent when sources agree:")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        path, state = _with_paths(tmp, [
            {"id": "moritz-weiss", "name": "Dr. Moritz Weiss",
             "wgs": [1], "source": "seed"},
        ])
        saved = sync_cost.BIOS, sync_cost.WG_STATE
        sync_cost.BIOS, sync_cost.WG_STATE = path, state
        try:
            _run({"moritz weiss": [1]})
            before_mtime = path.stat().st_mtime_ns
            state_before = state.read_text(encoding="utf-8")
            lines, _ = _run({"moritz weiss": [1]})
        finally:
            sync_cost.BIOS, sync_cost.WG_STATE = saved
        expect("no changes reported",
               any("(no changes)" in line for line in lines), True)
        expect("bios not rewritten", path.stat().st_mtime_ns, before_mtime)
        expect("state stable", state.read_text(encoding="utf-8"), state_before)
        expect("salutation variant matched (Dr. vs Dr)",
               _read_bios(path)[0]["wgs"], [1])


def test_reconcile_leaves_unmatched_and_missing_file() -> None:
    """Entries not on cost.eu stay untouched; a missing bios.json is
    non-fatal and returns the raw map as effective."""
    print("\nreconcile_wgs() — unmatched entries + missing file:")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        path, state = _with_paths(tmp, [
            {"id": "community-member", "name": "Dr External Collaborator",
             "wgs": [4], "source": "form"},
        ])
        saved = sync_cost.BIOS, sync_cost.WG_STATE
        sync_cost.BIOS, sync_cost.WG_STATE = path, state
        try:
            _run({"moritz weiss": [1]})
            expect("unmatched entry preserved", _read_bios(path)[0]["wgs"], [4])
            sync_cost.BIOS = tmp / "missing.json"
            lines, eff = _run({"anyone": [1]})
            expect("missing file skipped cleanly",
                   any("not present" in line for line in lines), True)
            expect("raw map returned", eff, {"anyone": [1]})
        finally:
            sync_cost.BIOS, sync_cost.WG_STATE = saved


# ─── extract_leadership() regression coverage ──────────────────────

def test_extract_leadership_matches_known_role_suffixes() -> None:
    """Regression coverage for the role-label regex. The current
    accepted suffixes are Chair, Coordinator, Co-Lead / Co-lead,
    Leader, Representative. Synthetic minimal HTML imitating cost.eu's
    structure (a <td>{role}</td> followed by an <h4> with span-wrapped
    name parts)."""
    print("\nextract_leadership() — accepted role suffixes still match:")
    html = """
    <table>
      <tr><td>Action Chair</td></tr></table>
    <h4><span>Dr</span><span>Moritz</span><span>Weiss</span></h4>
    <table><tr><td>Grant Awarding Coordinator</td></tr></table>
    <h4><span>Dr</span><span>Sample</span><span>Person</span></h4>
    <table><tr><td>WG2 Co-Lead</td></tr></table>
    <h4><span>Dr</span><span>Co</span><span>Lead</span></h4>
    <table><tr><td>WG1 Leader</td></tr></table>
    <h4><span>Prof</span><span>Filip</span><span>Ejdus</span></h4>
    <table><tr><td>MC Representative</td></tr></table>
    <h4><span>Dr</span><span>A</span><span>Rep</span></h4>
    """
    pairs = extract_leadership(html)
    roles = [r for r, _ in pairs]
    expect("Chair found", "Action Chair" in roles, True)
    expect("Coordinator found", "Grant Awarding Coordinator" in roles, True)
    expect("Co-Lead found", "WG2 Co-Lead" in roles, True)
    expect("Leader found", "WG1 Leader" in roles, True)
    expect("Representative found", "MC Representative" in roles, True)


def test_extract_leadership_matches_standalone_lead() -> None:
    """Fix C: a role ending in a bare `Lead` (no trailing `er`, not the
    hyphenated `Co-Lead`) now matches — e.g. a future Science
    Communication Lead or Diversity Lead. `Leader` must still win over
    the shorter `Lead` so "WG1 Leader" keeps its full label."""
    print("\nextract_leadership() — standalone 'Lead' suffix matches:")
    html = """
    <table><tr><td>Science Communication Lead</td></tr></table>
    <h4><span>Dr</span><span>Science</span><span>Comms</span></h4>
    <table><tr><td>WG1 Leader</td></tr></table>
    <h4><span>Prof</span><span>Filip</span><span>Ejdus</span></h4>
    """
    pairs = extract_leadership(html)
    roles = [r for r, _ in pairs]
    expect("standalone Lead found",
           "Science Communication Lead" in roles, True)
    expect("Leader still matches the full label, not truncated to 'Lead'",
           "WG1 Leader" in roles, True)
    expect("Leader not mis-captured as 'WG1 Lead'",
           "WG1 Lead" not in roles, True)


# ─── apply_leadership() — Fix C carve-out ──────────────────────────

def test_apply_leadership_reconciles_form_entries() -> None:
    """Fix C: leadership is reconciled on every entry, not just seeds.
    A form-submitted member promoted on cost.eu picks up the new role;
    their form-provided custom role survives; a stale leadership role
    pointing elsewhere is stripped even from a form entry."""
    print("\napply_leadership() — reconciles form entries, keeps custom roles:")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        path = _seed_bios(tmp, [
            # Form-submitted member, now promoted to WG1 Leader on
            # cost.eu, carrying a custom non-leadership role.
            {"id": "moritz-weiss", "name": "Dr Moritz Weiss",
             "roles": ["MC member · Germany"], "source": "form"},
            # Form-submitted member who used to be WG1 Leader but isn't
            # any more — the stale role must be stripped.
            {"id": "filip-ejdus", "name": "Prof Filip Ejdus",
             "roles": ["WG1 Leader"], "source": "form"},
        ])
        saved = sync_cost.BIOS
        sync_cost.BIOS = path
        try:
            apply_leadership([("WG1 Leader", "Dr Moritz WEISS")])
        finally:
            sync_cost.BIOS = saved
        bios = {m["id"]: m for m in _read_bios(path)}
        expect("promoted form member gains WG1 Leader",
               "WG1 Leader" in bios["moritz-weiss"]["roles"], True)
        expect("custom form role preserved",
               "MC member · Germany" in bios["moritz-weiss"]["roles"], True)
        expect("stale leadership role stripped from form entry",
               "WG1 Leader" not in bios["filip-ejdus"]["roles"], True)


# ─── apply_leadership() — wg_leadership reconciliation ─────────────

def test_apply_leadership_reconciles_wg_leadership() -> None:
    """A WG co-lead change on cost.eu must move the per-bio
    `wg_leadership` object, not just the flat `roles` array. The new
    holder gains `co_lead: [3]`, the previous holder loses it. The
    people.html WG filter reads this field to place leaders under their
    group, so leaving it stale would show the wrong co-lead."""
    print("\napply_leadership() — derives wg_leadership from roles:")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        path = _seed_bios(tmp, [
            # The previous WG3 co-lead, carrying the now-stale field.
            {"id": "silvia-damato", "name": "Dr Silvia D'Amato",
             "roles": ["WG3 Co-Leader"], "wg_leadership": {"co_lead": [3]},
             "source": "form"},
            # The new co-lead cost.eu now lists, not yet carrying it.
            {"id": "new-colead", "name": "Dr New Colead",
             "roles": ["MC member · France"], "wg_leadership": {},
             "source": "form"},
        ])
        saved = sync_cost.BIOS
        sync_cost.BIOS = path
        try:
            apply_leadership([("WG3 Co-Leader", "Dr New COLEAD")])
        finally:
            sync_cost.BIOS = saved
        bios = {m["id"]: m for m in _read_bios(path)}
        expect("new holder gains wg_leadership.co_lead [3]",
               bios["new-colead"].get("wg_leadership"), {"co_lead": [3]})
        expect("previous holder loses wg_leadership.co_lead",
               bios["silvia-damato"].get("wg_leadership"), {})
        expect("new holder also gains the WG3 Co-Leader role",
               "WG3 Co-Leader" in bios["new-colead"]["roles"], True)


# ─── build_wg_json() — per-WG dataset ──────────────────────────────

def test_build_wg_json_resolves_leaders_and_members() -> None:
    """build_wg_json derives each WG's lead/co-lead from bios'
    `wg_leadership`, then lists EVERY member of the WG (from the
    membership list) excluding the two leaders. A member with a
    directory bio carries a `slug`; one without carries only name +
    country. memberCount counts the full membership (leaders included).
    An empty WG resolves to no leaders and a zero count. A second build
    with the same inputs is idempotent."""
    print("\nbuild_wg_json() — resolves leadership + full membership per WG:")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        biospath = _seed_bios(tmp, [
            {"id": "moritz-weiss", "name": "Dr Moritz Weiss", "wgs": [1],
             "wg_leadership": {"lead": [1]}, "source": "seed"},
            {"id": "filip-ejdus", "name": "Prof Filip Ejdus", "wgs": [1],
             "wg_leadership": {"co_lead": [1]}, "source": "seed"},
            {"id": "jane-doe", "name": "Dr Jane Doe", "wgs": [1],
             "wg_leadership": {}, "source": "form"},
        ])
        wgpath = tmp / "wg.json"
        saved_bios, saved_wg = sync_cost.BIOS, sync_cost.WG_JSON
        sync_cost.BIOS, sync_cost.WG_JSON = biospath, wgpath
        try:
            # WG1 membership: the two leaders, one bio'd member, and two
            # members with no directory bio (the common cost.eu case).
            members = [
                {"name": "Dr Moritz Weiss", "country": "Germany", "wgs": [1]},
                {"name": "Prof Filip Ejdus", "country": "Serbia", "wgs": [1]},
                {"name": "Dr Jane Doe", "country": "France", "wgs": [1]},
                {"name": "Prof No Bio One", "country": "Italy", "wgs": [1]},
                {"name": "Dr No Bio Two", "country": "Spain", "wgs": [1]},
            ]
            sync_cost.build_wg_json(members)
            second = sync_cost.build_wg_json(members)
        finally:
            sync_cost.BIOS, sync_cost.WG_JSON = saved_bios, saved_wg
        data = json.loads(wgpath.read_text(encoding="utf-8"))
        wg1 = next(g for g in data["groups"] if g["number"] == 1)
        expect("WG1 lead resolved from wg_leadership",
               wg1["lead"]["slug"], "moritz-weiss")
        expect("WG1 co-lead resolved from wg_leadership",
               wg1["coLead"]["slug"], "filip-ejdus")
        expect("WG1 members exclude the two leaders",
               sorted(m["name"] for m in wg1["members"]),
               ["Dr Jane Doe", "Dr No Bio Two", "Prof No Bio One"])
        expect("WG1 bio'd member carries a slug",
               next(m for m in wg1["members"] if m["name"] == "Dr Jane Doe")["slug"],
               "jane-doe")
        expect("WG1 non-bio member has no slug",
               "slug" in next(m for m in wg1["members"] if m["name"] == "Prof No Bio One"),
               False)
        expect("WG1 non-bio member keeps its country",
               next(m for m in wg1["members"] if m["name"] == "Prof No Bio One")["country"],
               "Italy")
        expect("WG1 total member count (leaders included)", wg1["memberCount"], 5)
        wg2 = next(g for g in data["groups"] if g["number"] == 2)
        expect("empty WG has no lead", wg2["lead"], None)
        expect("empty WG count is zero", wg2["memberCount"], 0)
        expect("second build is idempotent (no change)",
               any("(no changes)" in line for line in second), True)



# ─── MC roster + statistics sync ───────────────────────────────────

# Mirrors cost.eu's real (malformed) markup: the country <td> is
# closed with a stray </div>, names arrive as title/first/SURNAME
# spans, and one upstream name has its space collapsed.
MC_FIXTURE = """
<h2 class="x">Management Committee</h2>
<table><thead><tr><th>Country</th><th>MC Member</th></tr></thead><tbody>
<tr><td class="text-gray-900 align-top w-5/12">Albania</div>
  <td class="w-7/12">
    <h4><span>Dr</span> <span>Noela</span> <span class="uppercase">MAHMUTAJ</span></h4>
    <h4><span>Dr</span> <span>Edlira</span> <span class="uppercase">TITINI</span></h4>
  </td></tr>
<tr><td class="text-gray-900 align-top w-5/12">Cyprus</div>
  <td class="w-7/12">
    <h4><span>Prof</span> <span>PAVLOSIOANNIS</span> <span class="uppercase">KOKTSIDIS</span></h4>
  </td></tr>
</tbody></table>
<h2>Working Groups and Membership</h2>
"""


def test_fetch_mc_parses_malformed_table() -> None:
    print("\nfetch_mc() — malformed cost.eu MC table:")
    mc = sync_cost.fetch_mc(MC_FIXTURE)
    expect("rep count", len(mc), 3)
    expect("countries", sorted({m["country"] for m in mc}), ["Albania", "Cyprus"])
    expect("title-cased name", mc[0]["name"], "Dr Edlira Titini")
    expect("iso code", mc[0]["country_code"], "al")
    expect("upstream name fix applied",
           next(m["name"] for m in mc if m["country"] == "Cyprus"),
           "Prof Pavlos Ioannis Koktsidis")
    expect("no section means empty roster", sync_cost.fetch_mc("<p>nothing</p>"), [])


def test_build_mc_json_reports_and_idempotent() -> None:
    print("\nbuild_mc_json() — roster diff + idempotency:")
    mc = sync_cost.fetch_mc(MC_FIXTURE)
    with tempfile.TemporaryDirectory() as td:
        old_mc_json = sync_cost.MC_JSON
        sync_cost.MC_JSON = Path(td) / "mc-members.json"
        try:
            sync_cost.MC_JSON.write_text(json.dumps({"members": [
                {"name": "Dr Noela Mahmutaj", "country": "Albania", "country_code": "al"},
                {"name": "Dr Gone Person", "country": "Albania", "country_code": "al"},
            ]}), encoding="utf-8")
            first = sync_cost.build_mc_json(mc)
            expect("addition reported", any("+ edlira titini" in l for l in first), True)
            expect("removal reported", any("- gone person" in l for l in first), True)
            second = sync_cost.build_mc_json(mc)
            expect("second run no-op", any("(no changes)" in l for l in second), True)
            expect("empty roster leaves file alone",
                   "untouched" in sync_cost.build_mc_json([])[0], True)
        finally:
            sync_cost.MC_JSON = old_mc_json


def test_apply_stats_rewrites_markers() -> None:
    print("\napply_stats() — data-cost-stat literal rewrite:")
    mc = sync_cost.fetch_mc(MC_FIXTURE)   # 3 reps, 2 countries
    with tempfile.TemporaryDirectory() as td:
        old_root, old_pages = sync_cost.ROOT, sync_cost.STAT_PAGES
        sync_cost.ROOT = Path(td)
        sync_cost.STAT_PAGES = ["about.html"]
        try:
            page = Path(td) / "about.html"
            page.write_text(
                '<span class="mc-stat-num" data-cost-stat="mc-count">49</span>'
                '<span data-cost-stat="country-count">30</span>'
                '<span class="mc-stat-num">52</span>', encoding="utf-8")
            first = sync_cost.apply_stats(mc)
            out = page.read_text(encoding="utf-8")
            expect("mc-count rewritten", 'data-cost-stat="mc-count">3<' in out, True)
            expect("country-count rewritten", 'data-cost-stat="country-count">2<' in out, True)
            expect("unmarked founding stat untouched",
                   '<span class="mc-stat-num">52</span>' in out, True)
            expect("change reported", any("updated" in l for l in first), True)
            second = sync_cost.apply_stats(mc)
            expect("second run no-op", any("(no changes)" in l for l in second), True)
        finally:
            sync_cost.ROOT, sync_cost.STAT_PAGES = old_root, old_pages


# ─── main ──────────────────────────────────────────────────────────

def main() -> None:
    test_norm()
    test_reconcile_applies_cost_addition()
    test_reconcile_keeps_form_extra_as_pending()
    test_reconcile_holds_deliberate_removal()
    test_reconcile_cost_newer_readds_after_form_change()
    test_reconcile_idempotent_when_in_agreement()
    test_reconcile_leaves_unmatched_and_missing_file()
    test_extract_leadership_matches_known_role_suffixes()
    test_extract_leadership_matches_standalone_lead()
    test_apply_leadership_reconciles_form_entries()
    test_apply_leadership_reconciles_wg_leadership()
    test_build_wg_json_resolves_leaders_and_members()
    test_fetch_mc_parses_malformed_table()
    test_build_mc_json_reports_and_idempotent()
    test_apply_stats_rewrites_markers()
    print("\nAll smoke tests passed.")


if __name__ == "__main__":
    main()
