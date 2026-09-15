#!/usr/bin/env python3
"""Voice and locale-coverage checks on the Year in Review page copy.

Every sentence a visitor reads on /year-in-review.html comes from one
of two places: the I18N table in assets/js/year-review.js, or the
`hand` block in data/year-review.json. The builder composes no prose,
so this is the whole authored surface of the feature and it is small
enough to check mechanically.

What is checked:
  * No em dash and no semicolon in any authored string (CLAUDE.md §7).
    A reviewer catches these on the day they are written and misses
    them on the day a template is edited a year later.
  * The three locale tables carry the same keys, so a string added in
    English cannot silently fall back to English on the French page.
  * The three page files carry no untranslated English hero copy.

Run: python3 -m pytest scripts/test-year-review-copy.py -q
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
RENDERER = ROOT / "assets" / "js" / "year-review.js"
PAGES = {
    "en": ROOT / "year-in-review.html",
    "fr": ROOT / "year-in-review.fr.html",
    "de": ROOT / "year-in-review.de.html",
}

BANNED = {"—": "em dash", ";": "semicolon"}

# A JS single- or double-quoted literal, escapes allowed, no newlines.
_STRING_RE = re.compile(r"'(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\"")


def _i18n_block() -> str:
    """The I18N table, from its opening brace to the closing `};`."""
    src = RENDERER.read_text(encoding="utf-8")
    start = src.index("var I18N = {")
    end = src.index("\n  };", start)
    return src[start:end]


def _locale_table(lang: str) -> str:
    """One locale's entry inside the I18N table."""
    block = _i18n_block()
    start = block.index("    %s: {" % lang)
    end = block.index("\n    },", start)
    return block[start:end]


def _strings(js: str) -> list[str]:
    return [m.group(0)[1:-1] for m in _STRING_RE.finditer(js)]


def _keys(lang: str) -> set:
    """Template keys in one locale table, `name:` at the entry indent."""
    return set(re.findall(r"^      ([A-Za-z]+):", _locale_table(lang), re.M))


# --------------------------------------------------------------------------
# Voice
# --------------------------------------------------------------------------
@pytest.mark.parametrize("lang", ["en", "fr", "de"])
def test_no_banned_punctuation_in_the_locale_templates(lang):
    offenders = []
    for text in _strings(_locale_table(lang)):
        for char, name in BANNED.items():
            if char in text:
                offenders.append(f"{name} in {lang}: {text!r}")
    assert not offenders, "\n".join(offenders)


@pytest.mark.parametrize("lang", ["en", "fr", "de"])
def test_no_banned_punctuation_in_the_page_prose(lang):
    """The hero copy and the no-JavaScript fallback are the only prose
    written into the page files themselves."""
    html = PAGES[lang].read_text(encoding="utf-8")
    main = html[html.index("<main id=\"main\""):html.index("</main>")]
    offenders = [
        name for char, name in BANNED.items() if char in main
    ]
    assert not offenders, f"{lang} page prose carries: {offenders}"


def test_the_renderer_holds_no_em_dash_anywhere():
    """Including the comments, which §7 covers for multi-paragraph
    blocks and which are the easiest place for one to slip in."""
    assert "—" not in RENDERER.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# Locale coverage
# --------------------------------------------------------------------------
def test_every_template_key_exists_in_all_three_locales():
    en, fr, de = _keys("en"), _keys("fr"), _keys("de")
    assert en, "no template keys found, the I18N parser needs updating"
    assert fr == en, f"fr missing {sorted(en - fr)}, extra {sorted(fr - en)}"
    assert de == en, f"de missing {sorted(en - de)}, extra {sorted(de - en)}"


def test_month_names_cover_the_year_in_all_three_locales():
    src = RENDERER.read_text(encoding="utf-8")
    block = src[src.index("var MONTHS = {"):src.index("\n  };")]
    for lang in ("en", "fr", "de"):
        names = _strings(block[block.index("    %s: [" % lang):])
        assert len(names) >= 12, f"{lang} has {len(names)} month names"


# --------------------------------------------------------------------------
# The pages agree with the renderer
# --------------------------------------------------------------------------
@pytest.mark.parametrize("lang", ["en", "fr", "de"])
def test_each_page_mounts_the_renderer(lang):
    html = PAGES[lang].read_text(encoding="utf-8")
    assert "data-year-review" in html
    assert "assets/js/year-review.js" in html
    assert "assets/css/year-review.css" in html


@pytest.mark.parametrize("lang", ["fr", "de"])
def test_the_translated_pages_do_not_reuse_the_english_hero(lang):
    en = PAGES["en"].read_text(encoding="utf-8")
    other = PAGES[lang].read_text(encoding="utf-8")
    en_h1 = re.search(r"<h1>(.*?)</h1>", en, re.S).group(1)
    assert f"<h1>{en_h1}</h1>" not in other
