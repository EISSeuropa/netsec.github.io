#!/usr/bin/env python3
"""Summarise what a data-sync auto-PR actually changes, in one line.

Why this exists
---------------

The bios-sync workflow composes its PR body immediately after running
`sync-bios.py`, which is *before* the eight generator steps that rebuild
profile pages, OG cards, search stubs, the sitemap, the directory index,
the atlas, and the glossary field guide. So the run log in the body could
only ever describe the upstream fetch, never the derived files that
actually landed in the diff.

That produced PRs like #1421, whose log said "No substantive changes"
(true of `data/bios.json`) while the diff carried a real correction: one
member's Working Group facet arriving in her three search stubs, four
days after `sync-cost.py` had written the WG membership without
rebuilding the stubs. The maintainer had to read the diff to discover
the PR was not a no-op.

This reads the working tree after every generator has run and prints a
one-line summary the maintainer can act on without opening the diff.

Usage
-----

    python3 scripts/summarise-sync-changes.py            # runs git itself
    git status --porcelain | python3 scripts/summarise-sync-changes.py -

Prints nothing when the tree is clean, so the caller can prepend
unconditionally.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Ordered longest-prefix-first: the first matching rule wins, so
# `data/bios.json` is claimed as upstream before the generic `data/` rules
# get a look in. Adding a generator to the workflow means adding its output
# path here, otherwise its files fall into "other" rather than going unseen.
UPSTREAM = "data/bios.json"

# The third field says whether the bucket holds one file per member. Only
# those are worth naming individually; a sitemap is a sitemap, and printing
# "sitemap (sitemap.xml)" is noise.
BUCKETS: list[tuple[str, str, bool]] = [
    ("search/bios/", "search stubs", True),
    ("assets/og/people/", "OG cards", True),
    ("assets/og/flags/", "flag assets", True),
    ("assets/images/people/", "headshots", True),
    ("people/", "profile pages", True),
    ("data/orcid-works.json", "ORCID publications", False),
    ("data/atlas.json", "Atlas graph", False),
    ("data/cost-wg-state.json", "WG state", False),
    ("data/wg.json", "WG rosters", False),
    ("directory-index.json", "directory index", False),
    ("sitemap.xml", "sitemap", False),
    ("glossary", "glossary field guide", False),
]

PER_MEMBER = {label for _, label, per_member in BUCKETS if per_member}

MAX_SLUGS = 4


def bucket_for(path: str) -> str:
    for prefix, label, _ in BUCKETS:
        if path.startswith(prefix):
            return label
    return "other"


def slug_for(path: str) -> str:
    """Best-effort member slug from a generated path.

    people/gayane-harutyunyan.fr.html  -> gayane-harutyunyan
    search/bios/de/gayane-harutyunyan.html -> gayane-harutyunyan
    """
    name = Path(path).name
    for suffix in (".html", ".png", ".webp", ".jpg", ".svg", ".json"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    for locale in (".fr", ".de", ".en"):
        if name.endswith(locale):
            name = name[: -len(locale)]
            break
    return name


def parse_porcelain(text: str) -> list[str]:
    """Paths out of `git status --porcelain`, handling renames."""
    paths = []
    for line in text.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip() if len(line) > 3 else line.strip()
        # `R  old -> new`: the new path is what landed.
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path.strip().strip('"'))
    return paths


def summarise(paths: list[str]) -> str:
    if not paths:
        return ""

    upstream_changed = UPSTREAM in paths
    derived = [p for p in paths if p != UPSTREAM]

    lede = (
        "member data changed upstream"
        if upstream_changed
        else "no member edits upstream"
    )

    if not derived:
        return f"**Summary: {lede}, no derived files rebuilt.**"

    grouped: dict[str, list[str]] = {}
    for path in derived:
        grouped.setdefault(bucket_for(path), []).append(path)

    parts = []
    for label, group in sorted(grouped.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        if label not in PER_MEMBER:
            parts.append(label if len(group) == 1 else f"{label} ({len(group)} files)")
            continue
        slugs = sorted({slug_for(p) for p in group})
        # Naming the members is the whole point when only a few are touched:
        # it turns "3 files changed" into "which person changed".
        if len(slugs) <= MAX_SLUGS:
            parts.append(f"{label} ({', '.join(slugs)})")
        else:
            parts.append(f"{label} ({len(group)} files, {len(slugs)} members)")

    noun = "file" if len(derived) == 1 else "files"
    return (
        f"**Summary: {lede}. {len(derived)} derived {noun} rebuilt "
        f"— {'; '.join(parts)}.**"
    )


def main(argv: list[str]) -> int:
    if len(argv) > 1 and argv[1] == "-":
        text = sys.stdin.read()
    else:
        text = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    line = summarise(parse_porcelain(text))
    if line:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
