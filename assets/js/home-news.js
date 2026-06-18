/* Home-page news renderer (v1.9.0 — parallel to home-events.js / #249).
 *
 * Pulls `data/news.json`, picks the locale from <html lang>, and
 * builds one .news-card per item into a target container. The
 * hand-coded HTML inside that container is wiped on success and
 * survives as a fail-soft fallback if the fetch or parse fails.
 *
 * News items are sorted newest first (by `pubDate`). Each card
 * carries: a date / status pill, the localised title, the localised
 * body, and an optional CTA link.
 *
 * Entry point: window.NetSec.renderHomeNews({ container, locale }).
 */
(function () {
  'use strict';

  function pickLocale(obj, locale, fallback) {
    if (!obj) return fallback;
    if (typeof obj === 'string') return obj;
    return obj[locale] || obj.en || fallback;
  }

  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    if (attrs) {
      for (const k in attrs) {
        if (k === 'class') node.className = attrs[k];
        else if (k === 'html') node.innerHTML = attrs[k];
        else if (attrs[k] != null) node.setAttribute(k, attrs[k]);
      }
    }
    (children || []).forEach(child => {
      if (child == null) return;
      node.appendChild(typeof child === 'string'
        ? document.createTextNode(child)
        : child);
    });
    return node;
  }

  function buildCard(item, locale) {
    // Whole-card click target (stretched-link) when the item has a CTA;
    // CTA-less news items stay non-clickable with no hover affordance.
    const hasCta = !!(item.cta && item.cta.href);
    const card = el('article', {
      class: 'news-card glass' + (hasCta ? ' card-clickable' : ''),
      'data-news-id': item.id,
    });
    const dateLabel = pickLocale(item.displayDate, locale, '');
    if (dateLabel) {
      card.appendChild(el('span', { class: 'news-date' }, [dateLabel]));
    }
    const title = pickLocale(item.title, locale, '');
    card.appendChild(el('h3', null, [title]));
    const body = pickLocale(item.body, locale, '');
    card.appendChild(el('p', null, [body]));
    if (item.cta && item.cta.href) {
      const href = typeof item.cta.href === 'string'
        ? item.cta.href
        : pickLocale(item.cta.href, locale, '');
      const label = pickLocale(item.cta.i18n, locale, '');
      // card-stretch: overlay this CTA over the whole card (see the
      // .card-clickable utility in site.css).
      const attrs = { class: 'card-stretch', href };
      if (item.cta.external) {
        attrs.target = '_blank';
        attrs.rel = 'noopener';
      }
      card.appendChild(el('a', attrs, [label]));
    }
    return card;
  }

  // The home block shows at most this many items, and only those still
  // within the decay window. Older items drop off the home page but stay
  // on the /news archive, which renders the full list.
  const HOME_MAX = 4;
  const DECAY_MONTHS = 18;

  function sortedItems(data) {
    const items = Array.isArray(data && data.items) ? data.items.slice() : [];
    // Newest first (descending by ISO pubDate).
    items.sort((a, b) => (b.pubDate || '').localeCompare(a.pubDate || ''));
    return items;
  }

  function withinDecay(item, now) {
    if (!item.pubDate) return true; // undated items never decay off
    const t = Date.parse(item.pubDate);
    if (isNaN(t)) return true;
    const cutoff = new Date(now);
    cutoff.setMonth(cutoff.getMonth() - DECAY_MONTHS);
    return t >= cutoff.getTime();
  }

  async function fetchNews(source) {
    const res = await fetch(source || 'data/news.json', { cache: 'no-cache' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return res.json();
  }

  function resolveContainer(opts) {
    return typeof opts.container === 'string'
      ? document.querySelector(opts.container)
      : opts.container;
  }

  // Home "Latest" block: the most recent, non-decayed items, capped.
  // Hides its whole section when nothing qualifies (e.g. all decayed).
  async function renderHomeNews(opts) {
    const container = resolveContainer(opts);
    if (!container) return;
    const locale = (opts.locale || 'en').toLowerCase();

    let data;
    try {
      data = await fetchNews(opts.source);
    } catch (e) {
      // Fail-soft: leave the hand-coded fallback HTML in place.
      console.debug('home-news: fetch failed, keeping fallback HTML.', e);
      return;
    }

    const now = Date.now();
    const items = sortedItems(data).filter(it => withinDecay(it, now)).slice(0, HOME_MAX);
    const section = container.closest('section');
    if (!items.length) {
      if (section) section.hidden = true;
      return;
    }
    const frag = document.createDocumentFragment();
    items.forEach(item => frag.appendChild(buildCard(item, locale)));
    container.innerHTML = '';
    container.appendChild(frag);
    container.dataset.renderedFromJson = '1';
  }

  // /news archive: the full chronological list, newest first, each card
  // carrying an `id` anchor so an item can be deep-linked. No decay, no
  // cap. Leaves the no-JS fallback in place on fetch failure.
  async function renderNewsArchive(opts) {
    const container = resolveContainer(opts);
    if (!container) return;
    const locale = (opts.locale || 'en').toLowerCase();

    let data;
    try {
      data = await fetchNews(opts.source);
    } catch (e) {
      console.debug('news-archive: fetch failed, keeping fallback HTML.', e);
      return;
    }

    const items = sortedItems(data);
    if (!items.length) return; // keep the "archive is empty" fallback
    const frag = document.createDocumentFragment();
    items.forEach(item => {
      const card = buildCard(item, locale);
      if (item.id) card.id = 'news-' + item.id;
      frag.appendChild(card);
    });
    container.innerHTML = '';
    container.appendChild(frag);
    container.dataset.renderedFromJson = '1';
  }

  window.NetSec = window.NetSec || {};
  window.NetSec.renderHomeNews = renderHomeNews;
  window.NetSec.renderNewsArchive = renderNewsArchive;
})();
