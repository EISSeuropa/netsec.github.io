#!/usr/bin/env python3
"""Staleness check for the accessibility statement's review date.

The statement at /accessibility.html commits to a "next scheduled
review <date>" in its version footer (rule: bumped on every release
that touches conformance, full review yearly). Every comparable
freshness promise on this site has a CI check; this one closes the
gap for the statement itself.

Behaviour:
  * exit 0  — next scheduled review is more than WARN_DAYS away
  * exit 0  — within WARN_DAYS, but prints a ⚠ heads-up
  * exit 1  — the review date has passed, or the marker is missing
              (someone reworded the footer and broke the contract)

Runs from the weekly launch-qa-link-check workflow, so an overdue
review surfaces as a red weekly run rather than going unnoticed.

Usage: python3 scripts/check-a11y-statement-date.py
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAGE = REPO / "accessibility.html"
WARN_DAYS = 60

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}

MARKER_RE = re.compile(
    r"next scheduled review\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})",
    re.IGNORECASE,
)


def next_review_date(text: str):
    m = MARKER_RE.search(text)
    if not m:
        return None
    day, month_name, year = m.groups()
    month = MONTHS.get(month_name.lower())
    if not month:
        return None
    return date(int(year), month, int(day))


def main() -> int:
    if not PAGE.exists():
        print("✗ accessibility.html not found")
        return 1
    due = next_review_date(PAGE.read_text(encoding="utf-8"))
    if due is None:
        print("✗ accessibility.html: no parseable 'next scheduled review "
              "<D Month YYYY>' marker in the version footer. Restore the "
              "marker or update this check to match the new wording.")
        return 1
    today = date.today()
    days = (due - today).days
    if days < 0:
        print(f"✗ accessibility statement review is {-days} day(s) overdue "
              f"(was scheduled for {due:%-d %B %Y}). Re-assess, bump the "
              f"statement version, and set a new review date.")
        return 1
    if days <= WARN_DAYS:
        print(f"⚠ accessibility statement review due in {days} day(s) "
              f"({due:%-d %B %Y}). Plan the re-assessment.")
        return 0
    print(f"✓ accessibility statement review scheduled {due:%-d %B %Y} "
          f"({days} days away).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
