#!/usr/bin/env python3
"""
Generate Pagefind-only HTML stubs for every member in data/bios.json.

Why
---
The Network directory at /people.html renders its content at runtime
from data/bios.json — so the names, affiliations, and bios are not
in the HTML when Pagefind indexes the site. Search for "Laudrain"
would otherwise return only incidental mentions on other pages
(press kit, FAQ, the country-list on the home page), with no result
pointing back at the directory.

This script generates one HTML file per member, per locale, under
`search/bios/<lang>/<slug>.html`. Each stub:

  - holds the member's full bio text so Pagefind can match against
    any of: name, affiliation, country, position, working groups,
    or the bio body
  - rewrites its own canonical URL via Pagefind's
    `<a data-pagefind-meta="url" href="…">` mechanism so the
    overlay link sends the visitor to /people.html#<slug>
    (locale-appropriate) — not to the stub itself
  - carries a 0-second meta-refresh that catches the rare case of
    someone visiting the stub URL directly (e.g. shared link from
    before the override existed); they're redirected to the live
    directory
  - exposes structured metadata (kind=bio, photo, country_code,
    affiliation, role, wgs) for the overlay to render a rich card
    UI rather than the plain-page card used for everything else

The stubs are regenerated on every search build (`./scripts/build-
search.sh`) — they are never edited by hand.
"""
from __future__ import annotations
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIOS = ROOT / "data" / "bios.json"
OUT_ROOT = ROOT / "search" / "bios"

LANGS = ("en", "fr", "de")


def people_url(slug: str, lang: str) -> str:
    """Locale-aware deep-link to a directory card."""
    if lang == "en":
        return f"/people.html#{slug}"
    return f"/people.{lang}.html#{slug}"


def html_escape(s: str) -> str:
    """Minimal HTML escape for text nodes and attribute values."""
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_stub(member: dict, lang: str) -> str:
    slug = member.get("id", "").strip()
    name = (member.get("name") or "").strip()
    if not slug or not name:
        return ""
    affiliation = (member.get("affiliation") or "").strip()
    position = (member.get("position") or "").strip()
    country = (member.get("country") or "").strip()
    country_code = (member.get("country_code") or "").strip().lower()
    bio = (member.get("bio") or "").strip()
    photo = (member.get("photo") or "").strip()
    roles = member.get("roles") or []
    wgs = member.get("wgs") or []
    keywords = member.get("keywords") or []

    role_label = " · ".join(roles) if roles else ""
    wgs_csv = ",".join(str(w) for w in wgs)
    wgs_label = " · ".join(f"WG{w}" for w in wgs) if wgs else ""
    canonical = people_url(slug, lang)

    # Build the indexable body. The order matters for Pagefind's
    # excerpt scoring — name + role appear early so they dominate
    # the snippet preview.
    #
    # We deliberately *don't* try to set Pagefind's `url` meta to
    # override the per-page URL: Pagefind v1 reads
    # `data-pagefind-meta="url"` as a text-meta key (the element's
    # text becomes meta.url) rather than as a URL override that
    # changes `hit.url`. URL rewriting is therefore done client-
    # side in the overlay's renderBioHit() — it parses the stub
    # URL (which carries the locale and slug in its path) and
    # rewrites the link to /people.html#<slug> (locale-aware).
    parts = [
        f'<h1>{html_escape(name)}</h1>',
        # `kind:bio` lets the overlay render a rich card; everything
        # else falls back to the plain-page card.
        '<p data-pagefind-meta="kind:bio">Member of the NetSec community directory.</p>',
    ]
    if role_label:
        parts.append(f'<p data-pagefind-meta="role">{html_escape(role_label)}</p>')
    if position:
        parts.append(f'<p data-pagefind-meta="position">{html_escape(position)}</p>')
    if affiliation:
        parts.append(f'<p data-pagefind-meta="affiliation">{html_escape(affiliation)}</p>')
    if country:
        parts.append(
            f'<p data-pagefind-meta="country:{html_escape(country_code)}">'
            f'{html_escape(country)}</p>'
        )
    if wgs_label:
        parts.append(
            f'<p data-pagefind-meta="wgs:{wgs_csv}">'
            f'Working Groups: {wgs_label}</p>'
        )
    if photo:
        parts.append(
            f'<span data-pagefind-meta="photo:/{html_escape(photo.lstrip("/"))}" '
            f'style="display:none"></span>'
        )
    if keywords:
        parts.append(
            f'<p data-pagefind-meta="keywords">{html_escape(", ".join(keywords))}</p>'
        )
    if bio:
        # Preserve paragraph breaks; the rest of the body is plain text.
        for paragraph in re.split(r"\n{2,}", bio):
            parts.append(f"<p>{html_escape(paragraph.strip())}</p>")

    body = "\n  ".join(parts)

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<title>{html_escape(name)} — NetSec directory</title>
<meta http-equiv="refresh" content="0; url={canonical}">
<meta name="robots" content="noindex,nofollow">
<link rel="canonical" href="{canonical}">
<!-- These pages are search-index stubs. Direct visitors are
     redirected to the live directory entry; search-result clicks
     go there too via the data-pagefind-meta="url" override. The
     stub itself is not user-facing. -->
<style>body{{display:none}}</style>
</head>
<body>
<main data-pagefind-body>
  {body}
</main>
</body>
</html>
"""


def main() -> int:
    if not BIOS.exists():
        print(f"✗ {BIOS} not found")
        return 1

    data = json.loads(BIOS.read_text(encoding="utf-8"))
    members = data.get("members") if isinstance(data, dict) else data
    if not members:
        print("✗ No members in bios.json")
        return 1

    # Wipe and recreate to drop stubs for members that have left the
    # directory.
    if OUT_ROOT.exists():
        shutil.rmtree(OUT_ROOT)
    for lang in LANGS:
        (OUT_ROOT / lang).mkdir(parents=True, exist_ok=True)

    counts = {lang: 0 for lang in LANGS}
    for m in members:
        slug = (m.get("id") or "").strip()
        if not slug:
            continue
        for lang in LANGS:
            html = render_stub(m, lang)
            if not html:
                continue
            (OUT_ROOT / lang / f"{slug}.html").write_text(html, encoding="utf-8")
            counts[lang] += 1

    total = sum(counts.values())
    print(
        f"✓ Generated {total} bio stubs "
        f"({counts['en']} EN · {counts['fr']} FR · {counts['de']} DE)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
