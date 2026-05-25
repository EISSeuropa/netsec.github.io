#!/usr/bin/env python3
"""
Indico API probe — one-shot diagnostic for Phase 1.5 of #210.

Hits the endpoints we couldn't validate from local (because the
INDICO_WRITE_TOKEN lives only as a GitHub Actions secret), captures
the response shape, and prints a structured report. Read-only:
every request is a GET. No data is mutated.

Run via the `.github/workflows/indico-probe.yml` workflow on
manual dispatch. The workflow log carries the report; iterate on
indico_patch.py based on what we learn.

Specifically resolves three open questions from Phase 1:

  1. Does `GET /event/<eid>/manage/sessions/<sid>/modify` ever
     return JSON when asked with `Accept: application/json`?
     (Smoke test got back HTML — but the smoke test used the
     anonymous read token, which may have triggered an auth
     redirect. With a `full:everything` token in hand, maybe the
     JSON path opens up.)

  2. Same question for `GET .../contributions/<cid>/edit`.

  3. What's the right endpoint for enumerating an event's persons
     so we can resolve `person_id` from a convener's name? The
     `/manage/sessions/<sid>/conveners` route 404'd. Plausible
     alternatives: `/manage/persons/`, `/api/event/<eid>/persons/`,
     `/manage/persons/list`.

Output is structured: one block per probe, with method, URL,
status, Content-Type, body shape (or first 300 chars if HTML).
Designed to be readable in the workflow log.
"""

from __future__ import annotations

import json
import os
import sys

try:
    import requests
except ImportError:
    sys.exit("Install: pip install -r scripts/requirements.txt")

INDICO_BASE = "https://indico.eiss-europa.com"
EVENT_ID = 22   # ESSC 2026

# Known-good internal IDs from the Phase 1 smoke test (resolved via
# the live read API):
SESSION_ID_TRANS = 117       # friendly #43, "Military Transformation"
SESSION_ID_CYBER1 = 112      # friendly #57, "Virtually Transformed?"
CONTRIB_ID_BARAM = 362       # "Resilience-by-Design" — Disruptive Machines
CONTRIB_ID_BACKMAN = 494     # "Cyber risk logics" — Virtually Transformed


def get_token() -> str:
    """Read the write token from env. Fails fast if missing — this
    script has no useful read-only mode (the read-only routes are
    already exercised by sync-indico.py)."""
    token = os.environ.get("INDICO_WRITE_TOKEN") or os.environ.get("INDICO_API_TOKEN")
    if not token:
        sys.exit(
            "Set INDICO_WRITE_TOKEN (or INDICO_API_TOKEN) in env. "
            "The GH Actions workflow injects this from the repo secret."
        )
    return token


def probe(name: str, method: str, path: str, *, token: str,
          accept: str = "application/json") -> None:
    """One probe. Prints a structured block."""
    url = INDICO_BASE + path
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": accept,
    }
    print(f"\n──── {name} ────")
    print(f"  {method} {url}")
    print(f"  Accept: {accept}")
    try:
        r = requests.request(method, url, headers=headers, timeout=30)
    except requests.RequestException as e:
        print(f"  ERROR: {type(e).__name__}: {e}")
        return
    print(f"  Status: {r.status_code} {r.reason}")
    ct = r.headers.get("Content-Type", "")
    print(f"  Content-Type: {ct}")
    print(f"  Body size: {len(r.content)} bytes")

    if "application/json" in ct:
        try:
            body = r.json()
            # Print top-level keys for objects, length for arrays
            if isinstance(body, dict):
                print(f"  JSON top-level keys: {sorted(body.keys())}")
                # Surface one level deeper for interesting keys
                for k in ("form_data", "data", "conveners", "persons",
                          "title", "session_id", "location_data"):
                    if k in body:
                        v = body[k]
                        if isinstance(v, (str, int, float, bool)):
                            print(f"    {k}: {v!r}")
                        elif isinstance(v, dict):
                            print(f"    {k}: dict[{sorted(v.keys())}]")
                        elif isinstance(v, list):
                            print(f"    {k}: list[{len(v)}]")
            elif isinstance(body, list):
                print(f"  JSON array: {len(body)} items")
                if body and isinstance(body[0], dict):
                    print(f"    first item keys: {sorted(body[0].keys())}")
            else:
                print(f"  JSON scalar: {body!r}")
        except json.JSONDecodeError:
            print(f"  (Content-Type claims JSON but body didn't parse)")
            print(f"  First 200 chars: {r.text[:200]!r}")
    else:
        snippet = r.text[:300].replace("\n", " ").strip()
        print(f"  First 300 chars: {snippet!r}")


def main() -> int:
    token = get_token()

    print("Indico API probe — Phase 1.5 endpoint discovery for #210")
    print(f"Base: {INDICO_BASE}")
    print(f"Event: {EVENT_ID}")
    # Don't log any bytes of the token, not even a prefix. CodeQL's
    # `py/clear-text-logging-sensitive-data` rule flags any flow from
    # the env var to print — and rightly so: workflow logs are
    # readable by anyone with repo access, and a token prefix can
    # accelerate offline guessing if the prefix encodes anything
    # structural. The /api/user/ probe below confirms the token
    # works without needing us to print any of it here.
    print("Token: present.")

    # ── Probe 0: confirm the token works ──
    probe(
        "0. Whoami (sanity check on the token)",
        "GET", "/api/user/",
        token=token,
    )

    # ── Probe 1: session-modify, JSON ──
    probe(
        "1a. Session modify — JSON",
        "GET", f"/event/{EVENT_ID}/manage/sessions/{SESSION_ID_TRANS}/modify",
        token=token, accept="application/json",
    )
    probe(
        "1b. Session modify — HTML (for comparison)",
        "GET", f"/event/{EVENT_ID}/manage/sessions/{SESSION_ID_TRANS}/modify",
        token=token, accept="text/html",
    )

    # ── Probe 2: contribution-edit, JSON ──
    probe(
        "2a. Contribution edit — JSON",
        "GET", f"/event/{EVENT_ID}/manage/contributions/{CONTRIB_ID_BARAM}/edit",
        token=token, accept="application/json",
    )
    probe(
        "2b. Contribution edit — HTML",
        "GET", f"/event/{EVENT_ID}/manage/contributions/{CONTRIB_ID_BARAM}/edit",
        token=token, accept="text/html",
    )
    # The narrow JSON PATCH route — what fields does its GET expose?
    probe(
        "2c. Contribution REST shape — JSON",
        "GET", f"/event/{EVENT_ID}/manage/contributions/{CONTRIB_ID_BARAM}",
        token=token, accept="application/json",
    )

    # ── Probe 3: person enumeration ──
    probe(
        "3a. Event persons (manage namespace)",
        "GET", f"/event/{EVENT_ID}/manage/persons/",
        token=token,
    )
    probe(
        "3b. Event persons (alternative)",
        "GET", f"/event/{EVENT_ID}/manage/persons/list",
        token=token,
    )
    probe(
        "3c. Event persons via /api/ namespace",
        "GET", f"/api/event/{EVENT_ID}/persons",
        token=token,
    )
    probe(
        "3d. Event persons via legacy export",
        "GET", f"/export/event/{EVENT_ID}.json?detail=conveners",
        token=token,
    )

    # ── Probe 4: session-level convener routes ──
    # The /manage/sessions/<sid>/conveners path 404'd in the Phase 1
    # smoke. Try alternates — some Indico versions put conveners under
    # blocks rather than sessions.
    probe(
        "4a. Session block listing",
        "GET", f"/event/{EVENT_ID}/manage/sessions/{SESSION_ID_CYBER1}/blocks/",
        token=token,
    )
    probe(
        "4b. Session full detail",
        "GET", f"/event/{EVENT_ID}/manage/sessions/{SESSION_ID_CYBER1}/",
        token=token,
    )

    # ── Probe 5: timetable entry — confirm the PATCH GET shape ──
    # The Phase 1 dry-run resolved entry_id as "s649" (an `s` prefix).
    # That's the timetable export's session-entry naming, but the
    # /manage/timetable/<entry_id> route probably wants the numeric
    # block id. Probe the GET to see.
    probe(
        "5. Timetable entry GET",
        "GET", f"/event/{EVENT_ID}/manage/timetable/",
        token=token,
    )

    print("\n──── Probe complete ────")
    print("Read the report above and update scripts/indico_patch.py accordingly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
