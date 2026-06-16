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

### Which events count as NetSec's, and which are joint

NetSec shares the EISS Indico, so the sync has to tell three kinds
of event apart and act on only two of them:

- **Standalone NetSec** — events in NetSec's own Indico category,
  `NETSEC_CATEGORY_ID` (#8): training schools, policy workshops, MC
  plenaries, the Summer School.
- **Joint EISS × NetSec** — events that live in an EISS category
  (e.g. Annual Conferences, #1) but carry the `NetSec` keyword. An
  Indico event can hold only one category label, so a conference
  that already carries the "Annual Conference" label opts onto the
  NetSec calendar with the keyword instead. The ESSC is the case in
  point.
- **EISS-only** — everything else; NetSec does not advertise it.

`classify_netsec()` encodes this (category #8 → `standalone`;
`NetSec` keyword elsewhere → `joint`; otherwise excluded), and
`build_netsec_index()` fetches both category #8 and the
Annual-Conference set, keeping only the first two kinds. The
NetSec-category fetch is best-effort: if #8 is briefly unreachable,
joint events are still detected from the Annual-Conference set, so
a co-host badge never silently disappears.

`_patch_events_json` then reconciles `events.json` against that
index:

1. Linked entries (those with `indicoEventId`) get their
   allow-listed fields refreshed as above, **plus** a derived
   `coHost` field (`"joint"` | `"standalone"`). Toggling the
   `NetSec` keyword on Indico therefore flips the card's co-host
   badge on the next sync, no hand-edit required.
2. A NetSec-relevant Indico event with no matching `events.json`
   entry is **appended** as a minimal `autoDiscovered: true` entry
   (EN copy synthesised from the Indico title + URL; the renderers
   fall back to EN for FR/DE until a maintainer fills them in, no
   machine translation, CLAUDE.md §1). It carries `indicoEventId`,
   so subsequent syncs keep its dates in step like any other linked
   entry. Hand-authored events with no `indicoEventId` (e.g. the
   ITC conference, hosted off-Indico) are never touched.

The renderer (`assets/js/home-events.js`) shows a "Joint EISS ×
NetSec" pill only on `coHost: "joint"` cards. Standalone events
get no badge, which is the quiet default on a NetSec-branded site.

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

## How to add a NetSec event on Indico

For **standalone NetSec events** (Summer School, training schools, MC
plenaries, workshops), create the event in Indico under category #8
(the dedicated NetSec category). The nightly sync auto-discovers it
and appends a minimal `autoDiscovered: true` entry to `data/events.json`
(EN title + display date derived from Indico, plus `coHost: "standalone"`).
No code change needed. The maintainer then enriches the entry at leisure:
add FR/DE `cardTitle`/`cardDescription`, richer `description`, `meta`
rows, working-group list, CTA. The `autoDiscovered: true` flag signals
where hand-enrichment is still pending.

For **jointly-run EISS × NetSec events** (the ESSC), create the event
under the relevant EISS category (e.g. Annual Conferences, #1) and add
`NetSec` as a keyword on Indico. The sync picks up the keyword,
classifies the event as `joint`, and sets `coHost: "joint"` on the linked
`events.json` entry. The renderer shows a "Joint EISS × NetSec" badge on
that card.

For **events not hosted on this Indico instance** (e.g. the ITC
conference on a different platform), hand-author an entry in
`data/events.json` as before. These entries carry no `indicoEventId` and
are never touched by the sync.

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
