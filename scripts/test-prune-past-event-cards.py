"""Tests for prune-past-event-cards.py (#1769).

The home page's fallback cards had no way to expire, so a concluded event
stayed on screen advertised as upcoming. These cover the expiry rule and the
two edges around it: the card of a still-running event survives, and a list
emptied by the prune gets the same empty state the JavaScript renders.
"""

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "prune_past_event_cards", REPO / "scripts" / "prune-past-event-cards.py"
)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

NOW = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)


def _data(**over):
    d = {
        "tzid": "Europe/Stockholm",
        "events": [
            {"uid": "past@x", "start": "2026-09-13T09:00", "end": "2026-09-13T18:00",
             "tzid": "Europe/Istanbul"},
            {"uid": "future@x", "start": "2026-09-18T09:00", "end": "2026-09-18T18:00"},
        ],
    }
    d.update(over)
    return d


def _page(*uids):
    cards = "".join(
        f'\n      <article class="event-card glass" data-event-uid="{u}">'
        f'\n        <h3>{u}</h3>'
        f'\n      </article>' for u in uids
    )
    return f'<section>\n    <div class="event-list">{cards}\n    </div>\n  </section>'


def test_concluded_event_is_ended():
    assert mod.ended_uids(_data(), NOW) == {"past@x"}


def test_event_still_ahead_is_not_ended():
    assert "future@x" not in mod.ended_uids(_data(), NOW)


def test_end_is_read_in_the_events_own_zone():
    """The Ankara workshop ends at 18:00 +03:00, which is 15:00 UTC. An hour
    before that it is still running, and the same wall clock read as
    Stockholm would already have called it finished."""
    just_before = datetime(2026, 9, 13, 14, 59, tzinfo=timezone.utc)
    assert "past@x" not in mod.ended_uids(_data(), just_before)
    just_after = datetime(2026, 9, 13, 15, 1, tzinfo=timezone.utc)
    assert "past@x" in mod.ended_uids(_data(), just_after)


def test_event_missing_a_zone_falls_back_to_the_calendar_default():
    d = _data(events=[{"uid": "a@x", "start": "2026-09-18T09:00",
                       "end": "2026-09-18T18:00"}])
    assert mod.ended_uids(d, NOW) == set()


def test_past_card_is_removed_and_future_card_survives():
    html, dropped = mod.prune(_page("past@x", "future@x"), {"past@x"}, "Nothing.")
    assert dropped == ["past@x"]
    assert "past@x" not in html
    assert 'data-event-uid="future@x"' in html


def test_emptying_the_list_leaves_the_empty_state():
    html, dropped = mod.prune(_page("past@x"), {"past@x"}, "Nothing upcoming.")
    assert dropped == ["past@x"]
    assert "<article" not in html
    assert '<p class="events-empty">Nothing upcoming.</p>' in html


def test_nothing_ended_leaves_the_page_untouched():
    page = _page("future@x")
    html, dropped = mod.prune(page, set(), "Nothing.")
    assert dropped == []
    assert html == page


def test_page_without_an_event_list_is_left_alone():
    page = "<section><p>No list here.</p></section>"
    assert mod.prune(page, {"past@x"}, "Nothing.") == (page, [])
