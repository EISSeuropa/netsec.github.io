#!/usr/bin/env python3
"""
Pytest suite for scripts/build-bio-search-stubs.py.

The script's filename uses hyphens, so it can't be imported by name. We
load it via importlib from the relative path. No network or subprocess
calls exist in the script; all file IO is redirected into tmp_path by
monkeypatching the module-level ROOT/BIOS/OUT_ROOT constants so no
tracked repo file is ever touched.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

# --- Load the hyphenated module from a path relative to this test file ---
_MODULE_PATH = Path(__file__).resolve().parent / "build-bio-search-stubs.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_bio_search_stubs", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bss = _load_module()


# --------------------------------------------------------------------------
# people_url
# --------------------------------------------------------------------------
def test_people_url_en_has_no_locale_suffix():
    assert bss.people_url("laudrain", "en") == "/people.html#laudrain"


def test_people_url_fr_inserts_locale():
    assert bss.people_url("laudrain", "fr") == "/people.fr.html#laudrain"


def test_people_url_de_inserts_locale():
    assert bss.people_url("mueller", "de") == "/people.de.html#mueller"


def test_people_url_preserves_slug_verbatim():
    # The function does not slugify; it trusts the caller's slug.
    assert bss.people_url("a-b_c", "en") == "/people.html#a-b_c"


# --------------------------------------------------------------------------
# html_escape
# --------------------------------------------------------------------------
def test_html_escape_all_special_chars():
    assert bss.html_escape('&<>"') == "&amp;&lt;&gt;&quot;"


def test_html_escape_ampersand_first_no_double_escape():
    # Ampersand must be replaced first so the entities it introduces
    # for < > " are not themselves re-escaped.
    assert bss.html_escape("<a>") == "&lt;a&gt;"
    assert bss.html_escape("&amp;") == "&amp;amp;"


def test_html_escape_none_returns_empty_string():
    assert bss.html_escape(None) == ""


def test_html_escape_empty_string():
    assert bss.html_escape("") == ""


def test_html_escape_plain_text_unchanged():
    assert bss.html_escape("Arthur Laudrain") == "Arthur Laudrain"


def test_html_escape_does_not_escape_apostrophe():
    # Single quotes are intentionally left alone (attrs use double quotes).
    assert bss.html_escape("O'Brien") == "O'Brien"


# --------------------------------------------------------------------------
# render_stub: guard clauses
# --------------------------------------------------------------------------
def test_render_stub_missing_slug_returns_empty():
    assert bss.render_stub({"name": "X"}, "en") == ""


def test_render_stub_missing_name_returns_empty():
    assert bss.render_stub({"id": "x"}, "en") == ""


def test_render_stub_blank_slug_after_strip_returns_empty():
    assert bss.render_stub({"id": "   ", "name": "X"}, "en") == ""


def test_render_stub_blank_name_after_strip_returns_empty():
    assert bss.render_stub({"id": "x", "name": "  "}, "en") == ""


# --------------------------------------------------------------------------
# render_stub: minimal valid member
# --------------------------------------------------------------------------
def _minimal():
    return {"id": "laudrain", "name": "Arthur Laudrain"}


def test_render_stub_minimal_has_doctype_and_lang():
    html = bss.render_stub(_minimal(), "fr")
    assert html.startswith("<!DOCTYPE html>")
    assert '<html lang="fr">' in html


def test_render_stub_minimal_title_and_h1():
    html = bss.render_stub(_minimal(), "en")
    assert "<title>Arthur Laudrain — NetSec directory</title>" in html
    assert "<h1>Arthur Laudrain</h1>" in html


def test_render_stub_canonical_and_refresh_locale_aware():
    html = bss.render_stub(_minimal(), "de")
    assert '<link rel="canonical" href="/people.de.html#laudrain">' in html
    assert 'content="0; url=/people.de.html#laudrain"' in html


def test_render_stub_always_emits_kind_bio_meta():
    html = bss.render_stub(_minimal(), "en")
    assert 'data-pagefind-meta="kind:bio"' in html


def test_render_stub_has_noindex_robots():
    html = bss.render_stub(_minimal(), "en")
    assert '<meta name="robots" content="noindex,nofollow">' in html


def test_render_stub_has_pagefind_body_main():
    html = bss.render_stub(_minimal(), "en")
    assert "<main data-pagefind-body>" in html


def test_render_stub_minimal_omits_optional_meta():
    html = bss.render_stub(_minimal(), "en")
    for key in ("role", "position", "affiliation", "country:", "wgs:", "photo:", "keywords"):
        assert f'data-pagefind-meta="{key}' not in html


# --------------------------------------------------------------------------
# render_stub: optional fields
# --------------------------------------------------------------------------
def _full():
    return {
        "id": "laudrain",
        "name": "Arthur Laudrain",
        "affiliation": "University of Oxford",
        "position": "Senior Researcher",
        "country": "United Kingdom",
        "country_code": "GB",
        "bio": "First paragraph.\n\nSecond paragraph.",
        "photo": "assets/img/people/laudrain.jpg",
        "roles": ["Chair", "MC Member"],
        "wgs": [1, 3],
        "keywords": ["cyber", "policy"],
    }


def test_render_stub_role_label_joined_with_middot():
    html = bss.render_stub(_full(), "en")
    assert '<span hidden data-pagefind-meta="role">Chair · MC Member</span>' in html


def test_render_stub_position_meta():
    html = bss.render_stub(_full(), "en")
    assert '<span hidden data-pagefind-meta="position">Senior Researcher</span>' in html


def test_render_stub_affiliation_meta():
    html = bss.render_stub(_full(), "en")
    assert '<span hidden data-pagefind-meta="affiliation">University of Oxford</span>' in html


def test_render_stub_country_code_lowercased_in_key():
    html = bss.render_stub(_full(), "en")
    # country_code "GB" should be lowercased to gb in the meta key,
    # and the country label stays as the visible text.
    assert 'data-pagefind-meta="country:gb">United Kingdom</span>' in html


def test_render_stub_wgs_csv_key_and_label():
    html = bss.render_stub(_full(), "en")
    assert 'data-pagefind-meta="wgs:1,3">WG1 · WG3</span>' in html


def test_render_stub_photo_meta_normalises_leading_slash():
    # photo without leading slash -> single leading slash in meta.
    html = bss.render_stub(_full(), "en")
    assert 'data-pagefind-meta="photo:/assets/img/people/laudrain.jpg"' in html


def test_render_stub_photo_meta_strips_existing_leading_slash():
    m = _full()
    m["photo"] = "/assets/img/x.jpg"
    html = bss.render_stub(m, "en")
    assert 'data-pagefind-meta="photo:/assets/img/x.jpg"' in html
    # Should not produce a double slash.
    assert "photo://" not in html


def test_render_stub_keywords_joined_with_comma_space():
    html = bss.render_stub(_full(), "en")
    assert '<span hidden data-pagefind-meta="keywords">cyber, policy</span>' in html


def test_render_stub_bio_split_into_paragraphs():
    html = bss.render_stub(_full(), "en")
    assert "<p>First paragraph.</p>" in html
    assert "<p>Second paragraph.</p>" in html


def test_render_stub_bio_single_paragraph():
    m = _minimal()
    m["bio"] = "Just one paragraph of text."
    html = bss.render_stub(m, "en")
    assert "<p>Just one paragraph of text.</p>" in html


def test_render_stub_bio_three_or_more_newlines_still_splits():
    m = _minimal()
    m["bio"] = "Para one.\n\n\n\nPara two."
    html = bss.render_stub(m, "en")
    assert "<p>Para one.</p>" in html
    assert "<p>Para two.</p>" in html


def test_render_stub_no_bio_means_no_paragraph():
    html = bss.render_stub(_minimal(), "en")
    assert "<p>" not in html


# --------------------------------------------------------------------------
# render_stub: escaping in dynamic content
# --------------------------------------------------------------------------
def test_render_stub_escapes_name_in_title_and_h1():
    m = {"id": "x", "name": 'A & B <script>'}
    html = bss.render_stub(m, "en")
    assert "<h1>A &amp; B &lt;script&gt;</h1>" in html
    assert "A &amp; B &lt;script&gt; — NetSec directory" in html


def test_render_stub_escapes_bio_paragraph():
    m = _minimal()
    m["bio"] = "Loves <tags> & ampersands"
    html = bss.render_stub(m, "en")
    assert "<p>Loves &lt;tags&gt; &amp; ampersands</p>" in html


def test_render_stub_escapes_affiliation():
    m = _minimal()
    m["affiliation"] = "R&D Lab"
    html = bss.render_stub(m, "en")
    assert '<span hidden data-pagefind-meta="affiliation">R&amp;D Lab</span>' in html


# --------------------------------------------------------------------------
# render_stub: type coercion / edge inputs
# --------------------------------------------------------------------------
def test_render_stub_wgs_non_int_values_stringified():
    m = _minimal()
    m["wgs"] = ["A", 2]
    html = bss.render_stub(m, "en")
    assert 'data-pagefind-meta="wgs:A,2">WGA · WG2</span>' in html


def test_render_stub_strips_whitespace_from_fields():
    m = {"id": "  x  ", "name": "  Name  ", "affiliation": "  Aff  "}
    html = bss.render_stub(m, "en")
    # slug stripped for canonical link
    assert "/people.html#x" in html
    assert "<h1>Name</h1>" in html
    assert '>Aff</span>' in html


def test_render_stub_empty_roles_list_omits_role_meta():
    m = _minimal()
    m["roles"] = []
    html = bss.render_stub(m, "en")
    assert 'data-pagefind-meta="role"' not in html


def test_render_stub_country_without_code_uses_empty_key():
    m = _minimal()
    m["country"] = "Atlantis"
    # no country_code key
    html = bss.render_stub(m, "en")
    assert 'data-pagefind-meta="country:">Atlantis</span>' in html


# --------------------------------------------------------------------------
# main(): end-to-end, redirected into tmp_path
# --------------------------------------------------------------------------
def _setup_root(monkeypatch, tmp_path, members_payload):
    """Point the module's path constants at tmp_path and write bios.json."""
    bios = tmp_path / "data" / "bios.json"
    bios.parent.mkdir(parents=True, exist_ok=True)
    bios.write_text(json.dumps(members_payload), encoding="utf-8")
    out_root = tmp_path / "search" / "bios"
    monkeypatch.setattr(bss, "ROOT", tmp_path)
    monkeypatch.setattr(bss, "BIOS", bios)
    monkeypatch.setattr(bss, "OUT_ROOT", out_root)
    return bios, out_root


def test_main_missing_bios_returns_1(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(bss, "BIOS", tmp_path / "nope.json")
    monkeypatch.setattr(bss, "OUT_ROOT", tmp_path / "out")
    assert bss.main() == 1
    assert "not found" in capsys.readouterr().out


def test_main_empty_members_returns_1(monkeypatch, tmp_path, capsys):
    _setup_root(monkeypatch, tmp_path, {"members": []})
    assert bss.main() == 1
    assert "No members" in capsys.readouterr().out


def test_main_generates_three_locale_stubs_per_member(monkeypatch, tmp_path, capsys):
    payload = {"members": [_full()]}
    _bios, out_root = _setup_root(monkeypatch, tmp_path, payload)
    assert bss.main() == 0
    for lang in ("en", "fr", "de"):
        stub = out_root / lang / "laudrain.html"
        assert stub.exists(), f"missing {lang} stub"
    out = capsys.readouterr().out
    assert "Generated 3 bio stubs" in out
    assert "1 EN · 1 FR · 1 DE" in out


def test_main_top_level_list_payload_supported(monkeypatch, tmp_path):
    # main() accepts either {"members": [...]} or a bare list.
    payload = [_full()]
    _bios, out_root = _setup_root(monkeypatch, tmp_path, payload)
    assert bss.main() == 0
    assert (out_root / "en" / "laudrain.html").exists()


def test_main_skips_members_without_slug(monkeypatch, tmp_path, capsys):
    payload = {"members": [_full(), {"name": "No Id"}]}
    _bios, out_root = _setup_root(monkeypatch, tmp_path, payload)
    assert bss.main() == 0
    # Only the valid member produced stubs (3 total).
    assert "Generated 3 bio stubs" in capsys.readouterr().out
    en_files = list((out_root / "en").glob("*.html"))
    assert len(en_files) == 1


def test_main_wipes_stale_stubs_on_rerun(monkeypatch, tmp_path):
    # First run with two members.
    payload = {"members": [_full(), {"id": "ghost", "name": "Ghost Member"}]}
    _bios, out_root = _setup_root(monkeypatch, tmp_path, payload)
    assert bss.main() == 0
    assert (out_root / "en" / "ghost.html").exists()

    # Second run with the ghost removed -> its stub must be gone.
    (tmp_path / "data" / "bios.json").write_text(
        json.dumps({"members": [_full()]}), encoding="utf-8"
    )
    assert bss.main() == 0
    assert not (out_root / "en" / "ghost.html").exists()
    assert (out_root / "en" / "laudrain.html").exists()


def test_main_written_file_content_matches_render_stub(monkeypatch, tmp_path):
    payload = {"members": [_full()]}
    _bios, out_root = _setup_root(monkeypatch, tmp_path, payload)
    assert bss.main() == 0
    written = (out_root / "fr" / "laudrain.html").read_text(encoding="utf-8")
    assert written == bss.render_stub(_full(), "fr")


def test_main_does_not_touch_repo_outside_tmp(monkeypatch, tmp_path):
    # Sanity: OUT_ROOT lives under tmp_path, never the real repo.
    payload = {"members": [_minimal()]}
    _bios, out_root = _setup_root(monkeypatch, tmp_path, payload)
    assert bss.main() == 0
    assert str(out_root).startswith(str(tmp_path))


# --- --check drift gate (#1428) ------------------------------------------


def test_check_passes_on_a_freshly_built_tree(monkeypatch, tmp_path, capsys):
    payload = {"members": [_full()]}
    _setup_root(monkeypatch, tmp_path, payload)
    assert bss.main() == 0
    assert bss.main(["--check"]) == 0
    assert "are current" in capsys.readouterr().out


def test_check_catches_stale_content(monkeypatch, tmp_path, capsys):
    """The #1421 case: a member's wgs facet reaches bios.json but not the stub."""
    member = _full()
    member["wgs"] = []
    _bios, out_root = _setup_root(monkeypatch, tmp_path, {"members": [member]})
    assert bss.main() == 0

    member["wgs"] = [2, 3]
    (tmp_path / "data" / "bios.json").write_text(
        json.dumps({"members": [member]}), encoding="utf-8"
    )
    assert bss.main(["--check"]) == 1
    out = capsys.readouterr().out
    assert "stale content" in out
    assert "drifted" in out


def test_check_catches_a_missing_stub(monkeypatch, tmp_path, capsys):
    _bios, out_root = _setup_root(monkeypatch, tmp_path, {"members": [_full()]})
    assert bss.main() == 0
    (out_root / "en" / "laudrain.html").unlink()
    assert bss.main(["--check"]) == 1
    assert "missing (member unsearchable)" in capsys.readouterr().out


def test_check_catches_an_orphaned_stub(monkeypatch, tmp_path, capsys):
    _bios, out_root = _setup_root(monkeypatch, tmp_path, {"members": [_full()]})
    assert bss.main() == 0
    (out_root / "en" / "ghost.html").write_text("<html></html>", encoding="utf-8")
    assert bss.main(["--check"]) == 1
    assert "orphaned (member gone)" in capsys.readouterr().out


def test_check_never_writes_to_the_tree(monkeypatch, tmp_path):
    """A gate that repairs what it measures would always pass."""
    _bios, out_root = _setup_root(monkeypatch, tmp_path, {"members": [_full()]})
    assert bss.main() == 0
    (out_root / "en" / "laudrain.html").unlink()
    before = sorted(p.name for p in out_root.glob("*/*.html"))
    assert bss.main(["--check"]) == 1
    assert sorted(p.name for p in out_root.glob("*/*.html")) == before


def test_check_on_a_missing_out_root_reports_everything_missing(
    monkeypatch, tmp_path, capsys
):
    _setup_root(monkeypatch, tmp_path, {"members": [_full()]})
    assert bss.main(["--check"]) == 1
    assert "missing (member unsearchable)" in capsys.readouterr().out


def test_build_stubs_keys_are_lang_slug_paths(monkeypatch, tmp_path):
    _setup_root(monkeypatch, tmp_path, {"members": [_full()]})
    stubs = bss.build_stubs([_full()])
    assert set(stubs) == {
        "en/laudrain.html",
        "fr/laudrain.html",
        "de/laudrain.html",
    }
