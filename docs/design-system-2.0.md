# Design system 2.0

> *Audience: anyone changing the visual or interaction layer of the site.*

The NetSec site follows an **Apple-inspired glassmorphism** language on top of
EU/COST brand colours. The look should feel modern, trustworthy, and
Brussels-adjacent without being corporate.

All values below are defined once as CSS custom properties in
`assets/css/site.css` (`:root` + `:root.dark`). **Always reference the token,
never the raw hex.**

## Principles

1. **Restraint over decoration.** White space, generous line-height, and one
   strong colour beat busy gradients and animated icons.
2. **Glass cards as the unit of UI.** Almost every distinct piece of information
   is wrapped in a `.glass` card. They define hierarchy.
3. **Stroke icons for generic glyphs, brand icons for brands.** Lucide-style
   strokes for envelope/globe/etc; Simple Icons for ORCID, LinkedIn, X, Bluesky,
   Mastodon.
4. **Motion is a hint, not a feature.** Hover transforms ‚â§ 4 px, transitions
   ‚â§ 300 ms, no parallax or scroll-jacking.
5. **British English** copy throughout.
6. **Accessibility first.** Every interactive element is keyboard reachable,
   every colour pair meets WCAG 2.1 AA, every page passes the skip-link ‚Üí main
   flow.

## Colour tokens

Defined as CSS custom properties on `:root` and `:root.dark`.

| Token               | Light value                                                    | Used for                                                   |
| ------------------- | -------------------------------------------------------------- | ---------------------------------------------------------- |
| `--bg-0`            | `#f6f8fc`                                                      | Page background                                            |
| `--bg-1`            | `#eef2fb`                                                      | Slight elevation backdrop (used inside the ambience blobs) |
| `--ink`             | `#0b1220`                                                      | Headings, primary copy                                     |
| `--ink-2`           | `#2b3850`                                                      | Body copy, sub-headings                                    |
| `--muted`           | `#5a6679`                                                      | Captions, meta text, fineprint                             |
| `--line`            | `rgba(11,18,32,.08)`                                           | Dividers, card borders in low-emphasis contexts            |
| `--glass-bg`        | `rgba(255,255,255,.55)`                                        | Default glass card fill                                    |
| `--glass-bg-strong` | `rgba(255,255,255,.72)`                                        | Sticky nav, more opaque cards                              |
| `--glass-border`    | `rgba(255,255,255,.6)`                                         | Glass card border                                          |
| `--glass-shadow`    | `0 10px 40px rgba(20,35,80,.10), 0 1px 2px rgba(20,35,80,.06)` | Glass card shadow (rest)                                   |
| `--glass-shadow-hover` | `0 18px 50px rgba(20,35,80,.14)`                            | Glass card shadow (hover)                                  |
| `--accent`          | **`#003399`** (EU blue)                                        | Primary brand colour ‚Äî buttons, focus rings, accents       |
| `--accent-2`        | **`#0a84ff`** (Apple blue)                                     | Hyperlinks, secondary accent, the colour-split headline word |
| `--accent-glow`     | `rgba(10,132,255,.35)`                                         | Soft glow under hovered primary buttons                    |
| `--gold`            | `#ffcc00`                                                      | EU-stars yellow ‚Äî used sparingly                           |

### Working Group accents

The four Working Groups each own a colour (source: `data/brand.json`), used on
member-card `.wg-chip`s and WG-scoped surfaces.

| Token    | Value      | Working Group                    |
| -------- | ---------- | -------------------------------- |
| `--wg-1` | `#0a84ff`  | WG1 ‚Äî building the network       |
| `--wg-2` | `#10b981`  | WG2                              |
| `--wg-3` | `#8b5cf6`  | WG3                              |
| `--wg-4` | `#f59e0b`  | WG4 ‚Äî next generation            |

### Semantic aliases & focus

Prefer these role names in new work so a token retint propagates:
`--text-strong` / `--text-body` / `--text-muted` / `--text-link`,
`--surface-page` / `--surface-card` / `--surface-card-strong`,
`--border-card` / `--border-hairline`, and `--focus-ring`
(`0 0 0 3px rgba(10,132,255,.45)` ‚Äî the shared `:focus-visible` ring).

### Dark theme

The dark theme (`:root.dark`) inverts `--bg-*`, `--ink*`, `--line`, and
`--glass-*`, and ‚Äî unlike earlier guidance ‚Äî **brightens the brand accents for
contrast on dark surfaces**: `--accent` ‚Üí `#6ea1ff`, `--accent-2` ‚Üí `#82b7ff`,
with a matching `--accent-glow`. The FOUC-prevention script sets the theme
before first paint, so there is no toggle transition.

### Ambience

The signature backdrop is `.ambience`: the `--ambience` gradient
(`linear-gradient(180deg,#eef3fc,#f6f8fc 40%,#fcfaf5)` ‚Äî cool blue ‚Üí off-white ‚Üí
warm cream at the foot) with three large blurred **blobs** tinted `--blob-1`
`#9bb8ff`, `--blob-2` `#ffd9a8`, `--blob-3` `#cdb6ff`, drifting on a 22‚Äì34 s
loop. Pure decoration, `aria-hidden="true"`.

## Typography

- **Lexend** ‚Äî display + headings (`--font-display`), weights **300‚Äì700**,
  letter-spacing `-.02em` (`--ls-display`; big display `h1` tightens to
  `-.035em`, `--ls-h1`), line-height `1.15` (`--lh-tight`). High x-height,
  friendly, optimised for reading speed.
- **Inter** ‚Äî body + UI (`--font-body`), weights **300‚Äì800**, letter-spacing
  `-.005em` (`--ls-body`), line-height `1.55` (`--lh-body`).
- **Monospace** (`--font-mono` = `ui-monospace, 'SF Mono', Menlo, monospace`) ‚Äî
  eyebrows, dates, and meta lines (especially on the EISS √ó NetSec conference
  slides) and inline code, for a precise "programme-listing" feel.

Both webfonts are self-hosted as `assets/fonts/*.woff2` and preloaded in every
page's `<head>` (since v1.4.x, issue #121). There is no external Google Fonts
request.

### Type scale

Clamp-based, matching the live-site fluid sizes:

| Token         | Value                          | Used for                        |
| ------------- | ------------------------------ | ------------------------------- |
| `--fs-h1`     | `clamp(2.4rem,5.2vw,4.4rem)`   | One `h1` per page               |
| `--fs-h2`     | `clamp(1.8rem,3.2vw,2.6rem)`   | Major sections                  |
| `--fs-h3`     | `1.25rem`                      | Sub-sections, member names      |
| `--fs-h4`     | `1rem`                         | Card titles, country names      |
| `--fs-lede`   | `clamp(1.05rem,1.4vw,1.2rem)`  | Hero lede, section intros       |
| `--fs-body`   | `1rem`                         | Body copy                       |
| `--fs-sm`     | `.92rem`                       | UI labels, nav                  |
| `--fs-xs`     | `.82rem`                       | Chips, fineprint                |
| `--fs-eyebrow`| `.78rem`                       | Uppercase section label (tracking `--ls-eyebrow` `.14em`) |

Weight tokens: `--fw-light 300` ¬∑ `--fw-regular 400` ¬∑ `--fw-medium 500` ¬∑
`--fw-semibold 600` ¬∑ `--fw-bold 700` ¬∑ `--fw-heavy 800`.

Heading hierarchy across the site is currently:

| Level | Count      | Example                           |
| ----- | ---------- | --------------------------------- |
| `h1`  | 1 per page | "The Directory", "Grants & Calls" |
| `h2`  | 6‚Äì9        | Major sections                    |
| `h3`  | ~20        | Sub-sections, member names        |
| `h4`  | ~18        | Card titles, country names        |

Never skip a level (no `h2` ‚Üí `h4`).

**Colour-split headlines:** the key phrase flips to `--accent-2` mid-sentence ‚Äî
*"Networking **European security** knowledge"*, *"A directory you can
**actually search**"*.

## Spacing, radii & layout

**Spacing** is an 8-px-ish rhythm with a few in-between steps the site leans on:
`--space-1 4px`, `--space-2 8px`, `--space-3 12px`, `--space-4 14px`,
`--space-5 18px`, `--space-6 24px` (container gutter + glass-card padding),
`--space-8 32px`, `--space-10 40px`, `--space-12 48px` (section-head margin),
`--space-16 64px`, `--space-20 80px` (vertical section padding).

**Radii** are generous and consistent: `--radius 22px` (glass cards),
`--radius-nav 18px` (sticky nav), `--radius-sm 14px` (inner panels, inputs),
`--radius-btn 13px` (buttons), `--radius-xs 10px` (small controls, nav links),
and `--radius-pill 999px` (chips, eyebrows, tags).

**Layout:** content maxes at `--maxw 1180px` (nav `--maxw-nav 1200px`) with a
`--gutter 24px` side padding, and `--nav-offset 90px` scroll-padding under the
sticky nav. Grids use `auto-fill` / `minmax()` so they re-flow continuously ‚Äî
there is no fixed mobile breakpoint (soft shifts at < 880 px and < 600 px).

## Components

The site is built from a small kit of components in `assets/css/site.css`; each
has a leading comment block explaining intent. Use the existing classes ‚Äî don't
introduce parallel ones.

### `.glass` ‚Äî the workhorse card

```
<article class="glass" style="padding:24px">‚Ä¶</article>
```

Backdrop-filter blur, semi-transparent fill, soft shadow, slight lift on hover.
Used by news cards, member cards, country cards, grant cards, MC cards, resource
cards, the timeline cards, the join-the-network CTA, the contact form, and the
search toolbar. The `.glass-strong` variant swaps in `--glass-bg-strong` for the
sticky nav and emphasis cards.

### `.card-clickable` / `.card-stretch` ‚Äî whole-card click target

```
<article class="news-card glass card-clickable">
  <h3>‚Ä¶</h3>
  <p>‚Ä¶</p>
  <a class="card-stretch" href="grants.html">View grants &amp; apply ‚Üí</a>
</article>
```

Stretched-link pattern: add `.card-clickable` to a card and `.card-stretch` to
its single primary link. The link's `::before` overlays the whole card
(`position:absolute;inset:0`) so a click anywhere on the card follows that one
link, while the accessibility tree still exposes one concise link (the CTA
text), not the card's whole body.

Notes and constraints:

- The overlay uses `::before`, not `::after`: the global external-link arrow
  marker already owns `::after` on `target="_blank"` links.
- Any other interactive element in the card (a second link, a button) must stay
  clickable; the utility lifts `.card-clickable a:not(.card-stretch)` and
  `button` above the overlay with `z-index:2`.
- Apply only to cards with one navigation destination. Do **not** apply to cards
  that are already interactive (directory `.member-card` expand, ESSC popover
  cards) or that have no destination. Skip it on large cards that already carry a
  single prominent CTA button (the `/grants.html` grant cards).
- Tradeoff: the overlay sits above the card text, so click-drag text selection
  of the card body is impeded. Acceptable for promo-style cards.
- In use on: the homepage event and news cards (all three locales).

### `.btn`, `.btn-primary`, `.btn-ghost`

```
<a class="btn btn-primary" href="‚Ä¶">Discover the Action</a>
<a class="btn btn-ghost"    href="‚Ä¶">Join the network</a>
```

Primary = filled `--ink`, hover ‚Üí `--accent` + glow + 1 px lift. Ghost =
transparent with a border, hover ‚Üí slight lift + glass fill. Radius
`--radius-btn`.

### `.chip`, `.wg-chip`, `.grant-tag`

Small pill-shaped labels (`--radius-pill`):

- `.chip` ‚Äî neutral keyword pill in the hero
- `.wg-chip wg-1` ‚Ä¶ `wg-4` ‚Äî colour-coded Working Group chips (`--wg-1‚Ä¶4`) on
  member cards
- `.grant-tag` ‚Äî uppercase tag inside a grant card head

### `.eyebrow`

```
<span class="eyebrow">Directory</span>
<h1>The Directory</h1>
```

Small uppercase letter-spaced label (`--fs-eyebrow`, tracking `--ls-eyebrow`)
above an `h1` or `h2`. Conveys section context without competing for hierarchy.

### `.timeline` (grants page)

Vertical timeline with `counter-reset:step` numbering and a gradient rail. Each
`.timeline-item` becomes the next numbered node automatically.

### `.mc-stats`

Three-up snapshot grid on the About page (MC representatives, countries
represented, ~51 % women). One-column on phones. The first two numbers carry
`data-cost-stat="mc-count"` / `"country-count"` and are rewritten by
`sync-cost.py` from the cost.eu roster, so don't hand-edit them; only the
approximate gender figure is manual.

### `.country-grid` / `.country-card`

Responsive card grid showing the MC countries with FlagCDN flags. Hand-authored
(curated flags + deep-link ids) and drift-checked against the synced roster.

### Deliverables Gantt (`.gantt` / `.g-row` / `.milestone`)

The About-page deliverables chart. One CSS grid owns the 17 column tracks (label
+ 16 quarters) and every `.g-row` inherits them via
`grid-template-columns:subgrid` (an `@supports` fallback keeps per-row grids on
browsers without subgrid). Milestone pills read as `.milestone` (planned),
`.is-shipped` (delivered), `.is-early` (delivered ahead of plan, the only
green), and `.is-ghost` (the original planned month when a deliverable shipped
early). The roadmap's "show earlier releases" collapse is driven by
`assets/js/roadmap-shipped-toggle.js`.

### `.members-toolbar`, `.members-filter-chip`, `.members-country`

Toolbar at the top of `people.html`. Free-text search + WG/MC chips + country
`<select>`, all ANDed by the directory's render loop. It also carries the
view-mode toggle (`.view-toggle`, persisted in
`localStorage('netsec-directory-view')`), the `?` tour-trigger, and the accent
`+` join-trigger (`.tour-trigger-cta`) that scrolls to `#join`.

### `.member-card.is-expanded` (click-to-expand in compact mode)

In compact mode a single card may carry `.is-expanded`, reverting its
compact-mode overrides so it renders as a detailed card in place. Triggered by
card-body clicks, Enter/Space on a focused card, or a `#slug` hash. Esc or an
outside click collapses; the URL hash mirrors the expanded card's `data-slug`.
Long-term plan: a sticky side-panel pattern (Issue #72).

### `.essc-member-card` ‚Äî the shared member popover

A floating profile card built once in `assets/js/site.js` and exposed as
`window.netsecMemberCard` (`show(anchorEl, member, opts)` / `hide()`). A
top-layer `<div popover>` holding a member's photo, name, role and WG badges,
country, and a link to the full directory entry. Hover/focus a wired name to
open; light-dismisses on Esc, an outside click, or a meaningful scroll; flips
above the anchor near the viewport foot. The ESSC programme speaker links and
the Summer School page share this one component.

### `.founding-badge`

A quiet outlined pill on `/people.html` cards reading "Founding contributor" ‚Äî
transparent fill, muted border, small star glyph. Set from the
`founding_contributor` flag that `scripts/sync-bios.py` reads from
`data/founding-proposers.json` (see `docs/bios-setup.md`).

### `.ecs-faculty-grid` / `.ecs-faculty-card` (Summer School)

The Summer School faculty roster: a card per scholar with a `.mc-avatar`
monogram, name, affiliation, and an optional coordinator tag. For faculty who
are NetSec members, `site.js` swaps the monogram for the live directory headshot
and adds a profile link, resolved by name.

## Conference slide template (EISS √ó NetSec)

The 1280√ó720 conference deck (session-title, plenary / name-cards, thank-you /
CTA) extends the same tokens with a slide-specific treatment:

- **White solid cards** (no blur) where there is no backdrop to refract.
- **Monospace meta** (`--font-mono`) for eyebrows, dates, and
  `Date ¬∑ Time ¬∑ Venue` lines, often with a leading accent `‚óè` dot.
- A faint **48‚Äì54 px grid** over the ambience, with the blob tints pulled into
  the four corners (cool top-left, peach top-right, green/violet bottom).
- The Apple-ish *"‚Ä¶and one more thing"* closer, used once.

## Animations & motion tokens

One easing curve everywhere: `--ease` `cubic-bezier(.22,.61,.36,1)` (a gentle
Apple-ish overshoot), with durations `--dur-fast .2s`, `--dur .25s`,
`--dur-slow .35s`. Lifts are `--lift translateY(-4px)` (glass cards) and
`--lift-sm translateY(-1px)` (buttons).

- `.reveal` ‚Äî fades in + slides up 12 px when intersecting viewport. Default
  state is **visible**; the `js-reveal` class on `<html>` (added by `site.js`)
  opts in to the fade. If JS fails, content stays visible.
- `.blob` ‚Äî the three `.ambience` blobs, drifting on a 22‚Äì34 s loop
  (`transform: translate + scale`). `aria-hidden="true"`.
- Glass-card hovers ‚Äî `--dur-slow` `--lift` + shadow swap to
  `--glass-shadow-hover`.
- Theme toggle ‚Äî instant; no transition.

Backdrop blur is tokenised too: `--blur-glass saturate(160%) blur(18px)`
(cards), `--blur-nav saturate(180%) blur(20px)` (sticky nav),
`--blur-chip blur(12px)` (chips, ghost buttons).

## Iconography

Two SVG styles coexist by design:

| Style        | When to use                                                     | Source / template                                                          |
| ------------ | --------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Stroke       | Generic glyphs (envelope, globe, briefcase, microphone, etc.)   | Lucide-style: `stroke="currentColor"`, `stroke-width‚âà1.8‚Äì1.9`, `fill="none"` |
| Filled brand | Recognisable brand marks (ORCID, LinkedIn, X, Bluesky, Mastodon)| Simple Icons: `fill="currentColor"` (or brand colour via a dedicated class)  |

**ORCID specifically** is rendered in brand green via `.contact-orcid`; other
brand marks inherit `currentColor` so they pick up theme. Same-concept-same-icon
rule: every conference grant uses the same microphone; every contact-item uses
the same envelope. **No icon font** ‚Äî icons are inline SVG. Any `target="_blank"`
http(s) link gets a Lucide external-link mark appended via CSS mask, so never
type a trailing ‚Üí in link text. For new work, link Lucide from CDN.

### Roadmap feature chips (`rmi-*`)

The public roadmap (`roadmap.html` + FR + DE) badges its headline release cards
with a row of icon chips (`.rm-features`, issue #767). Icons are defined once per
page as a hidden inline `<svg><defs>` sprite of `<symbol id="rmi-*">` and
referenced via same-document `<use href="#rmi-‚Ä¶">` ‚Äî no extra request, no JS.

| Symbol id       | Concept                                               |
| --------------- | ----------------------------------------------------- |
| `rmi-people`    | Directory, people, membership                         |
| `rmi-search`    | Search                                                |
| `rmi-calendar`  | Events, calendars, conference pages                   |
| `rmi-broadcast` | Livestream, live programme, RSS, recaps               |
| `rmi-globe`     | Internationalisation, the three locales               |
| `rmi-palette`   | Brand, visual identity, Open Graph imagery            |
| `rmi-gauge`     | Performance                                           |
| `rmi-a11y`      | Accessibility                                         |
| `rmi-document`  | Outputs, PDFs, FAQ, About, deliverables               |
| `rmi-filter`    | Directory facets, filter chips                        |
| `rmi-graph`     | Network Map, statistics, retrospectives, milestone tracking |
| `rmi-school`    | Summer School, mentorship, glossary                   |

Chip rules: at most three chips per card, headline minor releases and planned
cards only, never on a patch release. The markup lives in a sibling
`<ul class="rm-features">` after the card `<p>`, never inside the `<h3>`/`<p>`
(`scripts/promote-roadmap.py` rewrites those at release time). New `rmi-*`
symbols follow the Lucide stroke style (`stroke-width="1.8"`).

## Brand assets

Official marks live under `assets/images/brand/` (shipped v1.8.0):

| Asset                       | Use                                                                      |
| --------------------------- | ------------------------------------------------------------------------ |
| `netsec-lockup-primary.png` | Default lockup, for light backgrounds.                                   |
| `netsec-lockup-white.png`   | Lockup for dark backgrounds.                                             |
| `netsec-lockup-mono.png`    | Single-colour lockup for print.                                          |
| `netsec-mark.png` (595√ó599) | The four-petal mark on its own ‚Äî avatars, favicons, tight spaces.        |

The header uses `*-nav` crops (light/dark swapped by `.dark`) and falls back to
`netsec-mark-nav.png` below 700 px. The favicon family and PWA
`manifest.webmanifest` derive from the mark; `android-chrome-512.png` doubles as
the `Organization.logo` in structured data. The pre-brand
`assets/images/logo.png` is a placeholder and must not be reintroduced.

One partner mark ships outside the NetSec set: `assets/images/eiss-logo.svg` is
the EISS lockup, embedded inline on `/summer-school.html` so its `currentColor`
wordmark follows the theme. It belongs to EISS, the Summer School co-organiser,
and must not be recoloured or redrawn.

This is only the developer index. The authority for the contractual rules (COST
and EU emblem pairing, clear-space, minimum sizes, colour swatches and type
specimens) is the public press kit at `press-kit.html`.

## Responsive breakpoints

| Breakpoint | What changes                                                                    |
| ---------- | ------------------------------------------------------------------------------- |
| < 880 px   | Mobile nav (menu-toggle), single-column hero, smaller paddings                  |
| < 600 px   | MC stats stack to one column, timeline node sizes shrink, country grid compacts |

There is **no fixed mobile breakpoint** ‚Äî most layouts use `auto-fill` /
`minmax()` grids so they re-flow continuously.

## Accessibility checklist for new work

- [ ] All interactive controls reachable with keyboard alone
- [ ] Visible focus ring (use the shared `--focus-ring` / `:focus-visible` style)
- [ ] `aria-label` on icon-only buttons; `title` for hover hint
- [ ] Heading levels follow the hierarchy table above
- [ ] Colour contrast meets WCAG 2.1 AA in **both** themes (check against
      `--ink`, `--ink-2`, `--muted`)
- [ ] No content hidden behind `:hover` alone
- [ ] Animations respect `prefers-reduced-motion` (see the `.reveal` fallback)
- [ ] Skip-link still focuses `#top` (home) or `#main` (other pages)

See `accessibility.html` for the live conformance statement.

