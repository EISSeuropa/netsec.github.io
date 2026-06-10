#!/usr/bin/env python3
"""Test suite for scripts/build-field-guide.py.

The module is loaded via importlib from its hyphenated path (hyphens
block import-by-name). Page IO is routed through tmp_path by
monkeypatching the module-level ROOT / LOCALES file paths; no network,
no mutation of tracked files.

Covered logic:
  * keyword_slug       matches people.html's keywordSlug() on the
                       real theme names
  * theme_counts       counts members per theme from a bios-shaped dict
  * render_members_link plural / singular / count-free fallbacks, and
                       the no-theme empty string
  * render_sources     external links, empty list, url-less entry
  * render_concept     <dt id="fg-…"> + <dd>, locale-appropriate def,
                       theme-less / sources-less entries still render
  * render_section     sentinels wrap the section, heading + intro per
                       locale
  * replace_region     idempotent swap, sentinel-respecting, missing
                       sentinels raise
  * build              all three locales get their own definition
  * main               --check (in-sync / drift) and the write path

Run standalone:  /usr/bin/python3 scripts/test-build-field-guide.py
Or under pytest: python3 -m pytest scripts/test-build-field-guide.py -q
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_MOD_PATH = Path(__file__).resolve().parent / "build-field-guide.py"
_spec = importlib.util.spec_from_file_location("build_field_guide", _MOD_PATH)
bfg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bfg)


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------
def _concept(term, en, fr="FR def", de="DE def", theme=None, sources=None):
    c = {"term": term, "definition": {"en": en, "fr": fr, "de": de}}
    if theme is not None:
        c["theme"] = theme
    if sources is not None:
        c["sources"] = sources
    return c


_BIOS = {
    "members": [
        {"themes": ["Foreign policy and diplomacy", "Security and defence"]},
        {"themes": ["Foreign policy and diplomacy"]},
        {"themes": ["Cyber and emerging technology"]},
        {"themes": []},
        {},
    ]
}

# Build a minimal glossary page carrying the sentinels, plus a stray
# admin <dt>/<dd> outside the region the build must never touch.
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
    assert bfg.keyword_slug("Cyber and emerging technology") == "cyber-and-emerging-technology"


def test_keyword_slug_strips_punctuation_and_edges():
    assert bfg.keyword_slug("Intelligence, information and influence") == "intelligence-information-and-influence"
    assert bfg.keyword_slug("  --Hello, World!--  ") == "hello-world"
    assert bfg.keyword_slug("") == ""
    assert bfg.keyword_slug(None) == ""


def test_keyword_slug_no_underscores_leak():
    # JS \w-equivalent excludes underscore; the port must too.
    assert bfg.keyword_slug("a_b c") == "a-b-c"


# --------------------------------------------------------------------------
# theme_counts
# --------------------------------------------------------------------------
def test_theme_counts():
    counts = bfg.theme_counts(_BIOS)
    assert counts["Foreign policy and diplomacy"] == 2
    assert counts["Security and defence"] == 1
    assert counts["Cyber and emerging technology"] == 1
    assert "Theory and methods" not in counts


def test_theme_counts_empty_bios():
    assert bfg.theme_counts({}) == {}
    assert bfg.theme_counts({"members": []}) == {}


# --------------------------------------------------------------------------
# render_members_link
# --------------------------------------------------------------------------
def test_members_link_plural():
    loc = bfg.LOCALES["en"]
    out = bfg.render_members_link(loc, "Foreign policy and diplomacy", {"Foreign policy and diplomacy": 3})
    assert 'href="people.html#themes=foreign-policy-and-diplomacy"' in out
    assert "See 3 members working on this" in out
    assert out.startswith('<p class="fg-theme-link">')


def test_members_link_singular():
    loc = bfg.LOCALES["en"]
    out = bfg.render_members_link(loc, "Security and defence", {"Security and defence": 1})
    assert "See 1 member working on this" in out
    assert "1 members" not in out


def test_members_link_no_count_when_theme_absent():
    loc = bfg.LOCALES["en"]
    out = bfg.render_members_link(loc, "Nonexistent theme", {})
    assert "See members working on this" in out
    # No bogus number rendered.
    assert "See 0" not in out


def test_members_link_empty_when_no_theme():
    loc = bfg.LOCALES["en"]
    assert bfg.render_members_link(loc, "", {}) == ""


def test_members_link_uses_locale_people_page():
    out = bfg.render_members_link(bfg.LOCALES["fr"], "Security and defence", {"Security and defence": 2})
    assert "people.fr.html#themes=security-and-defence" in out
    out_de = bfg.render_members_link(bfg.LOCALES["de"], "Security and defence", {"Security and defence": 2})
    assert "people.de.html#themes=security-and-defence" in out_de


# --------------------------------------------------------------------------
# render_sources
# --------------------------------------------------------------------------
def test_render_sources_external_links():
    loc = bfg.LOCALES["en"]
    out = bfg.render_sources(loc, [{"label": "Official", "url": "https://europa.eu/x"}])
    assert 'target="_blank"' in out and 'rel="noopener"' in out
    assert "https://europa.eu/x" in out
    assert "Sources" in out


def test_render_sources_empty():
    assert bfg.render_sources(bfg.LOCALES["en"], []) == ""
    assert bfg.render_sources(bfg.LOCALES["en"], None or []) == ""


def test_render_sources_skips_urlless_entry():
    out = bfg.render_sources(bfg.LOCALES["en"], [{"label": "No URL"}])
    assert out == ""


# --------------------------------------------------------------------------
# render_concept
# --------------------------------------------------------------------------
def test_render_concept_has_dt_id_and_locale_def():
    c = _concept("CSDP", "EN definition", fr="Définition FR", de="DE Definition", theme="Foreign policy and diplomacy")
    counts = {"Foreign policy and diplomacy": 3}
    en = bfg.render_concept("en", c, counts)
    assert '<dt id="fg-csdp">CSDP</dt>' in en
    assert "EN definition" in en
    fr = bfg.render_concept("fr", c, counts)
    assert "Définition FR" in fr
    de = bfg.render_concept("de", c, counts)
    assert "DE Definition" in de


def test_render_concept_without_theme_or_sources():
    c = _concept("Plain", "Just a definition.")
    out = bfg.render_concept("en", c, {})
    assert '<dt id="fg-plain">Plain</dt>' in out
    assert "Just a definition." in out
    assert "fg-theme-link" not in out
    assert "fg-sources" not in out


def test_render_concept_escapes_html():
    c = _concept("A & B", "Less < than > more.")
    out = bfg.render_concept("en", c, {})
    assert "A &amp; B" in out
    assert "&lt; than &gt;" in out


# --------------------------------------------------------------------------
# render_section
# --------------------------------------------------------------------------
def test_render_section_wraps_sentinels_and_heading():
    concepts = [_concept("X", "Def X")]
    out = bfg.render_section("en", concepts, {})
    assert out.startswith(bfg.START)
    assert out.rstrip().endswith(bfg.END)
    assert '<h2 id="field-guide">Concepts in European security studies</h2>' in out
    assert 'class="fg-intro"' in out


def test_render_section_locale_headings():
    fr = bfg.render_section("fr", [_concept("X", "d")], {})
    assert "Concepts en études de sécurité européenne" in fr
    de = bfg.render_section("de", [_concept("X", "d")], {})
    assert "Konzepte der europäischen Sicherheitsforschung" in de


# --------------------------------------------------------------------------
# replace_region
# --------------------------------------------------------------------------
def test_replace_region_idempotent():
    region = bfg.render_section("en", [_concept("X", "Def X")], {})
    once = bfg.replace_region(_PAGE_TEMPLATE, region)
    twice = bfg.replace_region(once, region)
    assert once == twice


def test_replace_region_preserves_admin_terms():
    region = bfg.render_section("en", [_concept("X", "Def X")], {})
    out = bfg.replace_region(_PAGE_TEMPLATE, region)
    # The admin <dt>/<dd> outside the sentinels is untouched.
    assert '<dt id="action">Action</dt>' in out
    assert "An admin term that must survive." in out
    # The footer after the end sentinel survives.
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
    data = {"concepts": concepts}
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "data" / "field-guide.json").write_text(json.dumps(data), encoding="utf-8")
    (tmp_path / "data" / "bios.json").write_text(json.dumps(_BIOS), encoding="utf-8")
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
    concepts = [_concept("CSDP", "EN authoritative", fr="Texte FR", de="DE Text", theme="Foreign policy and diplomacy")]
    _wire_tmp(tmp_path, concepts)
    try:
        en = bfg.build("en", concepts, bfg.theme_counts(_BIOS))
        fr = bfg.build("fr", concepts, bfg.theme_counts(_BIOS))
        de = bfg.build("de", concepts, bfg.theme_counts(_BIOS))
        assert "EN authoritative" in en
        assert "Texte FR" in fr
        assert "DE Text" in de
        # Theme count of 2 for this theme in _BIOS.
        assert "See 2 members working on this" in en
    finally:
        _restore()


def test_main_write_then_check_roundtrip(tmp_path, monkeypatch):
    concepts = [_concept("X", "Def X", theme="Security and defence")]
    _wire_tmp(tmp_path, concepts)
    try:
        monkeypatch.setattr("sys.argv", ["build-field-guide.py"])
        assert bfg.main() == 0
        monkeypatch.setattr("sys.argv", ["build-field-guide.py", "--check"])
        assert bfg.main() == 0
    finally:
        _restore()


def test_main_check_fails_on_drift(tmp_path, monkeypatch):
    concepts = [_concept("X", "Def X")]
    _wire_tmp(tmp_path, concepts)
    try:
        # Pages still carry empty sentinels -> out of sync.
        monkeypatch.setattr("sys.argv", ["build-field-guide.py", "--check"])
        assert bfg.main() == 1
    finally:
        _restore()


def test_main_does_not_write_in_check_mode(tmp_path, monkeypatch):
    concepts = [_concept("X", "Def X")]
    _wire_tmp(tmp_path, concepts)
    try:
        before = (tmp_path / bfg.LOCALES["en"]["file"]).read_text(encoding="utf-8")
        monkeypatch.setattr("sys.argv", ["build-field-guide.py", "--check"])
        bfg.main()
        after = (tmp_path / bfg.LOCALES["en"]["file"]).read_text(encoding="utf-8")
        assert before == after
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
    counts = bfg.theme_counts(bios)
    for loc in bfg.LOCALES:
        section = bfg.render_section(loc, data["concepts"], counts)
        assert bfg.START in section and bfg.END in section
        for c in data["concepts"]:
            assert bfg.keyword_slug(c["term"]) in section


# --------------------------------------------------------------------------
# Standalone runner (no pytest dependency).
# --------------------------------------------------------------------------
def _standalone() -> int:
    import tempfile
    import types

    class _MonkeyPatch:
        def __init__(self):
            self._saved = []

        def setattr(self, target, name, value=None):
            if value is None:
                # "module.attr" style not used here; sys.argv path uses (target, value)
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
            tmp = None
            if "tmp_path" in params:
                tmp = Path(tempfile.mkdtemp())
                kwargs["tmp_path"] = tmp
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
