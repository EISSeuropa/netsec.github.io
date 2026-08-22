# The NetSec Network Map

A live map of the network behind the Action, at `/network-map.html` (plus
`/network-map.fr.html` and `/network-map.de.html`). It draws every person in the
Action as a node and links them through the structures they share:
the Working Groups they sit in, the research themes they work on, the
conference panels they shared, and the mentorship they offer or seek.
People sitting between two hubs are the bridges of the network. Issue
#764.

**Formerly the NetSec Atlas.** EISS publishes an Atlas of its own at
`/anthology-atlas.html`, a force-directed map of the Anthology corpus,
and the EISS brand work goes further by making the constellation graph
the shared identity of the Anthology and its Atlas
(EISSeuropa/EISSeuropa.github.io#1253). Two force-directed maps across
two sites of the same initiative cannot both be the Atlas, so each is
now named for its subject: the EISS Atlas maps published works, and
this one maps people. The rename landed while the page was still an
unlisted prototype, which is why it cost no redirects.

The whole map is **derived from the same data that already drives the
[Working Groups page](../working-groups.html) and the
[Directory](../people.html)**, so it never carries its own copy of who
is who. It is a reading of the existing data, not a new source of it.

## Status: a signposted prototype

The page is reachable and indexable. It carries a *Prototype* pill, is
linked from the Working Groups page and the Directory, sits in
`sitemap.xml` and the visual sitemap in all three locales, and its
`<main>` carries `data-pagefind-body` so on-site search finds it.

There is no primary-nav entry. The header is at the capacity rule in
`docs/homepage-ia-phase2.md`, so the map is reached from the two pages
whose data it draws, using the shared signpost callout that
`/about.html` already uses for the roadmap.

The *Prototype* pill stays until the co-authorship layer has edges,
which gives it a defined removal trigger rather than a judgement call.

One thing to confirm after the first Lighthouse run on the indexable
page: `lighthouserc.json` still drops the `categories:seo` assertion for
this URL, an exemption that existed only because of the `noindex`. Now
that the page is managed by `inject-seo.py` and indexable, that
assertion should be restorable.

## Two lenses and two overlays

The renderer shows one deduped set of people under a choice of lens,
with overlays layered on top:

- **Working Groups lens.** The four WG hubs, with each person linked to
  the WGs they belong to.
- **Research themes lens.** One hub per research theme drawn from the
  bios, the map of what the Action works on.
- **ESSC co-panels overlay.** Person-to-person arcs for a shared
  conference panel, the arc weighted by how many panels two people
  shared in that edition. Works on either lens. Each arc carries the
  edition it came from, so a pair who sat together at two conferences
  gets one arc per edition rather than a single merged tie.

  When the map holds more than one edition, an **Edition** row appears
  between the overlays and the hub chips, offering *All editions* plus
  one chip per conference. It is built by the renderer rather than sitting
  in the three locale pages, and only when there is a choice to make: a
  filter offering the single conference on the map is furniture. This
  mirrors the co-authorship chip, which waits for the first publication.
  Filtering recomputes each person's panel peers, so the hover card's
  "with {n} members" counts who is on screen rather than who ever shared
  a panel.
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
data/bios.json ───────────┼──►  scripts/build-network-map.py  ──►  data/network-map.json  ──►  assets/js/network-map.js
data/indico.json ─────────┼──►    (derivation)              (committed)          (renders /network-map.html)
data/essc-<year>-programme.json ┤
data/publications.json ───┘
```

### Which conference files are read

`load_programmes()` merges every programme on disk rather than naming one
file. `data/indico.json` is the live sync and holds whichever edition
Indico is currently serving. Each `data/essc-<year>-programme.json` is a
snapshot frozen at conference close so the past-conference page stays
stable against later syncs, and where both carry the same edition the
frozen copy wins, being the record of what actually happened.

Reading the whole set is what makes a new edition appear on the map by
itself. Before #1584 the script named `data/essc-2026-programme.json`
alone, which would have left ESSC 2027 invisible with no gate going red,
since `--check` can only detect staleness in inputs the script already
reads. `sync-indico.yml` now regenerates the graph in the same auto-PR
that refreshes `indico.json`.

`scripts/build-network-map.py` builds `data/network-map.json`, a node/edge graph.
The renderer, `assets/js/network-map.js`, is a **pure consumer**: it reads
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
ESSC co-panel ties matched by `name_key` against the conference
programmes. The hub form is chosen over pairwise co-membership on
purpose: pairwise would be a roughly nine-thousand-edge hairball, while
the bipartite hubs carry the same information legibly.

**Determinism.** There is no layout step in the build (the renderer lays
out client-side), so there is no randomness. Every list is sorted by a
stable key, so a given `wg.json` always produces byte-identical
`network-map.json`. That is what lets the `--check` gate work.

### How it stays current

`build-network-map.py` runs inside **both** sync workflows, since a WG move
comes from the cost.eu sync and a bios change comes from the bios sync,
and either shifts the graph. It also carries a `--check` mode that
regenerates in memory and diffs against the committed file. `data-shape-check.yml`
runs `--check` on any PR that touches the inputs, so a stale
`network-map.json` fails CI the same way a stale sitemap or directory index
does. Nothing about the Network Map is edited by hand.

## The renderer

`network-map.js` is vanilla JavaScript with no dependencies. It paints to
a `<canvas>` with a hand-rolled force layout on a deterministic seed, is
DPR-aware for sharp rendering on high-density screens, and reads its
colours from the CSS variables so it re-themes on a light/dark flip.
Reduced-motion visitors get the settled layout without the animation.

Every string it injects (the controls, the stats, the hover card) goes
through the shared `netsecT` catalogue in `site.js`, so the FR and DE
pages render in their own language, with singular and plural kept as
separate catalogue keys rather than an English stem plus an "s".

Headshots come from a map-sized derivative, not from the directory's
headshot. A face draws as a circle of about 16 CSS px on the canvas and
at 44 px in the hover card, so almost every byte of a 600 px portrait is
detail the page cannot show. `ensure_map_avatars()` in `sync-bios.py`
writes a 128 px webp per member into `assets/images/people/map/`, and
`build-network-map.py` prefers it. Across the current roster that is
178 KB of faces, against 1.67 MB for the directory webp variants and
5.24 MB for the original JPEGs.

The preference falls through rather than failing: map avatar, then the
sibling webp, then the original. A member who joins between syncs is
served the largest file that exists rather than none, and the canvas
draws no face at all if a path 404s, so no rung of the fallback can
break the layout.

## The performance budget

`network-map.html` is in the Lighthouse budget set (`lighthouserc.json`,
`.github/workflows/lighthouse.yml`). It was unmeasured until July 2026
even though that workflow already ran on every change to the files that
build it, which is how the page came to ship 5.6 MB of headshots
unnoticed. The first measured run caught exactly that.

It shares the performance and accessibility floors with every other
audited page, which it passes without relaxation. The one exemption is
`categories:seo`: the page scores 0.58 there because of its deliberate
`noindex` (see *Status* above), so asserting on it would warn on every
run forever. Restore that assertion when the prototype graduates.

The image budget passes. It warned for a while at 1.65 MB against
500 KB, fixed in #1480 by generating the map-sized derivatives described
above rather than by raising the budget.

Loading faces on demand was the other option in that issue and was not
taken. The whole graph is laid out inside the canvas, so every node is on
screen from the first paint and there is no offscreen work for a viewport
check to defer. At 178 KB the eager loop is no longer worth replacing
with per-frame intersection maths.

## Touch

Touch has no hover, so the desktop interaction (hover names a node, click
opens the profile) collapsed into a single tap that navigated to a profile
the visitor never saw the name of. At phone width the canvas is about
340 px across and holds 189 nodes, roughly 29 px apart, so the nearest
node to a fingertip is frequently the neighbour, and the visitor landed on
the wrong person with nothing to tell them so.

A tap now previews and a second tap on the same node follows through, with
a tap on empty space clearing the card. The pick radius widens from 13 px
to 20 px on a coarse pointer, which is safe only because the preview means
a wrong pick is seen before it is acted on. Mouse behaviour is unchanged:
hover names, one click opens.

The same bug was found and fixed on the EISS Atlas
(EISSeuropa/EISSeuropa.github.io#1431).

## Without JavaScript

`<main>` carries a `<noscript>` block naming the list-based equivalents,
matching the convention the ESSC pages already use. The canvas, the
statistics strip and the control rows are all script-rendered, so without
it the page was a heading, a lede and three empty boxes. That did not
matter while the page was unlisted and started mattering the moment it was
linked and indexed.

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

  `match_author()` resolves an author string to a member in two passes: the
  name as written, then the same name rewritten given-first when it is
  unambiguously surname-first. Each pass matches exactly, then on a first
  initial where exactly one member fits, since a wrong tie is worse than a
  missing one. Between them that covers `Ada Lovelace`, `A. Lovelace`,
  `Lovelace, Ada`, `Lovelace, A.P.B.` and `LOVELACE Ada`.

  Two guards keep it from inventing collaborations. A plain two-token name
  is never reversed, so `Turing Alan` stays unmatched rather than becoming
  Alan Turing. An entirely upper-case name is left alone, since there the
  capitalisation says nothing about which token is the surname, though
  initials are excluded from that test because they are upper case under
  every convention. Anything unresolved is listed in
  `stats.authors_unmatched` and printed by the build.

  That list is deliberately not a gate. A genuine co-author from outside
  the Action is an unmatched author and always will be, so no threshold
  separates one from a mistyped member. Reporting makes a formatting
  problem visible without a check that would cry wolf on most papers.
- **Server-side layout coordinates** are a deliberate follow-up. The
  renderer lays out client-side for now, which is fine at this size.

## Files

| Path | Role |
| --- | --- |
| `network-map.html`, `network-map.fr.html`, `network-map.de.html` | The prototype page in three locales |
| `assets/js/network-map.js` | The canvas renderer (pure consumer of `network-map.json`) |
| `assets/css/network-map.css` | Network-Map-only styles |
| `scripts/build-network-map.py` | Derives `data/network-map.json` (with a `--check` drift gate) |
| `scripts/test-build-network-map.py` | Tests for the derivation |
| `data/network-map.json` | The committed node/edge graph (generated, never hand-edited) |
