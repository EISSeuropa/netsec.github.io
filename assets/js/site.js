/* NetSec — shared site script
   ────────────────────────────────────────────────────────────────
   Loaded by every page. Each block is guarded so it no-ops when the
   relevant DOM element isn't present, so additional pages can opt in
   to whichever features they need. */
(function () {
  'use strict';

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
    const setLabel = () => {
      themeBtn.setAttribute('aria-label',
        document.documentElement.classList.contains('dark')
          ? 'Switch to light mode' : 'Switch to dark mode');
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
})();
