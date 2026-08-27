#!/usr/bin/env python3
"""Derive data/network-map.json: the node/edge graph behind the NetSec Network Map (#764).

Derivation only: the renderer (assets/js/network-map.js behind /network-map.html) stays
a pure consumer. Three graph layers over one deduped person universe:

  nodes  = 4 WG hubs + one theme hub per research theme in use + one node per
           unique person (WG rosters UNION directory bios, deduped by name_key)
  edges  = person->WG roster memberships (bipartite), person->theme edges from
           the member's bio themes, and person<->person ESSC co-panel edges
           (type "panel", weight = shared panels in that edition, tagged with
           the edition `year`) matched by name_key against every conference
           programme on disk. Bipartite hub forms are chosen over
           pairwise co-membership on purpose: pairwise would be a ~9k-edge
           hairball, the hub form carries the same information legibly.

Person nodes carry slug/photo/mentorship/country when a bio exists, so the
renderer can draw headshots, mentorship rings, and profile links without
fetching bios.json.

Co-authorship edges (type "coauthor") derive from data/publications.json's
`authors` arrays the same way; the file is empty until D6 ships its first
output, so the layer starts at zero edges and grows with the data. The same
file's `workingGroups` tag array is counted onto the WG hubs as an `outputs`
field (#1587), which is the reading that survives an author the matcher cannot
place and a single-author output that emits no co-authorship edge at all.

Not here yet, on purpose (follow-ups):
  - x/y layout coordinates (the renderer lays out client-side for now)

Input:  data/wg.json (always), data/bios.json, data/publications.json, and
        every conference programme (data/indico.json + each frozen
        data/essc-<year>-programme.json, merged by load_programmes()).
        All optional at call level, so the original skeleton tests stay valid.
Output: data/network-map.json

Determinism: there is no layout yet, so there is no RNG. Everything is sorted by a
stable key, so the output is byte-identical for a given wg.json. `--check`
regenerates in memory and diffs against the file on disk, so CI can catch a stale
network-map.json the same way build-calendar.py guards calendar.ics.

The script also rewrites the list region of the three locale pages, between
the network-map:list sentinels. The canvas needs scripting to draw anything
and is opaque to assistive technologies either way, so the page's alternative
cannot itself be script-rendered. Same posture, and the same sentinel splice,
as build-field-guide.py on the glossary pages.

Usage:
  python3 scripts/build-network-map.py            # write the graph + the three pages
  python3 scripts/build-network-map.py --check    # exit 1 if either is stale
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _directory_common import name_key, slugify  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
WG_JSON = REPO / "data" / "wg.json"
NETWORK_MAP_JSON = REPO / "data" / "network-map.json"


def _given_first(raw: str) -> str | None:
    """Rewrite a surname-first author string as "Given Surname", or None.

    Two conventions, both unambiguous, both standard in reference lists:

      "Laudrain, Arthur"   the comma is the signal
      "LAUDRAIN Arthur"    the all-caps surname is the signal, which is the
                           house style across French and much EU bibliography

    Returning a rewritten string rather than a flipped key matters for the
    initialised forms. `name_key` keeps only the first and last tokens, so
    flipping its output turns "Laudrain, A.P.B." into ("b", "laudrain") and
    loses the very initial the fallback needs. Rewriting first and letting
    name_key run on "A.P.B. Laudrain" keeps it.

    Deliberately conservative. A plain two-token name is never reversed on a
    guess, and an entirely upper-case name ("ADA LOVELACE") is left alone,
    since there the capitalisation says nothing about which token is which.
    Initials are excluded from that test, being upper case whatever the
    convention, so "LOVELACE A." still reads as surname-first.
    """
    if not raw:
        return None
    if "," in raw:
        surname, given = raw.split(",", 1)
        given, surname = given.strip(), surname.strip()
        return f"{given} {surname}" if given and surname else None
    tokens = raw.split()
    if len(tokens) < 2:
        return None
    head = re.sub(r"[^A-Za-z]", "", tokens[0])
    rest = [re.sub(r"[^A-Za-z]", "", x) for x in tokens[1:]]
    rest = [x for x in rest if x]
    if len(head) < 2 or not head.isupper() or not rest:
        return None
    # Only real words carry case information. A lone initial is always upper
    # case, so "LOVELACE A." must not be read as a shouted whole name.
    words = [x for x in rest if len(x) > 1]
    if words and all(x.isupper() for x in words):
        return None
    return " ".join(tokens[1:] + [tokens[0]])


def _resolve(key: tuple, people: dict) -> tuple | None:
    """A (first, last) key against the person universe, exact then initial.

    The initial pass only fires on a one-letter first token, and only when
    exactly one member fits. Two members sharing a surname and an initial is
    a coin flip, and a wrong co-authorship edge is worse than a missing one.
    """
    if key in people:
        return key
    first, last = key
    if len(first) == 1:
        hits = [k for k in people if k[1] == last and k[0].startswith(first)]
        if len(hits) == 1:
            return hits[0]
    return None


def match_author(raw: str, people: dict) -> tuple | None:
    """Resolve one publication author string to a key in the person universe.

    `name_key` reduces a name to (first, last), which is the shape a display
    name has. Bibliographies do not use display names, so an author written
    the way a reference list renders them was silently skipped before #1586.

    Two passes. The name as written, then the same name rewritten given-first
    when it is unambiguously surname-first (see `_given_first`). Each pass
    resolves exactly and then on a first initial.

    Returns None when nothing matches, which stays the correct answer for a
    genuine co-author from outside the Action.
    """
    key = name_key(raw)
    if key is None:
        return None
    hit = _resolve(key, people)
    if hit:
        return hit
    swapped = _given_first(raw)
    if swapped:
        key2 = name_key(swapped)
        if key2:
            return _resolve(key2, people)
    return None


def prefer_webp(photo: str) -> str:
    """Point a headshot at the smallest derivative the bios sync has made.

    The map draws faces as circles of about 16 CSS px on the canvas and at
    44 px in the hover card, so the directory's 600 px headshot spends
    almost all of its bytes on detail the page cannot show. Preference
    order, smallest first:

      1. assets/images/people/map/<slug>.webp — the 128 px map avatar
         (#1480). Across the current roster that is 176 KB in total.
      2. the sibling .webp the directory serves — 1.67 MB in total.
      3. the original JPEG — 5.24 MB in total.

    Each step falls through to the next when the file is absent, which is
    the state a member sits in between joining and the next bios sync. The
    canvas draws no face if a path 404s rather than breaking the layout, so
    every rung of the fallback is safe. Deterministic across checkouts,
    since the images are committed (until #119 moves them out).
    """
    stem = Path(photo).stem
    map_avatar = Path("assets/images/people/map") / f"{stem}.webp"
    if (REPO / map_avatar).exists():
        return map_avatar.as_posix()
    candidate = Path(photo).with_suffix(".webp")
    return candidate.as_posix() if (REPO / candidate).exists() else photo

_DOC = (
    "The NetSec Network Map graph (#764). Generated by scripts/build-network-map.py from "
    "data/wg.json + data/bios.json + data/essc-2026-programme.json. DO NOT EDIT "
    "BY HAND: rerun the script (pure standard library). `nodes` are WG hubs, "
    "research-theme hubs, and one node per unique person (rosters union bios); "
    "`edges` are bipartite person->hub memberships plus person<->person ESSC "
    "co-panel ties (type \"panel\", weighted). Person nodes carry slug/photo/"
    "mentorship when a bio exists. Sorted for a byte-stable diff; `--check` "
    "guards staleness in CI."
)


def build(wg: dict, bios: dict | None = None, programme: dict | None = None,
          publications: dict | None = None) -> dict:
    """Pure function: wg.json (+ optional bios.json / ESSC programme) -> network-map.json dict. No I/O, so it is trivially
    testable and its output depends only on its input (determinism)."""
    if not isinstance(wg, dict) or not isinstance(wg.get("groups"), list):
        raise ValueError("wg.json: expected an object with a 'groups' list")

    wg_nodes: list[dict] = []
    # Dedup people across WGs by name_key (collapses spelling drift); fall back to
    # a slug-based key when a name can't be reduced to first+last (never happens on
    # the current roster, but keeps a malformed name from crashing the build).
    people: dict = {}
    edge_pairs: set = set()

    for grp in wg["groups"]:
        number = grp.get("number")
        wg_id = f"wg-{number}"
        wg_nodes.append(
            {
                "id": wg_id,
                "type": "wg",
                "number": number,
                "name": grp.get("name", ""),
                "colour": grp.get("colour", wg_id),
                "memberCount": grp.get("memberCount"),
            }
        )
        for m in grp.get("members", []):
            nm = m.get("name", "")
            key = name_key(nm) or ("", slugify(nm))
            person = people.get(key)
            if person is None:
                slug = m.get("slug")
                person = {
                    "id": slug or f"p-{slugify(nm)}",
                    "type": "person",
                    "name": nm,
                    "country": m.get("country", ""),
                }
                if slug:
                    person["slug"] = slug
                people[key] = person
            elif m.get("slug") and "slug" not in person:
                # A later roster row carries the bio slug the first one lacked.
                person["slug"] = m["slug"]
                person["id"] = m["slug"]
            # Key the edge by the dedup key, not the id: the id can still be
            # promoted to a slug by a later roster row, so resolve to the final
            # id only after every group is processed.
            edge_pairs.add((key, wg_id))

    # ── Optional enrichment: directory bios (#764 PoC lens 2) ──
    # Themes, mentorship flags, and headshot paths ride onto the matching
    # person nodes; directory members with no WG roster row become nodes of
    # their own (they are part of the network even without a roster seat).
    # Theme hubs + person->theme edges give the renderer a second bipartite
    # lens over the same people: the map of the field.
    theme_nodes: list[dict] = []
    theme_edge_pairs: set = set()
    if bios is not None:
        by_slug = {p["slug"]: p for p in people.values() if p.get("slug")}
        theme_counts: dict[str, int] = {}
        theme_names: dict[str, str] = {}
        for m in bios.get("members", []):
            nm = m.get("name", "")
            key = name_key(nm) or ("", slugify(nm))
            person = by_slug.get(m.get("id")) or people.get(key)
            if person is None:
                person = {
                    "id": m.get("id") or f"p-{slugify(nm)}",
                    "type": "person",
                    "name": nm,
                    "country": m.get("country", ""),
                    "slug": m.get("id"),
                }
                people[key] = person
            else:
                if m.get("id") and "slug" not in person:
                    person["slug"] = m["id"]
                    person["id"] = m["id"]
            if m.get("photo"):
                person["photo"] = prefer_webp(m["photo"])
            if m.get("mentorship"):
                person["mentorship"] = sorted(m["mentorship"])
            for theme in m.get("themes") or []:
                t_slug = slugify(theme)
                theme_names[t_slug] = theme
                theme_counts[t_slug] = theme_counts.get(t_slug, 0) + 1
                theme_edge_pairs.add((key, f"theme-{t_slug}"))
        theme_nodes = sorted(
            (
                {
                    "id": f"theme-{t}",
                    "type": "theme",
                    "name": theme_names[t],
                    "memberCount": theme_counts[t],
                }
                for t in theme_counts
            ),
            key=lambda n: n["id"],
        )

    # ── Optional enrichment: ESSC co-panel edges (#764 PoC lens 3) ──
    # Two people listed on contributions inside the same programme item sat
    # on the same conference panel: a real person-to-person tie. Only people
    # already in the node universe count (conference guests from outside the
    # Action are not added); weight counts shared panels.
    panel_weights: dict[tuple, int] = {}
    panels_matched = 0
    if programme is not None:
        for year, conf in sorted((programme.get("annualConferences") or {}).items()):
            for day in ((conf.get("programme") or {}).get("days") or []):
                for row in day.get("rows", []):
                    for item in row.get("items", []):
                        keys = set()
                        for contrib in item.get("contributions") or []:
                            for pers in contrib.get("people") or []:
                                k = name_key(pers.get("name", ""))
                                if k and k in people:
                                    keys.add(k)
                        if len(keys) >= 2:
                            panels_matched += 1
                            ordered = sorted(keys, key=lambda k: people[k]["id"])
                            for i in range(len(ordered)):
                                for j in range(i + 1, len(ordered)):
                                    pair = (year, ordered[i], ordered[j])
                                    panel_weights[pair] = panel_weights.get(pair, 0) + 1

    # ── Optional enrichment: co-authorship (#764 Phase 3) ──
    # publications.json is hand-maintained and empty until D6 ships its first
    # output, but the schema already carries an `authors` array of display
    # names. Match them the same way as panel speakers; two matched authors on
    # one output are co-authors (weight = shared outputs). Zero edges today,
    # so the overlay lights up on its own as publications are entered.
    coauthor_weights: dict[tuple, int] = {}
    publications_matched = 0
    # Every entry carries a workingGroups tag array, the same mechanism
    # events.json uses to surface an item under a WG section. The map read the
    # file for authors only, so an output tagged to WG2 contributed nothing to
    # the WG2 hub, and a single-author output contributed nothing anywhere,
    # since the co-authorship pass needs two matched names before it emits an
    # edge (#1587). The tag is counted onto the hub, which is the reading that
    # survives an author the matcher cannot place.
    wg_outputs: dict = {}
    outputs_tagged = 0
    unmatched_authors: set = set()
    if publications is not None:
        for pub in publications.get("publications") or []:
            tagged = False
            for number in pub.get("workingGroups") or []:
                wg_id = f"wg-{number}"
                wg_outputs[wg_id] = wg_outputs.get(wg_id, 0) + 1
                tagged = True
            if tagged:
                outputs_tagged += 1
            keys = set()
            for author in pub.get("authors") or []:
                raw = author if isinstance(author, str) else author.get("name", "")
                k = match_author(raw, people)
                if k:
                    keys.add(k)
                elif raw:
                    unmatched_authors.add(raw)
            if len(keys) >= 2:
                publications_matched += 1
                ordered = sorted(keys, key=lambda k: people[k]["id"])
                for i in range(len(ordered)):
                    for j in range(i + 1, len(ordered)):
                        pair = (ordered[i], ordered[j])
                        coauthor_weights[pair] = coauthor_weights.get(pair, 0) + 1

    # Stamped on the hub rather than emitted as a key that is always there:
    # with no publications on file the graph is byte-identical to the one
    # before this landed, so the layer arrives with the data.
    for hub in wg_nodes:
        if wg_outputs.get(hub["id"]):
            hub["outputs"] = wg_outputs[hub["id"]]

    person_nodes = sorted(people.values(), key=lambda p: p["id"])
    nodes = wg_nodes + theme_nodes + person_nodes
    edges = sorted(
        ({"source": people[key]["id"], "target": wg_id} for key, wg_id in edge_pairs),
        key=lambda e: (e["source"], e["target"]),
    )
    edges += sorted(
        ({"source": people[key]["id"], "target": t_id} for key, t_id in theme_edge_pairs),
        key=lambda e: (e["source"], e["target"]),
    )
    edges += sorted(
        (
            {"source": people[a]["id"], "target": people[b]["id"],
             "type": "panel", "weight": w, "year": year}
            for (year, a, b), w in panel_weights.items()
        ),
        key=lambda e: (e["year"], e["source"], e["target"]),
    )
    edges += sorted(
        (
            {"source": people[a]["id"], "target": people[b]["id"],
             "type": "coauthor", "weight": w}
            for (a, b), w in coauthor_weights.items()
        ),
        key=lambda e: (e["source"], e["target"]),
    )

    stats = {
        "working_groups": len(wg_nodes),
        "people": len(person_nodes),
        "people_with_bios": sum(1 for p in person_nodes if "slug" in p),
        "edges": len(edges),
    }
    if bios is not None:
        stats["themes"] = len(theme_nodes)
    if programme is not None:
        stats["panels_matched"] = panels_matched
        stats["panel_edges"] = len(panel_weights)
        stats["panel_editions"] = sorted({y for (y, _a, _b) in panel_weights})
    if publications is not None:
        stats["publications_matched"] = publications_matched
        if outputs_tagged:
            stats["outputs_tagged"] = outputs_tagged
        stats["coauthor_edges"] = len(coauthor_weights)
        # Every author string that resolved to nobody. A co-author from
        # outside the Action belongs here and is not a problem. A member
        # written in a format the matcher cannot read also lands here, and
        # is: this list is what makes that visible instead of silent.
        stats["authors_unmatched"] = sorted(unmatched_authors)

    return {
        "_documentation": _DOC,
        "stats": stats,
        "nodes": nodes,
        "edges": edges,
    }


def load_programmes() -> dict | None:
    """Merge every conference programme on disk into one annualConferences map.

    data/indico.json is the live sync and holds whichever edition Indico is
    currently serving. Each data/essc-<year>-programme.json is a frozen snapshot
    taken at conference close, so where both carry the same edition the frozen
    copy wins: it is the record of what actually happened, and sync-indico will
    not touch it again.

    Reading every file rather than one hardcoded path is what makes a new
    edition appear on the map by itself (#1584).
    """
    merged: dict = {}
    live = REPO / "data" / "indico.json"
    if live.exists():
        data = json.loads(live.read_text(encoding="utf-8"))
        merged.update(data.get("annualConferences") or {})
    for frozen in sorted(REPO.glob("data/essc-*-programme.json")):
        data = json.loads(frozen.read_text(encoding="utf-8"))
        merged.update(data.get("annualConferences") or {})
    return {"annualConferences": merged} if merged else None


# ── The in-page list (#764) ─────────────────────────────────────────────────
# The canvas needs scripting to draw anything at all, and it is opaque to a
# screen reader whether or not scripting runs. The page used to answer both by
# pointing at the Working Groups page and the Directory, which is an
# alternative carrying the same dependency as the barrier in the first case and
# a different page in the second. The same people are now rendered here as a
# table at build time, inside a closed <details>, since a hidden link is a
# focusable link a sighted keyboard user cannot see. network-map.js narrows the
# same <tbody> as the filters move, so one code path serves both and the list
# cannot drift from the canvas.
#
# data-pagefind-ignore, because <main> carries data-pagefind-body: without it
# every member's name would index against this page as well as their own
# profile, and a search for a person would answer with the map.
LIST_START = "<!-- network-map:list start -->"
LIST_END = "<!-- network-map:list end -->"

# Countries are stored as English exonyms in bios.json, the same way the
# Directory stores them, and network-map.js localises the cell through
# window.netsecCountry from the data-country attribute. Without scripting the
# FR and DE tables carry the English name, which is the information rather than
# an error, and the alternative's job is to carry the information.
LIST_LOCALES = {
    "en": {
        "file": "network-map.html",
        "summary": "Browse this map as a list",
        "count": "Everyone the map draws, {n} people.",
        "col_name": "Name",
        "col_wgs": "Working Groups",
        "col_country": "Country",
        "none": "None recorded",
    },
    "fr": {
        "file": "network-map.fr.html",
        "summary": "Parcourir cette carte sous forme de liste",
        "count": "Toutes les personnes que la carte dessine, soit {n}.",
        "col_name": "Nom",
        "col_wgs": "Groupes de travail",
        "col_country": "Pays",
        "none": "Aucun",
    },
    "de": {
        "file": "network-map.de.html",
        "summary": "Diese Karte als Liste ansehen",
        "count": "Alle Personen der Karte, insgesamt {n}.",
        "col_name": "Name",
        "col_wgs": "Arbeitsgruppen",
        "col_country": "Land",
        "none": "Keine",
    },
}


def _wg_numbers(graph: dict) -> dict:
    """person id -> sorted WG numbers. Reads the same bipartite edges the
    canvas paints, so the two cannot disagree about who is in what."""
    by_id = {n["id"]: n for n in graph["nodes"]}
    out: dict = {}
    for e in graph["edges"]:
        if e.get("type"):          # panel / coauthor edges are person-to-person
            continue
        target = by_id.get(e["target"])
        if target and target["type"] == "wg":
            out.setdefault(e["source"], []).append(target["number"])
    return {k: sorted(v) for k, v in out.items()}


def render_list_region(loc: str, graph: dict) -> str:
    """The list region for one locale, sentinels included.

    Row order is the node order in the graph, which is sorted by person id, so
    the table and the JSON walk the same people in the same sequence. That is
    also the order the keyboard traversal in #1645 will want.
    """
    l = LIST_LOCALES[loc]
    wgs = _wg_numbers(graph)
    people = [n for n in graph["nodes"] if n["type"] == "person"]
    rows = []
    for p in people:
        name = html.escape(p["name"])
        cell = (f'<a href="people/{html.escape(p["slug"])}.html">{name}</a>'
                if p.get("slug") else name)
        nums = wgs.get(p["id"], [])
        wg_text = ", ".join(f"WG{n}" for n in nums) if nums else l["none"]
        country = p.get("country") or ""
        country_cell = (
            f'<td data-country="{html.escape(country)}">{html.escape(country)}</td>'
            if country else "<td></td>"
        )
        rows.append(
            f'          <tr data-person="{html.escape(p["id"])}">'
            f"<th scope=\"row\">{cell}</th>"
            f"<td>{wg_text}</td>{country_cell}</tr>"
        )
    return "\n".join([
        LIST_START,
        '  <details class="network-map-list" id="network-map-list" data-pagefind-ignore>',
        f'    <summary class="network-map-list__summary">{html.escape(l["summary"])}</summary>',
        f'    <p class="network-map-list__hint" id="network-map-list-hint">'
        f'{html.escape(l["count"]).replace("{n}", str(len(people)))}</p>',
        '    <div class="network-map-list__scroll" tabindex="0">',
        '      <table class="network-map-list__table">',
        "        <thead><tr>"
        f'<th scope="col">{html.escape(l["col_name"])}</th>'
        f'<th scope="col">{html.escape(l["col_wgs"])}</th>'
        f'<th scope="col">{html.escape(l["col_country"])}</th>'
        "</tr></thead>",
        '        <tbody id="network-map-list-body">',
        *rows,
        "        </tbody>",
        "      </table>",
        "    </div>",
        "  </details>",
        "  " + LIST_END,
    ]) + "\n"


def replace_list_region(page: str, region: str) -> str:
    """Swap the region between the sentinels. Raises when a page has lost
    them, rather than silently writing a page with no list on it."""
    pattern = re.compile(re.escape(LIST_START) + r".*?" + re.escape(LIST_END), re.DOTALL)
    if not pattern.search(page):
        raise ValueError(f"missing {LIST_START} / {LIST_END} sentinels")
    return pattern.sub(lambda _m: region.rstrip("\n"), page, count=1)


def _serialise(graph: dict) -> str:
    return json.dumps(graph, indent=2, ensure_ascii=False) + "\n"


def main(argv: list) -> int:
    check = "--check" in argv
    wg = json.loads(WG_JSON.read_text(encoding="utf-8"))
    bios_path = REPO / "data" / "bios.json"
    bios = json.loads(bios_path.read_text(encoding="utf-8")) if bios_path.exists() else None
    programme = load_programmes()
    pubs_path = REPO / "data" / "publications.json"
    publications = json.loads(pubs_path.read_text(encoding="utf-8")) if pubs_path.exists() else None
    graph = build(wg, bios, programme, publications)
    text = _serialise(graph)

    pages = {
        loc: (REPO / l["file"], replace_list_region(
            (REPO / l["file"]).read_text(encoding="utf-8"), render_list_region(loc, graph)))
        for loc, l in LIST_LOCALES.items()
    }

    if check:
        stale = []
        current = NETWORK_MAP_JSON.read_text(encoding="utf-8") if NETWORK_MAP_JSON.exists() else ""
        if current != text:
            stale.append("data/network-map.json")
        for loc, (path, rendered) in pages.items():
            if path.read_text(encoding="utf-8") != rendered:
                stale.append(LIST_LOCALES[loc]["file"])
        if stale:
            for name in stale:
                print(f"✗ {name} is stale", file=sys.stderr)
            print(
                "  Run: python3 scripts/build-network-map.py, and commit the result.",
                file=sys.stderr,
            )
            return 1
        print("✓ data/network-map.json and the three locale pages are current")
        return 0

    NETWORK_MAP_JSON.write_text(text, encoding="utf-8")
    for loc, (path, rendered) in pages.items():
        if path.read_text(encoding="utf-8") != rendered:
            path.write_text(rendered, encoding="utf-8")
            print(f"✓ rebuilt the list on {LIST_LOCALES[loc]['file']}")
    s = graph["stats"]
    if s.get("authors_unmatched"):
        # Printed, not fatal: an outside co-author is a legitimate miss, so
        # there is no threshold that separates one from a typo (#1586).
        print("  authors matching no member (check the spelling of any that "
              "should have matched):", file=sys.stderr)
        for a in s["authors_unmatched"]:
            print(f"    - {a}", file=sys.stderr)
    print(
        f"✓ wrote data/network-map.json — {s['working_groups']} WGs, {s['people']} people "
        f"({s['people_with_bios']} with bios), {s['edges']} edges"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
