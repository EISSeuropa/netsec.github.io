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
- **Parallel PRs that touch `site.css` (or anything `inject-seo.py`
  stamps a `?v=` hash into) must merge one at a time.** Each one
  regenerates the cache-bust hashes across every page, so two open at
  once collide on the `?v=` lines, and a careless merge can silently
  drop unrelated content baked into the regenerated pages (another
  PR's JSON-LD, a built section). Develop them in parallel if you
  like, but integrate sequentially: after each lands on `main`, merge
  `main` into the next branch, keep all the `site.css` and CHANGELOG
  additions, take `main`'s copy of the generated HTML, then re-run
  `scripts/inject-seo.py` (plus any page builder, e.g.
  `build-field-guide.py`) once to recompute every `?v=` against the
  combined tree. A bounded wait for a merge the next step genuinely
  depends on is fine.
- **Stack the PRs when the work is dependent and you were never
  going to auto-merge it.** Both conditions have to hold. The
  changes build on each other, the batch above being the canonical
  case, and the change needs the maintainer's eyes before it lands,
  so auto-merge was already off the table. Stacking and auto-merge
  are mutually exclusive: GitHub refuses `enablePullRequestAutoMerge`
  on a stacked PR, which is why the second condition is not a
  preference but the price of admission. Land the chain in the
  foreground with `gh stack merge --merge-method squash`, atomic
  across the whole stack and still bound by the `protect-main`
  ruleset. Stacking removes the `?v=` collision, because each PR's
  base is the one below it rather than `main`, but not the churn,
  since every level still restamps every page. When only one
  condition holds, open an ordinary PR and arm auto-merge as usual.
  Scripted use needs flags: `gh stack init <branches>` and
  `gh stack submit --auto`, which creates drafts unless you add
  `--open`. Trial findings in
  [#1497](https://github.com/EISSeuropa/netsec.github.io/issues/1497).
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

**No semicolons.** Use a full stop and a fresh sentence when both
halves stand alone, or a comma or a small rewrite when they do
not. Colons stay fine for "X: the reason." A semicolon reads as
careful machine prose to this maintainer, the same tell as an em
dash.

**No very short sentences.** Avoid two- or three-word fragments
standing on their own. Fold them into a fuller sentence so the
prose flows rather than clipping to a halt.

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
- The bios-sync workflow is structurally tuned to produce
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

Add to the release-cross-check skill's six-point cross-check: before running
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

## 16. Lessons learned

Hard-won checks that earned a place here after a near-miss. Each
entry is a rule, kept short on purpose.

### A green build is not proof a feature renders

CI checks consistency and structure (link integrity, i18n drift, SEO
asset stamps, CodeQL). None of them confirm that a feature actually
shows up on screen. A class can be referenced in new markup but never
defined in the stylesheet, or a stylesheet can be stale on the
visitor's device, and every check stays green while the feature
renders as unstyled plain text. This is exactly how the "Working
towards" block shipped looking like raw text.

Before calling a visual change done:

1. grep that every class the new markup references is actually
   defined in the stylesheet.
2. render it in a preview at both desktop and phone widths, in both
   light and dark themes. Headless Chrome follows the system
   preference (usually dark here), so a single render silently checks
   only one theme. The Early Access banner shipped unreadable in light
   mode because a global `p` colour rule resolved light under `.dark`
   but dark under the default theme, and the verification render was
   dark-only.
3. test the real device class the user reported the problem on, not
   only the one in front of you.

### Fix a bug, then grep for its siblings

A bug is rarely unique. The same mistake usually repeats wherever the
pattern was copied. After fixing one, search the codebase for the same
shape and fix the siblings in the same PR, rather than waiting for each
to be reported separately. This recurred with the home-page card
deep-links that scrolled to the wrong position and with padding
miscalculations that surfaced on more than one page.

### Trace a sitewide change through every drift gate

A change that touches every file (a cache-bust stamp, a shared header,
a global class rename) ripples into the CI drift checkers. Before
shipping, walk each gate the change could trip: i18n drift, calendar
drift, the SEO asset check, the link checker. The cache-bust `?v=`
query string is the canonical case. It changed every HTML file and
silently failed the i18n drift checker until that checker was taught
to strip `?v=` before hashing.

### Headless Chrome has verification blind spots

Headless Chrome is the verification workhorse here, but it does not
behave like a real browser in ways that have cost time more than once:

- `--screenshot` and `--dump-dom` do not reliably run a fragment scroll
  or a programmatic `scrollIntoView`, and do not fire
  `requestAnimationFrame`. Anything depending on those will not appear.
- Output from a backgrounded Chrome command often does not flush to
  stdout. Read the dumped DOM or screenshot file directly instead.
- Computed-style reads and synchronous DOM queries are reliable.
- `--force-prefers-reduced-motion=reduce` does emulate reduced motion
  correctly, so the reduced-motion path can be tested headless.

### Stage named paths, and clear scratch files first

Verification leaves throwaway probe files (one-off HTML pages, swatch
captures, DOM dumps). `git add -A` and `git add -u` sweep them into the
commit. Delete the scratch files first, then stage explicit named
paths. This is the §2 explicit-add rule seen from the other side: the
risk is not only staging the wrong source file, it is committing
verification litter that should never have been tracked. Offenders that
slipped through before: jprobe.html, rmm.html, swatch.html.

### Workflow agents write where you point them, not where they live

An agent spawned with `isolation: worktree` runs in its own fresh
worktree, but it will still write into the main checkout if the prompt
hands it an absolute repo path. Give workflow agents only paths relative
to their working directory, tell them their cwd IS the worktree, and
forbid absolute paths, `cd`, and any git command. Otherwise parallel
agents leak files into the shared checkout (and can collide on its git
state) while you are working in it. This surfaced when a test-writing
fan-out wrote `scripts/test-*.py` into the main checkout because the
prompt named the repo by its absolute path. Pair it with the
scratch-file rule above: when a run is killed, prune its leftover
worktrees with `git worktree remove -f -f` before continuing.

### Bind JS to `data-*` hooks, never to a styling class

When JavaScript needs to find an element (a `querySelector`, an event
listener, a filter target), key it off a dedicated `data-*` attribute,
not off a class that also carries styling. A styling class gets reused
the moment another element wants the same look, and that second element
is then silently swept into the first one's handler. Reach for the
attribute selector even when there is only one match today, because the
collision arrives with the next feature that clones the markup.

The STSM-hosting filter chip reused `class="members-mentorship-chip"` to
borrow the pill styling, so the mentorship click handler
(`querySelectorAll('.members-mentorship-chip')`) also fired on it and
pushed `undefined` into the mentorship set, which then filtered out every
member. The deep link worked because it never runs the click handlers, so
the bug read as data-related when it was a selector collision. Fixed in
[#862](https://github.com/EISSeuropa/netsec.github.io/pull/862) by scoping
the handler to `.members-mentorship-chip[data-mentorship]`.

The `Lint CSS for class-name collisions` CI check guards the CSS side of
this (two rules claiming one name). It does not see a JS selector reaching
an element that only wanted the class for looks. This convention is that
blind spot's counterpart.

*This file is short on purpose. If you need to add a rule, add it
here; if you need to add an example, prefer linking a PR / commit /
issue so this file stays a reference rather than a tutorial.*

---

## Lazy-loaded procedures

Four sections moved out of this file so they load when needed instead of
costing context every session, the same pattern §15 uses for
`docs/claude-usage.md`. Section numbers below are unchanged so existing §N
cross-references keep resolving.

- `release-cross-check` skill — the six-point cross-check before a minor or
  major release (was §5).
- `cross-repo-project` skill — the NetSec + EISS GitHub Project (was §13).
- `whats-new-banner` skill — when to run the announcement banner (was §14).
- [`.github/CLAUDE.md`](.github/CLAUDE.md) — SHA-pinning and release-workflow
  conventions, loaded when working under `.github/` (was §12).
