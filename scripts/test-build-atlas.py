"""Tests for build-atlas.py — the NetSec Atlas derivation (#764).

Covers the parts with real logic: person dedup across WGs, slug promotion when a
later roster row carries the bio slug an earlier one lacked, bipartite edge shape,
and byte-stable determinism. Pure standard library, no fixtures/framework beyond
pytest's collection.
"""

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "build_atlas", REPO / "scripts" / "build-atlas.py"
)
build_atlas = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_atlas)
build = build_atlas.build


def _wg(*groups):
    return {"groups": list(groups)}


def test_wg_hubs_and_person_nodes():
    atlas = build(
        _wg(
            {"number": 1, "name": "One", "colour": "wg-1", "memberCount": 2,
             "members": [{"name": "Dr Ada Lovelace", "country": "UK"}]},
        )
    )
    assert atlas["stats"] == {
        "working_groups": 1, "people": 1, "people_with_bios": 0, "edges": 1,
    }
    hub = next(n for n in atlas["nodes"] if n["type"] == "wg")
    assert hub["id"] == "wg-1" and hub["name"] == "One"
    person = next(n for n in atlas["nodes"] if n["type"] == "person")
    assert person["id"] == "p-ada-lovelace" and "slug" not in person


def test_person_dedup_across_wgs_is_one_node_two_edges():
    atlas = build(
        _wg(
            {"number": 1, "name": "One", "members": [{"name": "Dr Ada Lovelace"}]},
            {"number": 2, "name": "Two", "members": [{"name": "Prof Ada Lovelace"}]},
        )
    )
    people = [n for n in atlas["nodes"] if n["type"] == "person"]
    assert len(people) == 1                      # titles differ, name_key collapses them
    assert atlas["stats"]["edges"] == 2          # one edge to each WG (bipartite)
    targets = sorted(e["target"] for e in atlas["edges"])
    assert targets == ["wg-1", "wg-2"]


def test_slug_promotion_when_later_row_carries_the_bio():
    # First roster row has no slug; a later WG lists the same person *with* a slug.
    atlas = build(
        _wg(
            {"number": 1, "name": "One", "members": [{"name": "Dr Ada Lovelace"}]},
            {"number": 2, "name": "Two",
             "members": [{"name": "Dr Ada Lovelace", "slug": "ada-lovelace"}]},
        )
    )
    person = next(n for n in atlas["nodes"] if n["type"] == "person")
    assert person["id"] == "ada-lovelace"        # id upgrades to the stable slug
    assert person["slug"] == "ada-lovelace"
    assert atlas["stats"]["people_with_bios"] == 1
    # Edges must reference the promoted id, not the throwaway "p-..." one.
    assert {e["source"] for e in atlas["edges"]} == {"ada-lovelace"}


def test_deterministic_and_sorted():
    wg = _wg(
        {"number": 2, "name": "Two", "members": [{"name": "Dr Zed Zephyr"}]},
        {"number": 1, "name": "One", "members": [{"name": "Dr Ada Lovelace"}]},
    )
    a, b = build(wg), build(wg)
    assert json.dumps(a) == json.dumps(b)
    person_ids = [n["id"] for n in a["nodes"] if n["type"] == "person"]
    assert person_ids == sorted(person_ids)
    edges = [(e["source"], e["target"]) for e in a["edges"]]
    assert edges == sorted(edges)


def test_real_wg_json_derives_sane_stats():
    wg = json.loads((REPO / "data" / "wg.json").read_text(encoding="utf-8"))
    atlas = build(wg)
    s = atlas["stats"]
    assert s["working_groups"] == len(wg["groups"])
    assert s["people"] > 0 and s["edges"] >= s["people"]      # everyone joins ≥1 WG
    assert 0 <= s["people_with_bios"] <= s["people"]
    # Every edge endpoint resolves to a real node id.
    ids = {n["id"] for n in atlas["nodes"]}
    assert all(e["source"] in ids and e["target"] in ids for e in atlas["edges"])
