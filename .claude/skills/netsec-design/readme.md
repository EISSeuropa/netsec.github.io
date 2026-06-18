# NetSec Design System

**Networking European Security Knowledge (NetSec)** is a COST Action (European
Cooperation in Science & Technology) that fosters synergies across national and
local epistemic communities, bridges the academia–policy divide, and addresses
gender and generational imbalances in European security studies. Its work runs
across four Working Groups — from building the network to fostering the next
generation of scholars — through interdisciplinary research, annual conferences,
policy workshops, a mentorship programme, and a summer school. By connecting
academic, policy, and practitioner communities across the continent, NetSec
advances Europe's strategic autonomy in an increasingly complex global security
environment.

This design system captures the visual + interaction language of the NetSec
public site and its EISS × NetSec conference materials, so design agents can
build on-brand interfaces, slides, and assets.

---

## Sources

This system was reverse-engineered from the project's own code and brand kit.
The reader is encouraged to explore these further for higher-fidelity work:

- **Website + brand repo:** https://github.com/EISSeuropa/netsec.github.io
  - Authoritative design doc: `docs/design-system.md`
  - Tokens, components & full stylesheet: `assets/css/site.css`
  - Self-hosted webfonts: `assets/fonts/*.woff2`
  - Brand marks: `assets/images/brand/`
- **Partner / co-organiser:** EISS — European Initiative for Security Studies
  (https://github.com/EISSeuropa/EISSeuropa.github.io). The EISS lockup
  (`assets/images/eiss-logo.svg`) belongs to EISS and must not be recoloured or
  redrawn.
- **Indico integration (context only):** https://github.com/EISSeuropa/netsec-indico-dispatch
- Live site: https://netsec-cost.eu

Provided reference imagery (OpenGraph previews + EISS × NetSec conference
slides) lives in `uploads/`.

---

## Design language, in one line

**Apple-inspired glassmorphism over EU/COST brand colours** — modern,
trustworthy, and Brussels-adjacent without being corporate.

### Principles
1. **Restraint over decoration.** White space, generous line-height, and one
   strong colour beat busy gradients and animated icons.
2. **Glass cards as the unit of UI.** Almost every distinct piece of information
   is wrapped in a `.glass` card; they define hierarchy.
3. **Stroke icons for generic glyphs, brand icons for brands.**
4. **Motion is a hint, not a feature.** Hover transforms ≤ 4px, transitions
   ≤ 300ms, no parallax or scroll-jacking.
5. **British English** copy throughout.
6. **Accessibility first.** Keyboard-reachable, WCAG 2.1 AA in both themes.

---

## Content fundamentals

How NetSec writes:

- **Voice:** institutional but human; confident, plain, never breathless. It
  speaks as "we"/"the Action" and addresses the reader as "you" sparingly
  (mostly in CTAs: *"Before you go: join the NetSec Directory."*).
- **Spelling & grammar:** **British English** everywhere — "programme",
  "organised", "centre", "−" en-dashes in ranges ("16:40 – 17:55"),
  "academia–policy divide". A CI lint enforces this.
- **Casing:** sentence case for headings and body. **Eyebrows / meta lines are
  UPPERCASE** with wide letter-spacing ("COST ACTION · EUROPEAN COOPERATION IN
  SCIENCE & TECHNOLOGY"). Titles like "Dr", "Prof", "Mr" are kept.
- **Headlines split colour for emphasis:** the key phrase flips to accent blue
  mid-sentence — *"Networking **European security** knowledge"*, *"A directory
  you can **actually search**"*, *"Concluding Remarks **& Best Paper Prize**"*.
- **Numbers are concrete and earned:** "Filter **49 members** across **30
  countries**", "~51 % women", "Add your bio in ~2 minutes". No vanity stats.
- **Middots & bullets structure meta:** `Role · Institution`, `Date · Time ·
  Venue`, often with a leading `●` dot in accent.
- **Tone of CTAs:** action-first, no trailing arrows in link text (an external-
  link icon is auto-appended; a manual → is linted out). "Discover the Action",
  "Join the network", "Explore the directory".
- **Emoji:** not used in UI chrome. Country **flag emoji** appear only as data
  next to affiliations in the directory.
- **Punctuation flourish:** the Apple-ish *"…and one more thing"* shows up in
  conference closers — a knowing nod, used once.

---

## Visual foundations

**Colour.** Two blues do the work: `--accent` **#003399** (EU/COST blue —
buttons, focus, primary accents) and `--accent-2` **#0a84ff** (Apple blue —
links, the colour-split headline word). Ink is a near-black navy (`--ink`
#0b1220) over a cool off-white page (`--bg-0` #f6f8fc). `--gold` #ffcc00 is the
EU-stars yellow, used sparingly. The four **Working Groups** each own a colour:
WG1 blue #0a84ff, WG2 green #10b981, WG3 violet #8b5cf6, WG4 amber #f59e0b.
Imagery skews **cool** (blue/white) with **warm peach + soft green/violet**
accents bleeding in at the corners of slide backgrounds.

**Type.** **Lexend** for display + headings (weights 400–700, letter-spacing
−.02em, line-height 1.15 — friendly, high x-height). **Inter** for body + UI
(400–800, −.005em, line-height 1.55). A **monospace** stack
(`ui-monospace, 'SF Mono', Menlo`) carries eyebrows, dates, and meta lines —
especially on conference slides — giving a precise, "programme listing" feel.
Never skip a heading level.

**Backgrounds.** The signature backdrop is the **`.ambience`**: a soft vertical
gradient (cool blue → off-white → warm cream at the foot) with three large
blurred **blobs** drifting on a 22–34s loop (`aria-hidden`, pure decoration).
Conference slides add a faint **48–54px grid** and pull the blob tints into the
four corners (cool top-left, peach top-right, green/violet bottom). No photos in
chrome; headshots only in the directory.

**Glass.** The workhorse `--glass-bg` is `rgba(255,255,255,.55)` with
`backdrop-filter: saturate(160%) blur(18px)`, a `rgba(255,255,255,.6)` border,
and a soft blue-grey shadow (`0 10px 40px rgba(20,35,80,.10)`). A stronger
`.72` fill is used for the sticky nav and emphasis cards. White solid cards
(no blur) are used on slides where there's no backdrop to refract.

**Radii.** Generous and consistent: **22px** glass cards (`--radius`), 18px nav,
14px inner panels/inputs, 13px buttons, 10px small controls, and fully-rounded
**999px** pills (chips, eyebrows, tags).

**Shadows / elevation.** One soft, cool, blue-tinted family — `--shadow-md` at
rest, `--shadow-lg` on hover, and an `--accent-glow` halo under hovered primary
buttons. No hard or black drop-shadows.

**Motion.** One easing curve everywhere: `--ease` `cubic-bezier(.22,.61,.36,1)`
(an Apple-ish gentle overshoot). Glass cards lift **−4px** on hover (350ms);
buttons lift −1px (200ms). `.reveal` fades content in + up 12px on scroll, but
**defaults to visible** so a JS failure or reduced-motion never hides content.
No bounces, no parallax.

**Hover / press.** Links fade to 70% opacity. Primary buttons darken-to-accent +
glow + 1px lift. Ghost buttons gain the stronger glass fill. Nav links get a
5%-ink wash. Filter chips fill solid (ink, or their WG colour) when active.

**Borders.** Almost always 1px. Hairline dividers use `--line`
(`rgba(11,18,32,.08)`); card edges use the lighter `--glass-border`. No heavy
rules.

**Layout.** Content maxes at **1180px** (nav 1200px) with 24px gutters. Grids
use `auto-fill` / `minmax()` so they re-flow continuously — there is **no fixed
mobile breakpoint** (soft shifts at <880px and <600px). The nav floats as a
sticky glass bar 14px from the top.

---

## Iconography

- **Two SVG styles coexist by design.** Generic glyphs (envelope, globe,
  search, calendar, microphone) are **Lucide-style strokes**:
  `stroke="currentColor"`, `stroke-width≈1.8–1.9`, `fill="none"`. Brand marks
  (ORCID, LinkedIn, X, Bluesky, Mastodon) are **Simple Icons** filled glyphs,
  inheriting `currentColor` (ORCID is the exception — rendered brand-green).
- **Same-concept-same-icon:** every conference grant uses the same microphone;
  every contact uses the same envelope.
- **No icon font.** Icons are inline SVG. The roadmap page uses a hidden
  `<svg><defs>` sprite of `<symbol id="rmi-*">` referenced via `<use>`.
- **Auto external-link arrow:** any `target="_blank"` http(s) link gets a Lucide
  "external-link" mark appended via CSS mask — so never type a trailing → in
  link text.
- **No emoji as icons.** Country flag emoji appear only as directory data.
- For new work, **link Lucide from CDN** (matches the stroke style) rather than
  hand-drawing glyphs. Inline SVG with the stroke spec above is fine.

---

## File index

**Foundations / tokens**
- `styles.css` — the single entry point consumers link (manifest of `@import`s).
- `tokens/fonts.css` — `@font-face` for Inter & Lexend (self-hosted woff2).
- `tokens/colors.css` — colour custom properties + `.dark` theme + semantic aliases.
- `tokens/typography.css` — font families, scale, weights, line-height, tracking.
- `tokens/spacing.css` — spacing scale, radii, layout widths.
- `tokens/effects.css` — easing, blur, lift, shadows.
- `foundations/*.html` — specimen cards (Colors, Type, Spacing, Brand).

**Assets**
- `assets/fonts/` — Inter & Lexend woff2.
- `assets/images/brand/` — NetSec lockups (primary / white / mono / nav crops),
  the four-petal mark, favicon.
- `assets/images/` — EISS logo, COST logo, member headshots (`people/`).

**Components** (`window.NetSecDesignSystem_948961.*`)
- `components/buttons/` — **Button** (primary / ghost / accent · sm/md/lg).
- `components/surfaces/` — **GlassCard** (default / strong / hover).
- `components/labels/` — **Eyebrow**, **Chip**, **WGChip**, **Badge**.
- `components/media/` — **Avatar** (headshot or tinted monogram).
- `components/forms/` — **Input**, **FilterChip**.
- `components/directory/` — **MemberCard** (composite).

**UI kits**
- `ui_kits/website/` — interactive NetSec website: homepage hero + searchable,
  filterable people directory (`index.html`).
- `ui_kits/roadmap/` — public roadmap: status timeline (shipped / in-progress /
  planned / under-watch) with feature chips, progress bars, and Action
  milestones interleaved (`index.html`).
- `ui_kits/gantt/` — deliverables Gantt: the 16-quarter MoU deliverables chart
  (planned / delivered / ahead-of-plan, with the dotted early-delivery
  lead-line) on a subgrid column system (`index.html`).

**Slides** (`slides/*.html`, 1280×720)
- Session title, Plenary / name-cards, Thank-you / CTA — the EISS × NetSec
  conference slide template.

**Skill**
- `SKILL.md` — Agent-Skills-compatible entry point.

---

## Using the system

Link the tokens and read a component off the namespace:

```html
<link rel="stylesheet" href="styles.css">
<script src="_ds_bundle.js"></script>
<script type="text/babel">
  const { Button, GlassCard, MemberCard } = window.NetSecDesignSystem_948961;
</script>
```

Always reference tokens (`var(--accent)`), never raw hex. Wrap distinct blocks
in a `GlassCard`. Keep British English. Let the ambience + one strong blue do
the talking.
