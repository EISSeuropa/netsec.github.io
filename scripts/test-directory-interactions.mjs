#!/usr/bin/env node
// Interaction smoke tests for the Directory (people.html).
//
// The repo's CI gates check structure (links, i18n drift, asset stamps); none
// of them opens a browser, clicks a control, and asserts the page responded.
// Every directory bug shipped in July 2026 (#1376, #1380, #1382, #1383) was
// invisible to a green build for exactly that reason. This suite drives the
// real page in headless Chrome and asserts the interaction-level contract:
// every active filter has a visible pressed control, the mentorship wizard
// reflects every selection, and its popover survives being scrolled.
//
// Run locally:   node scripts/test-directory-interactions.mjs
// Dependencies:  puppeteer-core (npm ci) + an installed Chrome/Chromium.
// Chrome path:   $CHROME_PATH overrides autodetection.

import puppeteer from 'puppeteer-core';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

const CHROME_CANDIDATES = [
  process.env.CHROME_PATH,
  '/usr/bin/google-chrome',
  '/usr/bin/chromium-browser',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
].filter(Boolean);
const CHROME = CHROME_CANDIDATES.find(p => fs.existsSync(p));
if (!CHROME) {
  console.error('No Chrome binary found. Set CHROME_PATH.');
  process.exit(2);
}

const MIME = {
  '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css',
  '.json': 'application/json', '.svg': 'image/svg+xml', '.webp': 'image/webp',
  '.jpg': 'image/jpeg', '.png': 'image/png', '.ico': 'image/x-icon',
};
const server = http.createServer((req, res) => {
  // Resolve and confine to ROOT: the server only ever faces this script's
  // own requests on 127.0.0.1, but a traversal guard costs two lines
  // (CodeQL js/path-injection).
  let file = path.resolve(ROOT, '.' + path.posix.normalize('/' + decodeURIComponent(req.url.split('?')[0])));
  if (!file.startsWith(ROOT + path.sep) && file !== ROOT) { res.writeHead(403); res.end('403'); return; }
  if (req.url.split('?')[0].endsWith('/')) file = path.join(file, 'index.html');
  fs.readFile(file, (err, data) => {
    if (err) { res.writeHead(404); res.end('404'); return; }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream' });
    res.end(data);
  });
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const BASE = `http://127.0.0.1:${server.address().port}`;

// Two attempts. A cold headless Chrome on a GitHub runner occasionally never
// reaches its WS endpoint and throws a TimeoutError, which fails the whole
// suite for a reason that has nothing to do with the code under test (#1713).
// A recovered launch says so, since the count of them is the signal for
// whether this needs revisiting.
async function launchBrowser() {
  const options = {
    executablePath: CHROME,
    headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  };
  try {
    return await puppeteer.launch(options);
  } catch (first) {
    console.error(`  · browser launch failed (${first.message.split('\n')[0]}), retrying once`);
    await new Promise((r) => setTimeout(r, 2000));
    return puppeteer.launch(options);
  }
}

const browser = await launchBrowser();

// One fresh page per journey. Reduced motion kills the FLIP/scroll animations
// so geometry is deterministic; the tour key suppresses the first-visit
// overlay that would otherwise intercept clicks.
async function openDirectory(hash = '', { width = 1280, height = 900, dark = false, expectCards = true } = {}) {
  const page = await browser.newPage();
  await page.setViewport({ width, height });
  await page.emulateMediaFeatures([
    { name: 'prefers-reduced-motion', value: 'reduce' },
    { name: 'prefers-color-scheme', value: dark ? 'dark' : 'light' },
  ]);
  await page.evaluateOnNewDocument(() => {
    localStorage.setItem('netsec-directory-tour-seen', '1');
  });
  await page.goto(`${BASE}/people.html${hash}`, { waitUntil: 'networkidle0' });
  // A deep link can legitimately land on zero cards; the chip row renders on
  // every load, so it is the page-ready signal for those journeys.
  await page.waitForSelector(
    expectCards ? '#members-grid .member-card' : '#members-keyword-filter-chips .members-keyword-filter-chip',
    { timeout: 15000 });
  return page;
}

const gridCount = (page) => page.$$eval('#members-grid .member-card', els => els.length);
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

// Click a control that only just became clickable (#1472). Two shapes hit
// this: a control revealed by an `open` attribute or a "Show all" toggle,
// where the attribute lands before layout gives it a box, and a control the
// mobile media query switches from `display:none`, where the box arrives once
// the viewport is applied. Puppeteer needs a non-empty bounding box to compute
// a click point and throws "Node is either not clickable or not an Element"
// without one, naming no selector. Waiting for visibility asks for exactly
// that box, and the wrapper puts the selector and the measured geometry into
// any failure so the next one is evidence rather than another guess.
async function clickWhenReady(page, selector) {
  try {
    await page.waitForSelector(selector, { visible: true, timeout: 10000 });
    // A visible box is not yet a clickable one. The filter sheet's rise
    // keyframe starts at translateY(100%), and Chrome paints that start frame
    // for two or three frames even under reduced motion, because the .01ms
    // duration only applies once the animation has begun. The control has its
    // full box the whole time, parked a sheet-height below the viewport, so
    // waitForSelector returns and page.click throws "not clickable" on a click
    // point that is off-screen. Waiting for the box to stop moving covers that
    // window without hard-coding the animation length.
    await page.waitForFunction((sel) => {
      const el = document.querySelector(sel);
      if (!el) return false;
      const y = Math.round(el.getBoundingClientRect().y);
      const settled = el.__lastY === y;
      el.__lastY = y;
      return settled;
    }, { polling: 'raf', timeout: 10000 }, selector);
    await page.click(selector);
  } catch (e) {
    const seen = await page.evaluate((sel) => {
      const el = document.querySelector(sel);
      if (!el) return 'no such element';
      const r = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      return `box ${Math.round(r.width)}x${Math.round(r.height)} at ${Math.round(r.x)},${Math.round(r.y)} ` +
             `display:${s.display} visibility:${s.visibility} opacity:${s.opacity}`;
    }, selector).catch(() => 'could not measure');
    throw new Error(`click "${selector}" failed: ${e.message.split('\n')[0]} — ${seen}`);
  }
}

// Popover option clicks: the popover arms a 150 ms grace period before its
// dismiss handlers go live, so wait it out before interacting.
async function openAreaPopover(page, tokenKind = 'area') {
  await page.click(`.mentorship-token[data-token-kind="${tokenKind}"]`);
  await page.waitForSelector('.mentorship-pop', { timeout: 5000 });
  await sleep(200);
}

// ── Search-overlay helpers (#1404) ──────────────────────────────────────
// Pagefind loads its WASM lazily on the first query, so the waits here are
// on rendered rows rather than on a fixed sleep.
async function typeQuery(page, query) {
  // Clear through a real input event so runSearch empties the list, then wait
  // for that empty state. Without it the previous query's rows are still in
  // the DOM and a "rows > 0" wait resolves instantly on stale results.
  await page.$eval('.search-input', (el) => {
    el.value = '';
    el.dispatchEvent(new Event('input', { bubbles: true }));
  });
  await page.waitForFunction(
    () => document.querySelectorAll('.search-results li').length === 0,
    { timeout: 15000 });
  // Set the whole query through one input event rather than typing it key by
  // key (#1553). Each keystroke restarts the 120 ms debounce, so a runner that
  // stalls mid-word fires a query for the prefix as well as for the full word,
  // and the two land in either order. The prefix render satisfies the wait
  // below, the journey reads its chip counts, and the full query then arrives
  // and re-renders, resetting activeFilter to 'all' on its way through
  // runSearch: the People chip had said 7 while the list underneath had gone
  // back to all 9 rows. One event is one query, so the wait for rows means the
  // results are this query's and nothing further is coming.
  await page.$eval('.search-input', (el, q) => {
    el.value = q;
    el.dispatchEvent(new Event('input', { bubbles: true }));
  }, query);
  await page.waitForFunction(
    () => document.querySelectorAll('.search-results li').length > 0,
    { timeout: 15000 });
}

// ./pagefind/ is gitignored and built at deploy time. Without it the overlay
// sits on its load-error message and every search journey dies on a bare
// 15-second timeout, which says nothing about the cause. Check once and say
// so plainly instead.
let indexChecked = false;
async function requireSearchIndex(page) {
  if (indexChecked) return;
  const status = await page.evaluate(async (base) => {
    try { return (await fetch(`${base}/pagefind/pagefind-entry.json`)).status; }
    catch { return 0; }
  }, BASE);
  if (status !== 200) {
    throw new Error(
      `no Pagefind index at /pagefind/ (HTTP ${status}). Run: bash scripts/build-search.sh`);
  }
  indexChecked = true;
}

async function openSearch(query, { dark = false } = {}) {
  const page = await openDirectory('', { dark, expectCards: false });
  await requireSearchIndex(page);
  await page.evaluate(() => document.querySelector('.search-trigger').click());
  await page.waitForSelector('.search-overlay:not([hidden])', { timeout: 5000 });
  await typeQuery(page, query);
  return page;
}

function chipState(page) {
  return page.evaluate(() => {
    const row = document.querySelector('[data-search-filters]');
    const chips = [...row.querySelectorAll('[data-search-filter]')];
    const counts = {};
    chips.forEach((c) => {
      counts[c.dataset.searchFilter] = Number((c.textContent.match(/\((\d+)\)/) || [])[1] ?? -1);
    });
    const rows = [...document.querySelectorAll('.search-results li')];
    return {
      rowHidden: row.hidden,
      counts,
      pressed: (chips.find(c => c.getAttribute('aria-pressed') === 'true') || {}).dataset?.searchFilter,
      rendered: rows.length,
      // renderBioHit puts .search-bio on the <li> itself, not inside it.
      renderedBios: rows.filter(li => li.classList.contains('search-bio')).length,
    };
  });
}

const journeys = {

  // The wizard holds one research area at a time: picking a new area from
  // the token replaces the current one, so switching theme is one click
  // rather than deselect-then-select, and the "+ add an area" token is gone.
  async 'picking a second area replaces the first'() {
    const page = await openDirectory('#mentorship=mentor');
    await openAreaPopover(page);
    await page.click('.mentorship-pop-opt:nth-of-type(1)');
    await sleep(150);
    const firstSlug = await page.evaluate(() => (location.hash.match(/themes=([^&]*)/)?.[1] || ''));
    assert(firstSlug, 'first pick did not reach the hash');
    await openAreaPopover(page);
    // A DOM-level click: page.click() would scroll the option into view
    // first, and that page scroll trips the popover's dismiss-on-scroll
    // guard, detaching the option mid-click.
    await page.$eval('.mentorship-pop-opt:nth-of-type(2)', el => el.click());
    await sleep(150);
    const tokens = await page.$$eval('.mentorship-token[data-token-kind="area"]', els => els.length);
    const hash = await page.evaluate(() => location.hash);
    const slugs = (hash.match(/themes=([^&]*)/)?.[1] || '').split(',').filter(Boolean);
    assert(tokens === 1, `expected 1 area token, got ${tokens} (hash ${hash})`);
    assert(slugs.length === 1, `hash should carry exactly 1 theme: ${hash}`);
    assert(slugs[0] !== firstSlug, `second pick should replace the first (still ${firstSlug})`);
    const add = await page.$('.mentorship-token[data-token-kind="area-add"]');
    assert(!add, 'the add-an-area token should no longer render');
    await page.close();
  },

  // Re-picking the sole active area clears it back to the placeholder.
  async 'picking the active area again clears it'() {
    const page = await openDirectory('#mentorship=mentor');
    await openAreaPopover(page);
    await page.click('.mentorship-pop-opt:nth-of-type(1)');
    await sleep(150);
    await openAreaPopover(page);
    await page.click('.mentorship-pop-opt:nth-of-type(1)');
    await sleep(150);
    const hash = await page.evaluate(() => location.hash);
    assert(!/themes=/.test(hash), `hash should carry no theme after clearing: ${hash}`);
    const placeholder = await page.$eval('.mentorship-token[data-token-kind="area"]',
      el => el.classList.contains('is-add'));
    assert(placeholder, 'area token should be back to its placeholder state');
    await page.close();
  },

  // #1383: the popover's dismiss-on-scroll guard fired on its own list
  // scroll, so the lower options could never be reached.
  async 'area picker scrolls without dismissing'() {
    const page = await openDirectory('#mentorship=mentor');
    await openAreaPopover(page);
    // A wheel can only move a list that already overflows. On a loaded runner
    // the options can still be laying out when the wheel lands, and the
    // popover then sits at scrollTop 0 for a reason that has nothing to do
    // with the guard this journey is about. Wait for the premise, and say so
    // if it never holds. (This journey flaked in CI on 28 Aug 2026 with
    // "popover did not scroll", which is what sent us here.)
    await page.waitForFunction(() => {
      const el = document.querySelector('.mentorship-pop');
      return el && el.scrollHeight > el.clientHeight + 8;
    }, { timeout: 5000 }).catch(() => {});
    const metrics = await page.evaluate(() => {
      const el = document.querySelector('.mentorship-pop');
      return el ? { scrollHeight: el.scrollHeight, clientHeight: el.clientHeight } : null;
    });
    assert(metrics, 'popover vanished before the scroll');
    assert(
      metrics.scrollHeight > metrics.clientHeight,
      `popover does not overflow, so nothing could scroll (${metrics.scrollHeight} <= ${metrics.clientHeight}) — ` +
        'the list is shorter than the viewport, or it has not finished laying out'
    );
    // Wheel delivery is asynchronous, and the popover may scroll smoothly, so
    // poll for the result rather than sampling once after a fixed wait. Three
    // attempts, because a wheel that arrives before the pointer settles over
    // the list is simply lost, and one lost wheel is not a defect.
    let scrollTop = 0;
    for (let attempt = 0; attempt < 3 && scrollTop === 0; attempt++) {
      const box = await (await page.$('.mentorship-pop')).boundingBox();
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
      await page.mouse.wheel({ deltaY: 240 });
      await page
        .waitForFunction(() => (document.querySelector('.mentorship-pop')?.scrollTop || 0) > 0, { timeout: 1500 })
        .catch(() => {});
      scrollTop = await page.evaluate(() => document.querySelector('.mentorship-pop')?.scrollTop ?? 0);
      if (!(await page.$('.mentorship-pop'))) break; // closed: the assertion below reports it
      // Same reasoning as the browser-launch retry above: a recovered flake
      // announces itself, so the count of them is the signal for whether the
      // wheel needs a different approach.
      if (scrollTop === 0) console.error(`  · wheel ${attempt + 1} did not move the popover, retrying`);
    }
    const state = await page.evaluate(() => {
      const el = document.querySelector('.mentorship-pop');
      return el ? { open: true, scrollTop: el.scrollTop } : { open: false };
    });
    assert(state.open, 'popover closed on its own scroll');
    assert(state.scrollTop > 0, `popover did not scroll (scrollTop ${state.scrollTop})`);
    await page.close();
  },

  // The popover is a named, single-select listbox with full keyboard support:
  // End reaches the last option, Tab closes rather than stranding it open.
  async 'area picker is an accessible listbox'() {
    const page = await openDirectory('#mentorship=mentor');
    await openAreaPopover(page);
    const aria = await page.$eval('.mentorship-pop', el => ({
      label: el.getAttribute('aria-label'),
      multi: el.getAttribute('aria-multiselectable'),
    }));
    assert(aria.label, 'popover listbox has no accessible name');
    // The picker holds one area at a time, so it must NOT declare
    // aria-multiselectable (it did when the wizard accumulated areas).
    assert(aria.multi !== 'true', 'area popover must not declare multi-select');
    await page.keyboard.press('End');
    const onLast = await page.evaluate(() => {
      const opts = document.querySelectorAll('.mentorship-pop-opt');
      return document.activeElement === opts[opts.length - 1];
    });
    assert(onLast, 'End did not focus the last option');
    await page.keyboard.press('Tab');
    const after = await page.evaluate(() => ({
      popOpen: !!document.querySelector('.mentorship-pop'),
      tokenExpanded: document.querySelector('.mentorship-token[data-token-kind="area"]')?.getAttribute('aria-expanded'),
    }));
    assert(!after.popOpen, 'Tab left the popover stranded open');
    assert(after.tokenExpanded === 'false', 'token still marked expanded after Tab');
    await page.close();
  },

  // #1376: a deep link to a below-the-fold theme landed with an empty grid
  // and no pressed chip anywhere on screen.
  async 'deep link to a rare theme shows its pressed chip'() {
    let page = await openDirectory();
    await page.evaluate(() => { document.getElementById('members-keyword-filter').open = true; });
    await clickWhenReady(page, '#members-keyword-filter-toggle');
    const rareSlug = await page.$$eval('#members-keyword-filter-chips .members-keyword-filter-chip',
      els => els[els.length - 1].dataset.slug);
    await page.close();
    page = await openDirectory(`#themes=${rareSlug}&mentorship=mentor`, { expectCards: false });
    const pressed = await page.$$eval('#members-keyword-filter-chips [aria-pressed="true"]',
      els => els.map(e => e.dataset.slug));
    assert(pressed.includes(rareSlug), `chip for ${rareSlug} not pressed/visible (pressed: ${pressed})`);
    await page.close();
  },

  // #1376: "Show fewer" collapsed an active chip out of the row while it
  // carried on filtering the grid.
  async 'collapsing the theme row keeps the active chip visible'() {
    const page = await openDirectory();
    await page.evaluate(() => { document.getElementById('members-keyword-filter').open = true; });
    await clickWhenReady(page, '#members-keyword-filter-toggle');   // Show all
    const rareSlug = await page.$$eval('#members-keyword-filter-chips .members-keyword-filter-chip',
      els => els[els.length - 1].dataset.slug);
    await clickWhenReady(page, `#members-keyword-filter-chips [data-slug="${rareSlug}"]`);
    await clickWhenReady(page, '#members-keyword-filter-toggle');   // Show fewer
    const chip = await page.$(`#members-keyword-filter-chips [data-slug="${rareSlug}"][aria-pressed="true"]`);
    assert(chip, `active chip ${rareSlug} vanished on collapse`);
    await page.close();
  },

  // #1376: the mobile Filters badge left the STSM chip out of its count.
  async 'mobile filter badge counts every sheet facet'() {
    const page = await openDirectory('', { width: 375, height: 812 });
    // The Filters button is display:none until the <=640px media query
    // applies, so it is the one control here whose box can lag the cards
    // this journey waits on. It was the click still failing after the first
    // pass at #1472 converted the three inside the sheet.
    await clickWhenReady(page, '#members-filter-toggle');
    await page.waitForSelector('#members-filterset[open]');
    await clickWhenReady(page, '#members-stsm-filter [data-stsm]');
    await clickWhenReady(page, '.members-mentorship-chip[data-mentorship="mentor"]');
    await clickWhenReady(page, '#members-sheet-apply');
    await sleep(100);
    const badge = await page.$eval('#members-filter-toggle-count',
      el => ({ hidden: el.hidden, n: el.textContent.trim() }));
    assert(!badge.hidden && badge.n === '2', `badge should read 2, got ${JSON.stringify(badge)}`);
    await page.close();
  },

  // #1380: a specificity slip rendered the quiet No.2/No.3 rank badges as
  // near-black text on a dark pill in dark mode.
  async 'runner-up rank badges are readable in dark mode'() {
    const page = await openDirectory('#mentorship=mentor', { dark: true });
    await page.waitForSelector('.mentorship-rank.is-quiet');
    const lum = await page.$eval('.mentorship-rank.is-quiet', el => {
      const [r, g, b] = getComputedStyle(el).color.match(/[\d.]+/g).map(Number);
      const f = v => { v /= 255; return v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; };
      return .2126 * f(r) + .7152 * f(g) + .0722 * f(b);
    });
    assert(lum > 0.3, `quiet rank badge text too dark for a dark pill (luminance ${lum.toFixed(3)})`);
    await page.close();
  },

  // #1382: the sentence's line slot was shorter than the token boxes, so
  // wrapped rows of tokens touched. A phone-width viewport forces the
  // stage, direction, and area tokens onto wrapped rows (the wizard holds
  // a single area now, so width does the wrapping that a second area
  // token used to).
  async 'sentence tokens never overlap'() {
    const page = await openDirectory('#mentorship=mentor', { width: 375, height: 800 });
    await openAreaPopover(page);
    await page.click('.mentorship-pop-opt:nth-of-type(1)');
    await sleep(150);
    const bad = await page.$$eval('.mentorship-sentence .mentorship-token', els => {
      const rs = els.map(e => e.getBoundingClientRect());
      for (let i = 0; i < rs.length; i++) for (let j = i + 1; j < rs.length; j++) {
        const a = rs[i], b = rs[j];
        if (a.left < b.right - 1 && b.left < a.right - 1 && a.top < b.bottom - 1 && b.top < a.bottom - 1) {
          return `${i}~${j}`;
        }
      }
      return null;
    });
    assert(!bad, `sentence tokens overlap (${bad})`);
    await page.close();
  },

  // The render-state contract behind the whole #1376 bug class: after any
  // interaction, every active facet must surface a visible pressed control,
  // and clearing must actually clear.
  async 'clear all filters resets grid, hash and controls'() {
    const page = await openDirectory('#mentorship=mentor&stsm=1');
    const total = await page.$eval('#members-count', el => parseInt(el.textContent, 10))
      .catch(() => null);
    await page.click('#members-clear-all');
    await sleep(150);
    const after = await page.evaluate(() => ({
      hash: location.hash,
      pressed: document.querySelectorAll(
        '.members-mentorship-chip[aria-pressed="true"], [data-stsm][aria-pressed="true"]').length,
      cards: document.querySelectorAll('#members-grid .member-card').length,
      panelHidden: document.getElementById('members-mentorship-panel').hidden,
    }));
    assert(after.pressed === 0, `chips still pressed after clear (${after.pressed})`);
    assert(after.hash === '' || after.hash === '#', `hash not cleared: ${after.hash}`);
    assert(after.panelHidden, 'mentorship panel still open after clear');
    if (total) assert(after.cards >= total, 'grid did not return to the full directory');
    await page.close();
  },

  // ── Search overlay: result-type chips (#1404) ────────────────────────
  // The overlay is site-wide rather than directory-only, but it ships from
  // the same assets/js/site.js this suite already loads and this workflow
  // already watches, so its journeys live here rather than in a second
  // harness with its own server and browser.

  // The chips are a filter over hits already in hand. Clicking People must
  // render exactly the people, and every rendered row must be a bio card.
  async 'search chips filter the results to one type'() {
    const page = await openSearch('security');
    const before = await chipState(page);
    assert(!before.rowHidden, 'chip row hidden on a query returning both types');
    assert(before.counts.page + before.counts.bio === before.counts.all,
      `counts do not partition: ${JSON.stringify(before.counts)}`);

    await page.click('[data-search-filter="bio"]');
    await sleep(120);
    const after = await chipState(page);
    assert(after.rendered === before.counts.bio,
      `People chip rendered ${after.rendered}, expected ${before.counts.bio}`);
    assert(after.renderedBios === after.rendered,
      `${after.rendered - after.renderedBios} non-bio row(s) survived the People filter`);
    assert(after.pressed === 'bio', `pressed chip is ${after.pressed}, expected bio`);

    await page.click('[data-search-filter="page"]');
    await sleep(120);
    const pages = await chipState(page);
    assert(pages.rendered === before.counts.page,
      `Pages chip rendered ${pages.rendered}, expected ${before.counts.page}`);
    assert(pages.renderedBios === 0, 'a bio card survived the Pages filter');
    await page.close();
  },

  // The row only earns its space when both types are present. Asserted as an
  // invariant over a sweep rather than against one hand-picked query: which
  // words return a mixed result set is a property of the content, and a
  // fixture query that quietly stops being single-type would read as a
  // feature regression. Counting the rendered rows works for both cases
  // because a fresh query always renders under All.
  async 'the chip row appears exactly when both types are present'() {
    const page = await openSearch('security');
    let sawMixed = 0;
    let sawSingle = 0;
    for (const query of ['security', 'cyber', 'sitemap', 'changelog', 'accessibility', 'faq']) {
      await typeQuery(page, query);
      const s = await chipState(page);
      assert(s.rendered > 0, `"${query}" returned nothing, so it proves nothing`);
      const bothTypes = s.renderedBios > 0 && s.renderedBios < s.rendered;
      assert(s.rowHidden === !bothTypes,
        `"${query}": row ${s.rowHidden ? 'hidden' : 'shown'} with ` +
        `${s.renderedBios} bio of ${s.rendered} rows`);
      if (bothTypes) { sawMixed++; } else { sawSingle++; }
    }
    assert(sawMixed > 0 && sawSingle > 0,
      `sweep saw ${sawMixed} mixed and ${sawSingle} single-type queries, so one ` +
      `side of the rule went untested — refresh the query list`);
    await page.close();
  },

  // A filtered view must not leave activeIndex pointing at a row that is no
  // longer on screen, or Enter opens something the visitor cannot see.
  async 'arrow keys stay inside the filtered rows'() {
    const page = await openSearch('security');
    await page.click('[data-search-filter="bio"]');
    await sleep(120);
    const { rendered } = await chipState(page);
    await page.click('.search-input');
    for (let i = 0; i < rendered + 2; i++) await page.keyboard.press('ArrowDown');
    await sleep(80);
    const active = await page.evaluate(() => {
      const items = [...document.querySelectorAll('.search-results li')];
      return { total: items.length, activeAt: items.findIndex(li => li.classList.contains('is-active')) };
    });
    assert(active.activeAt >= 0 && active.activeAt < active.total,
      `highlight at ${active.activeAt} of ${active.total} rows`);
    await page.close();
  },

  // A fresh query starts from All, so a filter set two searches ago cannot
  // silently hide the new results.
  async 'a new query resets the filter to All'() {
    const page = await openSearch('security');
    await page.click('[data-search-filter="bio"]');
    await sleep(120);
    assert((await chipState(page)).pressed === 'bio', 'People chip did not take');
    await typeQuery(page, 'policy');
    const next = await chipState(page);
    assert(next.pressed === 'all', `filter stuck on ${next.pressed} after a new query`);
    assert(next.rendered === next.counts.all, 'new query did not render every hit');
    await page.close();
  },

  // The selected chip inverts via --ink on --bg-0, which flip together, so
  // it must stay readable in both themes without a .dark override.
  async 'selected chip keeps contrast in dark mode'() {
    for (const dark of [false, true]) {
      const page = await openSearch('security', { dark });
      const seen = await page.$eval('[data-search-filter="all"]', (el) => {
        const s = getComputedStyle(el);
        return { bg: s.backgroundColor, fg: s.color };
      });
      const lum = (rgb) => {
        const [r, g, b] = rgb.match(/[\d.]+/g).slice(0, 3).map(Number)
          .map(v => { v /= 255; return v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; });
        return .2126 * r + .7152 * g + .0722 * b;
      };
      const [hi, lo] = [lum(seen.bg), lum(seen.fg)].sort((a, b) => b - a);
      const ratio = (hi + .05) / (lo + .05);
      assert(ratio >= 4.5,
        `${dark ? 'dark' : 'light'} selected chip contrast ${ratio.toFixed(2)}:1 (${seen.fg} on ${seen.bg})`);
      await page.close();
    }
  },

  async 'search narrows the grid'() {
    const page = await openDirectory();
    const before = await gridCount(page);
    const name = await page.$eval('#members-grid .member-card .member-name',
      el => el.textContent.trim());
    await page.type('#member-search', name);
    await sleep(400);   // debounce is 120 ms
    const after = await gridCount(page);
    assert(after >= 1 && after < before, `search "${name}": ${before} -> ${after} cards`);
    await page.close();
  },
};

let failed = 0;
for (const [name, fn] of Object.entries(journeys)) {
  try {
    await fn();
    console.log(`  ok    ${name}`);
  } catch (e) {
    failed++;
    console.error(`  FAIL  ${name}\n        ${e.message}`);
  }
}

await browser.close();
server.close();
console.log(failed ? `\n${failed} journey(s) failed` : '\nall journeys passed');
process.exit(failed ? 1 : 0);
