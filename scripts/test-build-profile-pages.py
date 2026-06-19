#!/usr/bin/env python3
"""Tests for build-profile-pages.py — the enriched individual profile pages.

Covers the parts most likely to break silently: that the theme/region slug
matches the directory's own keywordSlug() (so the chip deep-links land
pre-filtered), the similar-people ranking, and that the card carries the new
hero + two-column structure with actionable CTAs.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "build_profile_pages", ROOT / "scripts" / "build-profile-pages.py")
bpp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bpp)

BIOS = json.loads((ROOT / "data" / "bios.json").read_text(encoding="utf-8"))
MEMBERS = [m for m in BIOS.get("members", []) if m.get("id")]
EN = bpp.LOCALES["en"]


def _reference_slug(s: str) -> str:
    """Faithful port of people-directory.js keywordSlug(): lowercase, collapse
    runs of non-alphanumerics to '-', trim. str.isalnum() is Unicode-aware,
    mirroring the JS \\p{L}\\p{N} class — so if a non-ASCII theme is ever
    added, this diverges from the ASCII area_slug() and the test fails,
    forcing both sides to be updated together."""
    out, prev_dash = [], False
    for ch in (s or "").lower():
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        elif not prev_dash:
            out.append("-")
            prev_dash = True
    return "".join(out).strip("-")


def test_area_slug_matches_directory_keyword_slug_for_live_vocab():
    # Every theme + region currently in the directory must slug identically on
    # both sides, or a profile chip's #themes=/#regions= deep link misses.
    vocab = set()
    for m in MEMBERS:
        vocab.update(m.get("themes") or [])
        vocab.update(m.get("regions") or [])
    assert vocab, "expected some themes/regions in bios.json"
    for term in vocab:
        assert bpp.area_slug(term) == _reference_slug(term), term


def test_similar_excludes_self_and_requires_overlap():
    target = next(m for m in MEMBERS if m["id"] == "moritz-weiss")
    sim = bpp.similar_members(target, MEMBERS)
    ids = [o["id"] for o in sim]
    assert target["id"] not in ids
    t_kw = set(target.get("canonical_keywords") or [])
    t_th = set(target.get("themes") or [])
    for o in sim:
        shared = (t_kw & set(o.get("canonical_keywords") or [])) or \
                 (t_th & set(o.get("themes") or []))
        assert shared, f"{o['id']} shares neither a keyword nor a theme"


def test_similar_ranks_by_shared_keyword_count():
    target = next(m for m in MEMBERS if m["id"] == "moritz-weiss")
    sim = bpp.similar_members(target, MEMBERS)
    t_kw = set(target.get("canonical_keywords") or [])
    overlaps = [len(t_kw & set(o.get("canonical_keywords") or [])) for o in sim]
    assert overlaps == sorted(overlaps, reverse=True), "not sorted by shared-keyword count"


def test_similar_empty_for_member_without_topics():
    bare = {"id": "x", "name": "Nobody", "canonical_keywords": [], "themes": []}
    assert bpp.similar_members(bare, MEMBERS) == []


def test_card_has_hero_two_columns_and_facepile():
    target = next(m for m in MEMBERS if m["id"] == "moritz-weiss")
    sim = bpp.similar_members(target, MEMBERS)
    html = bpp.render_card(target, [], sim, EN)
    for needle in ("profile-hero", "profile-cols", "profile-aside",
                   "pf-facepile", "profile-area-chip", "#themes="):
        assert needle in html, needle
    # Faces link to other members' own profile pages, not the directory.
    assert 'href="people/' in html


def test_mentor_badge_becomes_a_mailto_action_when_email_present():
    m = {"id": "t", "name": "Dr Test", "email": "t@example.org",
         "mentorship": ["mentor"], "canonical_keywords": [], "themes": []}
    html = bpp.render_card(m, [], [], EN)
    assert 'class="mentorship-badge is-offering is-action"' in html
    assert "mailto:t@example.org?subject=" in html


def test_mentor_badge_is_static_without_email():
    m = {"id": "t", "name": "Dr Test", "mentorship": ["mentor"],
         "canonical_keywords": [], "themes": []}
    html = bpp.render_card(m, [], [], EN)
    assert "mentorship-badge is-offering" in html
    assert "is-action" not in html
    assert "mailto:" not in html


def test_generate_produces_three_locales_per_member():
    pages = bpp.generate()
    assert len(pages) == len(MEMBERS) * 3
    # Spot-check the new aside survives the full page assembly.
    sample = next(v for k, v in pages.items() if k.endswith("moritz-weiss.html"))
    assert "profile-aside" in sample and "profile-hero" in sample


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
