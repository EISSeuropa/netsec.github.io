# Architecture

> *Audience: developers and maintainers who want to understand or
> extend the site.*

## Purpose

The NetSec website serves three distinct audiences with one
deliverable:

1. **The wider research community** — anyone working in or alongside
   European security studies. The site explains what the Action is,
   who's involved, what events are coming up, and how to engage.
2. **MC members, WG participants, and grant applicants** — practical
   resources: grant calls, e-COST workflow, deliverables, roadmap.
3. **External evaluators and funders** — COST and the EU Commission,
   for whom the site is also **Deliverable D1** (open community
   directory) of the Action's MoU.

Anything we add or change should help at least one of these groups
without confusing the others.

## Tech stack at a glance

```mermaid
flowchart LR
    A["Visitor's browser"] -->|HTTPS| B["GitHub Pages<br/>(static hosting)"]
    B --> C["netsec.github.io repo<br/>(this repo)"]
    C -.->|read at runtime| D["data/bios.json"]
    F["cost.eu/actions/CA24154"] -.->|weekly cron| G[".github/workflows/<br/>sync-cost.yml"]
    G -->|PR| C
    H["Google Form"] -->|writes| I["Google Sheet<br/>(published as CSV)"]
    I -.->|weekly cron| J[".github/workflows/<br/>sync-bios.yml"]
    J -->|PR| C
    K["Visitor submits<br/>contact form"] -->|POST| L["Formspree<br/>(meenwyrb)"]
    L -->|email| M["Action mailbox"]

    style B fill:#003399,stroke:#003399,color:#fff
    style C fill:#0a84ff,stroke:#0a84ff,color:#fff
    style D fill:#eef2fb,stroke:#0a84ff
```

- **No build step.** Every page is hand-authored HTML. The shared
  CSS and JS load directly from `assets/`.
- **No framework.** Vanilla browser APIs only.
- **No database.** Persistent state lives in `data/*.json`, committed
  to git.
- **No analytics or tracking.** Loading footprint is ~140 KB
  uncompressed including fonts.

## Site structure

```mermaid
flowchart TD
    H["index.html<br/><i>Home</i>"]
    P["people.html<br/><i>The Network</i>"]
    G["grants.html<br/><i>Grants &amp; Calls</i>"]
    S["sitemap.html<br/><i>Site map</i>"]
    A["accessibility.html<br/><i>Accessibility statement</i>"]
    R["privacy.html<br/><i>Privacy notice (+ Licensing §10)</i>"]

    H -- "anchor links<br/>#news #about #working-groups<br/>#committee #events #roadmap<br/>#outputs #contact" --> H
    H --> P
    H --> G
    H --> S
    P --> G
    G --> P
    S --> H
    S --> P
    S --> G
    S --> A
    S --> R
    A -.->|footer| R
    R -.->|footer| A

    style H fill:#0a84ff,stroke:#0a84ff,color:#fff
    style P fill:#eef2fb,stroke:#0a84ff
    style G fill:#eef2fb,stroke:#0a84ff
```

| Page                  | Purpose                                                                         | Reads at runtime         |
| --------------------- | ------------------------------------------------------------------------------- | ------------------------ |
| `index.html`          | Action overview, news, WGs, MC composition, events, roadmap, outputs, contact   | `data/bios.json` (none — leadership baked in via `data-bios-roles`) |
| `people.html`         | Open community directory with WG/MC/country filters and the Join-the-network CTA| `data/bios.json` (full) |
| `grants.html`         | The five NetSec grant schemes, the e-COST timeline, resources, grant managers   | `data/bios.json` (Grant Awarding Coordinator cards) |
| `sitemap.html`        | User-friendly site map linking every page and every in-page anchor              | nothing |
| `accessibility.html`  | WCAG 2.1 conformance statement                                                  | nothing |
| `privacy.html`        | GDPR-compliant privacy notice; §10 covers reuse/licensing                       | nothing |

## Feature inventory

### User-facing

- **Light/dark theme toggle** with `prefers-color-scheme` default,
  manual override in `localStorage` (`netsec-theme`).
- **Reveal-on-scroll** powered by `IntersectionObserver`. Falls back
  to "always visible" if JS is disabled or the observer fails.
- **Glass cards** with `backdrop-filter`; graceful fallback under
  `@supports not (backdrop-filter)`.
- **Country flags** thumbnails via FlagCDN for every ISO country
  code (~200), used in the MC-by-country grid and member cards.
- **Network directory filters** — free-text search × WG/MC chip ×
  country dropdown, all AND-combined client-side.
- **Two view densities on the directory** — detailed (photo + bio
  + contact icons) and compact (one-row, flag + affiliation + WG
  chips). Switched via a segmented toggle in the toolbar; preference
  persists in `localStorage('netsec-directory-view')`.
- **Click-to-expand in compact mode** — clicking a compact card
  flips it to its detailed form in place while the rest of the
  grid stays compact. URL hash `#slug` mirrors the expanded card
  for shareable deep-links; Esc / click-outside collapses. Tracked
  upgrade path to a sticky side panel in Issue #72.
- **First-visit orientation** — a dismissible welcome strip above
  the directory toolbar, plus a `?` button that re-opens an
  opt-in six-step guided tour (search → filter chips → country
  → density toggle → `+` quick-join → join card).
- **`+` quick-join button** in the directory toolbar — smooth-
  scrolls to the join card at the foot of the page and focuses
  the *Add your bio* CTA.
- **Bio collapse** — bios over 4 lines auto-detect and add a "Show
  more / Show less" toggle.
- **Awarding-process timeline** on `grants.html` — numbered nodes on
  a gradient rail with Before / During / After pills.
- **e-COST portal model** spelt out on `grants.html`: the portal is
  a single general COST surface that NetSec cannot customise. It
  filters visibility by applicant profile (ITC only to ITC
  affiliates, YRIG only to under-40s), so an applicant might not
  see every scheme listed. The portal can also surface grant types
  from other COST programmes that NetSec hasn't budgeted for;
  applications for anything outside the Work and Budget Plan are
  rejected by the Grant Awarding Coordinator. The Grants page sets
  expectations openly so members don't apply for what we can't
  fund.

### Operator-facing

- **Two weekly sync workflows** (see below) that open PRs rather
  than silently pushing to `main`.
- **`data-bios-roles` runtime binding** — any HTML element with this
  attribute gets populated from `data/bios.json` at load, so the
  grant-manager cards on `grants.html` and the Action-leadership
  blurbs on `index.html` stay in step with the directory without
  duplicating data.
- **MC member auto-tagging** — `sync-bios.py` cross-references new
  submissions against `data/mc-members.json` and appends an
  `MC member · <Country>` role if the name matches.
- **Brand-accurate social icons** — Simple Icons SVGs for ORCID
  (with the official green), LinkedIn, X, Bluesky, Mastodon.

## Data flow

### How a bio gets onto the site

```mermaid
sequenceDiagram
    participant M as Member
    participant F as Google Form
    participant S as Google Sheet<br/>(published CSV)
    participant W as sync-bios.yml<br/>(Mondays 05:15 UTC)
    participant P as sync-bios.py
    participant R as Repo<br/>(branch: bios-sync/auto)
    participant A as Admin

    M->>F: Submits bio (name, role, WGs,<br/>photo, contact links)
    F->>S: Append row
    Note right of S: Sheet is published to web<br/>as a CSV at a stable URL
    W->>P: Run sync-bios.py
    P->>S: GET published CSV
    P->>P: Parse rows, dedupe by email→slug,<br/>auto-tag MC role from mc-members.json
    P->>P: Download + resize photos<br/>via Pillow
    P->>R: git diff data/bios.json<br/>+ assets/images/people/*.jpg
    alt Diff non-empty
        P->>R: peter-evans/create-pull-request@v7
        Note over R,A: PR opens against main<br/>with a human-readable diff
        A->>R: Review + merge
        R-->>F: Live on /people.html next page-load
    else No diff
        P-->>P: Exit 0 (no PR, no inbox noise)
    end
```

### How a cost.eu change propagates

```mermaid
sequenceDiagram
    participant C as cost.eu/actions/CA24154
    participant W as sync-cost.yml<br/>(Mondays 05:00 UTC)
    participant P as sync-cost.py
    participant R as Repo<br/>(branch: cost-sync/auto)
    participant A as Admin

    W->>P: Run sync-cost.py
    P->>C: GET HTML
    P->>P: Parse Membership table → WG_MAP
    P->>P: Regex over malformed<br/>Leadership table → roles
    P->>P: Reconcile roles into<br/>data/bios.json seed entries
    P->>R: git diff index.html (WG_MAP)<br/>+ data/bios.json (roles)
    alt Diff non-empty
        P->>R: peter-evans/create-pull-request@v7
        A->>R: Review + merge
    else No diff
        P-->>P: Exit 0
    end
```

> **Why regex over the Leadership table?** cost.eu emits a malformed
> `</div>` where `</td>` should close — that breaks BeautifulSoup's
> table parser silently (only 5 of 14 roles come through). The
> regex falls back to the raw HTML and walks every `<td>…</td>`
> ending in a known leadership suffix (Chair, Coordinator, Leader,
> Co-Lead, Representative).

### How a contact-form submission flows

```mermaid
flowchart LR
    A["Visitor on<br/>/index.html#contact"] -->|HTML form POST| B["Formspree<br/>project meenwyrb"]
    B -->|email| C["Action mailbox"]
    B -->|JSON 200| A
    A -->|toast confirmation| A
    style B fill:#003399,stroke:#003399,color:#fff
```

Formspree is the only third-party that ever sees visitor data
besides GitHub Pages' own access logs. The full processor list is in
[`privacy.html`](https://netsec-cost.eu/privacy.html).

## Repository layout

```
.
├── index.html                       # Home
├── people.html                      # The Network
├── grants.html                      # Grants & Calls
├── accessibility.html               # WCAG statement
├── privacy.html                     # GDPR notice
├── sitemap.html                     # User-friendly site map
│
├── assets/
│   ├── css/site.css                 # Single shared stylesheet
│   ├── js/site.js                   # Nav, theme, reveal-on-scroll, accordions
│   ├── images/people/*.{jpg,png}    # Member headshots (downloaded by sync-bios)
│   ├── images/cost-logo.jpg         # COST logotype
│   └── images/logo.png              # Favicon / NS mark
│
├── data/
│   ├── bios.json                    # The directory (members, roles, WGs, contacts)
│   └── mc-members.json              # MC roster per country (used to auto-tag MC role)
│
├── scripts/
│   ├── sync-cost.py                 # Pulls WG_MAP + leadership from cost.eu
│   ├── sync-bios.py                 # Pulls Google Form submissions
│   ├── bios-source.json             # CSV URL + form URL + column mapping
│   └── requirements.txt             # requests, beautifulsoup4, Pillow
│
├── .github/workflows/
│   ├── sync-cost.yml                # Weekly cron — opens PR if WG_MAP / roles changed
│   └── sync-bios.yml                # Weekly cron — opens PR if bios.json changed
│
├── docs/                            # ← you are here
│   ├── README.md                    # ToC for this folder
│   ├── architecture.md              # this file
│   ├── design-system.md
│   ├── admin-guide.md
│   └── bios-setup.md                # One-time Google Form set-up guide
│
├── LICENSE                          # MIT (code)
├── LICENSE-CONTENT                  # CC BY 4.0 (prose) with carve-outs
├── README.md                        # Project entry point
├── SECURITY.md                      # Coordinated-disclosure policy
└── CNAME                            # GitHub Pages → netsec-cost.eu
```

## Naming and code conventions

- **British English** in all user-facing copy.
- **Slugs** are produced by `slugify()` in both Python sync scripts
  (must stay in lockstep): strip salutation prefix, drop diacritics,
  drop apostrophes, lowercase, replace anything not `[a-z0-9]` with
  `-`, collapse runs.
- **Member IDs** in `bios.json` are the slug of the cleaned name —
  stable across submissions, used as the DOM `id` on member cards
  so deep-links like `/people.html#arthur-laudrain` resolve.
- **Comments in CSS and JS** are full sentences explaining intent
  (why the code is there), not paraphrasing the code itself.
- **No JS framework, no transpiler, no bundler.** If a feature needs
  one, the bar is high — open an issue first.

## Extending the site

If you're adding a new page:

1. Copy `accessibility.html` as a skeleton — it has the canonical
   `<head>`, theme-FOUC script, ambience blobs, nav, and footer.
2. Update the nav `<a aria-current="page">` on the new page so the
   header shows the active link.
3. Add the page to `sitemap.html` and to every other page's footer
   list of statutory links if it's a statutory page.
4. Bump the version stamp in the page meta-strip if you're adding
   a privacy- or accessibility-relevant page.

If you're adding a new field to `bios.json`:

1. Add the question to the Google Form.
2. Add the column to `scripts/bios-source.json` → `columns`.
3. Add the field to `_make_seed_entry()` and to the form-row parser
   in `scripts/sync-bios.py`.
4. Render it where it should appear (`people.html`,
   `index.html` if leadership, `grants.html` if grant manager).
5. Update `docs/bios-setup.md` so the next admin doesn't have to
   reverse-engineer the change.
