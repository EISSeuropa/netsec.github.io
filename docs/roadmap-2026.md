# NetSec website + directory — 2026 roadmap

> *Audience: Action Chair, Vice-Chair, MC members, and the site
> maintainer. Covers the website and the open community directory
> (Deliverable D1) across all of 2026 — what's shipped, what's
> next, who needs to decide what, and when.*

Maintained by Dr Arthur Laudrain (MC member, CH; ETH Zurich).
Last revised **29 August 2026** (v1.12.0 shipped 17 June and v1.13.0 on 22 July, both earlier than this document had them, so the timeline rows below were resynthesised against the CHANGELOG). v1.10.0 shipped 31 May, ahead of its 5 June target. Since then the planned v1.10.1 patch was dropped and its quality-and-content scope folded into **v1.11.0**, cut on 8 June, the day before Stockholm opened, as a large pre-conference directory release. The feature work originally pencilled for a July v1.11.0 shifted to a new **v1.12.0**, and the December "Year 1" release became **v1.13.0**, which was pulled forward first to late August and then cut on 22 July. Six planned releases now interleave with the Action calendar: **v1.8.1** shipped **27 May** as a quality patch covering the work accumulated since v1.8.0 (founding contributors section, home-page events refresh, release-infrastructure hygiene, `sync-cost.py` per-bio WG sync, beta-translation ribbon language-switch fix, FR / DE prose em-dash sweep). **v1.9.0** shipped **29 May** (cut roughly a week early), ahead of the Training School + ESSC in Stockholm: per-event `.ics` files at `/calendar/<slug>.ics` driving a per-card *Add to calendar* dropdown (Google / Outlook / Apple webcal / direct .ics), news RSS feed at `/news.xml` (sourced from a new `data/news.json`), and a structural refactor so home-page event and news cards derive from JSON instead of hand-coded HTML across three locales, including a five-line clamp + Read more affordance for longer descriptions ([#249](https://github.com/EISSeuropa/netsec.github.io/issues/249)). D10 if ready. **v1.10.0** (shipped **31 May**, ahead of the 5 June target) version-tagged what had already merged since v1.9.0: ESSC co-author bylines, the roadmap-card automation, the Indico-sync change summary, and the sync-cost Gap C fix. The co-author feature makes it a minor, not a patch. **v1.11.0** shipped **8 June** as the pre-conference directory release, gathering everything merged since v1.10.0: directory filters by research theme, research region and mentorship ([#555](https://github.com/EISSeuropa/netsec.github.io/issues/555), [#498](https://github.com/EISSeuropa/netsec.github.io/issues/498)), the mobile filter sheet rebuilt as a native `<dialog>` (settling the iOS render and responsiveness saga), LinkedIn and Bluesky footer links, hand-designed social cards, WebP headshots ([#269](https://github.com/EISSeuropa/netsec.github.io/issues/269)), the directory Early Access banner, About-page deliverable statuses, the Working Groups page sections, keyword and affiliation data-quality fixes ([#505](https://github.com/EISSeuropa/netsec.github.io/issues/505), [#506](https://github.com/EISSeuropa/netsec.github.io/issues/506)), and the accessibility statement refresh to v1.3. **v1.12.0** shipped **17 June** as *A working directory and life after Stockholm*, and it pulled in most of what this document had pencilled for v1.13.0: STSM host matching ([#760](https://github.com/EISSeuropa/netsec.github.io/issues/760)), ORCID-powered recent publications ([#761](https://github.com/EISSeuropa/netsec.github.io/issues/761)), shareable per-member profile pages ([#762](https://github.com/EISSeuropa/netsec.github.io/issues/762)) and the mentorship matching view ([#763](https://github.com/EISSeuropa/netsec.github.io/issues/763)), alongside the directory self-growth work ([#758](https://github.com/EISSeuropa/netsec.github.io/issues/758) + [#236](https://github.com/EISSeuropa/netsec.github.io/issues/236)), the Outputs publications pipeline for the D6 briefs ([#726](https://github.com/EISSeuropa/netsec.github.io/issues/726)), a dedicated Events page ([#927](https://github.com/EISSeuropa/netsec.github.io/issues/927)), and a platform-quality layer. **v1.13.0** followed on **22 July** as *Introducing Mentorship Matching 2.0*, rebuilding the matching panel around a guided sentence with live re-ranked matches, recasting the profile pages, adding LinkedIn to the social pipeline beside Bluesky, giving News an issue-driven publishing path, and taking an editorial design pass across the site. It also moved the Indico write path onto the supported `netsec-dispatch` plugin CLI. The structural refactors that had been listed against v1.13.0 did not travel with it: photos out of git ([#119](https://github.com/EISSeuropa/netsec.github.io/issues/119)), events derived ([#170](https://github.com/EISSeuropa/netsec.github.io/issues/170)), the two-repo workflow ([#325](https://github.com/EISSeuropa/netsec.github.io/issues/325)) and the first usage analytics ([#727](https://github.com/EISSeuropa/netsec.github.io/issues/727)) are all still open against v1.14.0. That release is the Year-2 flagship **NetSec Network Map** ([#764](https://github.com/EISSeuropa/netsec.github.io/issues/764)), due early October, and it carries the Year 1 retrospective ([#765](https://github.com/EISSeuropa/netsec.github.io/issues/765)) through to publication at the anniversary. The per-release narrative further down still lags from the v1.4.0–v1.8.0 cycle. That catch-up is queued ([#229](https://github.com/EISSeuropa/netsec.github.io/issues/229)) and the public CHANGELOG remains authoritative for shipped scope and dates.

<!-- AUTOSTAMP:BEGIN -->
> _Auto-tracked: **9 entries** in [`[Unreleased]`](../CHANGELOG.md#unreleased) since **v1.14.0** (1 Added, 1 Changed, 7 Fixed). Last refresh by `scripts/sync-roadmap.py`: 2 Sep 2026. Prose in the timeline below may lag; the maintainer resynthesises on release-time §5 sweep._
<!-- AUTOSTAMP:END -->

> **Sync convention.** This file is the source of truth. The
> public-facing summary at [`/roadmap.html`](../roadmap.html) (+ FR
> + DE) is a derived view. Whenever you edit this document, scan
> the three public-roadmap pages for entries that need to follow
> — and bump the *Last reviewed* line on each. Most edits to this
> file don't touch the public view (audit-scope tweaks, decision
> deadlines, maintainer reasoning); a release shipping, a date
> slip, or a scope change to a card title or description does.

---

## At a glance — 2026 timeline

The two columns on the right read in chronological order. Action
milestones (conference, plenary, anniversary) and website
releases (`v1.x.0`) are interleaved so the site cadence sits
alongside the Action's own calendar. The public-facing summary at
[`/roadmap.html`](../roadmap.html) is the same information
rendered visually.

| When | What | Detail |
| --- | --- | --- |
| 20 May 2026 | ✅ **v1.0.0–v1.3.0** | Initial site, release tooling, FAQ + Glossary (back-to-back same week as the v1.0 launch sprint) |
| 22 May 2026 | ✅ **v1.4.0** | Site-wide Pagefind search · `/about` page · Phase 1 IA · iCalendar feed |
| 22 May 2026 | ✅ **v1.5.0** | Launch-QA polish · accessibility statement v1.2 · hybrid release-notes format |
| 23 May 2026 | ✅ **v1.6.0** | Live ESSC programme on `/essc-2026.html` · member-preview popover · collapsible shipped-list on the public roadmap · CSS class-collision lint |
| 24 May 2026 | ✅ **v1.6.1** | Pre-ESSC polish: per-session room badges + column alignment + inline-expand abstracts on the programme · Practical-info section on `/essc-2026.html` · sync-indico opens a PR + patches `events.json` + `calendar.ics` · mobile home + ribbon contrast · footer copy hygiene |
| 24 May 2026 | ✅ **v1.7.0** | Directory research-interest keyword pipeline (Phase 1 chips on cards · Phase 2 `data/keyword-aliases.json` + sync canonical normalisation · Phase 3 filter chip row above the grid with URL-hash persistence) · bios-sync robustness (Google Forms photo-replacement workaround, truthy-merge regression tests, defensive `PHOTOS_CHANGED` tracking, self-describing auto-PRs) · release-time automation (autostamp workflow, `promote-roadmap.py` flipping public-roadmap cards across EN/FR/DE, PDF cover reminder, open-issue audit) |
| 25 May 2026 | ✅ **v1.8.0** | Pre-Stockholm cut: NetSec brand identity across all 46 pages (header lockup + dark variant, favicon family, OG card, JSON-LD logo) · two new Indico operational scripts (`indico_patch.py` for fix-plans · `indico_clean_duplicate.py` for ESSC-N to ESSC-N+1 rollover, Phase 1.5 admin-flag unlock documented) · programme page self-identifying print-to-PDF (cover masthead, running header, page counter) · bios-sync + cost-sync maintainer notifications via `reviewers: APB-LDN` · retroactive CLAUDE.md §7 voice-rule sweep across EN public HTML. Original v1.8.0 scope (per-event `.ics`, news RSS, D10) was deferred. |
| 27 May 2026 | ✅ **v1.8.1** (patch) | Quality patch covering the work accumulated since v1.8.0: founding contributors section on `/about.html` from `data/founding-proposers.json` (52 researchers, 21 countries) · home-page events block refreshed against the official Action ledger (Policy Workshop + ITC Conference added, MC plenary firms to 18 Sep) · release-infrastructure hygiene (SHA-pinned third-party Actions, YAML issue forms, issue-lifecycle automation) · `sync-cost.py` propagates per-bio WG memberships from cost.eu into `data/bios.json` ([#236](https://github.com/EISSeuropa/netsec.github.io/issues/236) Gap A). |
| 29 May 2026 | ✅ **v1.9.0** | Cut early (29 May, ahead of the planned 5 June). Pre-Stockholm calendar plumbing: per-event `.ics` files at `/calendar/<slug>.ics` driving a per-card *Add to calendar* dropdown (Google / Outlook / Apple webcal / direct .ics) · news RSS feed at `/news.xml` (sourced from a new `data/news.json`) · structural refactor so home-page event *and* news cards derive from JSON instead of hand-coded HTML across three locales, with a five-line clamp + *Read more* affordance for longer descriptions ([#249](https://github.com/EISSeuropa/netsec.github.io/issues/249)) · D10 (risk management strategy) hosted if the document is ready. |
| 31 May 2026 | ✅ **v1.10.0** | Pre-conference cut that version-tagged what had already merged to `main` since v1.9.0: ESSC programme co-author bylines with a presenter mic ([#317](https://github.com/EISSeuropa/netsec.github.io/issues/317)) · CHANGELOG-derived roadmap-card automation + quarter relocation ([#233](https://github.com/EISSeuropa/netsec.github.io/issues/233)) · the Indico-sync change summary in the PR body ([#322](https://github.com/EISSeuropa/netsec.github.io/issues/322)) · the `sync-cost.py` Gap C leadership-label fix ([#236](https://github.com/EISSeuropa/netsec.github.io/issues/236)). A user-visible feature (co-author bylines) made this a minor, not a patch. Shipped 31 May, ahead of the 5 June target. |
| 8 Jun 2026 | ✅ **v1.11.0** | The pre-conference directory release, gathering everything merged since v1.10.0 (the planned v1.10.1 patch was folded in, no separate cut). Directory filters by research theme + research region + mentorship ([#555](https://github.com/EISSeuropa/netsec.github.io/issues/555), [#498](https://github.com/EISSeuropa/netsec.github.io/issues/498)), each member's keywords still on the card · mobile filter sheet rebuilt as a native `<dialog>` (top layer) so it behaves across iOS Safari and Chrome, with the iOS render / dismissal / latency saga settled · LinkedIn + Bluesky footer links ([#63](https://github.com/EISSeuropa/netsec.github.io/issues/63)) · hand-designed social cards · WebP headshots ([#269](https://github.com/EISSeuropa/netsec.github.io/issues/269)) · directory Early Access banner · About-page deliverable statuses · per-Working-Group deliverable + *Related publications* sections · research-keyword proper-noun capitalisation ([#505](https://github.com/EISSeuropa/netsec.github.io/issues/505)) + affiliation punctuation ([#506](https://github.com/EISSeuropa/netsec.github.io/issues/506)) · accessibility statement v1.3 · FR/DE FAQ bio-update clarification ([#183](https://github.com/EISSeuropa/netsec.github.io/issues/183)). |
| 9–12 Jun 2026 | 📅 *Stockholm* | Early-Career Scholars Training School (9–11 Jun) + European Security Studies Conference (11–12 Jun) |
| 17 Jun 2026 | ✅ **v1.12.0** | *A working directory and life after Stockholm.* The first cut after the conference, and it took most of what had been pencilled for v1.13.0: STSM host matching ([#760](https://github.com/EISSeuropa/netsec.github.io/issues/760)) · ORCID-powered recent publications ([#761](https://github.com/EISSeuropa/netsec.github.io/issues/761)) · shareable per-member profile pages at `/people/<slug>` ([#762](https://github.com/EISSeuropa/netsec.github.io/issues/762)) · the mentorship matching view ([#763](https://github.com/EISSeuropa/netsec.github.io/issues/763)) · a dedicated Events page ([#927](https://github.com/EISSeuropa/netsec.github.io/issues/927)) · claim-your-profile CTAs on bio-less Working Groups cards ([#758](https://github.com/EISSeuropa/netsec.github.io/issues/758)) + MC statistics auto-synced from the COST roster ([#236](https://github.com/EISSeuropa/netsec.github.io/issues/236)) · the Outputs publications pipeline for D6 briefs ([#726](https://github.com/EISSeuropa/netsec.github.io/issues/726)) · FAQ / Glossary rich-result metadata ([#766](https://github.com/EISSeuropa/netsec.github.io/issues/766)) · roadmap icon feature-chips ([#767](https://github.com/EISSeuropa/netsec.github.io/issues/767)) · the ESSC "Now happening" banner ([#832](https://github.com/EISSeuropa/netsec.github.io/issues/832)) and the page's turn to a past-conference archive · platform quality: shared page renderers ([#725](https://github.com/EISSeuropa/netsec.github.io/issues/725)), Lighthouse budgets ([#270](https://github.com/EISSeuropa/netsec.github.io/issues/270)), the extracted people-directory module ([#875](https://github.com/EISSeuropa/netsec.github.io/issues/875)). |
| 22 Jul 2026 | ✅ **v1.13.0** | *Introducing Mentorship Matching 2.0.* The Directory turns from something you read into something you use. Mentorship matching rebuilt around a guided sentence with live re-ranked matches, capacity and found-a-mentor signals that retire themselves, and profile pages recast on a hero band with a mentors facepile, deep-linking theme and region chips, and enquiry buttons. Profiles reach across to the EISS Anthology on a shared name key. Wider reach: the social pipeline adds LinkedIn beside Bluesky, News gains issue-driven publishing and a year-grouped archive, the audience router follows the reader onto every page. Underneath: an editorial design pass (fluid Lexend scale, solid-ink headlines, letterboxed home hero), the stylesheet split into a core plus two page bundles, and the Indico write path moved onto the supported `netsec-dispatch` plugin CLI. |
| 31 Aug 2026 | 📅 **v1.14.0** | *The NetSec Network Map, and a build that stopped arguing with itself.* The Working Groups, their members and the ties between them drawn as a map you can explore ([#764](https://github.com/EISSeuropa/netsec.github.io/issues/764)), shipped in Beta: find a person and deep-link to them from their profile ([#1642](https://github.com/EISSeuropa/netsec.github.io/issues/1642)), zoom and pan with the hover card kept on screen ([#1644](https://github.com/EISSeuropa/netsec.github.io/issues/1644)), a hub that answers when you click it ([#1643](https://github.com/EISSeuropa/netsec.github.io/issues/1643)), a keyboard path into the canvas and four states that previously said nothing ([#1645](https://github.com/EISSeuropa/netsec.github.io/issues/1645)), and the inclusiveness figure COST actually asks for, counted by country ([#1646](https://github.com/EISSeuropa/netsec.github.io/issues/1646)). The research-keyword taxonomy reached zero unassigned terms ([#1701](https://github.com/EISSeuropa/netsec.github.io/issues/1701)). Underneath, everything a machine writes moved out of the repository and into the deploy: the cache-bust tokens ([#1712](https://github.com/EISSeuropa/netsec.github.io/issues/1712)), then the Open Graph cards and the 252 profile pages with their drift gates ([#1716](https://github.com/EISSeuropa/netsec.github.io/issues/1716)), which also dissolved the build-ordering rule that was recorded nowhere but in whoever last got it wrong. Measurement got honest: Lighthouse now reads the median run against a production-like server ([#1613](https://github.com/EISSeuropa/netsec.github.io/issues/1613), [#1617](https://github.com/EISSeuropa/netsec.github.io/issues/1617)), one script replaced fifteen throwaway browser harnesses ([#1714](https://github.com/EISSeuropa/netsec.github.io/issues/1714)), and a 44px target-size floor is enforced in CI ([#1689](https://github.com/EISSeuropa/netsec.github.io/issues/1689)). The documentation PDF went from 24.6 MB to 7.7 MB ([#1727](https://github.com/EISSeuropa/netsec.github.io/issues/1727)). |
| 13 Sep 2026 | 📅 *Policy workshop* | Working Group 2's one-day policy workshop, *Great Power Politics and the Future of Alliances*, at Bilkent University, Ankara. Convenes members with policy practitioners on how alliance politics is shifting under great power competition. Accommodation and meals covered by Bilkent and the Royal Danish Defence College, travel reimbursed up to €700 pending an MC decision. Applications close 15 August 2026, notifications by 22 August. The 4 September date this row carried previously came from the [#244](https://github.com/EISSeuropa/netsec.github.io/pull/244) event ledger and moved by nine days once the workshop was actually scheduled. |
| Sep 2026 | 📅 *MC plenary* | Inaugural Management Committee plenary, date not yet confirmed. The 18 September date came from the event ledger in [#244](https://github.com/EISSeuropa/netsec.github.io/pull/244), the same batch that produced the non-existent ITC Conference and a Policy Workshop date that later moved by nine days, so it is held as provisional until the Action announces it ([#1491](https://github.com/EISSeuropa/netsec.github.io/issues/1491)). A Core Group working session is expected back-to-back on the same day. |
| 6 Oct 2026 | 📅 **v1.15.0** | *Year One, told back.* The auto-assembled Year 1 retrospective prepared for the anniversary ([#765](https://github.com/EISSeuropa/netsec.github.io/issues/765)) · the Action's first privacy-respecting usage figures ([#727](https://github.com/EISSeuropa/netsec.github.io/issues/727)) · the Glossary field guide grown into a fuller concept map ([#998](https://github.com/EISSeuropa/netsec.github.io/issues/998)) · the Network Map's last piece, co-authorship edges, which need D6 to deliver rather than any code ([#764](https://github.com/EISSeuropa/netsec.github.io/issues/764)) · ESSC 2027 lands in the data layer once the September organising meeting confirms dates, venue and rooms ([#1557](https://github.com/EISSeuropa/netsec.github.io/issues/1557), [#1558](https://github.com/EISSeuropa/netsec.github.io/issues/1558), [#1559](https://github.com/EISSeuropa/netsec.github.io/issues/1559)) · the Wiki freshness pass ([#231](https://github.com/EISSeuropa/netsec.github.io/issues/231)) and the two-repo synergies with EISS ([#325](https://github.com/EISSeuropa/netsec.github.io/issues/325)). |
| 10 Oct 2026 | 📅 *M12* | Year 1 anniversary · D1 first-version state · D6 first policy briefs |
| 8 Dec 2026 | 📅 **v1.16.0** | *The call for papers, and the work this repo cannot start alone.* The ESSC 2027 call-for-papers surface on the conference page ([#1561](https://github.com/EISSeuropa/netsec.github.io/issues/1561)), the 2026 leftovers cleared ([#1560](https://github.com/EISSeuropa/netsec.github.io/issues/1560)), the announcement banner run for the submission window ([#1562](https://github.com/EISSeuropa/netsec.github.io/issues/1562)), and the approval loop with EISS and COST tracked ([#1563](https://github.com/EISSeuropa/netsec.github.io/issues/1563), [#1564](https://github.com/EISSeuropa/netsec.github.io/issues/1564)). Alongside it the parking bay: deliverable ship-status once the Action confirms it ([#447](https://github.com/EISSeuropa/netsec.github.io/issues/447)), the Indico push pipeline waiting on the `netsec-dispatch` plugin being deployed ([#823](https://github.com/EISSeuropa/netsec.github.io/issues/823)), and the inaugural MC plenary date with the ledger audit behind it ([#1491](https://github.com/EISSeuropa/netsec.github.io/issues/1491)). The 46 incomplete directory entries get their mail-merge round ([#1631](https://github.com/EISSeuropa/netsec.github.io/issues/1631)). |
| 10 Jan 2027 | 📅 **v1.17.0** | Registration opens for ESSC 2027, behind the admission decisions: the review workflow and its notifications ([#1565](https://github.com/EISSeuropa/netsec.github.io/issues/1565)), the registration form carrying the accommodation and catering choices ([#1567](https://github.com/EISSeuropa/netsec.github.io/issues/1567)), visa-invitation letters with a named signatory ([#374](https://github.com/EISSeuropa/netsec.github.io/issues/374)), and the early-career prize running again ([#1566](https://github.com/EISSeuropa/netsec.github.io/issues/1566)). Alongside it, the mentorship questionnaire goes out to mentors and mentees, so D7's evaluation has evidence about experience and outcomes rather than only about how many roles were set ([#1763](https://github.com/EISSeuropa/netsec.github.io/issues/1763)). |
| 30 Apr 2027 | 📅 **v1.18.0** | The 2027 programme: the accepted papers rendered for the new edition ([#1568](https://github.com/EISSeuropa/netsec.github.io/issues/1568)), the keynote surfaced ([#1572](https://github.com/EISSeuropa/netsec.github.io/issues/1572)), a personal schedule attendees can build and export ([#855](https://github.com/EISSeuropa/netsec.github.io/issues/855)), practical information rewritten around what is arranged ([#1569](https://github.com/EISSeuropa/netsec.github.io/issues/1569)). |
| Jun 2027 | 📅 *ESSC 2027* | The tenth European Security Studies Conference, two days of panels and roundtables. Dates and venue confirmed at the September 2026 organising meeting ([#1557](https://github.com/EISSeuropa/netsec.github.io/issues/1557)). |
| 11 Jun 2027 | 📅 **v1.19.0** | Conference week: programme changes reaching the page in about a minute ([#1573](https://github.com/EISSeuropa/netsec.github.io/issues/1573), [#823](https://github.com/EISSeuropa/netsec.github.io/issues/823)), then the archive rollover and the 2028 template parked ([#1574](https://github.com/EISSeuropa/netsec.github.io/issues/1574)). |

Symbol key: ✅ shipped, 📅 planned.

**Renumbered on 29 August 2026.** The milestone numbers had drifted away
from the release sequence. Nothing had been tagged since v1.13.0 on 22
July, so the 41 issues closed across July and August all ship in the next
cut whatever milestone they carried, and they carried three different
ones. Every planned release therefore moved up by one, taking its date and
its content with it, and v1.19.0 was created to hold conference week. The
five ESSC 2027 phases below kept their dates and shifted their labels the
same way. A milestone names the release an issue ships in, which is what
rule §10 asks of it, and it had stopped doing that.

---

## ESSC 2027 preparation

The next European Security Studies Conference is planned for June
2027, jointly organised with EISS and the host university. The
organising group met in August 2026 and meets again on 7 September
2026 to settle the panels and the roundtables, along with the dates
and the venue.

The prep work rides the release milestones rather than a calendar of
its own (CLAUDE.md §10), so each phase lands in whichever release is
open when its deadline falls. The deadlines themselves live in the
issues.

The five phase names below are the joint organising group's, and the
EISS roadmap names them identically against its own releases. That is
how a deadline gets spoken about across two repositories without either
of them minting a milestone for it, which EISS briefly did and reverted
in August 2026.

| Release | Due | Conference work in it |
| --- | --- | --- |
| v1.15.0 | 6 Oct 2026 | *Save the date*, due 30 September. The edition confirmed and entered in `data/events.json` ([#1557](https://github.com/EISSeuropa/netsec.github.io/issues/1557)) · the Indico event created and the rollover clean-up run live for the first time ([#1558](https://github.com/EISSeuropa/netsec.github.io/issues/1558)) · the save-the-date published, due 30 September ([#1559](https://github.com/EISSeuropa/netsec.github.io/issues/1559)) · the Stockholm timezone mislabel fixed ([#1310](https://github.com/EISSeuropa/netsec.github.io/issues/1310)) |
| v1.16.0 | 8 Dec 2026 | *Call for papers*, drafted end of October and published early November. The conference page un-parked and its 2026 leftovers cleared ([#1560](https://github.com/EISSeuropa/netsec.github.io/issues/1560)) · the call-for-papers surface built ([#1561](https://github.com/EISSeuropa/netsec.github.io/issues/1561)) · the banner run for the call window ([#1562](https://github.com/EISSeuropa/netsec.github.io/issues/1562)) · EISS and COST approval recorded ([#1563](https://github.com/EISSeuropa/netsec.github.io/issues/1563)) · activation coordinated with the EISS page ([#1564](https://github.com/EISSeuropa/netsec.github.io/issues/1564)). |
| v1.17.0 | 10 Jan 2027 | *Selection and notifications*. Review workflow and notification templates ([#1565](https://github.com/EISSeuropa/netsec.github.io/issues/1565)) · the prize jury confirmed ([#1566](https://github.com/EISSeuropa/netsec.github.io/issues/1566)) · registration form carrying the dorm and reception numbers ([#1567](https://github.com/EISSeuropa/netsec.github.io/issues/1567)) · visa letters ([#374](https://github.com/EISSeuropa/netsec.github.io/issues/374)) · the mentorship questionnaire sent to mentors and mentees, feeding D7 ([#1763](https://github.com/EISSeuropa/netsec.github.io/issues/1763)) |
| v1.18.0 | 30 Apr 2027 | *Programme and logistics*. Programme renderer wired to the new edition ([#1568](https://github.com/EISSeuropa/netsec.github.io/issues/1568)) · practical information rewritten around the arranged accommodation ([#1569](https://github.com/EISSeuropa/netsec.github.io/issues/1569)) · budget envelope confirmed ([#1570](https://github.com/EISSeuropa/netsec.github.io/issues/1570)) · chairing guidance ([#1571](https://github.com/EISSeuropa/netsec.github.io/issues/1571)) · keynote confirmed and surfaced ([#1572](https://github.com/EISSeuropa/netsec.github.io/issues/1572)) · the programme backlog ([#1034](https://github.com/EISSeuropa/netsec.github.io/issues/1034), [#855](https://github.com/EISSeuropa/netsec.github.io/issues/855), [#364](https://github.com/EISSeuropa/netsec.github.io/issues/364)) |
| v1.19.0 | 11 Jun 2027 | *The conference itself*. Live-programme readiness, which needs the dispatch plugin at 1.0.0 and the push pipeline deployed ([#1573](https://github.com/EISSeuropa/netsec.github.io/issues/1573), [#823](https://github.com/EISSeuropa/netsec.github.io/issues/823)) · the archive rollover afterwards, parking the 2028 template ([#1574](https://github.com/EISSeuropa/netsec.github.io/issues/1574)) |

The public roadmap carries these as release cards, with a calendar
marker for the conference itself. That marker says June 2027 without a
day range: the 11 to 12 June on the parked page was copied from the
2026 edition, and the September meeting is what confirms the real one.

---

## Where we are today

As of late May 2026 — month **M8** of the four-year Action — the
delivery state is:

- **Website live** at <https://netsec-cost.eu> on GitHub Pages,
  HTTPS-only, EN/FR/DE.
- **Fourteen public pages**: home, network directory, grants &
  calls, press kit, FAQ, glossary, *about*, *publications*
  (placeholder), *news* archive, *roadmap*, *ESSC 2026 live
  programme*, sitemap, accessibility, privacy, licensing.
- **Open community directory** (D1, first version) accepting
  bios via a public Google Form. 13 members ingested at the most
  recent sync; the form is open to MC reps, WG participants, and
  the wider community. Research-interest keyword pills now render
  on each detailed bio card and feed a dedicated filter row above
  the grid (top-eight chips by submission count, multi-select OR
  semantics, URL-hash persistence so filtered views are shareable).
  A curated alias map in `data/keyword-aliases.json` collapses
  near-duplicates ("EU foreign policy" / "Foreign policy of the
  EU") to a canonical form and preserves acronym capitalisation
  (UN, NATO, EU, UK, US, UNDP, OSCE, EU–NATO, …) through the
  sentence-case normaliser.
- **Site-wide search** (Pagefind, EN/FR/DE shards) with rich
  bio result cards and on-page highlight-on-landing.
- **Live ESSC 2026 programme** at `/essc-2026.html` (+ FR + DE),
  rebuilt daily from `indico.eiss-europa.com`. Day chips, parallel
  session cards, livestream badges, member-preview popovers on
  speaker names that resolve to a `bios.json` record.
- **`/about` page** (EN/FR/DE) consolidating the Action narrative,
  deliverables Gantt, leadership, FAQ + Glossary teasers, and
  the relationship with EISS (placeholder pending content from
  Action Chair + WG4 lead).
- **Documentation pack v1.9.0** (`docs/pdf/NetSec-website-
  documentation.pdf`) carries the current cover stamp; the
  substantive section-level catch-up to website v1.7.0 shipped
  in PR #198 (closes [#122](https://github.com/EISSeuropa/netsec.github.io/issues/122)).
- **CHANGELOG** at SemVer v1.7.0 with `[Unreleased]` empty.
  Release tooling (`scripts/release.sh`) requires a short title
  per release; the hybrid release-notes format (lede + themes +
  index for minors / majors, index-only for patches) is in place
  across the whole changelog.
- **Maintainer**: one person (AL) running on volunteered time.

---

## Release history

Each tagged release at a glance — what landed, when, and the
GitHub Release link. The release-titles convention (every release
has a short title) was retroactively applied in v1.4 to all
historical releases.

### v1.0.0 · 20 May 2026 — *Initial public release*

The Action's first public website. **Deliverable D1** (open
community directory) presented for COST review.

- **Public website** at <https://netsec-cost.eu> on GitHub
  Pages, HTTPS-only.
- **Seven public pages**: Home, Network directory, Grants &
  Calls, Sitemap, Accessibility, Privacy, Licensing.
- Apple-style glass UI; light / dark themes with OS-default
  detection + manual override; responsive from 4K to phone.
- EU + COST branding compliance throughout.
- **Open community directory** accepting submissions via a
  public Google Form; weekly sync workflow opens a PR rather
  than pushing silently. MC roster auto-merged from cost.eu.
- GDPR-compliant privacy notice; WCAG 2.1 AA conformance
  statement; coordinated-disclosure policy.

[Release notes →](https://github.com/EISSeuropa/netsec.github.io/releases/tag/v1.0.0)

### v1.1.0 · 20 May 2026 — *Release tooling and PDF SemVer*

Operational hygiene. Made future releases boring to cut.

- **`scripts/release.sh`** one-command release helper: validates
  SemVer, promotes `[Unreleased]`, tags, pushes, creates the
  GitHub Release.
- Documentation pack re-versioned to SemVer (v1.0 / v1.1 / v1.2
  retroactively re-stamped as v1.0.0 / v1.1.0 / v1.2.0).
- Section 06 of the PDF: *Admin guide — Cutting a release*.
- Site screenshots refreshed.

[Release notes →](https://github.com/EISSeuropa/netsec.github.io/releases/tag/v1.1.0)

### v1.2.0 · 21 May 2026 — *Press kit, directory tour, compact view*

Outward-facing surface area expansion + directory polish.

- **Click-to-expand on compact directory cards** + a `+`
  quick-join button in the toolbar.
- **Guided six-step directory tour** anchored to the toolbar
  affordances. Two entry points: a *Take the tour* button in
  the welcome strip and a persistent `?` button. Keyboard nav,
  focus trap, `prefers-reduced-motion`. Engine generalised as
  `window.netsecTour(...)` for reuse on other pages.
- **First-visit orientation strip** above the directory toolbar.
- **Compact directory view** — three-across grid, density toggle
  in the toolbar, preference persists in `localStorage`.
- **Public press-kit page** at `/press-kit.html` — logos with
  pairing rules, palette, typography, funding-statement
  boilerplate (full / short / one-line), CC BY 4.0 attribution
  wording, do/don't rules.
- **Promotional A3 poster** as Appendix C of the docs PDF and
  embedded as a card-sized teaser at the top of the repo
  README.
- **Members' Wiki *Templates & press kit* page** — copy-paste
  versions of the boilerplate.
- **Grants page** spells out the e-COST portal model explicitly
  (filtering by profile, WBP boundaries).

[Release notes →](https://github.com/EISSeuropa/netsec.github.io/releases/tag/v1.2.0)

### v1.3.0 · 21 May 2026 — *Introducing FAQ and Glossary pages*

Reference content moved from the Wiki to the public site so
non-GitHub audiences can find it.

- **`/faq.html`** (+ FR + DE) — 21 Q&As across six themed
  sections with a jump-to TOC and per-question deep-link
  anchors.
- **`/glossary.html`** (+ FR + DE) — ~35 COST and NetSec terms
  with per-term anchors. The original Wiki pages were
  rewritten as short stubs pointing at the public URLs.
- **Discovery surface on the home page**: a four-card *Find
  out more* grid at the end of About (FAQ, Glossary, Press kit,
  members' Wiki) — keeps the floating header at ten items
  while making reference pages visible at a glance.
- **Wiki signposting on the home page**: tinted *For NetSec
  members* strip between Outputs and Contact with *Open the
  Wiki* + *e-COST portal* CTAs.
- **Footer FAQ + Glossary links** across all 24 page-locale
  permutations.
- **`scripts/inject-seo.py` `PAGES` list extended**; SEO blocks
  (canonical, OG, Twitter Card, JSON-LD WebPage) injected on
  the six new pages.
- **External-link icon CSS fix** — specificity bug + flex-shrink
  collapse + double-arrow on news cards all resolved.

[Release notes →](https://github.com/EISSeuropa/netsec.github.io/releases/tag/v1.3.0)

### v1.4.0 · early Jun 2026 (in progress) — *Site-wide search + IA Phase 1*

Currently being assembled in `[Unreleased]`. Largest release
since v1.0 — bundles two distinct streams:

- **Search**: site-wide overlay (Pagefind, EN/FR/DE shards) with
  rich bio result cards for directory entries, deep-link to the
  matched sub-section, on-page yellow highlight of the matched
  term, Cmd-K / Ctrl-K / `/` shortcuts.
- **iCalendar feed** at `/calendar.ics` with a centred *Subscribe
  to NetSec events* CTA in the Events section; calendar pipeline
  is JSON-source-of-truth with a CI drift check.
- **Header streamlined**: NetSec wordmark hidden in the floating
  bubble; nav reduced from 10 to 8 items (*Committee* and
  *Roadmap* merged into the new About page; *Outputs* renamed to
  *Publications*).
- **`/about` page** (EN/FR/DE) consolidating Action narrative +
  deliverables Gantt + Leadership + FAQ teaser + Glossary teaser
  + Relationship with EISS placeholder.
- **`/outputs` page** (placeholder) and **`/news` archive page**
  ready to receive content as it accrues.
- **Members' Wiki link** added to every page's footer between
  Glossary and Press kit.
- **Mobile fixes**: Gantt Year/Quarter column alignment;
  `.mc-subhead` separator wrapping.
- Many polish items from MC feedback iteration.

Release notes to follow at the v1.4.0 cut.

---

## Anchors driving this roadmap

Three streams set the pace:

1. **The Action calendar** — what audiences (members, applicants,
   press) need to find on the site, and when.
2. **The MoU deliverables** — D-numbered outputs the website
   hosts as they reach their milestones.
3. **Open feedback and known polish items** — GitHub Issues
   #62 / #63 / #72, plus the threads in maintainer review.

### Action calendar (firm + expected)

| Date | Event | Site impact |
|---|---|---|
| **9–11 Jun 2026** | Early-Career Scholars Training School (Stockholm University) | Liveness check on the event card, calendar feed up-to-date, post-event recap |
| **11–12 Jun 2026** | European Security Studies Conference (Stockholm University) | Same; flagship outreach moment. **Official logos + social channels in place** (see Q2 ship list) |
| **Before late Sep 2026** | Inaugural Management Committee Plenary *(date TBA)* | Date confirmation on home page well ahead of the meeting; agenda + minutes path to the members' Wiki; site reads as the canonical entry point for new MC reps |
| **10 Oct 2026** | Year 1 anniversary (M12) | Year-1 retrospective; D1 first-version milestone |
| **Throughout** | STSM applications, conference grants | Calls visible on `/grants`, application flow stable |

### Deliverables milestones (Year 1, due by M12 = Oct 2026)

The website is **not** responsible for producing these
deliverables — they're the Action's intellectual outputs. The
site's job is to **host** each one when it lands, with a
permalink and the right metadata so external evaluators can find
it.

| D# | Title | Due (Action month → calendar) | Site responsibility |
|---|---|---|---|
| D1 | First version of NetSec directory (updated regularly) | M12 → **Oct 2026** | **Owned by this roadmap.** See below. |
| D6 | First policy briefs published | M12 → **Oct 2026** | New page or section under `/outputs`; permalink + DOI placeholder |
| D8 | Planning guidelines for STSM & grant system | M9 → **Jul 2026** | Already on `/grants`; refresh once final document is approved |
| D9 | Strategy for a working structure | M6 → **Apr 2026** (passed) | Verify the version on the site matches the approved version |
| D10 | First draft of risk management strategy | M10 → **Aug 2026** | Host as a PDF + summary on a new sub-page |
| D11 | Inclusion & diversity declaration | TBD | Promote prominently on the home page once available |
| D12 | Environmental sustainability guidelines | TBD | Same |

### Open issues in the repo

- **#62** *Icons and logos need implementation* — favicon, NetSec
  mark placements across site / PDF / poster, accessibility +
  SEO implications.
- **#63** *Social media integration* — channel choice (LinkedIn?
  Bluesky? others?), footprint on the site (footer chips only?
  dedicated landing strip?), privacy posture.
- **#72** *Directory: replace expand-in-place with a sticky side
  panel / bottom sheet* — deferred until membership growth
  warrants the engineering cost. Today's behaviour (in-place
  expansion + click-to-expand on compact cards + search-landing
  spotlight + research-interest filter chip row) is sufficient at
  13 members. Trigger to act: membership past ~150, OR
  layout-disruption complaints.
- **#183** *Google Forms file-upload-edit bug, known upstream
  limitation*. Respondents can't replace a previously-uploaded
  headshot via the confirmation-email edit link. Workaround
  documented in `docs/bios-setup.md`: `Limit to 1 response` off,
  `Collect email addresses → Verified` keeps sign-in mandatory,
  edit-link still works for non-photo fields. Sync truthy-merges
  fields so a sparse photo-update resubmission doesn't wipe the
  respondent's other links. Closes (and the form-side note reverts)
  if Google ever fixes the upstream bug.

---

## What we'll ship, by quarter

### Q2 wrap-up — May / June 2026 *(in progress)*

**Theme**: ship the search and brand polish so the Conference is
the moment NetSec's public identity reads as deliberate. **The
Conference + the inaugural MC plenary (before late Sep) both
benefit from official logos and social channels already being in
place** — so brand work is pulled into June, not deferred to Q3.

#### Pre-Conference (target: before **5 Jun 2026**)

- [x] Public FAQ and Glossary, multilingual (v1.3.0)
- [x] Site-wide search, including directory bios (v1.3.x → v1.4.0)
- [x] Calendar feed + Subscribe affordance
- [x] Header streamline (drop NetSec wordmark, search trigger fits)
- [x] Release-title convention (every release reads as a thesis,
      not just a version number)
- [ ] **Pre-Conference dry-run on the live site**: verify the
      Training School + ESSC cards link out correctly, that the
      `webcal://` Subscribe button works on Apple Calendar /
      Outlook / Google Calendar, and that the news block is
      ready for live updates during the week of 9–12 June.
- [ ] **Cut v1.4.0** — bundles the recent fixes + the directory
      search additions. Title: *Search the directory, polished
      header*.

#### Pre-July — brand identity + social presence (target: before **30 Jun 2026**)

The Action's first public mass-outreach moments (Conference,
Training School, then the inaugural MC plenary) all benefit from
having a finalised visual identity and live social channels
*before* they happen, not after. The pre-Conference dates would
be ideal; the firm deadline is **end of June**.

- [ ] **Issue #62 — official logos and favicon**. Replace the
      placeholder NS-square mark and favicon with the Action's
      approved official versions. Audit logo placements across
      the site, the PDF documentation pack, the promotional
      poster, and the press kit. Verify the OG / Twitter Card
      / Bluesky preview images still render correctly with the
      new mark. *Blocker: receive the approved final-form logos
      from the Action Chair / WG4 lead.*
  - *Post-launch consistency pass (4 Jun 2026).* The identity shipped
    in v1.8.0; a follow-up pass then pointed the structured-data
    `Organization.logo` at the official mark sitewide (it had still
    been the placeholder), documented the identity in the design
    system, admin guide, and architecture docs, removed dead asset
    files, and added a `data/brand.json` source of truth plus a
    `brand-lint` CI gate (PRs #577, #579, #580). Residual items are
    tracked: ESSC JSON-LD restructure (#581), colour tokenisation
    (#582), PDF cover mark (#583), repo social-preview upload (#585),
    retiring `logo.png` (#586).
- [ ] **Issue #63 — social media presence**. Channels live,
      handles registered (consistent across networks), profile
      art using the new logos, biographies in EN/FR/DE.
      Footprint on the site: footer chips, press-kit page row,
      and a small *Follow us* card in the home-page *Find out
      more* grid. *Working proposal (pending decision):
      LinkedIn primary + Bluesky secondary, no X.*
- [ ] **Cut v1.5.0** — title: *Official logos + social channels
      live*. Ships the visual identity refresh, the social-media
      surfaces, and any small polish from the Conference dry-run
      feedback.

### Q3 — July / August / September 2026

**Theme**: harden the infrastructure, host the first Year-1
deliverables, prepare the site to be the canonical entry point
for new MC reps joining around the **inaugural MC plenary**
(before late September).

#### Content & deliverables

- **Post-event recap** for the Conference and Training School on
  the news block. Photo gallery (a small one — opt-in basis
  from participants), participant feedback summary, recordings
  link if available.
- **Host D8** (STSM planning guidelines, M9 ≈ Jul) as a
  permalink on the Grants page once the Grant Awarding
  Coordinator approves the final document.
- **Host D10** (risk management strategy, M10 ≈ Aug) — likely
  a new sub-page `/risk-management.html` with the PDF embedded
  and a short summary; or appended to the existing
  Documentation Pack appendix if the strategy is short.
- **Inaugural MC plenary** — date confirmation on home page as
  soon as known; agenda + minutes path to the members' Wiki
  finalised; the *For NetSec members* strip and the Wiki
  *Onboarding* page reviewed for new MC reps arriving via the
  plenary.

#### Features

- **FR / DE review pass on FAQ + Glossary content**. The
  translations are beta — flag a single native-speaker review
  per locale to lift them out of the beta banner.
- **Per-event `.ics` files + Add-to-calendar buttons.** Rounds
  out the calendar story shipped in v1.3.x — each event card
  gets a single-event download alongside the master Subscribe
  feed.
- **News RSS feed.** Generated from the news block at build
  time; academic + policy audiences still consume RSS.
- **Search acronym-synonyms.** `STSM` ↔ *Short-Term Scientific
  Mission*, `ITC` ↔ *Inclusiveness Target Country*, etc., via
  a small per-page keywords meta table.
- **Search index auto-rebuild** (consideration only — see *Open
  questions* below).

#### Quality (pre-MC plenary)

- **Pre-MC-plenary accessibility + cross-browser audit** —
  scope spelt out in the *Quality, accessibility, performance*
  theme below. Anchored at **early Sep**, ahead of the plenary
  date.
- **Performance audit** — Lighthouse + Core Web Vitals baseline
  on the four heaviest pages.
- **Homepage + header IA audit** (Jul–Aug). Written
  recommendation document, mirror of `search-assessment.md`.
  Output feeds the homepage restructure in v1.9.0. See the
  *Homepage IA* theme below for scope.

#### Infrastructure

- **Dependabot for GitHub Actions**: weekly checks on the
  pinned action SHAs (`actions/checkout@v4`, `actions/setup-
  node@v4`, `peter-evans/create-pull-request@v7`,
  `pagefind@1.5.2`). Auto-PR when a security update is
  available. *Drive-by from the GitHub App installation token
  format watch — having Dependabot on `actions` gives us the
  fix automatically if `peter-evans/create-pull-request` ships
  one.*

### Q4 — October / November / December 2026

**Theme**: Year-1 retrospective + ready Year 2.

#### Content & deliverables

- **D1 first-version milestone (M12, ~10 Oct 2026)**. By this
  date the directory needs to:
  - hold ≥30 members (back-of-envelope target; today's 13
    grows by ~5/month if the form intake stays steady),
  - be searchable by name and by working group,
  - have FR + DE chrome at least at the same level as today,
  - carry a *Year 1* milestone note on the home page,
  - have a stable URL pattern for sharing individual entries.
- **D6 first policy briefs** (M12) hosted on a new page or
  section, with citation metadata baked in (DOI placeholder,
  schema.org `ScholarlyArticle` JSON-LD). One brief minimum;
  more if available.
- **Year-1 retrospective** post on the news block on 10 Oct
  2026 — what shipped, who joined, what comes next.
- **Inclusion & diversity declaration (D11)** and
  **environmental sustainability guidelines (D12)** promoted
  on the home page when available.

#### Features

- **Outputs section refresh** (v1.9.0). Real card design for
  D6 policy briefs, `schema.org/ScholarlyArticle` JSON-LD,
  filter/sort if briefs accrue past ~10.
- **URL-encoded directory filter state** (partially shipped in v1.7.0
  via the keyword filter's `#keywords=` hash; the WG + country
  axes still to come, slated for v1.9.0).
- **Per-page Open Graph images** (v1.10.0). Distinct OG cards
  per page (FAQ, Grants, Press kit) so social previews tell
  the right story.
- **Print stylesheet for FAQ + Glossary** (v1.10.0). Researchers
  occasionally want offline hard copy.
- **Issue #72 reassessment**. By end-November we re-evaluate
  whether the directory's expand-in-place pattern is still
  serving. If membership has crossed the ~150 mark or if MC
  members are reporting friction, kick off the sticky-side-
  panel work for Q1 2027.
- **Member self-edit** — if the Google Form pipeline shows
  friction (members want to update bios faster than the
  weekly sync), spike a *Suggest an edit* CTA on each card
  that pre-fills the form with the existing bio. Decision
  point: only if at least 3 MC members ask for it.

#### Quality

- **Year-1-close audit** — focused re-test on whatever D6 /
  D11 / D12 surface lands, plus the *Outputs* section refresh.
  Light touch compared to the Q3 audit.

#### Releases & docs

- **v1.9.0** — Year-1 milestone release alongside D1's M12.
  Title: *Year 1 closes*.
- **v1.10.0** — late-December "Year 2 ready" release if scope
  warrants; PATCHes otherwise.
- **Documentation pack** bumped at each website MINOR release,
  in step with the website. (Pack version is independent of the
  website version axis — see CHANGELOG header.)

---

## Cross-quarter themes

Beyond the dated items above, four themes run through the half:

### 1 · Directory growth + UX

The directory has been the showcase since launch. As the member
count climbs, the trade-offs shift:

- Under **~30 members**: today's filter set (search × WG/MC ×
  country × research interest) is the right tool. Expand-in-place
  handles individual card reading.
- **30–150 members**: filter usage probably plateaus; visitors
  start arriving via search or shared deep-links. The
  search-landing spotlight + the URL-hash-persisted
  research-interest filter (shareable `#keywords=…` deep-links)
  are the bets for this band.
- **Past ~150**: the sticky-side-panel pattern (#72) becomes
  worth the engineering. The decision deadline is end-November.

The keyword pipeline (post-v1.6.1, in `[Unreleased]`) is the
preparation move for the wider rollout: form-side disclaimer
captures the photo-replacement workaround for the Google Forms
upload-edit bug (#183); sync-bios truthy-merges sparse
resubmissions so an updating respondent who only fills required
fields doesn't lose their previously-stored social links; the
sync's auto-PR self-describes (per-actor title + structured body
distinguishing new joiners from self-updates from bulk batches),
which scales better than the old static title once submissions
arrive at conference-week volume.

### 2 · Homepage + header IA — surviving content growth

The home page has accreted 10 sections since v1.0; the floating
header runs at 10 nav items (capacity, post-wordmark-removal).
Every Year-1 milestone adds more content:

- **News block** will gain Conference + Training School recaps in
  June, then monthly highlights, then post-plenary updates.
- **Outputs** currently shows three *Forthcoming* placeholders;
  D6 (policy briefs) makes it real in October and the section
  will keep accruing.
- **Events** will collect past + upcoming entries; a year out
  we'll need a "Past events" treatment.
- **D11 / D12** when they ship may need their own homepage
  presence (Inclusion & diversity, Environmental sustainability).
- **Find out more** grid + **For NetSec members** strip — both
  recently added (v1.3) — sit close together in the page and
  arguably compete for the same after-About attention.

Without a proactive pass, this gets messy and confusing.
Specific risks I can name:

- **No visual hierarchy** beyond ordering — every section uses
  similar weights, so nothing reads as "more important".
- **Long-scroll fatigue**, especially on mobile (10 sections
  × phone screen ≈ a lot of swiping).
- **First-time visitor** vs. **returning member** want
  different things from the same page: the new visitor wants
  *"what is NetSec"*; the returning visitor wants news /
  grants / directory.
- **Header at capacity** — there's no room for a new top-level
  page without restructuring; even *Outputs* / *Roadmap* are
  arguably internal-jargon labels that a journalist wouldn't
  parse instantly.
- **Audience tracks** (researcher, policy-maker, MC member,
  press) aren't differentiated; they all follow the same path.

#### What an IA pass would cover

A structured audit produces a written recommendation, not a
redesign. Scope:

- **Current-state inventory** — every section measured for
  content density, time-to-find for common tasks, mobile
  behaviour. Including: how does the home page perform for
  the visitor who arrives via search vs. direct vs. social?
- **Header IA** — does the flat 10-item nav still work, or
  should we group into dropdowns (e.g. *Activities* >
  Events / Grants / Training; *Reference* > FAQ / Glossary /
  Press kit)? Cost vs. benefit of each grouping vs. a flat
  list.
- **Homepage structure** — current order vs. an alternative
  rooted in audience tracks. Options to explore: sticky
  table-of-contents for long-scroll, mobile-specific section
  reordering, an *I'm a…* chooser at the top, offloading
  Outputs to a dedicated `/outputs.html` page.
- **Content lifecycle** — pagination / archive treatment for
  News and Events as they accumulate.
- **Consolidation** — *Find out more* grid + *For NetSec
  members* strip overlap; should one absorb the other, or
  should they sit further apart?
- **Future-proofing** — explicit positioning for the next 3-6
  homepage entries (D6 policy briefs, D11, D12, possibly a
  publications hub).

#### Timing — two phases

The biggest hidden cost of waiting for one big audit is that
the **official logos ship in v1.5 into a known-suboptimal IA,
then restructure in v1.7** — two brand-facing changes in four
months. Splitting the audit into two passes avoids that:

**Phase 1 — Structural quick-pass (this week)**

- 1–2 days of work, maintainer alone
- Focus: the structural decisions that need to land **before
  the v1.5 logo refresh** (consolidate the *Find out more* +
  *For NetSec members* overlap, regroup nav into dropdowns or
  not, sticky TOC on home or not, offload *Outputs* to its
  own page or wait for D6, etc.)
- Output: a written audit doc at `docs/homepage-ia-quick-
  audit.md` mirroring the `search-assessment.md` shape —
  issues, options, recommendations, costs per change.
- No consulting needed at this stage.

**Phase 2 — Detailed UX pass (July–August 2026)**

- Post-Conference, post-Training School (so we have real recap
  content to audit against)
- Post-v1.5 (so the audit happens against the real new
  visual identity, not placeholders)
- Optional consulting time here — same budget question as
  the original framing, just deferred to where the consulting
  budget pays off most.
- Output: deeper recommendations covering audience tracks,
  mobile patterns, content lifecycle, future-proofing for
  D6 / D11 / D12 / publications hub.

#### Implementation

- **v1.5.0 (late June)** absorbs the Phase 1 quick-wins
  alongside the brand refresh. Release title shifts to
  *Logos, socials, IA polish* to flag the broader scope.
- **v1.9.0 (mid Oct)** ships the deeper restructure from
  Phase 2 alongside the Year-1 close.
- The Phase 2 document shipped 2 July 2026 at
  `docs/homepage-ia-phase2.md`.

#### Open question

**Bring in a UI / UX professional for the Phase 2 audit?** A
few hours of an experienced practitioner's time produces a
substantively better recommendation than I can on my own,
particularly on audience-track separation and mobile patterns.
Decision owner: **Action Chair** (budget question). My
on-my-own version is the fallback if there's no budget.
Phase 1 runs without consulting regardless.

### 3 · Content cadence — deliverables hit the site

The site's value over 2026 grows as each MoU deliverable
publishes. The maintainer's commitment is **48-hour turnaround**
from approved-PDF-in-hand to live-on-site, with:

- a stable permalink,
- citation metadata (JSON-LD where appropriate),
- a news-block announcement,
- a press-kit-style social card if the deliverable warrants
  outreach.

### 4 · Quality, accessibility, performance

Last formal a11y audit shipped with **v1.0** (20 May). Between
then and now we've added a substantial surface area — search
overlay (modal, keyboard nav, focus trap, lazy WASM), directory
click-to-expand + search-landing spotlight, FAQ / Glossary with
deep-link anchors, press kit, *For NetSec members* strip, *Find
out more* grid, external-link auto-icon, calendar Subscribe
button, Pagefind `<mark>` painting, bio cards in search,
⌘K / `/` shortcuts. None of those have had a formal pass.

Three audit moments scheduled for H2:

#### **Pre-v1.5 audit (mid-to-late Jun 2026)** — comprehensive

Covers everything shipped between v1.0 and the brand refresh.
Necessary because v1.5 swaps in official logos that may shift
contrast ratios on icons / chips / shadows; auditing *before*
is the cheaper order than re-doing the audit after.

Scope:

- **Colour contrast (WCAG 2.1 AA, 4.5:1 text / 3:1 large)** — re-run
  on light + dark for: external-link icon, search-result cards
  (incl. bio cards), `<mark>` highlight, search-landing
  spotlight, calendar Subscribe button, *Find out more* cards,
  *For NetSec members* strip, FAQ / Glossary anchor `:target`
  state, news-card buttons.
- **Keyboard navigation** — full tab traversal of every page;
  visible focus indicators everywhere; no focus traps outside
  the search overlay. Verify ⌘K / Ctrl-K / `/` shortcuts in
  Chrome / Firefox / Safari (Mac) and Chrome / Firefox / Edge
  (Windows).
- **Screen-reader smoke test** — VoiceOver on macOS + NVDA on
  Windows. Specifically: the search overlay's modal semantics,
  `aria-live` result count, directory card auto-expand
  announcements, the `data-pagefind-body`-marked content vs.
  the (ignored) nav and footer.
- **Reduced motion** — confirm the spotlight scale-in, the
  overlay slide-in, and the bio-card hover transforms all
  respect `prefers-reduced-motion`.
- **Resize / zoom** — text-only zoom to 200 %, full-page zoom
  to 200 %; layout doesn't break, no horizontal scroll, no
  clipped content. Headers stay usable on the floating bubble.
- **Mobile** — touch tap targets ≥ 44 × 44 CSS px on all
  interactive elements (search trigger, overlay close,
  navigation, footer chips). Conference-week visitors will be
  on phones.
- **Translation** — `<html lang>` correct on every variant;
  `lang` attribute on inline foreign-language fragments where
  applicable; `:lang(fr)` / `:lang(de)` CSS rules still apply.

Method: axe-core CLI run across every page + locale (≈ 30
pages × 3 locales), spot-checks with the manual scripts above,
quick Lighthouse runs as a sanity check.

Output: a published a11y-audit report appended as Appendix to
the documentation pack; updated *Last assessed* date stamp on
`/accessibility.html`.

#### **Pre-MC-plenary audit (early Sep 2026)** — cross-browser + perf

The inaugural MC plenary brings 30+ new visitors who will form
their first impression of the site. Catch the long-tail issues.

Scope:

- **Cross-browser** — full smoke pass on Safari (Mac + iOS),
  Firefox (desktop + mobile), Edge, plus the Chrome baseline.
  Specific risks: `:where()` specificity (used in the external-
  link icon CSS) on older Safari, the `webcal://` Subscribe
  link on non-Apple platforms, Pagefind WASM on older
  browsers.
- **Cross-platform** — verify the directory looks right on
  Windows Edge, on a small Chromebook screen, on a phone in
  one-handed reach.
- **Performance** — Lighthouse run on the four heaviest pages
  (home, directory, FAQ, press kit). Target: ≥ 90 on every
  metric. Verify the page-weight budget hasn't drifted
  (baseline: ~140 KB excluding `bios.json`; Pagefind adds
  ~80 KB on first overlay open).
- **Core Web Vitals** — LCP, INP, CLS via WebPageTest.
- **Lighthouse SEO** — verify the new pages (FAQ, Glossary, the
  bio stubs) carry the right canonical + JSON-LD.
- **Re-run the axe-core suite** with any v1.5 deltas folded in.

#### **Year-1-close audit (mid Oct 2026)** — light touch

A focused re-test on whatever D6 / D11 / D12 surface lands in
v1.9.0. Plus a sweep of the *Outputs* section refresh (see
*Feature candidates* below). **And: a re-pass over whatever the
homepage IA audit recommended that landed in v1.9.0** — new
sectional groupings, dropdown nav, or audience-track strips all
need their own keyboard / screen-reader / mobile coverage.

Performance budget stays at the v1.0 number: **~140 KB
uncompressed page weight excluding bios.json**. The Pagefind
runtime (~80 KB on first overlay open) is the only meaningful
delta and is lazy-loaded.

### 5 · Feature candidates

Beyond what the release plan already commits to (search, brand,
deliverable hosting), these are the candidates worth queueing.
Each has a rough cost estimate and a decision point.

#### Round out the calendar story

- **Per-event "Add to calendar" buttons.** The `calendar.ics`
  master feed shipped in v1.3.x; this adds a one-shot
  `/calendar/<slug>.ics` per event so an MC member sharing a
  conference link can include the single-event invite. Cost:
  ~½ day. Slots into **v1.6.0**. Decision: ship as part of
  Q3.
- **RSS feed for the news block.** Academic + policy
  communities still consume RSS; the news block is small
  enough to render as Atom or RSS from `index.html` at build
  time. Cost: ~1 day (Python script + a workflow trigger).
  Slots into **v1.6.0**. Decision: ship as part of Q3.

#### Search improvements

- **Acronym synonyms.** Today `STSM` and `Short-Term
  Scientific Mission` are separate queries. Pagefind has a
  `data-pagefind-meta="keywords"` mechanism — adding a
  central acronym table baked into the relevant pages would
  let either form match. Cost: ~½ day. Slots into v1.6.0
  alongside the FR/DE review pass.
- **Result-type filter chips** (*All / Pages / People*) in
  the overlay header. Quality-of-life when both a page and a
  bio match the same query. Cost: ~1 day. Trigger fired in
  Q3 2026: tracked in
  [#1404](https://github.com/EISSeuropa/netsec.github.io/issues/1404),
  so it has left the watch list and the public roadmap's
  *Under watch* section. Built and merged, and it ships with
  v1.14.0.

#### Outputs section refresh

The `/outputs` section on the home page currently shows three
*Forthcoming* placeholder cards. **D6** (policy briefs) lands
in October as part of the Year-1 close. We need:

- A real card design with metadata (authors, date, abstract).
- A landing page per brief if briefs are PDF + abstract.
- `schema.org/ScholarlyArticle` JSON-LD for SEO + Google
  Scholar indexing.
- Filter / sort if briefs accrue past ~10.

Cost: ~2 days. Hard-blocked on the first brief being
production-ready. Slots into **v1.9.0** (*Year 1 closes*) by
design.

#### Directory ergonomics

- **URL-encoded filter state.** Today, `/people.html#stsm` opens
  Arthur's card; `/people.html?wg=3&country=fr` should open
  the directory pre-filtered to *WG3 members in France*.
  Powerful for share-links among the MC. Cost: ~1 day. Slots
  into **v1.9.0** (sized to match the Year-1 close moment).
- **Member self-edit CTA.** Still gated on at least 3 MC
  members asking for it. Visibility only.
- **Sticky side panel (#72).** Re-evaluate end-November as
  before — trigger is membership > 150 OR friction reports.

#### Engagement

- **Newsletter signup** (Formspree-backed, no analytics, no
  list-management dashboard — the form just forwards to the
  Action mailbox). Cost: ~½ day. Decision: only if the AC
  wants a newsletter channel and is willing to maintain the
  cadence. Otherwise skip.
- **Print stylesheet for FAQ + Glossary.** Researchers
  occasionally want hard copy for offline reference. Cost:
  ~1 day. Nice-to-have.

#### Operational

- **Open Graph image per page** — currently one global
  `og-image.png` shows for every share. Distinct per-page
  cards (FAQ uses one, Grants another, etc.) improve social
  preview quality. Pre-rendered at build time. Cost: ~1 day
  including OG-image design.

#### What I'm *not* proposing

A few patterns I considered and chose to skip, with reasons —
in case any of these surprises you:

- **Analytics / tracking pixels.** Violates the established
  privacy posture (no third-party trackers documented in
  `/privacy.html`). No change.
- **Search analytics** — same reason.
- **Comments on news / FAQ entries** — moderation burden + spam
  risk + accessibility complexity. Use the contact form.
- **Service worker / offline mode** — overkill for a content
  site; ROI not there yet.

### 6 · Infrastructure & DevOps hygiene

- **Release immutability** on GitHub Releases: enabled at the
  repo level but found in practice not to enforce on
  `gh release edit` (May 2026 finding). Worth a note to GitHub
  Support if we ever rely on it; otherwise the in-script
  *Publish?* confirmation prompt is the practical gate.
- **Auto-merge on PRs** with passing CI: enabled. Standard
  workflow for routine changes.
- **Branch auto-delete on merge**: enabled. Branch hygiene is
  automatic.
- **Tag immutability** (`protect-release-tags` ruleset, no
  bypass): in place since v1.0.
- **Dependabot for actions**: to be enabled in Q3 (see above).

---

## Release plan

The canonical view is the **At a glance** timeline at the top of
this file; the table below was a pre-cut planning fossil from
early 2026 and has been collapsed into a single pointer to avoid
two sources of truth drifting apart. Patch releases (`1.X.Y`
where `Y > 0`) ship as needed and aren't pre-scheduled; see
README.md → *Versioning* for the minor / patch boundary (a minor
needs at least one new or significantly improved feature).

---

## Open questions / decisions needed

These need an explicit yes/no from the Action Chair (or AC + WG4
lead where indicated) before the related work can start:

1. **Social media channels (issue #63).** Which channels does
   the Action commit to? *Working proposal: LinkedIn primary +
   Bluesky secondary, no X.* Decision owner: **Action Chair +
   WG4 Lead (Science Communication)**.

2. **Native-speaker review of FR + DE chrome and content.**
   The translations are beta. Lifting them out requires one
   review pass per locale. Decision owner: **AC** (assigns
   reviewers from MC pool).

3. **Auto-rebuild of the search index.** Today the maintainer
   runs `./scripts/build-search.sh` after content changes; CI
   page-count check catches forgotten rebuilds. Could be
   automated via an Action that auto-PRs index updates. **Cost:**
   noise in the PR list. **Benefit:** never stale. Decision
   owner: **maintainer** (AL); defer to Q3 unless friction is
   reported.

4. **#72 side panel — kick off?** Re-evaluate end-November
   against the triggers (membership > 150 OR usability
   complaints). Decision owner: **maintainer**, with input from
   MC.

5. **Member self-edit CTA** — only spin up if at least 3 MC
   members ask for faster turnaround than the weekly form
   sync. No decision needed today; mentioned for visibility.

6. **D11 / D12 publication dates.** WG4 (Inclusion &
   Dissemination) owns D11; whoever owns environmental
   sustainability owns D12. The website work is short (a few
   hours per deliverable) once the PDFs are approved. Decision
   owner: **respective WG / coordinator**.

7. **Homepage + header IA audit — bring in a UI/UX
   professional for *Phase 2*?** *Phase 1 runs without
   consulting regardless — the maintainer writes the
   structural quick-audit this week.* The decision is whether
   the deeper Phase 2 pass in July–August warrants a few hours
   of an experienced practitioner's time. **Cost:** modest
   (~½ day of consulting). **If no budget:** the maintainer
   self-runs Phase 2 too; output is acceptable but less rich,
   particularly on audience-track separation and mobile
   patterns. Decision owner: **Action Chair**. Decision
   deadline: **end of June** so the audit can start in July.

---

## Beyond 2026 — a peek at Year 2

For context only. The roadmap commits to the dated rows in the timeline above, which now run to June 2027, and to nothing beyond them.

The big-picture trajectory across **Y2 (Oct 2026 → Oct 2027)**:

- The **second annual conference** drives another spike of
  outreach + directory growth.
- **D7** (mentoring initiative evaluation) at M18 = ~Apr 2027 —
  a new page or section is plausible. The questionnaire that gives
  it something to evaluate goes out in January, against v1.17.0
  ([#1763](https://github.com/EISSeuropa/netsec.github.io/issues/1763)).
- **D2** (first draft of the manifesto) at M15 = ~Jan 2027 —
  hosted with annotation / commenting capability if the WG
  wants public feedback.
- The directory likely crosses **~80–120 members** by mid-Year-2
  if intake stays steady. Side-panel decision will have been
  taken either way.

The Action's **strategic autonomy** narrative gets its first
real evidence base (six months of policy briefs, member growth,
training school cohorts) — the website's role shifts from
"showcase" to "evidence library". Anticipate redesign work
around the *Outputs* section in Q1 2027 to support that.

---

## How to read this document

- **MC members**: skim *Where we are* + *What we'll ship, by
  quarter*. The release table summarises in one screen.
- **Action Chair / Vice-Chair**: the *Open questions* section
  is the one that needs your input.
- **WG leads**: scan *Deliverables milestones* and the
  per-quarter content blocks for your WG's hand-offs.
- **The maintainer (me)**: this is the working document. Edit
  in-tree, PR-review the changes, ship monthly status updates
  in the news block.

This document is a **living roadmap** — facts get updated as
events unfold. If you want a snapshot at any point, the git
history on this file is the audit trail.
