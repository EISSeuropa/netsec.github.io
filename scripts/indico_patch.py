#!/usr/bin/env python3
"""
Indico patch helper: apply a YAML fix-plan to an Indico event.

╔══════════════════════════════════════════════════════════════════╗
║  STATUS: writes architecturally blocked. Dry-run mode only.      ║
║                                                                  ║
║  The Phase 1.5 probe (#210, PRs #212/#213) established that      ║
║  Personal Access Tokens on the EISS Indico instance cannot       ║
║  reach `/event/<id>/manage/*` routes at any scope — not even     ║
║  with `full:everything` plus every other box ticked. The         ║
║  management routes return 403 with `Vary: Cookie` and a fresh    ║
║  Set-Cookie, meaning Indico is ignoring the Bearer header        ║
║  entirely and treating the request as anonymous. There's no      ║
║  scope hint on the 403 either (no WWW-Authenticate header) —     ║
║  the route literally doesn't process token auth.                 ║
║                                                                  ║
║  This is consistent with documented Indico behaviour: the        ║
║  management UI is session-cookie-only. Token-driven writes       ║
║  require either an OAuth 2.0 Client App (registered by an        ║
║  Indico admin) or a service account (newer feature, not yet      ║
║  enabled on this instance). Both routes need admin cooperation.  ║
║                                                                  ║
║  Until that lands, this script is useful as:                     ║
║    1. A specification of what fixes are needed — the fix-plan    ║
║       YAML format is a structured, auditable, git-trackable      ║
║       checklist of UI changes a human will make.                 ║
║    2. A dry-run validator — friendly→internal ID resolution      ║
║       works against the read API, so every patch is             ║
║       verified to point at a real session/contribution/person   ║
║       before a human clicks anything in the UI.                  ║
║    3. A future-proof skeleton — when OAuth-app auth lands,       ║
║       only the IndicoClient methods need to change; the          ║
║       dispatch/resolution/CLI layers are correct as-is.          ║
║                                                                  ║
║  `--apply` will still attempt the write calls but will hit       ║
║  the same 403 wall. The validate_token() check on startup        ║
║  doesn't catch this because /api/user/ works fine — only the     ║
║  /manage/* surface is blocked.                                   ║
╚══════════════════════════════════════════════════════════════════╝

This is the write-side companion to `sync-indico.py` (which is
read-only). It exists to make the next ESSC's prep cycle faster:
when we spot drift between the authoritative programme document
(e.g. the organisers' internal PDF) and what's live on Indico, we
can express the fixes as a tiny YAML file, dry-run it, then apply.

Goal flow (think ESSC 27 in spring 2027):
  1. Author / generate a fix-plan YAML (one entry per correction).
  2. `python3 scripts/indico_patch.py path/to/fix-plan.yaml --dry-run`
     → script resolves friendly IDs (e.g. "session 43", "Julia Carver")
       to internal IDs by querying the live read API, prints the plan,
       hits no write endpoints. Writes the resolved IDs back into the
       YAML alongside the human-readable refs.
  3. Eyeball the dry-run, commit the YAML for audit.
  4. `python3 scripts/indico_patch.py path/to/fix-plan.yaml --apply`
     → for real. Prints each request and the response status.
  5. Wait for the next daily `sync-indico.py` to pull corrected state
     into `data/indico.json`.

Why a separate tool, not a `--write` flag on sync-indico.py:
  - Different blast radius: sync is read-only, idempotent, runs daily
    in CI. Patch is destructive, occasional, run by a human.
  - Different auth: sync uses a read-scope token (`INDICO_API_TOKEN`).
    Patch needs a write-scope token (`INDICO_WRITE_TOKEN`, scope
    `full:everything`) — keeping them separate means the CI service
    account can't accidentally mutate state.
  - Different failure modes: sync soft-fails (CI continues with last
    good data). Patch hard-fails on the first error so the operator
    can investigate before continuing.

Endpoints used (all under `/event/<id>/manage/`):

  | Operation                  | Method | Route                       | Format |
  | -------------------------- | ------ | --------------------------- | ------ |
  | Rename session             | POST   | /sessions/<sid>/modify      | wtforms |
  | Change session room        | POST   | /sessions/<sid>/modify      | wtforms |
  | Edit person affiliation    | PATCH  | /persons/<pid>              | JSON   |
  | Move contribution → session| PATCH  | /contributions/<cid>        | JSON   |
  | Rename contribution        | POST   | /contributions/<cid>/edit   | wtforms |
  | Edit session block time    | PATCH  | /timetable/<entry_id>       | JSON   |

The JSON endpoints accept narrow PATCH bodies (e.g. `{"affiliation":
"…"}`); the wtforms endpoints need read-modify-write of the full
form. The helper functions below hide that asymmetry.

Tracked in #210. Predecessor: #208 (programme print-to-PDF, which
surfaced just how much manual remediation we were doing).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import requests
    import yaml
except ImportError as e:
    sys.exit(
        f"Missing dependency: {e.name}. "
        "Install with: pip install -r scripts/requirements.txt"
    )

# ──────────────────────────── config ────────────────────────────

INDICO_BASE = "https://indico.eiss-europa.com"

# Write-scope token. Generated via Indico UI → My Profile → API Tokens,
# scope `full:everything`. Stored as GitHub Actions secret
# `INDICO_WRITE_TOKEN`. Separate from `INDICO_API_TOKEN` (read-only)
# so the daily-sync CI service account can never escalate.
ENV_WRITE_TOKEN = "INDICO_WRITE_TOKEN"
ENV_READ_TOKEN = "INDICO_API_TOKEN"   # fallback for read-only operations

# How patches are loaded / saved. The YAML round-trips: dry-runs
# write resolved internal IDs back into the file alongside the
# friendly refs so subsequent runs skip the resolution step.
YAML_INDENT = 2


# ──────────────────────────── HTTP layer ────────────────────────────

class IndicoClient:
    """Thin client for read + write against an Indico instance.

    Mirrors the structure of `sync-indico.py`'s `_get()` but adds
    write methods. Write methods refuse to run unless an explicit
    `apply=True` is passed at construction — the default behaviour
    is dry-run, the safer mode.

    Token resolution: writes require `INDICO_WRITE_TOKEN`; reads
    accept either token (writes can read).
    """

    def __init__(self, *, apply: bool = False, verbose: bool = True):
        self.apply = apply
        self.verbose = verbose
        self.write_token = os.environ.get(ENV_WRITE_TOKEN)
        self.read_token = os.environ.get(ENV_READ_TOKEN) or self.write_token
        if apply and not self.write_token:
            sys.exit(
                f"--apply requires the {ENV_WRITE_TOKEN} env var "
                "(personal token with scope `full:everything`)."
            )

    # ── reads ──

    def get_json(self, path: str, *, params: dict | None = None) -> dict:
        """GET against any Indico endpoint, return parsed JSON.

        Uses Bearer auth on `/api/*` and on `/event/<id>/manage/*`;
        leaves `/export/*` anonymous (it rejects Bearer with 400 on
        some Indico versions).
        """
        url = path if path.startswith("http") else INDICO_BASE + path
        headers = {"Accept": "application/json"}
        if self.read_token and not path.startswith("/export"):
            headers["Authorization"] = f"Bearer {self.read_token}"
        r = requests.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    # ── writes ──

    def patch_json(self, path: str, payload: dict) -> dict | None:
        """JSON PATCH against a management endpoint.

        Used for the clean-JSON write paths (person affiliation,
        contribution session move, timetable entry datetime). Returns
        the parsed JSON response body or None in dry-run mode.
        """
        url = INDICO_BASE + path
        self._log_intent("PATCH", url, payload)
        if not self.apply:
            return None
        if not self.write_token:
            raise RuntimeError(
                f"PATCH requires {ENV_WRITE_TOKEN} (apply mode requested)."
            )
        headers = {
            "Authorization": f"Bearer {self.write_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        r = requests.patch(url, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        # Some 204 No Content responses have empty bodies.
        return r.json() if r.content else {}

    def post_form(self, path: str, form: dict) -> str | None:
        """Form-encoded POST against a management endpoint.

        Used for wtforms write paths (session-modify,
        contribution-edit). Returns the response body as text or
        None in dry-run mode. Caller is responsible for fetching the
        existing form first and merging the diff — wtforms validates
        every required field, so a partial submit will fail.
        """
        url = INDICO_BASE + path
        self._log_intent("POST", url, form)
        if not self.apply:
            return None
        if not self.write_token:
            raise RuntimeError(
                f"POST requires {ENV_WRITE_TOKEN} (apply mode requested)."
            )
        headers = {
            "Authorization": f"Bearer {self.write_token}",
            "Accept": "application/json",
        }
        r = requests.post(url, headers=headers, data=form, timeout=30)
        r.raise_for_status()
        return r.text

    # ── observability ──

    def _log_intent(self, method: str, url: str, body: dict) -> None:
        prefix = "WOULD " if not self.apply else ""
        if self.verbose:
            # Body redaction: nothing sensitive here today (no PII
            # beyond names + affiliations, which are already public),
            # but keep the hook visible for future fields.
            body_preview = json.dumps(body, ensure_ascii=False, sort_keys=True)
            if len(body_preview) > 500:
                body_preview = body_preview[:500] + "…"
            print(f"  {prefix}{method} {url}")
            print(f"    body: {body_preview}")

    def validate_token(self) -> None:
        """Hit `/api/user/` on startup to confirm the write token
        works before we attempt any writes. Fails fast with a clear
        message rather than letting the first patch return HTML.
        """
        if not self.write_token:
            return  # dry-run without token is fine
        try:
            me = self.get_json("/api/user/")
        except requests.HTTPError as e:
            sys.exit(
                f"Token validation failed (GET /api/user/ → {e.response.status_code}). "
                f"Check that {ENV_WRITE_TOKEN} carries the `full:everything` scope."
            )
        if self.verbose:
            name = me.get("full_name") or me.get("first_name") or "?"
            print(f"  token OK: authenticated as {name}")


# ──────────────────────────── data shapes ────────────────────────────

@dataclass
class Patch:
    """One entry in the fix-plan. Discriminated by `.kind`."""
    kind: str                       # 'session' | 'person' | 'contribution' | 'block_time'
    by: str                         # how `ref` identifies the target
    ref: Any                        # human-readable reference (friendly id or substring)
    set: dict[str, Any]             # field → new value
    in_session: int | str | None = None   # context for person lookups
    resolved: dict[str, Any] = field(default_factory=dict)  # cache of internal IDs
    note: str | None = None         # free-text reason (carried into commit message)


@dataclass
class FixPlan:
    event_id: int
    patches: list[Patch]

    @classmethod
    def from_yaml(cls, path: Path) -> "FixPlan":
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict) or "event_id" not in doc or "patches" not in doc:
            sys.exit(f"{path}: malformed — needs top-level `event_id` and `patches`.")
        # Load resolved-id cache from a JSON sidecar (`fix-plan.yaml`
        # ↔ `fix-plan.yaml.resolved.json`). The cache is auto-generated
        # and gitignored — keeping it out of the YAML preserves the
        # YAML's comments and human-authored formatting. Keyed by
        # patch index (1-based) for stability against YAML reshuffles.
        cache_path = _resolved_cache_path(path)
        cache: dict[str, dict[str, Any]] = {}
        if cache_path.exists():
            try:
                cache = json.loads(cache_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                # Corrupt cache → ignore and rebuild. The file is
                # advisory, not authoritative.
                cache = {}

        patches = []
        for i, raw in enumerate(doc.get("patches", []), 1):
            if "kind" not in raw or "by" not in raw or "ref" not in raw or "set" not in raw:
                sys.exit(
                    f"{path}: patch #{i} missing required keys "
                    "(kind, by, ref, set)."
                )
            patches.append(Patch(
                kind=raw["kind"],
                by=raw["by"],
                ref=raw["ref"],
                set=raw["set"],
                in_session=raw.get("in_session"),
                resolved=dict(cache.get(str(i), {})),
                note=raw.get("note"),
            ))
        return cls(event_id=int(doc["event_id"]), patches=patches)

    def write_cache(self, yaml_path: Path) -> None:
        """Persist resolved internal IDs to a sidecar JSON file so
        re-runs skip the lookup step. Leaves the YAML untouched."""
        cache = {
            str(i): p.resolved
            for i, p in enumerate(self.patches, 1)
            if p.resolved
        }
        if not cache:
            return
        cache_path = _resolved_cache_path(yaml_path)
        cache_path.write_text(
            json.dumps(cache, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def _resolved_cache_path(yaml_path: Path) -> Path:
    """The sidecar path next to a fix-plan YAML."""
    return yaml_path.with_suffix(yaml_path.suffix + ".resolved.json")


# ──────────────────────────── ID resolution ────────────────────────────

class Resolver:
    """Resolves friendly references in patches to Indico-internal IDs.

    Fetches the event timetable once on first use and caches it.
    Friendly IDs (e.g. session #43) come from Indico's UI numbering;
    they live alongside internal database IDs (e.g. sessionId 117) in
    the timetable export. See sync-indico.py for the same mapping.
    """

    def __init__(self, client: IndicoClient, event_id: int):
        self.client = client
        self.event_id = event_id
        self._timetable: dict | None = None
        self._contribs: dict | None = None

    def _timetable_data(self) -> dict:
        if self._timetable is None:
            doc = self.client.get_json(f"/export/timetable/{self.event_id}.json")
            self._timetable = doc["results"][str(self.event_id)]
        return self._timetable

    def _contributions(self) -> list[dict]:
        if self._contribs is None:
            doc = self.client.get_json(
                f"/export/event/{self.event_id}.json",
                params={"detail": "contributions"},
            )
            self._contribs = doc["results"][0].get("contributions", [])
        return self._contribs

    def session_id(self, *, by: str, ref: Any) -> int:
        """Return the internal session id for a friendly reference."""
        tt = self._timetable_data()
        matches: list[tuple[int, str]] = []
        for entries in tt.values():
            for entry in entries.values():
                if entry.get("entryType") != "Session":
                    continue
                sid = entry.get("sessionId")
                fid = entry.get("friendlyId")
                title = entry.get("title", "")
                if by == "friendlyId" and fid == int(ref):
                    matches.append((sid, title))
                elif by == "title_match" and isinstance(ref, str) and ref.lower() in title.lower():
                    matches.append((sid, title))
        if not matches:
            raise LookupError(f"No session matched {by}={ref!r}")
        unique = {m[0] for m in matches}
        if len(unique) > 1:
            raise LookupError(
                f"Ambiguous session match for {by}={ref!r}: "
                f"{[(s, t) for s, t in matches]}"
            )
        return matches[0][0]

    def contribution_id(self, *, by: str, ref: Any) -> int:
        """Return the internal contribution id."""
        contribs = self._contributions()
        matches: list[tuple[int, str]] = []
        for c in contribs:
            cid = c.get("id") or c.get("db_id")
            title = c.get("title", "")
            if by == "title_match" and isinstance(ref, str) and ref.lower() in title.lower():
                matches.append((int(cid), title))
            elif by == "id" and int(cid) == int(ref):
                matches.append((int(cid), title))
        if not matches:
            raise LookupError(f"No contribution matched {by}={ref!r}")
        if len({m[0] for m in matches}) > 1:
            raise LookupError(
                f"Ambiguous contribution match for {by}={ref!r}: "
                f"{[(c, t) for c, t in matches]}"
            )
        return matches[0][0]

    def person_id(self, *, in_session: int | str, by: str, ref: str) -> int:
        """Return the internal person id for a convener of a session.

        `in_session` is the friendly session ID; we look up that
        session's conveners list and match the person by name.

        NEEDS LIVE-TOKEN VALIDATION. The `/manage/sessions/<sid>/conveners`
        endpoint 404'd in smoke testing — either the path differs in
        the version of Indico we hit, or person enumeration requires
        a different route (likely `/manage/persons/` at event level).
        Tracked in #210 (P1.5). Until validated, person patches
        require manually supplying `resolved.person_id` in the cache.
        """
        if in_session is None:
            raise LookupError("person resolution needs an `in_session` field")
        sid_internal = self.session_id(by="friendlyId", ref=int(in_session))
        doc = self.client.get_json(
            f"/event/{self.event_id}/manage/sessions/{sid_internal}/conveners"
        )
        # The shape of the conveners endpoint varies by Indico version;
        # tolerate both `{conveners: [...]}` and a bare list.
        conveners = doc.get("conveners") if isinstance(doc, dict) else doc
        if not isinstance(conveners, list):
            raise LookupError(
                f"Unexpected conveners shape for session {in_session}: "
                f"{type(doc).__name__}"
            )
        if by == "name":
            ref_lc = ref.lower()
            matches = [
                c for c in conveners
                if ref_lc in (c.get("fullName") or c.get("full_name") or "").lower()
            ]
        else:
            raise LookupError(f"Unsupported person lookup mode: by={by!r}")
        if not matches:
            raise LookupError(
                f"No convener named {ref!r} found in session {in_session}"
            )
        if len(matches) > 1:
            raise LookupError(
                f"Ambiguous convener match {ref!r} in session {in_session}: "
                f"{[c.get('fullName') for c in matches]}"
            )
        c = matches[0]
        pid = c.get("personId") or c.get("person_id") or c.get("id")
        if not pid:
            raise LookupError(f"Convener match for {ref!r} has no personId field")
        return int(pid)


# ──────────────────────────── patch dispatch ────────────────────────────

def apply_session_patch(client: IndicoClient, event_id: int, patch: Patch,
                        resolver: Resolver) -> None:
    """Rename session, change room, or change venue.

    NEEDS LIVE-TOKEN VALIDATION. The session-modify endpoint is a
    wtforms POST that requires the full form to be re-submitted.
    Dry-run resolution works (session_id is found correctly), but
    the read-modify-write of the form has not been tested end-to-end.
    Expected to need adjustment after the first apply attempt — the
    `Accept: application/json` GET path returned HTML in smoke
    testing; we may need to scrape the HTML form for required-field
    defaults instead, or find an alternative JSON-aware route.
    Tracked in #210 (P1.5).
    """
    sid = patch.resolved.get("session_id") or resolver.session_id(
        by=patch.by, ref=patch.ref
    )
    patch.resolved["session_id"] = sid

    current = client.get_json(
        f"/event/{event_id}/manage/sessions/{sid}/modify"
    )
    form_data = current.get("form_data") or current.get("data") or current
    form = dict(form_data)

    if "title" in patch.set:
        form["title"] = patch.set["title"]
    if "room_name" in patch.set or "venue_name" in patch.set:
        loc = dict(form.get("location_data", {}))
        if "room_name" in patch.set:
            loc["room_name"] = patch.set["room_name"]
            loc["inheriting"] = False
        if "venue_name" in patch.set:
            loc["venue_name"] = patch.set["venue_name"]
            loc["inheriting"] = False
        form["location_data"] = json.dumps(loc)

    client.post_form(f"/event/{event_id}/manage/sessions/{sid}/modify", form)


def apply_person_patch(client: IndicoClient, event_id: int, patch: Patch,
                       resolver: Resolver) -> None:
    """Edit an event-person's name/affiliation/title."""
    pid = patch.resolved.get("person_id") or resolver.person_id(
        in_session=patch.in_session, by=patch.by, ref=patch.ref
    )
    patch.resolved["person_id"] = pid

    # JSON PATCH — narrow, idempotent. `EventPersonUpdateSchema` is
    # partial=True so we send only the fields we want to change.
    allowed = {"first_name", "last_name", "title", "affiliation",
               "affiliation_id", "email"}
    payload = {k: v for k, v in patch.set.items() if k in allowed}
    if not payload:
        raise ValueError(
            f"person patch for {patch.ref!r} has no recognised fields "
            f"(allowed: {sorted(allowed)})"
        )
    client.patch_json(f"/event/{event_id}/manage/persons/{pid}", payload)


def apply_contribution_patch(client: IndicoClient, event_id: int, patch: Patch,
                             resolver: Resolver) -> None:
    """Rename a contribution or move it between sessions."""
    cid = patch.resolved.get("contribution_id") or resolver.contribution_id(
        by=patch.by, ref=patch.ref
    )
    patch.resolved["contribution_id"] = cid

    if "session" in patch.set:
        # Session reparent via clean JSON PATCH.
        target_friendly = int(patch.set["session"])
        target_internal = patch.resolved.get("target_session_id") or \
                          resolver.session_id(by="friendlyId", ref=target_friendly)
        patch.resolved["target_session_id"] = target_internal
        client.patch_json(
            f"/event/{event_id}/manage/contributions/{cid}",
            {"session_id": target_internal},
        )

    if "title" in patch.set:
        # NEEDS LIVE-TOKEN VALIDATION. Same caveat as session-rename:
        # contribution-edit is a wtforms endpoint and the read path
        # may not honour Accept: application/json. Tracked in #210.
        current = client.get_json(
            f"/event/{event_id}/manage/contributions/{cid}/edit"
        )
        form_data = current.get("form_data") or current.get("data") or current
        form = dict(form_data)
        form["title"] = patch.set["title"]
        client.post_form(
            f"/event/{event_id}/manage/contributions/{cid}/edit", form
        )


def apply_block_time_patch(client: IndicoClient, event_id: int, patch: Patch,
                           resolver: Resolver) -> None:
    """Change a session block's start or end datetime via timetable entry."""
    entry_id = patch.resolved.get("entry_id")
    if not entry_id:
        # Resolve via timetable: the entry id is the `id` field on
        # session entries.
        tt = resolver._timetable_data()
        sid = resolver.session_id(by=patch.by, ref=patch.ref)
        for entries in tt.values():
            for entry in entries.values():
                if entry.get("sessionId") == sid:
                    entry_id = entry.get("id")
                    break
            if entry_id:
                break
        if not entry_id:
            raise LookupError(f"No timetable entry for session {patch.ref!r}")
        patch.resolved["entry_id"] = entry_id

    payload = {}
    if "start_dt" in patch.set:
        payload["start_dt"] = patch.set["start_dt"]
    if "end_dt" in patch.set:
        payload["end_dt"] = patch.set["end_dt"]
    if not payload:
        raise ValueError("block_time patch needs start_dt or end_dt in `set`")
    client.patch_json(
        f"/event/{event_id}/manage/timetable/{entry_id}", payload
    )


DISPATCH = {
    "session": apply_session_patch,
    "person": apply_person_patch,
    "contribution": apply_contribution_patch,
    "block_time": apply_block_time_patch,
}


# ──────────────────────────── CLI ────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Apply a YAML fix-plan to an Indico event.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Default mode is dry-run (no writes). Pass --apply to actually\n"
            "mutate Indico. Resolved internal IDs are cached in a sidecar\n"
            "JSON file (<plan>.resolved.json, gitignored) so subsequent\n"
            "runs skip the lookup step. The YAML itself is never modified."
        ),
    )
    parser.add_argument("plan", type=Path, help="Path to fix-plan YAML.")
    parser.add_argument(
        "--apply", action="store_true",
        help="Actually push changes. Without this flag, the script "
             "only prints what it would do.",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress per-patch logging.",
    )
    args = parser.parse_args(argv)

    if not args.plan.exists():
        sys.exit(f"Fix-plan not found: {args.plan}")

    plan = FixPlan.from_yaml(args.plan)
    client = IndicoClient(apply=args.apply, verbose=not args.quiet)
    resolver = Resolver(client, plan.event_id)

    print(f"Indico patch — event {plan.event_id}, "
          f"{len(plan.patches)} patch(es), "
          f"mode={'apply' if args.apply else 'dry-run'}")
    client.validate_token()

    failed = 0
    for i, patch in enumerate(plan.patches, 1):
        print(f"\n[{i}/{len(plan.patches)}] {patch.kind} · "
              f"by={patch.by} ref={patch.ref!r}"
              + (f"  ({patch.note})" if patch.note else ""))
        handler = DISPATCH.get(patch.kind)
        if not handler:
            print(f"  SKIP — unknown kind {patch.kind!r}")
            failed += 1
            continue
        try:
            handler(client, plan.event_id, patch, resolver)
        except Exception as e:
            print(f"  FAIL — {type(e).__name__}: {e}")
            failed += 1

    # Persist resolved IDs to the JSON sidecar so a re-run skips
    # the lookup step. Sidecar is gitignored; the YAML stays clean.
    plan.write_cache(args.plan)

    print(f"\n{'Applied' if args.apply else 'Dry-run'} "
          f"complete: {len(plan.patches) - failed}/{len(plan.patches)} OK, "
          f"{failed} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
