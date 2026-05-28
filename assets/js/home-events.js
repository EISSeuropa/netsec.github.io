/* Home-page events renderer (#249).
 *
 * Pulls `data/events.json`, picks the locale from <html lang>, and
 * builds one .event-card per event into a target container. The
 * hand-coded HTML inside that container is wiped on success and
 * survives as a fail-soft fallback if the fetch or the parse fails.
 *
 * Each card carries:
 *  - a date pill + an event-type pill (locale-aware)
 *  - the localised title + description
 *  - up to four meta rows, each with an inline SVG icon
 *  - a five-line clamp on the description with a Read more affordance
 *    that's only rendered when the text actually overflows
 *  - an optional CTA link (the existing per-event link, e.g.
 *    Summer School → eiss-europa or ESSC → /essc-2026.html)
 *  - an Add to calendar dropdown with four destinations:
 *      • Google Calendar (prefilled template URL)
 *      • Outlook (web) compose deep-link
 *      • Apple webcal:// subscription
 *      • Direct .ics download from /calendar/<slug>.ics
 *
 * Entry point: window.NetSec.renderHomeEvents({ container, locale }).
 * The home pages invoke this from a small inline <script> at the
 * bottom of the page.
 */
(function () {
  'use strict';

  // ─── Static i18n strings ───────────────────────────────────────
  const I18N = {
    en: {
      type: {
        'training-school':    'Training School',
        'annual-conference':  'Annual Conference',
        'policy-workshop':    'Policy Workshop',
        'itc-conference':     'ITC Conference',
        'mc-plenary':         'MC Plenary',
      },
      readMore:        'Read more',
      readLess:        'Show less',
      addToCalendar:   'Add to calendar',
      atcGoogle:       'Google Calendar',
      atcOutlook:      'Outlook',
      atcApple:        'Apple Calendar (webcal)',
      atcDownload:     'Download .ics',
    },
    fr: {
      type: {
        'training-school':    'École de formation',
        'annual-conference':  'Conférence annuelle',
        'policy-workshop':    'Atelier politique',
        'itc-conference':     'Conférence ITC',
        'mc-plenary':         'Plénière du CG',
      },
      readMore:        'Lire la suite',
      readLess:        'Réduire',
      addToCalendar:   'Ajouter au calendrier',
      atcGoogle:       'Google Agenda',
      atcOutlook:      'Outlook',
      atcApple:        'Apple Calendar (webcal)',
      atcDownload:     'Télécharger le .ics',
    },
    de: {
      type: {
        'training-school':    'Ausbildungsschule',
        'annual-conference':  'Jahreskonferenz',
        'policy-workshop':    'Politik-Workshop',
        'itc-conference':     'ITC-Konferenz',
        'mc-plenary':         'MC-Plenum',
      },
      readMore:        'Mehr anzeigen',
      readLess:        'Weniger anzeigen',
      addToCalendar:   'Zum Kalender hinzufügen',
      atcGoogle:       'Google Kalender',
      atcOutlook:      'Outlook',
      atcApple:        'Apple Kalender (webcal)',
      atcDownload:     '.ics herunterladen',
    },
  };

  // ─── Inline icon SVGs (shared with the hand-coded fallback) ────
  const ICONS = {
    pin: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>',
    clock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>',
    people: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 00-3-3.87M4 21v-2a4 4 0 013-3.87M16 3.13a4 4 0 010 7.75M8 3.13a4 4 0 000 7.75"/></svg>',
    calendar: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>',
  };

  // ─── Helpers ───────────────────────────────────────────────────

  /** Resolve a localised field with EN fallback. */
  function pickLocale(obj, locale, fallback) {
    if (!obj) return fallback;
    if (typeof obj === 'string') return obj;
    return obj[locale] || obj.en || fallback;
  }

  /** Slug from UID: 'summer-school-2026@netsec-cost.eu' → 'summer-school-2026'. */
  function slugFromUid(uid) {
    return (uid || '').split('@')[0];
  }

  /* Time-zone resolution (#260).
   *
   * Event start/end strings in events.json carry no offset
   * ('2026-06-09T09:00'); they are wall-clock times in the event's
   * IANA zone. Earlier this file hard-coded '+02:00', which is right
   * for Stockholm summer time but silently wrong for any event in
   * winter (CET, +01:00) or in another zone. We now resolve the real
   * offset for each wall-clock instant via Intl.DateTimeFormat, so
   * the Google and Outlook URLs land on the correct UTC time year
   * round. The .ics downloads were always correct (they ship a
   * VTIMEZONE block), so only the two inline-URL builders changed.
   *
   * TZID is lifted from events.json at render time (top-level `tzid`,
   * with an optional per-event `ev.tzid` override); this constant is
   * the fallback when the data omits it.
   */
  const DEFAULT_TZID = 'Europe/Stockholm';
  let TZID = DEFAULT_TZID;

  /**
   * Offset in minutes (positive = ahead of UTC) that the given IANA
   * zone applies at the supplied UTC instant.
   */
  function tzOffsetMinutes(date, tz) {
    const dtf = new Intl.DateTimeFormat('en-US', {
      timeZone: tz, hour12: false,
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    });
    const map = {};
    dtf.formatToParts(date).forEach(p => { map[p.type] = p.value; });
    // Some engines render midnight as hour '24'; normalise to 0.
    const hour = map.hour === '24' ? 0 : +map.hour;
    const asUTC = Date.UTC(
      +map.year, +map.month - 1, +map.day,
      hour, +map.minute, +map.second
    );
    return Math.round((asUTC - date.getTime()) / 60000);
  }

  /** '+02:00' / '-05:30' style offset string from a minute count. */
  function offsetString(mins) {
    const sign = mins >= 0 ? '+' : '-';
    const abs = Math.abs(mins);
    const hh = String(Math.floor(abs / 60)).padStart(2, '0');
    const mm = String(abs % 60).padStart(2, '0');
    return sign + hh + ':' + mm;
  }

  /**
   * Turn a zone-local wall-clock string ('2026-06-09T09:00') into the
   * UTC Date it denotes in the given IANA zone. Two-pass to stay
   * correct across a DST transition within the same day.
   */
  function zonedTimeToUTC(local, tz) {
    const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(local || '');
    if (!m) return null;
    const asUTC = Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0));
    const off1 = tzOffsetMinutes(new Date(asUTC), tz);
    let utc = asUTC - off1 * 60000;
    const off2 = tzOffsetMinutes(new Date(utc), tz);
    if (off2 !== off1) utc = asUTC - off2 * 60000;
    return new Date(utc);
  }

  /**
   * Convert an event's zone-local time into a UTC `YYYYMMDDTHHmmssZ`
   * stamp suitable for Google Calendar URLs.
   */
  function toUTCStamp(local, tz) {
    const d = zonedTimeToUTC(local, tz || TZID);
    if (!d || isNaN(d.getTime())) return '';
    const y = d.getUTCFullYear();
    const m = String(d.getUTCMonth() + 1).padStart(2, '0');
    const day = String(d.getUTCDate()).padStart(2, '0');
    const hh = String(d.getUTCHours()).padStart(2, '0');
    const mm = String(d.getUTCMinutes()).padStart(2, '0');
    return `${y}${m}${day}T${hh}${mm}00Z`;
  }

  /** ISO 8601 with the zone's actual offset (Outlook web compose expects this). */
  function toISOLocal(local, tz) {
    const zone = tz || TZID;
    const d = zonedTimeToUTC(local, zone);
    if (!d) return local;
    return local + ':00' + offsetString(tzOffsetMinutes(d, zone));
  }

  /** Build the four Add-to-calendar URLs for one event. */
  function buildATCUrls(ev, locale) {
    const slug = slugFromUid(ev.uid);
    const title = pickLocale(ev.cardTitle, locale, ev.summary);
    const desc = pickLocale(ev.cardDescription, locale, ev.description);
    const loc = ev.location || '';
    const tz = ev.tzid || TZID;
    const startUTC = toUTCStamp(ev.start, tz);
    const endUTC = toUTCStamp(ev.end, tz);
    const startISO = toISOLocal(ev.start, tz);
    const endISO = toISOLocal(ev.end, tz);
    const enc = encodeURIComponent;

    const google = 'https://www.google.com/calendar/render'
      + '?action=TEMPLATE'
      + '&text=' + enc(title)
      + '&dates=' + startUTC + '/' + endUTC
      + '&details=' + enc(desc)
      + '&location=' + enc(loc);

    const outlook = 'https://outlook.live.com/calendar/0/deeplink/compose'
      + '?path=%2Fcalendar%2Faction%2Fcompose'
      + '&rru=addevent'
      + '&subject=' + enc(title)
      + '&startdt=' + enc(startISO)
      + '&enddt=' + enc(endISO)
      + '&body=' + enc(desc)
      + '&location=' + enc(loc);

    // Production webcal must use absolute host; locally we keep a path.
    const host = location.host === 'netsec-cost.eu'
      ? 'netsec-cost.eu'
      : location.host;
    const webcal = 'webcal://' + host + '/calendar/' + slug + '.ics';
    const download = '/calendar/' + slug + '.ics';

    return { google, outlook, webcal, download };
  }

  /** DOM-builder helper. */
  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    if (attrs) {
      for (const k in attrs) {
        if (k === 'class') node.className = attrs[k];
        else if (k === 'html') node.innerHTML = attrs[k];
        else if (k.startsWith('on') && typeof attrs[k] === 'function') {
          node.addEventListener(k.slice(2), attrs[k]);
        } else if (attrs[k] != null) {
          node.setAttribute(k, attrs[k]);
        }
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

  // ─── ATC dropdown wiring ───────────────────────────────────────

  function buildAtcDropdown(ev, locale, t) {
    const urls = buildATCUrls(ev, locale);
    const slug = slugFromUid(ev.uid);
    const menuId = 'atc-menu-' + slug;

    const trigger = el('button', {
      type: 'button',
      class: 'event-atc-trigger',
      'aria-haspopup': 'menu',
      'aria-expanded': 'false',
      'aria-controls': menuId,
    }, [
      // Reuse the calendar icon
      (function () {
        const wrap = document.createElement('span');
        wrap.innerHTML = ICONS.calendar;
        wrap.classList.add('event-atc-icon');
        return wrap;
      })(),
      document.createTextNode(' ' + t.addToCalendar + ' '),
      (function () {
        const chev = document.createElement('span');
        chev.className = 'event-atc-chev';
        chev.setAttribute('aria-hidden', 'true');
        chev.textContent = '▾';
        return chev;
      })(),
    ]);

    const mkItem = (href, label, attrs) => el('a', Object.assign({
      class: 'event-atc-item',
      href: href,
      role: 'menuitem',
    }, attrs || {}), [label]);

    const menu = el('div', {
      class: 'event-atc-menu',
      id: menuId,
      role: 'menu',
      hidden: '',
    }, [
      mkItem(urls.google,   t.atcGoogle,   { target: '_blank', rel: 'noopener' }),
      mkItem(urls.outlook,  t.atcOutlook,  { target: '_blank', rel: 'noopener' }),
      mkItem(urls.webcal,   t.atcApple,    { rel: 'alternate', type: 'text/calendar' }),
      mkItem(urls.download, t.atcDownload, { download: '' }),
    ]);

    // The .event-card carries `.glass` → `backdrop-filter`, which
    // creates a new stacking context. A z-indexed absolute child
    // (the menu) is trapped inside that context, so the NEXT card's
    // own stacking context can occlude it. To escape every parent
    // stacking context cleanly we reparent the menu to <body> on
    // open and pin it with `position: fixed` against the trigger's
    // bounding rect. Mirrors the essc-2026 member-preview popover
    // pattern.
    menu.classList.add('event-atc-menu--portal');

    function position() {
      const r = trigger.getBoundingClientRect();
      const vw = document.documentElement.clientWidth;
      const gap = 6;
      // Right-align the menu to the trigger; the menu is at most
      // ~240 px wide. Clamp so it never overflows the viewport.
      menu.style.position = 'fixed';
      menu.style.top = (r.bottom + gap) + 'px';
      // First read the menu's own width post-attach to right-align.
      const menuW = menu.offsetWidth || 220;
      let left = r.right - menuW;
      if (left < 8) left = 8;
      if (left + menuW > vw - 8) left = vw - menuW - 8;
      menu.style.left = left + 'px';
      menu.style.right = 'auto';
    }
    function close() {
      menu.hidden = true;
      trigger.setAttribute('aria-expanded', 'false');
    }
    function open() {
      // Reparent on first open; subsequent opens are no-ops because
      // the body parent persists across toggles.
      if (menu.parentElement !== document.body) {
        document.body.appendChild(menu);
      }
      menu.hidden = false;
      position();
      trigger.setAttribute('aria-expanded', 'true');
    }
    function toggle() {
      if (menu.hidden) open();
      else close();
    }

    trigger.addEventListener('click', e => {
      e.stopPropagation();
      toggle();
    });
    // Outside-click + Escape dismiss. menu.contains() still works
    // after the body reparent.
    document.addEventListener('click', e => {
      if (!menu.hidden && !menu.contains(e.target) && e.target !== trigger
          && !trigger.contains(e.target)) close();
    });
    document.addEventListener('keydown', e => {
      if (!menu.hidden && e.key === 'Escape') {
        close();
        trigger.focus();
      }
    });
    // Re-anchor on scroll / resize so the menu tracks the trigger
    // (the trigger moves with the page; the menu is viewport-fixed).
    // Cheap to just close — matches the existing popover dismissal
    // pattern elsewhere in the site and avoids reflow churn.
    window.addEventListener('scroll', () => { if (!menu.hidden) close(); }, true);
    window.addEventListener('resize', () => { if (!menu.hidden) close(); });

    const wrap = el('div', { class: 'event-atc' }, [trigger, menu]);
    return wrap;
  }

  // ─── Card builder ──────────────────────────────────────────────

  function buildCard(ev, locale, t) {
    const isFeatured = !!ev.featured;
    const card = el('article', {
      class: 'event-card glass' + (isFeatured ? ' featured' : ''),
      'data-event-uid': ev.uid,
    });

    const dateLabel = pickLocale(ev.displayDate, locale, '');
    if (dateLabel) {
      card.appendChild(el('span', { class: 'event-date' }, [dateLabel]));
    }

    const typeLabel = (t.type && t.type[ev.eventType]) || ev.eventType || '';
    if (typeLabel) {
      card.appendChild(el('span', { class: 'event-type' }, [typeLabel]));
    }

    const title = pickLocale(ev.cardTitle, locale, ev.summary);
    card.appendChild(el('h3', null, [title]));

    // Description with 5-line clamp + Read more
    const desc = pickLocale(ev.cardDescription, locale, ev.description);
    const para = el('p', { class: 'event-desc event-desc--clamped' }, [desc]);
    card.appendChild(para);

    // Clamp detection: defer to after layout so we can measure overflow
    // accurately. We add a Read-more button only if the rendered height
    // is taller than the clamp.
    requestAnimationFrame(() => {
      if (para.scrollHeight > para.clientHeight + 1) {
        const btn = el('button', {
          type: 'button',
          class: 'event-desc-toggle',
          'aria-expanded': 'false',
        }, [t.readMore]);
        btn.addEventListener('click', () => {
          const expanded = btn.getAttribute('aria-expanded') === 'true';
          if (expanded) {
            para.classList.add('event-desc--clamped');
            btn.setAttribute('aria-expanded', 'false');
            btn.textContent = t.readMore;
          } else {
            para.classList.remove('event-desc--clamped');
            btn.setAttribute('aria-expanded', 'true');
            btn.textContent = t.readLess;
          }
        });
        para.insertAdjacentElement('afterend', btn);
      }
    });

    // Meta rows
    if (ev.meta && ev.meta.length) {
      const metaWrap = el('div', { class: 'event-meta' });
      ev.meta.forEach(row => {
        const iconHTML = ICONS[row.icon] || ICONS.calendar;
        const text = pickLocale(row.i18n, locale, '');
        const rowEl = el('div', { class: 'event-meta-row' });
        // Inject inline SVG via innerHTML to mirror the hand-coded shape
        const iconWrap = document.createElement('span');
        iconWrap.className = 'event-meta-icon';
        iconWrap.innerHTML = iconHTML;
        rowEl.appendChild(iconWrap.firstElementChild);
        // Text body — allow inline HTML (the JSON carries <strong> and <a>)
        const textNode = el('span', { html: text });
        rowEl.appendChild(textNode);
        metaWrap.appendChild(rowEl);
      });
      card.appendChild(metaWrap);
    }

    // CTAs row: optional event-link + ATC dropdown
    const ctasRow = el('div', { class: 'event-card-ctas' });

    if (ev.cta && ev.cta.href) {
      const href = typeof ev.cta.href === 'string'
        ? ev.cta.href
        : pickLocale(ev.cta.href, locale, '');
      const label = pickLocale(ev.cta.i18n, locale, '');
      const attrs = { class: 'event-link', href };
      if (ev.cta.external) {
        attrs.target = '_blank';
        attrs.rel = 'noopener';
      }
      ctasRow.appendChild(el('a', attrs, [label]));
    }

    ctasRow.appendChild(buildAtcDropdown(ev, locale, t));
    card.appendChild(ctasRow);

    return card;
  }

  // ─── Public entry point ────────────────────────────────────────

  async function renderHomeEvents(opts) {
    const container = typeof opts.container === 'string'
      ? document.querySelector(opts.container)
      : opts.container;
    if (!container) return;
    const locale = (opts.locale || 'en').toLowerCase();
    const t = I18N[locale] || I18N.en;

    let data;
    try {
      const res = await fetch(opts.source || 'data/events.json', { cache: 'no-cache' });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      data = await res.json();
    } catch (e) {
      // Fail-soft: leave the hand-coded fallback HTML in place.
      console.debug('home-events: fetch failed, keeping fallback HTML.', e);
      return;
    }

    // Lift the calendar time zone from the feed so the Add-to-calendar
    // URLs resolve the correct UTC offset for each event's wall-clock
    // time (#260). Per-event `ev.tzid` still overrides this in buildATCUrls.
    TZID = (data && data.tzid) || DEFAULT_TZID;

    const events = Array.isArray(data && data.events) ? data.events : [];
    if (!events.length) return;

    // Render off-DOM first, then swap to avoid a flash.
    const frag = document.createDocumentFragment();
    events.forEach(ev => frag.appendChild(buildCard(ev, locale, t)));
    container.innerHTML = '';
    container.appendChild(frag);
    container.dataset.renderedFromJson = '1';
  }

  window.NetSec = window.NetSec || {};
  window.NetSec.renderHomeEvents = renderHomeEvents;
})();
