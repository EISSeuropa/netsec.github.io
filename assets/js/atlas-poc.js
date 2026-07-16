/* The NetSec Atlas — proof of concept renderer (#764).
   Vanilla, no dependencies. Reads data/atlas.json (built by
   scripts/build-atlas.py from wg.json): 4 Working-Group hubs + one node per
   roster person, bipartite person->WG edges. A small hand-rolled force
   layout runs on canvas; people with several WGs settle between their hubs,
   which is the point of the picture. Deterministic seed, DPR-aware,
   dark/light aware (colours re-read from CSS variables on theme flip),
   reduced motion renders the settled layout without animating. */
(function () {
  'use strict';
  const canvas = document.getElementById('atlas-canvas');
  const card = document.getElementById('atlas-card');
  const statsEl = document.getElementById('atlas-stats');
  const controls = document.querySelector('.atlas-controls');
  if (!canvas || !canvas.getContext) return;
  const ctx = canvas.getContext('2d');

  const reduceMotion = window.matchMedia
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Deterministic RNG so the map is the same on every load.
  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  const cssVar = (name) =>
    getComputedStyle(document.documentElement).getPropertyValue(name).trim();

  let theme = {};
  function readTheme() {
    theme = {
      wg: { 1: cssVar('--wg-1'), 2: cssVar('--wg-2'), 3: cssVar('--wg-3'), 4: cssVar('--wg-4') },
      ink: cssVar('--ink') || '#0b1220',
      muted: cssVar('--muted') || '#5a6679',
      accent: cssVar('--accent-2') || '#0a84ff',
      dark: document.documentElement.classList.contains('dark'),
    };
  }
  readTheme();

  let hubs = [], people = [], edges = [], byId = {};
  const activeWG = new Set([1, 2, 3, 4]);
  let hovered = null, draggingHub = null;
  let W = 0, H = 0, dpr = 1;

  function resize() {
    const r = canvas.getBoundingClientRect();
    dpr = window.devicePixelRatio || 1;
    W = r.width; H = r.height;
    canvas.width = Math.round(W * dpr);
    canvas.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  // ── Layout ──
  // Hubs sit on a wide ellipse; each person starts at the centroid of their
  // hubs plus seeded jitter, then the force pass separates them.
  function seedPositions() {
    const rand = mulberry32(24154);   // the Action number, for the story
    const cx = W / 2, cy = H / 2;
    hubs.forEach((h, i) => {
      const ang = (i / hubs.length) * Math.PI * 2 - Math.PI / 2 - Math.PI / 4;
      h.x = cx + Math.cos(ang) * W * 0.27;
      h.y = cy + Math.sin(ang) * H * 0.28;
      h.r = Math.max(26, Math.sqrt(h.memberCount) * 4.4);
    });
    people.forEach(p => {
      const hs = p.hubs.map(id => byId[id]);
      const mx = hs.reduce((s, h) => s + h.x, 0) / hs.length;
      const my = hs.reduce((s, h) => s + h.y, 0) / hs.length;
      p.x = mx + (rand() - 0.5) * 140;
      p.y = my + (rand() - 0.5) * 140;
      p.vx = 0; p.vy = 0;
      p.r = p.slug ? 5 : 3.5;
    });
  }

  function tick() {
    // Springs: each person is pulled toward each of their hubs.
    people.forEach(p => {
      p.hubs.forEach(id => {
        const h = byId[id];
        const dx = h.x - p.x, dy = h.y - p.y;
        const d = Math.hypot(dx, dy) || 1;
        // Rest length past the hub's rim, longer for single-WG members so
        // clusters breathe; multi-WG people are pulled from both sides anyway.
        const rest = h.r + 60;
        const f = (d - rest) * 0.004;
        p.vx += (dx / d) * f * 60;
        p.vy += (dy / d) * f * 60;
      });
      // Gentle centering so satellites cannot drift out of frame.
      p.vx += (W / 2 - p.x) * 0.0004;
      p.vy += (H / 2 - p.y) * 0.0004;
    });
    // Pairwise repulsion between people (146² is trivial for canvas work).
    for (let i = 0; i < people.length; i++) {
      for (let j = i + 1; j < people.length; j++) {
        const a = people[i], b = people[j];
        let dx = b.x - a.x, dy = b.y - a.y;
        let d2 = dx * dx + dy * dy;
        if (d2 > 4600 || d2 === 0) continue;
        const d = Math.sqrt(d2);
        const f = 26 / d2;
        dx /= d; dy /= d;
        a.vx -= dx * f * 60; a.vy -= dy * f * 60;
        b.vx += dx * f * 60; b.vy += dy * f * 60;
      }
    }
    // Keep people off the hub discs.
    people.forEach(p => {
      hubs.forEach(h => {
        const dx = p.x - h.x, dy = p.y - h.y;
        const d = Math.hypot(dx, dy) || 1;
        const min = h.r + 14;
        if (d < min) { p.x = h.x + (dx / d) * min; p.y = h.y + (dy / d) * min; }
      });
      p.vx *= 0.82; p.vy *= 0.82;
      p.x += p.vx * 0.016; p.y += p.vy * 0.016;
      p.x = Math.max(10, Math.min(W - 10, p.x));
      p.y = Math.max(10, Math.min(H - 10, p.y));
    });
  }

  // ── Paint ──
  function hubColour(h) { return theme.wg[h.number] || theme.accent; }
  function personVisible(p) { return p.hubs.some(id => activeWG.has(byId[id].number)); }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    const hoverIds = hovered
      ? new Set([hovered.id].concat(hovered.hubs || [], hovered.people || []))
      : null;

    edges.forEach(e => {
      const p = byId[e.source], h = byId[e.target];
      if (!personVisible(p) || !activeWG.has(h.number)) return;
      const lit = hoverIds && (hoverIds.has(p.id) && (hovered.type === 'wg' ? h.id === hovered.id : true));
      ctx.strokeStyle = hubColour(h);
      ctx.globalAlpha = lit ? 0.55 : (hoverIds ? 0.05 : (theme.dark ? 0.16 : 0.13));
      ctx.lineWidth = lit ? 1.4 : 1;
      ctx.beginPath();
      ctx.moveTo(p.x, p.y);
      // A slight bow keeps overlapping edges legible.
      ctx.quadraticCurveTo((p.x + h.x) / 2 + (p.y - h.y) * 0.08, (p.y + h.y) / 2 + (h.x - p.x) * 0.08, h.x, h.y);
      ctx.stroke();
    });
    ctx.globalAlpha = 1;

    people.forEach(p => {
      if (!personVisible(p)) return;
      const dim = hoverIds && !hoverIds.has(p.id);
      ctx.globalAlpha = dim ? 0.18 : 1;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.id === (hovered && hovered.id) ? p.r + 2 : p.r, 0, Math.PI * 2);
      ctx.fillStyle = p.slug ? theme.accent : '#9aa7bd';
      ctx.fill();
      if (p.slug) {
        ctx.strokeStyle = theme.dark ? 'rgba(255,255,255,.5)' : 'rgba(255,255,255,.9)';
        ctx.lineWidth = 1.2;
        ctx.stroke();
      }
    });
    ctx.globalAlpha = 1;

    hubs.forEach(h => {
      const dim = (hoverIds && !hoverIds.has(h.id)) || !activeWG.has(h.number);
      ctx.globalAlpha = dim ? 0.25 : 1;
      ctx.beginPath();
      ctx.arc(h.x, h.y, h.r, 0, Math.PI * 2);
      ctx.fillStyle = hubColour(h);
      ctx.fill();
      ctx.font = '700 13px Lexend, Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillStyle = '#fff';
      ctx.fillText('WG' + h.number, h.x, h.y - 2);
      ctx.font = '600 10px Inter, sans-serif';
      ctx.fillStyle = 'rgba(255,255,255,.85)';
      ctx.fillText(h.memberCount + ' members', h.x, h.y + 12);
      ctx.globalAlpha = 1;
      ctx.font = '600 12px Inter, sans-serif';
      ctx.fillStyle = theme.muted;
      ctx.fillText(h.name, h.x, h.y + h.r + 18);
    });
  }

  // ── Interaction ──
  function nodeAt(mx, my) {
    for (const h of hubs) if (Math.hypot(mx - h.x, my - h.y) <= h.r) return h;
    let best = null, bd = 12;
    for (const p of people) {
      if (!personVisible(p)) continue;
      const d = Math.hypot(mx - p.x, my - p.y);
      if (d < bd) { bd = d; best = p; }
    }
    return best;
  }

  function showCard(node, mx, my) {
    if (!node || node.type === 'wg') { card.classList.remove('is-on'); card.setAttribute('aria-hidden', 'true'); return; }
    const wgs = node.hubs.map(id => byId[id]);
    card.innerHTML =
      '<div class="nm"></div><div class="meta"></div>'
      + '<div class="wgs">' + wgs.map(h =>
          '<span class="wgp" style="background:' + hubColour(h) + '">WG' + h.number + '</span>').join('') + '</div>'
      + (node.slug ? '<div class="go">View profile &rarr;</div>' : '');
    card.querySelector('.nm').textContent = node.name;
    card.querySelector('.meta').textContent = node.country || '';
    const stage = canvas.parentElement.getBoundingClientRect();
    card.style.left = Math.min(mx + 16, stage.width - 290) + 'px';
    card.style.top = Math.max(8, my - 14) + 'px';
    card.classList.add('is-on');
    card.setAttribute('aria-hidden', 'false');
  }

  canvas.addEventListener('pointermove', (e) => {
    const r = canvas.getBoundingClientRect();
    const mx = e.clientX - r.left, my = e.clientY - r.top;
    if (draggingHub) {
      draggingHub.x = mx; draggingHub.y = my;
      if (reduceMotion) { settle(120); }
      draw();
      return;
    }
    hovered = nodeAt(mx, my);
    canvas.classList.toggle('is-link', !!(hovered && hovered.slug));
    showCard(hovered, mx, my);
    draw();
  });
  canvas.addEventListener('pointerleave', () => {
    hovered = null; showCard(null); draw();
  });
  canvas.addEventListener('pointerdown', (e) => {
    const r = canvas.getBoundingClientRect();
    const n = nodeAt(e.clientX - r.left, e.clientY - r.top);
    if (n && n.type === 'wg') { draggingHub = n; canvas.setPointerCapture(e.pointerId); }
  });
  canvas.addEventListener('pointerup', (e) => {
    if (draggingHub) { draggingHub = null; return; }
    const r = canvas.getBoundingClientRect();
    const n = nodeAt(e.clientX - r.left, e.clientY - r.top);
    if (n && n.slug) location.href = 'people/' + n.slug + '.html';
  });

  // ── Boot ──
  function settle(n) { for (let i = 0; i < n; i++) tick(); }

  fetch('data/atlas.json', { cache: 'no-cache' })
    .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(data => {
      hubs = data.nodes.filter(n => n.type === 'wg');
      people = data.nodes.filter(n => n.type === 'person');
      edges = data.edges;
      byId = {};
      data.nodes.forEach(n => { byId[n.id] = n; });
      people.forEach(p => { p.hubs = []; });
      hubs.forEach(h => { h.people = []; });
      edges.forEach(e => { byId[e.source].hubs.push(e.target); byId[e.target].people.push(e.source); });

      // Stats strip from the data, not hand-maintained numbers.
      const countries = new Set(people.map(p => p.country).filter(Boolean));
      const bios = people.filter(p => p.slug).length;
      [['' + people.length, 'people on WG rosters'],
       ['' + countries.size, 'countries'],
       ['' + edges.length, 'Working-Group memberships'],
       [bios + ' / ' + people.length, 'with a directory profile']]
        .forEach(([b, s]) => {
          const el = document.createElement('div');
          el.className = 'atlas-stat';
          const bb = document.createElement('b'); bb.textContent = b;
          const ss = document.createElement('span'); ss.textContent = s;
          el.appendChild(bb); el.appendChild(ss);
          statsEl.appendChild(el);
        });

      // One filter chip per hub, coloured like its disc.
      hubs.forEach(h => {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'atlas-wg-chip';
        b.style.background = hubColour(h);
        b.textContent = 'WG' + h.number + ' · ' + h.name;
        b.setAttribute('aria-pressed', 'true');
        b.addEventListener('click', () => {
          if (activeWG.has(h.number)) activeWG.delete(h.number);
          else activeWG.add(h.number);
          b.setAttribute('aria-pressed', activeWG.has(h.number) ? 'true' : 'false');
          draw();
        });
        controls.appendChild(b);
      });

      resize();
      seedPositions();
      if (reduceMotion) { settle(400); draw(); return; }
      let frames = 0;
      (function loop() {
        tick(); draw();
        if (++frames < 420) requestAnimationFrame(loop);
      })();
    })
    .catch(() => {
      statsEl.textContent = 'The atlas data could not be loaded.';
    });

  window.addEventListener('resize', () => { resize(); settle(60); draw(); });
  // Theme flips (the header moon toggle) re-colour without a reload.
  new MutationObserver(() => { readTheme(); draw(); })
    .observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
})();
