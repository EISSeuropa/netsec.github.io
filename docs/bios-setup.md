# Setting up the member bios Google Form

This guide walks through creating the Google Form, linking it to a Sheet, and wiring the published Sheet into the auto-sync workflow. **One-time setup, ~30 minutes.** After this, all you do is review the weekly PR.

## How the pipeline works

```
Google Form ──► Google Sheet ──► sync-bios.yml (weekly) ──► PR ──► merge ──► /people/
```

- Members fill in the form once. Google records the response in the linked Sheet.
- Every Monday at 05:15 UTC (and on manual dispatch), the `Sync member bios from Google Form` workflow reads the Sheet as CSV, downloads any new headshots, regenerates `data/bios.json`, and opens a PR if anything changed.
- You merge the PR. The new bio appears on `/people/`.

Members can update their entries by submitting again — the script dedupes by email, keeping the most recent submission.

## Step 1 · Create the form

1. Go to <https://forms.google.com> and create a new blank form.
2. Title it **NetSec member bio**. Suggested description: *"Submit your bio for the NetSec member directory at netsec-cost.eu. Takes ~5 minutes. You can edit your response later via the link in your confirmation email."*
3. Add these questions, in this order. **The text of each question must match `scripts/bios-source.json`** — if you rename a question, update that file to match.

| # | Question text | Type | Required? |
|---|---|---|---|
| 1 | **Full name (with title — Dr / Prof / Mr / Ms)** | Short answer | ✅ |
| 2 | **Country** | Dropdown (paste the COST member-country list) | ✅ |
| 3 | **Institution or organisation** | Short answer | ✅ |
| 4 | **Public email (optional, will be shown on the site)** | Short answer | ⬜ |
| 5 | **Short bio (max 300 words)** | Paragraph | ✅ |
| 6 | **Research keywords (comma-separated, 3–5 suggested)** | Short answer | ⬜ |
| 7 | **Working Group membership** | Checkboxes: *WG1, WG2, WG3, WG4* | ⬜ |
| 8 | **Personal or institutional website (optional)** | Short answer | ⬜ |
| 9 | **ORCID iD (optional)** | Short answer | ⬜ |
| 10 | **LinkedIn URL (optional)** | Short answer | ⬜ |
| 11 | **X / Twitter URL (optional)** | Short answer | ⬜ |
| 12 | **Bluesky URL (optional)** | Short answer | ⬜ |
| 13 | **Mastodon URL (optional)** | Short answer | ⬜ |
| 14 | **Headshot photo (optional)** | File upload — image only — max 5 MB | ⬜ |
| 15 | **I consent to publication of my bio on netsec-cost.eu** | Checkboxes: single option | ✅ |

In *Settings → Responses*, **enable**:

- ☑ Collect email addresses (so we can match submissions and offer edit links)
- ☑ Allow response editing (so members can update later)
- ☑ Limit to 1 response (require Google sign-in — recommended; if you'd rather allow anonymous, leave off)

## Step 2 · Link to a Sheet

1. In the form's *Responses* tab, click the green Sheets icon → *Link to Sheets* → *Create a new spreadsheet*. Accept the default name.
2. Open the Sheet that just opened. Each response will appear as a new row. Each form question becomes a column header.

## Step 3 · Publish the Sheet as CSV

The workflow reads the Sheet via its *publish to web* CSV URL — there is no authentication, it's a long unguessable URL.

1. In the Sheet, *File → Share → Publish to web*.
2. **Link** tab:
   - Document picker → choose the worksheet that contains the form responses (usually *Form Responses 1*).
   - Format → **Comma-separated values (.csv)**.
3. ☑ *Automatically republish when changes are made*.
4. Click **Publish**, confirm.
5. Copy the URL it gives you. It will look like:
   ```
   https://docs.google.com/spreadsheets/d/e/<long-id>/pub?gid=<gid>&single=true&output=csv
   ```

## Step 4 · Wire the URL into the repo

Open `scripts/bios-source.json` and paste the URL into `sheet.csv_url`:

```json
{
  "sheet": {
    "csv_url": "https://docs.google.com/spreadsheets/d/e/.../pub?gid=...&single=true&output=csv"
  },
  ...
}
```

Commit this change to `main`. The next workflow run (manual *or* the next Monday) will pick it up.

## Step 5 · Photo permissions — the one Google quirk

Files uploaded via Google Forms land in a private Drive folder by default. For the workflow to download them, they need to be readable without auth.

**Easiest approach**: in Google Drive, find the form's auto-created folder (usually under `My Drive → <Form name> (File responses)`). Right-click → *Share* → set general access to **Anyone with the link → Viewer**. This applies to the folder and inherits to every file uploaded in the future.

If you prefer per-file control instead, do the same right-click → *Share* dance on each photo as submissions come in. More secure but more work.

## Trying it out

After Step 4, you can trigger the workflow manually:

1. Go to *Actions → Sync member bios from Google Form*.
2. Click *Run workflow*.
3. Wait ~30 s. If the Sheet has form responses, a PR opens on the `bios-sync/auto` branch. If it doesn't, the run is a clean no-op.

## Sharing the form with members

Once the workflow is live, the form's public URL (top right of the form editor → *Send → 🔗 Link*) is what you send out. A typical announcement email:

> Dear colleague,
>
> Please take 5 minutes to submit your bio to the NetSec member directory:
>
>   <https://forms.google.com/...your-form-url>
>
> Your entry will appear at <https://netsec-cost.eu/people.html> within a week of submission. You can edit your response any time using the link in your confirmation email.

## What to do when you want to remove or correct a bio

Two options:

1. **Edit the Sheet directly.** The form-response sheet is just data — you can correct typos, fix country misspellings, etc. directly. The next workflow run picks up your edits.
2. **Delete a row from the Sheet.** The next run will drop the corresponding bio from `/people/`.

If you delete by accident, restore the Sheet row from Drive's version history.

## Exporting the data

`data/bios.json` is the canonical export, version-controlled in this repo. To dump it to CSV for a one-off analysis:

```bash
python3 -c "import json, csv, sys; d=json.load(open('data/bios.json')); w=csv.DictWriter(sys.stdout, fieldnames=d['members'][0].keys()); w.writeheader(); w.writerows(d['members'])" > bios.csv
```

The Sheet itself is also exportable via *File → Download → Microsoft Excel / CSV*.
