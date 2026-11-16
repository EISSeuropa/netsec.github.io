"""Tests for report-unthemed-keywords.py, the monthly keyword-themes issue body."""
from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("report_unthemed", HERE / "report-unthemed-keywords.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

THEMES = {
    "geopolitics": "Foreign policy and diplomacy",
    "great power competition": "Foreign policy and diplomacy",
    "arctic security": "Security and defence",
    "cyber security": "Cyber and emerging technology",
}


def test_candidates_rank_by_shared_word_count():
    assert mod.candidate_themes("Arctic geopolitics", THEMES) == [
        ("Foreign policy and diplomacy", "geopolitics"),
        ("Security and defence", "arctic security"),
    ]


def test_candidates_capped_and_empty_when_nothing_shared():
    assert len(mod.candidate_themes("security geopolitics", THEMES, limit=1)) == 1
    assert mod.candidate_themes("Quantum key distribution", THEMES) == []


def test_body_lists_each_keyword_with_members_and_hints():
    body = mod.render_body({"Arctic geopolitics": ["Dr B", "Dr A", "Dr A"], "Quantum | key": ["Prof C"]},
                           THEMES, date(2026, 12, 1))
    assert body.startswith("2 keyword(s) on member profiles have no research theme, as of 2026-12-01.")
    assert "| Arctic geopolitics | Dr A, Dr B | Foreign policy and diplomacy (like _geopolitics_)" in body
    assert "| Quantum \\| key | Prof C | none found |" in body
    assert "- Cyber and emerging technology" in body


def test_main_writes_a_body_only_when_a_keyword_is_unplaced(tmp_path):
    # The script writes a body exactly when the shape check finds an
    # unplaced keyword, whatever the committed data holds today.
    out = tmp_path / "body.md"
    import json
    data = json.loads((mod.REPO / "data" / "bios.json").read_text(encoding="utf-8"))
    expected = len(mod.shape.unthemed_keywords(data))
    assert mod.main([str(out)]) == 0
    assert out.exists() == (expected > 0)


def test_runs_without_third_party_modules(tmp_path, monkeypatch):
    # The workflow installs nothing, so the script must load on the standard
    # library alone (its first run failed importing sync-bios.py).
    import runpy, sys
    for name in ("requests", "bs4", "PIL"):
        monkeypatch.setitem(sys.modules, name, None)
    monkeypatch.setattr(sys, "argv", ["report", str(tmp_path / "body.md")])
    try:
        runpy.run_path(str(HERE / "report-unthemed-keywords.py"), run_name="__main__")
    except SystemExit as exc:
        assert exc.code == 0
