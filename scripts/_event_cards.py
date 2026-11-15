"""The social card each event page unfurls as (#2185).

Shared by build-event-og.py, which draws the cards, inject-seo.py, which
points each event page's og:image at its card, and social-post.py, which
attaches the card to a news post that links to the page. Keeping the choice
of event and the card's wording here means the three cannot disagree about
which pages have a card or what it says.

An event page is a page that an event in data/events.json names as its url.
When a page holds more than one event (summer-school.html carries the 2026
and the 2027 Training School), the card shows the latest one.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://netsec-cost.eu"
CARD_DIR = "assets/og/events"

LANGS = ("en", "fr", "de")

# The event types that have a page of their own. The label is the card's
# eyebrow, in the terms the FR and DE pages already use. An MC plenary points
# at a section of the home page and gets none.
TYPE_LABEL = {
    "annual-conference": {"en": "Annual Conference", "fr": "Conférence annuelle", "de": "Jahreskonferenz"},
    "policy-workshop": {"en": "Policy Workshop", "fr": "Atelier politique", "de": "Politik-Workshop"},
    "training-school": {"en": "Training School", "fr": "École de formation", "de": "Ausbildungsschule"},
}

ALT_PREFIX = {
    "en": "Event card",
    "fr": "Carte de l'événement",
    "de": "Karte zur Veranstaltung",
}


def load_events() -> list[dict]:
    return json.loads((ROOT / "data" / "events.json").read_text(encoding="utf-8"))["events"]


def page_of(ev: dict) -> str:
    """The page base-name an event's url points at, or "" for a section of
    the home page."""
    path = ev.get("url", "").removeprefix(SITE).lstrip("/")
    return path[:-5] if path.endswith(".html") else ""


def card_events(events: list[dict] | None = None) -> dict[str, dict]:
    """Map each event page's base-name to the event its card shows."""
    chosen: dict[str, dict] = {}
    for ev in events if events is not None else load_events():
        page = page_of(ev)
        if not page or ev.get("eventType") not in TYPE_LABEL:
            continue
        if page not in chosen or ev["start"] > chosen[page]["start"]:
            chosen[page] = ev
    return chosen


def _t(field: dict | None, lang: str) -> str:
    """A per-locale field's text in lang, falling back to English."""
    field = field or {}
    return field.get(lang) or field.get("en", "")


def card_path(page: str, lang: str = "en") -> Path:
    """essc-2027.jpg, essc-2027.fr.jpg, essc-2027.de.jpg: the page's own
    naming, one card per locale."""
    suffix = "" if lang == "en" else f".{lang}"
    return ROOT / CARD_DIR / f"{page}{suffix}.jpg"


def card_version(page: str, ev: dict, lang: str = "en") -> str:
    """A short hash of everything the card shows, and of the builder that
    draws it. Platforms cache a preview image by URL for days, so a card
    redrawn for a moved date or a new template needs a new URL to be fetched
    again."""
    institution, place = venue(ev, lang)
    template = (ROOT / "scripts" / "build-event-og.py").read_bytes()
    text = json.dumps([page, lang, eyebrow(ev, lang), heading(ev, lang), _t(ev.get("displayDate"), lang),
                       institution, place], ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8") + template).hexdigest()[:8]


def card_url(page: str, ev: dict, lang: str = "en") -> str:
    return f"{SITE}/{CARD_DIR}/{card_path(page, lang).name}?v={card_version(page, ev, lang)}"


def full_name(ev: dict) -> str:
    return (ev.get("jsonld") or {}).get("name") or ev.get("summary", "")


# The longest title the card sets on two lines at its smaller size. The
# longest today is "Great Power Politics and the Future of Alliances" (48).
HEADING_MAX = 56
# Where a long title can be cut without losing its sense, in the order they
# are tried. A cut leaving fewer than HEADING_MIN characters is not taken.
NATURAL_BREAKS = (":", " – ", " — ", " | ", " (")
HEADING_MIN = 12


def shorten(title: str, limit: int = HEADING_MAX) -> str:
    """A title that fits the card. Over the limit, it is cut at its first
    natural break ("Security Beyond the State: Managing ..." keeps "Security
    Beyond the State"). With no break in reach, it is cut at the last word
    that fits and ends with an ellipsis. The full name stays in the alt text."""
    if len(title) <= limit:
        return title
    cuts = [title.find(b) for b in NATURAL_BREAKS]
    cuts = [c for c in cuts if HEADING_MIN <= c <= limit]
    if cuts:
        return title[:min(cuts)].rstrip()
    return title[:limit - 1].rsplit(" ", 1)[0].rstrip(",;:-–—") + "…"


def heading(ev: dict, lang: str = "en") -> str:
    """The card's title in lang, from the same cardTitle and cardSubtitle the
    event listings show. A policy workshop's cardTitle is only "NetSec Policy
    Workshop", which the eyebrow already says, so its card takes the
    workshop's own title from cardSubtitle. A title too long for two lines is
    shortened."""
    title = _t(ev.get("cardTitle"), lang) or full_name(ev)
    if ev.get("eventType") == "policy-workshop":
        if ev.get("cardSubtitle"):
            title = _t(ev.get("cardSubtitle"), lang)
        elif ":" in title:
            title = title.split(":", 1)[1].strip()
    return shorten(title)


def full_title(ev: dict, lang: str = "en") -> str:
    """The unshortened name for the alt text: cardTitle, then a workshop's own
    title after a colon. The date that follows in the alt text gives the year."""
    title = _t(ev.get("cardTitle"), lang) or full_name(ev)
    if ev.get("eventType") == "policy-workshop" and ev.get("cardSubtitle"):
        title = f"{title}: {_t(ev.get('cardSubtitle'), lang)}"
    return title


def eyebrow(ev: dict, lang: str = "en") -> str:
    """The event type, with the year when the title does not carry it."""
    label = _t(TYPE_LABEL[ev["eventType"]], lang)
    year = ev["start"][:4]
    return label if year in heading(ev, lang) else f"{label} · {year}"


_PIN_RE = re.compile(r"<strong>(?P<inst>.*?)</strong>\s*·\s*(?P<rest>.*)", re.S)
_FACULTY = ("Faculty", "Faculté", "Fakultät")


def venue(ev: dict, lang: str = "en") -> tuple[str, str]:
    """(institution, "City, Country") in lang.

    Both come from what the event listings already show in each locale. The
    institution is the bold part of the event's map-pin line (meta, icon
    "pin"), e.g. "<strong>Université de Belgrade</strong> · Faculté des
    sciences politiques, Belgrade, Serbie", plus a faculty named right after
    it. The place is cardLocation ("Belgrade, Serbie"). An event with neither
    falls back to its English postal location, below."""
    pin = next((m for m in ev.get("meta") or [] if m.get("icon") == "pin"), None)
    m = _PIN_RE.match(_t((pin or {}).get("i18n"), lang)) if pin else None
    if m:
        institution = html.unescape(m["inst"]).strip()
        first = html.unescape(re.sub(r"<[^>]+>", "", m["rest"])).split(",")[0].strip()
        if first.startswith(_FACULTY):
            institution += f", {first}"
        place = _t(ev.get("cardLocation"), lang)
        if place:
            return institution, place
    return _postal_venue(ev)


def _postal_venue(ev: dict) -> tuple[str, str]:
    """(institution, "City, Country") from the event's English location.

    The location is a postal line, e.g. "Stockholm University, Frescativägen,
    114 19 Stockholm, Sweden" or "University of Belgrade, Faculty of Political
    Science, Belgrade, Serbia". The institution is the first part, plus a
    following "Faculty of ..." part. The place is the last two parts with any
    postcode removed. A street between them is dropped.
    """
    parts = [p.strip() for p in ev.get("location", "").split(",") if p.strip()]
    if len(parts) < 3:
        return (", ".join(parts), "")
    institution = parts[0]
    if parts[1].startswith("Faculty"):
        institution += f", {parts[1]}"
    city = re.sub(r"[\d ]{3,}", " ", parts[-2]).strip()
    return institution, f"{city}, {parts[-1]}"


def card_alt(ev: dict, lang: str) -> str:
    institution, place = venue(ev, lang)
    bits = [full_title(ev, lang), _t(ev.get("displayDate"), lang), institution, place]
    return f"{ALT_PREFIX.get(lang, ALT_PREFIX['en'])}: " + ", ".join(b for b in bits if b) + "."
