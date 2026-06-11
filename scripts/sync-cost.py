#!/usr/bin/env python3
"""
Sync helper: refresh data sourced from
https://www.cost.eu/actions/CA24154/

Five things kept in step with cost.eu:

  1. WG_MAP in index.html
     Parsed from cost.eu's Membership table — the {normalised-name → [WGs]}
     dictionary that drives the colour-coded WG chips next to people's
     names throughout the site.

  2. Per-bio `wgs` field in data/bios.json
     Same Membership-table parse, reconciled per WG rather than
     overwritten (#236): a WG added on cost.eu after the member's
     last form change is applied; a WG the member's newer form
     submission dropped is held and flagged; a WG on the form that
     cost.eu has not published yet is kept and flagged as pending
     catch-up. Observation clocks live in data/cost-wg-state.json.
     The home-page WG_MAP and data/wg.json consume the reconciled
     result, so every chip surface shows the same sets. Entries not
     present on cost.eu are left untouched. The respondent-facing
     rule is restated in docs/bios-setup.md.

  3. Leadership roles in data/bios.json
     Parsed from cost.eu's Leadership and Additional-Roles tables —
     when the Action Chair, Grant Awarding Coordinator, WG Lead, etc.
     change, the change propagates here. Each leadership role is
     enforced to have exactly one current holder; previous holders
     keep their seed entry (and bio data) but lose the role tag.

  4. data/wg.json
     The per-Working-Group view: for each of the four WGs, its lead and
     co-lead (read from each bio's `wg_leadership`, set in step 3),
     its directory members (from the Membership map, step 1), and a
     count of members with no bio yet. Titles and the colour palette
     are config (WG_META). The Working Groups page renders from this.
     Regenerated every run, never hand-edited.

  5. data/mc-members.json + visible statistics
     The Management Committee roster (name, country, ISO code per rep),
     regenerated from cost.eu's MC table, plus the MC-count and
     country-count literals on the About page and press kit (marked
     with data-cost-stat spans, all locales). The hand-authored MC
     country grid on about.html is drift-CHECKED against the roster
     but never rewritten (curated markup, human applies the fix).

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
# The home-page WG_MAP is locale-independent data (lowercased name →
# group numbers), embedded in every locale's index so each renders the
# same WG chips. All three must be rewritten together, or the FR/DE
# copies drift behind cost.eu every sync (the bug fixed in this commit).
INDEX = ROOT / "index.html"
INDEX_LOCALES = [ROOT / "index.html", ROOT / "index.fr.html", ROOT / "index.de.html"]
BIOS = ROOT / "data" / "bios.json"


# ─── name helpers ───────────────────────────────────────────────────

def norm(name: str) -> str:
    """Normalised display name (no salutation, no diacritics, lower case)."""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"^(Dr|Prof|Mr|Mrs|Ms|Mx)\.?\s+", "", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def slugify(name: str) -> str:
    """Stable slug from a person's name — must match scripts/sync-bios.py."""
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"^(Dr|Prof|Mr|Mrs|Ms|Mx)\.?\s+", "", s)
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
    """Rewrite the WG_MAP literal in every locale's index. The map is
    locale-independent data, so all three carry the same value; writing
    only index.html (the old behaviour) left index.fr/de.html drifting
    behind cost.eu. Returns the previous map from the EN copy for the
    change report."""
    new_json = json.dumps(new_map, ensure_ascii=False)
    old_map: dict = {}
    for path in INDEX_LOCALES:
        html = path.read_text(encoding="utf-8")
        m = re.search(r"const WG_MAP = (\{.*?\});", html, re.S)
        if not m:
            raise SystemExit(f"Could not find WG_MAP literal in {path.name}")
        if path == INDEX:  # report against the authoritative EN copy
            old_map = json.loads(m.group(1))
        new_html = html[:m.start()] + f"const WG_MAP = {new_json};" + html[m.end():]
        path.write_text(new_html, encoding="utf-8")
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

WG_STATE = ROOT / "data" / "cost-wg-state.json"


def _load_wg_state() -> dict:
    if WG_STATE.exists():
        return json.loads(WG_STATE.read_text(encoding="utf-8"))
    return {"_documentation": (
        "Observation clocks for the per-bio Working Group reconciliation "
        "in scripts/sync-cost.py. Per member (normalised name): the WG "
        "set last seen on cost.eu with the date each WG first appeared "
        "there, and the member's form-side WG set with the date it last "
        "changed. Neither source carries decision dates, so recency is "
        "judged on when each change was OBSERVED by the weekly sync. "
        "Generated file, do not edit by hand; deleting it resets the "
        "clocks to the next sync run (additions then win, the safe "
        "direction)."), "members": {}}


def reconcile_wgs(new_map: dict[str, list[int]], today: str) -> tuple:
    """Per-WG additive reconciliation between the Google Form's WG sets
    (data/bios.json `wgs`) and cost.eu's formal record (`new_map`).

    Members add WGs far more often than they remove them, and cost.eu
    can lag a member's form submission by weeks, so neither source
    simply wins (issue #236, Gap A). Per matched member and per WG:

      * on cost.eu but not the form: applied when cost.eu's entry was
        observed AFTER the member's last form change (a formal addition
        the member never re-submitted about); held and flagged when the
        member's NEWER form submission omitted it (a deliberate removal
        only a human should overrule).
      * on the form but not cost.eu: kept and flagged as pending
        catch-up. Under the additive prior this is almost always a real
        addition the formal record has not published yet.

    Returns (report lines, effective {norm-name: wgs} map). The
    effective map carries each matched member's post-merge set so the
    home-page WG_MAP and data/wg.json can render the same chips the
    directory shows. Entries not on cost.eu are left untouched, same
    as before."""
    if not BIOS.exists():
        return (["Per-bio WGs: data/bios.json not present, skipped."],
                dict(new_map))

    data = json.loads(BIOS.read_text(encoding="utf-8"))
    members: list[dict] = data.get("members", [])
    state = _load_wg_state()
    s_members: dict = state.setdefault("members", {})

    diffs: list[str] = []
    flags: list[str] = []
    effective = dict(new_map)
    matched = 0
    bios_changed = False

    for m in members:
        name = m.get("name") or ""
        key = norm(name)
        if not key or key not in new_map:
            continue
        matched += 1
        form = sorted(m.get("wgs") or [])
        cost = sorted(new_map[key])
        s = s_members.setdefault(key, {})

        # cost.eu observation clock: stamp each WG when first seen
        # there; a WG that leaves and returns is re-stamped.
        first_seen = {int(k): v for k, v in (s.get("cost_first_seen") or {}).items()}
        first_seen = {wg: d for wg, d in first_seen.items() if wg in cost}
        for wg in cost:
            first_seen.setdefault(wg, today)

        # form observation clock: stamp when the member's set changed
        # relative to what the last sync recorded. First sight of a
        # member initialises the clock without counting as a change.
        prev_form = s.get("form_wgs")
        form_changed_on = s.get("form_changed_on") or today
        if prev_form is not None and sorted(prev_form) != form:
            form_changed_on = today

        final = set(form)
        for wg in (set(cost) - set(form)):
            if first_seen[wg] >= form_changed_on:
                final.add(wg)
                diffs.append(f"  + {name}: WG{wg} added (formal record moved "
                             f"after the last form change)")
            else:
                flags.append(f"  ? {name}: WG{wg} stands on cost.eu but their "
                             f"newer form submission omits it. Holding the "
                             f"form's version; overrule by editing the bio "
                             f"if the removal was accidental.")
        for wg in (set(form) - set(cost)):
            flags.append(f"  ~ {name}: WG{wg} from the form is not on "
                         f"cost.eu yet (pending formal catch-up).")

        final_sorted = sorted(final)
        if final_sorted != form:
            m["wgs"] = final_sorted
            bios_changed = True
        effective[key] = final_sorted

        s["cost_first_seen"] = {str(k): v for k, v in sorted(first_seen.items())}
        s["form_wgs"] = final_sorted
        s["form_changed_on"] = form_changed_on

    out = [f"Per-bio WGs: {matched} bios matched on cost.eu's Membership table"]
    if diffs:
        out.extend(diffs)
    if flags:
        out.append("  Discrepancies under watch (no action taken):")
        out.extend(flags)
    if not diffs and not flags:
        out.append("  (no changes)")

    if bios_changed:
        BIOS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    new_state = json.dumps(state, indent=2, ensure_ascii=False) + "\n"
    old_state = WG_STATE.read_text(encoding="utf-8") if WG_STATE.exists() else ""
    if new_state != old_state:
        WG_STATE.write_text(new_state, encoding="utf-8")
    return out, effective


# ─── Leadership sync (Leadership + Additional Roles tables) ────────

_ROLE_LABEL_RE = re.compile(
    # cost.eu's Leadership table emits malformed HTML (a </div> closing
    # what should be a </td>), which breaks BeautifulSoup's table parse.
    # Regex over the raw HTML instead — find every <td>{role}</(td|div)>
    # whose text ends in one of the known leadership suffixes.
    # `Leader` precedes the standalone `Lead` so a "WG1 Leader" cell
    # matches the longer suffix first; standalone `Lead` covers a future
    # label like "Science Communication Lead" or "Diversity Lead" that
    # carries no trailing "er" and isn't the hyphenated "Co-Lead".
    r"<td[^>]*>([A-Z][A-Za-z0-9 ./()\-]+"
    r"(?:Chair|Coordinator|Co-Lead|Co-lead|Leader|Lead|Representative))"
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


# WG lead / co-lead roles look like "WG1 Leader", "WG3 Co-Leader", or
# "WG3 Co-Lead". The per-bio `wg_leadership` object is derived from these
# reconciled role strings so it can never drift from `roles`.
_WG_LEAD_ROLE_RE = re.compile(r"^WG\s*(\d+)\s+(Co-)?Lead(?:er)?$", re.I)


def wg_leadership_from_roles(roles: list[str]) -> dict:
    """Derive the {"lead": [...], "co_lead": [...]} object from a
    member's reconciled leadership roles. Returns only the non-empty
    keys, with sorted, de-duplicated WG numbers, matching the shape the
    directory WG filter on people.html reads."""
    lead: list[int] = []
    co_lead: list[int] = []
    for r in roles:
        m = _WG_LEAD_ROLE_RE.match(str(r).strip())
        if not m:
            continue
        (co_lead if m.group(2) else lead).append(int(m.group(1)))
    out: dict[str, list[int]] = {}
    if lead:
        out["lead"] = sorted(set(lead))
    if co_lead:
        out["co_lead"] = sorted(set(co_lead))
    return out


def apply_leadership(leadership: list[tuple[str, str]]) -> list[str]:
    """Mutate data/bios.json so each leadership role from cost.eu is
    held by exactly one person there.

    Reconciles leadership roles on EVERY entry, not just `source ==
    "seed"` ones: a sitting MC member who submitted the Google Form and
    is later promoted to a Working Group Lead on cost.eu now picks up
    the role tag. The narrower guarantee that protects form data is at
    the role level, not the entry level — only roles that look like a
    cost.eu-tracked leadership label (i.e. appear in `leadership_roles`)
    are ever removed, so a form-provided custom role such as
    "MC member · Switzerland" is always kept. Returns diff lines."""
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

    # Reconcile roles on every entry, seed or form-submitted. The
    # role-level guard below (only labels in `leadership_roles` are ever
    # removed) is what protects form-provided custom roles, so the old
    # entry-level `source == "seed"` skip is no longer needed.
    for m in members:
        current = list(m.get("roles") or [])
        kept: list[str] = []
        # Remove leadership roles that no longer point to this person.
        # Non-leadership roles (form-provided custom labels) are never
        # in `leadership_roles`, so they always fall through to `kept`.
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
        # Derive `wg_leadership` from the reconciled roles so it can
        # never drift from them. A WG lead or co-lead change on cost.eu
        # updates only the flat `roles` array above. Without this step
        # the per-bio `wg_leadership` object (which the people.html WG
        # filter reads to place leaders under their group) keeps
        # pointing at the previous holder until someone hand-edits
        # bios.json. Recomputing it for every member each run also
        # removes a stale entry from anyone who has just lost the role.
        new_wgl = wg_leadership_from_roles(kept)
        if (m.get("wg_leadership") or {}) != new_wgl:
            diffs.append(
                f"  ~ {m['name']}: wg_leadership "
                f"{m.get('wg_leadership') or {}} -> {new_wgl}"
            )
            m["wg_leadership"] = new_wgl

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


# ─── WG dataset (data/wg.json) ──────────────────────────────────────

WG_JSON = ROOT / "data" / "wg.json"

# WG titles and palette classes. cost.eu does not expose Working Group
# names, so they live here as config. The four-colour palette matches
# `.wg-chip.wg-{1..4}` in assets/css/site.css. Purpose descriptions are
# hand-authored per locale in working-groups.html, not here.
WG_META = {
    1: {"name": "Building the Network", "colour": "wg-1"},
    2: {"name": "Transfer of Knowledge", "colour": "wg-2"},
    3: {"name": "Fostering the Next Generation of Scholars", "colour": "wg-3"},
    4: {"name": "Inclusion, Representativeness & Ethics", "colour": "wg-4"},
}


def fetch_members(bs: BeautifulSoup) -> list[dict]:
    """Parse cost.eu's Membership table (columns: Name, Working Group,
    Country) into [{name, country, wgs:[...]}]. The display name and
    country are kept so the Working Groups page can show a card for
    EVERY member, not only those with a directory bio. The leadership
    table (which puts a digit in the first cell) and the header row are
    skipped by the same guards fetch_wg_map uses."""
    out: list[dict] = []
    for tr in bs.find_all("tr"):
        cells = [" ".join(c.stripped_strings) for c in tr.find_all(["td", "th"])]
        if len(cells) < 3:
            continue
        name, wg_cell, country = cells[0], cells[1], cells[2]
        if not re.search(r"WG\s*\d", wg_cell or ""):
            continue
        k = norm(name)
        if not k or k.isdigit() or k == "name":
            continue
        wgs = sorted({int(d) for d in re.findall(r"WG\s*(\d)", wg_cell)})
        # cost.eu writes some names in ALL CAPS ("ANDREEA DRAGOMIR");
        # tidy to title case for display, same as leadership names.
        out.append({"name": titlecase_name(name.strip()),
                    "country": country.strip(), "wgs": wgs})
    out.sort(key=lambda m: norm(m["name"]))
    return out


def build_wg_json(members: list[dict]) -> list[str]:
    """Write data/wg.json: per-Working-Group leadership and FULL
    membership for the Working Groups page. Leadership is read from each
    bio's `wg_leadership` (set by apply_leadership from cost.eu's
    Leadership table); membership from `members` (cost.eu's Membership
    table, via fetch_members), carrying every member's name and country.
    A member who also has a directory bio gets a `slug`, so the page can
    link to their card and show their photo and affiliation. Titles and
    the colour palette come from the static WG_META. cost.eu is the
    source, so this file is regenerated every sync and never hand-edited.
    Idempotent: deterministic sorted output, written only on change."""
    bios: list[dict] = []
    if BIOS.exists():
        bios = json.loads(BIOS.read_text(encoding="utf-8")).get("members", [])
    bios_by_norm = {norm(b.get("name") or ""): b for b in bios}

    lead_by_wg: dict[int, dict] = {}
    colead_by_wg: dict[int, dict] = {}
    for b in bios:
        wgl = b.get("wg_leadership") or {}
        ref = {"slug": b.get("id"), "name": b.get("name") or ""}
        for n in wgl.get("lead") or []:
            lead_by_wg[int(n)] = ref
        for n in wgl.get("co_lead") or []:
            colead_by_wg[int(n)] = ref

    groups = []
    for n in (1, 2, 3, 4):
        meta = WG_META[n]
        lead = lead_by_wg.get(n)
        co_lead = colead_by_wg.get(n)
        leader_slugs = {x["slug"] for x in (lead, co_lead) if x}
        rows = [m for m in members if n in m.get("wgs", [])]
        out_members = []
        for m in rows:
            b = bios_by_norm.get(norm(m["name"]))
            slug = b.get("id") if b else None
            if slug and slug in leader_slugs:
                continue  # leaders render in the leadership block
            entry = {"name": m["name"], "country": m.get("country") or ""}
            if slug:
                entry["slug"] = slug
            out_members.append(entry)
        out_members.sort(key=lambda e: norm(e["name"]))
        groups.append({
            "number": n,
            "name": meta["name"],
            "colour": meta["colour"],
            "memberCount": len(rows) or len(leader_slugs),
            "lead": lead,
            "coLead": co_lead,
            "members": out_members,
        })

    payload = {
        "_documentation": (
            "Per-Working-Group leadership and membership. Generated by "
            "scripts/sync-cost.py from cost.eu's Membership and Leadership "
            "tables cross-referenced with data/bios.json. DO NOT EDIT BY "
            "HAND: the next weekly sync overwrites it. WG titles and the "
            "colour palette are config in sync-cost.py (WG_META); purpose "
            "descriptions are hand-authored per locale in working-groups.html. "
            "Each member carries name + country from cost.eu; a `slug` is "
            "present when they also have a directory bio (photo, affiliation, "
            "and a link to their card)."
        ),
        "source": URL,
        "groups": groups,
    }
    new_text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    old_text = WG_JSON.read_text(encoding="utf-8") if WG_JSON.exists() else ""
    if new_text == old_text:
        return ["WG dataset: data/wg.json (no changes)"]
    WG_JSON.write_text(new_text, encoding="utf-8")
    lines = ["WG dataset: data/wg.json updated"]
    for g in groups:
        lead = g["lead"]["name"] if g["lead"] else "(vacant)"
        lines.append(f"  WG{g['number']}: {g['memberCount']} members, lead {lead}")
    return lines



# ─── MC roster + statistics sync (Management Committee table) ───────

# COST member countries → ISO 3166-1 alpha-2 (flagcdn codes). Covers
# the full + cooperating member list so a country joining the Action
# resolves without a code change. A parsed country missing from this
# map is reported and skipped rather than guessed.
COUNTRY_CODES = {
    "Albania": "al", "Austria": "at", "Belgium": "be",
    "Bosnia and Herzegovina": "ba", "Bulgaria": "bg", "Croatia": "hr",
    "Cyprus": "cy", "Czech Republic": "cz", "Czechia": "cz",
    "Denmark": "dk", "Estonia": "ee", "Finland": "fi", "France": "fr",
    "Georgia": "ge", "Germany": "de", "Greece": "gr", "Hungary": "hu",
    "Iceland": "is", "Ireland": "ie", "Israel": "il", "Italy": "it",
    "Latvia": "lv", "Lithuania": "lt", "Luxembourg": "lu", "Malta": "mt",
    "Moldova": "md", "Republic of Moldova": "md", "Montenegro": "me",
    "Netherlands": "nl", "The Netherlands": "nl",
    "North Macedonia": "mk", "Norway": "no", "Poland": "pl",
    "Portugal": "pt", "Romania": "ro", "Serbia": "rs", "Slovakia": "sk",
    "Slovenia": "si", "Spain": "es", "Sweden": "se", "Switzerland": "ch",
    "Türkiye": "tr", "Turkey": "tr", "Ukraine": "ua",
    "United Kingdom": "gb",
}

# Display-name corrections for upstream data-entry defects in cost.eu's
# MC table (e.g. a collapsed "PAVLOSIOANNIS"). Keyed on the normalised
# parsed name; the value is the full corrected display name. Remove an
# entry once cost.eu fixes the source.
MC_NAME_FIXES = {
    "pavlosioannis koktsidis": "Prof Pavlos Ioannis Koktsidis",
    # cost.eu publishes these without their diacritics; norm() strips
    # diacritics for keying, so the corrected forms match either way.
    "danilo kalezic": "Mr Danilo Kalezić",
    "miha dvojmoc": "Mr Miha Dvojmoč",
}

MC_JSON = ROOT / "data" / "mc-members.json"

# Pages carrying <span data-cost-stat="mc-count|country-count"> markers
# whose text content is rewritten from the parsed roster. The founding
# numbers (52 contributors, 21 countries) are historical record and
# deliberately carry no marker.
STAT_PAGES = [
    "about.html", "about.fr.html", "about.de.html",
    "press-kit.html", "press-kit.fr.html", "press-kit.de.html",
]


_MC_SECTION_RE = re.compile(
    r"Management Committee</h2>(.*?)</table>", re.S)
_MC_COUNTRY_RE = re.compile(
    # cost.eu closes the country <td> with a stray </div> (the same
    # malformation that forces extract_leadership onto raw HTML), so
    # the whole MC table is parsed here with regex rather than bs4.
    r"<td[^>]*align-top[^>]*>([^<]+)</(?:div|td)>")


def fetch_mc(html: str) -> list[dict]:
    """Parse cost.eu's Management Committee table into
    [{name, country, country_code}].

    Works on the raw HTML because the country cells are closed with a
    stray </div> that fools BeautifulSoup's table parser (same defect
    extract_leadership works around). The section between the
    "Management Committee" heading and its </table> is split on the
    country cells; each country's segment carries one <h4> per
    representative holding the title/first/SURNAME spans. A country
    missing from COUNTRY_CODES is reported by the caller via the
    roster diff (its reps vanish), so keep the map covering the full
    COST membership."""
    m = _MC_SECTION_RE.search(html)
    if not m:
        return []
    seg = m.group(1)
    hits = list(_MC_COUNTRY_RE.finditer(seg))
    out: list[dict] = []
    seen: set = set()
    for i, cm in enumerate(hits):
        country = _unescape_html(cm.group(1).strip())
        if country not in COUNTRY_CODES:
            continue
        chunk = seg[cm.end(): hits[i + 1].start() if i + 1 < len(hits) else len(seg)]
        for h4 in _H4_RE.findall(chunk):
            name = " ".join(_SPAN_RE.findall(h4)).strip() or re.sub(r"<[^>]+>", " ", h4)
            name = titlecase_name(_unescape_html(re.sub(r"\s+", " ", name).strip()))
            name = MC_NAME_FIXES.get(norm(name), name)
            key = (country, norm(name))
            if not norm(name) or key in seen:
                continue
            seen.add(key)
            out.append({
                "name": name,
                "country": country,
                "country_code": COUNTRY_CODES[country],
            })
    out.sort(key=lambda m: (m["country"], norm(m["name"])))
    return out


def build_mc_json(mc: list[dict]) -> list[str]:
    """Write data/mc-members.json from the parsed MC table. Reports
    adds/removals against the previous roster so a representative
    change is visible in the weekly sync PR. Idempotent: deterministic
    sorted output, written only on change."""
    if not mc:
        return ["MC roster: cost.eu returned no parseable MC rows, "
                "leaving data/mc-members.json untouched."]
    old_names: set = set()
    if MC_JSON.exists():
        old = json.loads(MC_JSON.read_text(encoding="utf-8"))
        old_names = {norm(m.get("name") or "") for m in old.get("members", [])}
    payload = {
        "_documentation": (
            "Management Committee roster: one entry per MC representative "
            "with their country and ISO code (drives the flag images via "
            "flagcdn). Generated by scripts/sync-cost.py from cost.eu's "
            "Management Committee table. DO NOT EDIT BY HAND: the next "
            "weekly sync overwrites it. The same parse feeds the "
            "data-cost-stat literals on the About page and press kit."
        ),
        "source": URL,
        "members": mc,
    }
    new_text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    old_text = MC_JSON.read_text(encoding="utf-8") if MC_JSON.exists() else ""
    countries = len({m["country"] for m in mc})
    lines = [f"MC roster: {len(mc)} representatives, {countries} countries"]
    if new_text == old_text:
        lines.append("  (no changes)")
        return lines
    new_names = {norm(m["name"]) for m in mc}
    for n in sorted(new_names - old_names):
        lines.append(f"  + {n}")
    for n in sorted(old_names - new_names):
        lines.append(f"  - {n}")
    MC_JSON.write_text(new_text, encoding="utf-8")
    return lines


_STAT_SPAN_RE = {
    "mc-count": re.compile(
        r'(<span[^>]*data-cost-stat="mc-count"[^>]*>)[^<]*(</span>)'),
    "country-count": re.compile(
        r'(<span[^>]*data-cost-stat="country-count"[^>]*>)[^<]*(</span>)'),
}


def apply_stats(mc: list[dict]) -> list[str]:
    """Rewrite the data-cost-stat="mc-count|country-count" span contents
    on the About page and press kit (all locales) from the parsed
    roster, so the visible statistics can never drift from cost.eu.
    Reports per-file changes; no-ops idempotently."""
    if not mc:
        return ["Stat literals: skipped (no roster parsed)."]
    values = {
        "mc-count": str(len(mc)),
        "country-count": str(len({m["country"] for m in mc})),
    }
    lines = [f"Stat literals: MC {values['mc-count']} · "
             f"countries {values['country-count']}"]
    changed_any = False
    for page in STAT_PAGES:
        path = ROOT / page
        if not path.exists():
            continue
        html = path.read_text(encoding="utf-8")
        new_html = html
        for key, rx in _STAT_SPAN_RE.items():
            new_html = rx.sub(lambda m: m.group(1) + values[key] + m.group(2),
                              new_html)
        if new_html != html:
            path.write_text(new_html, encoding="utf-8")
            lines.append(f"  ~ {page} updated")
            changed_any = True
    if not changed_any:
        lines.append("  (no changes)")
    return lines


def check_country_grid(mc: list[dict]) -> list[str]:
    """Compare the hand-authored MC country grid on about.html against
    the parsed roster and report mismatches. Report-only: the grid
    carries curated markup (flags, deep-link ids), so a human applies
    the fix; this check makes sure the drift is visible in the weekly
    sync PR rather than silent."""
    if not mc:
        return []
    path = ROOT / "about.html"
    html = path.read_text(encoding="utf-8")
    # Scope to the MC countries block: the founding-contributors grid
    # further down the page reuses the same classes and data-person
    # attributes, and an inline JS template carries ${...} placeholders.
    m = re.search(r'id="mc-countries".*?</details>', html, re.S)
    block = m.group(0) if m else ""
    grid_countries = {c for c in re.findall(r'class="country-name">([^<]+)<', block)
                      if "${" not in c}
    grid_people = {norm(p) for p in re.findall(r'data-person="([^"]+)"', block)
                   if "${" not in p}
    roster_countries = {m["country"] for m in mc}
    roster_people = {norm(m["name"]) for m in mc}
    lines: list[str] = []
    for c in sorted(roster_countries - grid_countries):
        lines.append(f"  ! country on cost.eu missing from the about-page grid: {c}")
    for c in sorted(grid_countries - roster_countries):
        lines.append(f"  ! country in the about-page grid no longer on cost.eu: {c}")
    for p in sorted(roster_people - grid_people):
        lines.append(f"  ! MC rep on cost.eu missing from the grid: {p}")
    for p in sorted(grid_people - roster_people):
        lines.append(f"  ! grid entry no longer an MC rep on cost.eu: {p}")
    if lines:
        lines.insert(0, "Country-grid check (about.html, hand-maintained):")
        lines.append("  Apply grid edits by hand in all three locales, "
                     "or accept the drift knowingly.")
    else:
        lines = ["Country-grid check: about.html grid matches the roster."]
    return lines


# ─── main ───────────────────────────────────────────────────────────

def main() -> None:
    r = requests.get(URL, headers={"User-Agent": "netsec-sync/1.0"}, timeout=30)
    r.raise_for_status()
    bs = BeautifulSoup(r.text, "html.parser")

    from datetime import date
    today = date.today().isoformat()

    # 1) Per-bio WGs → data/bios.json: per-WG additive reconciliation
    #    between the form's sets and cost.eu's formal record (#236).
    #    Runs first because every other WG surface consumes its result.
    new_map = fetch_wg_map(bs)
    wg_report, effective_map = reconcile_wgs(new_map, today)

    # 2) WG_MAP — the reconciled union, so the home-page chips show
    #    exactly what the directory shows.
    old_map = rewrite_wg_map(effective_map)
    for line in report_wg(old_map, effective_map):
        print(line)
    print()
    for line in wg_report:
        print(line)

    # 3) Leadership → data/bios.json — uses raw HTML because cost.eu's
    #    Leadership table contains a malformed </div> closing tag that
    #    fools BeautifulSoup's table parser.
    leadership = extract_leadership(r.text)
    print()
    for line in apply_leadership(leadership):
        print(line)

    # 4) data/wg.json — per-WG membership + leadership for the Working
    #    Groups page. Reads the bios.json just reconciled in step 3, so
    #    the leadership it records matches, and the same `new_map` that
    #    drove steps 1 and 2, so all surfaces stay in lockstep.
    members = fetch_members(bs)
    for m in members:
        k = norm(m["name"])
        if k in effective_map:
            m["wgs"] = list(effective_map[k])
    print()
    for line in build_wg_json(members):
        print(line)

    # 5) MC roster → data/mc-members.json, plus the visible statistics
    #    (MC count, country count) on the About page and press kit, and
    #    a report-only drift check of the hand-authored country grid.
    mc = fetch_mc(r.text)
    print()
    for line in build_mc_json(mc):
        print(line)
    print()
    for line in apply_stats(mc):
        print(line)
    print()
    for line in check_country_grid(mc):
        print(line)


if __name__ == "__main__":
    main()
