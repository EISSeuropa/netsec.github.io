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
       - Seed entries (source == "seed") are preserved unless overwritten
         by a form submission whose normalised email or slug matches.
       - Form entries are keyed by email when available, otherwise slug.
       - Duplicate form submissions: latest by timestamp wins.
  5. Writes data/bios.json with deterministic ordering.
  6. Prints a human-readable diff (added / updated / removed).

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
            dest = dest_no_ext.with_suffix(".jpg")
            img.save(dest, format="JPEG", quality=82, optimize=True)
        except Exception as e:
            print(f"  ! photo decode failed: {e}", file=sys.stderr)
            dest = dest_no_ext.with_suffix(".jpg")
            dest.write_bytes(data)
    else:
        dest = dest_no_ext.with_suffix(".jpg")
        dest.write_bytes(data)

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
        "orcid": (row.get(cols.get("orcid", ""), "") or "").strip(),
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


def merge(seeds: list[dict], form_entries: list[dict]) -> list[dict]:
    """Merge seed list with form list.
    - Seeds keyed by id (slug).
    - Form entries keyed by email if available, otherwise slug.
    - When a form entry matches a seed (by slug OR by email), the form
      data wins for content fields, but the seed's role data
      (roles, wg_leadership) is preserved unless the form provided one.
    """
    by_slug: dict[str, dict] = {s["id"]: dict(s) for s in seeds}
    by_email: dict[str, str] = {
        (s.get("email") or "").lower(): s["id"]
        for s in seeds if s.get("email")
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
        # Find matching seed
        target_id = None
        if entry["_email_key"] and entry["_email_key"] in by_email:
            target_id = by_email[entry["_email_key"]]
        elif entry["id"] in by_slug:
            target_id = entry["id"]

        if target_id:
            seed = by_slug[target_id]
            # Form data wins for content; preserve roles + wg_leadership unless form overrode
            for k in ("name", "country", "country_code", "affiliation", "position", "bio",
                       "keywords", "email", "website", "orcid",
                       "linkedin", "twitter", "bluesky", "mastodon"):
                if entry.get(k):
                    seed[k] = entry[k]
            if entry.get("photo"):
                seed["photo"] = entry["photo"]
            if entry.get("wgs"):
                # Union of seed and form WGs
                seed["wgs"] = sorted(set(seed.get("wgs", []) + entry["wgs"]))
            seed["source"] = "form"
        else:
            # New entry from form, no seed match
            by_slug[entry["id"]] = {k: v for k, v in entry.items() if not k.startswith("_")}

    # Final ordering: leadership first (preserve seed order), then alphabetical
    seed_order = {s["id"]: i for i, s in enumerate(seeds)}
    result = list(by_slug.values())
    result.sort(key=lambda m: (seed_order.get(m["id"], 10_000), m.get("name", "").lower()))

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
    seeds = [m for m in old_members if m.get("source") == "seed"]

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

    merged = merge(seeds, form_entries)
    print(diff_summary(old_members, merged))

    bios_data["members"] = merged
    bios_data["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    bios_data["source"] = {
        "type": "google_sheet",
        "csv_url": csv_url,
        "form_url": (config.get("form_url") or "").strip(),
        "last_synced": bios_data["generated_at"],
    }
    BIOS.write_text(json.dumps(bios_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
