/* Home-page Now row: three tiles under the hero, filled from
 * data/events.json and data/news.json.
 *
 *  - Next up:    the event in progress, else the next one (a TENTATIVE
 *                entry reads "Save the date"), else the last one held.
 *  - Open calls: news items with `type: "call"`, soonest `homeUntil`
 *                first; an item with no `homeUntil` is a rolling call.
 *  - Latest:     the newest news item that is not a call.
 *
 * Every tile has a fallback, so the row is never empty while either file
 * holds anything. The section stays hidden without JavaScript and carries
 * data-pagefind-ignore, since its content depends on the date.
 *
 * Needs home-events.js (zonedTimeToUTC) and home-news.js (homeNewsItems)
 * loaded first. Entry point: window.NetSec.renderHomeNow({ container,
 * locale, now }). `now` (ms) forces a date, for testing a state.
 */
(function () {
  'use strict';

  const NS = window.NetSec = window.NetSec || {};
  const DAY = 86400000;
  // Beyond this a relative date ("in 258 days") reads worse than the date.
  const RELATIVE_LIMIT_DAYS = 30;
  const T = (s) => (window.netsecT && window.netsecT(s)) || s;

  function pick(obj, locale) {
    if (!obj) return '';
    if (typeof obj === 'string') return obj;
    return obj[locale] || obj.en || '';
  }

  // Pure selection, exported for scripts/test-home-now.mjs.
  function pickNow(eventsData, newsData, nowMs) {
    const tzid = (eventsData && eventsData.tzid) || 'Europe/Stockholm';
    const ms = (local, tz) => {
      const d = NS.zonedTimeToUTC(local, tz || tzid);
      return d ? d.getTime() : NaN;
    };
    const timed = ((eventsData && eventsData.events) || [])
      .map((ev) => ({ ev, start: ms(ev.start, ev.tzid), end: ms(ev.end || ev.start, ev.tzid) }))
      .filter((x) => !isNaN(x.start) && !isNaN(x.end));
    const live = timed.filter((x) => x.start <= nowMs && nowMs <= x.end).sort((a, b) => a.end - b.end)[0];
    const next = timed.filter((x) => x.start > nowMs).sort((a, b) => a.start - b.start)[0];
    const last = timed.filter((x) => x.end < nowMs).sort((a, b) => b.end - a.end)[0];
    let event = null;
    if (live) event = Object.assign({ state: 'live' }, live);
    else if (next) event = Object.assign({ state: next.ev.status === 'TENTATIVE' ? 'tentative' : 'next' }, next);
    else if (last) event = Object.assign({ state: 'recent' }, last);

    const items = NS.homeNewsItems(newsData, nowMs);
    const closes = (it) => (it.homeUntil ? Date.parse(it.homeUntil) : Infinity);
    const calls = items.filter((it) => it.type === 'call')
      .sort((a, b) => closes(a) - closes(b)).slice(0, 2);
    const latest = items.find((it) => it.type !== 'call') || null;
    return { event, calls, latest };
  }

  function el(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function link(cls, href, text, external) {
    const a = el('a', cls, text);
    a.href = href;
    if (external) { a.target = '_blank'; a.rel = 'noopener'; }
    return a;
  }

  function tile(state, eyebrow) {
    const t = el('article', 'now-tile glass');
    t.dataset.state = state;
    const e = el('p', 'now-eyebrow');
    const dot = el('span', 'now-dot');
    dot.setAttribute('aria-hidden', 'true');
    e.append(dot, eyebrow);
    t.append(e);
    return t;
  }

  function eventTile(x, locale, nowMs) {
    const ev = x.ev;
    const eyebrows = { live: 'Happening now', next: 'Next up', tentative: 'Save the date', recent: 'Most recent' };
    let eyebrow = T(eyebrows[x.state]);
    const days = Math.ceil((x.start - nowMs) / DAY);
    if ((x.state === 'next' || x.state === 'tentative') && days <= RELATIVE_LIMIT_DAYS) {
      eyebrow += ' · ' + new Intl.RelativeTimeFormat(locale, { numeric: 'auto' }).format(days, 'day');
    }
    const t = tile(x.state, eyebrow);
    const title = pick(ev.cardTitle, locale) || ev.summary;
    const cta = ev.cta || {};
    const href = pick(cta.href, locale) || ev.url;
    const h = el('h3', 'now-title');
    if (href) {
      t.classList.add('card-clickable');
      h.append(link('card-stretch', href, title, cta.external));
    } else {
      h.textContent = title;
    }
    t.append(h);
    const detail = [pick(ev.displayDate, locale), pick(ev.cardLocation, locale)].filter(Boolean).join(' · ');
    if (detail) t.append(el('p', 'now-detail', detail));
    return t;
  }

  function callsTile(calls, locale, nowMs, localHref) {
    const t = tile(calls.length ? 'open' : 'none', T('Open calls'));
    if (!calls.length) {
      t.append(el('p', 'now-detail', T('No open calls right now.')));
      t.append(link('now-more', localHref('grants.html'), T('See the grants') + ' →'));
      return t;
    }
    const list = el('ul', 'now-list');
    calls.forEach((it) => {
      const li = el('li');
      const cta = it.cta || {};
      const href = pick(cta.href, locale) || localHref('news.html') + '#news-' + it.id;
      li.append(link('now-call', href, pick(it.title, locale), cta.external));
      let when = T('Rolling applications');
      if (it.homeUntil) {
        const end = Date.parse(it.homeUntil);
        const days = Math.ceil((end - nowMs) / DAY);
        when = days <= RELATIVE_LIMIT_DAYS
          ? T('Closes') + ' ' + new Intl.RelativeTimeFormat(locale, { numeric: 'auto' }).format(days, 'day')
          : T('Closes on') + ' ' + new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'long' }).format(end);
      }
      li.append(el('span', 'now-detail', when));
      list.append(li);
    });
    t.append(list);
    return t;
  }

  function latestTile(it, locale, localHref) {
    const t = tile('latest', T('Latest'));
    const h = el('h3', 'now-title');
    t.classList.add('card-clickable');
    h.append(link('card-stretch', localHref('news.html') + '#news-' + it.id, pick(it.title, locale)));
    t.append(h);
    const date = pick(it.displayDate, locale);
    if (date) t.append(el('p', 'now-detail', date));
    return t;
  }

  async function renderHomeNow(opts) {
    opts = opts || {};
    const root = document.querySelector(opts.container || '[data-home-now]');
    const grid = root && root.querySelector('[data-home-now-grid]');
    if (!grid || !NS.zonedTimeToUTC || !NS.homeNewsItems) return;
    const locale = (opts.locale || 'en').toLowerCase();
    const localHref = (path) => (locale === 'en' ? path : path.replace(/\.html$/, '.' + locale + '.html'));
    const get = (url) => fetch(url, { cache: 'no-cache' }).then((r) => {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
    let events, news;
    try {
      [events, news] = await Promise.all([get('data/events.json'), get('data/news.json')]);
    } catch (e) {
      // Additive section: a failed fetch leaves it hidden.
      console.debug('home-now: fetch failed, row stays hidden.', e);
      return;
    }
    const nowMs = opts.now || Date.now();
    const picked = pickNow(events, news, nowMs);
    const tiles = [];
    if (picked.event) tiles.push(eventTile(picked.event, locale, nowMs));
    tiles.push(callsTile(picked.calls, locale, nowMs, localHref));
    if (picked.latest) tiles.push(latestTile(picked.latest, locale, localHref));
    grid.replaceChildren(...tiles);
    root.hidden = false;
  }

  NS.pickNow = pickNow;
  NS.renderHomeNow = renderHomeNow;
})();
