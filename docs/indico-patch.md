# Indico patch helper

The write-side companion to `scripts/sync-indico.py`. Designed to
apply small metadata corrections to a live Indico event without
clicking through the UI — useful when the authoritative programme
document drifts from what's on Indico, as happened during ESSC 2026
prep (audit at #208, six items hand-fixed in the UI).

> [!IMPORTANT]
> **Writes are architecturally blocked on the EISS Indico instance
> with current auth.** Phase 1.5 (#210, PRs #212/#213) established
> that Personal Access Tokens cannot reach `/event/<id>/manage/*`
> routes at any scope — the management UI is session-cookie-only.
> See "Findings" below. The tool is in **dry-run-only mode** until
> OAuth-app or service-account auth is set up.
>
> What still works: friendly→internal ID resolution against the read
> API, fix-plan YAML schema as a structured audit-trail, and the
> dry-run output as a deterministic checklist of UI clicks a human
> needs to make. What doesn't: the actual `--apply` step (will hit
> the 403 wall described below).

## Findings (Phase 1.5)

The probe (`scripts/indico_probe.py`, since deleted; results in
PRs #212 and #213) tried every plausible write endpoint shape
against a Personal Access Token with `full:everything` scope plus
every other available scope ticked:

- **Every `/event/<id>/manage/*` route returns 403** with
  `Vary: Cookie`, a fresh `Set-Cookie`, and **no `WWW-Authenticate`
  header**. Indico is ignoring the Bearer header on these routes
  entirely and treating the request as an anonymous browser
  visitor. The route doesn't acknowledge the token enough to even
  declare which scope it would need.
- **`/api/user/` returns 200** — auth works fine on the `/api/*`
  read surface. Probe whoami confirms `admin=true`.
- **OAuth introspect at `/oauth/introspect`** returns 401 — endpoint
  exists but rejects Personal Access Tokens (it's OAuth-app-only).

This pattern matches documented Indico behaviour: the management UI
checks `g.flask_login_user` (session cookie), not `g.current_user`
(any auth source). Personal Access Tokens populate the latter, not
the former, so management routes always see them as anonymous.

## Path forward (separate work, requires admin cooperation)

1. **OAuth 2.0 Client App.** Indico supports OAuth-app registration
   under admin panel; an app with `full:everything` scope can drive
   management routes via the authorization-code or client-credentials
   grant. This is the documented path for third-party programmatic
   writes against Indico. Needs the EISS Indico admin team to
   register an app for our use case.
2. **Service account.** Newer Indico feature (≥ v3.3 IIRC) — a
   non-interactive user with API-driven UI access. Not enabled on
   the current EISS instance per the probe.

When either lands, only the `IndicoClient` methods in
`scripts/indico_patch.py` need updating; the dispatch / resolution
/ CLI layers are already correct.

## Status: Phase 1 (writes blocked)

Two of four endpoint families are validated end-to-end against the
live API:

| Patch kind | Endpoint | Format | Status |
|---|---|---|---|
| `contribution` — move between sessions | `PATCH /event/<eid>/manage/contributions/<cid>` | JSON | ✅ resolution + dispatch validated, dry-run prints correct internal IDs |
| `block_time` — change session entry time | `PATCH /event/<eid>/manage/timetable/<entry>` | JSON | ✅ resolution + dispatch validated |
| `session` — rename / move room | `POST /event/<eid>/manage/sessions/<sid>/modify` | wtforms | ⚠️ resolution works, write path needs live-token validation (smoke-test got HTML back when asking for JSON) |
| `contribution` — rename | `POST /event/<eid>/manage/contributions/<cid>/edit` | wtforms | ⚠️ same caveat |
| `person` — edit affiliation | `PATCH /event/<eid>/manage/persons/<pid>` | JSON | ⚠️ JSON shape correct, but personId resolution needs alt route (the `/conveners` endpoint we tried 404s) |

Phase 1.5 work (#210) will validate the three ⚠️ paths with a real
write token against a benign no-op fix-plan.

## Workflow

```
1. Author fix-plan YAML in data/indico-fix-plans/
2. python3 scripts/indico_patch.py data/indico-fix-plans/YYYY-MM-DD-foo.yaml
   → dry-run, resolves IDs from live read API, prints WOULD-PATCH
3. Eyeball the output, commit the YAML
4. python3 scripts/indico_patch.py data/indico-fix-plans/YYYY-MM-DD-foo.yaml --apply
   → for real
5. The next daily sync-indico.py pulls corrected state into data/indico.json
```

The resolved internal IDs are cached in a sidecar
`fix-plan.yaml.resolved.json` (gitignored) so re-runs skip the lookup
step. The YAML itself stays pristine and comment-friendly.

## Fix-plan schema

See `data/indico-fix-plans/EXAMPLE.yaml` for the canonical reference.
Each patch is a dict with:

- `kind` — one of `session`, `person`, `contribution`, `block_time`
- `by` — how `ref` identifies the target (`friendlyId`, `title_match`, `name`, `id`)
- `ref` — the friendly reference (number or substring)
- `set` — dict of field → new value
- `in_session` — friendly session id (only for `kind: person`, since conveners are session-scoped)
- `note` — optional free-text reason (surfaces in the log)

## Required env

- `INDICO_WRITE_TOKEN` — personal token from Indico, scope
  `full:everything`. Stored as GitHub Actions secret. **Different
  from `INDICO_API_TOKEN`** (read-only, used by daily sync) — keeping
  them separate means the CI service account can never escalate to
  write access.

## Why not a `--write` flag on sync-indico.py

Different blast radius. The daily sync is read-only, idempotent, runs
in CI. The patch helper is destructive, occasional, and run by a
human. Different failure modes too: sync soft-fails (CI continues
with last good data); patch hard-fails on the first error so the
operator can investigate before continuing.

## Predecessors

- #208 — programme print-to-PDF improvements; surfaced just how much
  manual Indico-fixing we were doing during ESSC 2026 prep
- #210 — this work (Phase 1 + 1.5 + 2 milestones)
