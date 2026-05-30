/* Roadmap milestone progress bars.
 *
 * Reads data/roadmap-progress.json (per-milestone closed/total, synced
 * from the repo's GitHub milestones by scripts/sync-roadmap-progress.py)
 * and renders a progress bar into each *in-flight* roadmap card that
 * carries a data-milestone attribute. Shipped cards are left alone.
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
    },
    fr: {
      aria: 'Progression du jalon',
      pct: function (n) { return n + ' %'; },
      done: function (c, t) {
        return c + ' tâche' + (c > 1 ? 's' : '') + ' sur ' + t
          + ' terminée' + (c > 1 ? 's' : '');
      },
    },
    de: {
      aria: 'Meilenstein-Fortschritt',
      pct: function (n) { return n + ' %'; },
      done: function (c, t) { return c + ' von ' + t + ' Aufgaben erledigt'; },
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

  fetch('data/roadmap-progress.json')
    .then(function (r) { return r.json(); })
    .then(function (data) {
      var ms = (data && data.milestones) || {};
      var cards = document.querySelectorAll('.rm-card[data-milestone]');
      Array.prototype.forEach.call(cards, function (card) {
        var entry = card.closest('.rm-entry');
        // In-flight only: skip shipped (and anything else) even if the
        // attribute lingers after a release.
        if (!entry || !(entry.classList.contains('planned')
            || entry.classList.contains('in-progress'))) return;

        var m = ms[card.getAttribute('data-milestone')];
        if (!m || !m.total || m.percent == null) return;

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
        var notes = card.querySelector('.notes-link');
        if (notes) card.insertBefore(bar, notes);
        else card.appendChild(bar);
      });
    })
    .catch(function (e) {
      if (window.console && console.debug) console.debug('roadmap progress skipped:', e);
    });
})();
