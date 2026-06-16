#!/usr/bin/env python3
"""
Sync helper: refresh data/indico.json from the EISS Indico instance.

NetSec uses the same Indico as EISS (https://indico.eiss-europa.com) for
hosting jointly-organised conferences (ESSC 26 onwards) and NetSec's own
standalone events (Summer School, training schools, MC plenaries) via a
dedicated NetSec category (#8).

Usage:
    python3 scripts/sync-indico.py

What it does:
  1. GETs https://indico.eiss-europa.com/export/categ/1.json
     (the Annual Conferences category) with `from=today` and
     `to=today+LOOK_AHEAD_DAYS`. Returns the list of upcoming ESSC
     events. Also fetches category #8 (NetSec's own events, best-effort)
     for standalone events.
  2. Classifies events as standalone (category #8), joint (EISS category
     + NetSec keyword), or EISS-only (excluded). See `classify_netsec`.
  3. For each event, GETs /export/timetable/{event_id}.json and
     normalises the timetable into a `programme.days[].rows[]`
     structure: day → time-blocks → session cards. Parallel sessions
     (same startTime, different rooms) get grouped into a single
     `parallel` row.
  4. Strips PII surface: Indico publishes emailHashes (Gravatar
     lookups) for every person — we drop them. Internal db_ids /
     person_ids are also dropped. Names + affiliations remain (those
     are already public on Indico's event page; we don't widen
     exposure, we mirror it).
  5. Patches `data/events.json`: refreshes allow-listed fields on linked
     entries (those with `indicoEventId`), sets a `coHost` field
     (`"joint"` or `"standalone"`), and appends newly-discovered NetSec
     events as `autoDiscovered: true` entries (EN copy only, pending
     hand-translation, no machine translation per CLAUDE.md §1).
  6. Writes data/indico.json. Idempotent: if the new payload is
     byte-identical to what's on disk, the file isn't touched.

The schema mirrors EISS's exactly (annualConferences[year].programme
.days[].rows[]) so the same rendering template shape can be reused
when we eventually port the live grid. Design rationale at
https://github.com/EISSeuropa/EISSeuropa.github.io/blob/master/docs/indico-programme-integration.md
— written explicitly to be transferable to NetSec.

Failure modes:
  - Network failure or non-200 from Indico → exit 1. The CI workflow
    treats this as a soft fail: the existing snapshot stays in place
    and the site keeps working with the last good data.
  - Schema drift in Indico's response → defensive `.get()` everywhere
    with sensible defaults; partial data is preferred over a crash.

Auth modes:
  - Anonymous (default): the `/export/*` endpoints work without auth
    for public events. ESSC 26's programme is public, so this is all
    the first port needs.
  - Authenticated (opt-in): if INDICO_API_TOKEN is set in the env,
    `/api/*` endpoint calls add `Authorization: Bearer …`. Legacy
    `/export/*` rejects Bearer with a 400, so default `_get()` stays
    anonymous. Wire in `authenticate=True` per-call site once we
    reach for `/api/*` data (registration state, private events).

Requires: requests. See scripts/requirements.txt.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Install deps: pip install -r scripts/requirements.txt")

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "indico.json"

# Companion file: the hand-curated calendar / homepage-banner source.
# Entries that opt into a partial auto-sync (by carrying an
# `indicoEventId` field) get their `summary`, `start`, and `end`
# overwritten from the fresh Indico payload. Everything else stays
# hand-edited. See the function `_patch_events_json` for the
# allow-list rationale.
EVENTS_OUT = ROOT / "data" / "events.json"
EVENTS_JSON_SYNCED_FIELDS = ("summary", "start", "end")

INDICO_BASE = "https://indico.eiss-europa.com"

# The Indico category we sync. Currently `1` (Annual Conferences) on
# the EISS instance — ESSC editions live here. When NetSec starts
# putting its own events (Summer School, training schools, MC
# plenaries) on the same instance, either add their category ids to
# this set or expand to the root category `0` and bucket the result
# by categoryId. Kept narrow on purpose: fewer events fetched, fewer
# moving parts during the initial port.
SYNC_CATEGORY_IDS = {1}

# NetSec's own Indico category. Standalone NetSec events (training
# schools, policy workshops, MC plenaries, the Summer School) live
# here. Jointly-run EISS × NetSec events (the ESSC) instead live in an
# EISS category, e.g. Annual Conferences (#1), and signal their NetSec
# co-hosting with the `NetSec` keyword — Indico allows only one
# category label per event, so a conference that already carries the
# "Annual Conference" label uses the keyword to opt onto the NetSec
# calendar. The two signals together let the site advertise standalone
# and joint events while excluding EISS-only ones.
NETSEC_CATEGORY_ID = 8
NETSEC_KEYWORD = "netsec"

LOOK_AHEAD_DAYS = 540  # ~18 months — long enough to capture ESSC N+1

# Indico API token (read-only, on a dedicated service account shared
# with the EISS sync). Only used on the newer `/api/*` endpoints —
# Indico's legacy `/export/*` API rejects Bearer auth with 400 on
# some versions, so call sites must opt in via
# `_get(url, authenticate=True)`. The token is detected here so the
# startup mode banner confirms in CI logs that the secret is wired.
# Storage: GitHub Actions secret named `INDICO_API_TOKEN`. NEVER
# hardcode the token in source.
INDICO_API_TOKEN = os.environ.get("INDICO_API_TOKEN")

# Abstracts on Indico run to ~2000 chars. The grid only needs a
# teaser; the full text is one click away via the contribution URL.
ABSTRACT_TEASER_CHARS = 360

# Slot types we deliberately surface in the programme grid. Anything
# else (Indico has "Note", "Material" etc.) is filtered out.
PROGRAMME_SLOT_ENTRY_TYPES = {"Session", "Contribution", "Break"}

# Title prefixes that override `entryType=Session` into a more
# specific subtype on the rendered card. Roundtable: convention is
# the only one used at the moment.
TITLE_PREFIX_FALLBACKS = {"Roundtable:": "roundtable"}


# ──────────────────────────── HTTP ────────────────────────────


def _get(url: str, *, authenticate: bool = False) -> requests.Response:
    """One-stop HTTP GET. Adds the bearer token only when explicitly
    requested via `authenticate=True`, because Indico has two parallel
    APIs that disagree about auth headers:

      - legacy `/export/*` endpoints (everything this script currently
        hits) accept anonymous access, OR an `?apikey=…` query
        parameter. They reject `Authorization: Bearer …` with a 400
        on some Indico versions.
      - newer `/api/*` endpoints accept Bearer tokens and require
        them for protected resources.

    Default `authenticate=False` keeps every call site anonymous —
    which is what `/export/*` needs. The token is NEVER logged.
    """
    headers = {"Accept": "application/json"}
    if authenticate and INDICO_API_TOKEN:
        headers["Authorization"] = f"Bearer {INDICO_API_TOKEN}"
    return requests.get(url, timeout=30, headers=headers)


# ──────────────────────────── helpers ────────────────────────────


def _combine_indico_datetime(d: dict) -> str | None:
    """Indico returns {date: 'YYYY-MM-DD', time: 'HH:MM:SS', tz: 'Europe/Paris'}.
    Combine into a plain ISO-8601 string. We deliberately drop the
    timezone offset — consumers do lexicographic comparisons only, so
    events sharing a TZ assumption sort correctly. The original TZ is
    preserved on the parent event under `startTz`."""
    if not d:
        return None
    date = d.get("date")
    time = d.get("time") or "00:00:00"
    if not date:
        return None
    return f"{date}T{time}"


def _strip_html(s: str) -> str:
    """Crude HTML → text. Indico's description fields contain inline
    formatting (<p>, <em>, <a>) which we don't want to display
    verbatim. We keep the text content; the template can render it
    as a plain paragraph."""
    if not s:
        return ""
    no_tags = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", no_tags).strip()


def _normalise_person(p: dict) -> dict:
    """Strip Indico-internal fields from a person dict (presenter,
    convener, author). Notably drops `emailHash` — a Gravatar
    tracking surface we don't need on the NetSec site, and which
    isn't covered by the public-page disclosure that everything else
    in this script mirrors."""
    return {
        "name": p.get("name") or p.get("fullName") or "",
        "affiliation": p.get("affiliation") or "",
    }


def _person_key(p: dict) -> str:
    """Identity key for de-duplicating a person across Indico's
    speakers / primaryauthors / coauthors lists (Indico repeats the
    same human in more than one). Matches on the normalised display
    name: lower-cased, whitespace-collapsed."""
    name = p.get("name") or p.get("fullName") or ""
    return re.sub(r"\s+", " ", name).strip().lower()


def _people_with_speaker_flags(presenters: list, authors: list) -> list[dict]:
    """Build the full author byline for a contribution, flagging who
    actually presents.

    Indico keeps presenters and (co-)authors in separate lists. The
    timetable export uses `presenters` + `authors` (where `authors`
    holds the non-presenting co-authors); the contributions export
    uses `speakers` + `primaryauthors`/`coauthors`. Either way the
    site used to show only presenters, so multi-author papers
    under-listed their co-authors versus the printed programme.

    We emit presenters first (each `speaker: true`), then any author
    who isn't already a presenter (`speaker: false`), de-duped by
    normalised name. The renderer marks presenters with a mic only
    when a paper actually mixes the two, so single-author talks stay
    clean."""
    speaker_keys = {k for k in (_person_key(p) for p in presenters) if k}
    ordered: list = []
    seen: set = set()
    for p in list(presenters) + list(authors):
        k = _person_key(p)
        if not k or k in seen:
            continue
        seen.add(k)
        ordered.append(p)
    out = []
    for p in ordered:
        person = _normalise_person(p)
        person["speaker"] = _person_key(p) in speaker_keys
        out.append(person)
    return out


def _absolutize_indico_url(url: str) -> str:
    """Indico's timetable export is inconsistent: session URLs come
    back absolute (https://…), contribution URLs come back relative
    (/event/22/contributions/521/). Browsers resolve the latter
    against the NetSec domain, so the link would 404. Fix by
    prepending INDICO_BASE for any relative path."""
    if not url:
        return ""
    if url.startswith(("http://", "https://")):
        return url
    return f"{INDICO_BASE}{url}" if url.startswith("/") else f"{INDICO_BASE}/{url}"


def _looks_like_break(title: str) -> bool:
    """Indico inconsistently marks coffee breaks: morning registration
    coffee comes through as entryType=Break, but mid-day coffee breaks
    are entryType=Session with no inner contributions. Recognise the
    latter by title so the grid renders them in the quiet "break"
    style rather than as full session cards."""
    t = (title or "").strip().lower()
    return t.startswith("coffee") or t.startswith("tea break") or t == "lunch"


def _canonical_room(room: str) -> str:
    """Collapse the cosmetic differences between equivalent room
    labels so the sort key treats them as one column. ESSC organisers
    sometimes enter "Lecture Hall 8" and sometimes "D House, Lecture
    Hall 8" for the same physical room; we strip a leading "D House,"
    or similar building prefix, normalise whitespace + case, so both
    forms collapse to the same key. The full original label still
    renders on the card; only the sort key is canonicalised."""
    s = (room or "").strip().lower()
    if not s:
        return ""
    # Common building prefixes ESSC + sibling Indico events use. Add
    # to this list when a new venue ships with its own prefix style.
    for prefix in ("d house,", "building,", "venue,"):
        if s.startswith(prefix):
            s = s[len(prefix):].lstrip()
    return " ".join(s.split())


def _room_sort_key(slot: dict) -> tuple:
    """Sort key for parallel-row items so same-room panels stack
    vertically across the day. Slots with no room sink to the end
    (empty canonical room → ('~', '')), so they don't displace the
    room-bearing columns."""
    room = _canonical_room(slot.get("room", ""))
    return ("~", "") if not room else ("", room)


# ──────────────────────────── normalise ────────────────────────────


def normalise_event(event: dict) -> dict:
    """Strip Indico-internal fields, return only what the consumer
    needs. Defensive against schema drift — anything missing degrades
    to "" or None rather than crashing the sync."""
    return {
        "id": str(event.get("id", "")),
        "title": event.get("title", "(untitled)"),
        "category": event.get("category", ""),
        "categoryId": event.get("categoryId"),
        "start": _combine_indico_datetime(event.get("startDate") or {}),
        "end": _combine_indico_datetime(event.get("endDate") or {}),
        "startTz": (event.get("startDate") or {}).get("tz", ""),
        "startDateOnly": (event.get("startDate") or {}).get("date", ""),
        "endDateOnly": (event.get("endDate") or {}).get("date", ""),
        "location": event.get("location", ""),
        "room": event.get("room", ""),
        "url": event.get("url", ""),
        "type": event.get("type", ""),
        # Lower-cased keyword list, used to spot the "NetSec" co-host
        # marker on EISS-category events. Indico returns these as a flat
        # list of strings; absent → [].
        "keywords": [
            str(k).strip().lower() for k in (event.get("keywords") or []) if str(k).strip()
        ],
    }


def classify_netsec(norm: dict) -> "str | None":
    """Decide whether a normalised Indico event belongs on the NetSec
    calendar, and how.

      - "standalone" — the event lives in NetSec's own category (#8):
        a training school, policy workshop, MC plenary, etc.
      - "joint" — the event lives in another (EISS) category but carries
        the "NetSec" keyword: a jointly-run event such as the ESSC.
      - None — an EISS-only event that NetSec does not advertise.

    The NetSec category wins over the keyword: an event physically in
    #8 is standalone even if someone also tagged it, so the badge
    reflects where the event actually lives.
    """
    if norm.get("categoryId") == NETSEC_CATEGORY_ID:
        return "standalone"
    if NETSEC_KEYWORD in (norm.get("keywords") or []):
        return "joint"
    return None


def _normalise_contribution(c: dict) -> dict:
    """Turn an Indico contribution (a single paper / talk) into a
    compact dict. Authors include both `presenters` (who actually
    talks) and `primaryauthors` as fallback."""
    start = c.get("startDate") or {}
    end = c.get("endDate") or {}
    presenters_src = c.get("presenters") or c.get("speakers") or []
    # Timetable export exposes non-presenting co-authors as `authors`;
    # the contributions export splits them into primaryauthors+coauthors.
    authors_src = (
        c["authors"] if c.get("authors") is not None
        else (c.get("primaryauthors") or []) + (c.get("coauthors") or [])
    )
    abstract = _strip_html(c.get("description") or "")
    teaser = abstract[:ABSTRACT_TEASER_CHARS]
    if len(abstract) > ABSTRACT_TEASER_CHARS:
        # Trim back to the previous word boundary so we don't slice
        # mid-word, then append an ellipsis.
        teaser = teaser.rsplit(" ", 1)[0] + "…"
    has_full = len(abstract) > len(teaser)
    return {
        "title": c.get("title") or "(untitled contribution)",
        "startTime": (start.get("time") or "")[:5],
        "endTime": (end.get("time") or "")[:5],
        # Full author byline with a `speaker` flag per person, so the
        # renderer can list non-presenting co-authors (which the
        # printed programme shows) and still mark who presents.
        "people": _people_with_speaker_flags(presenters_src, authors_src),
        # `abstract` is the truncated teaser kept for the initial,
        # collapsed render. `fullAbstract` carries the un-truncated
        # plain text and is non-empty only when there's more to show
        # than the teaser; the renderer swaps it in when the visitor
        # clicks "Read full abstract", so the full text reaches the
        # reader without an offsite hop. Indico stays the canonical
        # source via the contribution `url`.
        "abstract": teaser,
        "fullAbstract": abstract if has_full else "",
        "hasFullAbstract": has_full,
        "url": _absolutize_indico_url(c.get("url") or ""),
    }


# ──────────────────────────── fetch + extract ────────────────────────────


def fetch_category_events(cat_id: int) -> list[dict]:
    """GET one Indico category's event list. Lookahead is ~18 months,
    ordering by start time, detail=events gives the full event shape.
    Raises on a non-200 or an unexpected payload shape — the caller
    decides whether that is fatal (the Annual-Conference fetch) or a
    soft miss (the NetSec-category fetch)."""
    today = dt.date.today()
    to_date = today + dt.timedelta(days=LOOK_AHEAD_DAYS)
    url = (
        f"{INDICO_BASE}/export/categ/{cat_id}.json"
        f"?from={today.isoformat()}&to={to_date.isoformat()}"
        f"&detail=events&order=start"
    )
    print(f"GET {url}", file=sys.stderr)
    r = _get(url)
    r.raise_for_status()
    payload = r.json()
    if payload.get("_type") != "HTTPAPIResult":
        sys.exit(
            f"Unexpected payload shape from Indico: top-level _type is "
            f"{payload.get('_type')!r}, expected 'HTTPAPIResult'"
        )
    return payload.get("results", []) or []


def fetch_events() -> list[dict]:
    """Hit the Annual Conferences category and return the raw event
    list. A network failure or non-200 here aborts the sync (the
    workflow treats it as a soft fail and keeps the last good data)."""
    return fetch_category_events(next(iter(SYNC_CATEGORY_IDS)))


def build_netsec_index(annual_raw: list[dict]) -> dict:
    """Build the id-keyed map of NetSec-relevant events feeding
    events.json. Combines the already-fetched Annual-Conference events
    (where joint events are detected by the NetSec keyword) with a
    fresh fetch of NetSec's own category (#8, the standalone events).

    The NetSec-category fetch is best-effort: if it errors, joint
    events are still detected from the Annual-Conference set, so a
    co-host badge never disappears just because #8 was briefly
    unreachable. Each kept value is the normalised event with a
    `coHost` field ('standalone' | 'joint') already attached."""
    raw = list(annual_raw)
    try:
        netsec_raw = fetch_category_events(NETSEC_CATEGORY_ID)
        print(
            f"Fetched {len(netsec_raw)} event(s) from NetSec category "
            f"#{NETSEC_CATEGORY_ID}",
            file=sys.stderr,
        )
        raw += netsec_raw
    except Exception as exc:  # noqa: BLE001 — discovery is best-effort
        print(
            f"  ! NetSec category #{NETSEC_CATEGORY_ID} fetch failed: {exc}. "
            "Joint events are still detected from the Annual-Conference set.",
            file=sys.stderr,
        )

    index: dict = {}
    for ev in raw:
        norm = normalise_event(ev)
        cls = classify_netsec(norm)
        if cls is None or not norm.get("id"):
            continue
        norm["coHost"] = cls
        index[str(norm["id"])] = norm
    return index


def fetch_timetable(event_id: str) -> dict:
    """Pull the public timetable for one event. Returns the raw
    Indico results-dict (keyed by event id, then by YYYYMMDD day) or
    an empty dict if anything goes wrong — a missing timetable must
    never abort the wider sync."""
    url = f"{INDICO_BASE}/export/timetable/{event_id}.json"
    print(f"GET {url}", file=sys.stderr)
    try:
        r = _get(url)
        r.raise_for_status()
        payload = r.json()
    except Exception as exc:  # noqa: BLE001 — sync is best-effort
        print(f"  ! timetable fetch failed: {exc}", file=sys.stderr)
        return {}
    return payload.get("results", {}) or {}


def extract_programme(timetable_results: dict, event_id: str) -> dict:
    """Turn the full Indico timetable into a normalised programme
    structure: days → rows → (per-session) contributions.

    Top-level shape consumed by the renderer:

        {
          "days": [
            { "date": "2026-06-11", "label": "Day 1",
              "rows": [
                { "startTime": "09:00", "endTime": "10:30",
                  "parallel": false, "items": [ <slot dict>, ... ] },
                ...
              ],
              "slots": [ ... ungrouped, kept for debugging ... ]
            },
            ...
          ]
        }

    A slot is one of:
      - kind="session"      — chaired panel / roundtable / plenary,
                              with conveners[], discussants[],
                              contributions[]
      - kind="contribution" — standalone, with speakers[] + abstract
      - kind="break"        — coffee / lunch / reception, rendered
                              quietly

    PII surface: bounded to names + affiliations. emailHash dropped,
    internal db_ids dropped. We mirror Indico's public disclosure
    decision; we don't widen it.
    """
    days: list[dict] = []
    event_block = timetable_results.get(str(event_id), {})

    for idx, day_key in enumerate(sorted(event_block.keys()), start=1):
        day_block = event_block[day_key]
        if not isinstance(day_block, dict):
            continue
        date_str = f"{day_key[:4]}-{day_key[4:6]}-{day_key[6:8]}"
        slots: list[dict] = []

        for slot_id, slot in day_block.items():
            if not isinstance(slot, dict):
                continue
            entry_type = slot.get("entryType")
            if entry_type not in PROGRAMME_SLOT_ENTRY_TYPES:
                continue

            start = slot.get("startDate") or {}
            end = slot.get("endDate") or {}
            raw_slot_title = slot.get("title") or slot.get("slotTitle") or ""

            # Strip the "Roundtable:" prefix from the displayed title —
            # the `subtype` field below conveys the type so the prefix
            # is redundant noise on the card.
            display_title = raw_slot_title
            for prefix in TITLE_PREFIX_FALLBACKS:
                if display_title.startswith(prefix):
                    display_title = display_title[len(prefix):].strip()
                    break

            # `inheritRoom` / `inheritLoc` come straight from Indico
            # and let the renderer tell apart "this slot was given an
            # explicit room" from "this slot fell back to the event
            # default". Coffee breaks and lunches can carry distinct
            # locations too, so both flags surface for every slot
            # type, not just sessions.
            base = {
                "id": str(slot.get("id", slot_id)),
                "title": display_title,
                "startTime": (start.get("time") or "")[:5],
                "endTime": (end.get("time") or "")[:5],
                "room": slot.get("room") or "",
                "location": slot.get("location") or "",
                "inheritRoom": bool(slot.get("inheritRoom", True)),
                "inheritLoc": bool(slot.get("inheritLoc", True)),
                "url": _absolutize_indico_url(slot.get("url") or ""),
            }

            if entry_type == "Session":
                inner_entries = slot.get("entries") or {}

                # Some "coffee breaks" come through as Session with
                # no inner contributions. Reclassify them as breaks
                # so the grid renders them quietly rather than as
                # a 0-paper panel.
                if not inner_entries and _looks_like_break(raw_slot_title):
                    slots.append({**base, "kind": "break"})
                    continue

                contribs = [
                    _normalise_contribution(c)
                    for c in inner_entries.values()
                    if isinstance(c, dict) and c.get("entryType") == "Contribution"
                ]
                contribs.sort(key=lambda c: c["startTime"])

                # Classify subtype from sessionCode + title-prefix.
                # Drives the renderer's decision to hide the
                # "View papers" expander on roundtables (which carry
                # a single placeholder "Contributors" entry, not
                # real papers) and on plenaries.
                code = (slot.get("sessionCode") or "").strip()
                subtype: str | None = None
                if code == "RT" or raw_slot_title.startswith("Roundtable:"):
                    subtype = "roundtable"
                elif code in {"INTRO", "KEY", "CONC"}:
                    subtype = "plenary"

                # For roundtables, flatten the single "Contributors"
                # placeholder into a top-level discussants list.
                # That's the useful info on the card; the placeholder
                # itself doesn't add anything.
                discussants: list[dict] = []
                if subtype == "roundtable" and len(contribs) == 1:
                    discussants = contribs[0]["people"]
                    contribs = []  # suppress the expander entirely

                slots.append({
                    **base,
                    "kind": "session",
                    "subtype": subtype,
                    "slotTitle": slot.get("slotTitle") or "",
                    "sessionCode": code,
                    "conveners": [
                        _normalise_person(c) for c in slot.get("conveners") or []
                    ],
                    "discussants": discussants,
                    "contributions": contribs,
                })
            elif entry_type == "Contribution":
                speakers_src = (
                    slot.get("presenters") or slot.get("speakers") or []
                )
                slots.append({
                    **base,
                    "kind": "contribution",
                    "speakers": [_normalise_person(p) for p in speakers_src],
                    "abstract": _strip_html(slot.get("description") or "")[
                        :ABSTRACT_TEASER_CHARS
                    ],
                })
            else:  # Break
                slots.append({**base, "kind": "break"})

        slots.sort(key=lambda s: s["startTime"])

        # Group consecutive slots that share a startTime into "rows".
        # Two panels happening in parallel (same start time, different
        # rooms) get rendered side-by-side; solo slots get a full-
        # width row. Breaks always sit on their own row.
        rows: list[dict] = []
        i = 0
        while i < len(slots):
            current = slots[i]
            if current["kind"] == "break":
                rows.append({
                    "startTime": current["startTime"],
                    "endTime": current["endTime"],
                    "parallel": False,
                    "items": [current],
                })
                i += 1
                continue
            # Greedy-collect every following non-break slot with the
            # same startTime into a parallel row.
            group = [current]
            j = i + 1
            while (
                j < len(slots)
                and slots[j]["kind"] != "break"
                and slots[j]["startTime"] == current["startTime"]
            ):
                group.append(slots[j])
                j += 1
            row_end = max(s["endTime"] for s in group)
            # Sort parallel-row items by a normalised room key so the
            # same room consistently lands in the same column across
            # rows of the day. Indico itself orders parallel panels
            # by submission / convener id, so without this the same
            # room can jump left → right between two time slots,
            # which breaks the "stay in your seat for the next panel
            # in this room" reading. Slots with no room sink to the
            # end so they don't displace the room-bearing columns.
            group.sort(key=_room_sort_key)
            rows.append({
                "startTime": current["startTime"],
                "endTime": row_end,
                "parallel": len(group) > 1,
                "items": group,
            })
            i = j

        days.append({
            "date": date_str,
            "label": f"Day {idx}",
            "rows": rows,
            "slots": slots,  # ungrouped — kept for debugging
        })

    return {"days": days}


# ──────────────────────────── main ────────────────────────────


_MONTHS_EN = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _en_display_date(start: str, end: str) -> str:
    """Human-readable EN date range from two ISO stamps. Mirrors the
    hand-written `displayDate.en` style already in events.json
    ('9–11 June 2026', '4 September 2026', '30 June – 2 July 2026').
    Returns '' if start can't be parsed. FR/DE are left to the
    maintainer (no machine translation, CLAUDE.md §1) — the renderer
    falls back to the EN string until they are filled in."""
    def parse(s: str):
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s or "")
        return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None

    a = parse(start)
    if not a:
        return ""
    b = parse(end) or a
    ay, am, ad = a
    by, bm, bd = b
    if (ay, am, ad) == (by, bm, bd):
        return f"{ad} {_MONTHS_EN[am - 1]} {ay}"
    if ay == by and am == bm:
        return f"{ad}–{bd} {_MONTHS_EN[am - 1]} {ay}"
    if ay == by:
        return f"{ad} {_MONTHS_EN[am - 1]} – {bd} {_MONTHS_EN[bm - 1]} {ay}"
    return (
        f"{ad} {_MONTHS_EN[am - 1]} {ay} – "
        f"{bd} {_MONTHS_EN[bm - 1]} {by}"
    )


def _event_type_for(title: str) -> str:
    """Best-effort eventType for a discovered NetSec event, keyed off
    its title so the renderer's type filter + pill land on a known
    label where possible. Falls back to the generic 'event' (which the
    renderers localise via their I18N `type` maps)."""
    t = (title or "").lower()
    if "summer school" in t or "training school" in t or "training" in t:
        return "training-school"
    if "workshop" in t:
        return "policy-workshop"
    if "itc" in t:
        return "itc-conference"
    if "plenary" in t or "management committee" in t:
        return "mc-plenary"
    if "conference" in t:
        return "annual-conference"
    return "event"


def _discovered_entry(norm: dict) -> dict:
    """Build a minimal but schema-valid events.json entry from a
    normalised Indico event newly discovered on the NetSec calendar.

    Only EN copy is synthesised (from the Indico title + URL); the
    renderers fall back to EN for FR/DE, and the `autoDiscovered` flag
    flags the entry for a maintainer to enrich by hand (richer
    description, hand-translated FR/DE, working groups). The entry
    carries `indicoEventId` so subsequent syncs keep its summary/dates
    in step, exactly like the hand-authored ESSC entry."""
    eid = norm.get("id")
    title = norm.get("title") or "(untitled)"
    start = (norm.get("start") or "")[:16]
    end = (norm.get("end") or "")[:16] or start
    url = norm.get("url") or "https://netsec-cost.eu/events.html"
    cats = ["NetSec"]
    cat_name = (norm.get("category") or "").strip()
    if cat_name and cat_name not in cats and cat_name.lower() != "netsec":
        cats.insert(0, cat_name)
    return {
        "uid": f"indico-{eid}@netsec-cost.eu",
        "indicoEventId": int(eid) if str(eid).isdigit() else eid,
        "summary": title,
        "description": f"{title}. Details and registration on Indico: {url}",
        "location": norm.get("location") or "To be confirmed",
        "url": url,
        "start": start,
        "end": end,
        "categories": cats,
        "status": "CONFIRMED",
        "eventType": _event_type_for(title),
        "coHost": norm.get("coHost", "standalone"),
        "autoDiscovered": True,
        "featured": False,
        "displayDate": {"en": _en_display_date(start, end)},
        "cardTitle": {"en": title},
        "cardDescription": {
            "en": f"{title}. Full details and registration are on Indico."
        },
        "cta": {
            "href": url,
            "external": True,
            "i18n": {
                "en": "Details on Indico →",
                "fr": "Détails sur Indico →",
                "de": "Details auf Indico →",
            },
        },
    }


def _patch_events_json(netsec_by_id: dict) -> bool:
    """Refresh and grow data/events.json from the NetSec Indico feed.

    `data/events.json` is the authoritative source for calendar.ics and
    the home-page + Events-page cards. Most of its fields are
    hand-curated (richer descriptions, full postal addresses, FR/DE
    copy) and must stay that way. This step does three things against
    the freshly-built NetSec index (`netsec_by_id`, keyed by Indico
    event id, each value carrying a `coHost` classification):

      1. For every entry that opts in via `indicoEventId`, overwrite the
         allow-listed fields in `EVENTS_JSON_SYNCED_FIELDS` (summary,
         start, end) and refresh the derived `coHost` marker. Curated
         fields (location, descriptions, working groups) are untouched.
      2. Append any NetSec-relevant Indico event not already present, as
         a minimal `autoDiscovered` entry, so a new standalone event on
         category #8 shows up without hand-editing. Hand-authored events
         with no `indicoEventId` (e.g. the ITC conference) are left
         exactly as they are.
      3. Returns True when anything changed, so the caller knows whether
         to rebuild calendar.ics.

    Why `location` is NOT in the allow-list: events.json carries the
    full street address (`Stockholm University, Frescativägen,
    114 19 Stockholm, Sweden`) while Indico returns the short venue
    name (`Stockholm University`). Auto-overwriting would lose the
    curated postal detail."""
    if not EVENTS_OUT.exists():
        return False
    try:
        events_doc = json.loads(EVENTS_OUT.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"  ! cannot read {EVENTS_OUT.name}: {exc}", file=sys.stderr)
        return False

    by_id = {str(k): v for k, v in netsec_by_id.items()}

    changed = False
    linked_ids: set = set()
    for entry in events_doc.get("events", []):
        indico_id = entry.get("indicoEventId")
        if indico_id is None:
            continue
        linked_ids.add(str(indico_id))
        source = by_id.get(str(indico_id))
        if source is None:
            print(
                f"  ! events.json entry {entry.get('uid', '?')!r} has "
                f"indicoEventId={indico_id} but no matching event was "
                f"fetched this run. Skipping (the maintainer may have "
                f"removed the event from Indico).",
                file=sys.stderr,
            )
            continue

        # Map the small set of fields. Indico timestamps come with
        # seconds (`2026-06-11T08:00:00`); events.json convention is
        # minute-precision (`2026-06-11T08:00`), so trim.
        patch = {
            "summary": source.get("title", ""),
            "start": (source.get("start") or "")[:16],
            "end": (source.get("end") or "")[:16],
        }
        for field in EVENTS_JSON_SYNCED_FIELDS:
            new = patch.get(field)
            if new and entry.get(field) != new:
                print(
                    f"  • events.json[{entry.get('uid')}] {field}: "
                    f"{entry.get(field)!r} → {new!r}",
                    file=sys.stderr,
                )
                entry[field] = new
                changed = True

        # Refresh the derived co-host marker (joint vs standalone) from
        # the live keyword/category signal, so toggling the NetSec
        # keyword on Indico flips the badge on the next sync.
        new_cohost = source.get("coHost")
        if new_cohost and entry.get("coHost") != new_cohost:
            print(
                f"  • events.json[{entry.get('uid')}] coHost: "
                f"{entry.get('coHost')!r} → {new_cohost!r}",
                file=sys.stderr,
            )
            entry["coHost"] = new_cohost
            changed = True

    # Append newly-discovered NetSec events (present in the feed, absent
    # from events.json). Sorted by id for a deterministic diff.
    for eid in sorted(set(by_id) - linked_ids, key=lambda s: (len(s), s)):
        entry = _discovered_entry(by_id[eid])
        events_doc.setdefault("events", []).append(entry)
        print(
            f"  + events.json: discovered {entry['coHost']} event "
            f"{entry['summary']!r} (Indico #{eid}) — added as autoDiscovered.",
            file=sys.stderr,
        )
        changed = True

    if not changed:
        return False

    # Bump dtstamp so calendar.ics build picks up a fresh modified
    # timestamp. Format follows the existing convention in the file
    # (`YYYYMMDDTHHMMSSZ`, UTC).
    events_doc["dtstamp"] = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    EVENTS_OUT.write_text(
        json.dumps(events_doc, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"  Patched {EVENTS_OUT.name} from Indico (allow-list).", file=sys.stderr)
    return True


def _regenerate_calendar() -> None:
    """Invoke scripts/build-calendar.py so calendar.ics stays in step
    with the freshly-patched events.json. Run as a subprocess (rather
    than imported as a module) so the build script's exit code and
    logs surface cleanly into the workflow output. A non-zero exit
    here aborts the sync so the workflow doesn't ship a half-updated
    state."""
    import subprocess
    cal_script = ROOT / "scripts" / "build-calendar.py"
    print(f"  Regenerating calendar.ics …", file=sys.stderr)
    result = subprocess.run(
        ["python3", str(cal_script)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.stdout:
        print(result.stdout, file=sys.stderr, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    if result.returncode != 0:
        sys.exit(
            f"build-calendar.py exited with {result.returncode}; "
            f"aborting sync so the PR doesn't ship a half-updated state."
        )


def _flatten_programme(conf: dict) -> dict:
    """Map a conference's programme to {item-id: compact-summary} for
    diffing. Items are sessions / breaks (the row entries); each
    session carries its contributions keyed by title, with the author
    byline as the value so author changes surface too."""
    out: dict[str, dict] = {}
    prog = (conf or {}).get("programme") or {}
    for day in prog.get("days", []):
        dlabel = day.get("date") or day.get("label") or ""
        for row in day.get("rows", []):
            for it in row.get("items", []):
                iid = it.get("id") or f"{dlabel}|{it.get('startTime')}|{it.get('title')}"
                out[iid] = {
                    "day": dlabel,
                    "title": it.get("title") or "",
                    "start": it.get("startTime") or "",
                    "end": it.get("endTime") or "",
                    "room": it.get("room") or "",
                    "kind": it.get("kind") or "",
                    "contribs": {
                        (c.get("title") or ""): ", ".join(
                            p.get("name") or ""
                            for p in (c.get("people") or c.get("speakers") or [])
                        )
                        for c in (it.get("contributions") or [])
                    },
                }
    return out


def summarise_changes(old: dict | None, new: dict) -> list[str]:
    """Human-readable, markdown change list between two indico.json
    `data` payloads (the `annualConferences` map). Reports event-level
    edits, sessions/breaks added/removed/retimed/renamed/moved-room,
    and per-session papers added/removed plus author-byline changes.
    Returns [] when nothing diffable changed (e.g. a normalisation-only
    delta)."""
    lines: list[str] = []
    old_confs = (old or {}).get("annualConferences", {}) or {}
    new_confs = new.get("annualConferences", {}) or {}
    for year in sorted(set(old_confs) | set(new_confs)):
        oc, nc = old_confs.get(year), new_confs.get(year)
        if oc is None:
            lines.append(f"### {year} — new conference added")
            continue
        if nc is None:
            lines.append(f"### {year} — conference removed")
            continue
        yl: list[str] = []
        for field, label in (
            ("title", "Title"), ("start", "Start date"), ("end", "End date"),
            ("location", "Venue"), ("room", "Default room"),
        ):
            if (oc.get(field) or "") != (nc.get(field) or ""):
                yl.append(f"- **{label}:** “{oc.get(field) or '—'}” → “{nc.get(field) or '—'}”")
        oi, ni = _flatten_programme(oc), _flatten_programme(nc)
        for iid, it in ni.items():
            if iid not in oi:
                room = f", {it['room']}" if it["room"] else ""
                yl.append(
                    f"- **+ Added {it['kind'] or 'item'}:** “{it['title']}” "
                    f"({it['day']} {it['start']}–{it['end']}{room})"
                )
        for iid, it in oi.items():
            if iid not in ni:
                yl.append(
                    f"- **− Removed {it['kind'] or 'item'}:** “{it['title']}” "
                    f"({it['day']} {it['start']}–{it['end']})"
                )
        for iid, b in ni.items():
            a = oi.get(iid)
            if a is None:
                continue
            if a["title"] != b["title"]:
                yl.append(f"- **~ Renamed:** “{a['title']}” → “{b['title']}”")
            if (a["start"], a["end"]) != (b["start"], b["end"]):
                yl.append(
                    f"- **~ Retimed** “{b['title']}”: "
                    f"{a['start']}–{a['end']} → {b['start']}–{b['end']}"
                )
            if a["room"] != b["room"]:
                yl.append(f"- **~ Room** “{b['title']}”: “{a['room'] or '—'}” → “{b['room'] or '—'}”")
            for ct in b["contribs"]:
                if ct not in a["contribs"]:
                    yl.append(f"  - **+ Paper** added to “{b['title']}”: “{ct}”")
            for ct in a["contribs"]:
                if ct not in b["contribs"]:
                    yl.append(f"  - **− Paper** removed from “{b['title']}”: “{ct}”")
            for ct, authors in b["contribs"].items():
                if ct in a["contribs"] and a["contribs"][ct] != authors:
                    yl.append(
                        f"  - **~ Authors** on “{ct}”: "
                        f"{a['contribs'][ct] or '—'} → {authors or '—'}"
                    )
        if yl:
            lines.append(f"### {year}")
            lines.extend(yl)
    return lines


def should_carry_over(annual_by_year: dict, existing_data: "dict | None") -> bool:
    """Decide whether to keep the snapshot on disk instead of writing the
    freshly-fetched data.

    True only when the fetch returned no conferences AND the existing
    snapshot still has some: the conference has ended and dropped out of
    Indico's window, so writing the empty result would erase the
    programme. False on a normal first run (no prior data) and whenever
    the fetch actually returned conferences. A network failure never
    reaches here (fetch_events exits first)."""
    return bool(
        not annual_by_year
        and existing_data
        and existing_data.get("annualConferences")
    )


def main() -> None:
    mode = "authenticated" if INDICO_API_TOKEN else "anonymous"
    print(f"Indico sync running in {mode} mode", file=sys.stderr)

    raw_events = fetch_events()
    print(f"Fetched {len(raw_events)} event(s) from Indico", file=sys.stderr)

    # Bucket by year. If multiple events exist for the same year
    # (e.g. a prep meeting AND the main conference), keep the latest-
    # starting one — the main conference usually starts later than
    # scaffolding events.
    annual_by_year: dict[str, dict] = {}
    for ev in raw_events:
        norm = normalise_event(ev)
        if norm["categoryId"] not in SYNC_CATEGORY_IDS:
            # Defensive — categ/{id} should only return events from
            # that category, but skip anything unexpected.
            continue
        year = (norm["startDateOnly"] or "")[:4]
        if not year:
            continue
        existing = annual_by_year.get(year)
        if existing is None or (norm["start"] or "") > (existing["start"] or ""):
            annual_by_year[year] = norm

    # Enrich each year with its timetable-derived programme. One
    # extra HTTP call per ESSC year — currently 1 (ESSC 26).
    for year, event in annual_by_year.items():
        tt = fetch_timetable(event["id"])
        event["programme"] = extract_programme(tt, event["id"])
        day_count = len(event["programme"]["days"])
        slot_count = sum(len(d["slots"]) for d in event["programme"]["days"])
        print(
            f"  {year}: programme has {day_count} day(s), "
            f"{slot_count} slot(s) (sessions + contributions + breaks)",
            file=sys.stderr,
        )

    # Build the payload twice-shaped: the data half (everything the
    # consumer reads) and the metadata half (timestamps, doc string).
    # The substantive-change check compares only the data half, so a
    # quiet day doesn't dirty the working tree just because the
    # `syncedAt` clock advanced. Same pattern as scripts/sync-bios.py
    # uses for `generated_at` — see PR #117 for the canonical fix.
    data_payload = {
        "source": f"{INDICO_BASE}/export/categ/{next(iter(SYNC_CATEGORY_IDS))}.json",
        "lookaheadDays": LOOK_AHEAD_DAYS,
        "annualConferences": annual_by_year,
    }

    # Read the existing file's data half (if any) for comparison.
    existing_data: dict | None = None
    if OUT.exists():
        try:
            existing = json.loads(OUT.read_text(encoding="utf-8"))
            existing_data = {
                "source": existing.get("source"),
                "lookaheadDays": existing.get("lookaheadDays"),
                "annualConferences": existing.get("annualConferences", {}),
            }
        except (json.JSONDecodeError, OSError):
            existing_data = None  # malformed → treat as no prior state

    # Post-conference carry-over. A network failure already exits early
    # (fetch_events), but a *successful* fetch that returns no events —
    # the ESSC edition has ended and dropped out of Indico's category
    # window — yields an empty annualConferences. Writing that would
    # erase the programme from the conference page and open a daily PR
    # that the data-shape guard (annualConferences must be non-empty)
    # correctly rejects. So when the fetch is empty but the snapshot on
    # disk still has the programme, keep the snapshot: the same posture
    # as an API outage. It preserves the programme as a post-conference
    # archive and self-heals when next year's edition appears on Indico.
    if should_carry_over(annual_by_year, existing_data):
        print(
            "Indico returned no conferences, but data/indico.json holds "
            f"{len(existing_data['annualConferences'])}; keeping the existing "
            "snapshot (post-conference carry-over).",
            file=sys.stderr,
        )
        return

    # Patch hand-curated companion files (events.json + calendar.ics)
    # BEFORE the early-return below: a quiet Indico day doesn't mean
    # events.json is in sync. If a maintainer edited events.json by
    # hand last week, this is the run that catches them up. The patch
    # is a no-op when nothing changed, so quiet days stay quiet.
    # Build the NetSec-calendar index (standalone events from category
    # #8 + joint events detected by the NetSec keyword on the
    # Annual-Conference set) and reconcile events.json against it:
    # refresh linked entries, append newly-discovered ones.
    netsec_by_id = build_netsec_index(raw_events)
    if _patch_events_json(netsec_by_id):
        _regenerate_calendar()

    if existing_data == data_payload:
        print(
            "No substantive change — leaving data/indico.json untouched "
            f"(last sync recorded: "
            f"{json.loads(OUT.read_text(encoding='utf-8')).get('syncedAt', 'unknown')}).",
            file=sys.stderr,
        )
        return

    # Substance changed. Emit a human-readable change summary to STDOUT
    # (the workflow captures stdout into the PR body); operational logs
    # stay on stderr. This is what tells the maintainer *precisely*
    # what moved between syncs rather than "something changed".
    change_lines = summarise_changes(existing_data, data_payload)
    if change_lines:
        print("\n".join(change_lines))
    else:
        print(
            "_Data changed at the structural level (normalisation or "
            "metadata) with no session- or paper-level difference detected._"
        )

    # Substance changed — write with a fresh syncedAt.
    output = {
        "_documentation": (
            f"Read-only snapshot of NetSec events on the EISS Indico "
            f"({INDICO_BASE}). Generated by scripts/sync-indico.py, run "
            f"daily by .github/workflows/sync-indico.yml. DO NOT EDIT BY "
            f"HAND — the next sync will overwrite. `annualConferences` is "
            f"a year-keyed map of ESSC editions; each entry carries event "
            f"metadata (title, dates, venue, URL) plus a `programme.days` "
            f"structure consumed by the (still-to-build) live programme "
            f"grid on the conference page. Schema mirrors EISS's "
            f"indico.json for cross-site renderer compatibility — see "
            f"https://github.com/EISSeuropa/EISSeuropa.github.io/blob/master/docs/indico-programme-integration.md."
        ),
        "syncedAt": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **data_payload,
    }
    serialised = json.dumps(output, indent=2, ensure_ascii=False) + "\n"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(serialised, encoding="utf-8")
    print(
        f"Wrote {OUT.relative_to(ROOT)} — "
        f"{len(annual_by_year)} Annual Conference page(s) by year: "
        f"{sorted(annual_by_year.keys())}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
