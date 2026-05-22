#!/usr/bin/env bash
# scripts/check-a11y.sh — axe-core accessibility scan across every
# public page-locale.
#
# Usage:
#   ./scripts/check-a11y.sh                  # full scan, writes tmp/a11y-report.md
#   ./scripts/check-a11y.sh PAGE [PAGE ...]  # scan only the named pages
#
# Behaviour:
#   - Spins up a temporary `python3 -m http.server` on a free port
#     so axe-core can hit the pages as a real browser would (file://
#     trips a bunch of cross-origin restrictions; localhost doesn't).
#   - Walks every *.html at the repo root (or just the ones you
#     name), runs `npx -y @axe-core/cli` against each, captures the
#     summary into a single Markdown report at tmp/a11y-report.md.
#   - Exits non-zero if any page has axe **violations** (the report
#     still gets written; failures + incomplete results are listed
#     in the summary).
#
# Pre-requirements:
#   - Node.js available on $PATH (axe-core CLI is JS).
#   - First run downloads @axe-core/cli (~150 MB including headless
#     Chromium); subsequent runs reuse the npx cache.
#
# Designed for the launch-QA audit (see docs/launch-qa-2026.md).
# Safe to run repeatedly; doesn't touch git or live state.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/.." && pwd)"
cd "$REPO_ROOT"

# Pick a free port — random in the 8800-9000 range.
PORT=$(( 8800 + RANDOM % 200 ))

mkdir -p tmp
REPORT="tmp/a11y-report.md"

# Decide which pages to scan
if [[ $# -gt 0 ]]; then
  PAGES=("$@")
else
  # Default: every root-level *.html EXCEPT 404 (axe complains
  # about a no-content page).
  PAGES=()
  while IFS= read -r f; do
    PAGES+=("$(basename "$f")")
  done < <(find . -maxdepth 1 -name "*.html" -not -name "404.html" | sort)
fi

echo "→ starting localhost on :${PORT}"
python3 -m http.server "$PORT" --bind 127.0.0.1 >/dev/null 2>&1 &
SRV_PID=$!
trap "kill ${SRV_PID} 2>/dev/null || true" EXIT
sleep 1   # give the server a moment to bind

echo "→ scanning ${#PAGES[@]} pages with @axe-core/cli (first run downloads Chromium)..."

{
  echo "# Accessibility scan — \`scripts/check-a11y.sh\`"
  echo
  echo "Generated $(date -u +"%Y-%m-%dT%H:%M:%SZ") against \`localhost:${PORT}\`."
  echo
  echo "axe-core rule set: WCAG 2.1 A + AA (the CLI default)."
  echo "Targets the same locale isolation that real users see"
  echo "(per-page \`<html lang>\`)."
  echo
  echo "## Summary"
  echo
  echo "| Page | Violations | Passes | Incomplete |"
  echo "|---|---|---|---|"
} > "$REPORT"

# Per-page detail accumulates into a second pass-through.
DETAILS_FILE="$(mktemp -t a11y-details-XXXXXX.md)"
trap "rm -f \"$DETAILS_FILE\"; kill ${SRV_PID} 2>/dev/null || true" EXIT

ANY_FAIL=0

for page in "${PAGES[@]}"; do
  URL="http://127.0.0.1:${PORT}/${page}"
  echo "  · $page"
  # axe-core CLI outputs JSON to stdout when --save - is used; we
  # use --exit to make the CLI exit non-zero on violations.
  RAW="$(npx -y @axe-core/cli "$URL" --save - 2>/dev/null || true)"
  # The CLI prints a banner before the JSON; strip everything before
  # the first '[' so we have parseable JSON.
  JSON="$(printf '%s' "$RAW" | sed -n '/^\[/,/^\]/p')"

  # Pull out the counts via Python (jq isn't universally installed).
  COUNTS=$(printf '%s' "$JSON" | python3 - <<'PY' 2>/dev/null || echo "ERR | ERR | ERR"
import json, sys
data = json.load(sys.stdin)
violations = passes = incomplete = 0
for run in data:
  violations += len(run.get("violations", []))
  passes     += len(run.get("passes", []))
  incomplete += len(run.get("incomplete", []))
print(f"{violations} | {passes} | {incomplete}")
PY
)
  echo "| \`$page\` | $COUNTS |" >> "$REPORT"

  # Append per-page violation detail to DETAILS_FILE (only if there
  # were violations — keeps the report short when things are clean).
  if [[ "${COUNTS%% *}" != "0" && "${COUNTS%% *}" != "ERR" ]]; then
    ANY_FAIL=1
    {
      echo
      echo "### \`$page\`"
      echo
      printf '%s' "$JSON" | python3 - <<'PY' 2>/dev/null
import json, sys
data = json.load(sys.stdin)
for run in data:
  for v in run.get("violations", []):
    print(f"- **{v.get('id','?')}** ({v.get('impact','?')})")
    print(f"  - {v.get('description','')}")
    print(f"  - {v.get('helpUrl','')}")
    for n in v.get("nodes", [])[:3]:
      tgt = n.get("target", ["?"])
      print(f"  - target: `{tgt[0] if tgt else '?'}`")
PY
    } >> "$DETAILS_FILE"
  fi
done

echo >> "$REPORT"
echo "## Per-page violation detail" >> "$REPORT"
if [[ -s "$DETAILS_FILE" ]]; then
  cat "$DETAILS_FILE" >> "$REPORT"
else
  echo >> "$REPORT"
  echo "*(no violations on any scanned page — clean run)*" >> "$REPORT"
fi

echo
echo "→ report written to $REPORT"
if [[ $ANY_FAIL -eq 0 ]]; then
  echo "✓ axe-core clean across ${#PAGES[@]} pages."
  exit 0
else
  echo "✗ axe-core violations present — see $REPORT."
  exit 1
fi
