#!/usr/bin/env node
/**
 * Measure what a rendered page actually does (#1714).
 *
 * CLAUDE.md §16 asks that a visual change be rendered and measured before it
 * is called done, at two widths and in both themes. That rule is right and it
 * has caught real defects. What it did not have was a tool, so each check was
 * improvised as a throwaway Puppeteer script and deleted: fifteen of them in
 * one day on the Network Map, none of them comparable with the next session's.
 *
 * Three checks, because these are the three that were written repeatedly:
 *
 *   fold     where the page's main content starts, per width and locale.
 *            The Network Map's canvas moved four times across #1650, #1662,
 *            #1677 and #1691, twice in the wrong direction, each caught by hand.
 *
 *   targets  interactive boxes under the 44px enhanced target size, under an
 *            emulated coarse pointer. This is the sweep #1603 asked for.
 *
 *   bytes    what a page actually transfers, by resource type. The lighthouse
 *            budget says a page is over; this says which files.
 *
 * Usage:
 *   node scripts/measure.mjs fold network-map.html network-map.fr.html
 *   node scripts/measure.mjs targets working-groups.html --theme dark
 *   node scripts/measure.mjs bytes essc-2026.html --json
 *
 * Options:
 *   --width 375x812        repeatable; defaults to 1280x900 and 375x812
 *   --theme light|dark|both        defaults to light
 *   --json                 machine-readable, for diffing between sessions
 *   --chrome <path>        overrides CHROME_PATH / the known locations
 *
 * Three traps this exists to have solved once, each of which cost a wrong
 * conclusion in a single session:
 *
 *   1. scripts/serve-static.cjs indexes the tree at startup, so a file written
 *      after the server started returns 404 and the page renders as if broken.
 *      A gallery that worked was diagnosed as broken this way. This starts its
 *      own server per run, after the build.
 *
 *   2. Puppeteer's page.emulateMediaFeatures rejects `pointer`, so every
 *      `@media (pointer:coarse)` rule silently goes untested. A viewport with
 *      hasTouch + isMobile does set it. That distinction is why the Network
 *      Map's chips measured 33px while the controls around them read 44px.
 *
 *   3. page.mouse ignores coordinates below the viewport, which reads exactly
 *      like a broken click handler. Anything interactive is scrolled into view
 *      before it is touched.
 */
import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const puppeteer = require(path.join(REPO, 'node_modules', 'puppeteer-core'));

// ── Arguments ──────────────────────────────────────────────────────────────
const argv = process.argv.slice(2);
const CHECKS = new Set(['fold', 'targets', 'bytes']);
const check = argv[0];
if (!CHECKS.has(check)) {
  console.error(`Usage: node scripts/measure.mjs <${[...CHECKS].join('|')}> <page...> [options]`);
  console.error('Run with no arguments for the header comment in this file.');
  process.exit(2);
}

const opt = (name, fallback) => {
  const i = argv.indexOf(`--${name}`);
  return i === -1 ? fallback : argv[i + 1];
};
const flag = (name) => argv.includes(`--${name}`);

const pages = argv.slice(1).filter((a) => !a.startsWith('--') && a.endsWith('.html'));
if (!pages.length) {
  console.error('No pages given. Example: node scripts/measure.mjs fold network-map.html');
  process.exit(2);
}

const widths = argv.reduce((acc, a, i) => {
  if (a === '--width' && argv[i + 1]) {
    const [w, h] = argv[i + 1].split('x').map(Number);
    if (w && h) acc.push({ w, h });
  }
  return acc;
}, []);
if (!widths.length) widths.push({ w: 1280, h: 900 }, { w: 375, h: 812 });

const shouldFail = flag('fail');
const themeArg = opt('theme', 'light');
const themes = themeArg === 'both' ? ['light', 'dark'] : [themeArg];
const asJson = flag('json');

// The enhanced target size in WCAG 2.5.5. The 24px minimum in 2.5.8 is what
// the site is held to; this reports against the higher bar because that is the
// number #1603 and #1689 are arguing about.
const TARGET_FLOOR = 44;

// ── Chrome ─────────────────────────────────────────────────────────────────
function findChrome() {
  const given = opt('chrome', process.env.CHROME_PATH);
  if (given) return given;
  const candidates = [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium-browser',
    '/usr/bin/chromium',
  ];
  const hit = candidates.find((p) => existsSync(p));
  if (!hit) {
    console.error('No Chrome found. Pass --chrome <path> or set CHROME_PATH.');
    process.exit(2);
  }
  return hit;
}

// ── A server of our own, started after the build, polled until it answers ──
async function serve() {
  // Port 0 would be cleaner, but serve-static.cjs takes the port as an
  // argument rather than reporting one back, so pick a high one and retry.
  const port = 8100 + Math.floor(Math.random() * 300);
  const proc = spawn('node', [path.join(REPO, 'scripts', 'serve-static.cjs'), String(port), REPO], {
    stdio: 'ignore',
  });
  const base = `http://localhost:${port}`;
  const deadline = Date.now() + 15000;
  for (;;) {
    try {
      const res = await fetch(`${base}/index.html`, { method: 'HEAD' });
      if (res.ok) break;
    } catch { /* not up yet */ }
    if (Date.now() > deadline) {
      proc.kill();
      throw new Error(`static server did not answer on ${base} within 15s`);
    }
    await new Promise((r) => setTimeout(r, 120));
  }
  return { base, stop: () => proc.kill() };
}

// ── The checks ─────────────────────────────────────────────────────────────

/** Where the page's main content starts, measured from the document top. */
async function fold(page) {
  return page.evaluate(() => {
    // The first element inside <main> that is a real content block rather than
    // page chrome. Named surfaces first, so the number means the same thing on
    // a page that has one.
    const named = document.querySelector(
      '.network-map-stage, .essc-photos, .members-grid, .rm-grid, main .container'
    );
    const el = named || document.querySelector('main');
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return {
      selector: named ? named.className.split(/\s+/)[0] : 'main',
      top: Math.round(r.top + window.scrollY),
      visible: Math.max(0, window.innerHeight - Math.round(r.top + window.scrollY)),
    };
  });
}

// What the floor applies to, written down here because a list in prose is a
// list nobody can run (#1689). The rule: a control in <main> that a person taps
// to *do* something clears the floor under a coarse pointer. These are the
// things that look like controls to a selector but are not targets.
const NOT_A_TARGET = [
  // Labels, not controls. They describe the card they sit on.
  'event-wg-pill', 'mentorship-badge', 'stsm-badge', 'country-flag',
  'programme-contrib-published',
  // The hit area is a stretched ::after covering the whole card, so the box
  // measured here is the text rather than the thing a finger lands on.
  'card-stretch', 'event-link',
  // Inline links in prose. WCAG 2.5.8 exempts these explicitly, and the
  // display check below misses them when a wrapper makes them block-level.
  'news-readmore', 'news-seeall', 'mc-mail', 'notes-link', 'event-desc-toggle',
  'ecs-faculty-card-link', 'members-clear-all',
];

/** Interactive boxes below the enhanced target size. */
async function targets(page, floor) {
  return page.evaluate(({ floorPx, exempt }) => {
    const out = [];
    document.querySelectorAll('main a, main button, main summary, main input').forEach((e) => {
      const r = e.getBoundingClientRect();
      if (!r.width || !r.height) return;
      if (getComputedStyle(e).display === 'inline') return;
      const classes = String(e.className || '').split(/\s+/);
      if (classes.some((c) => exempt.includes(c))) return;
      // A bare <a> with no class is a navigation or prose link rather than a
      // control the design system owns.
      if (!e.className && e.tagName === 'A') return;
      if (r.height >= floorPx) return;
      out.push({
        what: classes[0] || e.tagName.toLowerCase(),
        h: Math.round(r.height),
        w: Math.round(r.width),
        text: (e.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 28),
      });
    });
    return out;
  }, { floorPx: floor, exempt: NOT_A_TARGET });
}

/** What the page transferred, grouped by type. */
function bytesCollector(page) {
  const seen = new Map();
  const pending = [];
  page.on('response', (res) => {
    const url = res.url();
    if (seen.has(url)) return;
    // content-length is absent on a gzipped response served chunked, which is
    // every stylesheet and script here. Reporting those as 0 KB would be a
    // quietly wrong total, so fall back to the decoded body. It can throw on a
    // redirect or a response with no body, hence the catch.
    let len = Number(res.headers()['content-length'] || 0);
    if (!len) {
      pending.push(
        res.buffer().then((b) => { const e = seen.get(url); if (e) e.len = b.length; })
          .catch(() => {})
      );
    }
    const type = /\.(png|jpe?g|webp|svg|gif|avif)(\?|$)/i.test(url) ? 'image'
      : /\.(css)(\?|$)/i.test(url) ? 'css'
      : /\.(js|mjs|cjs)(\?|$)/i.test(url) ? 'js'
      : /\.(woff2?|ttf|otf)(\?|$)/i.test(url) ? 'font'
      : /\.(mp4|webm|mov)(\?|$)/i.test(url) ? 'video'
      : 'other';
    seen.set(url, { type, len, name: url.split('/').pop().split('?')[0] });
  });
  return async () => { await Promise.all(pending); return [...seen.values()]; };
}

// ── Run ────────────────────────────────────────────────────────────────────
const server = await serve();
const browser = await puppeteer.launch({
  executablePath: findChrome(),
  headless: 'new',
  args: ['--no-sandbox'],
});

const results = [];
try {
  for (const pageName of pages) {
    for (const { w, h } of widths) {
      for (const theme of themes) {
        const page = await browser.newPage();
        const errors = [];
        page.on('pageerror', (e) => errors.push(String(e)));

        // Trap 2: hasTouch + isMobile is what sets `pointer: coarse`.
        // emulateMediaFeatures rejects the `pointer` feature outright.
        const coarse = check === 'targets';
        await page.setViewport({
          width: w, height: h,
          hasTouch: coarse, isMobile: coarse,
          deviceScaleFactor: coarse ? 3 : 1,
        });
        await page.emulateMediaFeatures([{ name: 'prefers-color-scheme', value: theme }]);

        const readBytes = check === 'bytes' ? bytesCollector(page) : null;
        await page.goto(`${server.base}/${pageName}`, { waitUntil: 'networkidle0' });
        // Client-rendered surfaces need a beat after networkidle.
        await new Promise((r) => setTimeout(r, 2200));

        let value;
        if (check === 'fold') value = await fold(page);
        else if (check === 'targets') {
          value = { coarse: await page.evaluate(() => matchMedia('(pointer: coarse)').matches),
                    under: await targets(page, TARGET_FLOOR) };
        } else {
          // Lazy images below the fold only load once they are scrolled to.
          await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
          await new Promise((r) => setTimeout(r, 2000));
          value = await readBytes();
        }

        const overflow = await page.evaluate(
          () => document.documentElement.scrollWidth > document.documentElement.clientWidth
        );
        results.push({ page: pageName, width: w, height: h, theme, overflow, errors, value });
        await page.close();
      }
    }
  }
} finally {
  await browser.close();
  server.stop();
}

// ── Report ─────────────────────────────────────────────────────────────────
if (asJson) {
  console.log(JSON.stringify({ check, floor: TARGET_FLOOR, results }, null, 2));
} else if (check === 'fold') {
  console.log('page                        width   starts at   on first screen');
  for (const r of results) {
    const v = r.value || { top: '-', visible: '-' };
    console.log(
      `${r.page.padEnd(26)} ${String(r.width).padStart(5)}   ${String('y=' + v.top).padStart(9)}   ${String(v.visible + 'px').padStart(15)}`
      + (r.overflow ? '   ⚠ horizontal overflow' : '')
    );
  }
} else if (check === 'targets') {
  for (const r of results) {
    const n = r.value.under.length;
    console.log(`\n${r.page} at ${r.width}px, ${r.theme}, pointer:coarse=${r.value.coarse}`);
    if (!r.value.coarse) console.log('  ⚠ coarse pointer not emulated: every @media (pointer:coarse) rule is untested');
    if (!n) { console.log(`  ✓ nothing under ${TARGET_FLOOR}px`); continue; }
    console.log(`  ${n} under ${TARGET_FLOOR}px:`);
    for (const t of r.value.under) {
      console.log(`    ${String(t.h + 'px').padStart(6)}  ${t.what.slice(0, 34).padEnd(36)} "${t.text}"`);
    }
  }
} else {
  for (const r of results) {
    const byType = {};
    let total = 0;
    for (const res of r.value) {
      byType[res.type] = (byType[res.type] || 0) + res.len;
      total += res.len;
    }
    console.log(`\n${r.page} at ${r.width}px — ${Math.round(total / 1024)} KB total`);
    Object.entries(byType).sort((a, b) => b[1] - a[1]).forEach(([t, n]) =>
      console.log(`  ${String(Math.round(n / 1024) + ' KB').padStart(8)}  ${t}`));
    const biggest = r.value.filter((x) => x.len > 40 * 1024).sort((a, b) => b.len - a.len).slice(0, 5);
    if (biggest.length) {
      console.log('  largest:');
      biggest.forEach((x) => console.log(`    ${String(Math.round(x.len / 1024) + ' KB').padStart(8)}  ${x.name}`));
    }
  }
}

const failed = results.filter((r) => r.errors.length);
if (failed.length) {
  console.error('\nPage errors:');
  failed.forEach((r) => console.error(`  ${r.page} @${r.width}: ${r.errors.join('; ')}`));
  process.exit(1);
}

// --fail turns the report into a gate. Only `targets` has a pass/fail meaning:
// fold and bytes are numbers to compare between sessions, not thresholds.
if (shouldFail && check === 'targets') {
  const under = results.reduce((n, r) => n + r.value.under.length, 0);
  const uncoarse = results.filter((r) => !r.value.coarse);
  if (uncoarse.length) {
    console.error('\nCoarse pointer was not emulated, so this proves nothing.');
    process.exit(1);
  }
  if (under) {
    console.error(`\n${under} control(s) under ${TARGET_FLOOR}px. The floor and its`
      + ' exemptions are documented in docs/design-system.md and encoded in'
      + ' NOT_A_TARGET in this file.');
    process.exit(1);
  }
  console.log(`\n✓ every control clears ${TARGET_FLOOR}px under a coarse pointer`);
}
