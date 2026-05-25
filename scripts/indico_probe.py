#!/usr/bin/env python3
"""
Minimal one-shot probe to test whether promoting the bot account
to admin unblocks /event/<id>/manage/* writes for Personal Access
Token auth. See #210 Phase 1.5 for the back-story.

Runs four targeted requests — the same four that failed with 403
in the previous probe runs (PR #213's workflow output). Reports
status + key response headers. Strictly read-only.

Delete after this run; tracked in #210.
"""

from __future__ import annotations
import os
import sys
import requests

INDICO_BASE = "https://indico.eiss-europa.com"
EVENT_ID = 22
SESSION_ID = 117          # TRANS — Military Transformation
CONTRIB_ID = 362          # Baram — Resilience-by-Design

TOKEN = os.environ.get("INDICO_WRITE_TOKEN") or os.environ.get("INDICO_API_TOKEN")
if not TOKEN:
    sys.exit("Set INDICO_WRITE_TOKEN in env.")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json",
}


def probe(label: str, method: str, path: str) -> None:
    url = INDICO_BASE + path
    print(f"\n──── {label} ────")
    print(f"  {method} {url}")
    try:
        r = requests.request(method, url, headers=HEADERS, timeout=30)
    except requests.RequestException as e:
        print(f"  ERROR: {type(e).__name__}: {e}")
        return
    print(f"  Status: {r.status_code} {r.reason}")
    print(f"  Content-Type: {r.headers.get('Content-Type', '(none)')}")
    # Headers worth knowing for the auth-mechanism question:
    for h in ("Vary", "WWW-Authenticate", "Allow"):
        if h in r.headers:
            print(f"  {h}: {r.headers[h]}")
    if "Set-Cookie" in r.headers:
        print(f"  Set-Cookie: <redacted, length {len(r.headers['Set-Cookie'])}>")
    # If JSON, dump top-level keys; if HTML, just say so.
    ct = r.headers.get("Content-Type", "")
    if "application/json" in ct and r.content:
        try:
            body = r.json()
            if isinstance(body, dict):
                print(f"  JSON keys: {sorted(body.keys())}")
                if "admin" in body:
                    print(f"    admin: {body['admin']!r}")
            elif isinstance(body, list):
                print(f"  JSON array, {len(body)} items")
        except Exception:
            print(f"  (Content-Type JSON but body didn't parse)")
    else:
        print(f"  Body: {len(r.content)} bytes of {ct.split(';')[0] or 'unknown'}")


def main() -> int:
    print("Indico bot-admin re-test — #210 Phase 1.5")
    print("Confirming whether admin status unblocks Bearer auth on /manage/* routes.")
    print("Token: present.")

    probe("0. Whoami — does the bot now report admin=true?",
          "GET", "/api/user/")

    probe("1. Session modify (TRANS / 117)",
          "GET", f"/event/{EVENT_ID}/manage/sessions/{SESSION_ID}/modify")

    probe("2. Contribution edit (Baram / 362)",
          "GET", f"/event/{EVENT_ID}/manage/contributions/{CONTRIB_ID}/edit")

    probe("3. Event persons (manage namespace)",
          "GET", f"/event/{EVENT_ID}/manage/persons/")

    probe("4. Timetable management",
          "GET", f"/event/{EVENT_ID}/manage/timetable/")

    print("\n──── Probe complete ────")
    return 0


if __name__ == "__main__":
    sys.exit(main())
