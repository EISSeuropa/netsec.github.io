#!/usr/bin/env python3
"""Tests for build-directory-index.py — the cross-site member contract.

Loaded via importlib from its hyphenated path. Validates the rendered
index shape, the canonical name-key behaviour (notably that middle
initials are dropped), and that the committed directory-index.json
matches a fresh build (the drift gate).
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "build_directory_index", ROOT / "scripts" / "build-directory-index.py")
bdi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bdi)

INDEX = json.loads(bdi.build())


def test_output_is_valid_json_with_expected_shape():
    assert isinstance(INDEX["members"], list) and INDEX["members"]
    assert INDEX["count"] == len(INDEX["members"])
    assert INDEX["source"].endswith("/data/bios.json")
    for m in INDEX["members"]:
        assert set(m) >= {"name", "name_key", "aliases", "slug", "url", "orcid"}
        assert m["name"] and m["slug"]
        assert isinstance(m["aliases"], list)


def test_every_url_uses_the_profile_scheme():
    for m in INDEX["members"]:
        assert m["url"] == f"https://netsec-cost.eu/people/{m['slug']}.html"


def test_members_sorted_by_slug():
    slugs = [m["slug"] for m in INDEX["members"]]
    assert slugs == sorted(slugs)


def test_name_key_matches_sync_bios_and_drops_middle_initials():
    # The published key is exactly sync-bios.py's name_key(), joined.
    for m in INDEX["members"]:
        nk = bdi.name_key(m["name"])
        expected = (nk[0] + " " + nk[1]) if nk else None
        assert m["name_key"] == expected
    # And the documented trap: middle initials must not leak into the key.
    helferich = next((m for m in INDEX["members"] if m["slug"] == "john-helferich"), None)
    if helferich:
        assert helferich["name_key"] == "john helferich"
        assert "n.t" not in (helferich["name_key"] or "").lower()


def test_orcid_is_present_or_null_never_empty_string():
    for m in INDEX["members"]:
        assert m["orcid"] is None or (isinstance(m["orcid"], str) and m["orcid"].strip())


def test_committed_index_matches_a_fresh_build():
    # The drift gate: the checked-in directory-index.json must equal build().
    committed = (ROOT / "directory-index.json").read_text(encoding="utf-8")
    assert committed == bdi.build(), "directory-index.json is stale; run build-directory-index.py"


def test_build_is_deterministic():
    assert bdi.build() == bdi.build()


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
