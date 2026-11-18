#!/usr/bin/env python3
"""Turn a News item issue into an entry in data/news.json.

Called by .github/workflows/news-publish.yml when a publisher applies the
`news` label. Ported from the EISS repository's scripts/news-from-issue.py
(EISSeuropa/EISSeuropa.github.io#2058), adapted to NetSec's trilingual
schema (docs/news-publishing.md).

The issue is the News item form (.github/ISSUE_TEMPLATE/news.yml), which is
English only. The script writes the English text and asks the Claude API for
the French and German title, summary and body (translate()). Dates, the
link label and the type are set without translation.

Form field         news.json
  Site             "site": "joint" for a joint item, and with LinkedIn
                   ticked it needs EISS as Collaborator page. EISS, an option
                   on issues filed before 18 November 2026, stops the run.
  Post on          LinkedIn and Bluesky checkboxes, at least one ticked
                   unless Options says not to post. One ticked: "networks"
                   lists it, and the other network's box is ignored. Issues
                   filed before the boxes post on both.
  Headline         title.en, up to HEADLINE_MAX characters (blank: the issue
                   title minus a leading "news:", for issues filed before the
                   form required it)
  Website summary  summary.en, one line, up to SUMMARY_MAX characters
                   ("Summary" on issues filed before it was split)
  Body             body.en, up to BODY_MAX characters (blank: the summary)
  LinkedIn post    posts.linkedin, verbatim with its line breaks, up to
                   LINKEDIN_LIMIT characters with the link added
  Bluesky post     posts.bluesky, the same, up to BLUESKY_LIMIT characters
                   with the link and each tag written as its handle
                   (@Key tags come from data/social-accounts.json). A post
                   pasted from LinkedIn keeps its links as
                   [Name](https://www.linkedin.com/...): a page in the
                   accounts file becomes its @Key, any other link its plain
                   text (untangle_linkedin)
  Type             type (default announcement)
  Working Group    wg
  Link             cta, with the FR and DE pages when they exist
  Publication date pubDate at 12:00 Paris time, and displayDate
  On the home page until   homeUntil at 23:59 Paris time
  Collaborator page        "collaborator": "eiss", kept when LinkedIn is
                   ticked
  Image            a photo dragged into the field (an https address),
                   downloaded, shrunk to IMAGE_MAX_BYTES as a JPEG without
                   its camera data, and saved as assets/images/news/<id>.jpg.
                   Or a site image (assets/...). "image" is its path: the
                   picture of the social posts, before the event card
  Image description        "imageAlt", the photo's alt text. Required with
                   a photo, up to IMAGE_ALT_MAX characters
  Options          "social": "skip". "newsletter": true from the newsletter box,
                   off the form for now and still read for older issues

A headline or summary over its limit, an empty one, or Site set to EISS
stops the run. Those messages are written for the person who filed the form:
the workflow posts them on the issue. A message prefixed "news-from-issue:"
is a fault in the repository and gets the workflow's generic comment
(EISSeuropa/EISSeuropa.github.io#2191).

Environment: ISSUE_TITLE, ISSUE_BODY, TODAY (YYYY-MM-DD), and
ANTHROPIC_API_KEY for the translation. Without the key the item is written in
English only, and the script prints TRANSLATED=false so the workflow leaves the
PR for a person. With GITHUB_OUTPUT set it also writes translated=true|false,
id=<item id> and headline=<the English headline> there, so the workflow names
the issue and the PR after the headline.

Usage (local test):
    ISSUE_TITLE="news: x" ISSUE_BODY="$(cat body.md)" TODAY=2026-12-01 \\
        python3 scripts/news-from-issue.py
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
NEWS = ROOT / "data" / "news.json"

PARIS = ZoneInfo("Europe/Paris")
TYPES = ("announcement", "event", "publication", "call")
HEADLINE_MAX = 100
IMAGE_ALT_MAX = 300
IMAGE_DIR = "assets/images/news"
# Bluesky refuses an image over 1,000,000 bytes. LinkedIn takes more, so the
# smaller limit sets the size of the saved photo.
IMAGE_MAX_BYTES = 950_000
IMAGE_MAX_SIDE = 2000
DOWNLOAD_MAX_BYTES = 25_000_000
SUMMARY_MAX = 300
BODY_MAX = 2000
POST_BOXES = (("linkedin", "LinkedIn post", "linkedin post"), ("bluesky", "Bluesky post", "bluesky post"))
ID_MAX = 60
NO_RESPONSE = "_No response_"
FORM_HEADING_RE = re.compile(r"^###\s+(.+?)\s*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CHECKED_RE = re.compile(r"^\s*-\s*\[[xX]\]\s*(.+?)\s*$", re.M)
NETWORK_LABELS = {"linkedin": "LinkedIn", "bluesky": "Bluesky"}
LI_LINK_RE = re.compile(r"\[([^\]\n]+)\]\((https?://(?:[\w-]+\.)?linkedin\.com/[^)\s]*)\)", re.I)
LI_PAGE_RE = re.compile(r"(?:(?:company|school|showcase)/([^/?#)\s]+)|organization:(\d+))", re.I)

MODEL = "claude-opus-5-5"
LOCALES = ("fr", "de")

MONTHS = {
    "en": ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"],
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
           "août", "septembre", "octobre", "novembre", "décembre"],
    "de": ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
           "August", "September", "Oktober", "November", "Dezember"],
}
CTA_LABEL = {"en": "Read more →", "fr": "En savoir plus →", "de": "Mehr erfahren →"}

SYSTEM_PROMPT = (
    "You translate news items for the website of NetSec, COST Action CA24154, "
    "a European research network in security studies. Translate the English "
    "title, summary and body into French and German for the French and German "
    "pages of the site. Keep the meaning and the register of the English, which "
    "is plain and factual. Keep names of people, institutions, events, programmes "
    "and publications as they are written in English, unless an official French "
    "or German name exists. Write dates in the usual form for each language. "
    "Return plain text with no markdown, and add nothing that is not in the English."
)

TRANSLATION_SCHEMA = {
    "type": "object",
    "properties": {
        loc: {
            "type": "object",
            "properties": {k: {"type": "string"} for k in ("title", "summary", "body")},
            "required": ["title", "summary", "body"],
            "additionalProperties": False,
        }
        for loc in LOCALES
    },
    "required": list(LOCALES),
    "additionalProperties": False,
}


def clean_title(title: str) -> str:
    return re.sub(r"^\s*news\s*:\s*", "", (title or "").strip(), flags=re.IGNORECASE)


def form_sections(body: str) -> dict[str, str]:
    """{lower-cased heading: answer} when the body is an issue form, else {}.
    GitHub writes "_No response_" for a blank optional field, which reads here
    as an empty answer."""
    lines = (body or "").replace("\r\n", "\n").split("\n")
    first = next((ln for ln in lines if ln.strip()), "")
    if not FORM_HEADING_RE.match(first):
        return {}
    sections: dict[str, list[str]] = {}
    current = None
    for ln in lines:
        m = FORM_HEADING_RE.match(ln)
        if m:
            current = m.group(1).strip().lower()
            sections[current] = []
        elif current is not None:
            sections[current].append(ln)
    out = {}
    for key, val in sections.items():
        text = "\n".join(val).strip()
        out[key] = "" if text == NO_RESPONSE else text
    return out


def one_line(text: str) -> str:
    return " ".join((text or "").split())


_MODULES: dict = {}


def _module(name: str):
    """A sibling script loaded as a module (social-post.py for the post
    helpers, build-news-rss.py for the link a post ends with). Loaded once."""
    if name not in _MODULES:
        import importlib.util
        mod_name = name.replace("-", "_").removesuffix(".py")
        spec = importlib.util.spec_from_file_location(mod_name, Path(__file__).with_name(name))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = mod
        spec.loader.exec_module(mod)
        _MODULES[name] = mod
    return _MODULES[name]


def post_text(text: str) -> str:
    """A post as written, with its paragraphs: line ends trimmed, at most one
    blank line between paragraphs. The form shows the post boxes as code
    blocks (`render: text`), so GitHub does not notify a user for an @tag
    such as @EISS. The ``` lines around the text are dropped here."""
    text = (text or "").replace("\r\n", "\n").strip()
    m = re.fullmatch(r"```[\w-]*\n(.*?)\n?```", text, re.S)
    if m:
        text = m.group(1)
    lines = [ln.rstrip() for ln in text.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def linkedin_pages() -> dict[str, str]:
    """{page name or number in a LinkedIn address: @Key}, from the accounts
    file's linkedin_url and linkedin (the urn:li:organization number)."""
    sp = _module("social-post.py")
    try:
        accounts = json.loads(sp.ACCOUNTS_JSON.read_text(encoding="utf-8")).get("accounts") or {}
    except (OSError, json.JSONDecodeError):
        return {}
    pages = {}
    for key, acc in accounts.items():
        for ref in (acc.get("linkedin_url"), acc.get("linkedin")) if isinstance(acc, dict) else ():
            m = LI_PAGE_RE.search(ref or "")
            if m:
                pages[(m.group(1) or m.group(2)).lower()] = key
    return pages


def untangle_linkedin(text: str, tags: bool = True) -> str:
    """Text copied from LinkedIn writes each page, person and hashtag as a
    [Name](https://www.linkedin.com/...) link. A page in the accounts file
    becomes its @Key (when tags is true), and any other link its plain text."""
    pages = linkedin_pages() if tags else {}

    def sub(m: re.Match) -> str:
        page = LI_PAGE_RE.search(m.group(2))
        key = pages.get((page.group(1) or page.group(2)).lower()) if page else None
        return "@" + key if key else m.group(1)
    return LI_LINK_RE.sub(sub, text or "")


def check_post(network: str, label: str, text: str, item: dict) -> None:
    """Stops the run when a post box tags an unknown account or is over the
    network's limit once the link is added and the tags are written out."""
    sp = _module("social-post.py")
    accounts = sp.load_accounts()
    unknown = sp.unknown_tags(text, accounts)
    if unknown:
        known = ", ".join("@" + k for k in sorted(
            (json.loads(sp.ACCOUNTS_JSON.read_text(encoding="utf-8")).get("accounts") or {})))
        sys.exit(f"The {label} tags {', '.join(unknown)}, which is not in the list of accounts. "
                 f"Edit the issue and use {known}, or write the name without @.")
    link = _module("build-news-rss.py").item_link(item)
    shown, _ = sp.tagged(sp.with_link(text, link), network, accounts)
    limit = sp.LINKEDIN_LIMIT if network == "linkedin" else sp.BLUESKY_LIMIT
    if len(shown) > limit:
        extra = " with the link and the tags as Bluesky shows them" if network == "bluesky" else " with the link"
        sys.exit(f"The {label} is {len(shown)} characters long{extra}, and the limit is {limit}. "
                 f"Edit the issue and shorten the {label} by at least {len(shown) - limit} characters.")


def check_date(label: str, val: str) -> date | None:
    """The date in a date box, None when it is empty. Any other text stops
    the run: before, it was dropped without a word."""
    val = (val or "").strip()
    if not val:
        return None
    d = parse_date(val)
    if d is None:
        sys.exit(f"The {label} \"{val}\" is not a date the site can read. Edit the issue and write it "
                 "as year-month-day with dashes, for example 2026-12-01, or leave it empty.")
    return d


def check_length(field: str, text: str, limit: int) -> None:
    if len(text) > limit:
        sys.exit(f"The {field} is {len(text)} characters long, and the limit is {limit}. "
                 f"Edit the issue and shorten the {field} by at least {len(text) - limit} characters.")


def slugify(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug[:ID_MAX].rstrip("-") or "news"


def display_dates(d: date) -> dict[str, str]:
    day_fr = "1er" if d.day == 1 else str(d.day)
    return {
        "en": f"{d.day} {MONTHS['en'][d.month - 1]} {d.year}",
        "fr": f"{day_fr} {MONTHS['fr'][d.month - 1]} {d.year}",
        "de": f"{d.day}. {MONTHS['de'][d.month - 1]} {d.year}",
    }


def paris_iso(d: date, t: time) -> str:
    return datetime.combine(d, t, tzinfo=PARIS).isoformat()


def parse_date(val: str) -> date | None:
    val = (val or "").strip()
    if not DATE_RE.match(val):
        return None
    try:
        return date.fromisoformat(val)
    except ValueError:
        return None


def make_cta(link: str, root: Path = ROOT) -> dict | None:
    link = (link or "").strip()
    if link.startswith(("http://", "https://")):
        return {"href": link, "external": True, "i18n": dict(CTA_LABEL)}
    path = link.lstrip("/")
    if not path or " " in path or not re.match(r"^[\w./#-]+$", path):
        return None
    page, _, frag = path.partition("#")
    frag = f"#{frag}" if frag else ""
    href: str | dict = path
    if page.endswith(".html"):
        stem = page[: -len(".html")]
        variants = {loc: f"{stem}.{loc}.html" for loc in LOCALES}
        if all((root / v).exists() for v in variants.values()):
            href = {"en": f"{page}{frag}", **{loc: f"{v}{frag}" for loc, v in variants.items()}}
    return {"href": href, "external": False, "i18n": dict(CTA_LABEL)}


def image_source(text: str) -> str:
    """The photo in the Image field: an https address, or a site image path
    (assets/...). GitHub writes a dragged photo as <img ... src="..."> or
    ![name](...), and either is read. An empty field gives ""."""
    text = (text or "").strip()
    if not text:
        return ""
    for pattern in (r'src="(https://[^"\s]+)"', r"\]\((https://[^)\s]+)\)", r"(https://\S+)"):
        m = re.search(pattern, text)
        if m:
            return m.group(1)
    if re.fullmatch(r"/?assets/\S+", text):
        return text.lstrip("/")
    sys.exit("The Image field has no photo in it. Edit the issue and drag a photo into the Image "
             "field, then wait until the upload finishes. Or empty the field to post without a photo.")


def fetch(url: str) -> bytes:
    """The photo's bytes. Any failure is the person's to retry, so the
    message is theirs."""
    req = urllib.request.Request(url, headers={"User-Agent": "netsec-news-publisher"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read(DOWNLOAD_MAX_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        print(f"news-from-issue: download of {url} failed: {e}")
        sys.exit("The photo in the Image field could not be downloaded. Edit the issue, delete the "
                 "photo, drag it in again and wait until the upload finishes. Or empty the Image "
                 "field to post without a photo.")
    if len(data) > DOWNLOAD_MAX_BYTES:
        sys.exit(f"The photo is larger than {DOWNLOAD_MAX_BYTES // 1_000_000} MB. Edit the issue and use a smaller photo.")
    return data


def shrink(data: bytes) -> bytes:
    """The photo as a JPEG of at most IMAGE_MAX_BYTES and IMAGE_MAX_SIDE
    pixels on its longer side, turned the way the camera held it. The
    camera data (EXIF, with the place it was taken) is not copied."""
    try:
        from PIL import Image, ImageOps
    except ImportError:
        sys.exit("news-from-issue: Pillow is missing. Run pip install -r requirements.txt.")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
        img = ImageOps.exif_transpose(img)
    except Exception:
        sys.exit("The file in the Image field is not a photo that can be read. "
                 "Edit the issue and use a JPEG or PNG photo.")
    if img.mode in ("RGBA", "LA", "P"):
        rgba = img.convert("RGBA")
        flat = Image.new("RGB", rgba.size, "white")
        flat.paste(rgba, mask=rgba.getchannel("A"))
        img = flat
    elif img.mode != "RGB":
        img = img.convert("RGB")
    img.thumbnail((IMAGE_MAX_SIDE, IMAGE_MAX_SIDE), Image.LANCZOS)
    quality = 85
    while True:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
        out = buf.getvalue()
        if len(out) <= IMAGE_MAX_BYTES:
            return out
        if quality > 70:
            quality -= 5
        else:
            img = img.resize((max(1, img.width * 4 // 5), max(1, img.height * 4 // 5)), Image.LANCZOS)


def save_photo(item: dict, data: bytes, root: Path = ROOT) -> str:
    """Writes the shrunk photo as <IMAGE_DIR>/<item id>.jpg and returns that
    path, relative to the site root like the other paths in news.json."""
    out = shrink(data)
    rel = f"{IMAGE_DIR}/{item['id']}.jpg"
    dest = root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(out)
    print(f"news-from-issue: photo saved as {rel} ({len(out) // 1000} kB).")
    return rel


def parse_form(title: str, f: dict[str, str], today: str, root: Path = ROOT) -> dict:
    """The item in English, with the dates in all three languages."""
    site = f.get("site", "").strip().lower()
    if site.startswith("eiss"):
        sys.exit("The Site is EISS, and this form publishes on the NetSec website only. "
                 "Edit the issue and pick NetSec or Joint, or ask the maintainer to post an EISS-only item.")

    headline = one_line(f.get("headline", "")) or clean_title(title)
    if not headline:
        sys.exit("The Headline is empty. Edit the issue and write a headline.")
    check_length("Headline", headline, HEADLINE_MAX)
    label = "Website summary" if "website summary" in f else "Summary"
    summary = one_line(untangle_linkedin(f.get("website summary", f.get("summary", "")), tags=False))
    if not summary:
        sys.exit(f"The {label} is empty. Edit the issue and write one or two sentences for the website.")
    check_length(label, summary, SUMMARY_MAX)
    body = one_line(untangle_linkedin(f.get("body", ""), tags=False))
    check_length("Body", body, BODY_MAX)
    body = body or summary

    pub = check_date("Publication date", f.get("publication date", "")) or date.fromisoformat(today)
    t = f.get("type", "").strip().lower()

    item: dict = {
        "id": f"{slugify(headline)}-{pub:%Y-%m}",
        "type": t if t in TYPES else "announcement",
        "pubDate": paris_iso(pub, time(12, 0)),
        "displayDate": display_dates(pub),
        "title": {"en": headline},
        "summary": {"en": summary},
        "body": {"en": body},
    }
    wg = re.fullmatch(r"WG([1-4])", f.get("working group", "").strip())
    if wg:
        item["wg"] = int(wg.group(1))
    until = check_date("On the home page until date", f.get("on the home page until", ""))
    if until:
        item["homeUntil"] = paris_iso(until, time(23, 59))
    raw_link = f.get("link", "").strip()
    cta = make_cta(raw_link, root)
    if raw_link and (cta is None or any(c.isspace() for c in raw_link)):
        sys.exit("The Link is not a web address. Edit the issue and paste the full address, starting "
                 "with https://, or a page on this site such as essc-2027.html, or leave it empty.")
    if cta:
        item["cta"] = cta
    if site.startswith("joint"):
        item["site"] = "joint"
    ticked = {m.lower() for m in CHECKED_RE.findall(f.get("options", ""))}
    if "include in the newsletter" in ticked:
        item["newsletter"] = True
    no_post = "do not post to linkedin and bluesky" in ticked
    if no_post:
        item["social"] = "skip"
    networks = [] if no_post else list(NETWORK_LABELS)
    if "post on" in f:
        chosen = {m.lower() for m in CHECKED_RE.findall(f["post on"])}
        picked = [n for n, label in NETWORK_LABELS.items() if label.lower() in chosen]
        if no_post and picked:
            sys.exit("Post on has a box ticked, and Options says not to post. Edit the issue and "
                     "untick one of them.")
        if not no_post and not picked:
            sys.exit("No box is ticked under Post on. Edit the issue and tick LinkedIn, Bluesky or both, "
                     "or tick \"Do not post to LinkedIn and Bluesky\" under Options for the website only.")
        networks = networks and picked
    collaborator = f.get("collaborator page", "").strip().lower() == "eiss"
    if item.get("site") == "joint" and "linkedin" in networks and not collaborator:
        sys.exit("The Site is Joint and the news goes to LinkedIn, so EISS's page is added as collaborator. "
                 "Edit the issue and pick EISS under Collaborator page.")
    if collaborator and "linkedin" in networks:
        item["collaborator"] = "eiss"
    if networks and len(networks) < len(NETWORK_LABELS):
        item["networks"] = networks
    image = image_source(f.get("image", ""))
    if image:
        alt = one_line(f.get("image description", ""))
        if not alt:
            sys.exit("The item has a photo but the Image description is empty. Edit the issue and "
                     "write one sentence saying what the photo shows, for people who cannot see it.")
        check_length("Image description", alt, IMAGE_ALT_MAX)
        if image.startswith("https://"):
            item["_image_url"] = image  # downloaded by main(), after the duplicate check
        else:
            item["image"] = image
        item["imageAlt"] = alt
    posts = {}
    for network, box_label, key in POST_BOXES:
        if network not in networks:
            continue
        text = untangle_linkedin(post_text(f.get(key, "")))
        if text:
            check_post(network, box_label, text, item)
            posts[network] = text
    if posts:
        item["posts"] = posts
    return item


def translate(english: dict[str, str]) -> dict[str, dict[str, str]]:
    """{"fr": {title, summary, body}, "de": {...}} from the Claude API.

    Uses a server-side fallback model if the main one declines. Raises
    RuntimeError when no usable translation comes back."""
    import anthropic

    client = anthropic.Anthropic()
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=SYSTEM_PROMPT,
        output_config={"format": {"type": "json_schema", "schema": TRANSLATION_SCHEMA}},
        messages=[{"role": "user", "content": json.dumps(english, ensure_ascii=False)}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("the model declined to translate the item")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("the translation was cut off at max_tokens")
    text = next((b.text for b in response.content if b.type == "text"), "")
    data = json.loads(text)
    for loc in LOCALES:
        for key in ("title", "summary", "body"):
            if not str(data.get(loc, {}).get(key, "")).strip():
                raise RuntimeError(f"the {loc} {key} came back empty")
    return data


def add_translations(item: dict, translator=translate) -> bool:
    """Fill the FR and DE title, summary and body. False when the item stays
    English only (no API key, or the call failed)."""
    if translator is translate and not os.environ.get("ANTHROPIC_API_KEY"):
        print("news-from-issue: ANTHROPIC_API_KEY is not set. "
              "The item is in English only, and the FR and DE pages fall back to English.")
        return False
    english = {k: item[k]["en"] for k in ("title", "summary", "body")}
    try:
        out = translator(english)
    except Exception as e:  # noqa: BLE001 - any failure leaves the item in English
        print(f"news-from-issue: translation failed ({e}). The item is in English only.")
        return False
    for key in ("title", "summary", "body"):
        for loc in LOCALES:
            item[key][loc] = one_line(out[loc][key])
    return True


def insert(text: str, item: dict) -> str:
    """news.json with the item first in `items` and lastBuildDate moved on.

    Works on the file's text, so the rest of the file keeps its exact bytes
    (some older items escape their accents, others do not)."""
    block = json.dumps(item, ensure_ascii=False, indent=2)
    block = "\n".join("    " + ln for ln in block.splitlines())
    m = re.search(r'^  "items": \[\n', text, re.M)
    if not m:
        sys.exit("news-from-issue: data/news.json has no top-level \"items\" list.")
    rest = text[m.end():]
    sep = ",\n" if rest.lstrip().startswith("{") else "\n"
    text = text[: m.end()] + block + sep + rest
    lbd = re.search(r'^  "lastBuildDate": "([^"]*)"', text, re.M)
    if lbd and item["pubDate"] > lbd.group(1):
        text = text[: lbd.start(1)] + item["pubDate"] + text[lbd.end(1):]
    return text


def write_outputs(**values: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            for k, v in values.items():
                fh.write(f"{k}={v}\n")


def main(translator=translate, news_path: Path = NEWS, root: Path = ROOT, fetcher=None) -> int:
    title = os.environ.get("ISSUE_TITLE", "")
    body = os.environ.get("ISSUE_BODY", "")
    today = os.environ.get("TODAY") or date.today().isoformat()

    fields = form_sections(body)
    if not fields:
        sys.exit("This issue does not use the News item form. Open a new issue, "
                 "pick News item, and fill in the form.")
    item = parse_form(title, fields, today, root)
    write_outputs(headline=item["title"]["en"])

    text = news_path.read_text(encoding="utf-8")
    data = json.loads(text)
    if any(it.get("id") == item["id"] for it in data.get("items", [])):
        print(f"news-from-issue: {item['id']} is already in data/news.json. Nothing changed.")
        write_outputs(translated="true", id=item["id"])
        return 0

    url = item.pop("_image_url", "")
    if url:
        alt = item.pop("imageAlt")
        item["image"] = save_photo(item, (fetcher or fetch)(url), root)
        item["imageAlt"] = alt
    translated = add_translations(item, translator)
    text = insert(text, item)
    json.loads(text)  # the splice must leave valid JSON
    news_path.write_text(text, encoding="utf-8")
    print(f"news-from-issue: added {item['id']} ({item['displayDate']['en']}).")
    print(f"TRANSLATED={'true' if translated else 'false'}")
    print(json.dumps(item, ensure_ascii=False, indent=2))
    write_outputs(translated="true" if translated else "false", id=item["id"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
