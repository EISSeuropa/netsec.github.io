#!/usr/bin/env python3
"""Write the body of the monthly keyword-themes issue.

A canonical keyword with no research theme leaves its member out of that
theme's filter in the Directory. sync-bios.py places a new keyword itself
only when suggest_theme() finds strong evidence (#2090), and the data-shape
check warns about the rest without failing the bios sync PR. This script
lists every keyword still unplaced, the members who use it, and up to two
themes whose keywords share a word with it, so a volunteer can place them
in one pass. .github/workflows/keyword-themes-issue.yml runs it on the
first of each month and opens or refreshes one issue from the output.

Usage:
  python3 scripts/report-unthemed-keywords.py BODY.md   # writes the body
Prints the number of unplaced keywords on stdout, and writes nothing to
BODY.md when it is 0. Stdlib only.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


shape = _load("check_data_shape", "check-data-shape.py")

WORD = re.compile(r"[a-z]{4,}")


def load_keyword_themes() -> dict[str, str]:
    """Lower-cased keyword -> theme from the `themes` section of
    data/keyword-aliases.json, keyed the way sync-bios.py's
    load_keyword_themes() keys it. Read here rather than imported, since
    sync-bios.py needs `requests` and this job installs nothing."""
    doc = json.loads(shape.ALIASES.read_text(encoding="utf-8"))
    return {
        kw.strip().lower(): theme
        for theme, kws in (doc.get("themes") or {}).items()
        for kw in kws or []
        if isinstance(kw, str) and kw.strip()
    }


def candidate_themes(keyword: str, theme_of: dict[str, str], limit: int = 2) -> list[tuple[str, str]]:
    """Up to ``limit`` ``(theme, example keyword)`` pairs, ranked by how many
    of the theme's keywords share a word of four letters or more with
    ``keyword``. Looser than suggest_theme() on purpose: a person decides."""
    words = set(WORD.findall(keyword.lower()))
    counts: dict[str, int] = {}
    example: dict[str, str] = {}
    for themed, theme in theme_of.items():
        if words & set(WORD.findall(themed)):
            counts[theme] = counts.get(theme, 0) + 1
            example.setdefault(theme, themed)
    ranked = sorted(counts, key=lambda t: (-counts[t], t))[:limit]
    return [(t, example[t]) for t in ranked]


def render_body(unthemed: dict[str, list[str]], theme_of: dict[str, str], today: date) -> str:
    themes = sorted(set(theme_of.values()))
    lines = [
        f"{len(unthemed)} keyword(s) on member profiles have no research theme, "
        f"as of {today.isoformat()}. Each member below is missing from that "
        "theme's filter in the Directory until the keyword is placed.",
        "",
        "## How to place them",
        "",
        "1. Open `data/keyword-aliases.json` and find the `themes` section.",
        "2. Add each keyword, spelt exactly as in the table, to the array of the "
        "theme it belongs to. One keyword goes in one theme only.",
        "3. Open one pull request with all of them and link this issue. The "
        "next nightly bios sync updates the Directory.",
        "",
        "The suggested themes share a word with the keyword and are only a "
        "starting point. A keyword that is a spelling variant of an existing "
        "one belongs under `aliases` instead, and one that is not a research "
        "topic (a country, a sentence) belongs under `drop_keywords` or "
        "`splits`. Ask on this issue when unsure.",
        "",
        "## Keywords",
        "",
        "| Keyword | Members | Suggested themes |",
        "|---|---|---|",
    ]
    for kw, names in unthemed.items():
        cands = candidate_themes(kw, theme_of)
        hint = "<br>".join(f"{t} (like _{ex}_)" for t, ex in cands) or "none found"
        cell = kw.replace("|", "\\|")
        lines.append(f"| {cell} | {', '.join(sorted(set(names)))} | {hint} |")
    lines += [
        "",
        "<details><summary>The research themes</summary>",
        "",
        *[f"- {t}" for t in themes],
        "",
        "</details>",
        "",
        "This issue is opened and refreshed on the first of each month by "
        "`.github/workflows/keyword-themes-issue.yml`, and closed when no "
        "keyword is left.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    data = json.loads((REPO / "data" / "bios.json").read_text(encoding="utf-8"))
    unthemed = shape.unthemed_keywords(data)
    print(len(unthemed))
    if unthemed:
        body = render_body(unthemed, load_keyword_themes(), date.today())
        Path(argv[0]).write_text(body, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
