/* Outputs page: publications list rendered from data/publications.json.
 *
 * Built ahead of the first D6 policy briefs (October 2026) so that
 * publishing an output is a data entry task, not a page rebuild
 * (issue #726). One shared file serves the EN/FR/DE outputs pages;
 * the locale comes from <html lang>.
 *
 * Behaviour:
 *   - While data/publications.json holds no entries, this script does
 *     nothing and the static empty-state copy in the page stays up.
 *   - Once entries exist, the empty-state is hidden and the list
 *     renders newest-first, reusing the wg-pub-card styles the
 *     Working Groups page already ships.
 *   - Author names that match a directory member (same nameKey
 *     first|last matching the faculty and leadership cards use) link
 *     to their profile on the people page (issue #693).
 *
 * Schema lives in the _documentation block of data/publications.json.
 * Silent no-op on fetch error: the static empty-state remains.
 */
(function () {
  'use strict';

  var I18N = {
    en: {
      types: { 'policy-brief': 'Policy brief', 'article': 'Peer-reviewed article',
               'report': 'Report', 'training-material': 'Training material', 'dataset': 'Dataset' },
      deliverable: 'Deliverable',
      openAccess: 'Open access',
    },
    fr: {
      types: { 'policy-brief': 'Note de politique', 'article': 'Article évalué par les pairs',
               'report': 'Rapport', 'training-material': 'Matériel de formation', 'dataset': 'Jeu de données' },
      deliverable: 'Livrable',
      openAccess: 'Accès ouvert',
    },
    de: {
      types: { 'policy-brief': 'Policy Brief', 'article': 'Begutachteter Artikel',
               'report': 'Bericht', 'training-material': 'Schulungsmaterial', 'dataset': 'Datensatz' },
      deliverable: 'Deliverable',
      openAccess: 'Open Access',
    },
  };
  var locale = (document.documentElement.lang || 'en').slice(0, 2);
  var t = I18N[locale] || I18N.en;
  var peopleUrl = locale === 'fr' ? 'people.fr.html' : locale === 'de' ? 'people.de.html' : 'people.html';

  var root = document.getElementById('publications-list');
  if (!root) return;

  function el(tag, attrs) {
    var node = document.createElement(tag);
    for (var k in (attrs || {})) {
      if (k === 'class') node.className = attrs[k];
      else if (k === 'text') node.textContent = attrs[k];
      else node.setAttribute(k, attrs[k]);
    }
    for (var i = 2; i < arguments.length; i++) {
      var c = arguments[i];
      if (c == null) continue;
      node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
    }
    return node;
  }

  function localize(v) {
    if (v && typeof v === 'object') return v[locale] || v.en || '';
    return v || '';
  }

  // Same first|last keying as the faculty / leadership card matchers in
  // site.js, so author links self-heal as people join the directory.
  var POSTNOMINALS = { phd: 1, jr: 1, sr: 1, ii: 1, iii: 1, iv: 1, esq: 1 };
  var PARTICLES = {
    de: 1, del: 1, della: 1, di: 1, da: 1, das: 1, dos: 1,
    van: 1, von: 1, vom: 1, der: 1, den: 1, ter: 1, ten: 1,
    la: 1, le: 1, el: 1, al: 1, ibn: 1, bin: 1, bint: 1, zu: 1, auf: 1, af: 1,
  };
  function nameKey(name) {
    if (!name) return null;
    var s = name.normalize('NFKD').replace(/[̀-ͯ]/g, '');
    s = s.replace(/^(Dr|Prof|Mr|Ms|Mrs)\.?\s+/i, '');
    s = s.replace(/[‘’ʼ'`]/g, '');
    var tokens = s.split(/[^A-Za-z]+/).filter(Boolean).map(function (x) { return x.toLowerCase(); });
    var real = tokens.filter(function (x) { return !POSTNOMINALS[x] && !PARTICLES[x]; });
    if (real.length < 2) return null;
    return real[0] + '|' + real[real.length - 1];
  }

  function formatDate(d) {
    var p = String(d || '').split('-');
    if (p.length > 1) {
      return new Date(Date.UTC(+p[0], +p[1] - 1, 1))
        .toLocaleDateString(locale, { year: 'numeric', month: 'long' });
    }
    return p[0] || '';
  }

  function authorNodes(authors, byKey) {
    var nodes = [];
    (authors || []).forEach(function (name, i) {
      if (i > 0) nodes.push(', ');
      var m = byKey.get(nameKey(name));
      nodes.push(m
        ? el('a', { 'class': 'pub-author-link', href: peopleUrl + '#' + m.id }, name)
        : name);
    });
    return nodes;
  }

  function pubCard(pub, byKey) {
    var typeLabel = t.types[pub.type] || '';
    var meta = [];
    if (pub.date) meta.push(formatDate(pub.date));
    if (pub.deliverable) meta.push(t.deliverable + ' ' + pub.deliverable);

    var title = localize(pub.title);
    var href = pub.url || (pub.doi ? 'https://doi.org/' + pub.doi : '');
    var titleNode = href
      ? el('a', { href: href, target: '_blank', rel: 'noopener' }, title)
      : document.createTextNode(title);

    var card = el('article', { 'class': 'wg-pub-card glass' },
      typeLabel ? el('span', { 'class': 'wg-pub-type', text: typeLabel }) : null,
      el('h3', {}, titleNode),
      (pub.authors && pub.authors.length)
        ? el.apply(null, ['p', { 'class': 'wg-pub-meta pub-authors' }].concat(authorNodes(pub.authors, byKey)))
        : null,
      meta.length ? el('span', { 'class': 'wg-pub-meta', text: meta.join(' · ') }) : null
    );
    return card;
  }

  Promise.all([
    fetch('data/publications.json').then(function (r) { return r.json(); }),
    fetch('data/bios.json').then(function (r) { return r.json(); }).catch(function () { return null; }),
  ]).then(function (res) {
    var pubs = (res[0] && res[0].publications) || [];
    if (!pubs.length) return;   // static empty-state stays up

    var byKey = new Map();
    (((res[1]) && res[1].members) || []).forEach(function (m) {
      var add = function (raw) {
        var k = nameKey(raw);
        if (k && m.id && !byKey.has(k)) byKey.set(k, m);
      };
      add(m.name);
      (m.name_aliases || []).forEach(add);
    });

    pubs.sort(function (a, b) {
      return String(b.date || '').localeCompare(String(a.date || ''));
    });

    var grid = el('div', { 'class': 'wg-pub-grid' });
    pubs.forEach(function (p) { grid.appendChild(pubCard(p, byKey)); });

    var empty = document.querySelector('.empty-state');
    if (empty) empty.hidden = true;
    root.innerHTML = '';
    root.appendChild(grid);
    root.hidden = false;
  }).catch(function (err) {
    console.warn('outputs: publications.json fetch failed; empty-state kept:', err);
  });
})();
