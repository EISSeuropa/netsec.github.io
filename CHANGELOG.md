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

_Nothing yet._

## [1.1.0] · 2026-05-20

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

## [1.0.0] · 2026-05-20

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

[Unreleased]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/EISSeuropa/netsec.github.io/releases/tag/v1.0.0
