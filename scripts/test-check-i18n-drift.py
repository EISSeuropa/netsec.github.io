#!/usr/bin/env python3
"""
Pytest suite for scripts/check-i18n-drift.py.

The script under test has hyphens in its filename, so it cannot be
imported by name; we load it via importlib from the relative path.

The module exposes a module-level ROOT (repo root) and STATE (path to
data/i18n-state.json). Several functions read those globals, so every
test that touches the filesystem monkeypatches ROOT/STATE to point at a
tmp_path sandbox. No test reads or writes a tracked file, and nothing
hits the network (the script makes no network calls at all).

High-value coverage targets called out by the task:
  - sha1(): the ?v= cache-bust normalisation before hashing.
  - report() / mark_fresh(): drift comparison, missing-file handling,
    exit codes, and the round-trip of mark_fresh -> report being fresh.

Run:
    python3 -m pytest scripts/test-check-i18n-drift.py -q
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import date
from pathlib import Path

import pytest

# --------------------------------------------------------------------------
# Load the hyphenated module by path.
# --------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
_MODULE_PATH = _HERE / "check-i18n-drift.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_i18n_drift", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()


# --------------------------------------------------------------------------
# Fixtures: a self-contained fake repo under tmp_path.
# --------------------------------------------------------------------------
@pytest.fixture
def fake_repo(tmp_path, monkeypatch):
    """Build a minimal repo tree and repoint the module globals at it.

    Returns the tmp_path root. Tests place HTML sources and the state
    file relative to it. ROOT and STATE on the module are monkeypatched
    so load_state/save_state/report/mark_fresh all operate in-sandbox.
    """
    root = tmp_path
    (root / "data").mkdir()
    state_path = root / "data" / "i18n-state.json"
    monkeypatch.setattr(mod, "ROOT", root)
    monkeypatch.setattr(mod, "STATE", state_path)
    return root


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_state(root: Path, state: dict) -> None:
    (root / "data" / "i18n-state.json").write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


# ==========================================================================
# sha1() — content hashing with cache-bust normalisation
# ==========================================================================
class TestSha1:
    def test_plain_content_matches_raw_sha1(self, tmp_path):
        f = tmp_path / "plain.html"
        text = "<html><body>hi</body></html>"
        f.write_text(text, encoding="utf-8")
        expected = hashlib.sha1(text.encode("utf-8")).hexdigest()
        assert mod.sha1(f) == expected

    def test_cache_bust_query_is_stripped_before_hashing(self, tmp_path):
        """A ?v= cache-bust on an asset path must not affect the hash:
        the stripped content must equal the bare-path file's hash."""
        with_bust = (
            '<link rel="stylesheet" '
            'href="assets/css/site.css?v=ab12cd34">'
        )
        without_bust = '<link rel="stylesheet" href="assets/css/site.css">'
        a = tmp_path / "a.html"
        b = tmp_path / "b.html"
        a.write_text(with_bust, encoding="utf-8")
        b.write_text(without_bust, encoding="utf-8")
        assert mod.sha1(a) == mod.sha1(b)

    def test_stripped_hash_equals_bare_path_string(self, tmp_path):
        """The recorded hash stays valid: stripped == pre-cache-bust file."""
        f = tmp_path / "a.html"
        f.write_text('x assets/js/site.js?v=deadbeef y', encoding="utf-8")
        bare = hashlib.sha1("x assets/js/site.js y".encode("utf-8")).hexdigest()
        assert mod.sha1(f) == bare

    def test_changing_cache_bust_value_does_not_change_hash(self, tmp_path):
        a = tmp_path / "a.html"
        b = tmp_path / "b.html"
        a.write_text('assets/css/site.css?v=00000000', encoding="utf-8")
        b.write_text('assets/css/site.css?v=ffffffff', encoding="utf-8")
        assert mod.sha1(a) == mod.sha1(b)

    def test_both_css_and_js_assets_normalised(self, tmp_path):
        a = tmp_path / "a.html"
        b = tmp_path / "b.html"
        a.write_text(
            'assets/css/main.css?v=11112222 assets/js/app.js?v=33334444',
            encoding="utf-8",
        )
        b.write_text('assets/css/main.css assets/js/app.js', encoding="utf-8")
        assert mod.sha1(a) == mod.sha1(b)

    def test_multiple_busts_all_stripped(self, tmp_path):
        a = tmp_path / "a.html"
        a.write_text(
            'assets/css/a.css?v=aaaa1111 assets/css/a.css?v=bbbb2222',
            encoding="utf-8",
        )
        bare = hashlib.sha1(
            'assets/css/a.css assets/css/a.css'.encode("utf-8")
        ).hexdigest()
        assert mod.sha1(a) == bare

    def test_meaningful_markup_change_still_flagged(self, tmp_path):
        """Only the cache-bust is exempt; any other edit changes the hash."""
        a = tmp_path / "a.html"
        b = tmp_path / "b.html"
        a.write_text('<p>one</p> assets/css/s.css?v=abc12345', encoding="utf-8")
        b.write_text('<p>two</p> assets/css/s.css?v=abc12345', encoding="utf-8")
        assert mod.sha1(a) != mod.sha1(b)

    def test_uppercase_hex_in_bust_not_matched(self, tmp_path):
        """The regex pins lowercase hex ([0-9a-f]); an uppercase value is
        NOT stripped. Asserting current behaviour, not endorsing it."""
        a = tmp_path / "a.html"
        b = tmp_path / "b.html"
        a.write_text('assets/css/s.css?v=ABCDEF12', encoding="utf-8")
        b.write_text('assets/css/s.css', encoding="utf-8")
        assert mod.sha1(a) != mod.sha1(b)

    def test_non_asset_query_not_stripped(self, tmp_path):
        """A ?v= on a non assets/css|js path is left intact."""
        a = tmp_path / "a.html"
        b = tmp_path / "b.html"
        a.write_text('img/photo.png?v=12345678', encoding="utf-8")
        b.write_text('img/photo.png', encoding="utf-8")
        assert mod.sha1(a) != mod.sha1(b)

    def test_query_with_extra_params_only_strips_v(self, tmp_path):
        """The regex only consumes the ?v=<hex> token; a trailing &foo
        is preserved in the hashed content."""
        f = tmp_path / "a.html"
        f.write_text('assets/css/s.css?v=12345678&x=1', encoding="utf-8")
        bare = hashlib.sha1('assets/css/s.css&x=1'.encode("utf-8")).hexdigest()
        assert mod.sha1(f) == bare

    def test_utf8_content_hashed_as_utf8(self, tmp_path):
        f = tmp_path / "a.html"
        text = "<p>café — naïve</p>"
        f.write_text(text, encoding="utf-8")
        assert mod.sha1(f) == hashlib.sha1(text.encode("utf-8")).hexdigest()


# ==========================================================================
# load_state / save_state — JSON round-trip against the sandboxed STATE
# ==========================================================================
class TestStateIO:
    def test_load_state_reads_state_path(self, fake_repo):
        payload = {"translations": {"a.html": {}}}
        _write_state(fake_repo, payload)
        assert mod.load_state() == payload

    def test_save_state_round_trips(self, fake_repo):
        payload = {"translations": {"x.html": {"fr": {"file": "x.fr.html"}}}}
        mod.save_state(payload)
        on_disk = json.loads(
            (fake_repo / "data" / "i18n-state.json").read_text(encoding="utf-8")
        )
        assert on_disk == payload

    def test_save_state_preserves_non_ascii(self, fake_repo):
        """ensure_ascii=False: accented characters stored verbatim."""
        payload = {"translations": {"é.html": {}}}
        mod.save_state(payload)
        raw = (fake_repo / "data" / "i18n-state.json").read_text(encoding="utf-8")
        assert "é.html" in raw
        assert raw.endswith("\n")

    def test_load_after_save_round_trip(self, fake_repo):
        payload = {"translations": {"p.html": {"de": {"file": "p.de.html"}}}}
        mod.save_state(payload)
        assert mod.load_state() == payload


# ==========================================================================
# report() — drift comparison, exit codes, missing-file handling
# ==========================================================================
class TestReport:
    def _make_pair(self, root, src_name, tgt_name, src_text, tgt_text="x"):
        _write(root / src_name, src_text)
        _write(root / tgt_name, tgt_text)

    def test_no_translations_returns_zero(self, fake_repo, capsys):
        assert mod.report({"translations": {}}) == 0
        assert "No translations registered" in capsys.readouterr().out

    def test_empty_dict_returns_zero(self, fake_repo, capsys):
        assert mod.report({}) == 0

    def test_fresh_translation_returns_zero(self, fake_repo, capsys):
        src_text = "<p>hello</p>"
        self._make_pair(fake_repo, "a.html", "a.fr.html", src_text)
        current = mod.sha1(fake_repo / "a.html")
        state = {
            "translations": {
                "a.html": {
                    "fr": {
                        "file": "a.fr.html",
                        "source_sha1": current,
                        "translated_on": "2026-01-01",
                    }
                }
            }
        }
        assert mod.report(state) == 0
        out = capsys.readouterr().out
        assert "fresh" in out
        assert "All translations match" in out

    def test_stale_translation_returns_one(self, fake_repo, capsys):
        self._make_pair(fake_repo, "a.html", "a.fr.html", "<p>new content</p>")
        state = {
            "translations": {
                "a.html": {
                    "fr": {
                        "file": "a.fr.html",
                        "source_sha1": "0" * 40,  # never matches
                        "translated_on": "2025-12-01",
                    }
                }
            }
        }
        assert mod.report(state) == 1
        out = capsys.readouterr().out
        assert "stale" in out
        assert "drifted" in out

    def test_missing_english_source_returns_two(self, fake_repo, capsys):
        # No source file on disk.
        state = {
            "translations": {
                "gone.html": {
                    "fr": {"file": "gone.fr.html", "source_sha1": "x"}
                }
            }
        }
        assert mod.report(state) == 2
        out = capsys.readouterr().out
        assert "missing" in out
        assert "English source not found" in out

    def test_missing_target_returns_two(self, fake_repo, capsys):
        _write(fake_repo / "a.html", "<p>hi</p>")
        # Target file absent.
        state = {
            "translations": {
                "a.html": {
                    "fr": {"file": "a.fr.html", "source_sha1": "x"}
                }
            }
        }
        assert mod.report(state) == 2
        out = capsys.readouterr().out
        assert "expected a.fr.html" in out

    def test_exit_code_is_max_across_rows(self, fake_repo, capsys):
        """A missing source (2) outranks a mere stale (1)."""
        # Stale pair.
        self._make_pair(fake_repo, "a.html", "a.fr.html", "<p>x</p>")
        state = {
            "translations": {
                "a.html": {
                    "fr": {
                        "file": "a.fr.html",
                        "source_sha1": "0" * 40,
                        "translated_on": "2025-01-01",
                    }
                },
                "gone.html": {  # missing source -> 2
                    "de": {"file": "gone.de.html", "source_sha1": "x"}
                },
            }
        }
        assert mod.report(state) == 2

    def test_multiple_langs_one_stale_one_fresh(self, fake_repo, capsys):
        src_text = "<p>multi</p>"
        _write(fake_repo / "a.html", src_text)
        _write(fake_repo / "a.fr.html", "fr")
        _write(fake_repo / "a.de.html", "de")
        current = mod.sha1(fake_repo / "a.html")
        state = {
            "translations": {
                "a.html": {
                    "fr": {
                        "file": "a.fr.html",
                        "source_sha1": current,
                        "translated_on": "2026-01-01",
                    },
                    "de": {
                        "file": "a.de.html",
                        "source_sha1": "stale",
                        "translated_on": "2025-01-01",
                    },
                }
            }
        }
        # One stale -> exit 1.
        assert mod.report(state) == 1
        out = capsys.readouterr().out
        assert "fresh" in out and "stale" in out

    def test_cache_bust_only_change_reads_fresh(self, fake_repo, capsys):
        """End-to-end of issue #416: bumping a ?v= asset query must NOT
        flag the page as drifted. Record the hash of the bare-path
        version, then change only the cache-bust on disk."""
        bare = '<link href="assets/css/site.css">'
        # Compute recorded hash from the bare version.
        tmp = fake_repo / "_bare.html"
        _write(tmp, bare)
        recorded_hash = mod.sha1(tmp)
        # Now the live source carries a cache-bust query.
        _write(fake_repo / "a.html", '<link href="assets/css/site.css?v=abc12345">')
        _write(fake_repo / "a.fr.html", "fr")
        state = {
            "translations": {
                "a.html": {
                    "fr": {
                        "file": "a.fr.html",
                        "source_sha1": recorded_hash,
                        "translated_on": "2026-01-01",
                    }
                }
            }
        }
        assert mod.report(state) == 0


# ==========================================================================
# mark_fresh() — blessing a translation, error paths, save side-effect
# ==========================================================================
class TestMarkFresh:
    def test_unknown_entry_returns_two(self, fake_repo, capsys):
        state = {"translations": {}}
        assert mod.mark_fresh(state, "nope.html", "fr") == 2
        assert "no entry" in capsys.readouterr().out

    def test_unknown_lang_returns_two(self, fake_repo, capsys):
        state = {"translations": {"a.html": {"fr": {"file": "a.fr.html"}}}}
        assert mod.mark_fresh(state, "a.html", "de") == 2

    def test_missing_files_returns_two(self, fake_repo, capsys):
        # Entry exists but neither file is on disk.
        state = {"translations": {"a.html": {"fr": {"file": "a.fr.html"}}}}
        assert mod.mark_fresh(state, "a.html", "fr") == 2
        assert "missing" in capsys.readouterr().out

    def test_success_updates_hash_and_date_and_saves(self, fake_repo, capsys):
        src_text = "<p>bless me</p>"
        _write(fake_repo / "a.html", src_text)
        _write(fake_repo / "a.fr.html", "fr")
        state = {
            "translations": {
                "a.html": {
                    "fr": {
                        "file": "a.fr.html",
                        "source_sha1": "old",
                        "translated_on": "2000-01-01",
                    }
                }
            }
        }
        rc = mod.mark_fresh(state, "a.html", "fr")
        assert rc == 0
        entry = state["translations"]["a.html"]["fr"]
        assert entry["source_sha1"] == mod.sha1(fake_repo / "a.html")
        assert entry["translated_on"] == date.today().isoformat()
        # save_state wrote to the sandboxed STATE.
        on_disk = json.loads(
            (fake_repo / "data" / "i18n-state.json").read_text(encoding="utf-8")
        )
        assert on_disk == state
        assert "Marked a.fr.html as fresh" in capsys.readouterr().out

    def test_mark_fresh_then_report_is_fresh(self, fake_repo, capsys):
        """Round-trip: bless a translation, then a report on the same
        state reports it fresh (exit 0)."""
        _write(fake_repo / "a.html", "<p>round trip</p>")
        _write(fake_repo / "a.fr.html", "fr")
        state = {
            "translations": {
                "a.html": {
                    "fr": {
                        "file": "a.fr.html",
                        "source_sha1": "stale",
                        "translated_on": "2000-01-01",
                    }
                }
            }
        }
        assert mod.mark_fresh(state, "a.html", "fr") == 0
        capsys.readouterr()  # drain
        assert mod.report(state) == 0

    def test_mark_fresh_normalises_cache_bust(self, fake_repo, capsys):
        """The blessed hash is computed through sha1(), so it is the
        cache-bust-normalised hash."""
        _write(fake_repo / "a.html", 'assets/css/s.css?v=12345678')
        _write(fake_repo / "a.fr.html", "fr")
        state = {
            "translations": {"a.html": {"fr": {"file": "a.fr.html"}}}
        }
        mod.mark_fresh(state, "a.html", "fr")
        bare = hashlib.sha1("assets/css/s.css".encode("utf-8")).hexdigest()
        assert state["translations"]["a.html"]["fr"]["source_sha1"] == bare


# ==========================================================================
# main() — argparse wiring dispatches to report vs mark_fresh
# ==========================================================================
class TestMain:
    def test_main_no_args_calls_report(self, fake_repo, monkeypatch, capsys):
        _write_state(fake_repo, {"translations": {}})
        monkeypatch.setattr(__import__("sys"), "argv", ["check-i18n-drift.py"])
        assert mod.main() == 0

    def test_main_mark_fresh_dispatch(self, fake_repo, monkeypatch, capsys):
        _write(fake_repo / "a.html", "<p>m</p>")
        _write(fake_repo / "a.fr.html", "fr")
        _write_state(
            fake_repo,
            {"translations": {"a.html": {"fr": {"file": "a.fr.html"}}}},
        )
        monkeypatch.setattr(
            __import__("sys"),
            "argv",
            ["check-i18n-drift.py", "--mark-fresh", "a.html", "fr"],
        )
        assert mod.main() == 0
        # State on disk was updated by the mark_fresh path.
        on_disk = mod.load_state()
        entry = on_disk["translations"]["a.html"]["fr"]
        assert entry["source_sha1"] == mod.sha1(fake_repo / "a.html")

    def test_main_mark_fresh_unknown_returns_two(self, fake_repo, monkeypatch, capsys):
        _write_state(fake_repo, {"translations": {}})
        monkeypatch.setattr(
            __import__("sys"),
            "argv",
            ["check-i18n-drift.py", "--mark-fresh", "nope.html", "fr"],
        )
        assert mod.main() == 2