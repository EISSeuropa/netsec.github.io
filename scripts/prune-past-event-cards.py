#!/usr/bin/env python3
"""Drop concluded events from the home page's fallback event cards (#1769).

The home page's `#events .event-list` holds hand-written cards for the
upcoming events. `assets/js/home-events.js` replaces them from
`data/events.json` on load, and deliberately leaves them alone when that
fetch fails, so a reader without JavaScript still sees something.

Nothing expired them. The JavaScript filters on "end is still ahead", the
markup could not, so from the morning after an event the fallback advertised
a concluded workshop as upcoming.

This runs at deploy rather than in a commit, because the fact that goes stale
is the date rather than the file. A drift gate on a pull request cannot catch
a page that was correct when it merged and is wrong three weeks later, and the
Pages deploy already runs every six hours. Same reasoning as the profile pages
and the `?v=` cache-bust stamp, which are also derived at deploy.

Editorial copy stays hand-written. This only removes cards whose event has
ended, so a new event still gets its fallback card written by hand alongside
its entry in data/events.json.

Usage:
  python3 scripts/prune-past-event-cards.py            # rewrite in place
  python3 scripts/prune-past-event-cards.py --dry-run  # report, change nothing
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
EVENTS = ROOT / "data" / "events.json"
PAGES = {
    ROOT / "index.html": "No upcoming events right now.",
    ROOT / "index.fr.html": "Aucun événement à venir pour le moment.",
    ROOT / "index.de.html": "Derzeit keine bevorstehenden Veranstaltungen.",
}
# Same shape home-events.js renders for an empty list, so the two paths agree.
EMPTY = '      <p class="events-empty">{}</p>'


def ended_uids(data: dict, now: datetime) -> set[str]:
    """The uids whose event has finished, in the event's own time zone.

    Mirrors the `endMs(ev) >= nowMs` filter in home-events.js, including its
    fallback from `end` to `start`. An event whose zone is unknown is kept,
    on the principle that showing a finished event is the lesser fault
    against dropping a live one.
    """
    default_tz = data.get("tzid") or "Europe/Stockholm"
    out: set[str] = set()
    for ev in data.get("events", []):
        stamp = ev.get("end") or ev.get("start")
        if not stamp:
            continue
        try:
            zone = ZoneInfo(ev.get("tzid") or default_tz)
        except Exception:
            continue
        if datetime.fromisoformat(stamp).replace(tzinfo=zone) < now:
            out.add(ev["uid"])
    return out


def prune(html: str, ended: set[str], empty_text: str) -> tuple[str, list[str]]:
    """Remove every card tagged with an ended uid. Returns the new HTML and
    the uids dropped."""
    m = re.search(r'(<div class="event-list">)(.*?)(\n    </div>)', html, re.S)
    if not m:
        return html, []
    block = m.group(2)
    dropped: list[str] = []
    for card_m in re.finditer(
        r'\n[ \t]*<article class="event-card[^"]*" data-event-uid="([^"]*)">.*?\n[ \t]*</article>',
        block, re.S,
    ):
        if card_m.group(1) in ended:
            block = block.replace(card_m.group(0), "")
            dropped.append(card_m.group(1))
    if not dropped:
        return html, []
    if "<article" not in block:
        block = "\n" + EMPTY.format(empty_text) + "\n"
    return html[:m.start(2)] + block + html[m.end(2):], dropped


def main(argv: list[str]) -> int:
    dry = "--dry-run" in argv
    data = json.loads(EVENTS.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    ended = ended_uids(data, now)
    if not ended:
        print("✓ no concluded events, fallback cards left as written")
        return 0

    total = 0
    for path, empty_text in PAGES.items():
        html = path.read_text(encoding="utf-8")
        new, dropped = prune(html, ended, empty_text)
        if not dropped:
            continue
        total += len(dropped)
        verb = "would drop" if dry else "dropped"
        print(f"  {verb} {len(dropped)} card(s) from {path.name}: "
              + ", ".join(sorted(dropped)))
        if not dry:
            path.write_text(new, encoding="utf-8")
    if total:
        print(f"✓ {'would prune' if dry else 'pruned'} {total} concluded "
              f"fallback card(s)")
    else:
        print("✓ fallback cards already current")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
