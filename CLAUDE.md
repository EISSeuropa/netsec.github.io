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

### Issue template (informal — there are no `.github/ISSUE_TEMPLATE/` files)

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

## 5. Release-time five-point cross-check (minor / major only)

Every **minor (`X.Y.0` where `Y > prev`) or major (`X.0.0`)
release** should trigger a deliberate check across five surfaces
before `scripts/release.sh` runs. Skip the cross-check on **patch
releases** (`X.Y.Z` where `Z > 0`) — they're scoped to small
fixes and the overhead isn't justified. The release script's
*self-policing tier* mirrors this: patches ship the index only.

For each surface, the question is the same: *"Did anything in
this release change what this surface documents?"* If yes, edit
in the same release. If yes but too big to fit, open a tracking
issue (rule §3) and reference it from the surface itself.

### 1. Roadmap (`/roadmap.html` + FR + DE + `docs/roadmap-2026.md`)

- Move the just-shipped release from *In progress* → *Shipped*
  in both the public timeline and the internal doc.
- Is the next planned release on the timeline still accurate?
- Anything in *Under watch* (the deferred-items section at the
  foot of the page) ready to promote to a dated entry?
- Bump *Last reviewed* on `docs/roadmap-2026.md` if you touched it.

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
  version stamp and changelog appendix. Two-tier cadence:
  - **Cover bump** — fast, always. Bump the stamp + add a
    short appendix entry. Acceptable to defer section-level
    catch-up via an explicit "gap" entry (pattern: pack
    v1.7.0 in PR #116; tracking
    [#122](https://github.com/EISSeuropa/netsec.github.io/issues/122)).
  - **Section-level catch-up** — substantive; refresh
    Section 02 site graph + page inventory, refresh
    screenshots via `./docs/pdf/build.sh --shots`. Batch
    when site shape stabilises (typically every 2-3 minor
    releases, not every release).

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

### 6. Milestone hygiene (gate, not a surface)

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

Add to the rule §5 five-point cross-check: before running
`scripts/release.sh`, confirm that every issue **closed by this
release** carries the matching milestone, and that any **still-
open issue tagged with this milestone** has either been ticked off
in the release notes or moved to the next milestone with a one-
line reason in the issue thread. The release should not ship with
its own milestone holding open work.

---

*This file is short on purpose. If you need to add a rule, add it
here; if you need to add an example, prefer linking a PR / commit /
issue so this file stays a reference rather than a tutorial.*
