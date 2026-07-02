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
          claim: 'Is this you? Add your profile',
          events: 'Related events',
          pubs: 'Related publications',
          pubsEmpty: 'First publications expected October 2026.',
          pubsAll: 'See all publications',
          types: { 'training-school': 'Training School', 'annual-conference': 'Annual Conference',
                   'policy-workshop': 'Policy Workshop', 'itc-conference': 'ITC Conference',
                   'mc-plenary': 'MC Plenary' },
          pubTypes: { 'policy-brief': 'Policy brief', 'article': 'Peer-reviewed article',
                   'report': 'Report', 'training-material': 'Training material', 'dataset': 'Dataset' } },
    fr: { lead: 'Responsable', coLead: 'Co-responsable',
          people: 'personnes', countries: 'pays représentés', groups: 'groupes de travail',
          claim: 'Est-ce vous ? Ajoutez votre profil',
          events: 'Événements liés',
          pubs: 'Publications liées',
          pubsEmpty: 'Premières publications attendues en octobre 2026.',
          pubsAll: 'Voir toutes les publications',
          types: { 'training-school': 'École de formation', 'annual-conference': 'Conférence annuelle',
                   'policy-workshop': 'Atelier politique', 'itc-conference': 'Conférence ITC',
                   'mc-plenary': 'Plénière du CG' },
          pubTypes: { 'policy-brief': 'Note de politique', 'article': 'Article évalué par les pairs',
                   'report': 'Rapport', 'training-material': 'Matériel de formation', 'dataset': 'Jeu de données' } },
    de: { lead: 'Leitung', coLead: 'Co-Leitung',
          people: 'Personen', countries: 'vertretene Länder', groups: 'Arbeitsgruppen',
          claim: 'Sind das Sie? Profil hinzufügen',
          events: 'Verwandte Veranstaltungen',
          pubs: 'Verwandte Veröffentlichungen',
          pubsEmpty: 'Erste Veröffentlichungen werden für Oktober 2026 erwartet.',
          pubsAll: 'Alle Veröffentlichungen ansehen',
          types: { 'training-school': 'Ausbildungsschule', 'annual-conference': 'Jahreskonferenz',
                   'policy-workshop': 'Politik-Workshop', 'itc-conference': 'ITC-Konferenz',
                   'mc-plenary': 'MC-Plenum' },
          pubTypes: { 'policy-brief': 'Policy Brief', 'article': 'Begutachteter Artikel',
                   'report': 'Bericht', 'training-material': 'Schulungsmaterial', 'dataset': 'Datensatz' } },
  };
  var locale = (document.documentElement.lang || 'en').slice(0, 2);
  var t = I18N[locale] || I18N.en;

  // The join-form URL, read from bios.json's source block once the data
  // loads. Held at module scope so memberCard() can append the
  // claim-your-profile CTA to bio-less cards without threading the URL
  // through every call site.
  var formUrl = '';

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

  // Shared sitewide avatar-initials rule from site.js (#1194), which
  // loads before this file (defer scripts run in document order).
  var initials = window.netsecInitials;

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
    // A bio-less card is the directory's highest-intent conversion
    // surface: the person is named on the site but has no profile yet.
    // Offer a quiet link to the join form so they can claim their card.
    // Leadership cards (roleLabel set) are skipped: a lead or co-lead
    // without a bio is a sync gap, not a recruitment prospect.
    if (formUrl && !roleLabel) {
      kids.push(el('a', {
        class: 'wg-claim-cta',
        href: formUrl,
        target: '_blank',
        rel: 'noopener',
        text: t.claim,
      }));
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

  // A compact card for a publication tagged with this Working Group.
  // Type tag + title + a meta line (authors, formatted date). Links out
  // when a URL is present, otherwise renders as a plain (not-yet-public)
  // card. Date is an ISO year-month string ("2026-10").
  function wgPubCard(pub) {
    var typeLabel = (t.pubTypes && t.pubTypes[pub.type]) || '';
    var bits = [];
    if (pub.authors && pub.authors.length) {
      bits.push(pub.authors.length > 2
        ? pub.authors[0] + ' et al.'
        : pub.authors.join(', '));
    }
    if (pub.date) {
      var p = String(pub.date).split('-');
      var d = p.length > 1
        ? new Date(Date.UTC(+p[0], +p[1] - 1, 1)).toLocaleDateString(
            locale, { year: 'numeric', month: 'long' })
        : p[0];
      bits.push(d);
    }
    var title = localize(pub.title) || '';
    var kids = [
      typeLabel ? el('span', { 'class': 'wg-pub-type', 'text': typeLabel }) : null,
      el('h4', { 'text': title }),
      bits.length ? el('span', { 'class': 'wg-pub-meta', 'text': bits.join(' · ') }) : null,
    ];
    if (pub.url) {
      return el.apply(null, ['a', {
        'class': 'wg-pub-card glass', 'href': pub.url,
        'target': '_blank', 'rel': 'noopener',
      }].concat(kids));
    }
    return el.apply(null, ['div', { 'class': 'wg-pub-card glass wg-pub-card--plain' }].concat(kids));
  }

  Promise.all([
    fetch('data/wg.json').then(function (r) { return r.json(); }),
    fetch('data/bios.json').then(function (r) { return r.json(); }),
    // Events are an optional enhancement: a failure here must not take
    // down the core leadership / member render, so swallow it to null.
    fetch('data/events.json').then(function (r) { return r.json(); })
      .catch(function () { return null; }),
    // Publications likewise optional: swallow to null on any error.
    fetch('data/publications.json').then(function (r) { return r.json(); })
      .catch(function () { return null; }),
  ]).then(function (res) {
    var wg = res[0], bios = res[1];
    var allEvents = (res[2] && res[2].events) || [];
    var allPubs = (res[3] && res[3].publications) || [];
    formUrl = (bios.source && bios.source.form_url) || '';
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

      // Related publications: outputs tagged with this group's number in
      // data/publications.json. The heading shows whether or not any
      // exist yet; with none, a placeholder sets the expectation and
      // links to the outputs page, which the same data file will drive
      // once outputs start landing (first ones scheduled October 2026).
      var pubWrap = sec.querySelector('[data-wg-publications]');
      if (pubWrap) {
        var groupPubs = allPubs.filter(function (p) {
          return (p.workingGroups || []).indexOf(g.number) !== -1;
        }).sort(function (a, b) {
          return String(b.date || '').localeCompare(String(a.date || ''));
        });
        pubWrap.innerHTML = '';
        pubWrap.appendChild(el('h3', { 'class': 'wg-subhead', 'text': t.pubs }));
        var outputsHref = 'outputs.' + (locale === 'en' ? '' : locale + '.') + 'html';
        if (groupPubs.length) {
          var pubGrid = el('div', { 'class': 'wg-pub-grid' });
          groupPubs.forEach(function (p) { pubGrid.appendChild(wgPubCard(p)); });
          pubWrap.appendChild(pubGrid);
          pubWrap.appendChild(el('a', { 'class': 'wg-pub-all', 'href': outputsHref },
            t.pubsAll, el('span', { 'aria-hidden': 'true', 'text': ' →' })));
        } else {
          pubWrap.appendChild(el('p', { 'class': 'wg-pub-empty' },
            t.pubsEmpty + ' ',
            el('a', { 'href': outputsHref }, t.pubsAll,
              el('span', { 'aria-hidden': 'true', 'text': ' →' }))));
        }
        pubWrap.hidden = false;
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

    // A deep-link from another page (e.g. the home Working-Groups cards
    // linking to #wg2) is scrolled to by the browser before this async
    // render runs. The events, publications, and member content injected
    // above then changes the page height, leaving the target mis-aligned
    // under or below the header. Re-apply the scroll once everything is
    // in place. scroll-padding-top, kept in step with the fixed header by
    // site.js, supplies the correct offset.
    if (location.hash.length > 1) {
      var deepId;
      try { deepId = decodeURIComponent(location.hash.slice(1)); } catch (_) { deepId = ''; }
      var deepTarget = deepId && document.getElementById(deepId);
      // The content above was injected synchronously, so layout is
      // already final; scrollIntoView honours scroll-padding-top.
      if (deepTarget) deepTarget.scrollIntoView();
    }
  }).catch(function (e) {
    if (window.console && console.debug) console.debug('WG render skipped:', e);
  });
})();
