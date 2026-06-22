#!/usr/bin/env python3
"""Generate / refresh a LinkedIn access token for the social pipeline.

LinkedIn org posting uses OAuth 2.0 three-legged auth. This walks the two
network steps so you don't hand-build curl:

  1. auth-url  — print the authorization URL to open in a browser. Approve as a
                 page admin; you land on your redirect URL with ?code=...
  2. exchange  — swap that code for an access token + refresh token.
  3. refresh   — swap a refresh token for a fresh access token (~60-day TTL).

Put LINKEDIN_ORG_ID, the printed LINKEDIN_ACCESS_TOKEN and
LINKEDIN_REFRESH_TOKEN (plus LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET for
auto-refresh) into the `social` (and `social-auto`) GitHub environments.

Run locally. Nothing is sent anywhere except LinkedIn's OAuth endpoint. See
docs/social-publishing.md.

Usage:
  python3 scripts/linkedin-token.py auth-url --client-id ID --redirect-uri URL
  python3 scripts/linkedin-token.py exchange --client-id ID --client-secret SECRET \
      --redirect-uri URL --code CODE
  python3 scripts/linkedin-token.py refresh --client-id ID --client-secret SECRET \
      --refresh-token TOKEN
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

AUTH = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN = "https://www.linkedin.com/oauth/v2/accessToken"
SCOPE = "w_organization_social"


def _post(form: dict) -> dict:
    data = urllib.parse.urlencode(form).encode("utf-8")
    req = urllib.request.Request(
        TOKEN, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit(f"LinkedIn HTTP {e.code}: {e.read().decode('utf-8', 'replace')}")


def _opt(args, name: str, env: str) -> str:
    v = getattr(args, name) or os.environ.get(env)
    if not v:
        sys.exit(f"missing --{name.replace('_', '-')} (or ${env})")
    return v


def _show(tok: dict) -> None:
    print("\n# Add these to the `social` (and `social-auto`) GitHub environment secrets:\n")
    if tok.get("access_token"):
        print(f"LINKEDIN_ACCESS_TOKEN={tok['access_token']}")
    if tok.get("refresh_token"):
        print(f"LINKEDIN_REFRESH_TOKEN={tok['refresh_token']}")
    if tok.get("expires_in"):
        print(f"#   access token expires in ~{int(tok['expires_in']) // 86400} days")
    if tok.get("refresh_token_expires_in"):
        print(f"#   refresh token expires in ~{int(tok['refresh_token_expires_in']) // 86400} days")
    if not tok.get("refresh_token"):
        print("#   note: no refresh_token returned — your app may not have programmatic refresh\n"
              "#   enabled; you'll re-run `exchange` when the access token expires.")


def main() -> int:
    ap = argparse.ArgumentParser(description="LinkedIn OAuth token helper")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("auth-url", help="print the authorization URL to open in a browser")
    a.add_argument("--client-id")
    a.add_argument("--redirect-uri")
    e = sub.add_parser("exchange", help="exchange an authorization code for tokens")
    for f in ("--client-id", "--client-secret", "--redirect-uri", "--code"):
        e.add_argument(f)
    r = sub.add_parser("refresh", help="refresh an access token")
    for f in ("--client-id", "--client-secret", "--refresh-token"):
        r.add_argument(f)
    args = ap.parse_args()

    if args.cmd == "auth-url":
        cid = _opt(args, "client_id", "LINKEDIN_CLIENT_ID")
        redir = _opt(args, "redirect_uri", "LINKEDIN_REDIRECT_URI")
        q = urllib.parse.urlencode({
            "response_type": "code", "client_id": cid,
            "redirect_uri": redir, "scope": SCOPE, "state": "netsec"})
        print(f"{AUTH}?{q}")
        print("\nOpen that URL, approve as a page admin, then copy the `code=` value from the\n"
              "redirect URL and run:  python3 scripts/linkedin-token.py exchange --code <CODE> ...")
        return 0
    if args.cmd == "exchange":
        _show(_post({
            "grant_type": "authorization_code",
            "code": _opt(args, "code", "LINKEDIN_CODE"),
            "redirect_uri": _opt(args, "redirect_uri", "LINKEDIN_REDIRECT_URI"),
            "client_id": _opt(args, "client_id", "LINKEDIN_CLIENT_ID"),
            "client_secret": _opt(args, "client_secret", "LINKEDIN_CLIENT_SECRET")}))
        return 0
    if args.cmd == "refresh":
        _show(_post({
            "grant_type": "refresh_token",
            "refresh_token": _opt(args, "refresh_token", "LINKEDIN_REFRESH_TOKEN"),
            "client_id": _opt(args, "client_id", "LINKEDIN_CLIENT_ID"),
            "client_secret": _opt(args, "client_secret", "LINKEDIN_CLIENT_SECRET")}))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
