"""Tests for scripts/check-external-link-arrows.py.

The module name contains hyphens, so it cannot be imported by name.
We load it via importlib from its relative path. The module under test
is pure-stdlib (re, sys, pathlib) and has no network/subprocess side
effects, so the focus here is the regex parsing logic in find_hits and
the file-handling / exit-code logic in main.
"""

import importlib.util
from pathlib import Path

import pytest

# --- Load the hyphenated module under test -----------------------------------

_MODULE_PATH = Path(__file__).resolve().parent / "check-external-link-arrows.py"
_spec = importlib.util.spec_from_file_location("check_external_link_arrows", _MODULE_PATH)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


# --- find_hits: the core anti-pattern detector -------------------------------

def test_trailing_arrow_is_flagged():
    html = '<a href="https://example.com" target="_blank">Read more →</a>'
    hits = mod.find_hits(html)
    assert len(hits) == 1
    line_no, snippet = hits[0]
    assert line_no == 1
    assert "Read more" in snippet


def test_external_link_without_arrow_is_clean():
    html = '<a href="https://example.com" target="_blank">Read more</a>'
    assert mod.find_hits(html) == []


@pytest.mark.parametrize("arrow", list(mod.TRAILING_ARROWS))
def test_every_arrow_glyph_in_set_is_detected(arrow):
    html = f'<a href="https://example.com" target="_blank">Go {arrow}</a>'
    hits = mod.find_hits(html)
    assert len(hits) == 1, f"arrow {arrow!r} not detected"


def test_arrow_only_in_middle_is_not_flagged():
    # The check is endswith, so an arrow that is not the tail is fine.
    html = '<a href="https://example.com" target="_blank">A → B</a>'
    assert mod.find_hits(html) == []


def test_trailing_whitespace_after_arrow_still_flagged():
    # Inner text is stripped before the endswith check.
    html = '<a href="https://example.com" target="_blank">Visit ↗   </a>'
    assert len(mod.find_hits(html)) == 1


def test_non_blank_target_is_ignored():
    # Only target="_blank" links carry the auto-icon, so others are skipped.
    html = '<a href="https://example.com" target="_self">Internal →</a>'
    assert mod.find_hits(html) == []


def test_no_target_attribute_is_ignored():
    html = '<a href="https://example.com">Plain →</a>'
    assert mod.find_hits(html) == []


def test_relative_href_is_ignored():
    # The href must be http(s):// or protocol-relative //; a site-relative
    # path does not get the external-link icon, so an arrow is harmless.
    html = '<a href="/about.html" target="_blank">Local →</a>'
    assert mod.find_hits(html) == []


def test_protocol_relative_href_is_matched():
    # The regex explicitly allows (https?:)?// — bare // counts as external.
    html = '<a href="//cdn.example.com/x" target="_blank">Asset →</a>'
    assert len(mod.find_hits(html)) == 1


def test_http_and_https_both_match():
    http = '<a href="http://example.com" target="_blank">A →</a>'
    https = '<a href="https://example.com" target="_blank">B →</a>'
    assert len(mod.find_hits(http)) == 1
    assert len(mod.find_hits(https)) == 1


def test_nested_tags_are_stripped_before_check():
    # Author-placed SVG/span is removed; the real text tail is the arrow.
    html = (
        '<a href="https://example.com" target="_blank">'
        'Read <span>more</span> <svg><path/></svg> →</a>'
    )
    assert len(mod.find_hits(html)) == 1


def test_trailing_svg_after_arrowless_text_is_allowed():
    # A trailing <svg> author icon, with arrowless text, must NOT be flagged.
    html = (
        '<a href="https://example.com" target="_blank">'
        'Download<svg><path/></svg></a>'
    )
    assert mod.find_hits(html) == []


def test_empty_link_text_is_skipped():
    # Pure-icon link (text strips to nothing) is skipped, not flagged.
    html = '<a href="https://example.com" target="_blank"><svg></svg></a>'
    assert mod.find_hits(html) == []


def test_double_angle_bracket_arrow_detected():
    html = '<a href="https://example.com" target="_blank">Next >></a>'
    assert len(mod.find_hits(html)) == 1


def test_line_number_is_one_based_and_accurate():
    html = (
        "line one\n"
        "line two\n"
        '<a href="https://example.com" target="_blank">Hit →</a>\n'
    )
    hits = mod.find_hits(html)
    assert len(hits) == 1
    assert hits[0][0] == 3


def test_multiple_hits_across_lines():
    html = (
        '<a href="https://a.com" target="_blank">One →</a>\n'
        '<a href="https://b.com" target="_blank">Two ↗</a>\n'
        '<a href="https://c.com" target="_blank">Clean</a>\n'
    )
    hits = mod.find_hits(html)
    assert [h[0] for h in hits] == [1, 2]


def test_attribute_order_target_before_href():
    html = '<a target="_blank" href="https://example.com">Go →</a>'
    assert len(mod.find_hits(html)) == 1


def test_case_insensitive_tag_and_attrs():
    html = '<A HREF="https://example.com" TARGET="_blank">Go →</A>'
    assert len(mod.find_hits(html)) == 1


def test_multiline_inner_text_with_dotall():
    html = (
        '<a href="https://example.com" target="_blank">\n'
        '   Multi line link\n'
        '   →\n'
        '</a>'
    )
    assert len(mod.find_hits(html)) == 1


def test_snippet_is_compacted_and_truncated():
    long_text = "x " * 200
    html = f'<a href="https://example.com" target="_blank">{long_text}→</a>'
    hits = mod.find_hits(html)
    assert len(hits) == 1
    _, snippet = hits[0]
    assert len(snippet) <= 140
    # Whitespace collapsed to single spaces.
    assert "  " not in snippet


def test_extra_attributes_between_target_and_href():
    html = (
        '<a class="btn" rel="noopener" href="https://example.com" '
        'data-x="y" target="_blank">Go →</a>'
    )
    assert len(mod.find_hits(html)) == 1


# --- main: file handling, glob, exit codes -----------------------------------

def test_main_clean_file_returns_zero(tmp_path, monkeypatch, capsys):
    f = tmp_path / "clean.html"
    f.write_text('<a href="https://x.com" target="_blank">Clean</a>', encoding="utf-8")
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    rc = mod.main(["prog", str(f)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "OK" in out


def test_main_offending_file_returns_one(tmp_path, monkeypatch, capsys):
    f = tmp_path / "bad.html"
    f.write_text('<a href="https://x.com" target="_blank">Bad →</a>', encoding="utf-8")
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    rc = mod.main(["prog", str(f)])
    assert rc == 1
    captured = capsys.readouterr()
    # The per-hit line goes to stdout, the summary to stderr.
    assert "bad.html:1:" in captured.out
    assert "Found 1 external link" in captured.err


def test_main_missing_file_warns_and_continues(tmp_path, monkeypatch, capsys):
    missing = tmp_path / "nope.html"
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    rc = mod.main(["prog", str(missing)])
    # No hits, so a clean exit despite the missing file.
    assert rc == 0
    err = capsys.readouterr().err
    assert "does not exist" in err


def test_main_no_args_globs_repo_root(tmp_path, monkeypatch, capsys):
    (tmp_path / "a.html").write_text(
        '<a href="https://x.com" target="_blank">A →</a>', encoding="utf-8"
    )
    (tmp_path / "b.html").write_text(
        '<a href="https://y.com" target="_blank">B</a>', encoding="utf-8"
    )
    # A non-HTML file must be excluded by the *.html glob.
    (tmp_path / "c.txt").write_text("Junk →", encoding="utf-8")
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    rc = mod.main(["prog"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "a.html:1:" in out
    assert "b.html" not in out


def test_main_counts_total_across_multiple_files(tmp_path, monkeypatch, capsys):
    (tmp_path / "one.html").write_text(
        '<a href="https://x.com" target="_blank">One →</a>', encoding="utf-8"
    )
    (tmp_path / "two.html").write_text(
        '<a href="https://y.com" target="_blank">Two ↗</a>\n'
        '<a href="https://z.com" target="_blank">Three »</a>',
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    rc = mod.main(["prog"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "Found 3 external link" in err


def test_main_relative_path_in_output(tmp_path, monkeypatch, capsys):
    sub = tmp_path / "pages"
    sub.mkdir()
    f = sub / "deep.html"
    f.write_text('<a href="https://x.com" target="_blank">Deep →</a>', encoding="utf-8")
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    rc = mod.main(["prog", str(f)])
    assert rc == 1
    out = capsys.readouterr().out
    # path.relative_to(REPO_ROOT) renders the subdir-relative form.
    assert "pages/deep.html:1:" in out
