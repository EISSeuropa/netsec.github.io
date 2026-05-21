#!/usr/bin/env bash
# scripts/build-search.sh — rebuild the Pagefind search index.
#
# Usage:
#   ./scripts/build-search.sh           # rebuild ./pagefind/
#   ./scripts/build-search.sh --check   # exit 1 if the index would drift
#
# When to run:
#   - After any HTML change that affects searchable content (any
#     <main data-pagefind-body> body, on any page in any locale).
#   - CI runs this with --check on every PR; merging is blocked
#     when the committed index diverges from what the script would
#     produce.
#
# Pinned to Pagefind 1.5.2 so re-builds across machines / CI runs
# are deterministic and the committed shard hashes stay stable.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/.." && pwd)"
cd "$REPO_ROOT"

PAGEFIND_VERSION="1.5.2"

# Pagefind writes a top-level pagefind-entry.json that lists the
# per-language shard hashes — but it writes the languages in
# hash-table-iteration order, which is non-deterministic across
# runs. Normalise it with `python -m json.tool --sort-keys` so the
# committed manifest and the CI rebuild are byte-identical.
normalise_entry() {
  local dir="$1"
  python3 -m json.tool --sort-keys --compact \
    "$dir/pagefind-entry.json" "$dir/pagefind-entry.json.tmp"
  mv "$dir/pagefind-entry.json.tmp" "$dir/pagefind-entry.json"
}

# npm/npx, depending on Node version, sometimes drops a
# node-compile-cache directory inside the output path. It's a
# cache, not part of the index; remove it before comparison.
strip_cache() {
  rm -rf "$1/node-compile-cache"
}

if [[ "${1-}" == "--check" ]]; then
  TMPROOT="$(mktemp -d -t netsec-pagefind-check-XXXXXX)"
  trap 'rm -rf "$TMPROOT"' EXIT
  TMPDIR="$TMPROOT/pagefind"
  echo "→ Building search index to $TMPDIR for comparison"
  npx -y "pagefind@$PAGEFIND_VERSION" --site . --output-path "$TMPDIR" >/dev/null
  strip_cache "$TMPDIR"
  normalise_entry "$TMPDIR"
  if ! diff -r --brief "$TMPDIR" "$REPO_ROOT/pagefind" >/dev/null 2>&1; then
    echo "✗ Search index is out of sync with the HTML content."
    echo "  Run: ./scripts/build-search.sh"
    echo "  Then commit the resulting changes under ./pagefind/."
    diff -r --brief "$TMPDIR" "$REPO_ROOT/pagefind" || true
    exit 1
  fi
  echo "✓ Search index matches the HTML content."
  exit 0
fi

echo "→ Rebuilding search index to ./pagefind/"
rm -rf "$REPO_ROOT/pagefind"
npx -y "pagefind@$PAGEFIND_VERSION" --site . --output-path "$REPO_ROOT/pagefind"
strip_cache "$REPO_ROOT/pagefind"
normalise_entry "$REPO_ROOT/pagefind"
echo "✓ Done."
