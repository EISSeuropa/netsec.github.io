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
        # {n} is the member count, {slug} the theme slug.
        "members_link": "See {n} members working on this",
        "members_link_one": "See 1 member working on this",
        "members_link_nocount": "See members working on this",
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
        "members_link_nocount": "Voir les membres qui y travaillent",
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
        "members_link_nocount": "Mitglieder anzeigen, die daran arbeiten",
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


def theme_counts(bios: dict) -> dict:
    """Map each theme name to the number of directory members who list it
    in their `themes` array. Mirrors how data/bios.json's theme_aggregate
    is built, but recomputed so the link never trusts a stale aggregate."""
    counts: dict = {}
    for member in bios.get("members", []):
        for theme in member.get("themes", []) or []:
            counts[theme] = counts.get(theme, 0) + 1
    return counts


def render_members_link(loc: dict, theme: str, counts: dict) -> str:
    """Build the '→ See N members working on this' link for a theme, or
    return '' when the concept has no theme. Falls back to a count-free
    label when the theme is absent from the taxonomy."""
    if not theme:
        return ""
    slug = keyword_slug(theme)
    href = f"{loc['people']}#themes={slug}"
    n = counts.get(theme)
    if n is None or n <= 0:
        text = loc["members_link_nocount"]
    elif n == 1:
        text = loc["members_link_one"]
    else:
        text = loc["members_link"].format(n=n)
    return (
        f'<p class="fg-theme-link">'
        f'<a href="{html.escape(href, quote=True)}">'
        f'→ {html.escape(text)}</a></p>'
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


def render_concept(loc: str, concept: dict, counts: dict) -> str:
    """Render one concept as a <dt>/<dd> pair matching the glossary's
    existing markup. The locale-appropriate definition leads the <dd>;
    the optional theme link and sources list follow inside it so the
    DefinedTerm extractor (which reads <dt> then the next <dd>) still
    sees a clean term + definition."""
    l = LOCALES[loc]
    term = concept["term"]
    slug = keyword_slug(term)
    definition = concept["definition"][loc]

    parts = [f"<p>{html.escape(definition)}</p>"]
    theme_link = render_members_link(l, concept.get("theme", ""), counts)
    if theme_link:
        parts.append(theme_link)
    sources_html = render_sources(l, concept.get("sources") or [])
    if sources_html:
        parts.append(sources_html)
    dd_body = "".join(parts)

    return (
        f'        <dt id="fg-{slug}">{html.escape(term)}</dt>\n'
        f"        <dd>{dd_body}</dd>"
    )


def render_section(loc: str, concepts: list, counts: dict) -> str:
    """Render the full 'Concepts in European security studies' section for
    one locale, sentinels included, ready to drop between them."""
    l = LOCALES[loc]
    entries = "\n\n".join(render_concept(loc, c, counts) for c in concepts)
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


def build(loc: str, concepts: list, counts: dict) -> str:
    """Read the locale's glossary page and return its content with the
    field-guide region rebuilt. Does not write."""
    path = ROOT / LOCALES[loc]["file"]
    page = path.read_text(encoding="utf-8")
    region = render_section(loc, concepts, counts)
    return replace_region(page, region)


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
    bios = json.loads(BIOS.read_text(encoding="utf-8")) if BIOS.exists() else {}
    counts = theme_counts(bios)

    drift = False
    for loc in LOCALES:
        path = ROOT / LOCALES[loc]["file"]
        rendered = build(loc, concepts, counts)
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

    print(f"✓ Rendered {len(concepts)} concepts into 3 locales.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
