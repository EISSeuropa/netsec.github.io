/* ESSC programme renderer (shared across the EN/FR/DE pages).
 *
 * Extracted from the inline scripts of essc-2026.html / .fr.html /
 * .de.html (issue #725): the three copies had already drifted, which
 * is exactly the failure class a single shared module removes. The
 * I18N table below carries all three locales and the script picks one
 * from <html lang>, so the locale pages need nothing beyond the
 * <script src> tag.
 *
 * Data flow: fetches data/indico.json (rewritten nightly by
 * sync-indico) + data/bios.json (weekly) + data/essc-livestream.json
 * (hand-maintained), then renders the programme grid into
 * #programme-root. See docs/indico-sync.md for the pipeline.
 */
(async function () {
  'use strict';

  const root       = document.getElementById('programme-root');
  const chips      = document.getElementById('programme-day-chips');
  const quickfacts = document.getElementById('essc-quickfacts');
  const tzNode     = document.getElementById('programme-tz');

  // Chrome strings keyed by document.documentElement.lang. Content
  // from Indico (session titles, speaker names, abstracts) stays in
  // whatever language the submitter wrote it in (typically English
  // for ESSC). Only the structural labels translate.
  const I18N = {
    en: {
      day: 'Day',
      chair: 'Chair', chairs: 'Chairs',
      discussants: 'Discussants', speakers: 'Speakers', speakerTag: 'Speaker',
      session: 'Session', plenary: 'Plenary', roundtable: 'Roundtable',
      contribution: 'contribution', contributions: 'contributions',
      readOnIndico: 'Read on Indico →',
      readFullAbstract: 'Read full abstract',
      showLess: 'Show less',
      livestream: 'Livestream',
      breakFallback: 'Break',
      livestreamAria: 'This session will be livestreamed',
      watchAria: 'Watch the livestream on Zoom (opens in a new tab)',
      liveNow: 'Live now',
      errLoad:   'Couldn’t load the live programme.',
      errFetch:  'Couldn’t fetch the programme data.',
      errAbsent: 'ESSC 2026 isn’t published yet.',
      errEmpty:  'The programme isn’t published yet.',
      readItOn:  'Read it on',
      viewFullProfile: 'View full profile →',
      memberCardLabel: 'Member preview',
      closeCard: 'Close preview',
      pdfLabel: 'Download programme (PDF)',
      pdfHint: 'The official conference programme.',
      pdfFile: 'assets/programme/eiss-2026-programme.pdf',
      wgPrefix: 'WG',
      iconEmail: 'Email', iconWebsite: 'Website', iconOrcid: 'ORCID iD',
      iconLinkedin: 'LinkedIn', iconTwitter: 'X',
      iconBluesky: 'Bluesky', iconMastodon: 'Mastodon',
    },
    fr: {
      day: 'Jour',
      chair: 'Présidence', chairs: 'Présidence',
      discussants: 'Discutant·es', speakers: 'Intervenant·es', speakerTag: 'Intervenant·e',
      session: 'Session', plenary: 'Plénière', roundtable: 'Table ronde',
      contribution: 'communication', contributions: 'communications',
      readOnIndico: 'Lire sur Indico →',
      readFullAbstract: 'Lire le résumé complet',
      showLess: 'Réduire',
      livestream: 'Diffusion directe',
      breakFallback: 'Pause',
      livestreamAria: 'Session diffusée en direct',
      watchAria: 'Regarder la diffusion en direct sur Zoom (nouvel onglet)',
      liveNow: 'En direct',
      errLoad:   'Impossible de charger le programme en direct.',
      errFetch:  'Impossible de récupérer les données du programme.',
      errAbsent: 'L’ESSC 2026 n’est pas encore publiée.',
      errEmpty:  'Le programme n’est pas encore publié.',
      readItOn:  'Voir sur',
      viewFullProfile: 'Voir le profil complet →',
      memberCardLabel: 'Aperçu du membre',
      closeCard: 'Fermer l’aperçu',
      pdfLabel: 'Télécharger le programme (PDF)',
      pdfHint: 'Le programme officiel de la conférence.',
      pdfFile: 'assets/programme/eiss-2026-programme.pdf',
      wgPrefix: 'GT',
      iconEmail: 'Courriel', iconWebsite: 'Site web', iconOrcid: 'ORCID iD',
      iconLinkedin: 'LinkedIn', iconTwitter: 'X',
      iconBluesky: 'Bluesky', iconMastodon: 'Mastodon',
    },
    de: {
      day: 'Tag',
      chair: 'Vorsitz', chairs: 'Vorsitz',
      discussants: 'Diskutierende', speakers: 'Vortragende', speakerTag: 'Vortragende·r',
      session: 'Sitzung', plenary: 'Plenum', roundtable: 'Podiumsdiskussion',
      contribution: 'Beitrag', contributions: 'Beiträge',
      readOnIndico: 'Auf Indico lesen →',
      readFullAbstract: 'Vollständige Zusammenfassung lesen',
      showLess: 'Weniger anzeigen',
      livestream: 'Livestream',
      breakFallback: 'Pause',
      livestreamAria: 'Diese Sitzung wird per Livestream übertragen',
      watchAria: 'Den Livestream auf Zoom ansehen (neuer Tab)',
      liveNow: 'Jetzt live',
      errLoad:   'Das Live-Programm konnte nicht geladen werden.',
      errFetch:  'Die Programmdaten konnten nicht abgerufen werden.',
      errAbsent: 'ESSC 2026 ist noch nicht veröffentlicht.',
      errEmpty:  'Das Programm ist noch nicht veröffentlicht.',
      readItOn:  'Lesen auf',
      viewFullProfile: 'Vollständiges Profil ansehen →',
      memberCardLabel: 'Mitgliedsvorschau',
      closeCard: 'Vorschau schließen',
      pdfLabel: 'Programm herunterladen (PDF)',
      pdfHint: 'Das offizielle Konferenzprogramm.',
      pdfFile: 'assets/programme/eiss-2026-programme.pdf',
      wgPrefix: 'AG',
      iconEmail: 'E-Mail', iconWebsite: 'Website', iconOrcid: 'ORCID iD',
      iconLinkedin: 'LinkedIn', iconTwitter: 'X',
      iconBluesky: 'Bluesky', iconMastodon: 'Mastodon',
    },
  };
  const lang = (document.documentElement.lang || 'en').toLowerCase().slice(0, 2);
  const t = I18N[lang] || I18N.en;
  const dateLocale =
    lang === 'fr' ? 'fr-FR' :
    lang === 'de' ? 'de-DE' :
                    'en-GB';
  // Where to send a reader who clicks a member's name in the programme.
  const peopleUrl =
    lang === 'fr' ? 'people.fr.html' :
    lang === 'de' ? 'people.de.html' :
                    'people.html';

  // ── Download-PDF button ───────────────────────────────────────
  // Hands over the official, tailored conference programme PDF
  // (provided by the EISS organisers), committed at
  // assets/programme/eiss-2026-programme.pdf. We link a ready-made file
  // rather than leaning on the visitor's browser print because Chrome's
  // interactive "Save as PDF" truncates the long programme mid-document
  // (a Chrome print-fragmentation defect; Safari prints it fine). The
  // button is injected here, alongside the day-chip/member-card setup,
  // and runs independently of the data fetch, so the download stays
  // available even if the live render fails.
  (function injectProgrammeDownload() {
    if (!chips || !chips.parentNode) return;
    const link = el('a', { class: 'programme-download', href: t.pdfFile, download: '' });
    const ns = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', '0 0 24 24'); svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', 'currentColor'); svg.setAttribute('stroke-width', '2');
    svg.setAttribute('stroke-linecap', 'round'); svg.setAttribute('stroke-linejoin', 'round');
    svg.setAttribute('aria-hidden', 'true');
    for (const d of ['M12 3v12', 'M7 10l5 5 5-5', 'M5 21h14']) {
      const p = document.createElementNS(ns, 'path'); p.setAttribute('d', d); svg.appendChild(p);
    }
    link.appendChild(svg);
    link.appendChild(el('span', { class: 'programme-download-label' }, t.pdfLabel));
    if (t.pdfHint) link.appendChild(el('span', { class: 'programme-download-hint' }, t.pdfHint));
    chips.parentNode.insertBefore(link, chips);
  })();

  function setError(msg) {
    root.dataset.state = 'error';
    root.innerHTML =
      '<p class="programme-error">' +
      t.errLoad + ' ' + msg + ' ' + t.readItOn + ' ' +
      '<a href="https://indico.eiss-europa.com/event/22/" target="_blank" rel="noopener">Indico</a>.' +
      '</p>';
    if (quickfacts) {
      quickfacts.dataset.state = 'error';
      quickfacts.setAttribute('aria-busy', 'false');
    }
  }

  // ── helpers ───────────────────────────────────────────────────
  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    if (attrs) for (const k in attrs) {
      if (k === 'class')        node.className = attrs[k];
      else if (k === 'text')    node.textContent = attrs[k];
      else if (k === 'html')    node.innerHTML = attrs[k];
      else if (k === 'dataset') Object.assign(node.dataset, attrs[k]);
      else if (k.startsWith('on') && typeof attrs[k] === 'function') node.addEventListener(k.slice(2), attrs[k]);
      else                      node.setAttribute(k, attrs[k]);
    }
    for (const c of children.flat()) {
      if (c == null || c === false) continue;
      node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
    }
    return node;
  }

  function formatDate(iso) {
    // "2026-06-11" → "Thursday 11 June 2026" (or the localised form)
    if (!iso || !/^\d{4}-\d{2}-\d{2}$/.test(iso)) return iso || '';
    const d = new Date(iso + 'T12:00:00');
    return d.toLocaleDateString(dateLocale, {
      weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
    });
  }

  function formatDateRange(startIso, endIso) {
    if (!startIso) return '';
    if (!endIso || startIso === endIso) return formatDate(startIso);
    // Compact form: "11–12 June 2026" when the month matches.
    const s = new Date(startIso + 'T12:00:00');
    const e = new Date(endIso   + 'T12:00:00');
    if (s.getMonth() === e.getMonth() && s.getFullYear() === e.getFullYear()) {
      const month = s.toLocaleDateString(dateLocale, { month: 'long' });
      const year  = s.getFullYear();
      return `${s.getDate()}–${e.getDate()} ${month} ${year}`;
    }
    return `${formatDate(startIso)} – ${formatDate(endIso)}`;
  }

  function subtypeLabel(subtype) {
    if (subtype === 'roundtable') return t.roundtable;
    if (subtype === 'plenary')    return t.plenary;
    return t.session;
  }

  // Mirror of scripts/sync-bios.py's name_key(): strip diacritics,
  // honorifics, post-nominals, particles, and apostrophes, then key
  // on the first + last surviving tokens. Lets us match an Indico
  // speaker record like "Dr Marie Robin" to a NetSec member record
  // "Marie Robin" without a manual mapping table.
  const NAME_POSTNOMINALS = new Set(['phd', 'jr', 'sr', 'ii', 'iii', 'iv', 'esq']);
  // Nobiliary / patronymic particles. Dropping these prevents
  // "Jéssica da Costa Pereira" from keying on "pereira" while a bios
  // entry "Jéssica da Costa" keys on "costa". Conservative list:
  // only reliable connectors, not tokens that could ever be a given
  // or surname on their own.
  const NAME_PARTICLES = new Set([
    'de', 'del', 'della', 'di', 'da', 'das', 'dos',
    'van', 'von', 'vom', 'der', 'den', 'ter', 'ten',
    'la', 'le', 'el', 'al', 'ibn', 'bin', 'bint',
    'zu', 'auf', 'af',
  ]);
  function nameKey(name) {
    if (!name) return null;
    let s = name.normalize('NFKD').replace(/[̀-ͯ]/g, '');
    s = s.replace(/^(Dr|Prof|Mr|Ms|Mrs)\.?\s+/i, '');
    s = s.replace(/[‘’ʼ'`]/g, '');
    const tokens = s.split(/[^A-Za-z]+/).filter(Boolean).map(t => t.toLowerCase());
    const real = tokens.filter(t => !NAME_POSTNOMINALS.has(t) && !NAME_PARTICLES.has(t));
    if (real.length < 2) return null;
    return real[0] + '|' + real[real.length - 1];
  }

  function buildMemberLookup(bios) {
    // One member can be reachable under several keys: the canonical
    // name on the bios entry plus any optional `name_aliases` (covers
    // nicknames, married/maiden, transliteration variants — anything
    // the algorithm can't see). Later aliases don't overwrite an
    // earlier match for the same key, so two members can't shadow
    // each other through colliding aliases by accident. The value
    // stored is the full bios record so the on-hover member card has
    // every field it needs without a second fetch.
    const map = new Map();
    const add = (rawName, member) => {
      const k = nameKey(rawName);
      if (k && member && member.id && !map.has(k)) map.set(k, member);
    };
    for (const m of (bios && bios.members || [])) {
      add(m.name, m);
      for (const alias of (m.name_aliases || [])) add(alias, m);
    }
    return map;
  }

  // ── fetch ─────────────────────────────────────────────────────
  let indico;
  try {
    const res = await fetch('data/indico.json', { cache: 'no-cache' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    indico = await res.json();
  } catch (err) {
    console.error('indico.json fetch failed:', err);
    setError(t.errFetch);
    return;
  }

  // Member lookup is best-effort: if bios.json can't be fetched, the
  // programme still renders, just without name → /people.html links.
  let memberLookup = new Map();
  try {
    const res = await fetch('data/bios.json', { cache: 'no-cache' });
    if (res.ok) memberLookup = buildMemberLookup(await res.json());
  } catch (err) {
    console.warn('bios.json fetch failed; speaker links disabled:', err);
  }
  // Names we couldn't match — surfaced via console.debug after render
  // so near-misses (typos, name-order flips, missing aliases) show up
  // during preview without bothering readers. Speakers like "TBD" and
  // anyone with only one token are filtered out: they're not real
  // candidates and would just create noise.
  const unmatchedSpeakers = new Set();

  // Livestream link for the conference, hand-maintained in
  // data/essc-livestream.json so it survives the daily Indico sync and can
  // be taken down by blanking the url. Best-effort: absent, malformed, or
  // outside [start, end] all mean no link renders.
  let liveStream = null;
  try {
    const lsRes = await fetch('data/essc-livestream.json', { cache: 'no-cache' });
    if (lsRes.ok) {
      const cfg = await lsRes.json();
      if (cfg && cfg.url) {
        const now = Date.now();
        const okStart = !cfg.start || new Date(cfg.start).getTime() <= now;
        const okEnd   = !cfg.end   || now <= new Date(cfg.end).getTime();
        if (okStart && okEnd) liveStream = cfg;
      }
    }
  } catch (lsErr) {
    console.warn('essc-livestream.json fetch failed; no livestream link:', lsErr);
  }
  // A session is "live now" when the wall clock sits inside its slot. Indico
  // times are naive Stockholm-local (CEST in June), so pin +02:00 to compare
  // correctly from any visitor timezone.
  function isLiveNow(slot) {
    if (!liveStream || !slot || !slot.start || !slot.end) return false;
    const now = Date.now();
    return new Date(slot.start + '+02:00').getTime() <= now
        && now < new Date(slot.end + '+02:00').getTime();
  }

  const conf = indico.annualConferences && indico.annualConferences['2026'];
  if (!conf) {
    setError(t.errAbsent);
    return;
  }

  // ── quick facts ───────────────────────────────────────────────
  if (quickfacts) {
    const setField = (name, content) => {
      const node = quickfacts.querySelector(`[data-field="${name}"]`);
      if (!node) return;
      // accept both DOM nodes and plain strings
      node.innerHTML = '';
      if (typeof content === 'string') node.textContent = content;
      else                              node.appendChild(content);
    };
    setField('dates', formatDateRange(conf.startDateOnly, conf.endDateOnly));
    setField('venue', conf.location || '—');
    setField('room',  conf.room     || '—');
    setField('indico', el('a', {
      href: conf.url, target: '_blank', rel: 'noopener',
    }, 'indico.eiss-europa.com'));
    quickfacts.dataset.state = 'ready';
    quickfacts.setAttribute('aria-busy', 'false');
  }
  if (tzNode && conf.startTz) tzNode.textContent = conf.startTz;

  // Last-synced cue: reassures a panelist who just edited Indico that
  // the grid is dated and refreshes overnight, heading off "I edited
  // it, why is the site still wrong?" emails.
  if (indico.syncedAt) {
    const syncNode = document.getElementById('programme-synced');
    if (syncNode) {
      let when = indico.syncedAt;
      try {
        when = new Date(indico.syncedAt).toLocaleDateString(dateLocale, { day: 'numeric', month: 'long', year: 'numeric' });
      } catch (_) { /* keep the ISO fallback */ }
      syncNode.textContent =
        lang === 'fr' ? ('Programme mis à jour le ' + when + ' ; actualisé depuis Indico chaque nuit.') :
        lang === 'de' ? ('Programm aktualisiert am ' + when + '; täglich über Nacht aus Indico erneuert.') :
                        ('Programme updated ' + when + '; refreshed from Indico daily, overnight.');
      syncNode.hidden = false;
    }
  }

  // ── programme grid ────────────────────────────────────────────
  const days = (conf.programme && conf.programme.days) || [];
  if (!days.length) {
    setError(t.errEmpty);
    return;
  }

  // Day chips — anchor-link nav. No JS scroll handler needed; native
  // anchor behaviour does the right thing including respecting
  // `prefers-reduced-motion`.
  chips.hidden = false;
  days.forEach((day, idx) => {
    const slug = 'day-' + day.date;
    // day.label in indico.json is hardcoded English ("Day 1"); rebuild
    // it locally so FR/DE readers get "Jour 1" / "Tag 1".
    const localDayLabel = `${t.day} ${idx + 1}`;
    chips.appendChild(el('a', {
      href: '#' + slug, class: 'programme-day-chip',
    },
      el('span', { class: 'lbl' }, localDayLabel),
      ' · ',
      el('span', { class: 'date' }, formatDate(day.date)),
    ));
  });

  // Grid body.
  root.dataset.state = 'ready';
  root.innerHTML = '';
  days.forEach((day, idx) => {
    const slug = 'day-' + day.date;
    const localDayLabel = `${t.day} ${idx + 1}`;
    const dayNode = el('section', {
      class: 'programme-day', id: slug, 'aria-labelledby': slug + '-title',
    },
      el('header', { class: 'programme-day-head' },
        el('h3', { id: slug + '-title' }, localDayLabel),
        el('span', { class: 'programme-day-date' }, formatDate(day.date)),
      ),
    );

    for (const row of (day.rows || [])) {
      const rowNode = el('div', {
        class: 'programme-row' + (row.parallel ? ' is-parallel' : ''),
      });
      // Time gutter
      rowNode.appendChild(el('div', { class: 'programme-row-time' },
        el('span', { class: 'start' }, row.startTime || ''),
        ' – ',
        el('span', { class: 'end' },   row.endTime   || ''),
      ));
      // Items (1 or many, depending on parallel)
      const itemsNode = el('div', { class: 'programme-row-items' });
      for (const slot of (row.items || [])) {
        itemsNode.appendChild(renderSlot(slot));
      }
      rowNode.appendChild(itemsNode);
      dayNode.appendChild(rowNode);
    }
    root.appendChild(dayNode);
  });

  // ── slot renderers ────────────────────────────────────────────
  function renderSlot(slot) {
    if (slot.kind === 'break') return renderBreak(slot);
    if (slot.kind === 'contribution') return renderContribution(slot);
    return renderSession(slot);
  }

  // Small map-pin SVG used by the room badge. Inline so the badge
  // renders with no extra HTTP, same pattern as livestreamIcon().
  function roomPinIcon() {
    const svgNS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', 'currentColor');
    svg.setAttribute('stroke-width', '2');
    svg.setAttribute('stroke-linecap', 'round');
    svg.setAttribute('stroke-linejoin', 'round');
    svg.setAttribute('aria-hidden', 'true');
    const paths = [
      ['path', { d: 'M12 22s7-7.58 7-13a7 7 0 10-14 0c0 5.42 7 13 7 13z' }],
      ['circle', { cx: 12, cy: 9, r: 2.5 }],
    ];
    for (const [tag, attrs] of paths) {
      const n = document.createElementNS(svgNS, tag);
      for (const k in attrs) n.setAttribute(k, attrs[k]);
      svg.appendChild(n);
    }
    return svg;
  }

  // Room badge used by every slot kind (session, contribution,
  // break). Returns null when no room is set on the slot, so the
  // caller can drop it into a list with `.filter(Boolean)` or as
  // a conditional child. Indico's `inheritRoom: true` rooms still
  // render: visitors want to see "Lecture Hall 8" even when it's
  // the conference default, so they don't second-guess.
  function roomBadge(slot) {
    if (!slot.room) return null;
    const badge = el('span', { class: 'programme-slot-room' });
    badge.appendChild(roomPinIcon());
    badge.appendChild(el('span', { class: 'lbl' }, slot.room));
    return badge;
  }

  function renderBreak(slot) {
    return el('article', { class: 'programme-slot is-break' },
      el('span', { class: 'programme-break-title' }, slot.title || t.breakFallback),
      roomBadge(slot),
    );
  }

  function renderContribution(slot) {
    return el('article', { class: 'programme-slot is-contribution' },
      slot.title ? el('h4', { class: 'programme-slot-title' },
        slot.url ? el('a', { href: slot.url, target: '_blank', rel: 'noopener' }, slot.title) : slot.title,
      ) : null,
      roomBadge(slot),
      slot.speakers && slot.speakers.length ? renderPeople(slot.speakers, t.speakers) : null,
      slot.abstract ? el('p', { class: 'programme-slot-abstract' }, slot.abstract) : null,
    );
  }

  // Small broadcast / radio-waves SVG. Used inside the livestream
  // badge on plenary + roundtable session cards.
  function livestreamIcon() {
    const svgNS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', 'currentColor');
    svg.setAttribute('stroke-width', '2');
    svg.setAttribute('stroke-linecap', 'round');
    svg.setAttribute('stroke-linejoin', 'round');
    svg.setAttribute('aria-hidden', 'true');
    const paths = [
      // central dot
      ['circle', { cx: 12, cy: 12, r: 1.6, fill: 'currentColor', stroke: 'none' }],
      // inner arcs
      ['path', { d: 'M8.5 8.5a5 5 0 000 7' }],
      ['path', { d: 'M15.5 8.5a5 5 0 010 7' }],
      // outer arcs
      ['path', { d: 'M5.6 5.6a9 9 0 000 12.8' }],
      ['path', { d: 'M18.4 5.6a9 9 0 010 12.8' }],
    ];
    for (const [tag, attrs] of paths) {
      const n = document.createElementNS(svgNS, tag);
      for (const k in attrs) n.setAttribute(k, attrs[k]);
      svg.appendChild(n);
    }
    return svg;
  }

  function renderSession(slot) {
    const subtype = slot.subtype;
    const isRoundtable = subtype === 'roundtable';
    const isPlenary    = subtype === 'plenary';
    // EISS livestreams plenaries (INTRO / KEY / CONC codes) and
    // roundtables (RT). Both map to non-null `subtype` here, so
    // the test is just "did sync-indico.py tag this slot with a
    // subtype". Regular panel sessions stay quiet.
    const isLive = isRoundtable || isPlenary;

    const head = el('header', { class: 'programme-slot-head' });
    head.appendChild(el('span', {
      class: 'programme-slot-kind' + (isRoundtable ? ' is-roundtable' : isPlenary ? ' is-plenary' : ''),
    }, subtypeLabel(subtype)));
    if (isLive) {
      // The Livestream pill is itself the link to the stream while the
      // conference is on air (the same Zoom URL for every session), and falls
      // back to a plain indicator outside the window. It keeps its
      // "Livestream" label throughout and carries the external-link icon; the
      // session on air now adds the is-live-now state (a red pulse).
      let badge;
      if (liveStream) {
        const liveNow = isLiveNow(slot);
        badge = el('a', {
          class: 'programme-slot-livestream is-link' + (liveNow ? ' is-live-now' : ''),
          href: liveStream.url, target: '_blank', rel: 'noopener',
          title: t.watchAria,
          'aria-label': (liveNow ? t.liveNow + ' · ' : '') + t.watchAria,
        }, livestreamIcon(), el('span', { class: 'lbl' }, t.livestream));
      } else {
        badge = el('span', {
          class: 'programme-slot-livestream',
          title: t.livestreamAria,
          'aria-label': t.livestreamAria,
        }, livestreamIcon(), el('span', { class: 'lbl' }, t.livestream));
      }
      head.appendChild(badge);
    }
    const room = roomBadge(slot);
    if (room) head.appendChild(room);

    const titleNode = el('h4', { class: 'programme-slot-title' },
      slot.url ? el('a', { href: slot.url, target: '_blank', rel: 'noopener' }, slot.title || '(untitled session)')
               : (slot.title || '(untitled session)'),
    );

    const card = el('article', { class: 'programme-slot is-session' },
      head, titleNode,
      slot.conveners  && slot.conveners.length  ? renderPeople(slot.conveners,  isRoundtable ? t.chair : t.chairs) : null,
      slot.discussants && slot.discussants.length ? renderPeople(slot.discussants, t.discussants) : null,
    );

    if (slot.contributions && slot.contributions.length) {
      const details = el('details', { class: 'programme-contribs' },
        el('summary', null,
          slot.contributions.length === 1
            ? `1 ${t.contribution}`
            : `${slot.contributions.length} ${t.contributions}`,
        ),
      );
      const list = el('ol', { class: 'programme-contribs-list' });
      for (const c of slot.contributions) {
        const ci = el('li', { class: 'programme-contrib' },
          el('div', { class: 'programme-contrib-head' },
            (c.startTime ? el('span', { class: 'programme-contrib-time' }, c.startTime) : null),
            el('h5', { class: 'programme-contrib-title' },
              c.url ? el('a', { href: c.url, target: '_blank', rel: 'noopener' }, c.title) : c.title,
            ),
          ),
          renderContribPeople(c),
          c.abstract ? renderAbstract(c) : null,
        );
        list.appendChild(ci);
      }
      details.appendChild(list);
      card.appendChild(details);
    }

    return card;
  }

  // Per-contribution abstract block with inline expand toggle.
  //
  // Indico stores arbitrarily long abstracts; the sync truncates to
  // a teaser (~360 chars) so the initial render stays light. When a
  // `fullAbstract` is also present, we add a "Read full abstract"
  // button that swaps the teaser for the full text in place, with
  // a "Show less" toggle back. The contribution title remains an
  // anchor to the Indico page for the canonical record.
  //
  // No motion is added: the abstract is just text, and animating its
  // height would either fight `prefers-reduced-motion` or risk
  // janky reflows on long abstracts inside long sessions.
  function renderAbstract(c) {
    const node = el('p', { class: 'programme-contrib-abstract' });
    const text = el('span', { class: 'programme-contrib-abstract-text' }, c.abstract);
    node.appendChild(text);
    if (c.fullAbstract) {
      let expanded = false;
      const btn = el('button', {
        type: 'button',
        class: 'programme-contrib-more',
        'aria-expanded': 'false',
      }, t.readFullAbstract);
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        expanded = !expanded;
        text.textContent = expanded ? c.fullAbstract : c.abstract;
        btn.textContent = expanded ? t.showLess : t.readFullAbstract;
        btn.setAttribute('aria-expanded', expanded ? 'true' : 'false');
      });
      node.appendChild(document.createTextNode(' '));
      node.appendChild(btn);
    }
    return node;
  }

  // A small microphone glyph marking who presents a paper. Drawn as
  // an inline SVG so it prints and scales with the text; carries an
  // aria-label + title so it isn't silent to assistive tech.
  function micIcon() {
    const s = el('span', { class: 'programme-mic', role: 'img', 'aria-label': t.speakerTag, title: t.speakerTag });
    s.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false"><path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V21H8v2h8v-2h-3v-3.08A7 7 0 0 0 19 11h-2z"/></svg>';
    return s;
  }

  // Build the byline for one contribution. Prefers the new `people`
  // array (full author list, each with a `speaker` flag); falls back
  // to the legacy `speakers` array (all treated as presenters) so the
  // page still renders against data synced before this change.
  function renderContribPeople(c) {
    const people = (c.people && c.people.length)
      ? c.people
      : (c.speakers || []).map((s) => ({ name: s.name, affiliation: s.affiliation, speaker: true }));
    return people.length ? renderPeople(people, null) : null;
  }

  function renderPeople(people, label) {
    const node = el('p', { class: 'programme-people' });
    if (label) node.appendChild(el('span', { class: 'programme-people-label' }, label + ': '));
    // Only mark presenters when the list actually mixes speakers and
    // non-presenting co-authors — a single-author talk or an all-
    // presenting panel needs no disambiguation, so it stays clean.
    const markSpeakers = people.some((p) => p.speaker === true)
                      && people.some((p) => p.speaker === false);
    people.forEach((p, i) => {
      if (i > 0) node.appendChild(document.createTextNode(', '));
      const k = nameKey(p.name);
      const member = k && memberLookup.get(k);
      if (k && !member) unmatchedSpeakers.add(p.name);
      let nameNode;
      if (member) {
        // The anchor is a real link to /people.html#<slug>. Hover and
        // focus open the preview card; left-click also opens it
        // instead of navigating. Modifier-click and middle-click pass
        // through to native behaviour so "open in new tab" still works.
        nameNode = el('a', {
          class: 'name has-member-card',
          href: peopleUrl + '#' + member.id,
          'aria-haspopup': 'dialog',
        }, p.name || '—');
        nameNode.addEventListener('click',      (e) => openMemberCard(e, nameNode, member));
        nameNode.addEventListener('mouseenter', () => showMemberCard(nameNode, member));
        nameNode.addEventListener('mouseleave', hideMemberCardSoon);
        nameNode.addEventListener('focus',      () => showMemberCard(nameNode, member));
        nameNode.addEventListener('blur',       hideMemberCardSoon);
      } else {
        nameNode = el('span', { class: 'name' }, p.name || '—');
      }
      node.appendChild(el('span', { class: 'programme-person' + (markSpeakers && p.speaker ? ' is-speaker' : '') },
        nameNode,
        (markSpeakers && p.speaker) ? micIcon() : null,
        p.affiliation ? el('span', { class: 'aff' }, ' (' + p.affiliation + ')') : null,
      ));
    });
    return node;
  }

  // Surface the gap. Filtered to keyable names (≥2 tokens after
  // stripping) so "TBD" and similar placeholders don't show up.
  if (memberLookup.size && unmatchedSpeakers.size) {
    console.debug(
      `[essc] ${unmatchedSpeakers.size} speakers didn't match a member: ` +
      [...unmatchedSpeakers].sort().join(', ')
    );
  }

  // ── member card popover ──────────────────────────────────────
  // The hover / focus / click profile card is the shared, site-wide
  // component in assets/js/site.js, exposed as window.netsecMemberCard.
  // This renderer keeps its own fuzzy speaker-name matcher (nameKey /
  // buildMemberLookup above, the one piece the static module does not
  // need) and, once a name resolves to a bios record, hands the record
  // to the shared card. The locale differences the programme carries,
  // its raw Indico role strings, the localised WG-number prefix
  // ("WG" / "GT" / "AG"), the localised contact labels, the locale's
  // people.html target for the CTA, and the localised popover aria-label,
  // are passed through as options so the card stays one implementation.
  const memberCardOpts = (member) => ({
    ctaHref: peopleUrl + '#' + member.id,
    ariaLabel: t.memberCardLabel,
    roleLabel: (s) => s,            // programme role strings stay verbatim
    wgPrefix: t.wgPrefix,
    contactLabels: {
      email: t.iconEmail, website: t.iconWebsite, orcid: t.iconOrcid,
      linkedin: t.iconLinkedin, twitter: t.iconTwitter,
      bluesky: t.iconBluesky, mastodon: t.iconMastodon,
    },
  });

  function showMemberCard(anchor, member) {
    if (!window.netsecMemberCard) return null;
    return window.netsecMemberCard.show(anchor, member, memberCardOpts(member));
  }

  function hideMemberCardSoon() {
    if (window.netsecMemberCard) window.netsecMemberCard.scheduleHide();
  }

  function openMemberCard(e, anchor, member) {
    // Modifier or non-primary clicks fall through to native link
    // behaviour (open in new tab, etc.).
    if (e.defaultPrevented) return;
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    const card = showMemberCard(anchor, member);
    if (!card) return; // Popover unsupported; let the link navigate.
    e.preventDefault();
  }

  // ── Print: expand every panel before the print dialog renders ──
  // Each session's paper line-up lives in a collapsed <details> that
  // a reader expands on screen. The print engine honours that
  // open/closed state, so a printed programme would only show the
  // panels the reader happened to expand, leaving the rest as a bare
  // "N contributions" summary. We force every contributions <details>
  // open before the print render and restore the on-screen state
  // afterwards, so printing is non-destructive. The print stylesheet
  // hides the summary toggle and the abstracts, leaving a clean
  // line-up of session, chairs, paper titles, and speakers.
  //
  // `printActive` guards against the double-fire when both
  // `beforeprint` and the matchMedia('print') change land for the
  // same print (Chrome fires both): the second expand would otherwise
  // find nothing closed, empty `printExpanded`, and leave the panels
  // open after printing. The matchMedia path is the Safari fallback,
  // which historically does not fire before/afterprint.
  let printExpanded = [];
  let printActive = false;
  function expandForPrint() {
    if (printActive) return;
    printActive = true;
    printExpanded = [];
    document.querySelectorAll('details.programme-contribs:not([open])').forEach((d) => {
      d.open = true;
      printExpanded.push(d);
    });
  }
  function restoreAfterPrint() {
    if (!printActive) return;
    printActive = false;
    printExpanded.forEach((d) => { d.open = false; });
    printExpanded = [];
  }
  window.addEventListener('beforeprint', expandForPrint);
  window.addEventListener('afterprint', restoreAfterPrint);
  if (window.matchMedia) {
    const printMq = window.matchMedia('print');
    const onPrintChange = (e) => { (e.matches ? expandForPrint : restoreAfterPrint)(); };
    if (printMq.addEventListener) printMq.addEventListener('change', onPrintChange);
    else if (printMq.addListener) printMq.addListener(onPrintChange);
  }
})();
