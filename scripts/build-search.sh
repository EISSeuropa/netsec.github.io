#!/usr/bin/env bash
# scripts/build-search.sh — rebuild the Pagefind search index.
#
# Usage:
#   ./scripts/build-search.sh           # rebuild ./pagefind/
#   ./scripts/build-search.sh --check   # exit 1 if per-language page count drifted
#
# When to run:
#   - After any HTML change that affects searchable content (any
#     <main data-pagefind-body> body, on any page in any locale).
#   - CI runs this with --check on every PR; merging is blocked
#     when the committed page counts diverge from what the script
#     would produce.
#
# Pinned to Pagefind 1.5.2 so re-builds across machines / CI runs
# produce the same per-language page counts.
#
# A note on --check
#   Pagefind's per-platform WASM build is non-deterministic between
#   Linux (CI) and macOS (typical local). The shard hashes and WASM
#   binaries differ. We therefore *cannot* enforce a byte-diff drift
#   check. Instead we compare the per-language page_count from
#   pagefind-entry.json — which is deterministic — which catches
#   "added/removed a page without rebuilding". Content edits inside
#   an existing page are NOT caught by CI; maintainers must remember
#   to rebuild. The architecture doc spells this out.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/.." && pwd)"
cd "$REPO_ROOT"

PAGEFIND_VERSION="1.5.2"

# npm/npx, depending on Node version, sometimes drops a
# node-compile-cache directory inside the output path. It's a
# cache, not part of the index; remove it before committing.
strip_cache() {
  rm -rf "$1/node-compile-cache"
}

# Compare per-language page counts between two pagefind-entry.json
# files. Exits 1 if they differ; prints a per-locale breakdown.
counts_diff() {
  local fresh="$1" committed="$2"
  python3 - "$fresh" "$committed" <<'PY'
import json, sys
a = json.load(open(sys.argv[1]))["languages"]
b = json.load(open(sys.argv[2]))["languages"]
acounts = {k: v["page_count"] for k, v in a.items()}
bcounts = {k: v["page_count"] for k, v in b.items()}
if acounts != bcounts:
    print(f"  fresh:     {acounts}")
    print(f"  committed: {bcounts}")
    sys.exit(1)
PY
}

if [[ "${1-}" == "--check" ]]; then
  TMPROOT="$(mktemp -d -t netsec-pagefind-check-XXXXXX)"
  trap 'rm -rf "$TMPROOT"' EXIT
  TMPDIR="$TMPROOT/pagefind"
  echo "→ Building search index to $TMPDIR for comparison"
  npx -y "pagefind@$PAGEFIND_VERSION" --site . --output-path "$TMPDIR" >/dev/null
  if ! counts_diff "$TMPDIR/pagefind-entry.json" "$REPO_ROOT/pagefind/pagefind-entry.json"; then
    echo "✗ Per-language page count drifted between the committed index"
    echo "  and a fresh build."
    echo "  Run: ./scripts/build-search.sh"
    echo "  Then commit the resulting changes under ./pagefind/."
    exit 1
  fi
  echo "✓ Per-language page counts match."
  exit 0
fi

echo "→ Rebuilding search index to ./pagefind/"
rm -rf "$REPO_ROOT/pagefind"
npx -y "pagefind@$PAGEFIND_VERSION" --site . --output-path "$REPO_ROOT/pagefind"
strip_cache "$REPO_ROOT/pagefind"
echo "✓ Done."
