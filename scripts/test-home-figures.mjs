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

// The Directory counts only for leadership roles and a WG lead's country.
const bios = {
  members: [
    { id: 'filip-ejdus', name: 'Filip Ejdus', country: 'Serbia', roles: ['WG1 Leader'] },
    { id: 'ana-silva', name: 'Ana Silva', country: 'Portugal', roles: ['Action Vice-Chair'] },
    { id: 'eva-berg', name: 'Eva Berg', country: 'Norway', roles: ['Management Committee · Norway'] },
    { id: 'no-role', name: 'No Role', country: 'Malta' },
  ],
};
const wg = {
  groups: [
    // The lead has no country in wg.json and takes it from the bio.
    { lead: { slug: 'filip-ejdus', name: 'Prof. Filip Ejdus' },
      members: [{ name: 'Dr Jan Novák', country: 'Sweden' }, { name: 'Prof Ece Kaya', country: ' Türkiye ' }] },
    // The same person in a second group, written without the accent.
    { members: [{ name: 'Jan Novak', country: 'Sweden' }, { name: 'Dr John N.T. Helferich', country: '' }] },
    {}, {},
  ],
};
// One MC representative also sits in a WG, one does not.
const mc = { members: [{ name: 'Ece Kaya', country: 'Türkiye' }, { name: 'Dr Lea Weber', country: 'Austria' }] };
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

// Filip Ejdus, Jan Novák, Ece Kaya, John Helferich, Lea Weber, Ana Silva.
let c = countFigures(bios, wg, events, at('2026-09-26T12:00:00Z'), mc);
assert.deepEqual({ ...c }, { members: 6, countries: 5, groups: 4, held: 2 });

// The Istanbul event counts only once its own end has passed.
assert.equal(countFigures(bios, wg, events, at('2026-09-13T14:59:00Z')).held, 1);
assert.equal(countFigures(bios, wg, events, at('2026-09-13T15:01:00Z')).held, 2);

// Missing files count as zero rather than throwing.
c = countFigures(null, null, null, Date.now());
assert.deepEqual({ ...c }, { members: 0, countries: 0, groups: 0, held: 0 });

console.log('✓ home-figures counting: all cases pass');
