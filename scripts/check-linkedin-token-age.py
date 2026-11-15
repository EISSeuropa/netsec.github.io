#!/usr/bin/env python3
"""Warn before the LinkedIn refresh token expires (#2130).

A LinkedIn refresh token lasts 365 days from the full authorisation that
issued it. Refreshing the access token does not extend it. Once it lapses,
the pipeline cannot renew the access token on its own, and LinkedIn posts
stop until someone runs the full re-authorisation in docs/admin-guide.md.

The issue date is kept by hand in data/linkedin-api-version.json as
`refresh_token_issued` (YYYY-MM-DD). Update it whenever
`linkedin-token.py exchange` issues a new refresh token.

linkedin-version-check.yml runs this monthly. The reminder threshold is
61 days, so a monthly run always fires at least 30 days before expiry.

Writes `state` (ok, due, expired or unknown) and `expires` to
$GITHUB_OUTPUT when that variable is set. Always exits 0.

Stdlib only; runs under /usr/bin/python3.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIN_FILE = ROOT / "data" / "linkedin-api-version.json"
LIFETIME_DAYS = 365
REMIND_DAYS = 61


def assess(issued: str | None, today: dt.date) -> tuple[str, str]:
    """(state, expiry date as ISO string or "")."""
    if not issued:
        return "unknown", ""
    try:
        start = dt.date.fromisoformat(str(issued))
    except ValueError:
        return "unknown", ""
    expires = start + dt.timedelta(days=LIFETIME_DAYS)
    left = (expires - today).days
    if left < 0:
        return "expired", expires.isoformat()
    if left <= REMIND_DAYS:
        return "due", expires.isoformat()
    return "ok", expires.isoformat()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--today", help="override today's date (YYYY-MM-DD), for tests")
    ap.add_argument("--file", type=Path, default=PIN_FILE)
    args = ap.parse_args()

    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    data = json.loads(args.file.read_text(encoding="utf-8"))
    state, expires = assess(data.get("refresh_token_issued"), today)

    if state == "unknown":
        print("::warning::refresh_token_issued is not set in "
              "data/linkedin-api-version.json, so the LinkedIn refresh token's "
              "expiry cannot be checked.")
    else:
        left = (dt.date.fromisoformat(expires) - today).days
        print(f"LinkedIn refresh token expires {expires} ({left} days). State: {state}.")

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"state={state}\nexpires={expires}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
