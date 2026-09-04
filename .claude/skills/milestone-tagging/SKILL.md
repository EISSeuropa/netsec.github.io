---
name: milestone-tagging
description: "How NetSec's GitHub milestones are structured and maintained: where the set comes from, the two pre-versioning milestones to leave alone, due dates tracking the roadmap, and the pre-release milestone hygiene check. Use when creating or re-milestoning an issue or PR, when the roadmap shifts a release, or when checking milestone hygiene before a release."
---

# Milestone tagging

The always-loaded rule is CLAUDE.md §10: every open issue and every
pull request carries exactly one milestone, set at creation time, and
when none fits you stop and ask the maintainer. This skill carries the
rest, which only matters when you are actually working with the
milestone set.

## The milestone set

Milestones are created on GitHub from the version-tagged rows of
[`docs/roadmap-2026.md`](../../../docs/roadmap-2026.md)'s *At a glance*
timeline. One milestone per planned release, plus a single
`Backlog — Under watch` bucket for items waiting on external triggers
(COST-office decisions, post-conference activities, larger redesigns
with no fixed slot yet).

Two non-versioned milestones predate this convention
(`Directory Page and Workflow`, `Translations (FR+GE) in Beta`). Both
are closed. They are pre-versioning history and are intentionally not
on the public roadmap, since the roadmap-progress sync skips any title
that is not `vX.Y.Z`. Leave them as they are. Do not rename them to
versions: their work spanned several early releases, so no single
version maps.

Due dates come from the same timeline. When the roadmap shifts a
planned release, **bump the milestone's due date in the same commit
that updates the roadmap row**, since the two are projections of one
plan.

## When to set it

- **At issue creation.** Whenever CLAUDE.md §3 fires, set the milestone
  alongside the title and body: `gh issue create --milestone v1.7.0 ...`.
- **At PR creation.** The milestone is the release the PR will ship in:
  `gh pr create --milestone v1.15.0 ...`, or
  `gh pr edit <N> --milestone v1.15.0` if it was opened without one.
- **When an issue moves between releases.** Update the milestone in the
  same edit that records the slip ("deferred to v1.8.0, out of scope
  for v1.7.0 in this PR").
- **Never leave an open issue without one.** A milestone-less open
  issue is invisible to release planning, and the
  `Backlog — Under watch` bucket exists so there is no excuse.

## Pre-release check

This is also point seven of the `release-cross-check` skill. Before
running `scripts/release.sh`, confirm that every issue **closed by this
release** carries the matching milestone, and that any **still-open
issue tagged with this milestone** has either been ticked off in the
release notes or moved to the next milestone with a one-line reason in
the issue thread. A release should not ship with its own milestone
holding open work.

`scripts/release.sh` lists the currently-open issues tagged with the
milestone being cut, inside the y/n confirmation prompt. Skim it before
typing `y`. If the work for an issue actually shipped (the PR landed,
the bullet sits in `[Unreleased]`, the feature works on the live site)
but nobody wrote `Closes #N` in the PR description, that issue is still
open and needs explicit closure on release day:

```
gh issue close <N> --comment "Shipped in v<X.Y.Z>"
```

If the work has not shipped, the issue should already have been
re-milestoned in the PR that decided to defer it.
