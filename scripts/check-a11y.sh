#!/usr/bin/env bash
# scripts/check-a11y.sh — accessibility scan across every public
# page-locale, using pa11y (which wraps both HTML_CodeSniffer's
# WCAG 2.1 AA rule set and axe-core under a Puppeteer-bundled
# headless Chromium — so it doesn't depend on a system Chrome
# matching a system ChromeDriver, the failure mode that bit
# @axe-core/cli on the maintainer's laptop in May 2026).
#
# Usage:
#   ./scripts/check-a11y.sh                  # full scan, writes tmp/a11y-report.md
#   ./scripts/check-a11y.sh PAGE [PAGE ...]  # scan only the named pages
#
# Behaviour:
#   - Spins up a temporary `python3 -m http.server` on a free port
#     so the scanner can hit the pages as a real browser would
#     (file:// trips cross-origin restrictions; localhost doesn't).
#   - Walks every *.html at the repo root (or just the ones you
#     name), runs `npx -y pa11y` against each, captures the
#     summary into a single Markdown report at tmp/a11y-report.md.
#   - Exits non-zero if any page has **errors** (warnings + notices
#     are listed in the report but don't fail the build — htmlcs
#     can be over-triggered on warnings).
#
# Pre-requirements:
#   - Node.js available on $PATH.
#   - First run downloads pa11y (~150 MB inc. bundled Chromium);
#     subsequent runs reuse the npx cache.
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

echo "→ scanning ${#PAGES[@]} pages with pa11y (first run downloads Chromium)..."

{
  echo "# Accessibility scan — \`scripts/check-a11y.sh\`"
  echo
  echo "Generated $(date -u +"%Y-%m-%dT%H:%M:%SZ") against \`localhost:${PORT}\`."
  echo
  echo "Scanner: pa11y (HTML_CodeSniffer WCAG 2.1 AA rule set + Puppeteer-bundled headless Chromium)."
  echo
  echo "## Summary"
  echo
  echo "| Page | Errors | Warnings | Notices |"
  echo "|---|---|---|---|"
} > "$REPORT"

# Per-page detail accumulates into a second pass-through.
DETAILS_FILE="$(mktemp -t a11y-details-XXXXXX.md)"
trap "rm -f \"$DETAILS_FILE\"; kill ${SRV_PID} 2>/dev/null || true" EXIT

ANY_FAIL=0

for page in "${PAGES[@]}"; do
  URL="http://127.0.0.1:${PORT}/${page}"
  echo "  · $page"
  # pa11y emits JSON when --reporter json is passed. It exits with
  # code 2 if any errors are found — `|| true` so we keep going and
  # capture the JSON either way; we decide pass/fail from the counts.
  JSON="$(npx -y pa11y@latest --reporter json --standard WCAG2AA "$URL" 2>/dev/null || true)"

  # Pull out counts (errors / warnings / notices). Use `python3 -c`
  # rather than `python3 - <<HEREDOC` so that stdin stays free for
  # the piped JSON — the heredoc form competes with the pipe and
  # silently makes Python read JSON-as-code (was the May 2026 bug).
  COUNTS=$(printf '%s' "$JSON" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    print("ERR | ERR | ERR")
    sys.exit(0)
errors = warnings = notices = 0
for issue in data:
    t = issue.get("type", "")
    if t == "error":   errors += 1
    elif t == "warning": warnings += 1
    elif t == "notice":  notices += 1
print(f"{errors} | {warnings} | {notices}")
' 2>/dev/null || echo "ERR | ERR | ERR")
  echo "| \`$page\` | $COUNTS |" >> "$REPORT"

  # Append per-page error detail to DETAILS_FILE.
  if [[ "${COUNTS%% *}" != "0" && "${COUNTS%% *}" != "ERR" ]]; then
    ANY_FAIL=1
    {
      echo
      echo "### \`$page\`"
      echo
      printf '%s' "$JSON" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
for issue in data:
    if issue.get("type") != "error":
        continue
    code = issue.get("code", "?")
    msg = issue.get("message", "")
    sel = issue.get("selector", "")
    ctx = issue.get("context", "")[:100]
    print(f"- **{code}**")
    print(f"  - {msg}")
    print(f"  - selector: `{sel}`")
    print(f"  - context: `{ctx}`")
' 2>/dev/null
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
  echo "✓ pa11y clean across ${#PAGES[@]} pages."
  exit 0
else
  echo "✗ pa11y errors present — see $REPORT."
  exit 1
fi
