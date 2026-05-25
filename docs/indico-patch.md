# Indico patch helper

The write-side companion to `scripts/sync-indico.py`. Lets us apply
small metadata corrections to a live Indico event without clicking
through the UI — useful when the authoritative programme document
drifts from what's on Indico, as happened during ESSC 2026 prep
(audit at #208, six items hand-fixed in the UI).

## Status: Phase 1

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
