#!/usr/bin/env python3
"""Tests for scripts/check-social-credentials.py. No network: _http is
replaced. Runs under pytest or on its own:

    python3 scripts/test-check-social-credentials.py
"""
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("check_social_credentials", HERE / "check-social-credentials.py")
cc = importlib.util.module_from_spec(spec)
sys.modules["check_social_credentials"] = cc
spec.loader.exec_module(cc)

GOOD = {
    "BSKY_HANDLE": "eissnetwork.bsky.social",
    "BSKY_APP_PASSWORD": "abcd-efgh-ijkl-mnop",
    "LINKEDIN_ORG_ID": "78412359",
    "LINKEDIN_ACCESS_TOKEN": "AQVaccess",
    "LINKEDIN_REFRESH_TOKEN": "AQXrefresh",
    "LINKEDIN_CLIENT_ID": "86app",
    "LINKEDIN_CLIENT_SECRET": "s3cret",
}


def fake_http(token_status=None, signin=200, issued_to="86app"):
    token_status = token_status or {"AQVaccess": True, "AQXrefresh": True}

    def _http(url, data=None, headers=None):
        if "resolveHandle" in url:
            return 200, {"did": "did:plc:x"}
        if "createSession" in url:
            return (200, {"accessJwt": "j"}) if signin == 200 else (401, {"message": "Invalid identifier or password"})
        if "introspectToken" in url:
            form = dict(p.split("=", 1) for p in data.decode().split("&"))
            active = token_status.get(form["token"], False)
            return 200, {"active": active, "status": "active" if active else "revoked", "client_id": issued_to,
                         "scope": "w_organization_social,r_organization_social", "expires_at": 1798761600,
                         "created_at": 1762819200}
        raise AssertionError(url)
    return _http


def run(env, **kw):
    cc._http = fake_http(**kw)
    bs, li = cc.check_bluesky(env), cc.check_linkedin(env)
    return bs, li


def fails(results):
    return [m for lvl, m in results if lvl == cc.FAIL]


def test_all_good_passes():
    bs, li = run(GOOD)
    assert not fails(bs) and not fails(li), (fails(bs), fails(li))
    assert any("expires 2027-01-01" in m for _, m in li)


def test_never_prints_a_secret(capsys=None):
    import io
    import contextlib
    cc._http = fake_http()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cc.main(dict(GOOD))
    out = buf.getvalue()
    for k in ("BSKY_APP_PASSWORD", "LINKEDIN_ACCESS_TOKEN", "LINKEDIN_REFRESH_TOKEN", "LINKEDIN_CLIENT_SECRET"):
        assert GOOD[k] not in out, k


def test_stored_with_quotes_spaces_or_line_breaks():
    env = dict(GOOD, LINKEDIN_REFRESH_TOKEN="AQXrefresh\n", LINKEDIN_CLIENT_SECRET='"s3cret"',
               BSKY_APP_PASSWORD="abcd efgh")
    bs, li = run(env)
    msgs = " | ".join(fails(bs) + fails(li))
    assert "LINKEDIN_REFRESH_TOKEN starts or ends with a space or a line break" in msgs
    assert "LINKEDIN_CLIENT_SECRET is wrapped in quotation marks" in msgs
    assert "BSKY_APP_PASSWORD has a space or a line break inside it" in msgs


def test_handle_shapes():
    for raw, needle in (("@eissnetwork.bsky.social", "starts with @"),
                        ("https://bsky.app/profile/eissnetwork.bsky.social", "is an address"),
                        ("eissnetwork", "not shaped like a handle")):
        assert any(needle in m for _, m in cc.handle_shape(raw)), raw
    assert not fails(cc.handle_shape("eissnetwork.bsky.social"))
    assert not fails(cc.handle_shape("netsec-cost.eu"))


def test_account_password_instead_of_app_password():
    bs, _ = run(dict(GOOD, BSKY_APP_PASSWORD="MyAccountPassword1"), signin=401)
    msgs = " | ".join(fails(bs))
    assert "not shaped like an app password" in msgs and "Invalid identifier or password" in msgs


def test_revoked_refresh_token_and_wrong_app():
    _, li = run(GOOD, token_status={"AQVaccess": False, "AQXrefresh": False}, issued_to="other")
    msgs = " | ".join(fails(li))
    assert "The access token is not active (LinkedIn status: revoked)" in msgs
    assert "The refresh token is not active" in msgs
    assert "issued to another LinkedIn app" in msgs


def test_introspection_hint_names_the_token_or_the_app():
    # The EISS run on 18 November: LinkedIn answered 400 "Unable to parse
    # access token" for both tokens. That is the token, not the app.
    hint = cc._introspect_hint("access token", 400, {"message": "Unable to parse access token"})
    assert "does not recognise the access token" in hint and "LINKEDIN_CLIENT_ID" not in hint
    for code, body in ((401, {"error": "invalid_client"}),
                       (400, {"error": "invalid_client", "error_description": "Client authentication failed"})):
        assert "LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET" in cc._introspect_hint("access token", code, body)
    assert cc._introspect_hint("access token", 500, {"message": "Internal error"}) == ""

    def unparsable(url, data=None, headers=None):
        if "introspectToken" in url:
            return 400, {"message": "Unable to parse access token", "serviceErrorCode": 0, "status": 400}
        return fake_http()(url, data, headers)
    cc._http = unparsable
    msgs = fails(cc.check_linkedin(GOOD))
    assert any("does not recognise the refresh token" in m for m in msgs), msgs
    assert not any("LINKEDIN_CLIENT_SECRET belong" in m for m in msgs), msgs


def test_org_id_must_be_a_number():
    _, li = run(dict(GOOD, LINKEDIN_ORG_ID="urn:li:organization:78412359"))
    assert any("not a plain number" in m for m in fails(li))


def test_missing_values():
    bs, li = run({})
    assert "BSKY_HANDLE is not set" in fails(bs)
    assert "LINKEDIN_ACCESS_TOKEN is not set" in fails(li)


def test_exit_code():
    cc._http = fake_http()
    assert cc.main(dict(GOOD)) == 0
    cc._http = fake_http(signin=401)
    assert cc.main(dict(GOOD)) == 1


if __name__ == "__main__":
    import io
    import contextlib
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for name, fn in tests:
        with contextlib.redirect_stdout(io.StringIO()):
            fn()
    print(f"test-check-social-credentials: {len(tests)} checks passed")
