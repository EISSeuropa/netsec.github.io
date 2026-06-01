#!/usr/bin/env python3
"""
Pytest suite for scripts/indico_clean_duplicate.py.

The script has a hyphen-free filename but lives alongside hyphenated
siblings; we load it via importlib.util.spec_from_file_location from
the relative path so the suite is robust regardless of cwd quirks.

Every network surface (requests.get / requests.delete) is stubbed.
No real HTTP call is ever issued. The logic under test is:
  - IndicoClient: token gating in __init__, header / URL logic in
    get_json, dry-run vs apply in delete, validate_admin branches.
  - list_items: flat-list (contributions) and timetable parsing,
    dedup, untitled fallback, None-id filtering.
  - clean_category: delete loop, per-item failure counting, unknown
    category bail.
  - main: PROTECTED_EVENTS guard, --force override, empty --delete,
    end-to-end dry-run wiring.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest
import requests


# ──────────────────────────── module loader ────────────────────────────

_MODULE_PATH = Path(__file__).resolve().parent / "indico_clean_duplicate.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "indico_clean_duplicate", _MODULE_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


icd = _load_module()


# ──────────────────────────── test doubles ────────────────────────────

class FakeResponse:
    """Stand-in for requests.Response covering the attributes the
    script touches: .json(), .raise_for_status(), .status_code,
    .reason."""

    def __init__(self, *, json_data=None, status_code=200, reason="OK"):
        self._json = json_data
        self.status_code = status_code
        self.reason = reason

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            err = requests.HTTPError(f"{self.status_code} {self.reason}")
            err.response = self
            raise err


@pytest.fixture(autouse=True)
def _clear_token(monkeypatch):
    """Never leak a real INDICO_WRITE_TOKEN from the environment into
    a test; each test sets it explicitly when it needs one."""
    monkeypatch.delenv(icd.ENV_WRITE_TOKEN, raising=False)


# ──────────────────────────── IndicoClient.__init__ ────────────────────────────

def test_init_apply_without_token_exits(monkeypatch):
    monkeypatch.delenv(icd.ENV_WRITE_TOKEN, raising=False)
    with pytest.raises(SystemExit) as exc:
        icd.IndicoClient(apply=True)
    assert icd.ENV_WRITE_TOKEN in str(exc.value)


def test_init_apply_with_token_ok(monkeypatch):
    monkeypatch.setenv(icd.ENV_WRITE_TOKEN, "tok-123")
    client = icd.IndicoClient(apply=True)
    assert client.apply is True
    assert client.token == "tok-123"


def test_init_dryrun_without_token_ok(monkeypatch):
    monkeypatch.delenv(icd.ENV_WRITE_TOKEN, raising=False)
    client = icd.IndicoClient(apply=False)
    assert client.apply is False
    assert client.token is None


# ──────────────────────────── get_json: headers & URL ────────────────────────────

def test_get_json_export_path_omits_bearer(monkeypatch):
    """/export/* must NOT carry an Authorization header even when a
    token is set (Indico's export API rejects Bearer)."""
    monkeypatch.setenv(icd.ENV_WRITE_TOKEN, "tok-xyz")
    client = icd.IndicoClient(apply=False)

    captured = {}

    def fake_get(url, headers=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        return FakeResponse(json_data={"ok": True})

    monkeypatch.setattr(icd.requests, "get", fake_get)
    out = client.get_json("/export/event/23.json")
    assert out == {"ok": True}
    assert captured["url"] == icd.INDICO_BASE + "/export/event/23.json"
    assert "Authorization" not in captured["headers"]
    assert captured["headers"]["Accept"] == "application/json"


def test_get_json_management_path_includes_bearer(monkeypatch):
    """Non-export paths must carry the Bearer token."""
    monkeypatch.setenv(icd.ENV_WRITE_TOKEN, "tok-xyz")
    client = icd.IndicoClient(apply=False)

    captured = {}

    def fake_get(url, headers=None, timeout=None):
        captured["headers"] = headers
        return FakeResponse(json_data={"admin": True})

    monkeypatch.setattr(icd.requests, "get", fake_get)
    client.get_json("/api/user/")
    assert captured["headers"]["Authorization"] == "Bearer tok-xyz"


def test_get_json_no_token_no_bearer(monkeypatch):
    """Without a token, even a management path gets no Authorization."""
    monkeypatch.delenv(icd.ENV_WRITE_TOKEN, raising=False)
    client = icd.IndicoClient(apply=False)

    captured = {}

    def fake_get(url, headers=None, timeout=None):
        captured["headers"] = headers
        return FakeResponse(json_data={})

    monkeypatch.setattr(icd.requests, "get", fake_get)
    client.get_json("/api/user/")
    assert "Authorization" not in captured["headers"]


def test_get_json_absolute_url_passthrough(monkeypatch):
    """A path already starting with http is used verbatim (no base prepend)."""
    monkeypatch.delenv(icd.ENV_WRITE_TOKEN, raising=False)
    client = icd.IndicoClient(apply=False)

    captured = {}

    def fake_get(url, headers=None, timeout=None):
        captured["url"] = url
        return FakeResponse(json_data={})

    monkeypatch.setattr(icd.requests, "get", fake_get)
    client.get_json("http://example.test/foo")
    assert captured["url"] == "http://example.test/foo"


def test_get_json_raises_on_http_error(monkeypatch):
    monkeypatch.delenv(icd.ENV_WRITE_TOKEN, raising=False)
    client = icd.IndicoClient(apply=False)

    def fake_get(url, headers=None, timeout=None):
        return FakeResponse(status_code=500, reason="Server Error")

    monkeypatch.setattr(icd.requests, "get", fake_get)
    with pytest.raises(requests.HTTPError):
        client.get_json("/export/event/1.json")


# ──────────────────────────── delete: dry-run vs apply ────────────────────────────

def test_delete_dryrun_returns_none_and_logs(monkeypatch, capsys):
    monkeypatch.delenv(icd.ENV_WRITE_TOKEN, raising=False)
    client = icd.IndicoClient(apply=False, verbose=True)

    def fake_delete(url, headers=None, timeout=None):
        raise AssertionError("dry-run must not issue a real DELETE")

    monkeypatch.setattr(icd.requests, "delete", fake_delete)
    out = client.delete("/event/23/manage/contributions/9")
    assert out is None
    printed = capsys.readouterr().out
    assert "WOULD DELETE" in printed
    assert icd.INDICO_BASE + "/event/23/manage/contributions/9" in printed


def test_delete_apply_issues_request(monkeypatch, capsys):
    monkeypatch.setenv(icd.ENV_WRITE_TOKEN, "tok-d")
    client = icd.IndicoClient(apply=True, verbose=True)

    captured = {}

    def fake_delete(url, headers=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        return FakeResponse(status_code=204, reason="No Content")

    monkeypatch.setattr(icd.requests, "delete", fake_delete)
    resp = client.delete("/event/23/manage/sessions/5")
    assert resp is not None
    assert captured["url"] == icd.INDICO_BASE + "/event/23/manage/sessions/5"
    assert captured["headers"]["Authorization"] == "Bearer tok-d"
    printed = capsys.readouterr().out
    # In apply mode the "WOULD " prefix is absent.
    assert "WOULD" not in printed
    assert "DELETE" in printed


def test_delete_apply_raises_on_error(monkeypatch):
    monkeypatch.setenv(icd.ENV_WRITE_TOKEN, "tok-d")
    client = icd.IndicoClient(apply=True, verbose=False)

    def fake_delete(url, headers=None, timeout=None):
        return FakeResponse(status_code=403, reason="Forbidden")

    monkeypatch.setattr(icd.requests, "delete", fake_delete)
    with pytest.raises(requests.HTTPError):
        client.delete("/event/23/manage/contributions/1")


def test_delete_quiet_suppresses_log(monkeypatch, capsys):
    monkeypatch.delenv(icd.ENV_WRITE_TOKEN, raising=False)
    client = icd.IndicoClient(apply=False, verbose=False)
    monkeypatch.setattr(icd.requests, "delete", lambda *a, **k: None)
    client.delete("/event/23/manage/contributions/9")
    assert capsys.readouterr().out == ""


# ──────────────────────────── validate_admin ────────────────────────────

def test_validate_admin_no_token_returns(monkeypatch, capsys):
    monkeypatch.delenv(icd.ENV_WRITE_TOKEN, raising=False)
    client = icd.IndicoClient(apply=False, verbose=True)
    client.validate_admin()  # should not raise
    assert "read-only enumeration" in capsys.readouterr().out


def test_validate_admin_happy_path(monkeypatch, capsys):
    monkeypatch.setenv(icd.ENV_WRITE_TOKEN, "tok-a")
    client = icd.IndicoClient(apply=True, verbose=True)
    monkeypatch.setattr(
        client, "get_json",
        lambda path: {"admin": True, "full_name": "Bot Account"},
    )
    client.validate_admin()
    assert "token OK: Bot Account (admin)" in capsys.readouterr().out


def test_validate_admin_falls_back_to_first_name(monkeypatch, capsys):
    monkeypatch.setenv(icd.ENV_WRITE_TOKEN, "tok-a")
    client = icd.IndicoClient(apply=True, verbose=True)
    monkeypatch.setattr(
        client, "get_json",
        lambda path: {"admin": True, "first_name": "Fallback"},
    )
    client.validate_admin()
    assert "Fallback" in capsys.readouterr().out


def test_validate_admin_not_admin_exits(monkeypatch):
    monkeypatch.setenv(icd.ENV_WRITE_TOKEN, "tok-a")
    client = icd.IndicoClient(apply=True, verbose=False)
    monkeypatch.setattr(client, "get_json", lambda path: {"admin": False})
    with pytest.raises(SystemExit) as exc:
        client.validate_admin()
    assert "not admin" in str(exc.value)


def test_validate_admin_unexpected_shape_exits(monkeypatch):
    monkeypatch.setenv(icd.ENV_WRITE_TOKEN, "tok-a")
    client = icd.IndicoClient(apply=True, verbose=False)
    monkeypatch.setattr(client, "get_json", lambda path: ["not", "a", "dict"])
    with pytest.raises(SystemExit) as exc:
        client.validate_admin()
    assert "unexpected" in str(exc.value)


def test_validate_admin_http_error_exits(monkeypatch):
    monkeypatch.setenv(icd.ENV_WRITE_TOKEN, "tok-a")
    client = icd.IndicoClient(apply=True, verbose=False)

    def boom(path):
        err = requests.HTTPError("401")
        err.response = FakeResponse(status_code=401, reason="Unauthorized")
        raise err

    monkeypatch.setattr(client, "get_json", boom)
    with pytest.raises(SystemExit) as exc:
        client.validate_admin()
    assert "401" in str(exc.value)


# ──────────────────────────── list_items: contributions ────────────────────────────

def _client_with_doc(monkeypatch, doc):
    """Build a dry-run client whose get_json returns a fixed doc."""
    monkeypatch.delenv(icd.ENV_WRITE_TOKEN, raising=False)
    client = icd.IndicoClient(apply=False, verbose=False)
    monkeypatch.setattr(client, "get_json", lambda path: doc)
    return client


def test_list_items_contributions_flat(monkeypatch):
    doc = {
        "results": [
            {
                "contributions": [
                    {"id": 101, "title": "Keynote"},
                    {"id": 102, "title": "Panel"},
                ]
            }
        ]
    }
    client = _client_with_doc(monkeypatch, doc)
    items = icd.list_items(client, 23, "contributions")
    assert items == [(101, "Keynote"), (102, "Panel")]


def test_list_items_contributions_skips_none_id(monkeypatch):
    doc = {
        "results": [
            {
                "contributions": [
                    {"id": None, "title": "Ghost"},
                    {"id": 5, "title": "Real"},
                ]
            }
        ]
    }
    client = _client_with_doc(monkeypatch, doc)
    items = icd.list_items(client, 23, "contributions")
    assert items == [(5, "Real")]


def test_list_items_contributions_untitled_fallback(monkeypatch):
    doc = {"results": [{"contributions": [{"id": 7}]}]}
    client = _client_with_doc(monkeypatch, doc)
    items = icd.list_items(client, 23, "contributions")
    assert items == [(7, "(untitled)")]


def test_list_items_contributions_empty_results(monkeypatch):
    client = _client_with_doc(monkeypatch, {"results": []})
    assert icd.list_items(client, 23, "contributions") == []


def test_list_items_contributions_missing_results_key(monkeypatch):
    client = _client_with_doc(monkeypatch, {})
    assert icd.list_items(client, 23, "contributions") == []


def test_list_items_contributions_missing_field(monkeypatch):
    """results present but no 'contributions' field -> empty list."""
    client = _client_with_doc(monkeypatch, {"results": [{}]})
    assert icd.list_items(client, 23, "contributions") == []


# ──────────────────────────── list_items: sessions (timetable) ────────────────────────────

def test_list_items_sessions_timetable(monkeypatch):
    doc = {
        "results": {
            "23": {
                "20271001": {
                    "e1": {"entryType": "Session", "sessionId": 9, "title": "Morning"},
                    "e2": {"entryType": "Contribution", "title": "Talk (ignored)"},
                },
                "20271002": {
                    "e3": {"entryType": "Session", "sessionId": 10, "title": "Afternoon"},
                },
            }
        }
    }
    client = _client_with_doc(monkeypatch, doc)
    items = icd.list_items(client, 23, "sessions")
    assert sorted(items) == [(9, "Morning"), (10, "Afternoon")]


def test_list_items_sessions_dedup(monkeypatch):
    """Same sessionId appearing across multiple timetable entries is
    emitted once only."""
    doc = {
        "results": {
            "23": {
                "20271001": {
                    "e1": {"entryType": "Session", "sessionId": 9, "title": "Block A"},
                    "e2": {"entryType": "Session", "sessionId": 9, "title": "Block A dup"},
                },
            }
        }
    }
    client = _client_with_doc(monkeypatch, doc)
    items = icd.list_items(client, 23, "sessions")
    assert items == [(9, "Block A")]


def test_list_items_sessions_skips_none_session_id(monkeypatch):
    doc = {
        "results": {
            "23": {
                "d1": {
                    "e1": {"entryType": "Session", "title": "No id here"},
                    "e2": {"entryType": "Session", "sessionId": 3, "title": "Has id"},
                },
            }
        }
    }
    client = _client_with_doc(monkeypatch, doc)
    items = icd.list_items(client, 23, "sessions")
    assert items == [(3, "Has id")]


def test_list_items_sessions_untitled_fallback(monkeypatch):
    doc = {
        "results": {
            "23": {
                "d1": {"e1": {"entryType": "Session", "sessionId": 4}},
            }
        }
    }
    client = _client_with_doc(monkeypatch, doc)
    items = icd.list_items(client, 23, "sessions")
    assert items == [(4, "(untitled)")]


def test_list_items_sessions_empty_timetable(monkeypatch):
    doc = {"results": {"23": {}}}
    client = _client_with_doc(monkeypatch, doc)
    assert icd.list_items(client, 23, "sessions") == []


# ──────────────────────────── clean_category ────────────────────────────

def test_clean_category_unknown_exits(monkeypatch):
    client = _client_with_doc(monkeypatch, {})
    with pytest.raises(SystemExit) as exc:
        icd.clean_category(client, 23, "bogus")
    assert "Unknown category" in str(exc.value)


def test_clean_category_dryrun_counts_all(monkeypatch, capsys):
    doc = {
        "results": [
            {"contributions": [{"id": 1, "title": "A"}, {"id": 2, "title": "B"}]}
        ]
    }
    client = _client_with_doc(monkeypatch, doc)
    # dry-run delete is a no-op returning None
    n = icd.clean_category(client, 23, "contributions")
    assert n == 2
    out = capsys.readouterr().out
    assert "contributions: 2 item(s) inherited" in out
    assert "[1] A" in out and "[2] B" in out


def test_clean_category_empty_returns_zero(monkeypatch, capsys):
    client = _client_with_doc(monkeypatch, {"results": []})
    n = icd.clean_category(client, 23, "contributions")
    assert n == 0
    assert "0 item(s) inherited" in capsys.readouterr().out


def test_clean_category_counts_failures(monkeypatch, capsys):
    """One HTTP failure subtracts from the success count."""
    doc = {
        "results": [
            {"contributions": [
                {"id": 1, "title": "ok"},
                {"id": 2, "title": "boom"},
                {"id": 3, "title": "ok2"},
            ]}
        ]
    }
    monkeypatch.setenv(icd.ENV_WRITE_TOKEN, "tok")
    client = icd.IndicoClient(apply=True, verbose=True)
    monkeypatch.setattr(client, "get_json", lambda path: doc)

    def fake_delete(path):
        if path.endswith("/2"):
            err = requests.HTTPError("403")
            err.response = FakeResponse(status_code=403, reason="Forbidden")
            raise err
        return FakeResponse(status_code=204)

    monkeypatch.setattr(client, "delete", fake_delete)
    n = icd.clean_category(client, 23, "contributions")
    assert n == 2  # 3 items, 1 failed
    out = capsys.readouterr().out
    assert "FAIL — 403 Forbidden" in out


def test_clean_category_counts_non_http_failures(monkeypatch, capsys):
    """A generic exception (e.g. connection error) also counts as a failure."""
    doc = {"results": [{"contributions": [{"id": 1, "title": "x"}]}]}
    monkeypatch.setenv(icd.ENV_WRITE_TOKEN, "tok")
    client = icd.IndicoClient(apply=True, verbose=True)
    monkeypatch.setattr(client, "get_json", lambda path: doc)

    def fake_delete(path):
        raise ConnectionError("network down")

    monkeypatch.setattr(client, "delete", fake_delete)
    n = icd.clean_category(client, 23, "contributions")
    assert n == 0
    assert "FAIL — ConnectionError: network down" in capsys.readouterr().out


def test_clean_category_truncates_long_label(monkeypatch, capsys):
    long_title = "X" * 80
    doc = {"results": [{"contributions": [{"id": 1, "title": long_title}]}]}
    client = _client_with_doc(monkeypatch, doc)
    icd.clean_category(client, 23, "contributions")
    out = capsys.readouterr().out
    assert "…" in out
    assert "X" * 80 not in out  # full untruncated title not printed
    assert "X" * 60 in out


def test_clean_category_uses_delete_path_template(monkeypatch):
    """Confirms the delete path is formatted with event_id + item_id."""
    doc = {"results": [{"contributions": [{"id": 42, "title": "t"}]}]}
    monkeypatch.setenv(icd.ENV_WRITE_TOKEN, "tok")
    client = icd.IndicoClient(apply=True, verbose=False)
    monkeypatch.setattr(client, "get_json", lambda path: doc)

    seen = []
    monkeypatch.setattr(
        client, "delete",
        lambda path: seen.append(path) or FakeResponse(status_code=204),
    )
    icd.clean_category(client, 99, "contributions")
    assert seen == ["/event/99/manage/contributions/42"]


# ──────────────────────────── main: argument / guard logic ────────────────────────────

def test_main_protected_event_refuses(monkeypatch):
    protected = sorted(icd.PROTECTED_EVENTS)[0]
    with pytest.raises(SystemExit) as exc:
        icd.main(["--event", str(protected), "--delete", "contributions"])
    assert "PROTECTED_EVENTS" in str(exc.value)


def test_main_protected_event_with_force_proceeds(monkeypatch, capsys):
    protected = sorted(icd.PROTECTED_EVENTS)[0]
    doc = {"results": []}
    monkeypatch.delenv(icd.ENV_WRITE_TOKEN, raising=False)
    monkeypatch.setattr(icd.IndicoClient, "get_json", lambda self, path: doc)
    rc = icd.main(
        ["--event", str(protected), "--delete", "contributions", "--force"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "--force in use against PROTECTED" in out


def test_main_no_delete_categories_noop(monkeypatch, capsys):
    rc = icd.main(["--event", "23"])
    assert rc == 0
    assert "nothing to do" in capsys.readouterr().out


def test_main_dryrun_end_to_end(monkeypatch, capsys):
    doc = {
        "results": [
            {"contributions": [{"id": 1, "title": "A"}, {"id": 2, "title": "B"}]}
        ]
    }
    monkeypatch.delenv(icd.ENV_WRITE_TOKEN, raising=False)
    monkeypatch.setattr(icd.IndicoClient, "get_json", lambda self, path: doc)
    # ensure no real delete is ever attempted
    monkeypatch.setattr(
        icd.requests, "delete",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no real delete")),
    )
    rc = icd.main(["--event", "23", "--delete", "contributions"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "mode=dry-run" in out
    assert "would delete 2 contributions" in out
    assert "Would delete 2 item(s) total." in out


def test_main_apply_requires_token(monkeypatch):
    """--apply without a token bails in IndicoClient.__init__ via main."""
    monkeypatch.delenv(icd.ENV_WRITE_TOKEN, raising=False)
    with pytest.raises(SystemExit) as exc:
        icd.main(["--event", "23", "--delete", "contributions", "--apply"])
    assert icd.ENV_WRITE_TOKEN in str(exc.value)


def test_main_rejects_unknown_delete_choice(monkeypatch):
    """argparse choices= rejects an unknown category with exit code 2."""
    with pytest.raises(SystemExit) as exc:
        icd.main(["--event", "23", "--delete", "nope"])
    assert exc.value.code == 2


def test_main_apply_multi_category(monkeypatch, capsys):
    """apply mode across two categories sums the deleted counts and
    reports 'Deleted'."""
    contrib_doc = {"results": [{"contributions": [{"id": 1, "title": "C"}]}]}
    session_doc = {
        "results": {
            "23": {"d1": {"e1": {"entryType": "Session", "sessionId": 8, "title": "S"}}}
        }
    }

    def fake_get_json(self, path):
        return session_doc if "timetable" in path else contrib_doc

    monkeypatch.setenv(icd.ENV_WRITE_TOKEN, "tok")
    monkeypatch.setattr(icd.IndicoClient, "get_json", fake_get_json)
    monkeypatch.setattr(
        icd.IndicoClient, "validate_admin", lambda self: None
    )
    monkeypatch.setattr(
        icd.requests, "delete",
        lambda url, headers=None, timeout=None: FakeResponse(status_code=204),
    )
    rc = icd.main([
        "--event", "23", "--apply",
        "--delete", "contributions", "--delete", "sessions",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "mode=apply" in out
    assert "Deleted 2 item(s) total." in out


# ──────────────────────────── module-level config sanity ────────────────────────────

def test_protected_events_contains_essc_2026():
    assert 22 in icd.PROTECTED_EVENTS


def test_categories_have_required_keys():
    for name, spec in icd.CATEGORIES.items():
        for key in ("list_via", "list_field", "id_field", "delete_path"):
            assert key in spec, f"{name} missing {key}"


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-q"]))
