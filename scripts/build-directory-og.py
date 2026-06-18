#!/usr/bin/env python3
"""Render the directory social card (assets/images/og-image-people.png).

The card that ships on /people.html is the Open Graph image a shared directory
link unfurls as. The original was a hand-designed PNG (#495); this regenerates
it from an HTML template so it stays maintainable, and drops the hard member /
country counts in favour of action-verb features (find a mentor, host an STSM,
filter by theme) that do not go stale as the directory grows.

Reuses the headless-Chrome + CDP capture from build-og-cards.py for an exact
1200x630 PNG on macOS and Linux alike.

  python3 scripts/build-directory-og.py

Run from the repo root. Stdlib only; needs Google Chrome / Chromium.
"""
from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "images" / "og-image-people.png"

# Borrow the CDP renderer (serve + capture) from the per-member card builder.
_spec = importlib.util.spec_from_file_location("build_og_cards", ROOT / "scripts" / "build-og-cards.py")
boc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(boc)

CARD_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<style>
  @font-face { font-family:'Lexend'; src:url('/assets/fonts/lexend-latin.woff2') format('woff2'); font-weight:600 700; font-display:block; }
  @font-face { font-family:'Inter'; src:url('/assets/fonts/inter-latin.woff2') format('woff2'); font-weight:400 600; font-display:block; }
  * { margin:0; padding:0; box-sizing:border-box; }
  html, body { width:1200px; height:630px; }
  body { font-family:'Inter', sans-serif; background:#0b1220; color:#f4f8ff; position:relative; overflow:hidden; }
  .accent { position:absolute; left:0; top:0; bottom:0; width:14px; background:#003399; }
  .frame { position:absolute; inset:0; padding:60px 80px 58px; display:flex; flex-direction:column; }
  .top { display:flex; align-items:center; gap:18px; }
  .top img { height:42px; }
  .top .eyebrow { font-size:20px; letter-spacing:.16em; color:#9fb0d6; font-weight:600; }
  .body { flex:1; min-height:0; display:flex; flex-direction:column; justify-content:center; }
  .headline { font-family:'Lexend', sans-serif; font-weight:700; font-size:82px; line-height:1.02;
    letter-spacing:-.02em; color:#f4f8ff; }
  .headline .hl { color:#ffcc00; }
  .sub { margin-top:22px; font-size:30px; line-height:1.3; color:#d7def2; font-weight:500; max-width:1010px; }
  .pills { margin-top:36px; display:flex; flex-wrap:wrap; gap:14px; }
  .pill { font-size:25px; font-weight:600; line-height:1; padding:14px 24px; border-radius:999px;
    background:rgba(10,132,255,.16); border:1px solid rgba(10,132,255,.42); color:#cfe2ff; white-space:nowrap; }
  .pill.cta { background:#ffcc00; border-color:#ffcc00; color:#1a1400; }
  .foot { display:flex; align-items:center; }
  .foot .url { font-size:27px; color:#7f8cb0; letter-spacing:.02em; }
</style></head>
<body>
  <div class="accent"></div>
  <div class="frame">
    <div class="top">
      <img src="/assets/images/brand/netsec-lockup-white.png" alt="">
      <span class="eyebrow">THE NETWORK · OPEN DIRECTORY</span>
    </div>
    <div class="body">
      <div class="headline">A directory you can<br><span class="hl">actually search</span></div>
      <div class="sub">Browse the people of the NetSec network and reach them directly.</div>
      <div class="pills">
        <span class="pill">Find a mentor</span>
        <span class="pill">Host an STSM visitor</span>
        <span class="pill">Filter by research theme</span>
        <span class="pill">Connect by working group</span>
        <span class="pill cta">Add your bio</span>
      </div>
    </div>
    <div class="foot"><span class="url">netsec-cost.eu/people</span></div>
  </div>
</body></html>
"""


def main() -> int:
    chrome = boc._find_chrome()
    tmp = Path(tempfile.mkdtemp(prefix="dirog-", dir=str(ROOT)))
    port = boc._free_port()
    httpd = boc._serve(ROOT, port)
    try:
        (tmp / "card.html").write_text(CARD_HTML, encoding="utf-8")
        url = f"http://127.0.0.1:{port}/{tmp.relative_to(ROOT).as_posix()}/card.html"
        boc._capture_cards(chrome, [(url, OUT)])
        print(f"✓ wrote {OUT.relative_to(ROOT)}")
        return 0
    finally:
        httpd.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
