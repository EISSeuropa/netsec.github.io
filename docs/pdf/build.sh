#!/usr/bin/env bash
# Build NetSec-website-documentation.pdf from documentation.html.
#
# Pipeline:
#   1. Spin up a local static server so the HTML can reference local
#      images (the screenshots in this folder) and Mermaid can load
#      from the CDN.
#   2. Optionally refresh the six site screenshots (snap-home, snap-about,
#      snap-essc-2026, snap-network (the Directory), snap-grants and
#      snap-map (the Network Map)) from the live worktree, as JPEGs.
#   3. Headless Chrome renders documentation.html to A4 PDF with a
#      generous --virtual-time-budget so Mermaid finishes drawing
#      all seven diagrams before the print snapshot.
#
# Usage:
#   ./build.sh             # rebuild the PDF only
#   ./build.sh --shots     # also refresh the three site screenshots
#
# Requires:
#   - macOS with Google Chrome.app installed
#   - python3 on PATH (only used for the local server)

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT=8765

if [[ ! -x "$CHROME" ]]; then
  echo "Google Chrome.app not found at $CHROME — install it or edit this script." >&2
  exit 1
fi

# Resolve a python3 that actually runs. Some machines have a stale x86
# framework python3 first on PATH, which fails with "Bad CPU type in
# executable" on Apple Silicon and would leave the screenshot server dead.
PY3="$(command -v python3 || true)"
if [[ -z "$PY3" ]] || ! "$PY3" -c 'pass' >/dev/null 2>&1; then
  for cand in /usr/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
    if [[ -x "$cand" ]] && "$cand" -c 'pass' >/dev/null 2>&1; then PY3="$cand"; break; fi
  done
fi
if [[ -z "$PY3" ]] || ! "$PY3" -c 'pass' >/dev/null 2>&1; then
  echo "No working python3 found (needed for the local screenshot server)." >&2
  exit 1
fi

# Optional: refresh screenshots ------------------------------------------
if [[ "${1-}" == "--shots" ]]; then
  echo "→ Refreshing screenshots from worktree at $REPO_ROOT"
  ( cd "$REPO_ROOT" && "$PY3" -m http.server $PORT --bind 127.0.0.1 ) >/tmp/netsec-pdf-srv.log 2>&1 &
  SRV=$!
  trap 'kill $SRV 2>/dev/null || true' EXIT
  sleep 1
  # label:path. "network" is the Directory, named before the Network Map
  # existed; "map" is the Network Map itself, added for pack v1.13.0.
  for page in home:index.html about:about.html essc-2026:essc-2026.html network:people.html grants:grants.html map:network-map.html; do
    label="${page%%:*}"
    path="${page#*:}"
    # Window height bumped from 1600 to 3200 so the IntersectionObserver-
    # gated reveal-on-scroll sections on the home page are inside the
    # viewport at first paint; otherwise the screenshot captures the
    # hero but everything below stays hidden with opacity 0. The
    # virtual-time budget also goes up so the reveal transition has
    # room to complete inside the synthetic clock.
    # force-device-scale-factor=1 so the capture is the 1280 logical pixels
    # asked for. Without it a Mac screenshots at DPR 2, and the five figures
    # arrived at 2560x6400: sixteen megapixels each, embedded whole into a
    # print document that caps them at 170mm. That is what took the PDF to
    # 24.6 MB, of which 22.1 MB was these images (#1727).
    "$CHROME" --headless --no-sandbox --disable-gpu \
      --window-size=1280,3200 --hide-scrollbars \
      --force-device-scale-factor=1 \
      --virtual-time-budget=12000 \
      --screenshot="$HERE/snap-$label.png" \
      "http://127.0.0.1:$PORT/$path" 2>/dev/null
    # JPEG for the figures. At 1280px across the 170mm the layout allows,
    # that is about 190 DPI, and a screenshot of a page is a photograph of
    # text rather than text: quality 90 keeps it legible at six times less.
    "$PY3" - "$HERE/snap-$label" <<'CONVERT'
import sys
from PIL import Image
stem = sys.argv[1]
with Image.open(f"{stem}.png") as im:
    im.convert("RGB").save(f"{stem}.jpg", "JPEG", quality=90,
                           optimize=True, progressive=True)
CONVERT
    rm -f "$HERE/snap-$label.png"
    echo "   $HERE/snap-$label.jpg"
  done
  kill $SRV 2>/dev/null || true
  trap - EXIT
fi

# Build the PDF -----------------------------------------------------------
echo "→ Building NetSec-website-documentation.pdf"
"$CHROME" --headless --no-sandbox --disable-gpu --hide-scrollbars \
  --no-pdf-header-footer \
  --virtual-time-budget=30000 \
  --print-to-pdf="$HERE/NetSec-website-documentation.pdf" \
  "file://$HERE/documentation.html" 2>&1 | grep -E '(written|ERROR)' || true

ls -lh "$HERE/NetSec-website-documentation.pdf"
echo "✓ Done."
