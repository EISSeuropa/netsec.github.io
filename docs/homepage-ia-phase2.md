# Homepage IA: Phase 2 detailed UX pass

> *Audience: Action Chair, Vice-Chair, MC members, the
> maintainer. This document is the output of Phase 2 of the
> two-phase IA pass described in `roadmap-2026.md` §"Homepage
> + header IA". It succeeds `docs/homepage-ia-quick-audit.md`
> (Phase 1, 22 May 2026), which took the structural quick-wins
> into v1.5.0. Phase 2 covers the deeper UX questions Phase 1
> deferred: nav grouping, section ordering, mobile patterns,
> audience tracks, content lifecycle, and future-proofing.*

Prepared by Dr Arthur Laudrain · 2 July 2026.

---

## Why now

Phase 1 shipped structural quick-wins into v1.5.0: the *Find
out more* / *For NetSec members* overlap resolved, the
Roadmap Gantt and Outputs moved to their own pages, News
capped at four with an archive, and two jargon labels
renamed. The nav dropped from 10 items to 8, and the home
page from 12 sections to roughly seven visible ones.

Phase 2 was pencilled for July–August, after the Conference
and Training School gave real content and traffic to reason
about, and after the brand refresh landed so the audit runs
against the finished visual identity rather than placeholders.
Both preconditions are met: Stockholm concluded 12 June, the
brand identity has been live since v1.8.0, and the site has
carried a stable eight-item nav and current section order
since v1.5.0 with no reported friction.

This pass runs maintainer-side. The roadmap's open question
about bringing in a UI/UX professional for Phase 2 was never
resolved with a budget commitment, so the fallback the roadmap
already named applies: the maintainer self-runs the audit. See
*Position 6* below for how that gets revisited.

---

## Current-state inventory

The home page today, in DOM order:

1. **Floating header**: NS-mark, 8 nav links (News, About,
   Working Groups, Directory, Events, Grants, Publications,
   Contact), lang switch, theme toggle, search trigger.
2. **Hero**: title, lede, two CTAs, Action stats strip.
3. **Details strip** (`.details-strip`): Action Number, MoU,
   CSO Approval, Duration.
4. **News** (`#news`): capped at 4 cards + archive link.
5. **Member Spotlight** (`#member-spotlight`): weekly pick,
   hidden when no spotlight is set.
6. **About** (`#about`): narrative, objectives, and the
   *Find out more* grid (FAQ, Glossary, Press kit).
7. **Working Groups** (`#working-groups`): 4 cards.
8. **Events** (`#events`): cards + Subscribe CTA.
9. **For NetSec members strip** (`.members-strip`,
   `#for-members`): Wiki + e-COST portal CTAs.
10. **Contact** (`#contact`): form + Action mailbox row.

Roughly seven sections a visitor actually scrolls past (the
details strip and the spotlight read as extensions of the
hero and News rather than independent stops). This is the
scroll length Phase 1 was aiming for, and it holds.

---

## Decisions

Six positions, each argued in the Phase 1 format: options
considered, recommendation, cost, risk, and what phase it
lands in. All six are decided in this document, and the
audience strip (position 2) is the one change that ships as
code in the same PR as this document.

### 1 · Header stays flat, no dropdowns

**Current.** Flat 8-item nav, comfortably under the 10-item
mark that felt tight before Phase 1.

**Options**

- **A. Group now** (*Activities* > Events / Grants /
  Training, *Reference* > FAQ / Glossary / Press kit). Solves
  a capacity problem that does not exist yet.
- **B. Stay flat, set a capacity rule for the future.** No
  work now, only a documented threshold for when grouping
  becomes worth doing.
- **C. Partial grouping** (group only *Reference*, leave
  *Activities* flat). Splits the difference but leaves two
  different interaction patterns in one nav bar for no
  present gain.

**Recommendation: B.** Dropdown grouping adds touch, keyboard,
and screen-reader complexity across three locales. That cost
is worth paying when the nav is genuinely full, not
speculatively. At 8 items there is room to grow.

The capacity rule: a 9th or 10th item still joins the flat
list. An 11th item triggers grouping. The grouping itself is
pre-agreed so the future change is mechanical rather than a
fresh design exercise: *Activities* groups Events, Grants, and
Training School, while *Reference* groups FAQ, Glossary, and
Press kit. Publications, Directory, About, News, and Contact
stay top-level regardless, since none of them fit either
bucket.

**Cost:** none now. Grouping, when triggered, is roughly a
day across markup, CSS, and the three locale checks.
**Risk:** none (this is a documented threshold, not a change).

**Phase 2, closed with no implementation.**

### 2 · Audience-track strip ships now

**Current.** No audience differentiation. A researcher, a
policy-maker, an MC member, and a journalist all follow the
same scroll from News through Contact.

**Options**

- **A. Do nothing.** The strip Phase 1 deferred stays
  deferred, and audience needs stay implicit in page order.
- **B. An "I'm a…" interactive chooser.** A control that asks
  the visitor to self-identify and reveals a tailored path.
  Higher build cost (state, at minimum three locale copies of
  the interaction, a decision on whether the choice persists),
  and the payoff over a static strip is modest: the routing
  logic is the same four destinations either way.
- **C. A static four-card link strip.** Each card names an
  audience and links straight to what that audience needs.

**Recommendation: C.** A static strip headed "Start where you
are" (working title, final copy is the implementer's call)
sits directly after the details strip, so it is in the first
viewport on a phone. Four cards:

- Researcher → the Directory (`people.html`) and Grants.
- Policy-maker → Publications (`outputs.html`) and the
  Glossary.
- MC member → the *For NetSec members* strip / the members'
  Wiki.
- Press → the Press kit and News.

No JavaScript, no chooser state, no personalisation. The
interactive chooser (option B) was considered and rejected as
over-build: a set of links does the same routing job at zero
interaction cost, no additional accessibility surface, and no
locale-specific interaction copy to maintain.

**Cost:** roughly half a day (markup, CSS, three-locale copy).
**Risk:** low. Static links carry no new failure mode, and the
only judgement call is the four destination pairs, which this
document fixes.

**Phase 2, implemented in this PR.**

### 3 · Mobile long-scroll: the strip is the treatment

**Current.** Mobile gets the same DOM as desktop, in
mobile-friendly CSS. A phone visitor scrolls through the full
section order.

**Options**

- **A. Sticky table of contents.** A persistent jump-menu
  pinned to the viewport as the visitor scrolls.
- **B. Mobile-specific section reordering.** Serve a
  different DOM order under the mobile breakpoint.
- **C. Let the audience strip carry the load.** No separate
  mobile treatment, since the strip from position 2 already
  puts each audience's exit link in the first viewport.

**Recommendation: C.** A sticky TOC needs JavaScript to track
scroll position and carries a real stacking-context risk
against the floating header, which already occupies that
layer. Mobile section reordering makes the DOM diverge between
breakpoints, which breaks anchor deep links (a `#working-
groups` link would land somewhere different depending on
viewport) and confuses assistive technology that does not
share the visual reflow. Both were considered and rejected on
those grounds.

The page is down to roughly seven visible sections
post-Phase-1, which is a manageable phone scroll on its own.
The audience strip resolves the specific problem a sticky TOC
would have solved, first-time visitors not knowing where to
go, without either of the two costs above.

**Cost:** none beyond the strip already costed in position 2.
**Risk:** none.

**Phase 2, closed with no separate implementation.**

### 4 · Section ordering: keep current order

**Current.** News, About, Working Groups, Events, *For
members*, Contact.

**Options**

- **A. Reorder around audience tracks** (for example, moving
  Directory-adjacent content earlier for the researcher path).
- **B. Keep the current order.**

**Recommendation: B.** Reordering invalidates anchor deep
links every existing share-link, footer link, and cross-page
reference depends on, and it costs returning-visitor muscle
memory built up since launch. The gain would be speculative:
there is no traffic evidence that the current order is wrong,
only a hypothesis that audience-specific ordering might be
better. The audience strip already solves the tension Phase 1
flagged (a first-time visitor wanting "what is NetSec" versus
a returning visitor wanting news or grants) without moving
anything. A first-time visitor who lands via the strip's
routing gets there in one click regardless of where a section
sits in the scroll.

**Cost:** none. **Risk:** none, as this is a decision not to
act.

**Phase 2, closed with no implementation.**

### 5 · Content lifecycle: mostly settled elsewhere

**Current.** News is capped at 4 on home with a `/news.html`
archive (shipped, see the *Added* entries already in the
CHANGELOG). Events has no equivalent past/upcoming split on
the home-page block.

**Recommendation.** News scaling past the current cap is
already tracked in issue [#1230](https://github.com/EISSeuropa/netsec.github.io/issues/1230), so there is nothing new to
decide here.

Events' past-events treatment is the one open item this pass
surfaces. The Events page itself already separates Upcoming
and Past into distinct visual blocks. The home-page Events
block does not yet need the same split at today's event count,
but will as entries accumulate past the Year 1 mark. This is
noted as a future issue candidate rather than scoped here,
since it needs a concrete trigger (event count, or a specific
complaint) before it is worth designing against.

**Future-proofing (D11, D12).** The Inclusion & Diversity
Declaration and the Environmental Sustainability Guidelines
land as cards inside an existing section, About or the *Find
out more* grid, rather than as new top-level homepage
sections. Either lands without a new nav item under the
capacity rule from position 1: at 8 items today, neither
deliverable pushes the nav past the 10-item threshold that
would trigger a rule change, let alone the 11-item threshold
that triggers grouping.

**Cost:** none in this pass beyond documenting the pointers.
**Risk:** none.

**Phase 2, positions recorded, no new implementation beyond
the pointers above.**

### 6 · UI/UX consult stays open

The roadmap's Phase 2 framing left one open question: whether
to bring in a UI/UX professional for this pass, with the
Action Chair as decision owner on budget. That decision never
landed, so Phase 2 ran maintainer-side, as the roadmap's own
fallback anticipated.

The consult option stays open for a Year-2 pass. The trigger
is traffic data: once the first privacy-respecting usage
analytics ship (issue [#727](https://github.com/EISSeuropa/netsec.github.io/issues/727), milestone v1.13.0), real
numbers on whether the audience-track routing in position 2 is
actually being used will make the case for or against
professional input far better than another round of
maintainer judgement calls. Until then, the routing choices in
this document are the best available call without that data.

---

## Summary table

| Position | Decision | Cost | Phase |
|---|---|---|---|
| 1 | Header stays flat. Capacity rule set for a 9th–10th item (flat) and an 11th (grouped, pre-agreed groups) | none now | 2, closed |
| 2 | Static four-card audience-track strip after the details strip, no JS | ~½ day | 2, implemented |
| 3 | No sticky TOC, no mobile reorder. The audience strip is the mobile treatment | none beyond position 2 | 2, closed |
| 4 | Section order unchanged | none | 2, closed |
| 5 | News scaling tracked in #1230. Events past-treatment noted as a future issue candidate. D11/D12 land as cards in existing sections | none | 2, positions recorded |
| 6 | UI/UX consult stays open, revisited once #727 analytics (v1.13.0) show routing usage | none now | deferred to Year 2 |

**Total build cost this pass:** roughly half a day, all in
position 2.

## What's deferred

- **The UI/UX consult** (position 6): open, gated on Year-2
  traffic data from issue #727.
- **Events past-events home-page treatment** (position 5): a
  future issue candidate, not scoped here. Needs a concrete
  trigger before it is worth designing against.
- **Nav grouping implementation** (position 1): the grouping
  itself is pre-agreed, not built. It fires mechanically once
  a real 11th nav item is proposed.
- **Any reassessment of section order or mobile treatment**:
  both are closed decisions for now, but would be worth
  revisiting alongside the Year-2 consult if the analytics
  from #727 show a pattern this pass did not anticipate.
