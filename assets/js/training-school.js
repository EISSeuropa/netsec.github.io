/* NetSec Training School — editions renderer (shared EN/FR/DE).
 *
 * Renderer-light: reads data/training-school.json and fills two mount
 * points on summer-school.html (+ FR + DE):
 *   #ts-next-call  — the forward-looking edition (status announced/call-open).
 *                    The Add-to-calendar link shows only when the edition
 *                    carries a real `start` date; an announced-but-undated
 *                    edition (location/dates "To be announced") shows the
 *                    holding state with no calendar.
 *   #ts-editions   — the archive of past editions (newest first): dates,
 *                    host, cohort, coordinators (member-linked), topics, and
 *                    a photo gallery that silently omits any image not yet on
 *                    disk.
 * The rich prose (About, Taking part, heritage) stays hand-authored in the
 * page. Fail-soft: a missing or malformed data file leaves the static
 * fallback copy in the mount points untouched.
 */
(function () {
  'use strict';

  const nextRoot = document.getElementById('ts-next-call');
  const edRoot = document.getElementById('ts-editions');
  if (!nextRoot && !edRoot) return;

  const lang = (document.documentElement.lang || 'en').slice(0, 2);
  const I18N = {
    en: {
      nextCall: 'Next edition', toBeAnnounced: 'To be announced',
      location: 'Location', dates: 'Dates', deadline: 'Application deadline',
      addToCalendar: 'Add to calendar', pastEditions: 'Past editions',
      coordinators: 'Scientific coordinators', topics: 'Topics covered',
      funded: 'funded participants', notifyLede: 'Sign up to hear when the next call opens.',
    },
    fr: {
      nextCall: 'Prochaine édition', toBeAnnounced: 'À annoncer',
      location: 'Lieu', dates: 'Dates', deadline: 'Date limite de candidature',
      addToCalendar: 'Ajouter au calendrier', pastEditions: 'Éditions passées',
      coordinators: 'Coordination scientifique', topics: 'Thèmes abordés',
      funded: 'participant·es financé·es', notifyLede: 'Inscrivez-vous pour être informé·e de l’ouverture du prochain appel.',
    },
    de: {
      nextCall: 'Nächste Ausgabe', toBeAnnounced: 'Wird noch bekanntgegeben',
      location: 'Ort', dates: 'Termine', deadline: 'Bewerbungsfrist',
      addToCalendar: 'Zum Kalender hinzufügen', pastEditions: 'Frühere Ausgaben',
      coordinators: 'Wissenschaftliche Koordination', topics: 'Behandelte Themen',
      funded: 'geförderte Teilnehmende', notifyLede: 'Tragen Sie sich ein, um zu erfahren, wann der nächste Aufruf öffnet.',
    },
  };
  const t = I18N[lang] || I18N.en;
  const peopleUrl = lang === 'fr' ? 'people.fr.html' : lang === 'de' ? 'people.de.html' : 'people.html';

  function el(tag, attrs, ...kids) {
    const n = document.createElement(tag);
    if (attrs) for (const k in attrs) {
      if (k === 'class') n.className = attrs[k];
      else if (attrs[k] != null) n.setAttribute(k, attrs[k]);
    }
    for (const kid of kids) if (kid != null) n.append(kid.nodeType ? kid : document.createTextNode(kid));
    return n;
  }

  function defRow(label, value) {
    return el('div', { class: 'ts-deflist-row' },
      el('span', { class: 'ts-deflist-label' }, label),
      el('span', { class: 'ts-deflist-value' }, value));
  }

  function gallery(photos) {
    if (!photos || !photos.length) return null;
    const grid = el('div', { class: 'ts-gallery' });
    for (const p of photos) {
      if (!p || !p.src) continue;
      const img = el('img', { class: 'ts-gallery-img', src: p.src, alt: p.alt || '', loading: 'lazy', decoding: 'async' });
      // A photo not yet added to the repo drops out silently rather than
      // showing a broken-image icon.
      img.addEventListener('error', function () { const li = img.closest('.ts-gallery-item'); if (li) li.remove(); });
      grid.appendChild(el('figure', { class: 'ts-gallery-item' }, img));
    }
    return grid.children.length ? grid : null;
  }

  function coordinatorLine(coords) {
    if (!coords || !coords.length) return null;
    const wrap = el('p', { class: 'ts-edition-coords' }, el('span', { class: 'ts-edition-coords-label' }, t.coordinators + ': '));
    coords.forEach((c, i) => {
      if (i) wrap.append(document.createTextNode(', '));
      const label = c.affiliation ? `${c.name} (${c.affiliation})` : c.name;
      if (c.member_id) {
        wrap.append(el('a', { class: 'member-link', href: peopleUrl + '#' + c.member_id, 'data-member': c.member_id }, label));
      } else {
        wrap.append(document.createTextNode(label));
      }
    });
    return wrap;
  }

  function renderNextCall(ed) {
    if (!nextRoot || !ed) return;
    nextRoot.replaceChildren();
    const card = el('div', { class: 'ts-next-card glass' });
    card.append(el('p', { class: 'ts-next-eyebrow' }, t.nextCall));
    card.append(el('h3', { class: 'ts-next-year' }, String(ed.year)));
    const dl = el('div', { class: 'ts-deflist' });
    dl.append(defRow(t.location, ed.city && ed.city !== 'To be announced' ? (ed.host ? `${ed.host}, ${ed.city}` : ed.city) : t.toBeAnnounced));
    dl.append(defRow(t.dates, ed.dates && ed.dates !== 'To be announced' ? ed.dates : t.toBeAnnounced));
    if (ed.deadline) dl.append(defRow(t.deadline, ed.deadline));
    card.append(dl);
    if (ed.summary) card.append(el('p', { class: 'ts-next-summary' }, ed.summary));
    // Calendar only when a real start date is set (an announced, dated edition).
    if (ed.start && ed.ics) {
      card.append(el('a', { class: 'btn btn-ghost ts-next-cal', href: 'calendar/' + ed.ics + '.ics' }, t.addToCalendar));
    } else {
      card.append(el('p', { class: 'ts-next-notify' }, t.notifyLede));
    }
    nextRoot.appendChild(card);
  }

  function renderEditions(eds) {
    if (!edRoot || !eds.length) return;
    edRoot.replaceChildren();
    edRoot.append(el('h2', null, t.pastEditions));
    for (const ed of eds) {
      const card = el('article', { class: 'ts-edition glass' });
      card.append(el('header', { class: 'ts-edition-head' },
        el('h3', { class: 'ts-edition-year' }, String(ed.year)),
        el('span', { class: 'ts-edition-where' }, ed.host ? `${ed.host}, ${ed.city}` : ed.city)));
      const meta = el('p', { class: 'ts-edition-meta' });
      meta.append(ed.dates);
      if (ed.cohort) meta.append(` · ${ed.cohort} ${t.funded}`);
      card.append(meta);
      if (ed.summary) card.append(el('p', { class: 'ts-edition-summary' }, ed.summary));
      const co = coordinatorLine(ed.coordinators);
      if (co) card.append(co);
      if (ed.topics && ed.topics.length) {
        card.append(el('p', { class: 'ts-edition-topics-label' }, t.topics + ':'));
        const ul = el('ul', { class: 'ts-edition-topics' });
        for (const top of ed.topics) ul.append(el('li', null, top));
        card.append(ul);
      }
      const g = gallery(ed.photos);
      if (g) card.append(g);
      edRoot.appendChild(card);
    }
  }

  fetch('data/training-school.json', { cache: 'no-cache' })
    .then((r) => r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status)))
    .then((data) => {
      const eds = (data && data.editions) || [];
      const forward = eds.find((e) => e.status === 'call-open' || e.status === 'announced');
      const past = eds.filter((e) => e.status === 'past').sort((a, b) => b.year - a.year);
      if (forward) renderNextCall(forward);
      renderEditions(past);
    })
    .catch((err) => { console.warn('training-school.json fetch failed; static fallback kept:', err); });
})();
