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

Four traps sit outside the path-to-builder mapping.

- A directory member whose photo is only a `.jpg` renders a broken
  headshot, because the `<picture>` source does not fall back. The
  `.webp` comes from a bios-sync run, not from a local builder.
- Flags for a new country are fetched during the bios-sync workflow
  (`build-og-cards.py --ensure-flags`, #1323). Do not hand-add one
  unless CI cannot reach the upstream repository.
- The Pagefind index is gitignored, so a browser test that drives search
  has to run `scripts/build-search.sh` first. Skip it and the test
  passes locally, then times out in CI.
- A gate that filters on `data/**` claims every builder behind it, so
  the answer is a superset when the question is which builders a *sync
  workflow* has to rerun. Confirm against what the builder actually
  reads: `build-bio-search-stubs.py`, `build-directory-index.py` and
  `build-sitemap.py` open only `data/bios.json`, and suggesting them for
  an `indico.json` change is the filter talking. This matters because a
  sync script's write set is wider than one file (#1804).

## What each auto-PR workflow commits

Eight workflows open their own PRs, and each one has to rerun every
gated builder that reads what it writes. Four times it did not, and the
PR opened already red: the bio search stubs (#1428), the network map
(#764), then the directory index and the sitemap on the same workflow
inside a day (#1803, #1804).

| workflow | commits |
| --- | --- |
| `sync-bios.yml` | `data/bios.json`, `assets/images/people/` |
| `sync-cost.yml` | `data/bios.json`, `data/wg.json`, `data/mc-members.json`, `data/cost-wg-state.json` |
| `sync-indico.yml` | `data/indico.json`, `data/events.json` |
| `news-publish.yml` | `data/news.json` |
| `spotlight-rotate.yml` | `data/spotlight.json`, `data/social-posted.json` |
| `social-bluesky.yml` | `data/social-posted.json` |
| `roadmap-refresh.yml` | `data/roadmap-progress.json`, `docs/roadmap-2026.md` |
| `linkedin-version-check.yml` | `data/linkedin-api-version.json` |

`scripts/test-auto-pr-builders.py` holds the same table as `WRITES` and
fails when a workflow runs fewer builders than its writes invalidate, so
reach for the table when you are changing what a workflow commits rather
than to answer whether today's tree is stale. A test pins this copy
against that one, and another fails when a new auto-PR workflow is
missing from both.
