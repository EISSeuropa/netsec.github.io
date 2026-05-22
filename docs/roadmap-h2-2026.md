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
| **11–12 Jun 2026** | European Security Conference (Stockholm University) | Same; flagship outreach moment |
| **Q3 2026** *(date TBA)* | Inaugural Management Committee Plenary | Date confirmation on home page, agenda/minutes path to the members' Wiki |
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

**Theme**: ship the major polish items so the Conference + School
deployment is rock-solid.

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

### Q3 — July / August / September 2026

**Theme**: capitalise on the Conference momentum, harden the
infrastructure, host the first Year-1 deliverables.

#### Content & deliverables

- **Post-event recap** for the Conference and Summer School on
  the news block. Photo gallery (a small one — opt-in basis
  from participants), participant feedback summary, recordings
  link if available.
- **Host D8** (STSM planning guidelines, M9) as a permalink on
  the Grants page once the Grant Awarding Coordinator approves
  the final document.
- **Host D10** (risk management strategy, M10) — likely a new
  sub-page `/risk-management.html` with the PDF embedded and a
  short summary; or appended to the existing Documentation
  Pack appendix if the strategy is short.
- **Inaugural MC plenary** dates + minutes path published, once
  confirmed.

#### Features

- **Issue #62 — favicon and logo refinement**. Refresh the
  favicon with an adapted NetSec mark; audit logo placements
  across the site, the PDF, and the promotional poster; verify
  SEO/Open-Graph image still looks right on social-card
  previews (Twitter / X / LinkedIn / Bluesky).
- **Issue #63 — social media integration**, *if* the Action
  agrees on channels. Working assumption: LinkedIn (primary,
  professional reach) + Bluesky (privacy-friendly alternative
  to X for academic audiences). Footprint: footer chips +
  optional press-kit page section. **Decision needed from
  Action Chair / WG4 lead** before development starts.
- **FR / DE review pass on FAQ + Glossary content**. The
  translations are beta — flag a single native-speaker review
  per locale to lift them out of the beta banner.
- **Search index auto-rebuild** (consideration only — see *Open
  questions* below).

#### Infrastructure

- **Dependabot for GitHub Actions**: weekly checks on the
  pinned action SHAs (`actions/checkout@v4`, `actions/setup-
  node@v4`, `peter-evans/create-pull-request@v7`,
  `pagefind@1.5.2`). Auto-PR when a security update is
  available. *Drive-by from the GitHub App installation token
  format watch — having Dependabot on `actions` gives us the
  fix automatically if `peter-evans/create-pull-request` ships
  one.*
- **Re-test accessibility**: re-run axe-core on the new search
  overlay, the directory cards (post-spotlight class), and the
  FAQ/Glossary pages. Update the accessibility statement
  date stamp.

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

#### Releases & docs

- **v1.5.0** — bundles the Q3 features (favicons, social,
  translation review). Title TBD.
- **v1.6.0** — Year-1 milestone release alongside D1's M12.
  Title likely: *Year 1 closes*.
- **Documentation pack v1.7.0** at each website MINOR bump, in
  step with the website. (Pack version is independent of the
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

### 2 · Content cadence — deliverables hit the site

The site's value over 2026 grows as each MoU deliverable
publishes. The maintainer's commitment is **48-hour turnaround**
from approved-PDF-in-hand to live-on-site, with:

- a stable permalink,
- citation metadata (JSON-LD where appropriate),
- a news-block announcement,
- a press-kit-style social card if the deliverable warrants
  outreach.

### 3 · Quality, accessibility, performance

The site shipped at WCAG 2.1 AA in v1.0. We re-test once a
quarter:

- **Q3 audit**: search overlay, directory spotlight, FAQ /
  Glossary deep-links.
- **Q4 audit**: complete re-test after D11 (inclusion &
  diversity) ships.

Performance budget stays at the v1.0 number: **~140 KB
uncompressed page weight excluding bios.json**. The Pagefind
runtime (~80 KB on first overlay open) is the only meaningful
delta and is lazy-loaded.

### 4 · Infrastructure & DevOps hygiene

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
| v1.4.0 | early Jun 2026 | *Search the directory, polished header* | Site-wide search + bio cards + header streamline + small fixes from MC-feedback iteration |
| v1.5.0 | mid Sep 2026 | *Iconography, social, FR/DE reviewed* | #62 favicon/logos, #63 social, native-speaker translation pass |
| v1.6.0 | mid Oct 2026 | *Year 1 closes* | D1 first-version state, D6 policy-brief hosting, Year-1 retrospective content |
| v1.7.0 | late Dec 2026 | *Year 2 ready* | D11 + D12 hosting; #72 side-panel **if** triggers fired; whatever Q4 polish accumulates |

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
