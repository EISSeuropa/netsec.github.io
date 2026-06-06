# Changelog

All notable changes to this repository are recorded here.

This project follows [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html)
and the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.
What "MAJOR / MINOR / PATCH" means in the context of this repo is
spelt out in the **Versioning** section of [`README.md`](README.md).

The documentation pack (`docs/pdf/NetSec-website-documentation.pdf`)
carries its own version stamp on its cover and its own changelog
appendix; see Appendix C of that PDF for documentation-pack history.

## Release-notes format (applies to `[Unreleased]` + every `[X.Y.Z]` section)

Release notes here follow a **hybrid format**: a short prose lede,
two-to-five **themed sub-sections** carrying the actual narrative,
and a canonical **index of changes** at the bottom grouped by
Keep-a-Changelog categories. The themes are where the writing
happens; the index is the audit trail.

### Shape

```markdown
## [X.Y.Z] · YYYY-MM-DD — <short title>

> One- to three-sentence lede in voice. What is this release
> *about*? Who's it for? Why ship it now?

### <First theme — name it for the thing that changed>

Prose intro (~2-4 sentences). Inline links to docs / issues where
relevant. Add bullets only if the theme has multiple distinct
pieces; otherwise let the prose carry it.

### <Second theme>

Same shape.

### Index of changes

The themed sections above are the story; the index below is the
audit trail. Same content, terser.

#### Added
- (one-line pointer bullets — what, not why)

#### Changed
- Refreshed the public roadmap in all three locales to match the current milestones: v1.10.0 now reads as shipped, and the v1.10.1 card is dated 9 June and described by what it actually carries (the accessibility refresh, the social-media footer links, the directory Early Access banner, the About-page deliverable statuses, the Working Groups page sections, the FR/DE FAQ clarification, and the remaining cost.eu sync work) rather than a post-conference recap. The recap itself now sits under v1.11.0.
- (…)

#### Fixed
- (…)
```

### Rules

1. **Each release section has at most one `### Index of changes` block
   and at most one of each `#### Added` / `#### Changed` / `####
   Deprecated` / `#### Removed` / `#### Fixed` / `#### Security`
   sub-heading inside it**, in that order. When a PR adds an entry to
   `[Unreleased]`, the bullet goes inside the *existing* sub-heading
   — never in a new one with the same name below it.

2. **The lede + themes are written when the release is cut**, not
   accumulated bullet-by-bullet through the development cycle. The
   release-cutting moment is where the maintainer reads back through
   `[Unreleased]`, picks the 2-5 most coherent themes, drafts the
   lede, and weaves the bullets into prose sections.

3. **Self-policing tier**:
   - **Patch** (`1.x.y` with no headline) — skip the lede + themes.
     Index only. People reading patch notes care about specifics.
   - **Minor / major** (anything with at least one user-visible new
     feature) — full hybrid: lede + themes + index.
   - If you can't write a meaningful lede about a release, it's a
     patch. The format mirrors the actual significance.

4. **Within a theme**, order content by user impact: headline first,
   smaller polish after. Within the index, same ordering inside each
   `####` block.

5. **The release script (`scripts/release.sh`) extracts the
   `[Unreleased]` body verbatim** into the GitHub Release notes.
   Eyeball the body before confirming the script's prompt.

6. **No hard wraps in prose.** Each prose paragraph, blockquote lede,
   and multi-line bullet must be a single source line — do not break
   mid-sentence with a `\n`. GitHub Releases renders markdown with the
   *break-on-newline* GFM variant; every soft `\n` becomes a `<br>`
   and forces the prose to render narrow on the Releases page (even
   though it looks flowing on the `github.com` file view). One long
   line per paragraph keeps both renderings correct. Code fences,
   headings, blank lines, and the compare-link footer are unaffected.

v1.4.0 was the first release cut under this rule; v1.0.0 → v1.3.0 were
retrofitted to match. `docs/admin-guide.md` repeats this rule for the
maintainer-facing audience.

## [Unreleased]

#### Added

- New FAQ entry (all three locales) explaining why the directory intake runs on a Google Form rather than an open-source or European tool. It is honest about the trade-off (the tool is neither European nor open-source, and the sign-in asks something of researchers who would rather not hand Google a login) while laying out the practical reasons (spam barrier, an edit link, photo upload, and a spreadsheet the weekly sync reads with no server to run), and it points anyone who would rather not use the form to the contact form, noting the hand-entry delay.
- The directory's research-interest filter now clusters members by broad *research theme* instead of by individual keyword, in all three locales. Free-text keywords fragment (almost every one is unique, so a per-keyword filter rarely groups anyone); a curated set of eight themes (Foreign policy and diplomacy, Security and defence, Economic security and geoeconomics, Intelligence, information and influence, and so on, modelled on how peer bodies such as the EU Institute for Security Studies organise the field) groups related work so people in the same area surface together. Member cards still show each person's specific keyword pills; clicking a pill now selects that keyword's theme, and exact-keyword lookup stays available through the search box. The theme chips, their counts, and the URL hash (`#themes=…`) all follow; theme names are hand-translated for FR and DE.
- The directory (`/people.html`, all three locales) gains a second, geographic filter axis: research regions. Alongside the topical themes, a visitor can now narrow to people who work on a region (Europe, Europe - Western Balkans, Europe - Eastern neighbours / Russia, Middle East and North Africa, Africa, Asia, The Americas, or Global and cross-regional), and the two axes combine, so "cyber and Russia" is one query. Member cards carry their regions as clickable pills, and selecting one filters the grid. The eight-region vocabulary follows the EU Institute for Security Studies' lean regional taxonomy, kept short on purpose so members cluster rather than fragment. Like the mentorship facet, the region row stays hidden until at least one member opts in through a new optional form question, so nothing appears while the question is still being added. Region names are hand-translated for FR and DE. (Closes #555.)
- A second promotional poster on the press kit: a directory poster that invites scholars to add their bio, with the headline question, a QR code to the add-your-bio form, and the three reasons to join (be findable, connect across borders, mentor and be mentored). The press kit's poster section now holds both the general poster and the directory poster, each downloadable as a print file and a small preview, in all three locales. The directory poster ships as a print-ready PDF (vector) plus PNG renders.
- Directory and ESSC headshots now serve a WebP first, with the original JPEG or PNG kept as the fallback for browsers that need it, so photos download at roughly half the bytes with no visible change. The sync writes a `.webp` next to each headshot (both committed to the repository), and every place a photo appears (the directory cards, the ESSC speaker popovers, the About and Working Group leadership avatars) now wraps it in a `<picture>` element so the browser picks the format it supports. (Closes #269.)
- Shipped releases on the public roadmap now show how many tracked issues they closed, beside the release-notes link (a small "N tasks done" with a check mark). It reads the same per-milestone data the in-flight progress bars already use, and derives each card's version from its release-notes link, so every shipped release gets the tally with no per-card markup. The count is shown from v1.8.1 onward, the first release with full milestone tagging; earlier releases used milestones too lightly for the figure to be representative, so they omit it.
- The directory (`/people.html`, all three locales) can now surface mentorship. A member who offers mentoring shows a green *Available to mentor* badge on their card, and one looking for a mentor shows a *Seeking mentorship* badge. A new Mentorship filter sits alongside the Working Group and country filters, letting visitors narrow the directory to people offering or seeking mentorship. The badge and filter stay invisible until at least one member opts in through the form, so nothing appears while the question is still being added. (Tracked in #498.)
- New hand-designed social cards (the image that appears when a page is shared on LinkedIn, Bluesky, or anywhere reading Open Graph tags). The directory (`/people.html`, all locales) gets its own card showing the searchable directory; every other page uses a refreshed general card. `inject-seo.py` picks the right one per page, and the brand-asset script no longer regenerates the old auto-composed card over the top.
- The site footer now links the Action's two social channels, in every page and locale: LinkedIn (`costnetsec`) and Bluesky (`netsec-cost.eu`), alongside the existing repository link. They sit as small circular icon buttons in the footer's social row, the same place the placeholder links lived, so they stay out of the way of page content. The unused X / Twitter placeholder is gone. Both channels are also declared as the organisation's `sameAs` profiles in the home-page structured data, which helps search engines connect the site to the accounts.
- The directory (`/people.html`) now carries an Early Access Preview banner at the top, in all three locales, inviting visitors to contribute. The "adding your bio" link jumps straight to the join card at the foot of the page. The banner uses the same accent-gradient language as the What's New banner but sits in the page rather than as a dismissible top bar.
- The About-page deliverables timeline now shows which deliverables have shipped, not only what is planned, in all three locales. A shipped milestone gains a check mark, and one delivered ahead of plan shows in green with a faded marker left at its originally planned month and a dotted lead-line between the two. The first to land is the NetSec directory (D1). Each status carries a screen-reader description, so the meaning never rests on colour alone.
- Gave each Working Group on `/working-groups.html` two more sections, in all three locales: a *Working towards* list of the COST deliverables that group leads (with target months, each row linking to its entry in the About-page deliverables timeline) and a *Related publications* section. Publications are tagged by Working Group in a new `data/publications.json` and surface automatically as outputs land. Until the first ones arrive (October 2026), each group shows a short placeholder linking to the Publications page.

#### Changed

- Reworked the directory's filter card into two clear tiers, in all three locales. The primary row pairs the search box with a now-labelled Working-Group facet; below a divider, the mentorship, research-theme and research-region facets form a consistent second tier (mentorship moved down to join the themes and regions instead of floating between the rows). On desktop the applied filters now appear as a row of removable chips below the card, mirroring the mobile pattern, so the current selection and the per-filter remove sit together with the result count and the global Clear all.
- The directory's "Clear all filters" control now reads as an actionable link (a soft underline) when filters are active, rather than as static text.
- The directory's research-themes filter now carries a one-line explanation under its heading, in all three locales: themes automatically group people working in the same area based on their individual keywords, which stay visible on each card. It removes the apparent mismatch between the broad theme chips and the specific keyword pills on the cards.
- Tidied the directory's research-interest keywords. A standalone `&` in a keyword now reads as "and" (R&D and other acronyms are left intact), and two phrase-like entries were curated into tighter tags: *Policy evaluation & lessons learned (Afghanistan)* became *Policy evaluation*, and *Germany security policy* became the grammatical *German security policy*. The sync now also flags over-long or parenthetical keywords so they get curated rather than shipped as one-off tags.
- The directory's Join-the-Network card (and the matching guided-tour step) now say the bio form takes about 3 minutes rather than 5, in all three locales, to better reflect how long it actually takes.
- The directory's "First time here?" orientation card now includes the mentorship dimension, in all three locales: a new tip explains that a member's card can carry an *Available to mentor* or *Seeking mentorship* badge once they opt in, and that the directory can be filtered to either.
- The homepage event and news cards are now clickable across their whole surface, not just on the small link at the foot, matching how the homepage Working-Group cards already behave. (Grant cards keep their single prominent Apply button, since they are large and a whole-card target there would be easy to mis-click.) The card's existing link stays the one real link (so a screen reader still announces "View live programme", not the whole paragraph, and middle-click or open-in-new-tab keep working); a transparent overlay simply extends its hit area over the card. Cards that have no destination, or that already do something on click (the directory cards that expand, the conference speaker cards that open a profile), are deliberately left alone, and only cards that lead somewhere get the hover lift.
- Refreshed the promotional poster on the press kit with the new design: an eight-feature layout, the directory's running numbers, a searchable-directory mock, the four Working Groups with their leads, and the COST / EU funding strip at the foot. The source HTML, the print PNG, and the card PNG are all regenerated, and the download-size labels follow in all three locales.
- Clarified in the FAQ (all three locales) that the confirmation-email edit link can change text fields but cannot replace your photo, so a fresh form submission is the way to swap a headshot.
- Refreshed the accessibility statement (EN, FR, DE) to v1.3 for the 2 June 2026 re-assessment. It records the broader all-pages re-confirmation of WCAG 2.1 AA, corrects the now-resolved render-blocking-font note (the fonts are self-hosted), and bumps the version footer.
- Tagged three more events with their Working Groups, so they now show under the relevant sections on `/working-groups.html` and carry WG pills on the home Events cards: the NetSec ITC Conference (WG2, WG4), the MC Plenary (WG1) and the NetSec Policy Workshop (WG2).
- Swept prose semicolons out of every page in all three locales, rewriting them as full stops or commas to follow the house voice rules. The one semicolon in the ITC Conference calendar description got the same treatment.
- The public roadmap now shows only the most recent shipped release by default and tucks the earlier ones behind a "Show N earlier releases" toggle, so the shipped history no longer dominates the page as it grows. With JavaScript off, the full list stays visible.
- The roadmap's *In progress* dot now carries a steady accent halo for visitors who have reduced motion turned on, so the status still reads as live without the blink that reduced motion correctly suppresses.
- The directory got a filter rework, in all three locales. The research-themes and research-regions facets each became a compact collapsible row in the filter card (chevron, collapsed by default, opening automatically when a theme or region is selected from a card or a deep-link), while the mentorship row stays inline; the whole filter card was tightened so it leads with people rather than filter chrome. The result count ("N / M members") sits beside the "directory last updated" date just above the grid, after all the filters, with a global "Clear all filters" button on the right that stays in place, muted until a filter is active, so the number reflects what is on screen. The density toggle, guided tour and add-your-bio buttons live in a pinned bar at the corner of the directory, so they stay reachable while scrolling. The Working-Group, MC-members and country controls read with more contrast in light mode, as does the search box, whose placeholder is shortened so it no longer visually truncates; the research-regions heading carries a one-line note that it means where a member focuses their research, not where they are based. The guided-tour engine now scrolls each step into view, so the tour works correctly even when launched from the pinned tools bar after scrolling down, and its filter step covers both research themes and regions.
- On phones the directory filters now open in a bottom sheet, following the standard mobile pattern, so the member list leads instead of a screen of filter chrome. The toolbar collapses to a search field plus a **Filters** button badged with the number of active filters; tapping it slides up a sheet holding the working-group, research-theme, research-region and mentorship controls, with a **Reset** and a primary button that shows the live count ("Show N members") and closes the sheet. Active filters appear as a row of removable chips under the search, and the density toggle (which does nothing on a single-column grid) is hidden. The desktop layout is unchanged. All three locales.
- Dropped the directory's country dropdown (the free-text search already matches country) and moved the mentorship filter up into its place in the primary toolbar row, rendered inline rather than as a tinted band. The research-themes and research-regions facets now sit on their own below a divider, and the gap above them was trimmed. All three locales.
- The directory's card density now follows the viewport with a desktop opt-out. Phones always use compact cards (a single column of full photo-and-bio cards ran too long to scroll past); desktop defaults to detailed but keeps a density toggle in the pinned tools bar, and the choice persists in the browser. The toggle is hidden on phones, where the single-column grid makes it meaningless. All three locales.
- The directory's mentorship filter dropped its redundant "All" chip. "Available to mentor" and "Seeking mentorship" are now toggle chips, the same as the research-theme and research-region rows: tap to apply, tap again to clear, and select both to see everyone who has opted into mentoring either way. Neither selected means no mentorship filter, which is what "All" stood for. The global "Clear all filters" button and the removable filter chips still reset it. All three locales.
- Tightened the space above the directory's Early Access Preview banner on desktop and phones, and shortened the banner wording on phones so it sits on a couple of lines rather than filling the card. All three locales.

#### Fixed

- The directory's filter controls now meet the contrast bar in dark mode. The unselected Working-Group and mentorship chips, and the collapsed research-theme and research-region rows, carried borders too faint to see against the dark card (a 10% white edge); their boundaries are lifted to a visible level so each reads as a control. The selectable chip borders in light mode were nudged up to the same bar.
- The directory's guided tour now adapts to the viewport. On phones the filters live in a bottom sheet that is closed at tour time, so the steps pointing at each in-sheet facet were spotlighting an off-screen rectangle; the mobile tour now has a single step pointing at the Filters button that opens the sheet, while the desktop tour keeps a step per facet (and regains its card-density step). All three locales.
- The directory's "First time here?" orientation card no longer lists country as a filter dimension. The country dropdown was dropped earlier (the free-text search already matches country), but the tip still said "filter by working group, MC role, country, or mentorship status". All three locales.
- The mobile directory filter sheet no longer renders behind the member cards. The sheet is `position:fixed`, but the toolbar that wrapped it has a `backdrop-filter` (the glass blur), which establishes a containing block and stacking context for fixed descendants, so the sheet anchored to the toolbar and was trapped beneath later content. The sheet is now moved to `<body>` while open (escaping that context) and returned to the toolbar on close, with the toolbar's blur also dropped on mobile as a backstop. All three locales.
- The site's structured-data logo (the `Organization.logo` that Google and social crawlers read) now points at the official NetSec mark rather than a pre-brand placeholder. `scripts/inject-seo.py` had hardcoded the old `logo.png` from before the v1.8.0 brand launch, so every page emitted the placeholder; it now emits the real mark on all pages. Two stray EU-blue hexes in the stylesheet were also folded back onto the `--accent` token.
- The roadmap timeline markers (the status dots and milestone diamonds) now sit centred on the vertical connector line. The markers were vertically aligned to the status pill but their horizontal position never accounted for the line. The dots are content-box (the global box-sizing reset does not reach pseudo-elements), so their border sits outside the declared width, and the offsets are now computed from the rendered border-box centre at every breakpoint.
- Directory research keywords now keep country and region names capitalised wherever they sit in a phrase, not only as the first word. Previously the canonicaliser lowercased a proper noun in the middle of a keyword, so *Policy evaluation & lessons learned (Afghanistan)* rendered with a lowercase *afghanistan* and *Russia-Ukraine war* lost the capital on *Ukraine*. A curated list of countries and regions is now preserved through normalisation.
- Directory affiliations now read uniformly. The same employer was being written several ways depending on punctuation, so an institution and its named centre now use a comma (*ETH Zurich, Center for Security Studies*) and two separate affiliations use a slash (*Ghent University / Egmont Institute*), applied automatically on every sync.
- The Early Access Preview banner on the directory now keeps its white text readable in light mode. A global paragraph-colour rule was overriding the banner's intended white with a dark slate, which happened to read fine on the blue gradient in dark mode (where the same colour variable is light) but left dark-on-blue text in light mode.
- Stylesheet and script files now carry a content-hash cache-bust token (`site.css?v=…`), so a returning visitor renders new markup against the matching CSS rather than a stale cached copy after a release. A new check stops a CSS or JS change from merging without the hashes being refreshed.
- Gave the v1.10.0 roadmap card a proper description in all three locales. It had landed with the generic "maintenance release" auto-summary and an untranslated FR/DE body, which undersold a feature release.
- Clicking a Working Group card on the home page now lands on the exact section of `/working-groups.html`. The page builds its content from the directory after load, which shifted the target after the browser's initial jump, so the deep-link is re-applied once the section has rendered.

## [1.10.0] · 2026-05-31 — Working Groups page and milestone-aware roadmap

The headline this cycle is a dedicated Working Groups page: each of the four groups gets its own section with an objective, its leadership, and a live membership grid drawn straight from the COST directory, and the Action's Memorandum-of-Understanding titles are adopted across the whole site. The public roadmap learns to read its own GitHub milestones, showing a progress bar on every in-flight release and marking the next one as in progress on its own. Around those two sit a wave of conference run-up for the European Security Conference and the usual directory and data housekeeping.

### A home for the Working Groups

`/working-groups.html` (with hand-translated FR and DE) gives each Working Group an anchored section: the objective from the MoU, a row of focus areas, the lead and co-lead, and an expandable grid of every member with their country, all rendering at runtime from `data/wg.json`. That file is a new fourth surface the weekly cost.eu sync writes, so a leadership or membership change on the COST directory now flows through to the page, the home-page cards, the About leadership, and the directory filter with no hand-edit. The MoU titles (Building the Network, Transfer of Knowledge, Fostering the Next Generation of Scholars, and Inclusion, Representativeness & Ethics) replace the old working placeholders everywhere. Events and Working Groups cross-link both ways: the page lists the events a group runs, and each home-page Events card shows the groups its event serves.

### A milestone-aware roadmap

The public roadmap now reads the repository's own GitHub milestones. Each in-flight card shows a progress bar of issues closed over total, refreshed automatically whenever an issue or milestone changes, and the next incoming release marks itself as in progress with a softly blinking dot. The Under-watch section gained a count of what sits parked there. The milestone discipline that has always driven release planning behind the scenes finally has a visible public payoff.

### Conference run-up

With the European Security Conference approaching, the live ESSC programme and the FAQ both got attention. The programme now lists non-presenting co-authors alongside the speakers, carries a last-synced cue so a panelist who just edited Indico understands why the page is a day behind, and offers a one-click download of the official PDF (the browser print-to-PDF path had a chain of Chrome-specific truncation bugs, all now fixed). A new *At a NetSec conference* FAQ section, with matching signposts on the contact form and the programme page, answers the recurring questions about correcting your details, printing the programme, chairing a panel, and requesting a visa letter.

### Directory and plumbing

The weekly member-spotlight engine and its home-page block both landed dormant, waking once ten members are eligible. Directory keywords now fold American spellings to British English so a submitted *Defense* reads as *Defence*, the Working-Group filter follows a leadership change on cost.eu on its own, and a long-standing imprecision in where anchor links land under the floating header is fixed.

### Index of changes

#### Added

- **Related events on the Working Groups page.** An event in `data/events.json` can now carry a `workingGroups` array, and the Working Groups page renders a compact *Related events* card for each event tagged with that group. The NetSec Early-Career Scholars Summer School is tagged WG2, WG3, and WG4, and the European Security Conference is tagged across all four groups, so each event appears under the groups it serves with no duplication in the data. `assets/js/working-groups.js` fetches `events.json` alongside the WG data and fails soft if it is absent (the leadership and member render is unaffected). Cards localise the title, date, and event type EN/FR/DE, and a group with no tagged events shows nothing. While here, a `.prose-page a` underline that was bleeding onto the member and leadership cards was scoped out, so those cards read as tiles.
- **Working-Group pills on the home Events cards.** The reverse of that *Related events* block: each card in the home Events section now shows a small colour-coded pill for every Working Group the event serves, read from the same `workingGroups` tag, each linking to that group's section on the Working Groups page. So the Events ↔ Working Group relationship reads both ways (the Summer School shows WG2 / WG3 / WG4, the European Security Conference all four). Rendered by `assets/js/home-events.js`, EN/FR/DE, and an untagged event shows no pills.
- **Milestone progress bars on the public roadmap.** Each in-flight card on `/roadmap.html` (+ FR + DE) now shows a progress bar fed by its GitHub milestone, the closed-over-total issue count as a percentage (for example *29% · 2 of 7 tasks done*). `scripts/sync-roadmap-progress.py` writes `data/roadmap-progress.json` and a `roadmap-progress.yml` workflow refreshes it on every issue and milestone change (auto-PR, like the cost.eu and Indico syncs), so closing an issue moves the bar with no manual edit. `assets/js/roadmap-progress.js` renders the bar onto the card carrying the matching `data-milestone`, the fill follows the card's status colour, and the page fails soft when the JSON is absent. Shipped cards keep just their *Shipped* pill. The same renderer also marks the next incoming release (the first still-planned version card) as *In progress* automatically, with a slow-blinking status dot, so whichever release is next-up reads as active with no per-release edit (the static markup stays `planned`, so the release tooling is unaffected). The *Under watch* section heading also shows a small count of the items parked there. Localised EN/FR/DE and covered by `scripts/test-roadmap-progress.py`. This gives the milestone discipline of rule §10 a visible public payoff.
- **Dedicated Working Groups page (`/working-groups.html` + FR + DE).** Each of the four Working Groups gets its own anchored section with its objective (lifted from the Memorandum of Understanding), a row of focus areas each carrying a line icon, its lead and co-lead, and an expandable grid of every member. The page opens with an overall stats strip (people across the four groups, countries represented, and the group count), computed client-side from `data/wg.json` so it tracks the weekly sync. Every member card shows the member's country (a directory bio adds a photo and a link to their card). Leadership and membership render at runtime from `data/wg.json`, so a change on cost.eu flows through with no hand-edit, and the page fails soft to a static fallback. The global nav *Working Groups* link now points here instead of the home-page overview section, the four home-page Working Group tiles link through to their section, and the page joins the sitemap (XML, the visual `/sitemap.html`, all three locales). Closes [#378](https://github.com/EISSeuropa/netsec.github.io/issues/378).
- **Working Groups data layer (`data/wg.json`), synced from cost.eu.** The data half of [#378](https://github.com/EISSeuropa/netsec.github.io/issues/378). `scripts/sync-cost.py` writes a fourth surface: a per-WG dataset giving each of the four groups its lead and co-lead (read from each bio's `wg_leadership`) and every member of the group (name and country from cost.eu's Membership table, plus a directory `slug` for those who also have a bio). WG titles and the colour palette are config in the script, the file regenerates every weekly sync and is never hand-edited, so a leadership or membership change on cost.eu flows straight through. Covered by a new case in `scripts/test-sync-cost.py`.
- **ESSC programme now lists non-presenting co-authors alongside speakers.** Indico keeps presenters and co-authors in separate lists, and the live programme grid on `/essc-2026.html` (+ FR + DE) used to show only presenters, so multi-author papers under-listed their co-authors versus the printed programme. `scripts/sync-indico.py` now emits a full author byline per contribution (a `people` array with a `speaker` flag), and the renderer prints every author, marking presenters with a small microphone icon, shown only on papers that actually mix speakers and co-authors, so single-author talks stay clean. The microphone carries a localised *Speaker* / *Intervenant·e* / *Vortragende·r* label for assistive tech, and member-card links still resolve for co-authors who are NetSec members.
- **FAQ now answers the recurring conference-participation questions.** A new evergreen *At a NetSec conference* section on `/faq.html` (+ FR + DE) covers correcting your name, affiliation, or paper title on the programme; finding and printing the programme as a PDF; whether chairs can reorganise their own panel; and requesting a visa letter of invitation. The edit-my-details answer reflects how Indico actually works (it stores a per-event snapshot, so changing your personal profile does not update the programme; the paper title is self-editable on your contribution, while name and affiliation come to us or are fixed on the contribution's author entry). Recurring panelist requests can now self-serve or arrive complete and correctly addressed. `docs/admin-guide.md` gains the matching organiser-side setup (granting chairs session-coordinator rights each edition, and the document-generation route for invitation letters). First step of [#332](https://github.com/EISSeuropa/netsec.github.io/issues/332).
- **Self-service signposting on the contact form, the ESSC page, and the glossary.** The home-page contact form (EN + FR + DE) gains a short pre-submit signpost pointing the recurring conference questions (correcting your details, the printable programme, visa letters) at the new FAQ section, plus an optional topic dropdown so enquiries arrive categorised for triage (the existing Formspree handler captures it with no code change). The ESSC programme page carries a matching *Speakers & chairs* practical block linking through to the FAQ, and the glossary gains an *Indico* entry so the platform has a referent. Continues [#332](https://github.com/EISSeuropa/netsec.github.io/issues/332).
- **Last-synced cue on the ESSC programme.** The live grid now shows a localised *Programme updated &lt;date&gt;; refreshed from Indico daily, overnight* line under the heading, read from `indico.json`'s `syncedAt`. It heads off the "I edited Indico, why is the site still wrong?" email by making the once-daily sync lag visible: a panelist who just edited sees the page is dated before their change and knows to check the next morning. Date formats per locale (EN/FR/DE). Closes the on-page cue from [#332](https://github.com/EISSeuropa/netsec.github.io/issues/332); `docs/admin-guide.md` records that invitation letters use Indico document generation (signatory to confirm).
- **Directory join card now deep-links the FAQ.** The *Join the network* card on `/people.html` (+ FR + DE) points newcomers at the FAQ's *how to join* and *how to update your details later* answers, closing the one signposting gap a user-path simulation found: the network-candidate journey previously only reached the FAQ via the global nav, with no contextual link at the point of joining.
- **Weekly member spotlight, rotation engine (dormant for now).** Groundwork for a home-page block that showcases one network member each week (issue [#341](https://github.com/EISSeuropa/netsec.github.io/issues/341)). `scripts/rotate-spotlight.py` picks the week's member from `data/bios.json` using a balanced-rotation score: an early-career boost and a professor de-prioritisation inferred from the public job title, an Inclusiveness Target Country boost from `country_code`, and a Working-Group-balance boost, with recently-featured members held out and a `pinned` override for manual picks. Gender is deliberately not scored; the maintainer corrects any imbalance via the override. It stays **dormant until at least 10 members are eligible** (a member needs a photo and a written bio; the count is 4 today), so nothing renders yet. A weekly `spotlight-rotate.yml` workflow opens an auto-PR like the other syncs. Covered by `scripts/test-spotlight.py`.
- **Member spotlight documented as an inclusiveness feature.** The press kit (`/press-kit.html` + FR + DE) gains a short talking point framing the weekly spotlight as a concrete inclusiveness measure for early-career investigators, and the stakeholder documentation pack source (`docs/pdf/documentation.html`) gains user-facing and operator-facing feature-inventory entries with the same ECI framing. The built PDF refreshes at the v1.11.0 release per the usual cadence.
- **Weekly member spotlight, home-page block.** The renderer half of [#341](https://github.com/EISSeuropa/netsec.github.io/issues/341). `assets/js/home-spotlight.js` reads `data/spotlight.json` + `data/bios.json` and renders the featured member into a new section on the home page (EN/FR/DE), reusing the member-card visual language: photo or initials, name, role, country flag, Working-Group badges, research-interest chips, a clamped bio, and a *View full profile* link that deep-links the directory card. The block stays hidden while the spotlight is dormant (under 10 eligible) and self-heals if the featured member becomes ineligible, so it renders nothing today. `docs/admin-guide.md` documents the `pinned` manual override.
- **Download the ESSC programme as a PDF.** The programme page (`/essc-2026.html` + FR + DE) gains a *Download programme (PDF)* button above the day shortcuts, linking the official, tailored conference programme supplied by the EISS organisers (committed at `assets/programme/eiss-2026-programme.pdf`). It exists because Chrome's interactive *Save as PDF* truncates the long programme mid-document (a Chrome print-fragmentation defect, reproducible in the print preview itself; Safari prints the page fine). The button is localised EN/FR/DE and is hidden when the page itself is printed. The FAQ's *Where do I find a printable or PDF version?* answer now points at the download and records the Chrome limitation.

#### Changed

- **Working Group names now follow the Memorandum of Understanding everywhere.** The four groups are named *Building the Network*, *Transfer of Knowledge*, *Fostering the Next Generation of Scholars*, and *Inclusion, Representativeness & Ethics*, the authoritative titles from the MoU, replacing the earlier working placeholders (*Management & Coordination* and so on). Corrected on the home-page cards, the About leadership cards, the glossary, and the new Working Groups page, across all three locales. The home cards also pick up MoU-aligned descriptions and a network icon for WG1.
- **FAQ conference questions regrouped by who's asking.** In the *At a NetSec conference* section (EN + FR + DE), the *I'm chairing a panel* question now sits directly after *I'm speaking at a NetSec conference*, so the two participant-role questions are adjacent, with the general logistics (printable programme, visa letter) after them. Content unchanged, order only.
- **ESSC self-edit guidance now links straight into Indico.** A second live test confirmed a plain speaker (with an Indico account) can edit their own contribution, so the FAQ *edit-my-details* answer (EN + FR + DE) now leads with the self-edit route, deep-links *My Contributions* (`event/22/contributions/mine`), and spells out the small-pencil path for changing a name or affiliation. The *chairing-a-panel* answer deep-links *My Sessions* (`event/22/sessions/mine`). `docs/admin-guide.md` records the `event/<id>/{contributions,sessions}/mine` link format and that it is per-edition. Follows [#332](https://github.com/EISSeuropa/netsec.github.io/issues/332).
- **ESSC self-service guidance now matches how Indico actually behaves.** A permission test on the live event settled the open question: once a paper is accepted the *Call for Abstracts* pencil greys out (the abstract is locked), but a **panel chair granted modification rights can edit every talk in their session** (title, speakers, and author affiliations), verified by logging in as a chair. The FAQ *edit-my-details* and *chairing-a-panel* answers (EN + FR + DE) now lead with the chair route, explain the greyed-pencil as expected, and frame author self-edit (via *My Contributions*) as a conditional convenience. `docs/admin-guide.md` records the exact organiser settings (bulk *Grant modification rights to all session conveners*, plus optional submitter *Edit (basic)* + submission rights) and the two limits (locked abstract, account-less authors). Settles the Indico-permission prerequisite of [#332](https://github.com/EISSeuropa/netsec.github.io/issues/332).
- **FAQ copy edit: voice-rule sweep across all three locales, a removed entry, and a clearer photo-update answer.** The prose semicolons on `/faq.html` were rewritten as full stops or commas per the voice rules, and the same sweep now covers `faq.fr.html` and `faq.de.html`, where semicolons are uncommon too. The *Why is the site so minimalist?* entry was removed. The *How do I update my bio, photo, or affiliation later?* answer now explains that changing your photo uses the same Google Form as everything else (there is no separate headshot form), and reassures members that resubmitting keeps their existing data and only needs the required fields.
- **Directory join card trimmed.** The *No form configured yet? Get in touch* line was removed from the *Join the network* card on `/people.html` (+ FR + DE). The FAQ deep-link line stays.
- **Roadmap promotion now derives shipped cards from `CHANGELOG.md` and relocates them by ship date.** `scripts/promote-roadmap.py` (run by `scripts/release.sh`) used to flip only the status pill, date, and notes link, leaving the planned card's hand-authored `<h3>` + `<p>` describing *planned* scope rather than what shipped, and leaving the card in its original quarter even when the release crossed a quarter boundary. It now overwrites the title + body from the released CHANGELOG section's heading and lede, and moves the card into the `QN` / `TN` timeline matching the ship date. FR + DE card bodies get the EN copy plus a `[à traduire]` / `[zu übersetzen]` marker so `check-i18n-drift.py` flags them for a hand translation. The old git-blame staleness warning (which fired only after the wrong body had already shipped) is removed. Closes [#233](https://github.com/EISSeuropa/netsec.github.io/issues/233).
- **Directory keyword normalisation now folds American spellings to British English.** `data/keyword-aliases.json` gains a `spelling` section (a word-level US-to-British map) and `scripts/sync-bios.py` applies it during the keyword word-walk, so a submitted *Defense* renders as *Defence* on the member card and in the *Research interests* filter, with compounds like *Cyber defense* normalising too. Our first external directory submitter (Mr Felix Kösterke) had entered *Defense*; this folds the display form without rewriting his raw submission. The map covers common security and political-science cases (offence, behaviour, organisation, securitisation, modelling, neighbourhood, and similar); `program` is left alone since it is valid British English in the computing sense.

#### Fixed

- **Working Groups page visual polish.** The Working-Group tag in each section header was carrying a phantom 8px bottom margin and the heading a `.prose-page h2` top margin, which knocked the tag out of vertical alignment with the title and left a large gap above each heading; both are now reset so the tag sits centred on the heading and the sections read tighter. The four jump-nav pills at the top lost their stray underline (the `.prose-page a` tie-break again) and gained a proper interactive treatment: a heavier label, a lift on hover, and a border that picks up that group's colour. Across all three locales.
- **Header-anchor links now land precisely under the floating nav.** The nav is `position: fixed` and its height shifts with the beta ribbon and the What's-New / event banner, so the old static `scroll-padding-top` left section headings tucked under it (the symptom: clicking *Events* in the header sometimes overshot the Events section, the more so once the home page's events and spotlight blocks rendered in after load). `assets/js/site.js` now measures the real header bottom and keeps `scroll-padding-top` in step (watching the ribbon/banner CSS vars), which governs native `#hash` landings and cross-page links. It also intercepts header and jump-nav links that resolve to the current page and scrolls to them in-page, so on the home page a `index.html#events` link no longer triggers a reload + native jump. The `.wg-section` scroll-margin that double-counted with the new offset was removed, and the in-page scroll honours `prefers-reduced-motion`.
- **Directory WG filter now follows a leadership change on cost.eu.** The per-bio `wg_leadership` object in `data/bios.json` (which the `/people.html` Working Group filter reads to place a lead or co-lead under their group) was hand-seeded and never reconciled by any sync. When a WG lead or co-lead changed on cost.eu, `apply_leadership()` in `scripts/sync-cost.py` updated only the flat `roles` array on the new holder and left `wg_leadership` pointing at the previous one, so the directory would have shown the wrong co-lead under that group until someone hand-edited the file. `apply_leadership()` now derives `wg_leadership` from each member's reconciled leadership roles every run, so a change propagates to the new holder and clears from the old one with no manual edit. Idempotent on the current data (no spurious rewrites) and covered by a new case in `scripts/test-sync-cost.py`.
- **Printing the ESSC programme now shows every panel and drops the abstracts.** Saving `/essc-2026.html` (+ FR + DE) to PDF used to print inconsistently: each session's paper line-up sits in a collapsed `<details>`, and the print engine only kept open the panels a reader had expanded on screen, so most sessions printed as a bare *N contributions* line. A `beforeprint` hook now opens every contributions panel before the print dialog renders and restores the on-screen state afterwards, so the printed programme always carries the full line-up of session, chairs, paper titles, and speakers. The full abstracts are now hidden on paper (a printed programme is a line-up, not a book of abstracts), and the trailing Indico URL that the print stylesheet appended after every session and paper title is suppressed on the programme, removing the per-card page breaks the long URLs were forcing.
- **Printed ESSC programme no longer truncates mid-document.** With every panel force-opened, a session could exceed a page, and Chrome's print engine cannot fragment a tall CSS-grid (or flex) item across a page boundary: it silently dropped every page after the first overflowing row, stopping the PDF at the start of Day 2. The print layout now flows the programme rows as ordinary block boxes instead of grid, lets a long session break between contributions (each paper stays intact), and stacks parallel sessions vertically (each already shows its room badge). A headless print-to-PDF of the live Indico data now renders the whole programme end to end rather than halting partway.
- **Printed ESSC programme footer no longer truncates the document at all.** Even after the block-flow fix, the interactive *Save as PDF* still stopped mid-page (the PDF ended at *Page 7 of 13* with the rest of Day 2 missing), while headless print-to-PDF rendered the whole thing, which hid the fault from the automated check. The cause was the `counter(pages)` total in the running footer (*Page N of M*): resolving *M* forces the print engine into a second, whole-document layout pass, and Chrome's interactive print truncates long programmes during that pass. The footer now shows the page number without the total (*Page N*) in all three locales, removing the second pass. The block-flow pagination and the per-paper unbreakable units stay; a redundant `break-after: avoid` chain on the session header was also dropped to keep the constraint set minimal.

## [1.9.0] · 2026-05-29 — Per-event calendar downloads and a news RSS feed

> The pre-Stockholm cut, four days before the Summer School and European Security Conference open at Stockholm University. Visitors who land on the home page in the run-up to the conference get a calendar-savvy events block (per-card *Add to calendar* dropdown, every event downloadable as a single `.ics`), an RSS feed for the news block, and home-page cards that no longer drift between locales because they all derive from JSON. Three themes below; a single canonical index at the bottom.

### Calendar plumbing

The website has shipped a single `calendar.ics` subscribable feed since v1.3.0. v1.9.0 keeps that, and adds one `.ics` per event under `/calendar/<slug>.ics`. Slugs derive from each event's UID (`summer-school-2026@netsec-cost.eu` → `/calendar/summer-school-2026.ics`); `scripts/build-calendar.py` refuses non-conforming slugs at generation time so URLs stay predictable, removing an event from JSON auto-deletes its `.ics`, and the existing `calendar-drift` CI workflow now watches `calendar/**` too.

Every event card on the home page carries a new *Add to calendar* dropdown with four destinations: Google Calendar (prefilled template), Outlook web compose, Apple `webcal://` subscription, and direct `.ics` download. The menu reparents itself to `<body>` on first open and pins with `position: fixed` against the trigger's bounding rect, so it escapes the stacking context that `.event-card` creates via `backdrop-filter` — otherwise the menu was occluded by the next card down. Same portal pattern as the ESSC member-preview popover; the decision is logged on the Wiki *Decisions* page.

### Home page derives from data

Both the events block and the news block on `index.html` (+ FR + DE) now render at runtime from JSON. `data/events.json` and a new `data/news.json` are the source of truth; the renderers in `assets/js/home-events.js` and `assets/js/home-news.js` pick the locale from `<html lang>`, sort items, and rebuild the relevant `<div>`. The pre-existing hand-coded HTML survives as a fail-soft fallback that the renderer empties on success — so a fetch failure leaves visitors with a coherent page rather than an empty section. Card descriptions get a **five-line clamp with a *Read more* / *Lire la suite* / *Mehr anzeigen* toggle** that's only injected when the rendered text actually overflows; `@media print` drops the clamp.

This closes [#249](https://github.com/EISSeuropa/netsec.github.io/issues/249) and the drift class it tracked. The home-page event cards used to be hand-authored across three locales and could drift from the calendar feed; PR #248 had to paper over an "Applications now open" CTA that was already past its closing deadline. From v1.9.0 onwards, both lists share the same source of truth as the public `/calendar.ics` and `/news.xml` feeds. The Indico-write tooling continues to overwrite `summary` / `start` / `end` per `indicoEventId`; the renderer prefers `cardTitle.{locale}` over `summary` so localised home-page titles aren't affected.

### News on the open web

`/news.xml` is a new RSS 2.0 feed exposing the home-page news cards to feed readers (Feedly, Inoreader, NetNewsWire, Reeder). `scripts/build-news-rss.py` generates it from `data/news.json` with `<atom:link rel="self">`, CDATA-wrapped descriptions, RFC 822 `pubDate`, and `guid isPermaLink="false"`. A new `news-drift` CI workflow runs `--check` on every PR touching the data or the generator, mirroring the `calendar-drift` shape.

Every home page carries `<link rel="alternate" type="application/rss+xml">` in `<head>` so feed readers auto-discover the feed without the visitor needing to know the URL; a visible *Subscribe to NetSec news (RSS)* affordance under the news block (mirroring the existing calendar-subscribe block) covers visitors who don't read `<head>`. Single-language EN by RSS convention — per-locale feeds (`/news.fr.xml`, `/news.de.xml`) are a deferred follow-up if reader demand surfaces.

### Index of changes

#### Added

- **Per-event `.ics` downloads at `/calendar/<slug>.ics`.** `scripts/build-calendar.py` now writes one `.ics` per event in `data/events.json`, in addition to the existing aggregate `/calendar.ics` subscribable feed. Slug derives from the event's UID (`summer-school-2026@netsec-cost.eu` → `/calendar/summer-school-2026.ics`); the script refuses non-conforming slugs (`^[a-z0-9-]+$`) at generation time so URLs stay predictable. The per-event files carry the same VTIMEZONE block as the aggregate but no `REFRESH-INTERVAL` / `X-PUBLISHED-TTL` since they're one-shot import downloads, not subscribable feeds. Removing an event from JSON auto-deletes the matching `/calendar/*.ics`; the existing `calendar-drift` CI workflow now watches `calendar/**` too and fails the build if any output is stale. [#257](https://github.com/EISSeuropa/netsec.github.io/pull/257).
- **Home-page event cards now derive from `data/events.json`** (closes [#249](https://github.com/EISSeuropa/netsec.github.io/issues/249) renderer half). New `assets/js/home-events.js` reads the events JSON on `DOMContentLoaded`, picks the locale from `<html lang>`, and rebuilds the `#events .event-list` cards from structured data. Schema extends each event with `eventType`, `featured`, `displayDate`, `cardTitle`, `cardDescription`, `meta[]`, and `cta` — all with `{en, fr, de}` blocks where appropriate. The pre-existing hand-coded HTML survives as a fail-soft fallback. Card descriptions get a **five-line clamp with a *Read more* / *Lire la suite* / *Mehr anzeigen* toggle** injected only when the rendered text overflows; `@media print` drops the clamp. Each card carries an **Add to calendar dropdown** with four destinations: Google Calendar (prefilled template), Outlook web compose deep-link, Apple `webcal://` subscription, and direct `.ics` download from the per-event files. Outside-click + Escape dismiss the menu. The renderer prefers `cardTitle.{locale}` over `summary` so the Indico sync (which overwrites `summary` via `indicoEventId`) doesn't bleed into the localised home-page titles. [#259](https://github.com/EISSeuropa/netsec.github.io/pull/259).
- **News RSS feed at `/news.xml` + structured news data layer.** New `data/news.json` is the source of truth for both the home-page news cards and the public RSS feed. Schema mirrors `data/events.json` per item. `scripts/build-news-rss.py` generates `news.xml` in RSS 2.0 format with `<atom:link rel="self">`, per-item CDATA-wrapped descriptions, `guid isPermaLink="false"`, and RFC 822 `pubDate`. Single-language EN per RSS convention; FR / DE feeds deferred. The matching `news-drift.yml` CI workflow mirrors `calendar-drift`. `assets/js/home-news.js` reads the JSON on `DOMContentLoaded`, picks the locale, sorts newest-first, and rebuilds `#news .news-list`; hand-coded HTML survives as fail-soft fallback. Every home page now carries `<link rel="alternate" type="application/rss+xml">` in `<head>` for feed-reader auto-discovery. [#261](https://github.com/EISSeuropa/netsec.github.io/pull/261).
- **Visible *Subscribe to NetSec news (RSS)* affordance** under the news block on the home page (EN / FR / DE), mirroring the existing *Subscribe to NetSec events* calendar affordance. Hint sentence names three popular readers (Feedly, Inoreader, NetNewsWire) so non-technical visitors recognise the use case. [#263](https://github.com/EISSeuropa/netsec.github.io/pull/263).
- **Visual sitemap entries** for `/news.xml` and `/calendar.ics` in `sitemap.html` (+ FR + DE). The Home sub-tree now reads *News & announcements · RSS feed* and *Events · calendar.ics*. The machine-readable `sitemap.xml` is unchanged: RSS feeds and `.ics` files aren't pages and don't belong in `<urlset>`. [#264](https://github.com/EISSeuropa/netsec.github.io/pull/264).
- **Directory freshness line on *The Network*.** `/people.html` (+ FR + DE) now shows a discreet *Directory last updated <date>* line under the page lede, driven by `data/bios.json`'s top-level `generated_at` stamp. The stamp only moves when `scripts/sync-bios.py` produces a substantive change, so the date stays honest across weeks with no new submissions. Locale-aware date formatting (`en-GB` / `fr-FR` / `de-DE`) and a manually translated label; `docs/bios-setup.md` now documents the field. Closes [#271](https://github.com/EISSeuropa/netsec.github.io/issues/271).

#### Fixed

- **Add-to-calendar URLs now resolve the event's real UTC offset year-round.** `assets/js/home-events.js` hard-coded `+02:00` when building the Google Calendar and Outlook compose URLs. That matches Stockholm summer time but lands an hour off for any event in winter (CET, `+01:00`) or in a different zone. The two URL builders now resolve the offset for each event's wall-clock time via `Intl.DateTimeFormat`, lifting the zone from `data/events.json` (top-level `tzid`, with an optional per-event `tzid` override). The `.ics` downloads were always correct (they carry a VTIMEZONE block), so only the inline URLs changed. Closes [#260](https://github.com/EISSeuropa/netsec.github.io/issues/260).
- **404-page broken-star fragments now stream on a wind.** The loose pieces of the emblem (the cluster of yellow circles where three stars are missing from the top of the ring) used to bob straight up and down on a quiet `err-illu-drift` loop. They now blow left to right: each fragment enters from down-and-left, lifts up and across the canvas, then fades, as if a wind is carrying the broken pieces off the page. Per-fragment animation delays spread the cluster across the cycle so the motion never stalls, and a new `--frag-peak` custom property (set inline on each circle, matched to its `opacity` attribute) carries the resting opacity through the keyframes so the depth of the original cloud survives. `prefers-reduced-motion` falls back to the static attribute opacity with no transform.
- **404-page polish, sixth pass: the locale-row gap finally takes, map fills the card.** The button-to-locale gap had been bumped four times (28 px through 80 px across PRs #289, #293, #295, #299) with no visible effect, because the rule never applied: `.err-lang` is a paragraph and the earlier `.err-page p { margin: 0 0 24px }` has higher specificity (0,1,1 against the bare class's 0,1,0), so it reset `margin-top` to 0 every render. Qualifying the selector as `.err-page .err-lang` (0,2,0) wins the cascade, and a measured 48 px now sits the locale row clearly below the buttons. Separately the map cap went from 460 px to 520 px: the card's content box is about 488 px wide, so a cap above that lets `width: 100%` fill it edge to edge and the continent reads at full width rather than slightly pinched.
- **404-page polish, fifth pass: wider Europe map, more air below the buttons.** The map was capped at 340 px, which read as pinched in the 560 px glass card next to the EISS reference (which renders the same 10:7 outline at 48 rem). Bumped the cap to 460 px so the continent nearly fills the card's content width. The gap between the action buttons and the locale row went from 56 px to 80 px, the third adjustment on this spacing across review rounds.
- **404-page polish, fourth pass: real Europe map backdrop, more of the star ring broken, wider locale-row gap.** The third pass (PR #293) dropped the abstract continent shape because four overlapping ellipses read as a flying-saucer disc rather than as Europe. This pass imports the same Natural Earth 110m admin-0 Europe outline the EISS site uses behind its conference map (`src/_includes/europe-outline.njk`, 36 country paths, `viewBox 0 0 1000 700`), rendered at the full SVG canvas as a faint backdrop (light fill in light mode, muted navy in dark mode via the site's `.dark` ancestor convention). At full-canvas scale a faithful outline reads as Europe rather than as a cartoon, which the icon-scale attempt could not. The broken-emblem metaphor is stronger too: three stars are now missing from the top of the ring (11, 12 and 1 o'clock) instead of one, with a larger cloud of yellow fragments drifting up from the gap. Separately, the gap between the action buttons and the *Also available in…* locale row went from 40 px to 56 px so the locale row sits clearly as a meta-footer.
- **Press-kit logo cards stacked full-width and touched each other.** The §2 *Logos and emblems* markup referenced a `.grid-2` class from the start, but the rule was never defined in the page's `<style>` block, so the four brand-asset cards fell back to full-width block layout with no gap between them. Defined `.grid-2` as a responsive two-up grid (`repeat(auto-fit, minmax(280px, 1fr))` with a 20 px gap) that collapses to one column on narrow viewports. Applied identically across EN / FR / DE.
- **Add-to-calendar dropdown menu was occluded by the next event card.** The menu was absolutely positioned with `z-index: 20` inside an `.event-card` that carries `.glass` → `backdrop-filter`, which per W3C spec creates a new stacking context. The menu stayed inside the card's context and the next card's own context rendered above it. Fix: reparent the menu to `<body>` on first open and pin with `position: fixed` against `trigger.getBoundingClientRect()`. Same portal pattern as the ESSC member-preview popover. Outside-click + Escape dismiss still work; page scroll / window resize close the menu (matches existing popover dismissal convention). [#262](https://github.com/EISSeuropa/netsec.github.io/pull/262).
- **404-page polish, third pass: drop the failed continent backdrop, bump locale-row spacing.** The abstract European-continent shape behind the broken-EU-stars ring (PR #291) read at icon scale as a flying-saucer disc rather than as Europe — four overlapping ellipses turn out not to suggest a continent without recognisable peninsulas, and a faithful Europe outline at 260 px wide either dominates or reads as a cartoon. Dropped the backdrop entirely; the 11-of-12 EU stars with the broken top carry the metaphor cleanly on their own. Separately, the 28 px gap between the action buttons and the *Also available in…* locale row read tight again once the illustration above the 404 changed the page's vertical rhythm; bumped to 40 px so the locale row sits clearly as meta-footer rather than as a sibling of the buttons.
- **404-page polish, second pass: stray horizontal rules + on-theme illustration.** Two stray lines from the previous polish PR were cleaned up — the bordered `.search-results` list rendered its border even when empty (drawing a thin rule below the search bar before the visitor had typed); added `:empty { display: none }` so the box only appears once there's something to show. The `border-top` separator on `.err-lang` from PR #289 read as a stray rule against the glass card; the 28 px gap alone reads as enough separation, so the border is gone. New decorative illustration above the *404* heading: a 12-star EU emblem ring with the 12-o'clock star "broken" — its 11 siblings stay in their canonical positions, a small cloud of yellow fragments drifts up from the gap (subtly animated, honoured by `prefers-reduced-motion`), and a faint abstract land-mass blob sits behind in EU blue (`#003399` at 12% in light mode, `#7eb4ff` at 10% in dark mode). The metaphor: a piece of the Union's emblem has come loose — on-theme for both COST/EU identity and the "page got disconnected" idea, without trying to literally trace the European continent at icon scale (a recognisable outline would either dominate or read as a cartoon). `aria-hidden="true"` so screen readers skip the decoration; the *404* + *Page not found* text already convey the message verbally.
- **404-page polish: site-map button visibility, language switcher spacing + behaviour.** Three follow-ups to the earlier 404 search rewrite. (a) The *Open the site map* button uses `.btn-ghost`, which is bordered with `--glass-border` site-wide — intentionally faint for floating-glass UI but unreadable against the err-page glass card in both themes. Overridden locally on `.err-actions .btn-ghost` to use the stronger `--line` colour (and `rgba(255,255,255,.22)` in dark mode) so the button reads as a clear secondary call-to-action against either theme. (b) The *Also available in English · Français · Deutsch* row used to sit 18 px below the action buttons and read as part of the same cluster; bumped to a 28 px gap with a thin `border-top: 1px solid var(--line)` separator and 18 px internal padding. (c) The locale links used to navigate to the localised home (`/`, `/index.fr.html`, `/index.de.html`), yanking the visitor off the 404 they'd just landed on; new behaviour saves the chosen locale to `localStorage` and reloads the same URL, so GitHub Pages re-serves `404.html` for the unknown path and the page re-renders in the new locale without leaving the visitor's broken-link context. The existing `href` is preserved as a no-JS fallback. The 404 i18n loop also got a small refactor: a reusable `applyLang(lang)` function, EN now applied symmetrically (FR → EN no longer leaves the page frozen on French HTML defaults), and the currently-active locale is marked with `aria-current="page"` and styled as a label rather than a link.
- **404-page search was leaking internal Pagefind plumbing into the UI.** Pagefind UI v1.4+ auto-renders every `meta.*` key it finds as a `TitleCase: value` chip below the result card, which exposed our bio-stub meta as visible chrome (`Country: ch`, `Wgs: 2,3`, `Photo: /assets/images/people/…jpg`, `Kind: bio`, `Affiliation:`, `Position:`, `Role:`, `Keywords:`) and had no dark-mode CSS so result titles read as muddy gold on dark navy. The default UI also rendered the cleared-input control as a floating white pill outside the search box's right edge. Two changes converge: (a) `scripts/build-bio-search-stubs.py` now writes meta-bearing elements *outside* `<main data-pagefind-body>` as `<span hidden data-pagefind-meta="…">`, so Pagefind's body excerpt is drawn from the bio body text rather than a concatenation of role + position + affiliation + country + WGs + keywords paragraphs that produced snippets like *"Member of the NetSec community directory. MC member · …"* under the result title; (b) `404.html` drops the bundled `pagefind-ui` for an inline mini-search that calls Pagefind's low-level `pagefind.js` directly and renders results via the same `.search-result-*` / `.search-bio-*` classes that the Cmd-K overlay uses — bio hits get the avatar + flag + WG-chip card, page hits get the title + section + excerpt layout, and dark mode comes for free. All 39 bio stubs regenerated.

#### Changed

- **Shortened the *What's New* banner headline** to *"The full ESSC 2026 programme is live."* (EN / FR / DE). The previous wording carried the Stockholm dates as a trailing clause, which made the banner wrap on narrow viewports; the dates already sit on `/essc-2026.html` behind the CTA, so the banner can stay terse.
- **Documentation pack cover bump** from v1.9.3 to **v1.9.4** matching website v1.9.0. Cover-only bump per CLAUDE.md §11; section-level catch-up to website v1.9.0 (Section 02 repo layout adding `scripts/build-news-rss.py` + the `calendar/` directory + the new renderers, Section 04 architecture for the runtime-render-from-JSON pattern) queued under [#229](https://github.com/EISSeuropa/netsec.github.io/issues/229) → v1.11.0. New Appendix C entry summarises the gap. [#265](https://github.com/EISSeuropa/netsec.github.io/pull/265).
- **Press kit refreshed to v1.1** (EN / FR / DE). §2 *Logos and emblems* now documents the designer's four PNG brand-asset variants (`netsec-lockup-primary`, `-white`, `-mono`, `netsec-mark`) shipped in v1.8.0, with download links for each, replacing the stale launch-era "Pure CSS, no asset to download" copy that pointed at the gradient "NS" placeholder. §8 documentation-pack size bumped from 8 MB to 21 MB to match the live PDF. Footer stamp updated to "Press kit v1.1 · revised 28 May 2026 · supersedes v1.0".
- **Wiki *Decisions* log** picks up two v1.9.0 entries: (a) render home-page event and news cards from JSON at runtime, keep hand-coded HTML as fail-soft fallback (#249); (b) the body-portal pattern chosen for the Add-to-calendar dropdown to escape the `.glass` stacking-context trap (#262).

🤖 _Authored with help from [Claude Code](https://claude.com/claude-code)._

## [1.8.1] · 2026-05-27 — Founding contributors, release-infra hygiene, ribbon and voice polish

### Index of changes

#### Added

- **Founding contributors section on `/about.html`** (Item A of the founding-cohort brainstorm). New `<section id="founding">` between *Leadership* and *FAQ* lists the 52 researchers across 21 countries who participated in COST Open Call OC-2024-1-27931 establishing this Action. Sourced from a new [`data/founding-proposers.json`](data/founding-proposers.json) (the JSON also records membership status, MC-availability at founding, and the original source name where the affiliation needed light cleanup). Renders runtime via inline JS; reuses the existing `country-grid` / `mc-collapse` / `mc-stats` patterns from the MC country grid directly above so the founding cohort reads as a parallel "where we came from" narrative to the current MC composition. FR + DE variants land alongside, with locale-aware country names and the corresponding "Soumissionnaire" / "Antragsteller" badge for the Open Call Proposer (Dr Hugo Meijer). Privacy notice on `/privacy.html` (+ FR + DE) gains a new sub-section under §2 documenting the founding-listing as a separate processing activity with Article 6 (1)(f) legitimate-interest basis and a fourteen-day contact-form opt-out. Pairs with the Wiki-side directory-growth tracker (Item B) and a follow-up issue covering Items C (per-bio "founding contributor" badge) and D (founding-cohort stats refresh on press kit + PDF documentation pack). [#242](https://github.com/EISSeuropa/netsec.github.io/pull/242).
- **Three new entries in `data/events.json` from the official Action event ledger**: the *NetSec Policy Workshop* (4 September 2026, format TBC), the *NetSec ITC Conference* (8–11 September 2026, ITC Conference Grant scheme), and the *Inaugural Management Committee plenary* (18 September 2026, the firm date previously listed as "before late September"). Each entry feeds the home-page event banner via `data/events.json` and the public webcal feed via `calendar.ics`; `calendar.ics` rebuilt accordingly (5 events). Public roadmap (`/roadmap.html` + FR + DE) firms up the MC-plenary card date from "Before late September 2026" / "Avant fin septembre 2026" / "Vor Ende September 2026" to **18 September** / **18 septembre** / **18. September**. `docs/roadmap-2026.md` timeline gets matching rows for the Policy workshop and the ITC Conference between the existing Stockholm and MC plenary entries. Past Core Group JourFix dates (January, March, May 2026) and the September Core Group + MC back-to-back are seeded into the Wiki [Meetings index](https://github.com/EISSeuropa/netsec.github.io/wiki/Meetings) (Wiki commit; minutes pending). [#244](https://github.com/EISSeuropa/netsec.github.io/pull/244).
- **Issue-lifecycle automation** ([#238](https://github.com/EISSeuropa/netsec.github.io/issues/238) item C). Three new workflows under `.github/workflows/` bound the open-issue backlog without manual sweeping: `lock-closed-issues.yml` (daily 13:00 UTC) locks issues 14+ days after closure to keep drive-by comments off settled threads, `issue-lifecycle-comment.yml` (on `labeled` event) auto-posts the standard message when a lifecycle label lands (`needs-info`, `duplicate`, `wontfix`, `stale`), and `issue-sweep.yml` (daily 14:00 UTC) labels open issues `stale` after 60 days of inactivity, closes `stale` issues after another 14 days, and closes `needs-info` issues if no human comment arrives within 14 days. Two new labels (`needs-info`, `stale`) join the existing `bug`, `enhancement`, `documentation`, `duplicate`, `wontfix` set. Thresholds tuned softer than the upstream `anthropics/claude-code` defaults (14 / 60 / 14 vs. their 7 / 30 / 7) because our backlog is small and the maintainer reads every notification by hand. Label vocabulary + workflow behaviour codified in [CLAUDE.md §12](CLAUDE.md). [#240](https://github.com/EISSeuropa/netsec.github.io/pull/240).
- **YAML-form GitHub issue templates** ([#238](https://github.com/EISSeuropa/netsec.github.io/issues/238) item B). Three structured forms land under `.github/ISSUE_TEMPLATE/`: `bug_report.yml` (preflight checkboxes + required actual / expected / repro / environment), `enhancement.yml` (mirrors the maintainer's *What's happening / Why it matters / Fix path / Target* shape from CLAUDE.md §3), `documentation.yml` (typed dropdown picking which surface the issue affects: maintainer docs, Wiki, PDF pack, public copy, cross-cutting). A `config.yml` disables blank issues and routes routine questions to the public contact form, the FAQ, the Wiki onboarding page, and the ESSC 2026 member orientation. CLAUDE.md §3 updated to point external contributors at the forms while keeping the four-section maintainer-issue shape as the canonical body content for `gh issue create` paths. [#239](https://github.com/EISSeuropa/netsec.github.io/pull/239).
- **CLAUDE.md §12 *Release-infrastructure hygiene*** (#238). Codifies the three conventions on `.github/` introduced across items A, B, and C of the issue: SHA-pin third-party actions with tag-comment annotation, YAML-form issue templates rather than free-form markdown, and the lifecycle-label vocabulary table (`needs-info`, `stale`, `duplicate`, `wontfix`). Lands together so the next maintainer inherits the conventions rather than rederiving them from upstream.

#### Changed

- **Home-page event cards (`index.html` + FR + DE) refreshed against the official Action event ledger.** Two new cards added between the European Security Conference and the Inaugural MC Plenary: the *NetSec Policy Workshop* (4 September 2026) and the *NetSec ITC Conference* (8–11 September 2026, ITC Conference Grant scheme; travel-grant support linked through to `grants.html`). The Inaugural Management Committee Plenary card firms up from "To be announced" to **18 September 2026** with updated body prose (first formal plenary, MC representatives + Working Group leads, restricted-access notice; the previous *Kick-off Meeting* event-type pill becomes *MC Plenary*). The Summer School card updates the *Application deadline* meta row to *Applications closed on 1 March 2026. Selected participants will be contacted by the scientific coordinators*; the CTA text shortens from *Full details & how to apply* to *Full details* since applications have closed. The event-list now matches the chronological order in `data/events.json` (Summer School → ESSC → Policy Workshop → ITC Conference → MC Plenary). The home-page cards are still hand-coded HTML rather than rendered from `events.json`; deriving them at build time is tracked in [#249](https://github.com/EISSeuropa/netsec.github.io/issues/249) for v1.9.0. [#248](https://github.com/EISSeuropa/netsec.github.io/pull/248).
- **`.github/workflows/*.yml` third-party actions SHA-pinned with tag-comment annotation** ([#238](https://github.com/EISSeuropa/netsec.github.io/issues/238) item A). Every `uses:` line across the eleven touched workflow files now references a commit SHA instead of a floating version tag, with a trailing `# vN (sha-pinned)` comment for human readability. Closes the supply-chain exposure where a maintainer of any third-party action (or an attacker who compromises one) could push a malicious commit under the same tag and run with `contents: write` plus `pull-requests: write` on our next sync. Affected: `actions/checkout@v4`, `actions/configure-pages@v5`, `actions/deploy-pages@v4`, `actions/setup-node@v4`, `actions/setup-python@v5`, `actions/upload-pages-artifact@v3`, `peter-evans/create-pull-request@v7`. Widens the scope of [#151](https://github.com/EISSeuropa/netsec.github.io/issues/151) (which only covered Node 20 removal pinning) to the full third-party surface. Dependabot continues to surface updates via PR, updating the SHA explicitly each time. [#239](https://github.com/EISSeuropa/netsec.github.io/pull/239).
- **`scripts/sync-cost.py` now propagates per-bio WG memberships from cost.eu into `data/bios.json`** ([#236](https://github.com/EISSeuropa/netsec.github.io/issues/236) Gap A). The weekly Monday sync (plus any manual `workflow_dispatch`) parses the Membership table on <https://www.cost.eu/actions/CA24154/>, looks each row up against `bios.json.members[].name` via the existing `norm()` helper, and overwrites the matched entry's `wgs` field with cost.eu's list. Entries not present on cost.eu (community members in the directory who aren't on the MC, or seed entries for leaders not yet on the Membership table) are left untouched. Before this change, the home-page WG chips (driven by `WG_MAP` in `index.html`) and the `/people.html` per-bio chips (driven by the Google Form submitter's answer) could drift indefinitely. cost.eu is now the authoritative source for formal WG membership on both surfaces; the Google Form remains the seed when a bio first lands. Rule documented in [`docs/bios-setup.md`](docs/bios-setup.md). Six new smoke tests in `scripts/test-sync-cost.py` cover the overwrite, idempotency, leave-unmatched-alone, salutation normalisation, missing-file, and leadership-suffix regression cases. Gaps B (statistics + country roster) and C (leadership-label regex holes) deferred to v1.10.0. [#237](https://github.com/EISSeuropa/netsec.github.io/pull/237).
- **Public roadmap (`roadmap.html` + FR + DE) and `docs/roadmap-2026.md` reshuffled around the Stockholm conference cadence.** Five planned releases now interleave with the Action calendar: v1.8.1 (28 May, this release), v1.9.0 (5 June, pre-Stockholm calendar plumbing), v1.10.0 (late July, reactive post-conference patch with sync-cost Gaps B + C, Stockholm recap, FR / DE FAQ + Glossary native-speaker pass), v1.11.0 (mid September, three days ahead of the inaugural MC plenary; Outputs section refresh with D6 cards + `schema.org/ScholarlyArticle`, Phase 2 IA pass, founding-cohort follow-ups [#245](https://github.com/EISSeuropa/netsec.github.io/issues/245), PDF documentation pack section-level catch-up [#229](https://github.com/EISSeuropa/netsec.github.io/issues/229)), v1.12.0 (late December, Year 1 retrospective + D11 + D12 + per-page OG images + FAQ / Glossary print stylesheet + member-photos-out-of-git refactor [#119](https://github.com/EISSeuropa/netsec.github.io/issues/119)). August is a deliberate break. GitHub milestones bumped to match. *Last updated* / *Dernière mise à jour* / *Zuletzt aktualisiert* stamps refreshed to 27 May 2026 across all three locales. [#250](https://github.com/EISSeuropa/netsec.github.io/pull/250).
- **FR / DE prose em-dash sweep** ([#164](https://github.com/EISSeuropa/netsec.github.io/issues/164)). Four user-visible em-dashes in prose strings rewritten to commas per CLAUDE.md §7: the contact-form success toast on `/index.fr.html` + `/index.de.html` and the directory tour's country-filter chip body on `/people.fr.html` + `/people.de.html`. Decorative em-dashes wrapping the *Activity window* timeline label on `/grants.html` (+ FR + DE) deliberately kept since EN ships them as visual brackets, not prose punctuation, and locale divergence here would create inconsistency. Closes the FR / DE half of the voice-rule sweep that v1.8.0 only applied to EN public copy (#223).

#### Fixed

- **Beta-translation ribbon "View in English" link now sticks** ([#253](https://github.com/EISSeuropa/netsec.github.io/issues/253)). The nav `.lang-switch` chips persist the chosen language to `localStorage.netsec-lang` on click, and the auto-redirect in `assets/js/site.js` then sends EN visitors to the saved FR / DE variant on every subsequent page load (the asymmetry is deliberate, EN remains the authoritative fallback). The ribbon's `<a hreflang="en">Voir en anglais → / Auf Englisch ansehen →</a>` link sits outside `.lang-switch`, so it wasn't getting the same persistence treatment — clicking it landed on EN briefly, then the auto-redirect bounced the visitor straight back. Same handler now binds to `.i18n-beta-ribbon a[hreflang]` so the ribbon-driven EN switch persists as the user's deliberate preference. No HTML change needed; one diff in `site.js`.

🤖 _Authored with help from [Claude Code](https://claude.com/claude-code)._

## [1.8.0] · 2026-05-25 — Brand launch, Indico writes, programme PDF, voice sweep

> Pre-Stockholm release. The brand identity finally lands across the site, three Indico operational tools ship to make the ESSC 2027 prep cycle programmatic, the programme page exports a polished self-identifying PDF, and the CLAUDE.md §7 writing-voice rules get applied retroactively across the EN launch-era prose.

### NetSec brand identity

The designer's new four-petal mark and lockup deploy across all 46 HTML pages, replacing the launch-era "NS" gradient-square placeholder. Three surfaces move at once. The header brand link ships two `<img>` lockups keyed off the site's `.dark` class (light and dark variants follow whatever theme the visitor explicitly picked rather than the OS `prefers-color-scheme`, which would desync against the rest of the page), with a 32×32 mark-only swap below 700 px to free up header real estate against the hamburger, language switcher, and theme toggle. The favicon family rasterises from the 595×599 mark into the per-size PNG chain (16 / 32 / 48 for browser tabs, 180 for Apple touch-icon, 192 and 512 for Android home-screen and PWA manifest) plus a multi-resolution `favicon.ico` for legacy clients; a new `manifest.webmanifest` at repo root carries those references along with `theme_color` and `background_color` so the OS shortcut UI matches the brand. A fresh 2400×1260 OG card composes the primary lockup over a soft brand-tinted canvas for LinkedIn, Mastodon, Bluesky, Slack, Twitter, and Facebook link previews; JSON-LD `Organization.logo` points at the new 512×512 mark so the Google Knowledge Panel renders correctly. Two reproducible build scripts ship alongside ([`build-brand-assets.py`](scripts/build-brand-assets.py) and [`update-brand-html.py`](scripts/update-brand-html.py)) so the next designer refresh stays a one-command operation; the rationale and refresh workflow are written up in [`docs/brand-deployment.md`](docs/brand-deployment.md). Out of scope for this cut: SVG masters (designer delivered PNG only, follow-up on [#220](https://github.com/EISSeuropa/netsec.github.io/issues/220)) and the `#003399` to brand `#2B639C` accent migration (the values are close but not identical, and the migration is cross-cutting across `site.css`, JSON-LD `themeColor`, manifest `theme_color`, and several inline `<style>` blocks).

### Indico write-side automation

Two new operational scripts and one permission-model finding land together, the result of four probe rounds against the live EISS Indico instance through PRs #212 to #217. [`scripts/indico_patch.py`](scripts/indico_patch.py) is the write-side companion to the daily `sync-indico.py`: it reads a YAML "fix-plan" describing session renames, room changes, contribution session-moves, affiliation corrections, and block-time edits, resolves friendly Indico IDs to internal database IDs against the live read API, then dispatches the right write call against the management endpoints. Dry-run by default; `--apply` flips to live writes; resolved IDs cached in a gitignored sidecar JSON. [`scripts/indico_clean_duplicate.py`](scripts/indico_clean_duplicate.py) handles the ESSC-N to ESSC-N+1 rollover: Indico's "duplicate event" feature copies the previous year's contributions and sessions along with the configuration we actually want to inherit (review workflow, custom fields, registration form, role assignments), so new submissions continue the old friendly-ID counter and your first ESSC 2027 abstract lands as #342 instead of #1. The clean-duplicate script enumerates inherited content via the read API and selectively `DELETE`s it via the management API, leaving configuration intact, with a hardcoded `PROTECTED_EVENTS` allow-list refusing to touch the live ESSC 2026 (event 22) unless `--force` is passed; dry-run by default, explicit `--delete <category>` required per content type. Smoke-tested against event 22 in dry-run: enumerated 105 contributions correctly via the read API and produced the right DELETE URLs without issuing any. The probe rounds resolved a permission-model misread that had blocked Phase 1: the 403-with-anonymous-session pattern on `/event/<id>/manage/*` that we first read as "Bearer auth ignored" turned out to be Indico's standard auth-then-permission flow, falling through to the anonymous render path when the user lacked management permission. The unlock is the admin flag on the bot account that owns `INDICO_WRITE_TOKEN`, not a scope or auth-mechanism change. That operational precondition is now documented across all three Indico scripts in [`docs/indico-patch.md`](docs/indico-patch.md). Tracks [#210](https://github.com/EISSeuropa/netsec.github.io/issues/210).

### Programme page · self-identifying print-to-PDF

[`/essc-2026.html`](essc-2026.html) (plus FR and DE) now exports a self-identifying PDF when the visitor uses *Print → Save as PDF*. Page 1 carries a full title block (conference name, dates, venue, organisers) so the file makes sense when shared or archived separately from the URL; pages 2 onwards get a thin single-line locale-aware running header and a bottom-right page counter (`Page 2 of 4` / `sur` / `von`). A4 portrait, 20 / 14 / 16 mm margins, tighter cards at 9.5 pt body with 0.6 pt borders and no shadows, contributions list force-open on print so the full paper line-up and abstracts make it onto paper. The export shrank from 17 stretched-card pages to a clean 6 once the leak from the external-link `::after` decoration (`width: 0.85em` icon mask combined with `word-break: break-all` was wrapping URL characters one per line and inflating link headings to 565 px) was reset inside the print rules. Closes [#208](https://github.com/EISSeuropa/netsec.github.io/issues/208).

### Maintainer signals and the launch-prose sweep

Two small but high-leverage pieces of cleanup. The weekly bios-sync and cost-sync workflows open auto-PRs on dedicated branches and auto-merge them when CI is green, which keeps `main` fresh but means churn lands silently. Adding `reviewers: APB-LDN` to both `peter-evans/create-pull-request@v7` invocations turns each diff-producing run into an email and a mobile-push notification on the maintainer's GitHub account, without gating the auto-merge ([#222](https://github.com/EISSeuropa/netsec.github.io/pull/222)). Separately, the CLAUDE.md §7 writing-voice rules (no em dashes, no rule-of-three, no synonym cycling) get applied retroactively across the EN public surface: 30+ HTML pages, the SEO injection script and its regenerated meta and JSON-LD output, the hand-authored ESSC 2026 OG / Twitter / JSON-LD blocks, and the `events.json` calendar copy. UI glyph em dashes (the empty-field "—" in quickfacts cells, the JS no-value defaults) are kept as-is; those are typography, not punctuation. FR and DE prose is left to its translators, who decide their own punctuation conventions ([#223](https://github.com/EISSeuropa/netsec.github.io/pull/223)). The P1 documentation voice-sweep tracks separately for the next cycle.

### Index of changes

#### Added

- **NetSec logo deployment across all 46 HTML pages.** Header lockup (light / dark `<img>` pair keyed off `.dark` with a mark-only swap below 700 px), favicon family (16 / 32 / 48 / 180 / 192 / 512 PNG chain plus multi-resolution `.ico`), `manifest.webmanifest` at repo root, JSON-LD `Organization.logo`, and a fresh 2400×1260 OG social card. Reproducible via [`scripts/build-brand-assets.py`](scripts/build-brand-assets.py) and [`scripts/update-brand-html.py`](scripts/update-brand-html.py); refresh workflow at [`docs/brand-deployment.md`](docs/brand-deployment.md). Closes [#220](https://github.com/EISSeuropa/netsec.github.io/issues/220).
- **[`scripts/indico_patch.py`](scripts/indico_patch.py)**, the write-side companion to `sync-indico.py`. Reads a YAML fix-plan, resolves friendly Indico IDs against the live read API, dispatches session-rename, room-change, contribution-move, affiliation, and block-time edits against the management endpoints. Dry-run by default; `--apply` writes for real. Schema at [`data/indico-fix-plans/EXAMPLE.yaml`](data/indico-fix-plans/EXAMPLE.yaml); design rationale at [`docs/indico-patch.md`](docs/indico-patch.md). Tracks [#210](https://github.com/EISSeuropa/netsec.github.io/issues/210).
- **[`scripts/indico_clean_duplicate.py`](scripts/indico_clean_duplicate.py)**, for the ESSC-N to ESSC-N+1 rollover. Lists inherited content via the read API and `DELETE`s it via the management API, leaving configuration intact. A hardcoded `PROTECTED_EVENTS` allow-list refuses to touch ESSC 2026 (event 22) without `--force`. Smoke-tested against event 22 in dry-run: enumerated 105 contributions correctly and produced the right DELETE URLs without issuing any. Same admin-flag precondition as `indico_patch.py`.
- **Cover masthead, running header, and bottom-right page counter on the programme print-to-PDF** ([`essc-2026.html`](essc-2026.html) plus FR and DE). A4 portrait, 20 / 14 / 16 mm margins, tighter cards at 9.5 pt body, contributions list forced open. Closes [#208](https://github.com/EISSeuropa/netsec.github.io/issues/208).
- **Sync workflow maintainer notifications.** `reviewers: APB-LDN` added to both `bios-sync` and `cost-sync` `peter-evans/create-pull-request@v7` steps; each diff-producing run now emails plus mobile-pushes the maintainer. Auto-merge still fires on green CI, so the line is a change-awareness signal, not a review gate ([#222](https://github.com/EISSeuropa/netsec.github.io/pull/222)).

#### Changed

- **Voice rules applied retroactively to EN public HTML and shared SEO infrastructure** ([#223](https://github.com/EISSeuropa/netsec.github.io/pull/223)). 30+ pages swept: `<title>` em dashes to ` · `, `<meta description>` first em dash to colon and subsequent ones to comma, hand-authored ESSC 2026 OG / Twitter / JSON-LD blocks aligned to the new SEO constants in `scripts/inject-seo.py`. The `inject-seo.py` `BEGIN seo:auto` sentinel keeps its em dash for regex backward-compatibility with already-deployed pages. UI glyph em dashes (empty-field "—" placeholders) preserved. FR / DE prose untouched.
- **`docs/admin-guide.md` and `docs/design-system.md`** refreshed to point at the new brand assets and document the dual-`<img>` dark-mode pattern that the site uses instead of `<picture media="prefers-color-scheme: dark">`.
- **`indico_patch.py` un-parked after Phase 1.5 admin unlock.** The probe-era "writes-blocked" annotations are gone; the script is now the canonical write entrypoint, and the operational precondition (admin flag on the bot account that owns `INDICO_WRITE_TOKEN`) is documented at [`docs/indico-patch.md`](docs/indico-patch.md). Live no-op write validation deferred to the first real ESSC 2027 prep apply, on one open ID-namespace subtlety on contribution REST PATCH.
- **Accent / brand colour migration deferred to a follow-up.** The shift from `#003399` to the brand-pack `#2B639C` is flagged on [#220](https://github.com/EISSeuropa/netsec.github.io/issues/220) but not part of this cut.

#### Fixed

- **Brand-image visibility regression after the first deploy.** All three header `<img>` variants were rendering at once because `assets/css/site.css`'s global `img { display: block }` (specificity 0,0,1) defeats the UA `[hidden] { display: none }` rule, which only wins as user-agent CSS against author CSS of the same specificity. Restored explicit class-level `display: none` on `.brand-logo` and `.brand-mark-only` (specificity 0,1,0 wins over `img`'s 0,0,1) with contextual un-hides via `.dark`-prefixed selectors and the `@media (max-width: 699.98px)` mark-only break. The `hidden` attribute is kept on the default-hidden variants as defence in depth. A `?v=2026-05-25` cache-bust on the site.css link prevents repeat-visit regressions from stale CDN copies.

## [1.7.0] · 2026-05-24 — Directory keyword filter, bios-sync hardening, release automation

> Conference-prep release. The directory gets a research-interest filter chip row so visitors can drill in by topic across the membership; the bios-sync pipeline gets the robustness work to handle the volume the open form is about to deliver; and the release process itself gets the automation that will make every future release lighter than the last. Cut before the European Security Conference on 9–12 June so the new directory shape is what the incoming submissions land against.

### Directory research-interest filter

Three phases shipped end-to-end across the three locales. Phase 1 renders a member's research keywords as outlined chips on the detailed bio card. Phase 2 normalises submissions through a curated [`data/keyword-aliases.json`](data/keyword-aliases.json) so near-duplicates collapse to a single canonical form and acronyms (UN, NATO, EU, UK, US, UNDP, …) survive the sentence-case pass; an aggregate count per canonical keyword falls out as a by-product. Phase 3 surfaces that aggregate as a multi-select toggle chip row above the directory grid: top eight by count, *Show all* expander, OR semantics, URL-hash persistence so filtered views are shareable (`#keywords=ai-governance,foreign-policy-analysis`), and clickable per-bio pills that feed into the same filter. The guided tour and the welcome strip on `/people.html` were updated in EN / FR / DE to introduce the new row.

### Bios-sync robustness, before the firehose

The Google Form is about to open to ~50 incoming submissions. Three improvements harden the pipeline. The merge logic was already truthy-merge per field; that semantic guarantee is now pinned by [a regression test](scripts/test-sync-bios.py) and explained in [`docs/bios-setup.md`](docs/bios-setup.md) so respondents who resubmit sparsely (the documented workaround for the Google Forms file-upload-edit bug, [#183](https://github.com/EISSeuropa/netsec.github.io/issues/183)) don't lose their previously-stored optional links. Defensive `PHOTOS_CHANGED` tracking carries the lesson from sister-project EISSeuropa.github.io [#105+#106](https://github.com/EISSeuropa/EISSeuropa.github.io/pull/106): if `photo_source_sha256` propagation ever regresses, the script screams loudly instead of silently producing an unexplained binary diff. And the auto-PR itself self-describes now: title becomes `data: Dr Alex Petrova joined the network` or `data: 2 new bios + 3 updates`; body opens with a structured *What changed* section listing new joiners with country + affiliation, updated members with the specific fields that moved, and the list of headshot files rewritten on disk.

### Release-time automation

The maintainer-facing release process picks up two pieces of automation that close the *between-releases drift* gap [CLAUDE.md §11](CLAUDE.md) had deliberately left open. `docs/roadmap-2026.md` carries a machine-managed AUTOSTAMP block; a new workflow regenerates it on every push to `main` that touches `CHANGELOG.md`, auto-merging the PR. And `scripts/release.sh` now calls `scripts/promote-roadmap.py` before the release commit, which flips the matching `<li class="rm-entry planned">` card across EN / FR / DE to shipped with locale-correct date formats (`8 September 2026` / `8 septembre 2026` / `8. September 2026`), inserts the localised release-notes link, and bumps the *Last updated* paragraph's two `<time>` attributes plus visible text. On minor / major releases the script also prints a structured PDF-cover reminder pointing at the four version stamps to update. First observation of the workflow firing caught an auto-merge gap on `sync-roadmap.yml` and `sync-bios.yml`; fixed in the same window.

### Index of changes

#### Added

- **Research-interest keyword chips on directory cards** (`/people.html` + FR + DE). Detailed view only. Sentence-case normalisation at render time so submissions like "International Security" and "international security" collapse to a single visual form. A curated acronym set (UN / NATO / EU / UK / US / UNDP / OSCE / ASEAN / IMF / WHO / IAEA / GDPR / IoT / R&D / CFSP / PESCO / BRICS / G7 / G20 / …) keeps those preserved through the normaliser so compound forms like "EU–NATO relations" render correctly rather than mangling to "Eu–nato relations". Distinct styling from the WG chips (subdued outlined pill vs. bright gradient pill) so visitors parse the two layers at a glance. Keywords already entered the directory search vector and now also enter the site-wide Pagefind index via rendered DOM.
- **Phase 2 keyword infrastructure** for the directory. New `data/keyword-aliases.json` carries a curated acronym list + alias map. `scripts/sync-bios.py` resolves each bio's raw `keywords` through the alias map (with sentence-case + acronym preservation as the auto-normaliser), emits a `canonical_keywords` field per bio plus a top-level `keyword_aggregate` count, and logs Levenshtein / substring-close pairs as "possible alias candidate" hints so the maintainer can merge them by hand. The renderer (EN / FR / DE) prefers `canonical_keywords`, falling back to the inline normaliser for older data. Documented in `docs/bios-setup.md`. Phase 3 (dedicated filter chips above the grid) still tracked in [#175](https://github.com/EISSeuropa/netsec.github.io/issues/175).
- **Phase 3 research-interest filter chip row** above the directory (`/people.html` + FR + DE). Reads `keyword_aggregate` from `bios.json`, renders the top eight canonical keywords as toggle pills with submission counts, and expands to the full list on demand. Multi-select with OR semantics: any bio carrying at least one selected interest passes. Per-bio keyword pills are now buttons too: tap one to add it to the active filter and scroll to the result. Selection persists in the URL hash (`#keywords=…`) so filtered views are shareable and survive back-forward navigation. Visible as soon as the directory has any canonical keywords; hidden cleanly otherwise.

#### Changed

- **Directory guided tour + welcome strip** updated to introduce the research-interest filter row. A new tour step lands between Country and Card density, explaining the chip row, multi-select OR semantics, the clickable per-bio pills, and the URL-shareability of a filtered view. The welcome strip gains a matching bullet so the orientation is visible even to visitors who skip the tour. Mirrored to FR + DE. `docs/bios-setup.md` also gets a one-paragraph note that `keyword_aggregate` powers the filter automatically.
- **Bios-sync auto-PRs now self-describe.** Title used to be the static `data: sync member bios from Google Form`; it's now dynamic and reflects what changed: `data: Dr Alex Petrova joined the network`, `data: Bob Smith updated their headshot`, `data: 2 new bios + 3 updates`, etc. The body gains a structured `## What changed` section above the raw run log: per-member bullets list new joiners with country + affiliation, updated members with the specific fields that moved (`bio, LinkedIn` vs `headshot replaced` vs `bio, keywords + headshot`), removals, and the list of headshot files that were rewritten on disk. Driven by a pure `classify_diff` function in `scripts/sync-bios.py` covered by 20 new test assertions.
- **Roadmap-doc autostamp automated.** `docs/roadmap-2026.md` now carries a machine-managed AUTOSTAMP block near the top that records the number of bullets in `CHANGELOG.md` `[Unreleased]` (per category) and the freshness date. A new workflow `.github/workflows/sync-roadmap.yml` regenerates the stamp on every push to `main` touching `CHANGELOG.md` (plus a weekly cron + manual dispatch) and opens an auto-merging PR if the count moved. Closes the gap CLAUDE.md §11 deliberately left open between releases: the staleness signal is automated; humans still write the prose synthesis on release-time §5 sweep. Driven by `scripts/sync-roadmap.py`, pinned by 21 test assertions in `scripts/test-sync-roadmap.py`.
- **Public-roadmap promotion + last-updated stamps automated at release time.** `scripts/release.sh` now calls a new `scripts/promote-roadmap.py` before the release commit. The script finds the `<li class="rm-entry planned">` card matching the release version across `roadmap.html` + FR + DE, flips the status pill to *Shipped* / *Livrée* / *Veröffentlicht*, formats the date per locale convention (`8 September 2026` / `8 septembre 2026` / `8. September 2026`), adds the *Release notes* / *Notes de version* / *Release-Notizen* link, and bumps both `<time datetime="…">` attributes + the visible date text in the *Last updated* paragraph. Non-release planned milestones (Stockholm event, MC plenary) are protected by an `rm-milestone` class guard. Idempotent: re-runs no-op cleanly. Pinned by 28 test assertions in `scripts/test-promote-roadmap.py`. On minor / major releases (X.Y.0 / X.0.0), `release.sh` also prints a structured PDF-cover reminder with the current PDF version, the four stamps to update in `docs/pdf/documentation.html`, the `./docs/pdf/build.sh` rebuild command, and the PDF bump-policy ladder. Patch releases skip the PDF reminder per CLAUDE.md §11.
- **Join-form Google Forms settings flipped** to work around an upstream limitation: file uploads can't be replaced via the response-edit link, so photo updates need a fresh submission. `Limit to 1 response` is now off; `Collect email addresses → Verified` keeps sign-in mandatory and gives the sync a reliable dedup key; `Allow response editing` stays on for non-photo updates. A note on the form's Photo question points respondents at the workaround at the point of confusion. `docs/bios-setup.md` Step 1 + the Editing section rewritten accordingly. Tracked as [#183](https://github.com/EISSeuropa/netsec.github.io/issues/183); will revert if Google ever fixes the upstream bug.
- **Documented the truthy-merge semantics of `scripts/sync-bios.py`** in the bios-setup guide. A respondent submitting a "minimum-viable" second response that fills only the required fields plus the new photo will NOT lose their previously-stored LinkedIn, ORCID, keywords, etc; the sync overwrites only fields that carry a non-empty value in the new submission. WG memberships use union semantics. Form-side disclaimer on the Photo question reworded to make this safety net explicit, so respondents know they don't have to retype every optional link.

## [1.6.1] · 2026-05-24 — Pre-ESSC polish, sync robustness, copy hygiene

### Index of changes

#### Added

- **Inline-expand full abstract on programme contribution cards** (`/essc-2026.html` + FR + DE). `scripts/sync-indico.py` now emits a `fullAbstract` field alongside the truncated teaser; clicking *Read full abstract* swaps the teaser for the full text in place, *Show less* swaps it back. Title still anchors to the Indico contribution page for the canonical record. [#158](https://github.com/EISSeuropa/netsec.github.io/pull/158).
- **Per-session room badge on the programme grid.** Surfaces "D House, Lecture Hall 8" / "Lecture Hall 9" / "Floor 3" on session, contribution, and break cards via a small pin-icon chip. The sync exposes `inheritRoom` and `inheritLoc` flags from Indico for forward use. [#156](https://github.com/EISSeuropa/netsec.github.io/pull/156).
- **Practical information section** on `/essc-2026.html` after the live programme. Two cards: Accommodation (five recommended Stockholm neighbourhoods with their nearest red-line metro stops as chips) and Getting around (T13 context + sl.se link). Quick-facts strip grows from 4 to 5 tiles with a new *Practical info / Stockholm tips ↓* in-page anchor. Mirrored to FR + DE. [#159](https://github.com/EISSeuropa/netsec.github.io/pull/159).
- **`indicoEventId` link field on `data/events.json`.** Entries that opt in get their `summary`, `start`, and `end` overwritten from the fresh Indico payload on every sync, closing the drift between the live programme and the home-page banner / `calendar.ics`. Allow-list is tight; `location`, `description`, `url`, `categories` stay hand-edited. Documented in `docs/indico-sync.md`. Refactor to fully-derived data tracked in [#170](https://github.com/EISSeuropa/netsec.github.io/issues/170). [#171](https://github.com/EISSeuropa/netsec.github.io/pull/171).
- **Per-PR `[Unreleased]` maintenance rule** added to `CLAUDE.md` §4. Every PR that ships a user-visible change adds at least one bullet to `[Unreleased]` in the same PR; reconstructing the batch at release time loses nuance.

#### Changed

- **Parallel programme rows sorted by canonical room name** so the same room consistently lands in the same column across the day. Indico orders parallel panels by convener id; without normalisation, Lecture Hall 8 jumped between left and right between time slots. A small `_canonical_room` helper strips cosmetic building prefixes so "Lecture Hall 8" and "D House, Lecture Hall 8" collapse to the same column key. [#157](https://github.com/EISSeuropa/netsec.github.io/pull/157).
- **`sync-indico.yml` opens a PR via `peter-evans/create-pull-request@v7`** instead of pushing directly to `main`. Branch protection on `main` had started rejecting the direct push with `GH013`. CodeQL still runs on the bot PR (separate workflow), all checks complete, auto-merge fires, daily cadence stays hands-free. PAT not required; `GITHUB_TOKEN` is enough. [#160](https://github.com/EISSeuropa/netsec.github.io/pull/160).
- **Sitewide footer attribution: em-dash → colon.** `COST Action NetSec — Networking European Security Knowledge` becomes `COST Action NetSec: Networking European Security Knowledge` (and locale variants) across 45 page footers (15 EN + 15 FR + 15 DE). Voice-rule cleanup pass; rest of the em-dash audit tracked in [#164](https://github.com/EISSeuropa/netsec.github.io/issues/164). [#166](https://github.com/EISSeuropa/netsec.github.io/pull/166).

#### Fixed

- **Mobile home visual polish.** The floating nav no longer ghosts high-contrast details-strip text through its backdrop-filter on iOS Safari: a fixed top-scrim covers the gap above the bubble and the nav itself takes a near-opaque background on small viewports. Details-strip ↔ event-banner vertical gap tightened from 24 + 24 px to 12 + 8 px at ≤ 720 px. The event-banner status pill is now wrapped in a subtle `currentColor`-tinted chip so the dot reads as part of the same pill rather than a floating speck. [#154](https://github.com/EISSeuropa/netsec.github.io/pull/154).
- **Beta-translation ribbon ghosting on FR / DE pages.** The disclaimer ribbon used a ~5-15% alpha accent gradient over no base, so page content scrolled visibly through. Layered over `var(--glass-bg-strong)` + `backdrop-filter: saturate(180%) blur(20px)` on desktop, plus a near-opaque page-bg tint on mobile (≤ 720 px). [#155](https://github.com/EISSeuropa/netsec.github.io/pull/155).
- **Details-strip separator half-line on mobile home.** The 2 × 2 grid at ≤ 1100 px left a stray border-bottom under the third tile only. Switched the strip rule from `:nth-child(2n) + :last-child` to `:nth-last-child(-n+2)` so the final row sheds the border regardless of total item count. [#163](https://github.com/EISSeuropa/netsec.github.io/pull/163).
- **Break-card title and room badge collision** on `/essc-2026.html`. The pin icon sat right against the last word of the title; italic muted styling made the title vanish next to the badge. Now flex-laid with `gap: 14 px`, title in normal weight + `ink-2` colour, middle-dot `·` separator before the badge. [#168](https://github.com/EISSeuropa/netsec.github.io/pull/168).

🤖 _Authored with help from [Claude Code](https://claude.com/claude-code)._

## [1.6.0] · 2026-05-23 — Live ESSC programme and member previews

> The live ESSC programme release. v1.6.0 turns netsec-cost.eu into the canonical entry point for the European Security Studies Conference: a daily-synced live programme page at `/essc-2026.html`, in-place bio previews for speakers who are NetSec members, a collapsible shipped-history on the public roadmap, and a CSS lint that catches the class-name collisions that bit the directory mid-cycle.

### Live ESSC 2026 programme on netsec-cost.eu

The flagship outreach moment of the year now has its own page on the NetSec site rather than living only on Indico. `scripts/sync-indico.py` runs daily at 03:45 UTC, talks to `indico.eiss-europa.com`'s API, scopes to category 1 (Annual Conferences), and writes the normalised programme to `data/indico.json`. The page at `/essc-2026.html` (+ `.fr.html` + `.de.html`) reads that file at render-time and lays out a programme grid with day-chip navigation, parallel-session rows, contributions, abstracts, livestream badges on plenaries and roundtables, and a pulse-dot beside the page-level "Live programme" cue. Chrome strings (chair / speakers / discussants / day labels / error messages) translate via an inline I18N table; programme content stays in whatever language the submitter wrote it in. The home-page Events block now deep-links to the live page; the sitemap and calendar.ics treat it as the canonical URL for the conference. Schema-compatible with EISS's existing programme generator so a future port to a build-time renderer drops in.

### Member-aware previews on the programme

Hover a speaker name on the programme — if the speaker resolves to a NetSec member through `data/bios.json`, a glass-surfaced preview card opens via the native Popover API. The card carries photo, name, position, affiliation, country with flag, role / working-group chips, three-line bio excerpt, contact-icon row (email, website, ORCID, LinkedIn, X, Bluesky, Mastodon — only the ones the member has filled in), and a "View full profile →" link to `/people.html#<slug>` that scrolls to the matching directory card with a persistent spotlight. Matching uses a JS port of `scripts/sync-bios.py`'s `name_key()`: NFKD-normalise, strip diacritics, drop honorifics, drop apostrophes, drop post-nominals, drop nobiliary particles, key on first + last surviving tokens. Members whose Indico spelling won't match the canonical bios.json name can declare an optional `name_aliases: []` field to bridge the gap. Show / hide model: hover or focus opens; the popover stays open while the cursor is over either anchor or card; leaving both, scrolling the page, clicking outside, or pressing Esc all dismiss. Graceful degrade: feature-detects `HTMLElement.showPopover`; on browsers without it the anchor navigates straight to `/people.html#<slug>`.

### Roadmap UX + CSS hygiene

The Shipped list on `/roadmap.html` now collapses behind a single toggle (default collapsed) so the in-progress and planned items stay above the fold as the shipped history grows. A new CSS class-collision lint (`scripts/check-css-class-collisions.py`) runs on every PR that touches `assets/css/site.css` and flags the kind of mistake that briefly broke `/people.html` mid-cycle — the popover originally used `.member-card` as its container class, which was already the directory's main card class. The lint walks the CSS, finds classes declared as the sole-compound selector of two or more rule blocks more than 200 lines apart, and reports them as cross-feature collisions. Inline `/* css-collision-allow: .my-class */` markers handle legitimate cross-cutting cases.

### Polish

The matcher gained a debug logger that lists unmatched speakers via `console.debug` during render; useful for spotting near-misses (typo, name-order flip, missing alias) without bothering readers. The `/people.html` deep-link spotlight is now persistent instead of auto-fading after 3.5 s — in detailed view, where every card shows its full bio, the old timer often expired before the visitor noticed the landing; the spotlight now clears on user-initiated action (typing in search, clicking a different card, changing a filter) and the hash strips with it. Linked speaker names on the programme now read as tappable at rest (visible accent-coloured dotted underline plus a soft accent tint to the text) so touch users — who never see a `:hover` reveal — can tell at a glance which names lead to a profile. The popover's glass background respects `@supports (backdrop-filter)` with a solid `--bg-1` fallback. The roadmap's chevron animation respects `prefers-reduced-motion`.

### Index of changes

#### Added

- **Live ESSC 2026 programme page** at `/essc-2026.html` (+ FR + DE), sourced from a daily Indico sync (`scripts/sync-indico.py` + `.github/workflows/sync-indico.yml`, runs 03:45 UTC). Schema-compatible with EISS's programme generator. Home-page Events block, sitemap, and `calendar.ics` link to the live page rather than directly to Indico. New `data/indico.json` artefact. New `docs/indico-sync.md` documenting the pipeline.
- **Member preview popover** on the ESSC programme. Tap or hover a member-linked speaker name and a glass card opens with photo, position, affiliation, country, role + WG chips, bio excerpt, contact icons, and a deep-link CTA. Position is computed in JS (viewport-flipped, edge-clamped). Class family is `.essc-member-card*` to avoid colliding with the directory's `.member-card`.
- **Member-aware speaker links** on the programme. Names that match a `bios.json` record become dotted-underlined anchors to `/people.html#<slug>`. JS port of `name_key()` with diacritic / honorific / post-nominal / particle stripping. Optional `name_aliases: []` field on bios records for hard-to-match cases — documented in `docs/bios-setup.md`.
- **Collapsible Shipped list** on `/roadmap.html` (+ FR + DE). One toggle injected per `<ol class="rm-timeline">` that has shipped entries. Locale-aware labels. JS-off graceful degrade leaves entries visible.
- **CSS class-collision lint** (`scripts/check-css-class-collisions.py` + `.github/workflows/css-class-collisions.yml`). Catches same-class declarations >200 source lines apart and orphan BEM children. Inline suppression marker for legit cross-cutting patterns.
- **Particles drop in `name_key()`** (Python + JS). 24 nobiliary / patronymic connectors (de, van, von, da, della, etc.) excluded from the key so "Jéssica da Costa Pereira" matches "Jéssica da Costa".
- **`console.debug` unmatched-speaker log** on the programme render. Filtered to keyable names; surfaces near-misses during preview.
- **Three writing-voice rules** in `CLAUDE.md` §6 + §7: no "source of truth" on public copy, no em dashes, no rule-of-three rhythm, no synonym cycling.

#### Changed

- **`/people.html` deep-link spotlight is now persistent.** The 3.5 s auto-fade is gone; the spotlight clears when the visitor types in search, clicks a different card, focuses a filter, or changes the country select. Visual treatment strengthened: accent-2 outline + 6 px halo + 14 px drop shadow + subtle tinted background. Hash is stripped on dismissal.
- **Linked speaker names on the programme read as tappable at rest.** Resting state: dotted underline at full accent-2 opacity + a 70 / 30 colour mix of accent-2 / `--ink` for the text. Hover / focus brings the text to full accent-2. Replaces the earlier 55 %-transparent dotted underline that was effectively invisible at rest on a touch device.
- **Roadmap retro-truth-up**: v1.4.0 + v1.5.0 marked Shipped with their actual content; the "Official logos and social channels" milestone moved to *Under watch* with a clear external trigger.
- **Sitemap + calendar.ics** updated to reflect the NetSec-hosted ESSC live programme as the canonical URL. ESSC entry in `data/events.json` URL flipped from `indico.eiss-europa.com/event/22/` to `netsec-cost.eu/essc-2026.html`; Indico stays in the calendar `DESCRIPTION` as a registration link.

#### Fixed

- **Directory regression on `/people.html`.** The ESSC popover's CSS used `.member-card` — the directory's own class since launch. The new rules (`position: fixed; width: 360px; box-shadow; overflow: hidden`) cascaded onto every directory card and stacked all 13 of them at the viewport's top-left. The reported symptom — "only Arthur Laudrain shows, his card is half blue" — was 13 cards stacked, with `var(--bg-1)` showing through where the width clamp narrowed them. Renamed the entire popover class family to `.essc-member-card*` across CSS + JS in all three locale files; directory's own rules untouched.
- **Popover light-dismiss and visibility** in early popover drafts. The card was rendering with no background because `var(--surface)` / `var(--border)` / `var(--surface-2)` referenced design tokens that don't exist on this site (it uses `--bg-1` / `--line`). Without visible chrome, clicks that the visitor thought were "outside the card" often landed inside the invisible bounds, and the Popover API correctly didn't dismiss. Fix: use the tokens the site actually defines, add glassmorphism (`backdrop-filter: blur(18px)`), add a scroll-dismiss listener.
- **Pulse-dot vertical alignment** beside the "Live programme" heading on `/essc-2026.html`, pulled rightward from the heading column edge after multiple fine-tunes.
- **Search-overlay landing wrapped highlighted terms in a nested `<mark>`.** Two highlight passes were running on the same hits — Pagefind's `PagefindHighlight` constructor calls `this.highlight()` itself, and our bootstrap then explicitly called `ph.highlight()` a second time. Screen readers announce the inner mark twice (*"STSM, mark, STSM, mark"*); visual rendering is unaffected. Dropped the explicit call, kept the constructor's. Resolves [#118](https://github.com/EISSeuropa/netsec.github.io/issues/118).
- **Skip-link target inconsistency**: the home page's skip-link pointed at `#top` while every other page pointed at `#main`. Mechanically both work — they hit `<main>` — but the inconsistency was confusing. Renamed the home's `<main>` from `id="top"` to `id="main"` across EN / FR / DE and updated the skip-links accordingly. Resolves [#120](https://github.com/EISSeuropa/netsec.github.io/issues/120).

🤖 _Authored with help from [Claude Code](https://claude.com/claude-code)._



## [1.5.0] · 2026-05-22 — Pre-launch polish and accessibility v1.2

> The pre-launch quality pass. v1.5.0 closes the launch-QA loop before the public push — a swarm of polish fixes that surfaced from the user-journey sweep, an accessibility statement bumped to v1.2 with three new audit results, a hybrid release-notes format rolled out across the whole CHANGELOG so future releases read consistently, and the documentation pack caught up to v1.7.0.

### Pre-launch polish

Six user journeys × four-viewport sweep (desktop + iPhone-emulated mobile) ran end-to-end in headless Chromium across the eight most-trafficked pages. Three findings shipped in this release:

- **The FR / DE beta-translation ribbon said "machine translation"; the translations are manual.** Public-facing falsehood about how the site is built, directly contradicting the standing project constraint baked into the architecture doc and the documentation PDF. Corrected across 35 files: FR ribbon copy → *"Traduction manuelle"*, DE ribbon copy → *"Manuell übersetzt"*, EN top-of-file comments → *"manually translated"*, the accessibility statement, and the longer privacy-page ribbon flavour.
- **The mobile hamburger menu's panel was transparent in dark mode** — the floating-header bubble's own `backdrop-filter` and the panel's nested one didn't re-stack reliably, so the hero text bled through behind every nav item. Pinned the drawer to near-opaque (rgba(246,248,252,.97) / rgba(11,18,32,.97)) scoped to the mobile breakpoint, with a stronger elevation shadow.
- **`/people.html#<slug>` deep-links could fail to spotlight + expand the target card on cold load.** The whole hash-handler was wrapped in `requestAnimationFrame`; when RAF deferred (headless Chromium, plausibly real browsers under heavy load), nothing fired. Pulled the spotlight + expand class-manipulations out of RAF — they're layout-safe — and kept only `scrollIntoView` behind it, with a `setTimeout(50)` belt-and-braces fallback.

### Accessibility statement v1.2

Three new audits ran on top of the Phase 2 baseline from the earlier v1.1 statement: a programmatic structural assistive-technology audit of the four most-trafficked pages (landmarks, heading hierarchy, alt-text coverage, accessible names on every interactive element, label association on inputs — all clean); an Open Graph + Twitter Card metadata sweep on home / about / roadmap / press-kit with a render-check of the 2400×1260 shared `og-image.png`; and a dark-mode readability sweep across all sixteen public English pages, with both a per-element programmatic contrast probe and visual review. No new low-contrast findings surfaced beyond the manual-review item already documented on `/accessibility.html`. The statement at `/accessibility.html` (+ FR + DE) is updated to v1.2 with these results and the three corrections above explicitly referenced.

### Release-notes hybrid format

Adopted across the whole CHANGELOG, with the structure-rule documented in three places (the CHANGELOG preamble itself, `docs/admin-guide.md` *Cutting a release*, and the header comment in `scripts/release.sh`). The shape: lede + 2-4 themed `### sub-sections` + a canonical `### Index of changes` block with `#### Added` / `#### Changed` / `#### Deprecated` / `#### Removed` / `#### Fixed` / `#### Security` sub-headings. Self-policing tier: patch releases skip the lede + themes and ship the index only; minor and major releases get the full hybrid. v1.0.0 → v1.4.0 were retrofitted in place and their GitHub Release bodies overwritten to match. A `<!-- TEMPLATE -->` block at the top of `[Unreleased]` shows the shape so the next maintainer doesn't reverse-engineer it. A separate rule was added afterwards explaining why CHANGELOG prose must not be hard-wrapped: GitHub Releases use the *break-on-newline* GFM variant and every soft `\n` becomes a `<br>`, so a hard-wrapped paragraph renders narrow on the Releases page even though it looks flowing on the github.com file view.

### Launch-QA plan + automation

`docs/launch-qa-2026.md` lays out a three-phase audit (automation pre-flight → critical user journeys → a11y + cross-browser + perf) with explicit Go / No-Go criteria, a schedule, a tooling cheatsheet, and a findings log that survives past the launch as the audit trail. Two new scripts back it: `scripts/check-links.sh` (broken-link checker, Python-only, threads with per-host rate-limit-respecting concurrency, validates `people.*.html#<slug>` deep-links against `data/bios.json`, skips known auth-gated hosts) and `scripts/check-a11y.sh` (pa11y scan, aggregates per-page summary into `tmp/a11y-report.md`). New CI workflow `launch-qa-link-check.yml` runs the link checker on every HTML-touching PR and weekly on main. The findings log records the journey results, the I-1 / M-1 / J4-1 fixes, and the four "green" final-pass audits (VoiceOver-substitute, OG metadata, dark-mode sweep, structural AT).

### Index of changes

#### Added

- **Release-notes hybrid format**, applied across the whole CHANGELOG. v1.0.0 → v1.4.0 retrofitted in place and their GitHub Release bodies overwritten to match. Format rule documented in three places (CHANGELOG preamble, `docs/admin-guide.md`, `scripts/release.sh` header). Shape: lede + 2-4 themed `### sub-sections` + canonical `### Index of changes`. Self-policing tier: patch releases skip the lede + themes. Template block at the top of `[Unreleased]`. Companion rule against hard-wrapped prose (GitHub Releases renders soft `\n` as `<br>`).
- **Launch-QA plan + automation** for the late-May 2026 public push. New `docs/launch-qa-2026.md` lays out the three-phase audit with Go / No-Go criteria, schedule, tooling cheatsheet, findings log. Two new scripts (`scripts/check-links.sh`, `scripts/check-a11y.sh`) and a new CI workflow (`launch-qa-link-check.yml`).
- **Documentation pack refreshed to v1.7.0** — cover stamp bumped, changelog appendix entry recording what the pack now reflects (site v1.4.0 → v1.5.0), and a section-level catch-up scheduled for v1.8.0.

#### Changed

- **Accessibility statement bumped to v1.2** on `/accessibility.html` (+ FR + DE). New paragraph in the audit narrative covering three additional final-pass checks (structural AT audit, OG metadata sweep, dark-mode sweep). Three new bullets in the methods list. Version footer updated; *Last assessed* stays at 22 May 2026 (same day).
- **`scripts/check-a11y.sh` switched from `@axe-core/cli` to pa11y.** The original CLI requires a system Chrome that matches a system ChromeDriver — brittle. pa11y wraps the same axe-core engine behind a Puppeteer-bundled headless Chromium that doesn't depend on the system pair. Fixed a heredoc-vs-stdin race in the report generator while in there.

#### Fixed

- **Seven primary-CTA backgrounds failed WCAG AA contrast in dark mode.** The dark-mode `--accent` is `#6ea1ff` (lighter blue, chosen so accent text reads against the dark page). Buttons using `background: var(--accent); color: #fff` directly collapsed to 2.56:1 — below the 4.5:1 AA floor. Affected: `.event-card.featured .event-date`, `.event-subscribe`, `#for-members .members-actions .primary` (home); `.tour-btn-primary`, `.tour-trigger-cta` (people); `.deliverables-roadmap-link-cta` (about); `.rm-feedback-action.is-primary` (roadmap). Fix: pin those CTAs to brand EU-blue `#003399` in dark mode (10.86:1) plus a `#0a4ed0` hover (11:1). Surfaced by Phase 2 of the launch-QA audit.
- **FR / DE beta-translation ribbon misclaimed "machine translation".** The translations are manual. Public-facing falsehood about the build methodology, contradicting the standing project constraint. 35 files corrected: FR copy → "Traduction manuelle", DE copy → "Manuell übersetzt", EN HTML comments → "manually translated", accessibility statement updated.
- **Mobile hamburger menu drawer was transparent in dark mode** — hero text bled through behind nav items because the nested `backdrop-filter` didn't re-stack inside the floating-header bubble. Pinned the drawer to ~97 % opacity (rgba(246,248,252,.97) / rgba(11,18,32,.97)) scoped to `@media (max-width: 980px)`; bumped `box-shadow` so the drawer reads as elevated.
- **`/people.html#<slug>` hash-deep-link spotlight + expand could fail to fire on cold page load.** Handler was wrapped end-to-end in `requestAnimationFrame`; if RAF deferred (headless reliably, real browsers under load plausibly), none of the spotlight / expand / scroll actions ran. Pulled the class-manipulations out of RAF (layout-safe); kept `scrollIntoView` behind RAF with a `setTimeout(50)` fallback. Applied identically across `people.html` / `people.fr.html` / `people.de.html`.
- **Nine broken internal anchors** caught by the new link checker. `faq.{en,fr,de}.html` and `licensing.{en,fr,de}.html` still pointed at `index.html#committee`, `#roadmap`, `#outputs` — sections that the Phase 1 IA pass migrated to dedicated pages. Updated to `about.X.html#leadership`, `roadmap.X.html`, `outputs.X.html`.

## [1.4.0] · 2026-05-22 — Site-wide search, infrastructure and directory improvements

> The largest release since launch. In the two days since v1.0.0 the site doubled in surface area — site-wide search, a Phase-1 IA pass that gives the home page room to breathe, a public roadmap, a proper brand favicon, and the infrastructure work that turns Pagefind from a recurring PR-conflict source into a deploy-time artefact. The shape of the site for the late-May public push.

### Site-wide search

The button you'd expect, where you'd expect it. Magnifying-glass in the nav, Cmd-K or `/` anywhere outside an input. Modal overlay, results scoped to the visitor's locale automatically (Pagefind per- language shards key off `<html lang>`), per-section deep-link anchors so long pages like FAQ and Glossary jump straight to the matched section. Snippets highlight with the EU-yellow `<mark>` from the press kit, on-page highlighting on landing too. Privacy posture preserved: index served from `/pagefind/` on `netsec-cost.eu`, queries never leave the visitor's browser, no third-party calls. Lazy-loaded on first overlay open. Design history in `docs/search-assessment.md`.

**Directory bios are searchable.** A name search returns a rich card with the member's photo, country flag, role, and WG chips — rather than the plain page-text card used elsewhere. Member data is rendered as Pagefind index stubs under `search/bios/<lang>/<slug>.html` at build time, in all three locales, so a French visitor searching *"Laudrain"* hits the French shard too.

### Phase 1 information-architecture pass

The home page had ten sections after v1.0; the floating header ran at ten nav items. Every new release added more. Time to redistribute.

- **New `/about.html`** consolidates the Action narrative, the deliverables Gantt, the leadership grids, and FAQ + Glossary teasers. The home-page *About* anchor still carries the short intro; the dedicated page is the full story.
- **New `/outputs.html` and `/news.html`** stub pages — both ready to receive content as it accrues.
- **Header nav reduced from 10 to 8 items.** *Committee* and *Roadmap* and *Outputs* dropped as standalone nav entries; *About* points to the new `/about.html`; *Outputs* renamed to *Publications*.
- **Home page slimmed by ~25%.** EN / FR / DE go from ~990 / ~905 / ~905 lines down to ~745 / ~660 / ~660. Phase 2 of the IA pass (audience tracks, mobile patterns, deeper UX work) runs Jul–Aug 2026 and ships in v1.7.0; this round is the structural redistribution that needed to land before official logos in v1.5.

### Public roadmap

`/roadmap.html` (+ FR + DE). Visual, audience-facing companion to the internal `docs/roadmap-2026.md`. Vertical timeline grouped by quarter; four-pill status legend (*Shipped* — green, *In progress* — blue, *Planned* — purple, *Under watch* — amber); twelve dated entries interleave shipped releases (v1.0 → v1.3), the in-progress v1.4, planned v1.5 → v1.8, and the Action's own milestones (Stockholm Conference + Summer School, inaugural MC plenary, Year-1 anniversary). *Under watch* section at the foot lists deferred items with explicit triggers ("kick off the sticky-side-panel work if membership crosses ~150 OR an MC member reports friction"). A "Help shape this" card frames the roadmap as participatory and points readers at GitHub Issues + Discussions. Manual translations only — no machine translation.

Signposted in two places: a 4th card in the home-page *Find out more* grid, and an accent callout at the foot of the Deliverables section on `/about.html`.

### Infrastructure, quietly improved

- **Pagefind built at deploy time, not committed to main.** Two parallel PRs that both touched HTML used to conflict on the index manifest (content-hashed shard filenames diverging). The new Pages-deploy workflow rebuilds the index on every push and deploys via the artifact + `actions/deploy-pages` flow; `/pagefind/` is now gitignored. PR conflicts on the index are structurally gone.
- **iCalendar feed at `/calendar.ics`** + *Subscribe to NetSec events* CTA on the home page. Single-source-of-truth pipeline: generated from `data/events.json` by `scripts/build-calendar.py`; CI fails any PR where the JSON and the generated ICS disagree.
- **Brand favicon replacing the Mobirise placeholder.** New SVG favicon — rounded square in the EU-blue → Apple-blue gradient with "NS" in white, matching the in-header brand mark. Visitors no longer see a pink phone-with-sun icon in their browser tab.
- **Persistent lint against trailing arrows on external links** (`scripts/check-external-link-arrows.py` + CI workflow). The site CSS auto-injects an external-link icon after every `<a target="_blank">`, so a manually-typed arrow on top renders a double affordance — the lint catches it before merge.
- **Release-cutting now requires a short title** as a positional argument to `scripts/release.sh`. Past titles retitled to match the convention.

### Directory polish

The compact-view cards on `/people.html` got two improvements that make the underlying click-to-expand pattern discoverable. First, a small circular chevron at the bottom-right of every compact card — ▼ when collapsed, rotates to ▲ when expanded. Hidden in detailed view. Touch-friendly. Second, **search-result clicks on a directory entry now visually confirm the landing** with a 2 px accent-blue outline and a soft glow that auto-fades after 3.5 s.

### Polish + bug fixes

The full list is in the index below. Two patterns worth flagging:

- **Search overlay had several issues** that hadn't surfaced under light testing — backend returning *"SEARCH IS UNAVAILABLE"* (a stray filter argument), the modal sitting on top of the navigated page so users couldn't tell their click had worked, the Cmd-K shortcut breaking on non-QWERTY layouts. All fixed before the public push.
- **Mobile + IA aftermath.** The IA pass moved sections off the home page but a few stale references followed — a *Meet the team* link to a defunct anchor, the Gantt's responsive grid collapsing oddly at narrow widths, the mc-subhead dividers wrapping onto two lines. Caught during the launch-QA pass and fixed in the same window.

### Index of changes

#### Added

- Site-wide search via Pagefind (modal overlay, Cmd/Ctrl-K, `/`, per-locale shards, deep-link anchors, EU-yellow `<mark>` highlights, lazy-loaded, privacy-preserving).
- Directory bios searchable, rich result card with photo + flag + role + WG chips.
- `/about.html` (+ FR + DE) consolidating the Action narrative, deliverables Gantt, leadership grids, FAQ + Glossary teasers, EISS placeholder.
- `/outputs.html` and `/news.html` (+ FR + DE) stub pages.
- `/roadmap.html` (+ FR + DE) public roadmap with visual timeline, four-status legend, "Help shape this" community feedback card.
- Roadmap signposted on the home-page *Find out more* grid (4th card) and the About-page Deliverables section (accent callout).
- iCalendar feed at `/calendar.ics` + *Subscribe to NetSec events* CTA + single-source-of-truth pipeline from `data/events.json` with CI drift check.
- Brand favicon (`assets/images/favicon.svg`) replacing the Mobirise pink-phone-with-sun placeholder. 256 × 256 PNG fallback re-rendered. 43 page-locales updated.
- FAQ + Glossary teaser sections on the About page (5 FAQs + 8 glossary terms each, deep-linked to their full pages).
- Expand / collapse chevron on directory compact cards.
- `scripts/build-search.sh` + `.github/workflows/search-drift.yml`. Pagefind pinned to 1.5.2.
- `scripts/check-external-link-arrows.py` + CI workflow.
- Wiki link in every page footer (EN / FR / DE).
- Sync convention noted in `docs/roadmap-2026.md` + *Last reviewed* line on each public roadmap.

#### Changed

- Header IA: nav reduced from 10 to 8 items (canonical order *News · About · Working Groups · Network · Events · Grants · Publications · Contact*).
- Home page slimmed by ~25% — Committee + Roadmap + Outputs migrated to dedicated pages.
- `/sitemap.html` (+ FR + DE) rebuilt to match the new IA.
- Pagefind index moved from committed-to-main to built-at-deploy-time. `/pagefind/` now gitignored. Pages source flipped to *GitHub Actions* deploy.
- `search-drift.yml` simplified to a build-sanity check.
- `scripts/release.sh` now requires a short title as a second positional argument. Historical release entries retitled.

#### Fixed

- Search backend now works (was returning *"SEARCH IS UNAVAILABLE"* due to a bogus `filters` argument).
- Search results deep-link to the matched item and highlight the term on landing; the overlay closes on result-link click so the navigation is visible.
- Member-name search no longer false-positives on the home page (MC-by-country grid wrapped with `data-pagefind-ignore`).
- `Cmd-K` / `Ctrl-K` hardened — checks `e.code === 'KeyK'` so non-QWERTY layouts still work; listener moved from `document` to `window`.
- Search trigger no longer overflows the floating header on the home page (⌘K badge hidden; shortcut still discoverable via title + overlay).
- Windows / Linux users see *Ctrl K* in the search-button tooltip rather than the generic *Cmd/Ctrl-K*; adds `aria-keyshortcuts`.
- Directory bio cards now show the full biography text (dropped the rAF wrapper around the *Show more* detection; ResizeObserver belt-and-braces).
- Search-result clicks on a directory entry visually confirm the landing (accent-blue spotlight + auto-fade).
- Public-roadmap milestone cards no longer render as saturated-blue panels with unreadable text (class-name collision with the Gantt-pill `.milestone` rule — renamed to `.rm-milestone`).
- Status pill on roadmap timeline centred on the marker dot (`top` 16 → 19 px / 18 → 21 px).
- Beta-translation ribbon now present on all 14 recently-added FR/DE pages (`data-i18n-status="beta"` + the ribbon div).
- Beta-translation ribbon no longer overlaps the floating header on mobile (CSS offsets derived from a JS-measured `--ribbon-h`).
- *Meet the team* link on the home-page news block points at the new About page anchor.
- Gantt chart no longer misaligns on mobile (year row uses `repeat(4, minmax(184px, 1fr))`).
- `.mc-subhead` section dividers no longer wrap onto two lines on narrow screens (flexbox + `flex: 0 0 48px` on the pseudo-elements).
- Header crowding on the home page addressed by hiding the *NetSec* wordmark in the floating bubble.
- Events section: double-icon on external-link CTAs removed (hardcoded right-arrow stripped; auto-icon remains).
- Subscribe-to-events button now prominent and centred (was a small bordered chip in the margin).
- `.gitignore` now excludes `.DS_Store` site-wide.

## [1.3.0] · 2026-05-21 — Introducing FAQ and Glossary pages

> The reference content lived on the members' Wiki, which means it lived on GitHub — and academics, journalists, and prospective members don't naturally browse to GitHub. v1.3.0 brings the FAQ and the Glossary to the public site so the people who actually need them can find them.

### Reference content goes public

**Public FAQ at `/faq.html`** (plus FR + DE) — 21 Q&As across six themed sections (*About the Action* / *Joining & participating* / *Grants & funding* / *Meetings & reimbursement* / *Website & directory* / *For NetSec members*), with a jump-to TOC and per- question deep-link anchors. The Wiki FAQ page now stubs to this URL.

**Public Glossary at `/glossary.html`** (plus FR + DE) — ~35 COST and NetSec terms grouped into five sections (*COST framework* / *NetSec structure* / *People* / *Grants & meetings* / *Documents & outputs*), with per-term anchors. Same migration rationale.

The source of truth is now in one place — the public pages — so the FAQ and Glossary can't drift between two surfaces.

### Discovery surfaces on the home page

Reference content that nobody can find isn't reference content. Two new affordances make the FAQ and Glossary visible from the front door:

- A **four-card *Find out more* grid** at the end of the About section, pointing at FAQ / Glossary / Press kit / Members' Wiki. Keeps the header at ten items while surfacing the reference pages at a glance.
- A **"For NetSec members" strip** between Outputs and Contact, with two CTAs — *Open the Wiki* and *e-COST portal*. MC reps and WG participants don't drift to GitHub on their own; the strip leads them there.

Both localised in EN / FR / DE.

### External-link icon polish

The auto-injecting external-link icon introduced in v1.2.0 had four related regressions, all rooted in CSS specificity:

- **Specificity bug**: the global selector was `(0,0,2,2)`; every exclusion (`.cost-mark::after`, `.socials a::after`, etc.) was weaker and silently lost. The icon appeared on the COST mark, the EU mark, the GitHub footer link, the language switcher, the social-icon row on member cards, and stacked on top of inline arrows inside *Apply on e-COST* buttons. Fix: wrapped the global selector in `:where()` so it contributes 0 to specificity; every exclusion wins naturally.
- **Flex-shrink collapse**: inside flex containers the `::after` became a flex item with default `flex-shrink:1` and collapsed to width 0 — *Resources & reference documents* cards on the Grants page appeared to have no external-link indicator. Fix: `flex:none` on the pseudo-element.
- **Double-arrow on news cards**: two news cards carried both a hardcoded `→` and the auto-injected icon. The hardcoded arrow was dropped; the auto-icon remains.

### Index of changes

#### Added

- Public FAQ at `/faq.html` (+ FR + DE) — 21 Q&As, six themed sections, jump-to TOC, per-question deep-link anchors.
- Public Glossary at `/glossary.html` (+ FR + DE) — ~35 COST + NetSec terms, five sections, per-term anchors.
- *Find out more* grid at the end of the home-page About section (FAQ / Glossary / Press kit / Members' Wiki).
- *For NetSec members* strip between Outputs and Contact, with *Open the Wiki* + *e-COST portal* CTAs.
- FAQ + Glossary links in every page's footer (24 files).
- Sitemap entries for the two new pages in `sitemap.xml` + the in-page `/sitemap.html` *About & policies* branch.
- SEO metadata for the six new pages via `scripts/inject-seo.py`.
- i18n drift tracking for `faq.html` and `glossary.html`.

#### Changed

- Wiki `FAQ.md` and `Glossary.md` reduced to short stubs pointing at the public pages — single source of truth.

#### Fixed

- External-link icon specificity bug (global selector wrapped in `:where()`).
- External-link icon flex-shrink collapse (`flex:none` on the pseudo-element).
- Double-arrow on news cards (hardcoded `→` stripped from external-link cards).

## [1.2.0] · 2026-05-21 — Press kit, directory tour, compact view

> Three coordinated threads. The press kit goes live so anyone writing about NetSec — journalist, partner, MC member — has one URL to send. The directory gets a guided tour, a compact view, and click-to-expand cards, lowering the friction for first-time visitors. And the repository's branch + tag protection lands, so the release tags become immutable once published.

### Public press kit

**`/press-kit.html`** (+ FR + DE). One canonical URL for outreach. Includes the **promotional A3 poster** (with print + card-size downloads), the NetSec / COST / EU emblems with pairing rules, the colour palette and typography reference, the funding-statement boilerplate in three lengths (full, short, one-line credit), suggested CC BY 4.0 attribution wording, and explicit do / don't rules. Linked from every page's footer between *Licensing* and *Site map*.

The poster source is version-controlled (HTML-to-raster build), so future content changes don't require a manual reflow. A card-size variant ships as the README banner and as Appendix C of the documentation PDF; a member-facing copy-paste page lives at the **Members' Wiki *Templates & press kit*** entry.

### Directory: tour, compact view, click-to-expand

The first-visit directory experience used to assume the visitor knew it was open (not MC-only), knew filters existed, knew where the join form was. The directory now teaches that itself:

- **First-visit orientation strip** above the toolbar — three lines introducing the directory and its affordances. Dismissible; returning visitors never see it.
- **Six-step guided tour** anchored to: search box → filter chips → country dropdown → view-mode toggle → `+` quick-join button → join card. Two entry points (the welcome strip's *Take the tour* button and a persistent `?` button in the toolbar). Keyboard navigable; focus trap; reduced-motion aware. Engine generalised as `window.netsecTour({steps, labels, onComplete})` for reuse.
- **Compact view** — a two-button toggle next to the country filter switches between detailed (photo + bio + contact icons) and compact (initials/photo + name + affiliation + WG chips, three across on desktop). Preference persists per visitor.
- **Click-to-expand on compact cards** — clicking a compact card flips it to its detailed form in place, while every other card on the grid stays compact. Keyboard-focusable, Enter / Space triggers expansion, Esc collapses. The expanded card's slug mirrors to `location.hash` so the state is shareable: `/people.html#eugenio-sanchez` auto-expands that card on load.
- **`+` quick-join button** in the toolbar (bright accent CTA next to the muted `?` tour-trigger), smooth-scrolls to the join card at the foot of the page.

All localised in EN / FR / DE.

### Branch + tag protection

Two GitHub rulesets added to the repo, both visible at the [Settings → Rules → Rulesets page](https://github.com/EISSeuropa/netsec.github.io/settings/rules):

- **`protect-main`** — restricts deletions and force-pushes, requires linear history, requires a pull request before merging, requires all four CodeQL status checks to pass, requires conversation resolution, restricts merge methods to squash. Bypass: the *Repository Admin* role (so `scripts/release.sh` can push the changelog-promotion commit directly).
- **`protect-release-tags`** — restricts deletions, updates, and non-fast-forward updates on tags matching `v*`. **No bypass for anyone** — once a release tag is published, it is immutable.

The release script's docstring is updated to record the consequence: the release-cutter needs the repo `Admin` role (not `Maintain`).

### Grants page transparency

The Grants page used to imply a simple application flow. The reality on e-COST is more nuanced. Updated copy spells it out:

- Applications go through the general e-COST portal (no NetSec-specific form).
- The portal **filters by applicant profile** — ITC schemes are visible only to ITC affiliates; YRIG is visible only to under-40s. A member may not see every scheme listed on the page.
- Only the five schemes on the page are in NetSec's WBP; applications for anything else **will be rejected** by the Grant Awarding Coordinator.

The YRIG and ITC cards gain visibility captions; the Wiki FAQ gains two matching entries; the architecture doc lists the portal model.

### Index of changes

#### Added

- Public press-kit page at `/press-kit.html` (+ FR + DE) with logos, palette, funding-statement boilerplate (3 lengths), CC BY 4.0 attribution wording, do/don't rules.
- A3 promotional poster — HTML source, A3 raster (2480 × 3508 px), card-size variant (800 × 1131), Appendix C of the docs PDF.
- README banner showing the card-size poster.
- Members' Wiki *Templates & press kit* page (copy-paste boilerplate for members).
- Directory first-visit welcome strip.
- Directory guided six-step tour (anchored coachmarks, keyboard navigable, reduced-motion aware, engine reusable as `window.netsecTour(...)`).
- Directory compact view (segmented toggle, three-across grid, density preference persisted).
- Click-to-expand on compact directory cards; deep-link auto-expand on `#<slug>` hash.
- `+` quick-join button in the directory toolbar.

#### Changed

- Grants page now explicitly frames the e-COST portal model (profile-based filtering, NetSec WBP scope, rejection conditions).
- Documentation PDF: new Section 07 (Branch and tag protection); Section 06 (Admin guide) handover checklist rewritten; appendices C/D swapped so the PDF lands on the changelog; PDF title carries its own version; maintainer affiliation simplified to "ETH Zurich".
- `docs/admin-guide.md` handover checklist mirrors the PDF Section 06.
- Press kit page names the maintainer in §9 + the meta footer line.
- `scripts/release.sh` docstring records the Admin-role + PAT-permission requirements implied by the new rulesets.

#### Fixed

- Press-kit page primary buttons no longer render near-black in light theme (scoped EU-blue override, Apple-blue on hover).
- ORCID URL handling resilient to full-URL submissions (new `normalize_orcid()` helper in `sync-bios.py` + render-time normaliser in `people.html`).
- PDF poster image plate is now full-bleed (no more two blank pages flanking the poster).
- Accessibility FR / DE footers now use correctly localised links to Privacy + Licensing + Press kit.
- `LICENSE-CONTENT` now contains the canonical CC BY 4.0 legal-code text (was only the human-readable deed). GitHub's licence detector now identifies the file as CC-BY-4.0.
- PAT permissions clarified to least-privilege (bypass is keyed to *repository role*, not PAT scopes; misleading comment in `release.sh` corrected).

#### Security

- `protect-main` branch ruleset added — PR + linear history + status checks + squash merges; Admin-role bypass.
- `protect-release-tags` tag ruleset added — `v*` tags immutable after publication; no bypass for anyone.

## [1.1.0] · 2026-05-20 — Release tooling and PDF SemVer

> Operational hygiene. Future releases are boring to cut.

### One-command release tooling

**`scripts/release.sh`** lands as the canonical way to cut a release. Validates the SemVer string, runs a pre-flight check (on `main`, clean tree, in sync with origin, tag not yet used), promotes `[Unreleased]` → `[<version>]` in this file, resets a fresh `[Unreleased]`, updates the compare-link block, commits, pushes, creates an annotated `v<version>` tag on the new commit, pushes the tag, and publishes the GitHub Release whose body is the changelog section for the new version. `--dry-run` previews the whole flow without touching anything. Documented in PDF Section 06 *Admin guide → Cutting a release*.

### Documentation pack re-versioned

The stakeholder PDF previously used `v1.0` / `v1.1` / `v1.2` cover stamps — readable, but inconsistent with the website's SemVer discipline. Re-numbered in place to `v1.0.0` / `v1.1.0` / `v1.2.0` (content unchanged); the new cover stamp is **v1.3.0**. Section 06 gains the *Cutting a release* subsection mentioned above. Site screenshots refreshed against the live state.

### Index of changes

#### Added

- `scripts/release.sh` — one-command release helper with `--dry-run` support.

#### Changed

- Documentation PDF cover stamps re-versioned to SemVer (`v1.0` → `v1.0.0`, etc.); current cover stamp is `v1.3.0`.
- PDF Section 06 (Admin guide) gains a *Cutting a release* subsection.
- Site screenshots in the PDF refreshed (`snap-home.png`, `snap-network.png`, `snap-grants.png`).

## [1.0.0] · 2026-05-20 — Initial public release

> The first tagged release. Captures the state of the website and open community directory at the moment Deliverable D1 of COST Action CA24154 (NetSec) is presented for COST review. The site goes live publicly at <https://netsec-cost.eu>.

### The website

Seven public pages plus a designed 404: Home, The Network, Grants & Calls, Sitemap, Accessibility, Privacy, Licensing. Apple-style glass UI, light and dark themes, responsive from 4K screens down to a phone, EU + COST branding throughout. Hosted on GitHub Pages from `main` with HTTPS enforced and a Let's Encrypt certificate auto-managed by GitHub.

### Open community directory (Deliverable D1)

Members join via a public Google Form linked from the Network page. A weekly GitHub Action pulls submissions, deduplicates against the cost.eu MC roster, downloads + resizes headshots, and opens a pull request for human review before publication. `data/bios.json` is the canonical source-of-truth; leadership roles, directory position, and email-keyed identity all survive form re-submissions (see `scripts/sync-bios.py`). The home page's Action Leadership / WG Leadership / WG Co-Leader cards live-refresh from `bios.json` on page load.

### Multilingual support (beta)

Full French and German variants of every public page (sibling `.fr.html` / `.de.html` files; English authoritative). A SHA-1 based drift checker (`scripts/check-i18n-drift.py` + CI) flags translations that need refreshing when English changes. No machine-translation, no recurring API cost. Beta-banner on every non-authoritative page explaining the status and linking back to the English version.

### SEO + discoverability

Open Graph, Twitter Card, JSON-LD (Organization + WebSite + WebPage), canonical URLs, hreflang annotations, and a machine-readable `sitemap.xml` on every page — all generated from a single source-of-truth script (`scripts/inject-seo.py`) with sentinel-bracketed idempotent rewrites.

### Accessibility, security, licensing

- **Accessibility**: WCAG 2.1 AA target, EN 301 549 aligned. Zero axe-core violations on the home page at the v1.0 assessment. Statement at `/accessibility.html`. Skip-links, semantic landmarks, `:focus-visible` rings, `prefers-reduced-motion` honoured.
- **Security**: Five GitHub Advanced Security features enrolled (private vulnerability reporting, security advisories, Dependabot alerts, CodeQL code scanning with the security-and-quality + the security-extended suites, secret scanning with push protection). Pinned third-party Actions; least-privilege `GITHUB_TOKEN`. Coordinated-disclosure policy in `SECURITY.md`.
- **Licensing**: code under MIT (`LICENSE`), content + docs under CC BY 4.0 (`LICENSE-CONTENT`). Both attributed in every page's footer.

### Documentation

- **Stakeholder PDF**: `docs/pdf/NetSec-website-documentation.pdf` (v1.2 at v1.0.0). Cover, key-numbers poster, ToC, six chapters (Overview / Architecture / Design system / Translation / SEO / Admin guide / Security & DevSecOps), three appendices (Accessibility / Licensing / Changelog). Build pipeline at `docs/pdf/build.sh`.
- **Maintainer docs**: markdown reference under `docs/` for anyone working on the site — `architecture.md`, `design-system.md`, `admin-guide.md`, `bios-setup.md`, `i18n.md`, `seo.md`.
- **Members' Wiki**: working space for members + MC reps at <https://github.com/EISSeuropa/netsec.github.io/wiki>. Glossary, FAQ, onboarding, meeting-notes convention, decisions log. Member-editable without PR.

### Operational baseline

- **Domain**: `netsec-cost.eu`, registered at Namecheap under Dr Moritz Weiss (Action Chair), with Dr Arthur Laudrain as admin contact.
- **Hosting cost**: €0/month. GitHub Pages + the Google Form + Formspree's free tier cover everything; domain renewal is the only recurring expense.
- **GitHub org**: `EISSeuropa`. Two-factor authentication enforced at the org level.

### Index of changes

#### Added

- Public website at <https://netsec-cost.eu> on GitHub Pages, HTTPS-enforced.
- Seven public pages + 404: Home, The Network, Grants & Calls, Sitemap, Accessibility, Privacy, Licensing.
- Apple-style glass UI with light + dark themes; responsive 4K → phone.
- EU + COST branding throughout (`cost-logo.jpg` + EU emblem SVG with proper visual-identity proportions).
- Open community directory (Deliverable D1) + Google Form intake + weekly auto-PR sync (`scripts/sync-bios.py`).
- Home-page leadership cards live-refreshed from `data/bios.json`.
- French and German beta variants of every public page; SHA-1 drift checker via `scripts/check-i18n-drift.py` + CI job.
- SEO injector (`scripts/inject-seo.py`) — canonical, OG, Twitter Card, JSON-LD on every page; `sitemap.xml`.
- WCAG 2.1 AA accessibility statement (`/accessibility.html`) with zero axe-core violations on the home page.
- GitHub Advanced Security: private vulnerability reporting, security advisories, Dependabot alerts, CodeQL (security-and-quality + security-extended), secret scanning + push protection.
- Coordinated-disclosure policy in `SECURITY.md`.
- Stakeholder PDF documentation pack at `docs/pdf/NetSec-website-documentation.pdf` (v1.2).
- Maintainer markdown docs under `docs/` (architecture, design-system, admin-guide, bios-setup, i18n, seo).
- Members' Wiki seeded with glossary, FAQ, onboarding, meeting-notes convention, decisions log.
- Dual licensing — MIT for code, CC BY 4.0 for content + docs.

[Unreleased]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.10.0...HEAD
[1.10.0]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.9.0...v1.10.0
[1.9.0]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.8.1...v1.9.0
[1.8.1]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.8.0...v1.8.1
[1.8.0]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.7.0...v1.8.0
[1.7.0]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.6.1...v1.7.0
[1.6.1]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.6.0...v1.6.1
[1.6.0]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/EISSeuropa/netsec.github.io/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/EISSeuropa/netsec.github.io/releases/tag/v1.0.0
