# Changelog

All notable changes to this repository are recorded here.

This project follows [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html)
and the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.
What "MAJOR / MINOR / PATCH" means in the context of this repo is
spelt out in the **Versioning** section of [`README.md`](README.md).

The documentation pack (`docs/pdf/NetSec-website-documentation.pdf`)
carries its own version stamp on its cover and its own changelog
appendix; see Appendix C of that PDF for documentation-pack history.

## [Unreleased]

### Fixed

- **Search backend now works** (was: *"SEARCH IS UNAVAILABLE. RELOAD THE PAGE TO TRY AGAIN"* on every query). The overlay was calling `pagefind.search(query, { filters: { language: lang } })` — interpreted by Pagefind as "filter results to pages tagged with a `language` metadata field". We never tag pages with such a field; Pagefind returned zero matches and the catch branch fired. Pagefind v1 already handles locale isolation through per-language shards keyed off `<html lang>`, so no filter is required. Empty options is correct. The error UI now also surfaces the actual Pagefind error message so the next debugging session is faster.
- **Search trigger no longer overflows the floating header on the home page.** The `⌘K` hint badge was always visible above 880 px viewport and pushed the `.nav-actions` cluster past the bubble's edge on the 10-link home nav. Badge is now hidden in all viewports; the keyboard shortcut is still discoverable via the button's `title` tooltip and the *open* row inside the search overlay.
- **`Cmd-K` / `Ctrl-K` hardened.** The keydown handler now also checks `e.code === 'KeyK'` so the shortcut survives keyboard layouts where the printed glyph isn't at the physical KeyK position (Dvorak, AZERTY-in-some-browsers, etc.). The listener moved from `document` to `window` so it doesn't get swallowed by extensions that install higher-priority document-level handlers.

### Added

- **iCalendar feed at `/calendar.ics`** with the dated events from the home page (Summer School, European Security Conference). Hand-authored RFC 5545 file with a `Europe/Stockholm` `VTIMEZONE` block; refresh interval set to seven days. The Events section on the home page gains a subtle *Subscribe to NetSec events* link (using `webcal://` so Apple Calendar / iOS Calendar / Outlook prompt to subscribe natively) with a fallback `.ics` download for one-shot imports. Localised in EN/FR/DE. A `<link rel="alternate" type="text/calendar">` in each home-page `<head>` makes the feed autodiscoverable for capable clients.
- **Calendar single-source-of-truth pipeline.** The `.ics` feed is now generated from a structured `data/events.json` by `scripts/build-calendar.py`; CI workflow `calendar-drift.yml` runs the same script with `--check` on every PR and fails if `calendar.ics` would change. Maintainers edit one file (the JSON), regenerate (`python3 scripts/build-calendar.py`), and CI catches forgotten regenerations before merge. The HTML event cards in `index.html` (+ FR/DE) stay hand-authored — they carry locale-specific framing that doesn't trivially derive from JSON — but the architecture-doc checklist now walks through the JSON-first workflow. Output is byte-identical to the previous hand-authored `calendar.ics`, so existing subscribers see no change.

- **Site-wide search via Pagefind** (`docs/search-assessment.md` → ship). A modal overlay search UI triggered by Cmd/Ctrl-K, `/` (anywhere outside an input), or the new magnifying-glass button in the nav. Indexes every `<main data-pagefind-body>` across all 30 public pages (EN + FR + DE), so results are scoped to the visitor's active locale automatically. Each page's `<h1>`/`<h2>`/`<h3>` becomes a sub-result with a deep-link anchor — long pages like FAQ and Glossary jump straight to the matched section. Snippets are highlighted with `<mark>` in the same EU-yellow used in the press kit. Privacy posture preserved: index served from `/pagefind/` on `netsec-cost.eu`, queries never leave the visitor's browser, no third-party calls. Lazy-loaded on first overlay open (~80 KB JS + ~50 KB per-language shard). Keyboard navigation between results, focus trap, `aria-live` result count, full light + dark theme parity.
- **`scripts/build-search.sh` + `pagefind/` committed index + `.github/workflows/search-drift.yml`.** Mirrors the i18n-drift and calendar-drift patterns: one script with a `--check` flag, one CI workflow that fails any PR whose committed index diverges from what the script would produce. Pagefind is pinned to 1.5.2 for deterministic shard hashes; `pagefind-entry.json` is normalised with sorted keys after each build so the manifest is byte-stable across machines. `404.html` is `data-pagefind-ignore="all"` so the not-found page doesn't pollute results.

### Changed

- **Release-cutting now requires a short title.** `scripts/release.sh` takes the title as a required second positional argument (`./scripts/release.sh 1.4.0 "Site-wide search"`); the title appears in the CHANGELOG heading, the GitHub Release name, the release commit message, and the annotated tag. Convention is 3–8 words, sentence case, no trailing punctuation. Empty title and `--dry-run`-as-title both fail with helpful messages. README's *Versioning* section documents the convention and lists the canonical titles for v1.0.0 → v1.3.0.
- **Historical release entries retitled** to match the new convention — v1.0.0 *Initial public release*, v1.1.0 *Release tooling and PDF SemVer*, v1.2.0 *Press kit, directory tour, compact view*, v1.3.0 *Introducing FAQ and Glossary pages*. Applied to both the `CHANGELOG.md` headings and the corresponding GitHub Release titles (the `isImmutable: true` setting at the repo level does not in fact lock release titles via `gh release edit` — flagged separately).
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

[Unreleased]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/EISSeuropa/netsec.github.io/releases/tag/v1.0.0
