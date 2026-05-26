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
apply_wgs_to_bios = sync_cost.apply_wgs_to_bios
extract_leadership = sync_cost.extract_leadership


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


def test_apply_wgs_overwrites_matched() -> None:
    """The headline case: a bio entry whose name matches cost.eu's
    Membership table gets its `wgs` overwritten with cost.eu's list."""
    print("\napply_wgs_to_bios() — overwrites a matched entry:")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        path = _seed_bios(tmp, [
            {"id": "arthur-laudrain", "name": "Dr Arthur Laudrain",
             "wgs": [2, 3], "source": "form"},
        ])
        saved = sync_cost.BIOS
        sync_cost.BIOS = path
        try:
            lines = apply_wgs_to_bios({"arthur laudrain": [1, 2, 3]})
        finally:
            sync_cost.BIOS = saved
        bios = _read_bios(path)
        expect("wgs overwritten", bios[0]["wgs"], [1, 2, 3])
        expect("matched 1 bio",
               any("1 bios matched" in line for line in lines), True)
        expect("diff line emitted",
               any("Arthur Laudrain" in line for line in lines), True)


def test_apply_wgs_idempotent_when_already_matches() -> None:
    """A bio entry whose `wgs` already matches cost.eu produces no
    diff and the file is not rewritten."""
    print("\napply_wgs_to_bios() — idempotent when bios already matches:")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        path = _seed_bios(tmp, [
            {"id": "moritz-weiss", "name": "Dr. Moritz Weiss",
             "wgs": [1], "source": "seed"},
        ])
        before_mtime = path.stat().st_mtime_ns

        saved = sync_cost.BIOS
        sync_cost.BIOS = path
        try:
            lines = apply_wgs_to_bios({"moritz weiss": [1]})
        finally:
            sync_cost.BIOS = saved
        after_mtime = path.stat().st_mtime_ns

        expect("no changes reported",
               any("(no changes)" in line for line in lines), True)
        expect("file not rewritten", after_mtime, before_mtime)


def test_apply_wgs_leaves_unmatched_entries_alone() -> None:
    """A bio entry whose name is not in cost.eu's Membership table
    (community member, or a leader seeded ahead of cost.eu publishing
    them) is left untouched."""
    print("\napply_wgs_to_bios() — leaves unmatched entries untouched:")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        path = _seed_bios(tmp, [
            {"id": "community-member", "name": "Dr External Collaborator",
             "wgs": [4], "source": "form"},
        ])
        saved = sync_cost.BIOS
        sync_cost.BIOS = path
        try:
            apply_wgs_to_bios({"moritz weiss": [1], "arthur laudrain": [2, 3]})
        finally:
            sync_cost.BIOS = saved
        bios = _read_bios(path)
        expect("unmatched entry preserved", bios[0]["wgs"], [4])


def test_apply_wgs_handles_salutation_variants() -> None:
    """Names with and without a trailing-period salutation normalise
    to the same key, so cost.eu's `Dr Arthur Laudrain` matches a bio
    saved as `Dr. Arthur Laudrain`."""
    print("\napply_wgs_to_bios() — salutation variants normalise alike:")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        path = _seed_bios(tmp, [
            {"id": "filip-ejdus", "name": "Prof. Filip Ejdus",
             "wgs": [], "source": "form"},
        ])
        saved = sync_cost.BIOS
        sync_cost.BIOS = path
        try:
            apply_wgs_to_bios({"filip ejdus": [1]})
        finally:
            sync_cost.BIOS = saved
        expect("salutation variant matched",
               _read_bios(path)[0]["wgs"], [1])


def test_apply_wgs_no_bios_file() -> None:
    """When bios.json does not exist, the function returns a single
    'not present, skipped' line and does not crash."""
    print("\napply_wgs_to_bios() — missing bios.json is non-fatal:")
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "bios.json"   # does not exist
        saved = sync_cost.BIOS
        sync_cost.BIOS = path
        try:
            lines = apply_wgs_to_bios({"anyone": [1]})
        finally:
            sync_cost.BIOS = saved
        expect("skipped cleanly",
               any("not present" in line for line in lines), True)


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


# ─── main ──────────────────────────────────────────────────────────

def main() -> None:
    test_norm()
    test_apply_wgs_overwrites_matched()
    test_apply_wgs_idempotent_when_already_matches()
    test_apply_wgs_leaves_unmatched_entries_alone()
    test_apply_wgs_handles_salutation_variants()
    test_apply_wgs_no_bios_file()
    test_extract_leadership_matches_known_role_suffixes()
    print("\nAll smoke tests passed.")


if __name__ == "__main__":
    main()
