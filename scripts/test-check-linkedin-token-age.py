"""scripts/check-linkedin-token-age.py: the refresh-token expiry reminder (#2130)."""

import datetime as dt
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "check-linkedin-token-age.py"
spec = importlib.util.spec_from_file_location("token_age", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

D = dt.date.fromisoformat


def test_unknown_when_unset_or_malformed():
    assert mod.assess(None, D("2026-11-15")) == ("unknown", "")
    assert mod.assess("", D("2026-11-15")) == ("unknown", "")
    assert mod.assess("August 2026", D("2026-11-15")) == ("unknown", "")


def test_ok_well_before_expiry():
    assert mod.assess("2026-08-25", D("2026-11-15")) == ("ok", "2027-08-25")


def test_due_inside_the_reminder_window():
    # 61 days before expiry is the first day it fires.
    assert mod.assess("2026-08-25", D("2027-06-25"))[0] == "due"
    assert mod.assess("2026-08-25", D("2027-06-24"))[0] == "ok"


def test_monthly_run_always_gives_thirty_days():
    """Whatever day of the month the token expires, the run on the 5th of
    some month falls inside the window with at least 30 days left."""
    issued = D("2026-01-01")
    for offset in range(366):
        start = issued + dt.timedelta(days=offset)
        expires = start + dt.timedelta(days=365)
        runs = [dt.date(y, m, 5) for y in (start.year, start.year + 1, start.year + 2) for m in range(1, 13)]
        first = next(r for r in runs if r > start and mod.assess(start.isoformat(), r)[0] != "ok")
        assert (expires - first).days >= 30, (start, first)


def test_expired():
    assert mod.assess("2025-01-01", D("2026-11-15")) == ("expired", "2026-01-01")


def test_cli_writes_github_output():
    with tempfile.TemporaryDirectory() as td:
        pin = Path(td) / "pin.json"
        pin.write_text(json.dumps({"version": "202607", "refresh_token_issued": "2026-08-25"}))
        out = Path(td) / "out"
        subprocess.run(
            [sys.executable, str(SCRIPT), "--file", str(pin), "--today", "2027-07-01"],
            check=True, capture_output=True, env={**os.environ, "GITHUB_OUTPUT": str(out)},
        )
        assert out.read_text() == "state=due\nexpires=2027-08-25\n"
