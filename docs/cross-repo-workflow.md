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

## Cross-site member ↔ author linking (the two indexes)

The two sites link people to each other through a pair of mirror-image
JSON contracts, one published by each side. The join key on both is the
same canonical name key (`name_key()` in `scripts/sync-bios.py` on the
NetSec side, ported verbatim into the EISS Anthology build): lowercased,
diacritics folded, salutations and nobiliary particles and middle initials
dropped, reduced to first-and-last token. Publishing a slim index rather
than letting each side read the other's internal data keeps the consumer
decoupled from the producer's bio schema and URL scheme.

| Direction | Contract | Produced by | Consumed by |
| --- | --- | --- | --- |
| Anthology author → NetSec profile | `directory-index.json` (NetSec site root) | `scripts/build-directory-index.py` | the EISS Anthology |
| NetSec profile → Anthology author | `authors-index.json` (EISS `data/`) | EISS Anthology build | the NetSec profile page |

Both indexes carry, per person: the display name, the `name_key`, an
`aliases` array, and the absolute `url` to that person's page on the
producing site. A consumer matches its own people against the index by
`name_key` (falling back to `aliases`) and links to `url`.
`directory-index.json` additionally carries optional display fields
(`role`, `affiliation`, `photo`, all null when unset) so a consumer can
render an informative chip (a headshot plus who the person is) rather than
a bare link.

**`directory-index.json`** is generated from `data/bios.json`, regenerated
by the weekly bios-sync, and drift-gated in CI (`build-directory-index.py
--check` in `data-shape-check.yml`). It reuses `sync-bios.py`'s `name_key()`
so the published key can never drift from the directory's own matcher.

**`authors-index.json`** is consumed at runtime by the profile page, not
baked at build time. A small inline script on `/people/<slug>` fetches it,
matches the member, and injects the "In the EISS Anthology" link. Runtime
consumption is the same posture the ESSC programme already uses for
`anthology-index.json`, and it keeps the static, drift-gated profile pages a
pure function of local data. See
[`profile-pages.md`](./profile-pages.md) for the page side.

### The prize-winner mirror

The European Security Studies Prize is a third, one-directional link, and a
deliberate exception to the contract pattern above. EISS holds the
authoritative roll in its internal `paperPrizes.json` keyed by paper title
and does **not** publish it as a consumable artifact. So NetSec keeps a small
curated `data/prize-winners.json`, keyed by directory member id, listing only
the winners who also appear in the Directory, and renders the gold prize pill
on their profile page from it (`build-profile-pages.py`). If EISS ever
exposes a public prizes JSON, the builder could consume that and the local
mirror could be retired. Until then, adding a laureate is a one-row edit (see
[`profile-pages.md`](./profile-pages.md)).

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
