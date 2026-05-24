#!/usr/bin/env python3
"""
Auto-stamp the roadmap doc with current [Unreleased] metrics.

The roadmap (`docs/roadmap-2026.md`) carries a small machine-managed
block between `<!-- AUTOSTAMP:BEGIN -->` and `<!-- AUTOSTAMP:END -->`
markers. This script reads CHANGELOG.md, counts the bullets under
`[Unreleased]` per category, looks up the most recent SemVer tag,
and rewrites that block with the result. Everything else in the
roadmap stays human-edited.

The point is the maintainer never has to "remember to refresh the
roadmap" between releases: any PR that touches CHANGELOG.md fires
.github/workflows/sync-roadmap.yml, which runs this script and
opens an auto-PR with the stamp delta. Auto-merge ships it.

What this script does NOT do:
  - Rewrite the timeline-table rows. The prose synthesis there
    ("Directory keyword pipeline · photo workaround · sync
    robustness") is a maintainer call. The autostamp surfaces
    staleness; the maintainer decides when the prose needs a
    refresh.
  - Promote shipped releases from 📅 to ✅. That's release.sh's
    job (and a §5 cross-check item).
  - Touch the public `/roadmap.html` pages.

Usage:
    python3 scripts/sync-roadmap.py

Exit codes: 0 always. The script is best-effort; missing tag,
empty CHANGELOG, malformed file all produce a no-op stamp rather
than a hard failure. CI shouldn't go red because someone hand-
edited the roadmap and accidentally dropped a marker.
"""
from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = ROOT / "CHANGELOG.md"
ROADMAP = ROOT / "docs" / "roadmap-2026.md"

AUTOSTAMP_START = "<!-- AUTOSTAMP:BEGIN -->"
AUTOSTAMP_END = "<!-- AUTOSTAMP:END -->"


def count_unreleased_bullets(changelog_text: str) -> tuple[int, dict[str, int]]:
    """Parse a CHANGELOG body and count top-level bullets in the
    `[Unreleased]` section, broken down by `#### Added` / `Changed` /
    `Fixed` / `Deprecated` / `Removed` / `Security`.

    Pure: takes the raw text, returns (total, per-category dict).
    The function is tolerant of missing categories and trailing
    whitespace; it returns (0, {}) when no `[Unreleased]` section
    is present.
    """
    # Lift just the [Unreleased] block — from its heading to the next
    # top-level release heading or end-of-file.
    sect = re.search(
        r"^## \[Unreleased\][^\n]*\n(.*?)(?=^## \[|\Z)",
        changelog_text,
        flags=re.DOTALL | re.MULTILINE,
    )
    if not sect:
        return 0, {}
    body = sect.group(1)
    categories: dict[str, int] = {}
    for cat_match in re.finditer(
        r"^####\s+(\w+)\s*\n(.*?)(?=^####\s+|\Z)",
        body,
        flags=re.DOTALL | re.MULTILINE,
    ):
        cat = cat_match.group(1)
        cat_body = cat_match.group(2)
        # Count top-of-line `- ` bullets. Nested bullets indented by
        # spaces don't match — that's deliberate, sub-bullets are
        # continuation of their parent.
        bullets = re.findall(r"^- ", cat_body, flags=re.MULTILINE)
        if bullets:
            categories[cat] = len(bullets)
    total = sum(categories.values())
    return total, categories


def last_semver_tag(cwd: Path = ROOT) -> str | None:
    """Return the highest-versioned `v*` tag, or None if no tags exist.

    Uses `git tag --sort=-v:refname` so we don't have to parse SemVer
    ourselves. Tag names are returned verbatim ("v1.6.1"); strip the
    leading "v" downstream if you want a bare version string.
    """
    try:
        out = subprocess.check_output(
            ["git", "tag", "--list", "v*", "--sort=-v:refname"],
            cwd=cwd,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    tags = [t.strip() for t in out.splitlines() if t.strip()]
    return tags[0] if tags else None


def compose_stamp(
    total: int,
    categories: dict[str, int],
    last_tag: str | None,
    today: str,
) -> str:
    """Render the machine-managed block. Returns the full text
    including the START/END marker lines so the caller can splice it
    in with a single regex.
    """
    tag_label = last_tag or "(no release tagged yet)"
    if total == 0:
        body = (
            f"> _Auto-tracked: `[Unreleased]` is empty since **{tag_label}**. "
            f"Last refresh by `scripts/sync-roadmap.py`: {today}._"
        )
    else:
        breakdown = ", ".join(
            f"{n} {cat}" for cat, n in categories.items()
        )
        body = (
            f"> _Auto-tracked: **{total} "
            f"{'entries' if total != 1 else 'entry'}** in "
            f"[`[Unreleased]`](../CHANGELOG.md#unreleased) since "
            f"**{tag_label}** ({breakdown}). "
            f"Last refresh by `scripts/sync-roadmap.py`: {today}. "
            f"Prose in the timeline below may lag; the maintainer "
            f"resynthesises on release-time §5 sweep._"
        )
    return f"{AUTOSTAMP_START}\n{body}\n{AUTOSTAMP_END}"


def splice_stamp(roadmap_text: str, new_stamp: str) -> str | None:
    """Replace the existing AUTOSTAMP block with `new_stamp`. Returns
    the rewritten text, or None if no markers were found (in which
    case the caller decides whether to insert or skip)."""
    pattern = re.compile(
        re.escape(AUTOSTAMP_START) + r".*?" + re.escape(AUTOSTAMP_END),
        flags=re.DOTALL,
    )
    if not pattern.search(roadmap_text):
        return None
    # Use a callable replacement so backslash sequences in `new_stamp`
    # (URLs etc.) aren't interpreted as regex backreferences.
    return pattern.sub(lambda _m: new_stamp, roadmap_text, count=1)


def main() -> None:
    if not CHANGELOG.exists():
        print(f"! {CHANGELOG.relative_to(ROOT)} not found, nothing to do.",
              file=sys.stderr)
        return
    if not ROADMAP.exists():
        print(f"! {ROADMAP.relative_to(ROOT)} not found, nothing to do.",
              file=sys.stderr)
        return

    changelog_text = CHANGELOG.read_text(encoding="utf-8")
    roadmap_text = ROADMAP.read_text(encoding="utf-8")

    total, categories = count_unreleased_bullets(changelog_text)
    last_tag = last_semver_tag()
    # Date format: '24 May 2026' (no leading zero on day, UTC-anchored).
    # `%-d` is non-portable to Windows but fine on the Linux runners CI uses.
    today = datetime.now(timezone.utc).strftime("%-d %b %Y")

    new_stamp = compose_stamp(total, categories, last_tag, today)

    updated = splice_stamp(roadmap_text, new_stamp)
    if updated is None:
        print(
            f"! No AUTOSTAMP markers found in {ROADMAP.relative_to(ROOT)}. "
            f"Add the following block manually somewhere near the top of "
            f"the file (typically just under the 'Last revised' line):\n\n"
            f"{new_stamp}\n",
            file=sys.stderr,
        )
        return

    if updated == roadmap_text:
        print(f"No change to autostamp ({total} entries since "
              f"{last_tag or 'no tag'}, last refresh {today}).")
        return

    ROADMAP.write_text(updated, encoding="utf-8")
    print(
        f"Updated autostamp in {ROADMAP.relative_to(ROOT)}: "
        f"{total} entries since {last_tag or 'no tag'} "
        f"({', '.join(f'{n} {c}' for c, n in categories.items()) or 'none'}), "
        f"refresh stamp {today}."
    )


if __name__ == "__main__":
    main()
