# Homepage IA — Phase 1 quick-audit

> *Audience: Action Chair, Vice-Chair, MC members, the
> maintainer. This document is the output of Phase 1 of the
> two-phase IA pass described in `roadmap-h2-2026.md` §2.
> Phase 1 covers the structural decisions that need to land
> in v1.5.0 (late June 2026) — before the official-logo
> refresh ships into a known-suboptimal structure. Phase 2
> (July–August) does the deeper UX work.*

Prepared by Dr Arthur Laudrain · 22 May 2026 · ~1.5 days of
audit.

---

## Why now

The home page has accreted to **10 sections**; the floating
header runs at **10 nav items** (post-wordmark-removal it
fits, just). Year-1 deliverables (D6, D11, D12) and
post-Conference / post-Summer-School content will all land
between now and October. Without a structural pass first,
each addition slots into an already-tight grid.

The trigger to do it *now* rather than in Q3:

- **v1.5.0 ships the official Action logos** in late June.
  Logos define a *visual identity* — if they ship into an IA
  we plan to restructure four months later (v1.7.0 *Year 1
  closes*), we get two brand-facing changes in close
  succession. Not great for external readability.
- The Conference (11–12 Jun) and the inaugural MC plenary
  (before late Sep) both drive first-impression traffic.
  Cleaner-by-default beats clean-up-after.

Phase 1 is a **structural** pass — decisions about what
exists where, and which surfaces overlap. Phase 2 (Q3) is
the **detail UX** pass — audience tracks, mobile patterns,
content lifecycle.

---

## Current-state inventory

The home page today, in DOM order:

1. **Floating header** — NS-mark, 10 nav links, lang switch,
   theme toggle, search trigger.
2. **Hero** — title, lede, two CTAs (*Discover the Action*,
   *Join the network*), Action stats strip (CA24154 / launch
   date / membership).
3. **News** (`#news`) — 4 cards.
4. **About** (`#about`) — narrative + 3 numbered objectives.
5. *(within About)* **Find out more grid** — 4 cards: FAQ,
   Glossary, Press kit, members' Wiki.
6. **Working Groups** (`#working-groups`) — 4 cards.
7. **Committee** (`#committee`) — Action Leadership grid +
   WG-leads grid + WG co-leads grid + MC-by-country
   `<details>` collapse.
8. **Events** (`#events`) — 3 cards + centred Subscribe CTA.
9. **Roadmap** (`#roadmap`) — wide Gantt of 12 deliverables.
10. **Outputs** (`#outputs`) — 3 *Forthcoming* placeholder
    cards.
11. **For NetSec members strip** (`#for-members`) — tinted
    card with *Open the Wiki* + *e-COST portal* CTAs.
12. **Contact** (`#contact`) — form + Action mailbox row.

Floating header nav: News · About · Working Groups · Committee
· Network · Events · Grants · Roadmap · Outputs · Contact.

**Density measure** (rough): the home page is ~3 200 lines of
HTML — most pages on the site are 200–500 lines.

---

## Eight issues identified

For each: current behaviour, what's wrong (or might be),
options, recommendation, cost / risk, Phase (1 or 2).

### Issue 1 · Outputs section is mostly empty

**Current.** Three identical *Forthcoming* cards under
`#outputs`. Visible to every visitor, every visit. Reads as
"this Action hasn't produced anything yet."

**Wrong because**: D6 (policy briefs) doesn't ship until
M12 = mid-October. Until then we're advertising emptiness.

**Options**

- **A — Keep as-is.** Stable but visually weak for ~5 months.
- **B — Hide the section entirely until D6 lands.** Reads as
  "we're focused; check back". Drops a section's worth of
  scroll.
- **C — Replace with a status banner** ("First Year-1
  outputs arrive Oct 2026 — sign up for news"). Communicates
  the plan, recovers the screen real estate.
- **D — Move *Outputs* to a dedicated `/outputs.html` page;
  link from nav.** The page can have the same placeholders
  until D6, but they're not on the home page.

**Recommendation: B + D combined.** Hide the home-page
section now; create `/outputs.html` as the future home for
Year-1 outputs (currently empty / *Forthcoming* announcement).
When D6 lands in October, the dedicated page already exists
and we just populate it; the home page can choose to re-add
a *Latest output* card or link.

**Cost:** ½ day. **Risk:** none — placeholder removal.

**Phase 1.** Slots into v1.5.0.

### Issue 2 · "Find out more" grid + "For NetSec members" strip overlap conceptually

**Current.** The *Find out more* 4-card grid sits at the end
of the About section (FAQ, Glossary, Press kit, members'
Wiki). The *For NetSec members* tinted strip sits between
Outputs and Contact (Wiki + e-COST CTAs).

**Wrong because**: both signpost members-facing reference
content. *Find out more* includes the members' Wiki as one
of four cards; *For NetSec members* features the same Wiki
as its main CTA. A reader who sees both within one scroll
might wonder if they're meant to be different things.

**Options**

- **A — Keep both as-is.** Each has a distinct audience: the
  grid is for the discovery-curious; the strip is for
  members specifically.
- **B — Merge: drop the members' Wiki card from *Find out
  more*; keep the strip.** Now the grid is "for anyone" (FAQ
  / Glossary / Press kit) and the strip is "for members".
  Clean role separation.
- **C — Drop the strip entirely; rely on the *Find out more*
  card.** Loses the prominent member-onboarding signpost.
- **D — Move the strip up to right after the hero.** Members
  arrive directly; non-members scroll past.

**Recommendation: B.** *Find out more* becomes the
"reference shelf" (FAQ / Glossary / Press kit, public-
facing); the *For NetSec members* strip becomes
unambiguously the members-only entry point. Clean conceptual
separation; no scroll-length change.

**Cost:** ½ hour. **Risk:** none.

**Phase 1.** Slots into v1.5.0.

### Issue 3 · Roadmap Gantt belongs on its own page

**Current.** A wide, horizontally-scrolling Gantt chart of 12
deliverables, on the home page between Events and Outputs.

**Wrong because**: it's a project-management artefact that
the maintainer-evaluator audience reads but the
journalist-academic visitor mostly scrolls past. It also
breaks the "narrative flow" of the home page (news → about
→ what we do → how to help) by inserting an internal-project
chart in the middle.

**Options**

- **A — Keep on home (status quo).**
- **B — Move to a dedicated `/roadmap.html` page**; link from
  nav (replaces the current "Roadmap" nav item).
- **C — Collapse by default (`<details>`); expand on click.**
  Like the *MC by country* treatment.
- **D — Show a compressed two-line summary on home; link to
  the full Gantt on `/roadmap.html`.**

**Recommendation: B.** A dedicated `/roadmap.html` page lets
the Gantt have proper context (a short narrative explaining
what M-month means, COST quarter labels, etc.) and removes
~1 screen of scroll from the home page. The nav item stays;
just the destination changes.

**Cost:** ~½ day. **Risk:** low. The new page can re-use the
existing Gantt CSS.

**Phase 1.** Slots into v1.5.0.

### Issue 4 · News block has no archive strategy

**Current.** 4 cards on the home page. As post-Conference,
post-Summer-School, post-plenary content lands, this will
grow to 8–12+ by year-end. Nothing in the design says where
"old news" goes.

**Wrong because**: the home page will become "scroll through
13 news cards to get to About". Or we silently delete older
news — bad for institutional memory.

**Options**

- **A — Keep all news on home.** Acceptable up to ~6 cards;
  brittle past that.
- **B — Cap at 4 visible on home; "More news →" link to a
  dedicated `/news.html` archive page.**
- **C — Collapse old news into a *Past news* `<details>` on
  the home page** (like *MC by country*).
- **D — Switch to a feed-style design** (date headers,
  scrollable list) — bigger redesign.

**Recommendation: B.** Cap at 4 + archive page. Standard
pattern across news sites; readers know it. Cost is low and
the archive page also gives us a URL to link from the RSS
feed (queued for v1.6.0).

**Cost:** ~1 day (the archive page is the longer part).
**Risk:** low.

**Phase 1.** Slots into v1.5.0 (archive page can be minimal
in v1.5; expanded with metadata + pagination later).

### Issue 5 · Header label clarity

**Current.** Nav reads: *News · About · Working Groups ·
Committee · Network · Events · Grants · Roadmap · Outputs ·
Contact.*

**Wrong because**: *Outputs* is internal-EU-project jargon —
a journalist or external academic might not parse it as
"research publications". *Roadmap* is ambiguous (deliverable
timeline? upcoming events?). *Committee* could mean *MC* or
some other committee.

**Options**

- **A — Keep current labels.**
- **B — Rename selectively**: *Outputs* → *Publications*;
  *Committee* → *Leadership*; *Roadmap* → keep (it's a known
  term in EU-project contexts).
- **C — Group into dropdowns** (deferred to Phase 2).

**Recommendation:**

- *Outputs* → ***Publications***. Universal academic term;
  reads correctly for journalists too.
- *Committee* → ***Leadership***. The home-page section is
  literally headed *Action Leadership* + the MC roster; the
  label should match.
- *Roadmap* → keep.

**Cost:** 1 hour (label change + i18n re-stamp on EN/FR/DE).
**Risk:** none. Existing anchors (`#committee`, `#outputs`)
stay valid; only the visible label changes.

**Phase 1.** Slots into v1.5.0.

### Issue 6 · Nav grouping (flat vs. dropdowns) — *defer*

**Current.** Flat 10-item nav. At capacity.

**Why deferring to Phase 2**: dropdowns add UI complexity
(touch behaviour, keyboard accessibility, screen-reader
announcement, mobile-drawer interaction). They're worth
doing if the right grouping is clear, but the grouping isn't
obvious yet. Wait until Phase 2 with real Year-1 content +
optional UX consult.

**Phase 2.**

### Issue 7 · Section ordering for audience tracks — *defer*

**Current.** News, About, WGs, Committee, Events, Roadmap,
Outputs, *For members*, Contact.

**Why deferring**: deciding "Events before WGs" or "Network
before About" is the kind of question that benefits from real
audience signals (post-Conference traffic patterns, hallway
feedback from MC plenary attendees). Phase 2 has both.

**Phase 2.**

### Issue 8 · Mobile-specific treatment — *defer*

**Current.** Mobile gets the same DOM in mobile-friendly CSS.
Long scroll on phones.

**Why deferring**: the cheapest mobile wins (sticky TOC,
mobile-specific section reorder, condensed events list) need
real mobile-traffic data to prioritise. Phase 2 with
Lighthouse + Core Web Vitals baseline gives us that.

**Phase 2.**

---

## Phase 1 summary — what lands in v1.5.0

| Issue | Change | Cost |
|---|---|---|
| 1 | Hide home-page Outputs section; create empty `/outputs.html` for D6's future home | ½ day |
| 2 | Drop the *members' Wiki* card from *Find out more*; let *For NetSec members* strip own that signpost | ½ hour |
| 3 | Move the Gantt to `/roadmap.html`; nav item points there | ½ day |
| 4 | Cap news on home at 4; add `/news.html` archive with the rest | 1 day |
| 5 | *Outputs* → *Publications*; *Committee* → *Leadership* in nav | 1 hour |

**Total**: ~2 days of work. Lands in v1.5.0 alongside the
brand refresh.

## Phase 1 — what's *not* in scope

- Nav grouping (Issue 6): deferred to Phase 2.
- Section ordering (Issue 7): deferred to Phase 2.
- Mobile-specific treatment (Issue 8): deferred to Phase 2.
- Audience-track strips ("I'm a researcher / journalist /
  member"): considered, deferred to Phase 2 — needs more
  research before committing.

## Decisions I need from you

Six structural choices. None of them block the rest of v1.5
moving forward, so you can take these one at a time.

1. **Issue 1 — Hide Outputs section + create `/outputs.html`?**
   Yes / No / different option.
2. **Issue 2 — Drop members' Wiki card from *Find out more*?**
   Yes / No.
3. **Issue 3 — Move Roadmap Gantt to its own page?** Yes /
   No / collapse-by-default instead.
4. **Issue 4 — Cap news at 4 + archive page?** Yes / No /
   different cap (3? 6?).
5. **Issue 5 — Rename *Outputs* → *Publications* and
   *Committee* → *Leadership*?** Yes / No / different names.
6. **General**: any of the *defer-to-Phase-2* issues
   (6/7/8) you'd rather pull forward into v1.5?

When you've decided, I open one PR per accepted change (or
one big PR if you'd rather review together), and v1.5.0 ships
late June with the brand refresh and the IA quick-wins.

## What Phase 2 will cover

For completeness — so you know what's *not* in this audit:

- Nav grouping (flat vs. dropdowns) with audience-track
  considerations
- Section ordering rationale, with post-Conference traffic
  patterns informing the call
- Mobile-specific homepage treatment (TOC, condensed
  sections, gesture patterns)
- Audience-track strips or chooser
- Full content-lifecycle design for News + Events as they
  scale past ~10 entries each
- Visual hierarchy across the 8 remaining sections
- Future-proofing for D11 + D12 + the publications hub
- Optional: UI/UX consult (budget question already in the
  roadmap)

Phase 2 runs July–August; implementation lands in v1.7.0
(*Year 1 closes*, mid-October).
