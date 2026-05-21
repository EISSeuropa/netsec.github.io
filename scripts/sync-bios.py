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


def parse_keywords(raw: str) -> list[str]:
    if not raw:
        return []
    return [k.strip() for k in re.split(r"[,;]", raw) if k.strip()]


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


def download_photo(url: str, dest_no_ext: Path) -> str | None:
    """Download a photo, optimise if Pillow available, return final path
    (relative to ROOT) or None on failure."""
    if not url:
        return None
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
        return None

    # Build the bytes we *would* write, then only touch disk if they
    # differ from what's already there. Without this, every weekly
    # sync re-encodes every headshot and emits subtly different JPEG
    # bytes (libjpeg quantisation is not bit-stable across PIL runs),
    # which dirties the working tree even when no submitter has
    # actually changed their photo — and triggers an otherwise-empty
    # auto-PR.
    dest = dest_no_ext.with_suffix(".jpg")
    out_bytes: bytes | None = None

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

    if not (dest.exists() and dest.read_bytes() == out_bytes):
        dest.write_bytes(out_bytes)

    return str(dest.relative_to(ROOT)).replace(os.sep, "/")


def row_to_member(row: dict, cols: dict) -> dict | None:
    """Convert one CSV row dict to a bios.json member entry, or None if
    the row should be skipped."""
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
    photo_path = None
    if photo_url:
        # Save under assets/images/people/<slug>
        photo_path = download_photo(photo_url, PHOTO_DIR / slug)

    return {
        "id": slug,
        "name": name,
        "country": (row.get(cols.get("country", ""), "") or "").strip(),
        "country_code": "",  # filled by post-processing
        "affiliation": (row.get(cols.get("affiliation", ""), "") or "").strip(),
        "position": (row.get(cols.get("position", ""), "") or "").strip(),
        "roles": [],
        "wgs": parse_wgs(row.get(cols.get("wgs", ""), "")),
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
    - Form entries are keyed by email if available, otherwise slug.
    - When a form entry matches a prior entry (by slug OR by email),
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
        # Find matching prior entry by email first, then slug.
        target_id = None
        if entry["_email_key"] and entry["_email_key"] in by_email:
            target_id = by_email[entry["_email_key"]]
        elif entry["id"] in by_slug:
            target_id = entry["id"]

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
        entry = row_to_member(row, cols)
        if entry:
            form_entries.append(entry)

    merged = merge(old_members, form_entries)
    print(diff_summary(old_members, merged))

    # Substance check: did anything actually change?
    #
    # `generated_at` and `source.last_synced` advance to "now" on every
    # run, so if we wrote them unconditionally git would always see a
    # diff and the workflow's create-pull-request step would open an
    # otherwise-empty auto-PR every week. We only want a PR when the
    # member data or the configured source URLs have genuinely moved.
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

    if not members_changed and not source_meta_changed:
        print()
        print("No substantive changes — leaving data/bios.json untouched.")
        print(f"(Last sync recorded in file: "
              f"{existing_source.get('last_synced', 'unknown')}.)")
        return

    # Substance changed: stamp timestamps and write.
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    bios_data["members"] = merged
    bios_data["generated_at"] = now
    bios_data["source"] = {**new_source, "last_synced": now}
    BIOS.write_text(json.dumps(bios_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
