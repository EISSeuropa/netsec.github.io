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

  async function renderHomeNews(opts) {
    const container = typeof opts.container === 'string'
      ? document.querySelector(opts.container)
      : opts.container;
    if (!container) return;
    const locale = (opts.locale || 'en').toLowerCase();

    let data;
    try {
      const res = await fetch(opts.source || 'data/news.json', { cache: 'no-cache' });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      data = await res.json();
    } catch (e) {
      // Fail-soft: leave the hand-coded fallback HTML in place.
      console.debug('home-news: fetch failed, keeping fallback HTML.', e);
      return;
    }

    const items = Array.isArray(data && data.items) ? data.items : [];
    if (!items.length) return;

    // Sort newest first (descending by ISO pubDate).
    items.sort((a, b) => (b.pubDate || '').localeCompare(a.pubDate || ''));

    const frag = document.createDocumentFragment();
    items.forEach(item => frag.appendChild(buildCard(item, locale)));
    container.innerHTML = '';
    container.appendChild(frag);
    container.dataset.renderedFromJson = '1';
  }

  window.NetSec = window.NetSec || {};
  window.NetSec.renderHomeNews = renderHomeNews;
})();
