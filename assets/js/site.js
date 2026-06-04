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
      'Research interests': 'Domaines de recherche',
      'Show all': 'Tout afficher',
      'Show fewer': 'Réduire',
      'Clear': 'Effacer',
      'Filter by research interest': 'Filtrer par domaine de recherche',
      'Directory last updated {0}.': 'Annuaire mis à jour le {0}.',
      'Available to mentor': 'Disponible comme mentor',
      'Seeking mentorship': 'En recherche de mentorat',
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
      'Research interests': 'Forschungsschwerpunkte',
      'Show all': 'Alle anzeigen',
      'Show fewer': 'Weniger anzeigen',
      'Clear': 'Zurücksetzen',
      'Filter by research interest': 'Nach Forschungsschwerpunkt filtern',
      'Directory last updated {0}.': 'Verzeichnis zuletzt aktualisiert am {0}.',
      'Available to mentor': 'Als Mentor verfügbar',
      'Seeking mentorship': 'Sucht Mentoring',
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

  /* Headshot WebP helper (#269). The directory cards, the ESSC member
     popover, and the About / Working-Group avatars all serve
     <picture><source type="image/webp"><img original></picture>, so a
     modern browser fetches the ~50%-smaller WebP and the original JPEG /
     PNG stays as the fallback. sync-bios.py writes a `<slug>.webp`
     sibling for every headshot. Returns the WebP path, or null when the
     source is absent or already WebP (nothing to add). */
  window.netsecWebp = function (path) {
    if (typeof path !== 'string') return null;
    return /\.(jpe?g|png)$/i.test(path)
      ? path.replace(/\.(jpe?g|png)$/i, '.webp')
      : null;
  };

  /* Beta-translation ribbon: keep the layout offset in step with the
     ribbon's real measured height.

     The ribbon is `position: fixed; top: 0` and the body's
     `padding-top` + nav's `top` are derived from `--ribbon-h` so
     content doesn't sit under it. The fallback in CSS is 38px
     (single-line desktop). On narrow viewports the long
     "Traduction automatique…" sentence + link wraps to two or
     three lines, making the ribbon 60–100px tall. Without this
     measurement the nav would overlap the bottom of the ribbon
     (reported on mobile).

     The measurement runs:
       - once on script start (catches the initial layout),
       - on every viewport resize (catches wrap-state changes),
       - on every ribbon resize (covers anything we don't predict).
  */
  const ribbon = document.querySelector('.i18n-beta-ribbon');
  if (ribbon && document.documentElement.hasAttribute('data-i18n-status')) {
    const syncRibbonHeight = () => {
      const h = ribbon.offsetHeight;
      if (h > 0) {
        document.documentElement.style.setProperty('--ribbon-h', h + 'px');
      }
    };
    // Run now (best-effort: defer scripts run after DOM but before
    // CSS is guaranteed to have applied, so offsetHeight may still be
    // 0 here), then again once everything has loaded, then on every
    // viewport resize / ribbon resize. The window.load + ResizeObserver
    // pair guarantees we eventually set the right value even if the
    // synchronous read returned 0.
    syncRibbonHeight();
    if (document.readyState !== 'complete') {
      window.addEventListener('load', syncRibbonHeight, { once: true });
    }
    window.addEventListener('resize', syncRibbonHeight, { passive: true });
    if (typeof ResizeObserver === 'function') {
      new ResizeObserver(syncRibbonHeight).observe(ribbon);
    }
  }

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

  /* Anchor-scroll offset + precise in-page section navigation.

     Two problems this solves:
       1. The header is `position: fixed` and its height varies with
          the beta ribbon and the What's-New banner, so the static
          `scroll-padding-top` in CSS lands section headings under it.
          We measure the real header bottom and publish it as
          scroll-padding-top, recomputed whenever the ribbon, banner,
          or nav changes size. This governs native hash landings
          (page load with a #hash, and cross-page links like
          working-groups.html#wg1).
       2. The primary nav links are authored as `index.html#section`
          so they resolve from every page. On the home page itself
          that points at the same document but with a different path
          string, so the browser does a full reload + native hash jump
          rather than an in-page scroll, and the events / spotlight
          blocks that render in after load throw the landing off.
          We intercept header- and jump-nav links that resolve to the
          current document and scroll to them ourselves, clearing the
          measured header. */
  (function () {
    const headerBottom = () =>
      nav ? Math.max(0, nav.getBoundingClientRect().bottom) : 78;
    const syncPad = () => {
      document.documentElement.style.scrollPaddingTop =
        Math.round(headerBottom() + 14) + 'px';
    };
    syncPad();
    window.addEventListener('load', syncPad);
    window.addEventListener('resize', syncPad, { passive: true });
    if (nav && typeof ResizeObserver === 'function') {
      new ResizeObserver(syncPad).observe(nav);
      const rib = document.querySelector('.i18n-beta-ribbon');
      if (rib) new ResizeObserver(syncPad).observe(rib);
    }
    // The nav is `position: fixed` and its `top` is driven by the CSS
    // vars --whats-new-h / --ribbon-h, which the banner and ribbon set
    // on <html> *after* this runs. Changing top moves the nav without
    // resizing it, so the ResizeObserver above never fires. Watch the
    // <html> style attribute (where those vars live) and recompute, and
    // re-measure a few times early on to catch the async banner mount.
    if (typeof MutationObserver === 'function') {
      new MutationObserver(syncPad).observe(document.documentElement,
        { attributes: true, attributeFilter: ['style'] });
    }
    [150, 500, 1200].forEach((d) => setTimeout(syncPad, d));

    // Normalise so "/", "/index.html", "/index.fr.html" compare equal.
    const normPath = (p) =>
      p.replace(/index(\.[a-z]{2})?\.html$/, '').replace(/\/+$/, '') || '/';
    const inPageTarget = (a) => {
      if (!a || !a.hash || a.host !== location.host) return null;
      if (normPath(a.pathname) !== normPath(location.pathname)) return null;
      let id;
      try { id = decodeURIComponent(a.hash.slice(1)); } catch (_) { return null; }
      return id ? document.getElementById(id) : null;
    };
    document.addEventListener('click', (e) => {
      const a = e.target.closest && e.target.closest(
        '.nav-links a[href], .wg-jump a[href]');
      if (!a) return;
      const target = inPageTarget(a);
      if (!target) return;             // cross-page or no such section: let it navigate
      e.preventDefault();
      const y = window.scrollY + target.getBoundingClientRect().top
        - headerBottom() - 14;
      const reduce = window.matchMedia
        && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      window.scrollTo({ top: Math.max(0, y), behavior: reduce ? 'auto' : 'smooth' });
      if (history.replaceState) history.replaceState(null, '', a.hash);
      // Move focus to the section for keyboard / screen-reader users,
      // without letting .focus() yank the scroll position back.
      target.setAttribute('tabindex', '-1');
      try { target.focus({ preventScroll: true }); } catch (_) {}
    });
  })();

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

    // Beta-translation ribbon: the "View in English" link inside
    // `.i18n-beta-ribbon` lives outside `.lang-switch`, so without this
    // it doesn't update `netsec-lang`. Result: the auto-redirect below
    // bounces the user from EN straight back to the FR / DE page they
    // just left. Persist the destination language on click so the
    // ribbon-driven switch sticks (#253).
    document.querySelectorAll('.i18n-beta-ribbon a[hreflang]').forEach(a => {
      a.addEventListener('click', () => {
        try {
          const lang = (a.getAttribute('hreflang') || '').toLowerCase();
          if (lang) localStorage.setItem('netsec-lang', lang);
        } catch (e) {}
      });
    });

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
            if (img) {
              if (img.getAttribute('src') !== m.photo) img.setAttribute('src', m.photo);
              if (m.name) img.setAttribute('alt', m.name);
              // Wrap the avatar in <picture> with a WebP source (#269);
              // the original <img> stays as the fallback. Idempotent.
              const webp = window.netsecWebp && window.netsecWebp(m.photo);
              if (webp) {
                let pic = img.closest('picture');
                if (!pic) {
                  pic = document.createElement('picture');
                  const src = document.createElement('source');
                  src.type = 'image/webp';
                  src.srcset = webp;
                  img.parentNode.insertBefore(pic, img);
                  pic.appendChild(src);
                  pic.appendChild(img);
                } else {
                  const src = pic.querySelector('source');
                  if (src) src.srcset = webp;
                }
              }
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
      if (!target || target.hidden) {
        // Target missing, or present but hidden (e.g. a data-driven
        // filter row that has no data yet, like the keyword or
        // mentorship filters) — silently advance to keep the tour going.
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

  // ── Platform-aware shortcut label ────────────────────────────
  // Mac users have a ⌘ key; everyone else uses Ctrl. The button's
  // `title` tooltip is rewritten on load so each visitor sees the
  // shortcut that applies to *their* keyboard, not a generic
  // "Cmd/Ctrl-K" mash-up that adds visual noise.
  const isMac = /mac|iphone|ipad|ipod/i.test(
    navigator.platform || navigator.userAgent || ''
  );
  const shortcutLabel = isMac ? '⌘ K' : 'Ctrl K';

  // ── Highlight-on-landing bootstrap ────────────────────────────
  // When a search result link navigates here with a
  // `?pagefind-highlight=<term>` query, dynamically import
  // Pagefind's mark.js wrapper and highlight every match of the
  // term. The script injects a default `:where(.pagefind-
  // highlight){background:yellow;color:black}` style. If the URL
  // has no fragment to scroll to, also scroll the first highlight
  // into view so the visitor lands on the matched term, not on
  // the page top.
  //
  // We instantiate but deliberately DON'T call `.highlight()` on the
  // result — the constructor runs `this.highlight()` itself, so a
  // second call wraps every already-marked term in a nested second
  // `<mark>` (issue #118). Screen readers announce the inner mark
  // twice; visual rendering is unaffected.
  if (window.location.search.indexOf('pagefind-highlight=') !== -1) {
    import('/pagefind/pagefind-highlight.js')
      .then((mod) => {
        new mod.default();
        if (!window.location.hash) {
          requestAnimationFrame(() => {
            const first = document.querySelector('.pagefind-highlight');
            if (first) {
              first.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
          });
        }
      })
      .catch((e) => console.warn('Pagefind highlight failed', e));
  }

  // ── State ────────────────────────────────────────────────────
  let pagefind = null;           // The loaded Pagefind module
  let pagefindError = false;     // Set if the index fails to load
  let pagefindPromise = null;    // Memoised loader
  let overlay = null;            // The injected DOM
  let lastFocus = null;          // Restore on close
  let debounceTimer = 0;
  let activeIndex = -1;          // Highlighted result row
  let currentResults = [];       // Hits from the last search

  // Last error from Pagefind, surfaced in the overlay's meta line
  // alongside the user-facing message so a maintainer reading over
  // a user's shoulder can see what actually broke.
  let pagefindErrorMessage = '';

  // ── Lazy-load Pagefind ────────────────────────────────────────
  // On first open we dynamically import the index runtime. Errors
  // (e.g. missing /pagefind/ in dev) surface as a friendly inline
  // message; nothing else on the page is affected.
  function loadPagefind() {
    if (pagefindPromise) return pagefindPromise;
    pagefindPromise = (async () => {
      try {
        const mod = await import('/pagefind/pagefind.js');
        // mod.init() doesn't wait for the WASM to load — that
        // happens lazily on first .search() — but calling it lets
        // us set options before the first query.
        await mod.init();
        // Opt into the URL-based highlight feature. With this set,
        // Pagefind appends `?pagefind-highlight=<term>` to every
        // sub-result URL. The destination page's highlight script
        // (the bootstrap block at the top of this file) reads the
        // param and marks the matched term — so the visitor lands
        // on the anchored section AND sees the matched word
        // highlighted in yellow.
        await mod.options({ highlightParam: 'pagefind-highlight' });
        pagefind = mod;
        return mod;
      } catch (e) {
        pagefindError = true;
        pagefindErrorMessage = String(e && e.message ? e.message : e);
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
      // Close on the explicit close button / backdrop, AND on any
      // result-link click. Without the latter, the overlay would
      // stay open after navigation: same-page hash-only links
      // don't reload, so the visitor would see the modal still
      // covering the page they're trying to read.
      if (
        e.target.closest('[data-search-close]') ||
        e.target.closest('.search-results a')
      ) {
        close();
      }
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
      meta.textContent = pagefindErrorMessage
        ? `${t.loadError} (${pagefindErrorMessage})`
        : t.loadError;
      list.innerHTML = '';
      return;
    }

    try {
      const pf = await loadPagefind();
      // Pagefind v1 ships one shard per language and picks the
      // active one from <html lang> at init time. No filter needed
      // on the search call — passing `{filters: {language: lang}}`
      // is interpreted as "filter by a `language` metadata field
      // on each page", which we never set, so it threw / returned
      // nothing. Empty options is correct.
      const search = await pf.search(query);
      // search.results is a Promise array of hit handles. Resolve
      // the first ~12 — Pagefind returns ranked results lazily.
      const hits = await Promise.all(search.results.slice(0, 12).map((r) => r.data()));
      currentResults = hits;
      renderResults(hits, query);
    } catch (e) {
      pagefindErrorMessage = String(e && e.message ? e.message : e);
      console.error('Pagefind search failed', e);
      meta.textContent = `${t.loadError} (${pagefindErrorMessage})`;
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

    list.innerHTML = hits.map((hit, i) => renderHit(hit, i)).join('');
  }

  // Per-hit renderer. Directory bio hits get a richer card with the
  // member's photo / country flag / WG chips. Everything else falls
  // back to the plain title + section + excerpt layout.
  function renderHit(hit, i) {
    if (hit.meta && hit.meta.kind === 'bio') {
      return renderBioHit(hit, i);
    }
    return renderPageHit(hit, i);
  }

  function renderPageHit(hit, i) {
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
  }

  function renderBioHit(hit, i) {
    // Bio stubs (search/bios/<lang>/<slug>.html) set:
    //   meta.kind == 'bio'
    //   meta.title       — Dr Name (from the stub's <title>, sans " — NetSec directory")
    //   meta.photo       — relative path to the headshot
    //   meta.country     — ISO 3166-1 alpha-2 country code (lowercase)
    //   meta.affiliation — text
    //   meta.role        — "MC member · Switzerland", or "" for non-MC
    //   meta.wgs         — comma-separated WG numbers, e.g. "2,3"
    const rawTitle = (hit.meta.title || '').replace(/\s+—\s+NetSec directory$/, '');
    const name = escapeHtml(rawTitle);
    const affiliation = escapeHtml(hit.meta.affiliation || '');
    const role = escapeHtml(hit.meta.role || '');
    const country = (hit.meta.country || '').toLowerCase().replace(/[^a-z]/g, '');
    const photo = hit.meta.photo || '';
    const wgs = (hit.meta.wgs || '').split(',').map((s) => s.trim()).filter(Boolean);
    // Rewrite the stub URL to the canonical directory anchor.
    // Pagefind v1 doesn't have a per-page URL-override mechanism,
    // so we do it client-side: parse the stub URL's path for the
    // locale + slug, build /people.html#<slug> (locale-aware),
    // and carry the highlight query through if present.
    const url = canonicalBioUrl(hit.url) || hit.url;

    const flagImg = country
      ? `<img class="search-bio-flag" src="https://flagcdn.com/h20/${country}.png" alt="" loading="lazy">`
      : '';
    const photoEl = photo
      ? `<img class="search-bio-photo" src="${escapeHtml(photo)}" alt="" loading="lazy">`
      : `<span class="search-bio-photo search-bio-photo-fallback" aria-hidden="true">${initialsFor(rawTitle)}</span>`;
    const wgChips = wgs
      .map((w) => `<span class="search-bio-wg">WG${escapeHtml(w)}</span>`)
      .join('');
    const subline = role || affiliation;

    return `
      <li role="option" aria-selected="false" id="search-result-${i}" class="search-bio">
        <a href="${url}">
          ${photoEl}
          <div class="search-bio-text">
            <div class="search-bio-head">
              <span class="search-bio-name">${name}</span>
              ${flagImg}
            </div>
            ${subline ? `<div class="search-bio-subline">${subline}</div>` : ''}
            ${role && affiliation && role !== affiliation
                ? `<div class="search-bio-affiliation">${affiliation}</div>` : ''}
            ${wgChips ? `<div class="search-bio-wgs">${wgChips}</div>` : ''}
          </div>
        </a>
      </li>
    `;
  }

  // Rewrites a Pagefind bio-stub URL to the canonical directory
  // entry. Stubs live at /search/bios/<lang>/<slug>.html and are
  // never visited; the overlay link points straight at
  // /people.html#<slug> (or /people.<lang>.html#<slug>) with the
  // pagefind-highlight query carried through.
  //   /search/bios/en/arthur-laudrain.html?pagefind-highlight=foo
  //     → /people.html?pagefind-highlight=foo#arthur-laudrain
  function canonicalBioUrl(stubUrl) {
    if (!stubUrl) return null;
    const m = stubUrl.match(
      /\/search\/bios\/([a-z]{2})\/([^/?#.]+)\.html(\?[^#]*)?/
    );
    if (!m) return null;
    const [, bioLang, slug, query] = m;
    const peoplePath = bioLang === 'en'
      ? '/people.html'
      : `/people.${bioLang}.html`;
    return `${peoplePath}${query || ''}#${slug}`;
  }

  // Two-letter initials for the photo fallback — mirrors the
  // directory's own avatar fallback rule (strip salutation, take
  // first letter of first and last name).
  function initialsFor(name) {
    const tokens = String(name)
      .replace(/^(Dr|Prof|Mr|Mrs|Ms|Mx)\.?\s+/i, '')
      .trim()
      .split(/\s+/);
    if (tokens.length === 0) return '?';
    const first = tokens[0].charAt(0).toUpperCase();
    const last = tokens.length > 1
      ? tokens[tokens.length - 1].charAt(0).toUpperCase()
      : '';
    return escapeHtml(first + last);
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

  // Rewrite the .search-trigger button titles to show the visitor's
  // platform shortcut (⌘ K on Mac, Ctrl K elsewhere). The HTML
  // ships a generic "Search (Cmd/Ctrl-K)" placeholder; the rewrite
  // happens once on page load.
  (function setTriggerTitles() {
    const title = `${t.searchLabel} (${shortcutLabel})`;
    document.querySelectorAll('.search-trigger').forEach((btn) => {
      btn.setAttribute('title', title);
      btn.setAttribute('aria-keyshortcuts', isMac ? 'Meta+K' : 'Control+K');
    });
  })();

  // 1. Click on the magnifying-glass button in the nav.
  document.addEventListener('click', (e) => {
    if (e.target.closest('.search-trigger')) {
      e.preventDefault();
      open();
    }
  });

  // 2. Cmd/Ctrl-K from anywhere.
  // 3. "/" from anywhere EXCEPT inside an input / textarea / contenteditable.
  //
  // For Cmd/Ctrl-K we check both e.key and e.code so the shortcut
  // still works on layouts where the printed `k` glyph isn't at the
  // physical KeyK position (Dvorak, AZERTY in some browsers, etc.).
  // We also listen on `window` rather than `document` because some
  // browser extensions install higher-priority listeners on document
  // that swallow Cmd-K before it reaches a document-level handler.
  function isCmdK(e) {
    if (!(e.metaKey || e.ctrlKey)) return false;
    if (e.altKey) return false;
    const key = (e.key || '').toLowerCase();
    return key === 'k' || e.code === 'KeyK';
  }

  window.addEventListener('keydown', (e) => {
    if (isCmdK(e)) {
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

/* What's New banner — sparingly-used site-wide announcement.
   ──────────────────────────────────────────────────────────
   Reads /data/whats-new.json. If `active: true` and the visitor
   hasn't dismissed this exact `version`, renders a dismissible
   banner at the top of <body>. Dismissal saves to
   localStorage('netsec-whats-new-dismissed-<version>') so the
   visitor sees the banner once and never again for that release.

   Used sparingly per CLAUDE.md §14 — at most 3-4 activations per
   year, on releases that introduce something a returning visitor
   would want to know about without scrolling for it. NOT used for
   quality patches, structural refactors, or release-infrastructure
   changes. Maintainer flips `active` true → false manually. */
(function () {
  fetch('/data/whats-new.json', { cache: 'no-cache' })
    .then(r => r.ok ? r.json() : null)
    .then(data => {
      if (!data || !data.active || !data.version) return;
      let dismissed = null;
      try { dismissed = localStorage.getItem('netsec-whats-new-dismissed-' + data.version); } catch (e) {}
      if (dismissed) return;
      renderWhatsNewBanner(data);
    })
    .catch(() => { /* JSON 404 or parse error — silent no-op */ });

  function renderWhatsNewBanner(data) {
    const lang = (document.documentElement.lang || 'en').toLowerCase().slice(0, 2);
    const headline = (data.headline && (data.headline[lang] || data.headline.en)) || '';
    if (!headline) return;
    const ctaLabel = data.cta && data.cta.i18n && (data.cta.i18n[lang] || data.cta.i18n.en);
    // href can be a plain string (same URL for every locale, e.g. a
    // GitHub release page) OR a {en, fr, de} object (locale-specific
    // landing pages, e.g. /essc-2026.html vs .fr.html vs .de.html).
    const rawHref = data.cta && data.cta.href;
    const ctaHref = typeof rawHref === 'string'
      ? rawHref
      : (rawHref && (rawHref[lang] || rawHref.en)) || '';

    const banner = document.createElement('div');
    banner.className = 'whats-new-banner';
    banner.setAttribute('role', 'status');

    const sparkle = document.createElement('span');
    sparkle.className = 'whats-new-sparkle';
    sparkle.setAttribute('aria-hidden', 'true');
    sparkle.textContent = '✦';
    banner.appendChild(sparkle);

    const text = document.createElement('span');
    text.className = 'whats-new-text';
    text.textContent = headline;
    banner.appendChild(text);

    if (ctaLabel && ctaHref) {
      const cta = document.createElement('a');
      cta.className = 'whats-new-cta';
      cta.href = ctaHref;
      cta.textContent = ctaLabel;
      if (data.cta.external) {
        cta.target = '_blank';
        cta.rel = 'noopener';
      }
      banner.appendChild(cta);
    }

    const close = document.createElement('button');
    close.type = 'button';
    close.className = 'whats-new-close';
    const closeLabel = { en: 'Dismiss', fr: 'Fermer', de: 'Schließen' }[lang] || 'Dismiss';
    close.setAttribute('aria-label', closeLabel);
    close.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
    close.addEventListener('click', () => {
      try { localStorage.setItem('netsec-whats-new-dismissed-' + data.version, '1'); } catch (e) {}
      banner.classList.add('whats-new-banner--closing');
      // Keep --whats-new-h set through the slide-out animation so
      // content doesn't snap up while the banner is visibly leaving.
      // Clear it (so ribbon + nav slide back up to top:0) only after
      // the animation completes.
      setTimeout(() => {
        document.documentElement.style.removeProperty('--whats-new-h');
        banner.remove();
      }, 240);
    });
    banner.appendChild(close);

    // Insert at the very top of <body>. The banner is position: fixed,
    // so insertion order doesn't change the visual stack; what matters
    // is the body padding-top and the ribbon/nav top offsets, both
    // composed against --whats-new-h via CSS calc().
    document.body.insertBefore(banner, document.body.firstChild);

    // Measure and publish the banner height as --whats-new-h on the
    // documentElement so the existing top-stack math (body padding,
    // ribbon top, nav top) picks it up. Same pattern as --ribbon-h.
    // ResizeObserver covers wrap-state changes (the headline can
    // re-wrap on narrow viewports or as fonts swap).
    const syncBannerHeight = () => {
      const h = banner.offsetHeight;
      if (h > 0) {
        document.documentElement.style.setProperty('--whats-new-h', h + 'px');
      }
    };
    syncBannerHeight();
    if (document.readyState !== 'complete') {
      window.addEventListener('load', syncBannerHeight, { once: true });
    }
    window.addEventListener('resize', syncBannerHeight, { passive: true });
    if (typeof ResizeObserver === 'function') {
      try { new ResizeObserver(syncBannerHeight).observe(banner); } catch (e) {}
    }
  }
})();
