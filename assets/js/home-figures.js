/* Home-page figures strip: members, countries, Working Groups and events
 * held, counted at page load from data/bios.json, data/wg.json and
 * data/events.json, so the figures follow the data without a rebuild.
 *
 * The numbers count up the first time the strip scrolls into view. Under
 * prefers-reduced-motion the final values show at once: the global CSS
 * reduced-motion rule only reaches CSS animation, not this rAF loop.
 *
 * Needs home-events.js (zonedTimeToUTC) loaded first. Entry point:
 * window.NetSec.renderHomeFigures({ container, locale }).
 */
(function () {
  'use strict';

  const NS = window.NetSec = window.NetSec || {};
  const DURATION = 900;
  const T = (s) => (window.netsecT && window.netsecT(s)) || s;

  // Pure counting, exported for scripts/test-home-figures.mjs.
  function countFigures(bios, wg, eventsData, nowMs) {
    const members = (bios && bios.members) || [];
    const tzid = (eventsData && eventsData.tzid) || 'Europe/Stockholm';
    const held = ((eventsData && eventsData.events) || []).filter((ev) => {
      const end = NS.zonedTimeToUTC(ev.end || ev.start, ev.tzid || tzid);
      return end && end.getTime() < nowMs;
    }).length;
    return {
      members: members.length,
      countries: new Set(members.map((m) => (m.country || '').trim()).filter(Boolean)).size,
      groups: ((wg && wg.groups) || []).length,
      held,
    };
  }

  function countUp(nodes, fmt) {
    const start = performance.now();
    const step = (t) => {
      const p = Math.min(1, (t - start) / DURATION);
      const eased = 1 - Math.pow(1 - p, 3);
      nodes.forEach(([dd, n]) => { dd.textContent = fmt.format(Math.round(n * eased)); });
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  async function renderHomeFigures(opts) {
    opts = opts || {};
    const root = document.querySelector(opts.container || '[data-home-figures]');
    const grid = root && root.querySelector('[data-home-figures-grid]');
    if (!grid || !NS.zonedTimeToUTC) return;
    const locale = (opts.locale || 'en').toLowerCase();
    const get = (url) => fetch(url, { cache: 'no-cache' }).then((r) => {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
    let bios, wg, events;
    try {
      [bios, wg, events] = await Promise.all([get('data/bios.json'), get('data/wg.json'), get('data/events.json')]);
    } catch (e) {
      // Additive section: a failed fetch leaves it hidden.
      console.debug('home-figures: fetch failed, strip stays hidden.', e);
      return;
    }
    const c = countFigures(bios, wg, events, Date.now());
    const fmt = new Intl.NumberFormat(locale);
    const nodes = [];
    const rows = [[c.members, 'members'], [c.countries, 'countries'], [c.groups, 'Working Groups'], [c.held, 'events held']]
      .filter(([n]) => n > 0)
      .map(([n, label]) => {
        const row = document.createElement('div');
        row.className = 'figures-item';
        const dt = document.createElement('dt');
        dt.textContent = T(label);
        const dd = document.createElement('dd');
        dd.textContent = fmt.format(n);
        nodes.push([dd, n]);
        row.append(dt, dd);
        return row;
      });
    if (!rows.length) return;
    grid.replaceChildren(...rows);
    root.hidden = false;

    const still = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (still || !('IntersectionObserver' in window)) return;
    const io = new IntersectionObserver((entries) => {
      if (!entries.some((e) => e.isIntersecting)) return;
      io.disconnect();
      // Zeroed only now, so a page that never renders a frame (a hidden
      // tab, a crawler) keeps the real values.
      nodes.forEach(([dd]) => { dd.textContent = fmt.format(0); });
      countUp(nodes, fmt);
    }, { threshold: 0.5 });
    io.observe(root);
  }

  NS.countFigures = countFigures;
  NS.renderHomeFigures = renderHomeFigures;
})();
