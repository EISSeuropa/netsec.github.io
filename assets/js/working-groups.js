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
    en: { lead: 'Lead', coLead: 'Co-lead',
          people: 'people', countries: 'countries', groups: 'Working Groups',
          events: 'Related events',
          types: { 'training-school': 'Training School', 'annual-conference': 'Annual Conference',
                   'policy-workshop': 'Policy Workshop', 'itc-conference': 'ITC Conference',
                   'mc-plenary': 'MC Plenary' } },
    fr: { lead: 'Responsable', coLead: 'Co-responsable',
          people: 'personnes', countries: 'pays représentés', groups: 'groupes de travail',
          events: 'Événements liés',
          types: { 'training-school': 'École de formation', 'annual-conference': 'Conférence annuelle',
                   'policy-workshop': 'Atelier politique', 'itc-conference': 'Conférence ITC',
                   'mc-plenary': 'Plénière du CG' } },
    de: { lead: 'Leitung', coLead: 'Co-Leitung',
          people: 'Personen', countries: 'vertretene Länder', groups: 'Arbeitsgruppen',
          events: 'Verwandte Veranstaltungen',
          types: { 'training-school': 'Ausbildungsschule', 'annual-conference': 'Jahreskonferenz',
                   'policy-workshop': 'Politik-Workshop', 'itc-conference': 'ITC-Konferenz',
                   'mc-plenary': 'MC-Plenum' } },
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
    // Members all show their country, so the bio'd and non-bio cards
    // read consistently (a bio's position/affiliation fields are not
    // uniformly populated, which made some cards show a university and
    // others a job title). Leaders show their role instead.
    var sub = roleLabel
      ? null
      : (entry.country || (bio && (bio.position || bio.affiliation)) || '');
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

  // Resolve a possibly-localised field: {en,fr,de} → the current locale,
  // a plain string → itself.
  function localize(v) {
    if (v && typeof v === 'object' && !(v instanceof Array)) return v[locale] || v.en || '';
    return v || '';
  }

  // A compact card for an event tagged with this Working Group. Date
  // chip + type tag + title, the whole card linking to the event.
  function wgEventCard(ev) {
    var href = localize(ev.cta && ev.cta.href) || ev.url || '#';
    var typeLabel = (t.types && t.types[ev.eventType])
      || (ev.categories && ev.categories[0]) || '';
    var attrs = { 'class': 'wg-event-card glass', 'href': href };
    if (ev.cta && ev.cta.external) { attrs.target = '_blank'; attrs.rel = 'noopener'; }
    return el('a', attrs,
      typeLabel ? el('span', { 'class': 'wg-event-type', 'text': typeLabel }) : null,
      el('h4', { 'text': localize(ev.cardTitle) || ev.summary || '' }),
      el('span', { 'class': 'wg-event-date', 'text': localize(ev.displayDate) + ' →' })
    );
  }

  Promise.all([
    fetch('data/wg.json').then(function (r) { return r.json(); }),
    fetch('data/bios.json').then(function (r) { return r.json(); }),
    // Events are an optional enhancement: a failure here must not take
    // down the core leadership / member render, so swallow it to null.
    fetch('data/events.json').then(function (r) { return r.json(); })
      .catch(function () { return null; }),
  ]).then(function (res) {
    var wg = res[0], bios = res[1];
    var allEvents = (res[2] && res[2].events) || [];
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

      // Related events: any event tagged with this group's number in
      // data/events.json. One event can belong to several WGs, so it
      // appears under each without duplication in the data.
      var evWrap = sec.querySelector('[data-wg-events]');
      if (evWrap) {
        var groupEvents = allEvents.filter(function (ev) {
          return (ev.workingGroups || []).indexOf(g.number) !== -1;
        });
        if (groupEvents.length) {
          evWrap.innerHTML = '';
          evWrap.appendChild(el('h3', { 'class': 'wg-subhead', 'text': t.events }));
          var evGrid = el('div', { 'class': 'wg-event-grid' });
          groupEvents.forEach(function (ev) { evGrid.appendChild(wgEventCard(ev)); });
          evWrap.appendChild(evGrid);
          evWrap.hidden = false;
        }
      }
    });

    // Overall stats across all four groups: unique people (members plus
    // leads and co-leads, de-duplicated by name since cost.eu lists a
    // person under every WG they belong to) and the countries they come
    // from. Computed client-side from the same dataset, so it tracks the
    // weekly cost.eu sync with no extra maintenance.
    var statsEl = document.querySelector('[data-wg-stats]');
    if (statsEl) {
      var nameKey = function (n) {
        return (n || '').toLowerCase()
          .replace(/^(dr|prof|mr|ms|mrs|mme|m|pr)\.?\s+/, '').trim();
      };
      var people = {}, countries = {};
      (wg.groups || []).forEach(function (g) {
        [g.lead, g.coLead].forEach(function (L) {
          if (L && L.name) people[nameKey(L.name)] = 1;
        });
        (g.members || []).forEach(function (m) {
          if (m.name) people[nameKey(m.name)] = 1;
          if (m.country) countries[m.country] = 1;
        });
      });
      var stats = [
        { n: Object.keys(people).length, label: t.people },
        { n: Object.keys(countries).length, label: t.countries },
        { n: (wg.groups || []).length, label: t.groups },
      ];
      statsEl.innerHTML = '';
      stats.forEach(function (s) {
        statsEl.appendChild(el('div', { class: 'wg-stat' },
          el('span', { class: 'wg-stat-n', text: String(s.n) }),
          el('span', { class: 'wg-stat-l', text: s.label })));
      });
      statsEl.hidden = false;
    }
  }).catch(function (e) {
    if (window.console && console.debug) console.debug('WG render skipped:', e);
  });
})();
