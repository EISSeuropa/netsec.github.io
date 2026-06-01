# Using Claude Code on this repo: model + effort playbook

**Audience: the maintainer.** This note is a decision aid for choosing
the right Claude model and reasoning-effort level on a given task, and
for staying inside the Pro plan's weekly quota. It is calibrated to how
this repository actually works, not to a generic static site.

The short version lives in [`CLAUDE.md`](../CLAUDE.md) §15. The standing
defaults are set in `.claude/settings.local.json` (gitignored). This
doc is the longer reasoning behind both, kept out of `CLAUDE.md` so it
does not cost context on every session.

## The one correction that changes the calculus

Off-the-shelf advice treats this as a plain static site: edit a file,
commit, push, done, so use the cheap model at low effort for almost
everything. That under-describes what we have.

The site is a static *output*, but it sits on a real automation layer:

- A cache-bust hash (`scripts/inject-seo.py`) means editing one
  stylesheet restamps every HTML file in the repo.
- Hand-translated FR and DE variants with a drift checker
  (`scripts/check-i18n-drift.py`) mean an English copy change pulls
  manual translation work and a fresh-mark behind it.
- Generators and sync scripts (`promote-roadmap.py`, `sync-cost.py`,
  `sync-bios.py`, `build-calendar.py`, and friends) turn data into
  pages and calendars.
- CI gates (i18n drift, calendar drift, the SEO asset check, the link
  checker, CodeQL) hold a merge if any of the above is inconsistent.
- Changes ship through a branch, a PR, and auto-merge, not a direct
  push to the deploy branch. `main` is protected.

So a change that looks like a one-line edit often fans out across the
three locales, a script, the cache-bust stamp, and CI. The practical
consequence is the effort floor below: **medium, not low, for most
real edits.** Low produces output that looks right but quietly breaks a
downstream check.

## What each lever can and cannot do

There are three places this strategy can live, and they do different
jobs. Knowing which is which is the whole point.

| Lever | Where | What it does | What it cannot do |
| --- | --- | --- | --- |
| Persistent defaults | `.claude/settings.local.json` (`model`, `effortLevel`) | Sets the model and effort every session without anyone remembering. The only genuine set-once control. | Cannot persist `max` or `ultracode` (both session-only). |
| Behaviour nudges | `CLAUDE.md` §15 (auto-loaded) | Makes Claude plan first on multi-surface work and flag when the effort dial looks wrong. | Cannot set the model or move the slider. It can only recommend, because the dial is the maintainer's hand, not Claude's. |
| This reference | `docs/claude-usage.md` (read on demand) | Holds the full matrix and the reasoning, at zero per-session context cost, and survives a context reset. | Does nothing automatically. It informs a human decision. |

The residue that no file removes: the live call on whether *this* task,
*right now*, is worth Opus or high effort given the remaining weekly
quota. Only the maintainer can see the quota, and the model cannot
change its own effort mid-turn, so that judgement stays manual by
design.

## Per-task routing matrix (calibrated to this repo)

| Task | Model | Effort | Why, here |
| --- | --- | --- | --- |
| Single string, metadata line, one self-contained copy fix | `sonnet` | low | Genuinely contained, no cascade. |
| New page section, HTML, CSS on a single surface | `sonnet` | medium | Markup rarely needs full reasoning, but watch for the cache-bust and locale cascade. |
| Any change touching the three locales or a shared component | `opusplan` to plan, `sonnet` to execute | plan high, exec medium | Fan-out across FR and DE plus drift checks rewards a plan before the first edit. |
| Script, CI, cache-bust, or i18n-tooling change | `opus` | high | Reasoning-heavy and easy to break the pipeline silently. |
| Cross-file or behavioural debugging | `opus` | high, then max only if high stalls | Root-causing across files is where Opus earns its premium. |
| Cutting a release (`release.sh`, the six-point cross-check) | `opusplan` | high | Many surfaces at once and the publish step is hard to undo. |
| Codebase exploration, "how does X work" | `sonnet` plus subagents | low to medium | Keep the main context clean, let a subagent absorb the search. |

Rule of thumb: default to `opusplan` at `medium`, drop to `low` only
when the task is provably contained, and step up to `opus` plus `high`
the moment a change is multi-surface or a diagnosis.

## Quota hygiene

- Plan first on anything spanning more than one or two files. The plan
  is read-only, relatively cheap, and avoids expensive rework across
  locales and CI.
- `/clear` between unrelated tasks. One objective per session. A bloated
  context re-reads everything and wastes tokens.
- Watch Settings then Usage. Spend the weekly Opus allowance late in the
  week, once the remaining headroom is visible.
- Keep context lean. `/compact` or start fresh when it climbs.
- Avoid `max` effort and `ultracode` except for a rare, deliberate,
  high-value task. They have no token ceiling.

## A caution on the numbers

Plan limits, prices, and weekly caps changed repeatedly through 2026 and
will keep moving. Treat any specific figure in third-party write-ups as
a rough planning band, not a contract, and trust Settings then Usage in
the app over anything written down here. The strategy above (plan in
Opus, execute in Sonnet, hold a medium floor, escalate deliberately)
holds regardless of the exact ceilings.
