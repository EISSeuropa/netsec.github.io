# Indico ↔ NetSec integration plan

How the self-hosted EISS Indico instance
(`indico.eiss-europa.com`, Indico 3.3.12, on a dedicated VPS with full
root access) connects to the NetSec website (`netsec-cost.eu`, this
repo) and the GitHub Actions fleet. Written after a research pass over
the official Indico documentation in June 2026. The goal is to let the
two systems do together what neither can alone, hand routine work to
GitHub Actions or to Claude, and reduce maintainer toil.

The single operator of both systems is the maintainer (Dr Arthur
Laudrain).

---

## The strategic finding

Indico draws a hard line between two surfaces.

- **Reads are documented and stable.** The legacy `/export` HTTP API
  (events, timetable, sessions, contributions) is a documented,
  supported integration point across the 3.x line, with a `ts`-stamped
  `HTTPAPIResult` envelope for freshness. This is what `sync-indico.py`
  already uses.
- **Writes are undocumented and unstable.** The management endpoints
  that `indico_patch.py` reverse-engineers carry an explicit warning in
  Indico's own docs: "We make absolutely no promises of backwards
  compatibility on endpoints that are not part of documented APIs. You
  use them at your own risk." The docs also confirm the exact wall #323
  hit: cookie auth is GET-only and CSRF-gated, so management writes
  cannot go through any documented path.

The consequence, given full root on the VPS: **stop reverse-engineering
HTTP writes from outside, and move the writes server-side into an Indico
plugin.** Plugins are the supported, upgrade-safe extension path. They
hook Indico core through *signals* without patching it, can register
custom CLI commands and custom HTTP endpoints, and run mutations through
Indico's own Python API (transactional, no CSRF, stable across
upgrades). That single capability collapses most of #323 and unlocks the
push pipeline below.

## How the Indico API works (the parts that matter)

- **Auth.** `Authorization: Bearer` with a personal token (`indp_…`).
  The old API-key + HMAC signing is deprecated since Indico 3.0. The
  repo is already on Bearer.
- **Scopes are granular.** `read:everything`, `full:everything`,
  `read:legacy_api` / `write:legacy_api` (restricted to `/export/`),
  `registrants` (the registrant list + check-in, undocumented),
  `read:user`. A read-only sync should run on the smallest scope that
  works, not `full:everything`. Token creation can be restricted to
  admins instance-wide.
- **The `everything` scopes reach any endpoint**, including undocumented
  ones, which is how `indico_patch.py` can call management routes at
  all, but those routes have no stability guarantee.
- **Reads.** `/export/event/<id>.json` and
  `/export/timetable/<id>.json`, detail levels
  `events | contributions | subcontributions | sessions`, multiple
  events per call via dash-separated IDs, `occ` for per-day times.
- **Document generation** (visa letters, certificates) is driven from
  the registration-list UI and has no HTTP API. It runs inside Indico,
  produces per-registrant documents, and can email or publish them to
  registrants directly, so registrant data never has to leave the VPS.
- **Live instance: Indico 3.3.12** (current stable). Has API tokens,
  signals, and the document-templates feature.

## Target architecture

A custom plugin bridges the two systems in both directions:

- **Push.** The plugin subscribes to lifecycle signals and fires a
  GitHub `repository_dispatch` when the EISS programme changes, so the
  site refreshes in about a minute instead of waiting for the daily
  cron.
- **Writes server-side.** A plugin CLI command (or token-guarded
  endpoint) applies corrections through Indico's Python API, replacing
  the fragile external HTTP-write path.
- **Pull stays as the safety net.** The daily Actions sync keeps
  running, now also triggerable on dispatch.
- **Claude** drafts fix-plan PRs on a schedule and runs the plugin CLI
  on demand.

See the architecture diagram in the session that produced this doc, or
rebuild it from this description.

---

## Phased plan and timeline

### Phase 0 — Token + version hygiene (June 2026, ~half a day)

Immediate, pure risk-reduction, no new moving parts.

- Mint a **read-only minimal-scope token** for `sync-indico.py`
  (`read:everything` or `read:legacy_api`), separate from the
  `full:everything` write token. *(Maintainer action in Indico admin.)*
- Restrict API-token creation to admins instance-wide. *(Maintainer
  action.)*
- Pin the validated Indico version (**3.3.12**) in `indico_patch.py`,
  surfaced in its startup banner, so an upgrade that shifts the surface
  is visible. *(Code; completes #323 slice F.)*

### Phase 1 — Push pipeline, read-only (late June, ~1 week, v1.12.0)

The cleanest "impossible in isolation" win, with zero write risk.

- Write a plugin, `netsec-dispatch`, that subscribes to the EISS
  category's lifecycle signals (`times_changed`, `contribution_created`,
  session edits) and `POST`s a GitHub `repository_dispatch`. Store the
  GitHub token in Indico's admin settings, not in code.
- Add `on: repository_dispatch` to `sync-indico.yml`. Keep the daily
  cron as a fallback.
- Result: an Indico edit refreshes the live programme within about a
  minute.

### Phase 2 — Writes via the plugin (July–Aug, v1.13.0, supersedes #323 B/C/D)

The upgrade-safe resolution of #323.

- Add a plugin CLI command, `indico netsec apply-fixplan <yaml>`, that
  performs the corrections through Indico's Python API inside a database
  transaction. No CSRF, no wtforms scraping, no undocumented HTTP.
- Reuse the shipped read-back verification (#323 slice A) as the
  post-condition and the scope pre-flight (slice E) as the pre-check.
- Claude or Actions invoke it over SSH or a token-guarded plugin
  endpoint.
- #323 slices B/C/D (HTTP-write reverse-engineering) are retired in
  favour of this path.

### Phase 3 — Registration + visa letters, server-side (September, gated by #374)

PII stays on the VPS.

- Visa invitation letters via Indico's document-templates feature,
  generated and distributed inside Indico (publish to each registrant's
  page or email as attachments, retrievable as a ZIP).
- A plugin CLI command or scheduled job triggers generation.
- The static site receives only minimised aggregates (participant
  counts, country spread) through an export that drops the personal-data
  section, which Indico models as a structurally separate block.

### Phase 4 — Automation triad + VPS ops (ongoing)

- Scriptable upgrade and nightly `pg_dump` backup via cron, using the
  documented upgrade steps. Note 3.3 requires Python 3.12 (was 3.9), so
  unattended upgrades must handle the interpreter bump, not just `pip`.

## How the three automation modes map

- **GitHub Actions** is the deterministic spine: receives the push,
  runs the read sync, runs the data-shape and render gates, deploys
  Pages. The daily cron remains the fallback.
- **Scheduled Claude agent** is the judgement layer: a weekly
  reconciler reads `/export`, diffs it against the authoritative
  programme, and drafts a fix-plan PR with reasoning. It proposes; it
  does not write to Indico.
- **On-demand handoff**: the maintainer asks, Claude executes
  end-to-end (draft fix-plan, run `apply-fixplan` over SSH, read back,
  report), with no UI clicking.

## GDPR posture

Registrant personal data never flows toward the public repo's CI.
Document generation and distribution happen inside Indico. Any export
that feeds the static site is aggregate-only, built on Indico's
structural separation of the personal-data field section. Tokens that
can read registrants are kept off the public CI; only the read-only
programme token is used by Actions.

## Honest caveats

- A custom plugin must be maintained across Indico upgrades. The docs
  are explicit that non-official plugins can break. The cost is small
  and far below chasing undocumented HTTP endpoints that break the same
  way with none of the benefits.
- There is no off-the-shelf webhook / `repository_dispatch` plugin in
  the official set. Phase 1 is a small write-it-yourself. The official
  `livesync` plugin (MIT, CERN) is the nearest analogue and a useful
  reference.

## Issue map

| Phase | Issue | Milestone |
| --- | --- | --- |
| 0 | folded into this doc + the #323 version pin | v1.12.0 |
| 1 | push pipeline plugin + `repository_dispatch` | v1.12.0 |
| 2 | plugin-CLI write path (supersedes #323 B/C/D) | v1.13.0 |
| 3 | registrant + visa-letter pipeline (with #374) | Backlog |
| 4 | VPS upgrade/backup automation | Backlog |

## Sources

Official Indico documentation (docs.getindico.io, 3.3 stable) and the
`indico/indico` and `indico/indico-plugins` repositories: HTTP API
access and scopes, the events and timetable exporters, the plugin
signals reference and getting-started guide, the official plugin list,
the upgrade procedure, and the document-templates learning docs.
