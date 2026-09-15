#!/usr/bin/env python3
"""pytest suite for scripts/build-year-review.py and _member_series.py.

The module is loaded via importlib from its hyphenated path (hyphens
block import-by-name). All IO is routed through tmp_path by pointing
the module's ROOT and OUT globals at a fixture tree, so no tracked
file is read or written.

Covered logic:
  * window / quarters     Action-year bounds and the 10 October
                          boundary, including the leap-year window
  * news / events /
    outputs / releases    window filtering at both edges, locale-map
                          normalisation, minor-only release picks,
                          version ordering for same-day releases
  * hand block            preserved across a rebuild, per locale, and
                          independently per edition
  * build                 a second edition is additive and ordered
  * monthly_member_counts one point per month, the month's last commit,
                          the `until` ceiling, unreadable blobs dropped

Run: python3 -m pytest scripts/test-build-year-review.py -q
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
from datetime import date
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent


def _load(name: str, mod_name: str):
    spec = importlib.util.spec_from_file_location(mod_name, _HERE / name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


byr = _load("build-year-review.py", "build_year_review")
ms = _load("_member_series.py", "member_series")


# --------------------------------------------------------------------------
# Fixture tree
# --------------------------------------------------------------------------
CHANGELOG = """# Changelog

## [Unreleased]

## [1.3.0] · 2026-10-09 — Last day in window
## [1.2.0] · 2026-05-21 — Second minor
## [1.1.0] · 2026-05-21 — First minor
## [1.0.1] · 2026-05-20 — A patch
## [0.9.0] · 2025-10-09 — Day before the window
"""

NEWS = {
    "items": [
        {
            "id": "in-window",
            "pubDate": "2026-06-12T10:00:00+02:00",
            "displayDate": {"en": "12 June 2026", "fr": "12 juin 2026", "de": "12. Juni 2026"},
            "title": {"en": "In", "fr": "Dedans", "de": "Drin"},
            "type": "event",
            "wg": 2,
        },
        {
            "id": "first-day",
            "pubDate": "2025-10-10T09:00:00+02:00",
            "title": {"en": "Launch", "fr": "Lancement", "de": "Start"},
            "type": "announcement",
            "wg": 1,
        },
        {
            "id": "too-early",
            "pubDate": "2025-10-09T23:00:00+02:00",
            "title": {"en": "Before", "fr": "Avant", "de": "Vorher"},
            "type": "announcement",
        },
        {
            "id": "too-late",
            "pubDate": "2026-10-10T09:00:00+02:00",
            "title": {"en": "After", "fr": "Après", "de": "Danach"},
            "type": "announcement",
        },
    ]
}

EVENTS = {
    "events": [
        {
            "uid": "held@x",
            "start": "2026-06-09T09:00",
            "displayDate": {"en": "9–11 June 2026", "fr": "9–11 juin 2026", "de": "9.–11. Juni 2026"},
            "cardTitle": {"en": "Summer School", "fr": "École", "de": "Sommerschule"},
            "cardLocation": {"en": "Stockholm", "fr": "Stockholm", "de": "Stockholm"},
            "eventType": "training-school",
            "status": "CONFIRMED",
        },
        {
            # No card fields: falls back to the .ics summary/location,
            # which are bare strings rather than locale maps.
            "uid": "bare@x",
            "start": "2026-02-01T09:00",
            "summary": "Bare event",
            "location": "Leiden",
            "eventType": "workshop",
            "status": "CONFIRMED",
        },
        {"uid": "next-year@x", "start": "2026-10-10T09:00", "summary": "Next"},
    ]
}

PUBS = {
    "publications": [
        {
            "date": "2026-10",
            "title": {"en": "Brief", "fr": "Note", "de": "Papier"},
            "type": "policy-brief",
            "authors": ["A Person"],
            "doi": "10.0/x",
        },
        {"date": "2025-09", "title": {"en": "Earlier"}, "type": "report"},
    ]
}

BIOS = {
    "members": [
        {"id": "a", "name": "A", "country_code": "NL", "themes": ["Cyber", "Strategy"]},
        {"id": "b", "name": "B", "country_code": "NL", "themes": ["Cyber"]},
        {"id": "c", "name": "C", "country_code": "FR", "themes": []},
        {"id": "d", "name": "D", "country_code": "", "country": ""},
    ]
}


@pytest.fixture
def tree(tmp_path, monkeypatch):
    """A repo-shaped fixture tree with the module pointed at it."""
    (tmp_path / "data").mkdir()
    (tmp_path / "CHANGELOG.md").write_text(CHANGELOG, encoding="utf-8")
    for name, payload in (
        ("news.json", NEWS),
        ("events.json", EVENTS),
        ("publications.json", PUBS),
        ("bios.json", BIOS),
    ):
        (tmp_path / "data" / name).write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(byr, "ROOT", tmp_path)
    monkeypatch.setattr(byr, "OUT", tmp_path / "data" / "year-review.json")
    # The member series needs a git repo; the walk itself is tested
    # separately against a real one.
    monkeypatch.setattr(byr, "monthly_member_counts", lambda root, until=None: [])
    return tmp_path


# --------------------------------------------------------------------------
# window / quarters
# --------------------------------------------------------------------------
def test_window_year_one_is_the_action_year():
    assert byr.window(1) == ("2025-10-10", "2026-10-09")


def test_window_year_two_starts_the_day_after_year_one_ends():
    assert byr.window(2) == ("2026-10-10", "2027-10-09")


def test_window_spans_a_leap_day():
    """Year 3 contains 29 February 2028, so the end bound has to come
    from date arithmetic rather than a 365-day offset."""
    start, end = byr.window(3)
    assert (start, end) == ("2027-10-10", "2028-10-09")
    assert (date.fromisoformat(end) - date.fromisoformat(start)).days == 365


def test_quarters_tile_the_window_without_gap_or_overlap():
    start, end = byr.window(1)
    qs = byr.quarters(start, end)
    assert [q["n"] for q in qs] == [1, 2, 3, 4]
    assert qs[0]["from"] == start
    assert qs[-1]["to"] == end
    for earlier, later in zip(qs, qs[1:]):
        gap = date.fromisoformat(later["from"]) - date.fromisoformat(earlier["to"])
        assert gap.days == 1


# --------------------------------------------------------------------------
# Fact gathering
# --------------------------------------------------------------------------
def test_news_filters_on_both_window_edges(tree):
    items = byr.news_items("2025-10-10", "2026-10-09")
    assert [i["id"] for i in items] == ["first-day", "in-window"]


def test_news_without_a_display_date_falls_back_to_the_iso_day(tree):
    items = byr.news_items("2025-10-10", "2026-10-09")
    first = next(i for i in items if i["id"] == "first-day")
    assert first["displayDate"] == {
        "en": "2025-10-10",
        "fr": "2025-10-10",
        "de": "2025-10-10",
    }


def test_events_fall_back_to_the_calendar_summary_in_every_locale(tree):
    held = byr.events_held("2025-10-10", "2026-10-09")
    assert [e["uid"] for e in held] == ["bare@x", "held@x"]
    bare = held[0]
    assert bare["title"] == {"en": "Bare event", "fr": "Bare event", "de": "Bare event"}
    assert bare["location"]["de"] == "Leiden"


def test_outputs_compare_on_the_month(tree):
    """publications.json dates are year-month, so October 2026 belongs
    to year 1 even though the window ends on the 9th."""
    pubs = byr.outputs("2025-10-10", "2026-10-09")
    assert [p["date"] for p in pubs] == ["2026-10"]
    assert pubs[0]["url"] == "10.0/x"


def test_releases_count_patches_but_only_list_minors(tree):
    total, minors = byr.releases("2025-10-10", "2026-10-09")
    assert total == 4
    assert [r["version"] for r in minors] == ["1.1.0", "1.2.0", "1.3.0"]


def test_same_day_releases_order_by_version(tree):
    _, minors = byr.releases("2026-05-21", "2026-05-21")
    assert [r["version"] for r in minors] == ["1.1.0", "1.2.0"]


def test_release_outside_the_window_is_dropped(tree):
    total, minors = byr.releases("2025-10-10", "2026-10-09")
    assert "0.9.0" not in [r["version"] for r in minors]
    assert total == 4


def test_directory_snapshot_counts_distinct_countries_and_ranks_themes(tree):
    snap = byr.directory_snapshot()
    assert snap["members"] == 4
    assert snap["countries"] == 2  # NL, FR; the blank one is not a country
    assert snap["themes"] == [
        {"name": "Cyber", "members": 2},
        {"name": "Strategy", "members": 1},
    ]


# --------------------------------------------------------------------------
# Edition assembly
# --------------------------------------------------------------------------
def test_edition_quarters_reference_the_items_by_id(tree):
    ed = byr.build_edition(1)
    q3 = ed["quarters"][2]
    assert q3["news"] == ["in-window"]
    assert q3["events"] == ["held@x"]
    assert ed["quarters"][1]["events"] == ["bare@x"]


def test_edition_stats_match_the_gathered_lists(tree):
    ed = byr.build_edition(1)
    assert ed["stats"] == {
        "members": 4,
        "countries": 2,
        "events": 2,
        "outputs": 1,
        "news": 2,
        "releases": 4,
    }


def test_rebuild_preserves_the_hand_block(tree):
    byr.main([])
    out = byr.OUT
    data = json.loads(out.read_text(encoding="utf-8"))
    data["editions"][0]["hand"]["lede"]["fr"] = "Une année."
    out.write_text(json.dumps(data), encoding="utf-8")

    byr.main([])
    after = json.loads(out.read_text(encoding="utf-8"))
    assert after["editions"][0]["hand"]["lede"]["fr"] == "Une année."
    assert after["editions"][0]["hand"]["lede"]["en"] == ""


def test_a_second_edition_is_additive_and_ordered(tree):
    byr.main([])
    byr.main(["--year", "2"])
    data = json.loads(byr.OUT.read_text(encoding="utf-8"))
    assert [e["year"] for e in data["editions"]] == [1, 2]
    assert data["editions"][1]["window"]["from"] == "2026-10-10"


def test_the_hand_block_of_another_edition_is_left_alone(tree):
    byr.main([])
    byr.main(["--year", "2"])
    data = json.loads(byr.OUT.read_text(encoding="utf-8"))
    data["editions"][0]["hand"]["outlook"]["de"] = "Ausblick."
    byr.OUT.write_text(json.dumps(data), encoding="utf-8")

    byr.main(["--year", "2"])
    after = json.loads(byr.OUT.read_text(encoding="utf-8"))
    assert after["editions"][0]["hand"]["outlook"]["de"] == "Ausblick."


def test_a_corrupt_output_file_does_not_stop_a_rebuild(tree):
    byr.OUT.write_text("{ not json", encoding="utf-8")
    assert byr.main([]) == 0
    data = json.loads(byr.OUT.read_text(encoding="utf-8"))
    assert [e["year"] for e in data["editions"]] == [1]


def test_year_zero_is_rejected(tree):
    assert byr.main(["--year", "0"]) == 1


# --------------------------------------------------------------------------
# monthly_member_counts, against a real throwaway repo
# --------------------------------------------------------------------------
def _commit(repo: Path, members: int, when: str, raw: str | None = None):
    (repo / "data").mkdir(exist_ok=True)
    body = raw if raw is not None else json.dumps(
        {"members": [{"id": str(i), "name": str(i)} for i in range(members)]}
    )
    (repo / "data" / "bios.json").write_text(body, encoding="utf-8")
    env = {
        "GIT_AUTHOR_DATE": when,
        "GIT_COMMITTER_DATE": when,
        "GIT_AUTHOR_NAME": "T",
        "GIT_AUTHOR_EMAIL": "t@example.org",
        "GIT_COMMITTER_NAME": "T",
        "GIT_COMMITTER_EMAIL": "t@example.org",
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(repo),
    }
    subprocess.run(["git", "add", "data/bios.json"], cwd=repo, check=True, env=env)
    subprocess.run(
        ["git", "commit", "-q", "-m", f"{members} members"],
        cwd=repo,
        check=True,
        env=env,
    )


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"], cwd=tmp_path, check=True
    )
    return tmp_path


def test_series_takes_the_last_commit_of_each_month(repo):
    _commit(repo, 3, "2026-05-02T10:00:00+00:00")
    _commit(repo, 7, "2026-05-28T10:00:00+00:00")
    _commit(repo, 9, "2026-06-04T10:00:00+00:00")
    assert ms.monthly_member_counts(repo) == [
        {"month": "2026-05", "date": "2026-05-28", "members": 7},
        {"month": "2026-06", "date": "2026-06-04", "members": 9},
    ]


def test_series_honours_the_until_ceiling(repo):
    _commit(repo, 3, "2026-05-02T10:00:00+00:00")
    _commit(repo, 9, "2026-06-04T10:00:00+00:00")
    series = ms.monthly_member_counts(repo, until="2026-05-31")
    assert [p["month"] for p in series] == ["2026-05"]


def test_an_unreadable_revision_drops_its_point(repo):
    _commit(repo, 3, "2026-05-02T10:00:00+00:00")
    _commit(repo, 0, "2026-06-04T10:00:00+00:00", raw="{ broken")
    _commit(repo, 5, "2026-07-04T10:00:00+00:00")
    assert [p["month"] for p in ms.monthly_member_counts(repo)] == [
        "2026-05",
        "2026-07",
    ]


def test_a_full_clone_is_not_flagged_shallow(repo):
    _commit(repo, 1, "2026-05-02T10:00:00+00:00")
    assert ms.shallow(repo) is False
