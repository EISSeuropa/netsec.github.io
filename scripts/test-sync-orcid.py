#!/usr/bin/env python3
"""Tests for scripts/sync-orcid.py — the ORCID works fetcher (#761).

Pure-function coverage (no network): parse_works trims and sorts a real-
shaped ORCID /works payload, and build_works_map fails soft per member.
Runs under the stock interpreter (`python3 scripts/test-sync-orcid.py`);
no third-party deps, so it executes even where `requests` is absent.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sync_orcid = __import__("sync-orcid")
parse_works = sync_orcid.parse_works
build_works_map = sync_orcid.build_works_map


def expect(label: str, got, want) -> None:
    if got != want:
        print(f"FAIL: {label}\n  got:  {got!r}\n  want: {want!r}", file=sys.stderr)
        sys.exit(1)
    print(f"  ok  {label}")


def _work_group(title, year=None, journal=None, doi=None):
    """Build one ORCID `group` entry shaped like the real v3.0 /works
    response: title + date + journal on work-summary[0], DOI on the
    group's external-ids."""
    ws: dict = {"title": {"title": {"value": title}}}
    if year is not None:
        ws["publication-date"] = {"year": {"value": year}}
    if journal is not None:
        ws["journal-title"] = {"value": journal}
    group: dict = {"work-summary": [ws]}
    if doi is not None:
        group["external-ids"] = {
            "external-id": [
                {"external-id-type": "doi", "external-id-value": doi}
            ]
        }
    return group


def test_parse_works() -> None:
    print("\nparse_works():")
    payload = {
        "group": [
            _work_group("Older paper", "2018", "Some Journal", "10.1/old"),
            _work_group("Newest paper", "2025", "Top Journal", "10.1/new"),
            _work_group("Middle paper", "2021", None, None),
            _work_group("Undated note"),  # no year, no journal, no doi
        ]
    }
    out = parse_works(payload)
    expect("caps at 3 works", len(out), 3)
    expect("sorts newest first", [w["title"] for w in out],
           ["Newest paper", "Middle paper", "Older paper"])
    expect("dated newest carries its year", out[0]["year"], "2025")
    expect("extracts the journal", out[0]["journal"], "Top Journal")
    expect("extracts the DOI from the group", out[0]["doi"], "10.1/new")
    expect("missing journal becomes empty string", out[1]["journal"], "")
    expect("missing DOI becomes empty string", out[1]["doi"], "")

    # Undated work is kept but sorts last; with limit it can be trimmed off.
    out2 = parse_works(payload, limit=4)
    expect("undated work sorts last", out2[3]["title"], "Undated note")
    expect("undated work has empty year", out2[3]["year"], "")

    # A work with no title is dropped (nothing to render).
    titleless = {"group": [_work_group("", "2030"), _work_group("Real", "2029")]}
    out3 = parse_works(titleless)
    expect("titleless work is dropped", [w["title"] for w in out3], ["Real"])

    # Empty / malformed payloads never raise.
    expect("empty payload yields empty list", parse_works({}), [])
    expect("None payload yields empty list", parse_works(None), [])
    expect("group with no work-summary is skipped",
           parse_works({"group": [{"work-summary": []}]}), [])


def test_build_works_map_fails_soft() -> None:
    print("\nbuild_works_map() fail-soft:")
    members = [
        {"id": "has-works", "orcid": "0000-0000-0000-0001"},
        {"id": "fetch-fails", "orcid": "0000-0000-0000-0002"},
        {"id": "no-orcid", "orcid": ""},
        {"id": "empty-works", "orcid": "0000-0000-0000-0003"},
    ]

    def fetcher(orcid: str):
        if orcid.endswith("0001"):
            return {"group": [_work_group("A paper", "2024")]}
        if orcid.endswith("0002"):
            return None  # simulate a 404 / timeout
        if orcid.endswith("0003"):
            return {"group": []}  # member exists but published nothing
        return None

    out = build_works_map(members, fetcher)
    expect("only the member with works appears", sorted(out), ["has-works"])
    expect("a failed fetch is skipped, not fatal", "fetch-fails" in out, False)
    expect("a member with no iD is skipped", "no-orcid" in out, False)
    expect("a member with zero works is omitted", "empty-works" in out, False)
    expect("the kept member carries the parsed work",
           out["has-works"][0]["title"], "A paper")


def test_build_works_map_outage_carry_over() -> None:
    """A failed fetch must keep the member's previous works rather than
    dropping them, so a transient ORCID outage cannot wipe the file."""
    print("\nbuild_works_map() outage carry-over:")
    members = [{"id": "alice", "orcid": "0000-0000-0000-0009"}]
    existing = {"alice": [{"title": "Last week's paper", "year": "2024",
                           "journal": "", "doi": ""}]}

    # Total outage: fetcher always fails.
    out = build_works_map(members, lambda o: None, existing)
    expect("outage carries the previous works over", out, existing)

    # Recovery: a successful fetch replaces the carried-over value.
    fresh = {"group": [{"work-summary": [{"title": {"title": {"value": "New"}},
             "publication-date": {"year": {"value": "2025"}}}]}]}
    out2 = build_works_map(members, lambda o: fresh, existing)
    expect("a successful fetch supersedes the old works",
           out2["alice"][0]["title"], "New")

    # A member who genuinely cleared their works (successful fetch, empty)
    # is dropped even though they had an entry before.
    out3 = build_works_map(members, lambda o: {"group": []}, existing)
    expect("an emptied record clears the stale entry", "alice" in out3, False)


def main() -> None:
    test_parse_works()
    test_build_works_map_fails_soft()
    test_build_works_map_outage_carry_over()
    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
