// Selection tests for the home page's Now row (assets/js/home-now.js).
//
// Loads home-events.js, home-news.js and home-now.js into a bare vm context
// with a stub `window`, then asserts pickNow() for every state a tile can be
// in. No browser: the rendering is covered by the preview check, this covers
// which event and which news items get picked on a given date.
//
// Run: node scripts/test-home-now.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const window = {};
const ctx = vm.createContext({ window, Intl, Date, console });
for (const f of ['home-events.js', 'home-news.js', 'home-now.js']) {
  vm.runInContext(fs.readFileSync(new URL(`../assets/js/${f}`, import.meta.url), 'utf8'), ctx, { filename: f });
}
const { pickNow } = window.NetSec;
const at = (iso) => Date.parse(iso);

const events = {
  tzid: 'Europe/Stockholm',
  events: [
    { uid: 'past', start: '2026-09-13T09:00', end: '2026-09-13T18:00', tzid: 'Europe/Istanbul' },
    { uid: 'older', start: '2026-06-11T08:00', end: '2026-06-12T18:00' },
  ],
};
const withNext = (status) => ({
  ...events,
  events: [...events.events, { uid: 'next', start: '2027-06-11T09:00', end: '2027-06-12T18:00', status }],
});
const news = {
  items: [
    { id: 'latest', type: 'event', pubDate: '2026-09-13T18:00:00+03:00' },
    { id: 'rolling', type: 'call', pubDate: '2026-05-15T09:00:00+02:00' },
    { id: 'soon', type: 'call', pubDate: '2026-09-01T09:00:00+02:00', homeUntil: '2026-10-01T23:59:00+02:00' },
    { id: 'expired', type: 'call', pubDate: '2026-07-24T09:00:00+02:00', homeUntil: '2026-09-13T18:00:00+03:00' },
  ],
};
const NOW = at('2026-09-26T12:00:00Z');

// Nothing upcoming: the last event held.
let r = pickNow(events, news, NOW);
assert.equal(r.event.state, 'recent');
assert.equal(r.event.ev.uid, 'past');

// In progress, in the event's own zone (09:00 Istanbul is 06:00 UTC).
r = pickNow(events, news, at('2026-09-13T06:30:00Z'));
assert.equal(r.event.state, 'live');
assert.equal(pickNow(events, news, at('2026-09-13T05:30:00Z')).event.state, 'next');

// Upcoming, confirmed and tentative.
assert.equal(pickNow(withNext('CONFIRMED'), news, NOW).event.state, 'next');
r = pickNow(withNext('TENTATIVE'), news, NOW);
assert.equal(r.event.state, 'tentative');
assert.equal(r.event.ev.uid, 'next');

// Calls: soonest closing first, rolling last, expired dropped.
assert.deepEqual(r.calls.map((c) => c.id), ['soon', 'rolling']);
// Latest skips calls.
assert.equal(r.latest.id, 'latest');

// After the soon call closes only the rolling one stays.
r = pickNow(events, news, at('2026-10-02T12:00:00Z'));
assert.deepEqual(r.calls.map((c) => c.id), ['rolling']);

// No calls, no events: empty picks, no throw.
r = pickNow({ events: [] }, { items: [{ id: 'n', type: 'event', pubDate: '2026-09-01T09:00:00Z' }] }, NOW);
assert.equal(r.event, null);
assert.deepEqual(r.calls, []);
assert.equal(r.latest.id, 'n');

console.log('✓ home-now selection: all states pass');
