"""Test suite for scripts/indico_patch.py.

The module filename uses a hyphen-free underscore name but lives next to
hyphenated siblings; the project's convention is `test-<name>.py`, which is
not importable by name, so we load the module under test via importlib from
its relative path.

All network IO is stubbed. No real HTTP calls are ever made. File IO uses
tmp_path; no tracked repo file is mutated.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

# ──────────────────────────── module loading ────────────────────────────

_MODULE_PATH = Path(__file__).resolve().parent / "indico_patch.py"
_spec = importlib.util.spec_from_file_location("indico_patch_under_test", _MODULE_PATH)
mod = importlib.util.module_from_spec(_spec)
# Register before exec: the module uses @dataclass with field(default_factory),
# and on Python 3.9 the dataclasses ClassVar heuristic reads
# sys.modules[cls.__module__].__dict__, which is None for an unregistered
# module and raises AttributeError at class-definition time.
sys.modules[_spec.name] = mod
_spec.loader.exec_module(mod)


# ──────────────────────────── fakes ────────────────────────────

class FakeResponse:
    """Minimal stand-in for a requests.Response."""

    def __init__(self, json_data=None, text="", content=b"x", status=200):
        self._json = json_data
        self.text = text
        self.content = content
        self.status_code = status

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            err = mod.requests.HTTPError(f"HTTP {self.status_code}")
            err.response = self
            raise err


class RecordingClient:
    """A test double for IndicoClient that records calls and returns canned
    data, so resolver / dispatch logic can be exercised without HTTP."""

    def __init__(self, *, apply=False, get_map=None):
        self.apply = apply
        self.verbose = False
        self._get_map = get_map or {}
        self.gets = []
        self.patches = []
        self.posts = []

    def get_json(self, path, *, params=None):
        self.gets.append((path, params))
        if path in self._get_map:
            val = self._get_map[path]
            if isinstance(val, Exception):
                raise val
            return val
        raise AssertionError(f"unexpected get_json: {path!r}")

    def patch_json(self, path, payload):
        self.patches.append((path, payload))
        return {} if not self.apply else {"ok": True}

    def post_form(self, path, form):
        self.posts.append((path, form))
        return None if not self.apply else "ok"


# ──────────────────────────── _resolved_cache_path ────────────────────────────

def test_resolved_cache_path_appends_suffix(tmp_path):
    p = tmp_path / "fix-plan.yaml"
    cache = mod._resolved_cache_path(p)
    assert cache.name == "fix-plan.yaml.resolved.json"
    assert cache.parent == tmp_path


# ──────────────────────────── FixPlan.from_yaml ────────────────────────────

GOOD_YAML = """\
event_id: 42
patches:
  - kind: session
    by: friendlyId
    ref: 43
    set:
      title: New Session Name
    note: fix typo
  - kind: person
    by: name
    ref: Julia Carver
    in_session: 43
    set:
      affiliation: Oxford
"""


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_from_yaml_parses_event_and_patches(tmp_path):
    p = _write(tmp_path, "plan.yaml", GOOD_YAML)
    plan = mod.FixPlan.from_yaml(p)
    assert plan.event_id == 42
    assert len(plan.patches) == 2
    p0, p1 = plan.patches
    assert p0.kind == "session"
    assert p0.by == "friendlyId"
    assert p0.ref == 43
    assert p0.set == {"title": "New Session Name"}
    assert p0.note == "fix typo"
    assert p0.in_session is None
    assert p1.kind == "person"
    assert p1.in_session == 43
    assert p1.note is None
    assert p0.resolved == {}  # no sidecar cache present


def test_from_yaml_coerces_event_id_to_int(tmp_path):
    p = _write(tmp_path, "plan.yaml", 'event_id: "99"\npatches: []\n')
    plan = mod.FixPlan.from_yaml(p)
    assert plan.event_id == 99
    assert isinstance(plan.event_id, int)


def test_from_yaml_loads_resolved_cache_sidecar(tmp_path):
    p = _write(tmp_path, "plan.yaml", GOOD_YAML)
    cache = mod._resolved_cache_path(p)
    cache.write_text(json.dumps({"1": {"session_id": 117}}), encoding="utf-8")
    plan = mod.FixPlan.from_yaml(p)
    # patch index 1 (1-based) gets its resolved cache injected
    assert plan.patches[0].resolved == {"session_id": 117}
    assert plan.patches[1].resolved == {}


def test_from_yaml_tolerates_corrupt_cache(tmp_path):
    p = _write(tmp_path, "plan.yaml", GOOD_YAML)
    cache = mod._resolved_cache_path(p)
    cache.write_text("{not valid json", encoding="utf-8")
    plan = mod.FixPlan.from_yaml(p)  # must not raise
    assert plan.patches[0].resolved == {}


def test_from_yaml_missing_top_level_keys_exits(tmp_path):
    p = _write(tmp_path, "plan.yaml", "patches: []\n")  # no event_id
    with pytest.raises(SystemExit):
        mod.FixPlan.from_yaml(p)


def test_from_yaml_non_mapping_doc_exits(tmp_path):
    p = _write(tmp_path, "plan.yaml", "- just\n- a\n- list\n")
    with pytest.raises(SystemExit):
        mod.FixPlan.from_yaml(p)


def test_from_yaml_patch_missing_required_key_exits(tmp_path):
    bad = "event_id: 1\npatches:\n  - kind: session\n    by: friendlyId\n    ref: 1\n"  # no `set`
    p = _write(tmp_path, "plan.yaml", bad)
    with pytest.raises(SystemExit):
        mod.FixPlan.from_yaml(p)


# ──────────────────────────── FixPlan.write_cache ────────────────────────────

def test_write_cache_writes_resolved_only(tmp_path):
    p = _write(tmp_path, "plan.yaml", GOOD_YAML)
    plan = mod.FixPlan.from_yaml(p)
    plan.patches[0].resolved = {"session_id": 117}
    # patch[1] left empty → excluded
    plan.write_cache(p)
    cache = mod._resolved_cache_path(p)
    assert cache.exists()
    data = json.loads(cache.read_text())
    assert data == {"1": {"session_id": 117}}
    assert "2" not in data


def test_write_cache_noop_when_nothing_resolved(tmp_path):
    p = _write(tmp_path, "plan.yaml", GOOD_YAML)
    plan = mod.FixPlan.from_yaml(p)
    plan.write_cache(p)
    assert not mod._resolved_cache_path(p).exists()


def test_write_cache_roundtrips_through_from_yaml(tmp_path):
    p = _write(tmp_path, "plan.yaml", GOOD_YAML)
    plan = mod.FixPlan.from_yaml(p)
    plan.patches[1].resolved = {"person_id": 555}
    plan.write_cache(p)
    reloaded = mod.FixPlan.from_yaml(p)
    assert reloaded.patches[1].resolved == {"person_id": 555}


# ──────────────────────────── IndicoClient construction / gating ─────────────

def test_apply_without_write_token_exits(monkeypatch):
    monkeypatch.delenv(mod.ENV_WRITE_TOKEN, raising=False)
    monkeypatch.delenv(mod.ENV_READ_TOKEN, raising=False)
    with pytest.raises(SystemExit):
        mod.IndicoClient(apply=True)


def test_dry_run_without_token_is_allowed(monkeypatch):
    monkeypatch.delenv(mod.ENV_WRITE_TOKEN, raising=False)
    monkeypatch.delenv(mod.ENV_READ_TOKEN, raising=False)
    c = mod.IndicoClient(apply=False)
    assert c.apply is False
    assert c.write_token is None


def test_read_token_falls_back_to_write_token(monkeypatch):
    monkeypatch.delenv(mod.ENV_READ_TOKEN, raising=False)
    monkeypatch.setenv(mod.ENV_WRITE_TOKEN, "wtok")
    c = mod.IndicoClient(apply=False)
    assert c.read_token == "wtok"


# ──────────────────────────── IndicoClient.get_json ────────────────────────────

def test_get_json_sends_bearer_for_api(monkeypatch):
    monkeypatch.setenv(mod.ENV_READ_TOKEN, "rtok")
    captured = {}

    def fake_get(url, headers=None, params=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        return FakeResponse(json_data={"ok": 1})

    monkeypatch.setattr(mod.requests, "get", fake_get)
    c = mod.IndicoClient(apply=False)
    out = c.get_json("/api/user/")
    assert out == {"ok": 1}
    assert captured["url"] == mod.INDICO_BASE + "/api/user/"
    assert captured["headers"]["Authorization"] == "Bearer rtok"


def test_get_json_omits_bearer_for_export(monkeypatch):
    monkeypatch.setenv(mod.ENV_READ_TOKEN, "rtok")
    captured = {}

    def fake_get(url, headers=None, params=None, timeout=None):
        captured["headers"] = headers
        return FakeResponse(json_data={})

    monkeypatch.setattr(mod.requests, "get", fake_get)
    c = mod.IndicoClient(apply=False)
    c.get_json("/export/event/1.json")
    assert "Authorization" not in captured["headers"]


def test_get_json_passes_full_url_unchanged(monkeypatch):
    monkeypatch.delenv(mod.ENV_READ_TOKEN, raising=False)
    monkeypatch.delenv(mod.ENV_WRITE_TOKEN, raising=False)
    captured = {}

    def fake_get(url, headers=None, params=None, timeout=None):
        captured["url"] = url
        return FakeResponse(json_data={})

    monkeypatch.setattr(mod.requests, "get", fake_get)
    c = mod.IndicoClient(apply=False)
    c.get_json("https://elsewhere.example/x")
    assert captured["url"] == "https://elsewhere.example/x"


def test_get_json_raises_on_http_error(monkeypatch):
    monkeypatch.setenv(mod.ENV_READ_TOKEN, "rtok")

    def fake_get(url, headers=None, params=None, timeout=None):
        return FakeResponse(status=404)

    monkeypatch.setattr(mod.requests, "get", fake_get)
    c = mod.IndicoClient(apply=False)
    with pytest.raises(mod.requests.HTTPError):
        c.get_json("/api/user/")


# ──────────────────────────── IndicoClient write gating ────────────────────────────

def test_patch_json_dry_run_returns_none_and_does_not_call(monkeypatch):
    monkeypatch.setenv(mod.ENV_WRITE_TOKEN, "wtok")
    called = []
    monkeypatch.setattr(mod.requests, "patch",
                        lambda *a, **k: called.append(1) or FakeResponse(json_data={}))
    c = mod.IndicoClient(apply=False, verbose=False)
    assert c.patch_json("/event/1/manage/persons/9", {"affiliation": "X"}) is None
    assert called == []  # no real request issued in dry-run


def test_patch_json_apply_issues_request(monkeypatch):
    monkeypatch.setenv(mod.ENV_WRITE_TOKEN, "wtok")
    captured = {}

    def fake_patch(url, headers=None, json=None, timeout=None):
        captured.update(url=url, headers=headers, json=json)
        return FakeResponse(json_data={"done": True}, content=b"{}")

    monkeypatch.setattr(mod.requests, "patch", fake_patch)
    c = mod.IndicoClient(apply=True, verbose=False)
    out = c.patch_json("/event/1/manage/persons/9", {"affiliation": "X"})
    assert out == {"done": True}
    assert captured["headers"]["Authorization"] == "Bearer wtok"
    assert captured["json"] == {"affiliation": "X"}
    assert captured["url"].endswith("/manage/persons/9")


def test_patch_json_apply_empty_body_returns_empty_dict(monkeypatch):
    monkeypatch.setenv(mod.ENV_WRITE_TOKEN, "wtok")

    def fake_patch(url, headers=None, json=None, timeout=None):
        return FakeResponse(json_data=None, content=b"")  # 204-style empty

    monkeypatch.setattr(mod.requests, "patch", fake_patch)
    c = mod.IndicoClient(apply=True, verbose=False)
    assert c.patch_json("/x", {"a": 1}) == {}


def test_post_form_dry_run_returns_none(monkeypatch):
    monkeypatch.setenv(mod.ENV_WRITE_TOKEN, "wtok")
    called = []
    monkeypatch.setattr(mod.requests, "post",
                        lambda *a, **k: called.append(1) or FakeResponse(text="x"))
    c = mod.IndicoClient(apply=False, verbose=False)
    assert c.post_form("/x", {"title": "T"}) is None
    assert called == []


def test_post_form_apply_sends_form_data(monkeypatch):
    monkeypatch.setenv(mod.ENV_WRITE_TOKEN, "wtok")
    captured = {}

    def fake_post(url, headers=None, data=None, timeout=None):
        captured.update(url=url, headers=headers, data=data)
        return FakeResponse(text="body")

    monkeypatch.setattr(mod.requests, "post", fake_post)
    c = mod.IndicoClient(apply=True, verbose=False)
    out = c.post_form("/event/1/manage/sessions/5/modify", {"title": "T"})
    assert out == "body"
    assert captured["data"] == {"title": "T"}
    assert captured["headers"]["Authorization"] == "Bearer wtok"


# ──────────────────────────── _log_intent ────────────────────────────

def test_log_intent_prefixes_would_in_dry_run(monkeypatch, capsys):
    monkeypatch.delenv(mod.ENV_WRITE_TOKEN, raising=False)
    monkeypatch.delenv(mod.ENV_READ_TOKEN, raising=False)
    c = mod.IndicoClient(apply=False, verbose=True)
    c._log_intent("PATCH", "http://x/y", {"a": 1})
    out = capsys.readouterr().out
    assert "WOULD PATCH http://x/y" in out
    assert '"a": 1' in out


def test_log_intent_truncates_long_body(monkeypatch, capsys):
    monkeypatch.setenv(mod.ENV_WRITE_TOKEN, "wtok")
    c = mod.IndicoClient(apply=True, verbose=True)
    big = {"k": "v" * 1000}
    c._log_intent("POST", "http://x", big)
    out = capsys.readouterr().out
    assert "…" in out
    assert "WOULD" not in out  # apply mode: no WOULD prefix


def test_log_intent_silent_when_not_verbose(monkeypatch, capsys):
    monkeypatch.delenv(mod.ENV_WRITE_TOKEN, raising=False)
    c = mod.IndicoClient(apply=False, verbose=False)
    c._log_intent("PATCH", "http://x", {"a": 1})
    assert capsys.readouterr().out == ""


# ──────────────────────────── validate_token ────────────────────────────

def test_validate_token_noop_without_token(monkeypatch):
    monkeypatch.delenv(mod.ENV_WRITE_TOKEN, raising=False)
    monkeypatch.delenv(mod.ENV_READ_TOKEN, raising=False)
    c = mod.IndicoClient(apply=False)
    # No exception, no network access (requests.get not patched -> would fail).
    c.validate_token()


def test_validate_token_ok_prints_name(monkeypatch, capsys):
    monkeypatch.setenv(mod.ENV_WRITE_TOKEN, "wtok")
    monkeypatch.setattr(mod.requests, "get",
                        lambda *a, **k: FakeResponse(json_data={"full_name": "Bot User"}))
    c = mod.IndicoClient(apply=True, verbose=True)
    c.validate_token()
    assert "Bot User" in capsys.readouterr().out


def test_validate_token_http_error_exits(monkeypatch):
    monkeypatch.setenv(mod.ENV_WRITE_TOKEN, "wtok")

    def fake_get(url, headers=None, params=None, timeout=None):
        return FakeResponse(status=403)

    monkeypatch.setattr(mod.requests, "get", fake_get)
    c = mod.IndicoClient(apply=True, verbose=False)
    with pytest.raises(SystemExit):
        c.validate_token()


# ──────────────────────────── Resolver.session_id ────────────────────────────

def _timetable_doc(event_id, entries):
    """Build an /export/timetable/<id>.json shaped doc."""
    return {"results": {str(event_id): {"day1": entries}}}


def _make_resolver(event_id, get_map):
    client = RecordingClient(get_map=get_map)
    return mod.Resolver(client, event_id), client


def test_session_id_by_friendly_id():
    tt = _timetable_doc(42, {
        "e1": {"entryType": "Session", "sessionId": 117, "friendlyId": 43, "title": "Opening"},
        "e2": {"entryType": "Session", "sessionId": 200, "friendlyId": 44, "title": "Closing"},
        "e3": {"entryType": "Contribution", "sessionId": 999, "friendlyId": 43, "title": "noise"},
    })
    r, _ = _make_resolver(42, {"/export/timetable/42.json": tt})
    assert r.session_id(by="friendlyId", ref=43) == 117
    assert r.session_id(by="friendlyId", ref="44") == 200  # ref coerced to int


def test_session_id_by_title_match_case_insensitive():
    tt = _timetable_doc(42, {
        "e1": {"entryType": "Session", "sessionId": 117, "friendlyId": 43, "title": "Opening Plenary"},
    })
    r, _ = _make_resolver(42, {"/export/timetable/42.json": tt})
    assert r.session_id(by="title_match", ref="plenary") == 117


def test_session_id_no_match_raises():
    tt = _timetable_doc(42, {
        "e1": {"entryType": "Session", "sessionId": 117, "friendlyId": 43, "title": "Opening"},
    })
    r, _ = _make_resolver(42, {"/export/timetable/42.json": tt})
    with pytest.raises(LookupError):
        r.session_id(by="friendlyId", ref=999)


def test_session_id_ambiguous_distinct_ids_raises():
    tt = _timetable_doc(42, {
        "e1": {"entryType": "Session", "sessionId": 117, "friendlyId": 43, "title": "Workshop A"},
        "e2": {"entryType": "Session", "sessionId": 118, "friendlyId": 44, "title": "Workshop B"},
    })
    r, _ = _make_resolver(42, {"/export/timetable/42.json": tt})
    with pytest.raises(LookupError):
        r.session_id(by="title_match", ref="workshop")


def test_session_id_same_session_twice_not_ambiguous():
    # Two timetable blocks of the SAME session id -> unique set of 1 -> ok.
    tt = _timetable_doc(42, {
        "e1": {"entryType": "Session", "sessionId": 117, "friendlyId": 43, "title": "Track block 1"},
        "e2": {"entryType": "Session", "sessionId": 117, "friendlyId": 43, "title": "Track block 2"},
    })
    r, _ = _make_resolver(42, {"/export/timetable/42.json": tt})
    assert r.session_id(by="title_match", ref="track") == 117


def test_timetable_data_cached_single_fetch():
    tt = _timetable_doc(42, {
        "e1": {"entryType": "Session", "sessionId": 117, "friendlyId": 43, "title": "X"},
    })
    r, client = _make_resolver(42, {"/export/timetable/42.json": tt})
    r.session_id(by="friendlyId", ref=43)
    r.session_id(by="friendlyId", ref=43)
    assert sum(1 for path, _ in client.gets if path == "/export/timetable/42.json") == 1


# ──────────────────────────── Resolver.contribution_id ────────────────────────────

def _event_contribs_doc(contribs):
    return {"results": [{"contributions": contribs}]}


def test_contribution_id_by_title_match():
    doc = _event_contribs_doc([
        {"id": 501, "title": "Keynote on Quantum"},
        {"id": 502, "title": "Lightning talks"},
    ])
    r, _ = _make_resolver(42, {"/export/event/42.json": doc})
    assert r.contribution_id(by="title_match", ref="quantum") == 501


def test_contribution_id_by_id_uses_db_id_fallback():
    doc = _event_contribs_doc([
        {"db_id": 777, "title": "No id field, only db_id"},
    ])
    r, _ = _make_resolver(42, {"/export/event/42.json": doc})
    assert r.contribution_id(by="id", ref=777) == 777


def test_contribution_id_no_match_raises():
    doc = _event_contribs_doc([{"id": 501, "title": "A"}])
    r, _ = _make_resolver(42, {"/export/event/42.json": doc})
    with pytest.raises(LookupError):
        r.contribution_id(by="id", ref=999)


def test_contribution_id_ambiguous_raises():
    doc = _event_contribs_doc([
        {"id": 501, "title": "Panel north"},
        {"id": 502, "title": "Panel south"},
    ])
    r, _ = _make_resolver(42, {"/export/event/42.json": doc})
    with pytest.raises(LookupError):
        r.contribution_id(by="title_match", ref="panel")


# ──────────────────────────── Resolver.person_id ────────────────────────────

def test_person_id_resolves_convener_by_name():
    tt = _timetable_doc(42, {
        "e1": {"entryType": "Session", "sessionId": 117, "friendlyId": 43, "title": "S"},
    })
    conveners = {"conveners": [
        {"fullName": "Julia Carver", "personId": 88},
        {"fullName": "Sam Other", "personId": 89},
    ]}
    get_map = {
        "/export/timetable/42.json": tt,
        "/event/42/manage/sessions/117/conveners": conveners,
    }
    r, _ = _make_resolver(42, get_map)
    assert r.person_id(in_session=43, by="name", ref="julia") == 88


def test_person_id_bare_list_shape():
    tt = _timetable_doc(42, {
        "e1": {"entryType": "Session", "sessionId": 117, "friendlyId": 43, "title": "S"},
    })
    # bare list + snake_case keys
    conveners = [{"full_name": "Julia Carver", "person_id": 88}]
    get_map = {
        "/export/timetable/42.json": tt,
        "/event/42/manage/sessions/117/conveners": conveners,
    }
    r, _ = _make_resolver(42, get_map)
    assert r.person_id(in_session=43, by="name", ref="carver") == 88


def test_person_id_requires_in_session():
    r, _ = _make_resolver(42, {})
    with pytest.raises(LookupError):
        r.person_id(in_session=None, by="name", ref="x")


def test_person_id_unsupported_mode_raises():
    tt = _timetable_doc(42, {
        "e1": {"entryType": "Session", "sessionId": 117, "friendlyId": 43, "title": "S"},
    })
    get_map = {
        "/export/timetable/42.json": tt,
        "/event/42/manage/sessions/117/conveners": {"conveners": []},
    }
    r, _ = _make_resolver(42, get_map)
    with pytest.raises(LookupError):
        r.person_id(in_session=43, by="email", ref="x@y")


def test_person_id_unexpected_shape_raises():
    tt = _timetable_doc(42, {
        "e1": {"entryType": "Session", "sessionId": 117, "friendlyId": 43, "title": "S"},
    })
    get_map = {
        "/export/timetable/42.json": tt,
        "/event/42/manage/sessions/117/conveners": {"conveners": "not-a-list"},
    }
    r, _ = _make_resolver(42, get_map)
    with pytest.raises(LookupError):
        r.person_id(in_session=43, by="name", ref="x")


def test_person_id_ambiguous_raises():
    tt = _timetable_doc(42, {
        "e1": {"entryType": "Session", "sessionId": 117, "friendlyId": 43, "title": "S"},
    })
    conveners = {"conveners": [
        {"fullName": "Anna Lee", "personId": 1},
        {"fullName": "Anna Leeson", "personId": 2},
    ]}
    get_map = {
        "/export/timetable/42.json": tt,
        "/event/42/manage/sessions/117/conveners": conveners,
    }
    r, _ = _make_resolver(42, get_map)
    with pytest.raises(LookupError):
        r.person_id(in_session=43, by="name", ref="anna lee")


# ──────────────────────────── apply_session_patch ────────────────────────────

def test_apply_session_patch_sets_title_and_room():
    tt = _timetable_doc(42, {
        "e1": {"entryType": "Session", "sessionId": 117, "friendlyId": 43, "title": "Old"},
    })
    modify_doc = {"form_data": {"title": "Old", "location_data": {"room_name": "R1"}}}
    get_map = {
        "/export/timetable/42.json": tt,
        "/event/42/manage/sessions/117/modify": modify_doc,
    }
    client = RecordingClient(get_map=get_map)
    r = mod.Resolver(client, 42)
    patch = mod.Patch(kind="session", by="friendlyId", ref=43,
                      set={"title": "New", "room_name": "R2"})
    mod.apply_session_patch(client, 42, patch, r)

    assert patch.resolved["session_id"] == 117
    assert len(client.posts) == 1
    path, form = client.posts[0]
    assert path == "/event/42/manage/sessions/117/modify"
    assert form["title"] == "New"
    loc = json.loads(form["location_data"])
    assert loc["room_name"] == "R2"
    assert loc["inheriting"] is False


def test_apply_session_patch_uses_resolved_cache_skips_lookup():
    modify_doc = {"form_data": {"title": "Old"}}
    get_map = {"/event/42/manage/sessions/117/modify": modify_doc}
    client = RecordingClient(get_map=get_map)
    r = mod.Resolver(client, 42)
    patch = mod.Patch(kind="session", by="friendlyId", ref=43,
                      set={"title": "New"}, resolved={"session_id": 117})
    mod.apply_session_patch(client, 42, patch, r)
    # timetable export never fetched because session_id came from cache
    assert all(p != "/export/timetable/42.json" for p, _ in client.gets)


# ──────────────────────────── apply_person_patch ────────────────────────────

def test_apply_person_patch_filters_allowed_fields():
    client = RecordingClient(get_map={})
    r = mod.Resolver(client, 42)
    patch = mod.Patch(kind="person", by="name", ref="Julia",
                      set={"affiliation": "Oxford", "bogus": "x"},
                      resolved={"person_id": 88})
    mod.apply_person_patch(client, 42, patch, r)
    assert len(client.patches) == 1
    path, payload = client.patches[0]
    assert path == "/event/42/manage/persons/88"
    assert payload == {"affiliation": "Oxford"}  # bogus dropped


def test_apply_person_patch_no_recognised_fields_raises():
    client = RecordingClient(get_map={})
    r = mod.Resolver(client, 42)
    patch = mod.Patch(kind="person", by="name", ref="Julia",
                      set={"bogus": "x"}, resolved={"person_id": 88})
    with pytest.raises(ValueError):
        mod.apply_person_patch(client, 42, patch, r)


# ──────────────────────────── apply_contribution_patch ────────────────────────────

def test_apply_contribution_patch_session_reparent():
    tt = _timetable_doc(42, {
        "e1": {"entryType": "Session", "sessionId": 200, "friendlyId": 44, "title": "Target"},
    })
    get_map = {"/export/timetable/42.json": tt}
    client = RecordingClient(get_map=get_map)
    r = mod.Resolver(client, 42)
    patch = mod.Patch(kind="contribution", by="id", ref=501,
                      set={"session": 44}, resolved={"contribution_id": 501})
    mod.apply_contribution_patch(client, 42, patch, r)
    assert patch.resolved["target_session_id"] == 200
    assert client.patches == [
        ("/event/42/manage/contributions/501", {"session_id": 200}),
    ]


def test_apply_contribution_patch_rename_posts_form():
    edit_doc = {"form_data": {"title": "Old title", "extra": "keep"}}
    get_map = {"/event/42/manage/contributions/501/edit": edit_doc}
    client = RecordingClient(get_map=get_map)
    r = mod.Resolver(client, 42)
    patch = mod.Patch(kind="contribution", by="id", ref=501,
                      set={"title": "New title"}, resolved={"contribution_id": 501})
    mod.apply_contribution_patch(client, 42, patch, r)
    assert len(client.posts) == 1
    path, form = client.posts[0]
    assert path == "/event/42/manage/contributions/501/edit"
    assert form["title"] == "New title"
    assert form["extra"] == "keep"  # read-modify-write preserves other fields


# ──────────────────────────── apply_block_time_patch ────────────────────────────

def test_apply_block_time_patch_resolves_entry_and_patches():
    tt = _timetable_doc(42, {
        "e1": {"entryType": "Session", "sessionId": 117, "friendlyId": 43,
               "title": "S", "id": "s117"},
    })
    get_map = {"/export/timetable/42.json": tt}
    client = RecordingClient(get_map=get_map)
    r = mod.Resolver(client, 42)
    patch = mod.Patch(kind="block_time", by="friendlyId", ref=43,
                      set={"start_dt": "2027-03-01T09:00:00", "end_dt": "2027-03-01T10:00:00"})
    mod.apply_block_time_patch(client, 42, patch, r)
    assert patch.resolved["entry_id"] == "s117"
    assert client.patches == [
        ("/event/42/manage/timetable/s117",
         {"start_dt": "2027-03-01T09:00:00", "end_dt": "2027-03-01T10:00:00"}),
    ]


def test_apply_block_time_patch_uses_cached_entry_id():
    client = RecordingClient(get_map={})
    r = mod.Resolver(client, 42)
    patch = mod.Patch(kind="block_time", by="friendlyId", ref=43,
                      set={"start_dt": "2027-03-01T09:00:00"},
                      resolved={"entry_id": "s999"})
    mod.apply_block_time_patch(client, 42, patch, r)
    assert client.patches == [
        ("/event/42/manage/timetable/s999", {"start_dt": "2027-03-01T09:00:00"}),
    ]
    assert client.gets == []  # no resolution fetch needed


def test_apply_block_time_patch_no_dt_fields_raises():
    client = RecordingClient(get_map={})
    r = mod.Resolver(client, 42)
    patch = mod.Patch(kind="block_time", by="friendlyId", ref=43,
                      set={"irrelevant": 1}, resolved={"entry_id": "s1"})
    with pytest.raises(ValueError):
        mod.apply_block_time_patch(client, 42, patch, r)


def test_apply_block_time_patch_no_matching_entry_raises():
    # session resolves, but no timetable entry carries that sessionId id field
    tt = _timetable_doc(42, {
        "e1": {"entryType": "Session", "sessionId": 117, "friendlyId": 43, "title": "S"},
    })  # note: no "id" key on the entry
    get_map = {"/export/timetable/42.json": tt}
    client = RecordingClient(get_map=get_map)
    r = mod.Resolver(client, 42)
    patch = mod.Patch(kind="block_time", by="friendlyId", ref=43,
                      set={"start_dt": "2027-03-01T09:00:00"})
    with pytest.raises(LookupError):
        mod.apply_block_time_patch(client, 42, patch, r)


# ──────────────────────────── DISPATCH table ────────────────────────────

def test_dispatch_table_maps_all_kinds():
    assert set(mod.DISPATCH) == {"session", "person", "contribution", "block_time"}
    for fn in mod.DISPATCH.values():
        assert callable(fn)


# ──────────────────────────── main() integration ────────────────────────────

def test_main_missing_plan_exits(tmp_path):
    with pytest.raises(SystemExit):
        mod.main([str(tmp_path / "nope.yaml")])


def test_main_dry_run_unknown_kind_returns_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv(mod.ENV_WRITE_TOKEN, raising=False)
    monkeypatch.delenv(mod.ENV_READ_TOKEN, raising=False)
    yaml_text = (
        "event_id: 42\n"
        "patches:\n"
        "  - kind: mystery\n"
        "    by: id\n"
        "    ref: 1\n"
        "    set:\n"
        "      x: 1\n"
    )
    p = _write(tmp_path, "plan.yaml", yaml_text)
    rc = mod.main([str(p)])
    out = capsys.readouterr().out
    assert "unknown kind" in out
    assert rc == 1  # one failed patch


def test_main_dry_run_happy_path_no_network(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv(mod.ENV_WRITE_TOKEN, raising=False)
    monkeypatch.delenv(mod.ENV_READ_TOKEN, raising=False)

    # Stub the resolver+client interaction at the requests level so the
    # session dry-run does the GET (form fetch) but issues no real write.
    tt = _timetable_doc(42, {
        "e1": {"entryType": "Session", "sessionId": 117, "friendlyId": 43, "title": "Old"},
    })
    modify_doc = {"form_data": {"title": "Old"}}

    def fake_get(url, headers=None, params=None, timeout=None):
        if url.endswith("/export/timetable/42.json"):
            return FakeResponse(json_data=tt)
        if url.endswith("/sessions/117/modify"):
            return FakeResponse(json_data=modify_doc)
        raise AssertionError(f"unexpected GET {url}")

    write_called = []
    monkeypatch.setattr(mod.requests, "get", fake_get)
    monkeypatch.setattr(mod.requests, "post",
                        lambda *a, **k: write_called.append(1) or FakeResponse(text="x"))

    yaml_text = (
        "event_id: 42\n"
        "patches:\n"
        "  - kind: session\n"
        "    by: friendlyId\n"
        "    ref: 43\n"
        "    set:\n"
        "      title: New\n"
    )
    p = _write(tmp_path, "plan.yaml", yaml_text)
    rc = mod.main([str(p)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "mode=dry-run" in out
    assert write_called == []  # dry-run issued no POST

    # Resolved session_id should be persisted to the sidecar cache.
    cache = mod._resolved_cache_path(p)
    assert cache.exists()
    assert json.loads(cache.read_text())["1"]["session_id"] == 117


def test_main_handler_exception_counts_as_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv(mod.ENV_WRITE_TOKEN, raising=False)
    monkeypatch.delenv(mod.ENV_READ_TOKEN, raising=False)

    # person patch with no in_session and no cached id -> resolver raises.
    def fake_get(url, headers=None, params=None, timeout=None):
        raise AssertionError(f"should not GET in this flow: {url}")

    monkeypatch.setattr(mod.requests, "get", fake_get)
    yaml_text = (
        "event_id: 42\n"
        "patches:\n"
        "  - kind: person\n"
        "    by: name\n"
        "    ref: Ghost\n"
        "    set:\n"
        "      affiliation: Nowhere\n"
    )
    p = _write(tmp_path, "plan.yaml", yaml_text)
    rc = mod.main([str(p)])
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert rc == 1
