#!/usr/bin/env python3
"""
Smoke tests for scripts/promote-roadmap.py.

The script edits public-facing HTML on release day, so the tests
focus on:
  - correct flip of a planned card to shipped per locale
  - correct date format per locale (EN no period, FR lowercase month,
    DE day with period + capital month)
  - non-release planned milestones (Stockholm event, MC plenary)
    stay planned no matter what
  - idempotent re-runs
  - last-updated stamp gets both <time datetime=...> attrs + the
    visible date text

Usage:
    python3 scripts/test-promote-roadmap.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
pr = __import__("promote-roadmap")
promote_planned_card = pr.promote_planned_card
bump_updated_stamp = pr.bump_updated_stamp
parse_changelog_section = pr.parse_changelog_section
relocate_card_to_quarter = pr.relocate_card_to_quarter
LOCALES = pr.LOCALES


def expect(label: str, got, want) -> None:
    if got != want:
        print(f"FAIL: {label}\n  got:  {got!r}\n  want: {want!r}", file=sys.stderr)
        sys.exit(1)
    print(f"  ok  {label}")


# Reusable fixture: a tiny roadmap HTML stub with one shipped card,
# one planned release card, one planned non-release milestone (which
# must NEVER be promoted), and the last-updated paragraph.
def _fixture(locale_key: str, planned_label: str, when_release: str,
             when_milestone: str, updated_prose: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="{locale_key}">
<body>
  <p class="roadmap-updated">{updated_prose}</p>
  <ol class="rm-timeline">
    <li class="rm-entry shipped">
      <article class="rm-card">
        <div class="rm-head">
          <span class="rm-pill shipped"><span class="dot" aria-hidden="true"></span>Past</span>
          <span class="when">23 May 2026 &middot; v1.0.0</span>
        </div>
        <h3>Earlier release</h3>
        <p>Already shipped.</p>
        <a class="notes-link" href="https://github.com/EISSeuropa/netsec.github.io/releases/tag/v1.0.0" target="_blank" rel="noopener">Notes</a>
      </article>
    </li>
    <li class="rm-entry planned">
      <article class="rm-card">
        <div class="rm-head">
          <span class="rm-pill planned"><span class="dot" aria-hidden="true"></span>{planned_label}</span>
          <span class="when">{when_release}</span>
        </div>
        <h3>Some upcoming release</h3>
        <p>Pre-written description that the script should not touch.</p>
      </article>
    </li>
    <li class="rm-entry planned rm-milestone">
      <article class="rm-card">
        <div class="rm-head">
          <span class="rm-pill planned"><span class="dot" aria-hidden="true"></span>{planned_label}</span>
          <span class="when">{when_milestone}</span>
        </div>
        <h3>Non-release milestone</h3>
        <p>This must stay planned no matter what.</p>
      </article>
    </li>
  </ol>
</body>
</html>
"""


def test_promote_en() -> None:
    print("\npromote_planned_card() — EN locale:")
    locale = LOCALES["en"]
    html = _fixture(
        "en", "Planned",
        "Early September 2026 &middot; v1.7.0",
        "9–12 June 2026 &middot; Stockholm",
        '<p class="roadmap-updated">Last updated <time datetime="2026-05-23">23 May 2026</time> · last reviewed against the internal working document on <time datetime="2026-05-23">23 May 2026</time>.</p>',
    )
    out, changed = promote_planned_card(html, "1.7.0", "2026-09-08", locale)
    expect("changed flag is True", changed, True)
    expect("class flipped to shipped",
           '<li class="rm-entry shipped">' in out, True)
    expect("pill label changed to 'Shipped'",
           'class="rm-pill shipped"><span class="dot" aria-hidden="true"></span>Shipped</span>' in out, True)
    expect("date formatted as EN convention",
           '<span class="when">8 September 2026 &middot; v1.7.0</span>' in out, True)
    expect("notes-link inserted with EN text",
           '<a class="notes-link" href="https://github.com/EISSeuropa/netsec.github.io/releases/tag/v1.7.0" target="_blank" rel="noopener">Release notes</a>' in out, True)
    expect("non-release milestone stayed planned",
           '<li class="rm-entry planned rm-milestone">' in out, True)


def test_promote_fr() -> None:
    print("\npromote_planned_card() — FR locale:")
    locale = LOCALES["fr"]
    html = _fixture(
        "fr", "Planifié",
        "Début septembre 2026 &middot; v1.7.0",
        "9–12 juin 2026 &middot; Stockholm",
        '<p class="roadmap-updated">Dernière mise à jour le <time datetime="2026-05-23">23 mai 2026</time> &middot; dernière vérification par rapport au document de travail interne le <time datetime="2026-05-23">23 mai 2026</time>.</p>',
    )
    out, changed = promote_planned_card(html, "1.7.0", "2026-09-08", locale)
    expect("changed flag is True", changed, True)
    expect("pill text flipped to 'Livrée'",
           '<span class="dot" aria-hidden="true"></span>Livrée</span>' in out, True)
    expect("date formatted as FR convention (lowercase month, no period)",
           '<span class="when">8 septembre 2026 &middot; v1.7.0</span>' in out, True)
    expect("notes-link text is 'Notes de version'",
           ">Notes de version</a>" in out, True)


def test_promote_de() -> None:
    print("\npromote_planned_card() — DE locale:")
    locale = LOCALES["de"]
    html = _fixture(
        "de", "Geplant",
        "Anfang September 2026 &middot; v1.7.0",
        "9–12 Juni 2026 &middot; Stockholm",
        '<p class="roadmap-updated">Zuletzt aktualisiert am <time datetime="2026-05-23">23. Mai 2026</time> &middot; zuletzt mit dem internen Arbeitsdokument abgeglichen am <time datetime="2026-05-23">23. Mai 2026</time>.</p>',
    )
    out, changed = promote_planned_card(html, "1.7.0", "2026-09-08", locale)
    expect("changed flag is True", changed, True)
    expect("pill text flipped to 'Veröffentlicht'",
           '<span class="dot" aria-hidden="true"></span>Veröffentlicht</span>' in out, True)
    expect("date formatted as DE convention (day with period, capital month)",
           '<span class="when">8. September 2026 &middot; v1.7.0</span>' in out, True)
    expect("notes-link text is 'Release-Notizen'",
           ">Release-Notizen</a>" in out, True)


def test_idempotent_rerun() -> None:
    print("\npromote_planned_card() — idempotent on re-run:")
    locale = LOCALES["en"]
    html = _fixture(
        "en", "Planned",
        "Early September 2026 &middot; v1.7.0",
        "9–12 June 2026 &middot; Stockholm",
        '<p class="roadmap-updated">Last updated <time datetime="2026-05-23">23 May 2026</time> · last reviewed against the internal working document on <time datetime="2026-05-23">23 May 2026</time>.</p>',
    )
    once, _ = promote_planned_card(html, "1.7.0", "2026-09-08", locale)
    twice, changed_2 = promote_planned_card(once, "1.7.0", "2026-09-08", locale)
    expect("second run reports no change", changed_2, False)
    expect("notes-link not duplicated",
           once.count('releases/tag/v1.7.0'), twice.count('releases/tag/v1.7.0'))
    expect("class 'shipped' not stacked",
           once.count('class="rm-entry shipped"'),
           twice.count('class="rm-entry shipped"'))


def test_non_matching_version_is_safe() -> None:
    print("\npromote_planned_card() — non-matching version is a no-op:")
    locale = LOCALES["en"]
    html = _fixture(
        "en", "Planned",
        "Early September 2026 &middot; v1.7.0",
        "9–12 June 2026 &middot; Stockholm",
        '<p class="roadmap-updated">Last updated <time datetime="2026-05-23">23 May 2026</time> · last reviewed against the internal working document on <time datetime="2026-05-23">23 May 2026</time>.</p>',
    )
    out, changed = promote_planned_card(html, "9.9.9", "2026-09-08", locale)
    expect("changed flag is False", changed, False)
    expect("html unchanged", out, html)


def test_milestone_never_promoted() -> None:
    print("\npromote_planned_card() — non-release milestone never promotes:")
    # Construct a fixture where the milestone row has a string that
    # superficially looks like a version (rare in practice — the
    # Stockholm row's when-text is `9–12 June 2026 &middot; Stockholm`,
    # no version — but worth pinning).
    locale = LOCALES["en"]
    html = _fixture(
        "en", "Planned",
        "Early September 2026 &middot; v1.7.0",
        # Intentionally including a fake `v1.5.0` token in the milestone
        # to test that rm-milestone still suppresses the match.
        "9–12 June 2026 &middot; Stockholm (post-v1.5.0)",
        '<p class="roadmap-updated">Last updated <time datetime="2026-05-23">23 May 2026</time> · last reviewed against the internal working document on <time datetime="2026-05-23">23 May 2026</time>.</p>',
    )
    out, changed = promote_planned_card(html, "1.5.0", "2026-09-08", locale)
    # v1.5.0 doesn't match the v1.7.0 release card, and rm-milestone
    # suppresses the milestone match, so no change should happen at all.
    expect("nothing changed", changed, False)
    expect("milestone still planned",
           '<li class="rm-entry planned rm-milestone">' in out, True)
    expect("both planned pills survive (release v1.7.0 + milestone)",
           out.count('<span class="rm-pill planned">'), 2)


def test_bump_updated_stamp_en() -> None:
    print("\nbump_updated_stamp() — EN:")
    locale = LOCALES["en"]
    html = (
        '<p class="roadmap-updated">Last updated '
        '<time datetime="2026-05-23">23 May 2026</time> · last reviewed '
        'against the internal working document on '
        '<time datetime="2026-05-23">23 May 2026</time>.</p>'
    )
    out, changed = bump_updated_stamp(html, "2026-09-08", locale)
    expect("changed flag is True", changed, True)
    expect("both <time> datetimes bumped",
           out.count('datetime="2026-09-08"'), 2)
    expect("both visible dates bumped",
           out.count(">8 September 2026<"), 2)


def test_bump_updated_stamp_fr_de() -> None:
    print("\nbump_updated_stamp() — FR + DE date formats:")
    fr = LOCALES["fr"]
    fr_html = (
        '<p class="roadmap-updated">Dernière mise à jour le '
        '<time datetime="2026-05-23">23 mai 2026</time> &middot; dernière '
        'vérification par rapport au document de travail interne le '
        '<time datetime="2026-05-23">23 mai 2026</time>.</p>'
    )
    out, _ = bump_updated_stamp(fr_html, "2026-09-08", fr)
    expect("FR uses lowercase month, no period",
           out.count(">8 septembre 2026<"), 2)

    de = LOCALES["de"]
    de_html = (
        '<p class="roadmap-updated">Zuletzt aktualisiert am '
        '<time datetime="2026-05-23">23. Mai 2026</time> &middot; zuletzt '
        'mit dem internen Arbeitsdokument abgeglichen am '
        '<time datetime="2026-05-23">23. Mai 2026</time>.</p>'
    )
    out, _ = bump_updated_stamp(de_html, "2026-09-08", de)
    expect("DE uses day-with-period + capital month",
           out.count(">8. September 2026<"), 2)


# ─────────────── CHANGELOG-derived body (issue #233) ───────────────

_CHANGELOG = """# Changelog

## [Unreleased]

> Nothing yet.

## [1.7.0] · 2026-09-08 — Directory keyword filter and release automation

> The release that taught the *roadmap* script to read `CHANGELOG.md`. Cards now show what shipped, not what we guessed they would.

### Some theme

Prose.

#### Added

- A thing. [#1](https://example.com/1).

## [1.6.1] · 2026-05-24 — Pre-ESSC polish

> Earlier release lede.
"""

_CHANGELOG_PATCH = """# Changelog

## [1.7.1] · 2026-09-20 — Quality patch

### Index of changes

#### Changed

- Tidied.

#### Fixed

- A bug.

## [1.7.0] · 2026-09-08 — Earlier
"""


def test_parse_changelog_title_and_lede() -> None:
    print("\nparse_changelog_section() — title + lede:")
    title, lede = parse_changelog_section("1.7.0", _CHANGELOG)
    expect("title is text after the em-dash",
           title, "Directory keyword filter and release automation")
    expect("lede emphasis converted to <em>",
           "<em>roadmap</em>" in lede, True)
    expect("lede code span converted to <code>",
           "<code>CHANGELOG.md</code>" in lede, True)
    expect("lede has no leading '>' marker",
           lede.startswith("The release"), True)


def test_parse_changelog_missing_section() -> None:
    print("\nparse_changelog_section() — missing section is None:")
    expect("absent version returns None",
           parse_changelog_section("9.9.9", _CHANGELOG), None)


def test_parse_changelog_patch_fallback() -> None:
    print("\nparse_changelog_section() — patch fallback lede:")
    title, lede = parse_changelog_section("1.7.1", _CHANGELOG_PATCH)
    expect("title parsed", title, "Quality patch")
    expect("synthesised lede names the sub-sections present",
           "changed" in lede.lower() and "fixed" in lede.lower(), True)
    expect("synthesised lede did not pull a real blockquote",
           "Maintenance release" in lede, True)


def test_body_replacement_en() -> None:
    print("\npromote_planned_card() — body replaced from CHANGELOG (EN):")
    locale = LOCALES["en"]
    html = _fixture(
        "en", "Planned",
        "Early September 2026 &middot; v1.7.0",
        "9–12 June 2026 &middot; Stockholm",
        '<p class="roadmap-updated">Last updated <time datetime="2026-05-23">23 May 2026</time> · last reviewed against the internal working document on <time datetime="2026-05-23">23 May 2026</time>.</p>',
    )
    body = ("Directory keyword filter and release automation",
            "Cards now read the <code>CHANGELOG.md</code>.")
    out, changed = promote_planned_card(
        html, "1.7.0", "2026-09-08", locale, card_body=body,
    )
    expect("changed flag is True", changed, True)
    expect("h3 replaced with CHANGELOG title",
           "<h3>Directory keyword filter and release automation</h3>" in out, True)
    expect("p replaced with CHANGELOG lede",
           "<p>Cards now read the <code>CHANGELOG.md</code>.</p>" in out, True)
    expect("pre-written planned body is gone",
           "Pre-written description" not in out, True)


def test_body_untouched_without_card_body() -> None:
    print("\npromote_planned_card() — body untouched when card_body=None:")
    locale = LOCALES["en"]
    html = _fixture(
        "en", "Planned",
        "Early September 2026 &middot; v1.7.0",
        "9–12 June 2026 &middot; Stockholm",
        '<p class="roadmap-updated">Last updated <time datetime="2026-05-23">23 May 2026</time> · last reviewed against the internal working document on <time datetime="2026-05-23">23 May 2026</time>.</p>',
    )
    out, _ = promote_planned_card(html, "1.7.0", "2026-09-08", locale)
    expect("planned body preserved when no card_body given",
           "Pre-written description that the script should not touch." in out, True)


# Multi-quarter fixture for relocation tests. A Q2 timeline with one
# shipped card, then a Q3 timeline carrying the planned v1.7.0 release
# and a non-release milestone.
def _multi_quarter_fixture(prefix: str) -> str:
    return f"""<!DOCTYPE html>
<html><body>
    <div class="rm-quarter">
      <h2>{prefix}2 2026</h2>
    </div>
    <ol class="rm-timeline">
      <li class="rm-entry shipped">
        <article class="rm-card">
          <div class="rm-head">
            <span class="rm-pill shipped"><span class="dot" aria-hidden="true"></span>Shipped</span>
            <span class="when">20 May 2026 &middot; v1.0.0</span>
          </div>
          <h3>Earlier</h3>
          <p>Shipped already.</p>
        </article>
      </li>
    </ol>

    <div class="rm-quarter">
      <h2>{prefix}3 2026</h2>
    </div>
    <ol class="rm-timeline">
      <li class="rm-entry shipped">
        <article class="rm-card">
          <div class="rm-head">
            <span class="rm-pill shipped"><span class="dot" aria-hidden="true"></span>Shipped</span>
            <span class="when">8 September 2026 &middot; v1.7.0</span>
          </div>
          <h3>The release</h3>
          <p>Body.</p>
        </article>
      </li>
      <li class="rm-entry planned">
        <article class="rm-card">
          <div class="rm-head">
            <span class="rm-pill planned"><span class="dot" aria-hidden="true"></span>Planned</span>
            <span class="when">Late 2026 &middot; v1.8.0</span>
          </div>
          <h3>Future</h3>
          <p>Planned.</p>
        </article>
      </li>
    </ol>
</body></html>
"""


def test_relocate_across_quarters() -> None:
    print("\nrelocate_card_to_quarter() — moves card to ship-date quarter:")
    locale = LOCALES["en"]
    html = _multi_quarter_fixture("Q")
    # v1.7.0 lives in Q3 but ship date 2026-05-15 is Q2 → should move.
    out, moved = relocate_card_to_quarter(html, "1.7.0", "2026-05-15", locale)
    expect("moved flag is True", moved, True)
    # The v1.7.0 card should now precede the Q3 heading.
    expect("v1.7.0 card now sits before Q3 heading",
           out.index("v1.7.0") < out.index("<h2>Q3 2026</h2>"), True)
    # And land after the existing Q2 shipped card (v1.0.0) but before
    # the Q3 div — i.e. inside the first <ol>.
    expect("v1.0.0 still precedes v1.7.0 (appended after shipped)",
           out.index("v1.0.0") < out.index("v1.7.0"), True)
    # Q3 planned card must stay put.
    expect("planned v1.8.0 untouched in Q3",
           out.index("v1.8.0") > out.index("<h2>Q3 2026</h2>"), True)


def test_relocate_same_quarter_noop() -> None:
    print("\nrelocate_card_to_quarter() — no-op when already in quarter:")
    locale = LOCALES["en"]
    html = _multi_quarter_fixture("Q")
    # Ship date in Q3 (where v1.7.0 already lives) → no move.
    out, moved = relocate_card_to_quarter(html, "1.7.0", "2026-09-08", locale)
    expect("moved flag is False", moved, False)
    expect("html unchanged", out, html)


def test_relocate_fr_quarter_prefix() -> None:
    print("\nrelocate_card_to_quarter() — FR uses 'T' prefix:")
    locale = LOCALES["fr"]
    html = _multi_quarter_fixture("T")
    out, moved = relocate_card_to_quarter(html, "1.7.0", "2026-05-15", locale)
    expect("moved with FR trimestre headings", moved, True)
    expect("v1.7.0 now before T3 heading",
           out.index("v1.7.0") < out.index("<h2>T3 2026</h2>"), True)


def test_needs_translation_marker_count() -> None:
    print("\nFR/DE body carries exactly one [needs translation] marker:")
    # Mirror what main() does: append the locale marker to the lede.
    for lang in ("fr", "de"):
        locale = LOCALES[lang]
        title, lede = "Some title", "Some lede."
        localized = (title, lede + locale["needs_translation"])
        html = _fixture(
            lang, locale["pill_planned"],
            "Late 2026 &middot; v1.7.0",
            "9–12 June 2026 &middot; Stockholm",
            "<p class=\"roadmap-updated\">x</p>",
        )
        out, _ = promote_planned_card(
            html, "1.7.0", "2026-09-08", locale, card_body=localized,
        )
        marker = locale["needs_translation"].strip()
        expect(f"{lang}: marker present exactly once",
               out.count(marker), 1)


def main() -> None:
    test_promote_en()
    test_promote_fr()
    test_promote_de()
    test_idempotent_rerun()
    test_non_matching_version_is_safe()
    test_milestone_never_promoted()
    test_bump_updated_stamp_en()
    test_bump_updated_stamp_fr_de()
    test_parse_changelog_title_and_lede()
    test_parse_changelog_missing_section()
    test_parse_changelog_patch_fallback()
    test_body_replacement_en()
    test_body_untouched_without_card_body()
    test_relocate_across_quarters()
    test_relocate_same_quarter_noop()
    test_relocate_fr_quarter_prefix()
    test_needs_translation_marker_count()
    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
