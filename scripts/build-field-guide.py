#!/usr/bin/env python3
"""
Render data/field-guide.json into the glossary pages (EN + FR + DE).

The field guide is a plain-language starting point for people new to
European security studies. It lives as data so the maintainer edits one
JSON file and never hand-writes the same markup three times. The script
replaces only the region between the

    <!-- field-guide:start --> ... <!-- field-guide:end -->

sentinels in glossary.html / glossary.fr.html / glossary.de.html, so the
COST-admin sections of the page are never touched.

Because the entries land in STATIC HTML, they inherit the rest of the
pipeline for free: the DefinedTerm JSON-LD that scripts/inject-seo.py
builds from the visible <dt>/<dd> markup, Pagefind indexing, and the
i18n drift checker.

Each concept can carry a `theme` (matched against data/bios.json's
theme taxonomy). When set, the script counts how many directory members
work on that theme and renders a "see N members working on this" link
into the locale's people page, filtered by the same #themes= slug the
directory builds. If the count cannot be computed (theme absent from the
taxonomy), the link is rendered without a count rather than a wrong one.

Usage:
    python3 scripts/build-field-guide.py           # write the three pages
    python3 scripts/build-field-guide.py --check    # exit 1 if any page would change

Run from the repo root. Stdlib only (json + html + re), runs under
/usr/bin/python3. CI can run `--check` on every PR touching
data/field-guide.json, the glossary pages, or this script (a matching
field-guide-drift.yml workflow can be added later).
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "field-guide.json"
BIOS = ROOT / "data" / "bios.json"

START = "<!-- field-guide:start -->"
END = "<!-- field-guide:end -->"

# Per-locale chrome. The definitions themselves come from the JSON
# (hand-translated, no machine translation — CLAUDE.md §1); these are the
# section heading, the intro, and the small labels around the entries.
LOCALES = {
    "en": {
        "file": "glossary.html",
        "heading": "Concepts in European security studies",
        "intro": (
            "A plain-language starting point for people new to the field. "
            "These entries describe a handful of recurring ideas and "
            "institutions, with links to official sources and to the "
            "directory members who work on them."
        ),
        "people": "people.html",
        # {n} is the matched-member count, {name} a member's name.
        "members_link": "See {n} members working on this",
        "members_link_one": "See 1 member working on this",
        "face_aria": "Open the profile of {name}",
        "facepile_more": "{n} more",
        "sources_label": "Sources",
    },
    "fr": {
        "file": "glossary.fr.html",
        "heading": "Concepts en études de sécurité européenne",
        "intro": (
            "Un point de départ en langage clair pour celles et ceux qui "
            "découvrent le domaine. Ces entrées décrivent quelques idées et "
            "institutions récurrentes, avec des liens vers des sources "
            "officielles et vers les membres de l'annuaire qui y travaillent."
        ),
        "people": "people.fr.html",
        "members_link": "Voir {n} membres qui y travaillent",
        "members_link_one": "Voir 1 membre qui y travaille",
        "face_aria": "Ouvrir le profil de {name}",
        "facepile_more": "{n} de plus",
        "sources_label": "Sources",
    },
    "de": {
        "file": "glossary.de.html",
        "heading": "Konzepte der europäischen Sicherheitsforschung",
        "intro": (
            "Ein verständlicher Einstieg für alle, die neu in diesem Feld "
            "sind. Diese Einträge beschreiben einige wiederkehrende Ideen und "
            "Institutionen, mit Verweisen auf offizielle Quellen und auf die "
            "Mitglieder des Verzeichnisses, die daran arbeiten."
        ),
        "people": "people.de.html",
        "members_link": "{n} Mitglieder anzeigen, die daran arbeiten",
        "members_link_one": "1 Mitglied anzeigen, das daran arbeitet",
        "face_aria": "Profil von {name} öffnen",
        "facepile_more": "{n} weitere",
        "sources_label": "Quellen",
    },
}


def keyword_slug(value: str) -> str:
    """Port of people.html's keywordSlug(): lower-case, every run of
    non-letter/non-number collapsed to a hyphen, leading/trailing hyphens
    stripped. The directory builds its #themes= hashes the same way, so a
    slug produced here lands on the right filtered view."""
    s = str(value or "").lower()
    s = re.sub(r"[^\w]+", "-", s, flags=re.UNICODE)
    # \w includes underscore; the JS character class does not.
    s = s.replace("_", "-")
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


FACEPILE_MAX = 5


def _strip_salutation(name: str) -> str:
    return re.sub(r"^(Dr|Prof|Mr|Mrs|Ms|Mx)\.?\s+", "", (name or "").strip(), flags=re.I)


def _surname_key(name: str) -> str:
    """Lower-cased last-name token, salutation stripped, for stable
    alphabetical ordering within the facepile."""
    tokens = _strip_salutation(name).split()
    return (tokens[-1] if tokens else (name or "")).lower()


def _initials(name: str) -> str:
    """First + last initial, salutation stripped. The fallback avatar for a
    member with no headshot, mirroring the directory's own monogram."""
    tokens = [t for t in re.split(r"\s+", _strip_salutation(name)) if t]
    if not tokens:
        return "?"
    if len(tokens) == 1:
        return tokens[0][:1].upper()
    return (tokens[0][:1] + tokens[-1][:1]).upper()


def _is_leader(member: dict) -> bool:
    """A member with a named role or a WG lead / co-lead seat sorts to the
    front of the facepile, so the most recognisable faces survive the cap."""
    return bool(member.get("roles") or (member.get("wg_leadership") or {}))


def members_for(concept: dict, members: list) -> list:
    """Directory members whose chosen keywords overlap the concept's
    match_keywords, ordered leadership-first, then by overlap strength (so
    the closest match survives the cap), then by surname. Empty when the
    concept has no match_keywords or nothing overlaps. The match is on the
    member's canonical_keywords, case-insensitive."""
    wanted = {k.strip().lower() for k in (concept.get("match_keywords") or []) if k.strip()}
    if not wanted:
        return []
    ranked = []
    for m in members:
        kws = {k.lower() for k in (m.get("canonical_keywords") or [])}
        strength = len(wanted & kws)
        if strength:
            ranked.append((m, strength))
    ranked.sort(key=lambda t: (not _is_leader(t[0]), -t[1], _surname_key(t[0].get("name", ""))))
    return [m for m, _ in ranked]


def _render_face(loc: dict, member: dict) -> str:
    """One overlapping avatar: a `member-link` anchor (auto-wired to the
    shared popover by assets/js/site.js) wrapping the headshot, or a
    monogram when the member has none. The image carries an empty alt so
    the member's name reaches assistive tech once, through the anchor's
    aria-label, and never leaks into the DefinedTerm description (#803)."""
    mid = member.get("id", "")
    name = member.get("name", "")
    href = f"{loc['people']}#{mid}"
    aria = loc["face_aria"].format(name=name)
    photo = member.get("photo") or ""
    if photo:
        inner = (
            f'<img src="{html.escape(photo, quote=True)}" alt="" '
            f'width="36" height="36" loading="lazy" decoding="async">'
        )
    else:
        inner = f'<span class="fg-initials" aria-hidden="true">{html.escape(_initials(name))}</span>'
    return (
        f'<a class="member-link fg-face" data-member="{html.escape(mid, quote=True)}" '
        f'href="{html.escape(href, quote=True)}" aria-label="{html.escape(aria, quote=True)}">'
        f"{inner}</a>"
    )


def render_facepile(loc_key: str, concept: dict, members: list) -> str:
    """Build the inline member facepile for a concept, or '' when nothing
    matches. The faces open the shared directory popover; the trailing
    link and any '+N' overflow disc point at the concept's theme view on
    the directory, since the directory filters by theme, not by a single
    keyword, so the theme is the closest deep-linkable set."""
    loc = LOCALES[loc_key]
    matched = members_for(concept, members)
    if not matched:
        return ""
    shown = matched[:FACEPILE_MAX]
    overflow = len(matched) - len(shown)
    theme = concept.get("theme", "")
    href = f"{loc['people']}#themes={keyword_slug(theme)}" if theme else loc["people"]
    href_esc = html.escape(href, quote=True)

    faces = [_render_face(loc, m) for m in shown]
    if overflow > 0:
        more_aria = loc["facepile_more"].format(n=overflow)
        faces.append(
            f'<a class="fg-face fg-face-more" href="{href_esc}" '
            f'aria-label="{html.escape(more_aria, quote=True)}">+{overflow}</a>'
        )

    n = len(matched)
    link_text = loc["members_link_one"] if n == 1 else loc["members_link"].format(n=n)
    return (
        f'<div class="fg-people">'
        f'<span class="fg-facepile">{"".join(faces)}</span>'
        f'<a class="fg-people-link" href="{href_esc}">→ {html.escape(link_text)}</a>'
        f"</div>"
    )


def render_sources(loc: dict, sources: list) -> str:
    """Build the small 'Sources' list of authoritative external links, or
    '' when the concept carries none."""
    if not sources:
        return ""
    items = []
    for src in sources:
        url = src.get("url", "")
        label = src.get("label", url)
        if not url:
            continue
        items.append(
            f'<li><a href="{html.escape(url, quote=True)}" '
            f'target="_blank" rel="noopener">{html.escape(label)}</a></li>'
        )
    if not items:
        return ""
    body = "".join(items)
    return (
        f'<div class="fg-sources">'
        f'<span class="fg-sources-label">{html.escape(loc["sources_label"])}</span>'
        f"<ul>{body}</ul></div>"
    )


def render_concept(loc: str, concept: dict, members: list) -> str:
    """Render one concept as a <dt>/<dd> pair matching the glossary's
    existing markup. The locale-appropriate definition leads the <dd> as
    its first <p>, so the DefinedTerm extractor (which reads the leading
    paragraph, #803) sees a clean term + definition; the member facepile
    and sources list follow it."""
    l = LOCALES[loc]
    term = concept["term"]
    slug = keyword_slug(term)
    definition = concept["definition"][loc]

    parts = [f"<p>{html.escape(definition)}</p>"]
    facepile = render_facepile(loc, concept, members)
    if facepile:
        parts.append(facepile)
    sources_html = render_sources(l, concept.get("sources") or [])
    if sources_html:
        parts.append(sources_html)
    dd_body = "".join(parts)

    return (
        f'        <dt id="fg-{slug}">{html.escape(term)}</dt>\n'
        f"        <dd>{dd_body}</dd>"
    )


def render_empty_region() -> str:
    """The field-guide region when the section is unpublished: just the
    sentinels around a holding comment, so the section is off the live
    Glossary while the concept data is preserved in field-guide.json. The
    jump-to link in each page is removed separately (this script owns only
    the region between the sentinels). See the `published` note in
    field-guide.json and issue #998."""
    return (
        f"{START}\n"
        f"    <!-- Field guide held for a future release (issue #998); "
        f'set "published": true in data/field-guide.json to restore. -->\n'
        f"    {END}"
    )


def render_section(loc: str, concepts: list, members: list) -> str:
    """Render the full 'Concepts in European security studies' section for
    one locale, sentinels included, ready to drop between them."""
    l = LOCALES[loc]
    entries = "\n\n".join(render_concept(loc, c, members) for c in concepts)
    return (
        f"{START}\n"
        f'    <section class="glossary-section">\n'
        f'      <h2 id="field-guide">{html.escape(l["heading"])}</h2>\n'
        f'      <p class="fg-intro">{html.escape(l["intro"])}</p>\n'
        f'      <dl class="glossary-dl">\n'
        f"{entries}\n"
        f"      </dl>\n"
        f"    </section>\n"
        f"    {END}"
    )


def replace_region(page: str, new_region: str) -> str:
    """Swap the content between the sentinels (inclusive) for new_region.
    Idempotent: re-running with the same data is a no-op."""
    if START not in page or END not in page:
        raise ValueError(
            f"sentinels {START} / {END} not found in page"
        )
    pattern = re.compile(
        re.escape(START) + r".*?" + re.escape(END), re.DOTALL
    )
    return pattern.sub(lambda _m: new_region, page, count=1)


def build(loc: str, concepts: list, members: list, published: bool = True) -> str:
    """Read the locale's glossary page and return its content with the
    field-guide region rebuilt. Does not write. When unpublished the region
    is blanked rather than rendered, holding the section off the live page."""
    path = ROOT / LOCALES[loc]["file"]
    page = path.read_text(encoding="utf-8")
    region = render_section(loc, concepts, members) if published else render_empty_region()
    return replace_region(page, region)


def warn_unmatched_keywords(concepts: list, members: list) -> None:
    """Surface match_keywords that overlap no directory member, to stderr.
    A miss is a likely typo, or a valid keyword nobody has chosen yet;
    either way the maintainer wants to see it. Non-fatal, mirroring the
    uncategorised-keyword warning in sync-bios.py."""
    have = {k.lower() for m in members for k in (m.get("canonical_keywords") or [])}
    for c in concepts:
        for kw in c.get("match_keywords") or []:
            if kw.strip() and kw.strip().lower() not in have:
                print(
                    f"  ! match_keyword '{kw}' on '{c.get('term', '?')}' "
                    "matches no directory member (typo, or unused keyword).",
                    file=sys.stderr,
                )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if any glossary page would change. Don't write.",
    )
    args = p.parse_args()

    data = json.loads(DATA.read_text(encoding="utf-8"))
    concepts = data.get("concepts", [])
    published = bool(data.get("published", True))
    bios = json.loads(BIOS.read_text(encoding="utf-8")) if BIOS.exists() else {}
    members = bios.get("members", [])
    if published:
        warn_unmatched_keywords(concepts, members)
    else:
        print(
            "  Field guide is unpublished (published:false); the section is "
            "held off the live Glossary. See issue #998.",
            file=sys.stderr,
        )

    drift = False
    for loc in LOCALES:
        path = ROOT / LOCALES[loc]["file"]
        rendered = build(loc, concepts, members, published)
        existing = path.read_text(encoding="utf-8")
        if args.check:
            if rendered != existing:
                print(
                    f"✗ {LOCALES[loc]['file']} is out of sync with "
                    f"data/field-guide.json.",
                    file=sys.stderr,
                )
                drift = True
        else:
            if rendered != existing:
                path.write_text(rendered, encoding="utf-8")
                print(f"✓ Rebuilt {LOCALES[loc]['file']}.")
            else:
                print(f"✓ {LOCALES[loc]['file']} already current.")

    if args.check:
        if drift:
            print(
                "  Run `python3 scripts/build-field-guide.py` and commit "
                "the result.",
                file=sys.stderr,
            )
            return 1
        print("✓ Glossary pages match data/field-guide.json.")
        return 0

    if published:
        print(f"✓ Rendered {len(concepts)} concepts into 3 locales.")
    else:
        print("✓ Blanked the field-guide region in 3 locales (unpublished).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
