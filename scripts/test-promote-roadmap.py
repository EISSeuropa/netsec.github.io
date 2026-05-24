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


def main() -> None:
    test_promote_en()
    test_promote_fr()
    test_promote_de()
    test_idempotent_rerun()
    test_non_matching_version_is_safe()
    test_milestone_never_promoted()
    test_bump_updated_stamp_en()
    test_bump_updated_stamp_fr_de()
    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
