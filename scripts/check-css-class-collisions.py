#!/usr/bin/env python3
"""Lint assets/css/site.css for class-name collisions across feature areas.

Trigger
-------

In May 2026 we accidentally re-used `.member-card` — the directory's
main card class on /people.html since launch — as the container class
for a new popover feature on the ESSC programme page (PRs #137 /
#138 / #139). Two unrelated rule blocks ~1500 lines apart, both
styling `.member-card`. The second silently overwrote parts of the
first (position:fixed, width:360px, overflow:hidden). The directory
broke — every card stacked at the viewport top-left — and the
regression slipped through code review.

This lint catches two patterns:

1. Same class name as the keyed selector in two or more rule
   *clusters* separated by more than 200 source lines. The threshold
   is a heuristic for "different feature area"; related rules cluster
   in real codebases.

2. BEM-style child `.foo-bar` declared more than 200 lines from the
   nearest `.foo` declaration. Catches the variant where a feature
   adds `.foo-bar` thinking it's a private child of a `.foo` it just
   introduced — but `.foo` already lived elsewhere, with different
   intent.

Suppression
-----------

Inline comment, on the line immediately before the offending rule:

    /* css-collision-allow: .my-class */
    .my-class { ... }

Useful for legit cross-cutting patterns (theme switchers, utility
classes used in multiple feature areas).

Exit code
---------

0  no collisions found
1  one or more collisions found
2  setup error (file missing, parse error)
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS_DIR = ROOT / "assets" / "css"
GAP_THRESHOLD_LINES = 200

# Matches `.identifier`. The negative lookbehind keeps "0.5em" from
# being picked up as a `.5em` class — not strictly necessary since the
# capture also requires a letter at the start, but harmless and clearer.
CLASS_RE = re.compile(r"(?<!\d)\.([A-Za-z][\w-]*)")

# Splits a selector on its top-level combinators (whitespace, >, +, ~)
# to isolate the rightmost compound selector. We treat combinators
# generously — square-bracketed attributes can contain spaces but we
# don't try to handle that edge case; it'd cost more in complexity
# than it saves.
COMBINATOR_RE = re.compile(r"\s*[>+~]\s*|\s+")


def styled_class(selector):
    """Return the class that `selector` actually styles, or None.

    The "styled" class is the last class token inside the rightmost
    compound selector. Compounds are the subjects of a selector joined
    without whitespace; combinators (`>`, `+`, `~`, descendant
    whitespace) separate them.

    Examples
    --------
        `.foo`                     → "foo"
        `.foo:hover`               → "foo"
        `.foo .bar`                → "bar"
        `.foo > .bar:hover`        → "bar"
        `.foo .bar::after`         → "bar"
        `.foo a::after`            → None  (last compound has no class)
        `.foo[data-x]:not(.bar)`   → "foo" or "bar" depending on which
                                       comes last in the source order;
                                       :not() classes count as part of
                                       the compound by spec, so picking
                                       either is defensible. We pick
                                       the last in source order, which
                                       matches our `CLASS_RE.finditer`
                                       behaviour.
    """
    sel = selector.strip()
    if not sel:
        return None
    parts = COMBINATOR_RE.split(sel)
    last = parts[-1].strip()
    last_class = None
    for m in CLASS_RE.finditer(last):
        last_class = m.group(1)
    return last_class

# Inline suppression marker:
#   /* css-collision-allow: .my-class */
#   .my-class { ... }
SUPPRESS_RE = re.compile(r"/\*\s*css-collision-allow:\s*\.([A-Za-z][\w-]*)\s*\*/")


def iter_selectors(css_text):
    """Yield (line_no, selector_text, media_depth) for every rule block
    in `css_text`, in source order.

    Tracks brace depth and at-rule context. `media_depth` is the depth
    of the enclosing @media / @supports / @container blocks; rules at
    media_depth > 0 are inside a media query rather than top-level.

    Block / inline comments and string literals are skipped atomically
    so a `{` inside a comment or a `content: "{"` doesn't confuse the
    state machine.
    """
    i = 0
    n = len(css_text)
    line_no = 1
    brace_depth = 0
    media_depth = 0
    buf = []
    buf_start_line = None

    while i < n:
        ch = css_text[i]

        # Block comment
        if ch == "/" and i + 1 < n and css_text[i + 1] == "*":
            end = css_text.find("*/", i + 2)
            if end == -1:
                break
            line_no += css_text.count("\n", i, end + 2)
            i = end + 2
            continue

        # String literal — skip atomically so `content: "{}"` doesn't break us.
        if ch in ('"', "'"):
            quote = ch
            j = i + 1
            while j < n and css_text[j] != quote:
                if css_text[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if css_text[j] == "\n":
                    line_no += 1
                j += 1
            # j is at the closing quote (or end of input)
            i = j + 1
            continue

        if ch == "\n":
            line_no += 1
            i += 1
            continue

        if ch == "{":
            selector = "".join(buf).strip()
            buf = []
            start = buf_start_line if buf_start_line is not None else line_no
            buf_start_line = None
            if selector:
                stripped = selector.lstrip()
                # @media, @supports, @container open a new context that
                # contains real selectors as children.
                if (
                    stripped.startswith("@media")
                    or stripped.startswith("@supports")
                    or stripped.startswith("@container")
                ):
                    media_depth += 1
                elif stripped.startswith("@"):
                    # @keyframes, @font-face, @page, etc. The contents
                    # aren't class selectors we care about — skip the
                    # next balanced brace block.
                    depth = 1
                    j = i + 1
                    while j < n and depth > 0:
                        c2 = css_text[j]
                        if c2 == "/" and j + 1 < n and css_text[j + 1] == "*":
                            end = css_text.find("*/", j + 2)
                            if end == -1:
                                j = n
                                break
                            line_no += css_text.count("\n", j, end + 2)
                            j = end + 2
                            continue
                        if c2 in ('"', "'"):
                            quote = c2
                            k = j + 1
                            while k < n and css_text[k] != quote:
                                if css_text[k] == "\\" and k + 1 < n:
                                    k += 2
                                    continue
                                if css_text[k] == "\n":
                                    line_no += 1
                                k += 1
                            j = k + 1
                            continue
                        if c2 == "\n":
                            line_no += 1
                        elif c2 == "{":
                            depth += 1
                        elif c2 == "}":
                            depth -= 1
                        j += 1
                    i = j
                    continue
                else:
                    yield (start, selector, media_depth)
            brace_depth += 1
            i += 1
            continue

        if ch == "}":
            if brace_depth > 0:
                brace_depth -= 1
            if media_depth > 0 and brace_depth < media_depth:
                media_depth = brace_depth
            buf = []
            buf_start_line = None
            i += 1
            continue

        if ch == ";" and brace_depth > media_depth:
            # Declaration terminator inside a rule body — we're not
            # collecting selectors here anyway, but reset the buffer
            # just in case.
            buf = []
            buf_start_line = None
            i += 1
            continue

        # Outside any rule body (we're at brace_depth == media_depth):
        # accumulate selector characters.
        if brace_depth == media_depth:
            if not buf and ch.isspace():
                pass  # leading whitespace before a selector
            else:
                if buf_start_line is None:
                    buf_start_line = line_no
                buf.append(ch)
        i += 1


def collect_declarations(css_text):
    """Return a dict mapping class name -> sorted list of unique line
    numbers where that class is the keyed selector of a top-level rule
    (outside any @media / @supports / @container block).

    Suppressed classes (via `/* css-collision-allow: .name */` on the
    preceding line) are excluded from the output.
    """
    # Build a map: line -> set of classes suppressed on that line.
    # The marker on line N suppresses the rule starting on line N+1.
    suppress = defaultdict(set)
    for ln, line in enumerate(css_text.split("\n"), 1):
        m = SUPPRESS_RE.search(line)
        if m:
            suppress[ln + 1].add(m.group(1))

    decls = defaultdict(set)
    for start, selector, media in iter_selectors(css_text):
        if media > 0:
            continue
        # Selector lists with many subjects are usually cross-cutting
        # helpers (a single focus-visible style applied to ten button
        # classes, or an exclusion list for the external-link icon)
        # rather than feature-specific declarations. We don't want
        # these to pump up the cluster count for any of the listed
        # classes, so skip the whole rule above the threshold. Three
        # is generous enough to permit "primary + hover + focus"
        # groupings without triggering on big shared-helper rules.
        sels = [s.strip() for s in selector.split(",") if s.strip()]
        if len(sels) > 3:
            continue
        for sel in sels:
            # Skip selectors with descendant context — e.g. `.dark .foo`
            # is a theme variant of .foo, not a primary declaration.
            # Real collisions look like sole-compound selectors:
            # `.foo`, `.foo:hover`, `.foo.bar`.
            if COMBINATOR_RE.search(sel.strip()):
                continue
            target = styled_class(sel)
            if not target:
                continue
            if target in suppress.get(start, set()):
                continue
            decls[target].add(start)

    return {name: sorted(lines) for name, lines in decls.items()}


def cluster(lines, gap):
    """Group sorted line numbers into clusters; consecutive lines whose
    spacing is <= `gap` belong to the same cluster."""
    if not lines:
        return []
    out = [[lines[0]]]
    for ln in lines[1:]:
        if ln - out[-1][-1] <= gap:
            out[-1].append(ln)
        else:
            out.append([ln])
    return out


def find_collisions(decls):
    """Yield problem dicts for both rules.

    Problem dict shapes:
      {kind: 'collision', name, clusters}
      {kind: 'orphan_bem', name, child_lines, parent, parent_lines, distance}
    """
    # Rule 1: same class, multiple clusters far apart.
    collision_names = set()
    for name, lines in decls.items():
        clusters = cluster(lines, GAP_THRESHOLD_LINES)
        if len(clusters) >= 2:
            collision_names.add(name)
            yield {"kind": "collision", "name": name, "clusters": clusters}

    # Rule 2: orphan BEM child.
    for name, lines in decls.items():
        if name in collision_names:
            continue  # already flagged louder by rule 1
        if "-" not in name:
            continue
        parent = name.rsplit("-", 1)[0]
        if parent not in decls:
            continue
        nearest = min(abs(cl - pl) for cl in lines for pl in decls[parent])
        if nearest > GAP_THRESHOLD_LINES:
            yield {
                "kind": "orphan_bem",
                "name": name,
                "child_lines": lines,
                "parent": parent,
                "parent_lines": decls[parent],
                "distance": nearest,
            }


def format_problem(p):
    if p["kind"] == "collision":
        lines = [f"  COLLISION  .{p['name']}"]
        for c in p["clusters"]:
            span = f"L{c[0]}" if len(c) == 1 else f"L{c[0]}–L{c[-1]}"
            rules = f"{len(c)} rule{'s' if len(c) != 1 else ''}"
            lines.append(f"             · {span}  ({rules})")
        lines.append(
            f"             Two or more clusters >{GAP_THRESHOLD_LINES} lines apart."
        )
        lines.append(
            "             Rename one of them so the two features can't shadow each other."
        )
        return "\n".join(lines)
    if p["kind"] == "orphan_bem":
        child_loc = ", ".join(f"L{l}" for l in p["child_lines"])
        parent_loc = ", ".join(f"L{l}" for l in p["parent_lines"])
        return "\n".join([
            f"  ORPHAN BEM CHILD  .{p['name']}  ({child_loc})",
            f"                    Nearest `.{p['parent']}` declaration is "
            f"{p['distance']} lines away ({parent_loc}).",
            f"                    If you meant `.{p['name']}` as a private child of your own",
            f"                    `.{p['parent']}`, the existing `.{p['parent']}` is probably",
            "                    colliding with it. Rename or co-locate.",
        ])
    return f"  UNKNOWN  {p!r}"


def main():
    # Scan the git-tracked stylesheets, not the raw directory. A stray local
    # copy (macOS Finder "name 2.css" duplicates have tripped this before)
    # otherwise re-declares every class in the original and fails the
    # cross-file check with noise CI never sees. Falls back to the directory
    # glob outside a git checkout.
    try:
        tracked = subprocess.run(
            ["git", "ls-files", "assets/css/*.css"],
            capture_output=True, text=True, check=True, cwd=CSS_DIR.parent.parent,
        ).stdout.split()
        css_files = sorted(CSS_DIR.parent.parent / p for p in tracked)
    except (subprocess.CalledProcessError, FileNotFoundError):
        css_files = sorted(CSS_DIR.glob("*.css"))
    if not css_files:
        print(f"ERROR: no CSS files under {CSS_DIR}", file=sys.stderr)
        return 2

    exit_code = 0
    all_decls = {}  # rel path -> decls dict

    # Per-file pass: the original within-file cluster check.
    for css_file in css_files:
        css_text = css_file.read_text(encoding="utf-8")
        decls = collect_declarations(css_text)
        rel = css_file.relative_to(ROOT)
        all_decls[str(rel)] = decls

        problems = list(find_collisions(decls))
        if not problems:
            print(f"✓ {rel}: no class-name collisions detected "
                  f"({len(decls)} unique classes scanned).")
            continue

        exit_code = 1
        plural = "s" if len(problems) != 1 else ""
        print(f"✗ {rel}: {len(problems)} CSS class-name collision{plural} detected.")
        print()
        for p in problems:
            print(format_problem(p))
            print()

    # Cross-file pass: the same keyed class declared in two stylesheets
    # is the split-bundle variant of the original bug — the second file
    # silently overrides the first on any page loading both. Classes
    # suppressed with css-collision-allow are already excluded per file.
    owners = defaultdict(list)
    for rel, decls in all_decls.items():
        for cls in decls:
            owners[cls].append(rel)
    cross = {c: fs for c, fs in owners.items() if len(fs) > 1}
    if cross:
        exit_code = 1
        print(f"✗ cross-file: {len(cross)} class(es) keyed in more than one stylesheet.")
        for c, fs in sorted(cross.items()):
            print(f"    .{c}: {', '.join(fs)}")
        print()

    if exit_code:
        print("To suppress a known-safe false positive, add a comment on the")
        print("line immediately above the offending rule:")
        print("    /* css-collision-allow: .my-class */")
        print("    .my-class { ... }")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
