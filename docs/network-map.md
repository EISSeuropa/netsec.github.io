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

## Reading the detail: zoom, the card, and the labels

Three legibility defects, all found by measuring the served page (#1644).

**Zoom and pan.** 191 nodes share a 640 px canvas and a face draws at
about 16 px, so a busy cluster could not be resolved into people at any
window size. A view transform (scale plus translate) is applied at paint
time, with ctrl or command plus wheel to zoom about the cursor, buttons
over the stage, drag-to-pan on empty canvas, and a Reset. The force layout
never learns about it: `nodeAt()` converts screen coordinates to world
ones and divides the pick radius by the scale, so the paint and the
pointer stay in agreement and a target stays the same size under a
fingertip however far the map is zoomed.

A plain wheel keeps scrolling the page. Claiming every wheel event over
the canvas turns 640 px of the page into a scroll trap, which is the
phone problem arriving by the other door, and ctrl-wheel is what a
trackpad pinch sends anyway. `touch-action` flips to `none` while zoomed
so a finger pans the map, and back at rest so the page scrolls.

Zoom is floored at 1, so the map is never smaller than the stage, and the
pan is clamped to the overhang, which pins it to zero at rest. Reset also
puts a dragged hub back, since that is the other half of "the map is not
where I left it".

**The hover card flips rather than clamps.** `.network-map-stage` clips
its overflow and the card was anchored below and to the right of the
pointer with a clamp on the right edge only. Probing a grid of 45 hovers
across the map, four of them produced a card hanging up to 50 px outside
the stage, taking the themes, the co-panel line and "View profile" with
it. The card now flips above the pointer when it would run past the
bottom and to its left when it would run past the right. The same probe
now reports none outside. Its size is measured from the corner, once per
node, because a card measured where it sits near the right edge reports
itself narrower and taller than the one about to be drawn.

**Label de-confliction.** Fifteen theme hubs on a ring put their labels
through each other, worst at phone width. Labels are now a pass of their
own after the circles, so they can be placed against each other, with two
rules and no layout library. Radial ordering: on a ring of more than six
hubs the label goes on the side away from the centre, which is where the
space is. Then greedy placement, biggest hub first, trying four positions
(the outward side, the other side, then one line further out on each)
against the labels already placed and against every other hub's disc. A
hub under twelve people gives up its label rather than overlap when none
of the four is clear, since the hover card, the chips and the panel all
still name it. A larger hub keeps its label even when it has to overlap,
because a hub of thirty-five people with no name on it is worse.

The Working Groups lens is untouched: four hubs is not more than six, so
the radial rule never fires and the labels sit under their hubs as
before.

## The chip rows, and what a hub answers

Every hub chip starts pressed, so isolating one research theme cost
fourteen clicks off and fourteen back. Each row now leads with **All** and
**None**, both disabled at the ends of their range, and the filter summary
grows a **Clear** whenever anything is filtering, since the summary is the
one filter control still on screen while the row is folded away. A button
inside a `<summary>` toggles the disclosure on pointer and on keyboard
unless both are stopped, which is why Clear swallows its own events.

**A hub answers a click.** The four WG hubs and the fifteen theme hubs are
the largest targets on the canvas, and a click on one fell through to the
drag handler and did nothing. On a touchscreen, where there is no hover
card either, a hub did nothing at all.

A click or a tap opens a panel **under** the map, since at 375 px an
overlay covers the cluster it is describing. It carries the hub's member
count, the three hubs it shares the most people with, a button that solos
it, and a link into the matching surface: `working-groups.html#wg<N>` for a
Working Group, `people.html#themes=<slug>` for a theme. Each bridge is a
button that moves the panel across, so walking the network costs nothing
to undo. Filtering stays behind its own button rather than riding on the
click, so a stray click on a hub costs nothing.

`pinnedHub` joins `hovered` and `spotlight` in one focus chain in
`draw()`, which is the hover highlight made to stay put. Nothing else in
the paint changed.

A press that moves more than four pixels is a drag rather than a click, so
rearranging a hub does not also open its panel. A second click on the same
hub closes it, and so do Escape, the close button, a click on empty canvas
and a lens switch. A hub id means nothing in the other lens, which is why
the switch closes it rather than carrying it across.

The theme link is built from the theme **name** with the directory's own
slug rule, not from the hub id. The build slugifies theme ids with
`_directory_common.slugify`, which strips diacritics, and the directory
builds its `#themes=` hash with a rule that does not. They agree on all
fifteen themes today and would part company on the first theme name
carrying an accent.

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

The hub chips and the overlays fold into a `<details>`, closed by the
renderer on load and open in the markup so a reader without scripting
still gets them. The hub row is the one that grows with the lens, four
chips on Working Groups and fifteen on research themes, and the overlays
row wraps to three lines on a phone.

The overlays were deliberately left outside at first, so a first visit met
the ESSC co-panel and mentorship layers without opening anything. Each
chip added above the map costs a phone screen about 40 px, and #1674's
profile filter was the one that made that arithmetic visible (#1677), so
they went in with the rest.

Its summary carries both: how many hubs are showing, and how many overlays
are on. Either state behind a closed disclosure is otherwise a change to
the map with nothing on screen accounting for it.

Map top is now y=469 on a desktop and y=594 on an English phone. The Find row added in #1642 costs 77 px of
that, taking it to y=545 and y=684.

**The translated pages are measured too** (#1657). The first pass of this
work was measured against the English page alone, and the FR and DE
phones were sitting at y=830 and y=855, which is where the English page
had been before any of it. Three things separate them from English at
375 px: the beta-translation ribbon is an 80 px block above the header,
the lens chips wrap to two rows against English's one, and a faithful
translation of the English lede runs longer in both languages.

The FR and DE ledes are now cut shorter than the English one rather than
translated from it, since they are carrying an extra 80 px of ribbon. The
lede goes from 243 px and 267 px to 146 px in both, and the map top in
both is y=733. What it drops is the expansion of the Action's name, which
the footer carries on every page anyway.

The 43 px the wrapping lens row cost came back with the chip-row work.
Smaller chips under 640 px were not enough on their own, so the row labels
go too: each row carries an `aria-label` on the group, and two chips
reading "Groupes de travail" and "Thèmes de recherche" under the lede do
not need the word "Angle" above them. The Find row keeps its `<label>`,
since hiding that one would leave the input with no accessible name.

Map top on a phone is now y=622 in English and y=648 in French and German,
after the overlays followed the hub chips into the disclosure (#1677) and the
chips themselves went to 45 px under a thumb (#1603's sweep). The 28 px that
last one costs is the right trade: a target a thumb can hit beats 28 px more
map above it.

## Without JavaScript

`<main>` carries a `<noscript>` block, matching the convention the ESSC
pages already use. The canvas, the statistics strip and the control rows
are all script-rendered, so without it the page was a heading, a lede and
three empty boxes. That did not matter while the page was unlisted and
started mattering the moment it was linked and indexed. The block now
points at the table below the map rather than at another page, which is
an alternative the reader already has in front of them.

## The inclusiveness figure

COST evaluates an Action on its inclusiveness, and Inclusiveness Target
Country participation is the number that carries most weight there. The
map now reports it: 106 of 192 people, with a dashed ring on those
members behind an overlay chip (#1646).

**Where the list comes from.** The Annotated Rules (Level C v3.0, 25
September 2025) do not hold it. They say twice that it lives in the
Country and Organisations Table, so the 25 names in `ITC_COUNTRIES` are
quoted from *Annex I - Level A: Country and Organisations Table, version
1.7, 1 November 2023*, checked on 27 August 2026 and cross-checked
against the Excellence and Inclusiveness page on cost.eu, which lists the
same 25. The constant carries that provenance in a comment beside it.
Re-check it when COST publishes a new version of the annex: this is a
policy fact aimed at an evaluator, and a list one country wrong is a
wrong public claim about a member's institution.

**Spelling is where this breaks silently.** The directory writes
"Czechia" and "Bosnia & Herzegovina" where COST writes "Czech Republic"
and "Bosnia and Herzegovina". A plain membership test would drop two real
ITCs and understate the figure with nothing going red, so
`normalise_country()` strips diacritics, spells out the ampersand and
runs a small alias map, and the tests pin every spelling the roster
currently uses. Kosovo and Morocco are on the roster and are Near
Neighbour Countries rather than ITCs, so they are correctly outside.

**What the figure cannot see.** The same table designates the EU
Outermost Regions as ITC, so a member in the Canary Islands or Guadeloupe
is ITC while Spain and France are not. `bios.json` carries a country and
nothing finer, so the count understates them. The page says so under the
figure rather than burying it here.

**The ring is dashed on purpose.** `--wg-3` is `#8457ea` and `--wg-4` is
`#f59e0b`, so the four Working Group hues already claim violet and amber,
and the theme wheel claims more. Rather than hunt for a free hue, the ring
is dashed, which tells it apart from every solid fill and solid ring on
the map whatever the hue does.

## Findings

The statistics count the roster, which is what the Directory is for.
Under them sits a line of things only the map's own structure knows
(#1646), computed client-side from data already loaded and recomputed
with the lens:

- the pair of hubs sharing the most people, which opens the first of
  them,
- how many people sit in more than one hub of the current lens, which is
  the "bridges of the Action" claim the lede makes, with a number on it,
- the hub with the fewest people, which opens it.

The busiest pair reuses `sharedWith()`, the function the hub panel
already calls, so the finding and the panel can never name different
numbers. The pair is joined with a slash rather than an "and", since
theme names carry their own: "Foreign policy and diplomacy and Security
and defence" is four of them in one sentence. The EISS Atlas settled the
same question the same way (EISSeuropa/EISSeuropa.github.io#1480).

The smallest-hub finding carries no number, so there is no singular to
get wrong when a theme is down to one person. The count is on the hub
itself.

**Still open in #1646:** the Inclusiveness Target Country overlay, which
is parked on the maintainer confirming the ITC list. It is a COST policy
fact aimed at an evaluator, and a list one country wrong is a wrong
public claim about a member's institution.

## What the map actually draws

The statistics strip counted the whole roster while the canvas beside it
drew 142 of 191 on the Working Groups lens and 70 of 191 on the research
themes lens. A member on no WG roster has nothing to be drawn towards on
one lens, and a member with no research themes recorded has nothing on
the other, so the map has never drawn them while the figure above them
counted all 191.

A tile now reports it, and follows the lens (#1651). It counts membership
of the lens rather than of the current filter, since that is the gap the
strip was silent about, and the chips are already reported by the filter
summary and by the list hint.

The other half of the same gap is the 108 people with no directory
profile, who render as small grey dots that link nowhere (#1647). The map
is the clearest picture the site has of who is missing from the
Directory, so a line under the figures says so and points at the bios
form, and an **Only members with a profile** chip narrows the map to the
part the Directory documents. It is a view filter rather than an overlay,
so it runs through `personVisible()`, which is the one rule the canvas,
the table and the keyboard traversal all read.

On the themes lens that chip is a no-op, since research themes come from
the bios and every person carrying one therefore has a profile. On the
Working Groups lens it goes from 142 to 34.

The country-map view and the members-over-time series stay in #765, where
they were moved: they are a statistics page rather than a network view.

## The keyboard, and the states that said nothing

`document.querySelector('#network-map-canvas').tabIndex` was -1, measured.
There was no focus, no traversal and no announcement, and the canvas
`aria-label` answered by pointing at two other pages. The list under the
map is the conformance answer; this is what makes the map itself usable
rather than only skippable (#1645).

The canvas takes focus and the arrow keys walk it. Traversal order is the
hubs of the current lens followed by the visible people in the order the
graph holds them, which is the order the table under the map lists them,
so the two surfaces agree. Landing on a hub opens its panel, landing on a
person pins them the way Find does, Enter follows a profile and Escape
clears. It reuses `spotlight` and `pinnedHub` rather than introducing a
third kind of selection.

Announcements go through the Find control's status line rather than a
second live region, so a screen reader hears one voice for the map. A tap
that pins a person announces it too.

Three states used to say nothing:

- every hub switched off drew an empty canvas, and the notice now names
  the control that emptied it rather than saying "nothing to show",
- a data-load failure wrote one line into the statistics strip, which
  moved below the map in the fold work and would have stranded the
  message off the fold, so it paints on the stage,
- a search that matched nothing, which the Find work already answered.

Notices are painted in screen space, after the view transform is unwound,
so a notice is never scaled or panned off the canvas.

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

The i18n drift checker strips the region before hashing, the way it
already strips the `?v=` cache-bust queries and the glossary facepiles.
The rows are member names, WG numbers and English country exonyms,
identical in all three locales and regenerated by every bios and cost.eu
sync, so one member joining the Action moved the English markup and
flagged the FR and DE pages as stale on the sync's own auto-PR (#1686).
Nothing is lost by exempting it: the region's own chrome lives in
`LIST_LOCALES`, which writes all three locales from one dict, and
`--check` already fails CI if a page does not match what the script
emits. This is the third instance of the same lesson, and CLAUDE.md §16
already names it: trace a sitewide change through every drift gate.

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

The accessibility statement carries the map in both of its lists as of
v1.4 (#1652): the canvas under *Non-accessible or limited content*, since
it conveys clustering visually and cannot express that to assistive
technology, and the table plus the keyboard path under *Accessibility
features in place*. Hand-translated for FR and DE, with the version
footer bumped and the review date left where it was.

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
- **Outputs per Working Group** derive from the `workingGroups` tag array
  every entry in `data/publications.json` carries, the same mechanism
  `events.json` uses to surface an item under a WG section (#1587). The map
  read the file for `authors` only, so an output tagged to WG2 contributed
  nothing to the WG2 hub, and a single-author output contributed nothing
  anywhere, since the co-authorship pass needs two matched names before it
  emits an edge. A policy brief with one author is a normal shape, so that
  was a structural blind spot rather than a missing nicety.

  The tag is counted onto the hub as an `outputs` field, which is option 2
  from that issue. Option 1, weighting the person-to-WG edge, was not taken:
  the renderer draws hub edges at a constant width, so it would have needed
  edge-weight rendering for the bipartite layer before it showed anything,
  and it cannot represent an output whose authors the matcher never places.

  The field is stamped only when the count is non-zero, so an empty
  `publications.json` produces a byte-identical graph and the layer arrives
  with the data. The hub's hover card and its panel gain a "{n} outputs"
  clause, and the statistics strip gains a tile, both the way the
  co-authorship chip waits for its first edge.

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
