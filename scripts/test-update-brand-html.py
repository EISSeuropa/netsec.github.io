"""Tests for scripts/update-brand-html.py.

The module name contains hyphens, so it cannot be imported by name; we
load it from its relative path via importlib. All file IO uses tmp_path
fixtures; no tracked repo file is read or mutated, and there is no
network or subprocess involvement in the module under test.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# ── Load the hyphenated module from its relative path ──
_MODULE_PATH = Path(__file__).resolve().parent / "update-brand-html.py"
_spec = importlib.util.spec_from_file_location("update_brand_html", _MODULE_PATH)
ubh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ubh)


# ──────────────────────────── helpers ────────────────────────────

def write(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


# ──────────────────────────── favicon ────────────────────────────

def test_favicon_full_block_replaced_on_apply(tmp_path):
    body = "<head>\n" + ubh.OLD_FAVICON_BLOCK + "\n</head>\n"
    f = write(tmp_path, "page.html", body)

    changed, log = ubh.patch_file(f, apply=True)

    assert changed is True
    assert any("with alternate" in entry for entry in log)
    out = f.read_text(encoding="utf-8")
    assert ubh.NEW_FAVICON_BLOCK in out
    assert ubh.OLD_FAVICON_BLOCK not in out


def test_favicon_svg_only_fallback_replaced(tmp_path):
    # Only the svg line present (no PNG alternate) -> fallback branch.
    body = "<head>\n" + ubh.OLD_FAVICON_BLOCK_FALLBACK + "\n</head>\n"
    f = write(tmp_path, "page.html", body)

    changed, log = ubh.patch_file(f, apply=True)

    assert changed is True
    assert any("svg-only" in entry for entry in log)
    out = f.read_text(encoding="utf-8")
    assert ubh.NEW_FAVICON_BLOCK in out


def test_favicon_full_block_takes_precedence_over_fallback(tmp_path):
    # The full block contains the fallback substring; the elif must not
    # double-fire. Exactly one favicon log entry expected.
    body = "<head>\n" + ubh.OLD_FAVICON_BLOCK + "\n</head>\n"
    f = write(tmp_path, "page.html", body)

    _, log = ubh.patch_file(f, apply=True)

    favicon_entries = [e for e in log if "favicon" in e]
    assert len(favicon_entries) == 1
    assert "with alternate" in favicon_entries[0]


# ──────────────────────────── brand element ────────────────────────────

def test_brand_ns_placeholder_replaced(tmp_path):
    body = "<a>\n" + ubh.OLD_BRAND + "\n</a>\n"
    f = write(tmp_path, "page.html", body)

    changed, log = ubh.patch_file(f, apply=True)

    assert changed is True
    assert any("from NS placeholder" in e for e in log)
    out = f.read_text(encoding="utf-8")
    assert ubh.NEW_BRAND in out
    assert '<span class="brand-mark">NS</span>' not in out  # placeholder gone


def test_brand_v1_picture_migrated_to_dual_img(tmp_path):
    body = "<a>\n" + ubh.OLD_BRAND_V1 + "\n</a>\n"
    f = write(tmp_path, "page.html", body)

    changed, log = ubh.patch_file(f, apply=True)

    assert changed is True
    assert any("picture" in e for e in log)
    out = f.read_text(encoding="utf-8")
    assert ubh.NEW_BRAND in out
    assert "<picture" not in out


def test_brand_ns_takes_precedence_over_v1(tmp_path):
    # If both forms somehow present, NS placeholder branch wins (it's
    # the `if`, V1 is the `elif`).
    body = ubh.OLD_BRAND + "\n" + ubh.OLD_BRAND_V1 + "\n"
    f = write(tmp_path, "page.html", body)

    _, log = ubh.patch_file(f, apply=True)

    brand_entries = [e for e in log if "brand element" in e]
    assert len(brand_entries) == 1
    assert "from NS placeholder" in brand_entries[0]
    # The V1 picture block is left untouched because the elif never ran.
    out = f.read_text(encoding="utf-8")
    assert "<picture" in out


# ──────────────────────────── JSON-LD logo ────────────────────────────

def test_logo_url_replaced(tmp_path):
    body = '{\n  ' + ubh.OLD_LOGO_URL + '\n}\n'
    f = write(tmp_path, "page.html", body)

    changed, log = ubh.patch_file(f, apply=True)

    assert changed is True
    assert any("Organization.logo" in e for e in log)
    out = f.read_text(encoding="utf-8")
    assert ubh.NEW_LOGO_URL in out
    assert ubh.OLD_LOGO_URL not in out


# ──────────────────────────── combined / all three ────────────────────────────

def test_all_three_replacements_in_one_file(tmp_path):
    body = (
        "<head>\n" + ubh.OLD_FAVICON_BLOCK + "\n</head>\n"
        "<a>\n" + ubh.OLD_BRAND + "\n</a>\n"
        '{\n  ' + ubh.OLD_LOGO_URL + '\n}\n'
    )
    f = write(tmp_path, "page.html", body)

    changed, log = ubh.patch_file(f, apply=True)

    assert changed is True
    assert len(log) == 3
    out = f.read_text(encoding="utf-8")
    assert ubh.NEW_FAVICON_BLOCK in out
    assert ubh.NEW_BRAND in out
    assert ubh.NEW_LOGO_URL in out


# ──────────────────────────── dry-run vs apply ────────────────────────────

def test_dry_run_reports_change_but_does_not_write(tmp_path):
    body = '{\n  ' + ubh.OLD_LOGO_URL + '\n}\n'
    f = write(tmp_path, "page.html", body)
    original = f.read_text(encoding="utf-8")

    changed, log = ubh.patch_file(f, apply=False)

    assert changed is True
    assert log  # change was detected and logged
    # File on disk is untouched in dry-run mode.
    assert f.read_text(encoding="utf-8") == original


# ──────────────────────────── idempotency / no-op ────────────────────────────

def test_no_placeholders_is_noop(tmp_path):
    body = "<head>\n  <title>nothing to do</title>\n</head>\n"
    f = write(tmp_path, "page.html", body)
    original = f.read_text(encoding="utf-8")

    changed, log = ubh.patch_file(f, apply=True)

    assert changed is False
    assert log == []
    assert f.read_text(encoding="utf-8") == original


def test_idempotent_second_pass_is_noop(tmp_path):
    body = (
        "<head>\n" + ubh.OLD_FAVICON_BLOCK + "\n</head>\n"
        "<a>\n" + ubh.OLD_BRAND + "\n</a>\n"
        '{\n  ' + ubh.OLD_LOGO_URL + '\n}\n'
    )
    f = write(tmp_path, "page.html", body)

    ubh.patch_file(f, apply=True)
    after_first = f.read_text(encoding="utf-8")

    changed, log = ubh.patch_file(f, apply=True)

    assert changed is False
    assert log == []
    assert f.read_text(encoding="utf-8") == after_first


# ──────────────────────────── main() runner ────────────────────────────

def test_main_dry_run_does_not_write(tmp_path, monkeypatch, capsys):
    body = '{\n  ' + ubh.OLD_LOGO_URL + '\n}\n'
    f = write(tmp_path, "index.html", body)
    write(tmp_path, "other.html", "<p>untouched</p>\n")
    original = f.read_text(encoding="utf-8")

    monkeypatch.setattr(ubh, "ROOT", tmp_path)
    monkeypatch.setattr(ubh.sys, "argv", ["update-brand-html.py"])

    rc = ubh.main()

    assert rc == 0
    out = capsys.readouterr().out
    assert "Dry-run" in out
    assert "Run with --apply" in out
    # Dry-run leaves files alone.
    assert f.read_text(encoding="utf-8") == original


def test_main_apply_writes_changes(tmp_path, monkeypatch, capsys):
    body = '{\n  ' + ubh.OLD_LOGO_URL + '\n}\n'
    f = write(tmp_path, "index.html", body)

    monkeypatch.setattr(ubh, "ROOT", tmp_path)
    monkeypatch.setattr(ubh.sys, "argv", ["update-brand-html.py", "--apply"])

    rc = ubh.main()

    assert rc == 0
    out = capsys.readouterr().out
    assert "Apply" in out
    assert "1 file(s) updated" in out
    assert ubh.NEW_LOGO_URL in f.read_text(encoding="utf-8")


def test_main_counts_changed_and_unchanged(tmp_path, monkeypatch, capsys):
    write(tmp_path, "a.html", '{\n  ' + ubh.OLD_LOGO_URL + '\n}\n')
    write(tmp_path, "b.html", "<p>nothing here</p>\n")
    write(tmp_path, "c.html", "<head>\n" + ubh.OLD_FAVICON_BLOCK + "\n</head>\n")

    monkeypatch.setattr(ubh, "ROOT", tmp_path)
    monkeypatch.setattr(ubh.sys, "argv", ["update-brand-html.py", "--apply"])

    ubh.main()

    out = capsys.readouterr().out
    assert "2 file(s) updated" in out
    assert "1 unchanged" in out


def test_main_no_html_files(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(ubh, "ROOT", tmp_path)
    monkeypatch.setattr(ubh.sys, "argv", ["update-brand-html.py"])

    rc = ubh.main()

    assert rc == 0
    out = capsys.readouterr().out
    assert "0 HTML files" in out
