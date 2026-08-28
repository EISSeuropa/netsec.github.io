#!/usr/bin/env python3
"""Test suite for scripts/build-og-cards.py (browser-free).

Loaded via importlib from its hyphenated path. Covers the pure logic and
the committed-state invariants without rendering (no Chrome needed):
  * card_hash is deterministic and input-sensitive
  * card_markup escapes member text and includes the bundled flag
  * a flag SVG exists for every country_code used in bios.json
  * --check passes against the committed cards + manifest

Run standalone:  /usr/bin/python3 scripts/test-build-og-cards.py
Or under pytest: python3 -m pytest scripts/test-build-og-cards.py -q
"""
from __future__ import annotations

import importlib.util
import json
import types
from pathlib import Path

_MOD_PATH = Path(__file__).resolve().parent / "build-og-cards.py"
_spec = importlib.util.spec_from_file_location("build_og_cards", _MOD_PATH)
boc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(boc)


def test_card_hash_deterministic_and_sensitive():
    a = {"name": "Dr Ada Lovelace", "position": "Prof", "affiliation": "X Uni",
         "country": "United Kingdom", "country_code": "gb"}
    assert boc.card_hash(a) == boc.card_hash(dict(a))
    b = dict(a, affiliation="Y Uni")
    assert boc.card_hash(a) != boc.card_hash(b)


def test_card_markup_escapes_and_includes_flag():
    inp = {"name": "Dr <Ada> & Co", "position": "Prof", "affiliation": "X & Y",
           "country": "Netherlands", "country_code": "nl"}
    html = boc.card_markup(inp)
    assert "&lt;Ada&gt;" in html and "&amp;" in html  # escaped, not raw
    assert "<Ada>" not in html
    assert "/assets/og/flags/nl.svg" in html
    assert "Netherlands" in html


def test_card_markup_skips_an_affiliation_the_position_already_names():
    # #1506: the role line used to read "… at X University · X University".
    inp = {"name": "Dr Dup", "position": "guest lecturer at X University, XU",
           "affiliation": "X University, XU"}
    assert "guest lecturer at X University, XU</div>" in boc.card_markup(inp)
    # Distinct affiliations still join.
    other = dict(inp, position="PhD candidate")
    assert "PhD candidate · X University, XU" in boc.card_markup(other)


def test_card_markup_omits_flag_when_missing():
    inp = {"name": "X", "position": "", "affiliation": "", "country": "Nowhere", "country_code": "zz"}
    html = boc.card_markup(inp)
    assert "flags/zz.svg" not in html  # no bundled flag for zz -> omitted


def test_initials_drops_honorific():
    assert boc.initials("Dr Arthur Laudrain") == "AL"
    assert boc.initials("Prof. Ada Lovelace") == "AL"
    assert boc.initials("Madonna") == "M"
    assert boc.initials("") == "?"


def test_wg_pills_lead_and_co_lead_suffix():
    m = {"wgs": [1, 3], "wg_leadership": {"lead": [3], "co_lead": [1]}}
    assert boc.wg_pills(m) == ["WG1 · co-lead", "WG3 · lead"]
    assert boc.wg_pills({"wgs": [2]}) == ["WG2"]
    assert boc.wg_pills({}) == []


def test_mentor_and_stsm_pills():
    assert boc.mentor_pills({"mentorship": ["mentor"]}) == ["Mentor"]
    assert boc.mentor_pills({"mentorship": ["mentee"]}) == ["Mentee"]
    assert boc.mentor_pills({}) == []
    assert boc.stsm_pill({"stsm_hosting": "yes"}) == "STSM host"
    assert boc.stsm_pill({"stsm_hosting": "ask"}) == "STSM on request"
    assert boc.stsm_pill({"stsm_hosting": None}) == ""


def test_card_markup_renders_pills():
    inp = {"name": "X", "country_code": "zz",
           "wg": ["WG1 · lead"], "mentor": ["Mentor"], "stsm": "STSM host"}
    html = boc.card_markup(inp)
    assert "WG1 · lead" in html and "Mentor" in html and "STSM host" in html
    assert 'class="pill wg"' in html and 'class="pill stsm"' in html


def test_card_markup_initials_tile_when_no_photo():
    html = boc.card_markup({"name": "Dr Ada Lovelace", "initials": "AL"})
    assert '<div class="shot"><div class="initials">AL</div></div>' in html


def test_card_markup_headshot_when_photo_present():
    html = boc.card_markup({"name": "X", "photo": "assets/images/people/x.jpg"})
    assert '<div class="shot"><img src="/assets/images/people/x.jpg"' in html


def test_every_country_code_has_a_bundled_flag():
    for m in boc.members():
        cc = (m.get("country_code") or "").strip().lower()
        if cc:
            assert (boc.FLAGS_DIR / f"{cc}.svg").exists(), f"missing bundled flag for {cc}"


def test_minify_flag_strips_id_and_collapses_whitespace():
    # A raw flag-icons SVG (multi-line, carries an id) becomes the one-line,
    # id-free form the ensure_flags step writes to disk.
    raw = ('<svg xmlns="http://www.w3.org/2000/svg" id="flag-icons-ge" '
           'viewBox="0 0 640 480">\n  <path fill="#fff" d="M0 0h640v480H0z"/>\n</svg>')
    out = boc._minify_flag(raw)
    assert 'id=' not in out
    assert '>\n' not in out.rstrip("\n") and '  <' not in out
    assert out.endswith("\n") and out.count("\n") == 1
    assert out.startswith('<svg xmlns="http://www.w3.org/2000/svg" viewBox=')


def test_check_passes_against_committed_cards():
    assert boc.check() == 0


def _standalone() -> int:
    failures = []
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and isinstance(f, types.FunctionType)]
    for name, fn in tests:
        try:
            fn()
            print(f"  ok  {name}")
        except Exception as exc:  # noqa: BLE001
            failures.append((name, exc))
            print(f"FAIL  {name}: {exc}")
    print(f"\n{len(tests) - len(failures)}/{len(tests)} passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    import sys

    sys.exit(_standalone())


# ── The Chrome launch retry (#1726) ────────────────────────────────────────

class _FakeProc:
    """Stands in for the Popen handle _capture_cards is given."""

    def __init__(self):
        self.killed = False

    def terminate(self):
        self.killed = True

    def wait(self, timeout=None):
        return 0

    def kill(self):
        self.killed = True


def test_launch_is_retried_once_and_then_succeeds(monkeypatch, capsys):
    """A cold headless Chrome sometimes never reaches its DevTools endpoint.
    One attempt used to abort the whole render, which inside the daily bios
    sync leaves a member's share card stale with only the run log saying so."""
    attempts = []
    proc = _FakeProc()

    def flaky(chrome):
        attempts.append(chrome)
        if len(attempts) == 1:
            raise RuntimeError("Chrome did not expose the DevTools endpoint within 10s")
        return proc, object()

    monkeypatch.setattr(boc, "_launch_chrome", flaky)
    monkeypatch.setattr(boc.time, "sleep", lambda _s: None)
    # No jobs, so nothing renders: the launch path is what is under test.
    boc._capture_cards("/fake/chrome", [])

    assert len(attempts) == 2, "the failed launch should be retried exactly once"
    assert proc.killed, "the browser should still be shut down after the run"
    err = capsys.readouterr().err
    assert "retrying once" in err
    assert "second attempt succeeded" in err, "a silent recovery teaches nobody"


def test_two_failed_launches_give_up_rather_than_looping(monkeypatch):
    """Twice was enough for every occurrence seen; a third would be guessing,
    and an unbounded retry would hang the sync rather than report."""
    attempts = []

    def always_fails(chrome):
        attempts.append(chrome)
        raise RuntimeError("Chrome did not expose the DevTools endpoint within 10s")

    monkeypatch.setattr(boc, "_launch_chrome", always_fails)
    monkeypatch.setattr(boc.time, "sleep", lambda _s: None)
    try:
        boc._capture_cards("/fake/chrome", [])
    except SystemExit as exc:
        assert "after two attempts" in str(exc)
    else:
        raise AssertionError("a second failure should exit, not continue")
    assert len(attempts) == 2
