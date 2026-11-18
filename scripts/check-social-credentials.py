#!/usr/bin/env python3
"""Check the LinkedIn and Bluesky credentials in the `social` environment (or
`social-auto` on NetSec), without posting and without printing a secret.

Run by .github/workflows/check-social-credentials.yml (manual, approval-gated
like a post). It reads the same environment variables as
scripts/social-post.py and reports, for each value, what is wrong with it:

Bluesky
  BSKY_HANDLE        set, its shape (no @, no URL, no spaces or quotes), and
                     whether the handle exists (com.atproto.identity.resolveHandle)
  BSKY_APP_PASSWORD  set, its shape (an app password is xxxx-xxxx-xxxx-xxxx)
  sign-in            com.atproto.server.createSession with the two

LinkedIn
  LINKEDIN_ORG_ID, LINKEDIN_ACCESS_TOKEN, LINKEDIN_REFRESH_TOKEN,
  LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET
                     set, and free of spaces, line breaks and quotes
  access token       LinkedIn's token introspection (oauth/v2/introspectToken):
  refresh token      active or not, its status, whether it was issued to the
                     app in LINKEDIN_CLIENT_ID, its scope and its expiry

An expired access token is normal: it lasts about 60 days, and
scripts/social-post.py renews it from the refresh token at each post without
storing the new one. So when the access token has expired and the refresh
token is active, issued to the same app and has w_organization_social, the
check renews the access token the same way. A renewal that works is a note,
not a failure. A revoked access token, a renewal that LinkedIn refuses or an
inactive refresh token fails. A refresh token with fewer than
REFRESH_WARN_DAYS days left is a warning, which does not fail the job.

The output holds only yes/no answers, lengths, dates and the status LinkedIn
or Bluesky return. The exit code is 1 when any check fails.

Kept the same in EISSeuropa/EISSeuropa.github.io and EISSeuropa/netsec.github.io.

Usage: python3 scripts/check-social-credentials.py
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

PDS = "https://bsky.social"
LI_INTROSPECT = "https://www.linkedin.com/oauth/v2/introspectToken"
LI_TOKEN = "https://www.linkedin.com/oauth/v2/accessToken"
# Warn when the refresh token has fewer days left than this: after it expires,
# LinkedIn posting stops until scripts/linkedin-token.py is run again.
REFRESH_WARN_DAYS = 60
APP_PASSWORD_RE = re.compile(r"^[a-z0-9]{4}(-[a-z0-9]{4}){3}$")
HANDLE_RE = re.compile(r"^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]*[a-z0-9]$")

OK, FAIL, NOTE, WARN = "ok", "FAIL", "note", "warn"


def shape(name: str, raw: str | None) -> list[tuple[str, str]]:
    """What is wrong with how a value was stored, without showing it."""
    if raw is None or raw == "":
        return [(FAIL, f"{name} is not set")]
    out = []
    # scripts/linkedin-token.py prints each token as NAME=value. EISS stored the
    # whole line on 11 November 2026, 22 and 23 characters too long, and
    # LinkedIn answered "Unable to parse access token".
    m = re.match(r"\s*([A-Z][A-Z0-9_]{2,})\s*=", raw)
    if m:
        what = "its own name" if m.group(1) == name else m.group(1)
        out.append((FAIL, f"{name} starts with {what} and =, copied from a NAME=value line: "
                          f"store only the part after the ="))
        return out
    if raw != raw.strip():
        out.append((FAIL, f"{name} starts or ends with a space or a line break"))
    if any(c.isspace() for c in raw.strip()):
        out.append((FAIL, f"{name} has a space or a line break inside it"))
    if raw.strip()[:1] in "\"'" or raw.strip()[-1:] in "\"'":
        out.append((FAIL, f"{name} is wrapped in quotation marks"))
    if not out:
        out.append((OK, f"{name} is set ({len(raw)} characters, no spaces or quotes)"))
    return out


def handle_shape(raw: str) -> list[tuple[str, str]]:
    h = raw.strip()
    out = []
    if h.startswith("@"):
        out.append((FAIL, "BSKY_HANDLE starts with @: store the handle without it"))
    if "://" in h or "bsky.app" in h:
        out.append((FAIL, "BSKY_HANDLE is an address: store only the handle, such as name.bsky.social"))
    if h != h.lower():
        out.append((NOTE, "BSKY_HANDLE has capital letters: Bluesky handles are lower case"))
    if not out and not HANDLE_RE.match(h.lower()):
        out.append((FAIL, "BSKY_HANDLE is not shaped like a handle (name.bsky.social or a domain)"))
    return out


def app_password_shape(raw: str) -> list[tuple[str, str]]:
    if APP_PASSWORD_RE.match(raw.strip()):
        return [(OK, "BSKY_APP_PASSWORD is shaped like an app password (xxxx-xxxx-xxxx-xxxx)")]
    return [(FAIL, "BSKY_APP_PASSWORD is not shaped like an app password (xxxx-xxxx-xxxx-xxxx). "
                   "It may be the account's own password, which the API refuses: create an app "
                   "password in Bluesky (Settings > Privacy and security > App passwords)")]


def _http(url: str, data: bytes | None = None, headers: dict | None = None) -> tuple[int, dict]:
    req = urllib.request.Request(url, data=data, headers=headers or {}, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, {"message": body[:200]}
    except (urllib.error.URLError, TimeoutError) as e:
        return 0, {"message": str(e)}


def check_bluesky(env: dict) -> list[tuple[str, str]]:
    out = []
    handle, password = env.get("BSKY_HANDLE"), env.get("BSKY_APP_PASSWORD")
    out += shape("BSKY_HANDLE", handle)
    out += shape("BSKY_APP_PASSWORD", password)
    if not (handle and password):
        return out
    out += handle_shape(handle)
    out += app_password_shape(password)
    h = handle.strip().lstrip("@").lower()
    code, body = _http(f"{PDS}/xrpc/com.atproto.identity.resolveHandle?handle={urllib.parse.quote(h)}")
    if code == 200 and body.get("did"):
        out.append((OK, "The handle exists on Bluesky"))
    else:
        out.append((FAIL, f"Bluesky does not know the handle (HTTP {code}: {body.get('message') or body.get('error')})"))
    code, body = _http(f"{PDS}/xrpc/com.atproto.server.createSession",
                       data=json.dumps({"identifier": h, "password": password.strip()}).encode(),
                       headers={"Content-Type": "application/json"})
    if code == 200 and body.get("accessJwt"):
        out.append((OK, "Bluesky sign-in works"))
    else:
        out.append((FAIL, f"Bluesky sign-in refused (HTTP {code}: {body.get('message') or body.get('error')})"))
    return out


def _date(epoch) -> str:
    try:
        return dt.datetime.fromtimestamp(int(epoch), dt.timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OverflowError, OSError):
        return "unknown"


def _introspect_hint(label: str, code: int, body: dict) -> str:
    """What a refused introspection points to. A refused app is a 401 or an
    error naming the client. A token LinkedIn cannot parse is the token itself.
    Anything else gets no guess."""
    text = " ".join(str(body.get(k) or "") for k in ("error", "error_description", "message")).lower()
    if code == 401 or "client" in text:
        return (" LinkedIn refused the app credentials: check that LINKEDIN_CLIENT_ID and "
                "LINKEDIN_CLIENT_SECRET belong to the same app")
    if "parse" in text or "token" in text:
        return (f" LinkedIn does not recognise the {label}: create new tokens with "
                "scripts/linkedin-token.py and replace both token secrets")
    return ""


def _inspect(label: str, token: str, client_id: str, client_secret: str) -> tuple[dict | None, list]:
    """LinkedIn's introspection of a token: (its answer, []) or (None, [the failure])."""
    data = urllib.parse.urlencode({"client_id": client_id, "client_secret": client_secret,
                                   "token": token}).encode()
    code, body = _http(LI_INTROSPECT, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    if code != 200:
        msg = body.get("error_description") or body.get("message") or body.get("error")
        return None, [(FAIL, f"LinkedIn could not inspect the {label} (HTTP {code}: {msg}).{_introspect_hint(label, code, body)}")]
    return body, []


def _has_scope(body: dict) -> bool:
    return "w_organization_social" in re.split(r"[,\s]+", body.get("scope") or "")


def _describe(label: str, body: dict, client_id: str) -> list[tuple[str, str]]:
    """The app the token was issued to, its scope and its creation date."""
    out = []
    issued_to = body.get("client_id")
    if issued_to:
        if issued_to == client_id:
            out.append((OK, f"The {label} was issued to the app in LINKEDIN_CLIENT_ID"))
        else:
            out.append((FAIL, f"The {label} was issued to another LinkedIn app than LINKEDIN_CLIENT_ID: "
                              "use the client ID and secret of the app the tokens were made with"))
    scope = body.get("scope") or ""
    if scope:
        if _has_scope(body):
            out.append((OK, f"The {label} has the w_organization_social scope"))
        else:
            out.append((FAIL, f"The {label} lacks w_organization_social (it has: {scope})"))
    if body.get("created_at"):
        out.append((NOTE, f"The {label} was created {_date(body.get('created_at'))}"))
    return out


def _status(body: dict) -> str:
    return str(body.get("status") or ("active" if body.get("active") is True else "inactive")).lower()


def renew(refresh_token: str, client_id: str, client_secret: str) -> tuple[bool, str]:
    """Swap the refresh token for a new access token, as social-post.py does
    before a post. The new token is not kept or shown."""
    data = urllib.parse.urlencode({"grant_type": "refresh_token", "refresh_token": refresh_token,
                                   "client_id": client_id, "client_secret": client_secret}).encode()
    code, body = _http(LI_TOKEN, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    if code == 200 and body.get("access_token"):
        return True, ""
    return False, f"HTTP {code}: {body.get('error_description') or body.get('error') or body.get('message')}"


def check_tokens(env: dict, client_id: str, client_secret: str,
                 now: dt.datetime | None = None) -> list[tuple[str, str]]:
    """The two tokens judged together: an expired access token is fine while
    the refresh token renews it."""
    now = now or dt.datetime.now(dt.timezone.utc)
    access = (env.get("LINKEDIN_ACCESS_TOKEN") or "").strip()
    refresh = (env.get("LINKEDIN_REFRESH_TOKEN") or "").strip()
    out = []
    a_body, a_out = _inspect("access token", access, client_id, client_secret) if access else (None, [])
    r_body, r_out = _inspect("refresh token", refresh, client_id, client_secret) if refresh else (None, [])
    refresh_ok = bool(r_body and r_body.get("active") is True and _has_scope(r_body)
                      and (not r_body.get("client_id") or r_body.get("client_id") == client_id))

    # The refresh token: what renews everything else.
    out += r_out
    if r_body:
        if r_body.get("active") is True:
            left = None
            try:
                left = (dt.datetime.fromtimestamp(int(r_body.get("expires_at")), dt.timezone.utc) - now).days
            except (TypeError, ValueError, OverflowError, OSError):
                pass
            out.append((OK, f"The refresh token is active, expires {_date(r_body.get('expires_at'))}"))
            if left is not None and left < REFRESH_WARN_DAYS:
                out.append((WARN, f"The refresh token expires in {left} days, on {_date(r_body.get('expires_at'))}. "
                                  "After that day LinkedIn posting stops: create new tokens with "
                                  "scripts/linkedin-token.py before then"))
        else:
            until = (f" Posts work until the access token expires on {_date(a_body.get('expires_at'))}, then stop."
                     if a_body and a_body.get("active") is True else "")
            out.append((FAIL, f"The refresh token is not active (LinkedIn status: {_status(r_body)}), so the "
                              f"access token cannot be renewed.{until} Create new tokens with "
                              "scripts/linkedin-token.py"))
        out += _describe("refresh token", r_body, client_id)

    # The access token, judged with the refresh token.
    out += a_out
    if a_body:
        status = _status(a_body)
        if a_body.get("active") is True:
            out.append((OK, f"The access token is active, expires {_date(a_body.get('expires_at'))}"))
        elif status == "expired" and refresh_ok:
            ok, why = renew(refresh, client_id, client_secret)
            if ok:
                out.append((NOTE, "The stored access token has expired, which is expected: it lasts about "
                                  "60 days and is not stored again after a renewal"))
                out.append((OK, "The refresh token renews it: a new access token was issued just now, as "
                                "scripts/social-post.py does before each post"))
            else:
                out.append((FAIL, f"The access token has expired and LinkedIn refused to renew it ({why}). "
                                  "Create new tokens with scripts/linkedin-token.py"))
        elif status == "expired":
            out.append((FAIL, "The access token has expired, and the refresh token cannot renew it (see the "
                              "refresh token lines). Create new tokens with scripts/linkedin-token.py"))
        elif status == "revoked":
            out.append((FAIL, "The access token was revoked: the authorisation was withdrawn, and a refresh "
                              "does not bring it back. Create new tokens with scripts/linkedin-token.py"))
        else:
            out.append((FAIL, f"The access token is not active (LinkedIn status: {status}). "
                              "Create new tokens with scripts/linkedin-token.py"))
        out += _describe("access token", a_body, client_id)
    return out


def check_linkedin(env: dict, now: dt.datetime | None = None) -> list[tuple[str, str]]:
    names = ["LINKEDIN_ORG_ID", "LINKEDIN_ACCESS_TOKEN", "LINKEDIN_REFRESH_TOKEN",
             "LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET"]
    out = []
    for n in names:
        out += shape(n, env.get(n))
    org = (env.get("LINKEDIN_ORG_ID") or "").strip()
    if org and not org.isdigit():
        out.append((FAIL, "LINKEDIN_ORG_ID is not a plain number: store only the page's number, "
                          "not urn:li:organization:... or an address"))
    cid = (env.get("LINKEDIN_CLIENT_ID") or "").strip()
    cs = (env.get("LINKEDIN_CLIENT_SECRET") or "").strip()
    if not (cid and cs):
        out.append((FAIL, "Without LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET the tokens cannot be inspected"))
        return out
    out += check_tokens(env, cid, cs, now)
    return out


def report(title: str, results: list[tuple[str, str]], lines: list[str]) -> bool:
    lines += [f"### {title}", ""]
    failed = False
    for level, msg in results:
        mark = {"ok": "✅", "FAIL": "❌", "note": "ℹ️", "warn": "⚠️"}[level]
        lines.append(f"- {mark} {msg}")
        if level == FAIL:
            failed = True
            print(f"::error title={title}::{msg}")
        elif level == WARN:
            print(f"::warning title={title}::{msg}")
    lines.append("")
    return failed


def main(env: dict | None = None) -> int:
    env = dict(os.environ if env is None else env)
    lines = ["## Social credentials check", "",
             "Nothing was posted and no secret is shown. ❌ names the value to replace in "
             "Settings > Environments > `" + os.environ.get("SOCIAL_ENVIRONMENT", "social") + "`.", ""]
    failed = report("Bluesky", check_bluesky(env), lines)
    failed = report("LinkedIn", check_linkedin(env), lines) or failed
    print("\n".join(lines))
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
