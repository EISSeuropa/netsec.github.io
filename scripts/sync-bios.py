#!/usr/bin/env python3
"""
Sync helper: refresh data/bios.json from a Google Sheet linked to the
NetSec member bios Google Form.

Usage:
    python3 scripts/sync-bios.py

What it does:
  1. Reads scripts/bios-source.json for the sheet's published CSV URL.
     If the URL is empty (initial state), the script exits cleanly
     without touching anything — so the workflow stays green while the
     Google Form is still being set up.
  2. Fetches the sheet as CSV.
  3. For each row:
       - Validates required fields (name, consent).
       - Maps columns to the bio JSON schema.
       - Generates a stable slug from the name.
       - If a photo URL is present (Google Drive or any HTTPS URL),
         downloads it, resizes to max 600 px, saves to
         assets/images/people/<slug>.<ext>.
  4. Merges with the existing data/bios.json:
       - The full prior state of the directory (seed + previously-synced
         form entries) is preserved unless overwritten by a fresh form
         submission whose normalised email or slug matches. This means
         a leadership role (e.g. "Science Communication Coordinator")
         survives the submitter's own form fill, and the entry's
         position in the leadership-first ordering is preserved.
       - Form entries are keyed by email when available, otherwise slug.
       - Duplicate form submissions: latest by timestamp wins.
  5. Writes data/bios.json with deterministic ordering — but only
     when the member data or the configured source URLs have actually
     changed. The `generated_at` and `source.last_synced` timestamps
     advance only on substantive writes, so the working tree stays
     clean across idempotent re-runs and the workflow's auto-PR step
     stays quiet.
  6. Prints a human-readable diff (added / updated / removed), or
     a "no substantive changes" note when the sync was a no-op.

Requires: requests. Pillow is optional — used to optimise photos if
available; if not, photos are saved as-is.
"""
from __future__ import annotations

import copy
import csv
import difflib
import hashlib
import io
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from _directory_common import name_key, slugify

try:
    import requests
except ImportError:
    sys.exit("Install deps: pip install -r scripts/requirements.txt")

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "scripts" / "bios-source.json"
BIOS = ROOT / "data" / "bios.json"
PHOTO_DIR = ROOT / "assets" / "images" / "people"
PHOTO_DIR.mkdir(parents=True, exist_ok=True)

MAX_PHOTO_WIDTH = 600

# Repo-relative paths of photo files whose bytes were rewritten during
# the current run. Populated by download_photo() each time a new image
# differs from what's already on disk. Used in main()'s substance check
# as a belt-and-braces signal alongside the data-level comparison.
#
# Lesson borrowed from sister-project EISSeuropa.github.io PRs #105+#106:
# the data file's `photo` field is a path string that does not change
# when only the underlying bytes change, so a byte-comparison of the
# data file alone can silently swallow a photo-only update. Our primary
# defence is `photo_source_sha256` propagating through merge() so the
# byte change shows up in the merged data, but tracking the writes
# explicitly here means: (a) the log surfaces which files moved, helpful
# for reviewing the auto-PR; (b) if a future refactor ever breaks the
# sha256 propagation path, we'll see "headshot files changed but
# bios.json bytes unchanged" in the log instead of an unexplained PR
# with a lone binary diff.
PHOTOS_CHANGED: list[str] = []

# Link fields the sync rewrote this run (raw → normalised), accumulated
# across row_to_member calls the same way PHOTOS_CHANGED is. The auto-PR
# body lists them under "Review flags" so a normalisation a reviewer
# might want to sanity-check is visible at review time, not buried in the
# scheduled job's stderr (#796). Each entry: {name, field, before, after}.
LINK_REWRITES: list[dict] = []

# ──────────────────────────── helpers ────────────────────────────


def norm_email(s: str) -> str:
    return (s or "").strip().lower()


def country_key(s: str) -> str:
    """Normalise a country string for case-insensitive comparison in
    name_key fallback matching. We don't try to canonicalise aliases
    here — that's load_mc_lookup()'s job for the country_code field.
    Bare lowercase is enough to absorb the obvious case differences
    ("united kingdom" vs "United Kingdom") without false-merging
    "United Kingdom" with "United States". Returns "" for empty input,
    which the caller uses as "skip the name-based fallback" — we don't
    want to collapse entries that lack a country to confirm identity."""
    return (s or "").strip().lower()


def parse_timestamp(raw: str) -> float:
    """Parse a Google-Forms timestamp string to epoch seconds. The
    format depends on the form-owner's account locale at sheet creation:
    French gives "16/05/2026 11:35:42", US gives "5/16/2026 11:35:42",
    ISO accounts give "2026-05-16 11:35:42", etc. Comparing the raw
    strings would silently mis-sort across month boundaries for the
    non-ISO formats. Returns 0.0 for an empty / unparseable value, so
    older entries lose to newer ones in any dedup comparison."""
    if not raw:
        return 0.0
    raw = raw.strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S",       # ISO-ish (form owner in en/de/many)
        "%Y-%m-%dT%H:%M:%S",       # ISO with "T"
        "%d/%m/%Y %H:%M:%S",       # French / UK / EU
        "%m/%d/%Y %H:%M:%S",       # US
        "%d.%m.%Y %H:%M:%S",       # German with dots
        "%Y/%m/%d %H:%M:%S",       # Japanese
    ):
        try:
            return datetime.strptime(raw, fmt).timestamp()
        except ValueError:
            continue
    return 0.0


def parse_wgs(raw: str) -> list[int]:
    """Extract the set of {1,2,3,4} WG numbers from a Google-Forms
    checkbox cell. The cell value is a comma-separated list of the
    ticked checkbox labels — for this form those look like
    "WG1 · Building the Network". Prefer matching the digit after
    "WG"; if nothing matches that pattern (e.g. someone shortened the
    option labels to bare numerals), fall back to standalone digits.

    The previous regex `\\b([1-4])\\b` did not match because the
    digit in `WG1` sits between two word characters ("G" and end /
    " "), so the `\\b` word boundary never fires."""
    if not raw:
        return []
    s = str(raw)
    matches = re.findall(r"WG\s*([1-4])", s, re.IGNORECASE)
    if not matches:
        matches = re.findall(r"(?<![A-Za-z0-9])([1-4])(?![A-Za-z0-9])", s)
    return sorted({int(d) for d in matches})


def parse_mentorship(raw: str) -> list[str]:
    """Map the mentorship checkbox cell to role tags for the directory.

    The cell is the comma-joined list of ticked options. We emit a
    small ordered list drawn from {"mentor", "mentee", "mentor-full",
    "matched"}:

      - "mentor"       the member is offering to mentor (a mid-career or
                       senior scholar open to mentoring early-career ones).
      - "mentee"       the member is looking for a mentor.
      - "mentor-full"  the member mentors but is at capacity right now.
      - "matched"      the member found a mentor through the directory.

    The last two are the off-switches for the first two (#1415). merge()
    only overwrites a field when the new value is non-empty, so unticking
    a box and resubmitting leaves the old flag standing forever. A member
    who has filled their roster or found their mentor therefore needs a
    positive option to tick: the re-parsed cell replaces the stored list,
    and the new tag is one no filter chip or wizard column looks for, so
    they drop out of the matching pool while keeping the badge that says
    why. "mentor-full" suppresses "mentor" and "matched" suppresses
    "mentee", which covers the member who ticks the new box but leaves the
    old one ticked as well.

    Matching is tolerant substring matching against the option text, so
    light edits to the Form wording keep working. Distinct phrases keep
    the directions apart even though all four contain "mentor":
    "open to mentoring" / "as a mentor" -> mentor;
    "looking for a mentor" / "seeking a mentor" -> mentee;
    "at capacity" / "full capacity" -> mentor-full;
    "found a mentor" / "found my mentor" -> matched. The directory badge
    labels are also recognised ("available to mentor" -> mentor,
    "seeking mentorship" -> mentee, "mentoring, at capacity" ->
    mentor-full), so a maintainer editing the Sheet by hand can type the
    displayed status rather than the exact Form option. An empty or
    absent cell (the question is optional, and unconfigured columns read
    as "") yields []."""
    if not raw:
        return []
    s = str(raw).lower()
    out: list[str] = []
    # The two off-switches are tested first: each suppresses the standing
    # flag it retires, so a member who ticks the new box without unticking
    # the old one still reads as full / matched rather than both at once.
    full = any(p in s for p in (
        "at capacity", "at full capacity", "full capacity",
        "not taking on", "no capacity",
    ))
    matched = any(p in s for p in (
        "found a mentor", "found my mentor",
        "no longer looking for a mentor", "no longer seeking",
    ))
    if not full and any(p in s for p in (
        "open to mentoring", "offer mentor", "offering mentor",
        "happy to mentor", "as a mentor", "provide mentor",
        "mentoring early", "available to mentor", "available as a mentor",
    )):
        out.append("mentor")
    if not matched and any(p in s for p in (
        "looking for a mentor", "seeking a mentor", "find a mentor",
        "want a mentor", "need a mentor", "be mentored", "as a mentee",
        "seeking mentorship", "seeking mentoring", "looking for mentorship",
        "want mentorship", "need mentorship", "find mentorship",
    )):
        out.append("mentee")
    if full:
        out.append("mentor-full")
    if matched:
        out.append("matched")
    return out


def parse_stsm_hosting(raw: str) -> str:
    """Map the "Could your institution host STSM visitors?" cell to a
    tri-state hosting signal for the directory (#760). The Form offers
    Yes / No / Ask me; we emit:

      - "yes"  the institution can host STSM visitors.
      - "ask"  conditional ("Ask me" / "maybe" / "depends").
      - ""     declined, blank, or an unconfigured column.

    A scalar, not a list (unlike mentorship), since the question is
    single-select. Tolerant substring matching keeps light Form edits
    working, and the "ask" check runs first so a hand-typed "yes, but ask
    me first" lands on the softer, conditional signal. An empty string is
    dropped before write, so the field stays absent for non-hosts."""
    if not raw:
        return ""
    s = str(raw).strip().lower()
    if not s:
        return ""
    if any(p in s for p in (
        "ask", "maybe", "depends", "enquire", "inquire",
        "get in touch", "contact", "case by case", "case-by-case",
    )):
        return "ask"
    if any(p in s for p in (
        "yes", "can host", "happy to host", "able to host",
        "willing to host", "would host", "open to host",
    )):
        return "yes"
    return ""


def parse_keywords(raw: str) -> list[str]:
    """Split a free-text keyword cell into individual keywords.

    The form asks for a comma-separated list, but submitters reach for
    whatever separator is at hand: semicolons, newlines, bullet points, or
    a dash / slash typed in place of a comma. Split on all of those, while
    leaving an intra-keyword hyphen intact so "Civil-military relations" and
    "EU-NATO relations" stay whole: a dash or slash only separates when it
    is padded by spaces (or starts a bulleted line), never when it sits
    between two letters. Leading list markers ("- ", "• ") are trimmed."""
    if not raw:
        return []
    # , ; newlines  |  spaced - – — /  |  bullets (with optional spaces)
    parts = re.split(r"[,;\n\r]+|\s+[/–—-]\s+|\s*[•·]\s*", raw)
    out: list[str] = []
    for p in parts:
        p = p.strip().strip("-–—•·").strip()
        if p:
            out.append(p)
    return out


# Canonical honorific forms for the leading title in a member's name. The
# house style: the short courtesy titles carry no full stop (Mr, Mrs, Ms,
# Mx, Dr), while the abbreviation Prof keeps one (Prof.). Keyed by the
# lowercased title with any dot stripped.
_TITLE_FORMS = {
    "mr": "Mr", "mrs": "Mrs", "ms": "Ms", "mx": "Mx",
    "dr": "Dr", "doctor": "Dr", "prof": "Prof.", "professor": "Prof.",
}


def normalise_title(name: str) -> str:
    """Standardise the leading honorific(s) on a name to house style.

    Mr / Mrs / Ms / Mx / Dr lose any full stop; Prof gains one ("Prof.").
    The written-out forms fold to the abbreviation too ("Professor" ->
    "Prof.", "Doctor" -> "Dr"), so a submission that spells the title in
    full is uniformised like the rest. Works whether the title is spaced
    ("Dr Jane"), dotted ("Dr. Jane"), or glued by a dot ("Dr.Jane"), and
    consumes a stacked run of titles ("Prof. Dr. Hans" -> "Prof. Dr Hans")
    as some continental academics write them. The rest of the name is left
    exactly as submitted, and a real name that merely starts with a title's
    letters ("Drew", "Misha") is untouched because the title must be
    followed by a dot, a space, or the end of the string, never another
    letter."""
    if not name:
        return name
    rest = name.strip()
    titles: list[str] = []
    while True:
        m = re.match(r"(?i)^(professor|prof|doctor|mrs|mr|ms|mx|dr)\b\.?\s*", rest)
        if not m:
            break
        titles.append(_TITLE_FORMS[m.group(1).lower()])
        rest = rest[m.end():]
    if not titles:
        return name.strip()
    return " ".join(titles) + (" " + rest if rest else "")


# The "Title" dropdown's no-honorific option (and any blank) — the
# submitter explicitly wants no title in front of their name.
_NO_TITLE = {"", "none please", "none", "no title", "none.", "n/a", "-"}

# Leading-honorific strip for the name field, so a title a submitter still
# typed into "Full name" is removed before the dropdown title is prepended
# (never "Prof. Prof. Jane"). Covers the written-out forms too.
_LEADING_TITLE_RE = re.compile(
    r"(?i)^(Professor|Prof|Doctor|Dr|Mrs|Mr|Ms|Mx)\.?(?:\s+|$)")


def build_name(row: dict, cols: dict) -> str:
    """Assemble a member's display name from the form row, in house style.

    The form carries the honorific in its own "Title" dropdown (Prof. / Dr
    / Ms / Mr / Mx / None please), kept separate from "Full name" so a
    submitter never types the title into the name field, which used to leak
    it into the slug ("Professor Mark Rhinard" -> professor-mark-rhinard).
    The chosen title is prepended to the name and the whole thing is run
    through normalise_title(); "None please" (or a blank) means no title.

    The name is read from cols["name"], falling back to cols["name_legacy"]
    (the old single-field "Full name (with title …)" header) for responses
    captured before the question was split, so a renamed question never
    blanks an existing member. normalise_title() still folds any honorific
    that slipped into the name field, so a legacy row with the title inline
    keeps working untouched."""
    full = (row.get(cols.get("name", ""), "") or "").strip()
    if not full and cols.get("name_legacy"):
        full = (row.get(cols["name_legacy"], "") or "").strip()
    title_raw = (row.get(cols.get("title", ""), "") or "").strip()
    if title_raw.lower() not in _NO_TITLE:
        bare = _LEADING_TITLE_RE.sub("", full).strip() or full
        return normalise_title(f"{title_raw} {bare}")
    return normalise_title(full)


# ─────────────────── keyword normalisation (Phase 2) ───────────────────
#
# The directory renders each bio's `keywords` as small pills. Submitters
# enter free-text via the Google Form, so the corpus drifts in three
# directions over time:
#
#   1. Casing: "International Security" vs "international security".
#   2. Acronyms get mangled by naive sentence-case: "EU-NATO relations"
#      → "Eu-nato relations" if normalised letter-by-letter.
#   3. Near-duplicates: two submitters write "Foreign policy analysis"
#      and "FPA" for the same concept.
#
# We solve all three at sync time so the renderer can be dumb. The
# alias file `data/keyword-aliases.json` is the curated source: an
# `acronyms` list (preferred display forms preserved through any
# normalisation) and an `aliases` map (canonical phrase → list of
# lowercased aliases that resolve to it). The maintainer extends the
# file by hand when a submission lands; sync emits a `canonical_keywords`
# field per bio and a `keyword_aggregate` top-level array.

ALIAS_FILE = ROOT / "data" / "keyword-aliases.json"


def load_keyword_aliases() -> tuple[set[str], dict[str, str], dict[str, str]]:
    """Return (acronym_set, alias_to_canonical_map, spelling_map).

    - acronym_set: lowercased forms of every entry in `acronyms`. Used
      by the word-walking normaliser to preserve in-word capitalisation
      ("eu foreign policy" → "EU foreign policy").
    - alias_to_canonical_map: lowercased alias string → canonical
      display string. Used for whole-keyword aliasing ("fpa" →
      "Foreign policy analysis"). Auto-extended so every canonical's
      own lowercase form maps back to it ("eu" → "EU"), and so each
      acronym entry maps to itself ("nato" → "NATO").
    - spelling_map: lowercased American spelling → lowercased British
      spelling, applied word-by-word during the walk ("defense" →
      "defence"), so compound phrases normalise too ("cyber defense"
      → "Cyber defence")."""
    acronym_set: set[str] = set()
    alias_map: dict[str, str] = {}
    spelling_map: dict[str, str] = {}
    if not ALIAS_FILE.exists():
        return acronym_set, alias_map, spelling_map
    try:
        doc = json.loads(ALIAS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"  ! cannot read {ALIAS_FILE.name}: {exc}; falling back "
              f"to identity normalisation.")
        return acronym_set, alias_map, spelling_map

    # `acronyms` and `proper_nouns` feed the same preservation set: any
    # token matching one (case-insensitively) is emitted in the exact
    # listed form, bypassing the sentence-case lowercasing. Acronyms keep
    # their all-caps form (EU, NATO); proper nouns keep their Title-case
    # form (Afghanistan, Ukraine) so they don't lowercase mid-phrase.
    for entry in list(doc.get("acronyms", [])) + list(doc.get("proper_nouns", [])):
        if not isinstance(entry, str):
            continue
        lower = entry.lower()
        acronym_set.add(lower)
        # Each preserved form also maps to its own canonical display, so a
        # raw "eu"/"EU" or "ukraine"/"Ukraine" both resolve to the same key.
        alias_map[lower] = entry

    for canonical, aliases in (doc.get("aliases") or {}).items():
        if not isinstance(canonical, str):
            continue
        alias_map[canonical.lower()] = canonical
        for alias in aliases or []:
            if isinstance(alias, str) and alias.strip():
                alias_map[alias.strip().lower()] = canonical

    for us, uk in (doc.get("spelling") or {}).items():
        if isinstance(us, str) and isinstance(uk, str) and us.strip() and uk.strip():
            spelling_map[us.strip().lower()] = uk.strip().lower()

    return acronym_set, alias_map, spelling_map


def load_keyword_themes() -> dict[str, str]:
    """Return a lowercased-canonical-keyword → theme-name map from the
    `themes` section of data/keyword-aliases.json.

    Each canonical keyword belongs to at most one broad research theme.
    The directory's filter clusters members by theme (so people working
    in the same area surface together) while their cards keep the specific
    keyword pills. Empty if the file or the `themes` section is missing,
    in which case the renderer's theme filter simply stays hidden."""
    theme_of: dict[str, str] = {}
    if not ALIAS_FILE.exists():
        return theme_of
    try:
        doc = json.loads(ALIAS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return theme_of
    for theme, kws in (doc.get("themes") or {}).items():
        if not isinstance(theme, str):
            continue
        for kw in kws or []:
            if isinstance(kw, str) and kw.strip():
                theme_of[kw.strip().lower()] = theme
    return theme_of


_AFFILIATION_ALIASES_CACHE: "dict[str, str] | None" = None


def load_affiliation_aliases() -> dict[str, str]:
    """Return a lowercased-variant → canonical-affiliation map from the
    `affiliation_aliases` section of data/keyword-aliases.json.

    Free-text employer fields fragment the same institution across
    several spellings ("ETH Center for Security Studies" vs "ETH Zurich,
    Center for Security Studies"), so the directory shows two employers
    where there is one. This is a hand-curated map: each canonical name
    keys a list of the variants that should fold into it. Punctuation
    normalisation alone cannot do this (the words themselves differ), so
    the map is the only mechanism that merges them. Cached after first
    read; empty if the file or section is missing, in which case
    affiliations pass through punctuation-normalisation only."""
    global _AFFILIATION_ALIASES_CACHE
    if _AFFILIATION_ALIASES_CACHE is not None:
        return _AFFILIATION_ALIASES_CACHE
    aliases: dict[str, str] = {}
    if ALIAS_FILE.exists():
        try:
            doc = json.loads(ALIAS_FILE.read_text(encoding="utf-8"))
            for canonical, variants in (doc.get("affiliation_aliases") or {}).items():
                if not isinstance(canonical, str) or not canonical.strip():
                    continue
                # The canonical name resolves to itself, so an already-clean
                # value is idempotent under the lookup.
                aliases[canonical.strip().lower()] = canonical.strip()
                for v in variants or []:
                    if isinstance(v, str) and v.strip():
                        aliases[v.strip().lower()] = canonical.strip()
        except (json.JSONDecodeError, OSError):
            pass
    _AFFILIATION_ALIASES_CACHE = aliases
    return aliases


_REGION_VOCAB_CACHE: "dict[str, str] | None" = None


def load_region_vocab() -> dict[str, str]:
    """Return a lowercased-region → canonical-display map from the
    `regions` section of data/keyword-aliases.json.

    A controlled vocabulary of research-region names (modelled on the EU
    Institute for Security Studies' regions). Drives the directory's
    research-region filter — a geographic axis independent of the topical
    themes. Cached after first read; empty if the file or section is
    missing, in which case the region filter simply stays hidden."""
    global _REGION_VOCAB_CACHE
    if _REGION_VOCAB_CACHE is not None:
        return _REGION_VOCAB_CACHE
    vocab: dict[str, str] = {}
    if ALIAS_FILE.exists():
        try:
            doc = json.loads(ALIAS_FILE.read_text(encoding="utf-8"))
            for r in doc.get("regions", []):
                if isinstance(r, str) and r.strip():
                    vocab[r.strip().lower()] = r.strip()
        except (json.JSONDecodeError, OSError):
            pass
    _REGION_VOCAB_CACHE = vocab
    return vocab


def load_keyword_drops() -> set[str]:
    """Lowercased forms of every entry in `drop_keywords`.

    Country and sub-region names typed into the keyword box. The regions
    facet owns that axis, and `regions` only holds the eight broad
    controlled regions, so a bare "Ireland" or "MENA region" passed
    straight through and stood alone in the theme filter meaning nothing
    (#1701). Matched on the whole canonical form, never on a word inside
    one, so "Russia-Ukraine war" and the themed keyword "India" survive.
    """
    drops: set[str] = set()
    if ALIAS_FILE.exists():
        try:
            doc = json.loads(ALIAS_FILE.read_text(encoding="utf-8"))
            for k in doc.get("drop_keywords", []):
                if isinstance(k, str) and k.strip():
                    drops.add(k.strip().lower())
        except (json.JSONDecodeError, OSError):
            pass
    return drops


def load_keyword_splits() -> dict[str, list[str]]:
    """Lowercased submitted form → the canonical keywords it becomes.

    For a submission that is a phrase rather than a tag: "AI cyber
    security geopolitics" is three concepts the taxonomy already holds
    separately, and as one string it clustered with nothing and left its
    author with no research theme at all (#1701). Aliasing cannot help,
    since an alias maps many forms onto one and this needs the opposite.
    """
    splits: dict[str, list[str]] = {}
    if ALIAS_FILE.exists():
        try:
            doc = json.loads(ALIAS_FILE.read_text(encoding="utf-8"))
            for raw, parts in (doc.get("splits") or {}).items():
                if isinstance(parts, list) and parts:
                    splits[raw.strip().lower()] = [p for p in parts if isinstance(p, str) and p.strip()]
        except (json.JSONDecodeError, OSError):
            pass
    return splits


def parse_regions(raw: str) -> list[str]:
    """Map a Research-regions form cell (comma- or semicolon-separated
    checkbox values) to a sorted list of canonical region names from the
    controlled vocabulary. Unknown values are dropped, so a stray free-text
    entry never leaks into the filter."""
    vocab = load_region_vocab()
    out: list[str] = []
    seen: set[str] = set()
    for part in re.split(r"[,;]", raw or ""):
        canon = vocab.get(part.strip().lower())
        if canon and canon not in seen:
            seen.add(canon)
            out.append(canon)
    return sorted(out)


_WORD_RE = re.compile(r"[\w&]+", re.UNICODE)


def normalise_keyword(
    raw: str,
    acronyms: set[str],
    alias_map: dict[str, str],
    spelling_map: dict[str, str] | None = None,
) -> str:
    """Resolve a raw submitted keyword to its canonical display form.

    Two stages:
      1. Whole-keyword alias lookup. Strip + lowercase + check the
         reverse alias map. If hit, return the canonical verbatim.
      2. Word-walk normalisation. For each letter-run, if its lowercase
         form is in the acronym set, emit the canonical acronym (also
         from the alias map, which stores acronyms by their lowercase
         form). Otherwise: rewrite American to British spelling via the
         spelling map, then capitalise the first word and lowercase the
         rest. Separators (hyphens, en-dashes, spaces, slashes) pass
         through untouched."""
    spelling_map = spelling_map or {}
    trimmed = (raw or "").strip()
    if not trimmed:
        return ""

    # Stage 1: whole-keyword alias.
    direct = alias_map.get(trimmed.lower())
    if direct:
        return direct

    # Stage 2: word-walk with acronym preservation + spelling normalisation.
    state = {"first_alpha": True}

    def _replace(match: "re.Match[str]") -> str:
        word = match.group(0)
        # A standalone "&" reads as the conjunction "and" in canonical
        # form ("Policy evaluation & lessons learned" → "… and …").
        # &-bearing acronyms like "R&D" are matched whole (the token is
        # "R&D", not "&"), so they are untouched.
        if word == "&":
            word = "and"
        lower = word.lower()
        if lower in acronyms:
            state["first_alpha"] = False
            return alias_map.get(lower, word)
        # American → British spelling, applied per word so compounds
        # normalise too ("cyber defense" → "Cyber defence").
        lower = spelling_map.get(lower, lower)
        if state["first_alpha"]:
            state["first_alpha"] = False
            return lower[:1].upper() + lower[1:]
        return lower

    return _WORD_RE.sub(_replace, trimmed)


def normalise_affiliation(raw: str) -> str:
    """Standardise the separator style inside a free-text affiliation so
    the directory reads uniformly. Submitters write an institution plus a
    named sub-unit, or two affiliations, in several styles ("ETH Zurich -
    Center for Security Studies", "Ghent University; Egmont Institute",
    "Sciences Po, Center for International Studies"). We settle on two
    conventions:

      - a spaced hyphen or dash between an institution and its named part
        becomes a comma ("ETH Zurich, Center for Security Studies");
      - a semicolon between two separate affiliations becomes a slash
        ("Ghent University / Egmont Institute").

    Whitespace is collapsed. This does not merge differently-spelled names
    for the same institution (that needs a hand-curated alias map, tracked
    separately); it only fixes the punctuation so the field is consistent.
    Idempotent: an already-normalised value is returned unchanged."""
    s = " ".join((raw or "").split())
    if not s:
        return ""
    # Two separate affiliations: semicolon -> slash.
    s = re.sub(r"\s*;\s*", " / ", s)
    # Institution + named sub-unit: spaced hyphen / en-dash / em-dash -> comma.
    # The surrounding spaces are required, so hyphenated names with no
    # spaces ("Aix-Marseille", "Friedrich-Alexander") are left untouched.
    s = re.sub(r"\s+[-–—]\s+", ", ", s)
    # Fold a known spelling variant onto its canonical institution name.
    # Looked up after punctuation normalisation so the curated map can key
    # on the cleaned form. Punctuation-only normalisation cannot merge
    # differently-worded names for one place; this map is what does.
    return load_affiliation_aliases().get(s.lower(), s)


def _levenshtein(a: str, b: str) -> int:
    """Tight Levenshtein for the sync-time alias-candidate hint. The
    corpus is small (tens of unique keywords) so a quadratic
    implementation is fine; no need to pull in a dependency."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            curr[j] = min(
                prev[j] + 1,            # deletion
                curr[j - 1] + 1,        # insertion
                prev[j - 1] + (0 if ca == cb else 1),  # substitution
            )
        prev = curr
    return prev[-1]


def flag_alias_candidates(aggregate: dict[str, int], alias_map: dict[str, str]) -> None:
    """Print a human-readable hint when two canonical keywords look
    close enough to be candidates for merging via the alias map.
    Two heuristics fire:

      1. Levenshtein distance ≤ 2 (catches typo-ish variants the
         normaliser missed).
      2. One canonical is a strict suffix-or-prefix substring of
         another at a word boundary (catches "foreign policy" inside
         "foreign policy analysis").

    Already-aliased pairs are skipped (if the maintainer has decided
    they're different concepts, the script shouldn't keep nagging)."""
    canonicals = sorted(aggregate.keys())
    seen: set[tuple[str, str]] = set()
    aliased = set(alias_map.values())
    for i, a in enumerate(canonicals):
        for b in canonicals[i + 1:]:
            pair = tuple(sorted((a, b)))
            if pair in seen:
                continue
            seen.add(pair)
            a_lower, b_lower = a.lower(), b.lower()
            distance = _levenshtein(a_lower, b_lower)
            substring_hit = (
                f" {a_lower} " in f" {b_lower} "
                or f" {b_lower} " in f" {a_lower} "
                or b_lower.startswith(a_lower + " ")
                or a_lower.startswith(b_lower + " ")
                or b_lower.endswith(" " + a_lower)
                or a_lower.endswith(" " + b_lower)
            )
            if distance <= 2 or substring_hit:
                # Suppress noise from canonicals already paired via
                # the alias map.
                if a in aliased and b in aliased:
                    continue
                print(
                    f"  · possible alias candidate "
                    f"({aggregate[a]}× {a!r}) "
                    f"↔ ({aggregate[b]}× {b!r}); "
                    f"distance={distance}"
                    f"{', substring' if substring_hit else ''}"
                )


def normalize_orcid(raw: str) -> str:
    """Return the canonical 19-character ORCID iD given anything users
    are likely to paste into the form. Accepts any of:

      0000-0002-1825-0097              # the ID, the form we want
      https://orcid.org/0000-0002-...  # full URL (commonest mistake)
      http://orcid.org/0000-0002-...   # http scheme
      orcid.org/0000-0002-1825-0097    # bare host + path
      sandbox.orcid.org/...            # sandbox host (rare)
       0000-0002-1825-0097             # leading/trailing whitespace
      0000000218250097                 # 16 digits, no hyphens
      0000-0002-1825-009X              # legal checksum digit X

    Returns the canonical hyphenated form ("0000-0002-1825-0097"),
    or an empty string if no plausible ID is found. Render code can
    safely build the URL as 'https://orcid.org/' + this return value.
    """
    if not raw:
        return ""
    s = raw.strip()
    # Strip any URL prefix variant. Doing this case-insensitively
    # with one regex keeps us tolerant to "HTTPS://ORCID.ORG/..." etc.
    s = re.sub(r"(?i)^(?:https?://)?(?:sandbox\.)?orcid\.org/", "", s)
    # Drop a trailing slash, anchor, or query string the user might
    # have copied alongside the ID.
    s = s.split("?", 1)[0].split("#", 1)[0].rstrip("/").strip()
    # Allow the 16-digit (no hyphen) form by inserting hyphens.
    bare = re.fullmatch(r"\d{15}[\dX]", s, flags=re.I)
    if bare:
        s = f"{s[0:4]}-{s[4:8]}-{s[8:12]}-{s[12:16]}"
    # Final validation against the canonical pattern (uppercase X).
    m = re.fullmatch(r"(\d{4}-\d{4}-\d{4}-\d{3}[\dX])", s.upper())
    return m.group(1) if m else ""


def normalise_url(raw: str) -> str:
    """Return a clickable absolute URL given whatever a submitter typed
    into a website / profile field.

    The form's link fields are free text. People paste a full URL, but
    they also type a bare domain ("itsallcyber.baby") or a scheme-less
    "www." prefix. A scheme-less value rendered straight into an <a href>
    is a *relative* link, so the card's link icon resolves to
    netsec-cost.eu/itsallcyber.baby and 404s. Prefix "https://" whenever
    no scheme is present, while leaving an explicit scheme (http, https,
    and the odd mailto / tel someone might paste) untouched. Idempotent:
    an already-absolute URL comes back unchanged."""
    s = (raw or "").strip()
    if not s:
        return ""
    if re.match(r"(?i)^https?://", s):
        return s
    # Some other explicit scheme (mailto:, tel:, ftp:) — leave it alone.
    if re.match(r"(?i)^[a-z][a-z0-9+.\-]*:", s):
        return s
    return "https://" + s.lstrip("/")


def normalise_bluesky(raw: str) -> str:
    """Return a Bluesky profile URL given any of the three forms a
    submitter uses for their account: the "@handle" they see in the app
    ("@annapagnacco.com"), the bare handle ("annapagnacco.com"), or a
    full profile URL. The card links the value straight into an <a href>,
    so a handle becomes a broken relative link and the brand icon points
    nowhere. Normalise the first two to
    https://bsky.app/profile/<handle>; pass an explicit http(s) URL
    through unchanged. Idempotent."""
    s = (raw or "").strip()
    if not s:
        return ""
    if re.match(r"(?i)^https?://", s):
        return s
    # Tolerate a leading "@" and a scheme-less "bsky.app/profile/" prefix.
    s = re.sub(r"(?i)^bsky\.app/profile/", "", s.lstrip("@")).strip().strip("/")
    if not s:
        return ""
    return "https://bsky.app/profile/" + s


def drive_file_id(url: str) -> str | None:
    """Extract a Google Drive file ID from any common URL form."""
    if not url:
        return None
    m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
    if m:
        return m.group(1)
    qs = parse_qs(urlparse(url).query)
    if "id" in qs:
        return qs["id"][0]
    return None


def download_photo(
    url: str,
    dest_no_ext: Path,
    *,
    prior_hash: str | None = None,
) -> tuple[str | None, str | None]:
    """Download a photo, optimise if Pillow available, return
    (path-relative-to-ROOT, sha256-of-upstream-bytes). Returns
    (None, None) on failure / empty URL.

    The sha256 is computed over the *raw upstream bytes* (the response
    body from Google Drive, before any PIL processing). It is stable
    across runs as long as the form submitter hasn't re-uploaded.

    `prior_hash` is the photo_source_sha256 stored against this slug
    in the existing data/bios.json (or None for a new slug). When
    the upstream hash matches `prior_hash` AND the destination JPEG
    already exists on disk, we skip the entire PIL re-encode + write.
    This is the fix for the empty-PR bug: libjpeg-turbo's
    `optimize=True` heuristic is not bit-stable across PIL versions /
    runner hosts, so re-encoding an identical input could produce
    subtly different output bytes — the old byte-equality guard at
    the bottom of this function would then fail open, write the
    "new" bytes, dirty the working tree, and trigger an auto-PR with
    a lone binary diff even though sync-bios.py's data-level check
    correctly determined nothing had substantively changed.

    Falling back to the byte-equality guard for the rare case where
    `prior_hash` is None but the file exists (e.g. a member that
    pre-dates this field's introduction). After one sync the hash is
    populated and subsequent runs short-circuit cleanly.
    """
    if not url:
        return None, None
    file_id = drive_file_id(url)
    fetch_url = (
        f"https://drive.google.com/uc?export=download&id={file_id}"
        if file_id else url
    )
    try:
        r = requests.get(fetch_url, timeout=30, allow_redirects=True)
        r.raise_for_status()
        data = r.content
    except Exception as e:
        print(f"  ! photo download failed for {url}: {e}", file=sys.stderr)
        return None, None

    upstream_hash = hashlib.sha256(data).hexdigest()
    dest = dest_no_ext.with_suffix(".jpg")

    # Fast path: if the upstream bytes match what produced the file
    # on disk last time, the file on disk is still correct — no need
    # to re-encode, no need to compare libjpeg-quantised bytes.
    if prior_hash and prior_hash == upstream_hash and dest.exists():
        return (
            str(dest.relative_to(ROOT)).replace(os.sep, "/"),
            upstream_hash,
        )

    # Re-encode through PIL (downscale + optimise), or pass through
    # if Pillow isn't installed.
    out_bytes: bytes
    if HAS_PIL:
        try:
            img = Image.open(io.BytesIO(data))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            if img.width > MAX_PHOTO_WIDTH:
                ratio = MAX_PHOTO_WIDTH / img.width
                img = img.resize(
                    (MAX_PHOTO_WIDTH, int(img.height * ratio)),
                    Image.LANCZOS,
                )
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=82, optimize=True)
            out_bytes = buf.getvalue()
        except Exception as e:
            print(f"  ! photo decode failed: {e}", file=sys.stderr)
            out_bytes = data
    else:
        out_bytes = data

    # Belt-and-braces: the upstream-hash fast path above is the
    # primary determinism guarantee. This byte-equality guard is the
    # last-line backstop for the migration window where stored
    # hashes haven't propagated to every member yet.
    if not (dest.exists() and dest.read_bytes() == out_bytes):
        dest.write_bytes(out_bytes)
        # Surface this write in main()'s substance check. The data-level
        # comparison should already catch photo changes via
        # `photo_source_sha256`, but a parallel signal here means a future
        # regression in the sha-propagation chain won't silently swallow
        # the update. See PHOTOS_CHANGED at module top.
        PHOTOS_CHANGED.append(str(dest.relative_to(ROOT)).replace(os.sep, "/"))

    return (
        str(dest.relative_to(ROOT)).replace(os.sep, "/"),
        upstream_hash,
    )


# The Network Map draws each face as a circle of about 16 CSS px on the
# canvas, and at 44 px in the hover card. Serving the directory's 600 px
# headshot for that sent roughly 1.7 MB of detail the map cannot show and
# put the page over the 500 KB image budget (#1480). These derivatives sit
# in their own directory so none of the slug globs above can touch them.
MAP_AVATAR_DIR = PHOTO_DIR / "map"
MAP_AVATAR_WIDTH = 128


def ensure_map_avatars() -> int:
    """Write a map-sized .webp for every headshot, into
    assets/images/people/map/. Idempotent the same way ensure_people_webp
    is, through encode_webp's byte comparison. Returns the count written.

    Sourced from the .webp the directory already serves where one exists,
    falling back to the original, so this never re-encodes a JPEG twice.
    """
    if not HAS_PIL:
        return 0
    MAP_AVATAR_DIR.mkdir(exist_ok=True)
    written = 0
    for src in sorted(PHOTO_DIR.iterdir()):
        # .webp is in the list because a hand-added seed photo can arrive
        # as a webp with no JPEG sibling, and would otherwise be the one
        # member on the map still served at full size.
        if src.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            continue
        preferred = src.with_suffix(".webp")
        source = preferred if preferred.exists() else src
        dest = MAP_AVATAR_DIR / f"{src.stem}.webp"
        try:
            if encode_webp(source, dest, MAP_AVATAR_WIDTH):
                written += 1
                PHOTOS_CHANGED.append(str(dest.relative_to(ROOT)).replace(os.sep, "/"))
        except Exception as e:
            print(f"  ! map avatar encode failed for {src.name}: {e}", file=sys.stderr)
    return written


def encode_webp(source, dest, max_width: int) -> bool:
    """Encode `source` to `dest` as WebP, downscaled to `max_width`, and
    report whether the file on disk actually changed.

    Compares the encoded bytes against what is already there rather than
    comparing mtimes. Git does not store mtimes, so actions/checkout stamps
    every file with the checkout time in index order, and a source that
    happens to sort after its derivative looks newer on every single run.
    That is what made the map avatars re-encode nightly: the derivative
    lives at assets/images/people/map/<slug>.webp, so every slug sorting at
    or after "map" had its source written later, and 31 of 71 avatars were
    rewritten each night. The bytes were identical, so git saw nothing and
    the auto-PR stayed empty, but PHOTOS_CHANGED filled up and tripped the
    "data unchanged, photos rewritten" alarm (#1758's log). The encode is
    deterministic for a given source and Pillow build, so byte equality is
    the honest test of whether anything changed.
    """
    img = Image.open(source)
    if img.mode in ("RGBA", "P", "LA"):
        # WebP keeps alpha, but the headshots are opaque circles; flatten to
        # RGB for the smallest, most predictable output.
        img = img.convert("RGB")
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=80, method=6)
    encoded = buf.getvalue()
    if dest.exists() and dest.read_bytes() == encoded:
        return False
    dest.write_bytes(encoded)
    return True


def ensure_people_webp() -> int:
    """Make sure every headshot in assets/images/people/ has a sibling
    .webp (the smaller format the directory serves first, with the
    original as the <picture> fallback). Idempotent: encode_webp leaves a
    derivative alone when the re-encode is byte-identical. Returns the
    count written.

    Runs over .jpg / .jpeg / .png sources, keyed by basename, so it
    covers both the form-synced .jpg files and the hand-added seed /
    leadership photos (which use mixed extensions). Encoding failures
    are non-fatal (the original still serves via the fallback)."""
    if not HAS_PIL:
        return 0
    written = 0
    for src in sorted(PHOTO_DIR.iterdir()):
        if src.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue
        dest = src.with_suffix(".webp")
        try:
            if encode_webp(src, dest, MAX_PHOTO_WIDTH):
                written += 1
                PHOTOS_CHANGED.append(str(dest.relative_to(ROOT)).replace(os.sep, "/"))
        except Exception as e:
            print(f"  ! webp encode failed for {src.name}: {e}", file=sys.stderr)
    return written


def resolve_prior_entry(
    slug: str,
    email: str,
    name: str,
    country: str,
    old_by_id: dict[str, dict] | None = None,
    old_by_email: dict[str, dict] | None = None,
    old_by_namekey: dict[tuple[str, str, str], dict] | None = None,
) -> dict | None:
    """Find the prior bios.json entry a form submission will collapse
    onto, using the same three signals merge() uses, in the same order:
    the form-collected account email, then the slug, then name+country.
    Returns the prior member dict, or None for a genuinely new member.

    Called before the photo download so the image writes to — and its
    de-dup hash is read from — the entry's *canonical* slug, even when
    the submission's own slug differs. That is the name-collapse case
    (e.g. "Dr John N.T. Helferich" submitting against the seed "Dr John
    Helferich"): without it the photo re-encodes every run under the
    form slug and merge then renames it onto the canonical file, so the
    canonical file's bytes churn each sync (libjpeg is not bit-stable)
    and the workflow opens an auto-PR with a lone binary diff."""
    if email and old_by_email:
        hit = old_by_email.get(email.lower())
        if hit:
            return hit
    if old_by_id and slug in old_by_id:
        return old_by_id[slug]
    if old_by_namekey:
        nk = name_key(name)
        if nk:
            return old_by_namekey.get((nk[0], nk[1], country_key(country)))
    return None


# Website navigation chrome that submitters sometimes paste in front of
# their bio when they copy it straight off a university staff page. Each
# entry is matched case-insensitively against a whole leading line, so a
# stray "Till startsidan" / "Search" header (Uppsala University's site
# chrome, seen on Alexandra Brankova's first sync) is dropped while real
# prose, which never appears as one of these bare labels, is untouched.
# Lowercased; extend with new offenders as they surface (one line each).
_BIO_CHROME_LINES = {
    "search", "menu", "meny", "suche", "recherche", "buscar",
    "skip to main content", "skip to content",
    "till startsidan", "hoppa till innehållet", "hoppa till innehåll",
    "zur startseite", "zum inhalt springen", "aller au contenu",
    "home", "homepage", "startseite", "accueil",
}


def strip_bio_chrome(bio: str) -> str:
    """Drop leading website-navigation lines pasted ahead of a bio.

    Submitters who copy their bio off a university profile page can carry
    the page's nav header along with it (the canonical case is the Swedish
    "Till startsidan" / "Search" pair from Uppsala's staff site). Only a
    leading run of lines that exactly match a known chrome label (after
    trimming) is removed, so the body text is never trimmed by accident.
    Runs each sync, so the fix survives a re-read of the raw Sheet value
    without anyone having to edit the form response."""
    if not bio:
        return bio
    lines = bio.split("\n")
    while lines and lines[0].strip().lower() in _BIO_CHROME_LINES:
        lines.pop(0)
    return "\n".join(lines).strip()


def row_to_member(
    row: dict,
    cols: dict,
    old_by_id: dict[str, dict] | None = None,
    old_by_email: dict[str, dict] | None = None,
    old_by_namekey: dict[tuple[str, str, str], dict] | None = None,
) -> dict | None:
    """Convert one CSV row dict to a bios.json member entry, or None if
    the row should be skipped.

    The three `old_by_*` indexes are the prior bios.json members keyed by
    slug, account email, and (first, last, country) name key. They let
    the photo download resolve the entry this row will collapse onto, so
    an unchanged photo is neither re-encoded nor written under the wrong
    slug. Pass them all None (tests / one-off scripted runs) and the
    photo will always be re-encoded under the row's own slug.
    """
    name = build_name(row, cols)
    consent = (row.get(cols["consent"], "") or "").strip().lower()
    if not name:
        return None
    # A row whose name is only a title ("Mr", "Dr", …) with nothing after it
    # is an incomplete submission: the person left the name blank. slugify and
    # name_key both strip the title to nothing, so such a row can never
    # collapse onto the real entry and instead surfaces as a duplicate "Mr"
    # card next to the complete one. Drop it.
    if not re.sub(r"(?i)^(Prof|Mrs|Mr|Ms|Mx|Dr)\.?(?:\s+|$)", "", name).strip():
        print(f"  · skipping {name!r}: title only, no name", file=sys.stderr)
        return None
    # Strict: only publish if consent recorded
    if consent and not any(t in consent for t in ("yes", "agree", "✓", "consent", "true")):
        # Explicit non-consent — skip
        print(f"  · skipping {name!r}: no consent recorded", file=sys.stderr)
        return None

    slug = slugify(name)
    email = norm_email(row.get(cols.get("email", ""), ""))
    country = (row.get(cols.get("country", ""), "") or "").strip()
    photo_url = (row.get(cols.get("photo", ""), "") or "").strip()
    photo_path: str | None = None
    photo_hash: str | None = None
    if photo_url:
        # Resolve the entry this row collapses onto so the photo writes
        # to its canonical slug and compares against the stored hash,
        # even when this row's own slug differs (the name-collapse case).
        target_prior = resolve_prior_entry(
            slug, email, name, country,
            old_by_id, old_by_email, old_by_namekey,
        )
        dest_slug = target_prior["id"] if target_prior else slug
        prior_hash = (target_prior or {}).get("photo_source_sha256") or None
        photo_path, photo_hash = download_photo(
            photo_url, PHOTO_DIR / dest_slug, prior_hash=prior_hash,
        )

    # Normalise the free-text link fields, recording any value the
    # normaliser actually rewrote so the weekly sync PR body can surface
    # it for review (#796) instead of leaving it in the job's stderr.
    def _link(field: str, normaliser) -> str:
        raw = (row.get(cols.get(field, ""), "") or "").strip()
        norm = normaliser(raw)
        if raw and norm != raw:
            LINK_REWRITES.append(
                {"name": name, "field": field, "before": raw, "after": norm}
            )
        return norm

    out = {
        "id": slug,
        "name": name,
        "country": country,
        "country_code": "",  # filled by post-processing
        # Normalise here (not only in the later whole-list pass) so a
        # form entry carries the same punctuation the stored bio does.
        # Otherwise merge() overwrites the stored, normalised affiliation
        # with the raw Sheet value, and diff_summary (which runs before
        # the whole-list normalisation) reports a phantom "updated" every
        # sync even when nothing changed.
        "affiliation": normalise_affiliation(row.get(cols.get("affiliation", ""), "") or ""),
        "position": (row.get(cols.get("position", ""), "") or "").strip(),
        "roles": [],
        "wgs": parse_wgs(row.get(cols.get("wgs", ""), "")),
        "mentorship": parse_mentorship(row.get(cols.get("mentorship", ""), "")),
        "regions": parse_regions(row.get(cols.get("regions", ""), "")),
        "stsm_hosting": parse_stsm_hosting(row.get(cols.get("stsm_hosting", ""), "")),
        "wg_leadership": {},
        "bio": strip_bio_chrome((row.get(cols.get("bio", ""), "") or "").strip()),
        "keywords": parse_keywords(row.get(cols.get("keywords", ""), "")),
        "email": (row.get(cols.get("public_email", ""), "") or "").strip(),
        "website": _link("website", normalise_url),
        "orcid": normalize_orcid(row.get(cols.get("orcid", ""), "")),
        "linkedin": _link("linkedin", normalise_url),
        "twitter": _link("twitter", normalise_url),
        "bluesky": _link("bluesky", normalise_bluesky),
        "mastodon": _link("mastodon", normalise_url),
        "photo": photo_path or "",
        "source": "form",
        "_email_key": email,  # internal, stripped before write
        "_timestamp": (row.get(cols.get("timestamp", ""), "") or "").strip(),
    }
    if photo_hash:
        # Only set when we have a hash to record — keeps the field
        # absent for members with no photo, rather than serialising
        # "photo_source_sha256": "" everywhere.
        out["photo_source_sha256"] = photo_hash
    return out


# Country-name → ISO 3166-1 alpha-2 code, used by /people.html to render
# FlagCDN thumbnails (https://flagcdn.com/h20/<code>.png).
#
# Grouped by region for diffability — when the form's country dropdown
# gains an entry, add it to the matching region table below. The names
# here must match the dropdown text exactly (see docs/bios-setup.md);
# common alternative spellings are accepted via _ALIASES at the bottom.
#
# Codes follow ISO 3166-1 alpha-2 (lowercase, as FlagCDN expects).
# Kosovo uses "xk" — the provisional code accepted by FlagCDN.

_EUROPE = {
    "Albania": "al",
    "Andorra": "ad",
    "Armenia": "am",
    "Austria": "at",
    "Azerbaijan": "az",
    "Belarus": "by",
    "Belgium": "be",
    "Bosnia and Herzegovina": "ba",
    "Bulgaria": "bg",
    "Croatia": "hr",
    "Cyprus": "cy",
    "Czechia": "cz",
    "Denmark": "dk",
    "Estonia": "ee",
    "Finland": "fi",
    "France": "fr",
    "Georgia": "ge",
    "Germany": "de",
    "Greece": "gr",
    "Hungary": "hu",
    "Iceland": "is",
    "Ireland": "ie",
    "Italy": "it",
    "Kosovo": "xk",
    "Latvia": "lv",
    "Liechtenstein": "li",
    "Lithuania": "lt",
    "Luxembourg": "lu",
    "Malta": "mt",
    "Moldova": "md",
    "Monaco": "mc",
    "Montenegro": "me",
    "Netherlands": "nl",
    "North Macedonia": "mk",
    "Norway": "no",
    "Poland": "pl",
    "Portugal": "pt",
    "Romania": "ro",
    "Russia": "ru",
    "San Marino": "sm",
    "Serbia": "rs",
    "Slovakia": "sk",
    "Slovenia": "si",
    "Spain": "es",
    "Sweden": "se",
    "Switzerland": "ch",
    "Türkiye": "tr",
    "Ukraine": "ua",
    "United Kingdom": "gb",
    "Vatican City": "va",
}

_AMERICAS = {
    "Antigua and Barbuda": "ag",
    "Argentina": "ar",
    "Bahamas": "bs",
    "Barbados": "bb",
    "Belize": "bz",
    "Bolivia": "bo",
    "Brazil": "br",
    "Canada": "ca",
    "Chile": "cl",
    "Colombia": "co",
    "Costa Rica": "cr",
    "Cuba": "cu",
    "Dominica": "dm",
    "Dominican Republic": "do",
    "Ecuador": "ec",
    "El Salvador": "sv",
    "Grenada": "gd",
    "Guatemala": "gt",
    "Guyana": "gy",
    "Haiti": "ht",
    "Honduras": "hn",
    "Jamaica": "jm",
    "Mexico": "mx",
    "Nicaragua": "ni",
    "Panama": "pa",
    "Paraguay": "py",
    "Peru": "pe",
    "Saint Kitts and Nevis": "kn",
    "Saint Lucia": "lc",
    "Saint Vincent and the Grenadines": "vc",
    "Suriname": "sr",
    "Trinidad and Tobago": "tt",
    "United States": "us",
    "Uruguay": "uy",
    "Venezuela": "ve",
}

_ASIA = {
    "Afghanistan": "af",
    "Bahrain": "bh",
    "Bangladesh": "bd",
    "Bhutan": "bt",
    "Brunei": "bn",
    "Cambodia": "kh",
    "China": "cn",
    "India": "in",
    "Indonesia": "id",
    "Iran": "ir",
    "Iraq": "iq",
    "Israel": "il",
    "Japan": "jp",
    "Jordan": "jo",
    "Kazakhstan": "kz",
    "Kuwait": "kw",
    "Kyrgyzstan": "kg",
    "Laos": "la",
    "Lebanon": "lb",
    "Malaysia": "my",
    "Maldives": "mv",
    "Mongolia": "mn",
    "Myanmar": "mm",
    "Nepal": "np",
    "North Korea": "kp",
    "Oman": "om",
    "Pakistan": "pk",
    "Palestine": "ps",
    "Philippines": "ph",
    "Qatar": "qa",
    "Saudi Arabia": "sa",
    "Singapore": "sg",
    "South Korea": "kr",
    "Sri Lanka": "lk",
    "Syria": "sy",
    "Taiwan": "tw",
    "Tajikistan": "tj",
    "Thailand": "th",
    "Timor-Leste": "tl",
    "Turkmenistan": "tm",
    "United Arab Emirates": "ae",
    "Uzbekistan": "uz",
    "Vietnam": "vn",
    "Yemen": "ye",
}
_AFRICA = {
    "Algeria": "dz",
    "Angola": "ao",
    "Benin": "bj",
    "Botswana": "bw",
    "Burkina Faso": "bf",
    "Burundi": "bi",
    "Cameroon": "cm",
    "Cape Verde": "cv",
    "Central African Republic": "cf",
    "Chad": "td",
    "Comoros": "km",
    "Congo (Democratic Republic of the)": "cd",
    "Congo (Republic of the)": "cg",
    "Côte d'Ivoire": "ci",
    "Djibouti": "dj",
    "Egypt": "eg",
    "Equatorial Guinea": "gq",
    "Eritrea": "er",
    "Eswatini": "sz",
    "Ethiopia": "et",
    "Gabon": "ga",
    "Gambia": "gm",
    "Ghana": "gh",
    "Guinea": "gn",
    "Guinea-Bissau": "gw",
    "Kenya": "ke",
    "Lesotho": "ls",
    "Liberia": "lr",
    "Libya": "ly",
    "Madagascar": "mg",
    "Malawi": "mw",
    "Mali": "ml",
    "Mauritania": "mr",
    "Mauritius": "mu",
    "Morocco": "ma",
    "Mozambique": "mz",
    "Namibia": "na",
    "Niger": "ne",
    "Nigeria": "ng",
    "Rwanda": "rw",
    "São Tomé and Príncipe": "st",
    "Senegal": "sn",
    "Seychelles": "sc",
    "Sierra Leone": "sl",
    "Somalia": "so",
    "South Africa": "za",
    "South Sudan": "ss",
    "Sudan": "sd",
    "Tanzania": "tz",
    "Togo": "tg",
    "Tunisia": "tn",
    "Uganda": "ug",
    "Zambia": "zm",
    "Zimbabwe": "zw",
}
_OCEANIA = {
    "Australia": "au",
    "Fiji": "fj",
    "Kiribati": "ki",
    "Marshall Islands": "mh",
    "Micronesia": "fm",
    "Nauru": "nr",
    "New Zealand": "nz",
    "Palau": "pw",
    "Papua New Guinea": "pg",
    "Samoa": "ws",
    "Solomon Islands": "sb",
    "Tonga": "to",
    "Tuvalu": "tv",
    "Vanuatu": "vu",
}
_ALIASES = {
    # Common alternative names and historical forms
    "Turkey": "tr",                  # pre-2022 name for Türkiye
    "Czech Republic": "cz",          # longer form of Czechia
    "Swaziland": "sz",               # pre-2018 name for Eswatini
    "Macedonia": "mk",               # pre-2019 name for North Macedonia
    "Burma": "mm",                   # alternative name for Myanmar
    "Ivory Coast": "ci",             # English form of Côte d'Ivoire
    "East Timor": "tl",              # alternative name for Timor-Leste
    "Cabo Verde": "cv",              # Portuguese form of Cape Verde
    "Holy See": "va",                # diplomatic name for Vatican City
    "Russian Federation": "ru",
    "Viet Nam": "vn",                # UN spelling of Vietnam
    "South Korea (Republic of Korea)": "kr",
    "Korea (Republic of)": "kr",
    "Korea (Democratic People's Republic of)": "kp",
    # Common abbreviations
    "USA": "us",
    "U.S.": "us",
    "U.S.A.": "us",
    "United States of America": "us",
    "UK": "gb",
    "U.K.": "gb",
    "Great Britain": "gb",
    "Britain": "gb",
    "UAE": "ae",
    "DRC": "cd",
    "DR Congo": "cd",
}

COUNTRY_TO_CODE = {
    **_EUROPE, **_AMERICAS, **_ASIA, **_AFRICA, **_OCEANIA, **_ALIASES,
}


def fill_country_code(member: dict) -> None:
    if not member.get("country_code") and member.get("country"):
        member["country_code"] = COUNTRY_TO_CODE.get(member["country"], "")


# ─── Management Committee lookup ──────────────────────────────────
# data/mc-members.json is the canonical list of MC representatives per
# country, extracted from the index.html country grid (hand-entered
# from cost.eu). When a form submission's slugified name matches an
# entry here, we auto-assign a "Management Committee · <Country>" role and fill
# country / country_code if the form didn't.
MC_FILE = ROOT / "data" / "mc-members.json"


def load_mc_lookup() -> dict[str, dict]:
    """Return a dict: slugified-name → {name, country, country_code}."""
    if not MC_FILE.exists():
        return {}
    data = json.loads(MC_FILE.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for m in data.get("members", []):
        if m.get("name"):
            out[slugify(m["name"])] = m
    return out


def apply_mc_role(member: dict, mc_lookup: dict[str, dict]) -> None:
    """If this member matches an MC list entry, ensure their country
    fields are correct, and — *only if they don't already have a more
    specific role* — set the role to "Management Committee · <Country>".

    Reasoning: leaders such as the Action Chair or a WG Co-Leader are
    typically also their country's MC representative, but their
    formal title is more informative than the generic MC label. We
    surface the formal title in the role pill; the country flag
    already signals their country. For everyone else who matches the
    MC list (and so isn't already covered by a seed entry), the MC
    label IS the most useful summary."""
    hit = mc_lookup.get(member.get("id", ""))
    if not hit:
        return
    if not member.get("country"):
        member["country"] = hit["country"]
    if not member.get("country_code"):
        member["country_code"] = hit.get("country_code", "")
    if member.get("roles"):
        return  # leadership role already present — keep it
    member["roles"] = [f"Management Committee · {hit['country']}"]


# ─── Founding-contributor cross-reference ─────────────────────────
# data/founding-proposers.json lists the 52 researchers named in the
# COST Open Call proposal OC-2024-1-27931. When a directory member's
# name matches one of those names, the member is flagged
# `founding_contributor: true` so /people.html can surface a subdued
# "Founding contributor" pill next to the WG chips. The flag is a soft
# acknowledgement, not a role: it never affects the leadership-first
# ordering or the role pill.
FOUNDING_FILE = ROOT / "data" / "founding-proposers.json"


def load_founding_slugs() -> set[str]:
    """Return the set of slugified founding-proposer names. Uses the same
    slugify() the directory keys members by, so the comparison absorbs
    titles, diacritics, and apostrophes consistently. The proposer file
    carries `_documentation` / `_source` metadata keys alongside the
    `proposers` list; only the list is read. Returns an empty set when
    the file is missing or unreadable, in which case no member is flagged
    (the badge simply never renders)."""
    if not FOUNDING_FILE.exists():
        return set()
    try:
        doc = json.loads(FOUNDING_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"  ! cannot read {FOUNDING_FILE.name}: {exc}; no founding "
              f"flags applied.", file=sys.stderr)
        return set()
    slugs: set[str] = set()
    for p in doc.get("proposers", []):
        name = (p or {}).get("name", "")
        if name:
            slugs.add(slugify(name))
    return slugs


def apply_founding_flag(member: dict, founding_slugs: set[str]) -> None:
    """Set `founding_contributor: true` on a member whose slug matches a
    founding proposer; otherwise ensure the flag is absent. Idempotent —
    re-running the sync neither adds a duplicate flag nor leaves a stale
    one if the proposer list changes."""
    if member.get("id", "") in founding_slugs:
        member["founding_contributor"] = True
    else:
        member.pop("founding_contributor", None)


# The form-sourced content fields merge() overwrites onto a returning
# member's stored entry. Every field row_to_member emits from a form row
# must appear here OR in _MERGE_EXCLUDED_FIELDS below — test-sync-bios.py's
# test_merge_allowlist_covers_every_form_field fails otherwise, so a new
# Form question can never again be parsed but silently dropped on merge
# (the gap that lost `mentorship`, then `stsm_hosting`). When you add a
# field to row_to_member, add it here too (or, if it is deliberately not
# form-owned, to the excluded set with a reason).
_FORM_OVERWRITE_FIELDS = (
    "name", "country", "country_code", "affiliation", "position", "bio",
    "keywords", "mentorship", "regions", "stsm_hosting", "email",
    "website", "orcid", "linkedin", "twitter", "bluesky", "mastodon",
)

# Fields row_to_member emits that merge() deliberately does NOT overwrite,
# each for a stated reason. The completeness test treats these as accounted
# for, so adding one here is an explicit decision, not an oversight.
_MERGE_EXCLUDED_FIELDS = frozenset({
    "id",             # the merge key itself; the prior slug is preserved
    "source",         # set to "form" explicitly, not copied
    "photo",          # carried separately so the file move stays in step
    "wgs",            # union-merged (members add WGs, never remove them)
    "roles",          # seed / leadership-directory owned; form cannot set
    "wg_leadership",  # seed / leadership-directory owned; form cannot set
})


def merge(prior: list[dict], form_entries: list[dict]) -> list[dict]:
    """Merge the prior directory state with the latest form submissions.

    - `prior` is the full member list from the existing data/bios.json,
      in its current display order (leadership first, then alphabetical).
      It is NOT filtered to source == "seed": a leadership entry whose
      `source` was previously flipped to "form" by an earlier sync would
      otherwise be re-imported as a new alphabetical-only entry, losing
      its role and position. See the regression around eugenio-sanchez
      (PR #51 / fix PR).
    - Prior entries are keyed by id (slug).
    - Form entries are matched to prior entries by three signals, tried
      in this order:
        1. The submitter's Google-account email (`_email_key`) matches
           any prior entry's published `email` column.
        2. The submitter's slug (derived from the form's "Full name"
           answer via slugify()) matches a prior entry's id.
        3. The submitter's (first-name, last-name, country) tuple
           matches a prior entry's (via name_key()).
      Signal #3 is the fallback that catches "Dr John N.T. Helferich"
      submitting against an existing "Dr John Helferich" seed entry —
      slugify() gives different ids ("john-n-t-helferich" vs
      "john-helferich"), and the seed entry has no public email to
      bridge them. We require the *country* to also match to avoid
      false-merging two genuinely different members who happen to
      share first + last names.
    - When a form entry matches a prior entry (by any of the three),
      the form data wins for content fields, but role data
      (`roles`, `wg_leadership`) is preserved unconditionally — the
      form has no roles column, so it can only ever overwrite a real
      role with an empty list, which is never what we want.
    """
    by_slug: dict[str, dict] = {s["id"]: dict(s) for s in prior}
    by_email: dict[str, str] = {
        (s.get("email") or "").lower(): s["id"]
        for s in prior if s.get("email")
    }
    # Index of (first_name, last_name, country) → prior id, used by the
    # third matching signal in the form-entry loop below. Only entries
    # with both a parseable name and a non-empty country are indexed —
    # we don't trust the name fallback without a country to confirm.
    by_name_country: dict[tuple[str, str, str], str] = {}
    for s in prior:
        nk = name_key(s.get("name", ""))
        ck = country_key(s.get("country", ""))
        if nk and ck:
            by_name_country[(nk[0], nk[1], ck)] = s["id"]

    # Two-pass dedup so a returning submitter never lands twice on the
    # directory. Pass 1 keys by the form-collected Google-account email,
    # which is the most reliable signal for "this is the same person".
    # Pass 2 keys by slug, which catches the corner case where someone
    # submits a second time from a different Google account but with
    # the same displayed name. In both passes "newest by parsed
    # timestamp wins" — see parse_timestamp() for why we don't compare
    # the raw strings.
    def newer(a: dict, b: dict) -> bool:
        """True if `a` is newer than (or as new as) `b`."""
        return parse_timestamp(a.get("_timestamp", "")) >= parse_timestamp(b.get("_timestamp", ""))

    # Pass 1: collapse by email when present; entries with empty email
    # column flow through untouched for now.
    email_dedup: dict[str, dict] = {}
    no_email: list[dict] = []
    for entry in form_entries:
        e = entry.get("_email_key")
        if not e:
            no_email.append(entry)
            continue
        if e in email_dedup and newer(email_dedup[e], entry):
            continue
        email_dedup[e] = entry

    # Pass 2: collapse by slug across everything that survived pass 1.
    slug_dedup: dict[str, dict] = {}
    for entry in list(email_dedup.values()) + no_email:
        s = entry["id"]
        if s in slug_dedup and newer(slug_dedup[s], entry):
            continue
        slug_dedup[s] = entry

    form_entries = list(slug_dedup.values())

    for entry in form_entries:
        # Find matching prior entry by email first, then slug, then by
        # (first-name, last-name, country) — see merge() docstring for
        # why the third signal is needed and how the country guard
        # bounds its false-positive risk.
        target_id = None
        if entry["_email_key"] and entry["_email_key"] in by_email:
            target_id = by_email[entry["_email_key"]]
        elif entry["id"] in by_slug:
            target_id = entry["id"]
        else:
            nk = name_key(entry.get("name", ""))
            ck = country_key(entry.get("country", ""))
            if nk and ck and (nk[0], nk[1], ck) in by_name_country:
                target_id = by_name_country[(nk[0], nk[1], ck)]
                print(
                    f"  · collapsing form entry {entry['id']!r} → prior "
                    f"{target_id!r} via name+country fallback "
                    f"({entry.get('name','')!r} matches "
                    f"{by_slug[target_id].get('name','')!r})",
                    file=sys.stderr,
                )
                # The new form photo (if any) was downloaded to
                # <new-slug>.<ext>. Rebase it to the prior slug so the
                # existing entry's photo field stays valid and we don't
                # leave an orphan file under the abandoned slug.
                #
                # When row_to_member resolved the collapse before the
                # download (the normal path now that all three prior
                # indexes are wired in), the photo already sits at the
                # canonical slug, so src == dest and there is nothing to
                # move. Skipping the block in that case is not just an
                # optimisation: the unlink sweep below would otherwise
                # delete the canonical .webp derivative every sync, which
                # ensure_people_webp then regenerates, churning a lone
                # binary diff even though the source bytes never changed.
                new_photo = entry.get("photo") or ""
                if new_photo:
                    src = ROOT / new_photo
                    dest = PHOTO_DIR / f"{target_id}{src.suffix}"
                    if src.exists() and src != dest:
                        # If the previous entry had a photo at a different
                        # source extension, drop it — the form submission
                        # is authoritative for the visual. Leave the .webp
                        # derivative alone; ensure_people_webp owns it and
                        # regenerates it from whichever source survives.
                        for stale in PHOTO_DIR.glob(f"{target_id}.*"):
                            if (
                                stale != dest
                                and stale.is_file()
                                and stale.suffix.lower() != ".webp"
                            ):
                                stale.unlink()
                        src.replace(dest)
                        entry["photo"] = str(dest.relative_to(ROOT)).replace(os.sep, "/")

        if target_id:
            existing = by_slug[target_id]
            # Form data wins for content fields. Note that "roles" and
            # "wg_leadership" are deliberately NOT in this overwrite
            # list — they come from the seed/leadership directory and
            # the form has no way to set them, so an empty form value
            # would only ever wipe a real role.
            for k in _FORM_OVERWRITE_FIELDS:
                if entry.get(k):
                    existing[k] = entry[k]
            if entry.get("photo"):
                existing["photo"] = entry["photo"]
            if entry.get("photo_source_sha256"):
                # Carry the freshly-computed upstream hash forward so
                # next week's sync can short-circuit the PIL re-encode.
                existing["photo_source_sha256"] = entry["photo_source_sha256"]
            if entry.get("wgs"):
                # Union of prior and form WGs — submitters can add WG
                # membership but cannot remove an existing assignment.
                existing["wgs"] = sorted(set(existing.get("wgs", []) + entry["wgs"]))
            existing["source"] = "form"
        else:
            # New entry from form with no prior match.
            by_slug[entry["id"]] = {k: v for k, v in entry.items() if not k.startswith("_")}

    # Final ordering: prior entries keep their position (leadership
    # first, as encoded in the prior bios.json), new entries fall
    # through to the alphabetical tail.
    prior_order = {s["id"]: i for i, s in enumerate(prior)}
    result = list(by_slug.values())
    result.sort(key=lambda m: (prior_order.get(m["id"], 10_000), m.get("name", "").lower()))

    # Drop internal fields, fill country_code, attach MC role if applicable,
    # then cross-reference the founding-proposer list for the soft badge.
    mc_lookup = load_mc_lookup()
    founding_slugs = load_founding_slugs()
    out = []
    for m in result:
        for k in list(m.keys()):
            if k.startswith("_"):
                del m[k]
        fill_country_code(m)
        apply_mc_role(m, mc_lookup)
        apply_founding_flag(m, founding_slugs)
        out.append(m)
    return out


def diff_summary(old: list[dict], new: list[dict]) -> str:
    old_by_id = {m["id"]: m for m in old}
    new_by_id = {m["id"]: m for m in new}
    added = sorted(set(new_by_id) - set(old_by_id))
    removed = sorted(set(old_by_id) - set(new_by_id))
    changed = []
    for k in set(old_by_id) & set(new_by_id):
        if json.dumps(old_by_id[k], sort_keys=True) != json.dumps(new_by_id[k], sort_keys=True):
            changed.append(k)
    lines = [f"Members: {len(new)} (was {len(old)})"]
    if added:
        lines.append("Added:")
        for k in added:
            lines.append(f"  + {k}: {new_by_id[k].get('name','')}")
    if removed:
        lines.append("Removed:")
        for k in removed:
            lines.append(f"  - {k}: {old_by_id[k].get('name','')}")
    if changed:
        lines.append("Updated:")
        for k in sorted(changed):
            lines.append(f"  ~ {k}: {new_by_id[k].get('name','')}")
    if not (added or removed or changed):
        lines.append("No changes.")
    return "\n".join(lines)


# Fields that aren't user-content but appear in member dicts: skip them
# when deciding "did this update touch real fields or just a derived
# value?". `canonical_keywords` is derived from `keywords` by this
# script; `country_code` is auto-filled from `country`; `_*` fields
# are internal anyway and stripped by merge().
_DERIVED_FIELDS = {"canonical_keywords", "country_code", "roles", "wg_leadership", "founding_contributor"}
_PHOTO_FIELDS = {"photo", "photo_source_sha256"}

# Pretty labels for fields, used in the per-member "what changed"
# bullet. Anything not listed falls through to its raw key name.
_FIELD_LABELS = {
    "name": "name",
    "bio": "bio",
    "keywords": "keywords",
    "position": "position",
    "affiliation": "affiliation",
    "country": "country",
    "email": "public email",
    "website": "website",
    "orcid": "ORCID",
    "linkedin": "LinkedIn",
    "twitter": "X / Twitter",
    "bluesky": "Bluesky",
    "mastodon": "Mastodon",
    "wgs": "Working Group memberships",
    "mentorship": "mentorship",
    "regions": "research regions",
}


def classify_diff(
    old_members: list[dict],
    new_members: list[dict],
    photos_changed: list[str],
) -> dict:
    """Categorise a sync diff at the member level for the auto-PR
    title + body. Pure: no side effects, no I/O.

    Returns a dict with four keys:
      - `new`: full member dicts for bios that appeared this run
      - `removed`: full member dicts for bios that disappeared
      - `updates`: per-member descriptors `{id, name, photo_only,
        data_only, both, fields}` where `fields` is the list of
        user-content fields whose value moved
      - `photos_changed_paths`: pass-through from PHOTOS_CHANGED so
        callers don't have to thread it separately

    The `photo_only` / `data_only` / `both` flags drive the title
    choice (see render_pr_title). `data_only` excludes derived
    fields like `canonical_keywords` so a keyword normalisation
    pass alone doesn't masquerade as a respondent edit.
    """
    old_by_id = {m["id"]: m for m in old_members}
    new_by_id = {m["id"]: m for m in new_members}
    new_ids = sorted(set(new_by_id) - set(old_by_id))
    removed_ids = sorted(set(old_by_id) - set(new_by_id))
    common = sorted(set(old_by_id) & set(new_by_id))

    updates: list[dict] = []
    for mid in common:
        old, new = old_by_id[mid], new_by_id[mid]
        if old == new:
            continue
        changed_fields = sorted({
            k for k in set(old.keys()) | set(new.keys())
            if old.get(k) != new.get(k)
        })
        photo_changed_for_member = any(f in _PHOTO_FIELDS for f in changed_fields)
        user_content_fields = [
            f for f in changed_fields
            if f not in _PHOTO_FIELDS and f not in _DERIVED_FIELDS
        ]
        updates.append({
            "id": mid,
            "name": new.get("name") or mid,
            "photo_only": photo_changed_for_member and not user_content_fields,
            "data_only": bool(user_content_fields) and not photo_changed_for_member,
            "both": photo_changed_for_member and bool(user_content_fields),
            "fields": user_content_fields,
        })

    return {
        "new": [new_by_id[i] for i in new_ids],
        "removed": [old_by_id[i] for i in removed_ids],
        "updates": updates,
        "photos_changed_paths": list(photos_changed),
    }


def render_pr_title(diff: dict) -> str:
    """One-line PR title from a classify_diff() result. Aims for
    something a maintainer can scan in a notification list and tell
    immediately whether this is a new member, a self-update, or a
    bulk batch."""
    new = diff["new"]
    upd = diff["updates"]
    rm = diff["removed"]

    # Single-actor cases read best with the actor's name in the title.
    if len(new) == 1 and not upd and not rm:
        return f"data: {new[0].get('name') or new[0].get('id')} joined the network"
    if not new and len(upd) == 1 and not rm:
        u = upd[0]
        if u["photo_only"]:
            return f"data: {u['name']} updated their headshot"
        if u["both"]:
            return f"data: {u['name']} updated their bio + headshot"
        return f"data: {u['name']} updated their bio"

    # Photo-only alarm path: the substance guard would normally have
    # routed this through the WARNING branch in main() and skipped
    # writing bios.json, but we may still be called with photo paths
    # and no member-level changes (e.g. a future regression). Surface
    # it in the title so the maintainer notices.
    if not new and not upd and not rm and diff["photos_changed_paths"]:
        return "data: headshot files changed (no member-level diff, investigate)"

    # Multi-actor: counts. Removed entries are admin operations, not
    # respondent actions, so we mention them in the body but not the
    # title. Title stays scannable.
    parts: list[str] = []
    if new:
        parts.append(f"{len(new)} new bio{'s' if len(new) != 1 else ''}")
    if upd:
        parts.append(f"{len(upd)} update{'s' if len(upd) != 1 else ''}")
    if not parts:
        return "data: weekly bios sync"
    return "data: " + " + ".join(parts)


def suggest_theme(keyword: str, theme_of: dict[str, str]) -> tuple[str, str] | None:
    """Best-guess research theme for an unthemed keyword.

    Compares the keyword against every keyword already mapped to a theme and
    returns ``(theme, nearest_keyword)`` for the closest match, or ``None``
    when nothing is close. A shared significant word ("cyber", "maritime")
    counts for a lot; otherwise it falls back to overall string similarity.

    This automates the *review* of the no-theme flags, not the taxonomy: the
    sync prints the suggestion in the PR body so the maintainer confirms or
    overrides it, but never edits ``keyword-aliases.json`` automatically (a
    wrong auto-assignment would be invisible and sticky)."""
    kw = (keyword or "").lower().strip()
    if not kw or not theme_of:
        return None
    kw_tokens = set(re.findall(r"[a-z]{4,}", kw))  # skip short words like "of"
    best_score = 0.0
    best: tuple[str, str] | None = None
    for themed, theme in theme_of.items():
        score = difflib.SequenceMatcher(None, kw, themed).ratio()
        shared = kw_tokens & set(re.findall(r"[a-z]{4,}", themed))
        if shared:
            score = max(score, 0.55 + 0.12 * len(shared))
        if score > best_score:
            best_score, best = score, (theme, themed)
    return best if best_score >= 0.5 else None


def render_pr_body_overview(
    diff: dict,
    uncategorised: set[str] | list[str] | None = None,
    link_rewrites: list[dict] | None = None,
) -> str:
    """Markdown overview block to embed in the auto-PR body, ahead
    of the raw run log. Returns an empty string when there's nothing
    to surface (caller can skip emitting the section).

    `uncategorised` (canonical keywords mapping to no research theme) and
    `link_rewrites` (the link fields the sync normalised this run) are the
    two signals #796 lifts out of the scheduled job's stderr into a
    "Review flags" section, each rendered only when non-empty."""
    new = diff["new"]
    upd = diff["updates"]
    rm = diff["removed"]
    photos = diff["photos_changed_paths"]

    def _label(field: str) -> str:
        return _FIELD_LABELS.get(field, field)

    flag_keywords = sorted(uncategorised or [], key=str.lower)
    # A returning submitter's response can be processed by more than one
    # row, so the same rewrite can land in LINK_REWRITES twice. Dedupe
    # while keeping first-seen order.
    flag_rewrites: list[dict] = []
    seen_rw: set[tuple] = set()
    for r in link_rewrites or []:
        key = (r["name"], r["field"], r["before"], r["after"])
        if key in seen_rw:
            continue
        seen_rw.add(key)
        flag_rewrites.append(r)

    has_changes = bool(new or upd or rm or photos)
    has_flags = bool(flag_keywords or flag_rewrites)
    if not (has_changes or has_flags):
        return ""

    lines: list[str] = []
    if has_changes:
        lines += ["## What changed", ""]

    if new:
        lines.append(f"### New members ({len(new)})")
        lines.append("")
        for m in new:
            name = m.get("name") or m.get("id")
            country = m.get("country") or ""
            pos = m.get("position") or ""
            aff = m.get("affiliation") or ""
            tail_parts = [x for x in [pos, aff] if x]
            tail = " @ ".join(tail_parts) if len(tail_parts) == 2 else " ".join(tail_parts)
            line = f"- **{name}**"
            if country:
                line += f" · {country}"
            if tail:
                line += f" · _{tail}_"
            lines.append(line)
        lines.append("")

    if upd:
        lines.append(f"### Updated members ({len(upd)})")
        lines.append("")
        for u in upd:
            if u["photo_only"]:
                lines.append(f"- **{u['name']}**: headshot replaced")
            elif u["both"]:
                fields = ", ".join(_label(f) for f in u["fields"])
                lines.append(f"- **{u['name']}**: {fields} + headshot")
            else:
                fields = ", ".join(_label(f) for f in u["fields"]) or "metadata"
                lines.append(f"- **{u['name']}**: {fields}")
        lines.append("")

    if rm:
        lines.append(f"### Removed members ({len(rm)})")
        lines.append("")
        for m in rm:
            name = m.get("name") or m.get("id")
            lines.append(f"- **{name}**")
        lines.append("")

    if photos:
        lines.append(f"### Headshot files updated ({len(photos)})")
        lines.append("")
        for p in photos:
            lines.append(f"- `{p}`")
        lines.append("")

    if has_flags:
        lines.append("## Review flags")
        lines.append("")
        if flag_keywords:
            lines.append(
                f"### Keywords with no theme (won't cluster) ({len(flag_keywords)})"
            )
            lines.append("")
            lines.append(
                "These canonical keywords map to no research theme, so the members "
                "carrying them fall out of the theme filter chips on the directory. "
                "Add each under `themes` in `data/keyword-aliases.json` to fix it. "
                "A suggested theme (the closest already-mapped keyword) is shown "
                "where one is near enough; confirm or override it."
            )
            lines.append("")
            theme_of_now = load_keyword_themes()
            for k in flag_keywords:
                hint = suggest_theme(k, theme_of_now)
                if hint:
                    lines.append(
                        f"- {k} → suggested theme: **{hint[0]}** "
                        f"(nearest: _{hint[1]}_)"
                    )
                else:
                    lines.append(f"- {k} → no close theme; pick one")
            lines.append("")
        if flag_rewrites:
            lines.append(f"### Link fields rewritten ({len(flag_rewrites)})")
            lines.append("")
            lines.append(
                "The sync normalised these link fields. Confirm each rewrite points "
                "at the destination the member intended."
            )
            lines.append("")
            for r in flag_rewrites:
                lines.append(
                    f"- **{r['name']}** · {_label(r['field'])}: "
                    f"`{r['before']}` → `{r['after']}`"
                )
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ──────────────────────────── main ────────────────────────────


def apply_overrides(members: list[dict]) -> None:
    """Apply the hand corrections in data/bios-overrides.json (#1219).

    The Google Sheet is authoritative for member data, so an edit made only
    in bios.json is silently reverted by the next sync (this is how the
    'profesionnal' typo fix was lost). Corrections that cannot be made in
    the Sheet itself live in the overrides file and are re-applied after
    every fetch, so they survive any number of syncs. Each entry is a plain
    string substitution on one field of one member. A fix whose `from` text
    no longer occurs (the submitter corrected it upstream) prints a prune
    hint rather than failing, so the overrides file stays a short list of
    live corrections instead of accumulating fossils.
    """
    path = ROOT / "data" / "bios-overrides.json"
    if not path.exists():
        return
    fixes = json.loads(path.read_text()).get("text_fixes", [])
    if not fixes:
        return
    by_id = {m["id"]: m for m in members}
    print("Applying hand corrections from data/bios-overrides.json …")
    for fix in fixes:
        m = by_id.get(fix["id"])
        if m is None:
            print(f"  ! override for unknown member {fix['id']!r} — prune it?",
                  file=sys.stderr)
            continue
        field, old, new = fix["field"], fix["from"], fix["to"]
        text = m.get(field)
        if not isinstance(text, str) or old not in text:
            print(f"  · {fix['id']}.{field}: {old!r} not present (fixed at "
                  "source?) — override can be pruned.")
            continue
        m[field] = text.replace(old, new)
        print(f"  · {fix['id']}.{field}: {old!r} → {new!r}")


def enrich_keywords(merged: list, bios_data: dict) -> set[str]:
    """Resolve every member's raw keywords and write the derived fields.

    Mutates `merged` in place (each member gains `canonical_keywords` and
    `themes`) and `bios_data` (the three aggregates the directory's filter
    rows read), and returns the canonical keywords that resolved to no theme,
    which main() hands to _emit_pr_summary. Pure apart from the vocabulary
    files it loads, which is what lets --dry-run replay it over the committed
    bios.json without a fetch (#1715).

    Lifted out of main() unchanged rather than copied, so the dry run and the
    real sync can never disagree about what a keyword resolves to.
    """
    # Resolve raw keywords through the alias map + sentence-case +
    # acronym word-walk normaliser. Emits a `canonical_keywords` field
    # per bio and a top-level `keyword_aggregate` array sorted by use
    # count (ties broken alphabetically). Phase 3 (filter chips on
    # /people.html) will read the aggregate to seed the chip list.
    print()
    print("Normalising keywords against data/keyword-aliases.json …")
    acronyms, alias_map, spelling_map = load_keyword_aliases()
    theme_of = load_keyword_themes()
    region_vocab = load_region_vocab()
    keyword_drops = load_keyword_drops()
    keyword_splits = load_keyword_splits()
    aggregate: dict[str, int] = {}
    theme_member_counts: dict[str, int] = {}  # theme → distinct members
    keyword_theme_map: dict[str, str] = {}    # canonical keyword → theme
    uncategorised: set[str] = set()
    dropped_regions: set[str] = set()         # region names typed as keywords
    dropped_wg_tags: set[str] = set()         # WG memberships typed as keywords
    dropped_places: set[str] = set()          # country names typed as keywords
    split_keywords: set[str] = set()          # phrases expanded into their parts
    for m in merged:
        raw_kws = m.get("keywords") or []
        seen: dict[str, str] = {}  # lowercase canonical → canonical
        for raw in raw_kws:
            canon = normalise_keyword(raw, acronyms, alias_map, spelling_map)
            if not canon:
                continue
            # A submission that is a phrase rather than a tag becomes the
            # several canonical keywords it actually names (#1701). Expanded
            # here so everything below, the drops included, sees ordinary
            # keywords rather than a special case.
            parts = keyword_splits.get(canon.lower())
            if parts:
                split_keywords.add(canon)
            for kw in (parts or [canon]):
                # Geography belongs to the regions facet, not the topical
                # keyword pills. A region name typed into the keyword box
                # (e.g. "The Americas") would otherwise stand alone in the
                # theme filter; drop it here so the controlled regions
                # vocabulary owns that axis.
                if kw.lower() in region_vocab:
                    dropped_regions.add(kw)
                    continue
                # Country and sub-region names are the same problem one level
                # finer, and `regions` only holds the eight broad ones, so
                # they carry their own list (#1701).
                if kw.lower() in keyword_drops:
                    dropped_places.add(kw)
                    continue
                # Working-group memberships typed into the keywords field
                # ("Wg1", "WG 2") already have a home in the wgs facet and
                # would never cluster into a research theme; drop them the
                # same way (#1308).
                if re.fullmatch(r"wg\s*\d+", kw.lower()):
                    dropped_wg_tags.add(kw)
                    continue
                key = kw.lower()
                if key in seen:
                    continue
                seen[key] = kw
        # Stable order: alphabetical by canonical display form.
        canonicals = sorted(seen.values(), key=str.lower)
        if canonicals:
            m["canonical_keywords"] = canonicals
        else:
            m.pop("canonical_keywords", None)
        for c in canonicals:
            aggregate[c] = aggregate.get(c, 0) + 1
            theme = theme_of.get(c.lower())
            if theme:
                keyword_theme_map[c] = theme
            else:
                uncategorised.add(c)
            # Surface keywords that read as a phrase rather than a tag, so
            # the maintainer can curate them into a tighter form (or an
            # alias) instead of shipping a sentence-length singleton. Non-
            # fatal hint only; nothing is auto-edited.
            if len(c) > 40 or "(" in c or ")" in c:
                print(
                    f"  ! long/parenthetical keyword on {m.get('name', '?')}: "
                    f"{c!r} — consider tightening it or adding an alias in "
                    "data/keyword-aliases.json.",
                    file=sys.stderr,
                )
        # Per-bio research themes (distinct, alphabetical). Drives the
        # cluster filter on /people.html; cards keep the specific keywords.
        member_themes = sorted({theme_of[c.lower()] for c in canonicals if c.lower() in theme_of})
        if member_themes:
            m["themes"] = member_themes
            for t in member_themes:
                theme_member_counts[t] = theme_member_counts.get(t, 0) + 1
        else:
            m.pop("themes", None)
    print(f"  {len(aggregate)} unique canonical keywords across "
          f"{sum(aggregate.values())} bio mentions.")
    if dropped_regions:
        print(
            "  · dropped region names from keywords (they belong to the "
            "regions facet): " + ", ".join(sorted(dropped_regions))
        )
    if dropped_wg_tags:
        print(
            "  · dropped working-group tags from keywords (they belong to "
            "the wgs facet): " + ", ".join(sorted(dropped_wg_tags))
        )
    if dropped_places:
        print(
            "  · dropped place names from keywords (they belong to the "
            "regions facet): " + ", ".join(sorted(dropped_places))
        )
    if split_keywords:
        print(
            "  · split phrase keywords into their parts: "
            + ", ".join(sorted(split_keywords))
        )
    if uncategorised:
        # Keep the taxonomy complete: any canonical keyword without a theme
        # won't cluster and its card pill renders as display-only.
        print(
            "  ! keywords with no theme (add under `themes` in "
            "data/keyword-aliases.json): " + ", ".join(sorted(uncategorised)),
            file=sys.stderr,
        )
    flag_alias_candidates(aggregate, alias_map)
    bios_data["keyword_aggregate"] = sorted(
        ({"keyword": k, "count": v} for k, v in aggregate.items()),
        key=lambda e: (-e["count"], e["keyword"].lower()),
    )
    # Theme aggregate (distinct-member count per theme, sorted desc) drives
    # the research-theme filter chip row; keyword_theme_map lets the card
    # pills resolve their theme for the click-to-filter affordance.
    bios_data["theme_aggregate"] = sorted(
        ({"theme": t, "count": n} for t, n in theme_member_counts.items()),
        key=lambda e: (-e["count"], e["theme"].lower()),
    )
    bios_data["keyword_theme_map"] = {k: keyword_theme_map[k] for k in sorted(keyword_theme_map)}
    return uncategorised


def main() -> None:
    config = json.loads(CONFIG.read_text())
    csv_url = (config.get("sheet", {}).get("csv_url") or "").strip()
    if not csv_url:
        print("bios-source.json has no csv_url set — exiting cleanly.")
        print("See docs/bios-setup.md to wire up the Google Form.")
        return

    cols = config.get("columns", {})
    bios_data = json.loads(BIOS.read_text())
    old_members = bios_data.get("members", [])
    # We pass the full prior member list to merge(), not just
    # source == "seed". The seed/form distinction is informational
    # only — for merge purposes, "the prior state of the directory"
    # is what we want to preserve roles, position, and email-match
    # identity against.
    #
    # Index by slug so row_to_member → download_photo can look up
    # the prior `photo_source_sha256` for each submitter in O(1) and
    # skip the PIL re-encode when the upstream photo bytes are
    # unchanged. See download_photo's docstring for the empty-PR
    # failure mode this guards against.
    old_by_id = {m["id"]: m for m in old_members}
    # Two more indexes, mirroring merge()'s email and name+country
    # collapse signals, so a name-collapse submitter's photo resolves to
    # its canonical slug + stored hash before download (see
    # resolve_prior_entry).
    old_by_email = {
        m["email"].lower(): m for m in old_members if m.get("email")
    }
    old_by_namekey: dict[tuple[str, str, str], dict] = {}
    for m in old_members:
        nk = name_key(m.get("name", ""))
        if nk:
            old_by_namekey[(nk[0], nk[1], country_key(m.get("country", "")))] = m

    # Fetch the sheet CSV
    print(f"Fetching {csv_url}")
    r = requests.get(csv_url, timeout=30)
    r.raise_for_status()
    text = r.content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    form_entries: list[dict] = []
    for raw_row in reader:
        # The CSV from Google Sheets uses the form question text as the
        # header. Trim whitespace from header keys.
        row = {(k or "").strip(): v for k, v in raw_row.items()}
        entry = row_to_member(
            row, cols, old_by_id, old_by_email, old_by_namekey,
        )
        if entry:
            form_entries.append(entry)

    merged = merge(old_members, form_entries)
    apply_overrides(merged)
    print(diff_summary(old_members, merged))

    # Make sure every headshot has a .webp sibling for the directory's
    # <picture> serving (#269). Idempotent; only writes missing/stale ones.
    _webp_n = ensure_people_webp()
    if _webp_n:
        print(f"Generated {_webp_n} new .webp headshot(s).")
    # Map-sized derivatives come after, so they encode from the fresh .webp.
    _map_n = ensure_map_avatars()
    if _map_n:
        print(f"Generated {_map_n} new map avatar(s).")

    uncategorised = enrich_keywords(merged, bios_data)

    # Research-region aggregate (distinct-member count per region). The
    # per-bio `regions` come from the optional Research-regions form field
    # (controlled vocabulary); this drives the region filter chip row,
    # which stays hidden until at least one member has opted in. Empty
    # region lists are dropped so the field stays absent for non-opt-ins.
    region_counts: dict[str, int] = {}
    for m in merged:
        regs = m.get("regions") or []
        if regs:
            for r in regs:
                region_counts[r] = region_counts.get(r, 0) + 1
        else:
            m.pop("regions", None)
        # STSM hosting (#760): a tri-state scalar from the optional Form
        # question. Drop the empty case so the field stays absent for
        # members who declined or never answered, like the region list.
        if not m.get("stsm_hosting"):
            m.pop("stsm_hosting", None)
    bios_data["region_aggregate"] = sorted(
        ({"region": r, "count": n} for r, n in region_counts.items()),
        key=lambda e: (-e["count"], e["region"].lower()),
    )

    # Standardise affiliation punctuation so the same employer doesn't read
    # three different ways across cards. Runs over every member (seed and
    # form) each sync, so it survives a re-read of the raw Sheet value.
    for m in merged:
        aff = m.get("affiliation")
        if aff:
            m["affiliation"] = normalise_affiliation(aff)

    # Substance check: did anything actually change?
    #
    # `generated_at` and `source.last_synced` advance to "now" on every
    # run, so if we wrote them unconditionally git would always see a
    # diff and the workflow's create-pull-request step would open an
    # otherwise-empty auto-PR every week. We only want a PR when the
    # member data or the configured source URLs have genuinely moved.
    #
    # Note for the photo-only-change case (#183): a respondent who
    # submits a fresh response to update only their headshot (the
    # workaround for the Google Forms file-upload-edit bug) is detected
    # via `photo_source_sha256`. download_photo computes the upstream
    # sha; row_to_member sets it on the form entry; merge propagates it
    # onto the existing record. The list-of-dicts comparison below then
    # sees the field differ and opens a PR. Pinned by
    # test_substance_check_catches_photo_only_change() in
    # scripts/test-sync-bios.py. If the sha propagation path is ever
    # refactored, that test will fail.
    new_source = {
        "type": "google_sheet",
        "csv_url": csv_url,
        "form_url": (config.get("form_url") or "").strip(),
    }
    existing_source = bios_data.get("source") or {}
    existing_source_meta = {
        k: existing_source.get(k) for k in ("type", "csv_url", "form_url")
    }

    members_changed = merged != old_members
    source_meta_changed = new_source != existing_source_meta
    data_changed = members_changed or source_meta_changed

    if not data_changed and not PHOTOS_CHANGED:
        print()
        print("No substantive changes — leaving data/bios.json untouched.")
        print(f"(Last sync recorded in file: "
              f"{existing_source.get('last_synced', 'unknown')}.)")
        return

    if not data_changed and PHOTOS_CHANGED:
        # Belt-and-braces alarm. With photo_source_sha256 propagating
        # correctly through merge(), this branch should never fire on a
        # genuine photo update: the new sha would flip members_changed.
        # If we land here, something has regressed in the sha
        # propagation path (download_photo -> row_to_member -> merge ->
        # comparison) and the auto-PR is about to ship binary diffs with
        # no data-level context. Print loud diagnostics so the maintainer
        # spots it on the PR's workflow log.
        print()
        print("WARNING: bios.json bytes unchanged, but headshot file(s) "
              "were rewritten on disk:")
        for p in PHOTOS_CHANGED:
            print(f"  ~ {p}")
        print("This is unexpected. The create-pull-request action below "
              "will commit them, but the data side of the diff is silent. "
              "Investigate whether photo_source_sha256 propagation has "
              "regressed (see scripts/test-sync-bios.py).")
        # Emit a minimal title + overview so the workflow still produces
        # a coherent PR header rather than falling back to the generic
        # one. classify_diff sees no new/updated/removed members, just
        # the photo paths, and render_pr_title routes that to the
        # "investigate" title.
        alarm_diff = classify_diff(old_members, merged, PHOTOS_CHANGED)
        _emit_pr_summary(alarm_diff, uncategorised, LINK_REWRITES)
        # Keep bios.json untouched: data genuinely didn't change. The
        # photo files on disk are already updated; the PR will reflect
        # them. We just want the log to scream rather than mislead.
        return

    # Substance changed: stamp timestamps and write.
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    bios_data["members"] = merged
    bios_data["generated_at"] = now
    bios_data["source"] = {**new_source, "last_synced": now}
    BIOS.write_text(json.dumps(bios_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if PHOTOS_CHANGED:
        # Surface the binary side of the diff for reviewers of the
        # auto-PR. The diff_summary already mentioned the affected
        # member(s) by id; this adds the file path(s) so a reviewer
        # doesn't have to guess which photos moved.
        print()
        print(f"Headshot file(s) updated on disk: {len(PHOTOS_CHANGED)}")
        for p in PHOTOS_CHANGED:
            print(f"  ~ {p}")

    # Compose the dynamic PR title + structured overview for the
    # workflow to consume. classify_diff is a pure function over the
    # final member lists; render_pr_title + render_pr_body_overview
    # turn its output into Markdown the create-pull-request action
    # can pick up via env-pointed files. Skipped silently when the
    # env vars aren't set (local runs).
    diff = classify_diff(old_members, merged, PHOTOS_CHANGED)
    _emit_pr_summary(diff, uncategorised, LINK_REWRITES)


def _emit_pr_summary(
    diff: dict,
    uncategorised: set[str] | list[str] | None = None,
    link_rewrites: list[dict] | None = None,
) -> None:
    """Write the dynamic PR title + structured overview to the paths
    pointed at by `SYNC_BIOS_PR_TITLE_PATH` + `SYNC_BIOS_PR_OVERVIEW_PATH`
    when those env vars are set. The workflow sets them; a local
    invocation leaves them unset and this is a no-op."""
    title_path = os.environ.get("SYNC_BIOS_PR_TITLE_PATH")
    overview_path = os.environ.get("SYNC_BIOS_PR_OVERVIEW_PATH")
    if title_path:
        Path(title_path).write_text(render_pr_title(diff) + "\n", encoding="utf-8")
    if overview_path:
        Path(overview_path).write_text(
            render_pr_body_overview(diff, uncategorised, link_rewrites),
            encoding="utf-8",
        )


def dry_run() -> int:
    """Replay the keyword enrichment over the committed bios.json and report.

    The sync runs daily, so a change to data/keyword-aliases.json is invisible
    until the next morning's auto-PR. Verifying four such changes in one day
    meant writing this replay by hand twice, and the two traps it caught would
    not have been visible by reading the file: the directory writes "Czechia"
    where COST writes "Czech Republic", so a plain membership test silently
    understated a figure aimed at an evaluator, and moving one keyword between
    themes turned out to remove a member from a theme rather than add one,
    because that keyword was her only route into it (#1715).

    Reads nothing from the network and writes nothing. The raw `keywords` on
    each committed member are the input, which is exactly what the sync feeds
    the enrichment after a fetch that changed nobody's answers.
    """
    bios_data = json.loads(BIOS.read_text(encoding="utf-8"))
    before = {m["id"]: m for m in bios_data.get("members", [])}
    members = copy.deepcopy(bios_data.get("members", []))
    enrich_keywords(members, {})

    moved_keywords, moved_themes = [], []
    for m in members:
        was = before.get(m["id"], {})
        if (was.get("canonical_keywords") or []) != (m.get("canonical_keywords") or []):
            moved_keywords.append((m.get("name", "?"),
                                   was.get("canonical_keywords") or [],
                                   m.get("canonical_keywords") or []))
        if set(was.get("themes") or []) != set(m.get("themes") or []):
            moved_themes.append((m.get("name", "?"),
                                 sorted(set(was.get("themes") or []) - set(m.get("themes") or [])),
                                 sorted(set(m.get("themes") or []) - set(was.get("themes") or []))))

    print()
    if not moved_keywords and not moved_themes:
        print("✓ nothing would change: the committed bios.json already matches "
              "the current taxonomy.")
        return 0

    if moved_keywords:
        print(f"Keywords that would move at the next sync ({len(moved_keywords)} member(s)):")
        for name, was, now in moved_keywords:
            for k in sorted(set(was) - set(now)):
                print(f"    {name}: -{k!r}")
            for k in sorted(set(now) - set(was)):
                print(f"    {name}: +{k!r}")
    if moved_themes:
        print()
        print(f"Research themes that would move ({len(moved_themes)} member(s)):")
        for name, lost, gained in moved_themes:
            # A member losing a theme is the line to read twice. It means a
            # keyword was that member's only route into it.
            mark = "  ← loses a theme" if lost else ""
            print(f"    {name}: -{lost} +{gained}{mark}")
    print()
    print("Nothing was written. Run without --dry-run inside the sync workflow "
          "to apply, or wait for the daily run.")
    return 0


if __name__ == "__main__":
    # --dry-run replays the keyword enrichment over the committed bios.json and
    # reports what would move, without a fetch and without writing. It exists
    # because the sync is daily, so a taxonomy edit is otherwise invisible until
    # the next morning (#1715).
    if "--dry-run" in sys.argv[1:]:
        sys.exit(dry_run())
    main()
