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
#       point at which an abort leaves everything untouched. For
#       minor / major releases (X.Y.0 / X.0.0), an additional
#       six-point cross-check reminder prints before the prompt
#       (roadmap / sitemap / translations / repo docs + PDF / Wiki)
#       — see the release-cross-check skill for the full checklist.
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

# Resolve a python3 that actually runs. On some macOS setups the first
# python3 on PATH is an x86 framework build that aborts with "Bad CPU
# type in executable" on Apple silicon, so test each candidate before
# committing to it rather than trusting `command -v`. build.sh follows
# the same idea.
PY3=""
for _cand in python3 /usr/bin/python3 /opt/homebrew/bin/python3 python; do
  if command -v "$_cand" >/dev/null 2>&1 && "$_cand" -c '' >/dev/null 2>&1; then
    PY3="$_cand"; break
  fi
done
if [[ -z "$PY3" ]]; then
  echo "✗ No working python3 found (tried python3, /usr/bin/python3, /opt/homebrew/bin/python3, python)."
  echo "  Install python3 or fix the broken interpreter on PATH, then re-run."
  exit 1
fi

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

  # For minor / major releases (X.Y.Z where Z == 0), print the
  # six-point cross-check reminder before the prompt. Skipped for
  # patch releases — they're scoped to small fixes and the overhead
  # isn't justified. The full version of the checklist lives in
  # the release-cross-check skill and is mirrored in docs/admin-guide.md →
  # Cutting a
  # release.
  PATCH_PART="${VERSION##*.}"
  if [[ "$PATCH_PART" == "0" ]]; then
    printf '  Minor / major release — six-point cross-check (release-cross-check skill):\n'
    printf '    1. Roadmap       — /roadmap.html (+ FR + DE) and docs/roadmap-2026.md.\n'
    printf '    2. Sitemap       — sitemap.xml and /sitemap.html (+ FR + DE).\n'
    printf '    3. Translations  — `python3 scripts/check-i18n-drift.py` reports zero drift?\n'
    printf '    4. Repo docs+PDF — docs/ markdown + docs/pdf/documentation.html cover stamp.\n'
    printf "    5. Members' Wiki — decisions log, templates, stubs match public pages.\n"
    printf "    6. Banner        — data/whats-new.json \`active\` state still appropriate?\n"
    printf '\n'
    printf '  Land any edits in the same release, or open tracking issues (rule §3)\n'
    printf '  and reference them from the surface. Abort here if anything is missing —\n'
    printf '  the tag + GH Release are write-once after publication.\n'
    printf '  ──────────────────────────────────────────────────────────────\n\n'
  fi

  # Pre-release milestone audit (CLAUDE.md §10). List the issues
  # currently open under the v$VERSION milestone so the maintainer
  # can spot any work that shipped without explicit `gh issue close`.
  # gh may not have the milestone defined yet (first time a version
  # is cut from a milestone-less repo), so failures are non-fatal.
  open_count=$(gh issue list \
    --milestone "v$VERSION" --state open \
    --json number --jq 'length' 2>/dev/null || true)
  if [[ -n "$open_count" && "$open_count" != "0" ]]; then
    printf '  Open issues tagged with milestone v%s (CLAUDE.md §10):\n' "$VERSION"
    gh issue list \
      --milestone "v$VERSION" --state open \
      --json number,title \
      --jq '.[] | "    #\(.number)  \(.title)"' 2>/dev/null || true
    printf '\n'
    printf '  For each: did the work ACTUALLY ship in this release? If yes, close it now:\n'
    printf '      gh issue close <N> --comment "Shipped in v%s"\n' "$VERSION"
    printf '  If no, re-milestone before cutting (e.g. defer to v1.X+1.0 or Backlog).\n'
    printf '  ──────────────────────────────────────────────────────────────\n\n'
  fi

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
  "$PY3" - "$CHANGELOG" "$VERSION" "$TODAY" "$TITLE" <<'PY'
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
# Promote the public roadmap card (EN / FR / DE).
#
# scripts/promote-roadmap.py flips a matching <li class="rm-entry planned">
# card to shipped, formats the date per locale, adds the Release-notes
# link, and bumps the "Last updated" stamp paragraph. Idempotent: safe
# to re-run if the maintainer aborts and retries.
#
# Exit codes from the script:
#   0  one or more locales updated, or all already up-to-date.
#   2  no planned card AND no shipped card AND no stamp moved (the
#      maintainer probably forgot to write the v$VERSION card). We
#      print the warning, continue, and let the maintainer abort at
#      the confirmation prompt above (which already happened) OR
#      decide whether to commit anyway.
#
# Done BEFORE the commit so the roadmap edits land in the release
# commit, then ship with the tag.
# ────────────────────────────────────────────────────────────────────

step "Promote public roadmap card (EN / FR / DE)"

if [[ "$DRY_RUN" != "--dry-run" ]]; then
  if "$PY3" "$REPO_ROOT/scripts/promote-roadmap.py" "$VERSION" "$TODAY"; then
    echo "  ✓ roadmap promotion succeeded."
    # Re-mark the FR and DE roadmap entries fresh in i18n-state.json.
    # promote-roadmap.py edits all three locales together (a mechanical
    # card flip, not a translation change), so the FR/DE versions stay in
    # sync with EN. Without this the next PR sees a false-positive drift on
    # roadmap.fr/de (issue #412).
    "$PY3" "$REPO_ROOT/scripts/check-i18n-drift.py" --mark-fresh roadmap.html fr
    "$PY3" "$REPO_ROOT/scripts/check-i18n-drift.py" --mark-fresh roadmap.html de
  else
    rc=$?
    if [[ $rc -eq 2 ]]; then
      echo "  ! roadmap promotion ran but found nothing to do."
      echo "    See warnings above. release.sh will continue; abort with Ctrl-C if"
      echo "    you want to fix the roadmap before committing."
    else
      echo "✗ roadmap promotion failed (exit $rc). Aborting before commit."
      exit "$rc"
    fi
  fi
  echo
  echo "  ⚠ Card BODY check (release-cross-check skill, step 1). The script flipped the"
  echo "    status pill and bumped the date, but the card description"
  echo "    on roadmap.html (+ FR + DE) still shows whatever was planned"
  echo "    at the time the v$VERSION card was authored. If the actual"
  echo "    release scope differs from what was planned, edit the card"
  echo "    body now in a follow-up commit on this branch BEFORE the"
  echo "    tag + GH Release land. (The tag + Release are write-once;"
  echo "    public-roadmap edits afterwards still work but the GH Release"
  echo "    body is frozen to the CHANGELOG snapshot.)"
else
  echo "  \$ python3 scripts/promote-roadmap.py $VERSION $TODAY"
  echo "  [dry-run] roadmap.html (+ FR + DE) would be edited in-place."
fi

# ────────────────────────────────────────────────────────────────────
# Commit + tag + push
# ────────────────────────────────────────────────────────────────────

step "Commit, tag, push"

run git add CHANGELOG.md roadmap.html roadmap.fr.html roadmap.de.html data/i18n-state.json
run git commit -m \"Release v$VERSION — $TITLE\" \
       -m \"Promotes the CHANGELOG.md [Unreleased] section to [$VERSION] · $TODAY — $TITLE, resets [Unreleased], promotes the matching public-roadmap card on EN + FR + DE from planned to shipped, and bumps the roadmap last-updated stamp.\"
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
  "$PY3" - "$CHANGELOG" "$VERSION" >"$NOTES_FILE" <<'PY'
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

# ────────────────────────────────────────────────────────────────────
# Post-release maintainer reminder: PDF documentation pack.
#
# Per the release-cross-check skill (step 4) + CLAUDE.md §11, the PDF cover
# bumps on every minor / major
# release; patches skip it. The PDF version axis is independent from
# the website version (they don't track 1-to-1; see CHANGELOG appendix
# inside docs/pdf/documentation.html). The script doesn't auto-bump
# the cover stamp; too much heuristic about which version to pick.
# What it CAN do is surface the reminder + the four stamps to update
# + the build command, so the maintainer doesn't have to remember.
# ────────────────────────────────────────────────────────────────────

PATCH_PART="${VERSION##*.}"
if [[ "$PATCH_PART" == "0" ]]; then
  PDF_HTML="$REPO_ROOT/docs/pdf/documentation.html"
  CURRENT_PDF_VERSION=""
  if [[ -f "$PDF_HTML" ]]; then
    # Scrape the current PDF version from the cover. Match the first
    # occurrence of `vX.Y.Z` after "Documentation Pack". The grep falls
    # back to a sentinel if the pattern moves so the reminder still fires.
    CURRENT_PDF_VERSION="$(grep -oE 'Documentation Pack v[0-9]+\.[0-9]+\.[0-9]+' "$PDF_HTML" | head -n 1 | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' || true)"
  fi
  echo
  echo "── Reminder: PDF documentation pack (minor / major release)"
  echo "  v$VERSION is a minor / major release, so the PDF cover bumps."
  if [[ -n "$CURRENT_PDF_VERSION" ]]; then
    echo "  Current PDF version stamp: $CURRENT_PDF_VERSION."
  else
    echo "  Could not auto-detect current PDF version; check the cover yourself."
  fi
  echo
  echo "  Stamps to update in docs/pdf/documentation.html:"
  echo "    1. <title>NetSec — Website & Directory · Documentation Pack vX.Y.Z</title>"
  echo "    2. <div class=\"value\">vX.Y.Z · <Month> <Year></div>          (cover)"
  echo "    3. <span class=\"url\">vX.Y.Z · <Month> <Year></span>          (poster + last-page footer)"
  echo "    4. <h2>vX.Y.Z · <Month> <Year></h2>                         (appendix changelog)"
  echo
  echo "  Then rebuild the PDF:"
  echo "    ./docs/pdf/build.sh"
  echo
  echo "  Bump policy (CLAUDE.md §11):"
  echo "    cover-only bump (no section content refresh) → PDF patch (vX.Y.Z → vX.Y.(Z+1))"
  echo "    section-level catch-up                       → PDF minor (vX.Y.Z → vX.(Y+1).0)"
  echo "  Catch-ups are batched every 2-3 website minor releases."
fi
