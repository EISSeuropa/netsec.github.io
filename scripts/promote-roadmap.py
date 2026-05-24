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

import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Card-body staleness check (option 1, git-blame age). At release
# time, after the script has flipped the status pill, run `git blame`
# on the planned card's <p> prose and report how long ago it was
# last touched. If the age exceeds this threshold, print a warning
# so the maintainer remembers to refresh the body before tag + GH
# Release land. 30 days is a balance between false-positives (cards
# polished a month before release look fresh by blame but might
# still describe wrong scope) and missing genuinely-stale bodies.
# The check is best-effort: subprocess failures, missing git history,
# or unparseable blame output silently skip the warning rather than
# blocking release.sh.
CARD_BODY_AGE_THRESHOLD_DAYS = 30

# Per-locale strings. Keep the keys aligned across locales: anywhere
# the script needs a localised label, this is the single source of
# truth so a typo in DE doesn't quietly land on production.
LOCALES = {
    "en": {
        "filename": "roadmap.html",
        "pill_planned": "Planned",
        "pill_shipped": "Shipped",
        "notes_link_text": "Release notes",
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


def promote_planned_card(
    html: str, version: str, iso_date: str, locale: dict,
) -> tuple[str, bool]:
    """If a planned card for `v<version>` exists, flip it to shipped.

    Strict matching: only `<li class="rm-entry planned">` (without
    `rm-milestone`) whose `<span class="when">` text contains the
    exact string `v<version>` (so non-release planned milestones like
    the Stockholm event stay planned).

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


def find_planned_card_lines(
    html: str, version: str,
) -> tuple[int, int] | None:
    """Locate the planned card's prose body in `html` and return its
    (start_line, end_line) 1-indexed range, or None if no planned card
    for this version exists. The range covers the <p> inside the
    <article>, not the wrapper <li>, since the body is what we're
    checking for staleness. Lines are 1-based to match git's
    `-L start,end` convention."""
    # Match the planned card by version, then narrow to its <p>.
    card_re = re.compile(
        r'<li class="rm-entry planned"(?:\s+rm-milestone)?>'
        r'.*?<span class="when">[^<]*\bv'
        + re.escape(version)
        + r'\b.*?</li>',
        flags=re.DOTALL,
    )
    m = card_re.search(html)
    if not m:
        return None
    block = m.group(0)
    block_start_offset = m.start()
    # Find the <p>...</p> inside the card. There's typically one
    # body paragraph; if multiple, use the first (the description).
    p_re = re.compile(r'<p>.*?</p>', flags=re.DOTALL)
    p_match = p_re.search(block)
    if not p_match:
        return None
    p_start_offset = block_start_offset + p_match.start()
    p_end_offset = block_start_offset + p_match.end()
    start_line = html[:p_start_offset].count("\n") + 1
    end_line = html[:p_end_offset].count("\n") + 1
    return (start_line, end_line)


def git_blame_max_age_days(
    file_path: Path, start_line: int, end_line: int,
) -> int | None:
    """Run `git blame` on the line range and return how many days
    have passed since the most recent commit that touched any line
    in the range. Returns None on any subprocess error or unparseable
    output. Best-effort by design: a missing git history shouldn't
    abort the release."""
    try:
        result = subprocess.run(
            ["git", "blame", "--porcelain",
             "-L", f"{start_line},{end_line}",
             "--", str(file_path)],
            capture_output=True, text=True, cwd=ROOT,
            check=True, timeout=10,
        )
    except (subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            FileNotFoundError):
        return None
    # Porcelain output: each commit block contains a
    # "committer-time <unix-timestamp>" header line for each
    # blamed line. We want the newest (largest) timestamp.
    timestamps: list[int] = []
    for line in result.stdout.splitlines():
        if line.startswith("committer-time "):
            try:
                timestamps.append(int(line.split()[1]))
            except (ValueError, IndexError):
                continue
    if not timestamps:
        return None
    newest = max(timestamps)
    age_seconds = time.time() - newest
    return int(age_seconds // 86400)


def maybe_warn_stale_card_body(
    file_path: Path, html: str, version: str, lang: str,
) -> None:
    """Print a warning if the planned card's body looks stale.
    Called AFTER promotion succeeds. Best-effort: silently no-ops
    on any signal we can't interpret (missing card, blame failure,
    threshold not met). The expensive consequence is letting a
    stale card body ship with a release; the cheap one is occasional
    false positives."""
    line_range = find_planned_card_lines(html, version)
    if line_range is None:
        # No planned card found in the post-promotion HTML — expected,
        # since the promotion just flipped it to "shipped". Re-search
        # for the shipped card to get its line range instead.
        shipped_re = re.compile(
            r'<li class="rm-entry shipped"(?:\s+rm-milestone)?>'
            r'.*?<span class="when">[^<]*\bv'
            + re.escape(version)
            + r'\b.*?</li>',
            flags=re.DOTALL,
        )
        m = shipped_re.search(html)
        if not m:
            return
        block = m.group(0)
        block_start_offset = m.start()
        p_match = re.search(r'<p>.*?</p>', block, flags=re.DOTALL)
        if not p_match:
            return
        line_range = (
            html[:block_start_offset + p_match.start()].count("\n") + 1,
            html[:block_start_offset + p_match.end()].count("\n") + 1,
        )
    age = git_blame_max_age_days(file_path, *line_range)
    if age is None or age < CARD_BODY_AGE_THRESHOLD_DAYS:
        return
    print(
        f"  ⚠ {lang}: card body for v{version} was last touched "
        f"{age} days ago (threshold {CARD_BODY_AGE_THRESHOLD_DAYS}). "
        f"That's probably the planned scope from when the card was "
        f"written, not what actually shipped. Review {file_path.name} "
        f"lines {line_range[0]}–{line_range[1]} and edit the body "
        f"in a follow-up commit on this release branch before the "
        f"tag + GH Release land."
    )


def main() -> None:
    version, iso_date, dry_run = parse_args(sys.argv)

    any_card_promoted = False
    any_stamp_bumped = False
    any_already_current = False

    for lang, locale in LOCALES.items():
        path = ROOT / locale["filename"]
        if not path.exists():
            print(f"  · {lang}: {locale['filename']} not found, skipping.")
            continue
        original = path.read_text(encoding="utf-8")
        updated = original
        updated, promoted = promote_planned_card(
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
        if bumped:
            past_bits.append(f"bumped updated stamp to {iso_date}")
            future_bits.append(f"bump updated stamp to {iso_date}")
            any_stamp_bumped = True
        if dry_run:
            print(f"  · {lang}: [dry-run] would {' + '.join(future_bits)}.")
        else:
            path.write_text(updated, encoding="utf-8")
            print(f"  · {lang}: {' + '.join(past_bits)}.")
            # Staleness check on the just-promoted card body.
            # `updated` is the post-promotion HTML, so the card is
            # now `class="rm-entry shipped"`; the helper handles both
            # planned + shipped lookups. Best-effort: silently no-ops
            # on any subprocess error.
            if promoted:
                maybe_warn_stale_card_body(path, updated, version, lang)

    # Soft warning: if nothing happened AND no locale was already at
    # the desired state, the maintainer probably forgot to add a
    # v<version> card before running release.sh. Exit 2 surfaces this
    # without aborting release.sh (the maintainer can decide whether
    # to commit + tag anyway).
    nothing_happened = (
        not any_card_promoted
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
