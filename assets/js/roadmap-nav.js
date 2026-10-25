/* Roadmap quarter navigator (shared EN/FR/DE).
 *
 * Builds a jump list from the quarter headings already on the page
 * (.rm-quarter[id] plus the Under-watch section) and prepends it to
 * [data-rm-body]. CSS lays it out as a sticky side rail on wide
 * screens and a sticky chip bar below that. Each node carries the
 * quarter's status (from the cards in its timeline), an entry count,
 * and a "Now" tag on the quarter holding today's date. A scroll
 * listener marks the quarter on screen with aria-current and sets
 * --rm-fill for the rail line. Clicks are smooth-scrolled by the
 * shared [data-jump-nav] handler in site.js. Without JS nothing is
 * inserted and the page reads as before.
 */
(function () {
  const body = document.querySelector('[data-rm-body]');
  if (!body) return;
  const lang = (document.documentElement.lang || 'en').toLowerCase().slice(0, 2);
  const L = ({
    en: { nav: 'Jump to a quarter', now: 'Now', entries: (n) => n === 1 ? '1 entry' : `${n} entries` },
    fr: { nav: 'Aller à un trimestre', now: 'Actuel', entries: (n) => n === 1 ? '1 entrée' : `${n} entrées` },
    de: { nav: 'Zu einem Quartal springen', now: 'Jetzt', entries: (n) => n === 1 ? '1 Eintrag' : `${n} Einträge` },
  })[lang] || { nav: 'Jump to a quarter', now: 'Now', entries: (n) => `${n} entries` };

  const today = new Date();
  const nowId = `q${Math.floor(today.getMonth() / 3) + 1}-${today.getFullYear()}`;

  function status(ol) {
    if (!ol) return 'planned';
    if (ol.querySelector(':scope > .rm-entry.in-progress')) return 'progress';
    if (ol.querySelector(':scope > .rm-entry.planned')) return 'planned';
    return 'shipped';
  }

  // Each section: { el: scroll target, id, label, status, count }.
  const sections = [];
  body.querySelectorAll('.rm-quarter[id]').forEach((q) => {
    const h = q.querySelector('h2');
    let ol = q.nextElementSibling;
    while (ol && !ol.matches('ol.rm-timeline')) ol = ol.nextElementSibling;
    sections.push({
      el: q, id: q.id, label: h ? h.textContent.trim() : q.id,
      status: status(ol),
      count: ol ? ol.querySelectorAll(':scope > .rm-entry').length : 0,
    });
  });
  const watchHead = document.getElementById('under-watch-h');
  const watch = watchHead && watchHead.closest('section');
  if (watch) {
    if (!watch.id) watch.id = 'under-watch';
    sections.push({
      el: watch, id: watch.id,
      label: watchHead.firstChild ? watchHead.firstChild.textContent.trim() : '',
      status: 'watch',
      count: watch.querySelectorAll('.rm-later-item').length,
    });
  }
  if (sections.length < 2) return;

  const nav = document.createElement('nav');
  nav.className = 'rm-nav';
  nav.setAttribute('data-jump-nav', '');
  nav.setAttribute('aria-label', L.nav);
  const list = document.createElement('ol');
  list.className = 'rm-nav-list';
  const links = sections.map((s) => {
    const li = document.createElement('li');
    li.className = 'rm-nav-item';
    li.dataset.status = s.status;
    const a = document.createElement('a');
    a.href = '#' + s.id;
    a.innerHTML = '<span class="rm-nav-dot" aria-hidden="true"></span>';
    const label = document.createElement('span');
    label.className = 'rm-nav-label';
    label.textContent = s.label;
    a.appendChild(label);
    if (s.id === nowId) {
      const t = document.createElement('span');
      t.className = 'rm-nav-now';
      t.textContent = L.now;
      a.appendChild(t);
    }
    if (s.count) {
      const c = document.createElement('span');
      c.className = 'rm-nav-count';
      c.textContent = String(s.count);
      c.title = L.entries(s.count);
      a.appendChild(c);
    }
    li.appendChild(a);
    list.appendChild(li);
    return a;
  });
  nav.appendChild(list);
  body.insertBefore(nav, body.firstChild);

  // site.js keeps scroll-padding-top at the fixed header's bottom + 14px.
  const headerLine = () =>
    (parseFloat(document.documentElement.style.scrollPaddingTop) || 92);
  const reduce = window.matchMedia
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  // Matches the breakpoint in roadmap.css where the bar becomes a rail.
  const rail = window.matchMedia('(min-width: 1320px)');

  let active = -1;
  function update() {
    document.documentElement.style.setProperty('--rm-nav-top', (headerLine() - 14) + 'px');
    // In bar mode the sticky bar sits under the header and hides
    // its own height of content, so the reading line moves down.
    const line = headerLine() + (rail.matches ? 0 : nav.offsetHeight) + 24;
    let i = 0;
    sections.forEach((s, k) => { if (s.el.getBoundingClientRect().top <= line) i = k; });
    // The last section may never reach the line on a tall screen.
    if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2
        && sections[sections.length - 1].el.getBoundingClientRect().top < window.innerHeight) {
      i = sections.length - 1;
    }
    if (i === active) return;
    active = i;
    links.forEach((a, k) => {
      if (k === i) a.setAttribute('aria-current', 'location');
      else a.removeAttribute('aria-current');
    });
    nav.style.setProperty('--rm-fill', String(i / (sections.length - 1)));
    // Keep the active chip visible in the horizontal bar, without
    // touching the page's vertical scroll.
    if (list.scrollWidth > list.clientWidth) {
      const a = links[i];
      list.scrollTo({
        left: a.offsetLeft - (list.clientWidth - a.offsetWidth) / 2,
        behavior: reduce ? 'auto' : 'smooth',
      });
    }
  }

  let queued = false;
  const schedule = () => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => { queued = false; update(); });
  };
  window.addEventListener('scroll', schedule, { passive: true });
  window.addEventListener('resize', () => { active = -1; schedule(); }, { passive: true });
  update();
})();
