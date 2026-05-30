# Admin guide

> *Audience: site administrators (currently the Action Chair, Vice-Chair,
> and the maintainer). Covers what you own, where to log in, and how
> to do common tasks.*

This guide is the answer to: *"It's six months later, the maintainer
is on parental leave, something needs editing — where do I start?"*

> **Working with Claude Code in this repo?** The standing rules
> (British English, no machine translation, auto-merge by default,
> release-notes carve-out, the *open-an-issue-for-every-deferred-item*
> policy) are at [`CLAUDE.md`](../CLAUDE.md) in the repository root.
> Claude reads it automatically on every session. Edit it via PR
> when a rule shifts.

## Accounts and assets

A snapshot of every external account or asset the site depends on.
Keep this current as roles change.

### Domain and DNS

| Asset                | Location                                                | Owner / login                              | Notes                                                                                |
| -------------------- | ------------------------------------------------------- | ------------------------------------------ | ------------------------------------------------------------------------------------ |
| `netsec-cost.eu`     | **Namecheap**                                           | Registered under **Dr Moritz Weiss** (Action Chair); admin contact **Dr Arthur Laudrain** | `CNAME` file at repo root points GitHub Pages here. Renewal alarm should be on file. |
| GitHub Pages routing | `Settings → Pages` in the repo                          | GitHub org `EISSeuropa`                    | Source: `main` branch, root. Custom domain enforced (HTTPS).                          |
| TLS certificate      | Auto-managed by GitHub Pages (Let's Encrypt)            | n/a                                        | No action required unless DNS changes.                                                |

### Code and hosting

| Asset                                                        | Login                                                  | Who has access                              |
| ------------------------------------------------------------ | ------------------------------------------------------ | ------------------------------------------- |
| GitHub repo <https://github.com/EISSeuropa/netsec.github.io> | GitHub account, member of `EISSeuropa` org              | Action Chair, Vice-Chair, maintainer        |
| GitHub Actions (sync workflows)                              | Inherited from repo permissions                         | Same                                        |
| GitHub Pages deployment                                      | Inherited from repo permissions                         | Same                                        |
| Dependabot security alerts                                   | Repo `Insights → Dependency graph`                      | Same                                        |
| Branch & tag protection rulesets                             | Repo `Settings → Rules → Rulesets`                      | Read by all; edited by repo admin           |
| Automation PAT (for `release.sh` and any `gh api` work)      | <https://github.com/settings/personal-access-tokens>    | The maintainer; do not share                |

#### Branch & tag protection in place

Two repository rulesets enforce the boundary between routine and
catastrophic operations:

- **`protect-main`** — targets the default branch. Restricts
  deletions and force-pushes, requires linear history, requires a
  pull request with all four CodeQL checks green before merging,
  restricts merge methods to squash. **Bypass: Repository Admin**
  (so `scripts/release.sh` can push the changelog-promotion commit
  directly).
- **`protect-release-tags`** — targets tags matching `v*`. Restricts
  deletions, updates, and force-updates. **No bypass for anyone**,
  including admins. Release tags are immutable once published.

Both visible at
<https://github.com/EISSeuropa/netsec.github.io/settings/rules>.
For the rationale, see the PDF documentation pack, Section 07
("Branch and tag protection").

> **Bus-factor reminder.** Every admin task below assumes at least
> two people hold `EISSeuropa` org membership with `Maintain`
> permission on this repo, and at least one with the **Admin** role
> (required for cutting releases). If either drops to one, escalate.

### Bios pipeline (Google Form → Sheet → repo)

| Asset                              | Login                       | Notes                                                                                          |
| ---------------------------------- | --------------------------- | ---------------------------------------------------------------------------------------------- |
| Google Form "Join the NetSec network" | Google account that owns the form | URL: see `scripts/bios-source.json` → `form_url`. Set up per [`bios-setup.md`](./bios-setup.md). |
| Linked Google Sheet                | Same Google account         | The form's *Responses → Link to Sheets* destination. Publish-to-web is enabled (CSV).          |
| Published CSV URL                  | n/a (public)                | Stored in `scripts/bios-source.json` → `csv_url`. It's a public capability URL (anyone with it can read the Sheet as CSV), not a credential — the form's required-consent step is what gates what reaches it. |
| Country dropdown source            | Apps Script bound to the form | One-off script that bulk-loaded ~200 countries into question #4. See `bios-setup.md`.         |

### Contact form (Formspree)

| Asset                               | Login                                  | Notes                                                                  |
| ----------------------------------- | -------------------------------------- | ---------------------------------------------------------------------- |
| Formspree project (id `meenwyrb`)   | Formspree account that owns the project | Free tier; submission destination is the Action mailbox. ID is public. |

### Branding and visual identity

| Asset             | Location                                              | Licence                                                                              |
| ----------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------ |
| COST logo         | `assets/images/cost-logo.jpg`                         | © COST Association — used per COST visual-identity guidance for funded Actions       |
| EU emblem         | Inlined SVG in every page footer                      | Used per the [EU visual identity manual](https://commission.europa.eu/communication/visual-identity-and-branding_en) for *Funded by the EU* communication |
| NetSec wordmark   | `NS` letter-mark — pure CSS, no asset                 | © COST Action NetSec                                                                 |
| Member headshots  | `assets/images/people/<slug>.{jpg,png,jpeg,webp}`     | © the individual member, displayed with their consent                                |
| Country flags     | <https://flagcdn.com> (loaded at runtime)             | Flags themselves public domain; CDN MIT                                              |

### Third-party CDNs loaded at runtime

These don't need accounts — listed so admins know what makes
network calls when someone loads the site.

| Service        | What it serves               | Privacy implication                                                                   |
| -------------- | ---------------------------- | ------------------------------------------------------------------------------------- |
| Google Fonts   | Inter + Lexend webfonts      | IP + UA logged by Google; declared in `privacy.html`.                                 |
| FlagCDN        | Country flag PNGs            | IP + UA logged by FlagCDN; declared in `privacy.html`.                                |
| Formspree      | Contact-form POST endpoint   | Only on submit. Acts as data processor under SCC; declared in `privacy.html`.         |

## Routine admin tasks

### Reviewing a weekly sync PR

Both sync workflows open PRs against `main` on the branches
`bios-sync/auto` and `cost-sync/auto`. Either may be empty most
weeks.

```mermaid
sequenceDiagram
    autonumber
    actor A as Admin
    participant G as GitHub
    participant W as Workflow
    participant R as main branch

    W->>G: Open PR on bios-sync/auto<br/>(or cost-sync/auto)
    G->>A: Notify (watching the repo)
    A->>G: Read PR body — it shows the human-readable diff
    alt All entries look right
        A->>G: Approve + merge
        G->>R: Squash-merge
    else Something off (typo in submission,<br/>photo too small, sus content)
        A->>G: Comment on the PR
        A->>A: Either edit the source<br/>(Google Sheet) and re-run<br/>the workflow, or close the PR<br/>and contact the submitter
    end
```

**Soft-review policy.** We don't auto-merge — every new bio passes
through a human's eyes. The reviewer's job is **not** to fact-check
research claims; it's to catch:

- obvious typos (e.g. ALL-CAPS surnames, missing capitals)
- broken or mis-targeted links (ORCID under the LinkedIn field)
- photos that aren't headshots
- anyone who didn't tick the consent checkbox (sync drops these
  automatically, but worth double-checking)

### Manually triggering a sync

When you can't wait for Monday morning:

1. Go to *Actions* in the GitHub repo.
2. Pick `Sync member bios from Google Form` or
   `Sync WG membership from cost.eu`.
3. Click **Run workflow** → **main** → **Run**.
4. Watch the run; if it opens a PR, review and merge.

### Removing a member at their request

1. Open `data/bios.json` (or the PR if a sync just added them).
2. Delete the relevant `members[]` entry.
3. Delete the headshot at `assets/images/people/<slug>.jpg` if present.
4. **Lock the source.** Open the Google Sheet and either:
   - delete the row (cleanest), or
   - clear the consent column → next sync drops them anyway.
5. Commit with message `bios: remove <slug> on request`.

### Updating the MC roster

Use only when cost.eu hasn't caught up yet:

1. Edit `data/mc-members.json` directly — add/remove the person.
2. Edit the country-grid block in `index.html` — same change.
3. PR + merge.
4. Next `sync-bios.py` run will use the new roster when auto-tagging
   "MC member · Country" on form submissions.

### Editing static page copy

No tooling required:

1. `git checkout -b copy/<short-description>`.
2. Edit the relevant `*.html` file.
3. Preview locally: `python3 -m http.server 8000` → open
   <http://localhost:8000>.
4. Open a PR. Merge once review is in.

GitHub Pages rebuilds in ~30 seconds after merge.

### Setting up a conference on Indico (ESSC and future editions)

A few one-off steps on the Indico event reduce the recurring email
load described in [#332](https://github.com/EISSeuropa/netsec.github.io/issues/332).
The public guidance for panelists lives in the FAQ *At a NetSec
conference* section; these are the organiser-side actions that back
it up.

1. **Grant panel chairs session-coordinator rights.** Being listed as
   a session convener is display-only and carries no rights. For a
   chair to reorganise their own panel (running order, timing within
   the session), assign them as a session **coordinator** under
   *Sessions → shield icon → Coordination*, then enable the relevant
   toggles under *Protection → Session coordinator rights*
   (Contributions, and Session blocks if they should manage blocks).
   Do this for every edition; it is not inherited. Chairs then work
   from *My sessions* on the event page.
2. **Confirm authors can self-edit their contributions.** Submitters
   should be able to edit their own contribution (paper title) so the
   FAQ self-service guidance holds. Name and affiliation shown on the
   programme come from the per-event author record (Indico stores a
   snapshot at link time, so a personal-profile change does not
   propagate), so those corrections come to us or are made on the
   contribution's author entry.
3. **Invitation letters via document generation.** We issue visa
   invitation letters through Indico's document-generation module
   (decided for ESSC 2026). Build an HTML/Jinja template once under
   the event or category *Customisation → Document Templates* (admin
   right required), then bulk-generate from the registrations list
   (*Actions → Generate Documents*) and publish each letter to the
   registrant's own registration page for self-download. This keeps
   letters off the manual-drafting pile. The signatory is still to be
   confirmed (likely the Action Chair, Dr Moritz Weiss); the public
   FAQ answer stays signatory-agnostic until then, and the request
   channel for applicants remains the contact form.

### Cutting a release

The release script handles the SemVer bump, the CHANGELOG promotion,
the annotated tag, and the GitHub Release publication in one pass:

```bash
./scripts/release.sh <X.Y.Z> "<short title>"
```

Five things to get right *before* running it (the fifth applies on
minor / major releases only):

1. **`[Unreleased]` follows the hybrid release-notes format** spelled
   out at the top of `CHANGELOG.md`. Concretely:

   - A one- to three-sentence **lede** in voice (what is this
     release *about*?).
   - Two to four **themed `### sub-sections`** carrying the actual
     narrative — prose intro per theme, with bullets inside only if
     the theme has multiple distinct pieces.
   - A canonical **`### Index of changes`** at the bottom with
     `#### Added` / `#### Changed` / `#### Deprecated` /
     `#### Removed` / `#### Fixed` / `#### Security` sub-headings
     (in that order, each appearing at most once).

   **Every PR that ships a user-visible change adds at least one
   bullet to `[Unreleased]` in the same PR** (`CLAUDE.md` §4). The
   bullet goes into the *existing* index sub-heading, never in a new
   one with the same name below it. Exempt: dependabot / Renovate
   PRs, the automated `indico-sync/auto` data refresh, and any
   internal-only commit (docs-only refresh, CI tooling, working-tree
   hygiene). The lede + themes are written at release-cutting time
   for minor / major releases only. That's the moment the maintainer
   reads back through the index and shapes it into a release story.

   The release script extracts `[Unreleased]` *verbatim* into the
   GitHub Release notes. Eyeball the body before confirming the
   prompt; whatever lives in `[Unreleased]` lands on the public
   release page.

2. **Self-policing tier**:

   - **Patch releases** (`1.x.y` with no headline feature) skip the
     lede + themes. Index only. People reading patch notes care
     about specifics, not narrative.
   - **Minor / major** releases get the full hybrid.
   - If you can't write a meaningful lede about a release, it's a
     patch. The format mirrors the actual significance.

3. **Title is 3–8 words, sentence case, no trailing punctuation.**
   The title flows into the CHANGELOG heading, the GitHub Release
   name, the release commit message, and the tag. Past titles:

   - v1.4.0: *Site-wide search, infrastructure and directory improvements*
   - v1.3.0: *Introducing FAQ and Glossary pages*
   - v1.2.0: *Press kit, directory tour, compact view*
   - v1.1.0: *Release tooling and PDF SemVer*
   - v1.0.0: *Initial public release*

4. **No hard wraps in prose.** Each prose paragraph, blockquote lede,
   and multi-line bullet in `[Unreleased]` must be a single source
   line. GitHub Releases renders markdown with the *break-on-newline*
   GFM variant — every soft `\n` becomes a `<br>` and forces the
   prose to render visibly narrow on the Releases page (even though
   it looks flowing on the `github.com` file view). One long line per
   paragraph keeps both renderings correct. Editor soft-wrap is fine;
   hard line-breaks inside a paragraph are not.

5. **For minor / major releases (`X.Y.0` / `X.0.0`) — cross-check
   five surfaces.** Skip on patch releases (`X.Y.Z` where `Z > 0`);
   they're scoped to small fixes. For each, ask *"did anything in
   this release change what this surface documents?"* and either edit
   in the same release or open a tracking issue.

   - **Roadmap** — `/roadmap.html` (+ FR + DE) and
     `docs/roadmap-2026.md`. Promote the just-shipped release from
     *In progress* → *Shipped*; confirm next planned release is
     still accurate; consider whether anything in *Under watch* is
     ready to promote.
   - **Sitemap** — `sitemap.xml` and `/sitemap.html` (+ FR + DE).
     Add any new pages. Re-run `scripts/inject-seo.py` if titles /
     canonicals / hreflang changed.
   - **Translations** — `python3 scripts/check-i18n-drift.py`
     should report zero drift before cutting. Manual update on FR
     / DE for any EN copy that moved.
   - **Repo docs + PDF** — the markdown docs under `docs/` and the
     stakeholder PDF doc-pack. Cover-bump the PDF every minor /
     major release; defer the section-level catch-up via an
     explicit "gap" appendix entry when needed (see
     `docs/pdf/documentation.html` v1.7.0 entry as the canonical
     example).
   - **Members' Wiki** — <https://github.com/EISSeuropa/netsec.github.io/wiki>.
     Public FAQ / Glossary are source-of-truth (the Wiki holds
     stubs); decisions log should record any structural rewrite
     or convention change; *Templates & press kit* should match
     `/press-kit.html`.

   The full version of this checklist, with the cadence reasoning,
   lives in [`CLAUDE.md`](../CLAUDE.md) §5.

The script prints `[Unreleased]` + the proposed tag/title and prompts
for `y` confirmation before publishing. That prompt is the last
moment to abort cleanly. Re-run with `--dry-run` to preview without
the prompt.

### Rotating the Formspree project

If submission volume hits the free-tier quota, or if we move to a
self-hosted alternative:

1. Create the new endpoint on the chosen provider.
2. Search the repo for `meenwyrb` — currently only in
   `index.html` and `privacy.html`.
3. Replace with the new endpoint ID / URL.
4. Update `privacy.html` if the processor changes (legal basis,
   SCC reference).
5. PR + merge.

## Escalation

If something breaks:

| Symptom                                               | First port of call                                              |
| ----------------------------------------------------- | --------------------------------------------------------------- |
| Site returns 404 / 500                                | <https://www.githubstatus.com>                                  |
| Sync workflow fails                                   | *Actions* tab → click the failed run → scroll to the red step   |
| Form submissions stop arriving                        | <https://formspree.io/forms/meenwyrb> dashboard                 |
| New bio doesn't appear after Monday's sync            | Check the Google Sheet (consent ticked? row present?) → manually trigger `Sync member bios` |
| Suspected security issue                              | Follow [`../SECURITY.md`](../SECURITY.md) — **do not open a public issue** |
| DNS / domain issue                                    | Registrar admin (TBC); GitHub Pages settings as a sanity check  |

## Handover checklist

When admin responsibility moves to a new person, walk through the
checklist in order. The branch-protection ruleset's bypass is keyed
to the repo `Admin` role, so the role transfer specifically needs
care — get this wrong and `release.sh` will start failing for
everyone.

### Access grants (new admin)

- [ ] Add them to the `EISSeuropa` org with **`Admin`** role on this
      repo (not `Maintain` or `Write`). This is what permits the
      `release.sh` bypass against the `protect-main` ruleset; without
      it they can still merge PRs but cannot cut releases.
- [ ] If a second person will stay on as a non-release-cutting
      maintainer, give them `Maintain` separately — the `Admin` role
      is for the release-cutter.
- [ ] Grant them ownership of the Google Form + linked Sheet.
- [ ] Grant them access to the Formspree project (or migrate the
      project to their account).
- [ ] Make sure they have edit rights to the DNS registrar entry
      for `netsec-cost.eu`.

### Automation handover

- [ ] If automation tooling (`release.sh`, `gh api` scripts) is to
      keep running, provision a fresh PAT in the new admin's name
      with these Repository permissions on this repo:
      `Contents: read+write`, `Pull requests: read+write`,
      `Issues: read+write`, `Workflows: read+write`,
      `Administration: read+write`. Verify by listing rulesets:
      `gh api /repos/EISSeuropa/netsec.github.io/rulesets`.
- [ ] Once the new admin has verified the rulesets are visible and
      correct via the API listing above, **downgrade
      `Administration` to `Read` only**. This is the least-privilege
      steady-state: the token can still inspect rulesets (useful for
      future verification) but cannot create, modify, or delete
      them. Re-grant `Administration: read+write` temporarily only
      when a ruleset adjustment is actually needed (and prefer the
      Settings → Rules UI for one-off tweaks).
- [ ] Revoke the previous admin's PAT immediately after the new one
      is verified.

> **Why two-step on `Administration`.** The bypass that lets
> `release.sh` push the changelog-promotion commit through the
> `protect-main` ruleset is keyed to the user's *repository role*
> (`Admin`), not to the PAT's `Administration` permission. So
> downgrading the PAT to `Administration: Read` leaves the release
> pipeline working unchanged, while shrinking the blast radius of a
> leaked token: a compromised read-only token can no longer silently
> disable the rulesets that guard against catastrophic action.

### Verification

- [ ] Walk the new admin through this document and the
      [architecture overview](./architecture.md).
- [ ] Have them run `scripts/release.sh 0.0.0 --dry-run` from a
      synced `main`. Pre-flight should report
      *"✓ On main, clean, in sync with origin, v0.0.0 is fresh"*
      and stop there. (Nothing is changed by a dry-run.)
- [ ] Have them visit
      <https://github.com/EISSeuropa/netsec.github.io/settings/rules>
      and confirm both rulesets are listed as **Active**.

### Revocation (previous admin)

- [ ] Remove the previous admin's repo access. Their bypass capability
      against `protect-main` disappears the moment their `Admin` role
      is removed — verified by GitHub on every push.
- [ ] Remove or downgrade their org membership per policy.
- [ ] Update the **Owner / login** column above with the new owner.
