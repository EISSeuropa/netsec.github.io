#!/usr/bin/env python3
"""Keep the LinkedIn API version pin current.

LinkedIn versions its Marketing API monthly (YYYYMM) and supports each
version for ~12 months before sunsetting it. A sunset version returns
HTTP 426 and every post fails silently until someone bumps the pin. That
is exactly how the weekly member spotlight stopped reaching LinkedIn: the
pin sat at 202506 for 13 months (#1223) and nobody noticed until a post
went missing.

This reads LinkedIn's published active-version list and, when our pin
(data/linkedin-api-version.json) has fallen to the trailing edge of that
window, rewrites it to the latest version. The linkedin-version-check
workflow runs this monthly with --write and ships any change as an
auto-merging PR, so the bump stays visible in git rather than happening
behind the maintainer's back.

Modes:
    (no flag)   report the pin, the active window, and whether a bump is due
    --write     rewrite the pin file when a bump is due; no-op otherwise
    --check     exit 1 if a bump is due (for optional CI gating); never writes

A fetch or parse failure is non-fatal: the script reports it and exits 0
without writing, so a flaky doc page never breaks CI. The real backstop is
the ::warning:: social-post.py now emits when a live post is rejected.

Stdlib only; runs under /usr/bin/python3.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIN_FILE = ROOT / "data" / "linkedin-api-version.json"

# LinkedIn's own versioning page lists every active version as a
# `li-lms-YYYY-MM` moniker. Parsing those monikers out of the rendered HTML
# is sturdier than scraping the "Latest Version" table, and needs no auth.
LEARN_URL = "https://learn.microsoft.com/en-us/linkedin/marketing/versioning"
MONIKER_RE = re.compile(r"li-lms-(\d{4})-(\d{2})")

# How close to the oldest still-supported version the pin may drift before we
# bump. 2 means "bump once the pin is one of the two oldest active versions",
# which under LinkedIn's monthly cadence leaves a comfortable lead time before
# the actual sunset.
SUNSET_BUFFER = 2

# LinkedIn supports each version for a minimum of 12 months. The versioning
# page also names historical versions in prose (the "first release was June
# 2022" line leaves stray 202206/202207 monikers in the HTML), so keep only
# monikers within this many months of the newest one. 13 clears the 2022
# strays with headroom while retaining every genuinely-active version.
ACTIVE_WINDOW_MONTHS = 13


def _ordinal(yyyymm: str) -> int:
    return int(yyyymm[:4]) * 12 + int(yyyymm[4:])


def parse_versions(html: str) -> set[str]:
    """Every li-lms-YYYY-MM moniker in the page, active or historical."""
    return {f"{y}{m}" for y, m in MONIKER_RE.findall(html)}


def active_window(versions: set[str], months: int = ACTIVE_WINDOW_MONTHS) -> set[str]:
    """Drop strays older than `months` behind the newest moniker, so a
    historical version quoted in prose can't masquerade as active."""
    if not versions:
        return set()
    newest = max(_ordinal(v) for v in versions)
    return {v for v in versions if newest - _ordinal(v) <= months}


def fetch_active_versions(url: str = LEARN_URL) -> set[str]:
    """Return the set of active LinkedIn API versions as YYYYMM strings.

    Raises on a network error or an unparseable page; the caller decides
    whether that is fatal (it is not, for the workflow)."""
    req = urllib.request.Request(url, headers={"User-Agent": "netsec-version-check/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8", "replace")
    versions = active_window(parse_versions(body))
    if not versions:
        raise ValueError(f"no li-lms-YYYY-MM monikers found at {url}")
    return versions


def decide_target(pin: str, active: set[str], buffer: int = SUNSET_BUFFER) -> str | None:
    """The version to bump to, or None when the pin is comfortably current.

    Bumps to the latest active version when the pin has sunset (no longer in
    the active set) or has drifted into the oldest `buffer` still-supported
    versions. Position in the sorted list, not calendar arithmetic, so a
    skipped month in LinkedIn's line (e.g. 202512) can never mislead it."""
    if not active:
        return None
    ordered = sorted(active)
    latest = ordered[-1]
    if pin == latest:
        return None
    if pin not in ordered:
        return latest
    if ordered.index(pin) < buffer:
        return latest
    return None


def read_pin(path: Path = PIN_FILE) -> str:
    return str(json.loads(path.read_text(encoding="utf-8"))["version"]).strip()


def write_pin(version: str, path: Path = PIN_FILE) -> None:
    """Rewrite only the `version` field, preserving the `_comment`."""
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = version
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Keep the LinkedIn API version pin current.")
    ap.add_argument("--write", action="store_true", help="bump the pin file when a bump is due")
    ap.add_argument("--check", action="store_true", help="exit 1 if a bump is due; never write")
    args = ap.parse_args(argv)

    pin = read_pin()
    try:
        active = fetch_active_versions()
    except Exception as e:  # network / parse — non-fatal, never blocks CI
        print(f"! could not read LinkedIn's active versions ({e}); leaving pin at {pin}")
        return 0

    target = decide_target(pin, active)
    window = f"{min(active)}–{max(active)}"
    print(f"pin={pin}  active={window} ({len(active)} versions)  latest={max(active)}")

    if not target:
        print(f"✓ pin {pin} is current; no bump due")
        return 0

    reason = "sunset" if pin not in active else "nearing sunset"
    print(f"→ bump due: {pin} → {target} ({reason})")
    if args.check:
        return 1
    if args.write:
        write_pin(target)
        print(f"✓ wrote {PIN_FILE.relative_to(ROOT)}: version {pin} → {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
