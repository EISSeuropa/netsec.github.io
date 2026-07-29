# The NetSec Atlas

A live map of the network behind the Action, at `/atlas.html` (plus
`/atlas.fr.html` and `/atlas.de.html`). It draws every person in the
Action as a node and links them through the structures they share:
the Working Groups they sit in, the research themes they work on, the
conference panels they shared, and the mentorship they offer or seek.
People sitting between two hubs are the bridges of the network. Issue
#764.

The whole map is **derived from the same data that already drives the
[Working Groups page](../working-groups.html) and the
[Directory](../people.html)**, so it never carries its own copy of who
is who. It is a reading of the existing data, not a new source of it.

## Status: a prototype, deliberately unlisted

The page carries a "Prototype" pill and the title says so. It is **not
in the top nav, not in the footer, and not in `sitemap.xml`**, so it is
reachable only by its URL. That is on purpose while it proves itself.
When it graduates it needs three things it does not have yet: a nav or
discovery-grid entry, a `sitemap.xml` row plus a visual-sitemap entry
(CLAUDE.md §5.2), and a decision on whether the "prototype" framing
comes off. Until then, treat it as a standalone that most visitors will
never land on.

All three locales exist, with the hand-translation beta ribbon
(*Traduction manuelle* / *Manuell übersetzt*) and full hreflang
alternates (added in #1419, which also wired the language switcher so it
lands on the right locale rather than the home page).

## Two lenses and two overlays

The renderer shows one deduped set of people under a choice of lens,
with overlays layered on top:

- **Working Groups lens.** The four WG hubs, with each person linked to
  the WGs they belong to.
- **Research themes lens.** One hub per research theme drawn from the
  bios, the map of what the Action works on.
- **ESSC co-panels overlay.** Person-to-person arcs for a shared
  conference panel at ESSC 2026, the arc weighted by how many panels two
  people shared. Works on either lens.
- **Mentorship overlay.** Rings on the dots for who is offering
  mentorship and who is seeking it.

A member with a headshot renders as a small circular photo, so the map
carries faces. Hovering a node names the person, and clicking through
opens their directory profile where one exists. Co-authorship joins the
map as its own edge type once the Action's publications land (see
*Growing with the data* below).

## The data pipeline

```
data/wg.json ─────────────┐
data/bios.json ───────────┼──►  scripts/build-atlas.py  ──►  data/atlas.json  ──►  assets/js/atlas-poc.js
data/essc-2026-programme.json ─┤        (derivation)              (committed)          (renders /atlas.html)
data/publications.json ───┘
```

`scripts/build-atlas.py` builds `data/atlas.json`, a node/edge graph.
The renderer, `assets/js/atlas-poc.js`, is a **pure consumer**: it reads
the committed JSON and never fetches `bios.json` or reaches the network.

**Nodes** are the four WG hubs, one hub per research theme in use, and
one node per unique person. The person universe is the WG rosters
*unioned* with the directory bios, deduped by `name_key` (the same key
the directory and cross-site links match on), so a roster-only member
and a bio-carrying member are one node. A person node carries slug,
photo, mentorship flags, and country when a bio exists, which is what
lets the renderer draw headshots, mentorship rings, and profile links
without any further data.

**Edges** are bipartite person-to-hub memberships (person-to-WG from the
rosters, person-to-theme from the bio themes) plus person-to-person
ESSC co-panel ties matched by `name_key` against the frozen conference
programme. The hub form is chosen over pairwise co-membership on
purpose: pairwise would be a roughly nine-thousand-edge hairball, while
the bipartite hubs carry the same information legibly.

**Determinism.** There is no layout step in the build (the renderer lays
out client-side), so there is no randomness. Every list is sorted by a
stable key, so a given `wg.json` always produces byte-identical
`atlas.json`. That is what lets the `--check` gate work.

### How it stays current

`build-atlas.py` runs inside **both** sync workflows, since a WG move
comes from the cost.eu sync and a bios change comes from the bios sync,
and either shifts the graph. It also carries a `--check` mode that
regenerates in memory and diffs against the committed file. `data-shape-check.yml`
runs `--check` on any PR that touches the inputs, so a stale
`atlas.json` fails CI the same way a stale sitemap or directory index
does. Nothing about the Atlas is edited by hand.

## The renderer

`atlas-poc.js` is vanilla JavaScript with no dependencies. It paints to
a `<canvas>` with a hand-rolled force layout on a deterministic seed, is
DPR-aware for sharp rendering on high-density screens, and reads its
colours from the CSS variables so it re-themes on a light/dark flip.
Reduced-motion visitors get the settled layout without the animation.

Every string it injects (the controls, the stats, the hover card) goes
through the shared `netsecT` catalogue in `site.js`, so the FR and DE
pages render in their own language, with singular and plural kept as
separate catalogue keys rather than an English stem plus an "s".

Headshots come from the webp variant the bios sync generates, not the
original JPEG. The faces render as small circles, so the originals were
spending bytes the canvas cannot show: 5.24 MB across the 62 members
carrying a photo, against 1.45 MB of webp. `build-atlas.py` picks the
webp when the file exists and falls back to the original otherwise,
which is the state a member sits in between joining and the next sync.

## The performance budget

`atlas.html` is in the Lighthouse budget set (`lighthouserc.json`,
`.github/workflows/lighthouse.yml`). It was unmeasured until July 2026
even though that workflow already ran on every change to the files that
build it, which is how the page came to ship 5.6 MB of headshots
unnoticed. The first measured run caught exactly that.

It shares the performance and accessibility floors with every other
audited page, which it passes without relaxation. The one exemption is
`categories:seo`: the page scores 0.58 there because of its deliberate
`noindex` (see *Status* above), so asserting on it would warn on every
run forever. Restore that assertion when the prototype graduates.

The image budget is **still warning** at 1.65 MB against 500 KB. The
canvas loads every headshot eagerly on open, so trimming it further
means loading faces on demand or generating smaller derivatives rather
than raising the budget.

## Accessibility

The canvas is a visual convenience, not the only way to the
information. Its `aria-label` says what the map shows and points to the
list-based equivalents: WG membership lives on the Working Groups page
and everything person-level lives on the Directory, both fully
navigable without the canvas. The legend spells out what every colour
and ring means in text.

## Growing with the data

Two things are wired but start empty, and fill in as the Action
produces the data:

- **Co-authorship edges** derive from `data/publications.json` the same
  way co-panel edges derive from the programme. The file is empty until
  D6 ships its first output, so the layer starts at zero edges and grows
  on its own.
- **Server-side layout coordinates** are a deliberate follow-up. The
  renderer lays out client-side for now, which is fine at this size.

## Files

| Path | Role |
| --- | --- |
| `atlas.html`, `atlas.fr.html`, `atlas.de.html` | The prototype page in three locales |
| `assets/js/atlas-poc.js` | The canvas renderer (pure consumer of `atlas.json`) |
| `assets/css/atlas.css` | Atlas-only styles |
| `scripts/build-atlas.py` | Derives `data/atlas.json` (with a `--check` drift gate) |
| `scripts/test-build-atlas.py` | Tests for the derivation |
| `data/atlas.json` | The committed node/edge graph (generated, never hand-edited) |
