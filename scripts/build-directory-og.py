#!/usr/bin/env python3
"""Render the directory social card (assets/images/og-image-people.png).

The card that ships on /people.html is the Open Graph image a shared directory
link unfurls as. The original was a hand-designed PNG (#495); this regenerates
it from an HTML template so it stays maintainable, and drops the hard member /
country counts. The design is a "Find your next…" headline beside a faux
dropdown (co-author / mentor / host) plus an "Add your bio" call to action, so
it shows what the directory does instead of citing figures that go stale.

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
  .frame { position:absolute; inset:0; padding:56px 80px 54px; display:flex; flex-direction:column; }
  .top { display:flex; align-items:center; gap:18px; }
  .top img { height:40px; }
  .top .eyebrow { font-size:19px; letter-spacing:.16em; color:#9fb0d6; font-weight:600; }
  .main { flex:1; min-height:0; display:flex; align-items:center; gap:64px; }
  .left { flex:0 0 auto; max-width:560px; }
  .headline { font-family:'Lexend', sans-serif; font-weight:700; font-size:88px; line-height:1.0;
    letter-spacing:-.02em; color:#f4f8ff; }
  .sub { margin-top:18px; font-size:26px; color:#aeb7d6; font-weight:500; }
  .cta { display:inline-flex; align-items:center; gap:12px; margin-top:32px;
    background:#ffcc00; color:#1a1400; font-size:27px; font-weight:700; padding:16px 28px; border-radius:999px; }
  .cta svg { width:25px; height:25px; }
  .combo { flex:1; max-width:460px; }
  .select { display:flex; align-items:center; justify-content:space-between; gap:16px;
    background:#131d33; border:1.5px solid rgba(255,255,255,.16); border-radius:16px; padding:20px 26px; }
  .select .val { font-size:38px; font-weight:600; color:#f4f8ff; }
  .select svg { width:34px; height:34px; color:#ffcc00; flex:0 0 auto; }
  .menu { margin-top:12px; background:#16213c; border:1.5px solid rgba(255,255,255,.14); border-radius:16px;
    padding:10px; box-shadow:0 24px 60px rgba(0,0,0,.5); }
  .opt { display:flex; align-items:center; gap:16px; padding:16px 20px; border-radius:11px;
    font-size:38px; font-weight:600; color:#d7def2; }
  .opt.sel { background:rgba(10,132,255,.20); color:#fff; }
  .opt .tick { width:30px; height:30px; color:transparent; flex:0 0 auto; }
  .opt.sel .tick { color:#ffcc00; }
  .foot { display:flex; align-items:center; }
  .foot .url { font-size:26px; color:#7f8cb0; letter-spacing:.02em; }
</style></head>
<body>
  <div class="accent"></div>
  <div class="frame">
    <div class="top">
      <img src="/assets/images/brand/netsec-lockup-white.png" alt="">
      <span class="eyebrow">THE NETWORK · OPEN DIRECTORY</span>
    </div>
    <div class="main">
      <div class="left">
        <div class="headline">Find your<br>next&hellip;</div>
        <div class="sub">in the NetSec member directory.</div>
        <span class="cta">Add your bio
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>
        </span>
      </div>
      <div class="combo">
        <div class="select"><span class="val">co-author</span>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>
        </div>
        <div class="menu">
          <div class="opt sel"><svg class="tick" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>co-author</div>
          <div class="opt"><svg class="tick" viewBox="0 0 24 24"></svg>mentor</div>
          <div class="opt"><svg class="tick" viewBox="0 0 24 24"></svg>host</div>
        </div>
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
