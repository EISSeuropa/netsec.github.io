# Indico → site programme integration

NetSec's annual conference programme (ESSC 2026 onwards) is hosted on
the shared EISS Indico instance at <https://indico.eiss-europa.com>.
The website mirrors that data into `data/indico.json` via a daily
sync, and renders it as a live programme grid on `/essc-2026.html`
(and locale variants).

The canonical design rationale lives in the EISS repository:
**[`EISSeuropa.github.io/docs/indico-programme-integration.md`](https://github.com/EISSeuropa/EISSeuropa.github.io/blob/master/docs/indico-programme-integration.md)**.
That document is written to be transferable to any EISS-family
site, including this one. Read it first if you're touching this
pipeline. Local notes below cover the parts where NetSec diverges
from EISS or has its own conventions.

## Data flow

```
indico.eiss-europa.com  ← single Indico, shared with EISS
       │
       ▼   (daily cron, scripts/sync-indico.py via .github/workflows/sync-indico.yml)
data/indico.json        ← NetSec's mirror of programme + event metadata
       │
       ▼   (runtime JS renderer, assets/js/essc-programme.js, shared by all three locale pages)
/essc-2026.html (+ .fr.html + .de.html)
```

## Files

| Path | Purpose |
|---|---|
| `scripts/sync-indico.py` | Hits Indico's anonymous export API, normalises the timetable, writes `data/indico.json`. Strips email hashes; truncates abstracts to ~360 chars. On a substantive change, prints a human-readable markdown change summary to **stdout** (sessions/papers added, removed, retimed, renamed, plus author-byline changes) while operational logs go to stderr. |
| `scripts/test-sync-indico.py` | Standalone runnable. Mocks `requests.get` with a JPEG fixture; asserts on the normalised output. No live network. Covers `summarise_changes()`. |
| `.github/workflows/sync-indico.yml` | Daily cron at 03:45 UTC, manual `workflow_dispatch`. Opens/updates a PR on `indico-sync/auto` (auto-merge, squash) when `data/indico.json` changes substantively; the PR body renders the script's stdout change summary so the maintainer sees precisely what moved. |
| `data/indico.json` | Synced snapshot, year-keyed under `annualConferences`. Schema mirrors EISS's `indico.json` exactly so the renderer is portable. |
| `essc-2026.html` (+ FR + DE) | The pages that consume the data. Each carries a single `<script src>` tag pointing at the shared renderer. |
| `assets/js/essc-programme.js` | The runtime renderer, one file serving all three locale pages (extracted from the per-locale inline copies in #725). Fetches `data/indico.json`, looks up `annualConferences["2026"]`, and renders the grid. Locale-aware chrome labels via a small `I18N` lookup keyed on `document.documentElement.lang`. |

## Where NetSec differs from EISS

| Topic | EISS | NetSec |
|---|---|---|
| Stack | Eleventy + Nunjucks templates (`programme-grid.njk`) | Plain HTML + shared runtime JS renderer in `assets/js/essc-programme.js` ([Wiki decision, 22 May 2026](https://github.com/EISSeuropa/netsec.github.io/wiki/Decisions#2026-05-22--stay-on-plain-html-defer-eleventy-adoption)) |
| Scope | All EISS categories surfaced; livestream session block classified by `INTRO/KEY/RT/CONC` codes | ESSC editions only (category 1). Livestream classification stripped for now; can be re-added when NetSec wants a livestreamed-sessions block |
| Auth | Same shared `INDICO_API_TOKEN` Actions secret | Same shared `INDICO_API_TOKEN` Actions secret. `/export/*` works anonymously, so the token is only needed once a future call site reaches for `/api/*` |
| Render | Build-time via Nunjucks include | Runtime via `fetch()` + DOM. Pagefind doesn't index the rendered grid; full abstracts are one click away on Indico in any case |
| PDF coexistence | `programmePdf: { status: "draft" \| "final" }` flag in `conferences.js` toggles the download card | Not implemented yet. Add when the polished PDF lands post-event (Step 6 in [#127](https://github.com/EISSeuropa/netsec.github.io/issues/127)) |

## Idempotency

`scripts/sync-indico.py` follows the same anti-pattern fix as
`scripts/sync-bios.py` (see PR #117): the substantive-change check
compares the data half of the payload only, excluding `syncedAt`.
A quiet day produces no working-tree change. Three consecutive
runs after the initial write produce zero subsequent `git diff`
output. The workflow's commit step is a no-op when the data is
unchanged.

## Companion files: events.json + calendar.ics

`data/indico.json` is not the only file with ESSC dates and title
on it. `data/events.json` is the hand-curated source for
`calendar.ics` and the home-page "upcoming event" banner; it
historically duplicated the title / start / end / location that
also live in Indico. Hand-curated files drift: a maintainer who
fixed a typo on Indico in March would not remember to also fix
`events.json` in April.

The sync script closes that loop without trampling the curated
copy. Entries in `events.json` can opt into a partial auto-sync
by carrying a single field:

```json
{
  "uid": "european-security-conference-2026@netsec-cost.eu",
  "indicoEventId": 22,
  "summary": "…",
  "start": "…", "end": "…",
  "location": "…", "description": "…", "url": "…",
  ...
}
```

For each entry with `indicoEventId`, `_patch_events_json`
overwrites `summary`, `start`, and `end` from the fresh Indico
payload. Everything else is preserved.

The allow-list is tight on purpose. Specifically, `location` is
**not** auto-synced: events.json carries the full postal address
("Stockholm University, Frescativägen, 114 19 Stockholm, Sweden")
while Indico returns the short venue label ("Stockholm
University"). Overwriting would lose the curated detail. Same
posture for `description`, `url`, `categories`: those are the
banner / calendar copy and stay hand-edited.

After patching, `_regenerate_calendar` invokes
`scripts/build-calendar.py` so the on-disk `calendar.ics` matches
the new `events.json`. The calendar-drift CI check (see
`.github/workflows/calendar-drift.yml`) would otherwise block the
sync PR. The patch step runs **before** the early-return on a
quiet Indico day, so a maintainer who hand-edited `events.json`
with stale values gets caught up on the next nightly sync even if
Indico itself did not change.

### Why not delete `events.json` entirely

A cleaner architecture would derive Indico-tracked entries
directly from `indico.json` at build time and keep
`events-supplemental.json` for items Indico does not host
(deliverable deadlines, training schools on a different platform).
That refactor is tracked in [#170](https://github.com/EISSeuropa/netsec.github.io/issues/170).
For now the link-field approach gets the same correctness with a
~50-line change and zero consumer-side rewrite.

## Privacy posture

The EISS design doc states it cleanly:

> **Indico is the source of truth, the website is two views over
> the same truth, one live, one frozen.**
>
> We treat Indico's public surface as the canonical disclosure
> decision. The website doesn't widen exposure; it reflects what
> Indico already exposes.

Concretely:

- `emailHash` (Indico's Gravatar-lookup field) is dropped at
  normalisation time. Per-element in `scripts/sync-indico.py:_normalise_person`.
- Internal Indico IDs (`db_id`, `person_id`) are not surfaced in
  `data/indico.json`.
- Abstracts are truncated at ~360 chars with a "Read on Indico"
  link.
- Speaker names and affiliations are kept, because they're
  already public on the corresponding Indico event page. A
  speaker who withdraws is removed from Indico, which propagates
  to the site at the next daily sync (24-hour lag at most).

## How to add another event

Today the script is scoped to category 1 (Annual Conferences).
For other NetSec events on the same Indico instance — Summer
School, training schools, MC plenaries — extend
`SYNC_CATEGORY_IDS` in `scripts/sync-indico.py` with the
appropriate category ids and bucket the result accordingly in
`main()`. The data shape and the rendering logic are generic over
event id; the only EISS-specific bit was the base URL, which
stays the same.

## Adding a new annual edition (ESSC 2027 onwards)

1. The Indico event for ESSC 2027 gets created on the EISS Indico
   under category 1. The daily sync picks it up automatically.
2. Copy `essc-2026.html` → `essc-2027.html` (+ `.fr.html` +
   `.de.html`). Three find-and-replaces: the year in the title +
   meta + h1 + canonical URLs + the JSON-LD `Event` schema, the
   year key (`indico.annualConferences['2026']` → `'2027'`), and
   the Indico event-id in the canonical-source links.
3. Add to `sitemap.xml`, `/sitemap.html` (+ FR/DE), and link from
   the home-page Events block.
4. Move the previous year's page into a `past/` subfolder if you
   want to deprioritise it in search; or leave it in place as the
   archival record. The post-event `programmePdf: status: "final"`
   convention from EISS is the long-term fix here.
