#!/usr/bin/env python3
"""
Promote the public roadmap cards for a just-shipped release.

For each of `roadmap.html`, `roadmap.fr.html`, `roadmap.de.html`:

  - Find the `<li class="rm-entry planned">` whose `<span class="when">`
    mentions `v<VERSION>` (matching strictly on SemVer, so non-release
    planned milestones like the Stockholm event are never touched).
  - Flip its CSS class, status-pill text, "when" date, and append a
    `Release notes` link to the GitHub Release page.
  - Bump both `<time datetime="...">` elements + the visible date
    text in the `<p class="roadmap-updated">` paragraph at the top
    of the page so the freshness stamp matches the release date.

All three locale strings (pill text, notes-link text, month name,
date layout) are kept in the LOCALES table below.

Idempotent by design:
  - Re-promoting an already-shipped card no-ops.
  - Re-inserting the notes-link skips when one already exists.
  - Re-bumping the date stamp to the same value writes nothing.

Designed to be called from scripts/release.sh after the changelog
promotion but before the release commit, so the roadmap.html edits
land in the same commit + tag as the changelog promotion.

Usage:
    python3 scripts/promote-roadmap.py <version> [<iso-date>] [--dry-run]

    <version>   X.Y.Z (no leading "v"; the script adds it).
    <iso-date>  Optional YYYY-MM-DD. Defaults to today (UTC).
    --dry-run   Print what would change without writing any file.

Exit codes:
    0   success (one or more locales updated, OR all already up-to-date).
    1   bad usage / arg parsing.
    2   no locale had a matching planned card AND no last-updated stamp
        moved. Likely the maintainer forgot to write the v<VERSION>
        card. Surfaces the problem rather than silently no-opping.
"""
from __future__ import annotations

import html as _html
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = ROOT / "CHANGELOG.md"

# Card title + body are derived from CHANGELOG.md at promote time
# (see parse_changelog_section). The planned card's hand-authored
# <h3> + <p> describe *planned* scope; what actually ships often
# differs, so we overwrite both with the released section's heading
# title and lede. This replaced an earlier git-blame staleness
# warning that fired to stderr only *after* the wrong body had
# already landed — structurally too late (see issue #233).

# Per-locale strings. Keep the keys aligned across locales: anywhere
# the script needs a localised label, this is the single source of
# truth so a typo in DE doesn't quietly land on production.
LOCALES = {
    "en": {
        "filename": "roadmap.html",
        "pill_planned": "Planned",
        "pill_shipped": "Shipped",
        "notes_link_text": "Release notes",
        # Quarter heading prefix on this locale's <h2> (e.g. "Q2 2026").
        # FR uses "Trimestre" → "T"; EN + DE both use "Q".
        "quarter_prefix": "Q",
        # Appended to the lede on non-EN cards whose body was overwritten
        # with EN CHANGELOG content, so check-i18n-drift.py flags the card
        # for a human translation pass (CLAUDE.md §1). Empty for EN.
        "needs_translation": "",
        "months": [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ],
        # `format_date(day, month_idx, year)` returns the localised
        # human-readable form. EN style: "24 May 2026" — day, month
        # word, year, all space-separated, no comma, no period.
        "format_date": (
            lambda d, mname, y: f"{d} {mname} {y}"
        ),
        # The visible-date prose around the two <time> elements in
        # <p class="roadmap-updated">. The script matches this
        # pattern, captures the dates, and substitutes today's.
        "updated_pattern": re.compile(
            r'(<p class="roadmap-updated">Last updated '
            r'<time datetime=")\d{4}-\d{2}-\d{2}(">)[^<]+(</time>'
            r' · last reviewed against the internal working document on '
            r'<time datetime=")\d{4}-\d{2}-\d{2}(">)[^<]+(</time>)',
        ),
    },
    "fr": {
        "filename": "roadmap.fr.html",
        "pill_planned": "Planifié",
        "pill_shipped": "Livrée",
        "notes_link_text": "Notes de version",
        "quarter_prefix": "T",
        "needs_translation": " [à traduire]",
        "months": [
            "janvier", "février", "mars", "avril", "mai", "juin",
            "juillet", "août", "septembre", "octobre", "novembre", "décembre",
        ],
        # FR style: "24 mai 2026" — lowercase month, space-separated.
        "format_date": (
            lambda d, mname, y: f"{d} {mname} {y}"
        ),
        "updated_pattern": re.compile(
            r'(<p class="roadmap-updated">Dernière mise à jour le '
            r'<time datetime=")\d{4}-\d{2}-\d{2}(">)[^<]+(</time>'
            r' &middot; dernière vérification par rapport au document de travail interne le '
            r'<time datetime=")\d{4}-\d{2}-\d{2}(">)[^<]+(</time>)',
        ),
    },
    "de": {
        "filename": "roadmap.de.html",
        "pill_planned": "Geplant",
        "pill_shipped": "Veröffentlicht",
        "notes_link_text": "Release-Notizen",
        "quarter_prefix": "Q",
        "needs_translation": " [zu übersetzen]",
        "months": [
            "Januar", "Februar", "März", "April", "Mai", "Juni",
            "Juli", "August", "September", "Oktober", "November", "Dezember",
        ],
        # DE style: "24. Mai 2026" — day with trailing period,
        # capitalised month, space-separated.
        "format_date": (
            lambda d, mname, y: f"{d}. {mname} {y}"
        ),
        "updated_pattern": re.compile(
            r'(<p class="roadmap-updated">Zuletzt aktualisiert am '
            r'<time datetime=")\d{4}-\d{2}-\d{2}(">)[^<]+(</time>'
            r' &middot; zuletzt mit dem internen Arbeitsdokument abgeglichen am '
            r'<time datetime=")\d{4}-\d{2}-\d{2}(">)[^<]+(</time>)',
        ),
    },
}

# Stable URL prefix for the GitHub release page (no trailing slash).
RELEASE_URL_PREFIX = (
    "https://github.com/EISSeuropa/netsec.github.io/releases/tag/v"
)


# ──────────────────────────── helpers ────────────────────────────


def parse_args(argv: list[str]) -> tuple[str, str, bool]:
    """Return (version, iso_date, dry_run). Exits on bad usage."""
    args = [a for a in argv[1:] if a != "--dry-run"]
    dry_run = "--dry-run" in argv[1:]
    if len(args) < 1 or len(args) > 2:
        print(
            "usage: promote-roadmap.py <version> [<iso-date>] [--dry-run]",
            file=sys.stderr,
        )
        sys.exit(1)
    version = args[0]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        print(f"✗ Version must be X.Y.Z (got {version!r}).", file=sys.stderr)
        sys.exit(1)
    if len(args) == 2:
        iso_date = args[1]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", iso_date):
            print(
                f"✗ Date must be YYYY-MM-DD (got {iso_date!r}).",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        iso_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return version, iso_date, dry_run


# ─────────────────── CHANGELOG-derived card body ───────────────────


def _markdown_inline_to_html(text: str) -> str:
    """Convert the small slice of inline Markdown that appears in a
    CHANGELOG lede into the HTML the roadmap card expects. Handles
    code spans, links, bold, and emphasis; HTML-escapes everything
    else first so a literal `<head>` in a code span renders safely.
    The lede is trusted maintainer copy, so this is deliberately
    minimal rather than a full Markdown parser."""
    # Escape &, <, > first (leave quotes alone — they read fine in
    # body prose and we don't want &quot; noise). The Markdown markers
    # below are all ASCII punctuation untouched by escaping.
    text = _html.escape(text, quote=False)
    # Links: [label](url) → <a href="url">label</a>.
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2">\1</a>',
        text,
    )
    # Code spans: `code` → <code>code</code>.
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    # Bold before emphasis so **x** doesn't get eaten by the *x* rule.
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
    return text


def _extract_lede(section_body: str) -> str | None:
    """Return the first blockquote paragraph (the `> …` lede) of a
    CHANGELOG section, joined to a single line with the `> ` markers
    stripped, or None if the section has no blockquote (patch
    releases ship index-only)."""
    lines = section_body.splitlines()
    quote: list[str] = []
    started = False
    for line in lines:
        if line.startswith(">"):
            started = True
            quote.append(re.sub(r"^>\s?", "", line))
        elif started:
            # Blockquote ended (first non-`>` line after it began).
            break
    if not quote:
        return None
    # A lede may wrap across several `>` lines; join on spaces and
    # collapse the runs of whitespace that introduces.
    return re.sub(r"\s+", " ", " ".join(quote)).strip()


def _synthesize_lede(section_body: str) -> str:
    """Fallback lede for index-only patch releases that carry no
    blockquote. Joins the `#### Added / Changed / Fixed …` sub-section
    labels present into one sentence."""
    labels = re.findall(r"^#### (\w[\w ]*)$", section_body, flags=re.MULTILINE)
    seen: list[str] = []
    for lbl in labels:
        lbl = lbl.strip()
        if lbl and lbl not in seen:
            seen.append(lbl)
    if not seen:
        return "Maintenance release. See the changelog for details."
    if len(seen) == 1:
        joined = seen[0].lower()
    else:
        joined = ", ".join(s.lower() for s in seen[:-1]) + " and " + seen[-1].lower()
    return f"Maintenance release covering {joined}. See the changelog for details."


def parse_changelog_section(
    version: str, changelog_text: str,
) -> tuple[str, str] | None:
    """Extract (title, lede_html) for the `[<version>]` section of
    CHANGELOG.md. Title is the text after the em-dash on the section
    heading; lede_html is the first blockquote paragraph rendered to
    inline HTML, or a synthesised sentence for index-only patches.
    Returns None if the section heading is absent."""
    heading_re = re.compile(
        r"^## \[" + re.escape(version) + r"\][^\n]*?—\s*(.+?)\s*$",
        flags=re.MULTILINE,
    )
    m = heading_re.search(changelog_text)
    if not m:
        return None
    title = m.group(1).strip()
    body_start = m.end()
    nxt = re.search(r"^## \[", changelog_text[body_start:], flags=re.MULTILINE)
    section_body = (
        changelog_text[body_start: body_start + nxt.start()]
        if nxt else changelog_text[body_start:]
    )
    lede = _extract_lede(section_body) or _synthesize_lede(section_body)
    return title, _markdown_inline_to_html(lede)


# ───────────────────── quarter relocation ─────────────────────


def _target_quarter(iso_date: str) -> tuple[int, int]:
    """Return (quarter_number, year) for an ISO date. Q1 = Jan–Mar."""
    y, m, _d = (int(x) for x in iso_date.split("-"))
    return (m - 1) // 3 + 1, y


def _timeline_spans(html: str) -> list[tuple[int, int]]:
    """Return (start, end) offsets of each `<ol class="rm-timeline">…
    </ol>` block, in document order."""
    return [
        (m.start(), m.end())
        for m in re.finditer(
            r'<ol class="rm-timeline">.*?</ol>', html, flags=re.DOTALL,
        )
    ]


def _heading_before(html: str, offset: int) -> str | None:
    """Return the text of the nearest `<h2>…</h2>` before `offset`
    (the quarter heading governing the timeline that follows)."""
    heads = list(re.finditer(r"<h2[^>]*>([^<]*)</h2>", html[:offset]))
    return heads[-1].group(1).strip() if heads else None


def relocate_card_to_quarter(
    html: str, version: str, iso_date: str, locale: dict,
) -> tuple[str, bool]:
    """Move the just-shipped `v<version>` card into the `<ol>` for the
    quarter matching its ship date, inserting after that quarter's
    existing shipped cards and before its first planned card.

    No-op (returns (html, False)) when the card already sits in the
    right quarter, when no shipped card for the version exists yet,
    or when the destination quarter has no `<ol>` in this file."""
    q, year = _target_quarter(iso_date)
    target_heading = f"{locale['quarter_prefix']}{q} {year}"

    # Locate the full shipped <li> block (with its leading indentation
    # and trailing newline) whose when-span carries v<version>.
    card_m = None
    for m in re.finditer(
        r'[ \t]*<li class="rm-entry shipped(?: [^"]*)?">.*?</li>\n',
        html, flags=re.DOTALL,
    ):
        if re.search(
            rf'<span class="when">[^<]*\bv{re.escape(version)}\b',
            m.group(0),
        ):
            card_m = m
            break
    if card_m is None:
        return html, False

    spans = _timeline_spans(html)
    src = next((s for s in spans if s[0] <= card_m.start() < s[1]), None)
    if src is None or _heading_before(html, src[0]) == target_heading:
        # Card isn't inside a timeline, or already in the right quarter.
        return html, False
    if not any(_heading_before(html, s[0]) == target_heading for s in spans):
        # Destination quarter doesn't exist on this page; leave the
        # card where it is rather than fabricate a section.
        return html, False

    card_text = card_m.group(0)
    without = html[: card_m.start()] + html[card_m.end():]

    # Re-find the destination timeline in the card-removed document.
    dest = next(
        s for s in _timeline_spans(without)
        if _heading_before(without, s[0]) == target_heading
    )
    ol_text = without[dest[0]: dest[1]]
    planned = re.search(r'[ \t]*<li class="rm-entry planned', ol_text)
    if planned:
        insert_at = dest[0] + planned.start()
    else:
        insert_at = dest[0] + re.search(r"[ \t]*</ol>", ol_text).start()
    return without[:insert_at] + card_text + without[insert_at:], True


def promote_planned_card(
    html: str, version: str, iso_date: str, locale: dict,
    card_body: tuple[str, str] | None = None,
) -> tuple[str, bool]:
    """If a planned card for `v<version>` exists, flip it to shipped.

    Strict matching: only `<li class="rm-entry planned">` (without
    `rm-milestone`) whose `<span class="when">` text contains the
    exact string `v<version>` (so non-release planned milestones like
    the Stockholm event stay planned).

    When `card_body` is given as `(title, lede_html)`, the card's
    `<h3>` and first `<p>` are overwritten with it (the
    CHANGELOG-derived title + lede). When None, the hand-authored
    body is left untouched.

    Returns (new_html, was_changed). Idempotent: an already-shipped
    card or a missing card both return (html, False).
    """
    # 1. Locate the candidate <li>. Match the most permissive
    #    enclosing form, then narrow:
    #      - class contains "rm-entry"
    #      - class contains "planned"
    #      - class does NOT contain "rm-milestone" (those are non-
    #        release milestones like conferences)
    #      - <span class="when">...v<version>...</span> appears
    #        somewhere inside the <li>
    li_pattern = re.compile(
        r'(<li class="rm-entry planned(?: [^"]*)?">.*?</li>\n?)',
        flags=re.DOTALL,
    )

    def maybe_promote(match: re.Match) -> str:
        block = match.group(1)
        # Strict: bail out if the entry is a non-release milestone.
        if "rm-milestone" in block.split('"', 2)[1]:
            return block
        # Match `vX.Y.Z` inside the when-span as a whole word.
        when_match = re.search(
            r'<span class="when">([^<]*)</span>',
            block,
        )
        if not when_match:
            return block
        when_text = when_match.group(1)
        if not re.search(rf"\bv{re.escape(version)}\b", when_text):
            return block

        # We have a planned card matching the version. Build today's
        # date in the locale's format and rewrite the block.
        y, m, d = (int(x) for x in iso_date.split("-"))
        month_name = locale["months"][m - 1]
        date_str = locale["format_date"](d, month_name, y)
        when_new = f"{date_str} &middot; v{version}"

        new_block = block
        # 1a. Flip the outer class.
        new_block = re.sub(
            r'^<li class="rm-entry planned"',
            '<li class="rm-entry shipped"',
            new_block,
            count=1,
        )
        # 1b. Flip the inner pill class + label. The pill text comes
        #     immediately after `</span>` (the dot span). Be precise
        #     so we don't accidentally rename other "planned" tokens
        #     somewhere in the description prose.
        pill_re = re.compile(
            r'<span class="rm-pill planned">'
            r'<span class="dot" aria-hidden="true"></span>'
            + re.escape(locale["pill_planned"])
            + r'</span>'
        )
        pill_new = (
            '<span class="rm-pill shipped">'
            '<span class="dot" aria-hidden="true"></span>'
            + locale["pill_shipped"]
            + '</span>'
        )
        new_block = pill_re.sub(pill_new, new_block, count=1)
        # 1c. Replace the when-span content.
        new_block = re.sub(
            r'<span class="when">[^<]*</span>',
            f'<span class="when">{when_new}</span>',
            new_block,
            count=1,
        )
        # 1d. Add the notes-link before `</article>` IF none exists
        #     yet for this version. Idempotency guard: if a maintainer
        #     already added it by hand, don't double-insert.
        notes_link = (
            f'<a class="notes-link" href="{RELEASE_URL_PREFIX}{version}" '
            f'target="_blank" rel="noopener">'
            f'{locale["notes_link_text"]}</a>'
        )
        if notes_link in new_block:
            pass  # already there
        elif RELEASE_URL_PREFIX + version in new_block:
            # A link to the same release URL exists but the rendering
            # differs (different text, different attrs). Leave it.
            pass
        else:
            # Insert just before </article>, preserving the surrounding
            # whitespace + indentation. The existing pattern in the
            # file is:
            #     [10 spaces]<a class="notes-link" ...>...</a>
            #     [8 spaces]</article>
            new_block = re.sub(
                r'(\n)(\s*)</article>',
                rf'\1\2  {notes_link}\1\2</article>',
                new_block,
                count=1,
            )
        # 1e. Overwrite the title + body with the CHANGELOG-derived
        #     content, so the shipped card describes what actually
        #     shipped rather than the planned scope written months ago.
        if card_body is not None:
            title, lede_html = card_body
            new_block = re.sub(
                r"<h3>.*?</h3>",
                "<h3>" + _html.escape(title, quote=False) + "</h3>",
                new_block, count=1, flags=re.DOTALL,
            )
            new_block = re.sub(
                r"<p>.*?</p>",
                "<p>" + lede_html + "</p>",
                new_block, count=1, flags=re.DOTALL,
            )
        return new_block

    new_html, n_subs = li_pattern.subn(maybe_promote, html)
    return new_html, new_html != html


def bump_updated_stamp(
    html: str, iso_date: str, locale: dict,
) -> tuple[str, bool]:
    """Refresh the two `<time>` stamps + the visible date text in the
    `<p class="roadmap-updated">` paragraph at the top of the page.

    Returns (new_html, was_changed). Idempotent — if both stamps
    already read `iso_date`, returns (html, False).
    """
    y, m, d = (int(x) for x in iso_date.split("-"))
    month_name = locale["months"][m - 1]
    visible = locale["format_date"](d, month_name, y)

    def repl(match: re.Match) -> str:
        # Groups (per the regex above):
        #   1 = "<p class=\"roadmap-updated\">Last updated <time datetime=\""
        #   2 = "\">"  (closes the open-tag of <time>)
        #   3 = "</time> · ... <time datetime=\""
        #   4 = "\">"  (closes the second open-tag)
        #   5 = "</time>" (closes the second <time>)
        # The replacement keeps the prose chrome intact and only
        # rewrites the ISO date attributes + visible-date text.
        return (
            f"{match.group(1)}{iso_date}{match.group(2)}{visible}"
            f"{match.group(3)}{iso_date}{match.group(4)}{visible}"
            f"{match.group(5)}"
        )

    new_html, n = locale["updated_pattern"].subn(repl, html, count=1)
    return new_html, n > 0 and new_html != html


def main() -> None:
    version, iso_date, dry_run = parse_args(sys.argv)

    # Derive the shipped card's title + lede from the CHANGELOG once.
    # If the section is missing (shouldn't happen — release.sh promotes
    # the CHANGELOG before calling us), fall back to leaving the
    # hand-authored body untouched rather than blanking it.
    base_body: tuple[str, str] | None = None
    if CHANGELOG.exists():
        base_body = parse_changelog_section(
            version, CHANGELOG.read_text(encoding="utf-8"),
        )
    if base_body is None:
        print(
            f"  ! No [{version}] section in CHANGELOG.md; leaving card "
            f"bodies untouched (title + lede won't be refreshed).",
            file=sys.stderr,
        )

    any_card_promoted = False
    any_stamp_bumped = False
    any_card_moved = False
    any_already_current = False

    for lang, locale in LOCALES.items():
        path = ROOT / locale["filename"]
        if not path.exists():
            print(f"  · {lang}: {locale['filename']} not found, skipping.")
            continue
        original = path.read_text(encoding="utf-8")
        updated = original
        # Localise the body: EN gets the CHANGELOG content directly;
        # FR + DE get the EN content plus a [needs translation] marker
        # appended to the lede, so check-i18n-drift.py flags the card
        # for a hand translation (no machine translation — CLAUDE.md §1).
        card_body = base_body
        if base_body is not None and locale["needs_translation"]:
            title, lede_html = base_body
            card_body = (title, lede_html + locale["needs_translation"])
        updated, promoted = promote_planned_card(
            updated, version, iso_date, locale, card_body=card_body,
        )
        updated, moved = relocate_card_to_quarter(
            updated, version, iso_date, locale,
        )
        updated, bumped = bump_updated_stamp(updated, iso_date, locale)
        if updated == original:
            # Check whether the file is already at the desired state
            # (idempotent re-run) vs missing the card entirely (the
            # warning case below cares about the difference).
            shipped_marker = (
                f'class="rm-entry shipped"'  # any shipped card
            )
            already_shipped = bool(re.search(
                rf'<li class="rm-entry shipped">[^<]*(?:<[^>]+>[^<]*)*?'
                rf'<span class="when">[^<]*\bv{re.escape(version)}\b',
                original, flags=re.DOTALL,
            ))
            if already_shipped:
                any_already_current = True
                print(f"  · {lang}: already up-to-date for v{version} on {iso_date}.")
            else:
                print(f"  · {lang}: no v{version} card found to promote, "
                      f"stamp already at {iso_date}.")
            continue
        past_bits: list[str] = []
        future_bits: list[str] = []
        if promoted:
            past_bits.append(f"promoted v{version} card to shipped")
            future_bits.append(f"promote v{version} card to shipped")
            any_card_promoted = True
        if moved:
            q, year = _target_quarter(iso_date)
            label = f"{locale['quarter_prefix']}{q} {year}"
            past_bits.append(f"moved card to {label}")
            future_bits.append(f"move card to {label}")
            any_card_moved = True
        if bumped:
            past_bits.append(f"bumped updated stamp to {iso_date}")
            future_bits.append(f"bump updated stamp to {iso_date}")
            any_stamp_bumped = True
        if dry_run:
            print(f"  · {lang}: [dry-run] would {' + '.join(future_bits)}.")
        else:
            path.write_text(updated, encoding="utf-8")
            print(f"  · {lang}: {' + '.join(past_bits)}.")

    # Soft warning: if nothing happened AND no locale was already at
    # the desired state, the maintainer probably forgot to add a
    # v<version> card before running release.sh. Exit 2 surfaces this
    # without aborting release.sh (the maintainer can decide whether
    # to commit + tag anyway).
    nothing_happened = (
        not any_card_promoted
        and not any_card_moved
        and not any_stamp_bumped
        and not any_already_current
    )
    if nothing_happened:
        print(
            f"\n! No locale had a planned card for v{version}, "
            f"no shipped card either, no date stamp moved.\n"
            f"  Did you forget to write the v{version} card in roadmap.html "
            f"(+ FR + DE)\n"
            f"  before running release.sh? See docs/admin-guide.md "
            f"→ 'Cutting a release'.",
            file=sys.stderr,
        )
        sys.exit(2)
    if not any_card_promoted and any_stamp_bumped:
        # Date stamps moved but no planned card was promoted. This is
        # the normal patch-release path (maintainer hand-added a shipped
        # card directly). Print a soft note so the maintainer can
        # double-check on minor/major releases.
        print(
            f"\n  Note: date stamps bumped, but no planned card for "
            f"v{version} was found to promote.\n"
            f"  This is fine for a patch release where the v{version} "
            f"card was already\n"
            f"  hand-added as shipped. For a minor/major release, double-"
            f"check\n"
            f"  the planned card existed before running release.sh.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
