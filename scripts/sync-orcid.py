#!/usr/bin/env python3
"""Fetch each directory member's most recent works from the public ORCID
API and write them to data/orcid-works.json, keyed by member slug.

Why a sibling script rather than a step inside sync-bios.py: an ORCID
outage (or a single member's malformed record) must never block the
directory sync. This script reads the *already written* data/bios.json,
fetches works per member, and fails soft per member so one bad record
loses one member's publications, not the whole run.

The output feeds the directory's lazy "Recent publications" card section
(#761): /people.html fetches data/orcid-works.json only when a visitor
expands a card, so member cards at rest gain no weight. The same map is
the natural future feed for the Outputs page and a co-authorship Network Map,
so it is keyed by slug for a single-fetch join against bios.json.

Reads:  data/bios.json (members[].orcid, the canonical 19-char iD that
        normalize_orcid in sync-bios.py already writes).
Writes: data/orcid-works.json — only when the works payload actually
        changed, so the weekly workflow never opens an empty auto-PR.

Requires: requests. See scripts/requirements.txt.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

try:
    import requests
except ImportError:  # pragma: no cover - exercised only in a bare env
    requests = None  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
BIOS = ROOT / "data" / "bios.json"
OUT = ROOT / "data" / "orcid-works.json"

API_BASE = "https://pub.orcid.org/v3.0"
# A descriptive User-Agent is courteous on a public, unauthenticated API
# and lets ORCID contact the operator if a run ever misbehaves.
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "netsec-cost.eu directory sync (+https://netsec-cost.eu)",
}
TIMEOUT = 30
MAX_WORKS = 3  # most recent N works per member, by publication year


# ──────────────────────────── parsing ────────────────────────────


def _year(work_summary: dict) -> str:
    """Publication year as a string, or "" when ORCID has no date."""
    pd = work_summary.get("publication-date") or {}
    yr = (pd.get("year") or {}) if pd else {}
    return (yr.get("value") or "").strip()


def _doi(group: dict) -> str:
    """The DOI for a work group, or "". ORCID records the DOI on the
    *group* (which merges the same work across sources), not on the
    individual work-summary, so it is read from the group here."""
    eids = (group.get("external-ids") or {}).get("external-id", []) or []
    for e in eids:
        if (e.get("external-id-type") or "").lower() == "doi":
            val = (e.get("external-id-value") or "").strip()
            if val:
                return val
    return ""


def parse_works(payload: dict, limit: int = MAX_WORKS) -> list[dict]:
    """Turn an ORCID /works response into a trimmed, newest-first list of
    {title, year, journal, doi} records. Pure: no network, no I/O, so the
    test suite drives it with fixture payloads.

    A work with no parseable title is dropped (nothing to render). A work
    with no year is kept but sorts last (ORCID has plenty of undated
    entries that are still worth showing). Output is capped at `limit`."""
    records: list[dict] = []
    for group in (payload or {}).get("group", []) or []:
        summaries = group.get("work-summary") or []
        if not summaries:
            continue
        ws = summaries[0]
        title = (((ws.get("title") or {}).get("title") or {}).get("value") or "").strip()
        if not title:
            continue
        journal = ((ws.get("journal-title") or {}).get("value") or "").strip()
        records.append(
            {
                "title": title,
                "year": _year(ws),
                "journal": journal,
                "doi": _doi(group),
            }
        )
    # Newest first. Missing year ("") sorts after any real year because
    # "" < any digit string, so reverse puts it last.
    records.sort(key=lambda r: r["year"], reverse=True)
    return records[:limit]


# ──────────────────────────── fetching ────────────────────────────


def fetch_works(orcid: str, session) -> dict | None:
    """Fetch one member's /works payload, or None on any failure. Fails
    soft so a single 404 / timeout / non-200 skips that member without
    aborting the run."""
    url = f"{API_BASE}/{orcid}/works"
    try:
        r = session.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            print(f"  · {orcid}: HTTP {r.status_code}, skipping", file=sys.stderr)
            return None
        return r.json()
    except Exception as exc:  # noqa: BLE001 - intentional fail-soft catch-all
        print(f"  · {orcid}: {type(exc).__name__}: {exc}, skipping", file=sys.stderr)
        return None


def build_works_map(
    members: list[dict],
    fetcher,
    existing: dict[str, list[dict]] | None = None,
) -> dict[str, list[dict]]:
    """Map each member slug with an ORCID iD to their trimmed works list.
    `fetcher(orcid)` returns a raw /works payload or None; injected so the
    test suite can drive it without network.

    Resilience: a *failed* fetch (fetcher returns None) carries the
    member's previous works over from `existing` rather than dropping
    them, so a transient ORCID outage cannot wipe the file. A *successful*
    fetch that yields no works omits the member (genuinely nothing to
    show, and any stale entry is cleared). A member with no iD, or absent
    from the current roster, is dropped."""
    existing = existing or {}
    out: dict[str, list[dict]] = {}
    for m in members:
        orcid = (m.get("orcid") or "").strip()
        slug = m.get("id")
        if not orcid or not slug:
            continue
        payload = fetcher(orcid)
        if payload is None:
            # Fetch failed this run — keep what we last had for this member.
            if slug in existing:
                out[slug] = existing[slug]
            continue
        works = parse_works(payload)
        if works:
            out[slug] = works
    return out


# ──────────────────────────── main ────────────────────────────


def main() -> int:
    if requests is None:
        print("requests is not installed (see scripts/requirements.txt).", file=sys.stderr)
        return 1
    if not BIOS.exists():
        print(f"{BIOS.relative_to(ROOT)} not found — run sync-bios.py first.", file=sys.stderr)
        return 1

    bios = json.loads(BIOS.read_text(encoding="utf-8"))
    members = bios.get("members") or []

    # Load the previous works first so a failed fetch can carry a member's
    # publications over (a transient ORCID outage must not wipe the file).
    existing = {}
    if OUT.exists():
        try:
            existing = json.loads(OUT.read_text(encoding="utf-8")).get("works", {})
        except json.JSONDecodeError:
            existing = {}

    session = requests.Session()
    works_map = build_works_map(
        members, lambda o: fetch_works(o, session), existing
    )

    # Stable key order so the diff is minimal and review-friendly.
    works_sorted = {k: works_map[k] for k in sorted(works_map)}

    # Idempotent write: only rewrite (and advance the timestamp) when the
    # works payload itself changed, so a no-op weekly run leaves the file
    # untouched and the auto-PR step has nothing to open.
    if works_sorted == existing:
        print(
            f"No change — {OUT.relative_to(ROOT)} already current "
            f"({len(works_sorted)} member(s) with works)."
        )
        return 0

    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    doc = {
        "_documentation": (
            "Generated by scripts/sync-orcid.py from each member's public "
            "ORCID record. Keyed by directory slug; up to 3 most recent "
            "works each. Lazy-loaded by /people.html on card expansion "
            "(#761). Do not hand-edit — the next sync overwrites it."
        ),
        "generated_at": now,
        "works": works_sorted,
    }
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    total = sum(len(v) for v in works_sorted.values())
    print(
        f"Wrote {OUT.relative_to(ROOT)} — {len(works_sorted)} member(s), "
        f"{total} work(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
