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

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://netsec-cost.eu"
CARD_DIR = "assets/og/events"

# The event types that have a page of their own. The label is the card's
# eyebrow. An MC plenary points at a section of the home page and gets none.
TYPE_LABEL = {
    "annual-conference": "Annual Conference",
    "policy-workshop": "Policy Workshop",
    "training-school": "Training School",
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


def card_path(page: str) -> Path:
    return ROOT / CARD_DIR / f"{page}.png"


def card_url(page: str) -> str:
    return f"{SITE}/{CARD_DIR}/{page}.png"


def full_name(ev: dict) -> str:
    return (ev.get("jsonld") or {}).get("name") or ev.get("summary", "")


def heading(ev: dict) -> str:
    """The card's title. A policy workshop is named "NetSec Policy Workshop:
    <title>", and the eyebrow already says Policy Workshop, so the card keeps
    the part after the colon."""
    name = full_name(ev)
    if ev.get("eventType") == "policy-workshop" and ":" in name:
        return name.split(":", 1)[1].strip()
    return name


def eyebrow(ev: dict) -> str:
    """The event type, with the year when the title does not carry it."""
    label = TYPE_LABEL[ev["eventType"]]
    year = ev["start"][:4]
    return label if year in heading(ev) else f"{label} · {year}"


def venue(ev: dict) -> tuple[str, str]:
    """(institution, "City, Country") from the event's location.

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
    institution, place = venue(ev)
    date = (ev.get("displayDate") or {}).get(lang) or (ev.get("displayDate") or {}).get("en", "")
    bits = [full_name(ev), date, institution, place]
    return f"{ALT_PREFIX.get(lang, ALT_PREFIX['en'])}: " + ", ".join(b for b in bits if b) + "."
