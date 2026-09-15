#!/usr/bin/env python3
"""pytest suite for scripts/_analytics.py and its two call sites.

The counter is off until a GoatCounter account is set, and the privacy
notice describes collection that only happens once it is on. These
tests pin both halves of that: nothing is emitted while SITE_CODE is
empty, and the tag reaches both the top-level pages and the generated
profile pages once it is not.

Run: python3 -m pytest scripts/test-analytics.py -q
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import _analytics  # noqa: E402


def _load(name: str, mod_name: str):
    spec = importlib.util.spec_from_file_location(mod_name, _HERE / name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def code_set(monkeypatch):
    monkeypatch.setattr(_analytics, "SITE_CODE", "netsec-test")


def test_no_tag_while_no_account_is_set():
    """The committed default. A counter shipped ahead of the privacy
    notice's account would describe collection that is not happening."""
    assert _analytics.SITE_CODE == ""
    assert _analytics.tag() == ""
    assert _analytics.lines() == []


def test_tag_points_at_the_account_and_loads_over_https(code_set):
    tag = _analytics.tag()
    assert 'data-goatcounter="https://netsec-test.goatcounter.com/count"' in tag
    assert 'src="https://gc.zgo.at/count.js"' in tag
    assert " async " in tag
    # A protocol-relative src would inherit http:// on a plain-http view
    # of the page.
    assert 'src="//' not in tag


def test_lines_carry_a_comment_so_the_head_block_stays_readable(code_set):
    assert _analytics.lines()[1].startswith("<!--")
    assert _analytics.lines()[-1] == _analytics.tag()


def test_the_managed_head_block_is_unchanged_while_the_counter_is_off():
    seo = _load("inject-seo.py", "inject_seo_off")
    block = seo.build_seo_block("privacy", "en", "T", "D")
    assert "goatcounter" not in block
    assert block.rstrip().endswith(seo.SENTINEL_END)


def test_the_managed_head_block_carries_the_tag_when_the_counter_is_on(code_set):
    seo = _load("inject-seo.py", "inject_seo_on")
    block = seo.build_seo_block("privacy", "en", "T", "D")
    assert "netsec-test.goatcounter.com" in block
    # Inside the sentinels, so a re-run rewrites it rather than stacking
    # a second copy.
    assert block.index("goatcounter") < block.index(seo.SENTINEL_END)


def test_the_profile_page_head_carries_the_tag_when_the_counter_is_on(code_set):
    """Profile pages build their own head, so the tag has to be wired
    there separately from the managed block."""
    src = (_HERE / "build-profile-pages.py").read_text(encoding="utf-8")
    assert "_analytics.tag()" in src
    assert "{_counter}" in src
