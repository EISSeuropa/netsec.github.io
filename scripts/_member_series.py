#!/usr/bin/env python3
"""Directory size over time, read from the git history of data/bios.json.

Shared helper. `scripts/build-year-review.py` puts the series in the
Year in Review edition; the Network Map statistics strip (#764) reads
the same function, so the two surfaces cannot disagree about how many
members the Directory held in a given month.

One point per calendar month: the member count as of the last commit
that touched data/bios.json in that month. Monthly is the resolution a
sparkline can actually show, and it keeps the walk to a handful of
`git show` calls rather than one per commit.

Workflow trap: a walk of the file's history needs the full clone. The
default `actions/checkout` depth of 1 returns a single commit, so any
workflow calling this needs `fetch-depth: 0`. With a shallow clone the
series degrades to one point rather than failing, and `shallow()` says
so.

Usage as a module:
    from _member_series import monthly_member_counts
    points = monthly_member_counts(REPO)

Run directly to print the series as JSON:
    python3 scripts/_member_series.py
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

BIOS = "data/bios.json"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def shallow(repo: Path) -> bool:
    """True if the clone is shallow, which truncates the series."""
    return (repo / ".git" / "shallow").exists()


def _commits(repo: Path) -> list[tuple[str, str]]:
    """(sha, committer date) touching bios.json, newest first."""
    out = _git(repo, "log", "--format=%H %cs", "--", BIOS)
    rows = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2:
            rows.append((parts[0], parts[1]))
    return rows


def members_at(repo: Path, sha: str) -> int | None:
    """Member count in bios.json at `sha`, or None if unreadable there.

    Early history predates the file and a mid-history commit can hold a
    shape the current parser does not recognise, so an unreadable blob
    drops the point instead of ending the walk.
    """
    try:
        blob = _git(repo, "show", f"{sha}:{BIOS}")
        data = json.loads(blob)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return None
    members = data.get("members")
    return len(members) if isinstance(members, list) else None


def monthly_member_counts(
    repo: Path, until: str | None = None
) -> list[dict]:
    """One point per calendar month, oldest first.

    `until` is an inclusive ISO date ceiling (YYYY-MM-DD); commits after
    it are ignored, which is how an Action-year window gets a series that
    stops at the end of the year rather than at today.

    Each point: {"month": "2026-05", "date": "2026-05-30", "members": 14}
    """
    last_of_month: dict[str, tuple[str, str]] = {}
    # The log is newest-first, so the first commit seen in a month is
    # that month's last one.
    for sha, date in _commits(repo):
        if until and date > until:
            continue
        last_of_month.setdefault(date[:7], (sha, date))

    points = []
    for month in sorted(last_of_month):
        sha, date = last_of_month[month]
        count = members_at(repo, sha)
        if count is None:
            continue
        points.append({"month": month, "date": date, "members": count})
    return points


if __name__ == "__main__":
    repo = Path(__file__).resolve().parent.parent
    series = monthly_member_counts(repo)
    if shallow(repo):
        print("⚠ shallow clone: the series is truncated to what is here.")
    print(json.dumps(series, indent=2))
