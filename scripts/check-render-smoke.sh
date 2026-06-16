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
#   /essc-2026.html   >= 1 programme-slot article (inline renderer)
#   /people.html      people-directory.js wired in HTML + >= 2 members
#                     in bios.json. Chrome's --virtual-time-budget cannot
#                     reliably wait for the two-hop chain (external <script
#                     defer> fetch + async bios.json fetch) before the
#                     budget expires, so this page uses a static check.
#   /index.html       >= 1 event-atc block (inline renderer)
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
  # $1 page path, $2 marker string. Prints the marker count in the
  # post-JS DOM. virtual-time-budget lets the fetch+render settle.
  "$chrome" --headless --no-sandbox --disable-gpu --dump-dom \
    --virtual-time-budget=10000 "http://127.0.0.1:${PORT}/$1" 2>/dev/null \
    | grep -o "$2" | wc -l | tr -d ' '
}

fail=0
check() {
  # $1 page, $2 marker, $3 minimum count
  local n
  n="$(render_count "$1" "$2")"
  if [ "$n" -ge "$3" ]; then
    echo "✓ $1: $n × '$2' (need >= $3)"
  else
    echo "✗ $1: $n × '$2' (need >= $3) — renderer produced no content"
    fail=1
  fi
}

check_people_html() {
  # people-directory.js is an external <script defer> that then makes a
  # second async fetch for data/bios.json. Chrome's --virtual-time-budget
  # expires before both hops complete, so a Chrome-based check produces a
  # false negative. Use a static check instead: verify the renderer is
  # wired into the page and that bios.json holds enough members for the
  # data shape to be meaningful (the full schema is checked by
  # check-data-shape.py; this just guards against an empty file).
  local wired member_count
  if grep -q 'src="assets/js/people-directory\.js' people.html; then
    wired=1
  else
    wired=0
  fi
  member_count="$("$py" -c "import json,sys; d=json.load(open('data/bios.json')); print(len(d.get('members',[])))")"
  if [ "$wired" -eq 1 ] && [ "$member_count" -ge 2 ]; then
    echo "✓ people.html: people-directory.js wired + bios.json has $member_count members (need >= 2)"
  elif [ "$wired" -eq 0 ]; then
    echo "✗ people.html: people-directory.js not referenced in page"
    fail=1
  else
    echo "✗ people.html: bios.json has $member_count members (need >= 2)"
    fail=1
  fi
}

check "essc-2026.html" 'class="programme-slot' 1
check_people_html
check "index.html" 'class="event-atc' 1

exit "$fail"
