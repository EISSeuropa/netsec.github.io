#!/usr/bin/env python3
"""Generate the post-conference recruitment mail-merge list.

Diffs the cost.eu Management Committee roster (data/mc-members.json)
and the ESSC Indico speaker list (data/indico.json) against the
published directory (data/bios.json), matching people by a normalised
name key. Anyone present on cost.eu or Indico but absent from the
directory is emitted as a CSV row, so the maintainer can run a
mail-merge that invites every named-but-bio-less person to add their
profile via the join form.

With --incomplete it reports the other half of the same problem:
people who are already in the directory but whose entry is missing
fields. A member with no keywords is absent from every research-theme
filter and from the mentorship matcher, so they sit in the grid as a
name and nothing else. The output is the same mail-merge shape, so one
round of mail can invite them to fill the gaps. A fresh Form submission
merges into the existing entry and leaves blank answers as they were
(docs/bios-setup.md), so they only retype what is changing.

This is a maintainer-only tool with no UI. It is stdlib-only (json +
csv) so it runs under the system /usr/bin/python3 with no install
step.

Output columns (default mode):
  name          display name as it appears in the source
  country       country if the source carries one (MC always does;
                Indico speakers rarely do, so this is often blank)
  source        "mc" for a Management Committee representative,
                "speaker" for an Indico speaker
  form_link     the join-form URL read from bios.json's source block

Output columns (--incomplete):
  name          display name as it appears in the directory
  source        "form" if they submitted the join form (they hold an edit
                link and a gap is theirs to fill), "seed" if the entry was
                created from the cost.eu roster and they have never filled
                the form at all, which needs an invitation rather than a
                reminder
  email         published contact address, blank when they published none
  missing       the absent fields, comma-joined, worst rows first
  form_link     the join-form URL read from bios.json's source block

A person who is both an MC representative and an ESSC speaker is
reported once, under "mc" (the MC roster carries their country, the
speaker record usually does not, so the richer row wins).

Usage:
  /usr/bin/python3 scripts/report-missing-bios.py             > recruit.csv
  /usr/bin/python3 scripts/report-missing-bios.py --incomplete > gaps.csv
  /usr/bin/python3 scripts/report-missing-bios.py --help

The name key matches the norm() in scripts/sync-cost.py: lowercase,
strip a leading salutation (Dr / Prof / Mr / Ms / Mrs), strip
diacritics, collapse runs of whitespace.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MC = ROOT / "data" / "mc-members.json"
INDICO = ROOT / "data" / "indico.json"
BIOS = ROOT / "data" / "bios.json"


def norm(name: str) -> str:
    """Normalised name key (no salutation, no diacritics, lower case).

    Ports scripts/sync-cost.py's norm() so the matching here lines up
    with the matching the weekly sync already does.
    """
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"^(Dr|Prof|Mr|Ms|Mrs)\.?\s+", "", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def bio_keys(bios: dict) -> set:
    """The set of normalised name keys already in the directory."""
    keys = set()
    for m in bios.get("members", []):
        if m.get("name"):
            keys.add(norm(m["name"]))
        # name_aliases cover married/maiden names, transliteration
        # variants, and nicknames, so a person listed under an alias
        # on cost.eu still counts as already in the directory.
        for alias in m.get("name_aliases", []):
            if alias:
                keys.add(norm(alias))
    return keys


def mc_people(mc: dict):
    """Yield (name, country) for every Management Committee member."""
    for m in mc.get("members", []):
        name = m.get("name", "")
        if name:
            yield name, m.get("country", "")


def speaker_people(indico: dict):
    """Yield (name, country) for every Indico speaker.

    Walks the nested programme (days -> rows/slots -> contributions ->
    people) and yields each person flagged speaker=true. Speaker
    records carry an affiliation but no country, so country is always
    blank for this source.
    """
    seen = set()

    def walk(node):
        if isinstance(node, dict):
            if node.get("speaker") and node.get("name"):
                name = node["name"]
                key = norm(name)
                if key not in seen:
                    seen.add(key)
                    yield name, ""
            for v in node.values():
                yield from walk(v)
        elif isinstance(node, list):
            for v in node:
                yield from walk(v)

    confs = indico.get("annualConferences", {})
    for conf in confs.values():
        yield from walk(conf.get("programme", {}))


def collect_missing(mc: dict, indico: dict, bios: dict):
    """Return the list of missing-from-directory rows.

    A person already keyed in the directory is dropped. A person seen
    first via the MC roster wins over the same person seen later as a
    speaker, because the MC row carries a country.
    """
    have = bio_keys(bios)
    form_link = (bios.get("source") or {}).get("form_url", "")
    rows = []
    emitted = set()

    def consider(name, country, source):
        key = norm(name)
        if not key or key in have or key in emitted:
            return
        emitted.add(key)
        rows.append({
            "name": name,
            "country": country,
            "source": source,
            "form_link": form_link,
        })

    for name, country in mc_people(mc):
        consider(name, country, "mc")
    for name, country in speaker_people(indico):
        consider(name, country, "speaker")
    return rows


# Fields worth chasing on an entry that already exists. Working group is
# deliberately absent: the directory is open to the wider community, most
# of whom legitimately sit in no Working Group, so flagging it would bury
# the real gaps under half the roster.
INCOMPLETE_FIELDS = [
    ("bio", "bio"),
    ("keywords", "research keywords"),
    ("photo", "photo"),
    ("position", "position"),
    ("email", "contact email"),
    ("mentorship", "mentorship preference"),
]


def collect_incomplete(bios: dict):
    """Return the list of directory entries with fields left blank.

    One row per member missing at least one field in INCOMPLETE_FIELDS,
    worst first so the top of the CSV is the mail worth sending. An
    absent mentorship answer counts as missing: the question is opt-in
    and an untouched entry is indistinguishable from a considered "no",
    so the invitation goes to both.
    """
    form_link = (bios.get("source") or {}).get("form_url", "")
    rows = []
    for m in bios.get("members", []):
        if not m.get("name"):
            continue
        gaps = [label for key, label in INCOMPLETE_FIELDS if not m.get(key)]
        if not gaps:
            continue
        rows.append((len(gaps), {
            "name": m["name"],
            "source": m.get("source", "") or "",
            "email": m.get("email", "") or "",
            "missing": ", ".join(gaps),
            "form_link": form_link,
        }))
    rows.sort(key=lambda pair: (-pair[0], pair[1]["name"]))
    return [row for _, row in rows]


def write_csv(rows, stream, fieldnames=("name", "country", "source", "form_link")):
    writer = csv.DictWriter(stream, fieldnames=list(fieldnames))
    writer.writeheader()
    for r in rows:
        writer.writerow(r)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--mc", type=Path, default=MC,
        help="path to mc-members.json (default: data/mc-members.json)",
    )
    parser.add_argument(
        "--indico", type=Path, default=INDICO,
        help="path to indico.json (default: data/indico.json)",
    )
    parser.add_argument(
        "--bios", type=Path, default=BIOS,
        help="path to bios.json (default: data/bios.json)",
    )
    parser.add_argument(
        "--incomplete", action="store_true",
        help="report directory entries with blank fields instead of "
             "people missing from the directory",
    )
    args = parser.parse_args(argv)

    if args.incomplete:
        bios = json.loads(args.bios.read_text(encoding="utf-8"))
        write_csv(
            collect_incomplete(bios), sys.stdout,
            fieldnames=("name", "source", "email", "missing", "form_link"),
        )
        return 0

    mc = json.loads(args.mc.read_text(encoding="utf-8"))
    indico = json.loads(args.indico.read_text(encoding="utf-8"))
    bios = json.loads(args.bios.read_text(encoding="utf-8"))

    rows = collect_missing(mc, indico, bios)
    write_csv(rows, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
