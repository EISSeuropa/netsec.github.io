/* Working Groups page renderer.
 *
 * Reads data/wg.json (per-WG leadership + members, synced from cost.eu
 * by scripts/sync-cost.py) and data/bios.json (each member's photo,
 * role, and affiliation), then fills the leadership and member grids in
 * each #wg{1..4} section. Fail-soft: on any error the static fallback
 * already in the page markup is left in place. Same render-from-JSON
 * contract as assets/js/home-events.js / home-spotlight.js.
 */
(function () {
  'use strict';

  var I18N = {
    en: { lead: 'Lead', coLead: 'Co-lead' },
    fr: { lead: 'Responsable', coLead: 'Co-responsable' },
    de: { lead: 'Leitung', coLead: 'Co-Leitung' },
  };
  var locale = (document.documentElement.lang || 'en').slice(0, 2);
  var t = I18N[locale] || I18N.en;

  function el(tag, attrs) {
    var n = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === 'text') n.textContent = attrs[k];
      else if (k === 'html') n.innerHTML = attrs[k];
      else n.setAttribute(k, attrs[k]);
    });
    for (var i = 2; i < arguments.length; i++) {
      var c = arguments[i];
      if (c == null) continue;
      n.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
    }
    return n;
  }

  function initials(name) {
    var parts = (name || '').replace(/^(Dr|Prof|Mr|Ms|Mrs)\.?\s+/i, '').trim().split(/\s+/);
    var a = (parts[0] || '')[0] || '';
    var b = (parts.length > 1 ? parts[parts.length - 1] : '')[0] || '';
    return (a + b).toUpperCase();
  }

  // A member with a directory bio gets a photo, their affiliation, and
  // a link to their card (which auto-expands on arrival). A member with
  // only the cost.eu record gets an initials avatar, their name, and
  // their country, as a non-interactive card.
  function memberCard(entry, bio, roleLabel) {
    var name = (bio && bio.name) || entry.name || '';
    var slug = entry.slug || (bio && bio.id) || '';
    var avatar = (bio && bio.photo)
      ? el('div', { class: 'mc-avatar' },
          el('img', { src: bio.photo, alt: name, loading: 'lazy' }))
      : el('div', { class: 'mc-avatar mc-avatar--initials', 'aria-hidden': 'true' },
          initials(name));
    var sub = roleLabel
      ? null
      : ((bio && (bio.position || bio.affiliation)) || entry.country || '');
    var kids = [
      avatar,
      roleLabel ? el('div', { class: 'role', text: roleLabel }) : null,
      el('h4', { text: name }),
      sub ? el('p', { class: 'org', text: sub }) : null,
    ];
    if (slug) {
      return el.apply(null, ['a', {
        class: 'mc-card glass wg-member-card',
        href: 'people.' + (locale === 'en' ? '' : locale + '.') + 'html#' + slug,
      }].concat(kids));
    }
    return el.apply(null, ['div', {
      class: 'mc-card glass wg-member-card wg-member-card--plain',
    }].concat(kids));
  }

  Promise.all([
    fetch('data/wg.json').then(function (r) { return r.json(); }),
    fetch('data/bios.json').then(function (r) { return r.json(); }),
  ]).then(function (res) {
    var wg = res[0], bios = res[1];
    var bySlug = {};
    (bios.members || []).forEach(function (m) { bySlug[m.id] = m; });

    (wg.groups || []).forEach(function (g) {
      var sec = document.getElementById('wg' + g.number);
      if (!sec) return;

      var leadWrap = sec.querySelector('[data-wg-leadership]');
      if (leadWrap) {
        leadWrap.innerHTML = '';
        if (g.lead) leadWrap.appendChild(memberCard(g.lead, bySlug[g.lead.slug], t.lead));
        if (g.coLead) leadWrap.appendChild(memberCard(g.coLead, bySlug[g.coLead.slug], t.coLead));
      }

      var grid = sec.querySelector('[data-wg-member-grid]');
      if (grid) {
        grid.innerHTML = '';
        (g.members || []).forEach(function (m) {
          grid.appendChild(memberCard(m, bySlug[m.slug], null));
        });
      }

      var countEl = sec.querySelector('[data-wg-count]');
      if (countEl) countEl.textContent = String(g.memberCount);

      // If a WG has no members at all, hide the expander entirely.
      var details = sec.querySelector('[data-wg-members]');
      if (details && !(g.members || []).length) details.hidden = true;
    });
  }).catch(function (e) {
    if (window.console && console.debug) console.debug('WG render skipped:', e);
  });
})();
