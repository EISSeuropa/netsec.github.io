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
    html = bpp.render_card(target, [], sim, [], EN)
    for needle in ("profile-hero", "profile-cols", "profile-aside",
                   "pf-facepile", "profile-area-chip", "#themes="):
        assert needle in html, needle
    # Faces link to other members' own profile pages, not the directory.
    assert 'href="people/' in html


def test_affiliation_line_skips_an_institution_the_position_already_names():
    # #1506: a joint appointment spelled out in the position used to print the
    # institution twice in a row.
    m = {"id": "dup", "name": "Dr Dup",
         "position": "guest lecturer at Rīga Stradiņš University, RSU",
         "affiliation": "Rīga Stradiņš University, RSU", "country": "Latvia"}
    html = bpp.render_card(m, [], [], [], EN)
    assert "guest lecturer at Rīga Stradiņš University, RSU · Latvia" in html
    assert "RSU · Rīga Stradiņš University" not in html
    # An affiliation the position does not name still shows.
    other = dict(m, position="PhD candidate")
    assert "PhD candidate · Rīga Stradiņš University, RSU · Latvia" in bpp.render_card(
        other, [], [], [], EN)


def test_mentor_facepile_lists_on_topic_mentors_seniority_ordered():
    # Two mentors on the same topic; the inferred-seniority tiebreak orders the
    # senior one first, the non-mentor is excluded, and the facepile links into
    # the mentor-filtered directory.
    target = {"id": "seeker", "name": "Mr Seeker",
              "themes": ["Cyber and emerging technology"], "canonical_keywords": ["Cyber"]}
    senior = {"id": "snr", "name": "Prof. Senior", "position": "Professor",
              "mentorship": ["mentor"], "themes": ["Cyber and emerging technology"],
              "canonical_keywords": ["Cyber"]}
    junior = {"id": "jnr", "name": "Ms Junior", "position": "PhD candidate",
              "mentorship": ["mentor"], "themes": ["Cyber and emerging technology"],
              "canonical_keywords": ["Cyber"]}
    non_mentor = {"id": "nm", "name": "Dr NoMentor",
                  "themes": ["Cyber and emerging technology"], "canonical_keywords": ["Cyber"]}
    ranked = bpp.mentors_on_topics(target, [target, junior, senior, non_mentor])
    assert [m["id"] for m in ranked] == ["snr", "jnr"]
    assert bpp.career_stage(senior) == 3 and bpp.career_stage(junior) == 0
    html = bpp.render_card(target, [], [], ranked, EN)
    assert "profile-mentors" in html
    assert "mentorship=mentor" in html
    # No facepile when no on-topic mentor exists.
    assert "profile-mentors" not in bpp.render_card(target, [], [], [], EN)


def test_mentor_badge_becomes_a_mailto_action_when_email_present():
    m = {"id": "t", "name": "Dr Test", "email": "t@example.org",
         "mentorship": ["mentor"], "canonical_keywords": [], "themes": []}
    html = bpp.render_card(m, [], [], [], EN)
    assert 'class="mentorship-badge is-offering is-action"' in html
    assert "mailto:t@example.org?subject=" in html


def test_mentor_badge_is_static_without_email():
    m = {"id": "t", "name": "Dr Test", "mentorship": ["mentor"],
         "canonical_keywords": [], "themes": []}
    html = bpp.render_card(m, [], [], [], EN)
    assert "mentorship-badge is-offering" in html
    assert "is-action" not in html
    assert "mailto:" not in html


def test_prize_pill_renders_only_for_listed_winners():
    prizes = {k: v for k, v in json.loads(
        (ROOT / "data" / "prize-winners.json").read_text(encoding="utf-8")).items()
        if not k.startswith("_")}
    assert prizes, "expected at least one prize winner"
    # Every key must be a real directory member id.
    member_ids = {m["id"] for m in MEMBERS}
    for slug in prizes:
        assert slug in member_ids, f"prize-winners.json key {slug} is not a directory member"
    winner = next(iter(prizes))
    wm = next(m for m in MEMBERS if m["id"] == winner)
    html = bpp.render_card(wm, [], [], [], EN, prizes[winner])
    assert 'class="profile-prize-chip"' in html and 'lang="en"' in html
    # The pill is absent without prize data.
    assert "profile-prize-chip" not in bpp.render_card(wm, [], [], [], EN, None)


def test_every_card_has_the_anthology_slot_and_script():
    target = next(m for m in MEMBERS if m["id"] == "moritz-weiss")
    html = bpp.render_card(target, [], [], [], EN)
    assert 'class="profile-anthology-slot" hidden' in html
    # The inline runtime script that fills it ships on every built page.
    page = next(v for k, v in bpp.generate().items() if k.endswith("moritz-weiss.html"))
    assert "authors-index.json" in page and "profile-anthology-link" in page


def test_generate_produces_three_locales_per_member():
    pages = bpp.generate()
    assert len(pages) == len(MEMBERS) * 3
    # Spot-check the new aside survives the full page assembly.
    sample = next(v for k, v in pages.items() if k.endswith("moritz-weiss.html"))
    assert "profile-aside" in sample and "profile-hero" in sample


# ── Warm contact intro (#1171 part 1) ──

_INTRO_MEMBER = {
    "id": "t", "name": "Dr Test Person", "email": "t@example.org",
    "mentorship": ["mentor"], "stsm_hosting": "yes",
    "canonical_keywords": [], "themes": ["Cyber and emerging technology"],
}


def _decoded_bodies(html_out: str) -> list[str]:
    import re
    import urllib.parse
    return [urllib.parse.unquote(m)
            for m in re.findall(r'&amp;body=([^"]+)"', html_out)]


def test_action_mailto_carries_scaffold_body_with_theme_and_name():
    html_out = bpp.render_actions(_INTRO_MEMBER, EN)
    bodies = _decoded_bodies(html_out)
    assert len(bodies) == 2  # mentor badge + STSM badge
    mentor_body = bodies[0]
    assert "Dear Dr Test Person," in mentor_body
    assert "I found your profile in the NetSec directory." in mentor_body
    assert "I was drawn by your work on Cyber and emerging technology." in mentor_body
    assert "[your name]" in mentor_body            # editable blanks survive
    assert "\r\n" in mentor_body                   # RFC 6068 line breaks
    assert "e-COST" in bodies[1]                   # the STSM body is the STSM one


def test_action_mailto_body_and_subject_are_localised_per_page_locale():
    import urllib.parse
    for lang, body_probe, subject_probe in (
        ("fr", "J'ai trouvé votre profil", "Demande de mentorat"),
        ("de", "ich habe Ihr Profil", "Mentoring-Anfrage"),
    ):
        html_out = bpp.render_actions(_INTRO_MEMBER, bpp.LOCALES[lang])
        assert body_probe in _decoded_bodies(html_out)[0], lang
        subjects = [urllib.parse.unquote(m) for m in
                    __import__("re").findall(r'\?subject=([^&"]+)', html_out)]
        assert any(subject_probe in s for s in subjects), lang


def test_action_without_email_stays_a_passive_badge():
    m = dict(_INTRO_MEMBER, email="")
    html_out = bpp.render_actions(m, EN)
    assert "mailto:" not in html_out and "<span" in html_out


def test_scaffold_parity_with_site_js_catalog():
    """The scaffold texts live twice: SCAFFOLDS here (baked into profile-page
    hrefs) and the site.js I18N catalog (used by the directory at runtime).
    This test extracts the FR and DE catalog values from site.js and asserts
    byte-for-byte equality with SCAFFOLDS, so an edit to one home without the
    other fails CI instead of shipping drift."""
    import re
    js = (ROOT / "assets" / "js" / "site.js").read_text(encoding="utf-8")

    def js_value(en_key: str, occurrence: int) -> str:
        lit = re.escape(en_key.replace("\\", "\\\\").replace("\n", "\\n"))
        pat = re.compile(r"(['\"])" + lit + r"\1\s*:\s*(?P<q>['\"])"
                         r"(?P<v>(?:\\.|(?!(?P=q))[^\\\n])*)(?P=q)")
        matches = [m.group("v") for m in pat.finditer(js)]
        assert len(matches) >= occurrence + 1, f"missing catalog entry: {en_key[:50]!r}"
        return (matches[occurrence]
                .replace("\\n", "\n").replace("\\'", "'").replace('\\"', '"'))

    en = bpp.SCAFFOLDS["en"]
    for occurrence, lang in ((0, "fr"), (1, "de")):
        for key in ("subject_mentor", "subject_mentee", "subject_stsm",
                    "areas_own", "mentor", "mentee", "stsm"):
            assert js_value(en[key], occurrence) == bpp.SCAFFOLDS[lang][key], \
                f"{lang}/{key} drifted between site.js and SCAFFOLDS"


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
