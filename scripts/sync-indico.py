#!/usr/bin/env python3
"""
Sync helper: refresh data/indico.json from the EISS Indico instance.

NetSec uses the same Indico as EISS (https://indico.eiss-europa.com) for
hosting jointly-organised conferences (ESSC 26 onwards) and, in time,
NetSec's own Summer School, training schools, and MC plenaries.

Initial scope: ESSC 26 (event id 22, category 1 "Annual Conferences").

Usage:
    python3 scripts/sync-indico.py

What it does:
  1. GETs https://indico.eiss-europa.com/export/categ/1.json
     (the Annual Conferences category) with `from=today` and
     `to=today+LOOK_AHEAD_DAYS`. Returns the list of upcoming ESSC
     events.
  2. For each event, GETs /export/timetable/{event_id}.json and
     normalises the timetable into a `programme.days[].rows[]`
     structure: day → time-blocks → session cards. Parallel sessions
     (same startTime, different rooms) get grouped into a single
     `parallel` row.
  3. Strips PII surface: Indico publishes emailHashes (Gravatar
     lookups) for every person — we drop them. Internal db_ids /
     person_ids are also dropped. Names + affiliations remain (those
     are already public on Indico's event page; we don't widen
     exposure, we mirror it).
  4. Writes data/indico.json. Idempotent: if the new payload is
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

INDICO_BASE = "https://indico.eiss-europa.com"

# The Indico category we sync. Currently `1` (Annual Conferences) on
# the EISS instance — ESSC editions live here. When NetSec starts
# putting its own events (Summer School, training schools, MC
# plenaries) on the same instance, either add their category ids to
# this set or expand to the root category `0` and bucket the result
# by categoryId. Kept narrow on purpose: fewer events fetched, fewer
# moving parts during the initial port.
SYNC_CATEGORY_IDS = {1}

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
    }


def _normalise_contribution(c: dict) -> dict:
    """Turn an Indico contribution (a single paper / talk) into a
    compact dict. Authors include both `presenters` (who actually
    talks) and `primaryauthors` as fallback."""
    start = c.get("startDate") or {}
    end = c.get("endDate") or {}
    speakers_src = (
        c.get("presenters") or c.get("speakers") or c.get("primaryauthors") or []
    )
    abstract = _strip_html(c.get("description") or "")
    teaser = abstract[:ABSTRACT_TEASER_CHARS]
    if len(abstract) > ABSTRACT_TEASER_CHARS:
        # Trim back to the previous word boundary so we don't slice
        # mid-word, then append an ellipsis.
        teaser = teaser.rsplit(" ", 1)[0] + "…"
    return {
        "title": c.get("title") or "(untitled contribution)",
        "startTime": (start.get("time") or "")[:5],
        "endTime": (end.get("time") or "")[:5],
        "speakers": [_normalise_person(p) for p in speakers_src],
        "abstract": teaser,
        "hasFullAbstract": len(abstract) > len(teaser),
        "url": _absolutize_indico_url(c.get("url") or ""),
    }


# ──────────────────────────── fetch + extract ────────────────────────────


def fetch_events() -> list[dict]:
    """Hit the Annual Conferences category and return the raw event
    list. Defensive: lookahead is ~18 months, ordering is by start
    time, detail=events gives us the full event shape."""
    today = dt.date.today()
    to_date = today + dt.timedelta(days=LOOK_AHEAD_DAYS)
    # If we ever sync multiple categories, repeat this fetch and
    # concatenate. One category for now → one HTTP call.
    cat_id = next(iter(SYNC_CATEGORY_IDS))
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
                    discussants = contribs[0]["speakers"]
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

    if existing_data == data_payload:
        print(
            "No substantive change — leaving data/indico.json untouched "
            f"(last sync recorded: "
            f"{json.loads(OUT.read_text(encoding='utf-8')).get('syncedAt', 'unknown')}).",
            file=sys.stderr,
        )
        return

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
