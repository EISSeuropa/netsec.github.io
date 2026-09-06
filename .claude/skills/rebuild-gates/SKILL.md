---
name: "rebuild-gates"
description: "Which generated file a change has made stale, and the builder that refreshes it, derived from the workflows rather than from a list that drifts. Use after editing anything under data/, a locale HTML page, or a builder script, before staging a commit, and when a drift or freshness gate has failed on a PR."
---

# Which builders does this change invalidate?

Thirteen builders write files that are committed, and a drift gate fails
the PR when one is stale. Run the deriver rather than recalling the map:

```bash
python3 scripts/what-to-rebuild.py
```

It diffs the working tree against `origin/main` by default. Pass paths to
test a hypothetical change (`python3 scripts/what-to-rebuild.py
data/bios.json`), or `--base HEAD` for uncommitted work only.

The output has three parts. **Stale now** lists builders to run and
commit, read off the `--check` commands in each gate. **Must still
build** lists gates that only have to not crash, whose output is
gitignored. **Also runs on every PR** names the filter-free gates, which
declare nothing about which paths affect them and so imply nothing about
your change.

Why derived: the map from an edited file to its builder is already
declared in the workflows, in the `paths:` a gate triggers on and the
`--check` it runs. A hand-kept copy drifts away from the gates it
describes. `scripts/test-what-to-rebuild.py` pins the derivation against
the real workflow files, so a gate changing shape fails a test rather
than silently producing a wrong answer.

Deploy-time builders never appear, because `pages-deploy.yml` has no
`pull_request` trigger. Profile pages, the OG cards and the `?v=` stamp
are written at deploy and must not be committed by hand.

## What it cannot tell you

Three traps sit outside the path-to-builder mapping.

- A directory member whose photo is only a `.jpg` renders a broken
  headshot, because the `<picture>` source does not fall back. The
  `.webp` comes from a bios-sync run, not from a local builder.
- Flags for a new country are fetched during the bios-sync workflow
  (`build-og-cards.py --ensure-flags`, #1323). Do not hand-add one
  unless CI cannot reach the upstream repository.
- The Pagefind index is gitignored, so a browser test that drives search
  has to run `scripts/build-search.sh` first. Skip it and the test
  passes locally, then times out in CI.
