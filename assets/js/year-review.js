/* Year in Review: renders one Action-year edition from
 * data/year-review.json (#765).
 *
 * Every narrative sentence on the page comes from the I18N table
 * below, written as whole sentences per locale with numerals, names
 * and lists as the only slots. The builder that writes the JSON
 * composes no prose, and the lede and outlook paragraphs come from its
 * `hand` block, which the maintainer writes in all three locales.
 * Assembling a sentence from clause fragments would not survive French
 * or German grammar, so the templates are never split.
 *
 * One renderer for all three locales, picked off <html lang>, rather
 * than a copy per locale page: three copies of a template drift, which
 * is the lesson from #1136.
 *
 * Fail-soft: on any error the static fallback in the page survives and
 * nothing is replaced. Same render-from-JSON contract as
 * assets/js/roadmap-progress.js.
 */
(function () {
  'use strict';

  var locale = (document.documentElement.lang || 'en').slice(0, 2);

  var MONTHS = {
    en: ['January', 'February', 'March', 'April', 'May', 'June', 'July',
      'August', 'September', 'October', 'November', 'December'],
    fr: ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet',
      'août', 'septembre', 'octobre', 'novembre', 'décembre'],
    de: ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli',
      'August', 'September', 'Oktober', 'November', 'Dezember'],
  };

  // Plurals are handled inside each template, per locale, because the
  // rules differ: French treats 0 and 1 alike, German does not.
  var I18N = {
    en: {
      title: function (n) { return 'Year ' + n; },
      window: function (from, to) { return from + ' to ' + to; },
      openWindow: function (from) {
        return 'Year one is still under way. The figures below cover '
          + from + ' to today, and the edition is finalised after 9 October.';
      },
      closedWindow: function (from, to) {
        return 'The figures below cover the Action year from ' + from
          + ' to ' + to + '.';
      },
      statMembers: 'Directory members',
      statCountries: 'Countries',
      statEvents: 'Events held',
      statOutputs: 'Outputs published',
      growthH: 'How the Directory grew',
      growthCaption: function (first, last, from, to) {
        return 'The Directory held ' + first + ' members in ' + from
          + ' and ' + last + ' in ' + to + '.';
      },
      growthPoint: function (n, month) { return n + ' members in ' + month; },
      themesH: 'What the network works on',
      themeCount: function (n) {
        return n === 1 ? '1 member' : n + ' members';
      },
      quartersH: 'The year, quarter by quarter',
      quarter: function (n) { return 'Quarter ' + n; },
      quarterEmpty: 'Nothing recorded in this quarter.',
      newsH: 'News',
      eventsH: 'Events',
      outputsH: 'Outputs published',
      releasesH: 'What shipped on the website',
      releaseCount: function (total, minors) {
        return total + ' releases reached the site this year, '
          + minors + ' of them carrying new or reworked features. '
          + 'Each links to its own release notes.';
      },
      outlookH: 'Looking ahead',
      noOutputs: 'The Action published no outputs in this year.',
    },
    fr: {
      title: function (n) { return 'Année ' + n; },
      window: function (from, to) { return 'du ' + from + ' au ' + to; },
      openWindow: function (from) {
        return "La première année est encore en cours. Les chiffres ci-dessous"
          + ' portent sur la période du ' + from
          + " à aujourd'hui, et l'édition sera finalisée après le 9 octobre.";
      },
      closedWindow: function (from, to) {
        return "Les chiffres ci-dessous portent sur l'année de l'Action, du "
          + from + ' au ' + to + '.';
      },
      statMembers: 'Membres du répertoire',
      statCountries: 'Pays',
      statEvents: 'Événements tenus',
      statOutputs: 'Productions publiées',
      growthH: "Comment le répertoire s'est étoffé",
      growthCaption: function (first, last, from, to) {
        return 'Le répertoire comptait ' + first + ' membres en ' + from
          + ' et ' + last + ' en ' + to + '.';
      },
      growthPoint: function (n, month) { return n + ' membres en ' + month; },
      themesH: 'Les domaines de travail du réseau',
      themeCount: function (n) {
        return n > 1 ? n + ' membres' : n + ' membre';
      },
      quartersH: "L'année, trimestre par trimestre",
      quarter: function (n) { return 'Trimestre ' + n; },
      quarterEmpty: 'Rien à signaler pour ce trimestre.',
      newsH: 'Actualités',
      eventsH: 'Événements',
      outputsH: 'Productions publiées',
      releasesH: 'Ce qui a été livré sur le site',
      releaseCount: function (total, minors) {
        return total + ' versions ont été mises en ligne cette année, dont '
          + minors + ' apportant des fonctionnalités nouvelles ou refondues. '
          + 'Chacune renvoie à ses propres notes de version.';
      },
      outlookH: 'Perspectives',
      noOutputs: "L'Action n'a publié aucune production durant cette année.",
    },
    de: {
      title: function (n) { return 'Jahr ' + n; },
      window: function (from, to) { return from + ' bis ' + to; },
      openWindow: function (from) {
        return 'Das erste Jahr läuft noch. Die Zahlen unten umfassen den '
          + 'Zeitraum vom ' + from + ' bis heute, und die Ausgabe wird nach '
          + 'dem 9. Oktober abgeschlossen.';
      },
      closedWindow: function (from, to) {
        return 'Die Zahlen unten umfassen das Action-Jahr vom ' + from
          + ' bis ' + to + '.';
      },
      statMembers: 'Mitglieder im Verzeichnis',
      statCountries: 'Länder',
      statEvents: 'Durchgeführte Veranstaltungen',
      statOutputs: 'Veröffentlichte Ergebnisse',
      growthH: 'Wie das Verzeichnis gewachsen ist',
      growthCaption: function (first, last, from, to) {
        return 'Das Verzeichnis umfasste im ' + from + ' ' + first
          + ' Mitglieder und im ' + to + ' ' + last + '.';
      },
      growthPoint: function (n, month) {
        return n + ' Mitglieder im ' + month;
      },
      themesH: 'Woran das Netzwerk arbeitet',
      themeCount: function (n) {
        return n === 1 ? '1 Mitglied' : n + ' Mitglieder';
      },
      quartersH: 'Das Jahr, Quartal für Quartal',
      quarter: function (n) { return 'Quartal ' + n; },
      quarterEmpty: 'Für dieses Quartal ist nichts vermerkt.',
      newsH: 'Aktuelles',
      eventsH: 'Veranstaltungen',
      outputsH: 'Veröffentlichte Ergebnisse',
      releasesH: 'Was auf der Website erschienen ist',
      releaseCount: function (total, minors) {
        return total + ' Versionen erreichten die Website in diesem Jahr, '
          + minors + ' davon mit neuen oder überarbeiteten Funktionen. '
          + 'Jede verweist auf ihre eigenen Versionshinweise.';
      },
      outlookH: 'Ausblick',
      noOutputs: 'Die Action hat in diesem Jahr keine Ergebnisse veröffentlicht.',
    },
  };
  var t = I18N[locale] || I18N.en;

  var RELEASE_BASE =
    'https://github.com/EISSeuropa/netsec.github.io/releases/tag/v';

  function el(tag, attrs) {
    var n = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === 'text') n.textContent = attrs[k];
      else n.setAttribute(k, attrs[k]);
    });
    for (var i = 2; i < arguments.length; i++) {
      if (arguments[i]) n.appendChild(arguments[i]);
    }
    return n;
  }

  function pick(map) {
    if (!map) return '';
    return map[locale] || map.en || '';
  }

  /* "2025-10-10" -> "10 October 2025" / "10 octobre 2025" /
     "10. Oktober 2025". The three locale forms differ only in the
     separator, so one formatter covers them. */
  function longDate(iso) {
    var parts = String(iso || '').split('-');
    if (parts.length !== 3) return String(iso || '');
    var day = String(Number(parts[2]));
    var month = (MONTHS[locale] || MONTHS.en)[Number(parts[1]) - 1];
    if (!month) return iso;
    if (locale === 'de') return day + '. ' + month + ' ' + parts[0];
    return day + ' ' + month + ' ' + parts[0];
  }

  /* "2026-05" -> "May 2026" / "mai 2026" / "Mai 2026" */
  function monthLabel(ym) {
    var parts = String(ym || '').split('-');
    var month = (MONTHS[locale] || MONTHS.en)[Number(parts[1]) - 1];
    return month ? month + ' ' + parts[0] : String(ym || '');
  }

  function statStrip(stats) {
    var strip = el('div', { 'class': 'wg-stats yr-stats' });
    [
      [stats.members, t.statMembers],
      [stats.countries, t.statCountries],
      [stats.events, t.statEvents],
      [stats.outputs, t.statOutputs],
    ].forEach(function (pair) {
      strip.appendChild(el('div', { 'class': 'wg-stat' },
        el('span', { 'class': 'wg-stat-n', 'text': String(pair[0]) }),
        el('span', { 'class': 'wg-stat-l', 'text': pair[1] })));
    });
    return strip;
  }

  /* A sparkline of Directory size, inherited from #764. Inline SVG
     rather than a charting library: the series is a handful of points
     and the shape is a polyline. The figures are also written out in
     the caption and in the title of each point, so the trend is
     available without reading the picture. */
  function sparkline(series) {
    if (series.length < 2) return null;
    var W = 620, H = 120, PAD = 10;
    var counts = series.map(function (p) { return p.members; });
    var max = Math.max.apply(null, counts);
    var min = Math.min.apply(null, counts);
    var span = max - min || 1;
    var x = function (i) {
      return PAD + (i * (W - 2 * PAD)) / (series.length - 1);
    };
    var y = function (v) {
      return H - PAD - ((v - min) * (H - 2 * PAD)) / span;
    };

    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
    svg.setAttribute('class', 'yr-spark');
    svg.setAttribute('role', 'img');
    svg.setAttribute('preserveAspectRatio', 'none');
    svg.setAttribute('aria-label', t.growthCaption(
      counts[0], counts[counts.length - 1],
      monthLabel(series[0].month),
      monthLabel(series[series.length - 1].month)));

    function node(name, attrs) {
      var n = document.createElementNS('http://www.w3.org/2000/svg', name);
      Object.keys(attrs).forEach(function (k) { n.setAttribute(k, attrs[k]); });
      return n;
    }

    var points = series.map(function (p, i) {
      return x(i) + ',' + y(p.members);
    }).join(' ');
    svg.appendChild(node('polyline', {
      'points': points, 'class': 'yr-spark-line',
      'fill': 'none', 'vector-effect': 'non-scaling-stroke',
    }));
    series.forEach(function (p, i) {
      var dot = node('circle', {
        'cx': x(i), 'cy': y(p.members), 'r': 4, 'class': 'yr-spark-dot',
      });
      var title = document.createElementNS(
        'http://www.w3.org/2000/svg', 'title');
      title.textContent = t.growthPoint(p.members, monthLabel(p.month));
      dot.appendChild(title);
      svg.appendChild(dot);
    });
    return svg;
  }

  function themeBars(themes) {
    if (!themes.length) return null;
    var max = themes[0].members || 1;
    var list = el('ul', { 'class': 'yr-themes' });
    themes.forEach(function (th) {
      var pct = Math.max(2, Math.round((th.members / max) * 100));
      list.appendChild(el('li', { 'class': 'yr-theme' },
        el('span', { 'class': 'yr-theme-name', 'text': th.name }),
        el('span', { 'class': 'yr-theme-bar', 'aria-hidden': 'true' },
          el('span', {
            'class': 'yr-theme-fill', 'style': 'width:' + pct + '%',
          })),
        el('span', {
          'class': 'yr-theme-n', 'text': t.themeCount(th.members),
        })));
    });
    return list;
  }

  function itemList(heading, items, render) {
    if (!items.length) return null;
    var wrap = el('div', { 'class': 'yr-group' },
      el('h4', { 'class': 'yr-group-h', 'text': heading }));
    var list = el('ul', { 'class': 'yr-items' });
    items.forEach(function (it) { list.appendChild(render(it)); });
    wrap.appendChild(list);
    return wrap;
  }

  /* The day, formatted here, rather than the item's own displayDate.
     news.json carries a card label in that field, and three of the
     eight items read "Now open" or "Applications closed", which is
     right on a news card and useless in a chronology. Events keep
     their displayDate, since it spans a range a single day cannot
     express. */
  function newsItem(n) {
    return el('li', { 'class': 'yr-item' },
      el('span', { 'class': 'yr-item-date', 'text': longDate(n.date) }),
      el('span', { 'class': 'yr-item-title', 'text': pick(n.title) }));
  }

  function eventItem(e) {
    var place = pick(e.location);
    return el('li', { 'class': 'yr-item' },
      el('span', { 'class': 'yr-item-date', 'text': pick(e.displayDate) }),
      el('span', { 'class': 'yr-item-title', 'text': pick(e.title) }),
      place ? el('span', { 'class': 'yr-item-meta', 'text': place }) : null);
  }

  function outputItem(o) {
    var label = pick(o.title);
    var title = o.url
      ? el('a', { 'class': 'yr-item-title', 'href': o.url,
        'target': '_blank', 'rel': 'noopener', 'text': label })
      : el('span', { 'class': 'yr-item-title', 'text': label });
    return el('li', { 'class': 'yr-item' },
      el('span', { 'class': 'yr-item-date', 'text': monthLabel(o.date) }),
      title);
  }

  function quarterCards(ed) {
    var byId = {};
    ed.news.forEach(function (n) { byId['n:' + n.id] = n; });
    ed.events.forEach(function (e) { byId['e:' + e.uid] = e; });

    var grid = el('div', { 'class': 'yr-quarters' });
    ed.quarters.forEach(function (q) {
      var news = q.news.map(function (id) { return byId['n:' + id]; })
        .filter(Boolean);
      var events = q.events.map(function (id) { return byId['e:' + id]; })
        .filter(Boolean);
      var card = el('article', { 'class': 'glass yr-quarter' },
        el('h3', { 'class': 'yr-quarter-h', 'text': t.quarter(q.n) }),
        el('p', {
          'class': 'yr-quarter-span',
          'text': t.window(longDate(q.from), longDate(q.to)),
        }));
      var events_ = itemList(t.eventsH, events, eventItem);
      var news_ = itemList(t.newsH, news, newsItem);
      if (events_) card.appendChild(events_);
      if (news_) card.appendChild(news_);
      if (!events_ && !news_) {
        card.appendChild(el('p', {
          'class': 'yr-quarter-empty', 'text': t.quarterEmpty,
        }));
      }
      grid.appendChild(card);
    });
    return grid;
  }

  function releaseList(ed) {
    if (!ed.releases.length) return null;
    var list = el('ul', { 'class': 'yr-releases' });
    ed.releases.slice().reverse().forEach(function (r) {
      list.appendChild(el('li', { 'class': 'yr-release' },
        el('a', {
          'class': 'yr-release-v',
          'href': RELEASE_BASE + r.version,
          'target': '_blank',
          'rel': 'noopener',
          'text': r.version,
        }),
        el('span', { 'class': 'yr-release-t', 'text': r.title })));
    });
    return list;
  }

  /* No .reveal on anything built here. Under .js-reveal the class
     holds an element at opacity 0 until site.js's observer adds .in,
     and that observer runs once at load over the markup already in the
     page, so a section inserted afterwards never gets it and the whole
     page renders blank. The fetch is the entrance. */
  function section(id, heading, body, lede) {
    if (!body) return null;
    var inner = el('div', { 'class': 'container' },
      el('h2', { 'text': heading }));
    if (lede) inner.appendChild(el('p', { 'class': 'lede', 'text': lede }));
    inner.appendChild(body);
    return el('section', { 'class': 'about-section', 'id': id }, inner);
  }

  function render(ed, mount) {
    var frag = document.createDocumentFragment();

    // Window note plus the hero stat strip. The window is only closed
    // once the year's last day has passed, and a closed year's figures
    // are final while an open one's are not, which the reader is told.
    var open = ed.window.to >= new Date().toISOString().slice(0, 10);
    var intro = el('div', { 'class': 'container' },
      el('p', {
        'class': 'lede',
        'text': open
          ? t.openWindow(longDate(ed.window.from))
          : t.closedWindow(longDate(ed.window.from), longDate(ed.window.to)),
      }),
      statStrip(ed.stats));
    var lede = pick(ed.hand && ed.hand.lede);
    if (lede) {
      intro.insertBefore(el('p', { 'class': 'lede', 'text': lede }),
        intro.firstChild);
    }
    frag.appendChild(el('section', { 'class': 'about-section' }, intro));

    var spark = sparkline(ed.memberSeries || []);
    if (spark) {
      var counts = ed.memberSeries.map(function (p) { return p.members; });
      var growth = el('figure', { 'class': 'yr-spark-figure' }, spark,
        el('figcaption', {
          'text': t.growthCaption(
            counts[0], counts[counts.length - 1],
            monthLabel(ed.memberSeries[0].month),
            monthLabel(ed.memberSeries[ed.memberSeries.length - 1].month)),
        }));
      frag.appendChild(section('growth', t.growthH, growth));
    }

    var themes = themeBars(ed.themes || []);
    if (themes) frag.appendChild(section('themes', t.themesH, themes));

    frag.appendChild(section('quarters', t.quartersH, quarterCards(ed)));

    var outputs = (ed.outputs || []).length
      ? itemList(t.outputsH, ed.outputs, outputItem)
      : el('p', { 'class': 'lede', 'text': t.noOutputs });
    frag.appendChild(section('outputs', t.outputsH, outputs));

    var releases = releaseList(ed);
    if (releases) {
      frag.appendChild(section('releases', t.releasesH, releases,
        t.releaseCount(ed.stats.releases, ed.releases.length)));
    }

    var outlook = pick(ed.hand && ed.hand.outlook);
    if (outlook) {
      frag.appendChild(section('outlook', t.outlookH,
        el('p', { 'class': 'lede', 'text': outlook })));
    }

    mount.textContent = '';
    mount.appendChild(frag);
  }

  var mount = document.querySelector('[data-year-review]');
  if (!mount) return;

  fetch('data/year-review.json')
    .then(function (r) { return r.json(); })
    .then(function (data) {
      var editions = (data && data.editions) || [];
      if (!editions.length) return;
      // One edition today. A year selector arrives with the second,
      // and the newest is the one a visitor lands on.
      render(editions[editions.length - 1], mount);
    })
    .catch(function (e) {
      if (window.console && console.debug) {
        console.debug('year in review skipped:', e);
      }
    });
})();
