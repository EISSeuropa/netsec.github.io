# Setting up the network directory

This guide walks through creating the Google Form, linking it to a Sheet, and wiring the published Sheet into the auto-sync workflow. **One-time setup, ~30 minutes.** After this, weekly involvement is "review the PR, click Merge".

## How the pipeline works

```
Google Form ──► Google Sheet ──► sync-bios.yml (weekly) ──► PR ──► merge ──► /people/
```

- Anyone interested in NetSec — leadership, MC representatives, WG participants, or wider-community researchers and practitioners — fills the form once.
- Every Monday at 05:15 UTC (and on manual dispatch), the workflow reads the Sheet as CSV, downloads any new headshots, regenerates `data/bios.json`, and opens a PR if anything changed.
- You merge. The new bio appears on the **The Network** page (`/people.html`).
- Members can update their entries by submitting again — the script dedupes by email, newest submission wins.

## Step 1 · Create the form

1. Go to <https://forms.google.com> and create a new blank form.
2. Title it **Join the NetSec network**. Suggested description:
   > Submit your bio for the NetSec network directory at netsec-cost.eu. The directory is open to anyone working in or alongside European security studies — leadership, Management Committee representatives, Working Group participants, and wider-community researchers, policy-makers, and practitioners. Takes ~5 minutes. You can edit your response later via the link in your confirmation email.
3. Add these questions, **in this order, with the exact text below**. If you rename a question, mirror the change in `scripts/bios-source.json` (`columns` map).

| # | Question text | Type | Required? |
|---|---|---|---|
| 1 | **Full name (with title — Dr / Prof / Mr / Ms)** | Short answer | ✅ |
| 2 | **Position or current role (e.g. PhD candidate, Associate Professor, Policy analyst)** | Short answer | ✅ |
| 3 | **Institution or organisation** | Short answer | ✅ |
| 4 | **Country** | Dropdown — paste the full list of COST member countries plus an "Other / outside Europe" option | ✅ |
| 5 | **Public email (optional, will be shown on the site)** | Short answer | ⬜ |
| 6 | **Short bio (max 300 words)** | Paragraph | ✅ |
| 7 | **Research keywords (comma-separated, 3–5 suggested)** | Short answer | ⬜ |
| — | **Working Group involvement** *(retired)* | Was a checkbox question; removed from the form because members were often unsure which WG they belonged to. Working-Group chips are now sourced solely from cost.eu's Membership table (see below), not self-declared. | — |
| 9 | **Mentorship (optional)** | Checkboxes: *Open to mentoring early-career researchers · Looking for a mentor* | ⬜ |
| 10 | **Research regions (optional)** | Checkboxes: *Europe · Europe - Western Balkans · Europe - Eastern neighbours / Russia · Middle East and North Africa · Africa · Asia · The Americas · Global and cross-regional* | ⬜ |
| 11 | **Could your institution host STSM visitors?** | Multiple choice: *Yes · No · Ask me* | ⬜ |
| 12 | **Personal or institutional website (optional)** | Short answer | ⬜ |
| 13 | **ORCID iD (optional)** | Short answer | ⬜ |
| 14 | **LinkedIn URL (optional)** | Short answer | ⬜ |
| 15 | **X / Twitter URL (optional)** | Short answer | ⬜ |
| 16 | **Bluesky URL (optional)** | Short answer | ⬜ |
| 17 | **Mastodon URL (optional)** | Short answer | ⬜ |
| 18 | **Headshot photo (optional)** | File upload — image only — max 5 MB | ⬜ |
| 19 | **I consent to publication of my bio on netsec-cost.eu** | Checkboxes — single option | ✅ |

> **STSM-hosting parsing (#760).** Question 11 maps to a tri-state `stsm_hosting` field: *Yes* → `yes`, *Ask me* → `ask`, *No* (or blank) → the field is dropped. Matching is tolerant substring matching and the conditional ("ask") signal wins over a co-occurring "yes", so a hand-typed *"Yes, but ask me first"* lands on `ask`. The directory shows a quiet hosting badge on a member's card and a "STSM hosting" filter chip, both of which stay invisible until at least one member answers, and the grants page deep-links to the pre-filtered directory (`/people.html#stsm=1`). The exact question text must match the column name in `scripts/bios-source.json`.

> **WG-checkboxes parsing (retired).** The Working-Group question is no longer on the form, and `scripts/bios-source.json` maps no `wgs` column, so this no longer runs. The `parse_wgs` helper (which extracted the digits 1–4 from a checkbox cell) stays in `scripts/sync-bios.py` as a dormant no-op in case the question is ever reinstated. WG chips are sourced from cost.eu (see below).

> **Affiliation punctuation.** The sync standardises the separator inside the *Institution or organisation* answer so the directory reads uniformly: a spaced hyphen or dash between an institution and its named centre becomes a comma (*ETH Zurich - Center for Security Studies* → *ETH Zurich, Center for Security Studies*), and a semicolon between two separate affiliations becomes a slash (*Ghent University; Egmont Institute* → *Ghent University / Egmont Institute*). It does not merge differently-spelled names for the same institution, so keep the institution name itself consistent across submissions.

> **Pasted website navigation in a bio.** A member who copies their bio straight off a university staff page can carry the page's navigation header along with it (Alexandra Brankova's first sync arrived with Uppsala's Swedish *"Till startsidan"* / *"Search"* labels sitting above the prose). The sync drops a leading run of known navigation labels (the `_BIO_CHROME_LINES` set in `scripts/sync-bios.py`) before it stores the bio, so only a bare label on its own line is removed and real prose is never trimmed. The strip runs every sync, so the fix holds without editing the form response. If a new university's header slips through, add its labels (lowercased, one line each) to that set.

> **Mentorship parsing.** The script reads the two checkbox options into a `mentorship` list of role tags. *"Open to mentoring …"* parses to `mentor`; *"Looking for a mentor"* parses to `mentee`; a member can tick both, or neither. The match is a tolerant substring check on the cell text, so light rewording is safe as long as an offering option still says *mentoring* / *as a mentor* and a seeking option still says *looking for* / *seeking a mentor*. The directory badge labels are recognised too (*"Available to mentor"* → `mentor`, *"Seeking mentorship"* → `mentee`), so if you edit the Sheet by hand you can type the status as it appears on the card rather than the exact Form option. Put the senior / mid-level framing (mentors are typically senior or mid-level scholars) in the question's **description** text, not in the option labels: it stays guidance for respondents and never reaches the parser. The field is dormant until the question is live and members resubmit; an absent column parses to an empty list and renders nothing.

> **Research-regions parsing.** Question 10 is a second, geographic filter axis for the directory, independent of the topical research keywords and combined with them by AND (so a visitor can narrow to "cyber **and** Russia"). The script reads the ticked checkbox values into a `regions` list, matching each against the controlled vocabulary in `data/keyword-aliases.json` (`regions` section): *Europe · Europe - Western Balkans · Europe - Eastern neighbours / Russia · Middle East and North Africa · Africa · Asia · The Americas · Global and cross-regional*. The match is case-insensitive and the cell may be comma- or semicolon-separated; anything not in the vocabulary is dropped, so a stray free-text answer never leaks into the filter. The eight regions follow the EU Institute for Security Studies' lean regional taxonomy, kept short on purpose so members cluster rather than fragment. To change the list, edit the `regions` array in `keyword-aliases.json` **and** the checkbox options on the form so they stay in step. Like mentorship, the field is dormant until you add the question and members resubmit: until at least one member opts in, `region_aggregate` is empty and the directory's region-filter row stays hidden, so shipping the code ahead of the data is harmless. The translated region names live in the `netsecT` catalogues in `assets/js/site.js` (FR + DE), hand-translated per CLAUDE.md §1.

In *Settings → Responses*, configure as follows:

- ☑ **Collect email addresses → Verified.** Google sign-in is required and the form auto-captures the signed-in account's email. The sync uses email as the dedup key, so this guarantees one reliable identity per submission.
- ☑ **Allow response editing.** The confirmation email contains an edit link respondents can revisit to tweak text fields. (See the photo-replacement caveat in the box below.)
- ☐ **Limit to 1 response: leave UNCHECKED.** Counter-intuitive, since the sync already dedupes by email, but necessary because of an upstream Google Forms limitation. With this off, a respondent who wants to update their photo can submit a fresh response; the sync overwrites the previous entry on its next run.

> **Known Google Forms limitation: file uploads can't be replaced via the edit link.** When a respondent opens their edit link, Google Forms displays the previously-uploaded headshot but refuses to remove or replace it. Google has acknowledged the bug; their recommended workaround is "submit a new response." Tracked as [#183](https://github.com/EISSeuropa/netsec.github.io/issues/183), which will close (and the settings recommendation flip back) if upstream ever ships a fix.
>
> Add the following note to the **Photo** question's description on the form, so respondents see the workaround at the point of confusion:
>
> > Want to update your photo? Google Forms won't let you replace a file upload when editing an existing response. Submit a fresh response (use the link above, not the edit link from your confirmation email); the sync will merge your new answers into your old entry. Anything you leave blank in the new submission stays as it was, so you only have to fill in what's changing plus the required fields. For non-photo updates, the edit link works fine.

### How the sync handles a sparse resubmission

A natural worry, given the workaround above: if a respondent submits a "minimum-viable" second response that only fills the required fields (name, role, affiliation, country, bio, consent) plus the new photo, will the sync wipe their previously-entered LinkedIn, ORCID, keywords, etc?

**No.** `scripts/sync-bios.py` does a truthy-merge per field, not a full-record replacement:

- Optional fields (`email`, `website`, `orcid`, `linkedin`, `twitter`, `bluesky`, `mastodon`, `keywords`, `mentorship`, `regions`, `position`, `affiliation`, `bio`, `country`, etc.) only overwrite the prior value when the new submission carries a non-empty value for that field. Blanks are skipped.
- The headshot follows the same rule. A submission with no upload doesn't wipe the previous photo.
- Working-group memberships use **union** semantics on the Google Form sync, so a sparse resubmission can never drop a WG via the form alone. See the next subsection for the cost.eu-side reconciliation that runs weekly on top of this.

The knock-on consequence: respondents can't intentionally clear a field via the form. Submitting an empty Twitter field won't remove a previously-stored URL. To unset a link, a respondent can either use the confirmation-email edit link (which lets them actively delete the contents) or ask the maintainer to blank the cell in the Sheet directly.

This makes the photo-replacement workaround safe to recommend in practice: respondents only need to retype the required fields, not the full bio.

### How Working Group memberships stay in sync with cost.eu

Each bio's `wgs` field is sourced from cost.eu's authoritative Membership table, not from the form. The form's *Working Group involvement* question was retired (members were often unsure which WG they belonged to, and a guessed answer was union-merged and then sticky), so `scripts/sync-bios.py` no longer reads any self-declared WG (there is deliberately no `wgs` column mapping in `scripts/bios-source.json`). `scripts/sync-cost.py` (weekly Monday 05:00 UTC, plus manual `workflow_dispatch`) owns `wgs`, reconciling it against the Membership table on <https://www.cost.eu/actions/CA24154/>:

- **Per-WG reconciliation, biased towards additions.** Members add WGs far more often than they remove them, and cost.eu can lag a fresh form submission by weeks, so neither source simply wins. A WG newly published on cost.eu is applied to the bio; a WG declared on the form that cost.eu has not recorded yet stays on the card and is flagged in the sync PR as pending formal catch-up; a WG a member's newer form submission deliberately dropped is held rather than re-added, with a flag asking the maintainer to confirm. The observation clocks behind the recency comparison live in `data/cost-wg-state.json` (generated, never hand-edited).
- **Entries not on cost.eu are left untouched.** Wider-community researchers in the directory who aren't on the MC, plus seed entries for new leaders who haven't yet appeared in cost.eu's Membership table, keep whatever `wgs` value the form (or the maintainer) last set.
- **Every chip surface shows the same sets.** The home-page `WG_MAP` and `data/wg.json` consume the reconciled result, so the home page, the directory, and the Working Groups page can never tell different stories about a member's WGs.

When the maintainer (or COST admin) updates a member's WG list on cost.eu, the change reaches the directory on the next sync run. No respondent action required.

### The `founding_contributor` flag

`scripts/sync-bios.py` cross-references each bio's name against `data/founding-proposers.json`, the hand-curated list of the 52 researchers named in the COST Open Call proposal that established the Action. A match sets `"founding_contributor": true` on that member's `bios.json` record. The flag is computed at sync time using the same first-and-last name key the directory uses elsewhere, so it is not a form field a respondent can set, and it is rebuilt (cleared then re-applied) on every run so a stale flag never lingers. It is listed in the sync's `_DERIVED_FIELDS`, which keeps the weekly auto-PR from reading it as a respondent edit.

The flag drives the quiet "Founding contributor" badge on `/people.html` directory cards and feeds the founding-cohort figures on `/about.html` and `/press-kit.html`. To correct a miss, edit `data/founding-proposers.json` (add or remove the name) and re-run the sync. A member whose form name does not match the proposal name can be reconciled with a `name_aliases` entry, the same mechanism the speaker matcher uses.

## Step 2 · Link the form to a Sheet

In the form's *Responses* tab, click the green Sheets icon → *Link to Sheets* → *Create a new spreadsheet*. Each response will land as a row in the linked Sheet, with the form questions as column headers.

## Step 3 · Publish the Sheet as CSV

The workflow reads the Sheet via its *publish to web* CSV URL — no authentication, just a long unguessable URL.

1. In the Sheet, *File → Share → Publish to web*.
2. **Link** tab:
   - Document picker → *Form Responses 1*.
   - Format → **Comma-separated values (.csv)**.
3. ☑ *Automatically republish when changes are made*.
4. **Publish**, confirm.
5. Copy the URL — it looks like `https://docs.google.com/spreadsheets/d/e/<id>/pub?gid=<gid>&single=true&output=csv`.

## Step 4 · Wire the URLs into the repo

Open `scripts/bios-source.json` and fill in:

```json
{
  "sheet": {
    "csv_url": "https://docs.google.com/spreadsheets/d/e/.../pub?gid=...&single=true&output=csv"
  },
  "form_url": "https://forms.google.com/...",
  ...
}
```

- `csv_url` — the URL from Step 3 (the script reads this).
- `form_url` — the public form URL (top right of the form editor → *Send → 🔗 Link*). The "Add your bio" CTA on `/people.html` reads this; if it's empty the button is hidden.

Commit. The next workflow run picks it up.

## Step 5 · Photo permissions — the one Google quirk

Files uploaded via Google Forms land in a private Drive folder. For the workflow to download them, they need to be readable without auth.

In Google Drive, find the form's auto-created folder (under *My Drive → Join the NetSec network (File responses)*). Right-click → *Share* → set general access to **Anyone with the link → Viewer**. This inherits to every file uploaded later.

Record the resulting share URL in `scripts/bios-source.json` under `photo_folder_url`. The sync doesn't read it, but a future maintainer (including future-you, six months from now) will save a few minutes when something needs spot-checking.

(If you'd rather control sharing per-file, do the same right-click → *Share* dance on each upload as submissions arrive. More secure, more work.)

## Test the workflow

After Step 4, trigger the workflow manually:

1. *Actions → Sync member bios from Google Form*.
2. *Run workflow*. Wait ~30 s.
3. If the Sheet has responses, a PR opens on `bios-sync/auto`. If it doesn't, the run is a clean no-op.

## Share the form with the community

Announce the form widely — not just to the MC. Sample announcement copy:

> Subject: Join the NetSec network directory
>
> Dear colleague,
>
> The NetSec COST Action is opening its directory to the wider community of researchers, policy-makers, and practitioners working in or alongside European security studies — whether or not you sit on the Management Committee or a Working Group.
>
> If you'd like to be listed at <https://netsec-cost.eu/people.html>, please take ~5 minutes to submit your bio here:
>
>   <https://forms.google.com/your-form-url>
>
> You can edit non-photo fields any time using the link in your confirmation email. To change your headshot, submit a fresh response (the sync will overwrite the old entry). Please feel free to forward to colleagues who'd value being part of the network.

## Editing or removing a bio

**As the maintainer:**

- **Edit the Sheet directly.** The response sheet is just data. Correct typos, fix country misspellings, etc. The next workflow run picks up your edits.
- **Delete a row.** The next run will drop the corresponding bio from `/people/`.

If you delete by accident, Drive's version history can restore the Sheet row.

**As a respondent:**

- **Non-photo fields.** Use the edit link from the confirmation email. The form re-opens with the previous values prefilled; save the changes and the sync picks them up on the next run.
- **Photo update.** Submit a fresh response via the public form URL (not the edit link). The sync dedupes by email; the new submission is *merged* into the previous entry (truthy-merge per field: non-empty new values overwrite, blanks leave the old value alone), photo included. So only the required fields plus the changed photo need to be filled in. This dance exists because Google Forms doesn't let respondents replace a file upload through the edit flow; see the box under Step 1.

### Optional: `name_aliases` for hard-to-match speakers

The ESSC live programme page (`essc-2026.html`) tries to link any Indico speaker who is one of our members straight to their `/people.html` card. Matching is name-based, with diacritics, honorifics, post-nominals, and particles stripped, then keyed on (first surviving token, last surviving token). That handles most cases automatically, but a few patterns slip through: nickname vs legal name, married vs maiden, transliteration variants, reversed name order on Hungarian or East-Asian conventions.

When you spot a member whose name on the Indico programme doesn't link to their bio, hand-add a `name_aliases` array to that member's record in `data/bios.json`:

```json
{
  "id": "alex-petrova",
  "name": "Alexandra Petrova",
  "name_aliases": ["Sasha Petrova", "Petrova Alexandra"],
  ...
}
```

The sync script preserves this field across runs. It's only overwritten if a form submission explicitly resets it, and the form has no aliases column today, so in practice your edit survives. Each alias is fed through the same matcher as the canonical name, so add the variant exactly as it would appear on Indico.

To check what's currently missing, open the live programme in any browser, then `console.debug` in DevTools: the page logs `[essc] N speakers didn't match a member: ...` after render.

## Research-keyword normalisation (`data/keyword-aliases.json`)

The Google Form accepts free-text research keywords. To keep the directory's pill display + filter coherent, the sync resolves each submitted keyword to a canonical form via `data/keyword-aliases.json`, then writes the result to a per-bio `canonical_keywords` field (and an aggregate count to the top-level `keyword_aggregate`). The renderer reads the canonical list.

The sync also groups canonical keywords into a small set of broad **themes** (the `themes` section of the aliases file) and emits `theme_aggregate` (distinct-member count per theme) + `keyword_theme_map`. `theme_aggregate` drives the **research-theme filter chip row** above the directory grid on `/people.html`: the top eight themes by member count appear as toggle pills, so people working in the same area cluster together rather than fragmenting across one-off keywords. Visitors can multi-select (OR semantics), expand to the full list, and persist their selection through the URL hash (`#themes=slug-one,slug-two`). Member cards keep their specific keyword pills; clicking one selects that keyword's theme. Exact-keyword lookup stays available through the search box. Nothing for the maintainer to wire: the row appears automatically as soon as any bio carries a themed keyword, and hides cleanly when the aggregate is empty. A canonical keyword with no theme is surfaced in the weekly sync PR body, under a **Review flags → Keywords with no theme (won't cluster)** block, so the gap is visible to whoever reviews the PR rather than sitting in the scheduled job's stderr where no one reads it (the same review block lists any link field the sync rewrote to an absolute URL). Add the keyword under `themes` to clear the flag.

> **Form-description copy (themes).** Set the **description** of the *Research keywords* question to this exact sentence so submitters understand the grouping before they answer:
>
> > Your keywords appear in full on your directory profile, and we also group them under a broader research theme so visitors can find everyone working in the same area.
>
> The directory mirrors this on the visitor side: a one-line hint under the *Research themes* filter heading reads *"Themes automatically group people working in the same area based on their individual keywords, which remain visible on their card."* (hand-translated FR/DE). The two lines exist so neither the submitter nor the visitor reads the broad theme chips as a mismatch with the specific keyword pills on each card.

The file has two sections:

- **`acronyms`** is a flat list of preferred display forms (`UN`, `NATO`, `EU`, `IoT`, `R&D`, …). When one of these words appears in any position in a submitted keyword, the sentence-case normaliser preserves its canonical capitalisation. So `eu foreign policy` becomes `EU foreign policy`, not `Eu foreign policy`.

- **`aliases`** maps a canonical display form to a list of lowercased aliases that resolve to it. Use this when two genuinely-distinct submitted phrases should collapse (`fpa` → `Foreign policy analysis`) or when a phrase needs to override the auto-normaliser (`eu-nato relations` → `EU–NATO relations` with the en-dash).

The maintainer extends the file by hand when a submission lands. The sync also logs `· possible alias candidate (3× 'foreign policy') ↔ (1× 'foreign policy analysis'); distance=9, substring` for pairs that look close enough to be worth a manual merge. Distance ≤ 2 Levenshtein and word-boundary substring containment both trigger the hint; already-paired canonicals are suppressed.

Two hygiene behaviours run during normalisation. A standalone `&` between words is rewritten to `and` (so `Security & defence` becomes `Security and defence`); `&`-bearing acronyms like `R&D` are matched whole and stay intact. And the sync prints a non-fatal warning when a canonical keyword is over 40 characters or contains parentheses, so a phrase-like submission (`Policy evaluation & lessons learned (Afghanistan)`) gets curated into a tighter tag, or an alias that collapses it, rather than shipping as a sentence-length singleton.

If `data/keyword-aliases.json` is missing or malformed, the sync falls back to identity normalisation (sentence-case the whole string, no acronym preservation) and prints a warning. The renderer's own inline fallback covers the same case for visitors who land before the next sync runs.

## Freshness timestamp

`data/bios.json` carries a top-level `generated_at` field: an ISO 8601 stamp (with UTC offset) recording the moment `sync-bios.py` last regenerated the file. It is written on every run that produces a substantive change (`data_changed or PHOTOS_CHANGED`), so it tracks the most recent meaningful refresh rather than the last time the workflow merely executed. The same value is mirrored into `source.last_synced` alongside the form and sheet URLs.

The directory page reads `generated_at` to render a discreet "Directory last updated" line under the page lede, so visitors can see how current the listing is without opening the repo. Because the stamp only moves when the data actually changes, that line stays honest: a week with no new submissions shows the same date as the week before.

## ORCID publications (`data/orcid-works.json`)

A member's profile is otherwise static: nothing on the card moves unless they re-submit the form. To give cards a living-CV layer with no member effort, `scripts/sync-orcid.py` runs as a step on the same weekly bios-sync workflow, right after `sync-bios.py`. For each member carrying an `orcid` iD it fetches their public works from the ORCID API (`https://pub.orcid.org/v3.0/<iD>/works`, no authentication) and writes the three most recent, by publication year, to `data/orcid-works.json`, keyed by directory slug.

The script is built to be safe to run unattended. It fails soft per member, so one malformed record skips that member and keeps the rest, and a failed fetch carries the member's previous works over rather than dropping them, so a transient ORCID outage cannot wipe the file. It is idempotent like the other syncs: when the trimmed works are unchanged it leaves the file alone, so a quiet week opens no auto-PR. The shape of the file is gated by `scripts/check-data-shape.py`, and `scripts/test-sync-orcid.py` covers the parsing and the fail-soft paths.

The directory loads this file lazily: `/people.html` fetches it only when a visitor expands a card, so member cards at rest carry none of its weight. ORCID works are public records the member chose to publish under their public iD, the same posture the site takes for cost.eu data.

## Exporting the data

`data/bios.json` is the canonical export, version-controlled in this repo. To dump it to CSV one-off:

```bash
python3 -c "import json, csv, sys; d=json.load(open('data/bios.json')); w=csv.DictWriter(sys.stdout, fieldnames=d['members'][0].keys()); w.writeheader(); w.writerows(d['members'])" > bios.csv
```

The Sheet itself is also exportable via *File → Download → CSV / XLSX*.
