#!/usr/bin/env python3
"""Render the general social card (assets/images/og-image.png).

The card is the Open Graph image every page except /people.html unfurls as.
The original was a hand-designed PNG (#495) with no source file. This
regenerates it from an HTML template so the title can carry the same "Net" and
"Sec" gradient as the home page hero, and so it stays editable.

Reuses the headless-Chrome + CDP capture from build-og-cards.py, the same as
build-directory-og.py, for an exact 1200x630 PNG.

  python3 scripts/build-general-og.py

Run from the repo root. Stdlib only; needs Google Chrome / Chromium.
"""
from __future__ import annotations

import importlib.util
import math
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "images" / "og-image.png"

_spec = importlib.util.spec_from_file_location("build_og_cards", ROOT / "scripts" / "build-og-cards.py")
boc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(boc)


def _eu_flag() -> str:
    """The EU emblem to its official geometry: 12 upright stars on a circle of
    radius h/3, each star of outer radius h/18, on a 3:2 field."""
    h, w = 120, 180
    r, s = h / 3, h / 18
    star = " ".join(
        f"{s * math.sin(math.pi * k / 5) * (1 if k % 2 == 0 else 0.382):.2f},"
        f"{-s * math.cos(math.pi * k / 5) * (1 if k % 2 == 0 else 0.382):.2f}"
        for k in range(10)
    )
    stars = "".join(
        f'<polygon points="{star}" transform="translate({w / 2 + r * math.sin(math.pi * i / 6):.2f},'
        f'{h / 2 - r * math.cos(math.pi * i / 6):.2f})"/>'
        for i in range(12)
    )
    return (f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w}" height="{h}" fill="#003399"/><g fill="#ffcc00">{stars}</g></svg>')


CARD_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<style>
  @font-face { font-family:'Lexend'; src:url('/assets/fonts/lexend-latin.woff2') format('woff2'); font-weight:600 700; font-display:block; }
  @font-face { font-family:'Inter'; src:url('/assets/fonts/inter-latin.woff2') format('woff2'); font-weight:400 600; font-display:block; }
  * { margin:0; padding:0; box-sizing:border-box; }
  html, body { width:1200px; height:630px; }
  body { font-family:'Inter', sans-serif; color:#0b1220; position:relative; overflow:hidden;
    background:radial-gradient(600px 420px at 12% 0%, #dfe6fb, transparent 70%),
               radial-gradient(520px 380px at 100% 20%, #fbeee6, transparent 70%),
               linear-gradient(180deg, #f1f3fb, #f8f7f6); }
  .petal { position:absolute; right:-150px; bottom:-170px; width:620px; filter:grayscale(1); opacity:.09; }
  .frame { position:absolute; inset:0; padding:60px 68px 56px; display:flex; flex-direction:column; }
  .top { display:flex; align-items:center; justify-content:space-between; }
  .top img { height:54px; }
  .url { display:flex; align-items:center; gap:12px; background:#fff; border-radius:999px; padding:12px 22px;
    font:500 21px ui-monospace, Menlo, monospace; color:#1a2236; box-shadow:0 4px 18px rgba(11,18,32,.06); }
  .url i { width:12px; height:12px; border-radius:50%; background:#2e9e5b; }
  .eyebrow { align-self:flex-start; margin-top:58px; display:flex; align-items:center; gap:12px;
    border:1.5px solid #c5d0f0; background:#e6ebfb; border-radius:999px; padding:7px 18px;
    font:600 16px 'Inter', sans-serif; letter-spacing:.16em; color:#1d2d6b; }
  .eyebrow i { width:8px; height:8px; border-radius:50%; background:#1d2d6b; }
  h1 { margin-top:22px; font-family:'Lexend', sans-serif; font-weight:700; font-size:82px; line-height:1.04;
    letter-spacing:-.035em; }
  h1 span { background:linear-gradient(135deg, #003399, #0a84ff); -webkit-background-clip:text;
    background-clip:text; -webkit-text-fill-color:transparent; }
  .lede { margin-top:20px; font-size:23px; line-height:1.4; color:#2b3850; max-width:860px; }
  .lede b { font-weight:600; color:#0b1220; }
  .foot { margin-top:auto; display:flex; align-items:flex-end; justify-content:space-between; }
  .tags { display:flex; gap:12px; }
  .tags span { background:#fff; border-radius:999px; padding:10px 18px; font-size:18px; font-weight:500; color:#1a2236; }
  .eu { display:flex; align-items:center; gap:14px; font-size:17px; line-height:1.3; color:#4a5670; }
  .eu svg { width:60px; height:40px; }
</style></head>
<body>
  <img class="petal" src="/assets/images/brand/netsec-mark.png" alt="">
  <div class="frame">
    <div class="top">
      <img src="/assets/images/brand/netsec-lockup-primary.png" alt="">
      <span class="url"><i></i>netsec-cost.eu</span>
    </div>
    <span class="eyebrow"><i></i>COST ACTION · EUROPEAN COOPERATION IN SCIENCE &amp; TECHNOLOGY</span>
    <h1><span>Net</span>working European<br><span>Sec</span>urity Knowledge</h1>
    <p class="lede">An inclusive, multidisciplinary network <b>bridging the academia–policy divide</b> and cultivating the next generation of European security scholars.</p>
    <div class="foot">
      <div class="tags"><span>Security Studies</span><span>European Defence</span><span>Strategic Autonomy</span><span>Policy Impact</span></div>
      <div class="eu">EU_FLAG<div>Funded by<br>the European Union</div></div>
    </div>
  </div>
</body></html>
"""


def main() -> int:
    chrome = boc._find_chrome()
    tmp = Path(tempfile.mkdtemp(prefix="genog-", dir=str(ROOT)))
    port = boc._free_port()
    httpd = boc._serve(ROOT, port)
    try:
        (tmp / "card.html").write_text(CARD_HTML.replace("EU_FLAG", _eu_flag()), encoding="utf-8")
        url = f"http://127.0.0.1:{port}/{tmp.relative_to(ROOT).as_posix()}/card.html"
        boc._capture_cards(chrome, [(url, OUT)])
        print(f"✓ wrote {OUT.relative_to(ROOT)}")
        return 0
    finally:
        httpd.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
