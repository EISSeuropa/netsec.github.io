/* People directory renderer — shared across people.html, people.fr.html, people.de.html.
   Extracted from the per-locale inline <script> blocks (#875). Locale text routes through
   window.netsecT (defined in assets/js/site.js, loaded with defer before this file). */
(async function () {
  'use strict';
  const grid = document.getElementById('members-grid');
  const empty = document.getElementById('members-empty');
  const countEl = document.getElementById('members-count');
  const search = document.getElementById('member-search');
  const filterChips = document.querySelectorAll('.members-filter-chip');
  const mentorshipChips = document.querySelectorAll('.members-mentorship-chip[data-mentorship]');
  const stsmChip = document.querySelector('[data-stsm]');
  const countrySelect = document.getElementById('member-country');
  const tpl = document.getElementById('member-card-template');
  // Standalone profile-page URL for a member, in the current locale.
  // The directory cards link to these (name + "View full profile" CTA);
  // the card click still expands in place (the delegated handler ignores
  // clicks on link children).
  const PLANG = (document.documentElement.lang || 'en').slice(0, 2);
  const PSUF = PLANG === 'fr' ? '.fr' : PLANG === 'de' ? '.de' : '';
  const profileHref = (slug) => slug ? 'people/' + slug + PSUF + '.html' : null;
  const viewToggle = document.querySelectorAll('.view-toggle button[data-view]');

  /* Welcome strip + guided tour.
     Both share localStorage('netsec-directory-tour-seen'). On first
     visit (key absent) the strip auto-opens; the visitor can either
     "Take the tour" → tour runs, mark seen on completion; or "Got
     it" → mark seen and hide. The `?` button in the toolbar
     re-opens the tour at any time, regardless of the saved state. */
  const TOUR_KEY = 'netsec-directory-tour-seen';
  const welcome      = document.getElementById('welcome-strip');
  const welcomeDismiss = document.getElementById('welcome-strip-dismiss');
  const welcomeTour    = document.getElementById('welcome-strip-tour');
  const tourTrigger    = document.getElementById('tour-trigger');

  function markSeen() {
    try { localStorage.setItem(TOUR_KEY, 'true'); } catch (e) {}
    if (welcome) welcome.hidden = true;
  }

  // Tour configuration — selectors anchor each step to a real DOM
  // element on this page. Strings are localised per-page.
  //
  // We build the tour *lazily* (inside startTour()) because
  // assets/js/site.js is loaded with `defer`, which runs the engine
  // AFTER this inline script has been parsed. So window.netsecTour
  // is not yet defined when this IIFE runs — only by click time has
  // the deferred script finished executing.
  function startTour() {
    if (!window.netsecTour) return;  // engine missing — fail gracefully
    // The sheet is a top-layer modal; a tour overlay would mount behind it, so
    // close it first (only when open, to avoid stealing focus otherwise).
    if (filterSet && filterSet.open) closeFilterSheet();
    if (welcome) welcome.hidden = true;
    // The tour is viewport-aware. On desktop the filters render inline, so each
    // facet gets its own step. On phones they live in a bottom sheet that is
    // closed (and off-screen) at tour time, so a step pointing at an in-sheet
    // facet would spotlight an off-screen rectangle. There, a single step
    // points at the Filters button that opens the sheet instead.
    const isPhone = window.matchMedia('(max-width: 640px)').matches;
    const searchStep = { target: '#member-search',
      title: window.netsecT('Search'),
      body:  window.netsecT('Free-text search across names, affiliations, and countries. Combines with the filters.') };
    const joinTriggerStep = { target: '#join-trigger',
      title: window.netsecT('Jump to the join form'),
      body:  window.netsecT('The + button takes you straight to the join card at the foot of this page.') };
    const joinStep = { target: '#join',
      title: window.netsecT('Anyone can join'),
      body:  window.netsecT('Add yourself via the form here. About three minutes to fill in. Cards appear on this page within a week of submission.'),
      scroll: true };
    const desktopSteps = [
      searchStep,
      { target: '.members-filter',
        title: window.netsecT('Filter by working group or Management Committee role'),
        body:  window.netsecT('WG1–WG4 filter by Working Group. The Management Committee chip surfaces only Management Committee representatives.') },
      { target: '#members-keyword-filter',
        title: window.netsecT('Filter by research theme'),
        body:  window.netsecT('These chips group the directory by broad research theme, clustering people who work in the same area. Tap to narrow the list, tap more to widen the match. The keyword pills on each card are clickable too, and your selection lives in the URL so a filtered view is shareable.') },
      { target: '#members-region-filter',
        title: window.netsecT('Filter by research region'),
        body:  window.netsecT('A second, geographic axis: the parts of the world members focus their research on, not where they are based. Combine it with the themes above to narrow by both.') },
      { target: '#members-mentorship-filter',
        title: window.netsecT('Filter by mentorship'),
        body:  window.netsecT('Members can flag that they are available to mentor early-career researchers, or seeking mentorship themselves. Use these chips to find them. This row appears once at least one member has opted in.') },
      { target: '#members-stsm-filter',
        title: window.netsecT('Filter by STSM hosting'),
        body:  window.netsecT('A Short-Term Scientific Mission is a funded research visit to another member’s institution. This chip surfaces the members who have offered to host STSM visitors.') },
      { target: '.view-toggle',
        title: window.netsecT('Switch card density'),
        body:  window.netsecT('Detailed shows photos and bios. Compact shows initials, name, affiliation and Working-Group chips, three to a row. Your choice is remembered. Phones always use compact cards.') },
      joinTriggerStep,
      joinStep,
    ];
    const mobileSteps = [
      searchStep,
      { target: '.members-filter-toggle-btn',
        title: window.netsecT('Filters'),
        body:  window.netsecT('Tap Filters to narrow the directory by working group, research theme, research region, mentorship, or STSM hosting. The badge shows how many filters are active.') },
      joinTriggerStep,
      joinStep,
    ];
    // Drop steps whose target is absent or not rendered (the theme, region,
    // mentorship and STSM rows stay hidden until at least one member opts in),
    // so the "Step X of N" count matches what the visitor actually sees.
    const rawSteps = isPhone ? mobileSteps : desktopSteps;
    const tourSteps = rawSteps.filter(function (s) {
      const t = document.querySelector(s.target);
      if (!t || t.hidden) return false;
      const r = t.getBoundingClientRect();
      return r.width > 0 || r.height > 0;
    });
    window.netsecTour({
      steps: tourSteps.length ? tourSteps : rawSteps,
      labels: {
        next: window.netsecT('Next'), prev: window.netsecT('Back'), done: window.netsecT('Done'), skip: window.netsecT('Skip'),
        stepOf: window.netsecT('Step %1 of %2'), closeLabel: window.netsecT('Close tour'),
      },
      onComplete: markSeen,
    }).start();
  }

  // Auto-show the welcome strip on first visit.
  if (welcome && welcomeDismiss) {
    let seen = false;
    try { seen = localStorage.getItem(TOUR_KEY) === 'true'; } catch (e) {}
    if (!seen) welcome.hidden = false;
    welcomeDismiss.addEventListener('click', markSeen);
    if (welcomeTour) welcomeTour.addEventListener('click', startTour);
  }
  // The `?` button re-opens the tour any time, even after dismissal.
  if (tourTrigger) tourTrigger.addEventListener('click', startTour);

  /* View density is viewport-driven (see syncDirectoryView below): detailed
     on desktop, compact on phones. applyView flips the class on the grid and
     manages per-card tabindex; there is no user-facing toggle to keep in
     sync any more. */
  function applyView(mode) {
    const compact = (mode === 'compact');
    grid.classList.toggle('is-compact', compact);
    viewToggle.forEach(btn => {
      btn.setAttribute('aria-pressed', btn.dataset.view === mode ? 'true' : 'false');
    });
    // Manage tabindex + collapse any expanded card when leaving
    // compact mode — there's nothing left to expand into in detailed.
    grid.querySelectorAll('.member-card').forEach(card => {
      if (compact) card.setAttribute('tabindex', '0');
      else { card.removeAttribute('tabindex'); card.classList.remove('is-expanded'); }
    });
  }
  // Density is desktop-choosable, phone-forced. On phones (≤640px) the grid is
  // a single column where full photo + bio cards run too long, so compact is
  // forced and the toggle is hidden (CSS). On desktop the visitor picks, and
  // the choice persists in localStorage. syncDirectoryView applies the right
  // density on load and whenever the viewport crosses the breakpoint.
  const _mqCompact = window.matchMedia('(max-width: 640px)');
  function savedView() {
    try {
      const s = localStorage.getItem('netsec-directory-view');
      return (s === 'compact' || s === 'detailed') ? s : 'compact';
    } catch (e) { return 'detailed'; }
  }
  function syncDirectoryView() {
    applyView(_mqCompact.matches ? 'compact' : savedView());
  }
  syncDirectoryView();
  _mqCompact.addEventListener('change', syncDirectoryView);
  viewToggle.forEach(btn => {
    btn.addEventListener('click', () => {
      const mode = btn.dataset.view;
      applyView(mode);
      try { localStorage.setItem('netsec-directory-view', mode); } catch (e) {}
    });
  });

  /* Member preview panel (#72).
     ────────────────────────────
     Clicking a compact card opens that member's detail in a side
     panel (a right rail on desktop, a bottom sheet on mobile) instead
     of expanding in place, so the grid never reflows and the visitor
     keeps their scroll position. The panel content is a clone of the
     card's own already-rendered detail body, so there is no second
     renderer to keep in step; the bio is forced open and the
     non-functional toggle dropped. The "View full profile" CTA inside
     it hands off to the full /people/<slug> page for the bits the
     preview omits (the similar-people facepile, the Anthology link).
     A #slug deep-link opens the panel for that member. */
  function clearHashIfFocus() {
    // Only strip bare member-slug hashes. A key=value hash (the
    // shareable #themes= filter) is owned by the filter code and must
    // survive panel open/close (issue #647).
    const raw = (location.hash || '').replace(/^#/, '');
    if (raw && !raw.includes('=')) history.replaceState(null, '', location.pathname + location.search);
  }

  const panel = document.createElement('aside');
  panel.className = 'member-preview-panel';
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-modal', 'false');
  panel.setAttribute('aria-label', window.netsecT('Member profile'));
  panel.hidden = true;
  panel.innerHTML =
    '<div class="mpp-head">'
    + '<span class="mpp-eyebrow">' + window.netsecT('Quick look') + '</span>'
    + '<kbd class="mpp-esc" aria-hidden="true">Esc</kbd>'
    + '<button type="button" class="mpp-close" aria-label="' + window.netsecT('Close') + '">'
    + '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" '
    + 'stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>'
    + '</button>'
    + '</div>'
    + '<div class="mpp-scroll"></div>'
    + '<div class="mpp-foot" hidden>'
    + '<a class="mpp-cta" href="#"><span class="mpp-cta-label"></span>'
    + '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" '
    + 'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    + '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg></a>'
    + '</div>';
  const panelScrim = document.createElement('div');
  panelScrim.className = 'member-preview-scrim';
  panelScrim.hidden = true;
  document.body.appendChild(panelScrim);
  document.body.appendChild(panel);
  const panelScroll = panel.querySelector('.mpp-scroll');
  const panelFoot = panel.querySelector('.mpp-foot');
  const panelCta = panel.querySelector('.mpp-cta');
  let panelTrigger = null;

  // Build the panel body for a card: a cleaned clone, and the footer CTA
  // lifted out so the "View full profile" path is always in view.
  function buildPanelClone(card) {
    const clone = card.cloneNode(true);
    clone.classList.add('is-panel');
    clone.classList.remove('is-expanded', 'is-featured', 'is-search-landed');
    clone.removeAttribute('id');
    clone.removeAttribute('data-slug');
    clone.removeAttribute('tabindex');
    const chev = clone.querySelector('.member-toggle-chevron'); if (chev) chev.remove();
    const pin = clone.querySelector('.member-spotlight-pin'); if (pin) pin.remove();
    // The panel is a quick look: keep the bio clamped (no force-expand) so
    // the panel rarely scrolls; the full bio lives on the profile page,
    // reached via the pinned footer button. Drop the dead Show-more toggle.
    const bioToggle = clone.querySelector('.member-bio-toggle'); if (bioToggle) bioToggle.remove();
    // Lift the in-card "View full profile" link into the sticky footer so
    // the path to the full page is always visible without scrolling.
    const cta = clone.querySelector('.member-profile-cta');
    if (cta && cta.getAttribute('href')) {
      panelCta.setAttribute('href', cta.getAttribute('href'));
      panelCta.querySelector('.mpp-cta-label').textContent = window.netsecT('View full profile');
      panelFoot.hidden = false;
      cta.remove();
    } else {
      panelFoot.hidden = true;
    }
    return clone;
  }
  let swapTimer = null;
  function openPanel(card) {
    if (!card) return;
    const switching = !panel.hidden && panelTrigger !== card;
    panelTrigger = card;
    const clone = buildPanelClone(card);
    if (switching) {
      // Already open on another member: cross-fade the body rather than
      // swapping the content instantly. The panel frame stays put.
      clearTimeout(swapTimer);
      panelScroll.classList.add('is-swapping');
      swapTimer = setTimeout(() => {
        panelScroll.innerHTML = '';
        panelScroll.appendChild(clone);
        panelScroll.scrollTop = 0;
        panelScroll.classList.remove('is-swapping');
      }, 160);
      return;
    }
    panelScroll.classList.remove('is-swapping');
    panelScroll.innerHTML = '';
    panelScroll.appendChild(clone);
    panelScroll.scrollTop = 0;
    panel.hidden = false;
    panelScrim.hidden = false;
    requestAnimationFrame(() => { panel.classList.add('is-open'); panelScrim.classList.add('is-open'); });
    document.body.classList.add('mpp-open');
    panel.querySelector('.mpp-close').focus({ preventScroll: true });
    document.addEventListener('keydown', panelKeydown, true);
  }
  function closePanel() {
    if (panel.hidden) return;
    clearTimeout(swapTimer);                 // cancel any in-flight cross-fade
    panelScroll.classList.remove('is-swapping');
    panel.classList.remove('is-open');
    panelScrim.classList.remove('is-open');
    document.body.classList.remove('mpp-open');
    document.removeEventListener('keydown', panelKeydown, true);
    const t = panelTrigger; panelTrigger = null;
    setTimeout(() => { panel.hidden = true; panelScrim.hidden = true; }, 280);
    if (t) { try { t.focus({ preventScroll: true }); } catch (e) {} }
    clearHashIfFocus();
  }
  function panelKeydown(e) {
    if (e.key === 'Escape') { e.stopPropagation(); closePanel(); return; }
    if (e.key !== 'Tab') return;
    // Focus trap inside the panel.
    const f = panel.querySelectorAll('a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])');
    if (!f.length) return;
    const first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }
  panel.querySelector('.mpp-close').addEventListener('click', closePanel);
  panelScrim.addEventListener('click', closePanel);
  // Desktop has no scrim (the rail coexists with the grid), so close on a
  // click outside the panel that is not on another card (a card click
  // re-opens the panel via the grid handler below).
  document.addEventListener('click', (e) => {
    if (panel.hidden) return;
    if (e.target.closest('.member-preview-panel, .member-card')) return;
    if (e.target.closest('.tour-backdrop, .tour-tooltip, .tour-trigger')) return;
    closePanel();
  });

  grid.addEventListener('click', (e) => {
    if (!grid.classList.contains('is-compact')) return;
    if (e.target.closest('a, button')) return; // let the name link / contact icons work
    const card = e.target.closest('.member-card');
    if (!card) return;
    // Clicking the card whose panel is already open closes it (toggle);
    // clicking a different card switches the panel to that member.
    if (!panel.hidden && panelTrigger === card) closePanel();
    else openPanel(card);
  });
  // Enter/Space on a focused card mirrors the click.
  grid.addEventListener('keydown', (e) => {
    if (!grid.classList.contains('is-compact')) return;
    if (e.key !== 'Enter' && e.key !== ' ') return;
    const card = e.target.closest('.member-card');
    if (!card) return;
    e.preventDefault();
    card.click();
  });

  // "+" button in the toolbar: smooth-scroll to the join card and
  // focus its "Add your bio" CTA so the next keypress submits.
  const joinTrigger = document.getElementById('join-trigger');
  if (joinTrigger) {
    joinTrigger.addEventListener('click', () => {
      const joinCard = document.getElementById('join');
      if (!joinCard) return;
      joinCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
      setTimeout(() => {
        const cta = joinCard.querySelector('.join-card-cta');
        if (cta && !cta.hidden) cta.focus({ preventScroll: true });
      }, 380);
    });
  }

  let MEMBERS = [];
  let featuredId = null;            // weekly member-spotlight id (data/spotlight.json, #921)
  const SPOTLIGHT_LABEL = 'Member spotlight';
  // activeWG values:
  //   'all'                — no WG/role filter
  //   '1' | '2' | '3' | '4' — that working group (lead, co-lead, or member)
  //   'mc'                 — MC member role (sync-bios.py auto-tags
  //                          these as "Management Committee · <Country>")
  let activeWG = 'all';
  let activeCountry = 'all';
  // Mentorship filter: a separate AND dimension, multi-select OR (like the
  // theme and region chip rows). A Set of opted-in role tags:
  //   'mentor' — members open to mentoring (m.mentorship includes "mentor")
  //   'mentee' — members seeking a mentor (m.mentorship includes "mentee")
  // Each chip toggles its tag; an empty Set means no mentorship filter (the
  // old "All" state, now implicit). Transient (no URL hash). The chip row
  // stays hidden until the data carries at least one mentorship facet.
  const activeMentorship = new Set();
  // The visitor's own career stage (0 doctoral … 3 senior, or null), set by
  // the "find a mentoring match" card. Transient: a session variable only,
  // never stored and never in the URL. It gently personalises the panel's
  // ordering (a mentor a step above you, a mentee a step below).
  let viewerStage = null;
  // STSM-hosting filter (#760): a single boolean facet. When true, the
  // grid is narrowed to members whose institution can host STSM visitors
  // ("yes" or "ask"). Bookmarkable via `#stsm=1` so the grants page can
  // deep-link to the pre-filtered directory.
  let activeStsm = false;
  // Research-interest filter: a Set of canonical-keyword *slugs*
  // (lowercase, non-word → hyphen). Kept as slugs so URL hash
  // round-trips are stable and chip-on-card clicks resolve cleanly.
  // OR semantics across selected entries (any match keeps the bio).
  // Empty Set = no keyword filter applied.
  const activeKeywords = new Set();
  let KEYWORD_AGGREGATE = []; // [{ keyword: <theme name>, count: number }, …]
  let KEYWORD_THEME_MAP = {}; // canonical keyword → theme name (card pills)
  // Research-region filter (#555): a second, geographic axis independent
  // of the topical themes. Multi-select OR; the row stays hidden until
  // the data carries at least one region (the optional Research-regions
  // form field). No URL-hash persistence in this version (cf. mentorship).
  let REGION_AGGREGATE = []; // [{ region: string, count: number }, …]
  const activeRegions = new Set(); // region slugs
  let regionFilterExpanded = false;
  let keywordFilterExpanded = false;
  const KEYWORD_FILTER_VISIBLE_TOP_N = 8;

  function isMC(m) {
    return (m.roles || []).some(r => /^Management Committee\b/i.test(r));
  }

  // Slugify a canonical keyword for URL hash use. Lowercase the
  // string, then replace any run of non-word characters (including
  // spaces, en-dashes, ampersands) with a single hyphen, and trim
  // hyphens from the ends. Examples:
  //   "International security"     → "international-security"
  //   "EU–NATO relations"          → "eu-nato-relations"
  //   "R&D"                        → "r-d"
  // The slug is reversible only via the keyword_aggregate (slug →
  // canonical lookup), which is fine because the aggregate is
  // always loaded alongside the filter chips.
  function keywordSlug(canonical) {
    return String(canonical || '')
      .toLowerCase()
      .replace(/[^\p{L}\p{N}]+/gu, '-')
      .replace(/^-+|-+$/g, '');
  }

  // Shared sitewide rule from site.js (#1194): salutation stripped,
  // first letter of first and last name. This file's old fork took the
  // first two words instead, so a middle-named member rendered
  // different avatar initials here than in search or the spotlight.
  const initials = window.netsecInitials;

  // Fallback normaliser. Used only when a bio lacks the sync-emitted
  // `canonical_keywords` field (an old bios.json, a hand-edited
  // record, or a transition period). For any normal sync, the Python
  // sync script (`scripts/sync-bios.py` + `data/keyword-aliases.json`)
  // produces fully canonicalised keywords already; the renderer just
  // reads them. A short acronym list stays inline so the fallback
  // path doesn't render "Eu-nato relations" on first paint while the
  // upgrade rolls through.
  const KEYWORD_ACRONYMS_FALLBACK = {
    'un':'UN','eu':'EU','nato':'NATO','uk':'UK','us':'US','usa':'USA',
    'ai':'AI','iot':'IoT','gdpr':'GDPR','r&d':'R&D',
  };
  function normaliseKeywordDisplay(raw) {
    const trimmed = String(raw || '').trim();
    if (!trimmed) return '';
    let firstAlpha = true;
    return trimmed.replace(/[\p{L}&]+/gu, (word) => {
      const lower = word.toLowerCase();
      if (KEYWORD_ACRONYMS_FALLBACK[lower]) {
        firstAlpha = false;
        return KEYWORD_ACRONYMS_FALLBACK[lower];
      }
      if (firstAlpha) {
        firstAlpha = false;
        return lower.charAt(0).toUpperCase() + lower.slice(1);
      }
      return lower;
    });
  }

  // Title-case for the card pills: the shared helper in site.js
  // (#1194), which still mirrors the spotlight composer
  // (scripts/social-post.py `titlecase_theme`) by necessity — the
  // Python side runs at build time, the JS side at render time.
  // Applied to display text only — the original canonical form still
  // drives the theme lookup, slug, and dedup.
  const titlecaseTheme = window.netsecTitlecaseTheme;

  function leadershipOrder(m) {
    // Sort key: leadership first, then country reps alphabetical
    const r = (m.roles || []).join(' ');
    if (/Action Chair$/.test(r)) return '01';
    if (/Vice-Chair/.test(r)) return '02';
    if (/Grant Holder/.test(r)) return '03';
    if (/Science Communication/.test(r)) return '04';
    if (/Grant Awarding Coord/.test(r)) return '05';
    if (/Grant Awarding Co-/.test(r)) return '06';
    if (/WG1 Leader/.test(r)) return '07';
    if (/WG2 Leader/.test(r)) return '08';
    if (/WG3 Leader/.test(r)) return '09';
    if (/WG4 Leader/.test(r)) return '10';
    if (/WG1 Co-Leader/.test(r)) return '11';
    if (/WG2 Co-Leader/.test(r)) return '12';
    if (/WG3 Co-Leader/.test(r)) return '13';
    if (/WG4 Co-Leader/.test(r)) return '14';
    return '99' + (m.name || '').toLowerCase();
  }

  // Recent publications (#761). data/orcid-works.json is fetched once,
  // lazily, after the directory has gone idle — never on the critical
  // path — then backfilled into the rendered cards. Member cards carry
  // none of its weight at load. Keyed by member slug, up to three works.
  let ORCID_WORKS = null;       // slug -> [ {title, year, journal, doi} ]
  let orcidWorksPromise = null;
  let orcidKicked = false;
  function loadOrcidWorks() {
    if (orcidWorksPromise) return orcidWorksPromise;
    orcidWorksPromise = fetch('data/orcid-works.json', { cache: 'no-cache' })
      .then(r => (r.ok ? r.json() : null))
      .then(d => { ORCID_WORKS = (d && d.works) || {}; return ORCID_WORKS; })
      .catch(() => { ORCID_WORKS = {}; return ORCID_WORKS; });
    return orcidWorksPromise;
  }
  function fillMemberPubs(node, slug) {
    // No-op until the works file has loaded; render() calls this inline so
    // a re-render (filter change) repaints from the in-memory cache, and
    // backfillPubs() calls it once the deferred fetch resolves.
    if (!ORCID_WORKS) return;
    const wrap = node.querySelector('.member-pubs');
    if (!wrap) return;
    const works = (slug && ORCID_WORKS[slug]) || [];
    wrap.textContent = '';
    if (!works.length) { wrap.setAttribute('hidden', ''); return; }
    const title = document.createElement('p');
    title.className = 'member-pubs-title';
    title.textContent = window.netsecT('Recent publications');
    wrap.appendChild(title);
    const ul = document.createElement('ul');
    ul.className = 'member-pubs-list';
    works.forEach(w => {
      const li = document.createElement('li');
      let head;
      if (w.doi) {
        head = document.createElement('a');
        head.href = 'https://doi.org/' + w.doi;
        head.target = '_blank';
        head.rel = 'noopener';
      } else {
        head = document.createElement('span');
      }
      head.className = 'member-pubs-link';
      head.textContent = w.title;
      li.appendChild(head);
      const bits = [w.year, w.journal].filter(Boolean);
      if (bits.length) {
        const meta = document.createElement('span');
        meta.className = 'member-pubs-meta';
        meta.textContent = ' (' + bits.join(', ') + ')';
        li.appendChild(meta);
      }
      ul.appendChild(li);
    });
    wrap.appendChild(ul);
    wrap.removeAttribute('hidden');
  }
  function backfillPubs() {
    document.querySelectorAll('#members-grid .member-card[data-slug]')
      .forEach(card => fillMemberPubs(card, card.getAttribute('data-slug')));
  }

  // Mentorship matching panel state (#869). When true, the panel relaxes its
  // research-theme / research-region scoping and shows mentors and mentees
  // from across the network, so a member who tagged themselves narrowly is
  // never hidden from a mentee browsing by area. Reset on every render() (so
  // any filter change collapses it back); the relax button re-renders the
  // panel only, so it persists until the next filter change.
  let mentorshipShowOutsideScope = false;
  // The search query in force at the last render(), so renderMentorshipPanel()
  // can rebuild its (separately scoped) member pool without re-reading the
  // input element.
  let _lastQuery = '';

  // Single source of truth for the directory filter predicate, shared by the
  // grid and the mentorship matching panel (#869). `skipMentorship` lets the
  // panel pool everyone who passes the *other* facets, then split that pool
  // into Offering / Seeking. `skipAreas` additionally drops the theme and
  // region filters, powering the panel's "show people outside your selected
  // areas" escape hatch.
  function memberPassesFilters(m, q, opts) {
    opts = opts || {};
    if (activeWG === 'mc') {
      if (!isMC(m)) return false;
    } else if (activeWG !== 'all') {
      const wgs = (m.wgs || []).concat((m.wg_leadership && (m.wg_leadership.lead || [])) || [], (m.wg_leadership && (m.wg_leadership.co_lead || [])) || []);
      if (!wgs.includes(Number(activeWG))) return false;
    }
    if (activeCountry !== 'all') {
      if ((m.country || '') !== activeCountry) return false;
    }
    if (!opts.skipMentorship && activeMentorship.size > 0) {
      if (!(m.mentorship || []).some(t => activeMentorship.has(t))) return false;
    }
    if (activeStsm) {
      if (m.stsm_hosting !== 'yes' && m.stsm_hosting !== 'ask') return false;
    }
    if (q) {
      const hay = [m.name, m.affiliation, m.country, (m.roles||[]).join(' '), (m.keywords||[]).join(' '), (m.canonical_keywords||[]).join(' ')].join(' ').toLowerCase();
      if (!hay.includes(q)) return false;
    }
    // Theme filter (OR semantics): a bio passes when one of its research
    // themes is in the active set. Empty set = no filter. Skipped for the
    // panel's relaxed pool.
    if (!opts.skipAreas && activeKeywords.size > 0) {
      const bioThemeSlugs = (m.themes || []).map(keywordSlug);
      if (!bioThemeSlugs.some(s => activeKeywords.has(s))) return false;
    }
    // Research-region filter (#555): a second, independent axis, AND-combined
    // with the theme filter (so "cyber AND Russia" narrows). Also skipped for
    // the relaxed pool.
    if (!opts.skipAreas && activeRegions.size > 0) {
      const bioRegionSlugs = (m.regions || []).map(keywordSlug);
      if (!bioRegionSlugs.some(s => activeRegions.has(s))) return false;
    }
    return true;
  }

  function render() {
    grid.replaceChildren();
    const q = (search.value || '').trim().toLowerCase();
    _lastQuery = q;
    mentorshipShowOutsideScope = false;
    const filtered = MEMBERS.filter(m => memberPassesFilters(m, q, {}));

    filtered.sort((a, b) => leadershipOrder(a).localeCompare(leadershipOrder(b)) || (a.name||'').localeCompare(b.name||''));
    // Member spotlight (#921): in the default, unfiltered view, pin the
    // weekly-featured member to the front so they read first.
    const featuredView = !!(featuredId && q === '' && filtered.length === MEMBERS.length);
    if (featuredView) {
      const _fi = filtered.findIndex(m => m.id === featuredId);
      if (_fi > 0) { const _fm = filtered.splice(_fi, 1)[0]; filtered.unshift(_fm); }
    }

    filtered.forEach(m => {
      const node = tpl.content.firstElementChild.cloneNode(true);
      // Slug attribute powers the deep-link "expand this card" flow
      // and gives the existing leadership-card live-refresh anywhere
      // else on the site a consistent hook to find members by id.
      if (m.id) node.setAttribute('data-slug', m.id);
      if (featuredView && m.id === featuredId) {
        node.classList.add('is-featured');
        const _pin = document.createElement('div');
        _pin.className = 'member-spotlight-pin';
        _pin.innerHTML = '<span class="member-spotlight-badge"><svg viewBox="0 0 24 24" width="13" height="13" fill="currentColor" aria-hidden="true"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg><span>' + SPOTLIGHT_LABEL + '</span></span>';
        node.insertBefore(_pin, node.firstChild);
      }
      // Keyboard focusability is mode-dependent: in compact mode
      // cards are interactive (click expands), in detailed mode the
      // card itself doesn't do anything (contact icons inside it do).
      if (grid.classList.contains('is-compact')) {
        node.setAttribute('tabindex', '0');
      }
      const img = node.querySelector('img');
      const webpSource = node.querySelector('.member-photo-webp');
      const fallback = node.querySelector('.member-photo-fallback');
      if (m.photo) {
        img.src = m.photo;
        img.alt = m.name || '';
        const w = window.netsecWebp && window.netsecWebp(m.photo);
        if (w && webpSource) webpSource.srcset = w;
        else if (webpSource) webpSource.remove();
        fallback.style.display = 'none';
      } else {
        const pic = img.closest('picture');
        (pic || img).remove();
        fallback.textContent = initials(m.name);
      }
      const _phref = profileHref(m.id);
      const nameEl = node.querySelector('.member-name');
      if (_phref) {
        const nameLink = document.createElement('a');
        nameLink.className = 'member-name-link';
        nameLink.href = _phref;
        nameLink.textContent = m.name || '';
        nameEl.appendChild(nameLink);
      } else {
        nameEl.textContent = m.name || '';
      }
      // Role pill: formal role(s) if any, otherwise WG-participant; a
      // member with neither shows no pill at all.
      const roleEl = node.querySelector('.member-role');
      if ((m.roles || []).length) {
        // Translate each role label via the catalog while preserving
        // the " · Country" suffix for roles like "Management Committee · Switzerland".
        roleEl.textContent = m.roles.map(r => window.netsecT(r)).join(' · ');
      } else {
        const hasWGs = (m.wgs || []).length || ((m.wg_leadership || {}).lead || []).length || ((m.wg_leadership || {}).co_lead || []).length;
        if (hasWGs) {
          roleEl.textContent = window.netsecT('Working Group participant');
          roleEl.classList.add('is-soft');
        } else {
          roleEl.remove();
        }
      }
      // Affiliation line: optional position prefix (e.g. PhD candidate)
      // + institution + flag + country.
      //
      // We render TWO parallel versions inside this line so the
      // compact view can show a tighter form without re-rendering
      // the card. Both versions sit in the DOM; CSS picks which is
      // visible based on the .is-compact class on the grid:
      //
      //   .aff-full    — position · affiliation · country  (detailed)
      //   .aff-compact — affiliation only                  (compact)
      //
      // The flag stays in both modes — it conveys country
      // implicitly so we drop the country name from the compact
      // form to save the row.
      const aff = node.querySelector('.member-affiliation');
      const affParts = [m.position, m.affiliation, m.country].filter(Boolean);
      if (affParts.length) {
        aff.innerHTML = '';
        if (m.country_code) {
          const flag = document.createElement('img');
          flag.className = 'member-flag';
          flag.src = `https://flagcdn.com/h20/${m.country_code}.png`;
          flag.alt = ''; flag.loading = 'lazy';
          aff.appendChild(flag);
          aff.appendChild(document.createTextNode(' '));
        }
        const full = document.createElement('span');
        full.className = 'aff-full';
        full.textContent = affParts.join(' · ');
        aff.appendChild(full);
        if (m.affiliation) {
          const compact = document.createElement('span');
          compact.className = 'aff-compact';
          compact.textContent = m.affiliation;
          aff.appendChild(compact);
        }
      } else {
        aff.remove();
      }
      // WG chips
      const wgsAll = Array.from(new Set([].concat(m.wgs || [], (m.wg_leadership && m.wg_leadership.lead) || [], (m.wg_leadership && m.wg_leadership.co_lead) || []))).sort();
      const wgWrap = node.querySelector('.member-wgs');
      if (wgsAll.length) {
        wgsAll.forEach(w => {
          const c = document.createElement('span');
          c.className = 'wg-chip wg-' + w;
          c.textContent = 'WG' + w;
          wgWrap.appendChild(c);
        });
      } else {
        wgWrap.remove();
      }
      // Founding-contributor badge. A subdued outlined pill, visually
      // distinct from the bright-gradient WG chips, set on members whose
      // name matches the COST Open Call proposer list (the
      // founding_contributor flag is written by sync-bios.py). It reads
      // as a soft acknowledgement, not a role, so it sits below the WG
      // chips rather than in the role line.
      const foundingWrap = node.querySelector('.member-founding');
      if (m.founding_contributor) {
        const pill = document.createElement('span');
        pill.className = 'founding-badge';
        pill.textContent = window.netsecT('Founding contributor');
        pill.title = window.netsecT('Listed in the COST Open Call proposal OC-2024-1-27931');
        foundingWrap.appendChild(pill);
        foundingWrap.removeAttribute('hidden');
      } else {
        foundingWrap.remove();
      }
      // Mentorship badges. Offering ("mentor") and/or seeking
      // ("mentee"), read from m.mentorship (a list of role tags
      // emitted by sync-bios.py). The block stays hidden when the
      // member carries no facet, so it costs nothing while the Form
      // question is dormant and no member has opted in yet.
      const mentorWrap = node.querySelector('.member-mentorship');
      const mentorship = Array.isArray(m.mentorship) ? m.mentorship : [];
      const MENTOR_BADGES = [
        { tag: 'mentor', cls: 'is-offering', label: 'Available to mentor' },
        { tag: 'mentee', cls: 'is-seeking', label: 'Seeking mentorship' },
      ];
      let mentorAdded = false;
      MENTOR_BADGES.forEach(badge => {
        if (!mentorship.includes(badge.tag)) return;
        const span = document.createElement('span');
        span.className = 'mentorship-badge ' + badge.cls;
        span.textContent = window.netsecT(badge.label);
        mentorWrap.appendChild(span);
        mentorAdded = true;
      });
      if (mentorAdded) mentorWrap.removeAttribute('hidden');
      else mentorWrap.remove();
      // STSM hosting badge (#760): a quiet pill on hosts. "yes" reads as a
      // firm offer, "ask" as a conditional one. Absent for everyone else,
      // so it costs nothing while the Form question is still gathering data.
      const stsmWrap = node.querySelector('.member-stsm');
      if (stsmWrap && (m.stsm_hosting === 'yes' || m.stsm_hosting === 'ask')) {
        const span = document.createElement('span');
        span.className = 'stsm-badge' + (m.stsm_hosting === 'ask' ? ' is-ask' : '');
        span.textContent = window.netsecT(
          m.stsm_hosting === 'ask' ? 'Open to hosting STSM visitors' : 'Can host STSM visitors');
        stsmWrap.appendChild(span);
        stsmWrap.removeAttribute('hidden');
      } else if (stsmWrap) {
        stsmWrap.remove();
      }
      // Bio (or pending notice)
      const bio = node.querySelector('.member-bio');
      if (m.bio) {
        bio.textContent = m.bio;
      } else {
        bio.classList.add('is-pending');
        bio.textContent = window.netsecT('Bio coming soon.');
      }
      // Research-interest keywords. Detailed view only (CSS hides
      // the block in compact mode so the dense card stays readable).
      // Prefer `canonical_keywords` produced by the Python sync —
      // those are already resolved through `data/keyword-aliases.json`
      // (aliases) + the acronym word-walk. Falls back to the raw
      // `keywords` list and a tiny inline normaliser when the field
      // is missing (older bios.json, hand-edited record). The raw
      // `keywords` list also still feeds the directory search vector
      // (see line ~586).
      const kwWrap = node.querySelector('.member-keywords');
      const canonical = Array.isArray(m.canonical_keywords) ? m.canonical_keywords.filter(Boolean) : null;
      const kws = canonical && canonical.length
        ? canonical
        : (Array.isArray(m.keywords) ? m.keywords.filter(Boolean).map(normaliseKeywordDisplay) : []);
      if (kws.length) {
        const seen = new Set();
        kws.forEach(display => {
          if (!display) return;
          const dedupKey = display.toLowerCase();
          if (seen.has(dedupKey)) return;
          seen.add(dedupKey);
          // The pill shows the member's specific keyword; the directory
          // filter operates on its broader *theme*. When the keyword maps
          // to a theme, render a clickable button that selects that theme
          // (and scrolls up to the filter row); otherwise a static pill so
          // an unthemed keyword still displays without a dead control.
          const label = titlecaseTheme(display);
          const theme = KEYWORD_THEME_MAP[display] || null;
          if (!theme) {
            const span = document.createElement('span');
            span.className = 'member-keyword-chip is-static';
            span.textContent = label;
            kwWrap.appendChild(span);
            return;
          }
          const chip = document.createElement('button');
          chip.type = 'button';
          chip.className = 'member-keyword-chip';
          chip.textContent = label;
          const slug = keywordSlug(theme);
          chip.setAttribute('data-theme-slug', slug);
          chip.setAttribute('aria-label',
            window.netsecT('Filter by research theme') + ': ' + window.netsecT(theme));
          chip.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleKeywordFilter(slug);
            const filterRow = document.getElementById('members-keyword-filter');
            if (filterRow && !filterRow.hidden) {
              filterRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
          });
          kwWrap.appendChild(chip);
        });
        kwWrap.removeAttribute('hidden');
      }
      // Research-region pills (#555): the member's regions of expertise,
      // from the optional form field. Clickable — selects that region in
      // the filter row and scrolls up to it. Hidden when the member has none.
      const rgWrap = node.querySelector('.member-regions');
      const memberRegions = Array.isArray(m.regions) ? m.regions.filter(Boolean) : [];
      if (rgWrap && memberRegions.length) {
        memberRegions.forEach(region => {
          const slug = keywordSlug(region);
          const chip = document.createElement('button');
          chip.type = 'button';
          chip.className = 'member-keyword-chip member-region-chip';
          chip.textContent = window.netsecT(region);
          chip.setAttribute('data-region-slug', slug);
          chip.setAttribute('aria-label',
            window.netsecT('Filter by research region') + ': ' + window.netsecT(region));
          chip.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleRegionFilter(slug);
            const filterRow = document.getElementById('members-region-filter');
            if (filterRow && !filterRow.hidden) {
              filterRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
          });
          rgWrap.appendChild(chip);
        });
        rgWrap.removeAttribute('hidden');
      }
      // Contact links. Two icon styles: `stroke` (generic Lucide-like
      // line icons, used for email + website) and `fill` (official brand
      // glyphs, used for ORCID, LinkedIn, X, Bluesky, Mastodon).
      //
      // ORCID normaliser: defensive against bios.json containing a
      // pasted full URL rather than the bare 19-character ID. The
      // sync script (sync-bios.py → normalize_orcid) is the primary
      // line of defence at write time; this is the safety net at
      // render time for any historical or hand-edited record. Strips
      // any orcid.org URL prefix, drops trailing slashes / queries /
      // fragments, then asserts the canonical pattern. Returns null
      // for unrecognised input so the icon is silently omitted
      // rather than rendered with a broken double-prefixed href.
      const orcidId = (raw => {
        if (!raw) return null;
        let s = String(raw).trim();
        s = s.replace(/^(?:https?:\/\/)?(?:sandbox\.)?orcid\.org\//i, '');
        s = s.split('?')[0].split('#')[0].replace(/\/+$/, '').trim();
        // 16 digits no hyphens → re-insert
        if (/^\d{15}[\dX]$/i.test(s)) {
          s = `${s.slice(0,4)}-${s.slice(4,8)}-${s.slice(8,12)}-${s.slice(12,16)}`;
        }
        return /^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$/i.test(s) ? s.toUpperCase() : null;
      })(m.orcid);

      const contact = node.querySelector('.member-contact');
      const icons = [
        m.email && {
          href: 'mailto:' + m.email, label: 'Email', style: 'stroke',
          path: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>'
        },
        m.website && {
          href: m.website, label: 'Website', style: 'stroke',
          path: '<circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 010 20M12 2a15.3 15.3 0 000 20"/>'
        },
        orcidId && {
          href: 'https://orcid.org/' + orcidId, label: 'ORCID iD', style: 'orcid',
          // ORCID brand mark (single path, even-odd fill-rule): solid
          // circle with the "iD" cut out via sub-paths. Rendered in
          // ORCID green via the `.contact-orcid` class below.
          path: '<path fill-rule="evenodd" d="M12 0C5.372 0 0 5.372 0 12s5.372 12 12 12 12-5.372 12-12S18.628 0 12 0zM7.369 4.378c.525 0 .947.431.947.947 0 .525-.422.947-.947.947a.95.95 0 01-.947-.947c0-.516.422-.947.947-.947zm-.722 3.038h1.444v10.041H6.647V7.416zm3.562 0h3.9c3.712 0 5.344 2.653 5.344 5.025 0 2.578-2.016 5.025-5.325 5.025h-3.919V7.416zm1.444 1.303v7.444h2.297c3.272 0 4.022-2.484 4.022-3.722 0-2.016-1.284-3.722-4.094-3.722H12.8z"/>'
        },
        m.linkedin && {
          href: m.linkedin, label: 'LinkedIn', style: 'fill',
          // LinkedIn brand glyph (single path, even-odd): rounded
          // square with the "in" wordmark carved out.
          path: '<path fill-rule="evenodd" d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.063 2.063 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>'
        },
        m.twitter && {
          href: m.twitter, label: 'X', style: 'fill',
          // X (formerly Twitter) brand mark — the angular "X" crossbars.
          path: '<path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>'
        },
        m.bluesky && {
          href: m.bluesky, label: 'Bluesky', style: 'fill',
          // Bluesky brand mark (Simple Icons) — the butterfly silhouette,
          // filling the 24x24 box natively so it needs no scale transform.
          path: '<path d="M12 10.8c-1.087-2.114-4.046-6.053-6.798-7.995C2.566.944 1.561 1.266.902 1.565.139 1.908 0 3.08 0 3.768c0 .69.378 5.65.624 6.479.815 2.736 3.713 3.66 6.383 3.364.136-.02.275-.039.415-.056-.138.022-.276.04-.415.056-3.912.58-7.387 2.005-2.83 7.078 5.013 5.19 6.87-1.113 7.823-4.308.953 3.195 2.81 8.477 7.823 4.308 4.557-5.073 1.082-6.498-2.83-7.078a8.741 8.741 0 0 1-.415-.056c.14.017.279.036.415.056 2.67.297 5.568-.628 6.383-3.364.246-.829.624-5.79.624-6.479 0-.688-.139-1.86-.902-2.203-.659-.299-1.664-.621-4.3 1.24C16.046 4.748 13.087 8.687 12 10.8Z"/>'
        },
        m.mastodon && {
          href: m.mastodon, label: 'Mastodon', style: 'fill',
          // Mastodon brand mark — the rounded "M" with the trunk descenders.
          path: '<path fill-rule="evenodd" d="M23.27 5.31c-.35-2.58-2.62-4.61-5.31-5C17.51.25 15.79 0 11.81 0h-.03c-3.98 0-4.83.25-5.29.31C3.88.7 1.5 2.52.92 5.13.64 6.41.61 7.84.66 9.14c.07 1.88.09 3.74.26 5.61.12 1.24.32 2.47.62 3.68.55 2.24 2.78 4.1 4.96 4.86 2.34.79 4.85.92 7.26.38.26-.06.53-.13.79-.21.59-.18 1.27-.39 1.77-.75v-1.85a20.28 20.28 0 01-4.71.54c-2.73 0-3.46-1.28-3.67-1.82a5.6 5.6 0 01-.32-1.43c1.51.36 3.07.55 4.63.55l1.13-.01c1.57-.04 3.22-.12 4.77-.42l.11-.02c2.43-.46 4.75-1.92 4.99-5.6.01-.15.03-1.52.03-1.67 0-.51.17-3.63-.02-5.55zm-3.75 9.19h-2.56V8.29c0-1.31-.55-1.98-1.67-1.98-1.23 0-1.85.79-1.85 2.35v3.4h-2.55V8.66c0-1.56-.62-2.35-1.85-2.35-1.11 0-1.67.67-1.67 1.98v6.22H4.82V8.1c0-1.31.34-2.35 1.01-3.12.7-.77 1.61-1.16 2.74-1.16 1.31 0 2.3.5 2.96 1.5l.64 1.06.64-1.06c.66-1 1.65-1.5 2.96-1.5 1.13 0 2.04.39 2.74 1.16.68.77 1.01 1.81 1.01 3.12v6.4z"/>'
        }
      ].filter(Boolean);

      icons.forEach(i => {
        if (i.style !== 'stroke' && !i.path) return;  // skip placeholders
        const a = document.createElement('a');
        a.href = i.href;
        a.setAttribute('aria-label', i.label);
        a.setAttribute('title', i.label);
        if (i.href.startsWith('http')) { a.target = '_blank'; a.rel = 'noopener'; }
        if (i.style === 'orcid') {
          a.classList.add('contact-orcid');
        }
        const attrs = i.style === 'stroke'
          ? 'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"'
          : 'viewBox="0 0 24 24" fill="currentColor"';
        a.innerHTML = '<svg ' + attrs + ' aria-hidden="true">' + i.path + '</svg>';
        contact.appendChild(a);
      });
      if (!contact.children.length) contact.remove();
      // "View full profile" CTA into the standalone profile page. Hidden
      // on compact-collapsed cards (CSS), shown when expanded / in
      // detailed view; the linked name above reaches the same page from
      // the compact grid.
      if (_phref) {
        const cta = document.createElement('a');
        cta.className = 'member-profile-cta';
        cta.href = _phref;
        cta.textContent = window.netsecT('View full profile') + ' →';
        node.querySelector('.member-body').appendChild(cta);
      }
      // Recent publications (lazy): fills from the in-memory cache if the
      // deferred ORCID fetch has already resolved, otherwise backfillPubs()
      // populates it once the fetch lands.
      fillMemberPubs(node, m.id);
      // Deep-link anchor
      node.id = m.id;
      grid.appendChild(node);
    });

    countEl.textContent = (filtered.length === MEMBERS.length)
      ? filtered.length + ' ' + window.netsecT(filtered.length === 1 ? 'member' : 'members')
      : filtered.length + ' / ' + MEMBERS.length + ' ' + window.netsecT('members');
    empty.hidden = filtered.length > 0;
    _lastCount = filtered.length;
    updateFilterChrome();
    renderMentorshipPanel();

    // Kick the deferred publications load exactly once, off the critical
    // path. Cards are already painted from bios.json; the works arrive in a
    // single follow-up fetch (#761) and backfill into place when idle.
    if (!orcidKicked) {
      orcidKicked = true;
      (window.requestIdleCallback || function (cb) { return setTimeout(cb, 1200); })(
        function () { loadOrcidWorks().then(backfillPubs); }
      );
    }

    // After the cards are in the DOM, detect which bios overflow the
    // four-line clamp and add a "Show more"/"Show less" toggle to those.
    //
    // Previously this check was wrapped in requestAnimationFrame on the
    // theory that we needed to wait for layout before reading
    // scrollHeight. That turned out to be unnecessary AND unreliable:
    // reading scrollHeight already forces a synchronous layout in every
    // modern browser, and the rAF callback was observed to fire too
    // early in some scenarios (returning scrollHeight == clientHeight
    // because the line-clamp hadn't settled), or not fire at all on
    // tabs that lost focus during data fetch. The symptom in production
    // was that long bios stayed clamped to four lines with no expand
    // affordance, so the user could never read the full text.
    //
    // The synchronous version works for the same reason rAF was
    // *thought* to be needed: scrollHeight access flushes layout. We
    // also observe each newly-rendered bio with a ResizeObserver so
    // that any later metric change (font swap, theme toggle, viewport
    // resize) re-runs the overflow check.
    function tryInsertBioToggle(bio) {
      if (!bio || bio.classList.contains('is-pending')) return;
      if (bio.nextElementSibling && bio.nextElementSibling.classList.contains('member-bio-toggle')) return;
      if (bio.scrollHeight - bio.clientHeight < 2) return;  // fits within clamp
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'member-bio-toggle';
      btn.setAttribute('aria-expanded', 'false');
      btn.innerHTML = '<span class="lbl">' + window.netsecT('Show more') + '</span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>';
      btn.addEventListener('click', () => {
        const expanded = bio.classList.toggle('is-expanded');
        btn.classList.toggle('is-expanded', expanded);
        btn.setAttribute('aria-expanded', expanded);
        btn.querySelector('.lbl').textContent = window.netsecT(expanded ? 'Show less' : 'Show more');
      });
      bio.insertAdjacentElement('afterend', btn);
    }
    grid.querySelectorAll('.member-bio').forEach(tryInsertBioToggle);
    // ResizeObserver belt-and-braces: handles the rare case where the
    // bio's clamped height isn't final at sync time (web-font swap,
    // user changes zoom, etc.). The observer fires once per bio after
    // its first layout box, then on every subsequent box change.
    if (typeof ResizeObserver === 'function') {
      if (!window.__bioResizeObserver) {
        window.__bioResizeObserver = new ResizeObserver(entries => {
          entries.forEach(entry => tryInsertBioToggle(entry.target));
        });
      }
      grid.querySelectorAll('.member-bio').forEach(b => window.__bioResizeObserver.observe(b));
    }
  }

  // Filter handlers
  filterChips.forEach(b => {
    b.addEventListener('click', () => {
      activeWG = b.dataset.wg;
      filterChips.forEach(o => o.setAttribute('aria-pressed', o === b));
      render();
    });
  });
  mentorshipChips.forEach(b => {
    b.addEventListener('click', () => {
      const v = b.dataset.mentorship;
      if (activeMentorship.has(v)) activeMentorship.delete(v);
      else activeMentorship.add(v);
      b.setAttribute('aria-pressed', activeMentorship.has(v));
      writeHashKeywords();
      render();
    });
  });
  if (stsmChip) {
    stsmChip.addEventListener('click', () => {
      activeStsm = !activeStsm;
      stsmChip.setAttribute('aria-pressed', activeStsm ? 'true' : 'false');
      writeHashKeywords();
      render();
    });
  }
  if (countrySelect) {
    countrySelect.addEventListener('change', () => {
      activeCountry = countrySelect.value;
      render();
    });
  }
  let searchTimeout;
  search.addEventListener('input', () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(render, 120);
  });

  // Results bar: a global "Clear all filters" control, shown whenever any
  // filter is active.
  const clearAllBtn = document.getElementById('members-clear-all');
  // The theme + region facets are collapsible disclosures (collapsed by
  // default); open the relevant one when a filter inside it becomes active.
  const keywordDetails = document.getElementById('members-keyword-filter');
  const regionDetails = document.getElementById('members-region-filter');
  function anyFilterActive() {
    return search.value.trim() !== '' || activeWG !== 'all' || activeCountry !== 'all'
      || activeMentorship.size > 0 || activeStsm || activeKeywords.size > 0 || activeRegions.size > 0;
  }
  function updateFilterChrome() {
    if (clearAllBtn) clearAllBtn.disabled = !anyFilterActive();
    // Mobile filter-sheet chrome: the "Filters • N" badge, the apply
    // button's live count, and the removable active-filter chip row.
    if (filterToggleCount) {
      const n = sheetFilterCount();
      filterToggleCount.hidden = n === 0;
      filterToggleCount.textContent = n;
    }
    if (sheetApplyBtn) {
      sheetApplyBtn.textContent = window.netsecT('Show {0} members').replace('{0}', _lastCount);
    }
    renderActiveFilters();
  }
  function clearAllFilters() {
    search.value = '';
    activeWG = 'all';
    filterChips.forEach(o => o.setAttribute('aria-pressed', o.dataset.wg === 'all'));
    activeCountry = 'all';
    if (countrySelect) countrySelect.value = 'all';
    activeMentorship.clear();
    mentorshipChips.forEach(o => o.setAttribute('aria-pressed', 'false'));
    activeStsm = false;
    syncStsmChip();
    viewerStage = null;  // the in-panel career-stage nudge is a filter too
    activeKeywords.clear();
    activeRegions.clear();
    writeHashKeywords();
    renderKeywordFilter();
    renderRegionFilter();
    render();
  }
  if (clearAllBtn) clearAllBtn.addEventListener('click', clearAllFilters);

  // ──────────────────────────────────────────────────────────────────
  // Mobile filter sheet (≤640px). The same filter controls (Working
  // Group, country, themes, regions, mentorship) live in a bottom sheet
  // opened by the "Filters" button; on desktop they render inline and
  // this chrome is hidden. Filters apply live, so the sheet's primary
  // button just shows the current count and closes the sheet.
  let _lastCount = 0;
  const filterToggleBtn = document.getElementById('members-filter-toggle');
  const filterToggleCount = document.getElementById('members-filter-toggle-count');
  const filterSet = document.getElementById('members-filterset');
  const sheetCloseBtn = document.getElementById('members-sheet-close');
  const sheetResetBtn = document.getElementById('members-sheet-reset');
  const sheetApplyBtn = document.getElementById('members-sheet-apply');
  const activeFiltersEl = document.getElementById('members-active-filters');

  // Filters held inside the sheet (the free-text search has its own field
  // and is excluded from the badge count).
  function sheetFilterCount() {
    return (activeWG !== 'all' ? 1 : 0) + (activeCountry !== 'all' ? 1 : 0)
      + activeMentorship.size + activeKeywords.size + activeRegions.size;
  }
  // The filter sheet is a native <dialog>. On mobile the Filters button opens
  // it with showModal(), which promotes the dialog to the browser top layer:
  // positioned against the viewport and immune to ancestor containing blocks
  // (the toolbar's backdrop-filter), to page scroll, and to the iOS soft-keyboard
  // viewport offset that previously stranded a position:fixed sheet mid-page.
  // The dialog also provides the focus trap, Escape-to-close and the ::backdrop
  // dim natively, so the old inert / move-to-body / scroll-lock machinery is
  // gone. On desktop the wrapper is display:contents and never opened modally,
  // so the controls render inline in the toolbar.
  function openFilterSheet() {
    if (!filterSet || typeof filterSet.showModal !== 'function' || filterSet.open) return;
    filterSet.showModal();
    if (filterToggleBtn) filterToggleBtn.setAttribute('aria-expanded', 'true');
  }
  function syncToggleClosed() {
    if (filterToggleBtn) { filterToggleBtn.setAttribute('aria-expanded', 'false'); filterToggleBtn.focus({ preventScroll: true }); }
  }
  function closeFilterSheet() {
    if (filterSet && filterSet.open) filterSet.close();
    syncToggleClosed();
  }
  // Escape dismisses the dialog natively, bypassing closeFilterSheet, so mirror
  // the toggle reset + focus restore on the dialog's own close event. The
  // explicit X / Apply / backdrop paths run syncToggleClosed through
  // closeFilterSheet directly, so they do not depend on the close event firing.
  if (filterSet) filterSet.addEventListener('close', syncToggleClosed);
  // A tap in the dimmed area above the sheet (the dialog's own box; the click
  // lands on the dialog element with coordinates above its rect) closes it. The
  // y-check avoids closing on the thin margins between the stacked controls.
  if (filterSet) filterSet.addEventListener('click', (e) => {
    if (e.target !== filterSet) return;
    if (e.clientY < filterSet.getBoundingClientRect().top) closeFilterSheet();
  });
  if (filterToggleBtn) filterToggleBtn.addEventListener('click', openFilterSheet);
  if (sheetCloseBtn) sheetCloseBtn.addEventListener('click', closeFilterSheet);
  if (sheetApplyBtn) sheetApplyBtn.addEventListener('click', closeFilterSheet);
  if (sheetResetBtn) sheetResetBtn.addEventListener('click', clearAllFilters);
  // Back to desktop while the sheet is open: close it so the filterset returns
  // to its inline layout in the toolbar.
  window.matchMedia('(min-width: 641px)').addEventListener('change', (e) => { if (e.matches) closeFilterSheet(); });
  // bfcache: never freeze the page with the modal open, or a back-forward
  // restore would show a scroll-locked page under a stranded open sheet.
  window.addEventListener('pagehide', () => {
    if (filterSet && filterSet.open) {
      filterSet.close();
      if (filterToggleBtn) filterToggleBtn.setAttribute('aria-expanded', 'false');
    }
  });

  // Map a theme slug back to its display name via the aggregate.
  function themeNameForSlug(slug) {
    const e = KEYWORD_AGGREGATE.find(x => keywordSlug(x.keyword) === slug);
    return e ? e.keyword : slug;
  }
  // Same for a region slug (activeRegions holds slugs, not display names).
  function regionNameForSlug(slug) {
    const e = REGION_AGGREGATE.find(x => keywordSlug(x.region) === slug);
    return e ? e.region : slug;
  }
  // The list of currently-active filters, each with a remover, for the
  // removable chip row shown under the toolbar on mobile.
  function activeFilterPills() {
    const out = [];
    if (search.value.trim() !== '') {
      out.push({ label: '“' + search.value.trim() + '”', remove: () => { search.value = ''; render(); } });
    }
    if (activeWG !== 'all') {
      const chip = Array.from(filterChips).find(c => c.dataset.wg === activeWG);
      out.push({ label: chip ? chip.textContent.trim() : ('WG' + activeWG), remove: () => {
        activeWG = 'all'; filterChips.forEach(o => o.setAttribute('aria-pressed', o.dataset.wg === 'all')); render();
      }});
    }
    if (activeCountry !== 'all') {
      out.push({ label: activeCountry, remove: () => { activeCountry = 'all'; if (countrySelect) countrySelect.value = 'all'; render(); } });
    }
    activeKeywords.forEach(slug => {
      out.push({ label: window.netsecT(themeNameForSlug(slug)), remove: () => toggleKeywordFilter(slug) });
    });
    activeRegions.forEach(region => {
      out.push({ label: window.netsecT(regionNameForSlug(region)), remove: () => toggleRegionFilter(region) });
    });
    mentorshipChips.forEach(c => {
      const v = c.dataset.mentorship;
      if (!activeMentorship.has(v)) return;
      out.push({ label: c.textContent.trim(), remove: () => {
        activeMentorship.delete(v); c.setAttribute('aria-pressed', 'false'); render();
      }});
    });
    // STSM hosting is its own chip + boolean (not in mentorshipChips), so it
    // needs its own removable pill to stay consistent with every other facet.
    if (activeStsm && stsmChip) {
      out.push({ label: stsmChip.textContent.trim(), remove: () => {
        activeStsm = false; syncStsmChip(); render();
      }});
    }
    return out;
  }
  const XMARK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
  // Index of the active-filter chip whose remover was just tapped, so focus
  // can be re-homed after the row rebuilds instead of dropping to <body>.
  let _refocusActiveFilterIdx = -1;
  function renderActiveFilters() {
    if (!activeFiltersEl) return;
    const pills = activeFilterPills();
    activeFiltersEl.textContent = '';
    activeFiltersEl.hidden = pills.length === 0;
    pills.forEach((p, i) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'members-active-filter';
      const span = document.createElement('span');
      span.textContent = p.label;
      b.appendChild(span);
      b.insertAdjacentHTML('beforeend', XMARK);
      b.setAttribute('aria-label', window.netsecT('Remove filter') + ': ' + p.label);
      b.addEventListener('click', () => { _refocusActiveFilterIdx = i; p.remove(); });
      activeFiltersEl.appendChild(b);
    });
    // Keyboard / VoiceOver: after a removal the tapped button is gone, so move
    // focus to the chip that took its place (or the last one), and to the
    // Filters button when the row is now empty, rather than losing focus.
    if (_refocusActiveFilterIdx >= 0) {
      const btns = activeFiltersEl.querySelectorAll('.members-active-filter');
      const tgt = btns.length ? btns[Math.min(_refocusActiveFilterIdx, btns.length - 1)] : filterToggleBtn;
      if (tgt) tgt.focus({ preventScroll: true });
      _refocusActiveFilterIdx = -1;
    }
  }

  // Populate the country dropdown from the loaded MEMBERS. Builds an
  // alphabetised, deduplicated list of every country that has at least
  // one member; "All countries" is preserved as the first option.
  function populateCountryFilter() {
    if (!countrySelect) return;
    const countries = Array.from(new Set(
      MEMBERS.map(m => m.country).filter(Boolean)
    )).sort((a, b) => a.localeCompare(b));
    // Wipe everything except the first option.
    while (countrySelect.options.length > 1) countrySelect.remove(1);
    countries.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c; opt.textContent = c;
      countrySelect.appendChild(opt);
    });
  }

  // Reveal the mentorship filter only when the data carries at least
  // one mentorship facet, and hide each side's chip individually when
  // no member is on that side. Mirrors the keyword filter's data-
  // driven reveal: the dimension stays invisible until the Form
  // question is live and members opt in.
  function setupMentorshipFilter() {
    const root = document.getElementById('members-mentorship-filter');
    if (!root) return;
    const hasMentor = MEMBERS.some(m => (m.mentorship || []).includes('mentor'));
    const hasMentee = MEMBERS.some(m => (m.mentorship || []).includes('mentee'));
    if (!hasMentor && !hasMentee) {
      root.hidden = true;
      return;
    }
    root.hidden = false;
    mentorshipChips.forEach(chip => {
      if (chip.dataset.mentorship === 'mentor') chip.hidden = !hasMentor;
      if (chip.dataset.mentorship === 'mentee') chip.hidden = !hasMentee;
    });
  }

  // STSM-hosting filter (#760): reveal the chip only once at least one
  // member can host, so the row stays invisible while the Form question
  // is still gathering answers. Same data-driven posture as mentorship.
  function setupStsmFilter() {
    const root = document.getElementById('members-stsm-filter');
    if (!root) return;
    const hasHost = MEMBERS.some(m => m.stsm_hosting === 'yes' || m.stsm_hosting === 'ask');
    root.hidden = !hasHost;
    // If a deep link set the filter but no member hosts yet, neutralise it
    // so the visitor sees the full directory rather than an empty grid with
    // no visible chip to clear.
    if (!hasHost) activeStsm = false;
  }
  function syncStsmChip() {
    if (stsmChip) stsmChip.setAttribute('aria-pressed', activeStsm ? 'true' : 'false');
  }

  // Mentorship matching view (#763). The facet shipped as data plumbing;
  // this connects the two sides. When a mentorship chip is active, a panel
  // above the grid splits the matching members into "Offering" and
  // "Seeking", carries the how-to-approach guidance, and (when only one
  // side is active) offers a one-click jump to the opposite side. The grid
  // below still shows the filtered members.
  function syncMentorshipChips() {
    mentorshipChips.forEach(c => {
      c.setAttribute('aria-pressed', activeMentorship.has(c.dataset.mentorship) ? 'true' : 'false');
    });
  }
  // How many of a member's themes are in the currently-selected set. Drives
  // the panel's best-match-first ordering so the closest fits sit at the top
  // of a long column. Zero when no theme filter is active (every member ties).
  function mentorshipThemeOverlap(m) {
    if (activeKeywords.size === 0) return 0;
    return (m.themes || []).map(keywordSlug).filter(s => activeKeywords.has(s)).length;
  }
  function mentorshipRegionOverlap(m) {
    if (activeRegions.size === 0) return 0;
    return (m.regions || []).map(keywordSlug).filter(s => activeRegions.has(s)).length;
  }
  // Behind-the-scenes seniority signal (0 doctoral … 3 senior), inferred from
  // the academic position (and the name honorific as a fallback). It is never
  // shown: a reader judges seniority from the visible job title themselves. It
  // only nudges the order of mentors so that, among equally on-topic people, a
  // more established mentor surfaces first without burying near-peer mentors.
  function careerStage(m) {
    const name = m.name || '';
    const p = (m.position || '').toLowerCase();
    // Post-doc first, so "post-doctoral" is never misread as doctoral.
    if (/postdoc|post-?doctoral/.test(p)) return 1;
    if ((/\bprofessor\b/.test(p) && !/\b(assistant|associate)\b/.test(p))
        || /\b(director|head|dean|principal investigator)\b/.test(p)
        || (/\bprof\.?\b/i.test(name) && !/\b(assistant|associate)\b/.test(p))) return 3;
    if (/\bassociate professor\b|\breader\b|\bsenior (lecturer|researcher|research fellow|fellow|analyst)\b|\bteam lead\b|\bprincipal\b/.test(p)) return 2;
    if (/\bphd\b|\bdphil\b|doctoral (candidate|student|researcher|fellow)|\bdoctoral\b|doctorand|pre-?doctoral|\bcandidate\b|\bdoctoral student\b/.test(p)) return 0;
    if (/\bassistant professor\b|\blecturer\b|research fellow|research associate|\bresearcher\b|\banalyst\b/.test(p)) return 1;
    if (/\bdr\.?\b/i.test(name)) return 1;  // a doctorate implies at least early-career
    return 1;                               // unknown: neutral, so it never dominates
  }
  // Relevance of a member to the active theme + region filters. Theme overlap
  // dominates (weight 3), region overlap is secondary (1), and seniority is a
  // gentle tiebreak for the Offering side only (≤1.5, so it never outweighs a
  // single shared theme). Applied only when an area filter is on.
  function mentorshipMatchScore(m, tag, areasActive) {
    let s = mentorshipThemeOverlap(m) * 3 + mentorshipRegionOverlap(m);
    // Default (no stage given): among equally on-topic mentors, lean slightly
    // toward more established ones. Skipped once the viewer names their own
    // stage, where the near-peer nudge below governs instead.
    if (areasActive && tag === 'mentor' && viewerStage == null) s += careerStage(m) * 0.5;
    // Near-peer first. Academic-mentoring research finds the most useful mentor
    // is usually one or two career stages ahead (a postdoc for a PhD student, an
    // associate prof for a postdoc): relatable, recently in your shoes, and more
    // approachable than the most senior person available. So we lean toward a
    // 1–2 step gap in the mentoring direction, give a same-stage peer a smaller
    // nudge, and stop rewarding distance beyond that (a doctoral student is not
    // steered to a full professor over a near-peer). Symmetric on the mentee
    // side. Gentle: capped at 1.0, below a single shared theme (weight 3).
    if (viewerStage != null && (tag === 'mentor' || tag === 'mentee')) {
      const gap = tag === 'mentor' ? careerStage(m) - viewerStage
                                   : viewerStage - careerStage(m);
      s += gap <= 0 ? (gap === 0 ? 0.5 : 0)
         : gap <= 2 ? 1.0
         : 0.6;
    }
    return s;
  }
  // Members of one mentorship side, drawn from a pre-scoped pool and ordered
  // best-match first, then leadership, then name (#869). The pool already
  // honours the active facets, so the panel agrees with the grid.
  function mentorshipMembers(tag, pool) {
    const areasActive = activeKeywords.size > 0 || activeRegions.size > 0;
    return (pool || MEMBERS).filter(m => (m.mentorship || []).includes(tag))
      .sort((a, b) =>
        mentorshipMatchScore(b, tag, areasActive) - mentorshipMatchScore(a, tag, areasActive)
        || leadershipOrder(a).localeCompare(leadershipOrder(b))
        || (a.name || '').localeCompare(b.name || ''));
  }
  // Localised display names of the active theme + region filters, for the
  // panel's scope caption. Read from the aggregates (which carry every theme /
  // region) rather than the chip DOM, so an active-but-collapsed chip still
  // shows. Themes lead, regions follow.
  function activeAreaNames() {
    const names = [];
    if (activeKeywords.size) {
      const map = {};
      KEYWORD_AGGREGATE.forEach(e => { map[keywordSlug(e.keyword)] = window.netsecT(e.keyword); });
      activeKeywords.forEach(s => { if (map[s]) names.push(map[s]); });
    }
    if (activeRegions.size) {
      const map = {};
      REGION_AGGREGATE.forEach(e => { map[keywordSlug(e.region)] = window.netsecT(e.region); });
      activeRegions.forEach(s => { if (map[s]) names.push(map[s]); });
    }
    return names;
  }
  function mentorshipPersonLink(m) {
    const a = document.createElement('a');
    a.href = '#' + m.id;
    a.className = 'mentorship-person';
    const av = document.createElement('span');
    av.className = 'mentorship-person-avatar';
    if (m.photo) {
      const img = document.createElement('img');
      img.src = m.photo;
      img.alt = '';
      img.loading = 'lazy';
      av.appendChild(img);
    } else {
      av.classList.add('is-fallback');
      av.textContent = initials(m.name);
    }
    a.appendChild(av);
    const nm = document.createElement('span');
    nm.className = 'mentorship-person-name';
    nm.textContent = m.name || '';
    a.appendChild(nm);
    // Keep the active mentorship filter: open the member preview panel (or, in
    // detailed view, scroll to the already-full card) rather than navigating to
    // #slug, which would clobber the hash and drop the filter.
    a.addEventListener('click', (e) => {
      e.preventDefault();
      const card = grid.querySelector('.member-card[data-slug="' + m.id + '"]');
      if (!card) return;
      if (grid.classList.contains('is-compact')) openPanel(card);
      else card.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
    return a;
  }
  function renderMentorshipPanel() {
    const panel = document.getElementById('members-mentorship-panel');
    if (!panel) return;
    if (activeMentorship.size === 0) { panel.hidden = true; panel.replaceChildren(); return; }
    panel.replaceChildren();
    panel.hidden = false;
    const h = document.createElement('h2');
    h.className = 'mentorship-panel-title';
    h.textContent = window.netsecT('Mentorship matching');
    panel.appendChild(h);
    const guide = document.createElement('p');
    guide.className = 'mentorship-panel-guide';
    guide.textContent = window.netsecT('Mentoring in the network is informal. Introduce yourself directly and say what you are looking for. If you are unsure where to start, your Working Group lead can help make an introduction.');
    panel.appendChild(guide);
    // Optional, transient personalisation: the visitor can name their own
    // career stage, which gently leans mentors a step above them and mentees a
    // step below (mentorshipMatchScore). Nothing is stored. It lives in the
    // panel header so it only appears alongside the results it reorders, and a
    // single shared research theme always outweighs it, so a near-peer is never
    // buried. Replaces the old standalone match-finder card.
    const stageWrap = document.createElement('div');
    stageWrap.className = 'mentorship-panel-stage';
    const stageLabel = document.createElement('label');
    stageLabel.className = 'mentorship-panel-stage-label';
    stageLabel.setAttribute('for', 'mentorship-panel-stage-select');
    stageLabel.textContent = window.netsecT('Order for my career stage') + ':';
    const stageSel = document.createElement('select');
    stageSel.className = 'mentorship-panel-stage-select';
    stageSel.id = 'mentorship-panel-stage-select';
    [['', 'Any'], ['0', 'Doctoral'], ['1', 'Early-career'], ['2', 'Mid-career'], ['3', 'Senior']]
      .forEach(([value, label]) => {
        const o = document.createElement('option');
        o.value = value; o.textContent = window.netsecT(label);
        stageSel.appendChild(o);
      });
    stageSel.value = viewerStage == null ? '' : String(viewerStage);
    stageSel.addEventListener('change', () => {
      viewerStage = stageSel.value === '' ? null : parseInt(stageSel.value, 10);
      renderMentorshipPanel();  // rebuilds the panel (and this select)…
      document.getElementById('mentorship-panel-stage-select')?.focus();  // …so restore focus
    });
    stageWrap.appendChild(stageLabel);
    stageWrap.appendChild(stageSel);
    panel.appendChild(stageWrap);
    const sides = [];
    if (activeMentorship.has('mentor')) sides.push({ tag: 'mentor', label: 'Offering mentorship', other: 'mentee' });
    if (activeMentorship.has('mentee')) sides.push({ tag: 'mentee', label: 'Seeking mentorship', other: 'mentor' });

    // The panel agrees with the grid: it draws from members who pass every
    // active facet except mentorship itself (#869). When a theme or region is
    // selected, a caption names the slice, and a relaxed pool (areas dropped)
    // backs the "show people outside your selected research areas" escape hatch.
    const areasActive = activeKeywords.size > 0 || activeRegions.size > 0;
    const scopedPool = MEMBERS.filter(m => memberPassesFilters(m, _lastQuery, { skipMentorship: true }));
    const relaxedPool = areasActive
      ? MEMBERS.filter(m => memberPassesFilters(m, _lastQuery, { skipMentorship: true, skipAreas: true }))
      : scopedPool;
    const pool = (areasActive && mentorshipShowOutsideScope) ? relaxedPool : scopedPool;

    if (areasActive) {
      const scope = document.createElement('p');
      scope.className = 'mentorship-panel-scope';
      scope.textContent = window.netsecT('In your selected research areas') + ': ' + activeAreaNames().join(', ');
      panel.appendChild(scope);
      // Two-sided picture: in these research areas, how many members offer
      // mentoring against how many are seeking it, so supply and demand are
      // both visible rather than only the side you filtered to.
      const offerN = scopedPool.filter(m => (m.mentorship || []).includes('mentor')).length;
      const seekN = scopedPool.filter(m => (m.mentorship || []).includes('mentee')).length;
      if (offerN || seekN) {
        const bal = document.createElement('p');
        bal.className = 'mentorship-panel-balance';
        bal.textContent = window.netsecT('{offer} offering mentoring, {seek} seeking a mentor')
          .replace('{offer}', offerN).replace('{seek}', seekN);
        panel.appendChild(bal);
      }
    } else {
      // Signpost the theme / region filters: someone browsing all mentors or
      // mentees may not realise the lists can be narrowed to their own area.
      const tip = document.createElement('p');
      tip.className = 'mentorship-panel-tip';
      tip.textContent = window.netsecT('Tip: add a research-theme or region filter above to narrow these lists to your own research area.');
      panel.appendChild(tip);
    }

    // Make the ranking legible: the lists are ordered, not alphabetical. Only
    // claim it when there is an actual signal (a research-area filter or a
    // chosen career stage); without either, the order is just leadership then
    // name, which is not a recommendation worth advertising.
    if (areasActive || viewerStage != null) {
      const ord = document.createElement('p');
      ord.className = 'mentorship-panel-order';
      ord.innerHTML = '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="12" y1="5" x2="12" y2="19"/><polyline points="6 13 12 19 18 13"/></svg>';
      ord.appendChild(document.createTextNode(' ' + window.netsecT('Most relevant first')));
      panel.appendChild(ord);
    }

    const cols = document.createElement('div');
    cols.className = 'mentorship-panel-cols';
    sides.forEach(side => {
      const col = document.createElement('section');
      col.className = 'mentorship-panel-col';
      const people = mentorshipMembers(side.tag, pool);
      const sh = document.createElement('h3');
      sh.className = 'mentorship-panel-col-title';
      sh.textContent = window.netsecT(side.label) + ' (' + people.length + ')';
      col.appendChild(sh);
      if (people.length) {
        const ul = document.createElement('ul');
        ul.className = 'mentorship-panel-people';
        people.forEach(m => {
          const li = document.createElement('li');
          li.appendChild(mentorshipPersonLink(m));
          // Why this person is here: the research themes and regions they
          // share with your active filter. It reads as the match strength too,
          // since the list is ordered best-first and more shared areas means a
          // closer fit. Shown whenever an area filter is on; capped with a "+N".
          if (areasActive) {
            const shared = (m.themes || []).filter(t => activeKeywords.has(keywordSlug(t)))
              .map(t => ({ txt: window.netsecT(t), region: false }))
              .concat((m.regions || []).filter(r => activeRegions.has(keywordSlug(r)))
                .map(r => ({ txt: window.netsecT(r), region: true })));
            if (shared.length) {
              const why = document.createElement('div');
              why.className = 'mentorship-person-themes';
              const lab = document.createElement('span');
              lab.className = 'mentorship-person-why-label';
              lab.textContent = window.netsecT('Shared research areas') + ':';
              why.appendChild(lab);
              shared.slice(0, 3).forEach(it => {
                const c = document.createElement('span');
                c.className = 'mentorship-person-theme is-match' + (it.region ? ' is-region' : '');
                c.textContent = it.txt;
                why.appendChild(c);
              });
              if (shared.length > 3) {
                const more = document.createElement('span');
                more.className = 'mentorship-person-theme is-more';
                more.textContent = '+' + (shared.length - 3);
                why.appendChild(more);
              }
              li.appendChild(why);
            }
          }
          ul.appendChild(li);
        });
        col.appendChild(ul);
      } else {
        const none = document.createElement('p');
        none.className = 'mentorship-panel-none';
        // Context-aware empty state (#869 Phase 2): name the gap as a scoped
        // one when a theme / region is active, so the relax control below
        // reads as the obvious next step rather than a dead end.
        none.textContent = areasActive
          ? window.netsecT('No one in your selected research areas yet.')
          : window.netsecT('No one here yet.');
        col.appendChild(none);
      }
      cols.appendChild(col);
    });
    panel.appendChild(cols);

    // Escape hatch: with a theme / region filter on, let the visitor widen the
    // panel to people outside their selected research areas, so a mentor who tagged
    // themselves narrowly is never hidden from a mentee browsing by area. The
    // toggle re-renders the panel only, leaving the grid and the filters as is.
    if (areasActive) {
      const sideTags = sides.map(s => s.tag);
      const inScope = scopedPool.filter(m => (m.mentorship || []).some(t => sideTags.includes(t))).length;
      const inNetwork = relaxedPool.filter(m => (m.mentorship || []).some(t => sideTags.includes(t))).length;
      const extra = inNetwork - inScope;
      if (mentorshipShowOutsideScope || extra > 0) {
        const relax = document.createElement('button');
        relax.type = 'button';
        relax.className = 'mentorship-panel-relax';
        relax.setAttribute('aria-pressed', mentorshipShowOutsideScope ? 'true' : 'false');
        relax.textContent = mentorshipShowOutsideScope
          ? window.netsecT('Show only your selected research areas')
          : window.netsecT('Show people outside your selected research areas') + ' (' + extra + ')';
        relax.addEventListener('click', () => {
          mentorshipShowOutsideScope = !mentorshipShowOutsideScope;
          renderMentorshipPanel();
        });
        panel.appendChild(relax);
      }
    }

    // When only one side is active, offer the opposite side in one click.
    if (sides.length === 1) {
      const other = sides[0].other;
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'mentorship-panel-cross';
      btn.textContent = other === 'mentor'
        ? window.netsecT('Also show members offering mentorship')
        : window.netsecT('Also show members seeking mentorship');
      btn.addEventListener('click', () => {
        activeMentorship.add(other);
        syncMentorshipChips();
        writeHashKeywords();
        render();
      });
      panel.appendChild(btn);
    }
  }

  // ─────────── Research-interest filter (Phase 3) ───────────

  // Hash schema: `#keywords=slug-one,slug-two`. The slug form is
  // produced by keywordSlug(). Other consumers of the URL hash on
  // /people.html (the deep-link-to-member-card path that uses
  // `#<member-id>`) coexist because slugs always contain a hyphen
  // and an `=` sign while member-id hashes are bare slugs without
  // a query-string-style key. We disambiguate by checking for the
  // `keywords=` prefix.
  function parseHashKeywords() {
    activeKeywords.clear();
    activeRegions.clear();
    activeMentorship.clear();
    activeStsm = false;
    const raw = (location.hash || '').replace(/^#/, '');
    if (!raw) return;
    // Try query-string-style first: `themes=a,b,c` or
    // `themes=a,b&mentorship=mentor`.
    const params = new URLSearchParams(raw.includes('&') || raw.includes('=') ? raw : '');
    const csv = params.get('themes');
    if (csv) {
      csv.split(',').map(s => s.trim()).filter(Boolean).forEach(s => activeKeywords.add(s));
    }
    // Research-region facet (#555): `regions=europe,asia`, symmetric to
    // themes, so a profile page's region chip can deep-link here pre-filtered.
    const rcsv = params.get('regions');
    if (rcsv) {
      rcsv.split(',').map(s => s.trim()).filter(Boolean).forEach(s => activeRegions.add(s));
    }
    // Mentorship facet (#763): `mentorship=mentor`, `mentorship=mentee`, or
    // both, so a "Find a mentor" deep link lands pre-filtered.
    const ment = params.get('mentorship');
    if (ment) {
      ment.split(',').map(s => s.trim()).filter(s => s === 'mentor' || s === 'mentee')
        .forEach(s => activeMentorship.add(s));
    }
    // STSM-hosting facet (#760): `stsm=1`, so the grants page can deep-link
    // to the hosts. Any truthy value other than "0"/"false" turns it on.
    const stsm = params.get('stsm');
    if (stsm && stsm !== '0' && stsm.toLowerCase() !== 'false') {
      activeStsm = true;
    }
  }
  function writeHashKeywords() {
    const slugs = Array.from(activeKeywords);
    const mentors = Array.from(activeMentorship);
    const rawHash = (location.hash || '').replace(/^#/, '');
    // Preserve any portion of the hash this function does not own (e.g. a
    // member-card deep-link slug stays intact). Both the theme and the
    // mentorship keys are owned here so they coexist in one hash.
    const hasKeywordsKey = /(^|&)(themes|regions|mentorship|stsm)=/.test(rawHash);
    let rest = '';
    if (rawHash && hasKeywordsKey) {
      const params = new URLSearchParams(rawHash);
      params.delete('themes');
      params.delete('regions');
      params.delete('mentorship');
      params.delete('stsm');
      rest = params.toString();
    } else if (rawHash && !hasKeywordsKey && !rawHash.includes('=')) {
      // A bare member-id-style hash; keep it as a separate fragment.
      rest = '';
    } else if (rawHash) {
      rest = rawHash;
    }
    const regions = Array.from(activeRegions);
    const parts = [];
    if (slugs.length) parts.push('themes=' + slugs.join(','));
    if (regions.length) parts.push('regions=' + regions.join(','));
    if (mentors.length) parts.push('mentorship=' + mentors.join(','));
    if (activeStsm) parts.push('stsm=1');
    if (rest) parts.push(rest);
    const next = parts.join('&');
    // Use replaceState rather than assigning location.hash so that
    // the page does not jump to a same-page anchor when the slug
    // happens to match an element id. When the result is empty, strip
    // the `#` entirely rather than leaving a bare `#` in the URL bar.
    if (next) {
      history.replaceState(null, '', '#' + next);
    } else {
      history.replaceState(null, '', location.pathname + location.search);
    }
  }

  // Build / re-build the chip row. Renders top-N by count when
  // collapsed, full list when expanded. Active state mirrors
  // `activeKeywords`. Hidden entirely when the aggregate is empty.
  function renderKeywordFilter() {
    const root = document.getElementById('members-keyword-filter');
    const chipsWrap = document.getElementById('members-keyword-filter-chips');
    const toggleBtn = document.getElementById('members-keyword-filter-toggle');
    const clearBtn = document.getElementById('members-keyword-filter-clear');
    if (!root || !chipsWrap) return;
    if (!KEYWORD_AGGREGATE.length) {
      root.hidden = true;
      return;
    }
    root.hidden = false;
    chipsWrap.replaceChildren();
    const total = KEYWORD_AGGREGATE.length;
    const limit = keywordFilterExpanded ? total : Math.min(KEYWORD_FILTER_VISIBLE_TOP_N, total);
    KEYWORD_AGGREGATE.slice(0, limit).forEach(entry => {
      const slug = keywordSlug(entry.keyword);
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'members-keyword-filter-chip';
      const isActive = activeKeywords.has(slug);
      btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
      btn.dataset.slug = slug;
      btn.dataset.canonical = entry.keyword;
      const label = document.createElement('span');
      label.className = 'lbl';
      label.textContent = window.netsecT(entry.keyword);
      btn.appendChild(label);
      const count = document.createElement('span');
      count.className = 'count';
      count.textContent = entry.count;
      btn.appendChild(count);
      btn.addEventListener('click', () => toggleKeywordFilter(slug));
      chipsWrap.appendChild(btn);
    });
    // Show / hide the "show all" toggle.
    if (total > KEYWORD_FILTER_VISIBLE_TOP_N) {
      toggleBtn.hidden = false;
      toggleBtn.setAttribute('aria-expanded', keywordFilterExpanded ? 'true' : 'false');
      toggleBtn.textContent = keywordFilterExpanded
        ? window.netsecT('Show fewer')
        : (window.netsecT('Show all') + ' (' + total + ')');
    } else {
      toggleBtn.hidden = true;
    }
    // Show / hide "Clear" depending on whether any filter is active.
    clearBtn.hidden = activeKeywords.size === 0;
  }

  function toggleKeywordFilter(slug) {
    if (activeKeywords.has(slug)) activeKeywords.delete(slug);
    else activeKeywords.add(slug);
    if (keywordDetails && activeKeywords.has(slug)) keywordDetails.open = true;
    writeHashKeywords();
    renderKeywordFilter();
    render();
  }
  function clearKeywordFilter() {
    if (activeKeywords.size === 0) return;
    activeKeywords.clear();
    writeHashKeywords();
    renderKeywordFilter();
    render();
  }

  // Static control handlers for the keyword filter row. The chips
  // themselves get their click handler at render time inside
  // renderKeywordFilter; these two controls live in the markup so
  // we wire them once on page load.
  const kwToggleBtn = document.getElementById('members-keyword-filter-toggle');
  if (kwToggleBtn) {
    kwToggleBtn.addEventListener('click', () => {
      keywordFilterExpanded = !keywordFilterExpanded;
      renderKeywordFilter();
    });
  }
  const kwClearBtn = document.getElementById('members-keyword-filter-clear');
  if (kwClearBtn) {
    // The clear button lives inside the <summary>; stop its click from
    // toggling the disclosure open/closed.
    kwClearBtn.addEventListener('click', (e) => { e.stopPropagation(); clearKeywordFilter(); });
  }

  // ── Research-region filter (#555) ─────────────────────────────────
  // A second, geographic facet. Mirrors the theme chip row (multi-select
  // OR, top-N with a "show all" toggle, slugged chips) but its data comes
  // from the optional Research-regions form field, and it stays hidden
  // until at least one member has opted in. No URL-hash persistence.
  function renderRegionFilter() {
    const root = document.getElementById('members-region-filter');
    const chipsWrap = document.getElementById('members-region-filter-chips');
    const toggleBtn = document.getElementById('members-region-filter-toggle');
    const clearBtn = document.getElementById('members-region-filter-clear');
    if (!root || !chipsWrap) return;
    if (!REGION_AGGREGATE.length) { root.hidden = true; return; }
    root.hidden = false;
    chipsWrap.replaceChildren();
    const total = REGION_AGGREGATE.length;
    const limit = regionFilterExpanded ? total : Math.min(KEYWORD_FILTER_VISIBLE_TOP_N, total);
    REGION_AGGREGATE.slice(0, limit).forEach(entry => {
      const slug = keywordSlug(entry.region);
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'members-keyword-filter-chip members-region-filter-chip';
      btn.setAttribute('aria-pressed', activeRegions.has(slug) ? 'true' : 'false');
      btn.dataset.slug = slug;
      const label = document.createElement('span');
      label.className = 'lbl';
      label.textContent = window.netsecT(entry.region);
      btn.appendChild(label);
      const count = document.createElement('span');
      count.className = 'count';
      count.textContent = entry.count;
      btn.appendChild(count);
      btn.addEventListener('click', () => toggleRegionFilter(slug));
      chipsWrap.appendChild(btn);
    });
    if (total > KEYWORD_FILTER_VISIBLE_TOP_N) {
      toggleBtn.hidden = false;
      toggleBtn.setAttribute('aria-expanded', regionFilterExpanded ? 'true' : 'false');
      toggleBtn.textContent = regionFilterExpanded
        ? window.netsecT('Show fewer')
        : (window.netsecT('Show all') + ' (' + total + ')');
    } else {
      toggleBtn.hidden = true;
    }
    clearBtn.hidden = activeRegions.size === 0;
  }
  function toggleRegionFilter(slug) {
    if (activeRegions.has(slug)) activeRegions.delete(slug);
    else activeRegions.add(slug);
    if (regionDetails && activeRegions.has(slug)) regionDetails.open = true;
    writeHashKeywords();
    renderRegionFilter();
    render();
  }
  function clearRegionFilter() {
    if (activeRegions.size === 0) return;
    activeRegions.clear();
    writeHashKeywords();
    renderRegionFilter();
    render();
  }
  const rgToggleBtn = document.getElementById('members-region-filter-toggle');
  if (rgToggleBtn) {
    rgToggleBtn.addEventListener('click', () => {
      regionFilterExpanded = !regionFilterExpanded;
      renderRegionFilter();
    });
  }
  const rgClearBtn = document.getElementById('members-region-filter-clear');
  if (rgClearBtn) {
    rgClearBtn.addEventListener('click', (e) => { e.stopPropagation(); clearRegionFilter(); });
  }
  // Keep the keyword filter in sync with the URL hash on back/forward
  // navigation. The existing hashchange listener for #<slug> deep-links
  // is registered later (inside the bios.json load block); this one
  // listens specifically for the keywords= portion and re-renders.
  window.addEventListener('hashchange', () => {
    const snap = () => Array.from(activeKeywords).sort().join(',') + '|'
      + Array.from(activeRegions).sort().join(',') + '|'
      + Array.from(activeMentorship).sort().join(',') + '|' + (activeStsm ? '1' : '');
    const before = snap();
    parseHashKeywords();
    const after = snap();
    if (before !== after) {
      renderKeywordFilter();
      renderRegionFilter();
      syncMentorshipChips();
      syncStsmChip();
      render();
    }
  });

  // Load data
  try {
    const res = await fetch('data/bios.json', { cache: 'no-cache' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    MEMBERS = data.members || [];
    // Aggregate is emitted by sync-bios.py: a count-sorted list of
    // every canonical keyword in use across the directory. Drives the
    // filter chip row. Missing on older snapshots → empty array,
    // which hides the filter cleanly.
    // The research-interest filter clusters members by broad *theme*
    // (data/keyword-aliases.json `themes`) so people in the same area
    // surface together; cards still show their specific keyword pills.
    // theme_aggregate is reshaped to the {keyword,count} shape the chip
    // row already expects (here `keyword` carries the theme name).
    KEYWORD_AGGREGATE = (Array.isArray(data.theme_aggregate) ? data.theme_aggregate : [])
      .map(function (e) { return { keyword: e.theme, count: e.count }; });
    KEYWORD_THEME_MAP = (data && typeof data.keyword_theme_map === 'object' && data.keyword_theme_map) || {};
    REGION_AGGREGATE = Array.isArray(data.region_aggregate) ? data.region_aggregate : [];
    // Seed activeKeywords from the URL hash so a deep-link like
    //   /people.html#keywords=ai-governance,foreign-policy-analysis
    // lands with those filters already applied.
    parseHashKeywords();
    if (keywordDetails && activeKeywords.size > 0) keywordDetails.open = true;
    if (regionDetails && activeRegions.size > 0) regionDetails.open = true;
    populateCountryFilter();
    setupMentorshipFilter();
    syncMentorshipChips();
    setupStsmFilter();
    syncStsmChip();
    renderKeywordFilter();
    renderRegionFilter();
    // Member spotlight: read the weekly rotation so render() can pin the
    // featured member. Optional; the directory renders fine without it.
    try {
      const _sres = await fetch('data/spotlight.json', { cache: 'no-cache' });
      if (_sres.ok) {
        const _sp = await _sres.json();
        if (_sp && _sp.active && _sp.current && MEMBERS.some(m => m.id === _sp.current)) featuredId = _sp.current;
      }
    } catch (e) { /* spotlight optional */ }
    render();
    // Surface how current the directory is, driven by bios.json's
    // `generated_at` stamp (#271). The stamp only moves when the sync
    // produces a substantive change, so this date stays honest across
    // quiet weeks. Hidden until a valid stamp is parsed.
    const freshnessEl = document.querySelector('[data-directory-freshness]');
    if (freshnessEl && data.generated_at) {
      const stamp = new Date(data.generated_at);
      if (!isNaN(stamp.getTime())) {
        const lang = (document.documentElement.lang || 'en').toLowerCase().slice(0, 2);
        const dateLocale = { en: 'en-GB', fr: 'fr-FR', de: 'de-DE' }[lang] || 'en-GB';
        const pretty = stamp.toLocaleDateString(dateLocale, {
          year: 'numeric', month: 'long', day: 'numeric',
        });
        freshnessEl.textContent =
          window.netsecT('Directory last updated {0}.').replace('{0}', pretty);
        freshnessEl.hidden = false;
      }
    }
    // Wire the "Add your bio" CTA to the live Google Form URL if
    // bios.json records one. Until configured, hide the button and
    // leave only the fineprint fallback.
    const joinLink = document.querySelector('[data-form-link]');
    const formUrl = data.source && data.source.form_url;
    if (joinLink) {
      if (formUrl) {
        joinLink.href = formUrl;
        joinLink.target = '_blank';
        joinLink.rel = 'noopener';
      } else {
        joinLink.hidden = true;
      }
    }
    // Deep-link: scroll to #<id> if present. Robust to:
    //  - a hash that includes the salutation (e.g. #dr-arthur-laudrain →
    //    slug is arthur-laudrain because slugify strips the title)
    //  - the URL changing later (hashchange)
    //
    // We used to wrap the whole body in requestAnimationFrame so that
    // scrollIntoView ran on a settled layout. Problem: if RAF didn't
    // fire (headless Chromium in some timing scenarios; possibly real
    // browsers under heavy load), NONE of the spotlight / expand /
    // scroll actions ran, leaving the visitor staring at the top of
    // the directory with no landed card. Phase 1 Journey 4 of the
    // launch-QA pass (finding J4-1) repro'd this consistently in
    // headless. Fix: do the class manipulations synchronously — they
    // are layout-safe (no rect-measurement) — and only gate
    // `scrollIntoView` behind RAF so the scroll target's box is
    // computed from a settled layout *after* `.is-expanded` has had
    // a frame to recompute card height.
    const scrollToHash = () => {
      const hash = (location.hash || '').replace(/^#/, '');
      if (!hash) return;
      // Try first the legacy ID-on-element pattern (older
      // deep-links to e.g. #arthur-laudrain rendered on detailed
      // cards via an inline id attribute). Then try a member card
      // by slug — for the new expand-in-place flow this also flips
      // the matching card into its expanded form in compact view.
      const target =
        document.getElementById(hash) ||
        document.getElementById(hash.replace(/^(dr|prof|mr|ms|mrs)-/i, '')) ||
        grid.querySelector('.member-card[data-slug="' + CSS.escape(hash) + '"]');
      if (!target) return;
      if (target.classList.contains('member-card')) {
        // Visual spotlight so the landed card is unmissable, even in
        // detailed view where every other card is also showing its
        // full content. The class is persistent — it sticks until the
        // visitor dismisses it explicitly (clicks elsewhere in the
        // grid, types in the search box, or changes a filter). That
        // matches the "I clicked through to see this specific person"
        // mental model better than the old 3.5 s auto-fade did: in
        // detailed view a quick fade often passed unseen if the page
        // was still settling, leaving the visitor unsure they'd
        // actually landed on the right card.
        grid.querySelectorAll('.member-card.is-search-landed')
            .forEach(c => c.classList.remove('is-search-landed'));
        target.classList.add('is-search-landed');
        // In compact view, open the member preview panel for the landed
        // card. In detailed view, every card already shows its full
        // content, so the spotlight is the only treatment needed.
        if (grid.classList.contains('is-compact')) {
          openPanel(target);
        }
      }
      // Scroll on the next paint — after `.is-expanded` recomputes
      // the box. setTimeout(0) is a belt-and-braces fallback in case
      // RAF doesn't fire (the original bug); it queues a fresh task
      // that will run in either case.
      const doScroll = () => target.scrollIntoView({ behavior: 'instant', block: 'center' });
      requestAnimationFrame(doScroll);
      setTimeout(doScroll, 50);
    };
    scrollToHash();
    window.addEventListener('hashchange', scrollToHash);
    // Back-button re-entry path: if the visitor goes
    //   /essc-2026.html → /people.html#A → back → /people.html#B
    // the second arrival on /people.html is often served from
    // bfcache. bfcache restores the page exactly as it was when
    // the visitor left — including the previous spotlight on #A
    // — without firing `hashchange` (full navigations don't),
    // leaving the URL bar showing #B while card A stays
    // highlighted. `pageshow` with `event.persisted === true`
    // is the canonical signal that a bfcache restore happened;
    // re-running scrollToHash re-aligns the spotlight with the
    // current hash. The `e.persisted` guard keeps this from
    // double-firing alongside the initial `scrollToHash()` call
    // on a cold load.
    window.addEventListener('pageshow', (e) => {
      if (e.persisted) scrollToHash();
    });

    // Dismiss the spotlight as soon as the visitor signals they've
    // engaged with the page beyond just receiving the landing. We
    // explicitly do NOT listen for scroll events — the deep-link's
    // own scrollIntoView fires those, and dismissing on them would
    // clear the spotlight before the visitor has had a chance to
    // notice it.
    const dismissLanded = () => {
      const landed = grid.querySelector('.member-card.is-search-landed');
      if (landed) {
        landed.classList.remove('is-search-landed');
        // Strip a bare slug hash too, keeping the URL honest about
        // state, but leave a key=value hash (#themes= filter) alone
        // (issue #647).
        const raw = (location.hash || '').replace(/^#/, '');
        if (raw && !raw.includes('=')) history.replaceState(null, '', location.pathname + location.search);
      }
    };
    grid.addEventListener('pointerdown', (e) => {
      // Only dismiss when clicking on a DIFFERENT card or empty grid
      // space. Clicking the landed card itself (e.g. to follow a
      // contact icon) is not a dismissal.
      const onLanded = e.target.closest('.member-card.is-search-landed');
      if (!onLanded) dismissLanded();
    });
    if (search) {
      search.addEventListener('focus', dismissLanded);
      search.addEventListener('input', dismissLanded);
    }
    filterChips.forEach(b => b.addEventListener('click', dismissLanded));
    if (countrySelect) countrySelect.addEventListener('change', dismissLanded);
  } catch (err) {
    // Locale-aware contact link so a French / German visitor lands
    // on the FR / DE index page if it exists (else falls back to EN).
    const lang = (document.documentElement.lang || 'en').toLowerCase().slice(0, 2);
    const indexUrl = lang === 'en' ? 'index.html' : 'index.' + lang + '.html';
    const link = '<a href="' + indexUrl + '#contact">' + window.netsecT('contact page') + '</a>';
    const tail = window.netsecT('Please refresh, or use the {0}.').replace('{0}', link);
    grid.innerHTML = '<p style="text-align:center;color:var(--muted);padding:32px">'
      + window.netsecT('Unable to load network directory.') + ' ' + tail + '</p>';
    console.error('bios.json load failed:', err);
  }
})();
