// Counting tests for the home page's figures strip (assets/js/home-figures.js).
//
// Loads home-events.js and home-figures.js into a bare vm context with a
// stub `window`, then asserts countFigures(). The count-up and the layout
// are covered by the preview check, this covers what gets counted.
//
// Run: node scripts/test-home-figures.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const window = {};
const ctx = vm.createContext({ window, Intl, Date, console });
for (const f of ['home-events.js', 'home-figures.js']) {
  vm.runInContext(fs.readFileSync(new URL(`../assets/js/${f}`, import.meta.url), 'utf8'), ctx, { filename: f });
}
const { countFigures } = window.NetSec;
const at = (iso) => Date.parse(iso);

const bios = {
  members: [
    { country: 'Sweden' }, { country: 'Sweden' }, { country: ' Türkiye ' },
    { country: 'Türkiye' }, { country: '' }, {},
  ],
};
const wg = { groups: [{}, {}, {}, {}] };
const events = {
  tzid: 'Europe/Stockholm',
  events: [
    // Ends 18:00 Istanbul, which is 15:00 UTC.
    { start: '2026-09-13T09:00', end: '2026-09-13T18:00', tzid: 'Europe/Istanbul' },
    // No end: the start stands in for it.
    { start: '2026-06-11T08:00' },
    { start: '2027-06-11T09:00', end: '2027-06-12T18:00' },
  ],
};

let c = countFigures(bios, wg, events, at('2026-09-26T12:00:00Z'));
assert.deepEqual({ ...c }, { members: 6, countries: 2, groups: 4, held: 2 });

// The Istanbul event counts only once its own end has passed.
assert.equal(countFigures(bios, wg, events, at('2026-09-13T14:59:00Z')).held, 1);
assert.equal(countFigures(bios, wg, events, at('2026-09-13T15:01:00Z')).held, 2);

// Missing files count as zero rather than throwing.
c = countFigures(null, null, null, Date.now());
assert.deepEqual({ ...c }, { members: 0, countries: 0, groups: 0, held: 0 });

console.log('✓ home-figures counting: all cases pass');
