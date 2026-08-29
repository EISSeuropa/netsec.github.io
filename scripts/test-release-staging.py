#!/usr/bin/env python3
"""Every file scripts/release.sh writes is staged into the release commit.

The staging list and the steps that write those files sit 250 lines apart, so
they drifted: docs/roadmap-2026.md and data/roadmap-progress.json were
refreshed by the autostamp step and never staged, which left them dirty after
a release and made the next --dry-run fail its own clean-tree check.

Run standalone:  /usr/bin/python3 scripts/test-release-staging.py
Or under pytest: python3 -m pytest scripts/test-release-staging.py -q
"""
from __future__ import annotations

import re
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "release.sh"

# What the script writes, and which step writes it. Add a row here when a new
# step starts writing a tracked file.
WRITES = {
    "CHANGELOG.md": "the [Unreleased] promote step",
    "roadmap.html": "promote-roadmap.py",
    "roadmap.fr.html": "promote-roadmap.py",
    "roadmap.de.html": "promote-roadmap.py",
    "data/i18n-state.json": "promote-roadmap.py",
    "docs/roadmap-2026.md": "sync-roadmap.py",
    "data/roadmap-progress.json": "sync-roadmap-progress.py",
}


def _staged() -> set:
    s = SCRIPT.read_text(encoding="utf-8")
    m = re.search(r"run git add (.+?)\nrun git com" + "mit", s, re.S)
    assert m, "could not find the release commit's staging list"
    return set(m.group(1).replace("\\\n", " ").split())


def test_every_written_file_is_staged():
    staged = _staged()
    missing = sorted(f for f in WRITES if f not in staged)
    assert not missing, (
        "release.sh writes these but never stages them, so they are left dirty "
        f"after a release: {missing}"
    )


def test_nothing_extra_is_staged():
    # A file staged but not in WRITES is either dead or an undocumented write.
    extra = sorted(f for f in _staged() if f not in WRITES)
    assert not extra, f"staged but not recorded in WRITES: {extra}"


def test_dry_run_reverts_the_refresh():
    # The autostamp step writes before the dry-run guard returns, so the guard
    # has to put the files back or the next real run fails its clean-tree check.
    s = SCRIPT.read_text(encoding="utf-8")
    block = re.search(r"if ! git -C \"\$REPO_ROOT\" diff --quiet -- docs/roadmap-2026\.md.*?\nfi\n", s, re.S)
    assert block, "could not find the post-refresh guard"
    b = block.group(0)
    assert "--dry-run" in b, "the guard does not distinguish a dry run"
    assert "checkout --" in b, "a dry run leaves the refreshed files dirty"


if __name__ == "__main__":
    fails = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  ok  {name}")
            except AssertionError as e:
                fails.append(name)
                print(f"FAIL  {name}: {e}")
    print(f"\n{4 - len(fails) - 1}/3 passed." if fails else "\n3/3 passed.")
    raise SystemExit(1 if fails else 0)
