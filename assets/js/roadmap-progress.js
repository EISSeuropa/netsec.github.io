/* Roadmap milestone progress bars.
 *
 * Reads data/roadmap-progress.json (per-milestone closed/total, synced
 * from the repo's GitHub milestones by scripts/sync-roadmap-progress.py)
 * and renders a progress bar into each *in-flight* roadmap card that
 * carries a data-milestone attribute, plus a closed-issue tally beside
 * the release notes on each *shipped* card.
 *
 * Fail-soft: on any error, or for a card with no matching milestone, no
 * bar is added and the card renders exactly as authored. Same
 * render-from-JSON contract as assets/js/home-events.js.
 */
(function () {
  'use strict';

  var locale = (document.documentElement.lang || 'en').slice(0, 2);

  var I18N = {
    en: {
      aria: 'Milestone progress',
      pct: function (n) { return n + '%'; },
      done: function (c, t) { return c + ' of ' + t + ' task' + (t === 1 ? '' : 's') + ' done'; },
      doneCount: function (c) { return c + ' task' + (c === 1 ? '' : 's') + ' done'; },
    },
    fr: {
      aria: 'Progression du jalon',
      pct: function (n) { return n + ' %'; },
      done: function (c, t) {
        return c + ' tâche' + (c > 1 ? 's' : '') + ' sur ' + t
          + ' terminée' + (c > 1 ? 's' : '');
      },
      doneCount: function (c) {
        return c + ' tâche' + (c > 1 ? 's' : '') + ' terminée' + (c > 1 ? 's' : '');
      },
    },
    de: {
      aria: 'Meilenstein-Fortschritt',
      pct: function (n) { return n + ' %'; },
      done: function (c, t) { return c + ' von ' + t + ' Aufgaben erledigt'; },
      doneCount: function (c) { return (c === 1 ? '1 Aufgabe' : c + ' Aufgaben') + ' erledigt'; },
    },
  };
  var t = I18N[locale] || I18N.en;

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

  // Systematically mark the next incoming release as In progress. The
  // first still-planned version card (event-marker cards, which carry
  // .rm-milestone, are skipped) is the next-up release, so whichever
  // card that is gets promoted, with no per-release edit: when a release
  // ships and promote-roadmap.py flips its card to shipped, the
  // following one becomes In progress on the next render. The static
  // markup stays `planned` (so the release tooling still finds it); this
  // is a presentational promotion only. Runs synchronously, independent
  // of the progress-bar fetch below, so it works even if that fails.
  (function promoteNextInProgress() {
    var next = document.querySelector('.rm-entry.planned:not(.rm-milestone)');
    if (!next) return;
    var legend = document.querySelector('.rm-legend .rm-pill.in-progress');
    var label = (legend && legend.textContent.trim()) || 'In progress';
    next.classList.remove('planned');
    next.classList.add('in-progress');
    var pill = next.querySelector('.rm-pill');
    if (pill) {
      pill.classList.remove('planned');
      pill.classList.add('in-progress');
      // Rebuild: keep the leading status dot, swap the label text.
      pill.innerHTML = '<span class="dot" aria-hidden="true"></span>';
      pill.appendChild(document.createTextNode(label));
    }
  })();

  // Show how many items sit in the Under-watch section, counted from
  // the cards actually rendered there (so the badge always matches what
  // a visitor sees). Aria-hidden, since the heading text already reads
  // "Under watch" and the cards themselves are in the reading order.
  (function underWatchCount() {
    var list = document.querySelector('.rm-later-list');
    var head = document.getElementById('under-watch-h');
    if (!list || !head) return;
    var n = list.querySelectorAll('.rm-later-item').length;
    if (!n) return;
    head.appendChild(el('span', {
      'class': 'rm-later-count', 'aria-hidden': 'true', 'text': String(n),
    }));
  })();

  fetch('data/roadmap-progress.json')
    .then(function (r) { return r.json(); })
    .then(function (data) {
      var ms = (data && data.milestones) || {};
      var cards = document.querySelectorAll('.rm-card');
      Array.prototype.forEach.call(cards, function (card) {
        var entry = card.closest('.rm-entry');
        if (!entry) return;

        var notes = card.querySelector('.notes-link');

        // Milestone key: the explicit data-milestone attribute (in-flight
        // cards carry it), else parsed from the release-notes link, which
        // every shipped card points at (/releases/tag/vX.Y.Z). Deriving it
        // from the link means the closed-issue tally appears on every
        // historical shipped card without retrofitting the attribute.
        var key = card.getAttribute('data-milestone');
        if (!key && notes) {
          var mt = (notes.getAttribute('href') || '')
            .match(/\/releases\/tag\/(v\d+\.\d+\.\d+)/);
          if (mt) key = mt[1];
        }
        var m = key && ms[key];
        if (!m || !m.total) return;

        // Shipped: a closed-issue tally beside the release notes. (The
        // milestone is closed, so closed === total; we show the count
        // rather than a full progress bar.) Only from v1.8.1 onward:
        // milestones were sparsely tagged before then (v1.7.0 and v1.8.0
        // carried only a couple of issues each), so an earlier count
        // would undersell the release rather than inform.
        if (entry.classList.contains('shipped')) {
          var v = key.replace(/^v/, '').split('.');
          // Rank as MAJOR*10000 + MINOR*100 + PATCH (minor/patch < 100).
          // 10801 == v1.8.1, the first release with full milestone tagging.
          if (((+v[0]) * 10000 + (+v[1]) * 100 + (+v[2])) < 10801) return;
          var count = el('span', {
            'class': 'rm-shipped-count', 'text': t.doneCount(m.closed),
          });
          if (notes) card.insertBefore(count, notes);
          else card.appendChild(count);
          return;
        }

        // In-flight (planned, or promoted to in-progress above): a bar.
        if (!(entry.classList.contains('planned')
            || entry.classList.contains('in-progress'))) return;
        if (m.percent == null) return;

        var pct = Math.max(0, Math.min(100, m.percent));
        var bar = el('div', {
          'class': 'rm-progress',
          'role': 'progressbar',
          'aria-valuenow': String(pct),
          'aria-valuemin': '0',
          'aria-valuemax': '100',
          'aria-label': t.aria + ': ' + t.pct(pct),
        },
          el('div', { 'class': 'rm-progress-track' },
            el('div', { 'class': 'rm-progress-fill', 'style': 'width:' + pct + '%' })),
          el('div', { 'class': 'rm-progress-label',
            'text': t.pct(pct) + ' · ' + t.done(m.closed, m.total) })
        );

        // Sit the bar above the Release-notes link if there is one,
        // otherwise at the end of the card body.
        if (notes) card.insertBefore(bar, notes);
        else card.appendChild(bar);
      });
    })
    .catch(function (e) {
      if (window.console && console.debug) console.debug('roadmap progress skipped:', e);
    });
})();
