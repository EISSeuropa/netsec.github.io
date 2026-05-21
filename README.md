# NetSec — COST Action CA24154 website

<p align="center">
  <a href="https://netsec-cost.eu/press-kit.html">
    <img src="docs/promo/poster-promo-card.png" alt="NetSec promotional poster — Networking European security knowledge. CC BY 4.0 · COST Action CA24154. Click for the press kit." width="360">
  </a>
</p>

> Official website and open community directory of **COST Action
> CA24154 — Networking European Security Knowledge (NetSec)**.

🌐 **Live site:** <https://netsec-cost.eu>
🏛️ **COST page:** <https://www.cost.eu/actions/CA24154/>
🗓️ **Action running:** 10 Oct 2025 – 09 Oct 2029
📜 **Code licence:** [MIT](LICENSE) · **Content licence:** [CC BY 4.0](LICENSE-CONTENT)

This site doubles as the Action's **Deliverable D1** (open community
directory) and is maintained by [Dr Arthur Laudrain](https://netsec-cost.eu/people.html#arthur-laudrain)
(MC member, CH).

---

## Contents

- [Overview](#overview)
- [Repository layout](#repository-layout)
- [Local development](#local-development)
- [Automated pipelines](#automated-pipelines)
- [Editing content](#editing-content)
- [Contributing](#contributing)
- [Security](#security)
- [Privacy & GDPR](#privacy--gdpr)
- [Licensing](#licensing)
- [Acknowledgements](#acknowledgements)

> 📚 **For maintainers**: see [`docs/`](./docs/) for deep
> documentation — site architecture and data-flow diagrams, the
> design system, the admin guide (accounts, logins, common tasks),
> and the Google Form set-up walkthrough.

---

## Overview

The site is a small, dependency-light **static** GitHub Pages
deployment. There is **no build step** — every page is hand-authored
HTML that loads a shared CSS stylesheet, a shared JS file, and (for
the directory and grants pages) reads `data/bios.json` at runtime.

Design principles:

- **Apple-style glassmorphism** with a manual light/dark theme toggle
  (default follows `prefers-color-scheme`, override stored in
  `localStorage`).
- **British English** throughout the site copy.
- **Accessible by default**: skip links, ARIA landmarks, no
  content hidden behind hover, all interactive controls keyboard
  reachable. See [accessibility.html](https://netsec-cost.eu/accessibility.html).
- **Single source of truth**: `data/bios.json` drives the live
  directory (`people.html`) and the grant-manager cards (`grants.html`).
  Two scheduled GitHub Actions keep it in step with cost.eu and a
  public Google Form.

## Repository layout

```
.
├── index.html              # Home page (news, about, WGs, MC, events, roadmap, outputs, contact)
├── people.html             # The Network — open directory, fetched from data/bios.json
├── grants.html             # Grants & Calls — five NetSec grant schemes + e-COST workflow timeline
├── accessibility.html      # WCAG 2.1 conformance statement
├── privacy.html            # GDPR-compliant privacy notice (includes §10 Licensing)
├── sitemap.html            # User-friendly site map (linked from every footer)
├── assets/
│   ├── css/site.css        # Shared stylesheet (theme tokens, glass, components, responsive)
│   ├── js/site.js          # Shared scripts (nav, theme toggle, reveal-on-scroll, MC accordion)
│   └── images/people/      # Member headshots downloaded by sync-bios.py
├── data/
│   ├── bios.json           # The directory (members, roles, WGs, contacts, photos)
│   └── mc-members.json     # MC roster per country — used to auto-tag "MC member · <Country>"
├── scripts/
│   ├── sync-cost.py        # Pulls WG_MAP + leadership roles from cost.eu
│   ├── sync-bios.py        # Pulls form submissions + headshots from Google Sheets
│   ├── bios-source.json    # CSV URL + form URL + column mapping for sync-bios.py
│   └── requirements.txt    # Python deps (requests, beautifulsoup4, Pillow)
├── .github/workflows/
│   ├── sync-cost.yml       # Weekly cron: scripts/sync-cost.py → PR
│   └── sync-bios.yml       # Weekly cron: scripts/sync-bios.py → PR
├── docs/
│   ├── README.md           # Index of internal documentation
│   ├── architecture.md     # Purpose, structure, features, data-flow diagrams
│   ├── design-system.md    # Colour tokens, typography, components, accessibility
│   ├── admin-guide.md      # Accounts, logins, routine tasks, handover checklist
│   └── bios-setup.md       # One-time Google Form set-up guide
├── LICENSE                 # MIT (covers source code)
├── LICENSE-CONTENT         # CC BY 4.0 (covers prose, with carve-outs)
├── SECURITY.md             # Security policy and disclosure process
└── README.md               # You are here
```

## Local development

No toolchain to install — just open the file in a browser. For
hot-reload while you're editing, any zero-config static server will
do:

```bash
# Python (already on most macOS / Linux)
python3 -m http.server 8000

# Or, with Node.js available
npx serve .
```

Then visit <http://localhost:8000>.

To exercise the sync scripts locally:

```bash
pip install -r scripts/requirements.txt
python3 scripts/sync-cost.py      # rewrites index.html WG_MAP + data/bios.json roles
python3 scripts/sync-bios.py      # pulls Google Form submissions into data/bios.json
```

> ⚠️ The sync scripts write to tracked files. Always run them on a
> branch and review the diff before committing. CI does this for you
> automatically — see below.

## Automated pipelines

Two scheduled workflows keep the site in step with upstream data
sources. Both run **every Monday at 05:00–05:15 UTC**, both can be
triggered manually from the Actions tab, and both **open a pull
request** when (and only when) the data has changed — never a silent
push to `main`.

| Workflow             | Source                                  | Updates                                                                 | Cron        |
| -------------------- | --------------------------------------- | ----------------------------------------------------------------------- | ----------- |
| `sync-cost.yml`      | <https://www.cost.eu/actions/CA24154/> | `WG_MAP` in `index.html` + leadership roles in `data/bios.json`         | `0 5 * * 1` |
| `sync-bios.yml`      | Google Form → published Sheet CSV       | Every field on each member in `data/bios.json` + headshots in `assets/` | `15 5 * * 1` |

The Google-Form pipeline is documented in detail in
[`docs/bios-setup.md`](docs/bios-setup.md).

## Editing content

There are three classes of content with three different workflows:

1. **Page copy** (everything *not* in the directory or grants list) —
   edit the relevant `*.html` file directly and open a PR. CSS lives
   in `assets/css/site.css`; JS in `assets/js/site.js`.
2. **Member bios and photos** — submit or update via the Google Form
   linked from `people.html#join`. The next weekly sync (or a manual
   dispatch of `sync-bios.yml`) opens a PR with the diff.
3. **MC / leadership roster** — managed on cost.eu. The next weekly
   sync (or a manual dispatch of `sync-cost.yml`) opens a PR.

## Contributing

External contributions are welcome but small. We're a static site,
not a framework — keep changes minimal, well-commented, and
British-English. Conventions:

- One PR per logical change. Reference any related issue.
- Run the page in light **and** dark mode before submitting visual
  changes.
- Don't add a build step or a JS framework without discussion.
- Don't add tracking pixels, analytics, or third-party scripts.
- The MIT/CC-BY dual licence applies to every accepted contribution.

## Versioning

This repository follows **[Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html)**
from `v1.0.0` onwards. Tagged releases are visible under
[*Releases*](https://github.com/EISSeuropa/netsec.github.io/releases)
on GitHub; every release entry mirrors the relevant section of
[`CHANGELOG.md`](CHANGELOG.md).

Because the deliverable here is a website, a directory, and a
documentation pack rather than a software library, the three semver
components translate as follows:

| Bump | When | Examples |
| --- | --- | --- |
| **MAJOR** (`x.0.0`) | A foundational reset of scope, identity, or platform. Rare. | A full site redesign, switching off GitHub Pages, a new MoU replacing CA24154. |
| **MINOR** (`1.x.0`) | A **big new project** in the repo — a new top-level page, a new automated pipeline, a new locale, a new top-level feature. The default for substantive work. | Adding a new language; adding a fifth public page; introducing a new sync workflow; a redesign of a major section. |
| **PATCH** (`1.0.x`) | Bug fixes, copy edits, content refreshes, dependency bumps, small UX tweaks. | Fixing a typo, refreshing a member bio, tightening a CSS rule, restoring a wiped role. |

A release is cut whenever a milestone is worth marking — typically
at the close of a sprint of work, or after a noteworthy fix. We do
not tag every commit; we tag when the cumulative change reads as a
release.

**Every release has a short title** that summarises the key
contribution in 3–8 words, sentence case, no trailing punctuation.
The title appears in three places: the CHANGELOG heading (`## [1.4.0]
· 2026-05-22 — Site-wide search`), the GitHub Release name
(`v1.4.0 — Site-wide search`), and the release-cutting commit
message. `scripts/release.sh` requires the title as a positional
argument so the rule cannot be silently skipped:

```sh
./scripts/release.sh 1.4.0 "Site-wide search"
./scripts/release.sh 1.4.0 "Site-wide search" --dry-run
```

Examples from the existing release history:

| Tag | Title |
| --- | --- |
| `v1.3.0` | *Introducing FAQ and Glossary pages* |
| `v1.2.0` | *Press kit, directory tour, compact view* |
| `v1.1.0` | *Release tooling and PDF SemVer* |
| `v1.0.0` | *Initial public release* |

The documentation pack at `docs/pdf/NetSec-website-documentation.pdf`
carries its own version stamp on its cover (currently v1.2) and its
own changelog appendix. The two version axes are independent for
historical reasons; we may consolidate them at a future MAJOR
release.

## Security

We follow a public, time-bound coordinated-disclosure process —
please see [`SECURITY.md`](SECURITY.md). Do **not** open a public
GitHub issue for a suspected vulnerability; use the [private security
advisory form](https://github.com/EISSeuropa/netsec.github.io/security/advisories/new)
instead.

## Privacy & GDPR

Personal data (member bios, photographs, contact-form submissions)
is processed per the [Privacy Notice](https://netsec-cost.eu/privacy.html).
The Data Controller is **Universiteit Leiden**, the Grant Holder
Institution for CA24154. Submitters can request changes or removal
at any time.

## Licensing

This repository uses **dual licensing**:

| What                                                | Licence                                    |
| --------------------------------------------------- | ------------------------------------------ |
| Source code (HTML/CSS/JS, Python, Actions)          | [MIT](LICENSE)                             |
| Site content (prose, page copy, documentation)      | [CC BY 4.0](LICENSE-CONTENT)               |
| Member bios and photos                              | © contributors, used with permission       |
| Third-party assets (icons, fonts, flags, COST/EU)   | their own licences — see `LICENSE-CONTENT` |

If you reuse the site content under CC BY, please attribute it as:

> *Based on content from COST Action NetSec (CA24154),
> https://netsec-cost.eu, CC BY 4.0.*

## Acknowledgements

This website and the NetSec Directory were created by **Dr Arthur
Laudrain** (MC member, CH; Centre for Security Studies, ETH Zurich)
as part of Deliverable D1.

NetSec is supported by **COST (European Cooperation in Science and
Technology)** and the **European Union**.
[www.cost.eu](https://www.cost.eu)

<p align="center">
  <em>The views expressed are those of the Action and do not necessarily reflect those of COST or the European Union.</em>
</p>
