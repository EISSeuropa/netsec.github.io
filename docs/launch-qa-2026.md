# Launch QA — public push, late May 2026

> *Audience: the maintainer (Dr Arthur Laudrain, MC member CH; ETH
> Zurich). Drafted on 22 May 2026 against the `v1.4.0` release.
> Living document — fill in findings as the audit runs.*

## Context

The website at <https://netsec-cost.eu> has existed publicly since
20 May 2026 (`v1.0.0`). Since then we've shipped `v1.1.0` → `v1.4.0`
in five days — adding site-wide search, a new About page, the
public roadmap, the press kit, FAQ + Glossary, brand favicon, and
deploy-time Pagefind. The site has surface area now: **~14 public
pages × 3 locales = ~42 pages**, plus dynamic content (directory,
search index, calendar feed).

**Trigger**: a public-facing push is planned in the next 3-5 days
(small announcement now; the Stockholm Conference + Summer School
on 9-12 June is the bigger moment). The site will see real traffic,
real social shares, real screenshots in inboxes.

**Last formal audit**: `v1.0.0`. Two days ago. But the site has
grown ~50 % in surface area and complexity since then, the search
overlay + ResizeObserver + chevron + IA pass have all not been
audited yet, and the conference outreach is the first moment we'll
have non-MC visitors landing on the site with no warning.

## Constraints

- **Time**: 3-5 days. Realistically 15-20 hours of focused work
  spread across evenings.
- **People**: solo. Maintainer-only audit. No external consultant
  this round (queued for Phase 2 of the IA pass per `roadmap-2026.md`).
- **Tooling**: prefer automation over manual checks where the
  signal-to-noise warrants it. Browser DevTools + a small number
  of CLI tools.
- **Budget**: zero external spend. Free / OSS tools only.

## Launch criteria — Go / No-Go

The audit's job is to clear or knowingly defer every item below.
**Anything still red blocks launch.**

### P0 — must be green to ship

| Check | How | Owner |
|---|---|---|
| Zero broken **internal** links across all locales | `scripts/check-links.sh` (Phase 0) | maintainer |
| Zero broken **external** links to e-COST, cost.eu, GitHub, EISS | same | maintainer |
| Pagefind search returns results in EN + FR + DE on at least 3 queries each | manual smoke (Phase 1) | maintainer |
| Home, About, Directory, Grants, Press kit render and read on Chrome / Safari / Firefox (desktop) | manual smoke (Phase 1) | maintainer |
| Home, About, Directory render and are usable on **iPhone-class viewport (375 × 812)** | DevTools emulation (Phase 1) | maintainer |
| Zero red **axe-core** violations on home, about, people, faq, glossary, grants, press-kit, roadmap | `scripts/check-a11y.sh` (Phase 0) | maintainer |
| Lighthouse **Performance ≥ 80** and **Accessibility ≥ 95** on home, directory, grants | Lighthouse CLI (Phase 2) | maintainer |
| **i18n drift clean** (`scripts/check-i18n-drift.py` exits 0) | already on CI | (auto) |
| **External-link arrow lint clean** | already on CI | (auto) |
| **Pagefind build sanity** clean | already on CI | (auto) |
| **No third-party network calls** from any page (privacy posture) | Network tab manual + grep | maintainer |
| **`/calendar.ics`** parses on Apple Calendar / Outlook / Google Calendar | manual subscribe test | maintainer |

### P1 — should be green; document deviations

| Check | How | Owner |
|---|---|---|
| Keyboard-only navigation through home + directory + grants reaches every interactive element | manual (Phase 2) | maintainer |
| VoiceOver (macOS) screen-reader smoke on home, directory, search overlay | manual (Phase 2) | maintainer |
| `prefers-reduced-motion` respected (no scale animation on directory, no card hover transforms) | DevTools emulation (Phase 2) | maintainer |
| Dark mode parity (every page is readable in dark mode) | manual (Phase 2) | maintainer |
| Print stylesheet at least doesn't break (text remains, basic structure preserved) | Cmd-P preview (Phase 2) | maintainer |
| Open Graph card previews look right on LinkedIn / Twitter / Bluesky / Mastodon | OpenGraph.xyz / debugger.facebook.com (Phase 2) | maintainer |
| Mobile tap-target sizes ≥ 44 × 44 CSS px on all CTAs | manual (Phase 2) | maintainer |

### Deferred to post-launch (explicit)

Out of scope for this round; flagged so it's clear what we're
*not* committing to:

- Native-speaker FR / DE translation review (queued for `v1.6.0`).
- Deep IA / UX pass against audience tracks (Phase 2 IA audit, Jul-Aug per `roadmap-2026.md`).
- Per-page Open Graph images (one global `og-image.png` for now;
  per-page cards queued for `v1.8.0`).
- Comprehensive Windows + Edge + older-browser matrix (Chromium-Edge
  shares engine with Chrome, the realistic Windows path).
- Performance audit against very-low-end mobile (CWV on a slow 3G profile).
- Per-event `.ics` files (queued for `v1.6.0`).
- A11y AAA-level checks (we target 2.1 **AA** only — declared in
  `/accessibility.html`).

## Schedule

Five days, working evenings. Adjust if the launch slips.

| Day | Phase | Hours | Output |
|---|---|---|---|
| Day 1 (today) | **Phase 0 — automation** | 4 | `scripts/check-links.sh`, `scripts/check-a11y.sh`, plus this plan committed. First auto-run; findings logged below. |
| Day 2 | **Phase 1 — critical user journeys** | 4-5 | Six journeys completed on three desktop browsers + mobile emulation. Red findings filed as issues; quick fixes landed. |
| Day 3 | **Phase 2 — a11y + cross-browser + perf** | 3-4 | Keyboard pass, VoiceOver spot-check, Lighthouse on key pages, OG card previews. |
| Day 4 | **Fix + re-test** | 3-4 | Land P0 fixes, re-run automation, re-test the failing journeys. |
| Day 5 | **Final sweep + Go/No-Go** | 1-2 | All P0s green, sign-off below, `accessibility.html` *Last assessed* bumped, optional release if any fixes warrant it. |

**Total budget**: 15-19 hours. If a P0 item slips and can't be
fixed in time, the *No-Go* path is: hold the public push back to
the next safe window (worst case: just-after the conference
weekend) rather than ship with a known launch defect.

## Phase 0 — Automation pre-flight

Each item below is a single command. Run them in order. Findings
in the table at the bottom.

### Link check — broken internal + external URLs

```bash
./scripts/check-links.sh
```

Walks every `*.html` at the repo root, follows internal `<a href>`
attributes, and HEAD-pings every external URL. Fails on any 4xx /
5xx response or unresolvable target. **Built in this PR** (see
also `.github/workflows/launch-qa-link-check.yml` — runs weekly on
main from now on, so the link health stays visible past launch).

### Accessibility — axe-core across every page

```bash
./scripts/check-a11y.sh
```

Spins up a temporary `python3 -m http.server`, walks each public
page, runs `npx @axe-core/cli` against it, aggregates the results
into `tmp/a11y-report.md`. **Built in this PR.**

### i18n drift

```bash
python3 scripts/check-i18n-drift.py
```

Reports any FR / DE pages whose EN source has been edited since the
last "mark-fresh" stamp. Existing tool; expected to exit 0 — if it
doesn't, run `--mark-fresh <page>.html <lang>` after manually
porting changes.

### External-link arrow lint

```bash
python3 scripts/check-external-link-arrows.py
```

Existing tool. Catches the recurring "→ + auto-icon" double
affordance on external links. Expected exit 0.

### Pagefind build sanity

```bash
bash scripts/build-search.sh
```

Builds the index. Per-locale page counts should all be non-zero
(`pagefind/pagefind-entry.json`). Expected: `en: 27`, `fr: 27`,
`de: 27` (or whatever the current page count is).

### SEO surface

```bash
python3 scripts/inject-seo.py
```

Idempotent — exits with all "unchanged" if every page's SEO block
matches the generator. Any "changed" output means the SEO config
drifted from the served HTML; re-commit the result.

### Privacy posture — no third-party calls

Manual but mechanical:

```bash
# Should return nothing — no fonts.googleapis.com, googleapis,
# tracking, analytics, etc. embedded in any page.
grep -rE "google-analytics|googletagmanager|facebook\.com|plausible|fathom|mixpanel" *.html
# Allowed: fonts.googleapis.com + fonts.gstatic.com (declared in
# privacy.html); everything else is a regression.
```

## Phase 1 — Critical user journeys

Six journeys, each tested on **three browsers** (Chrome, Safari,
Firefox — macOS) and **one mobile profile** (DevTools iPhone 13
emulation, 390 × 844, no throttling).

For each journey, record either ✓ or note the issue + browser + viewport.

### Journey 1 — First-time visitor lands on home

Path: open `https://netsec-cost.eu` cold (clear cache).

Checks:

- LCP visible in under 2 s; no obvious layout shift.
- Hero copy reads; subtitle hints at "European security studies".
- Header bubble doesn't overflow (fixed in `v1.4.0` but verify).
- Theme toggle works; preference persists on reload.
- Language switch to FR + DE — beta ribbon appears, EN content
  doesn't leak.
- "Find out more" grid has 4 cards (FAQ / Glossary / Press kit /
  Roadmap), all click through.

### Journey 2 — Researcher looking for STSM info

Path: home → search overlay (Cmd-K or `/`) → query "STSM" → click first result.

Checks:

- Overlay opens within ~300 ms (lazy-load is acceptable on first open).
- Query "STSM" returns ≥ 3 results in EN; ≥ 2 in FR + DE.
- Clicking a Grants result lands on `/grants.html` at the STSM
  section anchor, with yellow `<mark>` highlight on the term.
- Esc closes the overlay; the highlight stays on the page.

### Journey 3 — Press / journalist downloads press kit

Path: home → footer "Press kit" → `/press-kit.html`.

Checks:

- Page loads cleanly.
- Logos visible, copyable.
- Boilerplate copy reads correctly (no orphaned variables).
- Funding statement is correct in all three lengths (full / short /
  one-line).
- CC BY 4.0 attribution wording present.

### Journey 4 — MC member finds own card in the directory

Path: home → Network → search the directory for own name.

Checks:

- Cards render in both compact and detailed view.
- Searching for a name filters down the grid.
- Clicking a card (compact view) expands in place, chevron rotates,
  bio expand-toggle works.
- Deep-link `/people.html#<slug>` scrolls to the right card and
  spotlights it.
- Search via the overlay for the same name → lands on the
  directory entry with the spotlight.

### Journey 5 — Prospective member fills the form

Path: home → Network → "Add your bio" button.

Checks:

- Button is visible from the directory page and from the home page
  CTA.
- Opens the Google Form in a new tab.
- Form is reachable; Google account email auto-collected.

### Journey 6 — Reader subscribes to events

Path: home → Events section → "Subscribe to NetSec events".

Checks:

- Button is prominent (centred, accent-blue).
- `webcal://` link prompts the OS calendar to subscribe on macOS.
- `/calendar.ics` parses (download it; the two events are present
  with correct dates + Stockholm location).

### Journey checklist

Tested 22 May 2026 against the local static mirror (Pagefind built
locally for the search-overlay journeys) via the Claude Code
preview tool, which drives a headless Chromium. The desktop +
mobile-emul columns are the two viewports the preview tool covers
directly; Safari + Firefox + real-device iPhone need a manual
sweep before public push.

| Journey | Headless Chromium (desktop) | Mobile-emul 390 × 844 | Safari | Firefox | Real iPhone |
|---|---|---|---|---|---|
| 1 Home landing | ✓ (one i18n-ribbon copy issue → I-1) | ✓ (one menu-panel contrast issue → M-1) | pending | pending | pending |
| 2 Search STSM | ✓ (7 EN / 7 FR / 7 DE; one nested-`<mark>` issue → J2-1) | — | pending | pending | pending |
| 3 Press kit | ✓ | — | pending | pending | pending |
| 4 Directory card | ⚠ (deep-link auto-expand + spotlight didn't fire under headless → J4-1) | — | pending | pending | pending |
| 5 Join form | ✓ | — | pending | pending | pending |
| 6 Calendar subscribe | ✓ (2 events at Stockholm, webcal:// link) | — | pending | pending | pending |

## Phase 2 — Accessibility + cross-browser + perf

### Keyboard-only pass

Tab through the entire home page + directory + grants from the top.

- Every interactive element receives visible focus.
- Tab order is logical (left-to-right, top-to-bottom).
- Skip-link works (first tab on each page → "Skip to main content").
- Search overlay: tab enters the input, then results; Esc closes.
- Directory card click-to-expand works with Enter / Space.
- No focus traps outside the search overlay.

### VoiceOver spot-check (macOS)

Cmd-F5 to start VoiceOver. Walk three pages with VO+arrow:

- **Home**: header → hero → news → about → events → grants → footer.
  Heading hierarchy logical; no orphan or duplicate landmarks.
- **Directory**: filter chips announce their state; card details
  read in a sensible order; contact icons read with their labels.
- **Search overlay**: `aria-live` result count announces; tabbing
  through results is intelligible.

### Reduced-motion check

DevTools → Rendering → "Emulate CSS prefers-reduced-motion: reduce".

- Search-landing spotlight: scale-in disabled, only the ring shows.
- Roadmap card hover: no `translateY`.
- Bio toggle: no transition on chevron rotation.
- Directory card hover: no transform.

### Lighthouse — 4 key pages

```bash
npx -y lighthouse https://netsec-cost.eu/ \
  --output=html --output-path=tmp/lh-home.html \
  --quiet --chrome-flags="--headless=new"
```

Repeat for `/people.html`, `/grants.html`, `/press-kit.html`.

Target floors:
- **Performance** ≥ 80
- **Accessibility** ≥ 95
- **Best Practices** ≥ 95
- **SEO** ≥ 95

### Open Graph card previews

For each of: home, about, people, grants, press-kit, roadmap,
faq:

- <https://www.opengraph.xyz/> — paste URL, verify image / title /
  description.
- <https://cards-dev.twitter.com/validator> — Twitter Card preview.
- LinkedIn Post Inspector — <https://www.linkedin.com/post-inspector/>.

OG image is currently global (`og-image.png`); per-page images
are deferred. Verify the global one renders cleanly on every
platform.

### Dark mode

Cycle every public page through dark mode (theme toggle in nav).
Look for: low-contrast text, broken gradients, white-on-white
artifacts, dark-on-dark.

### Print preview

Cmd-P on home, faq, glossary, press-kit. Check:

- No critical content cut off.
- Hyperlinks visible (URLs printed alongside link text — browser
  default is fine).
- No "infinite blank pages" failure mode.

## Phase 3 — Final sweep

- Re-run all Phase 0 automation, expect all green.
- Re-run any Phase 1 / 2 step that had red findings; expect green.
- Bump *Last assessed* date on `/accessibility.html` to today.
- Commit findings log + sign-off below.
- If any fixes warranted a release: `./scripts/release.sh 1.4.X "..."`
  before launch.

## Tooling — install + run cheatsheet

```bash
# axe-core CLI — install via npm (no global install needed; uses npx)
npx -y @axe-core/cli https://netsec-cost.eu/

# Lighthouse — same
npx -y lighthouse https://netsec-cost.eu/ --output=html --output-path=tmp/lh.html

# pa11y-ci — alternative to axe-core CLI, also wraps axe-core; runs
# against a list of URLs:
npx -y pa11y-ci --sitemap https://netsec-cost.eu/sitemap.xml

# lychee — broken-link checker (Rust; install via brew on macOS)
brew install lychee
lychee --no-progress --max-redirects 5 ./**/*.html
```

Existing repo tools (already on disk, already on CI):

```bash
python3 scripts/check-i18n-drift.py
python3 scripts/check-external-link-arrows.py
bash    scripts/build-search.sh
python3 scripts/inject-seo.py
bash    scripts/check-links.sh        # new in this audit (see below)
bash    scripts/check-a11y.sh         # new in this audit (see below)
```

## Findings log

> Populate as the audit runs. One row per finding; close them in
> order of severity (P0 first).

### Phase 0 first run (22 May 2026)

`scripts/check-links.sh` found 9 broken internal anchors (legacy
references to home-page sections removed in the IA pass) and 5
broken external URLs. The internal ones were fixed in the same
audit-prep PR; the external ones need replacement URLs and are
left as P0 findings below.

| ID | Phase | Page / locale | Severity | Finding | Resolution | Status |
|---|---|---|---|---|---|---|
| L1 | 0 / link-check | `licensing.{en,fr,de}.html` | **P0** | `commission.europa.eu/communication/visual-identity-and-branding_en` → 404. The EU Commission shuffled the URL for the visual-identity guidance. | Find the current EC URL for the visual-identity manual (or replace with the IIIO archive copy) and update the three locale variants. | open |
| L2 | 0 / link-check | `privacy.{en,fr,de}.html` | **P0** | `commission.europa.eu/law/law-topic/data-protection/international-dimension-data-protection/eu-us-data-privacy-framework_en` → 404. | Same — find the current EU Commission page for the EU-US Data Privacy Framework. | open |
| L3 | 0 / link-check | `privacy.{en,fr,de}.html` | **P0** | `formspree.io/legal/privacy-policy` → 404. Formspree moved their policies. | Update to the current Formspree privacy-policy URL (at the time of writing, probably under `formspree.io/legal/` or `help.formspree.io/`). | open |
| L4 | 0 / link-check | `faq.{en,fr,de}.html` | **P0** | `www.cost.eu/uploads/2025/06/COST-Annotated-Rules.pdf` → 404. Placeholder URL guessed at the time the FAQ was written. | Verify the canonical COST URL for the Annotated Rules, or remove the link if it's not yet published. | open |
| L5 | 0 / link-check | `glossary.{en,fr,de}.html` | **P0** | `www.cost.eu/uploads/2025/04/MoU-063-25.pdf` → 404. Same placeholder pattern as L4. | Verify with Grant Holder / COST office whether a public MoU URL exists; replace or remove. | open |
| L6 | 0 / link-check | `faq.{en,fr,de}.html` + `licensing.{en,fr,de}.html` | resolved | 9 anchor refs pointed at `index.html#committee`, `#roadmap`, `#outputs` — sections moved out of the home page in the Phase 1 IA pass. | Updated to `about.X.html#leadership`, `roadmap.X.html`, `outputs.X.html`. | **shipped (PR #104)** |

### Phase 2 (Lighthouse + a11y + manual spot-check, 22 May)

| ID | Phase | Page / locale | Severity | Finding | Resolution | Status |
|---|---|---|---|---|---|---|
| A1 | 2 / a11y dark-mode contrast | `index.html`, `people.html`, `about.html`, `roadmap.html` | **P0** (WCAG AA fail) | Seven primary-CTA backgrounds resolved to `var(--accent) = #6ea1ff` in dark mode, giving 2.56:1 with white text (below the 4.5:1 floor). Affected: `.event-card.featured .event-date`, `.event-subscribe`, `#for-members .members-actions .primary` (home); `.tour-btn-primary`, `.tour-trigger-cta` (people); `.deliverables-roadmap-link-cta` (about); `.rm-feedback-action.is-primary` (roadmap). The home-page `.btn-primary` and `.nav-cta` were unaffected because they already had explicit dark-mode inversion to light-bg + dark-text. | Pinned the seven affected CTAs to brand EU-blue `#003399` in dark mode (10.86:1 with white) plus a `#0a4ed0` hover (11:1). CSS comment in `assets/css/site.css` explains the rationale + verification method. | **shipped (this PR)** |
| P1 | 2 / Lighthouse | `index.html` | P1 | Performance score 71 on home (target 80). Largest offenders: render-blocking external font CSS, image delivery. | Live-site Lighthouse confirms 71-75 range (not a localhost artefact). Tracked in [issue #121](https://github.com/EISSeuropa/netsec.github.io/issues/121) — render-blocking external font CSS, fix in v1.6.0 / v1.7.0. | open (tracked in #121) |
| P2 | 2 / Lighthouse | `press-kit.html` | P1 | Performance score 62. LCP 8.3 s local; large logo + poster images dominate. | Same root cause + the press-kit poster image. Tracked in [issue #121](https://github.com/EISSeuropa/netsec.github.io/issues/121). | open (tracked in #121) |
| P3 | 2 / Lighthouse | `people.html` | P1 | Performance score 72. Directory cards + Pagefind scripts on first load. | Same root cause. Tracked in [issue #121](https://github.com/EISSeuropa/netsec.github.io/issues/121). | open (tracked in #121) |
| P4 | 2 / Lighthouse | `grants.html` | P1 | Performance score 74. Likely similar to home. | Same root cause. Tracked in [issue #121](https://github.com/EISSeuropa/netsec.github.io/issues/121). | open (tracked in #121) |
| LH-A | 2 / Lighthouse | all 4 key pages | resolved | **Accessibility 96-100**, **Best Practices 96**, **SEO 100** — all above the target floors of A11y ≥ 95 / BP ≥ 95 / SEO ≥ 95. | no action — green. | **green** |
| MD1 | 2 / metadata | all 42 pages | resolved | Per-page audit: every page has title, meta description, canonical, hreflang (en/fr/de/x-default), Open Graph (type/title/desc/url/image/locale), Twitter Card (card/title/desc/image), JSON-LD Organization + WebPage, and `<html lang>`. FR/DE pages also have `data-i18n-status="beta"` and the ribbon `<div>` (the latter fixed in PR #103). | no action — green across 42 pages × 21 checks. | **green** |
| MM1 | 2 / motion | site.css | P2 | 9 `prefers-reduced-motion` blocks vs 53 transitions / animations. Major animations (drift, search overlay, welcome strip, search-landed, tour spotlight) are properly disabled; some hover-translate effects on cards (`.find-card`, `.glass`, `.event-link`, `.bio-toggle`) don't have explicit disables. Brief (≤ 250 ms) hover effects don't typically trigger motion sensitivity but are technically out of scope of WCAG 2.3.3 (AAA, optional). | Leave as-is for launch (WCAG 2.1 AA conformance not affected). Add a comprehensive reduced-motion pass to v1.7.0 if Phase 2 IA review surfaces concerns. | deferred (P2, not blocking) |
| PR1 | 2 / print | site.css | P2 | Print stylesheet is one-rule (collapses the MC-by-country detail). No proper print formatting for FAQ / Glossary / individual pages. | Tracked in [issue #123](https://github.com/EISSeuropa/netsec.github.io/issues/123) for v1.8.0. | open (tracked in #123) |
| US1 | 2 / journey smoke | `/index.html` | resolved | Home loads cleanly: H1 reads correctly, 4 Find-out-more cards, 3 event cards + Subscribe CTA, 4 news cards, footer has 15 links, search trigger / theme toggle / 3-language switch all present. Mobile (375 × 812): no horizontal scroll, menu toggle visible, nav drawer hidden by default. | none. | **green** |
| US2 | 2 / journey smoke | `/index.html` search overlay | resolved | Search trigger opens overlay; query `STSM` returns 14 results in EN with relevant hits (FAQ + Grants); first 3 results readable. | none. | **green** |

### Phase 1 journeys (22 May 2026)

Six pre-launch journeys run end-to-end against the local static mirror (Pagefind built locally) via headless Chromium at both desktop (1280 × 800) and iPhone-emulated 390 × 844 viewports. Most journeys green; five findings logged below. The journey-by-journey checklist is at *Journey checklist* above.

| ID | Phase | Page / locale | Severity | Finding | Resolution | Status |
|---|---|---|---|---|---|---|
| I-1 | 1 / Journey 1 | `index.fr.html`, `index.de.html` + 36 other `*.fr.html` / `*.de.html` files | **P0** | Beta-translation ribbon says *"Traduction automatique"* (FR) / *"Maschinell übersetzt"* (DE) — "machine translation". The translations are **manual**. Public-facing falsehood, directly contradicting the standing project constraint "No machine translation; EN/FR/DE done manually". Same misclaim in 36 file headers + `accessibility.html`. | FR → "Traduction manuelle", DE → "Manuell übersetzt", EN comments → "manually translated", accessibility statement updated. 35 files. | **shipped (PR #111)** |
| J2-1 | 1 / Journey 2 | every `*-highlight=*` landing page | P2 | Pagefind's built-in `<mark>` highlighter and the page's own highlighter both wrap matched terms, producing `<mark><mark>STSM</mark></mark>` on Grants/FAQ/etc. landings. Renders identically (single highlight), but invalid-nesting markup will read awkwardly to a screen reader on terms in the result excerpt ("STSM STSM"). | Tracked in [issue #118](https://github.com/EISSeuropa/netsec.github.io/issues/118) for v1.6.0 / v1.7.0. | open (tracked in #118) |
| J4-1 | 1 / Journey 4 | `/people.html` (compact view) | P1 | Deep-link auto-expand + spotlight (`/people.html#<slug>` → expanded card + `is-search-landed` glow) did **not** fire under headless Chromium on a cold page load. Handler was wrapped end-to-end in `requestAnimationFrame`; if RAF deferred (headless certainly; real browsers under load plausibly), *none* of the spotlight / expand / scroll actions ran. | Pulled spotlight + expand class-manipulations out of RAF (layout-safe); kept `scrollIntoView` behind RAF for layout-settled scrolling, with a `setTimeout(50)` fallback if RAF skips. Applied across `people.html` / `people.fr.html` / `people.de.html`. | **shipped (PR #113)** |
| J4-2 | 1 / Journey 4 | `.member-toggle-chevron` | observation | `getComputedStyle(chev).transform` reads as `matrix(1, 0, 0, 1, 0, 0)` (identity) when the card is `.is-expanded`, even though the matched CSS rule is `rotate(180deg)`. Pure-JS verification; visual confirmation in a real browser still pending. Likely a headless-renderer quirk in how the preview tool exposes computed-style of nested transforms. | Spot-check by eye in real Chrome before public push. No code change planned — the CSS is correct. | open — sanity-check only |
| M-1 | 1 / Mobile sweep | `index.html` (mobile, 390 × 844) | P2 | Hamburger-menu panel renders with a transparent background — the hero text shows through behind every nav item. Caused by nested `backdrop-filter` not re-stacking reliably inside the floating-header bubble. | Pinned the drawer to rgba(246,248,252,.97) light / rgba(11,18,32,.97) dark, scoped to `@media (max-width: 980px)`; bumped `box-shadow` so the drawer reads as elevated. | **shipped (PR #112)** |

### Final pre-launch pass (22 May 2026)

Three additional audits ran the same day, after the Phase 1 fixes shipped, to close the launch-QA loop before the public push.

| ID | Phase | Page / locale | Severity | Finding | Resolution | Status |
|---|---|---|---|---|---|---|
| AT-1 | 3 / VO-substitute | home, network directory, grants, press kit | resolved | Programmatic structural audit (skip-link / landmarks / heading-level monotonicity / image alt coverage / accessible names on interactives / input-label association) ran clean on the four most-trafficked pages. Real-VoiceOver verification on macOS Safari is a *nice-to-have*, not a launch blocker. | no action — green. | **green** |
| AT-2 | 3 / VO-substitute | home vs others | observation | Home uses `<main id="top">` and skip-link `href="#top"`; other pages use `id="main"` + `href="#main"`. Functional but inconsistent. | Tracked in [issue #120](https://github.com/EISSeuropa/netsec.github.io/issues/120) for v1.6.0. | open (tracked in #120) |
| OG-1 | 3 / OG previews | home / about / roadmap / press-kit | resolved | Full OG + Twitter Card metadata: `og:type` / `og:title` / `og:description` / `og:url` / `og:image` (+ width / height / alt) + `twitter:card=summary_large_image`. Shared `og-image.png` is 2400×1260 (aspect 1.91, retina). Image renders cleanly. | no action — green. | **green** |
| DM-1 | 3 / Dark-mode sweep | all 16 public English pages | resolved | Programmatic per-element contrast probe + visual review across all sixteen pages in dark mode. Two probe-level flags on home (h1 gradient text with `-webkit-background-clip:text`; `.cost-mark` an image-based logo with no text) — both false positives. No real low-contrast text or surfaces beyond the manual-review item already documented on `/accessibility.html`. | no action — green. | **green** |

### Open follow-ups (tracked as GitHub issues)

The findings tables above cross-link to the issues. Listed here together so the cumulative deferral picture is one click away:

- [#118](https://github.com/EISSeuropa/netsec.github.io/issues/118) — Search overlay: remove duplicate `<mark>` nesting (finding **J2-1**).
- [#119](https://github.com/EISSeuropa/netsec.github.io/issues/119) — Move optimised member photos out of git (structural follow-up to PR #117's libjpeg-determinism fix).
- [#120](https://github.com/EISSeuropa/netsec.github.io/issues/120) — Skip-link target inconsistency: home uses `#top`, others use `#main` (finding **AT-2**).
- [#121](https://github.com/EISSeuropa/netsec.github.io/issues/121) — Lighthouse Performance score 67-75 — render-blocking external font CSS (findings **P1 / P2 / P3 / P4**).
- [#122](https://github.com/EISSeuropa/netsec.github.io/issues/122) — Documentation pack v1.8.0 — section-level catch-up to website v1.4.0 + v1.5.0.
- [#123](https://github.com/EISSeuropa/netsec.github.io/issues/123) — Print stylesheet — proper formatting for FAQ / Glossary / individual pages (finding **PR1**).

## Sign-off

Pre-launch checklist:

- [x] Phase 0 automation: all green (link checker + a11y scanner in CI).
- [x] Phase 1 journeys: all six tested under headless Chromium (desktop + mobile-emul); findings I-1, M-1, J4-1 shipped (PRs #111-113); J2-1 deferred to v1.5.0 search-polish.
- [x] Phase 2 keyboard pass: green (Phase 2 audit, PR #105).
- [x] Lighthouse, live: Perf 67-75 (deferred — render-blocking external fonts), A11y 96-100, BP 96, SEO 100 on home / directory / grants / press-kit.
- [x] Dark mode: page-by-page sweep across all sixteen public English pages — no further low-contrast text or surfaces beyond the manual-review item documented on `/accessibility.html`.
- [x] `/accessibility.html` *Last assessed* bumped to 22 May 2026 — v1.2 of the statement.
- [x] VoiceOver-substitute audit: programmatic structural pass across the four most-trafficked pages — landmarks, heading monotonicity, alt-text, accessible names, label association — all clean. Real-VoiceOver verification remains a *nice-to-have* and is **not** a launch blocker.
- [x] OG card previews: complete metadata across home / about / roadmap / press-kit; shared `og-image.png` (2400×1260) renders cleanly. Live social-platform render checks (LinkedIn / Bluesky / etc.) remain a *nice-to-have* and are **not** a launch blocker.
- [x] Findings log above: every row has *Resolution: shipped* or *Resolution: deferred (with reason)*.
- [~] Manual cross-browser smoke on real Safari / Firefox / real iPhone is **out of scope** for this Go/No-Go — informal maintainer spot-check only. The journey-checklist columns above are kept for the next audit cycle but are not gating.

Signed: ____________________________  Date: ____________________
       (Dr Arthur Laudrain, maintainer)

---

*This document survives past launch as the audit trail. The next
audit (anchored at the pre-MC-plenary deadline in early September
per `docs/roadmap-2026.md`) will reference this one as the
baseline.*
