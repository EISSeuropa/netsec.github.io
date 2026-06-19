# Individual member profile pages

**Audience: the maintainer.** Every Directory member has a permanent,
server-rendered page of their own at `/people/<slug>` (plus `.fr` and
`.de`). This note covers what those pages carry, how they are built, and
the two cross-site links they surface. The directory grid at `/people.html`
is a separate, client-rendered surface and is documented in
[`architecture.md`](./architecture.md) under *Feature inventory*.

## Why the pages exist

The directory renders client-side from a single JSON file, so a member has
no URL of their own to put in an email signature, and a shared link unfurls
with the generic site card. The profile pages give each member a permanent
address with their own Open Graph metadata, a `Person` JSON-LD record, and a
listing in `sitemap.xml`, so a search engine indexes them and a shared link
unfurls as that person (#762). They were a static card to begin with. The
enrichment below turned the page into a discovery hub.

## What `scripts/build-profile-pages.py` produces

One static HTML file per member per locale, written to `/people/`. The
chrome (nav, footer, head assets, the manual-translation ribbon on FR/DE) is
lifted verbatim at build time from the matching `people.*.html` shell, so a
profile is visually identical to the directory and the `?v=` asset hashes
always match. The few translatable strings carry `data-i18n` and are
localised on load by the shared `window.netsecT` catalog in `site.js`, the
same mechanism the directory uses.

The page is a hero band over a two-column body. The whole layout is scoped
to `.member-card.is-profile` in `site.css`, so the directory's own cards
(which reuse the same `.member-*` classes) are untouched. It collapses to a
single centred column under 820px.

### Hero band

- **Larger headshot** (104px) beside the identity block.
- Name, role, affiliation with country flag, and working-group pills.
- **Prize pill** when the member has won the European Security Studies Prize
  (see *Cross-site links* below).
- **Actionable mentor / STSM badges.** On the full page the passive
  mentorship and hosting badges become buttons: when the member has
  published an email they are a `mailto:` with a directory-aware subject
  line, turning the label into the "find a mentor / host" action from the
  directory's own framing. Without an email they fall back to the plain
  badge.

### Two-column body

Left (`.profile-main`): the full bio, the specific research-keyword pills,
and the recent-publications list from `data/orcid-works.json`.

Right (`.profile-aside`):

- **The anthology-link slot** (filled at runtime, see below).
- **Research-theme and region chips.** These surface data already computed
  per member in `data/bios.json` (`themes`, `regions`) but never shown on the
  profile before. Each chip deep-links to the directory pre-filtered to that
  facet (`#themes=` / `#regions=`). The chip's slug is produced by
  `area_slug()`, a Python mirror of the directory's `keywordSlug()`, so the
  link lands on the right filter. The test
  `scripts/test-build-profile-pages.py` asserts the two stay in step for the
  live theme + region vocabulary.
- **"Works on similar topics" facepile.** The Glossary field-guide visual
  (`.pf-face`, overlapping circular headshots) reused to show the members who
  work on the closest topics. Ranking is computed at build time by
  `similar_members()`: by shared canonical-keyword count, then shared-theme
  count, then name. A candidate needs at least one shared keyword or theme to
  appear, so a member with no topic data simply shows no suggestions. Each
  face links to that person's own profile, and a trailing link opens the
  directory filtered to the member's themes.
- **Contact icons**, the same set the directory card carries.

## Cross-site links

Both directions of the NetSec ↔ EISS member/author link surface here. The
contract itself is documented in
[`cross-repo-workflow.md`](./cross-repo-workflow.md); this is what the
profile page does with it.

### In the EISS Anthology (NetSec profile → Anthology author)

A small inline script on every profile matches the member against EISS's
published `authors-index.json` by canonical name key, and on a hit injects an
"In the EISS Anthology" link into the sidebar slot. The match runs at runtime
in the browser, the same posture the ESSC programme uses for its
published-paper marker. That choice is deliberate: it keeps the static,
drift-gated profile pages a pure function of local data (no build-time
network fetch that would make the `--check` gate non-deterministic, and no
committed copy of a ~500-row index to drift), and the link never goes stale.
The script's `nk()` is a faithful port of `sync-bios.py::name_key()`, which is
the exact key EISS publishes, so the join is exact. It is a silent no-op on
any fetch or parse failure.

### The prize pill (a curated mirror)

A gold "European Security Studies Prize" pill, matching the EISS Anthology's
`.paper-prize-chip`, on the profile of a directory member who has won it. It
is rendered at build time from `data/prize-winners.json`, keyed by member id.
EISS holds the authoritative roll in its own `paperPrizes.json` keyed by
paper title and does not publish it as a consumable file, so this small list
mirrors only the winners who also appear in the Directory. The pill lives in
`build-profile-pages.py` alone, which the directory-card renderer never
touches, so it shows on the full profile page only and never clutters the
card. The prize name stays in English across locales (a proper noun, carried
with `lang="en"`), matching the EISS chip.

**To add a future laureate:** add a row to `data/prize-winners.json` keyed by
the member's directory id, then rebuild (or let the weekly bios-sync do it).
The schema is in the file's `_documentation` block. If EISS later publishes a
public prizes JSON, the builder could consume that and the local mirror could
be retired.

## Build order and the drift gate

`build-profile-pages.py` owns the `?v=` hashes on `people/*` and must run
**after** `inject-seo.py`, which stamps the top-level pages. Run it last, or
the "Profile pages are current" CI gate fails on `main`:

```bash
python3 scripts/inject-seo.py          # stamps top-level *.html
python3 scripts/build-profile-pages.py # regenerates people/* with matching ?v=
python3 scripts/build-profile-pages.py --check   # the CI gate
```

The weekly `sync-bios.yml` regenerates the pages whenever `bios.json`
changes, and `data-shape-check.yml` runs the `--check` gate on any PR
touching the inputs (`bios.json`, the `people.*.html` shells,
`build-profile-pages.py`, or `data/prize-winners.json`). The directory's own
region filter became URL-addressable (`#regions=`, symmetric to `#themes=`)
as part of this work, so the profile region chips have somewhere to land; the
parse/write lives in `assets/js/people-directory.js`.
