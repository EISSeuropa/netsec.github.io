# Changelog

All notable changes to this repository are recorded here.

This project follows [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html)
and the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.
What "MAJOR / MINOR / PATCH" means in the context of this repo is
spelt out in the **Versioning** section of [`README.md`](README.md).

The documentation pack (`docs/pdf/NetSec-website-documentation.pdf`)
carries its own version stamp on its cover and its own changelog
appendix; see Appendix C of that PDF for documentation-pack history.

## Release-notes format (applies to `[Unreleased]` + every `[X.Y.Z]` section)

Release notes here follow a **hybrid format**: a short prose lede,
two-to-five **themed sub-sections** carrying the actual narrative,
and a canonical **index of changes** at the bottom grouped by
Keep-a-Changelog categories. The themes are where the writing
happens; the index is the audit trail.

### Shape

```markdown
## [X.Y.Z] · YYYY-MM-DD — <short title>

> One- to three-sentence lede in voice. What is this release
> *about*? Who's it for? Why ship it now?

### <First theme — name it for the thing that changed>

Prose intro (~2-4 sentences). Inline links to docs / issues where
relevant. Add bullets only if the theme has multiple distinct
pieces; otherwise let the prose carry it.

### <Second theme>

Same shape.

### Index of changes

The themed sections above are the story; the index below is the
audit trail. Same content, terser.

#### Added
- (one-line pointer bullets — what, not why)

#### Changed
- (…)

#### Fixed
- (…)
```

### Rules

1. **Each release section has at most one `### Index of changes` block
   and at most one of each `#### Added` / `#### Changed` / `####
   Deprecated` / `#### Removed` / `#### Fixed` / `#### Security`
   sub-heading inside it**, in that order. When a PR adds an entry to
   `[Unreleased]`, the bullet goes inside the *existing* sub-heading
   — never in a new one with the same name below it.

2. **The lede + themes are written when the release is cut**, not
   accumulated bullet-by-bullet through the development cycle. The
   release-cutting moment is where the maintainer reads back through
   `[Unreleased]`, picks the 2-5 most coherent themes, drafts the
   lede, and weaves the bullets into prose sections.

3. **Self-policing tier**:
   - **Patch** (`1.x.y` with no headline) — skip the lede + themes.
     Index only. People reading patch notes care about specifics.
   - **Minor / major** (anything with at least one user-visible new
     feature) — full hybrid: lede + themes + index.
   - If you can't write a meaningful lede about a release, it's a
     patch. The format mirrors the actual significance.

4. **Within a theme**, order content by user impact: headline first,
   smaller polish after. Within the index, same ordering inside each
   `####` block.

5. **The release script (`scripts/release.sh`) extracts the
   `[Unreleased]` body verbatim** into the GitHub Release notes.
   Eyeball the body before confirming the script's prompt.

6. **No hard wraps in prose.** Each prose paragraph, blockquote lede,
   and multi-line bullet must be a single source line — do not break
   mid-sentence with a `\n`. GitHub Releases renders markdown with the
   *break-on-newline* GFM variant; every soft `\n` becomes a `<br>`
   and forces the prose to render narrow on the Releases page (even
   though it looks flowing on the `github.com` file view). One long
   line per paragraph keeps both renderings correct. Code fences,
   headings, blank lines, and the compare-link footer are unaffected.

v1.4.0 was the first release cut under this rule; v1.0.0 → v1.3.0 were
retrofitted to match. `docs/admin-guide.md` repeats this rule for the
maintainer-facing audience.

## [Unreleased]

### Index of changes

#### Added

- **Founding contributors section on `/about.html`** (Item A of the founding-cohort brainstorm). New `<section id="founding">` between *Leadership* and *FAQ* lists the 52 researchers across 21 countries who participated in COST Open Call OC-2024-1-27931 establishing this Action. Sourced from a new [`data/founding-proposers.json`](data/founding-proposers.json) (the JSON also records membership status, MC-availability at founding, and the original source name where the affiliation needed light cleanup). Renders runtime via inline JS; reuses the existing `country-grid` / `mc-collapse` / `mc-stats` patterns from the MC country grid directly above so the founding cohort reads as a parallel "where we came from" narrative to the current MC composition. FR + DE variants land alongside, with locale-aware country names and the corresponding "Soumissionnaire" / "Antragsteller" badge for the Open Call Proposer (Dr Hugo Meijer). Privacy notice on `/privacy.html` (+ FR + DE) gains a new sub-section under §2 documenting the founding-listing as a separate processing activity with Article 6 (1)(f) legitimate-interest basis and a fourteen-day contact-form opt-out. Pairs with the Wiki-side directory-growth tracker (Item B) and a follow-up issue covering Items C (per-bio "founding contributor" badge) and D (founding-cohort stats refresh on press kit + PDF documentation pack). [#242](https://github.com/EISSeuropa/netsec.github.io/pull/242).
- **Three new entries in `data/events.json` from the official Action event ledger**: the *NetSec Policy Workshop* (4 September 2026, format TBC), the *NetSec ITC Conference* (8–11 September 2026, ITC Conference Grant scheme), and the *Inaugural Management Committee plenary* (18 September 2026, the firm date previously listed as "before late September"). Each entry feeds the home-page event banner via `data/events.json` and the public webcal feed via `calendar.ics`; `calendar.ics` rebuilt accordingly (5 events). Public roadmap (`/roadmap.html` + FR + DE) firms up the MC-plenary card date from "Before late September 2026" / "Avant fin septembre 2026" / "Vor Ende September 2026" to **18 September** / **18 septembre** / **18. September**. `docs/roadmap-2026.md` timeline gets matching rows for the Policy workshop and the ITC Conference between the existing Stockholm and MC plenary entries. Past Core Group JourFix dates (January, March, May 2026) and the September Core Group + MC back-to-back are seeded into the Wiki [Meetings index](https://github.com/EISSeuropa/netsec.github.io/wiki/Meetings) (Wiki commit; minutes pending). [#244](https://github.com/EISSeuropa/netsec.github.io/pull/244).
- **Issue-lifecycle automation** ([#238](https://github.com/EISSeuropa/netsec.github.io/issues/238) item C). Three new workflows under `.github/workflows/` bound the open-issue backlog without manual sweeping: `lock-closed-issues.yml` (daily 13:00 UTC) locks issues 14+ days after closure to keep drive-by comments off settled threads, `issue-lifecycle-comment.yml` (on `labeled` event) auto-posts the standard message when a lifecycle label lands (`needs-info`, `duplicate`, `wontfix`, `stale`), and `issue-sweep.yml` (daily 14:00 UTC) labels open issues `stale` after 60 days of inactivity, closes `stale` issues after another 14 days, and closes `needs-info` issues if no human comment arrives within 14 days. Two new labels (`needs-info`, `stale`) join the existing `bug`, `enhancement`, `documentation`, `duplicate`, `wontfix` set. Thresholds tuned softer than the upstream `anthropics/claude-code` defaults (14 / 60 / 14 vs. their 7 / 30 / 7) because our backlog is small and the maintainer reads every notification by hand. Label vocabulary + workflow behaviour codified in [CLAUDE.md §12](CLAUDE.md). [#240](https://github.com/EISSeuropa/netsec.github.io/pull/240).
- **YAML-form GitHub issue templates** ([#238](https://github.com/EISSeuropa/netsec.github.io/issues/238) item B). Three structured forms land under `.github/ISSUE_TEMPLATE/`: `bug_report.yml` (preflight checkboxes + required actual / expected / repro / environment), `enhancement.yml` (mirrors the maintainer's *What's happening / Why it matters / Fix path / Target* shape from CLAUDE.md §3), `documentation.yml` (typed dropdown picking which surface the issue affects: maintainer docs, Wiki, PDF pack, public copy, cross-cutting). A `config.yml` disables blank issues and routes routine questions to the public contact form, the FAQ, the Wiki onboarding page, and the ESSC 2026 member orientation. CLAUDE.md §3 updated to point external contributors at the forms while keeping the four-section maintainer-issue shape as the canonical body content for `gh issue create` paths. [#239](https://github.com/EISSeuropa/netsec.github.io/pull/239).
- **CLAUDE.md §12 *Release-infrastructure hygiene*** (#238). Codifies the three conventions on `.github/` introduced across items A, B, and C of the issue: SHA-pin third-party actions with tag-comment annotation, YAML-form issue templates rather than free-form markdown, and the lifecycle-label vocabulary table (`needs-info`, `stale`, `duplicate`, `wontfix`). Lands together so the next maintainer inherits the conventions rather than rederiving them from upstream.

#### Changed

- **Home-page event cards (`index.html` + FR + DE) refreshed against the official Action event ledger.** Two new cards added between the European Security Conference and the Inaugural MC Plenary: the *NetSec Policy Workshop* (4 September 2026) and the *NetSec ITC Conference* (8–11 September 2026, ITC Conference Grant scheme; travel-grant support linked through to `grants.html`). The Inaugural Management Committee Plenary card firms up from "To be announced" to **18 September 2026** with updated body prose (first formal plenary, MC representatives + Working Group leads, restricted-access notice; the previous *Kick-off Meeting* event-type pill becomes *MC Plenary*). The Summer School card updates the *Application deadline* meta row to *Applications closed on 1 March 2026. Selected participants will be contacted by the scientific coordinators*; the CTA text shortens from *Full details & how to apply* to *Full details* since applications have closed. The event-list now matches the chronological order in `data/events.json` (Summer School → ESSC → Policy Workshop → ITC Conference → MC Plenary). The home-page cards are still hand-coded HTML rather than rendered from `events.json`; deriving them at build time is tracked in [#249](https://github.com/EISSeuropa/netsec.github.io/issues/249) for v1.9.0. [#248](https://github.com/EISSeuropa/netsec.github.io/pull/248).
- **`.github/workflows/*.yml` third-party actions SHA-pinned with tag-comment annotation** ([#238](https://github.com/EISSeuropa/netsec.github.io/issues/238) item A). Every `uses:` line across the eleven touched workflow files now references a commit SHA instead of a floating version tag, with a trailing `# vN (sha-pinned)` comment for human readability. Closes the supply-chain exposure where a maintainer of any third-party action (or an attacker who compromises one) could push a malicious commit under the same tag and run with `contents: write` plus `pull-requests: write` on our next sync. Affected: `actions/checkout@v4`, `actions/configure-pages@v5`, `actions/deploy-pages@v4`, `actions/setup-node@v4`, `actions/setup-python@v5`, `actions/upload-pages-artifact@v3`, `peter-evans/create-pull-request@v7`. Widens the scope of [#151](https://github.com/EISSeuropa/netsec.github.io/issues/151) (which only covered Node 20 removal pinning) to the full third-party surface. Dependabot continues to surface updates via PR, updating the SHA explicitly each time. [#239](https://github.com/EISSeuropa/netsec.github.io/pull/239).
- **`scripts/sync-cost.py` now propagates per-bio WG memberships from cost.eu into `data/bios.json`** ([#236](https://github.com/EISSeuropa/netsec.github.io/issues/236) Gap A). The weekly Monday sync (plus any manual `workflow_dispatch`) parses the Membership table on <https://www.cost.eu/actions/CA24154/>, looks each row up against `bios.json.members[].name` via the existing `norm()` helper, and overwrites the matched entry's `wgs` field with cost.eu's list. Entries not present on cost.eu (community members in the directory who aren't on the MC, or seed entries for leaders not yet on the Membership table) are left untouched. Before this change, the home-page WG chips (driven by `WG_MAP` in `index.html`) and the `/people.html` per-bio chips (driven by the Google Form submitter's answer) could drift indefinitely. cost.eu is now the authoritative source for formal WG membership on both surfaces; the Google Form remains the seed when a bio first lands. Rule documented in [`docs/bios-setup.md`](docs/bios-setup.md). Six new smoke tests in `scripts/test-sync-cost.py` cover the overwrite, idempotency, leave-unmatched-alone, salutation normalisation, missing-file, and leadership-suffix regression cases. Gaps B (statistics + country roster) and C (leadership-label regex holes) deferred to v1.10.0. [#237](https://github.com/EISSeuropa/netsec.github.io/pull/237).
- **Public roadmap (`roadmap.html` + FR + DE) and `docs/roadmap-2026.md` reshuffled around the Stockholm conference cadence.** Five planned releases now interleave with the Action calendar: v1.8.1 (28 May, this release), v1.9.0 (5 June, pre-Stockholm calendar plumbing), v1.10.0 (late July, reactive post-conference patch with sync-cost Gaps B + C, Stockholm recap, FR / DE FAQ + Glossary native-speaker pass), v1.11.0 (mid September, three days ahead of the inaugural MC plenary; Outputs section refresh with D6 cards + `schema.org/ScholarlyArticle`, Phase 2 IA pass, founding-cohort follow-ups [#245](https://github.com/EISSeuropa/netsec.github.io/issues/245), PDF documentation pack section-level catch-up [#229](https://github.com/EISSeuropa/netsec.github.io/issues/229)), v1.12.0 (late December, Year 1 retrospective + D11 + D12 + per-page OG images + FAQ / Glossary print stylesheet + member-photos-out-of-git refactor [#119](https://github.com/EISSeuropa/netsec.github.io/issues/119)). August is a deliberate break. GitHub milestones bumped to match. *Last updated* / *Dernière mise à jour* / *Zuletzt aktualisiert* stamps refreshed to 27 May 2026 across all three locales. [#250](https://github.com/EISSeuropa/netsec.github.io/pull/250).

🤖 _Authored with help from [Claude Code](https://claude.com/claude-code)._

## [1.8.0] · 2026-05-25 — Brand launch, Indico writes, programme PDF, voice sweep

> Pre-Stockholm release. The brand identity finally lands across the site, three Indico operational tools ship to make the ESSC 2027 prep cycle programmatic, the programme page exports a polished self-identifying PDF, and the CLAUDE.md §7 writing-voice rules get applied retroactively across the EN launch-era prose.

### NetSec brand identity

The designer's new four-petal mark and lockup deploy across all 46 HTML pages, replacing the launch-era "NS" gradient-square placeholder. Three surfaces move at once. The header brand link ships two `<img>` lockups keyed off the site's `.dark` class (light and dark variants follow whatever theme the visitor explicitly picked rather than the OS `prefers-color-scheme`, which would desync against the rest of the page), with a 32×32 mark-only swap below 700 px to free up header real estate against the hamburger, language switcher, and theme toggle. The favicon family rasterises from the 595×599 mark into the per-size PNG chain (16 / 32 / 48 for browser tabs, 180 for Apple touch-icon, 192 and 512 for Android home-screen and PWA manifest) plus a multi-resolution `favicon.ico` for legacy clients; a new `manifest.webmanifest` at repo root carries those references along with `theme_color` and `background_color` so the OS shortcut UI matches the brand. A fresh 2400×1260 OG card composes the primary lockup over a soft brand-tinted canvas for LinkedIn, Mastodon, Bluesky, Slack, Twitter, and Facebook link previews; JSON-LD `Organization.logo` points at the new 512×512 mark so the Google Knowledge Panel renders correctly. Two reproducible build scripts ship alongside ([`build-brand-assets.py`](scripts/build-brand-assets.py) and [`update-brand-html.py`](scripts/update-brand-html.py)) so the next designer refresh stays a one-command operation; the rationale and refresh workflow are written up in [`docs/brand-deployment.md`](docs/brand-deployment.md). Out of scope for this cut: SVG masters (designer delivered PNG only, follow-up on [#220](https://github.com/EISSeuropa/netsec.github.io/issues/220)) and the `#003399` to brand `#2B639C` accent migration (the values are close but not identical, and the migration is cross-cutting across `site.css`, JSON-LD `themeColor`, manifest `theme_color`, and several inline `<style>` blocks).

### Indico write-side automation

Two new operational scripts and one permission-model finding land together, the result of four probe rounds against the live EISS Indico instance through PRs #212 to #217. [`scripts/indico_patch.py`](scripts/indico_patch.py) is the write-side companion to the daily `sync-indico.py`: it reads a YAML "fix-plan" describing session renames, room changes, contribution session-moves, affiliation corrections, and block-time edits, resolves friendly Indico IDs to internal database IDs against the live read API, then dispatches the right write call against the management endpoints. Dry-run by default; `--apply` flips to live writes; resolved IDs cached in a gitignored sidecar JSON. [`scripts/indico_clean_duplicate.py`](scripts/indico_clean_duplicate.py) handles the ESSC-N to ESSC-N+1 rollover: Indico's "duplicate event" feature copies the previous year's contributions and sessions along with the configuration we actually want to inherit (review workflow, custom fields, registration form, role assignments), so new submissions continue the old friendly-ID counter and your first ESSC 2027 abstract lands as #342 instead of #1. The clean-duplicate script enumerates inherited content via the read API and selectively `DELETE`s it via the management API, leaving configuration intact, with a hardcoded `PROTECTED_EVENTS` allow-list refusing to touch the live ESSC 2026 (event 22) unless `--force` is passed; dry-run by default, explicit `--delete <category>` required per content type. Smoke-tested against event 22 in dry-run: enumerated 105 contributions correctly via the read API and produced the right DELETE URLs without issuing any. The probe rounds resolved a permission-model misread that had blocked Phase 1: the 403-with-anonymous-session pattern on `/event/<id>/manage/*` that we first read as "Bearer auth ignored" turned out to be Indico's standard auth-then-permission flow, falling through to the anonymous render path when the user lacked management permission. The unlock is the admin flag on the bot account that owns `INDICO_WRITE_TOKEN`, not a scope or auth-mechanism change. That operational precondition is now documented across all three Indico scripts in [`docs/indico-patch.md`](docs/indico-patch.md). Tracks [#210](https://github.com/EISSeuropa/netsec.github.io/issues/210).

### Programme page · self-identifying print-to-PDF

[`/essc-2026.html`](essc-2026.html) (plus FR and DE) now exports a self-identifying PDF when the visitor uses *Print → Save as PDF*. Page 1 carries a full title block (conference name, dates, venue, organisers) so the file makes sense when shared or archived separately from the URL; pages 2 onwards get a thin single-line locale-aware running header and a bottom-right page counter (`Page 2 of 4` / `sur` / `von`). A4 portrait, 20 / 14 / 16 mm margins, tighter cards at 9.5 pt body with 0.6 pt borders and no shadows, contributions list force-open on print so the full paper line-up and abstracts make it onto paper. The export shrank from 17 stretched-card pages to a clean 6 once the leak from the external-link `::after` decoration (`width: 0.85em` icon mask combined with `word-break: break-all` was wrapping URL characters one per line and inflating link headings to 565 px) was reset inside the print rules. Closes [#208](https://github.com/EISSeuropa/netsec.github.io/issues/208).

### Maintainer signals and the launch-prose sweep

Two small but high-leverage pieces of cleanup. The weekly bios-sync and cost-sync workflows open auto-PRs on dedicated branches and auto-merge them when CI is green, which keeps `main` fresh but means churn lands silently. Adding `reviewers: APB-LDN` to both `peter-evans/create-pull-request@v7` invocations turns each diff-producing run into an email and a mobile-push notification on the maintainer's GitHub account, without gating the auto-merge ([#222](https://github.com/EISSeuropa/netsec.github.io/pull/222)). Separately, the CLAUDE.md §7 writing-voice rules (no em dashes, no rule-of-three, no synonym cycling) get applied retroactively across the EN public surface: 30+ HTML pages, the SEO injection script and its regenerated meta and JSON-LD output, the hand-authored ESSC 2026 OG / Twitter / JSON-LD blocks, and the `events.json` calendar copy. UI glyph em dashes (the empty-field "—" in quickfacts cells, the JS no-value defaults) are kept as-is; those are typography, not punctuation. FR and DE prose is left to its translators, who decide their own punctuation conventions ([#223](https://github.com/EISSeuropa/netsec.github.io/pull/223)). The P1 documentation voice-sweep tracks separately for the next cycle.

### Index of changes

#### Added

- **NetSec logo deployment across all 46 HTML pages.** Header lockup (light / dark `<img>` pair keyed off `.dark` with a mark-only swap below 700 px), favicon family (16 / 32 / 48 / 180 / 192 / 512 PNG chain plus multi-resolution `.ico`), `manifest.webmanifest` at repo root, JSON-LD `Organization.logo`, and a fresh 2400×1260 OG social card. Reproducible via [`scripts/build-brand-assets.py`](scripts/build-brand-assets.py) and [`scripts/update-brand-html.py`](scripts/update-brand-html.py); refresh workflow at [`docs/brand-deployment.md`](docs/brand-deployment.md). Closes [#220](https://github.com/EISSeuropa/netsec.github.io/issues/220).
- **[`scripts/indico_patch.py`](scripts/indico_patch.py)**, the write-side companion to `sync-indico.py`. Reads a YAML fix-plan, resolves friendly Indico IDs against the live read API, dispatches session-rename, room-change, contribution-move, affiliation, and block-time edits against the management endpoints. Dry-run by default; `--apply` writes for real. Schema at [`data/indico-fix-plans/EXAMPLE.yaml`](data/indico-fix-plans/EXAMPLE.yaml); design rationale at [`docs/indico-patch.md`](docs/indico-patch.md). Tracks [#210](https://github.com/EISSeuropa/netsec.github.io/issues/210).
- **[`scripts/indico_clean_duplicate.py`](scripts/indico_clean_duplicate.py)**, for the ESSC-N to ESSC-N+1 rollover. Lists inherited content via the read API and `DELETE`s it via the management API, leaving configuration intact. A hardcoded `PROTECTED_EVENTS` allow-list refuses to touch ESSC 2026 (event 22) without `--force`. Smoke-tested against event 22 in dry-run: enumerated 105 contributions correctly and produced the right DELETE URLs without issuing any. Same admin-flag precondition as `indico_patch.py`.
- **Cover masthead, running header, and bottom-right page counter on the programme print-to-PDF** ([`essc-2026.html`](essc-2026.html) plus FR and DE). A4 portrait, 20 / 14 / 16 mm margins, tighter cards at 9.5 pt body, contributions list forced open. Closes [#208](https://github.com/EISSeuropa/netsec.github.io/issues/208).
- **Sync workflow maintainer notifications.** `reviewers: APB-LDN` added to both `bios-sync` and `cost-sync` `peter-evans/create-pull-request@v7` steps; each diff-producing run now emails plus mobile-pushes the maintainer. Auto-merge still fires on green CI, so the line is a change-awareness signal, not a review gate ([#222](https://github.com/EISSeuropa/netsec.github.io/pull/222)).

#### Changed

- **Voice rules applied retroactively to EN public HTML and shared SEO infrastructure** ([#223](https://github.com/EISSeuropa/netsec.github.io/pull/223)). 30+ pages swept: `<title>` em dashes to ` · `, `<meta description>` first em dash to colon and subsequent ones to comma, hand-authored ESSC 2026 OG / Twitter / JSON-LD blocks aligned to the new SEO constants in `scripts/inject-seo.py`. The `inject-seo.py` `BEGIN seo:auto` sentinel keeps its em dash for regex backward-compatibility with already-deployed pages. UI glyph em dashes (empty-field "—" placeholders) preserved. FR / DE prose untouched.
- **`docs/admin-guide.md` and `docs/design-system.md`** refreshed to point at the new brand assets and document the dual-`<img>` dark-mode pattern that the site uses instead of `<picture media="prefers-color-scheme: dark">`.
- **`indico_patch.py` un-parked after Phase 1.5 admin unlock.** The probe-era "writes-blocked" annotations are gone; the script is now the canonical write entrypoint, and the operational precondition (admin flag on the bot account that owns `INDICO_WRITE_TOKEN`) is documented at [`docs/indico-patch.md`](docs/indico-patch.md). Live no-op write validation deferred to the first real ESSC 2027 prep apply, on one open ID-namespace subtlety on contribution REST PATCH.
- **Accent / brand colour migration deferred to a follow-up.** The shift from `#003399` to the brand-pack `#2B639C` is flagged on [#220](https://github.com/EISSeuropa/netsec.github.io/issues/220) but not part of this cut.

#### Fixed

- **Brand-image visibility regression after the first deploy.** All three header `<img>` variants were rendering at once because `assets/css/site.css`'s global `img { display: block }` (specificity 0,0,1) defeats the UA `[hidden] { display: none }` rule, which only wins as user-agent CSS against author CSS of the same specificity. Restored explicit class-level `display: none` on `.brand-logo` and `.brand-mark-only` (specificity 0,1,0 wins over `img`'s 0,0,1) with contextual un-hides via `.dark`-prefixed selectors and the `@media (max-width: 699.98px)` mark-only break. The `hidden` attribute is kept on the default-hidden variants as defence in depth. A `?v=2026-05-25` cache-bust on the site.css link prevents repeat-visit regressions from stale CDN copies.

## [1.7.0] · 2026-05-24 — Directory keyword filter, bios-sync hardening, release automation

> Conference-prep release. The directory gets a research-interest filter chip row so visitors can drill in by topic across the membership; the bios-sync pipeline gets the robustness work to handle the volume the open form is about to deliver; and the release process itself gets the automation that will make every future release lighter than the last. Cut before the European Security Conference on 9–12 June so the new directory shape is what the incoming submissions land against.

### Directory research-interest filter

Three phases shipped end-to-end across the three locales. Phase 1 renders a member's research keywords as outlined chips on the detailed bio card. Phase 2 normalises submissions through a curated [`data/keyword-aliases.json`](data/keyword-aliases.json) so near-duplicates collapse to a single canonical form and acronyms (UN, NATO, EU, UK, US, UNDP, …) survive the sentence-case pass; an aggregate count per canonical keyword falls out as a by-product. Phase 3 surfaces that aggregate as a multi-select toggle chip row above the directory grid: top eight by count, *Show all* expander, OR semantics, URL-hash persistence so filtered views are shareable (`#keywords=ai-governance,foreign-policy-analysis`), and clickable per-bio pills that feed into the same filter. The guided tour and the welcome strip on `/people.html` were updated in EN / FR / DE to introduce the new row.

### Bios-sync robustness, before the firehose

The Google Form is about to open to ~50 incoming submissions. Three improvements harden the pipeline. The merge logic was already truthy-merge per field; that semantic guarantee is now pinned by [a regression test](scripts/test-sync-bios.py) and explained in [`docs/bios-setup.md`](docs/bios-setup.md) so respondents who resubmit sparsely (the documented workaround for the Google Forms file-upload-edit bug, [#183](https://github.com/EISSeuropa/netsec.github.io/issues/183)) don't lose their previously-stored optional links. Defensive `PHOTOS_CHANGED` tracking carries the lesson from sister-project EISSeuropa.github.io [#105+#106](https://github.com/EISSeuropa/EISSeuropa.github.io/pull/106): if `photo_source_sha256` propagation ever regresses, the script screams loudly instead of silently producing an unexplained binary diff. And the auto-PR itself self-describes now: title becomes `data: Dr Alex Petrova joined the network` or `data: 2 new bios + 3 updates`; body opens with a structured *What changed* section listing new joiners with country + affiliation, updated members with the specific fields that moved, and the list of headshot files rewritten on disk.

### Release-time automation

The maintainer-facing release process picks up two pieces of automation that close the *between-releases drift* gap [CLAUDE.md §11](CLAUDE.md) had deliberately left open. `docs/roadmap-2026.md` carries a machine-managed AUTOSTAMP block; a new workflow regenerates it on every push to `main` that touches `CHANGELOG.md`, auto-merging the PR. And `scripts/release.sh` now calls `scripts/promote-roadmap.py` before the release commit, which flips the matching `<li class="rm-entry planned">` card across EN / FR / DE to shipped with locale-correct date formats (`8 September 2026` / `8 septembre 2026` / `8. September 2026`), inserts the localised release-notes link, and bumps the *Last updated* paragraph's two `<time>` attributes plus visible text. On minor / major releases the script also prints a structured PDF-cover reminder pointing at the four version stamps to update. First observation of the workflow firing caught an auto-merge gap on `sync-roadmap.yml` and `sync-bios.yml`; fixed in the same window.

### Index of changes

#### Added

- **Research-interest keyword chips on directory cards** (`/people.html` + FR + DE). Detailed view only. Sentence-case normalisation at render time so submissions like "International Security" and "international security" collapse to a single visual form. A curated acronym set (UN / NATO / EU / UK / US / UNDP / OSCE / ASEAN / IMF / WHO / IAEA / GDPR / IoT / R&D / CFSP / PESCO / BRICS / G7 / G20 / …) keeps those preserved through the normaliser so compound forms like "EU–NATO relations" render correctly rather than mangling to "Eu–nato relations". Distinct styling from the WG chips (subdued outlined pill vs. bright gradient pill) so visitors parse the two layers at a glance. Keywords already entered the directory search vector and now also enter the site-wide Pagefind index via rendered DOM.
- **Phase 2 keyword infrastructure** for the directory. New `data/keyword-aliases.json` carries a curated acronym list + alias map. `scripts/sync-bios.py` resolves each bio's raw `keywords` through the alias map (with sentence-case + acronym preservation as the auto-normaliser), emits a `canonical_keywords` field per bio plus a top-level `keyword_aggregate` count, and logs Levenshtein / substring-close pairs as "possible alias candidate" hints so the maintainer can merge them by hand. The renderer (EN / FR / DE) prefers `canonical_keywords`, falling back to the inline normaliser for older data. Documented in `docs/bios-setup.md`. Phase 3 (dedicated filter chips above the grid) still tracked in [#175](https://github.com/EISSeuropa/netsec.github.io/issues/175).
- **Phase 3 research-interest filter chip row** above the directory (`/people.html` + FR + DE). Reads `keyword_aggregate` from `bios.json`, renders the top eight canonical keywords as toggle pills with submission counts, and expands to the full list on demand. Multi-select with OR semantics: any bio carrying at least one selected interest passes. Per-bio keyword pills are now buttons too: tap one to add it to the active filter and scroll to the result. Selection persists in the URL hash (`#keywords=…`) so filtered views are shareable and survive back-forward navigation. Visible as soon as the directory has any canonical keywords; hidden cleanly otherwise.

#### Changed

- **Directory guided tour + welcome strip** updated to introduce the research-interest filter row. A new tour step lands between Country and Card density, explaining the chip row, multi-select OR semantics, the clickable per-bio pills, and the URL-shareability of a filtered view. The welcome strip gains a matching bullet so the orientation is visible even to visitors who skip the tour. Mirrored to FR + DE. `docs/bios-setup.md` also gets a one-paragraph note that `keyword_aggregate` powers the filter automatically.
- **Bios-sync auto-PRs now self-describe.** Title used to be the static `data: sync member bios from Google Form`; it's now dynamic and reflects what changed: `data: Dr Alex Petrova joined the network`, `data: Bob Smith updated their headshot`, `data: 2 new bios + 3 updates`, etc. The body gains a structured `## What changed` section above the raw run log: per-member bullets list new joiners with country + affiliation, updated members with the specific fields that moved (`bio, LinkedIn` vs `headshot replaced` vs `bio, keywords + headshot`), removals, and the list of headshot files that were rewritten on disk. Driven by a pure `classify_diff` function in `scripts/sync-bios.py` covered by 20 new test assertions.
- **Roadmap-doc autostamp automated.** `docs/roadmap-2026.md` now carries a machine-managed AUTOSTAMP block near the top that records the number of bullets in `CHANGELOG.md` `[Unreleased]` (per category) and the freshness date. A new workflow `.github/workflows/sync-roadmap.yml` regenerates the stamp on every push to `main` touching `CHANGELOG.md` (plus a weekly cron + manual dispatch) and opens an auto-merging PR if the count moved. Closes the gap CLAUDE.md §11 deliberately left open between releases: the staleness signal is automated; humans still write the prose synthesis on release-time §5 sweep. Driven by `scripts/sync-roadmap.py`, pinned by 21 test assertions in `scripts/test-sync-roadmap.py`.
- **Public-roadmap promotion + last-updated stamps automated at release time.** `scripts/release.sh` now calls a new `scripts/promote-roadmap.py` before the release commit. The script finds the `<li class="rm-entry planned">` card matching the release version across `roadmap.html` + FR + DE, flips the status pill to *Shipped* / *Livrée* / *Veröffentlicht*, formats the date per locale convention (`8 September 2026` / `8 septembre 2026` / `8. September 2026`), adds the *Release notes* / *Notes de version* / *Release-Notizen* link, and bumps both `<time datetime="…">` attributes + the visible date text in the *Last updated* paragraph. Non-release planned milestones (Stockholm event, MC plenary) are protected by an `rm-milestone` class guard. Idempotent: re-runs no-op cleanly. Pinned by 28 test assertions in `scripts/test-promote-roadmap.py`. On minor / major releases (X.Y.0 / X.0.0), `release.sh` also prints a structured PDF-cover reminder with the current PDF version, the four stamps to update in `docs/pdf/documentation.html`, the `./docs/pdf/build.sh` rebuild command, and the PDF bump-policy ladder. Patch releases skip the PDF reminder per CLAUDE.md §11.
- **Join-form Google Forms settings flipped** to work around an upstream limitation: file uploads can't be replaced via the response-edit link, so photo updates need a fresh submission. `Limit to 1 response` is now off; `Collect email addresses → Verified` keeps sign-in mandatory and gives the sync a reliable dedup key; `Allow response editing` stays on for non-photo updates. A note on the form's Photo question points respondents at the workaround at the point of confusion. `docs/bios-setup.md` Step 1 + the Editing section rewritten accordingly. Tracked as [#183](https://github.com/EISSeuropa/netsec.github.io/issues/183); will revert if Google ever fixes the upstream bug.
- **Documented the truthy-merge semantics of `scripts/sync-bios.py`** in the bios-setup guide. A respondent submitting a "minimum-viable" second response that fills only the required fields plus the new photo will NOT lose their previously-stored LinkedIn, ORCID, keywords, etc; the sync overwrites only fields that carry a non-empty value in the new submission. WG memberships use union semantics. Form-side disclaimer on the Photo question reworded to make this safety net explicit, so respondents know they don't have to retype every optional link.

## [1.6.1] · 2026-05-24 — Pre-ESSC polish, sync robustness, copy hygiene

### Index of changes

#### Added

- **Inline-expand full abstract on programme contribution cards** (`/essc-2026.html` + FR + DE). `scripts/sync-indico.py` now emits a `fullAbstract` field alongside the truncated teaser; clicking *Read full abstract* swaps the teaser for the full text in place, *Show less* swaps it back. Title still anchors to the Indico contribution page for the canonical record. [#158](https://github.com/EISSeuropa/netsec.github.io/pull/158).
- **Per-session room badge on the programme grid.** Surfaces "D House, Lecture Hall 8" / "Lecture Hall 9" / "Floor 3" on session, contribution, and break cards via a small pin-icon chip. The sync exposes `inheritRoom` and `inheritLoc` flags from Indico for forward use. [#156](https://github.com/EISSeuropa/netsec.github.io/pull/156).
- **Practical information section** on `/essc-2026.html` after the live programme. Two cards: Accommodation (five recommended Stockholm neighbourhoods with their nearest red-line metro stops as chips) and Getting around (T13 context + sl.se link). Quick-facts strip grows from 4 to 5 tiles with a new *Practical info / Stockholm tips ↓* in-page anchor. Mirrored to FR + DE. [#159](https://github.com/EISSeuropa/netsec.github.io/pull/159).
- **`indicoEventId` link field on `data/events.json`.** Entries that opt in get their `summary`, `start`, and `end` overwritten from the fresh Indico payload on every sync, closing the drift between the live programme and the home-page banner / `calendar.ics`. Allow-list is tight; `location`, `description`, `url`, `categories` stay hand-edited. Documented in `docs/indico-sync.md`. Refactor to fully-derived data tracked in [#170](https://github.com/EISSeuropa/netsec.github.io/issues/170). [#171](https://github.com/EISSeuropa/netsec.github.io/pull/171).
- **Per-PR `[Unreleased]` maintenance rule** added to `CLAUDE.md` §4. Every PR that ships a user-visible change adds at least one bullet to `[Unreleased]` in the same PR; reconstructing the batch at release time loses nuance.

#### Changed

- **Parallel programme rows sorted by canonical room name** so the same room consistently lands in the same column across the day. Indico orders parallel panels by convener id; without normalisation, Lecture Hall 8 jumped between left and right between time slots. A small `_canonical_room` helper strips cosmetic building prefixes so "Lecture Hall 8" and "D House, Lecture Hall 8" collapse to the same column key. [#157](https://github.com/EISSeuropa/netsec.github.io/pull/157).
- **`sync-indico.yml` opens a PR via `peter-evans/create-pull-request@v7`** instead of pushing directly to `main`. Branch protection on `main` had started rejecting the direct push with `GH013`. CodeQL still runs on the bot PR (separate workflow), all checks complete, auto-merge fires, daily cadence stays hands-free. PAT not required; `GITHUB_TOKEN` is enough. [#160](https://github.com/EISSeuropa/netsec.github.io/pull/160).
- **Sitewide footer attribution: em-dash → colon.** `COST Action NetSec — Networking European Security Knowledge` becomes `COST Action NetSec: Networking European Security Knowledge` (and locale variants) across 45 page footers (15 EN + 15 FR + 15 DE). Voice-rule cleanup pass; rest of the em-dash audit tracked in [#164](https://github.com/EISSeuropa/netsec.github.io/issues/164). [#166](https://github.com/EISSeuropa/netsec.github.io/pull/166).

#### Fixed

- **Mobile home visual polish.** The floating nav no longer ghosts high-contrast details-strip text through its backdrop-filter on iOS Safari: a fixed top-scrim covers the gap above the bubble and the nav itself takes a near-opaque background on small viewports. Details-strip ↔ event-banner vertical gap tightened from 24 + 24 px to 12 + 8 px at ≤ 720 px. The event-banner status pill is now wrapped in a subtle `currentColor`-tinted chip so the dot reads as part of the same pill rather than a floating speck. [#154](https://github.com/EISSeuropa/netsec.github.io/pull/154).
- **Beta-translation ribbon ghosting on FR / DE pages.** The disclaimer ribbon used a ~5-15% alpha accent gradient over no base, so page content scrolled visibly through. Layered over `var(--glass-bg-strong)` + `backdrop-filter: saturate(180%) blur(20px)` on desktop, plus a near-opaque page-bg tint on mobile (≤ 720 px). [#155](https://github.com/EISSeuropa/netsec.github.io/pull/155).
- **Details-strip separator half-line on mobile home.** The 2 × 2 grid at ≤ 1100 px left a stray border-bottom under the third tile only. Switched the strip rule from `:nth-child(2n) + :last-child` to `:nth-last-child(-n+2)` so the final row sheds the border regardless of total item count. [#163](https://github.com/EISSeuropa/netsec.github.io/pull/163).
- **Break-card title and room badge collision** on `/essc-2026.html`. The pin icon sat right against the last word of the title; italic muted styling made the title vanish next to the badge. Now flex-laid with `gap: 14 px`, title in normal weight + `ink-2` colour, middle-dot `·` separator before the badge. [#168](https://github.com/EISSeuropa/netsec.github.io/pull/168).

🤖 _Authored with help from [Claude Code](https://claude.com/claude-code)._

## [1.6.0] · 2026-05-23 — Live ESSC programme and member previews

> The live ESSC programme release. v1.6.0 turns netsec-cost.eu into the canonical entry point for the European Security Studies Conference: a daily-synced live programme page at `/essc-2026.html`, in-place bio previews for speakers who are NetSec members, a collapsible shipped-history on the public roadmap, and a CSS lint that catches the class-name collisions that bit the directory mid-cycle.

### Live ESSC 2026 programme on netsec-cost.eu

The flagship outreach moment of the year now has its own page on the NetSec site rather than living only on Indico. `scripts/sync-indico.py` runs daily at 03:45 UTC, talks to `indico.eiss-europa.com`'s API, scopes to category 1 (Annual Conferences), and writes the normalised programme to `data/indico.json`. The page at `/essc-2026.html` (+ `.fr.html` + `.de.html`) reads that file at render-time and lays out a programme grid with day-chip navigation, parallel-session rows, contributions, abstracts, livestream badges on plenaries and roundtables, and a pulse-dot beside the page-level "Live programme" cue. Chrome strings (chair / speakers / discussants / day labels / error messages) translate via an inline I18N table; programme content stays in whatever language the submitter wrote it in. The home-page Events block now deep-links to the live page; the sitemap and calendar.ics treat it as the canonical URL for the conference. Schema-compatible with EISS's existing programme generator so a future port to a build-time renderer drops in.

### Member-aware previews on the programme

Hover a speaker name on the programme — if the speaker resolves to a NetSec member through `data/bios.json`, a glass-surfaced preview card opens via the native Popover API. The card carries photo, name, position, affiliation, country with flag, role / working-group chips, three-line bio excerpt, contact-icon row (email, website, ORCID, LinkedIn, X, Bluesky, Mastodon — only the ones the member has filled in), and a "View full profile →" link to `/people.html#<slug>` that scrolls to the matching directory card with a persistent spotlight. Matching uses a JS port of `scripts/sync-bios.py`'s `name_key()`: NFKD-normalise, strip diacritics, drop honorifics, drop apostrophes, drop post-nominals, drop nobiliary particles, key on first + last surviving tokens. Members whose Indico spelling won't match the canonical bios.json name can declare an optional `name_aliases: []` field to bridge the gap. Show / hide model: hover or focus opens; the popover stays open while the cursor is over either anchor or card; leaving both, scrolling the page, clicking outside, or pressing Esc all dismiss. Graceful degrade: feature-detects `HTMLElement.showPopover`; on browsers without it the anchor navigates straight to `/people.html#<slug>`.

### Roadmap UX + CSS hygiene

The Shipped list on `/roadmap.html` now collapses behind a single toggle (default collapsed) so the in-progress and planned items stay above the fold as the shipped history grows. A new CSS class-collision lint (`scripts/check-css-class-collisions.py`) runs on every PR that touches `assets/css/site.css` and flags the kind of mistake that briefly broke `/people.html` mid-cycle — the popover originally used `.member-card` as its container class, which was already the directory's main card class. The lint walks the CSS, finds classes declared as the sole-compound selector of two or more rule blocks more than 200 lines apart, and reports them as cross-feature collisions. Inline `/* css-collision-allow: .my-class */` markers handle legitimate cross-cutting cases.

### Polish

The matcher gained a debug logger that lists unmatched speakers via `console.debug` during render; useful for spotting near-misses (typo, name-order flip, missing alias) without bothering readers. The `/people.html` deep-link spotlight is now persistent instead of auto-fading after 3.5 s — in detailed view, where every card shows its full bio, the old timer often expired before the visitor noticed the landing; the spotlight now clears on user-initiated action (typing in search, clicking a different card, changing a filter) and the hash strips with it. Linked speaker names on the programme now read as tappable at rest (visible accent-coloured dotted underline plus a soft accent tint to the text) so touch users — who never see a `:hover` reveal — can tell at a glance which names lead to a profile. The popover's glass background respects `@supports (backdrop-filter)` with a solid `--bg-1` fallback. The roadmap's chevron animation respects `prefers-reduced-motion`.

### Index of changes

#### Added

- **Live ESSC 2026 programme page** at `/essc-2026.html` (+ FR + DE), sourced from a daily Indico sync (`scripts/sync-indico.py` + `.github/workflows/sync-indico.yml`, runs 03:45 UTC). Schema-compatible with EISS's programme generator. Home-page Events block, sitemap, and `calendar.ics` link to the live page rather than directly to Indico. New `data/indico.json` artefact. New `docs/indico-sync.md` documenting the pipeline.
- **Member preview popover** on the ESSC programme. Tap or hover a member-linked speaker name and a glass card opens with photo, position, affiliation, country, role + WG chips, bio excerpt, contact icons, and a deep-link CTA. Position is computed in JS (viewport-flipped, edge-clamped). Class family is `.essc-member-card*` to avoid colliding with the directory's `.member-card`.
- **Member-aware speaker links** on the programme. Names that match a `bios.json` record become dotted-underlined anchors to `/people.html#<slug>`. JS port of `name_key()` with diacritic / honorific / post-nominal / particle stripping. Optional `name_aliases: []` field on bios records for hard-to-match cases — documented in `docs/bios-setup.md`.
- **Collapsible Shipped list** on `/roadmap.html` (+ FR + DE). One toggle injected per `<ol class="rm-timeline">` that has shipped entries. Locale-aware labels. JS-off graceful degrade leaves entries visible.
- **CSS class-collision lint** (`scripts/check-css-class-collisions.py` + `.github/workflows/css-class-collisions.yml`). Catches same-class declarations >200 source lines apart and orphan BEM children. Inline suppression marker for legit cross-cutting patterns.
- **Particles drop in `name_key()`** (Python + JS). 24 nobiliary / patronymic connectors (de, van, von, da, della, etc.) excluded from the key so "Jéssica da Costa Pereira" matches "Jéssica da Costa".
- **`console.debug` unmatched-speaker log** on the programme render. Filtered to keyable names; surfaces near-misses during preview.
- **Three writing-voice rules** in `CLAUDE.md` §6 + §7: no "source of truth" on public copy, no em dashes, no rule-of-three rhythm, no synonym cycling.

#### Changed

- **`/people.html` deep-link spotlight is now persistent.** The 3.5 s auto-fade is gone; the spotlight clears when the visitor types in search, clicks a different card, focuses a filter, or changes the country select. Visual treatment strengthened: accent-2 outline + 6 px halo + 14 px drop shadow + subtle tinted background. Hash is stripped on dismissal.
- **Linked speaker names on the programme read as tappable at rest.** Resting state: dotted underline at full accent-2 opacity + a 70 / 30 colour mix of accent-2 / `--ink` for the text. Hover / focus brings the text to full accent-2. Replaces the earlier 55 %-transparent dotted underline that was effectively invisible at rest on a touch device.
- **Roadmap retro-truth-up**: v1.4.0 + v1.5.0 marked Shipped with their actual content; the "Official logos and social channels" milestone moved to *Under watch* with a clear external trigger.
- **Sitemap + calendar.ics** updated to reflect the NetSec-hosted ESSC live programme as the canonical URL. ESSC entry in `data/events.json` URL flipped from `indico.eiss-europa.com/event/22/` to `netsec-cost.eu/essc-2026.html`; Indico stays in the calendar `DESCRIPTION` as a registration link.

#### Fixed

- **Directory regression on `/people.html`.** The ESSC popover's CSS used `.member-card` — the directory's own class since launch. The new rules (`position: fixed; width: 360px; box-shadow; overflow: hidden`) cascaded onto every directory card and stacked all 13 of them at the viewport's top-left. The reported symptom — "only Arthur Laudrain shows, his card is half blue" — was 13 cards stacked, with `var(--bg-1)` showing through where the width clamp narrowed them. Renamed the entire popover class family to `.essc-member-card*` across CSS + JS in all three locale files; directory's own rules untouched.
- **Popover light-dismiss and visibility** in early popover drafts. The card was rendering with no background because `var(--surface)` / `var(--border)` / `var(--surface-2)` referenced design tokens that don't exist on this site (it uses `--bg-1` / `--line`). Without visible chrome, clicks that the visitor thought were "outside the card" often landed inside the invisible bounds, and the Popover API correctly didn't dismiss. Fix: use the tokens the site actually defines, add glassmorphism (`backdrop-filter: blur(18px)`), add a scroll-dismiss listener.
- **Pulse-dot vertical alignment** beside the "Live programme" heading on `/essc-2026.html`, pulled rightward from the heading column edge after multiple fine-tunes.
- **Search-overlay landing wrapped highlighted terms in a nested `<mark>`.** Two highlight passes were running on the same hits — Pagefind's `PagefindHighlight` constructor calls `this.highlight()` itself, and our bootstrap then explicitly called `ph.highlight()` a second time. Screen readers announce the inner mark twice (*"STSM, mark, STSM, mark"*); visual rendering is unaffected. Dropped the explicit call, kept the constructor's. Resolves [#118](https://github.com/EISSeuropa/netsec.github.io/issues/118).
- **Skip-link target inconsistency**: the home page's skip-link pointed at `#top` while every other page pointed at `#main`. Mechanically both work — they hit `<main>` — but the inconsistency was confusing. Renamed the home's `<main>` from `id="top"` to `id="main"` across EN / FR / DE and updated the skip-links accordingly. Resolves [#120](https://github.com/EISSeuropa/netsec.github.io/issues/120).

🤖 _Authored with help from [Claude Code](https://claude.com/claude-code)._



## [1.5.0] · 2026-05-22 — Pre-launch polish and accessibility v1.2

> The pre-launch quality pass. v1.5.0 closes the launch-QA loop before the public push — a swarm of polish fixes that surfaced from the user-journey sweep, an accessibility statement bumped to v1.2 with three new audit results, a hybrid release-notes format rolled out across the whole CHANGELOG so future releases read consistently, and the documentation pack caught up to v1.7.0.

### Pre-launch polish

Six user journeys × four-viewport sweep (desktop + iPhone-emulated mobile) ran end-to-end in headless Chromium across the eight most-trafficked pages. Three findings shipped in this release:

- **The FR / DE beta-translation ribbon said "machine translation"; the translations are manual.** Public-facing falsehood about how the site is built, directly contradicting the standing project constraint baked into the architecture doc and the documentation PDF. Corrected across 35 files: FR ribbon copy → *"Traduction manuelle"*, DE ribbon copy → *"Manuell übersetzt"*, EN top-of-file comments → *"manually translated"*, the accessibility statement, and the longer privacy-page ribbon flavour.
- **The mobile hamburger menu's panel was transparent in dark mode** — the floating-header bubble's own `backdrop-filter` and the panel's nested one didn't re-stack reliably, so the hero text bled through behind every nav item. Pinned the drawer to near-opaque (rgba(246,248,252,.97) / rgba(11,18,32,.97)) scoped to the mobile breakpoint, with a stronger elevation shadow.
- **`/people.html#<slug>` deep-links could fail to spotlight + expand the target card on cold load.** The whole hash-handler was wrapped in `requestAnimationFrame`; when RAF deferred (headless Chromium, plausibly real browsers under heavy load), nothing fired. Pulled the spotlight + expand class-manipulations out of RAF — they're layout-safe — and kept only `scrollIntoView` behind it, with a `setTimeout(50)` belt-and-braces fallback.

### Accessibility statement v1.2

Three new audits ran on top of the Phase 2 baseline from the earlier v1.1 statement: a programmatic structural assistive-technology audit of the four most-trafficked pages (landmarks, heading hierarchy, alt-text coverage, accessible names on every interactive element, label association on inputs — all clean); an Open Graph + Twitter Card metadata sweep on home / about / roadmap / press-kit with a render-check of the 2400×1260 shared `og-image.png`; and a dark-mode readability sweep across all sixteen public English pages, with both a per-element programmatic contrast probe and visual review. No new low-contrast findings surfaced beyond the manual-review item already documented on `/accessibility.html`. The statement at `/accessibility.html` (+ FR + DE) is updated to v1.2 with these results and the three corrections above explicitly referenced.

### Release-notes hybrid format

Adopted across the whole CHANGELOG, with the structure-rule documented in three places (the CHANGELOG preamble itself, `docs/admin-guide.md` *Cutting a release*, and the header comment in `scripts/release.sh`). The shape: lede + 2-4 themed `### sub-sections` + a canonical `### Index of changes` block with `#### Added` / `#### Changed` / `#### Deprecated` / `#### Removed` / `#### Fixed` / `#### Security` sub-headings. Self-policing tier: patch releases skip the lede + themes and ship the index only; minor and major releases get the full hybrid. v1.0.0 → v1.4.0 were retrofitted in place and their GitHub Release bodies overwritten to match. A `<!-- TEMPLATE -->` block at the top of `[Unreleased]` shows the shape so the next maintainer doesn't reverse-engineer it. A separate rule was added afterwards explaining why CHANGELOG prose must not be hard-wrapped: GitHub Releases use the *break-on-newline* GFM variant and every soft `\n` becomes a `<br>`, so a hard-wrapped paragraph renders narrow on the Releases page even though it looks flowing on the github.com file view.

### Launch-QA plan + automation

`docs/launch-qa-2026.md` lays out a three-phase audit (automation pre-flight → critical user journeys → a11y + cross-browser + perf) with explicit Go / No-Go criteria, a schedule, a tooling cheatsheet, and a findings log that survives past the launch as the audit trail. Two new scripts back it: `scripts/check-links.sh` (broken-link checker, Python-only, threads with per-host rate-limit-respecting concurrency, validates `people.*.html#<slug>` deep-links against `data/bios.json`, skips known auth-gated hosts) and `scripts/check-a11y.sh` (pa11y scan, aggregates per-page summary into `tmp/a11y-report.md`). New CI workflow `launch-qa-link-check.yml` runs the link checker on every HTML-touching PR and weekly on main. The findings log records the journey results, the I-1 / M-1 / J4-1 fixes, and the four "green" final-pass audits (VoiceOver-substitute, OG metadata, dark-mode sweep, structural AT).

### Index of changes

#### Added

- **Release-notes hybrid format**, applied across the whole CHANGELOG. v1.0.0 → v1.4.0 retrofitted in place and their GitHub Release bodies overwritten to match. Format rule documented in three places (CHANGELOG preamble, `docs/admin-guide.md`, `scripts/release.sh` header). Shape: lede + 2-4 themed `### sub-sections` + canonical `### Index of changes`. Self-policing tier: patch releases skip the lede + themes. Template block at the top of `[Unreleased]`. Companion rule against hard-wrapped prose (GitHub Releases renders soft `\n` as `<br>`).
- **Launch-QA plan + automation** for the late-May 2026 public push. New `docs/launch-qa-2026.md` lays out the three-phase audit with Go / No-Go criteria, schedule, tooling cheatsheet, findings log. Two new scripts (`scripts/check-links.sh`, `scripts/check-a11y.sh`) and a new CI workflow (`launch-qa-link-check.yml`).
- **Documentation pack refreshed to v1.7.0** — cover stamp bumped, changelog appendix entry recording what the pack now reflects (site v1.4.0 → v1.5.0), and a section-level catch-up scheduled for v1.8.0.

#### Changed

- **Accessibility statement bumped to v1.2** on `/accessibility.html` (+ FR + DE). New paragraph in the audit narrative covering three additional final-pass checks (structural AT audit, OG metadata sweep, dark-mode sweep). Three new bullets in the methods list. Version footer updated; *Last assessed* stays at 22 May 2026 (same day).
- **`scripts/check-a11y.sh` switched from `@axe-core/cli` to pa11y.** The original CLI requires a system Chrome that matches a system ChromeDriver — brittle. pa11y wraps the same axe-core engine behind a Puppeteer-bundled headless Chromium that doesn't depend on the system pair. Fixed a heredoc-vs-stdin race in the report generator while in there.

#### Fixed

- **Seven primary-CTA backgrounds failed WCAG AA contrast in dark mode.** The dark-mode `--accent` is `#6ea1ff` (lighter blue, chosen so accent text reads against the dark page). Buttons using `background: var(--accent); color: #fff` directly collapsed to 2.56:1 — below the 4.5:1 AA floor. Affected: `.event-card.featured .event-date`, `.event-subscribe`, `#for-members .members-actions .primary` (home); `.tour-btn-primary`, `.tour-trigger-cta` (people); `.deliverables-roadmap-link-cta` (about); `.rm-feedback-action.is-primary` (roadmap). Fix: pin those CTAs to brand EU-blue `#003399` in dark mode (10.86:1) plus a `#0a4ed0` hover (11:1). Surfaced by Phase 2 of the launch-QA audit.
- **FR / DE beta-translation ribbon misclaimed "machine translation".** The translations are manual. Public-facing falsehood about the build methodology, contradicting the standing project constraint. 35 files corrected: FR copy → "Traduction manuelle", DE copy → "Manuell übersetzt", EN HTML comments → "manually translated", accessibility statement updated.
- **Mobile hamburger menu drawer was transparent in dark mode** — hero text bled through behind nav items because the nested `backdrop-filter` didn't re-stack inside the floating-header bubble. Pinned the drawer to ~97 % opacity (rgba(246,248,252,.97) / rgba(11,18,32,.97)) scoped to `@media (max-width: 980px)`; bumped `box-shadow` so the drawer reads as elevated.
- **`/people.html#<slug>` hash-deep-link spotlight + expand could fail to fire on cold page load.** Handler was wrapped end-to-end in `requestAnimationFrame`; if RAF deferred (headless reliably, real browsers under load plausibly), none of the spotlight / expand / scroll actions ran. Pulled the class-manipulations out of RAF (layout-safe); kept `scrollIntoView` behind RAF with a `setTimeout(50)` fallback. Applied identically across `people.html` / `people.fr.html` / `people.de.html`.
- **Nine broken internal anchors** caught by the new link checker. `faq.{en,fr,de}.html` and `licensing.{en,fr,de}.html` still pointed at `index.html#committee`, `#roadmap`, `#outputs` — sections that the Phase 1 IA pass migrated to dedicated pages. Updated to `about.X.html#leadership`, `roadmap.X.html`, `outputs.X.html`.

## [1.4.0] · 2026-05-22 — Site-wide search, infrastructure and directory improvements

> The largest release since launch. In the two days since v1.0.0 the site doubled in surface area — site-wide search, a Phase-1 IA pass that gives the home page room to breathe, a public roadmap, a proper brand favicon, and the infrastructure work that turns Pagefind from a recurring PR-conflict source into a deploy-time artefact. The shape of the site for the late-May public push.

### Site-wide search

The button you'd expect, where you'd expect it. Magnifying-glass in the nav, Cmd-K or `/` anywhere outside an input. Modal overlay, results scoped to the visitor's locale automatically (Pagefind per- language shards key off `<html lang>`), per-section deep-link anchors so long pages like FAQ and Glossary jump straight to the matched section. Snippets highlight with the EU-yellow `<mark>` from the press kit, on-page highlighting on landing too. Privacy posture preserved: index served from `/pagefind/` on `netsec-cost.eu`, queries never leave the visitor's browser, no third-party calls. Lazy-loaded on first overlay open. Design history in `docs/search-assessment.md`.

**Directory bios are searchable.** A name search returns a rich card with the member's photo, country flag, role, and WG chips — rather than the plain page-text card used elsewhere. Member data is rendered as Pagefind index stubs under `search/bios/<lang>/<slug>.html` at build time, in all three locales, so a French visitor searching *"Laudrain"* hits the French shard too.

### Phase 1 information-architecture pass

The home page had ten sections after v1.0; the floating header ran at ten nav items. Every new release added more. Time to redistribute.

- **New `/about.html`** consolidates the Action narrative, the deliverables Gantt, the leadership grids, and FAQ + Glossary teasers. The home-page *About* anchor still carries the short intro; the dedicated page is the full story.
- **New `/outputs.html` and `/news.html`** stub pages — both ready to receive content as it accrues.
- **Header nav reduced from 10 to 8 items.** *Committee* and *Roadmap* and *Outputs* dropped as standalone nav entries; *About* points to the new `/about.html`; *Outputs* renamed to *Publications*.
- **Home page slimmed by ~25%.** EN / FR / DE go from ~990 / ~905 / ~905 lines down to ~745 / ~660 / ~660. Phase 2 of the IA pass (audience tracks, mobile patterns, deeper UX work) runs Jul–Aug 2026 and ships in v1.7.0; this round is the structural redistribution that needed to land before official logos in v1.5.

### Public roadmap

`/roadmap.html` (+ FR + DE). Visual, audience-facing companion to the internal `docs/roadmap-2026.md`. Vertical timeline grouped by quarter; four-pill status legend (*Shipped* — green, *In progress* — blue, *Planned* — purple, *Under watch* — amber); twelve dated entries interleave shipped releases (v1.0 → v1.3), the in-progress v1.4, planned v1.5 → v1.8, and the Action's own milestones (Stockholm Conference + Summer School, inaugural MC plenary, Year-1 anniversary). *Under watch* section at the foot lists deferred items with explicit triggers ("kick off the sticky-side-panel work if membership crosses ~150 OR an MC member reports friction"). A "Help shape this" card frames the roadmap as participatory and points readers at GitHub Issues + Discussions. Manual translations only — no machine translation.

Signposted in two places: a 4th card in the home-page *Find out more* grid, and an accent callout at the foot of the Deliverables section on `/about.html`.

### Infrastructure, quietly improved

- **Pagefind built at deploy time, not committed to main.** Two parallel PRs that both touched HTML used to conflict on the index manifest (content-hashed shard filenames diverging). The new Pages-deploy workflow rebuilds the index on every push and deploys via the artifact + `actions/deploy-pages` flow; `/pagefind/` is now gitignored. PR conflicts on the index are structurally gone.
- **iCalendar feed at `/calendar.ics`** + *Subscribe to NetSec events* CTA on the home page. Single-source-of-truth pipeline: generated from `data/events.json` by `scripts/build-calendar.py`; CI fails any PR where the JSON and the generated ICS disagree.
- **Brand favicon replacing the Mobirise placeholder.** New SVG favicon — rounded square in the EU-blue → Apple-blue gradient with "NS" in white, matching the in-header brand mark. Visitors no longer see a pink phone-with-sun icon in their browser tab.
- **Persistent lint against trailing arrows on external links** (`scripts/check-external-link-arrows.py` + CI workflow). The site CSS auto-injects an external-link icon after every `<a target="_blank">`, so a manually-typed arrow on top renders a double affordance — the lint catches it before merge.
- **Release-cutting now requires a short title** as a positional argument to `scripts/release.sh`. Past titles retitled to match the convention.

### Directory polish

The compact-view cards on `/people.html` got two improvements that make the underlying click-to-expand pattern discoverable. First, a small circular chevron at the bottom-right of every compact card — ▼ when collapsed, rotates to ▲ when expanded. Hidden in detailed view. Touch-friendly. Second, **search-result clicks on a directory entry now visually confirm the landing** with a 2 px accent-blue outline and a soft glow that auto-fades after 3.5 s.

### Polish + bug fixes

The full list is in the index below. Two patterns worth flagging:

- **Search overlay had several issues** that hadn't surfaced under light testing — backend returning *"SEARCH IS UNAVAILABLE"* (a stray filter argument), the modal sitting on top of the navigated page so users couldn't tell their click had worked, the Cmd-K shortcut breaking on non-QWERTY layouts. All fixed before the public push.
- **Mobile + IA aftermath.** The IA pass moved sections off the home page but a few stale references followed — a *Meet the team* link to a defunct anchor, the Gantt's responsive grid collapsing oddly at narrow widths, the mc-subhead dividers wrapping onto two lines. Caught during the launch-QA pass and fixed in the same window.

### Index of changes

#### Added

- Site-wide search via Pagefind (modal overlay, Cmd/Ctrl-K, `/`, per-locale shards, deep-link anchors, EU-yellow `<mark>` highlights, lazy-loaded, privacy-preserving).
- Directory bios searchable, rich result card with photo + flag + role + WG chips.
- `/about.html` (+ FR + DE) consolidating the Action narrative, deliverables Gantt, leadership grids, FAQ + Glossary teasers, EISS placeholder.
- `/outputs.html` and `/news.html` (+ FR + DE) stub pages.
- `/roadmap.html` (+ FR + DE) public roadmap with visual timeline, four-status legend, "Help shape this" community feedback card.
- Roadmap signposted on the home-page *Find out more* grid (4th card) and the About-page Deliverables section (accent callout).
- iCalendar feed at `/calendar.ics` + *Subscribe to NetSec events* CTA + single-source-of-truth pipeline from `data/events.json` with CI drift check.
- Brand favicon (`assets/images/favicon.svg`) replacing the Mobirise pink-phone-with-sun placeholder. 256 × 256 PNG fallback re-rendered. 43 page-locales updated.
- FAQ + Glossary teaser sections on the About page (5 FAQs + 8 glossary terms each, deep-linked to their full pages).
- Expand / collapse chevron on directory compact cards.
- `scripts/build-search.sh` + `.github/workflows/search-drift.yml`. Pagefind pinned to 1.5.2.
- `scripts/check-external-link-arrows.py` + CI workflow.
- Wiki link in every page footer (EN / FR / DE).
- Sync convention noted in `docs/roadmap-2026.md` + *Last reviewed* line on each public roadmap.

#### Changed

- Header IA: nav reduced from 10 to 8 items (canonical order *News · About · Working Groups · Network · Events · Grants · Publications · Contact*).
- Home page slimmed by ~25% — Committee + Roadmap + Outputs migrated to dedicated pages.
- `/sitemap.html` (+ FR + DE) rebuilt to match the new IA.
- Pagefind index moved from committed-to-main to built-at-deploy-time. `/pagefind/` now gitignored. Pages source flipped to *GitHub Actions* deploy.
- `search-drift.yml` simplified to a build-sanity check.
- `scripts/release.sh` now requires a short title as a second positional argument. Historical release entries retitled.

#### Fixed

- Search backend now works (was returning *"SEARCH IS UNAVAILABLE"* due to a bogus `filters` argument).
- Search results deep-link to the matched item and highlight the term on landing; the overlay closes on result-link click so the navigation is visible.
- Member-name search no longer false-positives on the home page (MC-by-country grid wrapped with `data-pagefind-ignore`).
- `Cmd-K` / `Ctrl-K` hardened — checks `e.code === 'KeyK'` so non-QWERTY layouts still work; listener moved from `document` to `window`.
- Search trigger no longer overflows the floating header on the home page (⌘K badge hidden; shortcut still discoverable via title + overlay).
- Windows / Linux users see *Ctrl K* in the search-button tooltip rather than the generic *Cmd/Ctrl-K*; adds `aria-keyshortcuts`.
- Directory bio cards now show the full biography text (dropped the rAF wrapper around the *Show more* detection; ResizeObserver belt-and-braces).
- Search-result clicks on a directory entry visually confirm the landing (accent-blue spotlight + auto-fade).
- Public-roadmap milestone cards no longer render as saturated-blue panels with unreadable text (class-name collision with the Gantt-pill `.milestone` rule — renamed to `.rm-milestone`).
- Status pill on roadmap timeline centred on the marker dot (`top` 16 → 19 px / 18 → 21 px).
- Beta-translation ribbon now present on all 14 recently-added FR/DE pages (`data-i18n-status="beta"` + the ribbon div).
- Beta-translation ribbon no longer overlaps the floating header on mobile (CSS offsets derived from a JS-measured `--ribbon-h`).
- *Meet the team* link on the home-page news block points at the new About page anchor.
- Gantt chart no longer misaligns on mobile (year row uses `repeat(4, minmax(184px, 1fr))`).
- `.mc-subhead` section dividers no longer wrap onto two lines on narrow screens (flexbox + `flex: 0 0 48px` on the pseudo-elements).
- Header crowding on the home page addressed by hiding the *NetSec* wordmark in the floating bubble.
- Events section: double-icon on external-link CTAs removed (hardcoded right-arrow stripped; auto-icon remains).
- Subscribe-to-events button now prominent and centred (was a small bordered chip in the margin).
- `.gitignore` now excludes `.DS_Store` site-wide.

## [1.3.0] · 2026-05-21 — Introducing FAQ and Glossary pages

> The reference content lived on the members' Wiki, which means it lived on GitHub — and academics, journalists, and prospective members don't naturally browse to GitHub. v1.3.0 brings the FAQ and the Glossary to the public site so the people who actually need them can find them.

### Reference content goes public

**Public FAQ at `/faq.html`** (plus FR + DE) — 21 Q&As across six themed sections (*About the Action* / *Joining & participating* / *Grants & funding* / *Meetings & reimbursement* / *Website & directory* / *For NetSec members*), with a jump-to TOC and per- question deep-link anchors. The Wiki FAQ page now stubs to this URL.

**Public Glossary at `/glossary.html`** (plus FR + DE) — ~35 COST and NetSec terms grouped into five sections (*COST framework* / *NetSec structure* / *People* / *Grants & meetings* / *Documents & outputs*), with per-term anchors. Same migration rationale.

The source of truth is now in one place — the public pages — so the FAQ and Glossary can't drift between two surfaces.

### Discovery surfaces on the home page

Reference content that nobody can find isn't reference content. Two new affordances make the FAQ and Glossary visible from the front door:

- A **four-card *Find out more* grid** at the end of the About section, pointing at FAQ / Glossary / Press kit / Members' Wiki. Keeps the header at ten items while surfacing the reference pages at a glance.
- A **"For NetSec members" strip** between Outputs and Contact, with two CTAs — *Open the Wiki* and *e-COST portal*. MC reps and WG participants don't drift to GitHub on their own; the strip leads them there.

Both localised in EN / FR / DE.

### External-link icon polish

The auto-injecting external-link icon introduced in v1.2.0 had four related regressions, all rooted in CSS specificity:

- **Specificity bug**: the global selector was `(0,0,2,2)`; every exclusion (`.cost-mark::after`, `.socials a::after`, etc.) was weaker and silently lost. The icon appeared on the COST mark, the EU mark, the GitHub footer link, the language switcher, the social-icon row on member cards, and stacked on top of inline arrows inside *Apply on e-COST* buttons. Fix: wrapped the global selector in `:where()` so it contributes 0 to specificity; every exclusion wins naturally.
- **Flex-shrink collapse**: inside flex containers the `::after` became a flex item with default `flex-shrink:1` and collapsed to width 0 — *Resources & reference documents* cards on the Grants page appeared to have no external-link indicator. Fix: `flex:none` on the pseudo-element.
- **Double-arrow on news cards**: two news cards carried both a hardcoded `→` and the auto-injected icon. The hardcoded arrow was dropped; the auto-icon remains.

### Index of changes

#### Added

- Public FAQ at `/faq.html` (+ FR + DE) — 21 Q&As, six themed sections, jump-to TOC, per-question deep-link anchors.
- Public Glossary at `/glossary.html` (+ FR + DE) — ~35 COST + NetSec terms, five sections, per-term anchors.
- *Find out more* grid at the end of the home-page About section (FAQ / Glossary / Press kit / Members' Wiki).
- *For NetSec members* strip between Outputs and Contact, with *Open the Wiki* + *e-COST portal* CTAs.
- FAQ + Glossary links in every page's footer (24 files).
- Sitemap entries for the two new pages in `sitemap.xml` + the in-page `/sitemap.html` *About & policies* branch.
- SEO metadata for the six new pages via `scripts/inject-seo.py`.
- i18n drift tracking for `faq.html` and `glossary.html`.

#### Changed

- Wiki `FAQ.md` and `Glossary.md` reduced to short stubs pointing at the public pages — single source of truth.

#### Fixed

- External-link icon specificity bug (global selector wrapped in `:where()`).
- External-link icon flex-shrink collapse (`flex:none` on the pseudo-element).
- Double-arrow on news cards (hardcoded `→` stripped from external-link cards).

## [1.2.0] · 2026-05-21 — Press kit, directory tour, compact view

> Three coordinated threads. The press kit goes live so anyone writing about NetSec — journalist, partner, MC member — has one URL to send. The directory gets a guided tour, a compact view, and click-to-expand cards, lowering the friction for first-time visitors. And the repository's branch + tag protection lands, so the release tags become immutable once published.

### Public press kit

**`/press-kit.html`** (+ FR + DE). One canonical URL for outreach. Includes the **promotional A3 poster** (with print + card-size downloads), the NetSec / COST / EU emblems with pairing rules, the colour palette and typography reference, the funding-statement boilerplate in three lengths (full, short, one-line credit), suggested CC BY 4.0 attribution wording, and explicit do / don't rules. Linked from every page's footer between *Licensing* and *Site map*.

The poster source is version-controlled (HTML-to-raster build), so future content changes don't require a manual reflow. A card-size variant ships as the README banner and as Appendix C of the documentation PDF; a member-facing copy-paste page lives at the **Members' Wiki *Templates & press kit*** entry.

### Directory: tour, compact view, click-to-expand

The first-visit directory experience used to assume the visitor knew it was open (not MC-only), knew filters existed, knew where the join form was. The directory now teaches that itself:

- **First-visit orientation strip** above the toolbar — three lines introducing the directory and its affordances. Dismissible; returning visitors never see it.
- **Six-step guided tour** anchored to: search box → filter chips → country dropdown → view-mode toggle → `+` quick-join button → join card. Two entry points (the welcome strip's *Take the tour* button and a persistent `?` button in the toolbar). Keyboard navigable; focus trap; reduced-motion aware. Engine generalised as `window.netsecTour({steps, labels, onComplete})` for reuse.
- **Compact view** — a two-button toggle next to the country filter switches between detailed (photo + bio + contact icons) and compact (initials/photo + name + affiliation + WG chips, three across on desktop). Preference persists per visitor.
- **Click-to-expand on compact cards** — clicking a compact card flips it to its detailed form in place, while every other card on the grid stays compact. Keyboard-focusable, Enter / Space triggers expansion, Esc collapses. The expanded card's slug mirrors to `location.hash` so the state is shareable: `/people.html#eugenio-sanchez` auto-expands that card on load.
- **`+` quick-join button** in the toolbar (bright accent CTA next to the muted `?` tour-trigger), smooth-scrolls to the join card at the foot of the page.

All localised in EN / FR / DE.

### Branch + tag protection

Two GitHub rulesets added to the repo, both visible at the [Settings → Rules → Rulesets page](https://github.com/EISSeuropa/netsec.github.io/settings/rules):

- **`protect-main`** — restricts deletions and force-pushes, requires linear history, requires a pull request before merging, requires all four CodeQL status checks to pass, requires conversation resolution, restricts merge methods to squash. Bypass: the *Repository Admin* role (so `scripts/release.sh` can push the changelog-promotion commit directly).
- **`protect-release-tags`** — restricts deletions, updates, and non-fast-forward updates on tags matching `v*`. **No bypass for anyone** — once a release tag is published, it is immutable.

The release script's docstring is updated to record the consequence: the release-cutter needs the repo `Admin` role (not `Maintain`).

### Grants page transparency

The Grants page used to imply a simple application flow. The reality on e-COST is more nuanced. Updated copy spells it out:

- Applications go through the general e-COST portal (no NetSec-specific form).
- The portal **filters by applicant profile** — ITC schemes are visible only to ITC affiliates; YRIG is visible only to under-40s. A member may not see every scheme listed on the page.
- Only the five schemes on the page are in NetSec's WBP; applications for anything else **will be rejected** by the Grant Awarding Coordinator.

The YRIG and ITC cards gain visibility captions; the Wiki FAQ gains two matching entries; the architecture doc lists the portal model.

### Index of changes

#### Added

- Public press-kit page at `/press-kit.html` (+ FR + DE) with logos, palette, funding-statement boilerplate (3 lengths), CC BY 4.0 attribution wording, do/don't rules.
- A3 promotional poster — HTML source, A3 raster (2480 × 3508 px), card-size variant (800 × 1131), Appendix C of the docs PDF.
- README banner showing the card-size poster.
- Members' Wiki *Templates & press kit* page (copy-paste boilerplate for members).
- Directory first-visit welcome strip.
- Directory guided six-step tour (anchored coachmarks, keyboard navigable, reduced-motion aware, engine reusable as `window.netsecTour(...)`).
- Directory compact view (segmented toggle, three-across grid, density preference persisted).
- Click-to-expand on compact directory cards; deep-link auto-expand on `#<slug>` hash.
- `+` quick-join button in the directory toolbar.

#### Changed

- Grants page now explicitly frames the e-COST portal model (profile-based filtering, NetSec WBP scope, rejection conditions).
- Documentation PDF: new Section 07 (Branch and tag protection); Section 06 (Admin guide) handover checklist rewritten; appendices C/D swapped so the PDF lands on the changelog; PDF title carries its own version; maintainer affiliation simplified to "ETH Zurich".
- `docs/admin-guide.md` handover checklist mirrors the PDF Section 06.
- Press kit page names the maintainer in §9 + the meta footer line.
- `scripts/release.sh` docstring records the Admin-role + PAT-permission requirements implied by the new rulesets.

#### Fixed

- Press-kit page primary buttons no longer render near-black in light theme (scoped EU-blue override, Apple-blue on hover).
- ORCID URL handling resilient to full-URL submissions (new `normalize_orcid()` helper in `sync-bios.py` + render-time normaliser in `people.html`).
- PDF poster image plate is now full-bleed (no more two blank pages flanking the poster).
- Accessibility FR / DE footers now use correctly localised links to Privacy + Licensing + Press kit.
- `LICENSE-CONTENT` now contains the canonical CC BY 4.0 legal-code text (was only the human-readable deed). GitHub's licence detector now identifies the file as CC-BY-4.0.
- PAT permissions clarified to least-privilege (bypass is keyed to *repository role*, not PAT scopes; misleading comment in `release.sh` corrected).

#### Security

- `protect-main` branch ruleset added — PR + linear history + status checks + squash merges; Admin-role bypass.
- `protect-release-tags` tag ruleset added — `v*` tags immutable after publication; no bypass for anyone.

## [1.1.0] · 2026-05-20 — Release tooling and PDF SemVer

> Operational hygiene. Future releases are boring to cut.

### One-command release tooling

**`scripts/release.sh`** lands as the canonical way to cut a release. Validates the SemVer string, runs a pre-flight check (on `main`, clean tree, in sync with origin, tag not yet used), promotes `[Unreleased]` → `[<version>]` in this file, resets a fresh `[Unreleased]`, updates the compare-link block, commits, pushes, creates an annotated `v<version>` tag on the new commit, pushes the tag, and publishes the GitHub Release whose body is the changelog section for the new version. `--dry-run` previews the whole flow without touching anything. Documented in PDF Section 06 *Admin guide → Cutting a release*.

### Documentation pack re-versioned

The stakeholder PDF previously used `v1.0` / `v1.1` / `v1.2` cover stamps — readable, but inconsistent with the website's SemVer discipline. Re-numbered in place to `v1.0.0` / `v1.1.0` / `v1.2.0` (content unchanged); the new cover stamp is **v1.3.0**. Section 06 gains the *Cutting a release* subsection mentioned above. Site screenshots refreshed against the live state.

### Index of changes

#### Added

- `scripts/release.sh` — one-command release helper with `--dry-run` support.

#### Changed

- Documentation PDF cover stamps re-versioned to SemVer (`v1.0` → `v1.0.0`, etc.); current cover stamp is `v1.3.0`.
- PDF Section 06 (Admin guide) gains a *Cutting a release* subsection.
- Site screenshots in the PDF refreshed (`snap-home.png`, `snap-network.png`, `snap-grants.png`).

## [1.0.0] · 2026-05-20 — Initial public release

> The first tagged release. Captures the state of the website and open community directory at the moment Deliverable D1 of COST Action CA24154 (NetSec) is presented for COST review. The site goes live publicly at <https://netsec-cost.eu>.

### The website

Seven public pages plus a designed 404: Home, The Network, Grants & Calls, Sitemap, Accessibility, Privacy, Licensing. Apple-style glass UI, light and dark themes, responsive from 4K screens down to a phone, EU + COST branding throughout. Hosted on GitHub Pages from `main` with HTTPS enforced and a Let's Encrypt certificate auto-managed by GitHub.

### Open community directory (Deliverable D1)

Members join via a public Google Form linked from the Network page. A weekly GitHub Action pulls submissions, deduplicates against the cost.eu MC roster, downloads + resizes headshots, and opens a pull request for human review before publication. `data/bios.json` is the canonical source-of-truth; leadership roles, directory position, and email-keyed identity all survive form re-submissions (see `scripts/sync-bios.py`). The home page's Action Leadership / WG Leadership / WG Co-Leader cards live-refresh from `bios.json` on page load.

### Multilingual support (beta)

Full French and German variants of every public page (sibling `.fr.html` / `.de.html` files; English authoritative). A SHA-1 based drift checker (`scripts/check-i18n-drift.py` + CI) flags translations that need refreshing when English changes. No machine-translation, no recurring API cost. Beta-banner on every non-authoritative page explaining the status and linking back to the English version.

### SEO + discoverability

Open Graph, Twitter Card, JSON-LD (Organization + WebSite + WebPage), canonical URLs, hreflang annotations, and a machine-readable `sitemap.xml` on every page — all generated from a single source-of-truth script (`scripts/inject-seo.py`) with sentinel-bracketed idempotent rewrites.

### Accessibility, security, licensing

- **Accessibility**: WCAG 2.1 AA target, EN 301 549 aligned. Zero axe-core violations on the home page at the v1.0 assessment. Statement at `/accessibility.html`. Skip-links, semantic landmarks, `:focus-visible` rings, `prefers-reduced-motion` honoured.
- **Security**: Five GitHub Advanced Security features enrolled (private vulnerability reporting, security advisories, Dependabot alerts, CodeQL code scanning with the security-and-quality + the security-extended suites, secret scanning with push protection). Pinned third-party Actions; least-privilege `GITHUB_TOKEN`. Coordinated-disclosure policy in `SECURITY.md`.
- **Licensing**: code under MIT (`LICENSE`), content + docs under CC BY 4.0 (`LICENSE-CONTENT`). Both attributed in every page's footer.

### Documentation

- **Stakeholder PDF**: `docs/pdf/NetSec-website-documentation.pdf` (v1.2 at v1.0.0). Cover, key-numbers poster, ToC, six chapters (Overview / Architecture / Design system / Translation / SEO / Admin guide / Security & DevSecOps), three appendices (Accessibility / Licensing / Changelog). Build pipeline at `docs/pdf/build.sh`.
- **Maintainer docs**: markdown reference under `docs/` for anyone working on the site — `architecture.md`, `design-system.md`, `admin-guide.md`, `bios-setup.md`, `i18n.md`, `seo.md`.
- **Members' Wiki**: working space for members + MC reps at <https://github.com/EISSeuropa/netsec.github.io/wiki>. Glossary, FAQ, onboarding, meeting-notes convention, decisions log. Member-editable without PR.

### Operational baseline

- **Domain**: `netsec-cost.eu`, registered at Namecheap under Dr Moritz Weiss (Action Chair), with Dr Arthur Laudrain as admin contact.
- **Hosting cost**: €0/month. GitHub Pages + the Google Form + Formspree's free tier cover everything; domain renewal is the only recurring expense.
- **GitHub org**: `EISSeuropa`. Two-factor authentication enforced at the org level.

### Index of changes

#### Added

- Public website at <https://netsec-cost.eu> on GitHub Pages, HTTPS-enforced.
- Seven public pages + 404: Home, The Network, Grants & Calls, Sitemap, Accessibility, Privacy, Licensing.
- Apple-style glass UI with light + dark themes; responsive 4K → phone.
- EU + COST branding throughout (`cost-logo.jpg` + EU emblem SVG with proper visual-identity proportions).
- Open community directory (Deliverable D1) + Google Form intake + weekly auto-PR sync (`scripts/sync-bios.py`).
- Home-page leadership cards live-refreshed from `data/bios.json`.
- French and German beta variants of every public page; SHA-1 drift checker via `scripts/check-i18n-drift.py` + CI job.
- SEO injector (`scripts/inject-seo.py`) — canonical, OG, Twitter Card, JSON-LD on every page; `sitemap.xml`.
- WCAG 2.1 AA accessibility statement (`/accessibility.html`) with zero axe-core violations on the home page.
- GitHub Advanced Security: private vulnerability reporting, security advisories, Dependabot alerts, CodeQL (security-and-quality + security-extended), secret scanning + push protection.
- Coordinated-disclosure policy in `SECURITY.md`.
- Stakeholder PDF documentation pack at `docs/pdf/NetSec-website-documentation.pdf` (v1.2).
- Maintainer markdown docs under `docs/` (architecture, design-system, admin-guide, bios-setup, i18n, seo).
- Members' Wiki seeded with glossary, FAQ, onboarding, meeting-notes convention, decisions log.
- Dual licensing — MIT for code, CC BY 4.0 for content + docs.

[Unreleased]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.8.0...HEAD
[1.8.0]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.7.0...v1.8.0
[1.7.0]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.6.1...v1.7.0
[1.6.1]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.6.0...v1.6.1
[1.6.0]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/EISSeuropa/netsec.github.io/releases/tag/v1.0.0
