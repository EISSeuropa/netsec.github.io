#!/usr/bin/env bash
# PreToolUse(Bash) guard: refuse `git commit` on the default branch
# (main / master). The branch-first workflow means commits always land
# on a feature branch; release.sh is invoked as a script, so its internal
# commit is not in the command string and is never seen here.
#
# Fail OPEN on anything unexpected — a guard that wrongly blocks normal
# work is worse than the mistake it prevents. Every error path exits 0.

input="$(cat 2>/dev/null)" || exit 0

# Pull the Bash command out of the hook's stdin JSON. On any parse error
# the command is empty, so the commit check below simply doesn't fire.
cmd="$(printf '%s' "$input" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' \
  2>/dev/null)"

# Only care about commands that actually commit.
case "$cmd" in
  *"git commit"*) ;;
  *) exit 0 ;;
esac

# Commits are typically run as `cd <repo> && git commit ...`. Check the
# branch in that directory so the guard sees the repo the commit lands
# in, not the session's current directory (which may be a worktree).
dir="$(printf '%s\n' "$cmd" \
  | sed -n 's/^[[:space:]]*cd[[:space:]]\{1,\}\([^&;|]*\).*/\1/p' | head -1)"
dir="$(printf '%s' "$dir" | sed 's/[[:space:]]*$//')"
if [ -n "$dir" ] && [ -d "$dir" ]; then
  cd "$dir" 2>/dev/null || exit 0
fi

branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)" || exit 0

case "$branch" in
  main|master)
    printf '%s\n' "{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"deny\",\"permissionDecisionReason\":\"On ${branch} — branch first (git checkout -b <feature>) before committing. See the CLAUDE.md branch-first rule.\"}}"
    exit 0
    ;;
  *)
    exit 0
    ;;
esac
