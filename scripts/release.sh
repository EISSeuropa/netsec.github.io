#!/usr/bin/env bash
# scripts/release.sh — cut a tagged release of this repository.
#
# Usage:
#   scripts/release.sh <version> "<title>"          # cut the release
#   scripts/release.sh <version> "<title>" --dry-run # preview only
#
#   <version>  X.Y.Z, no leading "v" (e.g. 1.4.0)
#   <title>    short phrase summarising the key contribution of this
#              release — appears in BOTH the CHANGELOG heading
#              (`## [1.4.0] · YYYY-MM-DD — <title>`) AND the GitHub
#              Release title (`v1.4.0 — <title>`). Convention: 3-8
#              words, sentence case, no trailing punctuation.
#              Examples:
#                "Introducing FAQ and Glossary pages"      (v1.3.0)
#                "Press kit, directory tour, compact view" (v1.2.0)
#                "Initial public release"                  (v1.0.0)
#              The title is REQUIRED; the script will not run without it.
#
# Before running:
#
#   ❗ `[Unreleased]` in CHANGELOG.md must follow the hybrid release-
#      notes format documented at the top of that file: a one- to
#      three-sentence lede + 2-4 themed `### sub-sections` (prose-
#      led) + a canonical `### Index of changes` block at the bottom
#      with `#### Added` / `#### Changed` / `#### Fixed` etc. (each
#      appearing at most once, in that order). Patch releases skip
#      the lede + themes and ship the index only.
#
#      The script extracts `[Unreleased]` *verbatim* into the
#      GitHub Release notes. The confirmation prompt below prints
#      the body — eyeball it. Whatever lives in `[Unreleased]` lands
#      on the public release page.
#
# What it does, in order:
#   1.  Validate <version> against SemVer 2.0.0 (X.Y.Z, no leading "v").
#   2.  Validate <title> is non-empty.
#   3.  Refuse to run if anything is uncommitted, or if local main is
#       behind/ahead of origin/main.
#   4.  Read the [Unreleased] body from CHANGELOG.md; refuse to run if
#       it's empty or still the literal "_Nothing yet._" placeholder.
#   5.  Print the [Unreleased] body AND the title, then prompt for
#       explicit "y" confirmation before proceeding. This is the last
#       point at which an abort leaves everything untouched.
#       (--dry-run skips the prompt; the dry-run output IS the preview.)
#   6.  Promote [Unreleased] to `[<version>] · <today> — <title>` and
#       start a fresh [Unreleased] section above it. Update the
#       bottom compare links accordingly.
#   7.  Commit the changelog edit ("Release v<version> — <title>"),
#       push to main.
#   8.  Create an annotated tag v<version> on the new commit, push it.
#   9.  Use `gh release create` to publish a GitHub Release titled
#       "v<version> — <title>" whose body is the [<version>] section
#       of the changelog (markdown sliced between the two headings).
#
# Pre-conditions:
#   - `gh` CLI installed and authenticated against EISSeuropa/netsec.github.io.
#   - Your account holds the **Admin** role on the repo. The
#     `protect-main` ruleset blocks direct pushes to main for everyone
#     except Repository Admins; the release-promotion commit is the
#     one operation that legitimately needs that bypass. Maintain /
#     Write roles will see step 4 fail with a ruleset violation.
#   - If you run this through a fine-grained PAT (recommended), the
#     token needs `Contents: read+write` on the repo. That's it for
#     this script's own operations. `Administration: read` is also
#     handy (lets you `gh api .../rulesets` for verification), but
#     not required to cut a release.
#
#     The ruleset bypass is keyed to the user's *repository role*
#     (Admin), NOT to the PAT's Administration permission. So a
#     token with no Administration access at all will still bypass
#     `protect-main` as long as the authenticated user is a
#     Repository Admin.
#   - The work that is *in* this release is already merged to main.
#
# The convention for what counts as MAJOR / MINOR / PATCH is in
# README.md → "Versioning". Short version:
#   MAJOR — foundational reset of scope, identity, or platform.
#   MINOR — a big new project: new page, new pipeline, new locale, etc.
#   PATCH — bug fixes, copy edits, content refreshes.
#
# Exit codes:
#   0  success.
#   1  bad usage / preconditions not met.
#   2  changelog had no [Unreleased] entries (nothing to release).

set -euo pipefail

# ────────────────────────────────────────────────────────────────────
# Argument parsing
# ────────────────────────────────────────────────────────────────────

if [[ $# -lt 2 || $# -gt 3 ]]; then
  echo "usage: $0 <version> \"<title>\" [--dry-run]"
  echo "       <version>  X.Y.Z, e.g. 1.4.0"
  echo "       <title>    short phrase summarising the key contribution,"
  echo "                  e.g. \"Introducing FAQ and Glossary pages\""
  exit 1
fi

VERSION="$1"
TITLE="$2"
DRY_RUN="${3:-}"

if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "✗ Version must match X.Y.Z (got '$VERSION')."
  echo "  Don't prefix with 'v'; the script adds it for the tag."
  exit 1
fi

# A title is required by convention. Short phrase that reflects the
# key contribution of this release — appears in the CHANGELOG heading
# and the GitHub Release title. See the header docstring for examples.
if [[ -z "$TITLE" ]]; then
  echo "✗ Release title is required (got empty string)."
  echo "  Pick a short phrase that reflects the key contribution, e.g."
  echo "    \"Introducing FAQ and Glossary pages\""
  echo "  Convention: 3-8 words, sentence case, no trailing punctuation."
  exit 1
fi

# Guard against accidentally passing --dry-run as the title.
if [[ "$TITLE" == --* ]]; then
  echo "✗ Title looks like a flag ('$TITLE'). Did you forget to quote it,"
  echo "  or are you missing the title argument?"
  echo "  Correct: $0 $VERSION \"Introducing FAQ and Glossary pages\""
  exit 1
fi

if [[ -n "$DRY_RUN" && "$DRY_RUN" != "--dry-run" ]]; then
  echo "✗ Third argument, if given, must be --dry-run (got '$DRY_RUN')."
  exit 1
fi

# Helpers --------------------------------------------------------------

run() {
  # Echo the command; only execute if not in dry-run mode.
  echo "  \$ $*"
  if [[ "$DRY_RUN" != "--dry-run" ]]; then
    eval "$@"
  fi
}

step() {
  echo
  echo "── $1"
}

# ────────────────────────────────────────────────────────────────────
# Pre-flight checks
# ────────────────────────────────────────────────────────────────────

step "Pre-flight"

# Run from repo root regardless of cwd.
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# 1. gh authenticated?
if ! gh auth status >/dev/null 2>&1; then
  echo "✗ gh CLI is not authenticated. Run 'gh auth login' first."
  exit 1
fi

# 2. Are we on main?
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$BRANCH" != "main" ]]; then
  echo "✗ You must be on branch 'main' to cut a release (currently on '$BRANCH')."
  echo "  Tip: merge your release-prep PR first, then run this from main."
  exit 1
fi

# 3. Working tree clean? (Untracked files are fine.)
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "✗ Working tree has uncommitted changes. Commit or stash first."
  exit 1
fi

# 4. Local main matches origin/main exactly?
git fetch origin main --quiet
LOCAL_SHA="$(git rev-parse main)"
REMOTE_SHA="$(git rev-parse origin/main)"
if [[ "$LOCAL_SHA" != "$REMOTE_SHA" ]]; then
  echo "✗ Local main ($LOCAL_SHA) does not match origin/main ($REMOTE_SHA)."
  echo "  Run: git pull --ff-only origin main"
  exit 1
fi

# 5. Tag must not already exist locally or remotely.
if git rev-parse "v$VERSION" >/dev/null 2>&1; then
  echo "✗ Tag v$VERSION already exists locally."
  exit 1
fi
if git ls-remote --tags origin "refs/tags/v$VERSION" | grep -q .; then
  echo "✗ Tag v$VERSION already exists on origin."
  exit 1
fi

echo "✓ On main, clean, in sync with origin, v$VERSION is fresh."

# ────────────────────────────────────────────────────────────────────
# Promote [Unreleased] → [<version>] in CHANGELOG.md
# ────────────────────────────────────────────────────────────────────

step "Promote CHANGELOG.md [Unreleased] → [$VERSION]"

CHANGELOG="$REPO_ROOT/CHANGELOG.md"
if [[ ! -f "$CHANGELOG" ]]; then
  echo "✗ CHANGELOG.md not found at $CHANGELOG"
  exit 1
fi

TODAY="$(date -u +%Y-%m-%d)"

# Pull out the [Unreleased] section body to make sure it is non-empty
# (excluding the "Nothing yet." placeholder).
UNRELEASED_BODY="$(awk '
  /^## \[Unreleased\]/ { inblock = 1; next }
  /^## \[/            { inblock = 0 }
  inblock             { print }
' "$CHANGELOG")"

# Trim whitespace + ignore the literal "Nothing yet." placeholder.
TRIMMED="$(printf '%s\n' "$UNRELEASED_BODY" | sed -e 's/^[[:space:]]*//;s/[[:space:]]*$//' | grep -v '^$' || true)"

if [[ -z "$TRIMMED" ]] || [[ "$TRIMMED" == "_Nothing yet._" ]]; then
  echo "✗ [Unreleased] is empty (or just '_Nothing yet._')."
  echo "  Add release notes there first, then re-run."
  exit 2
fi

echo "  [Unreleased] body found, $(printf '%s' "$UNRELEASED_BODY" | wc -l) lines."
echo "  Promoting to [$VERSION] · $TODAY and resetting [Unreleased]."

# ────────────────────────────────────────────────────────────────────
# Final-review confirmation. With "Enforce release immutability"
# turned on at the repo level, the GitHub Release page is write-once
# after publication. This prompt is the last moment to abort if a
# typo or omission is spotted in the notes that will be published.
# Skipped during --dry-run (the dry-run is itself the preview).
#
# Aborting here leaves the working tree, commits, tag, and remote
# all in their pre-release state — nothing has been mutated yet.
# ────────────────────────────────────────────────────────────────────
if [[ "$DRY_RUN" != "--dry-run" ]]; then
  step "Preview & confirm — the release notes that will be published"
  printf '\n'
  printf '  Title:   v%s — %s\n' "$VERSION" "$TITLE"
  printf '  ──────────────────────────────────────────────────────────────\n'
  printf '%s\n' "$UNRELEASED_BODY" | sed 's/^/  /'
  printf '  ──────────────────────────────────────────────────────────────\n\n'
  printf '  Publish v%s — %s with the title + notes above?\n' "$VERSION" "$TITLE"
  printf '  Type "y" to publish, anything else to abort: '
  read -r CONFIRM
  case "$CONFIRM" in
    [yY]|[yY][eE][sS]) ;;
    *)
      printf '\n  Aborted. No commits, tags, or release were made.\n'
      printf '  CHANGELOG.md is unchanged. Edit [Unreleased] and re-run when ready.\n'
      exit 0
      ;;
  esac
fi

# Rewrite the file via Python for safety (BSD sed makes in-place edits
# of multi-line patterns painful).
if [[ "$DRY_RUN" != "--dry-run" ]]; then
  python3 - "$CHANGELOG" "$VERSION" "$TODAY" "$TITLE" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
version = sys.argv[2]
today   = sys.argv[3]
title   = sys.argv[4]
src     = path.read_text(encoding="utf-8")

# 1. Replace the [Unreleased] heading with two headings: a fresh
#    [Unreleased] (with placeholder body) and the promoted [version].
new_block = (
    f"## [Unreleased]\n\n"
    f"_Nothing yet._\n\n"
    f"## [{version}] · {today} — {title}"
)
src, n = re.subn(r"^## \[Unreleased\]", new_block, src, count=1, flags=re.M)
if n != 1:
    raise SystemExit("Could not find a unique [Unreleased] heading.")

# 2. Update the compare-link block at the bottom.
#    Replace:
#      [Unreleased]: …/compare/vPREVIOUS...HEAD
#    With:
#      [Unreleased]: …/compare/vNEW...HEAD
#      [vNEW]:        …/compare/vPREVIOUS...vNEW
#    Keep older link lines untouched.
m = re.search(
    r"^\[Unreleased\]:\s*(https://github\.com/[^/]+/[^/]+)/compare/v([0-9.]+)\.\.\.HEAD\s*$",
    src,
    flags=re.M,
)
if m:
    repo_url = m.group(1)
    previous = m.group(2)
    new_link_block = (
        f"[Unreleased]: {repo_url}/compare/v{version}...HEAD\n"
        f"[{version}]: {repo_url}/compare/v{previous}...v{version}"
    )
    src = re.sub(
        r"^\[Unreleased\]:.*$",
        new_link_block,
        src,
        count=1,
        flags=re.M,
    )
else:
    # No [Unreleased] compare link (first release after adopting this).
    # Try to retro-fit by linking to the tag.
    m = re.search(
        r"^\[([0-9.]+)\]:\s*(https://github\.com/[^/]+/[^/]+)/releases/tag/v[0-9.]+\s*$",
        src,
        flags=re.M,
    )
    if m:
        prev_version = m.group(1)
        repo_url     = m.group(2)
        new_link_block = (
            f"[Unreleased]: {repo_url}/compare/v{version}...HEAD\n"
            f"[{version}]: {repo_url}/compare/v{prev_version}...v{version}"
        )
        # Inject right before the first existing link line.
        src = re.sub(
            r"^(\[[0-9.]+\]:.*)$",
            new_link_block + "\n\\1",
            src,
            count=1,
            flags=re.M,
        )

path.write_text(src, encoding="utf-8")
PY
fi

# ────────────────────────────────────────────────────────────────────
# Commit + tag + push
# ────────────────────────────────────────────────────────────────────

step "Commit, tag, push"

run git add CHANGELOG.md
run git commit -m \"Release v$VERSION — $TITLE\" \
       -m \"Promotes the CHANGELOG.md [Unreleased] section to [$VERSION] · $TODAY — $TITLE and resets [Unreleased].\"
run git tag -a \"v$VERSION\" \
       -m \"v$VERSION — $TITLE\" \
       -m \"See CHANGELOG.md and https://github.com/EISSeuropa/netsec.github.io/releases/tag/v$VERSION\"

run git push origin main
run git push origin \"v$VERSION\"

# ────────────────────────────────────────────────────────────────────
# Slice the changelog entry for this version and publish the Release
# ────────────────────────────────────────────────────────────────────

step "Publish GitHub Release v$VERSION"

NOTES_FILE="$(mktemp -t "release-v$VERSION-XXXXXX.md")"

if [[ "$DRY_RUN" != "--dry-run" ]]; then
  python3 - "$CHANGELOG" "$VERSION" >"$NOTES_FILE" <<'PY'
import re
import sys

src = open(sys.argv[1], encoding="utf-8").read()
version = sys.argv[2]

# Capture the body of `## [<version>] · ...` up to the next `## [` heading.
pat = re.compile(
    rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)",
    re.M | re.S,
)
m = pat.search(src)
if not m:
    raise SystemExit(f"Could not find [{version}] section in changelog.")
print(m.group(1).strip())
PY
else
  echo "  [dry-run] would extract [$VERSION] body to $NOTES_FILE"
fi

run gh release create \"v$VERSION\" \
       --title \"v$VERSION — $TITLE\" \
       --notes-file \"$NOTES_FILE\" \
       --latest

if [[ "$DRY_RUN" != "--dry-run" ]]; then
  rm -f "$NOTES_FILE"
fi

step "Done"
echo "  ✓ Released v$VERSION."
echo "  https://github.com/EISSeuropa/netsec.github.io/releases/tag/v$VERSION"
