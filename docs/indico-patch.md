# Indico patch helper

The write-side companion to `scripts/sync-indico.py`. Applies small
metadata corrections to a live Indico event without clicking through
the UI — useful when the authoritative programme document drifts
from what's on Indico, as happened during ESSC 2026 prep (audit at
#208, six items hand-fixed in the UI).

> [!IMPORTANT]
> **Precondition: the bot account owning `INDICO_WRITE_TOKEN` must
> have the admin flag set on Indico.** Phase 1.5 (#210, PRs #212-#216)
> established this is the unlock — scope alone (even `full:everything`)
> is insufficient. With admin on, every `/event/<id>/manage/*` route
> returns 200 + JSON; with admin off, every same route returns 403
> with the anonymous-session pattern (`Vary: Cookie` + fresh
> `Set-Cookie` + no `WWW-Authenticate`). See "Findings" below.

## Findings (Phase 1.5)

Three probe iterations narrowed down what unlocks management-route
writes for Bearer-token auth on the EISS Indico instance:

| Probe | Result |
|---|---|
| **Read-only PAT** | All `/manage/*` → 403, anonymous session pattern |
| **PAT with `full:everything` + every scope ticked** | Identical 403 — scope alone isn't enough |
| **Same PAT, bot user now flagged `admin=true`** | All `/manage/*` → **200 OK**, returning JSON form data or HTML pages |

The 403-with-anonymous-session pattern was misleading: it looks like
the route is *ignoring* Bearer auth, but it's actually checking the
token, finding the user lacks management permission, and falling
through to the anonymous-render path (which happens to use cookies).
Admin status on the token-owning user is the gate. Once on, the
Bearer header is honoured normally.

OAuth introspection at `/oauth/introspect` returns 401 — endpoint
exists but rejects Personal Access Tokens. That's expected (it's
OAuth-app-only) and unrelated to our use case.

### Endpoint shape — what writes look like

Allow headers retrieved via OPTIONS (PR #216 probe), after the
admin unlock:

| Route | Methods | Body format |
|---|---|---|
| `/manage/sessions/<sid>/modify` | HEAD, GET, OPTIONS, POST | wtforms |
| `/manage/contributions/<cid>` | OPTIONS, PATCH, DELETE | clean JSON |
| `/manage/contributions/<cid>/edit` | HEAD, GET, OPTIONS, POST | wtforms |

GET against the wtforms routes (with `Accept: application/json`)
returns `{html, js}` — `html` is the rendered form template with
current values baked in. To round-trip a write: parse current
values from `html`, mutate one field, POST back. The clean-JSON
PATCH route on contributions accepts `{session_id, track_id}` per
the agent's source reading.

## Operational setup

1. **Dedicated bot account** on Indico (don't share with a human's
   personal token — keeps audit trail clean and blast radius
   isolated).
2. **Admin flag enabled** on the bot user.
3. **Personal Access Token** under the bot, with `full:everything`
   scope.
4. **GH Actions secret `INDICO_WRITE_TOKEN`** carries the `indp_…`
   value. The Indico admin status is what unlocks writes; the
   secret value rotation policy is independent.

## What's still unknown (resolve on first real apply)

- The empty-PATCH no-op test returned 404 with a structured error
  dict (PR #216 probe). The route accepts PATCH (Allow header
  confirms) and our token is honoured (auth works), so the 404 is
  likely an ID-namespace subtlety — the REST path may want the
  global contribution ID rather than the friendly one used by the
  `/edit` route. We'll iron this out on the first real apply during
  ESSC 2027 prep.
- Whether the wtforms POST endpoints need the full form re-submitted
  or accept a partial; the read path's `{html, js}` JSON shape
  suggests we'll need to parse current values out of the HTML and
  resubmit everything.

## Status: Phase 1 + 1.5 complete

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

## Read-back verification (#323)

A 2xx from Indico does not mean a write took: some management routes
return 200 while no-opping (a contribution "move" that only toggles
schedule state, a wtforms POST rejected for a missing CSRF token). So in
`--apply` mode, after every write the tool reads the authoritative state
back from the `/export/*` JSON, on a cache-busted GET, and confirms the
intended value actually landed. Each patch reports one of:

- **verified** — the read-back shows the intended value. The only OK.
- **mismatch** — the read-back shows a different value, so the write did
  not take (the silent no-op the tool used to hide).
- **unconfirmed** — the field cannot be read back from the export (today:
  session room/venue and event-person fields), so the tool will not claim
  a success it cannot confirm.

The run exits non-zero unless every patch is **verified**. A green "OK"
now means the change is provably live, not merely that an HTTP call
returned 200. The per-kind read-back sources and field mappings live in
the `verify_*` functions in `scripts/indico_patch.py`.

## Pre-flight scope + the real worklist (#323 slice E)

An audit of the committed fix-plans shows the corrections that actually
recur are narrow: the one genuine reconcile plan
(`2026-05-29-essc-programme-reconcile.yaml`) is **four contribution to
session moves and two session renames**, nothing else. Room, venue,
event-person, and block-time edits appear only in the `EXAMPLE` template,
not in real use. So the endpoint reverse-engineering (slices B and C of
#323) should prioritise **contribution to session** and **session
rename** and leave the rest to the read-back verifier or a manual UI fix.

Before any write, the tool now prints a one-line **pre-flight** that
splits the plan's patches into two buckets:

- **auto-confirmable by read-back** — a session or contribution title, a
  contribution's session, a block's start/end. The tool will tell you
  definitively whether these landed.
- **not confirmable via the export** — a session's room/venue, an
  event-person's fields. These have no read-back, so the pre-flight names
  them and the operator should confirm them in the Indico UI rather than
  trust a silent "OK".

The confirmable-field map (`CONFIRMABLE_FIELDS`) mirrors the `verify_*`
coverage, so the pre-flight and the post-write verdict never disagree.

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

## Companion tool: `scripts/indico_clean_duplicate.py`

Different shape of problem, same auth precondition. When we duplicate
ESSC 2026 → ESSC 2027 in Indico (which is the right move — preserves
the abstract review workflow, custom fields, registration form
schema, etc.) the duplicate also copies content: contributions,
session blocks, materials. New submissions then carry over the old
event's friendly-ID counter — your first ESSC 2027 abstract becomes
#342 instead of #1.

The cleanup script lists inherited content via the read API and
selectively `DELETE`s it via the management API. Configuration
stays. Counters effectively reset (modulo the open question of
whether Indico recycles deleted friendly IDs — resolved on first
real use).

```bash
# Dry-run: list what would be deleted from event 23
python3 scripts/indico_clean_duplicate.py --event 23

# Real cleanup of contributions + sessions
python3 scripts/indico_clean_duplicate.py --event 23 --apply \
    --delete contributions --delete sessions
```

**Safety net:** `PROTECTED_EVENTS` in the script hardcodes a list of
event IDs that this script refuses to touch (currently ESSC 2026 =
event 22). Override with `--force` only when you mean it.

**Recommended workflow for ESSC 2027:**

1. Indico UI → Manage Event 22 → Clone → pick the "Configuration
   only" preset (uncheck contributions, sessions, registrations,
   materials). This may already be sufficient.
2. If the duplicate UI still carries content over: run this script
   in dry-run against the new event ID to see what's inherited.
3. Run with `--apply --delete contributions --delete sessions` to
   clear it.
4. Verify the next-contribution friendly ID by adding a test
   contribution via the UI — that tells us whether Indico recycled
   the deleted IDs (next is #1) or continued from the high-water
   mark (next is #342). Document the answer here.
5. Delete the test contribution.

## Predecessors

- #208 — programme print-to-PDF improvements; surfaced just how much
  manual Indico-fixing we were doing during ESSC 2026 prep
- #210 — this work (Phase 1 + 1.5 + 2 milestones)
