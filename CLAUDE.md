# Claude project rules — netsec.github.io

Read by Claude Code on every session in this repository. Codifies the
standing constraints the maintainer has set for AI-assisted work, so
they survive context-window expiry. Update via PR when a rule shifts.

The single human reader of this file is the maintainer (Dr Arthur
Laudrain). Keep it terse — every word here is read once per session
and costs context.

---

## 1. Language & translation

- **British English** in all user-facing copy (site pages, the
  documentation pack, the accessibility statement, CHANGELOG release
  notes, GitHub Release bodies, PR descriptions where they'll be
  read by COST evaluators or members). Internal commit messages and
  code comments can be more relaxed but should not flip mid-document.
- **No machine translation, ever.** FR and DE variants are
  translated by hand. The beta-translation ribbon on `*.fr.html` /
  `*.de.html` says *"Traduction manuelle"* / *"Manuell übersetzt"*.
  If you find any user-facing copy that implies machine translation,
  fix it (see PR #111 for the canonical correction).

## 2. Pull-request workflow

- **Branch first, always (never commit on `main`).** The very first
  step of any task that will edit files is `git checkout -b
  <feature>`, *before* the first edit, not just before the commit. The
  natural `git checkout main && git pull` at task start leaves you on
  `main`, so create the branch immediately after. Every change reaches
  `main` only through a squashed PR. The one exception is the release
  commit, which `scripts/release.sh` writes on `main` on purpose. A
  committed guard hook (`.claude/hooks/guard-main-commit.sh`, wired in
  the shared `.claude/settings.json`) blocks a stray `git commit` on
  `main` as a backstop. It is the only part of `.claude/` that is not
  gitignored, so the guard travels with the repo. Also prefer explicit
  `git add <paths>` over `git add -A`, so stray scratch files never get
  swept into a commit.
- **Auto-merge by default.** Open the PR with `gh pr create`, then
  arm auto-merge with `gh pr merge --auto --squash`. CI checks (the
  link checker on every HTML-touching PR + CodeQL) will hold the
  merge if anything is wrong.
- **Carve-out: release notes.** When cutting a release via
  `scripts/release.sh`, eyeball the lede + themes + index before
  confirming the publish prompt. The maintainer expects to see the
  proposed notes; the carve-out exists precisely because publication
  to GitHub Releases is harder to undo than a merge.
- **Squash, not merge commits.** Every PR ends as a single commit on
  `main`. The release-cutter then writes the release commit on top.

## 3. Open a GitHub issue for every deferred item

Whenever you identify work that won't ship *this turn* — a bug, a
feature need, a structural follow-up, a "queued for later" finding —
**open a GitHub issue before the session ends.** The audit trail
self-references that way; loose ends survive context-window expiry
and release cycles.

### When to open an issue

- A **bug** you've spotted but aren't fixing now (because it's
  out of scope for the current PR, needs further investigation,
  or pairs better with future work). Example: PR #117 fixed the
  libjpeg-determinism symptom with a hash check; the deeper
  question of whether photos belong in git at all became
  [#119](https://github.com/EISSeuropa/netsec.github.io/issues/119).
- A **feature need** that surfaced from a user journey, an audit,
  or a maintainer conversation but isn't being scoped this turn.
- A **structural follow-up** — i.e. the current PR papered over a
  symptom but the root cause needs a different fix.
- A **deferral with a tag** — "queued for v1.6.0", "after public
  push", "needs design pass". Anything that ends up in the
  audit-trail tables of `docs/launch-qa-2026.md` or the *Under
  watch* section of `docs/roadmap-2026.md` belongs in an issue too.

### When **not** to open an issue

- Work that's shipping *this turn* — the PR is the record.
- Pure observations that need no action (e.g. *"the chevron
  rotation reads as identity in headless `getComputedStyle`; CSS
  rule is correct, real-browser confirmation pending"*).
- Duplicates — always `gh issue list --state open --search "..."`
  first, and prefer linking + commenting on an existing issue.
- Trivial inline fixes you can do in seconds without context
  switch.

### Issue template

External contributors filing through the GitHub UI land on one of
three structured YAML forms in `.github/ISSUE_TEMPLATE/`:
`bug_report.yml`, `enhancement.yml`, `documentation.yml`. Each
form has required preflight checkboxes and required-field
textareas; the chooser's `config.yml` disables blank issues and
routes routine questions to the public contact form, the FAQ,
and the Wiki onboarding page.

Maintainer-authored issues filed via `gh issue create` (the
common path for follow-up work spotted mid-session) follow the
same four-section shape the forms enforce, kept here as the
canonical body content:

```markdown
## What's happening
One paragraph + a concrete repro or pointer.

## Why it matters
One paragraph. User impact, audit-trail context, or accessibility /
compliance angle.

## Fix path (or fix options)
Specific enough that a future maintainer can pick it up without
re-deriving the analysis. Code paths, file names, line numbers.

## Target
Milestone or version, e.g. "v1.6.0 / v1.7.0".
```

**Set the GitHub milestone at creation time** (rule §10):
`gh issue create --milestone vX.Y.Z ...`. The `Target` line
in the body is human-readable context; the milestone is the
queryable commitment.

Labels — use the standard set already present in this repo (`bug`,
`enhancement`, `documentation`). Don't invent new labels without
asking; the label set is small on purpose.

### Cross-reference

When an issue closes a deferred row in an audit doc (e.g. a finding
in `docs/launch-qa-2026.md`, an "Under watch" entry in
`docs/roadmap-2026.md`, or a "needs follow-up" note in the
accessibility statement) — **edit the audit doc to link the new
issue.** Status should read e.g. "open (tracked in #119)" rather
than the dangling "deferred".

See PRs #115 and #124 for the canonical pattern.

## 4. Release-notes format

The hybrid format is documented at the top of `CHANGELOG.md`,
mirrored in `docs/admin-guide.md` *Cutting a release*, and
restated in `scripts/release.sh`'s header. Every release section
follows it; v1.0.0 → v1.5.0 were retrofitted to match.

Short version: **lede + 2-4 themed `### sub-sections` + canonical
`### Index of changes`**. Self-policing tier — patch releases skip
the lede + themes and ship the index only.

**Minor vs patch: the feature test** (see `README.md` → *Versioning*
for the full table). A minor (`X.Y.0` where `Y > prev`) ships at
least one new user-visible feature or a significantly improved
existing feature. Anything else (content additions on an
existing page, copy edits, translation refreshes, accessibility
passes, dependency bumps) is a patch. Read the lede aloud: *"we
polished / fixed / refreshed X"* → patch; *"you can now do X"* →
minor. When in doubt, patch.

Hard rule: **no hard wraps in prose.** One source line per
paragraph / bullet / blockquote. GitHub Releases renders soft `\n`
as `<br>` and would otherwise produce visibly narrow prose.

**Keep `[Unreleased]` current.** Every PR that introduces a
user-visible change adds at least one bullet under
`[Unreleased]` → `#### Added` / `#### Changed` / `#### Fixed` in
the same PR. Reconstructing a release batch from the git log at
release time loses nuance and burns time; capturing the bullet
while the context is fresh is cheap. Exempt: dependabot / Renovate
PRs, the automated `indico-sync/auto` data refresh PRs, and any
internal-only commit (docs-only refresh, CI tooling, working-tree
hygiene). When in doubt, add the bullet. Cutting a release
becomes: review what's already there, decide on the title,
`scripts/release.sh`.

## 5. Release-time six-point cross-check (minor / major only)

Every **minor (`X.Y.0` where `Y > prev`) or major (`X.0.0`)
release** should trigger a deliberate check across six surfaces
before `scripts/release.sh` runs. Skip the cross-check on **patch
releases** (`X.Y.Z` where `Z > 0`) — they're scoped to small
fixes and the overhead isn't justified. The release script's
*self-policing tier* mirrors this: patches ship the index only.

For each surface, the question is the same: *"Did anything in
this release change what this surface documents?"* If yes, edit
in the same release. If yes but too big to fit, open a tracking
issue (rule §3) and reference it from the surface itself.

### 1. Roadmap (`/roadmap.html` + FR + DE + `docs/roadmap-2026.md`)

- The `planned → shipped` flip on the public roadmap (`/roadmap.html`
  + FR + DE) is handled automatically by `scripts/release.sh` via
  `scripts/promote-roadmap.py`. That script also bumps the
  *Last updated* / *Dernière mise à jour* / *Zuletzt aktualisiert*
  stamps + the two `<time datetime="…">` attributes in the same
  paragraph. Pre-condition: the v\<version\> card must already
  exist as a `<li class="rm-entry planned">` entry in all three
  locales (or, for a snap patch release, hand-added as already
  shipped). The script fails soft with an exit-2 warning if it
  finds no card to promote.
- **In-flight progress bars are auto-synced.** Each planned /
  in-progress card carries `data-milestone="vX.Y.Z"`, and
  `assets/js/roadmap-progress.js` renders a progress bar from
  `data/roadmap-progress.json` (closed / total issues on the matching
  GitHub milestone, refreshed by the `roadmap-progress.yml` workflow on
  every issue / milestone change). No manual action at release time.
  One thing to remember when **hand-adding a new planned card** (the
  pre-condition above): give it the matching `data-milestone` so its
  bar appears. Shipped cards keep no bar (the renderer skips them), so
  the attribute can be left in place when `promote-roadmap.py` flips
  the card.
- **The next incoming release shows as *In progress* automatically.**
  `roadmap-progress.js` promotes the first still-planned version card
  (event-marker `.rm-milestone` cards excluded) to *In progress* at
  render, with a slow-blinking status dot. This is **presentational
  only**: the static markup stays `class="rm-entry planned"`, so
  `promote-roadmap.py` still finds the card to flip to shipped at
  release. When a release ships, the next card becomes *In progress*
  on its own. So on the live site the next-up card reads *In progress*
  even though the HTML says planned. Do not hand-edit a card to
  `in-progress` to chase this.
- **The card title + body are derived from `CHANGELOG.md` at promote
  time** (issue #233): the script overwrites the planned card's
  `<h3>` with the released section's heading title and its `<p>` with
  the section lede (the first `>` blockquote, or a synthesised
  sentence for index-only patch releases). This replaced an earlier
  git-blame staleness warning that only fired *after* stale planned
  scope had already shipped. EN gets the CHANGELOG copy directly; FR
  + DE get the EN copy plus a `[à traduire]` / `[zu übersetzen]`
  marker on the lede, so `check-i18n-drift.py` flags the card for a
  hand translation (no machine translation, rule §1). Translate the
  FR + DE card bodies in a follow-up before the marker lingers.
- **The script also relocates the card into the quarter matching its
  ship date** (issue #233): if a release shipped earlier or later
  than its planned card's `<ol class="rm-timeline">` quarter, the
  card moves to the right `QN` / `TN` section (inserted after that
  quarter's shipped cards, before its planned ones). So the timeline
  *is* reordered now; just confirm the next planned release below the
  shipped card still reads accurately.
- Anything in *Under watch* (the deferred-items section at the
  foot of the page) ready to promote to a dated entry? (Manual.)
- The autostamp in `docs/roadmap-2026.md` updates separately via
  `.github/workflows/sync-roadmap.yml` on every `CHANGELOG.md`
  change, so the *N entries in [Unreleased]* line is always
  current without manual action. The prose timeline + the
  *Last revised* line in `docs/roadmap-2026.md` are still
  maintainer-edited.

### 2. Sitemap (`sitemap.xml` + `/sitemap.html` + FR + DE)

- New pages added in this release? Add to `sitemap.xml` and to
  the visual `/sitemap.html` inventory.
- `scripts/inject-seo.py` regenerates `sitemap.xml` — re-run if
  any `<title>` / canonical / hreflang changed.
- The visual sitemap is hand-edited; confirm new pages show up
  in the correct branch (*About & policies* / *Working areas* /
  etc.).

### 3. Translations (FR + DE variants)

- Run `python3 scripts/check-i18n-drift.py` locally. CI catches
  drift on HTML-touching PRs, but a release moment is the right
  place to confirm zero drift before stamping a version.
- Did any EN copy change in this release? FR / DE need manual
  updates (no machine translation — rule §1).
- Ribbon stamps on `*.fr.html` / `*.de.html` carry
  `data-i18n-status="beta"`; if a translation has been
  re-verified against current EN, consider whether the *beta*
  marker still applies.

### 4. Repo docs + documentation PDF

- The maintainer-facing markdown docs under `docs/`
  (`architecture.md`, `design-system.md`, `admin-guide.md`,
  `bios-setup.md`, `i18n.md`, `seo.md`, `search-assessment.md`,
  `launch-qa-2026.md`) — does anything in this release contradict
  what's documented?
- The stakeholder PDF (`docs/pdf/NetSec-website-documentation.pdf`,
  source at `docs/pdf/documentation.html`) carries its own
  version stamp and changelog appendix. **Minor / major releases
  only; patches skip the PDF entirely.** Two-tier cadence within
  the minor / major track:
  - **Cover bump** on every minor / major release. Bump the
    stamp + add a short appendix entry. Acceptable to defer
    section-level catch-up via an explicit "gap" entry (pattern:
    pack v1.7.0 in PR #116; tracking
    [#122](https://github.com/EISSeuropa/netsec.github.io/issues/122)).
  - **Section-level catch-up** is substantive: refresh
    Section 02 site graph + page inventory, refresh
    screenshots via `./docs/pdf/build.sh --shots`. Batch
    when site shape stabilises (typically every 2-3 minor
    releases, not every minor).

### 5. Members' Wiki

- The Wiki at <https://github.com/EISSeuropa/netsec.github.io/wiki>
  holds glossary, FAQ stubs, onboarding for new MC reps, meeting
  notes, decisions log, templates & press-kit page.
- The public FAQ at `/faq.html` and Glossary at `/glossary.html`
  are the source of truth; the Wiki pages of the same name are
  short stubs pointing at them. **Don't drift the stubs** — if
  the public pages change, leave the stubs alone (they only
  link).
- *Decisions log* — did anything in this release warrant a brief
  decision-log entry? (Format choices, structural rewrites,
  branch-protection changes are typical examples.)
- *Templates & press kit* — does the public press kit `/press-kit.html`
  match the Wiki copy-paste boilerplate?

### 6. *What's New* banner currency

- `data/whats-new.json` carries `active: false` by default. If it
  was flipped `true` for a recent campaign (brand launch, ESSC
  live programme going up, founding cohort going up), is that
  campaign **still relevant** to a visitor landing in the next
  4-6 weeks?
- Yes → leave it on. The dismissal `localStorage` key tracks
  per-`version`, so as long as you don't change `version`,
  visitors who dismissed don't re-see it.
- No → flip `active: false` in the same release. The mechanism
  is deliberately manual (CLAUDE.md §14): the friction is the
  gate. Doing this at the release-day cross-check ensures the
  banner doesn't decay into furniture between cycles.
- Activating a new banner is the rarer move (§14 sets the bar
  high: a new visible section, a major feature, a deliverable
  milestone). If this release qualifies, edit `data/whats-new.json`
  now and pick a `version` string (typically `vX.Y.0`). The full
  CTA + headline + locale strings can land in the same release
  commit.

### 7. Milestone hygiene (gate, not a surface)

- Every issue closed by this release carries the matching
  milestone — `gh issue list --milestone vX.Y.Z --state closed`
  should equal the *Fixed/Resolved/Closes* references in the
  changelog index.
- Every issue still open and tagged with this milestone has
  either been ticked off in the release notes or has been moved
  to the next milestone with a one-line reason in the issue
  thread. The release should not ship with its own milestone
  holding open work — see rule §10.

This is a deliberate friction-point: cutting a minor release on
this repo is **slightly more work than running release.sh**, by
design. The release script's confirmation prompt is the last
moment to bail if the cross-check surfaces something that needs
to land in the same release.

## 6. Voice for public-facing copy

Public-facing copy means anything that appears on `netsec-cost.eu`
pages, the beta ribbon, the accessibility statement, the press
kit, OG card descriptions. Readers are COST evaluators,
journalists, MC representatives, and prospective members. None
of them are developers; none of them care how the site is built.

**No "source of truth".** It is developer jargon. Acceptable
substitutes by context include "authoritative source", "Indico",
"the form", "the directory".

**Show, don't tell, for feature mechanics.** If a page surfaces
synced data, don't write a sentence explaining the sync. Surface
liveness with a visual cue. The pulsing green dot next to "Live
programme" on `/essc-2026.html` is the canonical example.
Mechanism descriptions belong in the maintainer docs and the
decisions log.

## 7. Prose voice (em dashes and AI patterns)

These apply to every piece of prose I author in this project:
the public site, the CHANGELOG, PR descriptions, the Wiki
decisions log, the documentation pack body text, multi-paragraph
code comments. (One-line `# label` code comments stay flexible.)

**No em dashes.** Use commas, parentheses, full stops, or
colons. Em dashes pattern-match to AI-generated prose; a careful
reader notices.

**No rule-of-three rhythm.** If there are two items, write two.
If there are five, write five. Manufactured triplets for cadence
are the most reliable AI tell.

**No synonym cycling.** Pick one referent for an entity and
reuse it across consecutive sentences. Writing "the script" then
"the sync" then "the workflow" for the same thing in three
sentences is an AI tell, even when each label is technically
accurate.

The rules are forward-looking. They apply to prose authored from
the PR that introduces them onwards; pre-existing em dashes in
the repo aren't retroactively scrubbed unless the surrounding
text is being edited anyway.

## 8. Working tree hygiene

- Never leave the working tree dirty across PR boundaries. If a
  script (e.g. `sync-bios.py`, `build-search.sh`) modifies tracked
  files as a side-effect of a verification run, decide whether the
  modification is part of the current PR (include it) or an
  unrelated drift (revert before committing).
- The weekly bios-sync workflow is structurally tuned to produce
  zero dirty files when no submitter has substantively changed
  their entry (PR #117). If you see the workflow trip an
  apparently-empty PR, that's a regression — open an issue and
  investigate before silencing.

## 9. Accessibility & i18n cadence

- The accessibility statement at `/accessibility.html` (+ FR + DE)
  is bumped on every release that touches a11y conformance,
  audit results, or a known-limitations list. Version footer:
  `v<N>.<M> · prepared <date> · supersedes v<prev> · next
  scheduled review <date+1y>`.
- FR / DE drift checker (`scripts/check-i18n-drift.py`) runs in CI
  on every HTML-touching PR. When it flags drift, refresh the
  translation manually before merging.

## 10. Milestone tagging

Every open issue belongs to exactly one milestone. The milestone
is the bridge between the `Target` line in the issue template
(rule §3) and the planned releases on the roadmap; without it,
the backlog drifts and "queued for v1.7.0" becomes a string
floating in prose rather than a queryable commitment.

### The milestone set

Milestones are created on GitHub from the version-tagged rows of
[`docs/roadmap-2026.md`](docs/roadmap-2026.md)'s *At a glance*
timeline. One milestone per planned release plus a single
`Backlog — Under watch` bucket for items waiting on external
triggers (COST-office decisions, post-conference activities,
larger redesigns with no fixed slot yet).

Two non-versioned milestones predate this convention
(`Directory Page and Workflow`, `Translations (FR+GE) in Beta`).
Both are closed; they are pre-versioning history, intentionally
not on the public roadmap (the roadmap-progress sync skips any
title that isn't `vX.Y.Z`). Leave them as-is, do not rename them
to versions (their work spanned several early releases, so no
single version maps).

Due dates on the milestones come from the same timeline. When the
roadmap shifts a planned release, **bump the milestone's due date
in the same commit that updates the roadmap row** — they're two
projections of the same plan.

### When to set the milestone

- **At issue creation.** Whenever rule §3 fires, set the
  milestone alongside the title and body. `gh issue create
  --milestone v1.7.0 ...` keeps it inline.
- **When an issue moves between releases.** Update the milestone
  in the same edit that records the slip ("deferred to v1.8.0 —
  out of scope for v1.7.0 in this PR").
- **Never leave an open issue without one.** A milestone-less
  open issue is invisible to release planning. The `Backlog —
  Under watch` bucket exists so there's no excuse: items with no
  clear release home still get tagged.

### Pre-release check

Add to the rule §5 six-point cross-check: before running
`scripts/release.sh`, confirm that every issue **closed by this
release** carries the matching milestone, and that any **still-
open issue tagged with this milestone** has either been ticked off
in the release notes or moved to the next milestone with a one-
line reason in the issue thread. The release should not ship with
its own milestone holding open work.

`scripts/release.sh` lists the currently-open issues tagged with
the milestone you're about to cut, in the y/n confirmation prompt
block. Skim it before typing `y`. If the work for an issue actually
shipped (the PR landed, the bullet sits in `[Unreleased]`, the
feature works on the live site) but no one wrote `Closes #N` in the
PR description, that issue is still open and needs explicit closure
on release day:

```
gh issue close <N> --comment "Shipped in v<X.Y.Z>"
```

If the work hasn't shipped, the issue should already have been
re-milestoned in the PR that decided to defer it.

## 11. Documentation currency

The site has three classes of documentation, and each has a
different cadence for staying current.

### Repo `.md` docs + Wiki: three rules

1. **Inline at PR time.** If a PR changes something a doc
   describes (an architectural component, a documented
   procedure, the public surface of a script that has its own
   `.md` doc), the same PR updates that doc. Same posture as
   the per-PR `[Unreleased]` rule in §4. Examples:
   `architecture.md` for data-flow changes, `admin-guide.md`
   for procedure changes, `indico-sync.md` for sync changes,
   `bios-setup.md` for bios-form changes, the Wiki *How-tos*
   page when the matching public surface changes.

2. **Wiki *Decisions* log when a structural decision lands.**
   "Structural" here means: chose A over a credible B, future
   maintainer might re-litigate. Format and criteria are
   already at the top of the Wiki *Decisions* page. Cadence:
   within a week of the decision (ideally the same PR), single
   entry per decision. Roughly 1-3 entries per release at the
   current cadence.

3. **Catch-up sweep at every release** (patch, minor, major).
   Walk the repo `.md` index + the Wiki page list, spot-check
   each against what shipped, fix what's wrong. Lightweight by
   design: most PRs already updated their target doc inline, so
   the sweep is the safety net rather than the workhorse. This
   is also point 4 in §5's cross-check, which only fires on
   minor / major; the new rule extends the sweep to patches but
   keeps it deliberately shallow (no comprehensive read-through;
   spot-check only).

#### Automation note: `docs/roadmap-2026.md` autostamp

`.github/workflows/sync-roadmap.yml` keeps the AUTOSTAMP block
near the top of `docs/roadmap-2026.md` in sync with `CHANGELOG.md`'s
`[Unreleased]` section. It counts the bullets per category,
records the freshness date, and anchors against the most recent
SemVer tag. Triggers on every push to `main` that touches
`CHANGELOG.md` (plus weekly Monday 06:00 UTC + manual dispatch),
opens an auto-PR on `roadmap-sync/auto` with auto-merge armed.

So the maintainer never has to manually refresh the count or
freshness stamp; that's handled. **What the automation does NOT
do**: rewrite the prose timeline rows. When the count visibly
diverges from what the prose says is in flight, the maintainer
resynthesises by hand (which is also a §5 cross-check item at
release time). The autostamp is the staleness alarm; humans
write the synthesis.

**Why per-release instead of every N PRs.** Threshold options
considered: (a) at every release; (b) every N user-visible PRs
(N=5 was the candidate); (c) every M days (M=14). Option (a)
ties to a rhythm the maintainer already runs and never drifts
into "I forgot when I last swept". Options (b) and (c) decouple
from cadence but add a counter to remember. (a) wins on the
"will the maintainer actually do this" metric. If the release
cadence ever slows to less than monthly, revisit and consider
adding a calendar fallback.

### PDF documentation pack: minor / major only

Per §5 point 4: the PDF (`docs/pdf/NetSec-website-documentation.pdf`)
is refreshed on every minor / major release; patches skip it.
Cover bump always, section-level catch-up batched every 2-3
minor releases. The PDF carries its own version stamp and
appendix, and is built from `docs/pdf/documentation.html`.

## 12. Release-infrastructure hygiene

Three conventions on the `.github/` tree, codified together so the
next maintainer inherits them rather than rederiving from
`anthropics/claude-code`'s shape (which is where these came from
in May 2026).

### SHA-pin third-party Actions

Every `uses:` line in `.github/workflows/*.yml` that references
a third-party action (anyone other than `actions/*` shipped by
GitHub) pins to a commit SHA, with a trailing `# vN (sha-pinned)`
comment for human readability:

```yaml
uses: peter-evans/create-pull-request@22a9089034f40e5a961c8808d113e2c98fb63676  # v7 (sha-pinned)
```

For consistency the convention covers `actions/*` too, even
though those are first-party. Dependabot continues to surface
updates via PR and bumps the SHA explicitly each time. Resolve
a fresh SHA with:

```bash
gh api repos/<owner>/<repo>/commits/<tag> --jq '.sha'
```

Don't paste a tag without a SHA. The CI bypass exists exactly to
keep workflows running under the permissions we already granted,
so a tag-based supply-chain compromise inherits those permissions
on the next sync.

### Issue templates are YAML forms, not free-form markdown

External contributors filing through the GitHub UI land on one
of three structured forms in `.github/ISSUE_TEMPLATE/`:
`bug_report.yml`, `enhancement.yml`, `documentation.yml`. The
chooser's `config.yml` sets `blank_issues_enabled: false` and
routes routine questions to the public site and the Wiki.

When adding a new template, follow the existing form-schema
shape: required preflight checkboxes (search existing, single
report), required textareas for the substantive content, and a
`labels:` block that auto-applies the matching label.

Maintainer-authored issues filed via `gh issue create` (the
common path for mid-session follow-up work) still use the
four-section body shape from rule §3: *What's happening / Why
it matters / Fix path / Target*. The forms enforce the same
shape on external contributors.

### Lifecycle-label vocabulary

Four labels drive the automated lifecycle workflows:

| Label | Applied when | What fires |
| --- | --- | --- |
| `needs-info` | The maintainer asks the reporter for more details. | `issue-lifecycle-comment.yml` posts the standard ask + the 14-day clock notice. `issue-sweep.yml` closes the issue if no human comment lands in 14 days. |
| `stale` | An open issue has 60+ days of no activity. | Auto-applied by `issue-sweep.yml`. `issue-lifecycle-comment.yml` posts the 14-day-to-close warning. Closes after another 14 days unless someone comments. |
| `duplicate` | The maintainer closes a duplicate of another issue. | `issue-lifecycle-comment.yml` posts the standard close message pointing at the original. |
| `wontfix` | The maintainer closes without acting on the request. | `issue-lifecycle-comment.yml` posts the standard close message recording the reasoning context. |

Issues stay open under `needs-info` and `stale` while the
clocks run. The `issue-sweep.yml` workflow runs once daily and
the `lock-closed-issues.yml` workflow locks any closed issue
14 days after closure (drive-by comment prevention).

When adding a new lifecycle label, update the `messages`
dictionary in `issue-lifecycle-comment.yml` and the table
above. Labels not in the dictionary are silently ignored by
the workflow, so a forgotten update is non-fatal.

## 13. Cross-repo Project: NetSec + EISS websites

The maintainer runs two related repos under the `EISSeuropa`
account: this one (`netsec.github.io`, the NetSec website) and
`EISSeuropa.github.io` (the EISS website). They share patterns
(the runtime-render-from-JSON renderer, the Indico sync
pipeline, the `.glass` / popover style language, the brand
deployment workflow) and features often port from one to the
other.

A single user-level GitHub Project surfaces the cross-repo
overlap without duplicating bookkeeping:

**<https://github.com/users/EISSeuropa/projects/1>** — *NetSec
+ EISS websites*.

### What goes in

- Every open `enhancement` issue on either repo. Auto-add isn't
  wired yet (Projects v2 needs per-repo UI configuration under
  each repo's *Projects* tab); meanwhile, `gh project item-add 1
  --owner EISSeuropa --url <issue-url>` adds them by hand.
- Bug issues stay in their own repo's tracker unless they
  cross-cut both sites (e.g. the same `.glass` stacking-context
  trap surfacing on both).

### What does not go in

- Closed issues. They stay in the issue tracker for the audit
  trail; the Project is forward-looking.
- Per-repo operational follow-ups with no cross-repo parallel
  (e.g. a NetSec-only data fix). Leaves the Project as signal.
- Milestoned work already on a clear release path. **Milestones
  remain the source of truth for release planning** (rule §10);
  the Project is a view over the issue list, not a replacement.

### Custom fields

One field beyond the GitHub defaults:

- **Effort** (single-select: S / M / L). Set on triage. Helps
  the Roadmap view show whether a queue is realistically
  deliverable in the next cycle.

Projects creep is real — add more fields only when a recurring
need surfaces. The default **Status** field (`Todo` / `In
Progress` / `Done`) is fine. If a richer triage state ever
becomes useful (*Triage* / *Backlog* / *In flight* / *Shipped*
/ *Wontfix*), that's a UI edit on the Project page.

### When to look at it

- Before opening a new feature issue on either repo, scan the
  Project board to see whether the parallel already exists on
  the other site. If yes, link the new issue to the existing
  one rather than duplicating the discussion.
- At the start of every release cycle (rule §5), use the
  Roadmap view to spot cross-repo dependencies. Most common
  pattern: a feature ships on one site and gets ported to the
  other. The Project surfaces that pairing.
- The Project is **not** part of the rule §5 cross-check. Its
  job is between-cycle ambient awareness, not release gating.

### Maintenance

- New `enhancement` issues on either repo: add via the `gh
  project item-add` one-liner above. Effort field is fastest to
  set in the web UI.
- When an issue closes, the Project auto-tags it `Done`. Don't
  delete the item; the Done lane is the audit trail.
- If the Project becomes a museum (more than ~20% `Done` items
  in any view, or no Effort tags being added on new entries),
  it's past its useful life. Archive it or trim back to a
  triage-only view.

## 14. *What's New* banner: sparingly

The site has a small dismissible banner that appears at the top
of every page when `data/whats-new.json` carries `active: true`.
Visitors who dismiss it don't see it again unless the
maintainer publishes a new entry (each entry is keyed by a
`version` string the dismissal `localStorage` tracks).

The point of the banner is to surface things a returning visitor
would want to know about without scrolling. CHANGELOG and
roadmap pages are developer-facing; the banner is the only path
that reaches everyday visitors.

### When to activate it

The bar is high. Activate only for a release that introduces:

- A new section a returning visitor will want to see (founding
  contributors landing on `/about`, members directory rebooted,
  outputs page going live with real publications).
- A major new feature visible without scrolling (live ESSC
  programme going live, brand identity launching, sitewide
  search shipping).
- A content milestone tied to the Action's deliverables (D1
  ships, D6 ships, Year 1 retrospective lands).

### When NOT to activate it

The much longer list:

- Quality patches (the v1.8.1 / v1.10.0 cadence — visitors
  don't care which em-dashes got fixed).
- Structural refactors that don't change what visitors see
  (the v1.9.0 events-from-JSON refactor: visible to operators,
  invisible to visitors who weren't paying attention to drift).
- Release-infrastructure changes (CI tweaks, Dependabot, voice
  rules, milestone reshuffles).
- Copy edits, translation refreshes, accessibility passes.

### Cadence

**At most 3-4 activations per year.** Each on-state lasts
**4-6 weeks max** before the maintainer flips `active: false`
manually. Banner fatigue is the failure mode — visitors learn
to ignore it if it's always on, and the next genuine
announcement loses signal.

The maintainer flips `active` true → false directly in
`data/whats-new.json`. No automation. The friction is the
gate: if you can't be bothered to edit a JSON file, the
announcement isn't important enough.

### Implementation

- `data/whats-new.json` — source of truth. Schema in the
  `_documentation` block at the top of the file. `_example_active_state`
  shows a populated entry from the v1.8.0 brand-launch cycle as
  a template.
- `assets/js/site.js` — the banner-render IIFE at the bottom of
  the file. Reads the JSON, applies locale, handles dismissal,
  inserts at `body.firstChild`. Silent no-op on fetch error.
- `assets/css/site.css` — `.whats-new-banner` and friends, with
  a slide-in animation on mount and slide-out on dismiss.
- The banner is NOT part of any drift checker — there's nothing
  to keep in sync.

## 15. Model & effort defaults

The standing model and reasoning-effort defaults live in
`.claude/settings.local.json` (gitignored): `opusplan` (plan in
Opus, execute in Sonnet) at `medium` effort. The full per-task
matrix and the reasoning behind it are in
[`docs/claude-usage.md`](docs/claude-usage.md), kept out of this
file so it costs no per-session context.

Two things a config file cannot do, so they belong here as
behaviour:

- **Plan first on multi-surface work.** Anything spanning more
  than one or two files (a feature touching the three locale
  HTMLs plus CSS, a script, the CHANGELOG) goes through plan mode
  before the first edit. Front-loading the plan is what avoids
  expensive rework across locales and CI.
- **Flag an effort mismatch, do not silently absorb it.** When a
  task plainly needs deeper reasoning (cross-file debugging, a
  structural change) or plainly does not (a one-line copy fix),
  say so and recommend bumping or dropping the dial. The live call
  on whether a task is worth Opus or high effort stays with the
  maintainer, the only one who can see the remaining weekly quota.

The effort floor on this repo is `medium`, not `low`: most edits
cascade across the locales and the automation layer (cache-bust
restamp, i18n drift, generators, CI), so `low` tends to produce
output that looks right but breaks a downstream check.

---

*This file is short on purpose. If you need to add a rule, add it
here; if you need to add an example, prefer linking a PR / commit /
issue so this file stays a reference rather than a tutorial.*
