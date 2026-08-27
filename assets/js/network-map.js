/* The NetSec Network Map — proof of concept renderer (#764).
   Vanilla, no dependencies. Reads data/network-map.json (scripts/build-network-map.py):
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
  // Every string this file injects goes through T(), which defers to the
  // shared netsecT catalogue in site.js so the FR and DE pages render the
  // controls, stats, and hover card in their own language. Falls back to the
  // English key when site.js has not loaded, which keeps the map working if
  // the page is ever opened on its own again.
  const T = (s) => (window.netsecT ? window.netsecT(s) : s);
  // Singular and plural are separate catalogue keys rather than an English
  // "member" + "s", which no other language would build the same way.
  const peerLine = (one, many, n) => T(n === 1 ? one : many).replace('{n}', n);
  const canvas = document.getElementById('network-map-canvas');
  const card = document.getElementById('network-map-card');
  const statsEl = document.getElementById('network-map-stats');
  const hubChipsEl = document.getElementById('network-map-hub-chips');
  const lensEl = document.getElementById('network-map-lens');
  const overlaysEl = document.getElementById('network-map-overlays');
  const filtersEl = document.getElementById('network-map-filters');
  const filtersNEl = document.getElementById('network-map-filters-n');
  const listBodyEl = document.getElementById('network-map-list-body');
  const listHintEl = document.getElementById('network-map-list-hint');
  const findEl = document.getElementById('network-map-find');
  const findListEl = document.getElementById('network-map-find-list');
  const findMsgEl = document.getElementById('network-map-find-msg');
  const hubPanelEl = document.getElementById('network-map-hub-panel');
  const filtersSummaryEl = filtersEl
    ? filtersEl.querySelector('.network-map-filters__summary') : null;
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
  let panelEdges = [];                    // person<->person, weighted, per edition
  // Which conference edition the co-panel arcs show. 'all' until the map
  // holds more than one, at which point the chips below appear (#1584).
  let panelEdition = 'all';
  const inEdition = (e) => panelEdition === 'all' || e.year === panelEdition;
  let coauthorEdges = [];                 // person<->person, from publications
  let lens = 'wg';
  const activeHubs = new Set();           // hub ids active in the current lens
  const overlays = { panels: false, mentorship: false, coauthors: false };
  let hovered = null, draggingHub = null;
  let dragFrom = { x: 0, y: 0 }, dragMoved = false;
  let panning = false, panFrom = { x: 0, y: 0 };
  // A person pinned by the Find control (#1642). It outlives a pointer move,
  // which is what separates it from `hovered`, and it is what the ?find= in
  // the URL restores.
  let spotlight = null;
  // The hub whose panel is open. It joins the focus chain in draw(), which is
  // the hover highlight made to stay put.
  let pinnedHub = null;
  // Read from the query string at boot and applied once the lens is known,
  // since the hub ids only make sense inside a lens (#1602).
  let urlHubs = null, urlFind = null;
  let W = 0, H = 0, dpr = 1;
  // A view transform applied at paint time (#1644). The force layout never
  // learns about it: hit-testing converts screen coordinates to world ones, so
  // the paint and the pointer stay in agreement. k is floored at 1, so the map
  // is never smaller than the stage and the pan clamp below then pins it.
  const view = { k: 1, x: 0, y: 0 };
  const toWorldX = (sx) => (sx - view.x) / view.k;
  const toWorldY = (sy) => (sy - view.y) / view.k;
  const toScreenX = (wx) => wx * view.k + view.x;
  const toScreenY = (wy) => wy * view.k + view.y;
  const avatars = {};                     // person id -> loaded Image

  // The list under the map is rendered at build time by build-network-map.py.
  // Narrowing it here, off the same personVisible() the canvas paints with,
  // means one rule decides who is on the map and the two surfaces cannot
  // disagree.
  const listRows = listBodyEl ? Array.prototype.slice.call(listBodyEl.rows) : [];
  const listHintFull = listHintEl ? listHintEl.textContent : '';
  // Countries are stored as English exonyms in bios.json. The Directory renders
  // them translated, so the map's table and hover card go through the same
  // accessor rather than showing an English name on the FR and DE pages.
  const localCountry = (c) => (c && window.netsecCountry ? window.netsecCountry(c) : c);

  const hubs = () => allHubs[lens];
  const edges = () => hubEdges[lens];

  function resize() {
    const r = canvas.getBoundingClientRect();
    dpr = window.devicePixelRatio || 1;
    W = r.width; H = r.height;
    canvas.width = Math.round(W * dpr);
    canvas.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    // The pan bound is a function of the stage size, so a rotation or a
    // window resize can leave the view outside it.
    clampPan();
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
    ctx.save();
    ctx.translate(view.x, view.y);
    ctx.scale(view.k, view.k);
    // Find pins a node, hovering points at one. Either way the paint dims
    // everything that is not connected to it, so one focus chain serves both.
    const focus = hovered || spotlight || pinnedHub;
    const hoverIds = focus
      ? new Set([focus.id].concat(focus.links ? focus.links[lens] : [],
          focus.people || [], focus.panelPeers || [], focus.coPeers || []))
      : null;

    edges().forEach(e => {
      const p = byId[e.source], h = byId[e.target];
      if (!personVisible(p) || !activeHubs.has(h.id)) return;
      const lit = hoverIds && hoverIds.has(p.id)
        && (focus.type === 'person' || h.id === focus.id);
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
        if (!inEdition(e)) return;
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
      const r = (p.id === (focus && focus.id)) ? p.r + 2 : p.r;
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
        ctx.fillText(T('{n} members').replace('{n}', h.memberCount), h.x, h.y + 12);
      } else {
        ctx.font = '700 12px Lexend, Inter, sans-serif';
        ctx.fillStyle = '#fff';
        ctx.fillText(String(h.memberCount), h.x, h.y + 4);
      }
      ctx.globalAlpha = 1;
    });

    drawHubLabels(hoverIds);
    ctx.restore();
  }

  // Labels are a pass of their own, after the circles, so they can be placed
  // against each other rather than one at a time (#1644). Fifteen theme hubs
  // on a ring put their labels through each other at narrow widths.
  //
  // Two rules, no layout library. Radial ordering: on a ring of more than six
  // hubs the label goes on the side away from the centre, which is where the
  // space is. Then greedy de-confliction, biggest hub first, and a hub under
  // twelve people gives up its label rather than overlap, since the hover
  // card, the chips and the panel all still name it.
  function drawHubLabels(hoverIds) {
    const hs = hubs();
    const radial = hs.length > 6;
    ctx.font = '600 11px Inter, sans-serif';
    ctx.textAlign = 'center';
    // The hub circles are obstacles too. A label crossing a neighbour's disc
    // is as unreadable as one crossing another label, and on a phone that was
    // the overlap left after the label-versus-label pass.
    const discs = hs.map(h => ({
      id: h.id, l: h.x - h.r, r: h.x + h.r, t: h.y - h.r, b: h.y + h.r,
    }));
    const placed = [];
    hs.slice()
      .sort((a, b) => b.memberCount - a.memberCount || a.id.localeCompare(b.id))
      .forEach(h => {
        // Both the WG titles and the theme names are catalogue keys, so the
        // labels follow the page language. Truncation runs on the translated
        // string, since a translation can be the longer one.
        const name = T(h.name);
        const label = h.type === 'wg' ? name
          : (name.length > 26 ? name.slice(0, 25) + '…' : name);
        const w = ctx.measureText(label).width;
        const boxAt = (y) => ({ l: h.x - w / 2 - 3, r: h.x + w / 2 + 3, t: y - 9, b: y + 3 });
        const hits = (box, o) =>
          !(box.r < o.l || box.l > o.r || box.b < o.t || box.t > o.b);
        const clashes = (box) => placed.some(o => hits(box, o))
          || discs.some(d => d.id !== h.id && hits(box, d));
        // Four candidates, tried in order: the side away from the centre, the
        // other side, then one line further out on each. Two neighbours on the
        // ring both wanting the same side is the common case, and one of them
        // stepping over its hub or out a line settles it while the label stays
        // centred on the hub it belongs to.
        const up = radial && h.y < H / 2;
        const prefer = up ? h.y - h.r - 8 : h.y + h.r + 15;
        const other = up ? h.y + h.r + 15 : h.y - h.r - 8;
        const candidates = radial
          ? [prefer, other, prefer + (up ? -14 : 14), other + (up ? 14 : -14)]
          : [prefer];
        let y = candidates.find(c => !clashes(boxAt(c)));
        if (y === undefined) y = prefer;
        const box = boxAt(y);
        // Only a small hub gives up. A label the map cannot place without an
        // overlap is still better than a hub of thirty-five people with no
        // name on it, and the hover card, the chips and the panel all name
        // the ones that drop out.
        if (clashes(box) && h.memberCount < 12) return;
        placed.push(box);
        const dim = (hoverIds && !hoverIds.has(h.id)) || !activeHubs.has(h.id);
        ctx.globalAlpha = dim ? 0.22 : 1;
        ctx.fillStyle = theme.muted;
        ctx.fillText(label, h.x, y);
      });
    ctx.globalAlpha = 1;
  }

  // ── Interaction ──
  // `touch` widens the pick radius: a fingertip covers far more than a mouse
  // point, and the preview tap above means a wrong pick is now seen before it
  // is acted on rather than after.
  function nodeAt(sx, sy, touch) {
    const mx = toWorldX(sx), my = toWorldY(sy);
    for (const h of hubs()) if (Math.hypot(mx - h.x, my - h.y) <= h.r) return h;
    // Divided by the scale, so the target stays the same size under a
    // fingertip however far the map is zoomed in.
    let best = null, bd = (touch ? 20 : 13) / view.k;
    for (const p of people) {
      if (!personVisible(p)) continue;
      const d = Math.hypot(mx - p.x, my - p.y);
      if (d < bd) { bd = d; best = p; }
    }
    return best;
  }

  // The hovered node wins while the pointer is over one, and the pinned node
  // takes the card back when it is not.
  function paintCard(mx, my) {
    if (hovered) showCard(hovered, mx, my);
    else if (spotlight) showCard(spotlight, toScreenX(spotlight.x), toScreenY(spotlight.y));
    else showCard(null);
  }

  // The node the card is currently describing. A pinned card follows its dot
  // through the layout settling, which is 300 frames of repositioning, and
  // rebuilding the markup on each of them would be work for nothing.
  let cardNode = null;
  let cardW = 0, cardH = 0;

  function showCard(node, mx, my) {
    const measure = node !== cardNode;
    if (!node) {
      cardNode = null;
      card.classList.remove('is-on'); card.setAttribute('aria-hidden', 'true');
      return;
    }
    if (node !== cardNode) {
    cardNode = node;
    if (node.type !== 'person') {
      card.innerHTML = '<div class="nm"></div><div class="meta"></div>';
      // A hub node, so the name is a WG title or a theme, both catalogue
      // keys. The person branch below leaves node.name alone.
      card.querySelector('.nm').textContent = T(node.name);
      card.querySelector('.meta').textContent =
        T(node.type === 'wg' ? '{n} members' : '{n} people work here')
          .replace('{n}', node.memberCount);
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
            ? '<div class="panels">' + peerLine(
                'Shared an ESSC panel with {n} member',
                'Shared an ESSC panel with {n} members',
                node.panelPeers.length) + '</div>' : '')
        + (node.coPeers && node.coPeers.length
            ? '<div class="coauth">' + peerLine(
                'Co-authored with {n} member',
                'Co-authored with {n} members',
                node.coPeers.length) + '</div>' : '')
        + (node.slug ? '<div class="go">' + T('View profile') + ' &rarr;</div>' : '');
      if (node.photo) card.querySelector('.face').src = node.photo;
      card.querySelector('.nm').textContent = node.name;
      card.querySelector('.meta').textContent = localCountry(node.country) || '';
      if (themes.length) card.querySelector('.themes').textContent =
        themes.slice(0, 3).map(t => T(t.name)).join(' · ') + (themes.length > 3 ? ' +' + (themes.length - 3) : '');
    }
    }
    // .network-map-stage clips its overflow, and the card was anchored below
    // and to the right of the pointer with a clamp on the right edge only. A
    // node in the lower third lost the bottom of its card, which is where the
    // themes, the co-panel line and "View profile" sit, and one near the right
    // edge got a card sitting on top of its own dot. It now flips rather than
    // clamps, on both axes (#1644).
    card.classList.add('is-on');
    card.setAttribute('aria-hidden', 'false');
    const stage = canvas.parentElement.getBoundingClientRect();
    if (measure) {
      // Measured from the corner. The card is absolutely positioned with a
      // max-width, so measuring it where it currently sits would let the
      // distance to the stage's right edge decide how the text wraps, and a
      // card near that edge would report itself narrower and taller than the
      // one about to be drawn.
      card.style.left = '0px';
      card.style.top = '0px';
      cardW = card.offsetWidth;
      cardH = card.offsetHeight;
    }
    const right = mx + 16 + cardW;
    const bottom = my - 14 + cardH;
    const left = right > stage.width ? mx - 16 - cardW : mx + 16;
    const top = bottom > stage.height ? my + 14 - cardH : my - 14;
    card.style.left = Math.max(4, Math.min(left, stage.width - cardW - 4)) + 'px';
    card.style.top = Math.max(4, Math.min(top, stage.height - cardH - 4)) + 'px';
  }

  canvas.addEventListener('pointermove', (e) => {
    const r = canvas.getBoundingClientRect();
    const mx = e.clientX - r.left, my = e.clientY - r.top;
    if (draggingHub) {
      // Past a few pixels this is a drag, and the pointerup that ends it must
      // not also open the hub's panel.
      if (Math.hypot(mx - dragFrom.x, my - dragFrom.y) > 4) dragMoved = true;
      draggingHub.x = toWorldX(mx); draggingHub.y = toWorldY(my); draw(); return;
    }
    if (panning) {
      if (Math.hypot(mx - dragFrom.x, my - dragFrom.y) > 4) dragMoved = true;
      if (dragMoved) {
        view.x = panFrom.x + (mx - dragFrom.x);
        view.y = panFrom.y + (my - dragFrom.y);
        clampPan();
        paintCard(0, 0);
        draw();
      }
      return;
    }
    hovered = nodeAt(mx, my);
    // Cursor set inline rather than through a class: `.is-link` is already
    // claimed by site.css, and one property is not worth a second name.
    canvas.style.cursor = (hovered && (hovered.slug || hovered.type !== 'person'))
      ? 'pointer' : 'default';
    paintCard(mx, my);
    draw();
  });
  canvas.addEventListener('pointerleave', () => {
    panning = false;
    hovered = null; paintCard(0, 0); draw();
  });
  canvas.addEventListener('pointerdown', (e) => {
    const r = canvas.getBoundingClientRect();
    const mx = e.clientX - r.left, my = e.clientY - r.top;
    const n = nodeAt(mx, my);
    if (n && n.type !== 'person') {
      draggingHub = n;
      dragFrom = { x: mx, y: my };
      dragMoved = false;
      canvas.setPointerCapture(e.pointerId);
    } else if (!n) {
      // Empty canvas: a press that moves pans the map, one that does not is
      // still the tap that clears the card.
      panning = true;
      dragFrom = { x: mx, y: my };
      panFrom = { x: view.x, y: view.y };
      dragMoved = false;
      canvas.setPointerCapture(e.pointerId);
    }
  });
  canvas.addEventListener('pointerup', (e) => {
    if (panning) {
      panning = false;
      // A pan is not a tap, so it must not clear the card or follow a link.
      if (dragMoved) return;
    }
    if (draggingHub) {
      const hub = draggingHub;
      draggingHub = null;
      // A press that never moved is a click, and a hub opens its panel. A
      // second click on the same hub closes it.
      if (!dragMoved) {
        if (pinnedHub === hub) closeHubPanel();
        else openHubPanel(hub);
      }
      return;
    }
    const r = canvas.getBoundingClientRect();
    const mx = e.clientX - r.left, my = e.clientY - r.top;
    const touch = e.pointerType !== 'mouse';
    const n = nodeAt(mx, my, touch);
    // Touch has no hover, so navigating on the first tap sent a visitor to a
    // profile they never saw the name of, and at phone density the nearest
    // node to a fingertip is often the neighbour. First tap previews, second
    // tap on the same node follows through, and a tap on empty space clears.
    if (!n) {
      closeHubPanel();
      // Clicking away clears the pinned person too, on a mouse as well as
      // under a finger. Only the touch branch used to do it, so on a desktop
      // a spotlight could only be dismissed by emptying the search box.
      if (spotlight) {
        if (findEl) findEl.value = '';
        say('');
        setSpotlight(null);
      }
    }
    if (touch) {
      if (!n) {
        hovered = null;
        if (spotlight) { if (findEl) findEl.value = ''; say(''); setSpotlight(null); }
        else showCard(null);
        draw();
        return;
      }
      if (hovered !== n) { hovered = n; showCard(n, mx, my); draw(); return; }
    }
    if (n && n.slug) location.href = 'people/' + n.slug + '.html';
  });

  // One panel edge per edition, so a pair who shared a panel at two
  // conferences appears twice. The arcs want both, the hover card's
  // "with {n} members" wants distinct people who are actually on screen,
  // which is why this is recomputed when the edition filter moves (#1584).
  function recomputePanelPeers() {
    people.forEach(p => { p.panelPeers = []; });
    panelEdges.forEach(e => {
      if (!inEdition(e)) return;
      byId[e.source].panelPeers.push(e.target);
      byId[e.target].panelPeers.push(e.source);
    });
    people.forEach(p => {
      p.panelPeers = p.panelPeers.filter((id, i, a) => a.indexOf(id) === i);
    });
  }

  // The edition row is built rather than sitting in the three locale pages,
  // and only when there is a choice to make. With one conference on the map
  // a filter offering that one conference is furniture, so it stays absent
  // and appears by itself the first time a second edition lands (#1584), the
  // same way the co-authorship chip waits for the first publication.
  function buildEditionChips(editions) {
    if (!editions || editions.length < 2) return;
    const row = document.createElement('div');
    row.className = 'network-map-controls';
    row.id = 'network-map-editions';
    row.setAttribute('role', 'group');
    row.setAttribute('aria-label', T('Filter co-panels by conference edition'));
    const lab = document.createElement('span');
    lab.className = 'lbl';
    lab.textContent = T('Edition');
    row.appendChild(lab);
    const choose = (value) => (b) => {
      panelEdition = value;
      row.querySelectorAll('button').forEach(x =>
        x.setAttribute('aria-pressed', x === b ? 'true' : 'false'));
      recomputePanelPeers();
      hovered = null; paintCard(0, 0);
      syncUrl();
      draw();
    };
    row.appendChild(chip(T('All editions'), panelEdition === 'all', choose('all')));
    editions.forEach(y => row.appendChild(chip(y, panelEdition === y, choose(y))));
    overlaysEl.parentNode.insertBefore(row, overlaysEl.nextSibling);
  }

  // ── Find and spotlight (#1642) ─────────────────────────────────────────────
  // 191 people on one canvas and no way to reach one of them: a member looking
  // for themselves, or for the two others working on their theme, had to hover
  // dots until one was the right name. The datalist is built from the same
  // person nodes the canvas paints.
  function buildFindOptions() {
    if (!findListEl) return;
    findListEl.replaceChildren();
    people.slice()
      .sort((a, b) => a.name.localeCompare(b.name))
      .forEach(p => {
        const o = document.createElement('option');
        o.value = p.name;
        findListEl.appendChild(o);
      });
  }

  // Exact name first, then a substring, so typing a surname lands on the one
  // person who carries it and a full name picked from the datalist is never
  // beaten by someone whose name contains it.
  function resolveFind(q) {
    const s = String(q || '').trim().toLowerCase();
    if (!s) return null;
    // byId also holds the hubs, and a hub has no lens links, so pinning one
    // would break personVisible() rather than answer the search.
    const direct = byId[s];
    if (direct && direct.type === 'person') return direct;
    return people.find(p => p.name.toLowerCase() === s)
      || people.find(p => p.name.toLowerCase().indexOf(s) !== -1)
      || null;
  }

  function say(msg) {
    if (findMsgEl) findMsgEl.textContent = msg;
  }

  function setSpotlight(node) {
    spotlight = node;
    paintCard(0, 0);
    draw();
    syncUrl();
  }

  // A search that finds nobody and a search that finds someone the filters are
  // hiding are different answers, and a reader who gets the second one needs to
  // know the map holds the person rather than that they typed the name wrong.
  function applyFind(q) {
    if (!String(q || '').trim()) { setSpotlight(null); say(''); return; }
    const node = resolveFind(q);
    if (!node) {
      setSpotlight(null);
      say(T('No one on the map matches {q}.').replace('{q}', String(q).trim()));
      return;
    }
    if (!personVisible(node)) {
      setSpotlight(null);
      say(T('{name} is on the map but hidden by the filters in use.')
        .replace('{name}', node.name));
      return;
    }
    setSpotlight(node);
    say(T('Showing {name}.').replace('{name}', node.name));
  }

  // ── URL state (#1602) ──────────────────────────────────────────────────────
  // The lens, the hub chips, the overlays, the edition and the pinned person
  // all ride in the query string, so a narrowed view is a link somebody can
  // send. replaceState rather than pushState: a filter is not a page, and
  // twenty chip clicks should not be twenty presses of the back button.
  function hubParam(id) { return id.replace(/^(wg|theme)-/, ''); }

  function syncUrl() {
    const all = hubs();
    const on = all.filter(h => activeHubs.has(h.id));
    const q = new URLSearchParams();
    if (lens !== 'wg') q.set('lens', lens);
    if (on.length !== all.length) {
      // "none" rather than an empty value, which would read back as "no
      // filter" and quietly restore the full map.
      q.set('hubs', on.length ? on.map(h => hubParam(h.id)).join(',') : 'none');
    }
    const overlaysOn = Object.keys(overlays).filter(k => overlays[k]);
    if (overlaysOn.length) q.set('overlays', overlaysOn.join(','));
    if (panelEdition !== 'all') q.set('edition', panelEdition);
    if (spotlight) q.set('find', spotlight.id);
    const query = q.toString();
    history.replaceState(null, '', location.pathname + (query ? '?' + query : ''));
  }

  function applyUrlState() {
    const q = new URLSearchParams(location.search);
    const l = q.get('lens');
    if (l === 'wg' || l === 'theme') lens = l;
    (q.get('overlays') || '').split(',').filter(Boolean).forEach(k => {
      if (Object.prototype.hasOwnProperty.call(overlays, k)) overlays[k] = true;
    });
    const edition = q.get('edition');
    if (edition) panelEdition = edition;
    urlHubs = q.get('hubs');
    urlFind = q.get('find');
  }

  // ── Controls ──
  function chip(label, pressed, onClick, bg) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'network-map-wg-chip';
    if (bg) b.style.background = bg; else b.classList.add('is-plain');
    b.textContent = label;
    b.setAttribute('aria-pressed', pressed ? 'true' : 'false');
    b.addEventListener('click', () => onClick(b));
    return b;
  }

  // ── The hub panel (#1643) ──────────────────────────────────────────────────
  // A hub is the biggest target on the canvas and answered nothing when it was
  // clicked, the click falling through to the drag handler. On a touchscreen,
  // where there is no hover card either, it answered nothing at all.
  const localeSuffix = () => {
    const lang = (document.documentElement.lang || 'en').toLowerCase().slice(0, 2);
    return lang === 'en' ? '' : '.' + lang;
  };

  // The directory builds its #themes= hash from the theme NAME with this rule.
  // The hub id comes from a different slugifier in the build (it strips
  // diacritics, which this does not), so the link is derived from the name
  // rather than from the id, and cannot drift from the directory's own.
  const themeSlug = (name) => String(name || '').toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, '-').replace(/^-+|-+$/g, '');

  // Which hubs this one shares the most people with. Computed over the whole
  // hub rather than the current view: the panel describes the hub, and a
  // filtered map should not change what a Working Group is.
  function sharedWith(hub) {
    const mine = new Set(hub.people);
    const counts = [];
    hubs().forEach(other => {
      if (other.id === hub.id) return;
      let n = 0;
      other.people.forEach(id => { if (mine.has(id)) n += 1; });
      if (n) counts.push({ hub: other, n: n });
    });
    counts.sort((a, b) => b.n - a.n || a.hub.id.localeCompare(b.hub.id));
    return counts.slice(0, 3);
  }

  function closeHubPanel() {
    if (!pinnedHub) return;
    pinnedHub = null;
    if (hubPanelEl) { hubPanelEl.hidden = true; hubPanelEl.replaceChildren(); }
    draw();
  }

  function openHubPanel(hub) {
    if (!hubPanelEl) return;
    pinnedHub = hub;
    hubPanelEl.replaceChildren();

    const head = document.createElement('div');
    head.className = 'nmhp-head';
    const title = document.createElement('h2');
    title.className = 'nmhp-title';
    const dot = document.createElement('span');
    dot.className = 'nmhp-dot';
    dot.style.background = hubColour(hub);
    title.appendChild(dot);
    title.appendChild(document.createTextNode(
      hub.type === 'wg' ? 'WG' + hub.number + ' · ' + T(hub.name) : T(hub.name)));
    const close = document.createElement('button');
    close.type = 'button';
    close.className = 'nmhp-close';
    close.setAttribute('aria-label', T('Close this panel'));
    close.textContent = '\u00d7';
    close.addEventListener('click', closeHubPanel);
    head.appendChild(title);
    head.appendChild(close);
    hubPanelEl.appendChild(head);

    const meta = document.createElement('p');
    meta.className = 'nmhp-meta';
    meta.textContent = T(hub.type === 'wg' ? '{n} members' : '{n} people work here')
      .replace('{n}', hub.memberCount);
    hubPanelEl.appendChild(meta);

    const bridges = sharedWith(hub);
    if (bridges.length) {
      const label = document.createElement('p');
      label.className = 'nmhp-label';
      label.textContent = T('Shares members with');
      hubPanelEl.appendChild(label);
      const row = document.createElement('div');
      row.className = 'nmhp-bridges';
      bridges.forEach(b => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'nmhp-bridge';
        btn.appendChild(document.createTextNode(
          b.hub.type === 'wg' ? 'WG' + b.hub.number : T(b.hub.name)));
        // A space before the count, so a screen reader reads "WG3 40" rather
        // than running the two together into one token.
        btn.appendChild(document.createTextNode(' '));
        const n = document.createElement('b');
        n.textContent = b.n;
        btn.appendChild(n);
        // A bridge moves the panel across rather than filtering, so walking
        // the network costs nothing to undo.
        btn.addEventListener('click', () => openHubPanel(b.hub));
        row.appendChild(btn);
      });
      hubPanelEl.appendChild(row);
    }

    const actions = document.createElement('div');
    actions.className = 'nmhp-actions';
    const solo = document.createElement('button');
    solo.type = 'button';
    solo.className = 'nmhp-solo';
    solo.textContent = T('Show only this hub');
    // Filtering stays behind a button rather than riding on the click, so a
    // stray click on a hub costs nothing.
    solo.addEventListener('click', () => {
      activeHubs.clear();
      activeHubs.add(hub.id);
      buildHubChips();
      syncFilters();
      if (spotlight && !personVisible(spotlight)) applyFind(findEl ? findEl.value : '');
      syncUrl();
      draw();
    });
    actions.appendChild(solo);

    const link = document.createElement('a');
    link.className = 'nmhp-link';
    if (hub.type === 'wg') {
      link.href = 'working-groups' + localeSuffix() + '.html#wg' + hub.number;
      link.textContent = T('Open the Working Group page');
    } else {
      link.href = 'people' + localeSuffix() + '.html#themes=' + encodeURIComponent(themeSlug(hub.name));
      link.textContent = T('Open in the Directory');
    }
    actions.appendChild(link);
    hubPanelEl.appendChild(actions);

    hubPanelEl.hidden = false;
    draw();
  }

  // ── Zoom and pan (#1644) ───────────────────────────────────────────────────
  // 191 nodes share a 640px canvas and a face draws at about 16px, so a busy
  // cluster cannot be resolved into people at any window size.
  function clampPan() {
    // The map is never smaller than the stage, so the pan is bounded by the
    // overhang. At k = 1 that pins it to zero and the view cannot drift.
    view.x = Math.min(0, Math.max(W - W * view.k, view.x));
    view.y = Math.min(0, Math.max(H - H * view.k, view.y));
  }

  function zoomAt(sx, sy, factor) {
    const k = Math.min(6, Math.max(1, view.k * factor));
    if (k === view.k) return;
    const f = k / view.k;
    view.x = sx - (sx - view.x) * f;
    view.y = sy - (sy - view.y) * f;
    view.k = k;
    clampPan();
    // A finger pans the map once there is somewhere to pan to, and gives the
    // page its scroll back at rest.
    canvas.style.touchAction = view.k > 1 ? 'none' : '';
    paintCard(0, 0);
    draw();
  }

  function resetView() {
    view.k = 1; view.x = 0; view.y = 0;
    canvas.style.touchAction = '';
    // Reset puts a dragged hub back too, which is the other half of "the map
    // is not where I left it".
    seedPositions();
    reheat(200);
  }

  // Plain wheel keeps scrolling the page. Claiming every wheel event over the
  // canvas turns 640px of the page into a scroll trap, which is the phone
  // problem arriving by the other door, and ctrl-wheel is what a trackpad
  // pinch sends anyway.
  canvas.addEventListener('wheel', (e) => {
    if (!e.ctrlKey && !e.metaKey) return;
    e.preventDefault();
    const r = canvas.getBoundingClientRect();
    zoomAt(e.clientX - r.left, e.clientY - r.top, Math.exp(-e.deltaY * 0.002));
  }, { passive: false });

  function buildZoomControls() {
    const wrap = document.createElement('div');
    wrap.className = 'network-map-zoom';
    const btn = (glyph, label, onClick) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'network-map-zoom-btn';
      b.textContent = glyph;
      b.setAttribute('aria-label', T(label));
      b.title = T(label);
      b.addEventListener('click', onClick);
      return b;
    };
    wrap.appendChild(btn('+', 'Zoom in', () => zoomAt(W / 2, H / 2, 1.5)));
    wrap.appendChild(btn('\u2212', 'Zoom out', () => zoomAt(W / 2, H / 2, 1 / 1.5)));
    wrap.appendChild(btn('\u21ba', 'Reset the view', resetView));
    canvas.parentElement.appendChild(wrap);
  }

  // ── Bulk actions on the chip row (#1643) ───────────────────────────────────
  // Every chip starts pressed, so isolating one research theme cost fourteen
  // clicks off and fourteen back.
  function bulkBtn(label, onClick) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'network-map-bulk';
    b.textContent = label;
    b.addEventListener('click', () => onClick());
    return b;
  }

  function setAllHubs(on) {
    activeHubs.clear();
    if (on) hubs().forEach(h => activeHubs.add(h.id));
    hubChipsEl.querySelectorAll('.network-map-wg-chip').forEach(b =>
      b.setAttribute('aria-pressed', on ? 'true' : 'false'));
    if (spotlight && !personVisible(spotlight)) applyFind(findEl ? findEl.value : '');
    syncFilters();
    syncUrl();
    draw();
  }

  // Clear lives on the summary rather than in the row, since the summary is
  // the one filter control still on screen while the row is folded away. A
  // button inside a <summary> toggles the disclosure on both pointer and
  // keyboard unless both are stopped.
  let clearBtn = null;
  function buildClear() {
    if (!filtersSummaryEl || clearBtn) return;
    clearBtn = bulkBtn(T('Clear the filters'), () => {});
    clearBtn.classList.add('network-map-clear');
    clearBtn.hidden = true;
    const swallow = (e) => { e.preventDefault(); e.stopPropagation(); };
    clearBtn.addEventListener('click', (e) => { swallow(e); setAllHubs(true); });
    clearBtn.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { swallow(e); setAllHubs(true); }
    });
    filtersSummaryEl.appendChild(clearBtn);
  }

  function buildHubChips() {
    hubChipsEl.replaceChildren();
    hubChipsEl.appendChild(bulkBtn(T('All'), () => setAllHubs(true)));
    hubChipsEl.appendChild(bulkBtn(T('None'), () => setAllHubs(false)));
    hubs().forEach(h => {
      hubChipsEl.appendChild(chip(
        // The 14 theme names are already in the shared catalogue (the
        // directory's theme filter chips use the same keys), so the hub
        // chips translate without a single new string.
        h.type === 'wg' ? 'WG' + h.number : T(h.name),
        activeHubs.has(h.id),
        (b) => {
          if (activeHubs.has(h.id)) activeHubs.delete(h.id);
          else activeHubs.add(h.id);
          b.setAttribute('aria-pressed', activeHubs.has(h.id) ? 'true' : 'false');
          syncFilters();
          // A chip can hide the pinned person, which turns the spotlight into
          // a card pointing at a dot nobody can see.
          if (spotlight && !personVisible(spotlight)) applyFind(findEl ? findEl.value : '');
          syncUrl();
          draw();
        },
        hubColour(h)));
    });
  }

  // The chip row is folded away by default, so the summary has to report what
  // it is holding. Without that, a filtered map behind a closed disclosure is a
  // state with nothing on screen to explain it.
  function syncFilters() {
    const total = hubs().length;
    const on = hubs().filter(h => activeHubs.has(h.id)).length;
    const bulk = hubChipsEl.querySelectorAll('.network-map-bulk');
    if (bulk[0]) bulk[0].disabled = on === total;
    if (bulk[1]) bulk[1].disabled = on === 0;
    if (clearBtn) clearBtn.hidden = on === total;
    if (filtersNEl) {
      filtersNEl.textContent = on === total
        ? T('showing all {n}').replace('{n}', total)
        : T('showing {n} of {m}').replace('{n}', on).replace('{m}', total);
    }
    if (!listRows.length) return;
    let shown = 0;
    listRows.forEach(row => {
      const person = byId[row.dataset.person];
      const visible = !person || personVisible(person);
      row.hidden = !visible;
      if (visible) shown += 1;
    });
    if (listHintEl) {
      listHintEl.textContent = shown === listRows.length
        ? listHintFull
        : T('Showing {n} of {m} people.')
            .replace('{n}', shown).replace('{m}', listRows.length);
    }
  }

  let animFrames = 0;
  function reheat(frames) {
    if (reduceMotion) { for (let i = 0; i < 400; i++) tick(); draw(); return; }
    const wasRunning = animFrames > 0;
    animFrames = frames;
    if (wasRunning) return;
    (function loop() {
      tick(); draw();
      if (spotlight && !hovered) paintCard(0, 0);
      if (--animFrames > 0) requestAnimationFrame(loop);
    })();
  }

  function switchLens(next) {
    lens = next;
    closeHubPanel();
    activeHubs.clear();
    // A ?hubs= applies once, on the lens it was written for. Switching lens
    // afterwards starts from every hub on, since a hub id means nothing in
    // the other lens.
    if (urlHubs !== null) {
      const none = urlHubs === 'none';
      if (!none) {
        const wanted = new Set(urlHubs.split(',').filter(Boolean));
        hubs().forEach(h => { if (wanted.has(hubParam(h.id))) activeHubs.add(h.id); });
      }
      urlHubs = null;
      // "none" is somebody deliberately switching every chip off, and the
      // summary and the list both report that, so it is honoured. A ?hubs=
      // that matches nothing is a stale or mistyped link, which would open an
      // empty map that nothing on the page accounts for.
      if (!none && !activeHubs.size) {
        hubs().forEach(h => activeHubs.add(h.id));
        say(T('That link filtered the map to hubs it does not hold, so the whole map is shown.'));
      }
    } else {
      hubs().forEach(h => activeHubs.add(h.id));
    }
    lensEl.querySelectorAll('button').forEach(b =>
      b.setAttribute('aria-pressed', b.dataset.lens === lens ? 'true' : 'false'));
    buildHubChips();
    syncFilters();
    seedPositions();
    // The pinned person may not exist on the new lens, so the search is
    // answered again rather than carried across.
    if (findEl && findEl.value) applyFind(findEl.value);
    syncUrl();
    reheat(300);
  }

  // ── Boot ──
  fetch('data/network-map.json', { cache: 'no-cache' })
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
      people.forEach(p => {
        p.coPeers = p.coPeers.filter((id, i, a) => a.indexOf(id) === i);
      });
      // Before anything renders: the overlay chips, the edition chips and the
      // lens chips all paint their own pressed state from this, and reading
      // the URL after them left a chip saying "off" over an overlay that was
      // on.
      applyUrlState();
      recomputePanelPeers();

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
          el.className = 'network-map-stat';
          const bb = document.createElement('b'); bb.textContent = b;
          const ss = document.createElement('span'); ss.textContent = T(s);
          el.appendChild(bb); el.appendChild(ss);
          statsEl.appendChild(el);
        });

      [['wg', 'Working Groups'], ['theme', 'Research themes']].forEach(([v, label]) => {
        const b = chip(T(label), v === lens, () => switchLens(v));
        b.dataset.lens = v;
        lensEl.appendChild(b);
      });
      const overlayDefs = [['panels', 'ESSC co-panels'], ['mentorship', 'Mentorship offers & requests']];
      // Co-authorship starts at zero edges (publications.json is empty until
      // D6 ships its first output) and the chip appears with the first one.
      if (coauthorEdges.length) {
        overlayDefs.push(['coauthors', 'Co-authored outputs']);
        const leg = document.getElementById('network-map-legend');
        if (leg) {
          const sp = document.createElement('span');
          sp.innerHTML = '<span class="sw" style="background:#0aa2c0"></span>';
          sp.appendChild(document.createTextNode(T('co-authored an Action output')));
          leg.insertBefore(sp, leg.lastElementChild);
        }
      }
      buildEditionChips(data.stats && data.stats.panel_editions);
      overlayDefs.forEach(([k, label]) => {
        overlaysEl.appendChild(chip(T(label), overlays[k], (b) => {
          overlays[k] = !overlays[k];
          b.setAttribute('aria-pressed', overlays[k] ? 'true' : 'false');
          syncUrl();
          draw();
        }));
      });

      // Rendered open so the no-script reader gets the chips, closed here so
      // the map itself is the first thing on screen. On a 375px phone the
      // canvas used to start at y=998, below the whole first screen.
      if (filtersEl) filtersEl.open = false;
      buildFindOptions();
      buildClear();
      buildZoomControls();
      if (findEl) {
        // change fires on a datalist pick and on blur, keydown catches Enter
        // before either, and input clears a stale answer as soon as the text
        // stops matching it.
        findEl.addEventListener('change', () => applyFind(findEl.value));
        findEl.addEventListener('keydown', (e) => {
          if (e.key === 'Enter') { e.preventDefault(); applyFind(findEl.value); }
        });
        findEl.addEventListener('input', () => {
          if (!findEl.value.trim()) { say(''); if (spotlight) setSpotlight(null); }
        });
      }
      listRows.forEach(row => {
        const cell = row.querySelector('[data-country]');
        if (cell) cell.textContent = localCountry(cell.dataset.country);
      });
      resize();
      switchLens(lens);
      // After the layout, so the card lands on the node's settled position
      // rather than on its seed.
      if (urlFind) {
        const node = resolveFind(urlFind);
        if (node && findEl) findEl.value = node.name;
        applyFind(urlFind);
      }
    })
    .catch(() => { statsEl.textContent = T('The network map data could not be loaded.'); });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && pinnedHub) closeHubPanel();
  });
  window.addEventListener('resize', () => { resize(); seedPositions(); reheat(120); });
  new MutationObserver(() => { readTheme(); draw(); })
    .observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
})();
