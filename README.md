# netsec

GitHub Pages site for **COST Action CA24154 — Networking European
Security Knowledge (NetSec)**, served at
[netsec-cost.eu](https://netsec-cost.eu).

The site doubles as Deliverable D1 (open community directory) and is
maintained by Dr Arthur Laudrain (MC member, Centre for Security
Studies, ETH Zurich).

## Pipelines

- **`scripts/sync-cost.py`** — weekly sync from
  [cost.eu/actions/CA24154/](https://www.cost.eu/actions/CA24154/).
  Refreshes the working-group membership map in `index.html` and
  reconciles leadership roles into `data/bios.json`.
- **`scripts/sync-bios.py`** — pulls form submissions from the
  published Google Sheet CSV into `data/bios.json`, downloads and
  resizes member photos, and auto-assigns the `MC member · <Country>`
  role from `data/mc-members.json`.
- Both run weekly via GitHub Actions and open a PR if anything
  changed.

## Licensing

This repository uses **dual licensing**:

| What                                                | Licence                                    |
| --------------------------------------------------- | ------------------------------------------ |
| Source code (HTML/CSS/JS, Python, Actions)          | [MIT](LICENSE)                             |
| Site content (prose, page copy, documentation)      | [CC BY 4.0](LICENSE-CONTENT)               |
| Member bios and photos                              | © contributors, used with permission       |
| Third-party assets (icons, fonts, flags, COST/EU)   | their own licences — see `LICENSE-CONTENT` |

See [`LICENSE-CONTENT`](LICENSE-CONTENT) for the full scope notice and
list of third-party assets.

If you reuse the site content under CC BY, please attribute it as:

> Based on content from COST Action NetSec (CA24154),
> https://netsec-cost.eu, CC BY 4.0.
