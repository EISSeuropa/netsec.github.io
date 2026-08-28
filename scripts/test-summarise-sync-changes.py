#!/usr/bin/env python3
"""Tests for scripts/summarise-sync-changes.py."""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "summarise_sync_changes",
    Path(__file__).resolve().parent / "summarise-sync-changes.py",
)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def test_clean_tree_prints_nothing():
    assert mod.summarise([]) == ""


def test_pr_1421_reads_as_a_real_change():
    """The regression this script exists for.

    PR #1421's run log said "No substantive changes" because bios.json was
    untouched, while the diff carried one member's WG facet arriving in her
    three search stubs. The summary has to name her.
    """
    line = mod.summarise(
        [
            "search/bios/de/gayane-harutyunyan.html",
            "search/bios/en/gayane-harutyunyan.html",
            "search/bios/fr/gayane-harutyunyan.html",
        ]
    )
    assert "no member edits upstream" in line
    assert "3 derived files rebuilt" in line
    assert "search stubs (gayane-harutyunyan)" in line


def test_upstream_change_is_called_out():
    line = mod.summarise(["data/bios.json", "people/ada-lovelace.html"])
    assert "member data changed upstream" in line
    assert "1 derived file rebuilt" in line  # singular


def test_bios_only_change_reports_no_derived_files():
    line = mod.summarise(["data/bios.json"])
    assert line == "**Summary: member data changed upstream, no derived files rebuilt.**"


# These two cover the collapsing logic itself, and used the profile pages as
# the vehicle until those stopped being committed (#1716). search/bios/ is the
# per-member bucket the sync still writes.
def test_large_change_collapses_to_counts():
    paths = [f"search/bios/member-{i}.html" for i in range(12)]
    line = mod.summarise(paths)
    assert "search stubs (12 files, 12 members)" in line


def test_locale_variants_collapse_to_one_member():
    paths = [
        "search/bios/ada-lovelace.html",
        "search/bios/ada-lovelace.fr.html",
        "search/bios/ada-lovelace.de.html",
    ]
    assert "search stubs (ada-lovelace)" in mod.summarise(paths)


def test_buckets_are_labelled_not_dumped_as_paths():
    line = mod.summarise(["sitemap.xml", "directory-index.json"])
    assert "sitemap" in line and "directory index" in line
    assert ".xml" not in line


def test_unknown_path_falls_into_other_rather_than_vanishing():
    line = mod.summarise(["data/some-new-generator.json"])
    assert "other" in line
    assert "1 derived file rebuilt" in line


def test_porcelain_parsing_handles_status_codes_and_renames():
    paths = mod.parse_porcelain(
        " M data/bios.json\n"
        "?? search/bios/en/new-person.html\n"
        'R  people/old.html -> people/new.html\n'
    )
    assert paths == [
        "data/bios.json",
        "search/bios/en/new-person.html",
        "people/new.html",
    ]
