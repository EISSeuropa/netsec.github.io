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
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEWS_XML = ROOT / "news.xml"
NEWS_JSON = ROOT / "data" / "news.json"
SPOTLIGHT = ROOT / "data" / "spotlight.json"
BIOS = ROOT / "data" / "bios.json"
LEDGER = ROOT / "data" / "social-posted.json"
THREADS_DIR = ROOT / "data" / "social-threads"
LINKEDIN_VERSION_FILE = ROOT / "data" / "linkedin-api-version.json"
SITE = "https://netsec-cost.eu"
SITE_OG = ROOT / "assets" / "images" / "og-image.png"

# Bluesky posts are capped at 300 graphemes; we trim to a safe budget.
BLUESKY_LIMIT = 300
HASHTAGS = "#EuropeanSecurity #COSTAction"

# Last-resort LinkedIn version if the pin file is unreadable. Kept in sync
# with data/linkedin-api-version.json by hand only if that file is ever
# removed; the file is the real source (see LinkedInChannel.VERSION).
_LINKEDIN_VERSION_FALLBACK = "202607"


def _pinned_api_version() -> str:
    """Read the LinkedIn API version pin from its data file.

    Falls back to a literal only when the file is missing or malformed, so a
    posting run never dies on a bad pin file. The workflow keeps the file
    current; see .github/workflows/linkedin-version-check.yml."""
    try:
        v = str(json.loads(LINKEDIN_VERSION_FILE.read_text(encoding="utf-8"))["version"]).strip()
        return v if re.fullmatch(r"\d{6}", v) else _LINKEDIN_VERSION_FALLBACK
    except (OSError, ValueError, KeyError, TypeError):
        return _LINKEDIN_VERSION_FALLBACK


def _gha_warning(msg: str) -> None:
    """Emit a GitHub Actions warning annotation, so a best-effort channel
    failure surfaces on the run summary instead of hiding in the log. No-op
    off CI (the plain-text failure line is printed separately either way)."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::warning title=Social post::{msg}")


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
    # Optional per-member social handles (spotlight only). `bsky_handle` is
    # woven into the Bluesky text as an @-mention (resolved to a facet at
    # publish time); `profile_url` is the member's own LinkedIn URL, posted
    # as a first comment rather than in the body (LinkedIn downranks posts
    # with outbound links in the body, and person-mentions aren't reachable
    # from a public vanity URL). See read_spotlight.
    bsky_handle: str | None = None
    profile_url: str | None = None

    def _bsky_mention(self) -> str:
        return f"\n\nOn Bluesky: @{self.bsky_handle}" if self.bsky_handle else ""

    def render(self, channel: str) -> str:
        """Channel-appropriate text. Bluesky is trimmed to its limit; the
        link is always kept whole (it is what the post is for)."""
        head = f"📣 {self.title}" if self.kind == "news" else f"⭐ {self.title}"
        tail = f"\n\n{self.link}"
        if channel == "bluesky":
            mention = self._bsky_mention()
            budget = BLUESKY_LIMIT - len(head) - len(mention) - len(tail) - 2
            summary = _truncate(self.summary, max(0, budget))
            body = f"{head}\n\n{summary}{mention}{tail}" if summary else f"{head}{mention}{tail}"
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


def news_directives() -> dict:
    """{news item id: directive} from data/news.json. The optional per-item
    `social` field controls the auto single-post: "skip" (don't post this item)
    or "thread:<slug>" (announced as a curated thread, so the auto post stands
    down). Absent / "auto" means the item is eligible."""
    if not NEWS_JSON.exists():
        return {}
    try:
        data = json.loads(NEWS_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out = {}
    for it in data.get("items", []):
        d = (it.get("social") or "").strip()
        if it.get("id") and d:
            out[it["id"]] = d
    return out


def read_news_feed() -> list[Post]:
    """Parse news.xml into posts (stdlib regex; the feed is our own, small,
    and well-formed). One post per <item>, keyed on the item id (the <guid>),
    so two items linking the same page do not collide on the dedup key. Items
    whose news.json `social` directive is "skip" or "thread:*" are dropped."""
    if not NEWS_XML.exists():
        return []
    xml = NEWS_XML.read_text(encoding="utf-8")
    directives = news_directives()
    posts = []
    for block in re.findall(r"<item>(.*?)</item>", xml, re.S):
        def grab(tag, attrs=False):
            pat = rf"<{tag}\b[^>]*>(.*?)</{tag}>" if attrs else rf"<{tag}>(.*?)</{tag}>"
            m = re.search(pat, block, re.S)
            return m.group(1).strip() if m else ""
        title = html.unescape(_strip_tags(grab("title")))
        link = html.unescape(_strip_tags(grab("link")))
        # <guid isPermaLink="false">id</guid> — read the id, fall back to link.
        guid = html.unescape(_strip_tags(grab("guid", attrs=True))) or link
        desc = grab("description")
        desc = re.sub(r"^<!\[CDATA\[|\]\]>$", "", desc).strip()
        summary = html.unescape(_strip_tags(desc))
        if not (title and link):
            continue
        directive = directives.get(guid, "auto")
        if directive == "skip" or directive.startswith("thread:"):
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


# Small connector words kept lowercase mid-theme (British style, no Oxford comma).
_TITLE_SMALL = {"a", "an", "and", "the", "of", "for", "in", "on", "to", "with", "vs"}


def _join_and(items: list[str]) -> str:
    """British-style list join: "a", "a and b", "a, b and c" (no Oxford comma)."""
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def titlecase_theme(s: str) -> str:
    """Title-case a research keyword while preserving acronyms (EU, NATO) and any
    token that already carries an internal capital (IoT). "Black sea security" ->
    "Black Sea Security"; "EU foreign policy" -> "EU Foreign Policy"."""
    out = []
    for i, w in enumerate(s.split()):
        if w.isupper() or any(c.isupper() for c in w[1:]):
            out.append(w)                       # acronym / already-cased token
            continue
        lw = w.lower()
        if i != 0 and lw in _TITLE_SMALL:
            out.append(lw)
        else:
            out.append(lw[:1].upper() + lw[1:])
    return " ".join(out)


def _wg_phrase(m: dict) -> str:
    """A short Working-Group clause for the spotlight, preferring the strongest
    role (lead > co-lead > member), mirroring the OG card's WG fields."""
    valid = {"1", "2", "3", "4"}
    lead = sorted({str(x) for x in (m.get("wg_leadership") or {}).get("lead") or []} & valid)
    colead = sorted({str(x) for x in (m.get("wg_leadership") or {}).get("co_lead") or []} & valid)
    member = sorted({str(x) for x in (m.get("wgs") or [])} & valid)
    if lead:
        return "leading " + _join_and([f"WG{n}" for n in lead])
    if colead:
        return "co-leading " + _join_and([f"WG{n}" for n in colead])
    if member:
        return "in " + _join_and([f"WG{n}" for n in member])
    return ""


def _status_sentence(m: dict) -> str:
    """One sentence from the member's WG, mentorship and STSM-hosting status, or
    "" when none apply. Built from the same fields as the per-member OG card."""
    phrases = []
    wg = _wg_phrase(m)
    if wg:
        phrases.append(wg)
    tags = m.get("mentorship") or []
    if "mentor" in tags:
        phrases.append("offering mentorship")
    if "mentee" in tags:
        phrases.append("looking for a mentor")
    stsm = m.get("stsm_hosting")
    if stsm == "yes":
        phrases.append("willing to host Short Term Scientific Missions")
    elif stsm == "ask":
        phrases.append("open to hosting Short Term Scientific Missions")
    sent = _join_and(phrases)
    return (sent[:1].upper() + sent[1:] + ".") if sent else ""


def bluesky_handle(url: str | None) -> str | None:
    """The handle from a stored Bluesky profile URL (…/profile/<handle>), or
    None. Members submit a full URL; the tail is a resolvable Bluesky handle
    (e.g. `apb-ldn.org`, `foo.bsky.social`), which is what an @-mention needs.
    A bare handle (no URL) is accepted too."""
    s = (url or "").strip()
    if not s:
        return None
    m = re.search(r"bsky\.app/profile/([^/?#\s]+)", s)
    if m:
        return m.group(1)
    # Tolerate a bare handle typed without the profile URL.
    return s.lstrip("@") if "." in s and "/" not in s else None


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
    pos = (m.get("position") or "").strip()
    aff = (m.get("affiliation") or "").strip()
    role = f"{pos} at {aff}" if pos and aff else (pos or aff)
    themes = [titlecase_theme(t) for t in (m.get("canonical_keywords") or [])][:3]
    intro = f"Meet {m.get('name', slug)} in the NetSec Directory"
    lead = f"{intro}, {role}." if role else f"{intro}."
    status = _status_sentence(m)
    title = "NetSec Directory Spotlight"
    link = f"{SITE}/people/{slug}.html"

    # Tag the member on the platforms where that's reachable. Bluesky: the
    # submitted profile URL yields a handle we @-mention (resolved to a facet
    # at publish time). LinkedIn: the vanity URL can't be turned into a
    # notifying person-mention, so it rides along as a first comment instead
    # (see LinkedInChannel._do_publish).
    bsky = bluesky_handle(m.get("bluesky"))
    li_url = (m.get("linkedin") or "").strip() or None

    # Assemble the summary so the Bluesky render never has to hard-truncate
    # mid-word: the post text is lead + "Working on …" + status, and when it
    # would overrun the 300 limit we drop whole pieces (a theme at a time,
    # keeping the mentorship/STSM status line) so it always ends on a full
    # sentence. The budget mirrors Post.render's head/tail/mention arithmetic,
    # reserving the same @-mention length render() will append.
    mention_len = len(f"\n\nOn Bluesky: @{bsky}") if bsky else 0
    budget = BLUESKY_LIMIT - len(f"⭐ {title}") - len(f"\n\n{link}") - 2 - mention_len

    def _summary(n_themes: int, with_status: bool) -> str:
        parts = [lead]
        if themes and n_themes:
            parts.append("Working on " + ", ".join(themes[:n_themes]) + ".")
        if with_status and status:
            parts.append(status)
        return " ".join(parts)

    summary = _summary(len(themes), bool(status))
    for n, ws in [(3, True), (2, True), (1, True), (0, True), (0, False)]:
        cand = _summary(min(n, len(themes)), ws)
        if len(cand) <= budget:
            summary = cand
            break

    card = ROOT / "assets" / "og" / "people" / f"{slug}.png"
    week = _iso_week(sp.get("featuredSince", ""))
    return Post(
        kind="spotlight",
        key=f"spotlight::{slug}::{week}",
        title=title,
        summary=summary,
        link=link,
        image=card if card.exists() else (SITE_OG if SITE_OG.exists() else None),
        image_alt=f"Profile card for {m.get('name', slug)} in the NetSec Directory",
        bsky_handle=bsky,
        profile_url=li_url,
    )


# --------------------------------------------------------------------------
# Curated threads (hand-written multi-post announcements)
# --------------------------------------------------------------------------
@dataclass
class ThreadPost:
    text: str
    image: Path | None = None
    image_alt: str = ""
    card: dict | None = None  # external link card: {uri, title, description, thumb: Path}


@dataclass
class Thread:
    key: str
    channel: str
    posts: list
    langs: list = field(default_factory=lambda: ["en"])


def read_thread(path: Path) -> Thread:
    """Load a curated thread spec (see data/social-threads/*.json)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    posts = []
    for p in data.get("posts", []):
        img = p.get("image")
        card = p.get("card")
        if card:
            card = dict(card)
            thumb = card.get("thumb")
            card["thumb"] = (ROOT / thumb) if thumb else None
        posts.append(ThreadPost(
            text=p["text"],
            image=(ROOT / img) if img else None,
            image_alt=p.get("imageAlt", ""),
            card=card,
        ))
    if not posts:
        raise SystemExit(f"thread {path} has no posts")
    return Thread(key=data["key"], channel=data.get("channel", "bluesky"),
                  posts=posts, langs=data.get("langs", ["en"]))


def graphemes(text: str) -> int:
    """Approximate grapheme count for the Bluesky 300 limit. A variation
    selector or combining mark modifies the prior glyph (no count); a
    zero-width joiner folds the *next* glyph into the current one."""
    n = 0
    join_next = False
    for ch in text:
        if ch == "‍":  # ZWJ — the next glyph joins this one
            join_next = True
            continue
        if ch == "️" or unicodedata.combining(ch):  # VS16 / combining mark
            continue
        if join_next:
            join_next = False
            continue
        n += 1
    return n


MENTION_RE = re.compile(r"@[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?)+")
URL_RE = re.compile(r"https?://[^\s\]\)]+")


def _byte_span(text: str, start: int, end: int) -> tuple[int, int]:
    """UTF-8 byte offsets for a [start:end) character slice of `text`."""
    return len(text[:start].encode("utf-8")), len(text[:end].encode("utf-8"))


def find_mentions(text: str) -> list[tuple[str, int, int]]:
    """(handle, byteStart, byteEnd) for each @handle.tld in the text. The
    span covers the leading @, per the Bluesky richtext convention."""
    out = []
    for m in MENTION_RE.finditer(text):
        handle = m.group(0)[1:]  # drop the leading @
        bs, be = _byte_span(text, m.start(), m.end())
        out.append((handle, bs, be))
    return out


def find_links(text: str) -> list[tuple[str, int, int]]:
    out = []
    for m in URL_RE.finditer(text):
        url = m.group(0).rstrip(").,;")
        bs, be = _byte_span(text, m.start(), m.start() + len(url))
        out.append((url, bs, be))
    return out


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
            if ch == "bluesky" and post.bsky_handle:
                print(f"    [mention → resolves live: @{post.bsky_handle}]")
            if ch == "linkedin" and post.profile_url:
                print(f"    [+ first comment: {post.profile_url}]")
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


def _img_mime(path: Path) -> str:
    return "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"


def image_size(path: Path) -> tuple[int, int] | None:
    """(width, height) of a PNG or JPEG, stdlib-only. None if unreadable.
    Bluesky letterboxes an image embed unless it carries the aspect ratio, so
    the embed sends this so the card renders edge-to-edge at the true ratio."""
    data = path.read_bytes()
    if data[:8] == b"\x89PNG\r\n\x1a\n":  # IHDR width/height at bytes 16..24
        import struct
        w, h = struct.unpack(">II", data[16:24])
        return int(w), int(h)
    if data[:2] == b"\xff\xd8":  # JPEG: walk segments to a Start-Of-Frame marker
        import struct
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return int(w), int(h)
            i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    return None


class BlueskyChannel(Channel):
    PDS = "https://bsky.social"

    def _handle(self) -> str:
        return (os.environ.get("BSKY_HANDLE") or "").strip().lstrip("@")

    def configured(self) -> bool:
        return bool(self._handle() and os.environ.get("BSKY_APP_PASSWORD"))

    def _login(self) -> tuple[dict, str]:
        sess = _http_json(f"{self.PDS}/xrpc/com.atproto.server.createSession",
                          payload={"identifier": self._handle(), "password": os.environ["BSKY_APP_PASSWORD"]})
        return {"Authorization": f"Bearer {sess['accessJwt']}"}, sess["did"]

    def _resolve_handle(self, handle: str) -> str | None:
        try:
            return _http_json(
                f"{self.PDS}/xrpc/com.atproto.identity.resolveHandle?handle={handle}").get("did")
        except SystemExit:
            return None  # an unknown handle drops to plain text, never blocks the post

    def _upload(self, auth: dict, image: Path) -> dict:
        return _http_json(f"{self.PDS}/xrpc/com.atproto.repo.uploadBlob",
                          raw=image.read_bytes(), content_type=_img_mime(image),
                          headers=auth)["blob"]

    def _image_embed(self, auth: dict, image: Path, alt: str) -> dict:
        img = {"alt": alt, "image": self._upload(auth, image)}
        size = image_size(image)
        if size:  # declare the ratio so the client renders it edge-to-edge
            img["aspectRatio"] = {"width": size[0], "height": size[1]}
        return {"$type": "app.bsky.embed.images", "images": [img]}

    def _external_embed(self, auth: dict, card: dict) -> dict:
        """A clickable link-preview card (app.bsky.embed.external)."""
        external = {
            "uri": card["uri"],
            "title": card.get("title", ""),
            "description": card.get("description", ""),
        }
        thumb = card.get("thumb")
        if thumb and Path(thumb).exists():
            external["thumb"] = self._upload(auth, Path(thumb))
        return {"$type": "app.bsky.embed.external", "external": external}

    def _rich_facets(self, text: str) -> list:
        """Link + mention facets for arbitrary text (resolving each handle)."""
        facets = []
        for url, bs, be in find_links(text):
            facets.append({"index": {"byteStart": bs, "byteEnd": be},
                           "features": [{"$type": "app.bsky.richtext.facet#link", "uri": url}]})
        for handle, bs, be in find_mentions(text):
            did = self._resolve_handle(handle)
            if did:
                facets.append({"index": {"byteStart": bs, "byteEnd": be},
                               "features": [{"$type": "app.bsky.richtext.facet#mention", "did": did}]})
        return facets

    def publish(self, post: Post) -> str:
        auth, did = self._login()
        handle = self._handle()
        text = post.render("bluesky")
        record = {
            "$type": "app.bsky.feed.post",
            "text": text,
            "langs": ["en"],
            "createdAt": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        }
        # _rich_facets covers the link (find_links catches post.link in the
        # tail) plus any @-mention the spotlight wove in; news posts carry no
        # mention, so this stays equivalent to the old link-only path there.
        facets = self._rich_facets(text)
        if facets:
            record["facets"] = facets
        if post.image and post.image.exists():
            record["embed"] = self._image_embed(auth, post.image, post.image_alt or post.title)
        resp = _http_json(f"{self.PDS}/xrpc/com.atproto.repo.createRecord",
                          payload={"repo": did, "collection": "app.bsky.feed.post", "record": record},
                          headers=auth)
        rkey = resp.get("uri", "").rsplit("/", 1)[-1]
        return f"https://bsky.app/profile/{handle}/post/{rkey}" if rkey else resp.get("uri", "posted")

    def publish_thread(self, thread: Thread) -> list[str]:
        """Post each ThreadPost in order, each replying to the previous. Image
        (if any) rides its own post. Returns the post URLs."""
        auth, did = self._login()
        handle = self._handle()
        root = parent = None
        urls = []
        for tp in thread.posts:
            record = {
                "$type": "app.bsky.feed.post",
                "text": tp.text,
                "langs": thread.langs,
                "createdAt": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            }
            facets = self._rich_facets(tp.text)
            if facets:
                record["facets"] = facets
            if tp.card:
                record["embed"] = self._external_embed(auth, tp.card)
            elif tp.image and tp.image.exists():
                record["embed"] = self._image_embed(auth, tp.image, tp.image_alt)
            if parent:
                record["reply"] = {"root": root, "parent": parent}
            resp = _http_json(f"{self.PDS}/xrpc/com.atproto.repo.createRecord",
                              payload={"repo": did, "collection": "app.bsky.feed.post", "record": record},
                              headers=auth)
            ref = {"uri": resp["uri"], "cid": resp["cid"]}
            if root is None:
                root = ref
            parent = ref
            rkey = resp["uri"].rsplit("/", 1)[-1]
            urls.append(f"https://bsky.app/profile/{handle}/post/{rkey}")
        return urls


class _Unauthorized(Exception):
    """Raised by _li_request on a 401 so the caller can refresh + retry once."""


def _li_request(url: str, method: str = "GET", headers: dict | None = None,
                json_body: dict | None = None, data: bytes | None = None,
                content_type: str | None = None) -> tuple[int, dict, object]:
    """LinkedIn HTTP via stdlib urllib. Returns (status, lower-cased headers,
    parsed JSON or raw text). Raises _Unauthorized on 401 (caller refreshes the
    token), SystemExit on any other HTTP error (with the API's error body)."""
    import urllib.error
    import urllib.parse  # noqa: F401  (used by callers for form-encoding)
    import urllib.request

    hdrs = dict(headers or {})
    payload = data
    if json_body is not None:
        payload = json.dumps(json_body).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    elif content_type:
        hdrs.setdefault("Content-Type", content_type)
    req = urllib.request.Request(url, data=payload, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", "replace")
            rh = {k.lower(): v for k, v in resp.headers.items()}
            body = json.loads(raw) if raw.strip()[:1] in ("{", "[") else raw
            return resp.status, rh, body
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        if e.code == 401:
            raise _Unauthorized(detail) from e
        raise SystemExit(f"LinkedIn HTTP {e.code} from {url}: {detail}") from e


class LinkedInChannel(Channel):
    """Post to a LinkedIn Company Page via the Community-Management Posts API
    (POST /rest/posts), uploading the OG image through the Images API first.
    Image upload → create post is the same shape Bluesky uses. The access token
    expires ~60 days; on a 401 we refresh it once with the refresh token + app
    credentials and retry. See docs/social-publishing.md."""

    API = "https://api.linkedin.com"
    OAUTH = "https://www.linkedin.com/oauth/v2/accessToken"
    # LinkedIn versions the API monthly (YYYYMM) and sunsets a version after
    # ~12 months; a sunset version returns HTTP 426 and the post fails. The
    # pin lives in data/linkedin-api-version.json, kept current by the
    # linkedin-version-check workflow (auto-PR before sunset). LINKEDIN_API_VERSION
    # overrides it at runtime; the literal is a last-resort fallback if the
    # file is missing or unreadable, never the routine source of the value.
    VERSION = os.environ.get("LINKEDIN_API_VERSION") or _pinned_api_version()

    def _org(self) -> str:
        return (os.environ.get("LINKEDIN_ORG_ID") or "").strip()

    def _token(self) -> str:
        return (os.environ.get("LINKEDIN_ACCESS_TOKEN") or "").strip()

    def configured(self) -> bool:
        return bool(self._org() and self._token())

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token()}",
            "LinkedIn-Version": self.VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def _refresh(self) -> bool:
        """Swap the refresh token for a fresh access token, updating the process
        env so the retry uses it. Returns False when the refresh token or app
        credentials aren't set (so the caller can fail with a clear message)."""
        import urllib.parse
        rt = os.environ.get("LINKEDIN_REFRESH_TOKEN")
        cid = os.environ.get("LINKEDIN_CLIENT_ID")
        cs = os.environ.get("LINKEDIN_CLIENT_SECRET")
        if not (rt and cid and cs):
            return False
        body = urllib.parse.urlencode({
            "grant_type": "refresh_token", "refresh_token": rt,
            "client_id": cid, "client_secret": cs,
        }).encode("utf-8")
        _, _, data = _li_request(self.OAUTH, method="POST", data=body,
                                 content_type="application/x-www-form-urlencoded")
        tok = (data or {}).get("access_token") if isinstance(data, dict) else None
        if tok:
            os.environ["LINKEDIN_ACCESS_TOKEN"] = tok
            return True
        return False

    def _upload_image(self, image: Path, alt: str) -> str:
        """initializeUpload (owner = the org) → PUT the bytes to the signed
        uploadUrl → return the urn:li:image URN to attach to the post."""
        owner = f"urn:li:organization:{self._org()}"
        _, _, init = _li_request(
            f"{self.API}/rest/images?action=initializeUpload", method="POST",
            headers=self._headers(), json_body={"initializeUploadRequest": {"owner": owner}})
        value = (init or {}).get("value", {}) if isinstance(init, dict) else {}
        upload_url, urn = value.get("uploadUrl"), value.get("image")
        if not (upload_url and urn):
            raise SystemExit(f"LinkedIn initializeUpload returned no uploadUrl/image: {init}")
        _li_request(upload_url, method="PUT", data=image.read_bytes(),
                    content_type=_img_mime(image),
                    headers={"Authorization": f"Bearer {self._token()}"})
        return urn

    def _comment(self, post_urn: str, text: str) -> None:
        """Post a first comment on a just-published share, authored by the org.
        Used to carry the spotlighted member's own LinkedIn profile link out of
        the post body (LinkedIn suppresses reach on body links; a comment link
        sidesteps that). The URN is path-encoded per the socialActions API."""
        from urllib.parse import quote
        body = {
            "actor": f"urn:li:organization:{self._org()}",
            "message": {"text": text},
        }
        _li_request(f"{self.API}/rest/socialActions/{quote(post_urn, safe='')}/comments",
                    method="POST", headers=self._headers(), json_body=body)

    def _do_publish(self, post: Post) -> str:
        body = {
            "author": f"urn:li:organization:{self._org()}",
            "commentary": post.render("linkedin"),
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
        if post.image and post.image.exists():
            urn = self._upload_image(post.image, post.image_alt or post.title)
            body["content"] = {"media": {"altText": post.image_alt or post.title, "id": urn}}
        _, headers, _ = _li_request(f"{self.API}/rest/posts", method="POST",
                                    headers=self._headers(), json_body=body)
        pid = headers.get("x-restli-id", "")
        # Best-effort first comment carrying the member's LinkedIn profile link.
        # A broad catch keeps a comment failure from bubbling to publish()'s
        # 401 refresh-and-retry, which would re-post the whole share.
        # ponytail: comment is a nice-to-have; the share already stands.
        if pid and post.profile_url:
            try:
                self._comment(pid, post.profile_url)
            except (Exception, SystemExit) as e:  # noqa: BLE001
                # _li_request signals HTTP errors as SystemExit and 401 as
                # _Unauthorized; catch both so neither aborts the run nor
                # reaches publish()'s refresh-and-retry (which would re-post).
                print(f"  ! LinkedIn profile-link comment failed, post stands: {e}",
                      file=sys.stderr)
        return f"https://www.linkedin.com/feed/update/{pid}/" if pid else "posted"

    def publish(self, post: Post) -> str:
        try:
            return self._do_publish(post)
        except _Unauthorized:
            if self._refresh():
                return self._do_publish(post)  # retry once with the fresh token
            raise SystemExit(
                "LinkedIn returned 401 and no usable refresh token. Set "
                "LINKEDIN_REFRESH_TOKEN, LINKEDIN_CLIENT_ID and "
                "LINKEDIN_CLIENT_SECRET, or regenerate the access token."
            )


CHANNELS = {"bluesky": BlueskyChannel, "linkedin": LinkedInChannel}


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def run_thread(path: Path, live: bool, ledger: dict) -> int:
    """Compose (dry-run) or publish a curated Bluesky thread."""
    thread = read_thread(path)
    over = [i + 1 for i, tp in enumerate(thread.posts) if graphemes(tp.text) > BLUESKY_LIMIT]

    if not live:
        print(f"DRY RUN — thread {thread.key} ({len(thread.posts)} posts, channel {thread.channel}):\n")
        for i, tp in enumerate(thread.posts, 1):
            g = graphemes(tp.text)
            flag = "OK" if g <= BLUESKY_LIMIT else "OVER LIMIT"
            print(f"── post {i}/{len(thread.posts)}  [{g}/{BLUESKY_LIMIT} graphemes · {flag}] ──")
            for line in tp.text.splitlines():
                print(f"    {line}")
            if tp.card:
                thumb = tp.card.get("thumb")
                tmiss = "" if (thumb and Path(thumb).exists()) else "  (thumb MISSING!)"
                print(f"    [link card → {tp.card['uri']}{tmiss}]")
                print(f"      title: {tp.card.get('title', '')}")
                print(f"      desc:  {tp.card.get('description', '')}")
                if thumb:
                    print(f"      thumb: {Path(thumb).relative_to(ROOT)}")
            if tp.image:
                ok = "" if tp.image.exists() else "  (MISSING!)"
                print(f"    [image: {tp.image.relative_to(ROOT)}{ok} | alt: {tp.image_alt}]")
            mentions = [h for h, _, _ in find_mentions(tp.text)]
            links = [u for u, _, _ in find_links(tp.text)]
            if mentions:
                print(f"    [mentions → resolved live: {', '.join('@' + h for h in mentions)}]")
            if links:
                print(f"    [links: {', '.join(links)}]")
            print()
        already = thread.key in set(ledger.get("posted", []))
        print(f"Ledger: {'ALREADY POSTED — a live run would skip it' if already else 'not yet posted'}.")
        if over:
            print(f"⚠️  Post(s) {', '.join(map(str, over))} exceed {BLUESKY_LIMIT} graphemes; trim before going live.")
        print("Nothing was published. Re-run with --live behind the approval gate to post.")
        return 0

    # Live path — gated by the `social` environment in CI.
    if over:
        print(f"Refusing to post: post(s) {', '.join(map(str, over))} exceed {BLUESKY_LIMIT} graphemes.", file=sys.stderr)
        return 1
    if thread.key in set(ledger.get("posted", [])):
        print(f"Thread {thread.key} already posted; nothing to do.")
        return 0
    ch = BlueskyChannel("bluesky")
    if not ch.configured():
        print("Bluesky is not configured (missing secrets); nothing posted.", file=sys.stderr)
        return 1
    urls = ch.publish_thread(thread)
    for i, u in enumerate(urls, 1):
        print(f"posted thread {thread.key} [{i}/{len(urls)}]: {u}")
    ledger.setdefault("posted", []).append(thread.key)
    save_ledger(ledger)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Compose/publish NetSec social posts (#1072).")
    ap.add_argument("--dry-run", action="store_true", help="print posts; publish nothing (default)")
    ap.add_argument("--live", action="store_true", help="actually publish (phase 2+; needs secrets)")
    ap.add_argument("--kind", choices=["news", "spotlight", "all"], default="all")
    ap.add_argument("--channel", choices=["bluesky", "linkedin", "all"], default="all")
    ap.add_argument("--thread", metavar="FILE", help="post a curated thread spec (data/social-threads/*.json)")
    ap.add_argument("--count", action="store_true",
                    help="print only the number of items that would post (for CI gating); publish nothing")
    ap.add_argument("--best-effort", action="store_true",
                    help="don't abort if one channel fails to publish (for the ungated spotlight)")
    args = ap.parse_args()

    ledger = load_ledger()
    posted = set(ledger.get("posted", []))

    if args.count:
        if args.thread:
            thread = read_thread(Path(args.thread))
            over = any(graphemes(tp.text) > BLUESKY_LIMIT for tp in thread.posts)
            print(0 if (thread.key in posted or over) else 1)
        else:
            kinds = {"news", "spotlight"} if args.kind == "all" else {args.kind}
            print(len(pending(kinds, ledger)))
        return 0

    if args.thread:
        return run_thread(Path(args.thread), live=args.live and not args.dry_run, ledger=ledger)

    kinds = {"news", "spotlight"} if args.kind == "all" else {args.kind}
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
        posted_any = False
        for c in active:
            try:
                url = c.publish(p)
                print(f"posted [{p.kind}] to {c.name}: {url}")
                posted_any = True
            except SystemExit as e:
                # --best-effort (the ungated weekly spotlight) must not let one
                # channel's failure — an expired LinkedIn token, an API change —
                # break the others or the rotation. The gated path re-raises so
                # a reviewer sees the failure and re-runs.
                if not args.best_effort:
                    raise
                print(f"  ! {c.name} publish failed, skipping (best-effort): {e}", file=sys.stderr)
                _gha_warning(f"{c.name} publish failed for [{p.kind}] {p.title}: {e}")
        # Record the dedup key once any channel posted, so a partial failure
        # doesn't double-post the channel that succeeded on the next run.
        if posted_any:
            ledger.setdefault("posted", []).append(p.key)
    save_ledger(ledger)
    return 0


if __name__ == "__main__":
    sys.exit(main())
