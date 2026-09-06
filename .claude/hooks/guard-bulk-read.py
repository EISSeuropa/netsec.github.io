#!/usr/bin/env python3
"""PreToolUse(Read|Bash) guard: refuse whole-file reads of very large files.

A full read of site.css or bios.json puts thousands of lines into the context
and every following turn resends them. Targeted reads pass through untouched,
so the escape hatch is one flag away: grep for the region, then Read with an
offset and a limit. Threshold via CLAUDE_READ_MAX_LINES, default 800, which
catches 29 of the 501 tracked text files here.

Fail OPEN on anything unexpected, matching guard-main-commit.sh. A guard that
wrongly blocks normal work is worse than the reads it prevents.
"""
import json
import os
import re
import sys

DEFAULT_MAX = 800

# A bare whole-file dump and nothing else: no pipe, no redirect, no second
# path. `cat x | head -50` is already a targeted read and is left alone.
DUMP = re.compile(r"^\s*(?:cat|less|more)\s+(?:-\S+\s+)*(\S+)\s*$")


def target(payload):
    """The file a call would read in full, or None if it would not."""
    tool = payload.get("tool_name")
    args = payload.get("tool_input") or {}
    if tool == "Read":
        # An offset or a limit means the wanted section is already known.
        if args.get("limit") or args.get("offset"):
            return None
        return args.get("file_path")
    if tool == "Bash":
        hit = DUMP.match(args.get("command") or "")
        return hit.group(1).strip("'\"") if hit else None
    return None


def line_count(path):
    try:
        with open(path, "rb") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return 0


def check(payload, limit):
    """Return a refusal message, or None to let the call through."""
    path = target(payload)
    if not path:
        return None
    path = os.path.expanduser(path)
    if not os.path.isabs(path):
        path = os.path.join(payload.get("cwd") or os.getcwd(), path)
    if not os.path.isfile(path):
        return None
    lines = line_count(path)
    if lines <= limit:
        return None
    return (
        f"{os.path.basename(path)} is {lines} lines, over the {limit}-line "
        "guard, and a whole-file read is resent on every following turn. "
        "Grep for the region and Read it with an offset and a limit, or hand "
        "the reading to an Explore subagent. Set CLAUDE_READ_MAX_LINES higher "
        "when the whole file is genuinely needed."
    )


def main():
    try:
        payload = json.load(sys.stdin)
        limit = int(os.environ.get("CLAUDE_READ_MAX_LINES", DEFAULT_MAX))
    except (ValueError, OSError):
        return 0
    message = check(payload, limit)
    if message is None:
        return 0
    print(message, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
