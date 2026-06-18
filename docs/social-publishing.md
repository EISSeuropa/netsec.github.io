# Social publishing pipeline

Automatically turns NetSec **news** and the **weekly member spotlight** into
social posts on **Bluesky** and **LinkedIn**, with a human approval step
before anything goes public. Issue [#1072].

This is being built in phases:

| Phase | What | Status |
| --- | --- | --- |
| 1 | Composer + dedup ledger + `--dry-run` preview + tests | **done** (this PR) |
| 2 | Bluesky adapter, the two workflows, the `social` approval gate | after secrets are set |
| 3 | LinkedIn adapter | after the LinkedIn app + token exist |

Phase 1 publishes nothing. It builds the post text + picks the image and
prints exactly what *would* go out, so the wording and images can be reviewed
before any account is connected.

## How it will work

```
news.xml (a new entry)   ─┐
                          ├─►  scripts/social-post.py  ─►  Bluesky + LinkedIn
data/spotlight.json (wk) ─┘        composes text + image; records the ledger
```

- **News.** Each new entry in the RSS feed (`/news.xml`) becomes one post:
  the headline, a trimmed summary, and the link. The feed is the trigger, so
  this works the same on the sister EISS site.
- **Spotlight.** Once a week, the member in `data/spotlight.json` (the same
  one shown on the home page) becomes a post, with their **OG card**
  (`assets/og/people/<slug>.png`) as the image.
- **No duplicates.** `data/social-posted.json` records what has been posted
  (news by feed GUID; spotlight by member + ISO week), so re-runs post
  nothing and a member is posted at most once per week.
- **Approval gate.** The publishing job runs inside a GitHub *environment*
  called `social` with a required reviewer. GitHub pauses the job and emails
  the reviewer; the run page shows the exact text and image; the post is sent
  only after the reviewer clicks **Approve**.

## Preview the posts now (no setup needed)

```bash
python3 scripts/social-post.py --dry-run            # everything pending
python3 scripts/social-post.py --dry-run --kind spotlight
```

This prints the Bluesky version (trimmed to 300 characters) and the LinkedIn
version (full text + hashtags) for each pending item, plus the image path. It
publishes nothing and writes nothing.

---

## Setup — for the social media manager

These are the one-time steps to connect the accounts. They need **admin
access to the NetSec Bluesky and LinkedIn accounts** and **admin access to
the GitHub repository's settings**. Nothing here is done by the website code;
the workflow only reads the secrets you add.

### A. Bluesky (the easy one)

1. Sign in to the NetSec Bluesky account (`netsec-cost.eu`).
2. Go to **Settings → Privacy and security → App passwords**.
3. Click **Add App Password**, name it `netsec-website`, and copy the
   generated password (format `xxxx-xxxx-xxxx-xxxx`). It is shown once.
   - Use an **app password**, never the real account password.
4. You will add two environment secrets in step D: `BSKY_HANDLE` (the bare
   handle, e.g. `netsec-cost.eu`, no leading `@`) and `BSKY_APP_PASSWORD`
   (the app password from step 3).

### B. LinkedIn (more involved; needs a developer app)

LinkedIn only allows posting to a **Company Page** through a registered app
with a page-admin's approval. Plan ~30 minutes.

1. Confirm you are an **admin of the NetSec LinkedIn Company Page**
   (`linkedin.com/company/costnetsec`). Note its **Organization ID** (visible
   in the page URL as admin, or via the page's "Admin tools").
2. Go to <https://www.linkedin.com/developers/apps> and **Create app**:
   - Associate it with the NetSec Company Page.
   - Name it e.g. "NetSec website auto-post".
3. On the app's **Products** tab, request **"Share on LinkedIn"** and
   **"Advertising API"** / **"Community Management API"** access (the product
   that grants `w_organization_social`). Page-admin approval may be required;
   approve it from the page.
4. Under **Auth**, note the **Client ID** and **Client Secret**, and generate
   an **access token** with the `w_organization_social` scope (the OAuth
   "3-legged" flow, authorised as a page admin).
   - **Important:** LinkedIn access tokens expire after **~60 days**. Save the
     **refresh token** too; the pipeline (phase 3) will use it to renew. Put a
     recurring reminder to re-authorise if refresh ever fails.
5. You will add these environment secrets in step D: `LINKEDIN_ORG_ID` (the number
   from step 1), `LINKEDIN_ACCESS_TOKEN`, and `LINKEDIN_REFRESH_TOKEN`.

### C. Create the approval gate (do this before adding the secrets)

1. Go to **Settings → Environments → New environment**, name it exactly
   **`social`**.
2. Under **Deployment protection rules**, tick **Required reviewers** and add
   yourself (and/or the maintainer).
3. Optionally set a **wait timer** or restrict to certain branches.

From then on, when a post is pending, GitHub emails the reviewer "Deployment
review pending". Open the run, read the composed post and image in the summary,
and click **Approve and deploy** to send it, or **Reject** to cancel.

### D. Add the secrets to the `social` environment

Add the credentials as **environment secrets on `social`**, NOT as
repository secrets. Open **Settings → Environments → `social` →
Environment secrets → Add secret**, and add each of:

| Secret | From |
| --- | --- |
| `BSKY_HANDLE` | step A — the **bare** handle, e.g. `netsec-cost.eu` (no leading `@`) |
| `BSKY_APP_PASSWORD` | step A |
| `LINKEDIN_ORG_ID` | step B.1 |
| `LINKEDIN_ACCESS_TOKEN` | step B.4 |
| `LINKEDIN_REFRESH_TOKEN` | step B.4 |

Why environment secrets and not repository secrets: an environment secret is
only released to a job that targets `environment: social`, and only **after**
the required-reviewer approval passes. So the posting credentials are
unreadable until you approve — the gate protects both the action (posting) and
the access (the secret). A repository secret, by contrast, is readable by any
workflow at any time, which is a wider blast radius for no benefit here. Do not
add them at repo level as well.

Secrets are write-only: once saved, no one (including the maintainer) can read
them back, only overwrite them.

### E. Go live

Once A–D are done, the maintainer enables the phase-2 workflows. The first
real post will pause for your approval. To pause everything at any time,
remove a required secret or set the `social.enabled` switch to `false`.

---

## What gets posted (templates)

- **News:** `📣 {headline}` + a one-paragraph summary + the article link.
  Bluesky is trimmed to 300 characters; LinkedIn carries the full summary plus
  `#EuropeanSecurity #COSTAction`.
- **Spotlight:** `🔦 Member spotlight` + "Meet {name}, {role} at {affiliation}.
  Working on {themes}." + the profile link, with the member's OG card image.

Posts are **English only**. Edit the templates in `scripts/social-post.py`
(the `Post.render` method and the `read_spotlight` composer) to adjust tone,
emoji, or hashtags.

## Notes

- The pipeline is a **consumer** of already-published surfaces (the RSS feed
  and the spotlight state), so it never invents content; it only reposts what
  is already on the site.
- The ledger (`data/social-posted.json`) is the single source of "already
  posted". To re-post something deliberately, remove its key.
- Account creation, app registration, entering credentials, and granting
  OAuth are done by a person, never by the website code.
