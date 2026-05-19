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
})();
