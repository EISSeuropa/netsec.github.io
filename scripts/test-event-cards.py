"""Tests for _event_cards.py and build-event-og.py, the event-page social
cards (#2185)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import _event_cards as ec  # noqa: E402

_spec = importlib.util.spec_from_file_location("build_event_og", ROOT / "scripts" / "build-event-og.py")
beo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(beo)


def _ev(**kw) -> dict:
    ev = {
        "uid": "x@netsec-cost.eu",
        "url": "https://netsec-cost.eu/essc-2027.html",
        "eventType": "annual-conference",
        "start": "2027-06-10T08:00",
        "summary": "Summary",
        "jsonld": {"name": "European Security Studies Conference 2027"},
        "location": "University of Belgrade, Faculty of Political Science, Belgrade, Serbia",
        "displayDate": {"en": "10–11 June 2027", "fr": "10–11 juin 2027", "de": "10.–11. Juni 2027"},
    }
    ev.update(kw)
    return ev


def test_card_events_keeps_the_latest_event_per_page():
    old = _ev(uid="a", url="https://netsec-cost.eu/summer-school.html",
              eventType="training-school", start="2026-06-09T09:00")
    new = _ev(uid="b", url="https://netsec-cost.eu/summer-school.html",
              eventType="training-school", start="2027-06-08T09:00")
    assert ec.card_events([new, old])["summer-school"] is new
    assert ec.card_events([old, new])["summer-school"] is new


def test_card_events_skips_home_sections_and_other_types():
    plenary = _ev(url="https://netsec-cost.eu/#events", eventType="mc-plenary")
    other = _ev(url="https://netsec-cost.eu/grants.html", eventType="mc-plenary")
    assert ec.card_events([plenary, other]) == {}


def test_every_live_event_page_has_a_card():
    pages = set(ec.card_events())
    assert {"essc-2026", "essc-2027", "policy-workshop-2026",
            "policy-workshop-2027", "summer-school"} <= pages


def test_heading_drops_the_policy_workshop_prefix_and_eyebrow_adds_the_year():
    ws = _ev(eventType="policy-workshop", start="2027-04-28T09:00",
             jsonld={"name": "NetSec Policy Workshop: Security Beyond the State"})
    assert ec.heading(ws) == "Security Beyond the State"
    assert ec.eyebrow(ws) == "Policy Workshop · 2027"
    # The year is already in the conference's name.
    assert ec.eyebrow(_ev()) == "Annual Conference"


def test_venue_drops_street_and_postcode():
    stockholm = _ev(location="Stockholm University, Frescativägen, 114 19 Stockholm, Sweden")
    assert ec.venue(stockholm) == ("Stockholm University", "Stockholm, Sweden")
    assert ec.venue(_ev()) == ("University of Belgrade, Faculty of Political Science", "Belgrade, Serbia")
    assert ec.venue(_ev(location="Online")) == ("Online", "")


def test_card_alt_is_localised():
    assert ec.card_alt(_ev(), "fr").startswith("Carte de l'événement: European Security Studies Conference 2027, 10–11 juin 2027")
    assert ec.card_alt(_ev(), "de").startswith("Karte zur Veranstaltung: ")
    assert ec.card_alt(_ev(), "en").endswith("Belgrade, Serbia.")


def test_card_markup_fills_every_slot_and_escapes():
    ev = _ev(jsonld={"name": "Peace & War <2027>"})
    out = beo.card_markup("essc-2027", ev, "<svg/>")
    assert "Peace &amp; War &lt;2027&gt;" in out
    assert "10–11 June 2027" in out and "· Belgrade, Serbia" in out
    assert "netsec-cost.eu/essc-2027" in out
    assert "$" not in out


def test_long_heading_takes_the_smaller_size():
    long = _ev(eventType="policy-workshop",
               jsonld={"name": "NetSec Policy Workshop: Great Power Politics and the Future of Alliances"})
    assert '<h1 class="long">' in beo.card_markup("p", long, "")
    assert "<h1>" in beo.card_markup("p", _ev(jsonld={"name": "Short"}), "")


# ── Long titles (#2193) ──

def test_shorten_keeps_a_title_that_fits():
    t = "Great Power Politics and the Future of Alliances"
    assert ec.shorten(t) == t


def test_shorten_cuts_at_the_first_natural_break():
    t = "Security Beyond the State: Managing and Countering Transnational Threats and Vulnerabilities"
    assert ec.shorten(t) == "Security Beyond the State"
    t = "European Security in a Fragmenting Order – Alliances, Autonomy and Deterrence Revisited"
    assert ec.shorten(t) == "European Security in a Fragmenting Order"
    # The first break wins, not the longest prefix that fits.
    t = "Deterrence Today: Theory – Practice and the Long Shadow of Nuclear Weapons in Europe"
    assert ec.shorten(t) == "Deterrence Today"


def test_shorten_skips_a_break_too_early_to_carry_the_sense():
    # "WG2: " would leave three characters, so the word cut applies.
    t = "WG2: " + "word " * 20
    out = ec.shorten(t)
    assert out.endswith("…") and len(out) <= ec.HEADING_MAX


def test_shorten_falls_back_to_a_word_boundary_with_an_ellipsis():
    t = "The Long and Winding Road of European Defence Integration Since the End of the Cold War"
    out = ec.shorten(t)
    assert out == "The Long and Winding Road of European Defence…"
    assert len(out) <= ec.HEADING_MAX


def test_heading_shortens_a_long_policy_workshop_title_after_the_prefix():
    ws = _ev(eventType="policy-workshop", jsonld={
        "name": "NetSec Policy Workshop: Security Beyond the State: Managing and Countering "
                "Transnational Threats and Vulnerabilities"})
    assert ec.heading(ws) == "Security Beyond the State"
    # The alt text keeps the full name.
    assert "Transnational Threats and Vulnerabilities" in ec.card_alt(ws, "en")


def test_card_css_clamps_title_and_facts():
    out = beo.card_markup("p", _ev(), "")
    assert "-webkit-line-clamp:2" in out
    assert "text-overflow:ellipsis" in out


# ── Versioned card URL (#2193) ──

def test_card_url_is_a_jpeg_with_a_version_that_follows_the_card_text():
    a = ec.card_url("essc-2027", _ev())
    assert a.startswith("https://netsec-cost.eu/assets/og/events/essc-2027.jpg?v=")
    assert a == ec.card_url("essc-2027", _ev())
    moved = _ev(displayDate={"en": "17–18 June 2027", "fr": "", "de": ""})
    assert ec.card_url("essc-2027", moved) != a
    # A change the card does not show leaves the URL alone.
    assert ec.card_url("essc-2027", _ev(summary="Other summary")) == a
    assert ec.card_path("essc-2027").suffix == ".jpg"
