# Force-map lessons

Two force-directed maps run across the two repositories of this initiative.
The **NetSec Network Map** ([`/network-map.html`](../network-map.html)) draws
the Action's people. The **EISS Anthology Atlas** (`/anthology-atlas.html`, in
[EISSeuropa/EISSeuropa.github.io](https://github.com/EISSeuropa/EISSeuropa.github.io))
draws the published corpus. Roughly a thousand lines of hand-rolled canvas
each, written independently.

They keep finding the same bugs, months apart.

In August 2026 the Network Map received about twenty user-experience fixes, and
every one of them had already been found and fixed on the Atlas. Reconstructing
that list meant an hour reading the other repository's commit history, which is
an hour a checklist gives back.

## The rule

**Before changing either map, read this list.** After fixing a user-experience
bug in either map, add a line to it: what broke, what the fix was, and the pull
request that carried it.

Not a shared library. Two build systems, two deployment paths, and a coupling
that would make each repository harder to change alone. The duplication is not
the expensive part, the forgetting is.

## The list

`NM` links into this repository, `AT` into
[EISSeuropa.github.io](https://github.com/EISSeuropa/EISSeuropa.github.io). The
middle column is where the fix landed first.

| Lesson | Found first | Then |
| --- | --- | --- |
| A hover card anchored below-right of the pointer is clipped by a stage with `overflow: hidden`. Flip on both axes rather than clamp, or a node in the lower third loses its call to action. | AT [#1428](https://github.com/EISSeuropa/EISSeuropa.github.io/pull/1428) | NM [#1668](https://github.com/EISSeuropa/netsec.github.io/pull/1668) |
| `touch-action: none` for node dragging makes the whole canvas deaf to page scrolling on a phone. Declare `pan-y pinch-zoom` at rest and flip to `none` only while zoomed in. | AT [#1428](https://github.com/EISSeuropa/EISSeuropa.github.io/pull/1428) | NM [#1668](https://github.com/EISSeuropa/netsec.github.io/pull/1668) |
| Wheel zoom that claims every event turns the canvas into a desktop scroll trap. Require ctrl or command, which is what a trackpad pinch already sends, and say so in the legend. | AT [#1441](https://github.com/EISSeuropa/EISSeuropa.github.io/pull/1441) | NM [#1668](https://github.com/EISSeuropa/netsec.github.io/pull/1668) |
| Ring and hub labels overprint each other. Order them radially, de-conflict greedily biggest-first, and check each label against the other hubs' **discs** rather than only against other labels. | AT [#1484](https://github.com/EISSeuropa/EISSeuropa.github.io/pull/1484) | NM [#1668](https://github.com/EISSeuropa/netsec.github.io/pull/1668) |
| On a touchscreen the first tap navigates before the card can be read, and a mouse-sized hit radius lands on a neighbour. First tap previews, second follows, and the radius widens under a coarse pointer. | AT [#1437](https://github.com/EISSeuropa/EISSeuropa.github.io/pull/1437) | NM [#1668](https://github.com/EISSeuropa/netsec.github.io/pull/1668) |
| Every filter chip starting pressed makes isolating one of fifteen a fourteen-click job. Lead each row with All and None, and put a Clear on the summary, which is the only filter control visible while the row is folded. | AT [#1450](https://github.com/EISSeuropa/EISSeuropa.github.io/pull/1450) | NM [#1665](https://github.com/EISSeuropa/netsec.github.io/pull/1665) |
| The largest targets on the map answer nothing when clicked, and on a touchscreen answer nothing at all. Open a panel **under** the canvas: at 375px an overlay covers the cluster it is describing. | AT [#1467](https://github.com/EISSeuropa/EISSeuropa.github.io/pull/1467) | NM [#1665](https://github.com/EISSeuropa/netsec.github.io/pull/1665) |
| Filtering that rides on the hub click makes a stray click expensive. Put it behind its own button inside the panel. | AT [#1467](https://github.com/EISSeuropa/EISSeuropa.github.io/pull/1467) | NM [#1665](https://github.com/EISSeuropa/netsec.github.io/pull/1665) |
| Every chip off, a search that matches nothing, a search whose match the filters are hiding, and a failed data load are four different states and need four different sentences. | AT [#1441](https://github.com/EISSeuropa/EISSeuropa.github.io/pull/1441) | NM [#1671](https://github.com/EISSeuropa/netsec.github.io/pull/1671) |
| The page opens on a column of chips rather than on the map. Fold the filter rows into a disclosure, move the statistics below the canvas, and cut the lede to what the map is. | AT [#1437](https://github.com/EISSeuropa/EISSeuropa.github.io/pull/1437) | NM [#1650](https://github.com/EISSeuropa/netsec.github.io/pull/1650) |
| A lede teaching the mechanics repeats what the chips and the legend already say, and costs 340px on a phone. | AT [#1462](https://github.com/EISSeuropa/EISSeuropa.github.io/pull/1462) | NM [#1650](https://github.com/EISSeuropa/netsec.github.io/pull/1650) |
| A list alternative rendered by the same script that draws the canvas is not an alternative, since it shares the dependency that is the barrier. Render it at build time. | AT [#1500](https://github.com/EISSeuropa/EISSeuropa.github.io/pull/1500) | NM [#1650](https://github.com/EISSeuropa/netsec.github.io/pull/1650) |
| Two theme names joined by "and" are unreadable, because theme names carry their own. Join a pair with a slash. | AT [#1480](https://github.com/EISSeuropa/EISSeuropa.github.io/pull/1480) | NM [#1674](https://github.com/EISSeuropa/netsec.github.io/pull/1674) |
| A translated page has less room than the English one: the beta ribbon costs 80px and the copy runs longer. Measure every locale at 375px, not only English. | AT [#1553](https://github.com/EISSeuropa/EISSeuropa.github.io/pull/1553) | NM [#1662](https://github.com/EISSeuropa/netsec.github.io/pull/1662) |
| Nobody can find one dot among two hundred. A native `<datalist>` gives type-ahead, keyboard navigation and announcement for free. | AT [#1178](https://github.com/EISSeuropa/EISSeuropa.github.io/pull/1178) | NM [#1658](https://github.com/EISSeuropa/netsec.github.io/pull/1658) |
| Filters that are not in the URL cannot be shared. Use `replaceState`, not `pushState`: a filter is not a page. | AT [#1166](https://github.com/EISSeuropa/EISSeuropa.github.io/pull/1166) | NM [#1658](https://github.com/EISSeuropa/netsec.github.io/pull/1658) |
| "Prototype" reads as unfinished to a reader who cannot tell the difference. Beta says the same thing without inviting them to wait. | AT [#1427](https://github.com/EISSeuropa/EISSeuropa.github.io/pull/1427) | NM [#1655](https://github.com/EISSeuropa/netsec.github.io/pull/1655) |
| The canvas is not keyboard-reachable and announces nothing. `tabindex="0"`, arrow-key traversal in the same order as the list alternative, and one polite live region shared with the search. | NM [#1671](https://github.com/EISSeuropa/netsec.github.io/pull/1671) | — |
| An overlay hidden behind a closed disclosure changes the map with nothing on screen accounting for it. The summary has to report it. | NM [#1678](https://github.com/EISSeuropa/netsec.github.io/pull/1678) | — |
| A ring colour picked without checking the hub palette collides with a hub fill. Dash the ring rather than hunt for a free hue. | NM [#1698](https://github.com/EISSeuropa/netsec.github.io/pull/1698) | — |
| Controls drawn by script drift below the target-size floor, because they never sit in a stylesheet anyone audits. Measure them. | NM [#1691](https://github.com/EISSeuropa/netsec.github.io/pull/1691) | — |

## Where the two maps genuinely differ

Worth knowing before copying a fix across.

- The Atlas draws **papers and authors**, the Network Map draws **people and
  hubs**. The Atlas has a bridge filter for papers carrying two themes. The
  Network Map's nearest equivalent is the hub panel, since a person's hubs are
  memberships rather than tags.
- The Network Map has an in-page table rendered at build time, a keyboard path,
  and a `?find=` deep link from every profile. The Atlas has none of those yet.
- The Atlas has a guided tour and a first-visit welcome bar. The Network Map has
  neither, and is reached from two signpost cards rather than browsed cold.
- The Atlas is English-only. The Network Map is EN, FR and DE, which is why
  every string it draws goes through the shared `netsecT` catalogue.
