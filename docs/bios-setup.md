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
| 8 | **Working Group involvement (tick all that apply)** | Checkboxes: *WG1 · Building the Network · WG2 · Transfer of Knowledge · WG3 · Fostering the Next Generation · WG4 · Ensuring Inclusion · None yet* | ⬜ |
| 9 | **Personal or institutional website (optional)** | Short answer | ⬜ |
| 10 | **ORCID iD (optional)** | Short answer | ⬜ |
| 11 | **LinkedIn URL (optional)** | Short answer | ⬜ |
| 12 | **X / Twitter URL (optional)** | Short answer | ⬜ |
| 13 | **Bluesky URL (optional)** | Short answer | ⬜ |
| 14 | **Mastodon URL (optional)** | Short answer | ⬜ |
| 15 | **Headshot photo (optional)** | File upload — image only — max 5 MB | ⬜ |
| 16 | **I consent to publication of my bio on netsec-cost.eu** | Checkboxes — single option | ✅ |

> **WG-checkboxes parsing.** The script extracts the digits 1–4 from whatever the checkbox column contains, so the precise wording of each option doesn't matter as long as it includes the WG number. *"WG2 · Transfer of Knowledge"* parses to `2`; *"None yet"* parses to no WG. You can rename the WGs freely later.

In *Settings → Responses*, **enable**:

- ☑ Collect email addresses
- ☑ Allow response editing (so members can update later via the link in their confirmation email)
- ☑ Limit to 1 response (require Google sign-in — recommended; if you'd rather allow anonymous, leave off)

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
> You can edit your response any time using the link in your confirmation email. Please feel free to forward to colleagues who'd value being part of the network.

## Editing or removing a bio

- **Edit the Sheet directly** — the response sheet is just data. Correct typos, fix country misspellings, etc. The next workflow run picks up your edits.
- **Delete a row** — the next run will drop the corresponding bio from `/people/`.

If you delete by accident, Drive's version history can restore the Sheet row.

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

The file has two sections:

- **`acronyms`** is a flat list of preferred display forms (`UN`, `NATO`, `EU`, `IoT`, `R&D`, …). When one of these words appears in any position in a submitted keyword, the sentence-case normaliser preserves its canonical capitalisation. So `eu foreign policy` becomes `EU foreign policy`, not `Eu foreign policy`.

- **`aliases`** maps a canonical display form to a list of lowercased aliases that resolve to it. Use this when two genuinely-distinct submitted phrases should collapse (`fpa` → `Foreign policy analysis`) or when a phrase needs to override the auto-normaliser (`eu-nato relations` → `EU–NATO relations` with the en-dash).

The maintainer extends the file by hand when a submission lands. The sync also logs `· possible alias candidate (3× 'foreign policy') ↔ (1× 'foreign policy analysis'); distance=9, substring` for pairs that look close enough to be worth a manual merge. Distance ≤ 2 Levenshtein and word-boundary substring containment both trigger the hint; already-paired canonicals are suppressed.

If `data/keyword-aliases.json` is missing or malformed, the sync falls back to identity normalisation (sentence-case the whole string, no acronym preservation) and prints a warning. The renderer's own inline fallback covers the same case for visitors who land before the next sync runs.

## Exporting the data

`data/bios.json` is the canonical export, version-controlled in this repo. To dump it to CSV one-off:

```bash
python3 -c "import json, csv, sys; d=json.load(open('data/bios.json')); w=csv.DictWriter(sys.stdout, fieldnames=d['members'][0].keys()); w.writeheader(); w.writerows(d['members'])" > bios.csv
```

The Sheet itself is also exportable via *File → Download → CSV / XLSX*.
