---
name: release-cross-check
description: "Release-time six-point cross-check for NetSec: the surfaces to verify before cutting a minor or major release, plus milestone hygiene. Use when cutting a release, running the release script, or asked what to check before a release. Skip for patch releases."
---

# 5. Release-time six-point cross-check (minor / major only)

Every **minor (`X.Y.0` where `Y > prev`) or major (`X.0.0`)
release** should trigger a deliberate check across six surfaces
before `scripts/release.sh` runs. Skip the cross-check on **patch
releases** (`X.Y.Z` where `Z > 0`) — they're scoped to small
fixes and the overhead isn't justified. The release script's
*self-policing tier* mirrors this: patches ship the index only.

For each surface, the question is the same: *"Did anything in
this release change what this surface documents?"* If yes, edit
in the same release. If yes but too big to fit, open a tracking
issue (rule §3) and reference it from the surface itself.

### 1. Roadmap (`/roadmap.html` + FR + DE + `docs/roadmap-2026.md`)

- The `planned → shipped` flip on the public roadmap (`/roadmap.html`
  + FR + DE) is handled automatically by `scripts/release.sh` via
  `scripts/promote-roadmap.py`. That script also bumps the
  *Last updated* / *Dernière mise à jour* / *Zuletzt aktualisiert*
  stamps + the two `<time datetime="…">` attributes in the same
  paragraph. Pre-condition: the v\<version\> card must already
  exist as a `<li class="rm-entry planned">` entry in all three
  locales (or, for a snap patch release, hand-added as already
  shipped). The script fails soft with an exit-2 warning if it
  finds no card to promote.
- **In-flight progress bars are auto-synced.** Each planned /
  in-progress card carries `data-milestone="vX.Y.Z"`, and
  `assets/js/roadmap-progress.js` renders a progress bar from
  `data/roadmap-progress.json` (closed / total issues on the matching
  GitHub milestone, refreshed daily by the `roadmap-refresh.yml`
  workflow, and by `scripts/release.sh` itself before it composes the
  notes). No manual action at release time.
  One thing to remember when **hand-adding a new planned card** (the
  pre-condition above): give it the matching `data-milestone` so its
  bar appears. Shipped cards keep no bar (the renderer skips them), so
  the attribute can be left in place when `promote-roadmap.py` flips
  the card.
- **The next incoming release shows as *In progress* automatically.**
  `roadmap-progress.js` promotes the first still-planned version card
  (event-marker `.rm-milestone` cards excluded) to *In progress* at
  render, with a slow-blinking status dot. This is **presentational
  only**: the static markup stays `class="rm-entry planned"`, so
  `promote-roadmap.py` still finds the card to flip to shipped at
  release. When a release ships, the next card becomes *In progress*
  on its own. So on the live site the next-up card reads *In progress*
  even though the HTML says planned. Do not hand-edit a card to
  `in-progress` to chase this.
- **The card title + body are derived from `CHANGELOG.md` at promote
  time** (issue #233): the script overwrites the planned card's
  `<h3>` with the released section's heading title and its `<p>` with
  the section lede (the first `>` blockquote, or a synthesised
  sentence for index-only patch releases). This replaced an earlier
  git-blame staleness warning that only fired *after* stale planned
  scope had already shipped. EN gets the CHANGELOG copy directly; FR
  + DE get the EN copy plus a `[à traduire]` / `[zu übersetzen]`
  marker on the lede, so `check-i18n-drift.py` flags the card for a
  hand translation (no machine translation, rule §1). Translate the
  FR + DE card bodies in a follow-up before the marker lingers.
- **The script also relocates the card into the quarter matching its
  ship date** (issue #233): if a release shipped earlier or later
  than its planned card's `<ol class="rm-timeline">` quarter, the
  card moves to the right `QN` / `TN` section (inserted after that
  quarter's shipped cards, before its planned ones). So the timeline
  *is* reordered now; just confirm the next planned release below the
  shipped card still reads accurately.
- Anything in *Under watch* (the deferred-items section at the
  foot of the page) ready to promote to a dated entry? (Manual.)
- The autostamp in `docs/roadmap-2026.md` refreshes daily via
  `.github/workflows/roadmap-refresh.yml`, and `scripts/release.sh`
  runs the same script itself before composing the notes, so the
  *N entries in [Unreleased]* line is current at release time
  without manual action and without waiting on the schedule. The prose timeline + the
  *Last revised* line in `docs/roadmap-2026.md` are still
  maintainer-edited.

### 2. Sitemap (`sitemap.xml` + `/sitemap.html` + FR + DE)

- New pages added in this release? Add to `sitemap.xml` and to
  the visual `/sitemap.html` inventory.
- `scripts/inject-seo.py` regenerates `sitemap.xml` — re-run if
  any `<title>` / canonical / hreflang changed.
- The visual sitemap is hand-edited; confirm new pages show up
  in the correct branch (*About & policies* / *Working areas* /
  etc.).

### 3. Translations (FR + DE variants)

- Run `python3 scripts/check-i18n-drift.py` locally. CI catches
  drift on HTML-touching PRs, but a release moment is the right
  place to confirm zero drift before stamping a version.
- Did any EN copy change in this release? FR / DE need manual
  updates (no machine translation — rule §1).
- Ribbon stamps on `*.fr.html` / `*.de.html` carry
  `data-i18n-status="beta"`; if a translation has been
  re-verified against current EN, consider whether the *beta*
  marker still applies.

### 4. Repo docs + documentation PDF

- The maintainer-facing markdown docs under `docs/`
  (`architecture.md`, `design-system.md`, `admin-guide.md`,
  `bios-setup.md`, `i18n.md`, `seo.md`, `search-assessment.md`,
  `launch-qa-2026.md`) — does anything in this release contradict
  what's documented?
- The stakeholder PDF (`docs/pdf/NetSec-website-documentation.pdf`,
  source at `docs/pdf/documentation.html`) carries its own
  version stamp and changelog appendix. **Minor / major releases
  only; patches skip the PDF entirely.** Two-tier cadence within
  the minor / major track:
  - **Cover bump** on every minor / major release. Bump the
    stamp + add a short appendix entry. Acceptable to defer
    section-level catch-up via an explicit "gap" entry (pattern:
    pack v1.7.0 in PR #116; tracking
    [#122](https://github.com/EISSeuropa/netsec.github.io/issues/122)).
  - **Section-level catch-up** is substantive: refresh
    Section 02 site graph + page inventory, refresh
    screenshots via `./docs/pdf/build.sh --shots`. Batch
    when site shape stabilises (typically every 2-3 minor
    releases, not every minor).

### 5. Members' Wiki

- The Wiki at <https://github.com/EISSeuropa/netsec.github.io/wiki>
  holds glossary, FAQ stubs, onboarding for new MC reps, meeting
  notes, decisions log, templates & press-kit page.
- The public FAQ at `/faq.html` and Glossary at `/glossary.html`
  are the source of truth; the Wiki pages of the same name are
  short stubs pointing at them. **Don't drift the stubs** — if
  the public pages change, leave the stubs alone (they only
  link).
- *Decisions log* — did anything in this release warrant a brief
  decision-log entry? (Format choices, structural rewrites,
  branch-protection changes are typical examples.)
- *Templates & press kit* — does the public press kit `/press-kit.html`
  match the Wiki copy-paste boilerplate?

### 6. *What's New* banner currency

- `data/whats-new.json` carries `active: false` by default. If it
  was flipped `true` for a recent campaign (brand launch, ESSC
  live programme going up, founding cohort going up), is that
  campaign **still relevant** to a visitor landing in the next
  4-6 weeks?
- Yes → leave it on. The dismissal `localStorage` key tracks
  per-`version`, so as long as you don't change `version`,
  visitors who dismissed don't re-see it.
- No → flip `active: false` in the same release. The mechanism
  is deliberately manual (CLAUDE.md §14): the friction is the
  gate. Doing this at the release-day cross-check ensures the
  banner doesn't decay into furniture between cycles.
- Activating a new banner is the rarer move (§14 sets the bar
  high: a new visible section, a major feature, a deliverable
  milestone). If this release qualifies, edit `data/whats-new.json`
  now and pick a `version` string (typically `vX.Y.0`). The full
  CTA + headline + locale strings can land in the same release
  commit.

### 7. Milestone hygiene (gate, not a surface)

- Every issue closed by this release carries the matching
  milestone — `gh issue list --milestone vX.Y.Z --state closed`
  should equal the *Fixed/Resolved/Closes* references in the
  changelog index.
- Every issue still open and tagged with this milestone has
  either been ticked off in the release notes or has been moved
  to the next milestone with a one-line reason in the issue
  thread. The release should not ship with its own milestone
  holding open work — see rule §10.

This is a deliberate friction-point: cutting a minor release on
this repo is **slightly more work than running release.sh**, by
design. The release script's confirmation prompt is the last
moment to bail if the cross-check surfaces something that needs
to land in the same release.
