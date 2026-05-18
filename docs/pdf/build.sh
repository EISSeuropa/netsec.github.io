#!/usr/bin/env bash
# Build NetSec-website-documentation.pdf from documentation.html.
#
# Pipeline:
#   1. Spin up a local static server so the HTML can reference local
#      images (the screenshots in this folder) and Mermaid can load
#      from the CDN.
#   2. Optionally refresh the three site screenshots (snap-home.png,
#      snap-network.png, snap-grants.png) from the live worktree.
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

# Optional: refresh screenshots ------------------------------------------
if [[ "${1-}" == "--shots" ]]; then
  echo "→ Refreshing screenshots from worktree at $REPO_ROOT"
  ( cd "$REPO_ROOT" && python3 -m http.server $PORT --bind 127.0.0.1 ) >/tmp/netsec-pdf-srv.log 2>&1 &
  SRV=$!
  trap 'kill $SRV 2>/dev/null || true' EXIT
  sleep 1
  for page in home:index.html network:people.html grants:grants.html; do
    label="${page%%:*}"
    path="${page#*:}"
    "$CHROME" --headless --no-sandbox --disable-gpu \
      --window-size=1280,1600 --hide-scrollbars \
      --virtual-time-budget=5000 \
      --screenshot="$HERE/snap-$label.png" \
      "http://127.0.0.1:$PORT/$path" 2>/dev/null
    echo "   $HERE/snap-$label.png"
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
