#!/usr/bin/env python3
"""
check-external-link-arrows.py — lint for arrow-glyph + auto-icon
collisions on external links.

The site's CSS (`assets/css/site.css`) automatically appends a small
"external link" icon after every `<a target="_blank">` to an absolute
URL. If the link text *also* ends with a manual arrow glyph
(→ / ↗ / » / >>), the rendered link shows BOTH and looks scruffy.

This script scans every tracked HTML file for that anti-pattern and
exits non-zero if any are found. Run locally before opening a PR; CI
runs it on every push as `external-link-arrows.yml`.

Usage:
  python3 scripts/check-external-link-arrows.py            # check repo
  python3 scripts/check-external-link-arrows.py FILE [...] # check specific files

The fix when a hit lands: delete the arrow glyph from the link text.
The auto-injected icon already signals "this opens externally".

This lint covers content authoring; the CSS exclusions in site.css
(.cost-mark::after, .socials a::after, etc.) handle structural
exceptions where the icon shouldn't render at all.
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Arrow glyphs that have been used (or might be used by mistake) at the
# tail of an external link's text. Keep this list narrow — we only want
# the trailing-arrow anti-pattern, not legitimate prose containing →.
TRAILING_ARROWS = ("→", "↗", "»", ">>", "➔", "➜", "▶")

# Match the *opening* tag of an external link, then capture the text
# up to the closing </a>. We accept any attribute order and only
# require target="_blank" + http(s)/// href to mirror the CSS rule.
LINK_RE = re.compile(
    r'<a\s+(?=[^>]*\btarget\s*=\s*"_blank")(?=[^>]*\bhref\s*=\s*"(?:https?:)?//)[^>]*>'
    r'(?P<inner>.*?)'
    r'</a>',
    re.DOTALL | re.IGNORECASE,
)


def find_hits(html: str) -> list[tuple[int, str]]:
    """Return (line_number, snippet) for every offending external link."""
    hits = []
    for m in LINK_RE.finditer(html):
        inner = m.group("inner")
        # Strip nested tags + trailing whitespace, then check the tail
        # against the arrow set. We strip *all* tags so a trailing
        # `<svg>…</svg>` placed by the author is allowed (the auto-icon
        # is a CSS pseudo-element, not real DOM — so it never matches).
        text = re.sub(r"<[^>]+>", "", inner).strip()
        if not text:
            continue
        if text.endswith(TRAILING_ARROWS):
            line_no = html.count("\n", 0, m.start()) + 1
            # Compact snippet for the error message.
            snippet = re.sub(r"\s+", " ", m.group(0))[:140]
            hits.append((line_no, snippet))
    return hits


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        paths = [Path(p) for p in argv[1:]]
    else:
        paths = sorted(REPO_ROOT.glob("*.html"))

    total = 0
    for path in paths:
        if not path.exists():
            print(f"WARN: {path} does not exist", file=sys.stderr)
            continue
        html = path.read_text(encoding="utf-8")
        for line_no, snippet in find_hits(html):
            print(f"{path.relative_to(REPO_ROOT)}:{line_no}: {snippet}")
            total += 1

    if total:
        print(
            f"\nFound {total} external link(s) ending with a manual arrow glyph.\n"
            f"The CSS auto-icon (see assets/css/site.css, search "
            f"'External-link indicator') already adds the visual cue, so the "
            f"trailing → / ↗ / » / >> is redundant and prints a double "
            f"affordance. Delete the arrow glyph from the link text.",
            file=sys.stderr,
        )
        return 1

    print(f"OK — {len(paths)} HTML file(s) scanned, no manual arrows on external links.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
