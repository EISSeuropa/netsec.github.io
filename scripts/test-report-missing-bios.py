#!/usr/bin/env python3
"""Stdlib test suite for scripts/report-missing-bios.py.

The module is loaded via importlib from its hyphenated path (hyphens
block import-by-name). No network, no mutation of tracked files: every
test feeds in-memory dicts.

Covered logic:
  * norm            salutation strip, diacritic strip, whitespace
                    collapse, case fold
  * bio_keys        names plus name_aliases keyed
  * speaker_people  nested-programme walk, speaker=true gate, dedup
  * collect_missing already-in-directory drop, mc-over-speaker
                    precedence, alias suppression, form_link plumbing
  * collect_incomplete
                    gap detection, complete entries dropped, worst-first
                    ordering, seed/form source plumbing
  * write_csv       header + row shape, both column sets

Run standalone:  /usr/bin/python3 scripts/test-report-missing-bios.py
Run via pytest:  /usr/bin/python3 -m pytest scripts/test-report-missing-bios.py -q
"""
from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path

_MOD_PATH = Path(__file__).resolve().parent / "report-missing-bios.py"
_spec = importlib.util.spec_from_file_location("report_missing_bios", _MOD_PATH)
rmb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rmb)


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------
def _bios(members=None, form_url="https://forms.example/join"):
    return {
        "source": {"form_url": form_url},
        "members": members or [],
    }


def _mc(members):
    return {"members": members}


def _indico_with_speakers(people):
    """Wrap a flat list of person dicts in a minimal programme tree."""
    return {
        "annualConferences": {
            "2026": {
                "programme": {
                    "days": [
                        {"slots": [{"contributions": [{"people": people}]}]}
                    ]
                }
            }
        }
    }


# --------------------------------------------------------------------------
# norm
# --------------------------------------------------------------------------
def test_norm_strips_salutation():
    assert rmb.norm("Dr Jane Doe") == "jane doe"
    assert rmb.norm("Prof. John Roe") == "john roe"


def test_norm_strips_diacritics_and_folds_case():
    assert rmb.norm("Senada Šelo Šabić") == "senada selo sabic"


def test_norm_collapses_whitespace():
    assert rmb.norm("  Anna   Krasteva ") == "anna krasteva"


def test_norm_handles_empty():
    assert rmb.norm("") == ""
    assert rmb.norm(None) == ""


# --------------------------------------------------------------------------
# bio_keys
# --------------------------------------------------------------------------
def test_bio_keys_includes_names_and_aliases():
    bios = _bios([
        {"name": "Dr Marie Robin"},
        {"name": "John Roe", "name_aliases": ["Johnny Roe"]},
    ])
    keys = rmb.bio_keys(bios)
    assert "marie robin" in keys
    assert "john roe" in keys
    assert "johnny roe" in keys


# --------------------------------------------------------------------------
# speaker_people
# --------------------------------------------------------------------------
def test_speaker_people_only_yields_flagged_speakers():
    indico = _indico_with_speakers([
        {"name": "Yijun Xu", "speaker": True},
        {"name": "Not A Speaker", "speaker": False},
        {"name": "No Flag"},
    ])
    out = list(rmb.speaker_people(indico))
    names = [n for n, _ in out]
    assert names == ["Yijun Xu"]


def test_speaker_people_dedupes_by_key():
    indico = _indico_with_speakers([
        {"name": "Dr Marie Robin", "speaker": True},
        {"name": "Marie Robin", "speaker": True},
    ])
    out = list(rmb.speaker_people(indico))
    assert len(out) == 1


# --------------------------------------------------------------------------
# collect_missing
# --------------------------------------------------------------------------
def test_collect_drops_people_already_in_directory():
    mc = _mc([{"name": "Dr Jane Doe", "country": "Albania"}])
    bios = _bios([{"name": "Jane Doe"}])
    rows = rmb.collect_missing(mc, _indico_with_speakers([]), bios)
    assert rows == []


def test_collect_emits_missing_mc_member_with_country():
    mc = _mc([{"name": "Dr Jane Doe", "country": "Albania"}])
    rows = rmb.collect_missing(mc, _indico_with_speakers([]), _bios())
    assert len(rows) == 1
    r = rows[0]
    assert r["name"] == "Dr Jane Doe"
    assert r["country"] == "Albania"
    assert r["source"] == "mc"
    assert r["form_link"] == "https://forms.example/join"


def test_collect_emits_missing_speaker_with_blank_country():
    indico = _indico_with_speakers([{"name": "Yijun Xu", "speaker": True}])
    rows = rmb.collect_missing(_mc([]), indico, _bios())
    assert len(rows) == 1
    assert rows[0]["source"] == "speaker"
    assert rows[0]["country"] == ""


def test_collect_mc_wins_over_speaker_for_same_person():
    mc = _mc([{"name": "Dr Jane Doe", "country": "Albania"}])
    indico = _indico_with_speakers([{"name": "Jane Doe", "speaker": True}])
    rows = rmb.collect_missing(mc, indico, _bios())
    assert len(rows) == 1
    assert rows[0]["source"] == "mc"
    assert rows[0]["country"] == "Albania"


def test_collect_respects_directory_aliases():
    mc = _mc([{"name": "Dr Marie Dupont", "country": "France"}])
    bios = _bios([{"name": "Marie Martin", "name_aliases": ["Marie Dupont"]}])
    rows = rmb.collect_missing(mc, _indico_with_speakers([]), bios)
    assert rows == []


# --------------------------------------------------------------------------
# collect_incomplete
# --------------------------------------------------------------------------
def _full_member(**over):
    """A directory entry with every INCOMPLETE_FIELDS key filled."""
    m = {
        "name": "Dr Jane Doe", "source": "form", "bio": "A bio.",
        "keywords": ["deterrence"], "photo": "assets/img/jane.webp",
        "position": "Senior Lecturer", "email": "jane@example.eu",
        "mentorship": ["mentor"],
    }
    m.update(over)
    return m


def test_incomplete_drops_a_complete_entry():
    rows = rmb.collect_incomplete(_bios([_full_member()]))
    assert rows == []


def test_incomplete_names_the_absent_fields():
    rows = rmb.collect_incomplete(_bios([_full_member(bio="", photo=None)]))
    assert len(rows) == 1
    assert rows[0]["missing"] == "bio, photo"
    assert rows[0]["form_link"] == "https://forms.example/join"


def test_incomplete_counts_an_empty_mentorship_list_as_missing():
    # [] is what parse_mentorship emits for an untouched question, and is
    # indistinguishable from a considered "none", so it is chased either way.
    rows = rmb.collect_incomplete(_bios([_full_member(mentorship=[])]))
    assert rows[0]["missing"] == "mentorship preference"


def test_incomplete_orders_worst_first_then_by_name():
    bios = _bios([
        _full_member(name="Bee", photo=""),
        _full_member(name="Ann", photo="", bio="", email=""),
        _full_member(name="Cid", photo=""),
    ])
    rows = rmb.collect_incomplete(bios)
    assert [r["name"] for r in rows] == ["Ann", "Bee", "Cid"]


def test_incomplete_carries_source_and_blank_email():
    rows = rmb.collect_incomplete(_bios([
        _full_member(name="Seeded", source="seed", email=None, bio=""),
    ]))
    assert rows[0]["source"] == "seed"
    assert rows[0]["email"] == ""


def test_incomplete_skips_a_nameless_entry():
    assert rmb.collect_incomplete(_bios([_full_member(name="", bio="")])) == []


# --------------------------------------------------------------------------
# write_csv
# --------------------------------------------------------------------------
def test_write_csv_shape():
    rows = [{
        "name": "Dr Jane Doe", "country": "Albania",
        "source": "mc", "form_link": "https://forms.example/join",
    }]
    buf = io.StringIO()
    rmb.write_csv(rows, buf)
    lines = buf.getvalue().splitlines()
    assert lines[0] == "name,country,source,form_link"
    assert lines[1] == "Dr Jane Doe,Albania,mc,https://forms.example/join"


def test_write_csv_takes_the_incomplete_column_set():
    rows = rmb.collect_incomplete(_bios([_full_member(photo="")]))
    buf = io.StringIO()
    rmb.write_csv(rows, buf,
                  fieldnames=("name", "source", "email", "missing", "form_link"))
    lines = buf.getvalue().splitlines()
    assert lines[0] == "name,source,email,missing,form_link"
    assert lines[1].startswith("Dr Jane Doe,form,jane@example.eu,photo,")


# --------------------------------------------------------------------------
# Real-fixture smoke: run against the repo data files (read-only).
# --------------------------------------------------------------------------
def test_real_data_produces_wellformed_csv():
    import csv as _csv
    root = _MOD_PATH.resolve().parent.parent
    paths = [root / "data" / f for f in
             ("mc-members.json", "indico.json", "bios.json")]
    if not all(p.exists() for p in paths):
        return  # checkout without data; skip silently
    mc, indico, bios = (json.loads(p.read_text(encoding="utf-8")) for p in paths)
    rows = rmb.collect_missing(mc, indico, bios)
    buf = io.StringIO()
    rmb.write_csv(rows, buf)
    buf.seek(0)
    parsed = list(_csv.DictReader(buf))
    assert len(parsed) == len(rows)
    for r in parsed:
        assert r["source"] in ("mc", "speaker")
        assert set(r.keys()) == {"name", "country", "source", "form_link"}


def test_real_data_incomplete_report_is_wellformed():
    root = _MOD_PATH.resolve().parent.parent
    path = root / "data" / "bios.json"
    if not path.exists():
        return  # checkout without data; skip silently
    bios = json.loads(path.read_text(encoding="utf-8"))
    rows = rmb.collect_incomplete(bios)
    names = {m.get("name") for m in bios["members"]}
    for r in rows:
        assert r["name"] in names
        assert r["missing"]
    # Worst-first ordering holds across the real roster.
    counts = [r["missing"].count(",") for r in rows]
    assert counts == sorted(counts, reverse=True)


# --------------------------------------------------------------------------
# Standalone runner (no pytest required).
# --------------------------------------------------------------------------
def _run_standalone():
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    import sys
    sys.exit(_run_standalone())
