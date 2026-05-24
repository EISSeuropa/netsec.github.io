#!/usr/bin/env python3
"""
Smoke tests for scripts/sync-roadmap.py.

Mirrors the in-process pattern of scripts/test-sync-bios.py: no
pytest tree, just a runnable that exercises the pure parsing /
rendering / splicing functions on in-memory fixtures.

Usage:
    python3 scripts/test-sync-roadmap.py

Exits non-zero on first failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sync_roadmap = __import__("sync-roadmap")
count_unreleased_bullets = sync_roadmap.count_unreleased_bullets
compose_stamp = sync_roadmap.compose_stamp
splice_stamp = sync_roadmap.splice_stamp
AUTOSTAMP_START = sync_roadmap.AUTOSTAMP_START
AUTOSTAMP_END = sync_roadmap.AUTOSTAMP_END


def expect(label: str, got, want) -> None:
    if got != want:
        print(f"FAIL: {label}\n  got:  {got!r}\n  want: {want!r}", file=sys.stderr)
        sys.exit(1)
    print(f"  ok  {label}")


def test_count_unreleased_bullets() -> None:
    print("\ncount_unreleased_bullets():")

    # Empty changelog: no [Unreleased], no totals.
    expect("empty changelog → (0, {})",
           count_unreleased_bullets(""), (0, {}))

    # [Unreleased] present but no categories yet.
    text = (
        "## [Unreleased]\n\n"
        "(content will go here)\n\n"
        "## [1.0.0] · 2026-01-01 — *first*\n"
        "..."
    )
    expect("[Unreleased] with no #### subsections → (0, {})",
           count_unreleased_bullets(text), (0, {}))

    # Three Added + two Changed under [Unreleased]. A bare hyphen at
    # the start of a continuation paragraph (not at column 0) must
    # not be counted. A sub-bullet (indented) must not be counted.
    text = (
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "### Index of changes\n\n"
        "#### Added\n\n"
        "- **Feature A** lorem ipsum.\n"
        "- **Feature B** dolor sit amet.\n"
        "- **Feature C** consectetur.\n"
        "  - sub-bullet that must not be counted\n"
        "\n"
        "#### Changed\n\n"
        "- **Tweak A** quia dolor sit.\n"
        "- **Tweak B** ut enim.\n"
        "\n"
        "## [1.5.0] · 2026-05-01 — *previous*\n\n"
        "#### Added\n\n"
        "- **Old thing** (must not be counted, this is the previous "
        "release section).\n"
    )
    total, cats = count_unreleased_bullets(text)
    expect("category totals", cats, {"Added": 3, "Changed": 2})
    expect("grand total", total, 5)

    # Mixed categories including a Fixed.
    text = (
        "## [Unreleased]\n\n"
        "#### Added\n- a\n- b\n\n"
        "#### Changed\n- c\n\n"
        "#### Fixed\n- d\n- e\n- f\n\n"
        "## [9.9.9] · prev\n"
    )
    total, cats = count_unreleased_bullets(text)
    expect("all three categories detected",
           cats, {"Added": 2, "Changed": 1, "Fixed": 3})
    expect("grand total 6", total, 6)


def test_compose_stamp() -> None:
    print("\ncompose_stamp():")

    # Empty case: tagged but nothing in [Unreleased] yet.
    stamp = compose_stamp(0, {}, "v1.6.1", "25 May 2026")
    expect("empty case mentions 'is empty since'",
           "is empty since" in stamp and "v1.6.1" in stamp, True)
    expect("empty case wraps markers",
           stamp.startswith(AUTOSTAMP_START)
           and stamp.endswith(AUTOSTAMP_END),
           True)

    # Non-empty case: counts + categories + tag + date all present.
    stamp = compose_stamp(7, {"Added": 3, "Changed": 4},
                          "v1.6.1", "24 May 2026")
    expect("non-empty case has the right counts",
           "7 entries" in stamp
           and "3 Added" in stamp
           and "4 Changed" in stamp,
           True)
    expect("non-empty case mentions the tag",
           "v1.6.1" in stamp, True)
    expect("non-empty case has the date",
           "24 May 2026" in stamp, True)
    expect("non-empty case mentions the script path so future readers "
           "know where the stamp came from",
           "scripts/sync-roadmap.py" in stamp, True)

    # Single-entry case: grammar must be "1 entry" not "1 entries".
    stamp = compose_stamp(1, {"Added": 1}, "v1.6.1", "24 May 2026")
    expect("singular grammar",
           "1 entry" in stamp and "1 entries" not in stamp, True)

    # No tag case: degrades gracefully.
    stamp = compose_stamp(3, {"Added": 3}, None, "24 May 2026")
    expect("no-tag case has a clear placeholder",
           "no release tagged yet" in stamp, True)


def test_splice_stamp() -> None:
    print("\nsplice_stamp():")

    new_stamp = (
        f"{AUTOSTAMP_START}\n"
        "> _Auto-tracked: NEW stamp content._\n"
        f"{AUTOSTAMP_END}"
    )

    # Document with an existing stamp: must be replaced cleanly,
    # surrounding prose preserved.
    doc = (
        "# Heading\n\n"
        "Maintainer prose paragraph.\n\n"
        f"{AUTOSTAMP_START}\n"
        "> _Auto-tracked: OLD stamp content._\n"
        f"{AUTOSTAMP_END}\n\n"
        "## Next section\n"
        "More prose.\n"
    )
    out = splice_stamp(doc, new_stamp)
    assert out is not None, "splice returned None despite markers present"
    expect("replaced once → OLD content gone",
           "OLD stamp content" in out, False)
    expect("replaced once → NEW content present",
           "NEW stamp content" in out, True)
    expect("surrounding prose preserved (heading)",
           "# Heading" in out, True)
    expect("surrounding prose preserved (section after stamp)",
           "## Next section" in out, True)

    # Document without markers: splice must signal that by returning
    # None, leaving the caller to decide insertion / skip.
    doc_no_markers = "# Heading\n\nNo markers in this file at all.\n"
    expect("no-markers → returns None",
           splice_stamp(doc_no_markers, new_stamp), None)

    # Document with markers but special regex characters in the new
    # stamp (e.g. `\1` would be a backreference under naive re.sub).
    # The callable-replacement path in splice_stamp protects against
    # this.
    tricky_stamp = (
        f"{AUTOSTAMP_START}\n"
        "> _Tricky: \\1 reference, [link](https://example.com) etc._\n"
        f"{AUTOSTAMP_END}"
    )
    doc2 = (
        "before\n"
        f"{AUTOSTAMP_START}\nold\n{AUTOSTAMP_END}\n"
        "after\n"
    )
    out = splice_stamp(doc2, tricky_stamp)
    assert out is not None
    expect("tricky replacement preserves the literal backslash",
           "\\1 reference" in out, True)
    expect("tricky replacement preserves the link",
           "[link](https://example.com)" in out, True)


def main() -> None:
    test_count_unreleased_bullets()
    test_compose_stamp()
    test_splice_stamp()
    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
