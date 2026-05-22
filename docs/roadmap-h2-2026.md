# Website & directory roadmap — H2 2026

> *Audience: Action Chair, Vice-Chair, MC members, and the site
> maintainer. This document sets expectations for what the NetSec
> website and the open community directory (Deliverable D1) will
> deliver between now and 31 December 2026.*

Maintained by Dr Arthur Laudrain (MC member, CH; ETH Zurich).
Last revised **22 May 2026**.

---

## Where we are today

As of May 2026 — month **M8** of the four-year Action — the
delivery state is:

- **Website live** at <https://netsec-cost.eu> on GitHub Pages,
  HTTPS-only, EN/FR/DE.
- **Ten public pages**: home, network directory, grants & calls,
  press kit, FAQ, glossary, sitemap, accessibility, privacy,
  licensing.
- **Open community directory** (D1, first version) accepting
  bios via a public Google Form. 13 members ingested at last
  weekly sync; the form is open to MC reps, WG participants, and
  the wider community.
- **Site-wide search** (Pagefind, EN/FR/DE shards) with rich
  bio result cards.
- **Documentation pack v1.6.0** (`docs/pdf/NetSec-website-
  documentation.pdf`) reflects the current site.
- **CHANGELOG** at SemVer v1.3.0; release tooling (`scripts/
  release.sh`) requires a short title per release.
- **Maintainer**: one person (AL) running on volunteered time.

---

## Anchors driving this roadmap

Three streams set the pace:

1. **The Action calendar** — what audiences (members, applicants,
   press) need to find on the site, and when.
2. **The MoU deliverables** — D-numbered outputs the website
   hosts as they reach their milestones.
3. **Open feedback and known polish items** — GitHub Issues
   #62 / #63 / #72, plus the threads in maintainer review.

### Action calendar (firm + expected)

| Date | Event | Site impact |
|---|---|---|
| **9–11 Jun 2026** | Early-Career Scholars Summer School (Stockholm University) | Liveness check on the event card, calendar feed up-to-date, post-event recap |
| **11–12 Jun 2026** | European Security Conference (Stockholm University) | Same; flagship outreach moment. **Official logos + social channels in place** (see Q2 ship list) |
| **Before late Sep 2026** | Inaugural Management Committee Plenary *(date TBA)* | Date confirmation on home page well ahead of the meeting; agenda + minutes path to the members' Wiki; site reads as the canonical entry point for new MC reps |
| **10 Oct 2026** | Year 1 anniversary (M12) | Year-1 retrospective; D1 first-version milestone |
| **Throughout** | STSM applications, conference grants | Calls visible on `/grants`, application flow stable |

### Deliverables milestones (Year 1, due by M12 = Oct 2026)

The website is **not** responsible for producing these
deliverables — they're the Action's intellectual outputs. The
site's job is to **host** each one when it lands, with a
permalink and the right metadata so external evaluators can find
it.

| D# | Title | Due (Action month → calendar) | Site responsibility |
|---|---|---|---|
| D1 | First version of NetSec directory (updated regularly) | M12 → **Oct 2026** | **Owned by this roadmap.** See below. |
| D6 | First policy briefs published | M12 → **Oct 2026** | New page or section under `/outputs`; permalink + DOI placeholder |
| D8 | Planning guidelines for STSM & grant system | M9 → **Jul 2026** | Already on `/grants`; refresh once final document is approved |
| D9 | Strategy for a working structure | M6 → **Apr 2026** (passed) | Verify the version on the site matches the approved version |
| D10 | First draft of risk management strategy | M10 → **Aug 2026** | Host as a PDF + summary on a new sub-page |
| D11 | Inclusion & diversity declaration | TBD | Promote prominently on the home page once available |
| D12 | Environmental sustainability guidelines | TBD | Same |

### Open issues in the repo

- **#62** *Icons and logos need implementation* — favicon, NetSec
  mark placements across site / PDF / poster, accessibility +
  SEO implications.
- **#63** *Social media integration* — channel choice (LinkedIn?
  Bluesky? others?), footprint on the site (footer chips only?
  dedicated landing strip?), privacy posture.
- **#72** *Directory: replace expand-in-place with a sticky side
  panel / bottom sheet* — deferred until membership growth
  warrants the engineering cost. Today's behaviour (in-place
  expansion + click-to-expand on compact cards + search-landing
  spotlight) is sufficient at 13 members. Trigger to act:
  membership past ~150, OR layout-disruption complaints.

---

## What we'll ship, by quarter

### Q2 wrap-up — May / June 2026 *(in progress)*

**Theme**: ship the search and brand polish so the Conference is
the moment NetSec's public identity reads as deliberate. **The
Conference + the inaugural MC plenary (before late Sep) both
benefit from official logos and social channels already being in
place** — so brand work is pulled into June, not deferred to Q3.

#### Pre-Conference (target: before **5 Jun 2026**)

- [x] Public FAQ and Glossary, multilingual (v1.3.0)
- [x] Site-wide search, including directory bios (v1.3.x → v1.4.0)
- [x] Calendar feed + Subscribe affordance
- [x] Header streamline (drop NetSec wordmark, search trigger fits)
- [x] Release-title convention (every release reads as a thesis,
      not just a version number)
- [ ] **Pre-Conference dry-run on the live site**: verify the
      Summer School + ESC cards link out correctly, that the
      `webcal://` Subscribe button works on Apple Calendar /
      Outlook / Google Calendar, and that the news block is
      ready for live updates during the week of 9–12 June.
- [ ] **Cut v1.4.0** — bundles the recent fixes + the directory
      search additions. Title: *Search the directory, polished
      header*.

#### Pre-July — brand identity + social presence (target: before **30 Jun 2026**)

The Action's first public mass-outreach moments (Conference,
Summer School, then the inaugural MC plenary) all benefit from
having a finalised visual identity and live social channels
*before* they happen, not after. The pre-Conference dates would
be ideal; the firm deadline is **end of June**.

- [ ] **Issue #62 — official logos and favicon**. Replace the
      placeholder NS-square mark and favicon with the Action's
      approved official versions. Audit logo placements across
      the site, the PDF documentation pack, the promotional
      poster, and the press kit. Verify the OG / Twitter Card
      / Bluesky preview images still render correctly with the
      new mark. *Blocker: receive the approved final-form logos
      from the Action Chair / WG4 lead.*
- [ ] **Issue #63 — social media presence**. Channels live,
      handles registered (consistent across networks), profile
      art using the new logos, biographies in EN/FR/DE.
      Footprint on the site: footer chips, press-kit page row,
      and a small *Follow us* card in the home-page *Find out
      more* grid. *Working proposal (pending decision):
      LinkedIn primary + Bluesky secondary, no X.*
- [ ] **Cut v1.5.0** — title: *Official logos + social channels
      live*. Ships the visual identity refresh, the social-media
      surfaces, and any small polish from the Conference dry-run
      feedback.

### Q3 — July / August / September 2026

**Theme**: harden the infrastructure, host the first Year-1
deliverables, prepare the site to be the canonical entry point
for new MC reps joining around the **inaugural MC plenary**
(before late September).

#### Content & deliverables

- **Post-event recap** for the Conference and Summer School on
  the news block. Photo gallery (a small one — opt-in basis
  from participants), participant feedback summary, recordings
  link if available.
- **Host D8** (STSM planning guidelines, M9 ≈ Jul) as a
  permalink on the Grants page once the Grant Awarding
  Coordinator approves the final document.
- **Host D10** (risk management strategy, M10 ≈ Aug) — likely
  a new sub-page `/risk-management.html` with the PDF embedded
  and a short summary; or appended to the existing
  Documentation Pack appendix if the strategy is short.
- **Inaugural MC plenary** — date confirmation on home page as
  soon as known; agenda + minutes path to the members' Wiki
  finalised; the *For NetSec members* strip and the Wiki
  *Onboarding* page reviewed for new MC reps arriving via the
  plenary.

#### Features

- **FR / DE review pass on FAQ + Glossary content**. The
  translations are beta — flag a single native-speaker review
  per locale to lift them out of the beta banner.
- **Per-event `.ics` files + Add-to-calendar buttons.** Rounds
  out the calendar story shipped in v1.3.x — each event card
  gets a single-event download alongside the master Subscribe
  feed.
- **News RSS feed.** Generated from the news block at build
  time; academic + policy audiences still consume RSS.
- **Search acronym-synonyms.** `STSM` ↔ *Short-Term Scientific
  Mission*, `ITC` ↔ *Inclusiveness Target Country*, etc., via
  a small per-page keywords meta table.
- **Search index auto-rebuild** (consideration only — see *Open
  questions* below).

#### Quality (pre-MC plenary)

- **Pre-MC-plenary accessibility + cross-browser audit** —
  scope spelt out in the *Quality, accessibility, performance*
  theme below. Anchored at **early Sep**, ahead of the plenary
  date.
- **Performance audit** — Lighthouse + Core Web Vitals baseline
  on the four heaviest pages.
- **Homepage + header IA audit** (Jul–Aug). Written
  recommendation document, mirror of `search-assessment.md`.
  Output feeds the homepage restructure in v1.7.0. See the
  *Homepage IA* theme below for scope.

#### Infrastructure

- **Dependabot for GitHub Actions**: weekly checks on the
  pinned action SHAs (`actions/checkout@v4`, `actions/setup-
  node@v4`, `peter-evans/create-pull-request@v7`,
  `pagefind@1.5.2`). Auto-PR when a security update is
  available. *Drive-by from the GitHub App installation token
  format watch — having Dependabot on `actions` gives us the
  fix automatically if `peter-evans/create-pull-request` ships
  one.*

### Q4 — October / November / December 2026

**Theme**: Year-1 retrospective + ready Year 2.

#### Content & deliverables

- **D1 first-version milestone (M12, ~10 Oct 2026)**. By this
  date the directory needs to:
  - hold ≥30 members (back-of-envelope target; today's 13
    grows by ~5/month if the form intake stays steady),
  - be searchable by name and by working group,
  - have FR + DE chrome at least at the same level as today,
  - carry a *Year 1* milestone note on the home page,
  - have a stable URL pattern for sharing individual entries.
- **D6 first policy briefs** (M12) hosted on a new page or
  section, with citation metadata baked in (DOI placeholder,
  schema.org `ScholarlyArticle` JSON-LD). One brief minimum;
  more if available.
- **Year-1 retrospective** post on the news block on 10 Oct
  2026 — what shipped, who joined, what comes next.
- **Inclusion & diversity declaration (D11)** and
  **environmental sustainability guidelines (D12)** promoted
  on the home page when available.

#### Features

- **Outputs section refresh** (v1.7.0). Real card design for
  D6 policy briefs, `schema.org/ScholarlyArticle` JSON-LD,
  filter/sort if briefs accrue past ~10.
- **URL-encoded directory filter state** (v1.7.0). Shareable
  pre-filtered directory links — `/people.html?wg=3&country=fr`
  opens the directory with WG3 members in France already
  filtered.
- **Per-page Open Graph images** (v1.8.0). Distinct OG cards
  per page (FAQ, Grants, Press kit) so social previews tell
  the right story.
- **Print stylesheet for FAQ + Glossary** (v1.8.0). Researchers
  occasionally want offline hard copy.
- **Issue #72 reassessment**. By end-November we re-evaluate
  whether the directory's expand-in-place pattern is still
  serving. If membership has crossed the ~150 mark or if MC
  members are reporting friction, kick off the sticky-side-
  panel work for Q1 2027.
- **Member self-edit** — if the Google Form pipeline shows
  friction (members want to update bios faster than the
  weekly sync), spike a *Suggest an edit* CTA on each card
  that pre-fills the form with the existing bio. Decision
  point: only if at least 3 MC members ask for it.

#### Quality

- **Year-1-close audit** — focused re-test on whatever D6 /
  D11 / D12 surface lands, plus the *Outputs* section refresh.
  Light touch compared to the Q3 audit.

#### Releases & docs

- **v1.7.0** — Year-1 milestone release alongside D1's M12.
  Title: *Year 1 closes*.
- **v1.8.0** — late-December "Year 2 ready" release if scope
  warrants; PATCHes otherwise.
- **Documentation pack** bumped at each website MINOR release,
  in step with the website. (Pack version is independent of the
  website version axis — see CHANGELOG header.)

---

## Cross-quarter themes

Beyond the dated items above, four themes run through the half:

### 1 · Directory growth + UX

The directory has been the showcase since launch. As the member
count climbs, the trade-offs shift:

- Under **~30 members**: today's filter (search × WG/MC ×
  country) is the right tool. Expand-in-place handles individual
  card reading.
- **30–150 members**: filter usage probably plateaus; visitors
  start arriving via search or shared deep-links. The new
  search-landing spotlight is the bet for this band.
- **Past ~150**: the sticky-side-panel pattern (#72) becomes
  worth the engineering. The decision deadline is end-November.

### 2 · Homepage + header IA — surviving content growth

The home page has accreted 10 sections since v1.0; the floating
header runs at 10 nav items (capacity, post-wordmark-removal).
Every Year-1 milestone adds more content:

- **News block** will gain Conference + Summer School recaps in
  June, then monthly highlights, then post-plenary updates.
- **Outputs** currently shows three *Forthcoming* placeholders;
  D6 (policy briefs) makes it real in October and the section
  will keep accruing.
- **Events** will collect past + upcoming entries; a year out
  we'll need a "Past events" treatment.
- **D11 / D12** when they ship may need their own homepage
  presence (Inclusion & diversity, Environmental sustainability).
- **Find out more** grid + **For NetSec members** strip — both
  recently added (v1.3) — sit close together in the page and
  arguably compete for the same after-About attention.

Without a proactive pass, this gets messy and confusing.
Specific risks I can name:

- **No visual hierarchy** beyond ordering — every section uses
  similar weights, so nothing reads as "more important".
- **Long-scroll fatigue**, especially on mobile (10 sections
  × phone screen ≈ a lot of swiping).
- **First-time visitor** vs. **returning member** want
  different things from the same page: the new visitor wants
  *"what is NetSec"*; the returning visitor wants news /
  grants / directory.
- **Header at capacity** — there's no room for a new top-level
  page without restructuring; even *Outputs* / *Roadmap* are
  arguably internal-jargon labels that a journalist wouldn't
  parse instantly.
- **Audience tracks** (researcher, policy-maker, MC member,
  press) aren't differentiated; they all follow the same path.

#### What an IA pass would cover

A structured audit produces a written recommendation, not a
redesign. Scope:

- **Current-state inventory** — every section measured for
  content density, time-to-find for common tasks, mobile
  behaviour. Including: how does the home page perform for
  the visitor who arrives via search vs. direct vs. social?
- **Header IA** — does the flat 10-item nav still work, or
  should we group into dropdowns (e.g. *Activities* >
  Events / Grants / Training; *Reference* > FAQ / Glossary /
  Press kit)? Cost vs. benefit of each grouping vs. a flat
  list.
- **Homepage structure** — current order vs. an alternative
  rooted in audience tracks. Options to explore: sticky
  table-of-contents for long-scroll, mobile-specific section
  reordering, an *I'm a…* chooser at the top, offloading
  Outputs to a dedicated `/outputs.html` page.
- **Content lifecycle** — pagination / archive treatment for
  News and Events as they accumulate.
- **Consolidation** — *Find out more* grid + *For NetSec
  members* strip overlap; should one absorb the other, or
  should they sit further apart?
- **Future-proofing** — explicit positioning for the next 3-6
  homepage entries (D6 policy briefs, D11, D12, possibly a
  publications hub).

#### Timing — two phases

The biggest hidden cost of waiting for one big audit is that
the **official logos ship in v1.5 into a known-suboptimal IA,
then restructure in v1.7** — two brand-facing changes in four
months. Splitting the audit into two passes avoids that:

**Phase 1 — Structural quick-pass (this week)**

- 1–2 days of work, maintainer alone
- Focus: the structural decisions that need to land **before
  the v1.5 logo refresh** (consolidate the *Find out more* +
  *For NetSec members* overlap, regroup nav into dropdowns or
  not, sticky TOC on home or not, offload *Outputs* to its
  own page or wait for D6, etc.)
- Output: a written audit doc at `docs/homepage-ia-quick-
  audit.md` mirroring the `search-assessment.md` shape —
  issues, options, recommendations, costs per change.
- No consulting needed at this stage.

**Phase 2 — Detailed UX pass (July–August 2026)**

- Post-Conference, post-Summer School (so we have real recap
  content to audit against)
- Post-v1.5 (so the audit happens against the real new
  visual identity, not placeholders)
- Optional consulting time here — same budget question as
  the original framing, just deferred to where the consulting
  budget pays off most.
- Output: deeper recommendations covering audience tracks,
  mobile patterns, content lifecycle, future-proofing for
  D6 / D11 / D12 / publications hub.

#### Implementation

- **v1.5.0 (late June)** absorbs the Phase 1 quick-wins
  alongside the brand refresh. Release title shifts to
  *Logos, socials, IA polish* to flag the broader scope.
- **v1.7.0 (mid Oct)** ships the deeper restructure from
  Phase 2 alongside the Year-1 close.

#### Open question

**Bring in a UI / UX professional for the Phase 2 audit?** A
few hours of an experienced practitioner's time produces a
substantively better recommendation than I can on my own,
particularly on audience-track separation and mobile patterns.
Decision owner: **Action Chair** (budget question). My
on-my-own version is the fallback if there's no budget.
Phase 1 runs without consulting regardless.

### 3 · Content cadence — deliverables hit the site

The site's value over 2026 grows as each MoU deliverable
publishes. The maintainer's commitment is **48-hour turnaround**
from approved-PDF-in-hand to live-on-site, with:

- a stable permalink,
- citation metadata (JSON-LD where appropriate),
- a news-block announcement,
- a press-kit-style social card if the deliverable warrants
  outreach.

### 4 · Quality, accessibility, performance

Last formal a11y audit shipped with **v1.0** (20 May). Between
then and now we've added a substantial surface area — search
overlay (modal, keyboard nav, focus trap, lazy WASM), directory
click-to-expand + search-landing spotlight, FAQ / Glossary with
deep-link anchors, press kit, *For NetSec members* strip, *Find
out more* grid, external-link auto-icon, calendar Subscribe
button, Pagefind `<mark>` painting, bio cards in search,
⌘K / `/` shortcuts. None of those have had a formal pass.

Three audit moments scheduled for H2:

#### **Pre-v1.5 audit (mid-to-late Jun 2026)** — comprehensive

Covers everything shipped between v1.0 and the brand refresh.
Necessary because v1.5 swaps in official logos that may shift
contrast ratios on icons / chips / shadows; auditing *before*
is the cheaper order than re-doing the audit after.

Scope:

- **Colour contrast (WCAG 2.1 AA, 4.5:1 text / 3:1 large)** — re-run
  on light + dark for: external-link icon, search-result cards
  (incl. bio cards), `<mark>` highlight, search-landing
  spotlight, calendar Subscribe button, *Find out more* cards,
  *For NetSec members* strip, FAQ / Glossary anchor `:target`
  state, news-card buttons.
- **Keyboard navigation** — full tab traversal of every page;
  visible focus indicators everywhere; no focus traps outside
  the search overlay. Verify ⌘K / Ctrl-K / `/` shortcuts in
  Chrome / Firefox / Safari (Mac) and Chrome / Firefox / Edge
  (Windows).
- **Screen-reader smoke test** — VoiceOver on macOS + NVDA on
  Windows. Specifically: the search overlay's modal semantics,
  `aria-live` result count, directory card auto-expand
  announcements, the `data-pagefind-body`-marked content vs.
  the (ignored) nav and footer.
- **Reduced motion** — confirm the spotlight scale-in, the
  overlay slide-in, and the bio-card hover transforms all
  respect `prefers-reduced-motion`.
- **Resize / zoom** — text-only zoom to 200 %, full-page zoom
  to 200 %; layout doesn't break, no horizontal scroll, no
  clipped content. Headers stay usable on the floating bubble.
- **Mobile** — touch tap targets ≥ 44 × 44 CSS px on all
  interactive elements (search trigger, overlay close,
  navigation, footer chips). Conference-week visitors will be
  on phones.
- **Translation** — `<html lang>` correct on every variant;
  `lang` attribute on inline foreign-language fragments where
  applicable; `:lang(fr)` / `:lang(de)` CSS rules still apply.

Method: axe-core CLI run across every page + locale (≈ 30
pages × 3 locales), spot-checks with the manual scripts above,
quick Lighthouse runs as a sanity check.

Output: a published a11y-audit report appended as Appendix to
the documentation pack; updated *Last assessed* date stamp on
`/accessibility.html`.

#### **Pre-MC-plenary audit (early Sep 2026)** — cross-browser + perf

The inaugural MC plenary brings 30+ new visitors who will form
their first impression of the site. Catch the long-tail issues.

Scope:

- **Cross-browser** — full smoke pass on Safari (Mac + iOS),
  Firefox (desktop + mobile), Edge, plus the Chrome baseline.
  Specific risks: `:where()` specificity (used in the external-
  link icon CSS) on older Safari, the `webcal://` Subscribe
  link on non-Apple platforms, Pagefind WASM on older
  browsers.
- **Cross-platform** — verify the directory looks right on
  Windows Edge, on a small Chromebook screen, on a phone in
  one-handed reach.
- **Performance** — Lighthouse run on the four heaviest pages
  (home, directory, FAQ, press kit). Target: ≥ 90 on every
  metric. Verify the page-weight budget hasn't drifted
  (baseline: ~140 KB excluding `bios.json`; Pagefind adds
  ~80 KB on first overlay open).
- **Core Web Vitals** — LCP, INP, CLS via WebPageTest.
- **Lighthouse SEO** — verify the new pages (FAQ, Glossary, the
  bio stubs) carry the right canonical + JSON-LD.
- **Re-run the axe-core suite** with any v1.5 deltas folded in.

#### **Year-1-close audit (mid Oct 2026)** — light touch

A focused re-test on whatever D6 / D11 / D12 surface lands in
v1.7.0. Plus a sweep of the *Outputs* section refresh (see
*Feature candidates* below). **And: a re-pass over whatever the
homepage IA audit recommended that landed in v1.7.0** — new
sectional groupings, dropdown nav, or audience-track strips all
need their own keyboard / screen-reader / mobile coverage.

Performance budget stays at the v1.0 number: **~140 KB
uncompressed page weight excluding bios.json**. The Pagefind
runtime (~80 KB on first overlay open) is the only meaningful
delta and is lazy-loaded.

### 5 · Feature candidates

Beyond what the release plan already commits to (search, brand,
deliverable hosting), these are the candidates worth queueing.
Each has a rough cost estimate and a decision point.

#### Round out the calendar story

- **Per-event "Add to calendar" buttons.** The `calendar.ics`
  master feed shipped in v1.3.x; this adds a one-shot
  `/calendar/<slug>.ics` per event so an MC member sharing a
  conference link can include the single-event invite. Cost:
  ~½ day. Slots into **v1.6.0**. Decision: ship as part of
  Q3.
- **RSS feed for the news block.** Academic + policy
  communities still consume RSS; the news block is small
  enough to render as Atom or RSS from `index.html` at build
  time. Cost: ~1 day (Python script + a workflow trigger).
  Slots into **v1.6.0**. Decision: ship as part of Q3.

#### Search improvements

- **Acronym synonyms.** Today `STSM` and `Short-Term
  Scientific Mission` are separate queries. Pagefind has a
  `data-pagefind-meta="keywords"` mechanism — adding a
  central acronym table baked into the relevant pages would
  let either form match. Cost: ~½ day. Slots into v1.6.0
  alongside the FR/DE review pass.
- **Result-type filter chips** (*All / Pages / People*) in
  the overlay header. Quality-of-life when both a page and a
  bio match the same query. Cost: ~1 day. Optional for v1.6;
  could defer if Q3 is tight.

#### Outputs section refresh

The `/outputs` section on the home page currently shows three
*Forthcoming* placeholder cards. **D6** (policy briefs) lands
in October as part of the Year-1 close. We need:

- A real card design with metadata (authors, date, abstract).
- A landing page per brief if briefs are PDF + abstract.
- `schema.org/ScholarlyArticle` JSON-LD for SEO + Google
  Scholar indexing.
- Filter / sort if briefs accrue past ~10.

Cost: ~2 days. Hard-blocked on the first brief being
production-ready. Slots into **v1.7.0** (*Year 1 closes*) by
design.

#### Directory ergonomics

- **URL-encoded filter state.** Today, `/people.html#stsm` opens
  Arthur's card; `/people.html?wg=3&country=fr` should open
  the directory pre-filtered to *WG3 members in France*.
  Powerful for share-links among the MC. Cost: ~1 day. Slots
  into **v1.7.0** (sized to match the Year-1 close moment).
- **Member self-edit CTA.** Still gated on at least 3 MC
  members asking for it. Visibility only.
- **Sticky side panel (#72).** Re-evaluate end-November as
  before — trigger is membership > 150 OR friction reports.

#### Engagement

- **Newsletter signup** (Formspree-backed, no analytics, no
  list-management dashboard — the form just forwards to the
  Action mailbox). Cost: ~½ day. Decision: only if the AC
  wants a newsletter channel and is willing to maintain the
  cadence. Otherwise skip.
- **Print stylesheet for FAQ + Glossary.** Researchers
  occasionally want hard copy for offline reference. Cost:
  ~1 day. Nice-to-have.

#### Operational

- **Open Graph image per page** — currently one global
  `og-image.png` shows for every share. Distinct per-page
  cards (FAQ uses one, Grants another, etc.) improve social
  preview quality. Pre-rendered at build time. Cost: ~1 day
  including OG-image design.

#### What I'm *not* proposing

A few patterns I considered and chose to skip, with reasons —
in case any of these surprises you:

- **Analytics / tracking pixels.** Violates the established
  privacy posture (no third-party trackers documented in
  `/privacy.html`). No change.
- **Search analytics** — same reason.
- **Comments on news / FAQ entries** — moderation burden + spam
  risk + accessibility complexity. Use the contact form.
- **Service worker / offline mode** — overkill for a content
  site; ROI not there yet.

### 6 · Infrastructure & DevOps hygiene

- **Release immutability** on GitHub Releases: enabled at the
  repo level but found in practice not to enforce on
  `gh release edit` (May 2026 finding). Worth a note to GitHub
  Support if we ever rely on it; otherwise the in-script
  *Publish?* confirmation prompt is the practical gate.
- **Auto-merge on PRs** with passing CI: enabled. Standard
  workflow for routine changes.
- **Branch auto-delete on merge**: enabled. Branch hygiene is
  automatic.
- **Tag immutability** (`protect-release-tags` ruleset, no
  bypass): in place since v1.0.
- **Dependabot for actions**: to be enabled in Q3 (see above).

---

## Release plan

| Version | Target date | Working title | What's in it |
|---|---|---|---|
| v1.4.0 | early Jun 2026 *(pre-Conference)* | *Search the directory, polished header* | Site-wide search + bio cards + header streamline + small fixes from MC-feedback iteration |
| v1.5.0 | late Jun 2026 *(pre-July)* | *Logos, socials, IA polish* | #62 official logos / favicon refresh across site + PDF + poster, #63 social-media presence and on-site footprint, **structural IA quick-wins from `docs/homepage-ia-quick-audit.md` (Phase 1)** |
| v1.6.0 | early Sep 2026 *(pre-MC plenary, with buffer)* | *FR / DE reviewed, calendar + search rounded out* | Native-speaker translation pass; D8 (M9 STSM guidelines) + D10 (M10 risk management) hosted; per-event `.ics` files + Add-to-calendar buttons; news RSS feed; search acronym-synonyms; pre-MC-plenary a11y + cross-browser pass |
| v1.7.0 | mid Oct 2026 | *Year 1 closes* | D1 first-version state, D6 policy-brief hosting with proper *Outputs* card design + schema.org metadata, Year-1 retrospective content, URL-encoded directory filter state, **homepage restructure landing the IA-audit recommendations** |
| v1.8.0 | late Dec 2026 | *Year 2 ready* | D11 + D12 hosting; #72 side-panel **if** triggers fired; per-page Open Graph images; print stylesheet for FAQ + Glossary; whatever Q4 polish accumulates |

Patch releases (`1.x.y`) ship as needed; we don't pre-schedule
them.

---

## Open questions / decisions needed

These need an explicit yes/no from the Action Chair (or AC + WG4
lead where indicated) before the related work can start:

1. **Social media channels (issue #63).** Which channels does
   the Action commit to? *Working proposal: LinkedIn primary +
   Bluesky secondary, no X.* Decision owner: **Action Chair +
   WG4 Lead (Science Communication)**.

2. **Native-speaker review of FR + DE chrome and content.**
   The translations are beta. Lifting them out requires one
   review pass per locale. Decision owner: **AC** (assigns
   reviewers from MC pool).

3. **Auto-rebuild of the search index.** Today the maintainer
   runs `./scripts/build-search.sh` after content changes; CI
   page-count check catches forgotten rebuilds. Could be
   automated via an Action that auto-PRs index updates. **Cost:**
   noise in the PR list. **Benefit:** never stale. Decision
   owner: **maintainer** (AL); defer to Q3 unless friction is
   reported.

4. **#72 side panel — kick off?** Re-evaluate end-November
   against the triggers (membership > 150 OR usability
   complaints). Decision owner: **maintainer**, with input from
   MC.

5. **Member self-edit CTA** — only spin up if at least 3 MC
   members ask for faster turnaround than the weekly form
   sync. No decision needed today; mentioned for visibility.

6. **D11 / D12 publication dates.** WG4 (Inclusion &
   Dissemination) owns D11; whoever owns environmental
   sustainability owns D12. The website work is short (a few
   hours per deliverable) once the PDFs are approved. Decision
   owner: **respective WG / coordinator**.

7. **Homepage + header IA audit — bring in a UI/UX
   professional for *Phase 2*?** *Phase 1 runs without
   consulting regardless — the maintainer writes the
   structural quick-audit this week.* The decision is whether
   the deeper Phase 2 pass in July–August warrants a few hours
   of an experienced practitioner's time. **Cost:** modest
   (~½ day of consulting). **If no budget:** the maintainer
   self-runs Phase 2 too; output is acceptable but less rich,
   particularly on audience-track separation and mobile
   patterns. Decision owner: **Action Chair**. Decision
   deadline: **end of June** so the audit can start in July.

---

## Beyond 2026 — a peek at Year 2

For context only; this roadmap commits to nothing past Dec 2026.

The big-picture trajectory across **Y2 (Oct 2026 → Oct 2027)**:

- The **second annual conference** drives another spike of
  outreach + directory growth.
- **D7** (mentoring initiative evaluation) at M18 = ~Apr 2027 —
  a new page or section is plausible.
- **D2** (first draft of the manifesto) at M15 = ~Jan 2027 —
  hosted with annotation / commenting capability if the WG
  wants public feedback.
- The directory likely crosses **~80–120 members** by mid-Year-2
  if intake stays steady. Side-panel decision will have been
  taken either way.

The Action's **strategic autonomy** narrative gets its first
real evidence base (six months of policy briefs, member growth,
training school cohorts) — the website's role shifts from
"showcase" to "evidence library". Anticipate redesign work
around the *Outputs* section in Q1 2027 to support that.

---

## How to read this document

- **MC members**: skim *Where we are* + *What we'll ship, by
  quarter*. The release table summarises in one screen.
- **Action Chair / Vice-Chair**: the *Open questions* section
  is the one that needs your input.
- **WG leads**: scan *Deliverables milestones* and the
  per-quarter content blocks for your WG's hand-offs.
- **The maintainer (me)**: this is the working document. Edit
  in-tree, PR-review the changes, ship monthly status updates
  in the news block.

This document is a **living roadmap** — facts get updated as
events unfold. If you want a snapshot at any point, the git
history on this file is the audit trail.
