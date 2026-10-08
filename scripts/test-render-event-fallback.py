"""Tests for render-event-fallback.py (#1769).

The home page's fallback cards are rendered from data/events.json at deploy.
These cover the selection rule it shares with home-events.js (end still
ahead, read in the event's own zone, soonest first, the two most recent when
nothing is upcoming), the card fields, and that its copied I18N table still
matches the JavaScript one.
"""

import importlib.util
import json
import re
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "render_event_fallback", REPO / "scripts" / "render-event-fallback.py"
)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

NOW = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)
PAGE = '<section id="events">\n    <div class="event-list">\n      <p>hand-written</p>\n    </div>\n</section>'


def _ev(uid, start, end=None, **over):
    ev = {"uid": uid, "start": start, "end": end, "eventType": "policy-workshop",
          "cardTitle": {"en": "T " + uid, "fr": "T fr"}, "displayDate": {"en": "D " + uid}}
    ev.update(over)
    return ev


def _data(*events):
    return {"tzid": "Europe/Stockholm", "events": list(events)}


def test_ended_event_is_dropped_and_upcoming_sorted_soonest_first():
    data = _data(_ev("late@x", "2027-06-10T09:00", "2027-06-11T18:00"),
                 _ev("past@x", "2026-09-13T09:00", "2026-09-13T18:00"),
                 _ev("soon@x", "2026-09-18T09:00", "2026-09-18T18:00"))
    upcoming, recent = mod.select(data, NOW)
    assert [e["uid"] for e in upcoming] == ["soon@x", "late@x"] and recent == []


def test_end_is_read_in_the_events_own_zone():
    # 23:30 in Istanbul is 20:30 UTC, already past a 21:00 UTC now.
    now = datetime(2026, 9, 13, 21, 0, tzinfo=timezone.utc)
    data = _data(_ev("ist@x", "2026-09-13T09:00", "2026-09-13T23:30", tzid="Europe/Istanbul"))
    assert mod.select(data, now)[0] == []


def test_nothing_upcoming_shows_the_two_most_recent():
    data = _data(_ev("a@x", "2026-06-09T09:00", "2026-06-11T18:00"),
                 _ev("b@x", "2026-09-13T09:00", "2026-09-13T18:00"),
                 _ev("c@x", "2026-09-11T09:00", "2026-09-11T11:00"))
    upcoming, recent = mod.select(data, NOW)
    assert upcoming == [] and [e["uid"] for e in recent] == ["b@x", "c@x"]


def test_empty_state_matches_the_javascript():
    data = _data(_ev("b@x", "2026-09-13T09:00", "2026-09-13T18:00"))
    out = mod.render(PAGE, *mod.select(data, NOW), "de")
    assert '<p class="events-empty">Derzeit keine bevorstehenden Veranstaltungen.</p>' in out
    assert '<h3 class="events-recent-head">Letzte Veranstaltungen</h3>' in out
    assert "hand-written" not in out


def test_card_carries_the_localised_fields():
    ev = _ev("w@x", "2026-09-18T09:00", "2026-09-18T18:00", workingGroups=[3, 2], coHost="joint",
             status="TENTATIVE", cta={"href": "w.html", "i18n": {"en": "Details"}},
             meta=[{"icon": "pin", "i18n": {"en": "<strong>Ankara</strong>"}}])
    html = mod.card(ev, "fr")
    assert 'class="event-card glass card-clickable" data-event-uid="w@x"' in html
    assert '<span class="event-type">Atelier politique</span>' in html
    assert "event-tentative" in html and "Conjoint EISS × NetSec" in html
    assert html.index("wg-2") < html.index("wg-3") and "working-groups.fr.html#wg2" in html
    assert "<h3>T fr</h3>" in html and '<span class="event-date">D w@x</span>' in html
    assert "<span><strong>Ankara</strong></span>" in html
    assert '<a class="event-link card-stretch" href="w.html">Details</a>' in html


def test_i18n_table_matches_home_events_js():
    js = (REPO / "assets" / "js" / "home-events.js").read_text(encoding="utf-8")
    for locale, t in mod.I18N.items():
        for kind, label in t["type"].items():
            assert re.search(rf"'{re.escape(kind)}':\s*'{re.escape(label)}'", js), (locale, kind)
        for key in ("wgAria", "jointBadge", "jointTitle", "noUpcoming", "recent"):
            assert f"'{t[key]}'" in js, (locale, key)
        assert json.dumps(t["saveTheDate"], ensure_ascii=False) in js or f"'{t['saveTheDate']}'" in js


def test_page_without_an_event_list_is_left_alone():
    assert mod.render("<p>no list</p>", [], [], "en") == "<p>no list</p>"
