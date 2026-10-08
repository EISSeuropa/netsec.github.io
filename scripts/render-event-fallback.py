#!/usr/bin/env python3
"""Rewrite the home page's fallback event cards from data/events.json (#1769).

The cards in `#events .event-list` are what a reader sees when
`assets/js/home-events.js` does not run, and what Pagefind indexes. They used
to be hand-written. #1771 pruned the concluded ones at deploy, but nothing
added a card for a new event, so once the 2026 events ended the fallback said
"No upcoming events" while data/events.json already listed two for 2027.

The cards are now rendered from the same fields buildCard in home-events.js
reads, with the same selection: events whose end is still ahead, soonest
first, and when none are, the empty line followed by the two most recently
finished. Left out are the parts that only work with JavaScript running, the
Read-more clamp and the Add-to-calendar menu.

Runs at deploy, like render-news-fallback.py, because the right set of cards
is a function of the date as well as of the file.

Usage:
  python3 scripts/render-event-fallback.py            # rewrite in place
  python3 scripts/render-event-fallback.py --dry-run  # report, change nothing
"""
from __future__ import annotations

import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
EVENTS = ROOT / "data" / "events.json"
PAGES = {"en": ROOT / "index.html", "fr": ROOT / "index.fr.html", "de": ROOT / "index.de.html"}
LIST = re.compile(r'(<div class="event-list">)(.*?)(\n    </div>)', re.S)

# Copied from I18N in home-events.js. The test suite checks the two agree.
I18N = {
    "en": {"type": {"training-school": "Training School", "annual-conference": "Annual Conference",
                    "policy-workshop": "Policy Workshop", "itc-conference": "ITC Conference",
                    "mc-plenary": "MC Plenary", "event": "Event"},
           "wgAria": "Working Groups served", "jointBadge": "Joint EISS × NetSec",
           "jointTitle": "Jointly organised by EISS and NetSec",
           "noUpcoming": "No upcoming events right now.", "recent": "Recent events",
           "saveTheDate": "Save the date"},
    "fr": {"type": {"training-school": "École de formation", "annual-conference": "Conférence annuelle",
                    "policy-workshop": "Atelier politique", "itc-conference": "Conférence ITC",
                    "mc-plenary": "Plénière du CG", "event": "Événement"},
           "wgAria": "Groupes de travail concernés", "jointBadge": "Conjoint EISS × NetSec",
           "jointTitle": "Organisé conjointement par EISS et NetSec",
           "noUpcoming": "Aucun événement à venir pour le moment.", "recent": "Événements récents",
           "saveTheDate": "À noter dans l'agenda"},
    "de": {"type": {"training-school": "Ausbildungsschule", "annual-conference": "Jahreskonferenz",
                    "policy-workshop": "Politik-Workshop", "itc-conference": "ITC-Konferenz",
                    "mc-plenary": "MC-Plenum", "event": "Veranstaltung"},
           "wgAria": "Beteiligte Arbeitsgruppen", "jointBadge": "Gemeinsam EISS × NetSec",
           "jointTitle": "Gemeinsam von EISS und NetSec organisiert",
           "noUpcoming": "Derzeit keine bevorstehenden Veranstaltungen.", "recent": "Letzte Veranstaltungen",
           "saveTheDate": "Vormerken"},
}
_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{}</svg>'
ICONS = {
    "pin": _SVG.format('<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/>'),
    "clock": _SVG.format('<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>'),
    "people": _SVG.format('<path d="M20 21v-2a4 4 0 00-3-3.87M4 21v-2a4 4 0 013-3.87M16 3.13a4 4 0 010 7.75M8 3.13a4 4 0 000 7.75"/>'),
    "calendar": _SVG.format('<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>'),
}


def _pick(value, locale: str) -> str:
    if isinstance(value, dict):
        return value.get(locale) or value.get("en") or ""
    return value or ""


def _when(ev: dict, field: str, default_tz: str) -> datetime | None:
    """An event time in UTC, read in the event's own zone as home-events.js does."""
    stamp = ev.get(field) or ev.get("start")
    if not stamp:
        return None
    try:
        zone = ZoneInfo(ev.get("tzid") or default_tz)
    except Exception:
        return None
    return datetime.fromisoformat(stamp).replace(tzinfo=zone).astimezone(timezone.utc)


def select(data: dict, now: datetime) -> tuple[list[dict], list[dict]]:
    """(upcoming, recent). Mirrors renderHomeEvents: an event whose end is
    unknown counts as upcoming, and `recent` is only filled when nothing is."""
    tz = data.get("tzid") or "Europe/Stockholm"
    events = data.get("events", [])
    upcoming = [ev for ev in events if (_when(ev, "end", tz) or now) >= now]
    upcoming.sort(key=lambda ev: _when(ev, "start", tz) or now)
    if upcoming:
        return upcoming, []
    ended = [ev for ev in events if _when(ev, "end", tz)]
    ended.sort(key=lambda ev: _when(ev, "end", tz), reverse=True)
    return [], ended[:2]


def card(ev: dict, locale: str) -> str:
    e = lambda s: html.escape(str(s), quote=True)
    t = I18N[locale]
    cta = ev.get("cta") or {}
    cls = "event-card glass" + (" featured" if ev.get("featured") else "") + (" card-clickable" if cta.get("href") else "")
    out = [f'      <article class="{cls}" data-event-uid="{e(ev["uid"])}">']
    date = _pick(ev.get("displayDate"), locale)
    if date:
        out.append(f'        <span class="event-date">{e(date)}</span>')
    kind = t["type"].get(ev.get("eventType")) or ev.get("eventType") or ""
    if kind:
        out.append(f'        <span class="event-type">{e(kind)}</span>')
    if ev.get("status") == "TENTATIVE":
        out.append(f'        <span class="event-tentative">{e(t["saveTheDate"])}</span>')
    if ev.get("coHost") == "joint":
        out.append(f'        <span class="event-cohost" title="{e(t["jointTitle"])}">{e(t["jointBadge"])}</span>')
    wgs = sorted(ev.get("workingGroups") or [])
    if wgs:
        suffix = "" if locale == "en" else locale + "."
        pills = "".join(f'<a class="event-wg-pill wg-{n}" href="working-groups.{suffix}html#wg{n}">WG{n}</a>' for n in wgs)
        out.append(f'        <div class="event-wgs" aria-label="{e(t["wgAria"])}">{pills}</div>')
    out.append(f'        <h3>{e(_pick(ev.get("cardTitle"), locale) or ev.get("summary", ""))}</h3>')
    out.append(f'        <p class="event-desc">{e(_pick(ev.get("cardDescription"), locale) or ev.get("description", ""))}</p>')
    if ev.get("meta"):
        out.append('        <div class="event-meta">')
        for row in ev["meta"]:
            # The JSON carries <strong> and <a> in these rows, and home-events.js
            # writes them as HTML too, so they are not escaped.
            out.append('          <div class="event-meta-row">'
                       f'{ICONS.get(row.get("icon"), ICONS["calendar"])}'
                       f'<span>{_pick(row.get("i18n"), locale)}</span></div>')
        out.append("        </div>")
    if cta.get("href"):
        ext = ' target="_blank" rel="noopener"' if cta.get("external") else ""
        out.append('        <div class="event-card-ctas">'
                   f'<a class="event-link card-stretch" href="{e(_pick(cta["href"], locale))}"{ext}>'
                   f'{e(_pick(cta.get("i18n"), locale))}</a></div>')
    out.append("      </article>")
    return "\n".join(out)


def render(page: str, upcoming: list[dict], recent: list[dict], locale: str) -> str:
    if upcoming:
        parts = [card(ev, locale) for ev in upcoming]
    else:
        t = I18N[locale]
        parts = [f'      <p class="events-empty">{html.escape(t["noUpcoming"])}</p>']
        if recent:
            parts.append(f'      <h3 class="events-recent-head">{html.escape(t["recent"])}</h3>')
            parts += [card(ev, locale) for ev in recent]
    body = "\n" + "\n".join(parts)
    return LIST.sub(lambda m: m.group(1) + body + m.group(3), page, count=1)


def main(argv: list[str]) -> int:
    data = json.loads(EVENTS.read_text(encoding="utf-8"))
    upcoming, recent = select(data, datetime.now(timezone.utc))
    for locale, path in PAGES.items():
        page = path.read_text(encoding="utf-8")
        if not LIST.search(page):
            print(f"✗ no event-list block in {path.name}")
            return 1
        new = render(page, upcoming, recent, locale)
        if new != page and "--dry-run" not in argv:
            path.write_text(new, encoding="utf-8")
        print(f"  {path.name}: {'unchanged' if new == page else 'rewritten'}")
    shown = upcoming or recent
    print(("✓ fallback events: " if upcoming else "✓ no upcoming events, showing recent: ")
          + ", ".join(ev["uid"] for ev in shown))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
