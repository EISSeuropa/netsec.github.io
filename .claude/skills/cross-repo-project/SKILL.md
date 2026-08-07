---
name: cross-repo-project
description: The private GitHub Project spanning open enhancement issues across the NetSec and EISS repos: its scope, its boundary against milestones, the single Effort field, the manual add step, and the retirement threshold. Use when asked about the cross-repo Project board.
---

# 13. Cross-repo Project: NetSec + EISS websites

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
