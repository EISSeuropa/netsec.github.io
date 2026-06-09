#!/usr/bin/env python3
"""Translator diff: show what changed in an English page since a
translation was last marked fresh.

The drift checker (check-i18n-drift.py) says *that* a FR or DE page is
stale; this tool says *what* changed, so a refresh becomes "translate
these blocks" instead of "re-read the whole page against the
translation". See issue #728.

How it works:
  1. data/i18n-state.json records the normalised SHA-1 of the English
     source at the moment each translation was last refreshed.
  2. The English page's git history is walked until a commit whose
     normalised content matches that SHA-1 (the same cache-bust
     normalisation the drift checker hashes with). If no commit
     matches (a fresh-mark against uncommitted content), the newest
     commit on or before the recorded translated_on date is used and
     a note says so.
  3. Visible prose blocks (headings, paragraphs, list items, table
     cells, figure captions) are extracted from both versions and
     diffed block-wise. Removed blocks print with "-", added blocks
     with "+"; attribute-only and script/style changes don't surface,
     which is the point: translators care about prose.

Usage:
  python3 scripts/i18n-diff.py <source.html> <lang>
  python3 scripts/i18n-diff.py faq.html fr

Dependency-free (stdlib only), like the other i18n tooling. Exit 0 on
a clean run (including "translation is current"), 2 on bad arguments
or missing state.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STATE = REPO / "data" / "i18n-state.json"

# Same normalisation as check-i18n-drift.py's sha1(): cache-bust
# queries are injected per-release and carry no translatable meaning.
_CACHE_BUST_RE = re.compile(
    r'(assets/(?:css|js)/[A-Za-z0-9._-]+\.(?:css|js))\?v=[0-9a-f]+'
)

BLOCK_TAGS = {
    "p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "td", "th",
    "figcaption", "summary", "blockquote", "dt", "dd", "caption",
}
SKIP_TAGS = {"script", "style", "head", "template"}


def normalise(text: str) -> str:
    return _CACHE_BUST_RE.sub(r"\1", text)


def norm_sha1(text: str) -> str:
    return hashlib.sha1(normalise(text).encode("utf-8")).hexdigest()


class _BlockExtractor(HTMLParser):
    """Collects the visible text of block-level prose elements.

    Nested block tags (an <li> containing a <p>) flush the outer
    block first, so each piece of prose appears once.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks: list = []
        self._buf: list = []
        self._depth = 0          # inside >=1 block tag
        self._skip = 0           # inside script/style/head/template

    def _flush(self):
        text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
        if text:
            self.blocks.append(text)
        self._buf = []

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self._skip += 1
        elif tag in BLOCK_TAGS and not self._skip:
            if self._depth:
                self._flush()
            self._depth += 1

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            self._skip = max(0, self._skip - 1)
        elif tag in BLOCK_TAGS and self._depth and not self._skip:
            self._depth -= 1
            if not self._depth:
                self._flush()

    def handle_data(self, data):
        if self._depth and not self._skip:
            self._buf.append(data)


def extract_blocks(html: str) -> list:
    p = _BlockExtractor()
    p.feed(html)
    p.close()
    return p.blocks


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, check=True,
        capture_output=True, text=True,
    ).stdout


def historical_content(source: str, want_sha1: str, fallback_date: str):
    """Return (content, note) for the English page at fresh-mark time.

    Walks the page's commit history for a normalised-content match on
    want_sha1; falls back to the newest commit on or before
    fallback_date when nothing matches.
    """
    commits = git("log", "--format=%H %cs", "--", source).splitlines()
    dated = []
    for line in commits:
        sha, date = line.split()
        try:
            content = git("show", f"{sha}:{source}")
        except subprocess.CalledProcessError:
            continue
        if norm_sha1(content) == want_sha1:
            return content, None
        dated.append((date, content))
    for date, content in dated:   # newest-first already
        if date <= fallback_date:
            return content, (
                f"note: no commit matches the recorded fresh-mark hash; "
                f"using the newest commit on or before {fallback_date}."
            )
    return None, None


def diff_blocks(old: list, new: list) -> list:
    """Block-wise diff as a list of ('-'|'+', text) tuples."""
    out = []
    sm = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    for op, a0, a1, b0, b1 in sm.get_opcodes():
        if op in ("delete", "replace"):
            out.extend(("-", b) for b in old[a0:a1])
        if op in ("insert", "replace"):
            out.extend(("+", b) for b in new[b0:b1])
    return out


def main(argv: list) -> int:
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[0])
        print("usage: python3 scripts/i18n-diff.py <source.html> <lang>")
        return 2
    source, lang = argv
    state = json.loads(STATE.read_text(encoding="utf-8"))
    entry = (state.get("translations", {}).get(source) or {}).get(lang)
    if not entry:
        print(f"✗ no {lang} entry for {source} in data/i18n-state.json")
        return 2

    current_path = REPO / source
    if not current_path.exists():
        print(f"✗ {source} not found")
        return 2
    current = current_path.read_text(encoding="utf-8")

    if norm_sha1(current) == entry["source_sha1"]:
        print(f"✓ {source} [{lang}] is current (fresh-marked "
              f"{entry.get('translated_on', '?')}); nothing to diff.")
        return 0

    old, note = historical_content(
        source, entry["source_sha1"], entry.get("translated_on", "")
    )
    if old is None:
        print(f"✗ could not locate the English source at fresh-mark time "
              f"for {source} [{lang}]; diff the git history by hand.")
        return 2
    if note:
        print(note)

    changes = diff_blocks(extract_blocks(old), extract_blocks(current))
    if not changes:
        print(f"△ {source} [{lang}]: the markup changed since the "
              f"fresh-mark, but no visible prose block did. A "
              f"--mark-fresh without re-translation is likely fine "
              f"(confirm attribute strings like alt/aria-label by eye).")
        return 0

    removed = sum(1 for s, _ in changes if s == "-")
    added = sum(1 for s, _ in changes if s == "+")
    print(f"{source} [{lang}] — {removed} block(s) removed/changed, "
          f"{added} block(s) added/changed since "
          f"{entry.get('translated_on', '?')}:\n")
    for sign, text in changes:
        print(f"  {sign} {text}")
    print(f"\nTranslate the '+' blocks into {lang}, update "
          f"{entry.get('file', source)}, then run:\n"
          f"  python3 scripts/check-i18n-drift.py --mark-fresh {source} {lang}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
