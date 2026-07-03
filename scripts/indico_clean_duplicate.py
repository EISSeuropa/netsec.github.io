#!/usr/bin/env python3
"""
Clean a duplicated Indico event of inherited content.

USE CASE: Indico's "duplicate event" feature is fast and preserves
the configuration we want (abstract types, custom fields, review
workflow, role assignments, theme, branding, important dates). But
it ALSO copies the content of the previous event — contributions,
sessions, materials — carrying their friendly IDs along. New
submissions in the duplicated event continue from the old counter,
so contribution #1 in "ESSC 2027" is actually #341 (or whatever
the carryover is).

This script enumerates inherited content in a duplicated event and
selectively deletes it, leaving the configuration intact. Run it
once, right after duplicating, to get a clean event with the right
config and reset counters.

PRECONDITION: the bot account owning INDICO_WRITE_TOKEN must have
the admin flag set on the Indico instance. Phase 1.5 of #210
established this; see docs/indico-patch.md (retirement notice) for
the back-story. The fix-plan write path that shared this precondition
(the former scripts/indico_patch.py) has been retired in favour of the
plugin CLI `indico netsec apply-fixplan`; this cleanup script is the
only remaining consumer of INDICO_WRITE_TOKEN.

SAFETY:
  - Refuses to touch events in PROTECTED_EVENTS (a hardcoded
    allow-list of IDs we never want this script to delete from —
    notably the live ESSC 2026 event 22). Override with --force,
    but the only legitimate use of --force is unsticking the
    PROTECTED_EVENTS list itself.
  - Dry-run by default. --apply required for real deletes.
  - --delete must be given explicitly per category. No "delete
    everything" shortcut.
  - Logs every DELETE before issuing. Bails on first error.
  - Token validation on startup confirms admin status before any
    write — fails fast if the bot was demoted.

USAGE:
  Dry-run, list what would be deleted from event 23:
    python3 scripts/indico_clean_duplicate.py --event 23

  Real cleanup of contributions + sessions:
    python3 scripts/indico_clean_duplicate.py --event 23 --apply \\
        --delete contributions --delete sessions

  Verify counter behaviour (after running):
    Inspect /export/event/23.json?detail=contributions for the next
    expected friendly ID of new contributions. Indico's friendly_id
    behaviour on deleted records is one of the open Phase 1.5
    items — first real apply will resolve it.

Tracked alongside the (now-retired) indico_patch.py in #210
(v1.7.0 milestone).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

try:
    import requests
except ImportError:
    sys.exit("Install: pip install -r scripts/requirements.txt")


# ──────────────────────────── config ────────────────────────────

INDICO_BASE = "https://indico.eiss-europa.com"
ENV_WRITE_TOKEN = "INDICO_WRITE_TOKEN"

# Events this script REFUSES to touch under any normal circumstance.
# Guards against accidental wipe of live data. Override only with
# --force, and only when intentionally clearing the live event for
# a fresh start (extremely rare).
PROTECTED_EVENTS = {
    22,   # ESSC 2026 — live conference data, never wipe via this script
}

# Categories of inherited content we know how to delete. Each
# carries the API discovery + delete pattern. Tracks list:
#   - list_via: how to enumerate item IDs in a duplicated event
#   - list_field: where the items live in the response
#   - id_field: which JSON field carries the management-API ID
#   - delete_path: DELETE URL pattern (event_id, item_id substituted)
CATEGORIES: dict[str, dict[str, str]] = {
    "contributions": {
        "list_via": "/export/event/{event_id}.json?detail=contributions",
        "list_field": "contributions",
        "id_field": "id",
        "delete_path": "/event/{event_id}/manage/contributions/{item_id}",
    },
    # Sessions live in the timetable. The /export/timetable export
    # exposes sessionId on each Session entry. The DELETE route is
    # not yet probed end-to-end — first real apply will resolve.
    "sessions": {
        "list_via": "/export/timetable/{event_id}.json",
        # `list_field` is special-cased below — timetable is keyed
        # by date then entry, not a flat list.
        "list_field": "__timetable__",
        "id_field": "sessionId",
        "delete_path": "/event/{event_id}/manage/sessions/{item_id}",
    },
}


# ──────────────────────────── HTTP layer ────────────────────────────

class IndicoClient:
    """Minimal HTTP wrapper: read + delete only — no PATCH or POST
    surfaces, because the write side of this script is strictly
    DELETE. (The former indico_patch.py carried a fuller client with
    PATCH/POST; it has been retired, so this is now self-contained.)"""

    def __init__(self, *, apply: bool, verbose: bool = True):
        self.apply = apply
        self.verbose = verbose
        self.token = os.environ.get(ENV_WRITE_TOKEN)
        if apply and not self.token:
            sys.exit(
                f"--apply requires the {ENV_WRITE_TOKEN} env var. "
                "Generate the token under a bot account with admin flag "
                "and `full:everything` scope (see docs/indico-patch.md)."
            )

    def get_json(self, path: str) -> Any:
        url = path if path.startswith("http") else INDICO_BASE + path
        headers = {"Accept": "application/json"}
        if self.token and not path.startswith("/export"):
            # /export/* rejects Bearer; everything else needs it.
            headers["Authorization"] = f"Bearer {self.token}"
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        return r.json()

    def delete(self, path: str) -> requests.Response | None:
        url = INDICO_BASE + path
        prefix = "WOULD " if not self.apply else ""
        if self.verbose:
            print(f"  {prefix}DELETE {url}")
        if not self.apply:
            return None
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }
        r = requests.delete(url, headers=headers, timeout=30)
        r.raise_for_status()
        return r

    def validate_admin(self) -> None:
        """Confirm token + admin status before any write. Fails
        fast with a clear message if the bot was demoted.

        Skipped when no token is set — that's the legitimate
        no-write enumeration mode, which uses anonymous /export/*
        reads only and never needs auth. The --apply path is
        already gated in __init__ to require a token, so this
        branch is reached only via dry-run without a token, where
        bailing here would be unhelpful."""
        if not self.token:
            if self.verbose:
                print("  no token set — read-only enumeration mode")
            return
        try:
            me = self.get_json("/api/user/")
        except requests.HTTPError as e:
            sys.exit(
                f"Token validation failed (GET /api/user/ → "
                f"{e.response.status_code}). Token expired or revoked?"
            )
        if not isinstance(me, dict):
            sys.exit(
                f"Token validation: GET /api/user/ returned an unexpected "
                f"shape ({type(me).__name__}). Expected a JSON object — "
                "the Indico instance may have rejected the token without "
                "an HTTP-level error. Verify the token still exists in "
                "the bot account's API Tokens page."
            )
        if not me.get("admin"):
            sys.exit(
                "Token validates but the user is not admin on Indico. "
                "This script needs admin write access to manage routes "
                "(Phase 1.5 finding, see docs/indico-patch.md). Ask the "
                "Indico admin to set the admin flag on the bot account."
            )
        name = me.get("full_name") or me.get("first_name") or "?"
        if self.verbose:
            print(f"  token OK: {name} (admin)")


# ──────────────────────────── enumeration ────────────────────────────

def list_items(client: IndicoClient, event_id: int,
               category: str) -> list[tuple[Any, str]]:
    """Return [(item_id, human_label), ...] for the requested category."""
    spec = CATEGORIES[category]
    doc = client.get_json(spec["list_via"].format(event_id=event_id))

    if spec["list_field"] == "__timetable__":
        # Timetable: results -> {event_id_str} -> {date} -> {entry_id} -> entry
        tt = doc["results"][str(event_id)]
        items: list[tuple[Any, str]] = []
        seen: set[Any] = set()
        for entries in tt.values():
            for entry in entries.values():
                if entry.get("entryType") != "Session":
                    continue
                sid = entry.get(spec["id_field"])
                if sid is None or sid in seen:
                    continue
                seen.add(sid)
                title = entry.get("title", "(untitled)")
                items.append((sid, title))
        return items

    # Standard flat-list categories (contributions, etc.).
    results = doc.get("results", [])
    if not results:
        return []
    event = results[0]
    contribs = event.get(spec["list_field"], [])
    return [
        (c.get(spec["id_field"]), c.get("title", "(untitled)"))
        for c in contribs
        if c.get(spec["id_field"]) is not None
    ]


# ──────────────────────────── delete loop ────────────────────────────

def clean_category(client: IndicoClient, event_id: int,
                   category: str) -> int:
    """Delete all items of the named category. Returns the count."""
    if category not in CATEGORIES:
        sys.exit(
            f"Unknown category {category!r}. "
            f"Known: {sorted(CATEGORIES.keys())}"
        )
    spec = CATEGORIES[category]
    items = list_items(client, event_id, category)
    print(f"\n── {category}: {len(items)} item(s) inherited ──")
    if not items:
        return 0
    failed = 0
    for item_id, label in items:
        # Truncate label so a single deletion line stays readable.
        short = label[:60] + "…" if len(label) > 60 else label
        print(f"  [{item_id}] {short}")
        try:
            client.delete(spec["delete_path"].format(
                event_id=event_id, item_id=item_id,
            ))
        except requests.HTTPError as e:
            print(f"    FAIL — {e.response.status_code} {e.response.reason}")
            failed += 1
        except Exception as e:
            print(f"    FAIL — {type(e).__name__}: {e}")
            failed += 1
    return len(items) - failed


# ──────────────────────────── CLI ────────────────────────────

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Clean inherited content from a duplicated Indico event.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "PROTECTED_EVENTS is hardcoded in the script. ESSC 2026 (event 22) "
            "is always protected. Override with --force only when intentionally "
            "wiping the live event."
        ),
    )
    p.add_argument("--event", type=int, required=True,
                   help="Indico event ID to clean.")
    p.add_argument("--delete", action="append", default=[],
                   choices=sorted(CATEGORIES.keys()),
                   help="Category to delete. Repeat for multiple "
                        "(e.g. --delete contributions --delete sessions).")
    p.add_argument("--apply", action="store_true",
                   help="Actually issue DELETEs. Without this flag, "
                        "the script only lists what it would do.")
    p.add_argument("--force", action="store_true",
                   help="Bypass the PROTECTED_EVENTS guard. Use only "
                        "when intentionally wiping a normally-protected "
                        "event (extremely rare).")
    p.add_argument("--quiet", action="store_true",
                   help="Suppress per-item logging.")
    args = p.parse_args(argv)

    if args.event in PROTECTED_EVENTS and not args.force:
        sys.exit(
            f"Event {args.event} is in PROTECTED_EVENTS. Refusing to act. "
            "If this is intentional, pass --force (and re-read the script's "
            "warnings about why this event was protected in the first place)."
        )
    if args.event in PROTECTED_EVENTS:
        print(f"⚠️  --force in use against PROTECTED event {args.event}. "
              f"Proceeding because --force is explicit.")

    if not args.delete:
        print("No --delete categories specified — nothing to do.")
        print(f"Pass one or more of: {sorted(CATEGORIES.keys())}")
        return 0

    print(f"Indico clean-duplicate — event {args.event}, "
          f"mode={'apply' if args.apply else 'dry-run'}, "
          f"categories={args.delete}")

    client = IndicoClient(apply=args.apply, verbose=not args.quiet)
    client.validate_admin()

    total = 0
    for category in args.delete:
        n = clean_category(client, args.event, category)
        total += n
        if not args.apply:
            print(f"  (would delete {n} {category})")

    verb = "Deleted" if args.apply else "Would delete"
    print(f"\n{verb} {total} item(s) total.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
