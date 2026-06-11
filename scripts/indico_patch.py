#!/usr/bin/env python3
"""
Indico patch helper: apply a YAML fix-plan to an Indico event.

PRECONDITION: the Indico user owning INDICO_WRITE_TOKEN must have
the **admin flag set** on the Indico instance. Without it,
management routes (/event/<id>/manage/*) return 403 with the
anonymous-session pattern (Vary: Cookie + fresh Set-Cookie + no
WWW-Authenticate). Phase 1.5 (#210, PRs #212-#216) walked the
permission ladder: read-only token → full:everything + every
scope ticked → still 403 → admin flag on the user → 200 +
JSON form data. The admin precondition is the unlock; scope on
top of it is needed but not sufficient.

Practical setup:
  1. Dedicated bot account on Indico (recommended: not a human's
     personal token — separates audit trail and blast radius).
  2. The bot's user has the admin flag enabled.
  3. A Personal Access Token under that bot account, with
     full:everything scope.
  4. That token goes in GH Actions secret INDICO_WRITE_TOKEN.

Endpoint families confirmed by the write-confirm probe (PR #216),
Allow headers retrieved via OPTIONS:

  | Route                                  | Methods           | Body format |
  | -------------------------------------- | ----------------- | ----------- |
  | /manage/sessions/<sid>/modify          | HEAD GET OPTIONS POST | wtforms |
  | /manage/contributions/<cid>            | OPTIONS PATCH DELETE  | clean JSON |
  | /manage/contributions/<cid>/edit       | HEAD GET OPTIONS POST | wtforms |
  | /manage/persons/<pid>                  | (PATCH expected)      | clean JSON |
  | /manage/timetable/<entry_id>           | (PATCH expected)      | clean JSON |

The wtforms POST endpoints need read-modify-write: GET with
Accept: application/json returns {html, js} where `html` is the
rendered form with current values; we either parse it or use a
companion JSON endpoint (TBD on the first real apply attempt).

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
import time
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

# The Indico version the management endpoints below were last validated
# against. Indico disclaims backwards compatibility for the undocumented
# management routes this tool uses, so a version bump on the live instance
# is exactly when they can shift under us. Re-check the write paths (and
# the read-back field maps) after an upgrade, then bump this. Surfaced in
# the startup banner. See docs/indico-integration.md (Phase 0, #323).
VALIDATED_INDICO_VERSION = "3.3.12"

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

    def get_json(self, path: str, *, params: dict | None = None,
                 fresh: bool = False) -> dict:
        """GET against any Indico endpoint, return parsed JSON.

        Uses Bearer auth on `/api/*` and on `/event/<id>/manage/*`;
        leaves `/export/*` anonymous (it rejects Bearer with 400 on
        some Indico versions).

        `fresh=True` defeats any HTTP caching between a write and the
        read-back that confirms it: no-cache headers plus a unique query
        param so an intermediary cannot serve a stale copy of the state
        we just changed (#323).
        """
        url = path if path.startswith("http") else INDICO_BASE + path
        headers = {"Accept": "application/json"}
        if self.read_token and not path.startswith("/export"):
            headers["Authorization"] = f"Bearer {self.read_token}"
        if fresh:
            headers["Cache-Control"] = "no-cache"
            headers["Pragma"] = "no-cache"
            params = dict(params or {})
            params["_nocache"] = str(time.time_ns())
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


# ─────────────────────── write verification (#323) ───────────────────────
#
# A 2xx from Indico does not mean the write took: some management routes
# return 200 while no-opping (a contribution "move" that only toggles
# schedule state, a wtforms POST rejected for a missing CSRF token). So
# after every apply we read the authoritative state back from the
# `/export/*` JSON the resolver already trusts, on a cache-busted GET, and
# confirm the intended value actually landed. A patch is reported OK only
# when a verifier returns `verified`; a field we cannot read back returns
# `unverifiable`, never a false OK. Verifiers return (status, detail) with
# status in {"verified", "mismatch", "unverifiable"}.

VERIFIED = "verified"
MISMATCH = "mismatch"
UNVERIFIABLE = "unverifiable"


def _iter_timetable_entries(tt: dict):
    """Yield every timetable entry, descending one level into a session's
    own `entries` so contributions scheduled inside a session are seen."""
    for day in tt.values():
        if not isinstance(day, dict):
            continue
        for entry in day.values():
            if not isinstance(entry, dict):
                continue
            yield entry
            for sub in (entry.get("entries") or {}).values():
                if isinstance(sub, dict):
                    yield sub


def _fresh_timetable(client, event_id: int) -> dict:
    doc = client.get_json(f"/export/timetable/{event_id}.json", fresh=True)
    return doc["results"][str(event_id)]


def _fresh_contributions(client, event_id: int) -> list:
    doc = client.get_json(
        f"/export/event/{event_id}.json",
        params={"detail": "contributions"}, fresh=True,
    )
    return doc["results"][0].get("contributions", [])


def verify_session_patch(client, event_id: int, patch: Patch) -> tuple[str, str]:
    sid = patch.resolved.get("session_id")
    if not sid:
        return UNVERIFIABLE, "no resolved session_id to read back"
    entry = next(
        (e for e in _iter_timetable_entries(_fresh_timetable(client, event_id))
         if e.get("entryType") == "Session" and e.get("sessionId") == sid),
        None,
    )
    if entry is None:
        return MISMATCH, f"session {sid} absent from timetable read-back"
    bad, unsure = [], []
    if "title" in patch.set:
        cur = entry.get("title", "")
        if cur != patch.set["title"]:
            bad.append(f"title is {cur!r}, expected {patch.set['title']!r}")
    if "room_name" in patch.set:
        cur = entry.get("room")
        if cur is None:
            unsure.append("room not exposed by the timetable export")
        elif cur != patch.set["room_name"]:
            bad.append(f"room is {cur!r}, expected {patch.set['room_name']!r}")
    if "venue_name" in patch.set:
        cur = entry.get("location")
        if cur is None:
            unsure.append("venue not exposed by the timetable export")
        elif cur != patch.set["venue_name"]:
            bad.append(f"venue is {cur!r}, expected {patch.set['venue_name']!r}")
    if bad:
        return MISMATCH, "; ".join(bad)
    if unsure:
        return UNVERIFIABLE, "; ".join(unsure)
    return VERIFIED, "session fields match the read-back"


def verify_contribution_patch(client, event_id: int, patch: Patch) -> tuple[str, str]:
    cid = patch.resolved.get("contribution_id")
    if not cid:
        return UNVERIFIABLE, "no resolved contribution_id to read back"
    bad, unsure = [], []
    if "session" in patch.set:
        target = patch.resolved.get("target_session_id")
        entry = next(
            (e for e in _iter_timetable_entries(_fresh_timetable(client, event_id))
             if e.get("entryType") == "Contribution"
             and (e.get("contributionId") == cid or e.get("contribution_id") == cid)),
            None,
        )
        if entry is None:
            bad.append(f"contribution {cid} is not scheduled under any session "
                       "(the move did not take)")
        elif entry.get("sessionId") != target:
            bad.append(f"contribution session is {entry.get('sessionId')}, "
                       f"expected {target}")
    if "title" in patch.set:
        contribs = _fresh_contributions(client, event_id)
        match = next(
            (c for c in contribs
             if int(c.get("id") or c.get("db_id") or 0) == int(cid)),
            None,
        )
        if match is None:
            unsure.append(f"contribution {cid} absent from contributions export")
        elif match.get("title", "") != patch.set["title"]:
            bad.append(f"title is {match.get('title')!r}, "
                       f"expected {patch.set['title']!r}")
    if bad:
        return MISMATCH, "; ".join(bad)
    if unsure:
        return UNVERIFIABLE, "; ".join(unsure)
    return VERIFIED, "contribution fields match the read-back"


def _entry_dt(node: dict | None) -> str | None:
    """Normalise an Indico `{date, time, tz}` block to 'YYYY-MM-DD HH:MM'."""
    if not isinstance(node, dict) or "date" not in node or "time" not in node:
        return None
    return f"{node['date']} {str(node['time'])[:5]}"


def _norm_dt(value: str) -> str:
    """Normalise a patch datetime to 'YYYY-MM-DD HH:MM' for comparison,
    tolerating the 'T' separator and trailing seconds."""
    s = str(value).replace("T", " ").strip()
    return s[:16]


def verify_block_time_patch(client, event_id: int, patch: Patch) -> tuple[str, str]:
    sid = patch.resolved.get("session_id")
    entry = None
    for e in _iter_timetable_entries(_fresh_timetable(client, event_id)):
        if e.get("entryType") == "Session" and (
            (sid and e.get("sessionId") == sid)
            or e.get("id") == patch.resolved.get("entry_id")
        ):
            entry = e
            break
    if entry is None:
        return MISMATCH, "session block absent from timetable read-back"
    bad, unsure = [], []
    for key, node_key in (("start_dt", "startDate"), ("end_dt", "endDate")):
        if key in patch.set:
            cur = _entry_dt(entry.get(node_key))
            if cur is None:
                unsure.append(f"{node_key} not exposed by the timetable export")
            elif cur != _norm_dt(patch.set[key]):
                bad.append(f"{key} is {cur!r}, expected {_norm_dt(patch.set[key])!r}")
    if bad:
        return MISMATCH, "; ".join(bad)
    if unsure:
        return UNVERIFIABLE, "; ".join(unsure)
    return VERIFIED, "block time matches the read-back"


def verify_person_patch(client, event_id: int, patch: Patch) -> tuple[str, str]:
    # Event-person fields (name, affiliation, title) are not carried by the
    # public export, so there is no read-back to confirm them against. Honest
    # default: report unverifiable rather than a false OK. A real verifier
    # arrives with the person-write reverse-engineering (#323 slice B).
    return UNVERIFIABLE, ("event-person fields are not exposed by the export "
                          "API; confirm this change in the Indico UI")


VERIFY = {
    "session": verify_session_patch,
    "person": verify_person_patch,
    "contribution": verify_contribution_patch,
    "block_time": verify_block_time_patch,
}


def verify_patch(client, event_id: int, patch: Patch) -> tuple[str, str]:
    """Read the authoritative state back and confirm the patch landed.
    Never trusts the write's HTTP status."""
    verifier = VERIFY.get(patch.kind)
    if not verifier:
        return UNVERIFIABLE, f"no verifier for patch kind {patch.kind!r}"
    try:
        return verifier(client, event_id, patch)
    except Exception as e:  # a failed read-back is itself an unconfirmed write
        return UNVERIFIABLE, f"read-back failed ({type(e).__name__}: {e})"


# ─────────────────────── pre-flight scope report (#323 slice E) ───────────────────────
#
# An audit of data/indico-fix-plans/ shows the real corrections are
# dominated by contribution->session moves and session renames; room,
# venue, person, and block-time edits did not appear in the one genuine
# reconcile plan. And only some fields can be read back from the export to
# confirm a write (slice A): a session or contribution title, a
# contribution's session, a block's start/end. A session's room/venue and
# an event-person's fields are not in the export, so a write to them can
# never be auto-confirmed and is better done in the Indico UI. The
# pre-flight surfaces this before any write, so the operator knows which
# patches the tool can vouch for and which to eyeball by hand.

# Fields whose post-write value the export read-back can confirm, per kind.
# Mirror of the verify_* coverage above.
CONFIRMABLE_FIELDS = {
    "session": {"title"},                  # room_name / venue_name aren't in the export
    "contribution": {"session", "title"},
    "block_time": {"start_dt", "end_dt"},
    "person": set(),                       # event-person fields aren't in the export
}


def unconfirmable_fields(patch: Patch) -> list[str]:
    """The patch's set-fields that the export read-back cannot confirm.
    Empty when every field is auto-confirmable."""
    confirmable = CONFIRMABLE_FIELDS.get(patch.kind, set())
    return sorted(f for f in (patch.set or {}) if f not in confirmable)


def preflight_report(patches: list[Patch]) -> str:
    """A short scope summary printed before any write: how many patches the
    tool can auto-confirm via read-back, and which carry fields the export
    cannot confirm and so must be eyeballed in the Indico UI."""
    confirmable, manual = [], []
    for i, p in enumerate(patches, 1):
        miss = unconfirmable_fields(p)
        (manual if miss else confirmable).append((i, p, miss))
    lines = [f"Pre-flight: {len(patches)} patch(es)",
             f"  {len(confirmable)} auto-confirmable by read-back"]
    if manual:
        lines.append(f"  {len(manual)} with fields the export can't confirm "
                     "(verify these in the Indico UI):")
        for i, p, miss in manual:
            lines.append(f"    [{i}] {p.kind} {p.ref!r} — {', '.join(miss)}")
    return "\n".join(lines)


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
    print(f"  endpoints validated against Indico {VALIDATED_INDICO_VERSION} "
          "— re-check after an upgrade (docs/indico-integration.md).")
    client.validate_token()
    print("\n" + preflight_report(plan.patches))

    failed = 0
    verified = 0
    unconfirmed = 0
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
            continue
        # A write only counts once the change is read back from Indico.
        # Dry-run made no write, so there is nothing to confirm.
        if not args.apply:
            continue
        status, detail = verify_patch(client, plan.event_id, patch)
        if status == VERIFIED:
            verified += 1
            if not args.quiet:
                print(f"  OK (verified) — {detail}")
        elif status == MISMATCH:
            failed += 1
            print(f"  FAIL (write did not take) — {detail}")
        else:
            unconfirmed += 1
            print(f"  UNCONFIRMED (could not read back) — {detail}")

    # Persist resolved IDs to the JSON sidecar so a re-run skips
    # the lookup step. Sidecar is gitignored; the YAML stays clean.
    plan.write_cache(args.plan)

    total = len(plan.patches)
    if args.apply:
        print(f"\nApply complete: {verified} verified, {failed} failed, "
              f"{unconfirmed} unconfirmed (of {total}).")
        # Honest exit: success only when every write was positively read
        # back. An unconfirmed write is not a success, so it fails the run
        # rather than printing a green "OK" the maintainer cannot trust.
        return 0 if (failed == 0 and unconfirmed == 0) else 1

    print(f"\nDry-run complete: {total - failed}/{total} resolved, "
          f"{failed} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
