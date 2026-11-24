#!/usr/bin/env bash
# scripts/build-search.sh — rebuild the Pagefind search index.
#
# Usage:
#   ./scripts/build-search.sh
#
# Where the index lives:
#   /pagefind/ at the repo root. The directory is gitignored — the
#   index is built fresh at deploy time by the Pages workflow
#   (.github/workflows/pages-deploy.yml), not committed to main.
#   We deliberately stopped committing it: two parallel PRs that
#   each rebuilt the index conflicted on the content-hashed shard
#   filenames in pagefind-entry.json. Deferring the build to the
#   deploy step eliminates that conflict source for good.
#
# When you'd still run this locally:
#   - To preview a content change with working search before
#     pushing — the gitignored /pagefind/ is served by any local
#     static server (`python3 -m http.server`, etc.).
#   - The script is also what CI calls in pages-deploy.yml and in
#     search-drift.yml (build sanity check on PRs).
#
# Pagefind is a devDependency: package-lock.json pins the exact version,
# so re-builds across machines and CI runs produce the same per-language
# page counts, and Dependabot's npm block proposes its updates (#2267).
# The script installs it with `npm ci` when node_modules lacks a working
# binary.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/.." && pwd)"
cd "$REPO_ROOT"

PAGEFIND="$REPO_ROOT/node_modules/.bin/pagefind"

# npm/npx, depending on Node version, sometimes drops a
# node-compile-cache directory inside the output path. It's a
# cache, not part of the index; remove it after build.
strip_cache() {
  rm -rf "$1/node-compile-cache"
}

# Backwards-compatibility shim: the old --check mode compared a
# fresh build against the committed index. Since /pagefind/ is no
# longer committed, the comparison has no anchor and the flag is a
# no-op now. Print a deprecation note so old muscle memory and any
# stray references in docs / scripts surface, then run the build
# anyway so callers don't break.
if [[ "${1-}" == "--check" ]]; then
  echo "ℹ️  --check is deprecated: /pagefind/ is no longer committed."
  echo "    CI now runs a build sanity check directly (see "
  echo "    .github/workflows/search-drift.yml). Running a full build."
fi

echo "→ Generating bio search stubs from data/bios.json"
python3 "$REPO_ROOT/scripts/build-bio-search-stubs.py"

echo "→ Rebuilding search index to ./pagefind/"
rm -rf "$REPO_ROOT/pagefind"
# Up to three installs for a working binary. On 2026-10-15 npm dropped the
# linux-x64 binary package without an error, and three workflows on two PRs
# went red until a rerun. The platform binary is an optional dependency of
# the pagefind package, so a dropped one leaves an install that succeeds and
# a binary that fails. `pagefind --version` catches that, and `npm ci`
# reinstalls from scratch.
for attempt in 0 1 2 3; do
  "$PAGEFIND" --version >/dev/null 2>&1 && break
  if [[ $attempt == 3 ]]; then
    echo "✗ No working Pagefind binary after three installs." >&2
    exit 1
  fi
  [[ $attempt == 0 ]] || sleep 10
  echo "  · Installing Pagefind from package-lock.json (npm ci, install $((attempt + 1)) of 3)" >&2
  npm ci --no-audit --no-fund >&2 || true
done
"$PAGEFIND" --site . --output-path "$REPO_ROOT/pagefind"
strip_cache "$REPO_ROOT/pagefind"
echo "✓ Done."
