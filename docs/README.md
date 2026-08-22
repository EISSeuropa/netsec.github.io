# NetSec Website — Documentation

Welcome to the internal documentation for the **COST Action CA24154 —
NetSec** website (<https://netsec-cost.eu>). The project [`README`](../README.md)
covers high-level orientation and quickstart; this folder is the deep
reference for maintainers, MC representatives, and admins.

## Contents

| Document                                       | Read this when you want to…                                                                  |
| ---------------------------------------------- | -------------------------------------------------------------------------------------------- |
| [`architecture.md`](./architecture.md)         | Understand the site's purpose, structure, features, and how data flows through it.           |
| [`design-system.md`](./design-system.md)       | Match the existing look-and-feel — colour tokens, typography, components, accessibility.     |
| [`admin-guide.md`](./admin-guide.md)           | Operate the site: accounts you need, where credentials live, common admin tasks, escalation. |
| [`bios-setup.md`](./bios-setup.md)             | One-time set-up guide for the Google Form → bios.json pipeline.                              |
| [`profile-pages.md`](./profile-pages.md)       | What the `/people/<slug>` profile pages carry and how `build-profile-pages.py` builds them: the two-column anatomy, the theme/region chips, the similar-people facepile, the actionable CTAs, the prize pill, and the runtime EISS-Anthology link. |
| [`og-cards.md`](./og-cards.md)                 | How each member's personal Open Graph share image is generated and kept current — the hashed inputs that trigger a re-render, the churn-free manifest, and the CI gate. |
| [`network-map.md`](./network-map.md)                       | The NetSec Network Map prototype at `/network-map.html`: what the network map shows (WG and theme lenses, co-panel and mentorship overlays), how `build-network-map.py` derives the graph from the same data as the Directory, and why it is deliberately unlisted for now. |
| [`news-publishing.md`](./news-publishing.md)   | How a news item reaches the site and the RSS feed (the trigger the social pipeline consumes). |
| [`social-publishing.md`](./social-publishing.md) | How news and the weekly spotlight become Bluesky and LinkedIn posts — the approval-gated path, the ungated auto-spotlight, curated threads, the dedup ledger, the one-time account set-up, and how the LinkedIn API version stays current. |
| [`i18n.md`](./i18n.md)                         | How translations work (FR + DE in beta), what's in scope, how to refresh when English drifts.|
| [`seo.md`](./seo.md)                           | SEO posture — Open Graph, Twitter Card, JSON-LD, canonical URLs, hreflang, sitemap, 404. |
| [`search-assessment.md`](./search-assessment.md) | Decide whether to add site-wide search — options compared (Pagefind / Lunr / MiniSearch / DDG / Algolia), constraints, recommendation. *(Status: shipped in v1.4.x — kept as the design history.)* |
| [`roadmap-2026.md`](./roadmap-2026.md) | Full-year 2026 roadmap for the website + directory — Mermaid timeline up top, then *Release history* covering every shipped version (v1.0 → v1.4) with major features, then the quarter-by-quarter plan for v1.5 → v1.8, open decisions, deliverables we host. Intended for the Action Chair, MC members, and the maintainer. |
| [`homepage-ia-quick-audit.md`](./homepage-ia-quick-audit.md) | Phase 1 of the two-phase IA pass — structural decisions the home page + header need before v1.5.0 ships in late June. Eight issues identified, five queued for Phase 1, three deferred to Phase 2. Six decisions needed from the Action Chair. |
| [`chair-confirmations.md`](./chair-confirmations.md) | Open questions where the live site rests on maintainer inference or a placeholder and needs Chair / WG-lead sign-off (deliverable assignments, the EISS paragraph, event tags, WG copy, leadership names). A tickable checklist, mirrored on the members' Wiki. |
| [`launch-qa-2026.md`](./launch-qa-2026.md) | Pre-launch QA plan for the late-May 2026 public push. Three-phase audit (automation pre-flight → critical user journeys → a11y + cross-browser + perf), Go / No-Go criteria, schedule, tooling cheatsheet, and a live findings log. Companion scripts: `scripts/check-links.sh`, `scripts/check-a11y.sh`. |
| [`claude-usage.md`](./claude-usage.md)         | Choose the right Claude model and reasoning-effort level for a task on this repo, and stay inside the Pro plan's weekly quota. Calibrated to our automation layer (scripts, i18n, CI, release tooling), not a generic static site. |
| [`cross-repo-workflow.md`](./cross-repo-workflow.md) | Conventions for keeping the NetSec and EISS sites in step: shared patterns, the "ported from" convention, the duplicate-scripts stance, and Indico sync alignment. Complements the cross-repo-project skill (the shared Project board). |
| [`audit-2026-06.md`](./audit-2026-06.md)       | Point-in-time cross-cutting static audit (June 2026): accessibility, voice, links, dead code, responsive, SEO, across all pages and locales. Records what was fixed, dismissed as a false positive, and deferred. |
| [`pdf/NetSec-website-documentation.pdf`](./pdf/NetSec-website-documentation.pdf) | All of the above combined into a stakeholder-ready PDF deliverable. Cover, table of contents, every diagram, and three site screenshots. Rebuild via `docs/pdf/build.sh`. |
| [`pdf/NetSec-Design-System.pdf`](./pdf/NetSec-Design-System.pdf) | A4 visual companion to `design-system.md`: cover, design language, colour / type / spacing tokens, components, and the conference-deck layouts, rendered as swatches and specimens. Built from the standalone NetSec Design System package (the Claude Design export), so it includes the tidied, partly aspirational token layer the live `site.css` does not yet fully implement. |

## Conventions across all docs

- **British English** — *organisation*, *centre*, *behaviour*.
- **Mermaid diagrams** are rendered natively by GitHub. View the
  `.md` file on github.com to see them; on a local checkout, install
  any Markdown previewer with Mermaid support (VS Code with the
  *Markdown Preview Mermaid Support* extension, for example).
- **Audience**: each doc states its audience in the opening line so
  you can skip what you don't need.

## Quick links

- 🌐 Live site: <https://netsec-cost.eu>
- 🏛️ COST Action page: <https://www.cost.eu/actions/CA24154/>
- 🐙 Repository: <https://github.com/EISSeuropa/netsec.github.io>
- 🔒 Security policy: [`../SECURITY.md`](../SECURITY.md)
- 📜 Licences: [`../LICENSE`](../LICENSE) (MIT) · [`../LICENSE-CONTENT`](../LICENSE-CONTENT) (CC BY 4.0)
