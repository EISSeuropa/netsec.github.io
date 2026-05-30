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
    en: { lead: 'Lead', coLead: 'Co-lead', showAll: 'Show all members',
          hide: 'Hide members', more: 'more members without a profile yet' },
    fr: { lead: 'Responsable', coLead: 'Co-responsable',
          showAll: 'Voir tous les membres', hide: 'Masquer les membres',
          more: 'autres membres sans fiche pour le moment' },
    de: { lead: 'Leitung', coLead: 'Co-Leitung',
          showAll: 'Alle Mitglieder anzeigen', hide: 'Mitglieder ausblenden',
          more: 'weitere Mitglieder ohne Profil' },
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

  // A member card in the directory's visual language, linking to the
  // member's directory entry (which auto-expands the matching card).
  function memberCard(ref, bio, roleLabel) {
    var name = (bio && bio.name) || ref.name || '';
    var slug = ref.slug || (bio && bio.id) || '';
    var avatar;
    if (bio && bio.photo) {
      avatar = el('div', { class: 'mc-avatar' },
        el('img', { src: bio.photo, alt: name, loading: 'lazy' }));
    } else {
      avatar = el('div', { class: 'mc-avatar mc-avatar--initials', 'aria-hidden': 'true' },
        initials(name));
    }
    var sub = roleLabel || (bio && (bio.position || bio.affiliation)) || '';
    var card = el('a', {
      class: 'mc-card glass wg-member-card',
      href: 'people.' + (locale === 'en' ? '' : locale + '.') + 'html#' + slug,
    },
      avatar,
      roleLabel ? el('div', { class: 'role', text: roleLabel }) : null,
      el('h4', { text: name }),
      sub && !roleLabel ? el('p', { class: 'org', text: sub }) : null
    );
    return card;
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

      var moreEl = sec.querySelector('[data-wg-more]');
      if (moreEl) {
        if (g.membersWithoutProfile > 0) {
          moreEl.textContent = '+ ' + g.membersWithoutProfile + ' ' + t.more;
          moreEl.hidden = false;
        } else {
          moreEl.hidden = true;
        }
      }

      // If a WG has no bio'd members at all, hide the expander entirely.
      var details = sec.querySelector('[data-wg-members]');
      if (details && !(g.members || []).length && !(g.membersWithoutProfile > 0)) {
        details.hidden = true;
      }
    });
  }).catch(function (e) {
    if (window.console && console.debug) console.debug('WG render skipped:', e);
  });
})();
