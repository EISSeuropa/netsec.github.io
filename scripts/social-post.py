#!/usr/bin/env python3
"""
Compose and (in later phases) publish social posts for NetSec news + the
weekly member spotlight. Issue #1072.

PHASE 1 (this file): the composer, the dedup ledger, and a --dry-run that
prints exactly what each channel would post. No credentials are needed to
run --dry-run, and nothing is published. The live Bluesky / LinkedIn
adapters are wired in later phases behind a GitHub `social` environment
(an approval gate), once the maintainer has registered the apps and added
the secrets (see docs/social-publishing.md).

Two post sources, both read from already-published surfaces so this script
stays a pure consumer:
  - News:     parsed from the RSS feed news.xml (one post per new entry,
              deduped on the entry's stable key).
  - Spotlight: the member in data/spotlight.json `current`, with the
              per-member OG card (assets/og/people/<slug>.png) as the image.

A ledger (data/social-posted.json) records what has been posted so re-runs
publish nothing. The spotlight key includes the ISO week, so the same
member is posted at most once per week.

Usage:
    python3 scripts/social-post.py --dry-run                  # preview everything pending
    python3 scripts/social-post.py --dry-run --kind spotlight # just the spotlight
    python3 scripts/social-post.py --live --channel bluesky    # phase 2+, needs secrets

Stdlib only; runs under /usr/bin/python3.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEWS_XML = ROOT / "news.xml"
SPOTLIGHT = ROOT / "data" / "spotlight.json"
BIOS = ROOT / "data" / "bios.json"
LEDGER = ROOT / "data" / "social-posted.json"
SITE = "https://netsec-cost.eu"
SITE_OG = ROOT / "assets" / "images" / "og-image.png"

# Bluesky posts are capped at 300 graphemes; we trim to a safe budget.
BLUESKY_LIMIT = 300
HASHTAGS = "#EuropeanSecurity #COSTAction"


# --------------------------------------------------------------------------
# Post model + composers
# --------------------------------------------------------------------------
@dataclass
class Post:
    kind: str            # "news" | "spotlight"
    key: str             # dedup key recorded in the ledger
    title: str
    summary: str
    link: str
    image: Path | None = None
    image_alt: str = ""
    hashtags: str = HASHTAGS

    def render(self, channel: str) -> str:
        """Channel-appropriate text. Bluesky is trimmed to its limit; the
        link is always kept whole (it is what the post is for)."""
        head = f"📣 {self.title}" if self.kind == "news" else f"🔦 {self.title}"
        tail = f"\n\n{self.link}"
        if channel == "bluesky":
            budget = BLUESKY_LIMIT - len(head) - len(tail) - 2
            summary = _truncate(self.summary, max(0, budget))
            body = f"{head}\n\n{summary}{tail}" if summary else f"{head}{tail}"
            return body[:BLUESKY_LIMIT]
        # LinkedIn (and the dry-run echo): room for the full summary + tags.
        parts = [head, "", self.summary, "", self.link]
        if self.hashtags:
            parts += ["", self.hashtags]
        return "\n".join(p for p in parts if p is not None)


def _truncate(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    if limit <= 1:
        return ""
    cut = text[: limit - 1].rsplit(" ", 1)[0]
    return (cut or text[: limit - 1]).rstrip(",.;:") + "…"


def _strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "").strip()


def read_news_feed() -> list[Post]:
    """Parse news.xml into posts (stdlib regex; the feed is our own, small,
    and well-formed). One post per <item>, keyed on <guid> or the link."""
    if not NEWS_XML.exists():
        return []
    xml = NEWS_XML.read_text(encoding="utf-8")
    posts = []
    for block in re.findall(r"<item>(.*?)</item>", xml, re.S):
        def grab(tag):
            m = re.search(rf"<{tag}>(.*?)</{tag}>", block, re.S)
            return m.group(1).strip() if m else ""
        title = html.unescape(_strip_tags(grab("title")))
        link = html.unescape(_strip_tags(grab("link")))
        guid = html.unescape(_strip_tags(grab("guid"))) or link
        desc = grab("description")
        desc = re.sub(r"^<!\[CDATA\[|\]\]>$", "", desc).strip()
        summary = html.unescape(_strip_tags(desc))
        if not (title and link):
            continue
        posts.append(Post(
            kind="news",
            key=f"news::{guid}",
            title=title,
            summary=summary,
            link=link,
            image=SITE_OG if SITE_OG.exists() else None,
            image_alt="NetSec, COST Action CA24154",
        ))
    return posts


def _iso_week(date_str: str) -> str:
    try:
        d = dt.date.fromisoformat((date_str or "")[:10])
    except ValueError:
        d = dt.datetime.now(dt.timezone.utc).date()
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def read_spotlight() -> Post | None:
    """The current weekly spotlight member as a post, or None when the
    spotlight is dormant or the member is missing."""
    if not SPOTLIGHT.exists() or not BIOS.exists():
        return None
    sp = json.loads(SPOTLIGHT.read_text(encoding="utf-8"))
    if not sp.get("active") or not sp.get("current"):
        return None
    slug = sp["current"]
    members = {m.get("id"): m for m in json.loads(BIOS.read_text(encoding="utf-8")).get("members", [])}
    m = members.get(slug)
    if not m:
        return None
    role = " · ".join(b for b in [(m.get("position") or "").strip(),
                                  (m.get("affiliation") or "").strip()] if b)
    themes = [t for t in (m.get("canonical_keywords") or [])][:3]
    bits = [f"Meet {m.get('name', slug)}, a member of the NetSec network."]
    if role:
        bits.append(role + ".")
    if themes:
        bits.append("Working on " + ", ".join(themes).lower() + ".")
    card = ROOT / "assets" / "og" / "people" / f"{slug}.png"
    week = _iso_week(sp.get("featuredSince", ""))
    return Post(
        kind="spotlight",
        key=f"spotlight::{slug}::{week}",
        title="Member spotlight",
        summary=" ".join(bits),
        link=f"{SITE}/people/{slug}.html",
        image=card if card.exists() else (SITE_OG if SITE_OG.exists() else None),
        image_alt=f"{m.get('name', slug)} — NetSec member",
    )


# --------------------------------------------------------------------------
# Ledger
# --------------------------------------------------------------------------
def load_ledger() -> dict:
    if LEDGER.exists():
        data = json.loads(LEDGER.read_text(encoding="utf-8"))
    else:
        data = {}
    data.setdefault("posted", [])
    return data


def save_ledger(data: dict) -> None:
    LEDGER.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def pending(kinds: set[str], ledger: dict) -> list[Post]:
    posted = set(ledger.get("posted", []))
    out = []
    if "news" in kinds:
        out += [p for p in read_news_feed() if p.key not in posted]
    if "spotlight" in kinds:
        sp = read_spotlight()
        if sp and sp.key not in posted:
            out.append(sp)
    return out


# --------------------------------------------------------------------------
# Channels
# --------------------------------------------------------------------------
@dataclass
class Channel:
    name: str

    def configured(self) -> bool:
        return False

    def publish(self, post: Post) -> str:  # returns a post URL/id
        raise NotImplementedError


class DryRunChannel(Channel):
    """Prints what would be posted. Always available; needs no secrets."""

    def configured(self) -> bool:
        return True

    def publish(self, post: Post) -> str:
        for ch in ("bluesky", "linkedin"):
            print(f"  ── would post to {ch} ──")
            for line in post.render(ch).splitlines():
                print(f"    {line}")
            if post.image:
                print(f"    [image: {post.image.relative_to(ROOT)} | alt: {post.image_alt}]")
            print()
        return "dry-run"


# Live adapters. Bluesky is implemented (phase 2); LinkedIn is a phase-3 stub.
# Both are guarded by credential checks so the script stays import-safe and
# runnable in dry-run without any secrets. The live path runs only behind the
# `social` GitHub environment approval gate. See docs/social-publishing.md.
def _http_json(url: str, payload: dict | None = None, headers: dict | None = None,
               raw: bytes | None = None, content_type: str | None = None) -> dict:
    """Minimal JSON HTTP helper (stdlib urllib). POST when payload/raw given."""
    import urllib.error
    import urllib.request

    hdrs = dict(headers or {})
    data = None
    if raw is not None:
        data = raw
        hdrs["Content-Type"] = content_type or "application/octet-stream"
    elif payload is not None:
        data = json.dumps(payload).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=hdrs, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:  # surface the API error body
        detail = e.read().decode("utf-8", "replace")
        raise SystemExit(f"HTTP {e.code} from {url}: {detail}") from e


def link_facets(text: str, url: str) -> list:
    """A Bluesky richtext facet making `url` (as it appears in `text`) a
    clickable link. Byte offsets are over the UTF-8 encoding, per the spec."""
    if not url or url not in text:
        return []
    btext = text.encode("utf-8")
    burl = url.encode("utf-8")
    start = btext.find(burl)
    if start < 0:
        return []
    return [{
        "index": {"byteStart": start, "byteEnd": start + len(burl)},
        "features": [{"$type": "app.bsky.richtext.facet#link", "uri": url}],
    }]


class BlueskyChannel(Channel):
    PDS = "https://bsky.social"

    def _handle(self) -> str:
        return (os.environ.get("BSKY_HANDLE") or "").strip().lstrip("@")

    def configured(self) -> bool:
        return bool(self._handle() and os.environ.get("BSKY_APP_PASSWORD"))

    def publish(self, post: Post) -> str:
        handle, app_pw = self._handle(), os.environ["BSKY_APP_PASSWORD"]
        sess = _http_json(f"{self.PDS}/xrpc/com.atproto.server.createSession",
                          payload={"identifier": handle, "password": app_pw})
        auth = {"Authorization": f"Bearer {sess['accessJwt']}"}
        did = sess["did"]

        text = post.render("bluesky")
        record = {
            "$type": "app.bsky.feed.post",
            "text": text,
            "langs": ["en"],
            "createdAt": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        }
        facets = link_facets(text, post.link)
        if facets:
            record["facets"] = facets
        if post.image and post.image.exists():
            blob = _http_json(f"{self.PDS}/xrpc/com.atproto.repo.uploadBlob",
                              raw=post.image.read_bytes(), content_type="image/png",
                              headers=auth)["blob"]
            record["embed"] = {
                "$type": "app.bsky.embed.images",
                "images": [{"alt": post.image_alt or post.title, "image": blob}],
            }
        resp = _http_json(f"{self.PDS}/xrpc/com.atproto.repo.createRecord",
                          payload={"repo": did, "collection": "app.bsky.feed.post", "record": record},
                          headers=auth)
        rkey = resp.get("uri", "").rsplit("/", 1)[-1]
        return f"https://bsky.app/profile/{handle}/post/{rkey}" if rkey else resp.get("uri", "posted")


class LinkedInChannel(Channel):
    def configured(self) -> bool:
        return bool(os.environ.get("LINKEDIN_ORG_ID") and os.environ.get("LINKEDIN_ACCESS_TOKEN"))

    def publish(self, post: Post) -> str:
        raise SystemExit(
            "LinkedInChannel.publish is a phase-3 stub. Wire the Posts API "
            "(register image upload → create post) once the LinkedIn app + "
            "org token exist. See docs/social-publishing.md."
        )


class LinkedInChannel(Channel):
    def configured(self) -> bool:
        return bool(os.environ.get("LINKEDIN_ORG_ID") and os.environ.get("LINKEDIN_ACCESS_TOKEN"))

    def publish(self, post: Post) -> str:
        raise SystemExit(
            "LinkedInChannel.publish is a phase-3 stub. Wire the Posts API "
            "(register image upload → create post) once the LinkedIn app + "
            "org token exist. See docs/social-publishing.md."
        )


CHANNELS = {"bluesky": BlueskyChannel, "linkedin": LinkedInChannel}


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Compose/publish NetSec social posts (#1072).")
    ap.add_argument("--dry-run", action="store_true", help="print posts; publish nothing (default)")
    ap.add_argument("--live", action="store_true", help="actually publish (phase 2+; needs secrets)")
    ap.add_argument("--kind", choices=["news", "spotlight", "all"], default="all")
    ap.add_argument("--channel", choices=["bluesky", "linkedin", "all"], default="all")
    args = ap.parse_args()

    kinds = {"news", "spotlight"} if args.kind == "all" else {args.kind}
    ledger = load_ledger()
    posts = pending(kinds, ledger)

    if not posts:
        print("Nothing pending.")
        return 0

    live = args.live and not args.dry_run
    if not live:
        print(f"DRY RUN — {len(posts)} post(s) pending:\n")
        ch = DryRunChannel("dry-run")
        for p in posts:
            print(f"• [{p.kind}] {p.title}  (key: {p.key})")
            ch.publish(p)
        print("Nothing was published. Re-run with --live (phase 2+) once secrets are set.")
        return 0

    # Live path (phase 2+). Fail safe: only post through configured channels.
    wanted = list(CHANNELS) if args.channel == "all" else [args.channel]
    active = [CHANNELS[name](name) for name in wanted]
    active = [c for c in active if c.configured()]
    if not active:
        print("No channel is configured (missing secrets); nothing posted.", file=sys.stderr)
        return 1
    for p in posts:
        for c in active:
            url = c.publish(p)
            print(f"posted [{p.kind}] to {c.name}: {url}")
        ledger.setdefault("posted", []).append(p.key)
    save_ledger(ledger)
    return 0


if __name__ == "__main__":
    sys.exit(main())
