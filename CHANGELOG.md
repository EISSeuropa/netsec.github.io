# Changelog

All notable changes to this repository are recorded here.

This project follows [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html)
and the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.
What "MAJOR / MINOR / PATCH" means in the context of this repo is
spelt out in the **Versioning** section of [`README.md`](README.md).

The documentation pack (`docs/pdf/NetSec-website-documentation.pdf`)
carries its own version stamp on its cover and its own changelog
appendix; see Appendix C of that PDF for documentation-pack history.

## Structure rule (applies to `[Unreleased]` + every `[X.Y.Z]` section)

Each release section has **at most one** of each category heading,
in this order:

> `### Added` → `### Changed` → `### Deprecated` → `### Removed`
> → `### Fixed` → `### Security`

When a PR adds an entry to `[Unreleased]`, the bullet goes inside the
*existing* `### Added` (or `### Fixed`, etc.) subsection — **never
in a new subsection of the same name below it**. The release script
extracts the `[Unreleased]` body verbatim into the GitHub Release
notes, so structural mess inside `[Unreleased]` is preserved into
the public release page. (v1.4.0 was cut while this rule was
implicit and ended up with 13 category headings instead of 3;
that was the prompt to write the rule down.)

Within a category, order bullets by user impact:

1. **Headline** changes first (new top-level features, IA shifts).
2. **Smaller polish** after.
3. Optional sub-headings (`#### Headline features` / `#### Tooling`)
   are fine inside one `###` block when a section has > ~8 bullets,
   but the parent `###` heading must still appear at most once.

The release script (`scripts/release.sh`) prints the `[Unreleased]`
body verbatim before prompting for confirmation; eyeball it then.
The `docs/admin-guide.md` "Cutting a release" section repeats this
rule for the maintainer-facing audience.

## [Unreleased]

### Added

- **Release-notes structure rule** documented in three places: at the top of `CHANGELOG.md` itself, in `docs/admin-guide.md` (new *Cutting a release* section), and in the `scripts/release.sh` header comment. The rule: each `[Unreleased]` and `[X.Y.Z]` section has at most ONE of each category heading (`### Added`, `### Changed`, `### Deprecated`, `### Removed`, `### Fixed`, `### Security`), in that order. PRs that add entries merge into the existing subsection rather than appending a new one with the same name. Prompted by v1.4.0's release notes, which had ended up with 13 category headings instead of 3 because the rule was implicit; that release section + its GitHub Release notes were cleaned up in this PR.

- **Launch-QA plan + automation** for the late-May 2026 public push. New `docs/launch-qa-2026.md` lays out the three-phase audit (automation pre-flight → critical user journeys → a11y + cross-browser + perf), the Go / No-Go criteria, the five-day schedule, the tooling cheatsheet, and a findings log. Two new scripts: `scripts/check-links.sh` (broken-link checker — internal anchors + external HTTP/HTTPS, Python-only, threads with rate-limit-respecting concurrency of 3, retries SSL-cert failures with verification off as a macOS-friendly fallback, validates `people.*.html#<slug>` deep-links against `data/bios.json`, skips known auth-gated hosts) and `scripts/check-a11y.sh` (axe-core scan via `@axe-core/cli`, spins up a localhost server so the scan sees the pages as a browser would, aggregates a per-page summary into `tmp/a11y-report.md`). New CI workflow `launch-qa-link-check.yml` runs the link checker on every PR that touches HTML and weekly on main, so link rot is visible within seven days. First Phase-0 run is recorded in the findings log.

### Changed

- **`scripts/check-a11y.sh` rewritten to use pa11y instead of `@axe-core/cli`.** The original axe-core CLI relies on a system Chrome that matches a system ChromeDriver — a brittle pairing that broke on the maintainer's laptop (Chrome 131, ChromeDriver expecting 149). pa11y wraps the same axe-core engine behind a Puppeteer-bundled headless Chromium so it doesn't depend on the system pair. The script also drops the heredoc-vs-stdin race that silently fed JSON-as-Python-source to the parser (printf | python3 - <<HEREDOC was wrong; switched to `python3 -c`).
- **Accessibility statement bumped to v1.1** on `/accessibility.html` (+ FR + DE). New audit date (22 May 2026), expanded *Preparation* section listing pa11y + Lighthouse + manual contrast verification, audit-card recast as "Violations after fix / Lighthouse a11y score / Needs manual review", and a paragraph about the dark-mode CTA contrast fix that was found and shipped as part of this audit. Statement supersedes v1.0 of 14 May 2026.
- **v1.4.0 CHANGELOG section + GitHub Release notes restructured.** The original [1.4.0] section had 13 category headings (multiple `### Added`, `### Changed`, `### Fixed` blocks) because each contributing PR appended its own subsection rather than merging into the existing one. Collapsed to the canonical three headings (`Added`, `Changed`, `Fixed`), with `#### Headline features` / `#### Phase 1 IA pass` / `#### Tooling + brand` sub-headings inside `### Added` to keep navigation manageable in a long release. Content preserved; the GitHub Release body at <https://github.com/EISSeuropa/netsec.github.io/releases/tag/v1.4.0> was overwritten via `gh release edit` to match.

### Fixed

- **Seven primary-CTA backgrounds failed WCAG AA contrast in dark mode.** The dark-mode `--accent` is `#6ea1ff` (lighter blue, chosen so accent text reads against the dark page). Buttons that used `background: var(--accent); color: #fff` directly resolved to **2.56:1** in dark mode — below the 4.5:1 floor for AA. The home-page `.btn-primary` and `.nav-cta` already inverted to light-bg + dark-text via explicit `.dark` overrides and were unaffected; seven other CTAs had no override and silently regressed. Affected: `.event-card.featured .event-date`, `.event-subscribe`, `#for-members .members-actions .primary` (home); `.tour-btn-primary`, `.tour-trigger-cta` (people); `.deliverables-roadmap-link-cta` (about); `.rm-feedback-action.is-primary` (roadmap). Fix: pin those CTA backgrounds to brand EU-blue `#003399` in dark mode (10.86:1 with white text) plus a `#0a4ed0` hover (11:1). Brand identity stays consistent across both modes. Surfaced by Phase 2 of the launch-QA audit (`docs/launch-qa-2026.md` finding A1).

- **Nine broken internal anchors** uncovered by the new link checker. `faq.{en,fr,de}.html` and `licensing.{en,fr,de}.html` still pointed at `index.html#committee`, `#roadmap`, `#outputs` — three home-page sections that the Phase 1 IA pass (PR #93) migrated to dedicated pages months ago without the FAQ + Licensing copy following. Updated to `about.X.html#leadership`, `roadmap.X.html`, `outputs.X.html` across the six page-locale combinations.

## [1.4.0] · 2026-05-22 — Site-wide search, infrastructure and directory improvements

### Added

#### Headline features

- **Site-wide search via Pagefind**. Modal overlay triggered by Cmd/Ctrl-K, `/` (anywhere outside an input), or the new magnifying-glass button in the nav. Indexes every `<main data-pagefind-body>` across all 30 public pages (EN + FR + DE), so results are scoped to the visitor's active locale automatically. Each page's `<h1>`/`<h2>`/`<h3>` becomes a sub-result with a deep-link anchor — long pages like FAQ and Glossary jump straight to the matched section. Snippets are highlighted with `<mark>` in the same EU-yellow used in the press kit. Privacy posture preserved: index served from `/pagefind/` on `netsec-cost.eu`, queries never leave the visitor's browser, no third-party calls. Lazy-loaded on first overlay open (~80 KB JS + ~50 KB per-language shard). Keyboard navigation between results, focus trap, `aria-live` result count, full light + dark theme parity. Design history: `docs/search-assessment.md`.
- **Directory bios are now searchable**, and a name search returns a rich card with the member's photo, country flag, role, and WG chips. Member data is rendered as Pagefind index stubs under `search/bios/<lang>/<slug>.html` at build time by the new `scripts/build-bio-search-stubs.py`, generated for all three locales so a French visitor searching *"Laudrain"* gets a hit in the French shard too. Stubs carry a meta-refresh + `noindex,nofollow` so the rare visitor who lands on a stub is bounced to the canonical `/people.html#<slug>`. The overlay rewrites the stub URL to the canonical anchor client-side (Pagefind v1 has no URL-override hook).
- **New `/about.html` page** (plus FR + DE). Consolidates the *Action* narrative, the deliverables Gantt, the *Leadership* grids (Action Leadership + WG Leaders + WG Co-leaders + the *MC by country* collapsible), and a *Relationship with EISS* placeholder. The home-page *About* anchor still carries the short intro; the dedicated page is the full story.
- **Public roadmap page at `/roadmap.html`** (plus FR + DE). Visual, audience-facing companion to the internal `docs/roadmap-2026.md`. Hero with last-updated stamp, a four-pill colour legend (*Shipped* — green, *In progress* — blue, *Planned* — purple, *Under watch* — amber), and a vertical timeline grouped by quarter. Twelve dated entries interleave shipped releases, the in-progress v1.4.0, the planned v1.5.0 – v1.8.0, and Action milestones (Stockholm Conference + Summer School, inaugural MC plenary, Year-1 anniversary). *Under watch* section at the foot lists deferred items with explicit triggers. Footnote points readers at the working doc on GitHub. Manual translations only (no machine translation).
- **iCalendar feed at `/calendar.ics`** + *Subscribe to NetSec events* CTA on the home page. Hand-authored RFC 5545 file with a `Europe/Stockholm` `VTIMEZONE` block. Localised in EN/FR/DE. A `<link rel="alternate" type="text/calendar">` in each home-page `<head>` makes the feed autodiscoverable for capable clients.

#### Phase 1 IA pass

- **FAQ + Glossary teaser sections on the About page** (EN / FR / DE). Five hand-picked FAQs and eight glossary terms surfaced directly on `/about.html`, each linking to the dedicated `/faq.html` or `/glossary.html` deep-link anchor. *View all 21 FAQ entries* / *Browse the full glossary* CTAs at the foot of each section.
- **New `/outputs.html` and `/news.html`** stub pages (each in EN / FR / DE). `/outputs.html` shows a *First outputs expected October 2026* status banner; `/news.html` is the future archive for older news entries.
- **Roadmap signposted on the home page and the About page**. (1) 4th card in the home-page *Find out more* grid, sitting alongside FAQ / Glossary / Press kit. (2) Accent callout at the foot of the Deliverables section on `/about.html` with an EU-blue *See the roadmap* CTA.
- **Expand / collapse chevron on directory cards in compact view** (`/people.html`). Small circular chevron at the bottom-right of every card — ▼ when collapsed, rotates to ▲ when expanded, hidden in detailed view. `pointer-events: none` so the chevron never absorbs the click. Touch-friendly, respects `prefers-reduced-motion`.
- **"Help shape this" community-feedback card on the public roadmap** (EN / FR / DE). Three CTAs: *Open an issue*, *Start a discussion*, *Browse the source*. Frames the roadmap as participatory.
- **Wiki link in every page footer** (EN / FR / DE) — *Glossary · Members' Wiki · Press kit*.

#### Tooling + brand

- **Brand favicon replacing the Mobirise placeholder**. New `assets/images/favicon.svg` — rounded square in the EU-blue → Apple-blue gradient with "NS" in white, designed to read cleanly at 16, 32, 48 px. Every page declares `<link rel="icon" type="image/svg+xml">` for modern browsers and `<link rel="alternate icon" type="image/png">` (a 256 × 256 PNG, same design) as fallback.
- **Calendar single-source-of-truth pipeline**. The `.ics` feed is generated from `data/events.json` by `scripts/build-calendar.py`; CI workflow `calendar-drift.yml` fails any PR where the JSON and the generated `calendar.ics` disagree.
- **`scripts/build-search.sh` + `.github/workflows/search-drift.yml`**. Pagefind pinned to 1.5.2 for deterministic shard hashes; `404.html` carries `data-pagefind-ignore="all"` so the not-found page doesn't pollute results.
- **Persistent lint against trailing arrows on external links**. `scripts/check-external-link-arrows.py` walks every root-level HTML file and fails if any `<a target="_blank">` to an absolute URL ends with a manual arrow glyph (→ / ↗ / » / >> / ➔ / ➜ / ▶) — the site CSS auto-injects an external-link icon, so a manually-typed arrow on top renders a double affordance. CI workflow `external-link-arrows.yml` runs the script on every HTML-touching PR.
- **Sync convention noted in `docs/roadmap-2026.md`** + *Last reviewed* line on each public roadmap, so the internal and public views stay in step.

### Changed

- **Header IA: nav reduced from 10 to 8 items**. Removed *Committee*, *Roadmap*, *Outputs* as standalone nav entries; *About* now points to `/about.html` (which contains the merged content); *Outputs* renamed to *Publications* and points to `/outputs.html`. New nav order across all 30 page × locale permutations: *News · About · Working Groups · Network · Events · Grants · Publications · Contact*.
- **Home page slimmed**. The *Committee* section (~265 lines), the *Roadmap* Gantt (~150 lines), and the three *Forthcoming* *Outputs* placeholder cards (~25 lines) all migrated to `/about.html` or `/outputs.html`. EN / FR / DE home pages now ~745 / ~660 / ~660 lines (down from ~990 / ~905 / ~905).
- **`/sitemap.html`** (+ FR + DE) rebuilt to match the new IA: the *Home* branch shrinks; new *About* and *Publications* branches list the new dedicated pages and their deep-link anchors.
- **Pagefind search index now built at deploy time, not committed to main**. Two PRs that both touched HTML used to conflict on `pagefind/pagefind-entry.json` because the content-hashed shard filenames diverged. Moved to a new Pages workflow (`.github/workflows/pages-deploy.yml`) that rebuilds the index on every push to main and deploys via `actions/upload-pages-artifact` + `actions/deploy-pages`. `/pagefind/` is now gitignored — PRs never touch it, the conflict source is gone. `search-drift.yml` simplified to a build-sanity check (per-locale page count > 0). Required a one-time Settings → Pages → Source flip from *Deploy from a branch* to *GitHub Actions* when the PR landed.
- **Release-cutting now requires a short title**. `scripts/release.sh` takes the title as a required second positional argument (e.g. `./scripts/release.sh 1.4.0 "Site-wide search"`). The title appears in the CHANGELOG heading, the GitHub Release name, the release commit message, and the annotated tag. Convention: 3-8 words, sentence case, no trailing punctuation.
- **Historical release entries retitled** to match the new convention — v1.0.0 *Initial public release*, v1.1.0 *Release tooling and PDF SemVer*, v1.2.0 *Press kit, directory tour, compact view*, v1.3.0 *Introducing FAQ and Glossary pages*.

### Fixed

#### Search overlay

- **Search backend now works.** Was returning *"SEARCH IS UNAVAILABLE. RELOAD THE PAGE TO TRY AGAIN"* on every query — the overlay was calling `pagefind.search(query, { filters: { language: lang } })`, which Pagefind interpreted as "filter to pages tagged with a `language` metadata field" (we never tag pages that way → 0 matches → catch branch fired). Pagefind v1 handles locale isolation via per-language shards keyed off `<html lang>`, so no filter is required.
- **Search results now deep-link to the matched item and highlight the term on landing.** Pagefind initialised with `{ highlightParam: 'pagefind-highlight' }`; a top-of-`site.js` bootstrap dynamically imports `pagefind-highlight.js` whenever the URL carries the query param, wraps matched terms in `<mark class="pagefind-highlight">`, and scrolls the first match into view. The overlay now closes on result-link click so the visitor actually sees the navigated page.
- **Member-name search no longer false-positives on the home page.** The *MC by country* grid on the home page carried 49 member names as `<li data-person="…">` — Pagefind was indexing those names and returning `/` for searches like *"Laudrain"*. The grid is now wrapped with `data-pagefind-ignore="all"`; the new directory bio stubs are the authoritative search index for member names.
- **`Cmd-K` / `Ctrl-K` hardened.** Now also checks `e.code === 'KeyK'` so the shortcut survives keyboard layouts where the printed glyph isn't at the physical KeyK position (Dvorak, AZERTY-in-some-browsers). Listener moved from `document` to `window` so extensions don't swallow it.
- **Windows / Linux users see a Ctrl-K shortcut** in the search button's tooltip (was the generic "Cmd/Ctrl-K"). Mac users get *Search (⌘ K)*; everyone else gets *Search (Ctrl K)*. Adds `aria-keyshortcuts` for screen readers.
- **Search trigger no longer overflows the floating header on the home page.** The `⌘K` hint badge is hidden in all viewports; the shortcut is still discoverable via the button's `title` tooltip and the *open* row inside the overlay.

#### Directory

- **Directory bio cards now show the full biography text.** The *Show more / Show less* toggle was never inserted on overflowing bios because the detection was wrapped in `requestAnimationFrame` — both unnecessary (reading `scrollHeight` already forces a sync layout) and unreliable (the callback fired too early in some browsers, when `scrollHeight === clientHeight`). Dropped the rAF wrapper; check runs synchronously after cards are appended. Belt-and-braces: each new bio is observed by a `ResizeObserver` so any later metric change (web-font swap, theme toggle, viewport resize) re-runs the check. EN / FR / DE.
- **Search-result clicks on a directory entry now visually confirm the landing.** The matched card gets an `.is-search-landed` class on hash arrival: a 2 px accent-blue outline with a soft glow, a 0.4 s scale-in animation, auto-fading after 3.5 s. Honours `prefers-reduced-motion`. In compact view the card is also expanded in place.

#### Public roadmap

- **Milestone cards rendered as saturated-blue panels with hard-to-read dark-on-blue text** (MC plenary, Year-1 anniversary, Summer School + Conference). Root cause: class-name collision. The Gantt chart on `/about.html` ships a `.milestone {}` rule that paints `background: linear-gradient(135deg, var(--accent), var(--accent-2))` on whatever element carries the class. The roadmap's timeline entries used `<li class="rm-entry planned milestone">`, so the `<li>` underneath each milestone *card* was getting the strong-blue Gantt-pill gradient applied directly, and the semi-transparent card on top bled through. Fix: renamed the public-roadmap class from `.milestone` to `.rm-milestone` (CSS + HTML, EN / FR / DE). CSS comment in `site.css` now flags the collision risk.
- **Status pill not perfectly centred on the timeline marker dot.** Marker `top` was 16 px (circle) / 18 px (milestone diamond) — visually about 3 px above the pill row's centre. Bumped to 19 px and 21 px respectively so each marker's geometric centre lands exactly on the pill's vertical centre.

#### Mobile + IA aftermath

- **Beta-translation ribbon was missing from every recently-added FR/DE page** — `about`, `outputs`, `news`, `faq`, `glossary`, `press-kit`, `roadmap` (14 page-locales). The two-part recipe (`data-i18n-status="beta"` on `<html>` + the ribbon `<div>` after `<body>`) was added on each missing page; the "View in English" link points at the EN sibling of that page.
- **Beta-translation ribbon overlapped the floating header on mobile.** On narrow viewports the long FR/DE sentence + link wraps to two or three lines (~60-100 px). The CSS used a fixed `body { padding-top: 38px }` and `.nav { top: 52px }` that only fit a single-line desktop ribbon. Fixed by deriving the offsets from `var(--ribbon-h, 38px)`, with a JS handler in `site.js` that measures the ribbon's real `offsetHeight` and writes it to `--ribbon-h` on `<html>` (re-runs on `window.load`, `resize`, and a `ResizeObserver` on the ribbon itself).
- ***Meet the team* link on the home-page news block was dead** (pointed at `#committee`, which no longer exists on the home page after the IA pass). Now points at `about.html#leadership` (locale-aware). EN / FR / DE.
- **Gantt chart misaligned on mobile**: Year 1 Q4 visually bled into Year 2 because the year row's `1fr` columns had no minimum, while the quarter row enforced `minmax(46px, 1fr)`. Year row now uses `repeat(4, minmax(184px, 1fr))` — every year column is exactly 4 × quarter width. Gantt's overall `min-width` raised from 780 px to 916 px.
- **`.mc-subhead` section dividers leaking onto a second line on narrow screens**: switched from `inline-block` + `vertical-align` to flexbox; pseudo-elements now use `flex: 0 0 48px` so they can't wrap.
- **Header crowding on the home page** addressed by hiding the *NetSec* wordmark in the floating bubble. The NS-square mark stays as the brand affordance; `aria-label="NetSec home"` still announces the brand to screen readers.

#### Events section

- **Events section: double-icon on external-link CTAs removed.** Two event cards (`Full details & how to apply`, `Programme & registration on Indico`) shipped both a hardcoded right-arrow SVG and the auto-injected external-link icon. The right-arrow SVG is stripped; the auto-icon remains.
- **Subscribe-to-NetSec-events button is now prominent and centred.** Previously a small bordered chip in the left margin under the events grid. Now a centred accent-blue CTA with a soft glow.
- **`.gitignore` now excludes `.DS_Store`** site-wide. macOS Finder metadata files had been at risk of being swept in by `git add -A`.

## [1.3.0] · 2026-05-21 — Introducing FAQ and Glossary pages

### Added

- **Public FAQ page at `/faq.html`** (plus FR + DE beta variants). 21 Q&As across six themed sections (About the Action / Joining & participating / Grants & funding / Meetings & reimbursement / Website & directory / For NetSec members) with a jump-to TOC and per-question deep-link anchors. Migrated from the members' Wiki so that academics, journalists, and prospective members — who will not naturally browse to GitHub — can find the answers on the public site. The Wiki FAQ page now stubs to this URL.
- **Public glossary at `/glossary.html`** (plus FR + DE beta variants). ~35 COST and NetSec terms grouped into five sections (COST framework / NetSec structure / People / Grants & meetings / Documents & outputs) with per-term deep-link anchors. Same migration rationale as the FAQ.
- **Discovery surface on the home page.** End of the About section gains a four-card "Find out more" grid pointing at the FAQ, the glossary, the press kit, and the members' Wiki — keeps the floating header at ten items while making the reference pages visible at a glance. Localised in EN/FR/DE.
- **Wiki signposting on the home page.** New "For NetSec members" strip between Outputs and Contact with a tinted card and two CTAs ("Open the Wiki" / "e-COST portal"). MC reps and WG participants don't drift to GitHub on their own; this strip leads them there. Localised in EN/FR/DE.
- **Footer references on every page.** FAQ and Glossary links inserted between *Licensing* and *Press kit* on every locale of every existing page (24 files).
- **Sitemap entries** for `/faq.html` and `/glossary.html` in `sitemap.xml`; the in-page `/sitemap.html` "About & policies" branch lists them (plus the press kit which was previously missing) on EN / FR / DE.
- **SEO metadata** (canonical, OG, Twitter Card, JSON-LD WebPage) for the six new pages via `scripts/inject-seo.py` — the `PAGES` list now includes `faq` and `glossary`.
- **i18n drift tracking** for `faq.html` and `glossary.html` (FR + DE) in `data/i18n-state.json`.

### Changed

- **Wiki `FAQ.md` and `Glossary.md` are now short stubs** that point at the canonical public versions. Keeping the source of truth in one place stops the FAQ and Glossary from drifting between two surfaces.

### Fixed

- **External-link icon now appears, suppresses, and renders in the right places.** Four related regressions, all rooted in the auto-injecting `a[target="_blank"][href^="http"]::after` rule introduced in v1.2.0.
  - **Specificity bug.** The global selector was (0,0,2,2); every exclusion (`.cost-mark::after`, `.socials a::after`, `.grant-cta::after`, `.member-contact a::after`, `.brand::after`, `.eu-mark::after`, `.lang-switch a::after`, `.tour-trigger::after`, `.welcome-strip-tips a::after`) was (0,0,1,1) or (0,0,1,2) and silently lost. Result: the icon was appearing on the COST mark, the EU mark, the GitHub footer link, the language switcher, the social-icon row on member cards, and was rendering on top of the inline arrow inside *Apply on e-COST* buttons. Fix: wrap the global selector in `:where()` so it contributes 0 to specificity; every exclusion now wins naturally.
  - **Flex-shrink collapse.** Inside flex containers (e.g. `.resource-card` on the Grants page) the `::after` becomes a flex item with default `flex-shrink:1` and collapses to width 0 — the *Resources & reference documents* cards appeared to have no external-link indicator at all. Fix: `flex:none` on the pseudo-element.
  - **Double-arrow on news cards.** Two news cards on the home page (*View the school*, *See the programme*) carried both a hardcoded `→` and the auto-injected icon. Fix: drop the hardcoded `→` from the external-link news cards (kept on the internal-link ones, where there is no auto-icon). EN/FR/DE.

## [1.2.0] · 2026-05-21 — Press kit, directory tour, compact view

### Added

- **Click-to-expand on compact directory cards** + a **`+` quick-join button** in the toolbar.
  - Clicking a card in compact mode flips it to its detailed form in place (photo, role, full affiliation, WGs, bio, contact icons), while every other card on the grid stays compact. Click outside / Esc / click another card collapses. Cards become keyboard-focusable in compact mode; Enter / Space triggers expansion. The expanded card's `data-slug` mirrors to `location.hash` so the state is shareable; `/people.html#eugenio-sanchez` auto-expands that card on page load. Long-term upgrade path to a sticky side-panel pattern is tracked in [Issue #72](https://github.com/EISSeuropa/netsec.github.io/issues/72).
  - The directory toolbar gains a **`+` button** (styled as a bright accent CTA next to the muted `?` tour-trigger). Clicking it smooth-scrolls to the join card at the foot of the page and focuses the *Add your bio* CTA. Localised in EN/FR/DE.
- **Guided six-step directory tour.** Anchors coachmark tooltips to: search box → WG/MC filter chips → country dropdown → view-mode toggle → `+` quick-join button → join card (with smooth-scroll into view). Two entry points: a *Take the tour* button in the welcome strip and a persistent **`?` button** in the toolbar. Keyboard navigable (← / → / Enter / Esc), focus trap on the tooltip's Prev/Skip/Next buttons, backdrop click skips, honours `prefers-reduced-motion`. Completion or skip sets the same `localStorage('netsec-directory-tour-seen')` flag as the welcome strip. Engine lives in `assets/js/site.js` as `window.netsecTour({steps, labels, onComplete})` — designed to be reusable for other pages later. Localised in EN/FR/DE.
- **First-visit orientation strip on the directory.** A dismissible banner above the `/people/` toolbar that introduces the directory in three lines: it's open (not only MC), search and filter affordances, density toggle, where the join form lives. One click to dismiss; preference persists in `localStorage('netsec-directory-tour-seen')`; returning visitors never see it. Localised in EN/FR/DE. Honours `prefers-reduced-motion`.
- **Compact directory view.** A two-button segmented toggle in the toolbar (next to the country filter) switches the member grid between detailed (photo + bio + contact icons) and compact (initials/photo + name + affiliation + WG chips only, three across on a desktop). Preference persists per visitor via `localStorage('netsec-directory-view')`. The compact card's affiliation line drops the position prefix and country name in text (the flag conveys the country implicitly).
- **Public press-kit page at `/press-kit.html`** (plus FR + DE beta variants). One canonical URL for outreach: the poster with print and card-size downloads, the NetSec / COST / EU emblems with pairing rules, the colour palette and typography reference, the funding-statement boilerplate in three forms (full, short, one-line credit), suggested CC BY 4.0 attribution wording, and explicit do / don't rules. Linked from every page's footer between *Licensing* and *Site map*. Added to `sitemap.xml`, the i18n drift manifest, and the `scripts/inject-seo.py` `PAGES` list.
- **Promotional poster** for the Action, sized A3 portrait and ready for outreach print runs. Source HTML version-controlled at [`docs/promo/poster-promo.html`](docs/promo/poster-promo.html); rendered raster at `docs/pdf/poster-promo.png` (2480 × 3508 px, ~192 dpi); 800 × 1131 px card-size variant (544 KB) at `docs/promo/poster-promo-card.png` for inline use in README, Wiki, email, and chat. Embedded as Appendix C of the documentation PDF (Appendix D in PDF v1.5.0, reordered to C in v1.5.2).
- **README banner** at the top of the repo's `README.md` showing the card-size poster and linking to the public press kit.
- **Members' Wiki "Templates & press kit" page** at <https://github.com/EISSeuropa/netsec.github.io/wiki/Templates> — member-facing companion to `/press-kit.html`, with the funding-statement boilerplate and attribution wording in fast copy-paste form. The Wiki sidebar "Templates" entry now resolves to this page; the Wiki Home page gains the same poster banner as the README.

### Changed

- **Grants page: explicit framing of the e-COST portal model.** The portal note at the top of `/grants/` now spells out three things openly: applications go through the general e-COST portal (no NetSec-specific form); the portal **filters by applicant profile** (ITC visible only to ITC affiliates, YRIG visible only to under-40s) so a member may not see every scheme listed; and only the five schemes on the page are in NetSec's WBP — applications for anything else **will be rejected** by the Grant Awarding Coordinator. The YRIG and ITC cards gain a small italic visibility caption under their eligibility lists. Wiki FAQ gains two matching entries ("Why don't I see grant X?" / "Why might my application be rejected?"). `docs/architecture.md` user-facing features list notes the portal model.
- **Documentation PDF reorganised** (cumulative across v1.4.0 → v1.5.2 of the PDF, see Appendix D of the pack for per-revision detail):
  - **New Section 07 — Branch and tag protection.** Documents the two GitHub rulesets, what each blocks, where the bypass sits, and why the tag ruleset has no bypass for anyone.
  - **Section 06 (Admin guide) handover checklist rewritten** around the consequence that the release-cutter needs the repo `Admin` role (not `Maintain`). Four sub-checklists: Access grants, Automation handover, Verification, Revocation.
  - **Accounts & assets table** in Section 06 gains rows for the branch-and-tag rulesets and the automation PAT.
  - **Appendices C and D swapped** (v1.5.2): the changelog is now the last appendix (D); the promotional poster is C. Opening the PDF on its last page lands the reader on a per-version record of what changed, not on the poster image.
  - **HTML `<title>` now carries the documentation-pack version** (v1.5.1) — surfaces the version in PDF metadata and the browser tab.
  - **Maintainer affiliation simplified** on the cover and last-page footer from *"ETH Zurich CSS"* to *"ETH Zurich"* (v1.5.1).
- **`docs/admin-guide.md` handover checklist rewritten** to mirror the PDF Section 06 changes — Access grants, Automation handover, Verification, Revocation.
- **Press kit page now names the maintainer.** A short attribution paragraph at the foot of section 9 ("Contact for media enquiries"); the meta footer-line reads *"prepared … by Dr Arthur Laudrain"*. Applied identically across EN / FR / DE.
- **`scripts/release.sh` header docstring** records the Admin-role and PAT-permission requirements that the new rulesets imply.

### Fixed

- **Press-kit page primary buttons no longer render near-black in light theme.** The site-wide `.btn-primary` rule fills with `var(--ink)` (#0b1220), which read as harshly heavy on the outreach-oriented press-kit page (§1 *What's on it* downloads, §8 *Open the documentation pack*). A scoped override re-themes those buttons to EU blue (`--accent`), with Apple blue (`--accent-2`) on hover / focus.
- **ORCID URL handling resilient to full-URL submissions.** The Google Form's *ORCID* field asks for the 19-character ID but members frequently paste their whole profile URL, producing a broken double-prefixed `href`. `scripts/sync-bios.py` now normalises ORCID input at write time via a new `normalize_orcid()` helper (strips `https?://(sandbox\.)?orcid.org/`, drops trailing slash / query / fragment, reinserts hyphens for the 16-digit-no-hyphen form, asserts the canonical pattern, returns empty string otherwise). `people.html` and its FR/DE variants apply the same defensive normaliser at render time. 16-case smoke test covers all common variants.
- **PDF poster image plate is now full-bleed.** The A3 raster, rendered inside a standard `.page` container, came out ~252mm tall — just over the ~257mm column height once the figure caption was included — and overflowed to a successor page, leaving the parent page blank. Visible to readers as two blank pages flanking the poster. Fixed via a dedicated `@page promo-plate { margin: 0 }` rule.
- **Accessibility FR / DE footers** previously linked at the English versions of Privacy and Licensing (with the *Lizenz*/*Licence* label mis-targeted at `privacy.html#main`). Replaced with the correctly localised footer used by the other FR / DE pages, plus the new Press kit link.
- **`LICENSE-CONTENT` now contains the canonical CC BY 4.0 legal code text**, fronted by a short NetSec-specific preamble. The previous file held only the human-readable summary deed, which is explicitly not the legal instrument; GitHub's licence detector (licensee) accordingly listed the file as *Unknown*. With the canonical text in place — sourced from <https://creativecommons.org/licenses/by/4.0/legalcode.txt> — the file matches licensee's `CC-BY-4.0` template well above the 95 % similarity threshold, and the "Licenses found" panel now correctly identifies it as **CC-BY-4.0**.
- **PAT permissions for automation clarified to least-privilege.** Earlier handover guidance recommended `Administration: read+write` indefinitely, but the ruleset bypass that lets `release.sh` push directly to `main` is keyed to the user's *repository role* (`Admin`), not to the PAT's `Administration` permission. Steady-state automation now runs with `Administration: Read` (sufficient for `gh api .../rulesets` verification) or no `Administration` access at all. The handover checklist grants `read+write` only at takeover for verification, then downgrades to `Read`. A misleading comment in `scripts/release.sh` that attributed the bypass to the PAT permission rather than the user's role has been corrected.

### Security

- **Branch & tag protection rulesets** added to the repository.
  - `protect-main`: restricts deletions and force-pushes, requires linear history, requires a pull request before merging, requires all four CodeQL status checks to pass, requires conversation resolution, restricts merge methods to squash. Bypass: the Repository Admin role (so `scripts/release.sh` can still push the changelog-promotion commit directly).
  - `protect-release-tags`: restricts deletions, updates, and non-fast-forward updates on tags matching `v*`. No bypass for anyone — once a release tag is published it is immutable.
- Both rulesets are documented in PDF Section 07 ("Branch and tag protection") and visible at the [Settings → Rules → Rulesets page](https://github.com/EISSeuropa/netsec.github.io/settings/rules).

## [1.1.0] · 2026-05-20 — Release tooling and PDF SemVer

### Added

- **`scripts/release.sh`** — one-command release helper. Validates the
  semver string, performs a pre-flight check (must be on `main`, clean
  tree, in sync with origin, tag not yet used), promotes
  `[Unreleased]` → `[<version>]` in this file, resets a fresh
  `[Unreleased]`, updates the compare-link block, commits, pushes,
  creates an annotated `v<version>` tag on the new commit, pushes the
  tag, and publishes a GitHub Release whose body is the changelog
  section for the new version. Supports `--dry-run`. Documented in
  `docs/pdf/` Section 06 "Admin guide → Cutting a release".

### Changed

- **Documentation PDF re-versioned to SemVer** (`docs/pdf/NetSec-website-documentation.pdf`).
  Previous cover stamps v1.0 / v1.1 / v1.2 are re-numbered to their
  SemVer equivalents v1.0.0 / v1.1.0 / v1.2.0; their content is
  unchanged. New PDF cover stamp is **v1.3.0**.
- **PDF Section 06 (Admin guide)** gains a new "Cutting a release"
  subsection walking through the `release.sh` workflow.
- **Site screenshots refreshed** in the PDF (`snap-home.png`,
  `snap-network.png`, `snap-grants.png`) against the current state
  of <https://netsec-cost.eu>.

## [1.0.0] · 2026-05-20 — Initial public release

The first tagged release. This snapshot captures the state of the
website and open directory at the point Deliverable D1 of COST
Action CA24154 is presented for review.

### What ships in v1.0.0

**Public website (<https://netsec-cost.eu>).** Seven public pages
plus a designed 404: Home, The Network, Grants & Calls, Sitemap,
Accessibility, Privacy, Licensing. Apple-style glass UI, light and
dark themes, responsive from 4K screens down to a phone, EU and
COST branding throughout. Hosted on GitHub Pages from `main` with
HTTPS enforced and a Let's Encrypt certificate auto-managed by
GitHub.

**Open directory.** Members join via a public Google Form linked
on the Network page. A weekly GitHub Action pulls submissions,
deduplicates against the cost.eu MC roster, downloads and resizes
headshots, and opens a pull request for human review before
publication. Bios.json is the canonical source-of-truth; leadership
roles, position in the directory, and email-keyed identity all
survive form re-submissions (see `scripts/sync-bios.py`). The home
page's Action Leadership / WG Leadership / WG Co-Leader cards are
live-refreshed from `data/bios.json` on page load.

**Multilingual support (beta).** Full French and German variants
of every public page (sibling `.fr.html` / `.de.html` files;
English authoritative). A SHA-1 based drift checker
(`scripts/check-i18n-drift.py` + CI job) flags translations that
need refreshing when English changes. No machine-translation, no
recurring API cost.

**SEO and discoverability.** Open Graph, Twitter Card, JSON-LD
(Organization + WebSite + WebPage), canonical URLs, hreflang
annotations, and a machine-readable `sitemap.xml` on every page,
all generated from a single source-of-truth script
(`scripts/inject-seo.py`) with sentinel-bracketed idempotent
rewrites.

**Accessibility.** WCAG 2.1 AA target, EN 301 549 aligned. Zero
axe-core violations on the home page (assessed 14 May 2026).
Statement at `/accessibility.html`. Skip-links, semantic landmarks,
`:focus-visible` rings, `prefers-reduced-motion` honoured.

**Security automation.** Five GitHub Advanced Security features
enrolled: private vulnerability reporting, security advisories,
Dependabot alerts, CodeQL code scanning (security-and-quality and
security-extended suites at high precision, on push, pull-request,
and weekly cron), secret scanning with push protection. Supply-chain
hardening via pinned third-party Actions and least-privilege
`GITHUB_TOKEN`. Coordinated-disclosure policy in `SECURITY.md`.

**Stakeholder documentation pack.** A self-contained PDF deliverable
at `docs/pdf/NetSec-website-documentation.pdf` (currently v1.2),
covering the cover, a key-numbers-and-features poster, table of
contents, six numbered chapters (Overview, Architecture, Design
system, Translation, SEO, Admin guide, Security & DevSecOps), and
three appendices (Accessibility, Licensing, Changelog). Build
pipeline at `docs/pdf/build.sh`.

**Maintainer documentation.** Markdown reference under `docs/` for
anyone working on the site: `architecture.md`, `design-system.md`,
`admin-guide.md`, `bios-setup.md`, `i18n.md`, `seo.md`. PDF and
markdown are kept conceptually parallel.

**Members' Wiki.** Working space for NetSec members and MC
representatives at <https://github.com/EISSeuropa/netsec.github.io/wiki>.
Glossary, FAQ, onboarding for new MC reps, meeting-notes
convention, decisions log, how-tos landing. Separate from the
website and from `docs/`; member-editable without PR.

**Dual licensing.** Code under MIT (`LICENSE`); site content and
documentation under CC BY 4.0 (`LICENSE-CONTENT`). Both are
reuse-friendly and attributed in the footer of every page.

### Operational baseline

- **Domain:** `netsec-cost.eu`, registered at Namecheap under Dr
  Moritz Weiss (Action Chair), with Dr Arthur Laudrain as admin
  contact.
- **Hosting cost:** €0/month. GitHub Pages, the Google Form, and
  Formspree's free tier cover everything; domain renewal is the
  only recurring expense.
- **GitHub org:** `EISSeuropa`. Two-factor authentication enforced
  at the org level.

[Unreleased]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.4.0...HEAD
[1.4.0]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/EISSeuropa/netsec.github.io/releases/tag/v1.0.0
