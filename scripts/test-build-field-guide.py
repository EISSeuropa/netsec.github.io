#!/usr/bin/env python3
"""Test suite for scripts/build-field-guide.py.

The module is loaded via importlib from its hyphenated path (hyphens
block import-by-name). Page IO is routed through tmp_path by
monkeypatching the module-level ROOT / LOCALES file paths; no network,
no mutation of tracked files.

Covered logic:
  * keyword_slug        matches people.html's keywordSlug() on real themes
  * _initials/_surname  salutation-stripped monogram + sort key
  * members_for         keyword-overlap match, leadership-then-strength
                        ordering, no-match and no-keywords empties
  * render_facepile     avatar anchors (photo + monogram), cap + overflow
                        disc, singular/plural trailing link, theme href,
                        zero-match empty, locale people page
  * warn_unmatched_keywords  warns on a keyword no member has
  * render_sources      external links, empty list, url-less entry
  * render_concept      <dt id="fg-…"> + <dd>, definition leads as first
                        <p> (DefinedTerm-safe), facepile / sources follow
  * render_section      sentinels wrap the section, heading + intro
  * replace_region      idempotent swap, sentinel-respecting, raises
  * build / main        all locales, --check + write path

Run standalone:  /usr/bin/python3 scripts/test-build-field-guide.py
Or under pytest: python3 -m pytest scripts/test-build-field-guide.py -q
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path

_MOD_PATH = Path(__file__).resolve().parent / "build-field-guide.py"
_spec = importlib.util.spec_from_file_location("build_field_guide", _MOD_PATH)
bfg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bfg)


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------
def _concept(term, en, fr="FR def", de="DE def", theme=None, match=None, sources=None):
    c = {"term": term, "definition": {"en": en, "fr": fr, "de": de}}
    if theme is not None:
        c["theme"] = theme
    if match is not None:
        c["match_keywords"] = match
    if sources is not None:
        c["sources"] = sources
    return c


# A leader (role), a co-lead, a plain member, a photo-less member, and a
# member with no keywords at all.
_MEMBERS = [
    {"id": "ada-lovelace", "name": "Dr Ada Lovelace", "roles": ["WG1 Lead"],
     "canonical_keywords": ["Cyber security", "Defence"],
     "photo": "assets/images/people/ada-lovelace.jpg"},
    {"id": "bob-stone", "name": "Mr Bob Stone", "roles": [],
     "canonical_keywords": ["Cyber security"], "photo": ""},
    {"id": "cara-iqbal", "name": "Cara Iqbal", "wg_leadership": {"co_lead": [2]},
     "canonical_keywords": ["Defence"],
     "photo": "assets/images/people/cara-iqbal.jpg"},
    {"id": "dan-ng", "name": "Dr Dan Ng",
     "canonical_keywords": ["Industrial policy"]},
    {"id": "eve-park", "name": "Eve Park", "canonical_keywords": []},
]

_PAGE_TEMPLATE = (
    "<main>\n"
    '  <section class="glossary-section">\n'
    '    <dl class="glossary-dl">\n'
    '      <dt id="action">Action</dt>\n'
    "      <dd>An admin term that must survive.</dd>\n"
    "    </dl>\n"
    "  </section>\n\n"
    "  <!-- field-guide:start -->\n"
    "  <!-- field-guide:end -->\n\n"
    "  <p>footer</p>\n"
    "</main>\n"
)


# --------------------------------------------------------------------------
# keyword_slug
# --------------------------------------------------------------------------
def test_keyword_slug_real_themes():
    assert bfg.keyword_slug("Foreign policy and diplomacy") == "foreign-policy-and-diplomacy"
    assert bfg.keyword_slug("Security and defence") == "security-and-defence"
    assert (
        bfg.keyword_slug("European and transatlantic security order")
        == "european-and-transatlantic-security-order"
    )


def test_keyword_slug_strips_punctuation_and_edges():
    assert bfg.keyword_slug("Intelligence, information and influence") == "intelligence-information-and-influence"
    assert bfg.keyword_slug("  --Hello, World!--  ") == "hello-world"
    assert bfg.keyword_slug("") == ""
    assert bfg.keyword_slug(None) == ""


def test_keyword_slug_no_underscores_leak():
    assert bfg.keyword_slug("a_b c") == "a-b-c"


# --------------------------------------------------------------------------
# name helpers
# --------------------------------------------------------------------------
def test_strip_salutation_and_surname_and_initials():
    assert bfg._strip_salutation("Dr Ada Lovelace") == "Ada Lovelace"
    assert bfg._strip_salutation("Dr. Moritz Weiss") == "Moritz Weiss"
    assert bfg._surname_key("Dr John N.T. Helferich") == "helferich"
    assert bfg._surname_key("Cara Iqbal") == "iqbal"
    assert bfg._initials("Mr Felix Kösterke") == "FK"
    assert bfg._initials("Madonna") == "M"
    assert bfg._initials("") == "?"


def test_is_leader():
    assert bfg._is_leader({"roles": ["WG1 Lead"]}) is True
    assert bfg._is_leader({"wg_leadership": {"co_lead": [2]}}) is True
    assert bfg._is_leader({"roles": [], "wg_leadership": {}}) is False
    assert bfg._is_leader({}) is False


# --------------------------------------------------------------------------
# members_for
# --------------------------------------------------------------------------
def test_members_for_orders_leader_then_strength_then_surname():
    c = _concept("X", "d", match=["Cyber security", "Defence"])
    ids = [m["id"] for m in bfg.members_for(c, _MEMBERS)]
    # ada: leader, strength 2.  cara: leader, strength 1.  bob: non-leader,
    # strength 1.  dan/eve: no overlap.
    assert ids == ["ada-lovelace", "cara-iqbal", "bob-stone"]


def test_members_for_case_insensitive():
    c = _concept("X", "d", match=["cyber SECURITY"])
    ids = [m["id"] for m in bfg.members_for(c, _MEMBERS)]
    assert ids == ["ada-lovelace", "bob-stone"]


def test_members_for_empty_without_match_keywords_or_overlap():
    assert bfg.members_for(_concept("X", "d"), _MEMBERS) == []
    assert bfg.members_for(_concept("X", "d", match=["Quantum"]), _MEMBERS) == []


# --------------------------------------------------------------------------
# render_facepile
# --------------------------------------------------------------------------
def test_render_facepile_markup_photo_and_monogram():
    c = _concept("X", "d", theme="Security and defence", match=["Cyber security", "Defence"])
    out = bfg.render_facepile("en", c, _MEMBERS)
    # Photo member -> img with empty alt; popover-wired anchor.
    assert '<a class="member-link fg-face" data-member="ada-lovelace"' in out
    assert 'href="people.html#ada-lovelace"' in out
    assert 'aria-label="Open the profile of Dr Ada Lovelace"' in out
    assert 'src="assets/images/people/ada-lovelace.jpg" alt=""' in out
    # Photo-less member -> monogram, not an <img>.
    assert '<span class="fg-initials" aria-hidden="true">BS</span>' in out
    # Trailing link points at the theme view, plural count = 3 matched.
    assert 'class="fg-people-link" href="people.html#themes=security-and-defence"' in out
    assert "See 3 members working on this" in out
    # No overflow disc below the cap.
    assert "fg-face-more" not in out


def test_render_facepile_caps_and_shows_overflow_disc():
    many = [
        {"id": f"m{i}", "name": f"Person {i}", "canonical_keywords": ["Defence"]}
        for i in range(7)
    ]
    c = _concept("X", "d", theme="Security and defence", match=["Defence"])
    out = bfg.render_facepile("en", c, many)
    assert out.count('class="member-link fg-face"') == bfg.FACEPILE_MAX
    assert '<a class="fg-face fg-face-more"' in out
    assert ">+2</a>" in out
    assert 'aria-label="2 more"' in out
    assert "See 7 members working on this" in out


def test_render_facepile_singular_no_disc():
    c = _concept("X", "d", theme="Security and defence", match=["Industrial policy"])
    out = bfg.render_facepile("en", c, _MEMBERS)
    assert "See 1 member working on this" in out
    assert "1 members" not in out
    assert "fg-face-more" not in out


def test_render_facepile_empty_when_no_match():
    c = _concept("X", "d", theme="Security and defence", match=["Quantum"])
    assert bfg.render_facepile("en", c, _MEMBERS) == ""
    assert bfg.render_facepile("en", _concept("X", "d"), _MEMBERS) == ""


def test_render_facepile_locale_people_page():
    c = _concept("X", "d", theme="Security and defence", match=["Defence"])
    fr = bfg.render_facepile("fr", c, _MEMBERS)
    assert "people.fr.html#themes=security-and-defence" in fr
    assert "people.fr.html#cara-iqbal" in fr
    assert "Ouvrir le profil de" in fr


# --------------------------------------------------------------------------
# warn_unmatched_keywords
# --------------------------------------------------------------------------
def test_warn_unmatched_keywords_flags_unknown():
    concepts = [_concept("X", "d", match=["Defence", "Quantum"])]
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        bfg.warn_unmatched_keywords(concepts, _MEMBERS)
    err = buf.getvalue()
    assert "Quantum" in err
    assert "Defence" not in err  # Defence matches a member, no warning.


def test_warn_unmatched_keywords_silent_when_all_match():
    concepts = [_concept("X", "d", match=["Defence", "Cyber security"])]
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        bfg.warn_unmatched_keywords(concepts, _MEMBERS)
    assert buf.getvalue() == ""


# --------------------------------------------------------------------------
# render_sources
# --------------------------------------------------------------------------
def test_render_sources_external_links():
    out = bfg.render_sources(bfg.LOCALES["en"], [{"label": "Official", "url": "https://europa.eu/x"}])
    assert 'target="_blank"' in out and 'rel="noopener"' in out
    assert "https://europa.eu/x" in out
    assert "Sources" in out


def test_render_sources_empty_and_urlless():
    assert bfg.render_sources(bfg.LOCALES["en"], []) == ""
    assert bfg.render_sources(bfg.LOCALES["en"], [{"label": "No URL"}]) == ""


# --------------------------------------------------------------------------
# render_concept
# --------------------------------------------------------------------------
def test_render_concept_has_dt_id_and_locale_def():
    c = _concept("CSDP", "EN definition", fr="Définition FR", de="DE Definition",
                 theme="Security and defence", match=["Defence"])
    assert '<dt id="fg-csdp">CSDP</dt>' in bfg.render_concept("en", c, _MEMBERS)
    assert "EN definition" in bfg.render_concept("en", c, _MEMBERS)
    assert "Définition FR" in bfg.render_concept("fr", c, _MEMBERS)
    assert "DE Definition" in bfg.render_concept("de", c, _MEMBERS)


def test_render_concept_definition_leads_as_first_paragraph():
    # The DefinedTerm extractor reads the leading <p>; member names live in
    # the facepile that follows it, so they must not be inside that <p>.
    c = _concept("CSDP", "Just the definition.", theme="Security and defence", match=["Defence"])
    out = bfg.render_concept("en", c, _MEMBERS)
    first_p = out.split("</p>", 1)[0]
    assert "Just the definition." in first_p
    assert "Cara" not in first_p and "fg-face" not in first_p
    # The facepile is present, just after the paragraph.
    assert "fg-facepile" in out


def test_render_concept_without_match_or_sources():
    c = _concept("Plain", "Just a definition.")
    out = bfg.render_concept("en", c, _MEMBERS)
    assert '<dt id="fg-plain">Plain</dt>' in out
    assert "fg-facepile" not in out
    assert "fg-sources" not in out


def test_render_concept_escapes_html():
    out = bfg.render_concept("en", _concept("A & B", "Less < than > more."), _MEMBERS)
    assert "A &amp; B" in out
    assert "&lt; than &gt;" in out


# --------------------------------------------------------------------------
# render_section
# --------------------------------------------------------------------------
def test_render_section_wraps_sentinels_and_heading():
    out = bfg.render_section("en", [_concept("X", "Def X")], _MEMBERS)
    assert out.startswith(bfg.START)
    assert out.rstrip().endswith(bfg.END)
    assert '<h2 id="field-guide">Concepts in European security studies</h2>' in out
    assert 'class="fg-intro"' in out


def test_render_section_locale_headings():
    assert "Concepts en études de sécurité européenne" in bfg.render_section("fr", [_concept("X", "d")], _MEMBERS)
    assert "Konzepte der europäischen Sicherheitsforschung" in bfg.render_section("de", [_concept("X", "d")], _MEMBERS)


# --------------------------------------------------------------------------
# replace_region
# --------------------------------------------------------------------------
def test_replace_region_idempotent():
    region = bfg.render_section("en", [_concept("X", "Def X")], _MEMBERS)
    once = bfg.replace_region(_PAGE_TEMPLATE, region)
    assert once == bfg.replace_region(once, region)


def test_replace_region_preserves_admin_terms():
    region = bfg.render_section("en", [_concept("X", "Def X")], _MEMBERS)
    out = bfg.replace_region(_PAGE_TEMPLATE, region)
    assert '<dt id="action">Action</dt>' in out
    assert "An admin term that must survive." in out
    assert "<p>footer</p>" in out


def test_replace_region_missing_sentinels_raises():
    try:
        bfg.replace_region("<main>no sentinels</main>", "x")
    except ValueError:
        return
    raise AssertionError("expected ValueError on missing sentinels")


# --------------------------------------------------------------------------
# build + main (globals monkeypatched to tmp paths)
# --------------------------------------------------------------------------
def _wire_tmp(tmp_path, concepts):
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "data" / "field-guide.json").write_text(json.dumps({"concepts": concepts}), encoding="utf-8")
    (tmp_path / "data" / "bios.json").write_text(json.dumps({"members": _MEMBERS}), encoding="utf-8")
    for loc in bfg.LOCALES:
        (tmp_path / bfg.LOCALES[loc]["file"]).write_text(_PAGE_TEMPLATE, encoding="utf-8")
    bfg.ROOT = tmp_path
    bfg.DATA = tmp_path / "data" / "field-guide.json"
    bfg.BIOS = tmp_path / "data" / "bios.json"


def _restore():
    bfg.ROOT = _MOD_PATH.resolve().parent.parent
    bfg.DATA = bfg.ROOT / "data" / "field-guide.json"
    bfg.BIOS = bfg.ROOT / "data" / "bios.json"


def test_build_all_locales_get_their_definition(tmp_path):
    concepts = [_concept("CSDP", "EN authoritative", fr="Texte FR", de="DE Text",
                         theme="Security and defence", match=["Defence"])]
    _wire_tmp(tmp_path, concepts)
    try:
        assert "EN authoritative" in bfg.build("en", concepts, _MEMBERS)
        assert "Texte FR" in bfg.build("fr", concepts, _MEMBERS)
        assert "DE Text" in bfg.build("de", concepts, _MEMBERS)
        # Defence matches ada + cara = 2.
        assert "See 2 members working on this" in bfg.build("en", concepts, _MEMBERS)
    finally:
        _restore()


def test_main_write_then_check_roundtrip(tmp_path, monkeypatch):
    concepts = [_concept("X", "Def X", theme="Security and defence", match=["Defence"])]
    _wire_tmp(tmp_path, concepts)
    try:
        monkeypatch.setattr("sys.argv", ["build-field-guide.py"])
        assert bfg.main() == 0
        monkeypatch.setattr("sys.argv", ["build-field-guide.py", "--check"])
        assert bfg.main() == 0
    finally:
        _restore()


def test_main_check_fails_on_drift(tmp_path, monkeypatch):
    _wire_tmp(tmp_path, [_concept("X", "Def X")])
    try:
        monkeypatch.setattr("sys.argv", ["build-field-guide.py", "--check"])
        assert bfg.main() == 1
    finally:
        _restore()


# --------------------------------------------------------------------------
# Real-fixture smoke: the tracked data/field-guide.json renders.
# --------------------------------------------------------------------------
def test_real_field_guide_json_renders():
    repo = _MOD_PATH.resolve().parent.parent
    data_path = repo / "data" / "field-guide.json"
    if not data_path.exists():
        return
    data = json.loads(data_path.read_text(encoding="utf-8"))
    bios = json.loads((repo / "data" / "bios.json").read_text(encoding="utf-8"))
    members = bios.get("members", [])
    for loc in bfg.LOCALES:
        section = bfg.render_section(loc, data["concepts"], members)
        assert bfg.START in section and bfg.END in section
        for c in data["concepts"]:
            assert bfg.keyword_slug(c["term"]) in section


def test_real_field_guide_entry_shape():
    """Every real concept carries a headword and all three locale definitions,
    and every source is a {label, url} pair with non-empty values. Guards new
    entries (e.g. the EU defence-instrument batch, issue #998) against a
    missing FR/DE definition or a malformed citation slipping in."""
    repo = _MOD_PATH.resolve().parent.parent
    data_path = repo / "data" / "field-guide.json"
    if not data_path.exists():
        return
    data = json.loads(data_path.read_text(encoding="utf-8"))
    for c in data["concepts"]:
        assert c.get("term", "").strip(), f"concept missing term: {c}"
        defn = c.get("definition") or {}
        for lang in ("en", "fr", "de"):
            assert defn.get(lang, "").strip(), f"{c['term']}: missing {lang} definition"
        for src in c.get("sources") or []:
            assert src.get("label", "").strip(), f"{c['term']}: source missing label"
            assert src.get("url", "").strip().startswith("http"), f"{c['term']}: bad source url"


# --------------------------------------------------------------------------
# Standalone runner (no pytest dependency).
# --------------------------------------------------------------------------
def _standalone() -> int:
    import tempfile
    import types

    class _MonkeyPatch:
        def setattr(self, target, name, value=None):
            if value is None:
                import sys as _sys
                _sys.argv = name
                return
            setattr(target, name, value)

    failures = []
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and isinstance(f, types.FunctionType)]
    for name, fn in tests:
        try:
            params = fn.__code__.co_varnames[: fn.__code__.co_argcount]
            kwargs = {}
            if "tmp_path" in params:
                kwargs["tmp_path"] = Path(tempfile.mkdtemp())
            if "monkeypatch" in params:
                kwargs["monkeypatch"] = _MonkeyPatch()
            fn(**kwargs)
            print(f"  ok  {name}")
        except Exception as exc:  # noqa: BLE001
            failures.append((name, exc))
            print(f"FAIL  {name}: {exc}")
    print(f"\n{len(tests) - len(failures)}/{len(tests)} passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    import sys

    sys.exit(_standalone())
