/* NetSec — shared site script
   ────────────────────────────────────────────────────────────────
   Loaded by every page. Each block is guarded so it no-ops when the
   relevant DOM element isn't present, so additional pages can opt in
   to whichever features they need. */
(function () {
  'use strict';

  /* String catalog + window.netsecT() helper — defined first so that
     every later block (theme toggle, mobile menu, member directory)
     can call it without ordering pitfalls. The catalog lives here as
     a single source of truth; page-specific scripts read from it via
     the global helper exposed at the bottom of this block. */
  const I18N = {
    en: {},
    fr: {
      'Action Chair': "Président·e de l'Action",
      'Action Vice-Chair': "Vice-président·e de l'Action",
      'Grant Holder Scientific Representative': 'Représentant·e scientifique du porteur de subvention',
      'Science Communication Coordinator': 'Coordinateur·rice communication scientifique',
      'Grant Awarding Coordinator': "Coordinateur·rice d'attribution des subventions",
      'Grant Awarding Coordinator Co-lead': "Coordinateur·rice adjoint·e d'attribution",
      'WG1 Leader': 'Responsable WG1',
      'WG2 Leader': 'Responsable WG2',
      'WG3 Leader': 'Responsable WG3',
      'WG4 Leader': 'Responsable WG4',
      'WG1 Co-Leader': 'Co-responsable WG1',
      'WG2 Co-Leader': 'Co-responsable WG2',
      'WG3 Co-Leader': 'Co-responsable WG3',
      'WG4 Co-Leader': 'Co-responsable WG4',
      'MC member': 'Membre du CG',
      'Network member': 'Membre du réseau',
      'Working Group participant': 'Participant·e au groupe de travail',
      'Bio coming soon.': 'Biographie à venir.',
      'Show more': 'Voir plus',
      'Show less': 'Voir moins',
      'member': 'membre',
      'members': 'membres',
      'Switch to dark mode': 'Basculer le mode sombre',
      'Switch to light mode': 'Basculer le mode clair',
      'Unable to load network directory.': "Impossible de charger l'annuaire du réseau.",
      'Please refresh, or use the {0}.': 'Veuillez recharger ou utiliser le {0}.',
      'contact page': 'formulaire de contact',
    },
    de: {
      'Action Chair': 'Aktionsvorsitz',
      'Action Vice-Chair': 'Stellv. Aktionsvorsitz',
      'Grant Holder Scientific Representative': 'Wissenschaftliche Vertretung des Förderträgers',
      'Science Communication Coordinator': 'Koordination Wissenschaftskommunikation',
      'Grant Awarding Coordinator': 'Koordination Fördervergabe',
      'Grant Awarding Coordinator Co-lead': 'Stellv. Koordination Fördervergabe',
      'WG1 Leader': 'Leitung WG1',
      'WG2 Leader': 'Leitung WG2',
      'WG3 Leader': 'Leitung WG3',
      'WG4 Leader': 'Leitung WG4',
      'WG1 Co-Leader': 'Co-Leitung WG1',
      'WG2 Co-Leader': 'Co-Leitung WG2',
      'WG3 Co-Leader': 'Co-Leitung WG3',
      'WG4 Co-Leader': 'Co-Leitung WG4',
      'MC member': 'MC-Mitglied',
      'Network member': 'Netzwerkmitglied',
      'Working Group participant': 'Arbeitsgruppen-Mitglied',
      'Bio coming soon.': 'Biografie folgt.',
      'Show more': 'Mehr anzeigen',
      'Show less': 'Weniger anzeigen',
      'member': 'Mitglied',
      'members': 'Mitglieder',
      'Switch to dark mode': 'Dunkelmodus umschalten',
      'Switch to light mode': 'Hellmodus umschalten',
      'Unable to load network directory.': 'Netzwerkverzeichnis konnte nicht geladen werden.',
      'Please refresh, or use the {0}.': 'Bitte aktualisieren Sie die Seite oder nutzen Sie das {0}.',
      'contact page': 'Kontaktformular',
    },
  };
  /** Translate a known string for the current page's language.
   *  Falls back to the original if no translation is registered.
   *  Strings of the form "MC member · Switzerland" translate only
   *  the prefix before " · " so the country name stays intact. */
  window.netsecT = function (s) {
    if (typeof s !== 'string') return s;
    const lang = (document.documentElement.lang || 'en').toLowerCase().slice(0, 2);
    const dict = I18N[lang];
    if (!dict) return s;
    const sep = ' · ';
    if (s.includes(sep)) {
      const [head, ...rest] = s.split(sep);
      return (dict[head] || head) + sep + rest.join(sep);
    }
    return dict[s] || s;
  };

  /* Nav: stronger shadow once scrolled past the top. */
  const nav = document.querySelector('.nav');
  if (nav) {
    const onScroll = () => {
      nav.style.boxShadow = window.scrollY > 12
        ? '0 14px 40px rgba(20,35,80,.14)'
        : 'var(--glass-shadow)';
    };
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  /* Theme toggle — flips .dark on <html>, persists choice.
     Initial state is set by the inline <head> script to avoid FOUC. */
  const themeBtn = document.querySelector('.theme-toggle');
  if (themeBtn) {
    // aria-label and title are kept in step with the current theme.
    // The strings flow through window.netsecT() so the FR/DE pages
    // get translated labels for screen-reader users.
    const setLabel = () => {
      const dark = document.documentElement.classList.contains('dark');
      const key = dark ? 'Switch to light mode' : 'Switch to dark mode';
      const t = (window.netsecT && window.netsecT(key)) || key;
      themeBtn.setAttribute('aria-label', t);
      themeBtn.setAttribute('title', t);
    };
    setLabel();
    themeBtn.addEventListener('click', () => {
      const nowDark = document.documentElement.classList.toggle('dark');
      try { localStorage.setItem('netsec-theme', nowDark ? 'dark' : 'light'); } catch (e) {}
      setLabel();
    });
  }

  /* MC-by-country collapsible: persist open/closed state, auto-open
     on deep-link to a country card inside. */
  const mcDetails = document.getElementById('mc-countries');
  if (mcDetails) {
    try {
      if (localStorage.getItem('netsec-mc-countries-open') === '1') mcDetails.open = true;
    } catch (e) {}
    try {
      if (location.hash && location.hash.length > 1) {
        const target = document.querySelector(location.hash);
        if (target && mcDetails.contains(target)) mcDetails.open = true;
      }
    } catch (e) {}
    mcDetails.addEventListener('toggle', () => {
      try { localStorage.setItem('netsec-mc-countries-open', mcDetails.open ? '1' : '0'); } catch (e) {}
    });
  }

  /* Language switcher (Phase 2)
     ────────────────────────────────────────────────────────────────
     Three responsibilities:
       1) Rewrite the switcher chip hrefs to point at the same page in
          each language. Each chip carries hreflang; the JS swaps the
          suffix to land on the matching locale variant. This means
          every page can ship an identical chip block and the JS
          figures out the destinations.
       2) Mark the chip whose hreflang matches <html lang> with
          aria-current="true" so screen readers and the active-style
          rule (white pill background) light up the right one.
       3) On click, save the preference to localStorage. On every
          subsequent page load, if the user is on the English version
          but the preference is FR or DE, redirect them — *only* when
          an <link rel="alternate" hreflang="…"> is declared for the
          current page (no 404 redirects). */
  (function langSwitcher() {
    const currentLang = (document.documentElement.lang || 'en').toLowerCase().slice(0, 2);

    // --- (1) and (2): rewire chip hrefs + aria-current
    const chips = document.querySelectorAll('.lang-switch a');
    if (chips.length) {
      // Compute the canonical English filename of the page we're on.
      // Strip the trailing /, normalise index, drop the .fr/.de locale
      // suffix if present.
      let here = location.pathname.replace(/\/$/, '/index.html').split('/').pop();
      if (!here) here = 'index.html';
      const stem = here.replace(/\.(fr|de)\.html$/i, '.html');
      const variants = {
        en: stem,
        fr: stem.replace(/\.html$/, '.fr.html'),
        de: stem.replace(/\.html$/, '.de.html'),
      };
      chips.forEach(a => {
        const lang = (a.getAttribute('hreflang') || '').toLowerCase();
        if (lang && variants[lang]) {
          // Preserve any hash on the current page so deep-links survive.
          a.href = variants[lang] + (location.hash || '');
        }
        a.setAttribute('aria-current', lang === currentLang ? 'true' : 'false');
        // Persist the preference on click.
        a.addEventListener('click', () => {
          try { localStorage.setItem('netsec-lang', lang); } catch (e) {}
        });
      });
    }

    // --- (3): redirect to saved preference when safe
    try {
      const saved = localStorage.getItem('netsec-lang');
      if (!saved || saved === currentLang) return;
      const alt = document.querySelector('link[rel="alternate"][hreflang="' + saved + '"]');
      if (!alt || !alt.href) return;
      // Avoid loops: only redirect if we're actually on a different URL.
      const here = location.origin + location.pathname;
      const there = alt.href.split('#')[0];
      if (here === there) return;
      // Only auto-redirect from the authoritative English to a saved
      // FR/DE — never the other direction. This keeps the English
      // version reachable as a fallback when a translation is broken.
      if (currentLang !== 'en') return;
      location.replace(alt.href + (location.hash || ''));
    } catch (e) { /* localStorage / DOM API may be unavailable */ }
  })();

  /* Mobile menu */
  const menuBtn = document.querySelector('.menu-toggle');
  const navLinks = document.querySelector('.nav-links');
  if (menuBtn && navLinks) {
    menuBtn.addEventListener('click', () => {
      const open = navLinks.classList.toggle('open');
      menuBtn.setAttribute('aria-expanded', open);
    });
    navLinks.addEventListener('click', e => {
      if (e.target.tagName === 'A') navLinks.classList.remove('open');
    });
  }

  /* Reveal-on-scroll. threshold:0 + bottom rootMargin so very tall
     sections (eg. Management Committee) still trigger reliably on
     phones — see commit history for the diagnosis. */
  try {
    const targets = document.querySelectorAll('.reveal');
    if (targets.length) {
      document.documentElement.classList.add('js-reveal');
      const io = new IntersectionObserver(entries => {
        entries.forEach(e => {
          if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
        });
      }, { threshold: 0, rootMargin: '0px 0px -10% 0px' });
      targets.forEach(el => io.observe(el));
      // Safety: never leave anything stuck at opacity:0
      setTimeout(() => targets.forEach(el => el.classList.add('in')), 3000);
    }
  } catch (err) {
    document.documentElement.classList.remove('js-reveal');
    document.querySelectorAll('.reveal').forEach(el => el.classList.add('in'));
  }

  /* Year stamp in the footer */
  const yearEl = document.getElementById('year');
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  /* ─────────────────────────────────────────────────────────────
     Live-refresh leadership cards from data/bios.json.
     ─────────────────────────────────────────────────────────────
     The home page leadership cards (Action Leadership, WG Leadership,
     WG Co-Leaders) are hand-authored HTML — they need to render even
     before any JS runs, since they sit above the fold and appear in
     view-source. But once a leader submits a refreshed photo or
     affiliation via the public Google Form, the new data lives in
     data/bios.json while the hand-authored HTML still points at the
     old photo file. This block reconciles the two on page load.

     Contract:
       - Card opts in by carrying data-slug="…" matching its bios.json id.
       - Photo + heading are always refreshed when the slug resolves.
       - The .org line is only refreshed when the card carries
         data-org-from-bio="affiliation" (currently the five Co-Leader
         cards). Other cards keep their hand-authored .org text because
         it is not an affiliation — it is "WG1 Leader", "Outreach &
         dissemination", "Co-lead: <Name>", etc.
       - On any error (no JS, fetch fails, slug absent), the static
         HTML stays exactly as written. Nothing is hidden, nothing is
         blanked. */
  const leaderCards = document.querySelectorAll('.mc-card[data-slug]');
  if (leaderCards.length) {
    (async () => {
      try {
        const res = await fetch('data/bios.json', { cache: 'no-cache' });
        if (!res.ok) return;
        const data = await res.json();
        const bySlug = Object.create(null);
        (data.members || []).forEach(m => { if (m.id) bySlug[m.id] = m; });

        leaderCards.forEach(card => {
          const slug = card.getAttribute('data-slug');
          const m = bySlug[slug];
          if (!m) return;

          // Photo
          if (m.photo) {
            const img = card.querySelector('.mc-avatar img');
            if (img && img.getAttribute('src') !== m.photo) {
              img.setAttribute('src', m.photo);
              if (m.name) img.setAttribute('alt', m.name);
            }
          }
          // Display name (honorifics sometimes change between
          // initial seed and a refreshed form submission)
          if (m.name) {
            const h = card.querySelector('h4');
            if (h && h.textContent.trim() !== m.name) h.textContent = m.name;
          }
          // Affiliation line, opt-in
          if (card.getAttribute('data-org-from-bio') === 'affiliation') {
            const org = card.querySelector('.org');
            if (org && m.affiliation && org.textContent.trim() !== m.affiliation) {
              org.textContent = m.affiliation;
            }
          }
        });
      } catch (err) {
        // Silent: the static HTML is already a correct fallback.
      }
    })();
  }

  /* ─────────────────────────────────────────────────────────────
     Guided tour engine — netsecTour({steps, labels, onComplete})
     ─────────────────────────────────────────────────────────────
     Coachmark-style walkthrough exposed as window.netsecTour so
     page-specific scripts can configure their own tours. Currently
     used by /people/ for the directory orientation; designed to be
     reusable on other pages later.

     Each `step` is { target, title, body, scroll? }:
       - target : CSS selector for the element to spotlight.
       - title  : short heading shown above the body.
       - body   : one or two short sentences.
       - scroll : optional bool. If true, the target is scrolled
                  into view before the spotlight is positioned —
                  needed for the "Join CTA" step which sits below
                  the fold on most viewports.

     `labels` carries the localised UI strings: next / prev / done
     / skip / stepOf (e.g. "Step 2 of 5"). Tour module never
     synthesises strings; everything visible comes from labels.

     `onComplete` fires when the user finishes or skips — used by
     the caller to set localStorage so the first-visit welcome
     strip stays dismissed.

     Behaviour:
       - Backdrop dims the page (50% black). Spotlight is a glowing
         ring around the target. Tooltip card carries the step
         content + Prev / Next / Done buttons.
       - Tooltip positions itself below the target by default, or
         above when the target sits in the bottom half of the
         viewport. On narrow viewports (< 640 px) it spans the
         full width minus a 12 px margin.
       - Focus trap: Tab cycles only inside the tooltip's buttons.
       - Keyboard: Enter advances (matching the focused Next
         button), Esc exits (treated as a skip), Left/Right arrows
         step back/forward.
       - prefers-reduced-motion: animations are disabled (the
         transitions are pure CSS so this is handled in the stylesheet).
       - On viewport resize, the spotlight + tooltip reposition.
       - If a target selector resolves to nothing (e.g. the page
         changed shape), that step is skipped silently and the tour
         continues. */
  function netsecTour(config) {
    const steps  = (config && config.steps) || [];
    const labels = Object.assign(
      { next: 'Next', prev: 'Back', done: 'Done', skip: 'Skip',
        stepOf: 'Step %1 of %2', closeLabel: 'Close tour' },
      (config && config.labels) || {}
    );
    const onComplete = (config && config.onComplete) || function () {};

    let idx = -1;
    let backdrop = null, spotlight = null, tooltip = null;
    let prevFocus = null;
    let resizeBound = null;

    function $el(tag, cls, html) {
      const el = document.createElement(tag);
      if (cls) el.className = cls;
      if (html !== undefined) el.innerHTML = html;
      return el;
    }

    function mount() {
      backdrop  = $el('div', 'tour-backdrop');
      spotlight = $el('div', 'tour-spotlight');
      tooltip   = $el('div', 'tour-tooltip', '');
      tooltip.setAttribute('role', 'dialog');
      tooltip.setAttribute('aria-modal', 'true');
      tooltip.setAttribute('aria-live', 'polite');
      document.body.appendChild(backdrop);
      document.body.appendChild(spotlight);
      document.body.appendChild(tooltip);
      // Click outside the tooltip (i.e. on the backdrop) is a skip.
      backdrop.addEventListener('click', skip);
    }

    function unmount() {
      [backdrop, spotlight, tooltip].forEach(n => n && n.remove());
      backdrop = spotlight = tooltip = null;
      document.removeEventListener('keydown', onKey);
      window.removeEventListener('resize', resizeBound);
      window.removeEventListener('scroll', resizeBound, true);
      if (prevFocus && typeof prevFocus.focus === 'function') {
        try { prevFocus.focus(); } catch (e) {}
      }
    }

    function start() {
      if (!steps.length) return;
      prevFocus = document.activeElement;
      mount();
      resizeBound = () => positionForStep(steps[idx]);
      window.addEventListener('resize', resizeBound);
      // Use capture so we catch any container's scroll, not only window's.
      window.addEventListener('scroll', resizeBound, true);
      document.addEventListener('keydown', onKey);
      idx = 0;
      render();
    }

    function next() {
      if (idx >= steps.length - 1) return done();
      idx++;
      render();
    }
    function prev() {
      if (idx <= 0) return;
      idx--;
      render();
    }
    function done() { unmount(); onComplete('done'); }
    function skip() { unmount(); onComplete('skip'); }

    function onKey(e) {
      if (e.key === 'Escape') { e.preventDefault(); return skip(); }
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        e.preventDefault(); return next();
      }
      if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault(); return prev();
      }
      // Focus trap: keep Tab inside the tooltip's buttons.
      if (e.key === 'Tab' && tooltip) {
        const focusables = tooltip.querySelectorAll('button');
        if (!focusables.length) return;
        const first = focusables[0];
        const last  = focusables[focusables.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault(); last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault(); first.focus();
        }
      }
    }

    function render() {
      const step = steps[idx];
      if (!step) return done();
      const target = document.querySelector(step.target);
      if (!target) {
        // Target missing — silently advance to keep the tour going.
        if (idx < steps.length - 1) return next();
        return done();
      }
      if (step.scroll) {
        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
        // Wait briefly for the scroll to settle before positioning.
        setTimeout(() => positionForStep(step), 360);
      } else {
        positionForStep(step);
      }
      // Render the tooltip content. Buttons in DOM order: Prev → Skip → Next/Done.
      const showPrev = idx > 0;
      const isLast   = idx === steps.length - 1;
      const stepLabel = labels.stepOf
        .replace('%1', String(idx + 1)).replace('%2', String(steps.length));
      tooltip.innerHTML = '';
      const titleEl   = $el('h3', 'tour-title');
      titleEl.textContent = step.title || '';
      const bodyEl    = $el('p',  'tour-body');
      bodyEl.textContent = step.body || '';
      const footerEl  = $el('div', 'tour-footer');
      const progress  = $el('span', 'tour-progress');
      progress.textContent = stepLabel;
      const actions   = $el('div', 'tour-actions');
      if (showPrev) {
        const b = $el('button', 'tour-btn tour-btn-ghost');
        b.type = 'button'; b.textContent = labels.prev;
        b.addEventListener('click', prev);
        actions.appendChild(b);
      }
      const skipBtn = $el('button', 'tour-btn tour-btn-ghost');
      skipBtn.type = 'button'; skipBtn.textContent = labels.skip;
      skipBtn.addEventListener('click', skip);
      actions.appendChild(skipBtn);
      const nextBtn = $el('button', 'tour-btn tour-btn-primary');
      nextBtn.type = 'button';
      nextBtn.textContent = isLast ? labels.done : labels.next;
      nextBtn.addEventListener('click', isLast ? done : next);
      actions.appendChild(nextBtn);
      footerEl.appendChild(progress);
      footerEl.appendChild(actions);
      tooltip.appendChild(titleEl);
      tooltip.appendChild(bodyEl);
      tooltip.appendChild(footerEl);
      // Focus the Next/Done button so Enter advances.
      requestAnimationFrame(() => nextBtn.focus());
      // Reveal the backdrop on the first render (it mounts hidden).
      backdrop.classList.add('is-visible');
    }

    function positionForStep(step) {
      if (!step || !tooltip || !spotlight) return;
      const target = document.querySelector(step.target);
      if (!target) return;
      const rect = target.getBoundingClientRect();
      // Spotlight is positioned in the viewport (fixed). We pad the
      // target rectangle by 6 px so the ring sits just outside it.
      const pad = 6;
      spotlight.style.top    = (rect.top - pad) + 'px';
      spotlight.style.left   = (rect.left - pad) + 'px';
      spotlight.style.width  = (rect.width + pad * 2) + 'px';
      spotlight.style.height = (rect.height + pad * 2) + 'px';

      // Tooltip placement. Prefer below; flip to above if the
      // target's bottom is in the lower half of the viewport.
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      const ttRect = tooltip.getBoundingClientRect();
      // We need to set position first, then measure — but the
      // tooltip may not have a stable size yet. Use a sensible
      // estimate (180px tall) for the first frame, then refine.
      const ttH = ttRect.height || 180;
      const ttW = Math.min(360, vw - 24);
      tooltip.style.width = ttW + 'px';
      const gap = 14;
      const placeBelow = (rect.bottom + ttH + gap) < vh - 8;
      let top  = placeBelow ? (rect.bottom + gap) : (rect.top - ttH - gap);
      // Clamp into viewport vertically.
      top = Math.max(8, Math.min(top, vh - ttH - 8));
      // Horizontally: try to centre on the target, then clamp.
      let left = rect.left + (rect.width / 2) - (ttW / 2);
      left = Math.max(12, Math.min(left, vw - ttW - 12));
      tooltip.style.top  = top + 'px';
      tooltip.style.left = left + 'px';
    }

    return { start };
  }
  window.netsecTour = netsecTour;
})();

/* ════════════════════════════════════════════════════════════════
   SITE-WIDE SEARCH (Pagefind)
   ────────────────────────────────────────────────────────────────
   A modal overlay search UI powered by a Pagefind index served from
   /pagefind/. Triggers:
     - Click on the .search-trigger button in the nav.
     - Cmd/Ctrl-K from anywhere.
     - "/" from anywhere except inside an input/textarea/contenteditable.
   The overlay lazy-loads Pagefind on first open so non-searchers
   never pay the runtime cost.
   ════════════════════════════════════════════════════════════════ */
(function () {
  // Per-locale strings. Picked off the <html lang="..."> attribute.
  // English is the authoritative source; FR/DE are mirrors.
  const STRINGS = {
    en: {
      placeholder: 'Search the site…',
      close: 'Close',
      navigate: 'navigate',
      open: 'open',
      escClose: 'close',
      noResults: 'No results for',
      typeToSearch: 'Type to search across pages, FAQ entries, glossary terms, and more.',
      resultsCount: (n) => `${n} ${n === 1 ? 'result' : 'results'}`,
      loading: 'Loading search…',
      loadError: 'Search is unavailable. Reload the page to try again.',
      searchLabel: 'Search',
    },
    fr: {
      placeholder: 'Rechercher sur le site…',
      close: 'Fermer',
      navigate: 'naviguer',
      open: 'ouvrir',
      escClose: 'fermer',
      noResults: 'Aucun résultat pour',
      typeToSearch: 'Tapez pour chercher dans les pages, la FAQ, le glossaire, et plus encore.',
      resultsCount: (n) => `${n} résultat${n === 1 ? '' : 's'}`,
      loading: 'Chargement de la recherche…',
      loadError: 'La recherche est indisponible. Rechargez la page pour réessayer.',
      searchLabel: 'Rechercher',
    },
    de: {
      placeholder: 'Website durchsuchen…',
      close: 'Schließen',
      navigate: 'navigieren',
      open: 'öffnen',
      escClose: 'schließen',
      noResults: 'Keine Treffer für',
      typeToSearch: 'Tippen Sie, um Seiten, FAQ-Einträge, Glossarbegriffe und mehr zu durchsuchen.',
      resultsCount: (n) => `${n} ${n === 1 ? 'Treffer' : 'Treffer'}`,
      loading: 'Suche wird geladen…',
      loadError: 'Suche nicht verfügbar. Seite neu laden und erneut versuchen.',
      searchLabel: 'Suchen',
    },
  };

  const lang = (document.documentElement.lang || 'en').slice(0, 2);
  const t = STRINGS[lang] || STRINGS.en;

  // ── State ────────────────────────────────────────────────────
  let pagefind = null;           // The loaded Pagefind module
  let pagefindError = false;     // Set if the index fails to load
  let pagefindPromise = null;    // Memoised loader
  let overlay = null;            // The injected DOM
  let lastFocus = null;          // Restore on close
  let debounceTimer = 0;
  let activeIndex = -1;          // Highlighted result row
  let currentResults = [];       // Hits from the last search

  // ── Lazy-load Pagefind ────────────────────────────────────────
  // On first open we dynamically import the index runtime. Errors
  // (e.g. missing /pagefind/ in dev) surface as a friendly inline
  // message; nothing else on the page is affected.
  function loadPagefind() {
    if (pagefindPromise) return pagefindPromise;
    pagefindPromise = (async () => {
      try {
        const mod = await import('/pagefind/pagefind.js');
        await mod.init();
        // Restrict results to the current locale. Pagefind reads
        // each indexed page's <html lang> at build time and labels
        // shards by language; .filters({language: lang}) further
        // narrows queries.
        pagefind = mod;
        return mod;
      } catch (e) {
        pagefindError = true;
        console.error('Pagefind failed to load', e);
        throw e;
      }
    })();
    return pagefindPromise;
  }

  // ── Build the overlay DOM (once, on first open) ──────────────
  function buildOverlay() {
    if (overlay) return overlay;
    overlay = document.createElement('div');
    overlay.className = 'search-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-label', t.searchLabel);
    overlay.hidden = true;
    overlay.innerHTML = `
      <div class="search-backdrop" data-search-close></div>
      <div class="search-panel glass" role="document">
        <div class="search-header">
          <svg class="search-input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
          <input class="search-input" type="search" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" placeholder="${t.placeholder}" aria-label="${t.searchLabel}" aria-controls="search-results-list" aria-expanded="false" aria-autocomplete="list">
          <button class="search-close" type="button" aria-label="${t.close}" data-search-close>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 6L6 18M6 6l12 12"/></svg>
          </button>
        </div>
        <div class="search-meta" aria-live="polite" aria-atomic="true"></div>
        <ul class="search-results" id="search-results-list" role="listbox" aria-label="${t.searchLabel}"></ul>
        <div class="search-hints">
          <span><kbd>↑</kbd><kbd>↓</kbd> ${t.navigate}</span>
          <span><kbd>↵</kbd> ${t.open}</span>
          <span><kbd>Esc</kbd> ${t.escClose}</span>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    const input = overlay.querySelector('.search-input');
    const list = overlay.querySelector('.search-results');
    const meta = overlay.querySelector('.search-meta');

    // Idle state — empty input shows the prompt.
    meta.textContent = t.typeToSearch;

    input.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => runSearch(input.value.trim()), 120);
    });

    // Keyboard navigation between results.
    overlay.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { close(); return; }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        moveActive(1);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        moveActive(-1);
      } else if (e.key === 'Enter' && activeIndex >= 0 && currentResults[activeIndex]) {
        e.preventDefault();
        const a = list.children[activeIndex]?.querySelector('a');
        if (a) a.click();
      }
    });

    overlay.addEventListener('click', (e) => {
      if (e.target.closest('[data-search-close]')) close();
    });

    return overlay;
  }

  // ── Query + render ───────────────────────────────────────────
  async function runSearch(query) {
    const meta = overlay.querySelector('.search-meta');
    const list = overlay.querySelector('.search-results');
    const input = overlay.querySelector('.search-input');

    activeIndex = -1;
    currentResults = [];

    if (!query) {
      meta.textContent = t.typeToSearch;
      list.innerHTML = '';
      input.setAttribute('aria-expanded', 'false');
      return;
    }

    if (pagefindError) {
      meta.textContent = t.loadError;
      list.innerHTML = '';
      return;
    }

    try {
      const pf = await loadPagefind();
      // Pagefind's per-language filtering: only results in the
      // active locale appear. (Each indexed page's <html lang>
      // determines the shard it lands in.)
      const search = await pf.search(query, { filters: { language: lang } });
      // search.results is a Promise array of hit handles. Resolve
      // the first ~10 — Pagefind returns ranked results lazily.
      const hits = await Promise.all(search.results.slice(0, 12).map((r) => r.data()));
      currentResults = hits;
      renderResults(hits, query);
    } catch (e) {
      meta.textContent = t.loadError;
      list.innerHTML = '';
    }
  }

  function renderResults(hits, query) {
    const meta = overlay.querySelector('.search-meta');
    const list = overlay.querySelector('.search-results');
    const input = overlay.querySelector('.search-input');

    if (hits.length === 0) {
      meta.textContent = `${t.noResults} "${query}"`;
      list.innerHTML = '';
      input.setAttribute('aria-expanded', 'false');
      return;
    }

    meta.textContent = t.resultsCount(hits.length);
    input.setAttribute('aria-expanded', 'true');

    list.innerHTML = hits.map((hit, i) => {
      // Pagefind populates meta.title from the page's <title>; the
      // section heading comes via sub_results[0].title if the hit
      // matched within an anchored sub-section.
      const title = escapeHtml(hit.meta.title || hit.url);
      const sub = hit.sub_results && hit.sub_results[0];
      const heading = sub ? escapeHtml(sub.title) : '';
      const url = sub ? sub.url : hit.url;
      const excerpt = sub ? sub.excerpt : hit.excerpt;
      return `
        <li role="option" aria-selected="false" id="search-result-${i}">
          <a href="${url}">
            <div class="search-result-head">
              <span class="search-result-title">${title}</span>
              ${heading ? `<span class="search-result-sep">·</span><span class="search-result-section">${heading}</span>` : ''}
            </div>
            <div class="search-result-excerpt">${excerpt}</div>
          </a>
        </li>
      `;
    }).join('');
  }

  function moveActive(delta) {
    const list = overlay.querySelector('.search-results');
    const items = list.children;
    if (items.length === 0) return;
    activeIndex = (activeIndex + delta + items.length) % items.length;
    for (let i = 0; i < items.length; i++) {
      const isActive = i === activeIndex;
      items[i].classList.toggle('is-active', isActive);
      items[i].setAttribute('aria-selected', isActive ? 'true' : 'false');
    }
    const active = items[activeIndex];
    if (active) {
      const input = overlay.querySelector('.search-input');
      input.setAttribute('aria-activedescendant', active.id);
      active.scrollIntoView({ block: 'nearest' });
    }
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  // ── Open / close ─────────────────────────────────────────────
  function open() {
    if (overlay && !overlay.hidden) return;
    lastFocus = document.activeElement;
    buildOverlay();
    overlay.hidden = false;
    document.body.classList.add('search-open');
    // Pre-load the index in the background so the first keystroke
    // is fast (we don't await; if it fails the input still works
    // and surfaces the error).
    loadPagefind().catch(() => {});
    requestAnimationFrame(() => {
      overlay.querySelector('.search-input').focus();
    });
  }

  function close() {
    if (!overlay || overlay.hidden) return;
    overlay.hidden = true;
    document.body.classList.remove('search-open');
    const input = overlay.querySelector('.search-input');
    if (input) input.value = '';
    const list = overlay.querySelector('.search-results');
    if (list) list.innerHTML = '';
    const meta = overlay.querySelector('.search-meta');
    if (meta) meta.textContent = t.typeToSearch;
    activeIndex = -1;
    currentResults = [];
    if (lastFocus && typeof lastFocus.focus === 'function') {
      lastFocus.focus();
    }
  }

  // ── Trigger wiring ───────────────────────────────────────────
  // 1. Click on the magnifying-glass button in the nav.
  document.addEventListener('click', (e) => {
    if (e.target.closest('.search-trigger')) {
      e.preventDefault();
      open();
    }
  });

  // 2. Cmd/Ctrl-K from anywhere.
  // 3. "/" from anywhere EXCEPT inside an input / textarea / contenteditable.
  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
      e.preventDefault();
      open();
      return;
    }
    if (e.key === '/' && !e.metaKey && !e.ctrlKey && !e.altKey) {
      const tag = (e.target.tagName || '').toLowerCase();
      const editable = e.target.isContentEditable;
      if (tag === 'input' || tag === 'textarea' || tag === 'select' || editable) return;
      e.preventDefault();
      open();
    }
  });

  // Expose for debugging / programmatic open if ever needed.
  window.netsecSearch = { open, close };
})();
