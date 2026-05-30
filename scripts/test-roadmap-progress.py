#!/usr/bin/env python3
"""Smoke tests for scripts/sync-roadmap-progress.py's pure build().

Run: python3 scripts/test-roadmap-progress.py
No network: build() takes a milestone list, so we feed it fixtures.
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "sync_roadmap_progress",
    Path(__file__).resolve().parent / "sync-roadmap-progress.py",
)
srp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(srp)

FAILED = []


def expect(label, got, want):
    ok = got == want
    print(f"  {'ok ' if ok else 'FAIL'} {label}")
    if not ok:
        print(f"       got:  {got!r}\n       want: {want!r}")
        FAILED.append(label)


def test_build():
    print("\nbuild() — shapes milestones into roadmap-progress payload:")
    milestones = [
        {"title": "v1.11.0", "closed_issues": 2, "open_issues": 5,
         "state": "open", "due_on": "2026-07-06T00:00:00Z"},
        {"title": "v1.10.0", "closed_issues": 17, "open_issues": 0,
         "state": "open", "due_on": "2026-06-05T00:00:00Z"},
        {"title": "v1.6.1", "closed_issues": 0, "open_issues": 0,
         "state": "closed", "due_on": "2026-06-08T00:00:00Z"},
        # non-version milestones must be skipped
        {"title": "Backlog — Under watch", "closed_issues": 0,
         "open_issues": 9, "state": "open", "due_on": None},
        {"title": "Translations (FR+GE) in Beta", "closed_issues": 8,
         "open_issues": 0, "state": "closed", "due_on": None},
    ]
    payload = srp.build(milestones, "2026-05-30")
    ms = payload["milestones"]

    expect("only version milestones kept", set(ms.keys()),
           {"v1.6.1", "v1.10.0", "v1.11.0"})
    expect("output sorted by version (v1.6.1 first)", list(ms.keys()),
           ["v1.6.1", "v1.10.0", "v1.11.0"])
    expect("percent = closed/(open+closed), rounded", ms["v1.11.0"]["percent"], 29)
    expect("total = open + closed", ms["v1.11.0"]["total"], 7)
    expect("all-closed milestone is 100%", ms["v1.10.0"]["percent"], 100)
    expect("zero-issue milestone has null percent", ms["v1.6.1"]["percent"], None)
    expect("zero-issue milestone has zero total", ms["v1.6.1"]["total"], 0)
    expect("due trimmed to date", ms["v1.11.0"]["due"], "2026-07-06")
    expect("generatedAt carried through", payload["generatedAt"], "2026-05-30")


def main():
    test_build()
    print()
    if FAILED:
        print(f"FAILED: {len(FAILED)} check(s): {', '.join(FAILED)}")
        raise SystemExit(1)
    print("All smoke tests passed.")


if __name__ == "__main__":
    main()
