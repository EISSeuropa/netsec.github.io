#!/usr/bin/env python3
"""
Sync helper: refresh data sourced from
https://www.cost.eu/actions/CA24154/

Three things kept in step with cost.eu:

  1. WG_MAP in index.html
     Parsed from cost.eu's Membership table — the {normalised-name → [WGs]}
     dictionary that drives the colour-coded WG chips next to people's
     names throughout the site.

  2. Per-bio `wgs` field in data/bios.json
     Same Membership-table parse: for each bio entry whose name
     matches a row on cost.eu, the `wgs` list is overwritten with
     cost.eu's value. cost.eu is the authoritative source for
     FORMAL WG membership; the Google Form's "Working Group
     memberships" field is the seed when a bio first lands, and on
     subsequent weekly syncs cost.eu wins. Entries not present on
     cost.eu (community members in the directory who aren't on
     the MC, or seed entries for leaders who haven't appeared
     in the Membership table yet) are left untouched. The rule
     is restated in docs/bios-setup.md for respondents.

  3. Leadership roles in data/bios.json
     Parsed from cost.eu's Leadership and Additional-Roles tables —
     when the Action Chair, Grant Awarding Coordinator, WG Lead, etc.
     change, the change propagates here. Each leadership role is
     enforced to have exactly one current holder; previous holders
     keep their seed entry (and bio data) but lose the role tag.

Usage:
    python3 scripts/sync-cost.py

Run from the repo root. Requires: requests, beautifulsoup4.
"""
import json, re, sys, unicodedata
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("Install deps: pip install requests beautifulsoup4")

URL = "https://www.cost.eu/actions/CA24154/"
ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
BIOS = ROOT / "data" / "bios.json"


# ─── name helpers ───────────────────────────────────────────────────

def norm(name: str) -> str:
    """Normalised display name (no salutation, no diacritics, lower case)."""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"^(Dr|Prof|Mr|Ms|Mrs)\.?\s+", "", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def slugify(name: str) -> str:
    """Stable slug from a person's name — must match scripts/sync-bios.py."""
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"^(Dr|Prof|Mr|Ms|Mrs)\.?\s+", "", s)
    s = s.lower()
    s = re.sub(r"[‘’ʼ'`]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "member"


_TITLE_TOKENS = {"Dr", "Dr.", "Prof", "Prof.", "Mr", "Mr.", "Ms", "Ms.", "Mrs", "Mrs."}


def titlecase_name(name: str) -> str:
    """Convert cost.eu's "Dr Moritz WEISS" style to "Dr Moritz Weiss"."""
    out = []
    for p in name.split():
        if p in _TITLE_TOKENS:
            out.append(p)
        elif len(p) > 1 and p.isupper():
            out.append(p.capitalize())
        else:
            out.append(p)
    return " ".join(out)


# ─── WG_MAP sync (Membership table) ─────────────────────────────────

def fetch_wg_map(bs: BeautifulSoup) -> dict:
    out: dict[str, list[int]] = {}
    for tr in bs.find_all("tr"):
        cells = [" ".join(c.stripped_strings) for c in tr.find_all(["td", "th"])]
        if len(cells) >= 3 and re.search(r"WG\s*\d", cells[1] or ""):
            k = norm(cells[0])
            if not k or k.isdigit() or k == "name":
                continue
            out[k] = sorted({int(d) for d in re.findall(r"WG\s*(\d)", cells[1])})
    return dict(sorted(out.items()))


def rewrite_wg_map(new_map: dict) -> dict:
    html = INDEX.read_text(encoding="utf-8")
    m = re.search(r"const WG_MAP = (\{.*?\});", html, re.S)
    if not m:
        raise SystemExit("Could not find WG_MAP literal in index.html")
    old_map = json.loads(m.group(1))
    new_json = json.dumps(new_map, ensure_ascii=False)
    new_html = html[:m.start()] + f"const WG_MAP = {new_json};" + html[m.end():]
    INDEX.write_text(new_html, encoding="utf-8")
    return old_map


def report_wg(old: dict, new: dict) -> list[str]:
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = sorted(k for k in (set(old) & set(new)) if old[k] != new[k])
    lines = [f"WG_MAP: {len(new)} members (was {len(old)})"]
    if added:   lines.append("  Added:");   lines += [f"    + {k}: WG {new[k]}" for k in added]
    if removed: lines.append("  Removed:"); lines += [f"    - {k}: WG {old[k]}" for k in removed]
    if changed: lines.append("  Changed:"); lines += [f"    ~ {k}: {old[k]} -> {new[k]}" for k in changed]
    if not (added or removed or changed):
        lines.append("  (no changes)")
    return lines


# ─── Per-bio WG sync (cost.eu Membership → data/bios.json) ─────────

def apply_wgs_to_bios(new_map: dict[str, list[int]]) -> list[str]:
    """Propagate cost.eu's per-member WG list into data/bios.json.

    For each bio entry whose `name` normalises to a key in `new_map`,
    overwrite `wgs` with cost.eu's list. Entries not present on
    cost.eu (a non-MC community member listed in the directory, or a
    seed entry for a leader who hasn't appeared in the Membership
    table yet) are left untouched.

    The rule, documented in docs/bios-setup.md: cost.eu is the
    authoritative source for FORMAL WG membership. The Google Form's
    "Working Group memberships" field is the seed when a bio first
    lands; on subsequent weekly syncs, cost.eu wins. Respondents who
    want to surface an informal WG affiliation that cost.eu hasn't
    recorded should write it into their bio prose rather than the
    structured field.

    Returns diff lines for the sync report. No-ops idempotently when
    every entry already matches cost.eu."""
    if not BIOS.exists():
        return ["Per-bio WGs: data/bios.json not present, skipped."]

    data = json.loads(BIOS.read_text(encoding="utf-8"))
    members: list[dict] = data.get("members", [])

    diffs: list[str] = []
    matched = 0
    for m in members:
        name = m.get("name") or ""
        key = norm(name)
        if not key or key not in new_map:
            continue
        matched += 1
        current = sorted(m.get("wgs") or [])
        target = sorted(new_map[key])
        if current == target:
            continue
        m["wgs"] = target
        diffs.append(f"  ~ {name}: {current} -> {target}")

    out_lines = [
        f"Per-bio WGs: {matched} bios matched on cost.eu's Membership table"
    ]
    if diffs:
        out_lines.extend(diffs)
        BIOS.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    else:
        out_lines.append("  (no changes)")
    return out_lines


# ─── Leadership sync (Leadership + Additional Roles tables) ────────

_ROLE_LABEL_RE = re.compile(
    # cost.eu's Leadership table emits malformed HTML (a </div> closing
    # what should be a </td>), which breaks BeautifulSoup's table parse.
    # Regex over the raw HTML instead — find every <td>{role}</(td|div)>
    # whose text ends in one of the known leadership suffixes.
    r"<td[^>]*>([A-Z][A-Za-z0-9 ./()\-]+"
    r"(?:Chair|Coordinator|Co-Lead|Co-lead|Leader|Representative))"
    r"</(?:td|div)>"
)
_H4_RE = re.compile(r"<h4[^>]*>(.*?)</h4>", re.S)
_SPAN_RE = re.compile(r"<span[^>]*>([^<]+)</span>")


def _unescape_html(s: str) -> str:
    """Decode the small set of HTML entities cost.eu emits in names."""
    return (s.replace("&#039;", "'").replace("&apos;", "'")
              .replace("&amp;", "&").replace("&quot;", '"'))


def extract_leadership(html: str) -> list[tuple[str, str]]:
    """Pull (role, name) pairs from the cost.eu Action page.

    For each <td>{ROLE}</td-or-div> cell that ends with a leadership
    suffix (Chair, Coordinator, Leader, Representative, Co-Lead), the
    leader's name lives in the next <h4>…</h4> as a sequence of
    <span>-wrapped name parts (Dr / First / Last). Joining the span
    text gives the displayable name."""
    pairs: list[tuple[str, str]] = []
    seen = set()
    for m in _ROLE_LABEL_RE.finditer(html):
        role = m.group(1).strip()
        h = _H4_RE.search(html, m.end())
        if not h:
            continue
        spans = _SPAN_RE.findall(h.group(1))
        name = re.sub(r"\s+", " ", " ".join(s.strip() for s in spans if s.strip())).strip()
        name = _unescape_html(name)
        if not name:
            continue
        key = (role, name)
        if key in seen:
            continue
        seen.add(key)
        pairs.append((role, name))
    return pairs


def _make_seed_entry(slug: str, name: str) -> dict:
    """Skeleton seed entry for a new leader that cost.eu just appointed.
    Their personal details (photo, bio, affiliation) get filled in when
    they submit the Google Form — until then the card renders with an
    initials avatar and an empty bio placeholder."""
    return {
        "id": slug,
        "name": name,
        "country": "",
        "country_code": "",
        "affiliation": "",
        "position": "",
        "roles": [],
        "wgs": [],
        "wg_leadership": {},
        "bio": "",
        "keywords": [],
        "email": "",
        "website": "",
        "orcid": "",
        "linkedin": "",
        "twitter": "",
        "bluesky": "",
        "mastodon": "",
        "photo": "",
        "source": "seed",
    }


def apply_leadership(leadership: list[tuple[str, str]]) -> list[str]:
    """Mutate data/bios.json so each leadership role from cost.eu is
    held by exactly one person there. Only touches `source == "seed"`
    entries — form submissions are left alone. Returns diff lines."""
    if not BIOS.exists():
        return ["Leadership: data/bios.json not present, skipped."]

    data = json.loads(BIOS.read_text(encoding="utf-8"))
    members: list[dict] = data.get("members", [])
    by_slug: dict[str, dict] = {m["id"]: m for m in members}

    # Build the desired state: each role → slug who should hold it.
    desired: dict[str, str] = {}
    diffs: list[str] = []
    for role, raw_name in leadership:
        name = titlecase_name(raw_name)
        slug = slugify(name)
        desired[role] = slug
        if slug not in by_slug:
            entry = _make_seed_entry(slug, name)
            members.append(entry)
            by_slug[slug] = entry
            diffs.append(f"  + new seed: {name} (role: {role})")

    leadership_roles = set(desired.keys())

    # Reconcile roles on every seed entry.
    for m in members:
        if m.get("source") != "seed":
            continue
        current = list(m.get("roles") or [])
        kept: list[str] = []
        # Remove leadership roles that no longer point to this person.
        for r in current:
            if r in leadership_roles and desired.get(r) != m["id"]:
                diffs.append(f"  - {m['name']}: -{r!s}")
                continue
            kept.append(r)
        # Add leadership roles that now point to this person and that
        # they don't yet carry.
        for role, slug in desired.items():
            if slug == m["id"] and role not in kept:
                kept.append(role)
                diffs.append(f"  + {m['name']}: +{role!s}")
        if kept != current:
            m["roles"] = kept

    out_lines = [f"Leadership: {len(leadership)} roles on cost.eu"]
    if diffs:
        out_lines.extend(diffs)
        BIOS.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    else:
        out_lines.append("  (no changes)")
    return out_lines


# ─── main ───────────────────────────────────────────────────────────

def main() -> None:
    r = requests.get(URL, headers={"User-Agent": "netsec-sync/1.0"}, timeout=30)
    r.raise_for_status()
    bs = BeautifulSoup(r.text, "html.parser")

    # 1) WG_MAP — uses the parsed DOM (Membership table is well-formed).
    new_map = fetch_wg_map(bs)
    old_map = rewrite_wg_map(new_map)
    for line in report_wg(old_map, new_map):
        print(line)

    # 2) Per-bio WGs → data/bios.json. Uses the same `new_map` that
    #    drove the home-page WG_MAP refresh, so the two surfaces stay
    #    in lockstep against cost.eu's formal record.
    print()
    for line in apply_wgs_to_bios(new_map):
        print(line)

    # 3) Leadership → data/bios.json — uses raw HTML because cost.eu's
    #    Leadership table contains a malformed </div> closing tag that
    #    fools BeautifulSoup's table parser.
    leadership = extract_leadership(r.text)
    print()
    for line in apply_leadership(leadership):
        print(line)


if __name__ == "__main__":
    main()
