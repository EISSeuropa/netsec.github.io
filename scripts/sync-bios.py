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

import csv
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

# ──────────────────────────── helpers ────────────────────────────


def norm_email(s: str) -> str:
    return (s or "").strip().lower()


def slugify(name: str) -> str:
    """Stable slug from a person's name. Strips diacritics, titles, and
    apostrophes BEFORE collapsing non-alphanumerics to hyphens, so that
    e.g. "Dr Silvia D'Amato" → "silvia-damato" (matches the existing
    seed id) rather than "silvia-d-amato"."""
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"^(Dr|Prof|Mr|Ms|Mrs)\.?\s+", "", s)
    s = s.lower()
    # Drop apostrophes / curly quotes / similar marks first — they
    # shouldn't introduce a hyphen between adjacent letters.
    s = re.sub(r"[‘’ʼ'`]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "member"


def name_key(name: str) -> tuple[str, str] | None:
    """Reduce a name to (first_token, last_token), lowercased and
    diacritic-stripped, dropping titles and any middle names / initials.

    Used as a fallback dedup signal in merge(): collapses cases where a
    member who already has a seed entry (e.g. "Dr John Helferich") fills
    in the public form with a slightly different name spelling (e.g.
    "Dr John N.T. Helferich"). slugify() would treat those two as
    different ids (john-helferich vs john-n-t-helferich), and the form
    submitter's Google account email isn't on the seed entry to bridge
    them — so without a third signal, the form submission creates a
    new alphabetical entry beside the seed one.

    Returns None when we can't extract both a first and a last token —
    the caller treats that as "no fallback match available".

    Conservative on purpose: only the *first* and the *last* token are
    used, so middle names, suffixes ("Jr"), and academic post-nominals
    ("PhD") don't affect the key. The matcher in merge() additionally
    requires the country to match, so two genuinely different members
    who happen to share first + last names won't collapse.
    """
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"^(Dr|Prof|Mr|Ms|Mrs)\.?\s+", "", s, flags=re.I)
    s = re.sub(r"[‘’ʼ'`]", "", s)
    # Tokenise on any non-letter so "N.T." becomes ["N", "T"] (and the
    # initials get dropped by the first/last selection below).
    tokens = [t.lower() for t in re.split(r"[^A-Za-z]+", s) if t]
    # Strip common post-nominal tokens that aren't really part of the name.
    POST_NOMINALS = {"phd", "jr", "sr", "ii", "iii", "iv", "esq"}
    # Strip nobiliary / patronymic particles too. Without this, "Jéssica
    # da Costa Pereira" keys as (jessica, pereira) while a bios.json entry
    # of "Jéssica da Costa" keys as (jessica, costa) and the two miss
    # each other. Dropping particles makes both reduce to (jessica,
    # pereira) / (jessica, costa) cleanly based on the actual surname
    # tokens. Conservative list — only particles that are reliably
    # connectors, not standalone names.
    PARTICLES = {
        "de", "del", "della", "di", "da", "das", "dos",
        "van", "von", "vom", "der", "den", "ter", "ten",
        "la", "le", "el", "al", "ibn", "bin", "bint",
        "zu", "auf", "af",
    }
    tokens = [t for t in tokens if t not in POST_NOMINALS and t not in PARTICLES]
    if len(tokens) < 2:
        return None
    return (tokens[0], tokens[-1])


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
    small ordered list drawn from {"mentor", "mentee"}:

      - "mentor"  the member is offering to mentor (a mid-career or
                  senior scholar open to mentoring early-career ones).
      - "mentee"  the member is looking for a mentor.

    Matching is tolerant substring matching against the option text, so
    light edits to the Form wording keep working. Distinct phrases keep
    the two directions apart even though both contain "mentor":
    "open to mentoring" / "as a mentor" -> mentor;
    "looking for a mentor" / "seeking a mentor" -> mentee. An empty or
    absent cell (the question is optional, and unconfigured columns read
    as "") yields []."""
    if not raw:
        return []
    s = str(raw).lower()
    out: list[str] = []
    if any(p in s for p in (
        "open to mentoring", "offer mentor", "offering mentor",
        "happy to mentor", "as a mentor", "provide mentor",
        "mentoring early",
    )):
        out.append("mentor")
    if any(p in s for p in (
        "looking for a mentor", "seeking a mentor", "find a mentor",
        "want a mentor", "need a mentor", "be mentored", "as a mentee",
    )):
        out.append("mentee")
    return out


def parse_keywords(raw: str) -> list[str]:
    if not raw:
        return []
    return [k.strip() for k in re.split(r"[,;]", raw) if k.strip()]


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

    for entry in doc.get("acronyms", []):
        if not isinstance(entry, str):
            continue
        lower = entry.lower()
        acronym_set.add(lower)
        # Each acronym also maps to its own canonical display, so a raw
        # "eu" or "EU" both resolve to the same key.
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


def row_to_member(
    row: dict,
    cols: dict,
    old_by_id: dict[str, dict] | None = None,
) -> dict | None:
    """Convert one CSV row dict to a bios.json member entry, or None if
    the row should be skipped.

    `old_by_id` is the prior bios.json members keyed by slug — passed
    in so download_photo can look up the prior photo_source_sha256
    and short-circuit the PIL re-encode when the upstream bytes
    haven't changed. Pass None and the photo will always be re-encoded
    (only relevant for tests / one-off scripted runs).
    """
    name = (row.get(cols["name"], "") or "").strip()
    consent = (row.get(cols["consent"], "") or "").strip().lower()
    if not name:
        return None
    # Strict: only publish if consent recorded
    if consent and not any(t in consent for t in ("yes", "agree", "✓", "consent", "true")):
        # Explicit non-consent — skip
        print(f"  · skipping {name!r}: no consent recorded", file=sys.stderr)
        return None

    slug = slugify(name)
    email = norm_email(row.get(cols.get("email", ""), ""))
    photo_url = (row.get(cols.get("photo", ""), "") or "").strip()
    photo_path: str | None = None
    photo_hash: str | None = None
    if photo_url:
        # Save under assets/images/people/<slug>. Look up the prior
        # hash so an unchanged photo doesn't get re-encoded.
        prior_hash = None
        if old_by_id is not None:
            prior = old_by_id.get(slug) or {}
            prior_hash = prior.get("photo_source_sha256") or None
        photo_path, photo_hash = download_photo(
            photo_url, PHOTO_DIR / slug, prior_hash=prior_hash,
        )

    out = {
        "id": slug,
        "name": name,
        "country": (row.get(cols.get("country", ""), "") or "").strip(),
        "country_code": "",  # filled by post-processing
        "affiliation": (row.get(cols.get("affiliation", ""), "") or "").strip(),
        "position": (row.get(cols.get("position", ""), "") or "").strip(),
        "roles": [],
        "wgs": parse_wgs(row.get(cols.get("wgs", ""), "")),
        "mentorship": parse_mentorship(row.get(cols.get("mentorship", ""), "")),
        "wg_leadership": {},
        "bio": (row.get(cols.get("bio", ""), "") or "").strip(),
        "keywords": parse_keywords(row.get(cols.get("keywords", ""), "")),
        "email": (row.get(cols.get("public_email", ""), "") or "").strip(),
        "website": (row.get(cols.get("website", ""), "") or "").strip(),
        "orcid": normalize_orcid(row.get(cols.get("orcid", ""), "")),
        "linkedin": (row.get(cols.get("linkedin", ""), "") or "").strip(),
        "twitter": (row.get(cols.get("twitter", ""), "") or "").strip(),
        "bluesky": (row.get(cols.get("bluesky", ""), "") or "").strip(),
        "mastodon": (row.get(cols.get("mastodon", ""), "") or "").strip(),
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
# entry here, we auto-assign a "MC member · <Country>" role and fill
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
    specific role* — set the role to "MC member · <Country>".

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
    member["roles"] = [f"MC member · {hit['country']}"]


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
                new_photo = entry.get("photo") or ""
                if new_photo:
                    src = ROOT / new_photo
                    if src.exists():
                        dest_ext = src.suffix
                        dest = PHOTO_DIR / f"{target_id}{dest_ext}"
                        # If the previous entry had a photo at a
                        # different extension, drop it — the form
                        # submission is authoritative for the visual.
                        for stale in PHOTO_DIR.glob(f"{target_id}.*"):
                            if stale != dest and stale.is_file():
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
            for k in ("name", "country", "country_code", "affiliation", "position", "bio",
                       "keywords", "email", "website", "orcid",
                       "linkedin", "twitter", "bluesky", "mastodon"):
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

    # Drop internal fields, fill country_code, attach MC role if applicable
    mc_lookup = load_mc_lookup()
    out = []
    for m in result:
        for k in list(m.keys()):
            if k.startswith("_"):
                del m[k]
        fill_country_code(m)
        apply_mc_role(m, mc_lookup)
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
_DERIVED_FIELDS = {"canonical_keywords", "country_code", "roles", "wg_leadership"}
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


def render_pr_body_overview(diff: dict) -> str:
    """Markdown overview block to embed in the auto-PR body, ahead
    of the raw run log. Returns an empty string when there's nothing
    to surface (caller can skip emitting the section)."""
    new = diff["new"]
    upd = diff["updates"]
    rm = diff["removed"]
    photos = diff["photos_changed_paths"]
    if not (new or upd or rm or photos):
        return ""

    def _label(field: str) -> str:
        return _FIELD_LABELS.get(field, field)

    lines: list[str] = ["## What changed", ""]

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

    return "\n".join(lines).rstrip() + "\n"


# ──────────────────────────── main ────────────────────────────


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
        entry = row_to_member(row, cols, old_by_id)
        if entry:
            form_entries.append(entry)

    merged = merge(old_members, form_entries)
    print(diff_summary(old_members, merged))

    # Resolve raw keywords through the alias map + sentence-case +
    # acronym word-walk normaliser. Emits a `canonical_keywords` field
    # per bio and a top-level `keyword_aggregate` array sorted by use
    # count (ties broken alphabetically). Phase 3 (filter chips on
    # /people.html) will read the aggregate to seed the chip list.
    print()
    print("Normalising keywords against data/keyword-aliases.json …")
    acronyms, alias_map, spelling_map = load_keyword_aliases()
    aggregate: dict[str, int] = {}
    for m in merged:
        raw_kws = m.get("keywords") or []
        seen: dict[str, str] = {}  # lowercase canonical → canonical
        for raw in raw_kws:
            canon = normalise_keyword(raw, acronyms, alias_map, spelling_map)
            if not canon:
                continue
            key = canon.lower()
            if key in seen:
                continue
            seen[key] = canon
        # Stable order: alphabetical by canonical display form.
        canonicals = sorted(seen.values(), key=str.lower)
        if canonicals:
            m["canonical_keywords"] = canonicals
        else:
            m.pop("canonical_keywords", None)
        for c in canonicals:
            aggregate[c] = aggregate.get(c, 0) + 1
    print(f"  {len(aggregate)} unique canonical keywords across "
          f"{sum(aggregate.values())} bio mentions.")
    flag_alias_candidates(aggregate, alias_map)
    bios_data["keyword_aggregate"] = sorted(
        ({"keyword": k, "count": v} for k, v in aggregate.items()),
        key=lambda e: (-e["count"], e["keyword"].lower()),
    )

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
        _emit_pr_summary(alarm_diff)
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
    _emit_pr_summary(diff)


def _emit_pr_summary(diff: dict) -> None:
    """Write the dynamic PR title + structured overview to the paths
    pointed at by `SYNC_BIOS_PR_TITLE_PATH` + `SYNC_BIOS_PR_OVERVIEW_PATH`
    when those env vars are set. The workflow sets them; a local
    invocation leaves them unset and this is a no-op."""
    title_path = os.environ.get("SYNC_BIOS_PR_TITLE_PATH")
    overview_path = os.environ.get("SYNC_BIOS_PR_OVERVIEW_PATH")
    if title_path:
        Path(title_path).write_text(render_pr_title(diff) + "\n", encoding="utf-8")
    if overview_path:
        Path(overview_path).write_text(render_pr_body_overview(diff), encoding="utf-8")


if __name__ == "__main__":
    main()
