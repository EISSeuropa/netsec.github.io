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

| Journey | Chrome | Safari | Firefox | iPhone emul |
|---|---|---|---|---|
| 1 Home landing | | | | |
| 2 Search STSM | | | | |
| 3 Press kit | | | | |
| 4 Directory card | | | | |
| 5 Join form | | | | |
| 6 Calendar subscribe | | | | |

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
| L6 | 0 / link-check | `faq.{en,fr,de}.html` + `licensing.{en,fr,de}.html` | resolved | 9 anchor refs pointed at `index.html#committee`, `#roadmap`, `#outputs` — sections moved out of the home page in the Phase 1 IA pass. | Updated to `about.X.html#leadership`, `roadmap.X.html`, `outputs.X.html`. | **shipped (this PR)** |

## Sign-off

Pre-launch checklist:

- [ ] Phase 0 automation: all green.
- [ ] Phase 1 journeys: all six green on Chrome / Safari / Firefox / iPhone emul.
- [ ] Phase 2 keyboard pass: green.
- [ ] Phase 2 VoiceOver spot-check: green.
- [ ] Lighthouse: Perf ≥ 80, A11y ≥ 95, BP ≥ 95, SEO ≥ 95 on home / directory / grants / press-kit.
- [ ] OG previews: home + about + roadmap previewed on at least one social
      platform and visually correct.
- [ ] Dark mode: every page readable.
- [ ] `/accessibility.html` *Last assessed* bumped.
- [ ] Findings log above is empty *or* all rows have *Resolution: deferred (with reason)* or *Resolution: shipped*.

Signed: ____________________________  Date: ____________________
       (Dr Arthur Laudrain, maintainer)

---

*This document survives past launch as the audit trail. The next
audit (anchored at the pre-MC-plenary deadline in early September
per `docs/roadmap-2026.md`) will reference this one as the
baseline.*
