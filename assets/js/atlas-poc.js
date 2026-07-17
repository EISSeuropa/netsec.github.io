/* The NetSec Atlas — proof of concept renderer (#764).
   Vanilla, no dependencies. Reads data/atlas.json (scripts/build-atlas.py):
   one deduped person universe (WG rosters union directory bios) under three
   graph layers, rendered as two lenses plus two overlays:

     Lens "Working Groups"  — 4 WG hubs, roster-membership edges.
     Lens "Research themes" — 14 theme hubs from the bios: the map of the field.
     Overlay "ESSC co-panels" — person-to-person arcs for shared conference
       panels (weight = shared panels), on either lens.
     Overlay "Mentorship"   — rings on the dots: offering and/or seeking.

   Members with a headshot render as tiny circular photos, so the map has
   faces. Hand-rolled force layout, deterministic seed, DPR-aware, dark/light
   from CSS variables (re-read on theme flip), reduced motion renders the
   settled layout without animating. */
(function () {
  'use strict';
  const canvas = document.getElementById('atlas-canvas');
  const card = document.getElementById('atlas-card');
  const statsEl = document.getElementById('atlas-stats');
  const hubChipsEl = document.getElementById('atlas-hub-chips');
  const lensEl = document.getElementById('atlas-lens');
  const overlaysEl = document.getElementById('atlas-overlays');
  if (!canvas || !canvas.getContext) return;
  const ctx = canvas.getContext('2d');

  const reduceMotion = window.matchMedia
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  const cssVar = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

  // A stable colour per theme hub, drawn from a small brand-adjacent wheel
  // (the four WG hues plus rotations), so the theme lens is not a monochrome.
  const THEME_WHEEL = ['#0973de', '#10b981', '#8457ea', '#f59e0b', '#e2568c',
    '#0aa2c0', '#7a9a01', '#b3562e', '#5867dd', '#2e9e6a', '#a855f7', '#d97706',
    '#3b82f6', '#14b8a6'];

  let theme = {};
  function readTheme() {
    theme = {
      wg: { 1: cssVar('--wg-1'), 2: cssVar('--wg-2'), 3: cssVar('--wg-3'), 4: cssVar('--wg-4') },
      muted: cssVar('--muted') || '#5a6679',
      accent: cssVar('--accent-2') || '#0a84ff',
      offer: '#2e9e6a',
      seek: '#f59e0b',
      dark: document.documentElement.classList.contains('dark'),
    };
  }
  readTheme();

  // ── State ──
  let allHubs = { wg: [], theme: [] };
  let people = [], byId = {};
  let hubEdges = { wg: [], theme: [] };   // person->hub, keyed by lens
  let panelEdges = [];                    // person<->person, weighted
  let coauthorEdges = [];                 // person<->person, from publications
  let lens = 'wg';
  const activeHubs = new Set();           // hub ids active in the current lens
  const overlays = { panels: false, mentorship: false, coauthors: false };
  let hovered = null, draggingHub = null;
  let W = 0, H = 0, dpr = 1;
  const avatars = {};                     // person id -> loaded Image

  const hubs = () => allHubs[lens];
  const edges = () => hubEdges[lens];

  function resize() {
    const r = canvas.getBoundingClientRect();
    dpr = window.devicePixelRatio || 1;
    W = r.width; H = r.height;
    canvas.width = Math.round(W * dpr);
    canvas.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function hubColour(h) {
    if (h.type === 'wg') return theme.wg[h.number] || theme.accent;
    return THEME_WHEEL[h.wheel % THEME_WHEEL.length];
  }
  function personVisible(p) {
    return p.links[lens].some(id => activeHubs.has(id));
  }

  // ── Layout ──
  function seedPositions() {
    const rand = mulberry32(24154);
    const cx = W / 2, cy = H / 2;
    const hs = hubs();
    hs.forEach((h, i) => {
      const ang = (i / hs.length) * Math.PI * 2 - Math.PI / 2;
      h.x = cx + Math.cos(ang) * W * (hs.length > 6 ? 0.34 : 0.27);
      h.y = cy + Math.sin(ang) * H * (hs.length > 6 ? 0.36 : 0.28);
      h.r = h.type === 'wg'
        ? Math.max(26, Math.sqrt(h.memberCount) * 4.4)
        : Math.max(17, Math.sqrt(h.memberCount) * 4.2);
    });
    people.forEach(p => {
      const linked = p.links[lens].map(id => byId[id]).filter(Boolean);
      if (!linked.length) { p.x = -50; p.y = -50; p.vx = p.vy = 0; return; }
      const mx = linked.reduce((s, h) => s + h.x, 0) / linked.length;
      const my = linked.reduce((s, h) => s + h.y, 0) / linked.length;
      p.x = mx + (rand() - 0.5) * 130;
      p.y = my + (rand() - 0.5) * 130;
      p.vx = 0; p.vy = 0;
    });
  }

  function tick() {
    const visible = people.filter(p => p.links[lens].length);
    visible.forEach(p => {
      p.links[lens].forEach(id => {
        const h = byId[id];
        const dx = h.x - p.x, dy = h.y - p.y;
        const d = Math.hypot(dx, dy) || 1;
        const rest = h.r + (hubs().length > 6 ? 44 : 60);
        const f = (d - rest) * 0.004;
        p.vx += (dx / d) * f * 60;
        p.vy += (dy / d) * f * 60;
      });
      p.vx += (W / 2 - p.x) * 0.0004;
      p.vy += (H / 2 - p.y) * 0.0004;
    });
    for (let i = 0; i < visible.length; i++) {
      for (let j = i + 1; j < visible.length; j++) {
        const a = visible[i], b = visible[j];
        let dx = b.x - a.x, dy = b.y - a.y;
        const d2 = dx * dx + dy * dy;
        if (d2 > 4600 || d2 === 0) continue;
        const d = Math.sqrt(d2);
        const f = 26 / d2;
        dx /= d; dy /= d;
        a.vx -= dx * f * 60; a.vy -= dy * f * 60;
        b.vx += dx * f * 60; b.vy += dy * f * 60;
      }
    }
    visible.forEach(p => {
      hubs().forEach(h => {
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
  function draw() {
    ctx.clearRect(0, 0, W, H);
    const hoverIds = hovered
      ? new Set([hovered.id].concat(hovered.links ? hovered.links[lens] : [],
          hovered.people || [], hovered.panelPeers || [], hovered.coPeers || []))
      : null;

    edges().forEach(e => {
      const p = byId[e.source], h = byId[e.target];
      if (!personVisible(p) || !activeHubs.has(h.id)) return;
      const lit = hoverIds && hoverIds.has(p.id)
        && (hovered.type === 'person' || h.id === hovered.id);
      ctx.strokeStyle = hubColour(h);
      ctx.globalAlpha = lit ? 0.55 : (hoverIds ? 0.04 : (theme.dark ? 0.15 : 0.12));
      ctx.lineWidth = lit ? 1.4 : 1;
      ctx.beginPath();
      ctx.moveTo(p.x, p.y);
      ctx.quadraticCurveTo((p.x + h.x) / 2 + (p.y - h.y) * 0.08,
        (p.y + h.y) / 2 + (h.x - p.x) * 0.08, h.x, h.y);
      ctx.stroke();
    });
    ctx.globalAlpha = 1;

    if (overlays.coauthors) {
      coauthorEdges.forEach(e => {
        const a = byId[e.source], b = byId[e.target];
        if (!personVisible(a) || !personVisible(b)) return;
        const lit = hoverIds && (hoverIds.has(a.id) && hoverIds.has(b.id));
        ctx.strokeStyle = theme.dark ? '#5fd4e8' : '#0aa2c0';
        ctx.globalAlpha = lit ? 0.9 : (hoverIds ? 0.06 : 0.45);
        ctx.lineWidth = 0.8 + e.weight * 0.8;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.quadraticCurveTo((a.x + b.x) / 2 + (a.y - b.y) * 0.14,
          (a.y + b.y) / 2 + (b.x - a.x) * 0.14, b.x, b.y);
        ctx.stroke();
      });
      ctx.globalAlpha = 1;
    }

    if (overlays.panels) {
      panelEdges.forEach(e => {
        const a = byId[e.source], b = byId[e.target];
        if (!personVisible(a) || !personVisible(b)) return;
        const lit = hoverIds && (hoverIds.has(a.id) && hoverIds.has(b.id));
        ctx.strokeStyle = theme.dark ? '#ff9db8' : '#d23a68';
        ctx.globalAlpha = lit ? 0.9 : (hoverIds ? 0.06 : 0.4);
        ctx.lineWidth = 0.8 + e.weight * 0.8;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.quadraticCurveTo((a.x + b.x) / 2 + (a.y - b.y) * 0.18,
          (a.y + b.y) / 2 + (b.x - a.x) * 0.18, b.x, b.y);
        ctx.stroke();
      });
      ctx.globalAlpha = 1;
    }

    people.forEach(p => {
      if (!personVisible(p)) return;
      const dim = hoverIds && !hoverIds.has(p.id);
      const r = (p.id === (hovered && hovered.id)) ? p.r + 2 : p.r;
      ctx.globalAlpha = dim ? 0.15 : 1;
      const img = avatars[p.id];
      if (img && img.complete && img.naturalWidth) {
        ctx.save();
        ctx.beginPath();
        ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
        ctx.clip();
        ctx.drawImage(img, p.x - r, p.y - r, r * 2, r * 2);
        ctx.restore();
        ctx.beginPath();
        ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
        ctx.strokeStyle = theme.dark ? 'rgba(255,255,255,.55)' : 'rgba(255,255,255,.95)';
        ctx.lineWidth = 1.3;
        ctx.stroke();
      } else {
        ctx.beginPath();
        ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
        ctx.fillStyle = p.slug ? theme.accent : '#9aa7bd';
        ctx.fill();
      }
      if (overlays.mentorship && p.mentorship) {
        if (p.mentorship.indexOf('mentor') !== -1) {
          ctx.beginPath(); ctx.arc(p.x, p.y, r + 3, 0, Math.PI * 2);
          ctx.strokeStyle = theme.offer; ctx.lineWidth = 2; ctx.stroke();
        }
        if (p.mentorship.indexOf('mentee') !== -1) {
          ctx.beginPath(); ctx.arc(p.x, p.y, r + (p.mentorship.length > 1 ? 6 : 3), 0, Math.PI * 2);
          ctx.strokeStyle = theme.seek; ctx.lineWidth = 2; ctx.stroke();
        }
      }
    });
    ctx.globalAlpha = 1;

    hubs().forEach(h => {
      const dim = (hoverIds && !hoverIds.has(h.id)) || !activeHubs.has(h.id);
      ctx.globalAlpha = dim ? 0.22 : 1;
      ctx.beginPath();
      ctx.arc(h.x, h.y, h.r, 0, Math.PI * 2);
      ctx.fillStyle = hubColour(h);
      ctx.fill();
      ctx.textAlign = 'center';
      if (h.type === 'wg') {
        ctx.font = '700 13px Lexend, Inter, sans-serif';
        ctx.fillStyle = '#fff';
        ctx.fillText('WG' + h.number, h.x, h.y - 2);
        ctx.font = '600 10px Inter, sans-serif';
        ctx.fillStyle = 'rgba(255,255,255,.85)';
        ctx.fillText(h.memberCount + ' members', h.x, h.y + 12);
      } else {
        ctx.font = '700 12px Lexend, Inter, sans-serif';
        ctx.fillStyle = '#fff';
        ctx.fillText(String(h.memberCount), h.x, h.y + 4);
      }
      ctx.globalAlpha = 1;
      ctx.font = '600 11px Inter, sans-serif';
      ctx.fillStyle = theme.muted;
      const label = h.type === 'wg' ? h.name
        : (h.name.length > 26 ? h.name.slice(0, 25) + '…' : h.name);
      ctx.fillText(label, h.x, h.y + h.r + 15);
    });
  }

  // ── Interaction ──
  function nodeAt(mx, my) {
    for (const h of hubs()) if (Math.hypot(mx - h.x, my - h.y) <= h.r) return h;
    let best = null, bd = 13;
    for (const p of people) {
      if (!personVisible(p)) continue;
      const d = Math.hypot(mx - p.x, my - p.y);
      if (d < bd) { bd = d; best = p; }
    }
    return best;
  }

  function showCard(node, mx, my) {
    if (!node) { card.classList.remove('is-on'); card.setAttribute('aria-hidden', 'true'); return; }
    if (node.type !== 'person') {
      card.innerHTML = '<div class="nm"></div><div class="meta"></div>';
      card.querySelector('.nm').textContent = node.name;
      card.querySelector('.meta').textContent = node.memberCount
        + (node.type === 'wg' ? ' members' : ' people work here');
    } else {
      const wgs = node.links.wg.map(id => byId[id]);
      const themes = node.links.theme.map(id => byId[id]);
      card.innerHTML =
        (node.photo ? '<img class="face" alt="">' : '')
        + '<div class="nm"></div><div class="meta"></div>'
        + '<div class="wgs">' + wgs.map(h =>
            '<span class="wgp" style="background:' + hubColour(h) + '">WG' + h.number + '</span>').join('') + '</div>'
        + (themes.length ? '<div class="themes"></div>' : '')
        + (node.panelPeers && node.panelPeers.length
            ? '<div class="panels">Shared an ESSC 2026 panel with ' + node.panelPeers.length + ' member' + (node.panelPeers.length > 1 ? 's' : '') + '</div>' : '')
        + (node.coPeers && node.coPeers.length
            ? '<div class="coauth">Co-authored with ' + node.coPeers.length + ' member' + (node.coPeers.length > 1 ? 's' : '') + '</div>' : '')
        + (node.slug ? '<div class="go">View profile &rarr;</div>' : '');
      if (node.photo) card.querySelector('.face').src = node.photo;
      card.querySelector('.nm').textContent = node.name;
      card.querySelector('.meta').textContent = node.country || '';
      if (themes.length) card.querySelector('.themes').textContent =
        themes.slice(0, 3).map(t => t.name).join(' · ') + (themes.length > 3 ? ' +' + (themes.length - 3) : '');
    }
    const stage = canvas.parentElement.getBoundingClientRect();
    card.style.left = Math.min(mx + 16, stage.width - 300) + 'px';
    card.style.top = Math.max(8, my - 14) + 'px';
    card.classList.add('is-on');
    card.setAttribute('aria-hidden', 'false');
  }

  canvas.addEventListener('pointermove', (e) => {
    const r = canvas.getBoundingClientRect();
    const mx = e.clientX - r.left, my = e.clientY - r.top;
    if (draggingHub) { draggingHub.x = mx; draggingHub.y = my; draw(); return; }
    hovered = nodeAt(mx, my);
    canvas.classList.toggle('is-link', !!(hovered && hovered.slug));
    showCard(hovered, mx, my);
    draw();
  });
  canvas.addEventListener('pointerleave', () => { hovered = null; showCard(null); draw(); });
  canvas.addEventListener('pointerdown', (e) => {
    const r = canvas.getBoundingClientRect();
    const n = nodeAt(e.clientX - r.left, e.clientY - r.top);
    if (n && n.type !== 'person') { draggingHub = n; canvas.setPointerCapture(e.pointerId); }
  });
  canvas.addEventListener('pointerup', (e) => {
    if (draggingHub) { draggingHub = null; return; }
    const r = canvas.getBoundingClientRect();
    const n = nodeAt(e.clientX - r.left, e.clientY - r.top);
    if (n && n.slug) location.href = 'people/' + n.slug + '.html';
  });

  // ── Controls ──
  function chip(label, pressed, onClick, bg) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'atlas-wg-chip';
    if (bg) b.style.background = bg; else b.classList.add('is-plain');
    b.textContent = label;
    b.setAttribute('aria-pressed', pressed ? 'true' : 'false');
    b.addEventListener('click', () => onClick(b));
    return b;
  }

  function buildHubChips() {
    hubChipsEl.replaceChildren();
    hubs().forEach(h => {
      hubChipsEl.appendChild(chip(
        h.type === 'wg' ? 'WG' + h.number : h.name,
        activeHubs.has(h.id),
        (b) => {
          if (activeHubs.has(h.id)) activeHubs.delete(h.id);
          else activeHubs.add(h.id);
          b.setAttribute('aria-pressed', activeHubs.has(h.id) ? 'true' : 'false');
          draw();
        },
        hubColour(h)));
    });
  }

  let animFrames = 0;
  function reheat(frames) {
    if (reduceMotion) { for (let i = 0; i < 400; i++) tick(); draw(); return; }
    const wasRunning = animFrames > 0;
    animFrames = frames;
    if (wasRunning) return;
    (function loop() {
      tick(); draw();
      if (--animFrames > 0) requestAnimationFrame(loop);
    })();
  }

  function switchLens(next) {
    lens = next;
    activeHubs.clear();
    hubs().forEach(h => activeHubs.add(h.id));
    lensEl.querySelectorAll('button').forEach(b =>
      b.setAttribute('aria-pressed', b.dataset.lens === lens ? 'true' : 'false'));
    buildHubChips();
    seedPositions();
    reheat(300);
  }

  // ── Boot ──
  fetch('data/atlas.json', { cache: 'no-cache' })
    .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(data => {
      allHubs.wg = data.nodes.filter(n => n.type === 'wg');
      allHubs.theme = data.nodes.filter(n => n.type === 'theme');
      allHubs.theme.forEach((h, i) => { h.wheel = i; });
      people = data.nodes.filter(n => n.type === 'person');
      byId = {};
      data.nodes.forEach(n => { byId[n.id] = n; });
      people.forEach(p => { p.links = { wg: [], theme: [] }; p.panelPeers = []; p.coPeers = []; p.r = p.photo ? 8 : (p.slug ? 5 : 3.5); });
      allHubs.wg.concat(allHubs.theme).forEach(h => { h.people = []; });
      data.edges.forEach(e => {
        if (e.type === 'panel') {
          panelEdges.push(e);
          byId[e.source].panelPeers.push(e.target);
          byId[e.target].panelPeers.push(e.source);
        } else if (e.type === 'coauthor') {
          coauthorEdges.push(e);
          byId[e.source].coPeers.push(e.target);
          byId[e.target].coPeers.push(e.source);
        } else if (e.target.indexOf('wg-') === 0) {
          byId[e.source].links.wg.push(e.target);
          byId[e.target].people.push(e.source);
        } else {
          byId[e.source].links.theme.push(e.target);
          byId[e.target].people.push(e.source);
        }
      });

      // Faces: lazy-load headshots; each arrival repaints once.
      people.forEach(p => {
        if (!p.photo) return;
        const img = new Image();
        img.src = p.photo;
        img.onload = () => { avatars[p.id] = img; draw(); };
      });

      const countries = new Set(people.map(p => p.country).filter(Boolean));
      [['' + people.length, 'people in the network'],
       ['' + countries.size, 'countries'],
       ['' + allHubs.theme.length, 'research themes'],
       ['' + panelEdges.length, 'ESSC co-panel ties'],
       ...(coauthorEdges.length ? [['' + coauthorEdges.length, 'co-authored outputs']] : []),
       [data.stats.people_with_bios + ' / ' + people.length, 'with a directory profile']]
        .forEach(([b, s]) => {
          const el = document.createElement('div');
          el.className = 'atlas-stat';
          const bb = document.createElement('b'); bb.textContent = b;
          const ss = document.createElement('span'); ss.textContent = s;
          el.appendChild(bb); el.appendChild(ss);
          statsEl.appendChild(el);
        });

      [['wg', 'Working Groups'], ['theme', 'Research themes']].forEach(([v, label]) => {
        const b = chip(label, v === lens, () => switchLens(v));
        b.dataset.lens = v;
        lensEl.appendChild(b);
      });
      const overlayDefs = [['panels', 'ESSC 2026 co-panels'], ['mentorship', 'Mentorship offers & requests']];
      // Co-authorship starts at zero edges (publications.json is empty until
      // D6 ships its first output) and the chip appears with the first one.
      if (coauthorEdges.length) {
        overlayDefs.push(['coauthors', 'Co-authored outputs']);
        const leg = document.getElementById('atlas-legend');
        if (leg) {
          const sp = document.createElement('span');
          sp.innerHTML = '<span class="sw" style="background:#0aa2c0"></span>co-authored an Action output';
          leg.insertBefore(sp, leg.lastElementChild);
        }
      }
      overlayDefs.forEach(([k, label]) => {
        overlaysEl.appendChild(chip(label, overlays[k], (b) => {
          overlays[k] = !overlays[k];
          b.setAttribute('aria-pressed', overlays[k] ? 'true' : 'false');
          draw();
        }));
      });

      resize();
      switchLens('wg');
    })
    .catch(() => { statsEl.textContent = 'The atlas data could not be loaded.'; });

  window.addEventListener('resize', () => { resize(); seedPositions(); reheat(120); });
  new MutationObserver(() => { readTheme(); draw(); })
    .observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
})();
