#!/usr/bin/env python3
"""Render the social card of each event page (assets/og/events/<page>.jpg).

One 1200x630 card per page that an event in data/events.json names as its
url: the ESSC pages, the policy workshop pages and the Training School
(#2185). The card names the event type, the event, its date and its venue, in
the visual style of the general card (build-general-og.py). Which event a page
shows, and the wording, come from scripts/_event_cards.py, which inject-seo.py
and social-post.py read as well.

The cards are not committed. pages-deploy.yml renders them on every deploy,
as it does the member cards (#1716), so a date moved by the Indico sync
reaches the card on the next deploy. assets/og/events/ is gitignored.

  python3 scripts/build-event-og.py              # every event page
  python3 scripts/build-event-og.py --only PAGE  # one page, e.g. essc-2027

Run from the repo root. Stdlib only; needs Google Chrome / Chromium.
"""
from __future__ import annotations

import argparse
import html
import importlib.util
import shutil
import string
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import _event_cards as ec  # noqa: E402


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CALENDAR_ICON = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
                 'stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2"/>'
                 '<path d="M3 10h18M8 3v4M16 3v4"/></svg>')
PIN_ICON = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s7-6.2 7-12a7 7 0 0 0-14 0c0 5.8 7 12 7 12z"/>'
            '<circle cx="12" cy="10" r="2.5"/></svg>')

CARD_HTML = string.Template("""<!DOCTYPE html>
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
  .eyebrow { align-self:flex-start; margin-top:56px; display:flex; align-items:center; gap:12px;
    border:1.5px solid #c5d0f0; background:#e6ebfb; border-radius:999px; padding:7px 18px;
    font:600 16px 'Inter', sans-serif; letter-spacing:.16em; text-transform:uppercase; color:#1d2d6b; }
  .eyebrow i { width:8px; height:8px; border-radius:50%; background:#1d2d6b; }
  h1 { margin-top:24px; font-family:'Lexend', sans-serif; font-weight:700; font-size:80px; line-height:1.06;
    letter-spacing:-.03em; max-width:1064px; }
  h1.long { font-size:68px; }
  /* Fail-safe behind _event_cards.shorten: whatever the text, the title
     stops at two lines and each fact at one, so nothing reaches the footer. */
  h1 { display:-webkit-box; -webkit-box-orient:vertical; -webkit-line-clamp:2; overflow:hidden; }
  .fact > span, .fact > b { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; min-width:0; }
  .facts { margin-top:34px; display:flex; flex-direction:column; gap:14px; }
  .fact { display:flex; align-items:center; gap:16px; font-size:29px; line-height:1.3; color:#2b3850; }
  .fact b { font-weight:600; color:#0b1220; }
  .fact svg { flex:none; width:34px; height:34px; color:#003399; }
  .foot { margin-top:auto; display:flex; align-items:flex-end; justify-content:space-between; }
  .action { font-size:18px; font-weight:500; color:#4a5670; }
  .eu { display:flex; align-items:center; gap:14px; font-size:17px; line-height:1.3; color:#4a5670; }
  .eu svg { width:60px; height:40px; }
</style></head>
<body>
  <img class="petal" src="/assets/images/brand/netsec-mark.png" alt="">
  <div class="frame">
    <div class="top">
      <img src="/assets/images/brand/netsec-lockup-primary.png" alt="">
      <span class="url"><i></i>${url}</span>
    </div>
    <span class="eyebrow"><i></i>${eyebrow}</span>
    <h1${h1_class}>${heading}</h1>
    <div class="facts">
      <div class="fact">${calendar}<b>${date}</b></div>
      <div class="fact">${pin}<span><b>${institution}</b>${place}</span></div>
    </div>
    <div class="foot">
      <div class="action">COST Action CA24154</div>
      <div class="eu">${eu_flag}<div>Funded by<br>the European Union</div></div>
    </div>
  </div>
</body></html>
""")

# A heading longer than this sets in the smaller size, so it stays on two lines.
LONG_HEADING = 34


def card_markup(page: str, ev: dict, eu_flag: str) -> str:
    institution, place = ec.venue(ev)
    title = ec.heading(ev)
    return CARD_HTML.substitute(
        url=html.escape(f"netsec-cost.eu/{page}"),
        eyebrow=html.escape(ec.eyebrow(ev)),
        h1_class=' class="long"' if len(title) > LONG_HEADING else "",
        heading=html.escape(title),
        calendar=CALENDAR_ICON,
        date=html.escape(ev["displayDate"]["en"]),
        pin=PIN_ICON,
        institution=html.escape(institution),
        place=html.escape(f" · {place}") if place else "",
        eu_flag=eu_flag,
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--only", metavar="PAGE", help="Render one event page's card, e.g. essc-2027.")
    args = p.parse_args()

    cards = ec.card_events()
    if args.only:
        if args.only not in cards:
            print(f"No event card for {args.only!r}. Event pages: {', '.join(sorted(cards))}")
            return 2
        cards = {args.only: cards[args.only]}

    boc = _load("build_og_cards", "build-og-cards.py")
    eu_flag = _load("build_general_og", "build-general-og.py")._eu_flag()
    chrome = boc._find_chrome()
    (ROOT / ec.CARD_DIR).mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="eventog-", dir=str(ROOT)))
    port = boc._free_port()
    httpd = boc._serve(ROOT, port)
    try:
        jobs = []
        for page, ev in sorted(cards.items()):
            (tmp / f"{page}.html").write_text(card_markup(page, ev, eu_flag), encoding="utf-8")
            url = f"http://127.0.0.1:{port}/{tmp.relative_to(ROOT).as_posix()}/{page}.html"
            jobs.append((url, ec.card_path(page)))
        boc._capture_cards(chrome, jobs)
        for _, out in jobs:
            print(f"✓ wrote {out.relative_to(ROOT)}")
        return 0
    finally:
        httpd.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
