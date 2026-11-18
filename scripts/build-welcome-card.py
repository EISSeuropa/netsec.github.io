#!/usr/bin/env python3
"""Render the image card for the weekly welcome post (#2237).

The welcome post (scripts/social-post.py, kind "welcome", #2236) names the
members who joined the NetSec Directory. This renders one 1200x630 PNG with
their headshots and names, the count and the NetSec branding. Only members
with a headshot are pictured, and the rest are counted in a "+N" tile (see
welcome_card_faces() in social-post.py). When nobody has a headshot, the card
uses the initials tiles of the per-member cards.

The members come from social-post.py's welcome_pending(), with the same ledger
and the same `since` rule, so the card shows exactly the people the post names.
The file is assets/og/welcome/<hash of their ids>.png, which social-post.py
attaches when it exists and otherwise falls back to the Directory card. The
directory is gitignored.

Reuses the headless-Chrome capture of build-og-cards.py.

Usage:
    python3 scripts/build-welcome-card.py                    # the next live welcome
    python3 scripts/build-welcome-card.py --since 2026-11-13 # a preview window

Run from the repo root. Stdlib only. Needs Google Chrome / Chromium (set
$CHROME, else common paths are tried).
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import importlib.util
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # @dataclass resolves its module through sys.modules
    spec.loader.exec_module(mod)
    return mod


sp = _load("social_post", "social-post.py")
boc = _load("build_og_cards", "build-og-cards.py")

CARD_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<style>
  @font-face {{ font-family:'Lexend'; src:url('/assets/fonts/lexend-latin.woff2') format('woff2'); font-weight:600 700; font-display:block; }}
  @font-face {{ font-family:'Inter'; src:url('/assets/fonts/inter-latin.woff2') format('woff2'); font-weight:400 600; font-display:block; }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html, body {{ width:1200px; height:630px; }}
  body {{ font-family:'Inter', sans-serif; background:#0b1220; color:#f4f8ff; position:relative; overflow:hidden; }}
  .accent {{ position:absolute; left:0; top:0; bottom:0; width:14px; background:#003399; }}
  .frame {{ position:absolute; inset:0; padding:52px 78px 52px; display:flex; flex-direction:column; }}
  .brand {{ display:flex; align-items:center; gap:18px; }}
  .brand img {{ height:42px; }}
  .brand .ca {{ font-size:21px; letter-spacing:.04em; color:#aeb7d6; }}
  .main {{ flex:1; min-height:0; display:flex; flex-direction:column; justify-content:center; gap:34px; }}
  .headline {{ font-family:'Lexend', sans-serif; font-weight:700; font-size:58px; line-height:1.05;
    letter-spacing:-.02em; color:#f4f8ff; }}
  .count {{ margin-top:12px; font-size:28px; color:#ffcc00; font-weight:600; }}
  .faces {{ display:flex; gap:20px; }}
  .face {{ width:132px; flex:0 0 132px; display:flex; flex-direction:column; gap:12px; }}
  .shot {{ width:132px; height:132px; border-radius:22px; overflow:hidden;
    background:#152138; border:1px solid rgba(255,255,255,.14); }}
  .shot img {{ width:100%; height:100%; object-fit:cover; display:block; }}
  .initials, .more {{ width:100%; height:100%; display:flex; align-items:center; justify-content:center;
    font-family:'Lexend', sans-serif; font-weight:700; color:#9fb3e0; }}
  .initials {{ font-size:48px; }}
  .more {{ font-size:44px; color:#ffcc00; }}
  .who {{ font-size:19px; line-height:1.25; color:#d7def2; font-weight:500;
    display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }}
  .foot {{ display:flex; align-items:center; }}
  .foot .url {{ font-size:26px; color:#7f8cb0; letter-spacing:.02em; }}
</style></head>
<body>
  <div class="accent"></div>
  <div class="frame">
    <div class="brand">
      <img src="/assets/images/brand/netsec-lockup-white.png" alt="">
      <span class="ca">COST Action CA24154</span>
    </div>
    <div class="main">
      <div>
        <div class="headline">Welcome to the NetSec Directory</div>
        <div class="count">{count}</div>
      </div>
      <div class="faces">{faces}</div>
    </div>
    <div class="foot"><span class="url">netsec-cost.eu/people</span></div>
  </div>
</body></html>
"""


def display_name(name: str) -> str:
    """The name without its honorific: "Prof. Carmen Márquez Carrasco" reads
    "Carmen Márquez Carrasco" under the photo."""
    words = (name or "").split()
    while len(words) > 1 and words[0].lower().strip(".") in boc._TITLES:
        words = words[1:]
    return " ".join(words)


def face_html(m: dict) -> str:
    photo = (m.get("photo") or "").strip()
    if photo and (ROOT / photo).exists():
        shot = f'<img src="/{html.escape(photo)}" alt="">'
    else:
        shot = f'<div class="initials">{html.escape(boc.initials(m.get("name", "")))}</div>'
    who = html.escape(display_name(m.get("name", "")))
    return f'<div class="face"><div class="shot">{shot}</div><div class="who">{who}</div></div>'


def more_html(n: int) -> str:
    label = "more member" if n == 1 else "more members"
    return (f'<div class="face"><div class="shot"><div class="more">+{n}</div></div>'
            f'<div class="who">{label}</div></div>')


def card_markup(members: list[dict]) -> str:
    shown = sp.welcome_card_faces(members)
    faces = [face_html(m) for m in shown]
    if len(members) > len(shown):
        faces.append(more_html(len(members) - len(shown)))
    return CARD_HTML.format(
        count=html.escape(sp._count_words(len(members), "new member").capitalize()),
        faces="".join(faces),
    )


def render(members: list[dict], out: Path) -> None:
    chrome = boc._find_chrome()
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="ogcards-welcome-", dir=str(ROOT)))
    port = boc._free_port()
    httpd = boc._serve(ROOT, port)
    try:
        (tmp / "card.html").write_text(card_markup(members), encoding="utf-8")
        url = f"http://127.0.0.1:{port}/{tmp.relative_to(ROOT).as_posix()}/card.html"
        boc._capture_cards(chrome, [(url, out)])
    finally:
        httpd.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Render the weekly welcome post's image card.")
    ap.add_argument("--since", metavar="YYYY-MM-DD",
                    help="preview: members who joined on or after this date, "
                         "in place of data/welcome.json `since`")
    args = ap.parse_args()
    if args.since and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.since):
        ap.error(f"--since must be a date as YYYY-MM-DD, not {args.since!r}")
    if args.since:
        dt.date.fromisoformat(args.since)
    posted = set(sp.load_ledger().get("posted", []))
    members = sp.welcome_pending(posted, args.since)
    if not members:
        print("Nobody to welcome, so no card.")
        return 0
    out = sp.welcome_card_path(members)
    render(members, out)
    print(f"✓ wrote {out.relative_to(ROOT)} for {len(members)} member(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
