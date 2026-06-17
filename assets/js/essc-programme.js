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

  // Per-page configuration, read from #programme-root, so one renderer
  // serves every ESSC edition. `data-year` picks the conference inside
  // annualConferences; `data-src` points at a frozen snapshot instead of
  // the live data/indico.json (used to archive a past edition against
  // future Indico changes); `data-archived` hides the "synced" freshness
  // cue. Defaults keep the live 2026 behaviour for an un-attributed page.
  const PROG_YEAR     = (root && root.dataset.year) || '2026';
  const PROG_SRC      = (root && root.dataset.src) || 'data/indico.json';
  const PROG_ARCHIVED = !!(root && root.dataset.archived);

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
      readAbstract: 'Read abstract',
      hideAbstract: 'Hide abstract',
      published: 'Published →',
      publishedAria: 'Read the published version in the EISS Anthology (opens in a new tab)',
      anthologyBrowse: 'Browse published EISS papers in the Anthology →',
      livestream: 'Livestream',
      breakFallback: 'Break',
      livestreamAria: 'This session will be livestreamed',
      watchAria: 'Watch the livestream on Zoom (opens in a new tab)',
      liveNow: 'Live now',
      nowHappening: 'Now happening',
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
      readAbstract: 'Lire le résumé',
      hideAbstract: 'Masquer le résumé',
      published: 'Publié →',
      publishedAria: 'Lire la version publiée dans l’Anthologie de l’EISS (ouvre dans un nouvel onglet)',
      anthologyBrowse: 'Parcourir les articles publiés de l’EISS dans l’Anthologie →',
      livestream: 'Diffusion directe',
      breakFallback: 'Pause',
      livestreamAria: 'Session diffusée en direct',
      watchAria: 'Regarder la diffusion en direct sur Zoom (nouvel onglet)',
      liveNow: 'En direct',
      nowHappening: 'En ce moment',
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
      readAbstract: 'Zusammenfassung lesen',
      hideAbstract: 'Zusammenfassung ausblenden',
      published: 'Veröffentlicht →',
      publishedAria: 'Die veröffentlichte Fassung in der EISS-Anthologie lesen (öffnet in neuem Tab)',
      anthologyBrowse: 'Veröffentlichte EISS-Beiträge in der Anthologie durchsuchen →',
      livestream: 'Livestream',
      breakFallback: 'Pause',
      livestreamAria: 'Diese Sitzung wird per Livestream übertragen',
      watchAria: 'Den Livestream auf Zoom ansehen (neuer Tab)',
      liveNow: 'Jetzt live',
      nowHappening: 'Jetzt im Programm',
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
    const link = el('a', { class: 'programme-download', href: t.pdfFile.replace('2026', PROG_YEAR), download: '' });
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

  // ── EISS Anthology cross-link (published papers only) ─────────
  // The EISS Anthology (eiss-europa.com) publishes
  // data/anthology-index.json — one record per paper
  // { title, year, slug, url, published }, built from its own
  // paperIndex.js. We consume the result rather than reconstruct the
  // slug, which is collision-deduped and truncated on their side. A
  // paper that matches by title AND is flagged `published` gets a quiet
  // "Published →" link to its Anthology page, where the publication card
  // lives. Runtime fetch (the artifact is CORS-open), so markers appear
  // on their own as EISS reviews more publications, with no NetSec
  // rebuild. Published-only by design: this page already shows the
  // abstract, so the link only earns its place when it adds the route to
  // the published version.
  const ANTHOLOGY_INDEX_URL = 'https://eiss-europa.com/data/anthology-index.json';
  const ANTHOLOGY_PUBLISHED_VIEW = 'https://eiss-europa.com/anthology.html?view=papers&published=1';

  // Normalise a paper title to a match key: lowercase, fold accents,
  // collapse every run of non-alphanumerics to one space, trim. Tolerates
  // the punctuation / whitespace / accent drift between an Indico title and
  // the Anthology's (e.g. the double space in a real 2026 title).
  function titleKey(s) {
    return (s || '')
      .toLowerCase()
      .normalize('NFKD').replace(/[̀-ͯ]/g, '')
      .replace(/[^a-z0-9]+/g, ' ')
      .trim();
  }

  function buildAnthologyLookup(records, year) {
    // Published papers for THIS edition only, keyed by normalised title.
    // Scoping to the page's conference year stops a title that recurs
    // across years from matching the wrong edition.
    const map = new Map();
    const y = Number(year);
    for (const r of (Array.isArray(records) ? records : [])) {
      if (Number(r && r.year) === y && r && r.published && r.url) {
        const k = titleKey(r.title);
        if (k && !map.has(k)) map.set(k, r.url);
      }
    }
    return map;
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
    const res = await fetch(PROG_SRC, { cache: 'no-cache' });
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

  // EISS Anthology published-paper lookup (best-effort, runtime). Absent,
  // malformed, or a fetch error all mean no "Published" markers render and
  // the programme is unaffected.
  let anthologyLookup = new Map();
  try {
    const res = await fetch(ANTHOLOGY_INDEX_URL, { cache: 'no-cache' });
    if (res.ok) anthologyLookup = buildAnthologyLookup(await res.json(), PROG_YEAR);
  } catch (err) {
    console.warn('anthology-index.json fetch failed; published markers disabled:', err);
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

  const conf = indico.annualConferences && indico.annualConferences[PROG_YEAR];
  if (!conf) {
    setError(t.errAbsent.replace('2026', PROG_YEAR));
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
  if (indico.syncedAt && !PROG_ARCHIVED) {
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

  // EISS Anthology signpost: one quiet line
  // under the grid pointing at the Anthology's published-papers view, the
  // cross-conference record of EISS abstracts and their published versions.
  // Appended only once a programme has rendered, so a not-yet-published
  // edition (the parked ESSC27 template) shows nothing until its grid lands.
  root.appendChild(el('p', { class: 'programme-anthology-note' },
    el('a', { href: ANTHOLOGY_PUBLISHED_VIEW, target: '_blank', rel: 'noopener' }, t.anthologyBrowse)));

  // ── "Now happening" banner (issue #832) ───────────────────────
  // During the conference, surface the session(s) in progress now as a
  // banner above the day chips, each linking to its card. Liveness is the
  // row's HH:MM window on the day's date, compared to the current wall
  // clock in the conference timezone (Europe/Stockholm) — correct from any
  // visitor timezone and DST-safe, since both sides are conference-local
  // wall-clock and no offset arithmetic is involved. The grid data itself
  // refreshes via the daily sync (and, once the dispatch plugin lands,
  // within ~1 min), so a last-minute change surfaces here too. Hidden
  // whenever nothing is live, so it self-limits to the conference window.
  // A `?now=YYYY-MM-DDTHH:MM` query param overrides "now" for QA outside a
  // live conference.
  const confTz = conf.startTz || 'Europe/Stockholm';
  const nowOverride = (function () {
    const m = /[?&]now=(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})/.exec(location.search);
    return m ? { date: m[1], minutes: (+m[2]) * 60 + (+m[3]) } : null;
  })();
  function confNow() {
    if (nowOverride) return nowOverride;
    try {
      const p = Object.fromEntries(new Intl.DateTimeFormat('en-CA', {
        timeZone: confTz, year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', hour12: false,
      }).formatToParts(new Date()).map(x => [x.type, x.value]));
      const hour = p.hour === '24' ? 0 : (+p.hour);  // some engines emit 24 at midnight
      return { date: `${p.year}-${p.month}-${p.day}`, minutes: hour * 60 + (+p.minute) };
    } catch (_) {
      return null;  // no Intl tz support → never show the banner
    }
  }
  function toMin(hhmm) { const a = String(hhmm || '').split(':'); return (+a[0] || 0) * 60 + (+a[1] || 0); }
  function liveItemsAt(now) {
    if (!now) return [];
    const found = [];
    for (const day of days) {
      if (day.date !== now.date) continue;
      for (const row of (day.rows || [])) {
        if (!row.startTime || !row.endTime) continue;
        if (toMin(row.startTime) <= now.minutes && now.minutes < toMin(row.endTime)) {
          for (const item of (row.items || [])) found.push({ item, row });
        }
      }
    }
    return found;
  }

  const nowBanner = el('div', {
    class: 'programme-now', id: 'programme-now',
    role: 'status', 'aria-live': 'polite', hidden: '',
  });
  if (chips && chips.parentNode) chips.parentNode.insertBefore(nowBanner, chips);

  function renderNow() {
    const found = liveItemsAt(confNow());
    // Prefer sessions/contributions; show a break only if nothing else is live.
    const sessions = found.filter(f => f.item.kind !== 'break');
    const show = sessions.length ? sessions : found;
    if (!show.length) { nowBanner.hidden = true; nowBanner.textContent = ''; return; }
    const list = el('ul', { class: 'programme-now-list' },
      show.map(({ item, row }) => {
        const label = item.title || t.session;
        const link =
          item.id != null ? el('a', { href: '#prog-slot-' + item.id, class: 'programme-now-link' }, label)
          : item.url      ? el('a', { href: item.url, target: '_blank', rel: 'noopener', class: 'programme-now-link' }, label)
          :                 el('span', { class: 'programme-now-link' }, label);
        return el('li', { class: 'programme-now-item' },
          link,
          item.room ? el('span', { class: 'programme-now-room' }, item.room) : null,
          el('span', { class: 'programme-now-time' }, `${row.startTime} – ${row.endTime}`),
        );
      }),
    );
    nowBanner.textContent = '';
    nowBanner.appendChild(el('span', { class: 'programme-now-dot', 'aria-hidden': 'true' }));
    nowBanner.appendChild(el('span', { class: 'programme-now-label' }, t.nowHappening));
    nowBanner.appendChild(list);
    nowBanner.hidden = false;
  }
  renderNow();
  // Advance as time passes; re-check on refocus so a backgrounded tab catches up.
  setInterval(renderNow, 30000);
  document.addEventListener('visibilitychange', function () { if (!document.hidden) renderNow(); });

  // ── slot renderers ────────────────────────────────────────────
  function renderSlot(slot) {
    const node =
      slot.kind === 'break'        ? renderBreak(slot) :
      slot.kind === 'contribution' ? renderContribution(slot) :
                                     renderSession(slot);
    // A stable anchor so the "Now happening" banner can link to the card.
    if (node && slot && slot.id != null && !node.id) node.id = 'prog-slot-' + slot.id;
    return node;
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
      publishedMarker(slot),
      // Same collapsed-toggle treatment as a paper inside a session, so a
      // standalone contribution reads identically (forward-safe: the
      // current programme has no top-level contribution slots).
      slot.abstract ? renderAbstract(slot) : null,
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
      // Parallel panels share a row height, so expanding one paper list on
      // its own leaves the sibling panel short with a tall empty gap. Keep
      // the contribution lists in a parallel row in lockstep: toggling one
      // opens or closes the others. The d.open !== details.open guard makes
      // the cascade converge (a peer already in the target state fires no
      // further toggle), so it is safe despite the toggle event being async,
      // and no recursion flag is needed. Single (non-parallel) rows match no
      // `.is-parallel` ancestor, so they are unaffected.
      details.addEventListener('toggle', function () {
        const row = details.closest('.programme-row.is-parallel');
        if (!row) return;
        row.querySelectorAll('details.programme-contribs').forEach(function (d) {
          if (d !== details && d.open !== details.open) d.open = details.open;
        });
      });
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
          publishedMarker(c),
          c.abstract ? renderAbstract(c) : null,
        );
        list.appendChild(ci);
      }
      details.appendChild(list);
      card.appendChild(details);
    }

    return card;
  }

  // Per-contribution abstract, collapsed behind a single toggle.
  //
  // Every paper reads the same way: by default only a "Read abstract"
  // button shows, and clicking it reveals the full text in place
  // ("Hide abstract" toggles back). Showing the abstract by default
  // used to leave the panel looking half-expanded and was uneven
  // across papers — a long paper showed a ~360-char teaser with a
  // toggle, while a short one (no separate `fullAbstract`) showed its
  // whole abstract with no toggle. Hiding it until asked makes the
  // line-up scannable and identical for every paper.
  //
  // `fullAbstract` is the complete text; `abstract` is the teaser the
  // sync stores, which equals the full text when it was short enough
  // not to truncate, so it is the right fallback. The contribution
  // title remains an anchor to the Indico page for the canonical
  // record. No motion is added: animating the height would fight
  // `prefers-reduced-motion` or risk janky reflows on long abstracts.
  function renderAbstract(c) {
    const full = c.fullAbstract || c.abstract;
    const node = el('p', { class: 'programme-contrib-abstract' });
    const btn = el('button', {
      type: 'button',
      class: 'programme-contrib-more',
      'aria-expanded': 'false',
    }, t.readAbstract);
    const text = el('span', { class: 'programme-contrib-abstract-text' }, full);
    let expanded = false;
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      expanded = !expanded;
      node.classList.toggle('is-open', expanded);
      btn.textContent = expanded ? t.hideAbstract : t.readAbstract;
      btn.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    });
    node.appendChild(btn);
    node.appendChild(text);
    return node;
  }

  // "Published →" marker for a paper whose published version EISS has
  // reviewed into the Anthology (matched by title against the published,
  // current-year records). Returns null for everything else, so most
  // papers show nothing. Links to the Anthology paper page, which carries
  // the publication card.
  function publishedMarker(c) {
    const url = c && c.title ? anthologyLookup.get(titleKey(c.title)) : null;
    if (!url) return null;
    return el('a', {
      class: 'programme-contrib-published',
      href: url, target: '_blank', rel: 'noopener',
      title: t.publishedAria, 'aria-label': t.publishedAria,
    }, t.published);
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

/* Conference recap reel: muted autoplay loop with a minimal UI.
   The static markup ships with `controls` as a no-JS fallback (a visitor
   without scripting still gets a playable, paused video and the 24 MB file
   loads only on their press). When scripting is on and the visitor has not
   asked for reduced motion, we drop the controls for a clean ambient reel
   and play it muted in a loop while it sits in the viewport, pausing when it
   scrolls away so the page is not decoding video off-screen. A click toggles
   sound, the one control the bare reel still needs. Honouring
   prefers-reduced-motion, we leave the controls on and never autoplay. */
(function () {
  const v = document.querySelector('.essc-recap-video');
  if (!v) return;
  const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce) return;                 // keep controls, no autoplay
  v.muted = true;
  v.loop = true;
  v.setAttribute('playsinline', '');
  v.removeAttribute('controls');      // minimal UI once we can drive it
  v.classList.add('is-ambient');
  function play() {
    const p = v.play();
    if (p && p.catch) p.catch(() => { v.setAttribute('controls', ''); });
  }
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting) play(); else v.pause(); });
    }, { threshold: 0.25 });
    io.observe(v);
  } else {
    play();
  }
  // The reel has no control bar now, so a click is the sound toggle.
  v.addEventListener('click', () => {
    v.muted = !v.muted;
    if (v.paused) play();
  });
})();

