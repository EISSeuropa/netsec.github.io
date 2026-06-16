#!/usr/bin/env bash
# Headless render smoke test for the runtime-rendered pages.
#
# The shape lint (check-data-shape.py) validates the data files; this
# script closes the remaining gap by rendering the consuming pages in
# headless Chrome against the working tree and asserting that the
# runtime renderers actually produced cards. A data change that parses
# cleanly but blanks a page (renamed key the renderer reads, an
# upstream contract drift the shape lint is too loose to catch) fails
# here. See issue #724.
#
# Pages and assertions:
#   /essc-2026.html   >= 1 programme-slot article (the live programme)
#   /people.html      >= 2 member-card occurrences (the <template>
#                     contributes one; a rendered grid adds more)
#   /index.html       >= 1 event-atc block (the home events cards)
#
# Requires a Chrome/Chromium binary (preinstalled on the GitHub
# ubuntu runners; resolved from common paths locally, or set
# CHROME_BIN). Serves the repo root on a local port for the fetch()
# calls the renderers make.
#
# Usage: ./scripts/check-render-smoke.sh
# Exit codes: 0 all pages render, 1 any page blanked or Chrome missing.
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${SMOKE_PORT:-8819}"

chrome=""
for candidate in "${CHROME_BIN:-}" google-chrome google-chrome-stable chromium-browser chromium \
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; do
  [ -n "$candidate" ] || continue
  if command -v "$candidate" >/dev/null 2>&1; then chrome="$candidate"; break; fi
done
if [ -z "$chrome" ]; then
  echo "✗ no Chrome/Chromium binary found (set CHROME_BIN)" >&2
  exit 1
fi

# Resolve a python3 that actually runs (some macOS setups put a
# wrong-architecture framework python3 first on PATH).
py=""
for candidate in python3 /usr/bin/python3 /opt/homebrew/bin/python3; do
  if "$candidate" -c '' >/dev/null 2>&1; then py="$candidate"; break; fi
done
if [ -z "$py" ]; then
  echo "✗ no working python3 found for the local server" >&2
  exit 1
fi

cd "$ROOT"
"$py" -m http.server "$PORT" --bind 127.0.0.1 >/dev/null 2>&1 &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null' EXIT
sleep 1
if ! kill -0 "$server_pid" 2>/dev/null; then
  echo "✗ local server failed to start on port $PORT" >&2
  exit 1
fi

render_count() {
  # $1 page path, $2 marker string, $3 optional extra virtual-time-budget
  # (default 10000). Pages whose renderers are in external <script defer>
  # files need a larger budget: two chained network fetches (the script
  # itself plus the data file) must both complete before the budget expires.
  local budget="${3:-10000}"
  "$chrome" --headless --no-sandbox --disable-gpu --dump-dom \
    "--virtual-time-budget=$budget" "http://127.0.0.1:${PORT}/$1" 2>/dev/null \
    | grep -o "$2" | wc -l | tr -d ' '
}

render_count_slow() {
  # Like render_count but with a 60 s virtual-time-budget for pages that
  # load their renderer from an external <script defer> and then make a
  # second async fetch for data (two-hop network chain).
  render_count "$1" "$2" 60000
}

fail=0
check() {
  # $1 page, $2 marker, $3 minimum count, $4 optional render function
  local n fn="${4:-render_count}"
  n="$($fn "$1" "$2")"
  if [ "$n" -ge "$3" ]; then
    echo "✓ $1: $n × '$2' (need >= $3)"
  else
    echo "✗ $1: $n × '$2' (need >= $3) — renderer produced no content"
    fail=1
  fi
}

check "essc-2026.html" 'class="programme-slot' 1
# people-directory.js is an external <script defer> that then fetches
# data/bios.json — two chained network hops need the extended budget.
check "people.html" 'class="member-card' 2 render_count_slow
check "index.html" 'class="event-atc' 1

exit "$fail"
