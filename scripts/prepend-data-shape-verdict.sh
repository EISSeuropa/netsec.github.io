#!/usr/bin/env bash
# Run the data shape check inside a sync job and, when it fails, put the
# failure at the top of the auto-PR body.
#
# Usage: scripts/prepend-data-shape-verdict.sh <pr-body.md>
#
# The same check runs as a gate once the PR opens, but there it shows only as
# a red check after the review email has gone out. Running it here puts the
# reason (an unthemed keyword with no close match, a malformed field) in the
# email itself. Always exits 0: the PR still opens, and the gate on it still
# blocks the merge. Prints nothing and leaves the body alone when the check
# passes.
set -u
body="$1"
cd "$(dirname "$0")/.."

if out=$(python3 scripts/check-data-shape.py 2>&1); then
  exit 0
fi

{
  echo '> [!WARNING]'
  echo '> **The data shape check fails on this PR**, so it cannot merge until this is fixed. The sync found it before opening the PR:'
  echo
  echo '```'
  printf '%s\n' "$out" | grep -v '^✓'
  echo '```'
  echo
  cat "$body"
} > "$body.new" && mv "$body.new" "$body"
echo "data shape check failed; the warning is at the top of the PR body"
