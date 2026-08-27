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

## Status: a signposted beta

The page is reachable and indexable. It carries a *Beta* pill, is
linked from the Working Groups page and the Directory, sits in
`sitemap.xml` and the visual sitemap in all three locales, and its
`<main>` carries `data-pagefind-body` so on-site search finds it.

There is no primary-nav entry. The header is at the capacity rule in
`docs/homepage-ia-phase2.md`, so the map is reached from the two pages
whose data it draws, using the shared signpost callout that
`/about.html` already uses for the roadmap.

The pill read *Prototype* until August 2026, and its removal trigger was
the first co-authorship edge. That trigger belonged to D6 rather than to
the map: the layer is built, tested against a planted entry, and waiting
on publications the Action has not produced yet, so the label was pinned
to someone else's schedule. It now reads *Beta*, and goes when the UX
issues filed alongside it have landed (#1643 to #1646), which is a
trigger the maintainer controls. The EISS Atlas made the same move for
the same reason (EISSeuropa/EISSeuropa.github.io#1427).

The pill's class is still `.network-map-proto-pill`. Renaming it would
restamp the `?v=` hash on every page of the site, which is a large diff
for a word that appears in no user-facing surface.

The page is held to the same Lighthouse assertions as every other
audited page. It used to carry the one exemption `lighthouserc.json` ever
had, dropping `categories:seo` while the deliberate `noindex` kept the
score at 0.58. The first measured run after signposting put it at 1.00,
so the exemption and the `assertMatrix` it forced were both removed
(#1605).

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

`scripts/build-network-map.py` builds `data/network-map.json`, a node/edge graph,
and rewrites the list region of the three locale pages from the same graph.
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

`check-data-shape.py` validates the node and edge shape, the referential
integrity of every edge endpoint, and the fields the edition filter depends
on: a `year` on every panel edge, and a `stats.panel_editions` that is
sorted and agrees with the years actually present (#1600). That last check
matters because `--check` only proves the committed file matches what the
current script emits, so a bug in the script yields a file that is
consistent, wrong, and stale-free.

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
audited page, which it passes without relaxation, and since #1605 it
carries no exemption at all (see *Status* above).

The image budget passes, confirmed by measurement rather than by
arithmetic: the run on the signposted page reports no budget warning for
this URL. It warned for a while at 1.65 MB against 500 KB, fixed in #1480
by generating the map-sized derivatives described above rather than by
raising the budget.

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

## Find, and the URL

The map draws 191 people and, until #1642, offered no way to reach one of
them. A member opening the page to find themselves, or the two others
working on their theme, had to hover dots until one was the right name,
which at phone density is roughly 29 px between neighbours.

A search row above the map is backed by a native `<datalist>` built from
the same person nodes the canvas paints. The browser's own picker is
keyboard-navigable, announced, and filters as it is typed, so there is no
custom listbox here. A match pins the person as `spotlight`, which joins
`hovered` in one focus chain in `draw()`: the pinned card outlives a
pointer move, and everything not connected to the person dims.

The answer is written into a visible `role="status"` line under the box.
Three states are separate on purpose, since a reader who searched a name
that the filters are hiding needs to know the map holds the person rather
than that they typed it wrong:

- nothing matches what was typed,
- somebody matches but the current filters hide them,
- somebody matches and is now pinned.

**The URL carries the view** (#1602). The lens, the hub chips, the
overlays, the edition and the pinned person all ride in the query string,
written with `replaceState` rather than `pushState`, since a filter is not
a page and twenty chip clicks should not be twenty presses of the back
button. `applyUrlState()` runs before any control renders: reading it
after them left a chip painted "off" over an overlay that was on.

`?hubs=` is read once, on the lens it was written for, because a hub id
means nothing in the other lens. Two failure modes are told apart. A
`hubs=none` is somebody deliberately switching every chip off, and the
disclosure summary and the list under the map both report the empty
result, so it is honoured. A `?hubs=` matching nothing this lens holds is
a stale or mistyped link, so the whole map is restored and the status
line says why.

**Every profile is an entry point.** `build-profile-pages.py` renders a
link to `network-map.html?find=<slug>` beside the way back to the
directory, in all three locales, so a profile leads into the network
rather than ending at itself. The `?find=` value resolves as a node id
first, then an exact name, then a substring, and a hub id is refused
since pinning one would break `personVisible()` rather than answer the
search.

A copy-link button is not here. The address bar is the share affordance on
a desktop, and the EISS Atlas only added its own button
(EISSeuropa/EISSeuropa.github.io#1445) once the view had more state than a
reader could see. Worth revisiting for the phone, where the URL is
truncated and awkward to copy.

## The page order

The map is the reason a visitor opens the page, so it comes first. It did
not: measured on the served page, the canvas started at y=622 on a
1280x900 desktop and y=998 on a 375x812 phone, which put the whole map
below the first screen on a phone. Three things were sitting in front of
it, and each moved.

The lede taught the mechanics (the two lenses, the overlays, the hover,
the click-through) at 170 px on a desktop and 340 px on a phone. Those
mechanics are all on the page already, named on the chips and spelled out
in the legend, so the lede now says what the map is and stops.

The statistics strip moved below the canvas. Six tiles cost 70 px and
229 px respectively, and they are a thing to read rather than a control.

The hub chips fold into a `<details>`, closed by the renderer on load and
open in the markup so a reader without scripting still gets them. That
row is the one that grows with the lens, four chips on Working Groups and
fifteen on research themes. Its summary reports how many hubs are showing,
since a filtered map behind a closed disclosure is otherwise a state with
nothing on screen to explain it.

Map top is now y=470 and y=638. The Find row added in #1642 costs 77 px of
that, taking it to y=547 and y=715, which still leaves the canvas inside
the first screen on a phone. #1643 is where the rest comes back.

## Without JavaScript

`<main>` carries a `<noscript>` block, matching the convention the ESSC
pages already use. The canvas, the statistics strip and the control rows
are all script-rendered, so without it the page was a heading, a lede and
three empty boxes. That did not matter while the page was unlisted and
started mattering the moment it was linked and indexed. The block now
points at the table below the map rather than at another page, which is
an alternative the reader already has in front of them.

## Accessibility

The canvas is a visual convenience, not the only way to the
information. Under the map sits a table of everyone it draws, with their
Working Groups and their country, and the canvas `aria-label` points at
it. The legend spells out what every colour and ring means in text.

That table is rendered at build time by `build-network-map.py`, between
the `network-map:list` sentinels, the same splice `build-field-guide.py`
uses on the glossary pages. Rendering it in the browser would have given
the alternative the same dependency as the barrier it answers, which is
the defect the EISS Atlas found in its own list
(EISSeuropa/EISSeuropa.github.io#1496).

It sits inside a closed `<details>`, because 83 profile links that a
sighted keyboard user cannot see are 83 stops in the tab order that
appear to lead nowhere. `network-map.js` hides and shows the same rows as
the filters move, off the same `personVisible()` the canvas paints with,
so one rule decides who is on the map and the two surfaces cannot
disagree.

Countries are stored as English exonyms, the way the Directory stores
them, and the renderer localises each cell through `window.netsecCountry`
from a `data-country` attribute. Without scripting the FR and DE tables
carry the English name, which is the information rather than an error.

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
