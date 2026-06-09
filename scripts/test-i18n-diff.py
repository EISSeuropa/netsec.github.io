#!/usr/bin/env python3
"""Pytest suite for scripts/i18n-diff.py.

The module is loaded via importlib from its hyphenated path. Block
extraction, normalisation, and block-diffing are pure functions tested
directly; the git-walking path is exercised against a throwaway git
repository built in tmp_path, so no network and no mutation of the
real working tree.

Run: python3 -m pytest scripts/test-i18n-diff.py -q
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("i18n_diff", HERE / "i18n-diff.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


# ── block extraction ────────────────────────────────────────────────

def test_extract_blocks_basic():
    html = "<body><h1>Title</h1><p>One two.</p><ul><li>Item A</li></ul></body>"
    assert mod.extract_blocks(html) == ["Title", "One two.", "Item A"]


def test_extract_blocks_skips_script_style_head():
    html = ("<head><title>x</title></head><body><p>Kept</p>"
            "<script>var p = '<p>not prose</p>';</script>"
            "<style>p{color:red}</style></body>")
    assert mod.extract_blocks(html) == ["Kept"]


def test_extract_blocks_collapses_whitespace_and_inline_tags():
    html = "<p>A   <strong>bold</strong>\n  claim.</p>"
    assert mod.extract_blocks(html) == ["A bold claim."]


def test_extract_blocks_nested_blocks_flush_outer():
    html = "<li>Outer lead <p>Inner para</p></li>"
    blocks = mod.extract_blocks(html)
    assert "Outer lead" in blocks and "Inner para" in blocks


def test_extract_blocks_entities_decoded():
    assert mod.extract_blocks("<p>Caf&eacute; &amp; bar</p>") == ["Café & bar"]


# ── normalisation ───────────────────────────────────────────────────

def test_norm_sha1_ignores_cache_bust_tokens():
    a = '<link href="assets/css/site.css?v=1234abcd"><p>X</p>'
    b = '<link href="assets/css/site.css?v=feedbeef"><p>X</p>'
    assert mod.norm_sha1(a) == mod.norm_sha1(b)


def test_norm_sha1_catches_prose_change():
    a = '<p>Old wording</p>'
    b = '<p>New wording</p>'
    assert mod.norm_sha1(a) != mod.norm_sha1(b)


# ── block diff ──────────────────────────────────────────────────────

def test_diff_blocks_replace():
    out = mod.diff_blocks(["Same", "Old text"], ["Same", "New text"])
    assert ("-", "Old text") in out and ("+", "New text") in out
    assert all(t != "Same" for _, t in out)


def test_diff_blocks_insert_only():
    out = mod.diff_blocks(["A"], ["A", "B"])
    assert out == [("+", "B")]


def test_diff_blocks_identical():
    assert mod.diff_blocks(["A", "B"], ["A", "B"]) == []


# ── end-to-end against a throwaway git repo ─────────────────────────

@pytest.fixture
def fake_repo(tmp_path, monkeypatch):
    def run(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True,
                       capture_output=True)
    run("init", "-q")
    run("config", "user.email", "t@example.org")
    run("config", "user.name", "T")
    page = tmp_path / "page.html"
    page.write_text("<p>Original sentence.</p>\n", encoding="utf-8")
    run("add", "page.html")
    run("commit", "-qm", "v1")
    old_sha1 = mod.norm_sha1(page.read_text(encoding="utf-8"))
    page.write_text("<p>Rewritten sentence.</p>\n<p>Brand new block.</p>\n",
                    encoding="utf-8")
    run("add", "page.html")
    run("commit", "-qm", "v2")

    state = {
        "translations": {
            "page.html": {
                "fr": {"file": "page.fr.html", "source_sha1": old_sha1,
                       "translated_on": "2026-01-01", "status": "beta"},
            }
        }
    }
    state_path = tmp_path / "data"
    state_path.mkdir()
    (state_path / "i18n-state.json").write_text(json.dumps(state),
                                                encoding="utf-8")
    monkeypatch.setattr(mod, "REPO", tmp_path)
    monkeypatch.setattr(mod, "STATE", state_path / "i18n-state.json")
    return tmp_path


def test_end_to_end_reports_changed_blocks(fake_repo, capsys):
    assert mod.main(["page.html", "fr"]) == 0
    out = capsys.readouterr().out
    assert "- Original sentence." in out
    assert "+ Rewritten sentence." in out
    assert "+ Brand new block." in out
    assert "--mark-fresh page.html fr" in out


def test_end_to_end_current_translation(fake_repo, capsys):
    state_path = fake_repo / "data" / "i18n-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    now = mod.norm_sha1((fake_repo / "page.html").read_text(encoding="utf-8"))
    state["translations"]["page.html"]["fr"]["source_sha1"] = now
    state_path.write_text(json.dumps(state), encoding="utf-8")
    assert mod.main(["page.html", "fr"]) == 0
    assert "is current" in capsys.readouterr().out


def test_main_unknown_entry(fake_repo, capsys):
    assert mod.main(["page.html", "de"]) == 2
    assert "no de entry" in capsys.readouterr().out


def test_main_bad_args(capsys):
    assert mod.main(["only-one"]) == 2
