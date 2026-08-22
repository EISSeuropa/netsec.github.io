"""Tests for build-network-map.py — the NetSec Network Map derivation (#764).

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
    "build_network_map", REPO / "scripts" / "build-network-map.py"
)
build_network_map = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_network_map)
build = build_network_map.build


def _wg(*groups):
    return {"groups": list(groups)}


def test_wg_hubs_and_person_nodes():
    graph = build(
        _wg(
            {"number": 1, "name": "One", "colour": "wg-1", "memberCount": 2,
             "members": [{"name": "Dr Ada Lovelace", "country": "UK"}]},
        )
    )
    assert graph["stats"] == {
        "working_groups": 1, "people": 1, "people_with_bios": 0, "edges": 1,
    }
    hub = next(n for n in graph["nodes"] if n["type"] == "wg")
    assert hub["id"] == "wg-1" and hub["name"] == "One"
    person = next(n for n in graph["nodes"] if n["type"] == "person")
    assert person["id"] == "p-ada-lovelace" and "slug" not in person


def test_person_dedup_across_wgs_is_one_node_two_edges():
    graph = build(
        _wg(
            {"number": 1, "name": "One", "members": [{"name": "Dr Ada Lovelace"}]},
            {"number": 2, "name": "Two", "members": [{"name": "Prof Ada Lovelace"}]},
        )
    )
    people = [n for n in graph["nodes"] if n["type"] == "person"]
    assert len(people) == 1                      # titles differ, name_key collapses them
    assert graph["stats"]["edges"] == 2          # one edge to each WG (bipartite)
    targets = sorted(e["target"] for e in graph["edges"])
    assert targets == ["wg-1", "wg-2"]


def test_slug_promotion_when_later_row_carries_the_bio():
    # First roster row has no slug; a later WG lists the same person *with* a slug.
    graph = build(
        _wg(
            {"number": 1, "name": "One", "members": [{"name": "Dr Ada Lovelace"}]},
            {"number": 2, "name": "Two",
             "members": [{"name": "Dr Ada Lovelace", "slug": "ada-lovelace"}]},
        )
    )
    person = next(n for n in graph["nodes"] if n["type"] == "person")
    assert person["id"] == "ada-lovelace"        # id upgrades to the stable slug
    assert person["slug"] == "ada-lovelace"
    assert graph["stats"]["people_with_bios"] == 1
    # Edges must reference the promoted id, not the throwaway "p-..." one.
    assert {e["source"] for e in graph["edges"]} == {"ada-lovelace"}


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
    graph = build(wg)
    s = graph["stats"]
    assert s["working_groups"] == len(wg["groups"])
    assert s["people"] > 0 and s["edges"] >= s["people"]      # everyone joins ≥1 WG
    assert 0 <= s["people_with_bios"] <= s["people"]
    # Every edge endpoint resolves to a real node id.
    ids = {n["id"] for n in graph["nodes"]}
    assert all(e["source"] in ids and e["target"] in ids for e in graph["edges"])


def test_coauthor_edges_from_publications():
    graph = build(
        _wg(
            {"number": 1, "name": "One", "colour": "wg-1", "memberCount": 3,
             "members": [
                 {"name": "Dr Ada Lovelace", "country": "UK", "slug": "ada-lovelace"},
                 {"name": "Prof. Alan Turing", "country": "UK", "slug": "alan-turing"},
                 {"name": "Dr Grace Hopper", "country": "US", "slug": "grace-hopper"},
             ]},
        ),
        publications={"publications": [
            # Two members + one outside author: one edge, outsider ignored.
            {"title": {"en": "Paper A"}, "authors": ["Ada Lovelace", "Alan Turing", "Jane Doe"]},
            # The same pair again: weight climbs to 2.
            {"title": {"en": "Paper B"}, "authors": ["Alan Turing", "Ada Lovelace"]},
            # A single matched author: no edge.
            {"title": {"en": "Paper C"}, "authors": ["Grace Hopper", "Someone Else"]},
        ]},
    )
    co = [e for e in graph["edges"] if e.get("type") == "coauthor"]
    assert co == [{"source": "ada-lovelace", "target": "alan-turing",
                   "type": "coauthor", "weight": 2}]
    assert graph["stats"]["publications_matched"] == 2
    assert graph["stats"]["coauthor_edges"] == 1


def test_empty_publications_add_zero_edges_and_stats():
    graph = build(_wg({"number": 1, "name": "One", "colour": "wg-1",
                       "memberCount": 0, "members": []}),
                  publications={"publications": []})
    assert graph["stats"]["coauthor_edges"] == 0
    assert graph["stats"]["publications_matched"] == 0


# The Network Map draws headshots as small canvas circles, so a node pointing at the
# original JPEG spends bytes the page cannot use. Lighthouse's 500 KB image
# budget caught the page shipping 5.6 MB of them.
def test_photo_prefers_the_webp_beside_it(tmp_path, monkeypatch):
    monkeypatch.setattr(build_network_map, "REPO", tmp_path)
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "ada.webp").write_bytes(b"webp")
    assert build_network_map.prefer_webp("assets/ada.jpg") == "assets/ada.webp"


def test_photo_falls_back_when_no_webp_exists(tmp_path, monkeypatch):
    # The state a member sits in between joining and the next bios sync.
    monkeypatch.setattr(build_network_map, "REPO", tmp_path)
    assert build_network_map.prefer_webp("assets/newcomer.jpg") == "assets/newcomer.jpg"


def test_every_committed_photo_path_resolves_to_a_real_file():
    """A photo path that 404s renders a faceless dot, which no gate would catch."""
    graph = json.loads((REPO / "data" / "network-map.json").read_text(encoding="utf-8"))
    missing = [n["photo"] for n in graph["nodes"]
               if n.get("photo") and not (REPO / n["photo"]).exists()]
    assert missing == [], f"network-map.json points at files that do not exist: {missing}"


def test_committed_photo_payload_stays_under_the_lighthouse_budget():
    """resource-summary:image:size warns above 500 KB; the canvas loads every
    headshot eagerly, so the whole set is the page's image weight."""
    graph = json.loads((REPO / "data" / "network-map.json").read_text(encoding="utf-8"))
    total = sum((REPO / n["photo"]).stat().st_size
                for n in graph["nodes"]
                if n.get("photo") and (REPO / n["photo"]).exists())
    mb = total / 1024 / 1024
    # 2.5 MB leaves room to grow from today's 1.45 MB without hiding a
    # regression back to the 5.24 MB the originals cost.
    assert mb < 2.5, f"graph headshot payload is {mb:.2f} MB"


def _edition(year, panels):
    """One annualConferences entry: each panel is a list of speaker names."""
    return {
        year: {"programme": {"days": [{"rows": [{"items": [
            {"contributions": [{"people": [{"name": n} for n in names]}]}
            for names in panels
        ]}]}]}}
    }


def _three_members():
    return _wg(
        {"number": 1, "name": "One", "colour": "wg-1", "memberCount": 3,
         "members": [
             {"name": "Dr Ada Lovelace", "country": "UK", "slug": "ada-lovelace"},
             {"name": "Prof. Alan Turing", "country": "UK", "slug": "alan-turing"},
             {"name": "Dr Grace Hopper", "country": "US", "slug": "grace-hopper"},
         ]},
    )


def test_panel_edges_carry_their_edition():
    graph = build(_three_members(), programme={"annualConferences":
                  _edition("2026", [["Ada Lovelace", "Alan Turing", "Jane Doe"]])})
    panels = [e for e in graph["edges"] if e.get("type") == "panel"]
    assert panels == [{"source": "ada-lovelace", "target": "alan-turing",
                       "type": "panel", "weight": 1, "year": "2026"}]
    assert graph["stats"]["panel_editions"] == ["2026"]


def test_two_editions_stay_separate_edges(monkeypatch):
    """#1584: the same pair sharing a panel in two editions is two edges, not one
    with weight 2, so an edition filter has something to filter on."""
    ac = _edition("2026", [["Ada Lovelace", "Alan Turing"]])
    ac.update(_edition("2027", [["Ada Lovelace", "Alan Turing"],
                                ["Ada Lovelace", "Grace Hopper"]]))
    graph = build(_three_members(), programme={"annualConferences": ac})
    panels = [e for e in graph["edges"] if e.get("type") == "panel"]
    assert [(e["year"], e["source"], e["target"], e["weight"]) for e in panels] == [
        ("2026", "ada-lovelace", "alan-turing", 1),
        ("2027", "ada-lovelace", "alan-turing", 1),
        ("2027", "ada-lovelace", "grace-hopper", 1),
    ]
    assert graph["stats"]["panel_editions"] == ["2026", "2027"]
    assert graph["stats"]["panels_matched"] == 3


def test_frozen_snapshot_wins_over_the_live_sync(tmp_path, monkeypatch):
    """load_programmes prefers data/essc-<year>-programme.json where both files
    carry the same edition, since the frozen copy is the record of what happened."""
    monkeypatch.setattr(build_network_map, "REPO", tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "indico.json").write_text(json.dumps(
        {"annualConferences": {"2026": {"stale": True}, "2027": {"live": True}}}))
    (tmp_path / "data" / "essc-2026-programme.json").write_text(json.dumps(
        {"annualConferences": {"2026": {"frozen": True}}}))
    merged = build_network_map.load_programmes()["annualConferences"]
    assert merged == {"2026": {"frozen": True}, "2027": {"live": True}}


def test_load_programmes_returns_none_with_no_files(tmp_path, monkeypatch):
    monkeypatch.setattr(build_network_map, "REPO", tmp_path)
    (tmp_path / "data").mkdir()
    assert build_network_map.load_programmes() is None
