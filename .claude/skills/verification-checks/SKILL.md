---
name: "verification-checks"
description: "What CI does not prove on NetSec, and how to verify a change instead: the render checks before calling a visual change done, scripts/measure.mjs, headless Chrome's blind spots, and why a cancelled workflow run hides an outage a failed-run list never shows. Use before calling a visual or rendering change done, when verifying that a feature actually shows up on screen, and when auditing CI health or confirming a deploy really published."
---

# 16. Lessons learned: the verification checks

Moved out of CLAUDE.md §16 so they load when a change needs
verifying rather than costing context every session. The reflexes
that have to fire unprompted (grep for a bug's siblings, the locale
triplet, the drift gates, staging named paths, workflow agents,
`data-*` hooks) stay resident in §16.

### A cancelled run is not a passing run

Auditing CI by listing failures misses the worst outages, because a run
blocked by a concurrency group is recorded as `cancelled` rather than
`failed`. A Pages deploy job sat in `queued` for six days in August 2026
without ever getting a runner, held the `pages` slot, and every deploy
behind it was cancelled while pending. The failed-run list stayed empty
and the live site quietly fell four commits behind `main`.

When checking CI health, read the `cancelled` runs too, and confirm the
deploy actually published rather than trusting the workflow list:

```bash
gh api "repos/EISSeuropa/netsec.github.io/deployments?environment=github-pages&per_page=1" --jq '.[].sha'
```

A run of `cancelled` results on one scheduled workflow is the signature
to look for, since a healthy schedule does not cancel itself.

### A green build is not proof a feature renders

CI checks consistency and structure (link integrity, i18n drift, SEO
asset stamps, CodeQL). None of them confirm that a feature actually
shows up on screen. A class can be referenced in new markup but never
defined in the stylesheet, or a stylesheet can be stale on the
visitor's device, and every check stays green while the feature
renders as unstyled plain text. This is exactly how the "Working
towards" block shipped looking like raw text.

`scripts/measure.mjs` does the measuring, so this is a command rather
than an improvisation each time (#1714):

```bash
node scripts/measure.mjs fold network-map.html network-map.fr.html
node scripts/measure.mjs targets working-groups.html
node scripts/measure.mjs bytes essc-2026.html
```

It serves the tree itself (a server started earlier 404s on a file
written since), and `targets` emulates a coarse pointer through the
viewport, because `emulateMediaFeatures` rejects `pointer` and every
`@media (pointer:coarse)` rule otherwise goes untested.

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
