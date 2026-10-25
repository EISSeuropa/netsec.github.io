/* Weekly member spotlight on the home page (issue #341).
 *
 * Reads data/spotlight.json (rotation state, written weekly by
 * scripts/rotate-spotlight.py) and data/bios.json (the member data),
 * and renders one member into #member-spotlight. Stays hidden unless
 * the spotlight is active AND the featured member is still eligible
 * (has a photo and a bio), so the block self-heals if a member leaves
 * or the pool drops below the activation threshold. Any error leaves
 * the section hidden: it is purely additive, never blocks the page.
 *
 * Locale comes from <html lang>; only the chrome translates, the bio
 * is shown as the member wrote it.
 */
(function () {
  'use strict';

  var section = document.getElementById('member-spotlight');
  if (!section) return;

  var lang = (document.documentElement.lang || 'en').toLowerCase().slice(0, 2);
  var T = {
    en: { eyebrow: 'Community', title: 'Member spotlight', view: 'View full profile →',
          action: 'In the Action', lead: 'Leader', coLead: 'Co-leader', member: 'Member' },
    fr: { eyebrow: 'Communauté', title: 'Coup de projecteur sur un membre', view: 'Voir le profil complet →',
          action: "Dans l'Action", lead: 'Responsable', coLead: 'Co-responsable', member: 'Membre' },
    de: { eyebrow: 'Gemeinschaft', title: 'Mitglied im Fokus', view: 'Vollständiges Profil ansehen →',
          action: 'In der Action', lead: 'Leitung', coLead: 'Co-Leitung', member: 'Mitglied' }
  };
  var t = T[lang] || T.en;
  var peopleUrl = lang === 'fr' ? 'people.fr.html' : lang === 'de' ? 'people.de.html' : 'people.html';

  function el(tag, attrs, kids) {
    var n = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === 'class') n.className = attrs[k];
      else if (k === 'text') n.textContent = attrs[k];
      else n.setAttribute(k, attrs[k]);
    });
    (kids || []).forEach(function (c) { if (c) n.appendChild(c); });
    return n;
  }

  function eligible(m) {
    return m && (m.photo || '').trim() && (m.bio || '').trim();
  }

  // Avatar initials + theme-chip title-casing are the shared sitewide
  // helpers from site.js (#1194), which loads before this file on every
  // page (defer scripts run in document order).
  var initials = window.netsecInitials;
  var titlecaseTheme = window.netsecTitlecaseTheme;
  var tr = function (s) { return (window.netsecT && window.netsecT(s)) || s; };
  var WG_NAMES = { 1: 'Building the Network', 2: 'Transfer of Knowledge',
    3: 'Fostering the Next Generation of Scholars', 4: 'Inclusion, Representativeness & Ethics' };

  // The member's place in the Action: one row per Working Group with their
  // role in it, then any role outside the WGs (coordinator, MC seat). WG
  // leadership comes from wg_leadership, so the "WG2 Leader" role labels
  // are skipped to avoid listing it twice.
  function actionRoles(member) {
    var lead = (member.wg_leadership || {});
    var role = {};
    (member.wgs || []).forEach(function (w) { role[w] = t.member; });
    (lead.co_lead || []).forEach(function (w) { role[w] = t.coLead; });
    (lead.lead || []).forEach(function (w) { role[w] = t.lead; });
    var rows = Object.keys(role).sort().map(function (w) {
      return el('li', { class: 'spotlight-action-row' }, [
        el('span', { class: 'spotlight-action-tag', style: 'background:var(--wg-' + w + ');color:var(--wg-' + w + '-ink)', text: 'WG' + w }),
        el('span', { class: 'spotlight-action-text' }, [
          el('span', { class: 'spotlight-action-name', text: tr(WG_NAMES[w] || '') }),
          el('span', { class: 'spotlight-action-role', text: role[w] })
        ])
      ]);
    });
    (member.roles || []).filter(function (r) { return !/^WG\d/.test(r); }).forEach(function (r) {
      rows.push(el('li', { class: 'spotlight-action-row spotlight-action-other', text: tr(r) }));
    });
    if (!rows.length) return null;
    return el('aside', { class: 'spotlight-action', 'aria-label': t.action }, [
      el('p', { class: 'spotlight-action-title', text: t.action }),
      el('ul', { class: 'spotlight-action-list' }, rows)
    ]);
  }

  function flag(cc) {
    cc = (cc || '').toLowerCase();
    if (!/^[a-z]{2}$/.test(cc)) return '';
    return String.fromCodePoint(0x1F1E6 + (cc.charCodeAt(0) - 97)) +
           String.fromCodePoint(0x1F1E6 + (cc.charCodeAt(1) - 97));
  }

  function render(member) {
    var photo;
    if ((member.photo || '').trim()) {
      photo = el('img', { src: member.photo, alt: '', loading: 'lazy', decoding: 'async' });
    } else {
      photo = el('span', { class: 'spotlight-initials', 'aria-hidden': 'true', text: initials(member.name) });
    }

    var metaBits = [];
    if (member.position) metaBits.push(member.position);
    if (member.affiliation) metaBits.push(member.affiliation);
    var country = [flag(member.country_code), member.country].filter(Boolean).join(' ');
    if (country) metaBits.push(country);

    var chips = el('div', { class: 'spotlight-keywords' });
    (member.canonical_keywords || []).slice(0, 4).forEach(function (k) {
      chips.appendChild(el('span', { class: 'spotlight-chip', text: titlecaseTheme(k) }));
    });

    var body = el('div', { class: 'spotlight-body' }, [
      el('h3', { class: 'spotlight-name', text: member.name || '' }),
      metaBits.length ? el('p', { class: 'spotlight-role', text: metaBits.join(' · ') }) : null,
      member.bio ? el('p', { class: 'spotlight-bio', text: member.bio }) : null,
      (member.canonical_keywords || []).length ? chips : null,
      el('a', { class: 'btn btn-ghost spotlight-cta', href: peopleUrl + '#' + member.id, text: t.view })
    ]);

    var card = el('article', { class: 'spotlight-card glass' }, [
      el('div', { class: 'spotlight-photo' }, [photo]),
      body,
      actionRoles(member)
    ]);

    var head = el('h3', { class: 'spotlight-heading', id: 'spotlight-title', text: t.title });

    var container = section.querySelector('.container') || section;
    container.innerHTML = '';
    container.appendChild(head);
    container.appendChild(card);
    section.hidden = false;
  }

  Promise.all([
    fetch('data/spotlight.json', { cache: 'no-cache' }).then(function (r) { return r.ok ? r.json() : null; }),
    fetch('data/bios.json', { cache: 'no-cache' }).then(function (r) { return r.ok ? r.json() : null; })
  ]).then(function (res) {
    var state = res[0], bios = res[1];
    if (!state || !bios || !state.active || !state.current) return;   // dormant
    var member = (bios.members || []).filter(function (m) { return m.id === state.current; })[0];
    if (!eligible(member)) return;                                     // self-heal
    render(member);
  }).catch(function (err) {
    if (window.console) console.warn('[home-spotlight] skipped:', err);
  });
})();
