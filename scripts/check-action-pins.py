#!/usr/bin/env python3
"""Check that every SHA-pinned action names the version of its SHA (#2260).

Each `uses:` line in .github/workflows/*.yml pins an action to a commit SHA
with a trailing `# vN (sha-pinned)` comment (.github/CLAUDE.md). Dependabot
bumps the SHA and leaves the comment as it was, so the comment drifts one
major behind with every major bump. This script resolves each SHA against
the action repository's tags and compares the major version of those tags
with the comment.

Usage:
    python3 scripts/check-action-pins.py          # exit 1 on any mismatch
    python3 scripts/check-action-pins.py --warn   # report, exit 0
    python3 scripts/check-action-pins.py --fix    # rewrite the comments

The check runs on every PR (action-pins-check.yml), as a warning on
Dependabot's. The daily roadmap-refresh workflow runs --fix and opens a PR
on `action-pins/auto` when a comment has drifted.

Lines that are not resolvable fail in every mode, --fix included: a
third-party `uses:` not pinned to a 40-character SHA, and a SHA that no tag
of the action points at. Local reusable workflows (`uses: ./...`) are
skipped. Tags are read with `git ls-remote --tags`, one call per action
repository, with no GitHub API token.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"

USES = re.compile(r"^(?P<lead>\s*(?:-\s*)?uses:\s*)(?P<ref>\S+)(?P<rest>.*)$")
PINNED = re.compile(r"^(?P<repo>[\w.-]+/[\w.-]+)(?P<path>/[^@\s]*)?@(?P<sha>[0-9a-f]{40})$")
COMMENT = re.compile(r"^\s*#\s*(?P<version>v?\d+(?:\.\d+)*)\s*\(sha-pinned\)\s*$")
VERSION_TAG = re.compile(r"^v?(\d+)(?:\.\d+)*$")


def list_tags(repo: str) -> list[tuple[str, str]]:
    """(sha, tag) pairs for every tag of github.com/<repo>.

    An annotated tag is listed twice by ls-remote, once for the tag object
    and once, with a `^{}` suffix, for the commit it points at. Both are
    kept with the suffix removed, so a SHA matches either form."""
    out = subprocess.run(
        ["git", "ls-remote", "--tags", f"https://github.com/{repo}"],
        check=True, capture_output=True, text=True,
    ).stdout
    pairs = []
    for line in out.splitlines():
        sha, _, ref = line.partition("\t")
        tag = ref.removeprefix("refs/tags/").removesuffix("^{}")
        pairs.append((sha, tag))
    return pairs


def major_for(sha: str, tags: list[tuple[str, str]]) -> int | None:
    """Highest major among the version tags that point at `sha`."""
    majors = [int(m.group(1)) for s, t in tags if s == sha and (m := VERSION_TAG.match(t))]
    return max(majors) if majors else None


def scan(paths, resolve=list_tags):
    """One record per `uses:` line that names a remote action.

    Each record is (path, line number, line, problem, expected comment),
    with problem None when the comment already matches."""
    cache: dict[str, list[tuple[str, str]]] = {}
    records = []
    for path in paths:
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            m = USES.match(line)
            if not m or m.group("ref").startswith("./"):
                continue
            pin = PINNED.match(m.group("ref"))
            if not pin:
                records.append((path, n, line, "not pinned to a 40-character SHA", None))
                continue
            repo = pin.group("repo")
            if repo not in cache:
                cache[repo] = resolve(repo)
            major = major_for(pin.group("sha"), cache[repo])
            if major is None:
                records.append((path, n, line, f"no version tag of {repo} points at this SHA", None))
                continue
            expected = f"# v{major} (sha-pinned)"
            c = COMMENT.match(m.group("rest"))
            if not c:
                records.append((path, n, line, f"has no `{expected}` comment", expected))
            elif c.group("version").lstrip("v") != str(major):
                records.append((path, n, line, f"comment says {c.group('version')}, the SHA is v{major}", expected))
            else:
                records.append((path, n, line, None, expected))
    return records


def fixed_line(line: str, expected: str) -> str:
    m = USES.match(line)
    return f"{m.group('lead')}{m.group('ref')}  {expected}"


def main(argv=None, resolve=list_tags, workflows=WORKFLOWS) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--warn", action="store_true", help="report mismatches and exit 0")
    mode.add_argument("--fix", action="store_true", help="rewrite drifted comments in place")
    args = ap.parse_args(argv)

    paths = sorted(workflows.glob("*.yml")) + sorted(workflows.glob("*.yaml"))
    records = scan(paths, resolve)
    problems = [r for r in records if r[3]]
    fixable = [r for r in problems if r[4]]
    unfixable = [r for r in problems if not r[4]]

    if args.fix:
        by_path: dict[Path, dict[int, str]] = {}
        for path, n, line, _, expected in fixable:
            by_path.setdefault(path, {})[n] = fixed_line(line, expected)
        for path, edits in by_path.items():
            text = path.read_text(encoding="utf-8")
            lines = text.splitlines()
            for n, new in edits.items():
                lines[n - 1] = new
            path.write_text("\n".join(lines) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")
        for path, n, _, problem, expected in fixable:
            print(f"fixed {path.relative_to(ROOT)}:{n}: {problem} -> {expected}")

    level = "warning" if args.warn else "error"
    shown = unfixable if args.fix else problems
    for path, n, _, problem, _ in shown:
        print(f"::{level} file={path.relative_to(ROOT)},line={n}::{problem}")

    print(f"check-action-pins: {len(records)} pinned actions checked. "
          f"Drifted comments{' fixed' if args.fix else ''}: {len(fixable)}. "
          f"Unresolvable: {len(unfixable)}.")
    if unfixable or (problems and not args.warn and not args.fix):
        if not args.fix and fixable:
            print("Run `python3 scripts/check-action-pins.py --fix` to rewrite the comments.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
