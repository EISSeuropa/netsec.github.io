# Site-wide search — feasibility assessment

> *Audience: maintainers + the Action Chair, deciding whether to add
> a cross-page search to netsec-cost.eu and which implementation to
> pick.*

## Why this document exists

The site has grown from six pages (v1.1) to ten (v1.3). The FAQ
holds 21 Q&As, the Glossary ~35 terms, the Grants page documents
five schemes with eligibility detail, the Network directory holds
the bios of every MC member and WG participant. A visitor who
arrives knowing what they want — *"STSM eligibility for Switzerland"*,
*"what's a Grant Period"*, *"who chairs the European Security
Conference"* — currently has three options:

1. Use the top nav to guess the right page, then browser-Ctrl-F.
2. Use the Network directory's own search (only finds people).
3. Use an external search engine with `site:netsec-cost.eu`.

This document scopes a **site-wide search** as a possible new
feature: one input, queries across every page, results take the
visitor to the right place.

It does **not** recommend a build yet — that's a separate decision
to make after reading this. The PR that introduces this file leaves
no code shipped beyond the doc itself.

## Constraints

These shape the option space; any candidate that violates one is
ruled out.

- **No third-party trackers.** The site has no analytics, no
  cookies, no chat widget. Routing queries through an external
  service that logs them (Algolia, Google CSE, etc.) would violate
  the established privacy posture documented in `/privacy.html`.
- **Static GitHub Pages.** No server, no API. Anything dynamic has
  to be either build-time (a CI step that emits artefacts) or
  client-side JS reading those artefacts.
- **No existing build step.** Today every page is hand-authored
  HTML; CSS and JS load directly from `assets/`. Adding any build
  step is a real cost — pinned versions, CI minutes, a new failure
  mode in the deploy pipeline.
- **EN / FR / DE.** Whatever we ship has to handle three languages
  reasonably — at minimum, "search the active locale's pages
  only" or "search all locales with a hint per result".
- **Zero recurring cost.** No paid services, no API quotas.
- **Light + dark theme parity.** Whatever UI ships has to work
  in both themes without a separate stylesheet.
- **Accessibility.** WCAG 2.1 AA target: keyboard reachable, visible
  focus ring, screen-reader-announced results count, no colour-only
  signals.
- **No bloat.** Current site footprint is ~140 KB uncompressed.
  Adding more than ~50 KB on top would change the page-weight
  story we tell evaluators.

## What "site-wide search" means here

The shippable scope:

- **Cross-page text search.** Indexes the body content of every
  HTML page (headings, paragraphs, FAQ answers, glossary
  definitions, grant descriptions, news, events). Excludes the
  navigation chrome, footer, and theme-toggle markup.
- **Output:** ranked list of hits with: the page, the section
  (anchor-link), a snippet showing the matched phrase in context.
- **UI surface:** either a header chip / overlay (Algolia-style
  `Cmd-K`), a dedicated `/search.html` page, or both.
- **Excluded from scope:** bios.json (the directory has its own
  in-page filter); the members' Wiki (separate repo, no business
  being indexed by the public site); the documentation PDF
  (search-within-PDF is a built-in Reader function).

## Options evaluated

### 1 · Do nothing (browser-native)

Status quo: users Ctrl-F per page; the directory has its own
search.

**Pros**

- Zero code, zero maintenance, zero risk.

**Cons**

- Doesn't span pages. A user who doesn't know which page holds
  the answer has to guess.
- The FAQ and Glossary work hard to *be* the discovery surface,
  but only if the user lands on them first.

**Cost:** 0.

### 2 · Pagefind — recommended candidate

[Pagefind](https://pagefind.app/) is a build-time static-search
indexer purpose-built for the shape of site we have.

**How it works.** A Node CLI walks the built HTML, emits a
fragmented index under `/pagefind/`, and ships a tiny JS UI that
loads index shards on demand. The index is per-language (it reads
`<html lang>` on each page); the runtime auto-selects the active
language.

**Pros**

- **Same-origin only.** No third-party. Queries never leave the
  visitor's browser. Fits the privacy posture cleanly.
- **Multilingual out of the box.** EN/FR/DE indexed and served
  separately; per-locale stemming uses the right rules without us
  writing language code.
- **Tiny runtime.** ~80 KB minified + gzipped (or use the
  pre-built UI). Index shards are loaded on demand, so the cold
  cost of having search available is ~5 KB.
- **Accessibility designed in.** The built-in UI is keyboard
  navigable, announces result counts to screen readers, and has
  visible focus rings.
- **Light + dark theme.** Built-in UI honours `prefers-color-scheme`
  and exposes CSS variables to override.
- **Snippet highlighting.** Matches are surrounded with `<mark>`
  in the snippet, which we can style.
- **Section anchoring.** Each `<h2>` / `<h3>` becomes a sub-result
  so we link directly to the right place on the page (matters for
  long pages like FAQ and Glossary).
- **Reads `data-pagefind-*` attributes** so we can mark e.g.
  `nav.nav` and `footer.footer` as not-to-be-indexed without
  rewriting the HTML.
- **Compatible with GitHub Pages.** Runs in CI; commits the index
  back to the repo or to gh-pages.

**Cons**

- **Introduces a build step.** A new GitHub Action runs `npx
  pagefind` after each merge to `main` and either commits the
  index back or publishes to gh-pages. This is the one
  philosophical departure from the current "no build step"
  stance.
- **Pinned versions to maintain.** Pagefind is at v1.x; pin the
  Action to a major-version SHA, watch for security advisories.
- **CSS commitment.** We either accept the default-styled UI
  (clean, but not on-brand) or overlay our glass-card aesthetic
  on top of Pagefind's structure.

**Effort:** 1–2 days for first ship.
**Footprint:** ~30 KB JS runtime + ~80 KB index for our content
size, all loaded on demand after the first keystroke.

### 3 · Lunr.js — minimum-viable alternative

[Lunr](https://lunrjs.com/) is the oldest static-search library
for JS sites. We'd write a small Python or Node script that
walks the HTML, extracts text, and emits a JSON index; ship a
Lunr runtime that loads the index and answers queries.

**Pros**

- **Vanilla JS, well-known.** No new Node toolchain in CI — we
  could write the indexer in Python and add it next to
  `inject-seo.py`.
- **Tiny.** ~30 KB runtime + ~20–40 KB index for our size.

**Cons**

- **Per-language stemmers.** Need to load three (Lunr's EN
  default + the French and German add-ons). Bigger runtime cost
  than a single English-only stemmer.
- **We write the indexer.** Walks HTML, drops nav/footer, joins
  page text, emits JSON. ~200 lines of Python, maintained by us.
  Pagefind does this in a tool we don't own.
- **UI built from scratch.** Lunr ships no UI; we write the
  input, the results list, the highlighting, the keyboard
  navigation, the accessibility scaffolding.
- **No section anchoring out of the box.** We'd compute it
  ourselves in the indexer.

**Effort:** 2–3 days for first ship.
**Footprint:** ~60–80 KB total.

### 4 · MiniSearch

[MiniSearch](https://lucaong.github.io/minisearch/) is a younger,
smaller JS search library. Smaller than Lunr (~10 KB) but the
indexer + UI story is the same as Lunr — we write both.

**Pros / cons:** roughly Lunr's, smaller bundle, marginally
newer, smaller community.

**Effort:** 1–2 days. Comparable to Lunr; would be the pick if
Lunr were ruled out for size.

### 5 · DuckDuckGo `site:` redirect

The search input is just an HTML form that opens
`https://duckduckgo.com/?q=site%3Anetsec-cost.eu+QUERY` in a new
tab.

**Pros**

- **Zero code, zero hosting.** Half a day of work to wire up.

**Cons**

- **Leaves our site.** Visitor's session moves to DDG; results
  are DDG-styled, not ours.
- **Lag.** Hits DDG's web index, which crawls on its own
  cadence. New pages (e.g. an event news card we just added)
  may not show up for days.
- **DDG sees the query.** Even though they're privacy-friendly,
  it's still a third-party seeing visitor queries — uncomfortable
  with our "no third-party" stance.

**Anti-recommendation.** Only ship this if we want a search box
*today* and can't budget any build work; in that case, it's an
honest stopgap rather than the long-term answer.

### 6 · Algolia DocSearch

Algolia's free-for-open-source-docs offering. Run on the same
indexer that powers React's docs, Vite's docs, dozens of others.

**Pros**

- **Best in the industry.** Instant typeahead, weighting,
  analytics, suggestions.

**Cons**

- **Third-party tracker.** Algolia sees every keystroke a visitor
  types. Directly violates `/privacy.html` §"no third-party
  trackers".
- **Application + approval.** Free tier is for projects Algolia
  agrees to host; takes a few weeks; not guaranteed.
- **Accounts to maintain.** A new external dependency the next
  maintainer has to learn.

**Anti-recommendation.** Don't apply.

## Comparison matrix

| Option | First-ship | Maintenance | Footprint | Multilingual | Privacy |
|---|---|---|---|---|---|
| Browser-native | 0 | 0 | 0 KB | n/a | ✓ |
| **Pagefind** | **1–2 d** | **low** | **~80 KB** | **yes (built-in)** | **✓** |
| Lunr.js | 2–3 d | medium | ~80 KB | yes (manual) | ✓ |
| MiniSearch | 1–2 d | medium | ~50 KB | yes (manual) | ✓ |
| DDG redirect | ½ d | 0 | 0 KB | yes (DDG side) | ⚠ third-party |
| Algolia DocSearch | ½ d + approval | low | external | yes | ✗ third-party tracker |

## Recommendation

**Ship Pagefind**, behind a small spike to confirm the multilingual
shards and the accessibility of the custom-styled UI before we
commit. The deciding factors:

1. **It's the only candidate that gives us multilingual indexing
   without writing the indexer ourselves.**
2. The build-step cost — which is the only honest objection — is
   bounded: one GitHub Action, one pinned dependency, one config
   file at the repo root. Compared to the maintenance burden of a
   hand-authored Python indexer (Lunr / MiniSearch path), it's
   smaller in expectation over the four-year life of the Action.
3. Privacy posture stays intact: queries never leave the visitor's
   browser; the index is served from `netsec-cost.eu`.

**Decision points before building**

These are the choices that need a yes/no before a spike branch:

1. **UI surface — header chip or dedicated `/search.html`?**
   - Header chip with `Cmd/Ctrl-K` overlay is the modern pattern
     (Stripe, Vercel, MDN). Visible from every page.
   - A dedicated page is simpler (no overlay focus-management),
     less visible, easier to link to from the *Find out more*
     grid.
   - Could ship both; the overlay is reasonable to wire up later.
2. **Index scope — current locale only, or all three?**
   - Current locale only is the standard expectation: an EN
     visitor searches EN content.
   - All-three could surface FR/DE-only content for an EN
     visitor; useful for the Wiki-equivalent reference content
     where the FR/DE pages are sometimes the most recent.
3. **What to *not* index.**
   - Definitely exclude: `<nav>`, `<footer>`, the language
     switcher, the theme toggle, the social-icon row.
   - Probably exclude: the directory member cards on
     `/people.html` (they have their own search; including them
     would clutter the global results).
4. **Keyboard shortcut.** `Cmd/Ctrl-K`? `/`? Both?

## What this is *not*

To stay honest about scope:

- It is not a research assistant. No "ask in natural language,
  get a summary". This is term / phrase matching with snippets.
- It is not a member-search replacement. The directory's own
  filter is purpose-built for the bios shape (WG chips, country
  flag, MC vs non-MC); a generic search would lose that.
- It does not index the members' Wiki. The Wiki is a working
  space behind GitHub auth; public search would expose drafts
  and meeting notes that have no business on the public surface.

## If we don't build it

A defensible "no-build" answer exists: the site has invested
heavily in *signposting* (top nav, *Find out more* grid, footer
links, sitemap.html, FAQ + Glossary TOCs). For a ten-page site,
that signposting is doing most of the work search would do.
**Re-evaluate** when any of the following triggers fires:

- Member count past ~150 and the directory page becomes the
  primary navigation pattern.
- The FAQ exceeds ~30 entries (the TOC stops scanning at a
  glance).
- A second similar reference page joins FAQ + Glossary.
- A redesign breaks the discovery grid we have.

Until then, the cost-benefit on a build is ambiguous.

## Next steps if approved

1. Open a spike branch: install Pagefind locally, run it against
   the current site, look at the index size and the default UI
   quality.
2. Decide *UI surface* (overlay vs page).
3. Decide *index scope* (locale-scoped vs all).
4. Write the GitHub Action that runs Pagefind on push to `main`
   and commits the index back to the repo (or publishes to
   gh-pages).
5. Style the search UI in glass-card aesthetic; accessibility
   audit; light + dark theme parity.
6. Add to `sitemap.html`, footer, and the home-page *Find out
   more* grid.
7. Ship as a MINOR bump (v1.4.0).
