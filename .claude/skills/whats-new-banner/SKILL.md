---
name: whats-new-banner
description: "Discipline for the site-wide \"What's New\" announcement banner: when activating it is justified, when it is not, the cadence, and how to update it. Use when asked to activate, update, or retire the banner."
---

# 14. *What's New* banner: sparingly

The site has a small dismissible banner that appears at the top
of every page when `data/whats-new.json` carries `active: true`.
Visitors who dismiss it don't see it again unless the
maintainer publishes a new entry (each entry is keyed by a
`version` string the dismissal `localStorage` tracks).

The point of the banner is to surface things a returning visitor
would want to know about without scrolling. CHANGELOG and
roadmap pages are developer-facing; the banner is the only path
that reaches everyday visitors.

### When to activate it

The bar is high. Activate only for a release that introduces:

- A new section a returning visitor will want to see (founding
  contributors landing on `/about`, members directory rebooted,
  outputs page going live with real publications).
- A major new feature visible without scrolling (live ESSC
  programme going live, brand identity launching, sitewide
  search shipping).
- A content milestone tied to the Action's deliverables (D1
  ships, D6 ships, Year 1 retrospective lands).

### When NOT to activate it

The much longer list:

- Quality patches (the v1.8.1 / v1.10.0 cadence — visitors
  don't care which em-dashes got fixed).
- Structural refactors that don't change what visitors see
  (the v1.9.0 events-from-JSON refactor: visible to operators,
  invisible to visitors who weren't paying attention to drift).
- Release-infrastructure changes (CI tweaks, Dependabot, voice
  rules, milestone reshuffles).
- Copy edits, translation refreshes, accessibility passes.

### Cadence

**At most 3-4 activations per year.** Each on-state lasts
**4-6 weeks max** before the maintainer flips `active: false`
manually. Banner fatigue is the failure mode — visitors learn
to ignore it if it's always on, and the next genuine
announcement loses signal.

The maintainer flips `active` true → false directly in
`data/whats-new.json`. No automation. The friction is the
gate: if you can't be bothered to edit a JSON file, the
announcement isn't important enough.

### Implementation

- `data/whats-new.json` — source of truth. Schema in the
  `_documentation` block at the top of the file. `_example_active_state`
  shows a populated entry from the v1.8.0 brand-launch cycle as
  a template.
- `assets/js/site.js` — the banner-render IIFE at the bottom of
  the file. Reads the JSON, applies locale, handles dismissal,
  inserts at `body.firstChild`. Silent no-op on fetch error.
- `assets/css/site.css` — `.whats-new-banner` and friends, with
  a slide-in animation on mount and slide-out on dismiss.
- The banner is NOT part of any drift checker — there's nothing
  to keep in sync.
