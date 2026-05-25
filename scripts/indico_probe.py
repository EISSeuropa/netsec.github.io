#!/usr/bin/env python3
"""
Phase 1.5 write-side confirmation. The previous probe (PR #215)
proved GETs on /manage/* routes work for the admin-promoted bot.
This one validates the write path too — without actually mutating
anything.

Safe-by-construction tests:
  - OPTIONS on the suspected write routes (returns Allow header
    without touching state).
  - PATCH with empty {} body — if the route's update schema is
    partial=True (per the agent's earlier source reading), an empty
    body is a structural no-op: either 200/204 (nothing to change)
    or 400 (validation error). Either tells us the route accepts
    PATCH from Bearer-auth admin tokens without mutating data.
  - Re-fetch of /api/user/ at the end to verify the bot identity
    didn't accidentally change.

NO POSTs with form data — those would risk mutating state.
"""

from __future__ import annotations
import os
import sys
import requests

INDICO_BASE = "https://indico.eiss-europa.com"
EVENT_ID = 22
SESSION_ID = 117          # TRANS — Military Transformation
CONTRIB_ID = 362          # Baram

TOKEN = os.environ.get("INDICO_WRITE_TOKEN") or os.environ.get("INDICO_API_TOKEN")
if not TOKEN:
    sys.exit("Set INDICO_WRITE_TOKEN in env.")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json",
}


def call(label: str, method: str, path: str, body: dict | None = None) -> None:
    url = INDICO_BASE + path
    print(f"\n──── {label} ────")
    print(f"  {method} {url}")
    if body is not None:
        print(f"  Body: {body!r}")
    try:
        kwargs = {"headers": HEADERS, "timeout": 30}
        if body is not None:
            kwargs["json"] = body
        r = requests.request(method, url, **kwargs)
    except requests.RequestException as e:
        print(f"  ERROR: {type(e).__name__}: {e}")
        return
    print(f"  Status: {r.status_code} {r.reason}")
    ct = r.headers.get("Content-Type", "")
    print(f"  Content-Type: {ct}")
    for h in ("Allow", "Vary"):
        if h in r.headers:
            print(f"  {h}: {r.headers[h]}")
    if "application/json" in ct and r.content:
        try:
            j = r.json()
            if isinstance(j, dict):
                print(f"  JSON keys: {sorted(j.keys())}")
                for k in ("error", "message", "errors", "id", "html"):
                    if k in j:
                        v = j[k]
                        if isinstance(v, str):
                            print(f"    {k}: {v[:120]!r}")
                        else:
                            print(f"    {k}: {type(v).__name__}")
        except Exception:
            print(f"  (JSON parse failed)")
    else:
        print(f"  Body: {len(r.content)} bytes of {ct.split(';')[0] or 'unknown'}")


def main() -> int:
    print("Indico write-confirm probe — admin-promoted bot, #210 Phase 1.5")

    call("0. Pre-test whoami", "GET", "/api/user/")

    # OPTIONS — discover allowed methods on each candidate write route.
    call("1. Session modify — OPTIONS",
         "OPTIONS", f"/event/{EVENT_ID}/manage/sessions/{SESSION_ID}/modify")
    call("2. Contribution REST — OPTIONS",
         "OPTIONS", f"/event/{EVENT_ID}/manage/contributions/{CONTRIB_ID}")
    call("3. Contribution edit — OPTIONS",
         "OPTIONS", f"/event/{EVENT_ID}/manage/contributions/{CONTRIB_ID}/edit")

    # Empty PATCH — if the schema is partial=True, empty body is a no-op.
    # Either succeeds (no changes applied) or rejects with 400. NEVER 403
    # if Bearer-auth admin is honoured on writes.
    call("4. Contribution REST — empty PATCH (no-op test)",
         "PATCH", f"/event/{EVENT_ID}/manage/contributions/{CONTRIB_ID}", body={})

    # Post-test whoami — confirm identity unchanged.
    call("5. Post-test whoami", "GET", "/api/user/")

    print("\n──── Probe complete ────")
    return 0


if __name__ == "__main__":
    sys.exit(main())
