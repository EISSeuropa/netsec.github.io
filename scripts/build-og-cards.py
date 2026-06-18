#!/usr/bin/env python3
"""
Generate per-member Open Graph card images for the profile pages (#1023).

Each member's /people/<slug> page should unfurl on social media as that
person, not the generic site card. This renders a 1200x630 PNG per member
(rounded headshot, name, role, working-group / mentorship / STSM pills,
country flag, NetSec branding) by screenshotting an HTML template with headless
Chrome, the same technique as docs/pdf/build.sh.

A member with no committed headshot falls back to an initials tile, so every
card renders. The pills mirror the language of the live profile pages
(scripts/build-profile-pages.py): WG1..WG4 with a lead / co-lead suffix,
Mentor / Mentee, and an STSM-hosting badge.

  - Cards are written to assets/og/people/<slug>.png (committed; see #119 for
    the eventual move to deploy-time build).
  - Flags are bundled locally under assets/og/flags/<cc>.svg so the render is
    deterministic and needs no network.
  - PNG, not WebP: OG/Twitter scrapers want PNG, and it avoids the x86 cwebp
    limitation in the dev sandbox.
  - A content manifest (assets/og/people/_manifest.json) records a hash of each
    card's inputs (name, position, affiliation, country) so --check can tell a
    card is stale without a flaky pixel diff (PNGs aren't byte-reproducible
    across Chrome / font versions).

Usage:
    python3 scripts/build-og-cards.py            # render all cards + manifest
    python3 scripts/build-og-cards.py --check     # exit 1 if any card is stale
    python3 scripts/build-og-cards.py --only SLUG # render one card (debugging)

Run from the repo root. Stdlib only. Rendering needs Google Chrome / Chromium
(set $CHROME, else common paths are tried); --check needs no browser.
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import html as html_mod
import http.server
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIOS = ROOT / "data" / "bios.json"
CARDS_DIR = ROOT / "assets" / "og" / "people"
FLAGS_DIR = ROOT / "assets" / "og" / "flags"
MANIFEST = CARDS_DIR / "_manifest.json"

CHROME_CANDIDATES = [
    os.environ.get("CHROME", ""),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome",
    "google-chrome-stable",
    "chromium-browser",
    "chromium",
]

CARD_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<style>
  @font-face {{ font-family:'Lexend'; src:url('/assets/fonts/lexend-latin.woff2') format('woff2'); font-weight:600 700; font-display:block; }}
  @font-face {{ font-family:'Inter'; src:url('/assets/fonts/inter-latin.woff2') format('woff2'); font-weight:400 600; font-display:block; }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html, body {{ width:1200px; height:630px; }}
  body {{
    font-family:'Inter', sans-serif;
    background:#0b1220; color:#f4f8ff; position:relative; overflow:hidden;
  }}
  /* A single flat accent bar down the left edge instead of full-bleed
     gradients: keeps the colour count low so the PNG stays small. */
  .accent {{ position:absolute; left:0; top:0; bottom:0; width:14px;
    background:#003399; }}
  .frame {{ position:absolute; inset:0; padding:52px 78px 56px; display:flex; flex-direction:column; }}
  .brand {{ display:flex; align-items:center; gap:18px; }}
  .brand img {{ height:42px; }}
  .brand .ca {{ font-size:21px; letter-spacing:.04em; color:#aeb7d6; }}
  .main {{ flex:1; min-height:0; display:flex; align-items:center; gap:50px; }}
  .shot {{ flex:0 0 290px; width:290px; height:290px; border-radius:30px; overflow:hidden;
    background:#152138; border:1px solid rgba(255,255,255,.14); }}
  .shot img {{ width:100%; height:100%; object-fit:cover; display:block; }}
  .shot .initials {{ width:100%; height:100%; display:flex; align-items:center; justify-content:center;
    font-family:'Lexend', sans-serif; font-weight:700; font-size:108px; color:#9fb3e0;
    letter-spacing:.01em; }}
  .text {{ flex:1; min-width:0; display:flex; flex-direction:column; }}
  .name {{ font-family:'Lexend', sans-serif; font-weight:700; font-size:60px; line-height:1.06;
    letter-spacing:-.02em; color:#f4f8ff;
    display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }}
  .role {{ margin-top:16px; font-size:27px; line-height:1.32; color:#d7def2; font-weight:500;
    display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }}
  .pills {{ margin-top:26px; display:flex; flex-wrap:wrap; gap:12px; }}
  .pill {{ font-size:21px; font-weight:600; line-height:1; padding:10px 18px; border-radius:999px;
    background:rgba(255,255,255,.09); border:1px solid rgba(255,255,255,.16); color:#e7ecfb; white-space:nowrap; }}
  .pill.wg {{ background:rgba(10,132,255,.16); border-color:rgba(10,132,255,.42); color:#cfe2ff; }}
  .pill.stsm {{ background:rgba(255,204,0,.15); border-color:rgba(255,204,0,.40); color:#ffe79a; }}
  .foot {{ display:flex; align-items:center; gap:18px; }}
  .foot .flag {{ width:58px; height:39px; border-radius:6px; object-fit:cover;
    border:1px solid rgba(255,255,255,.15); }}
  .foot .country {{ font-size:27px; color:#d7def2; font-weight:500; }}
  .foot .sep {{ flex:1; }}
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
      <div class="shot">{shot_html}</div>
      <div class="text">
        <div class="name">{name}</div>
        {role_html}
        {pills_html}
      </div>
    </div>
    <div class="foot">
      {flag_html}
      <span class="country">{country}</span>
      <span class="sep"></span>
      <span class="url">netsec-cost.eu</span>
    </div>
  </div>
</body></html>
"""

# Honorifics dropped before deriving the initials tile, so "Dr Arthur
# Laudrain" reads as "AL", not "DA".
_TITLES = {"dr", "prof", "professor", "mr", "mrs", "ms", "mx", "miss", "sir", "dame"}
WG_LABELS = {"1": "WG1", "2": "WG2", "3": "WG3", "4": "WG4"}


def members() -> list[dict]:
    data = json.loads(BIOS.read_text(encoding="utf-8"))
    return [m for m in data.get("members", []) if m.get("id")]


def initials(name: str) -> str:
    words = [w for w in re.split(r"[\s.]+", name or "") if w]
    named = [w for w in words if w.lower().strip(".") not in _TITLES] or words
    if not named:
        return "?"
    first = named[0][0]
    last = named[-1][0] if len(named) > 1 else ""
    return (first + last).upper()


def wg_pills(m: dict) -> list[str]:
    """WG1..WG4 with a lead / co-lead suffix, mirroring build-profile-pages.py."""
    lead = {str(x) for x in (m.get("wg_leadership") or {}).get("lead") or []}
    colead = {str(x) for x in (m.get("wg_leadership") or {}).get("co_lead") or []}
    nums = sorted({str(x) for x in (list(m.get("wgs") or []) + list(lead) + list(colead))})
    pills = []
    for n in nums:
        if n not in WG_LABELS:
            continue
        label = WG_LABELS[n]
        if n in lead:
            label += " · lead"
        elif n in colead:
            label += " · co-lead"
        pills.append(label)
    return pills


def mentor_pills(m: dict) -> list[str]:
    tags = m.get("mentorship") or []
    pills = []
    if "mentor" in tags:
        pills.append("Mentor")
    if "mentee" in tags:
        pills.append("Mentee")
    return pills


def stsm_pill(m: dict) -> str:
    s = m.get("stsm_hosting")
    if s == "yes":
        return "STSM host"
    if s == "ask":
        return "STSM on request"
    return ""


def card_inputs(m: dict) -> dict:
    """The fields that determine a card's pixels."""
    photo = (m.get("photo") or "").strip()
    has_photo = bool(photo and (ROOT / photo).exists())
    name = (m.get("name") or "").strip()
    return {
        "name": name,
        "position": (m.get("position") or "").strip(),
        "affiliation": (m.get("affiliation") or "").strip(),
        "country": (m.get("country") or "").strip(),
        "country_code": (m.get("country_code") or "").strip().lower(),
        "photo": photo if has_photo else "",
        # Hash the source-photo digest so a re-crop re-renders even when the
        # path is unchanged; sync-bios.py records it per member.
        "photo_sha": (m.get("photo_source_sha256") or "")[:16] if has_photo else "",
        "initials": initials(name),
        "wg": wg_pills(m),
        "mentor": mentor_pills(m),
        "stsm": stsm_pill(m),
    }


def card_hash(inputs: dict) -> str:
    parts = [
        inputs.get("name", ""),
        inputs.get("position", ""),
        inputs.get("affiliation", ""),
        inputs.get("country", ""),
        inputs.get("country_code", ""),
        inputs.get("photo", ""),
        inputs.get("photo_sha", ""),
        ",".join(inputs.get("wg") or []),
        ",".join(inputs.get("mentor") or []),
        inputs.get("stsm", ""),
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def card_markup(inputs: dict) -> str:
    role_bits = [b for b in (inputs.get("position", ""), inputs.get("affiliation", "")) if b]
    role = " · ".join(role_bits)
    role_html = f'<div class="role">{html_mod.escape(role)}</div>' if role else ""

    photo = inputs.get("photo", "")
    if photo:
        shot_html = f'<img src="/{photo}" alt="">'
    else:
        shot_html = f'<div class="initials">{html_mod.escape(inputs.get("initials") or "?")}</div>'

    pills = []
    for label in inputs.get("wg") or []:
        pills.append(f'<span class="pill wg">{html_mod.escape(label)}</span>')
    for label in inputs.get("mentor") or []:
        pills.append(f'<span class="pill">{html_mod.escape(label)}</span>')
    if inputs.get("stsm"):
        pills.append(f'<span class="pill stsm">{html_mod.escape(inputs["stsm"])}</span>')
    pills_html = f'<div class="pills">{"".join(pills)}</div>' if pills else ""

    cc = inputs.get("country_code", "")
    flag = FLAGS_DIR / f"{cc}.svg"
    flag_html = f'<img class="flag" src="/assets/og/flags/{cc}.svg" alt="">' if cc and flag.exists() else ""
    return CARD_HTML.format(
        name=html_mod.escape(inputs.get("name", "")),
        role_html=role_html,
        pills_html=pills_html,
        shot_html=shot_html,
        flag_html=flag_html,
        country=html_mod.escape(inputs.get("country", "")),
    )


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------
def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _serve(root: Path, port: int) -> http.server.ThreadingHTTPServer:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def _find_chrome() -> str:
    for cand in CHROME_CANDIDATES:
        if not cand:
            continue
        if "/" in cand and Path(cand).exists():
            return cand
        if shutil.which(cand):
            return cand
    raise SystemExit("No Chrome/Chromium found. Set $CHROME to the binary path.")


def render_all(only: str | None = None, force: bool = False) -> int:
    CARDS_DIR.mkdir(parents=True, exist_ok=True)
    ms = members()
    if only:
        ms = [m for m in ms if m["id"] == only]
        if not ms:
            raise SystemExit(f"No member with id {only!r}")

    manifest = {}
    if MANIFEST.exists():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    # Only (re)render cards whose inputs changed or whose PNG is missing.
    # PNG screenshots are not byte-reproducible across Chrome / font versions,
    # so re-rendering unchanged cards would churn the repo on every weekly
    # sync. The content manifest (input-hash per slug) is the freshness test.
    todo = []
    for m in ms:
        slug, want = m["id"], card_hash(card_inputs(m))
        fresh = (not force) and manifest.get(slug) == want and (CARDS_DIR / f"{slug}.png").exists()
        if not fresh:
            todo.append(m)
        manifest[slug] = want

    if todo:
        chrome = _find_chrome()
        tmp = Path(tempfile.mkdtemp(prefix="ogcards-", dir=str(ROOT)))
        rel = tmp.relative_to(ROOT)
        port = _free_port()
        httpd = _serve(ROOT, port)
        try:
            for m in todo:
                inp = card_inputs(m)
                slug = m["id"]
                (tmp / f"{slug}.html").write_text(card_markup(inp), encoding="utf-8")
                out = CARDS_DIR / f"{slug}.png"
                url = f"http://127.0.0.1:{port}/{rel.as_posix()}/{slug}.html"
                subprocess.run([
                    chrome, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                    "--force-device-scale-factor=1", "--window-size=1200,630",
                    "--virtual-time-budget=6000", f"--screenshot={out}", url,
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(0.05)
                print(f"  ✓ {slug}.png")
        finally:
            httpd.shutdown()
            shutil.rmtree(tmp, ignore_errors=True)
    else:
        print("  (all cards already current)")

    # Prune manifest entries and stale PNGs for members that no longer exist
    # (full rebuilds only, so a single --only run never deletes siblings).
    if not only:
        live = {m["id"] for m in members()}
        for slug in list(manifest):
            if slug not in live:
                del manifest[slug]
                (CARDS_DIR / f"{slug}.png").unlink(missing_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"✓ {len(todo)} card(s) rendered; manifest has {len(manifest)} entries.")
    return 0


def check() -> int:
    if not MANIFEST.exists():
        print("✗ assets/og/people/_manifest.json missing — run build-og-cards.py", file=sys.stderr)
        return 1
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    stale, missing_png = [], []
    live_ids = set()
    for m in members():
        slug = m["id"]
        live_ids.add(slug)
        want = card_hash(card_inputs(m))
        if manifest.get(slug) != want:
            stale.append(slug)
        if not (CARDS_DIR / f"{slug}.png").exists():
            missing_png.append(slug)
    orphan = sorted(set(manifest) - live_ids)
    if stale or missing_png or orphan:
        if stale:
            print(f"✗ {len(stale)} card(s) stale (inputs changed): {', '.join(sorted(stale))}", file=sys.stderr)
        if missing_png:
            print(f"✗ {len(missing_png)} card PNG(s) missing: {', '.join(sorted(missing_png))}", file=sys.stderr)
        if orphan:
            print(f"✗ {len(orphan)} manifest entr(ies) for removed members: {', '.join(orphan)}", file=sys.stderr)
        print("  run: python3 scripts/build-og-cards.py", file=sys.stderr)
        return 1
    print(f"✓ OG cards current ({len(live_ids)} members).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate per-member OG card images.")
    ap.add_argument("--check", action="store_true", help="exit 1 if any card is stale")
    ap.add_argument("--only", metavar="SLUG", help="render a single member's card")
    ap.add_argument("--force", action="store_true", help="re-render every card, ignoring the manifest")
    args = ap.parse_args()
    if args.check:
        return check()
    return render_all(only=args.only, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
