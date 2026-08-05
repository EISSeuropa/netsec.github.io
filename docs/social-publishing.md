# Social publishing pipeline

Automatically turns NetSec **news** and the **weekly member spotlight** into
social posts on **Bluesky** and **LinkedIn**, with a human approval step
before anything goes public. Issue [#1072].

This is being built in phases:

| Phase | What | Status |
| --- | --- | --- |
| 1 | Composer + dedup ledger + `--dry-run` preview + tests | **done** |
| 2 | Bluesky adapter + the `social-bluesky.yml` workflow + the approval gate | **done** (live once the Bluesky secrets + `social` environment exist) |
| 3 | LinkedIn adapter (Posts API + image upload) + token refresh, wired into the gated `social-bluesky.yml` and the ungated `spotlight-rotate.yml` | **done** (live once the LinkedIn secrets exist on the `social` / `social-auto` environments) |

`--dry-run` publishes nothing: it builds the post text, picks the image, and
prints exactly what *would* go out. Live posting only happens inside the
`social` environment, after a reviewer approves.

## How it will work

```
news.xml (a new entry)   ─┐
                          ├─►  scripts/social-post.py  ─►  Bluesky + LinkedIn
data/spotlight.json (wk) ─┘        composes text + image; records the ledger
```

- **News.** Each new entry in the RSS feed (`/news.xml`) becomes one post:
  the headline, a trimmed summary, and the link. The feed is the trigger, so
  this works the same on the sister EISS site.
- **Spotlight.** Every **Tuesday at 10:00 Central European time**, the member
  in `data/spotlight.json` (the same one shown on the home page) becomes a
  post, with their **OG card** (`assets/og/people/<slug>.png`) as the image.
  Cron can't follow DST, so `spotlight-rotate.yml` fires at both 08:00 and
  09:00 UTC on Tuesdays and a gate job lets through only the one that lands at
  10:00 Europe/Paris.
- **Tagging the member.** When a member has supplied a Bluesky profile
  (`bluesky` in `data/bios.json`), the handle is woven into the Bluesky post as
  an @-mention and resolved to a richtext facet, so the person is notified. On
  LinkedIn a public vanity URL can't become a notifying person-mention, so the
  member's LinkedIn profile link is posted as the **first comment** instead of
  in the body (a body link would suppress the post's reach). Both degrade
  silently: no handle, no mention; a failed comment leaves the post standing.
- **No duplicates.** `data/social-posted.json` records what has been posted
  (news by feed GUID; spotlight by member + ISO week), so re-runs post
  nothing and a member is posted at most once per week. The ledger is read
  from the checkout, and the rotation workflow checks out `main`, so the guard
  only holds once the week's auto-PR has merged. Re-running **Rotate member
  spotlight** while that PR is still open reads a ledger without the week's
  key and posts the spotlight a second time. Wait for the merge, or use the
  dry run.
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

## Curated threads (hand-written multi-post announcements)

Some announcements need more than one auto-composed post: a launch, an award,
a recap. For those, write a thread spec under `data/social-threads/<slug>.json`
and post it with `--thread`:

```bash
python3 scripts/social-post.py --thread data/social-threads/best-paper-prize-2026.json --dry-run
python3 scripts/social-post.py --thread data/social-threads/best-paper-prize-2026.json --live   # behind the gate
```

A spec is a `key` (recorded in the ledger so it cannot double-post), an
ordered list of `posts`, and an optional `image` on any post. Each post is
verbatim text. Inside the text:

- `@handle.bsky.social` becomes a clickable mention (the handle is resolved to
  its DID live, at post time).
- An `http(s)://` URL becomes a clickable link.

A post can also carry a **`card`** instead of an `image`, which renders as a
clickable link-preview card (`app.bsky.embed.external`): `{uri, title,
description, thumb}`, where `thumb` is a repo image path (typically the page's
own OG card). The two are mutually exclusive: a post leads with **either** an
`image` **or** a `card`. A card suits a landscape link preview where the URL
should be the single tap target (leave it out of the post text). An `image`
suits a portrait or hero visual (a poster), with the URL kept in the text as a
link facet, since a link card would crop a portrait image to a thin strip. The
Directory Early-Access thread (`data/social-threads/directory-early-access.json`)
is image-led for exactly that reason.

Posts are chained as a reply thread (post 2 replies to post 1, and so on). The
dry-run prints each post with its grapheme count against the 300 limit, flags
any post that is over, lists the mentions and links it found, and shows whether
the ledger has already posted the thread. The live path refuses to post if any
post is over the limit. Images may be PNG or JPEG.

To post a thread **through the approval gate** rather than locally: GitHub
→ Actions → *Publish to Bluesky (approval-gated)* → **Run workflow**, and set
the `thread` input to the spec slug (the filename without `.json`, e.g.
`best-paper-prize-2026`). The `preview` job writes the dry-run to the run
summary, then the `publish` job waits for a required reviewer before posting.
Leave `thread` empty for the normal news / spotlight run.

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
4. Under **Auth**, note the **Client ID** and **Primary Client Secret**, and
   generate an **access token** with the `w_organization_social` scope (OAuth
   "3-legged", authorised as a page admin). `scripts/linkedin-token.py` walks
   the two steps so you don't hand-build curl:
   ```
   python3 scripts/linkedin-token.py auth-url  --client-id <ID> --redirect-uri <URL>
   # open the printed URL, approve, copy the ?code= value, then:
   python3 scripts/linkedin-token.py exchange  --client-id <ID> --client-secret <SECRET> \
       --redirect-uri <URL> --code <CODE>
   ```
   It prints `LINKEDIN_ACCESS_TOKEN` and `LINKEDIN_REFRESH_TOKEN`. Run it
   locally; nothing leaves your machine except the call to LinkedIn.
   - **Important:** access tokens expire after **~60 days**. The adapter renews
     them automatically from the refresh token (which lasts ~1 year) **if** the
     Client ID and Secret are also in the environment; otherwise re-run
     `linkedin-token.py refresh` (or `exchange` once the refresh token lapses).
5. You will add these environment secrets in step D: `LINKEDIN_ORG_ID` (the
   number from step 1), `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_REFRESH_TOKEN`, and —
   to let the pipeline auto-renew — `LINKEDIN_CLIENT_ID` and
   `LINKEDIN_CLIENT_SECRET`. The adapter sends a `LinkedIn-Version` header
   pinned in `data/linkedin-api-version.json`. LinkedIn sunsets a version after
   ~12 months (a sunset version returns HTTP 426 and the post fails), so the
   `linkedin-version-check` workflow reads LinkedIn's published active-version
   list monthly and opens an auto-merging PR to bump the pin before it lapses.
   Set the `LINKEDIN_API_VERSION` env var to override the pin at runtime. If a
   live post is ever rejected mid-cycle, `social-post.py` emits a GitHub
   `::warning::` on the run so the failure is visible rather than silent.

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
| `LINKEDIN_CLIENT_ID` | step B.4 — lets the pipeline auto-renew an expired token |
| `LINKEDIN_CLIENT_SECRET` | step B.4 — same |

`LINKEDIN_ORG_ID` and `LINKEDIN_ACCESS_TOKEN` are the minimum to post; the other
three let the adapter renew the access token on its own when it expires. With
any LinkedIn secret unset, the channel is simply skipped (Bluesky still posts),
so you can add Bluesky first and LinkedIn later.

### E. (Optional) the `social-auto` environment for the auto spotlight

The **weekly member spotlight posts itself**, with no approval — it is
auto-generated, low-risk content. The rotation workflow (`spotlight-rotate.yml`)
runs in a second environment, **`social-auto`**, which holds the same
credentials but has **no required reviewer**, so the post goes straight out. It
posts to both Bluesky and LinkedIn, best-effort: a LinkedIn failure (e.g. an
expired token) never blocks the Bluesky post.

To enable it: **Settings → Environments → New environment → `social-auto`**,
leave **Required reviewers unchecked** (optionally restrict it to the `main`
branch), and add the same environment secrets there as on `social`:

| Secret | From |
| --- | --- |
| `BSKY_HANDLE` | step A — the bare handle |
| `BSKY_APP_PASSWORD` | step A |
| `LINKEDIN_ORG_ID` | step B.1 (omit the LinkedIn block to keep the spotlight Bluesky-only) |
| `LINKEDIN_ACCESS_TOKEN` | step B.4 |
| `LINKEDIN_REFRESH_TOKEN` | step B.4 |
| `LINKEDIN_CLIENT_ID` | step B.4 |
| `LINKEDIN_CLIENT_SECRET` | step B.4 |

If you skip this environment entirely, the rotation still runs and the home-page
spotlight still rotates; the post step simply logs a warning and does nothing (no
secrets). News and curated threads are unaffected — they stay on the gated
`social` environment.

Why environment secrets and not repository secrets: an environment secret is
only released to a job that targets `environment: social`, and only **after**
the required-reviewer approval passes. So the posting credentials are
unreadable until you approve — the gate protects both the action (posting) and
the access (the secret). A repository secret, by contrast, is readable by any
workflow at any time, which is a wider blast radius for no benefit here. Do not
add them at repo level as well.

Secrets are write-only: once saved, no one (including the maintainer) can read
them back, only overwrite them.

### F. Test it (gated first, LinkedIn included)

Once the Bluesky secrets (A) and the `social` environment (C, D) exist, the
`Publish to Bluesky (approval-gated)` workflow is live. **Validate LinkedIn
through this gated path first**, before relying on the ungated weekly spotlight:
the preview shows the exact post and you approve each one, so the first real
LinkedIn post is one you have eyes on.

1. In the repo, go to **Actions → Publish to Bluesky (approval-gated) → Run
   workflow**. Leave the input as `all` (or pick `spotlight`) and run it.
2. The **preview** job runs first and writes the exact post(s) + image to the
   run summary, in both the Bluesky and LinkedIn renderings. Open the run and
   read it.
3. The **publish** job is then held at the `social` gate — you (the reviewer)
   get an email "Deployment review pending". Read the preview, then click
   **Approve and deploy** to post, or **Reject** to cancel.
4. After approval, the post goes to **both Bluesky and LinkedIn** and a small
   auto-merging PR records it in the ledger so it is never posted twice.

After that first test, it runs on its own: a new news item (a `news.xml`
change on `main`) or the weekly spotlight rotation (a `data/spotlight.json`
change) triggers the same preview-then-approve flow. Nothing posts without your
approval.

A first-run caveat on the LinkedIn image upload: the adapter uploads the
spotlight OG card with an HTTP `PUT` to LinkedIn's returned upload URL. If a
spotlight post ever fails with a `405 Method Not Allowed` on the image step, the
upload wants `POST` instead — a one-line change in `LinkedInChannel._upload_image`
(`scripts/social-post.py`). Text-only posts (news) are unaffected.

The ledger is seeded so the four news items already on the site are not
re-announced; the **current spotlight** is left unseeded, so your first run
posts it. To pause everything, remove the `BSKY_APP_PASSWORD` secret (the
publish step then fails safely and posts nothing).

---

## What gets posted (templates)

- **News:** `📣 {headline}` + a one-paragraph summary + the article link.
  Bluesky is trimmed to 300 characters; LinkedIn carries the full summary plus
  `#EuropeanSecurity #COSTAction`.
- **Spotlight:** `⭐ NetSec Directory Spotlight` + "Meet {name} in the NetSec
  Directory, {role}. Working on {themes}. {status}" + the profile link, with the
  member's OG card image. The **status** sentence is built from the same fields
  as the OG card (Working-Group membership or leadership, mentorship, STSM
  hosting) and is omitted when the member has none of them. **Themes** are
  title-cased with acronym preservation (so "black sea security" reads "Black
  Sea Security", "EU foreign policy" reads "EU Foreign Policy"). The **role**
  joins the submitted position and affiliation, unless the position already
  names the affiliation, in which case it is not repeated.

  Bluesky has 300 characters for all of that, so `read_spotlight` drops whole
  pieces until the text fits rather than letting `Post.render` cut a word in
  half: three themes, then two, then one, then none, then the status sentence,
  and finally the role itself, which leaves the bare introduction and the
  profile link. A submitted position long enough to fill the limit on its own
  is what the last rung is for (PR #1503). The pieces come off in that order
  because the link is what the post is for and the mentorship line is what a
  reader can act on.

Posts are **English only**. Edit the templates in `scripts/social-post.py`
(the `Post.render` method and the `read_spotlight` composer) to adjust tone,
emoji, or hashtags.

## Opting a news item out of the auto-post

A news item can carry an optional **`social`** field in `data/news.json` that
controls only the Bluesky auto single-post (never the website or the RSS feed):

- absent / `"auto"` — the gated workflow offers the item (default).
- `"skip"` — never auto-post it.
- `"thread:<slug>"` — the item is announced as a curated thread
  (`data/social-threads/<slug>.json`), so the single-post stands down and you
  post the thread by hand instead.

This is what stops a big announcement from going out twice (once as the plain
auto-post, once as the thread). The dedup key is the news item **id** (its
`<guid>`), not the link, so two items pointing at the same page never collide.

## Nothing-pending is skipped, not left waiting

The `preview` job counts what would actually post and the `publish` job only
runs when that count is non-zero. So an edit to an old item (which re-fires the
workflow but adds nothing new) no longer leaves a no-op approval sitting in the
queue — the run finishes with a `Nothing pending` notice. When there *is*
something to post, the notice says so and the required reviewer is emailed.

## Keeping the LinkedIn API version current

LinkedIn's posting API is versioned by month (`YYYYMM`) and each version is
supported for about a year before it sunsets. A sunset version returns HTTP
426 and every LinkedIn post fails, while Bluesky (a different service) keeps
working. This is what happened once: the pin sat stale for 13 months and the
weekly spotlight quietly stopped reaching LinkedIn until a missing post was
noticed by hand.

Two mechanisms now prevent a repeat:

- The version is pinned in `data/linkedin-api-version.json`, and the
  `linkedin-version-check` workflow runs `scripts/check-linkedin-version.py`
  monthly. The script reads LinkedIn's published active-version list and,
  once the pin reaches the trailing edge of that window, opens an
  auto-merging PR that bumps it to the current latest. Most months nothing is
  due. The `LINKEDIN_API_VERSION` env var still overrides the pin at runtime.
- A failed live post is no longer silent. The best-effort spotlight path
  (which deliberately does not abort when one channel fails) now emits a
  GitHub `::warning::`, so a LinkedIn failure surfaces on the workflow run
  even though the job stays green.

Because the spotlight's dedup key is written once any channel posts, fixing a
sunset version does **not** back-fill a spotlight that already went out on
Bluesky. That member's key is spent, so the next week's spotlight is the first
to reach both channels again.

## Notes

- The pipeline is a **consumer** of already-published surfaces (the RSS feed
  and the spotlight state), so it never invents content; it only reposts what
  is already on the site.
- The ledger (`data/social-posted.json`) is the single source of "already
  posted". To re-post something deliberately, remove its key. The news key is
  the item id (`news::<id>`); the spotlight key includes the ISO week; threads
  use `thread::<slug>`.
- A published post reaches the ledger on `main` only once its auto-merging PR
  lands, so both jobs of `social-bluesky.yml` read `data/social-posted.json`
  from the `social/ledger` branch whenever that branch still exists. Otherwise
  a news push arriving in the gap would offer the reviewer a post that has
  already gone out (run 30129049311 on 24 July 2026 is the case that prompted
  this).
- Account creation, app registration, entering credentials, and granting
  OAuth are done by a person, never by the website code.
