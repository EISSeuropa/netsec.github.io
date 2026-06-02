# Cross-repo workflow: NetSec + EISS sites

**Audience: the maintainer.** Two repositories under the EISSeuropa
account share infrastructure and features that routinely port between
them: `netsec.github.io` (this site) and `EISSeuropa.github.io` (the
EISS site). This note records the lightweight conventions that keep the
two in step without rework. It complements CLAUDE.md §13, which covers
the shared GitHub Project board. The board tracks *what* crosses over.
This doc covers *how* it crosses over.

## Shared patterns

These ship on one site and tend to port to the other. When you change
one, check whether the parallel needs the same change.

| Pattern | Where | Portable |
| --- | --- | --- |
| Indico sync pipeline | `scripts/sync-indico.py` | Yes, the `indico.json` schema is identical |
| Programme renderer | `essc-2026.html` runtime JS | Yes, the renderer is generic over the `indico.json` shape |
| Glass and popover styling | `assets/css/site.css` (`.glass`, `.popover-*`) | Yes, the class vocabulary is shared |
| Name normalisation | `name_key()` in `scripts/sync-indico.py` (Python) and the renderer (JS) | Yes, the function is language-agnostic |
| Render-from-JSON contract | `data/*.json` plus the site JS | Yes, the pattern ports even when the data differs |
| Cache-bust + i18n pipeline | `scripts/inject-seo.py`, `scripts/check-i18n-drift.py` | Yes, mechanism is identical |

Not portable: anything visually NetSec-specific (the 404 illustration,
brand assets, the deliverables Gantt).

## The "ported from" convention

When a feature or fix lands on one site and the other needs the same:

1. File an enhancement issue on the target repo.
2. Link the source PR in the body: *"Ported from EISSeuropa/&lt;repo&gt;#N"*.
3. Add it to the shared Project board (CLAUDE.md §13) so the pairing is
   visible at the next release cycle.

This keeps the audit trail self-referencing on both sides, the same way
deferred work is tracked within a single repo (CLAUDE.md §3).

## Shared scripts: duplicate, do not centralise (for now)

The sync and build scripts are duplicated across the two repos rather
than extracted into a shared package. At the current scale (a handful
of stable scripts) a periodic manual sync of bug fixes is cheaper than
the overhead of a shared dependency and its release coordination.

Revisit this stance if either of these happens:
- A critical bug needs simultaneous patching on both repos.
- A new feature must ship on both before the same release cycle.

At that point, weigh a small shared repo (a git submodule or a published
package) against the coordination cost, and record the decision in the
Wiki decisions log.

## Indico sync alignment

Both sites read from the same Indico instance
(`indico.eiss-europa.com`). Keep the two sync workflows from fighting
each other:

- Stagger the scheduled runs so they do not hit Indico at the same
  minute.
- Use a single read-token convention documented in each repo's
  `docs/admin-guide.md`, so a token rotation is a known two-step change.
- Indico itself is a separate hosted application, not part of either
  static repo. Neither repo should try to "fix" Indico from its own
  codebase (CLAUDE.md notes this boundary for the EISS repo too).

## What this doc is not

It is not a migration plan to merge the two repos, and it is not a
mandate to share code today. It is the convention that makes the
existing two-repo split cheap to maintain. The Project board (§13) is
the live view. This doc is the rulebook behind it.
