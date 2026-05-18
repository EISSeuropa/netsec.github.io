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
| [`pdf/NetSec-website-documentation.pdf`](./pdf/NetSec-website-documentation.pdf) | All of the above combined into a stakeholder-ready PDF deliverable. Cover, table of contents, every diagram, and three site screenshots. Rebuild via `docs/pdf/build.sh`. |

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
