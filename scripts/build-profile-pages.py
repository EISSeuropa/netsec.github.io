#!/usr/bin/env python3
"""Generate real, shareable member profile pages at /people/<slug>.html
(+ FR/DE), server-rendered from data/bios.json (#762).

The 252 pages are built by the Pages deploy and are not committed (#1716).
`people/` is gitignored, so run this to preview them locally and serve the
working tree. There is no --check: a drift gate exists to prove a committed
artefact current, and the deploy rebuilds the set from bios.json every time.

Why these exist: the directory at /people.html renders client-side from a
single JSON file, so a member has no URL of their own to put in an email
signature, and a shared link unfurls with the generic site card. These
pages give each member a permanent address with their own Open Graph
metadata and a `Person` JSON-LD record, so external search engines index
them and a shared link unfurls as that person.

They deliberately carry no `data-pagefind-body`: the site's on-site
Pagefind search still runs through the existing redirect stubs
(scripts/build-bio-search-stubs.py), keeping the two pipelines independent
for now. Pointing Pagefind at these real pages (retiring the stubs) is the
remaining #762 follow-up; sitemap listing (#1027) and per-member OG card
images (#1023) have shipped.

How the chrome stays identical with zero drift: each page reuses the
exact nav, footer, head assets, and site.js from the matching locale
`people.*.html` shell, extracted at build time. The page sits one
directory deep, so a single `<base href="/">` makes every root-authored
relative URL (assets, data, nav links) resolve correctly without rewrites.

The card is static (no directory filter interactivity). The few
translatable chrome strings carry `data-i18n` and are localised on load by
the shared `window.netsecT` catalog in site.js, the same mechanism the
directory uses.

Run: `python3 scripts/build-profile-pages.py` writes the pages and a
`sitemap fragment`. `--check` re-generates in memory and exits non-zero if
anything on disk has drifted (the CI gate), writing nothing.

Per-member Open Graph *images* are rendered separately by
scripts/build-og-cards.py (headless Chrome). This script points each
profile's og:image at the member's card when one exists, else the generic
people card, so a profile without a card still unfurls cleanly.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIOS = ROOT / "data" / "bios.json"
WORKS = ROOT / "data" / "orcid-works.json"
PRIZES = ROOT / "data" / "prize-winners.json"
OUT_DIR = ROOT / "people"
SITE = "https://netsec-cost.eu"

# The three locale shells the chrome is lifted from, and the filename
# suffix + <html> attributes each profile page carries.
LOCALES = {
    "en": {"shell": "people.html", "suffix": "", "lang": "en", "i18n": ""},
    "fr": {"shell": "people.fr.html", "suffix": ".fr", "lang": "fr",
           "i18n": ' data-i18n-status="beta"'},
    "de": {"shell": "people.de.html", "suffix": ".de", "lang": "de",
           "i18n": ' data-i18n-status="beta"'},
}

# Chrome strings rendered on the card. Marked with data-i18n so site.js's
# netsecT localises them on load from the shared catalog (the same keys the
# directory already uses). English is the catalog's identity fallback. The
# theme + region *display* names are already in that catalog (the directory
# filter chips translate them), so chips carry data-i18n for free.
T_BACK = "Back to the directory"
# The Network Map draws 191 people and, until #1642, offered no way to reach
# one of them. ?find= arrives on the map with this person already pinned, so
# a profile is now an entry point into the network rather than a leaf.
T_MAP = "See this member on the Network Map"
T_PUBS = "Recent publications"
T_THEMES = "Research themes"
T_REGIONS = "Research regions"
T_SIMILAR = "Works on similar topics"
T_SEE_ALL = "See everyone in these themes"
T_MENTORS = "Mentors on similar topics"
T_SEE_MENTORS = "See these mentors in the directory"
T_ANTHOLOGY = "In the EISS Anthology"

WG_NAMES = {"1": "WG1", "2": "WG2", "3": "WG3", "4": "WG4"}

# Warm contact-intro scaffolds (#1171 part 1). Baked into the mailto: hrefs at
# build time because data-i18n only rewrites textContent, never an href, so
# runtime localisation cannot reach these. The directory's runtime twin lives
# in assets/js/site.js (the I18N catalog, same EN keys) and the two homes are
# held together by test_scaffold_parity in test-build-profile-pages.py: edit
# the texts in BOTH places or that test fails.
#
# Each body is short and deliberately editable: the bracketed blanks are the
# sender's to fill, and the {areas_line} slot carries the one piece of match
# context the page already knows (the member's own research themes).
SCAFFOLDS = {
    "en": {
        "subject_mentor": "Mentorship enquiry via the NetSec directory",
        "subject_mentee": "Mentorship via the NetSec directory",
        "subject_stsm": "STSM hosting enquiry via the NetSec directory",
        "areas_own": " I was drawn by your work on {areas}.",
        "mentor": (
            "Dear {name},\n\n"
            "I found your profile in the NetSec directory.{areas_line}\n\n"
            "About me: [your name, career stage, institution, and a line on your research]\n"
            "What I am hoping for: [advice on publishing, a career conversation, feedback on a draft]\n\n"
            "Would you be open to a short online conversation in the coming weeks?\n\n"
            "Best regards,\n[your name]"),
        "mentee": (
            "Dear {name},\n\n"
            "I saw in the NetSec directory that you are seeking mentorship.{areas_line}\n\n"
            "About me: [your name, role, institution, and the areas where you could help]\n\n"
            "If useful, I would be happy to have a short conversation about your goals.\n\n"
            "Best regards,\n[your name]"),
        "stsm": (
            "Dear {name},\n\n"
            "I found you in the NetSec directory as a possible STSM host.{areas_line}\n\n"
            "About me: [your name, career stage, institution]\n"
            "Visit idea: [topic and rough dates]\n\n"
            "An STSM is a short funded research visit under the NetSec COST Action. "
            "If the fit looks right I would apply through e-COST. "
            "Would you be open to discussing it?\n\n"
            "Best regards,\n[your name]"),
    },
    "fr": {
        "subject_mentor": "Demande de mentorat via l'annuaire NetSec",
        "subject_mentee": "Mentorat via l'annuaire NetSec",
        "subject_stsm": "Demande d'accueil STSM via l'annuaire NetSec",
        "areas_own": " Vos travaux sur {areas} ont retenu mon attention.",
        "mentor": (
            "Bonjour {name},\n\n"
            "J'ai trouvé votre profil dans l'annuaire NetSec.{areas_line}\n\n"
            "Qui je suis : [votre nom, niveau de carrière, institution, et une ligne sur vos recherches]\n"
            "Ce que je recherche : [des conseils de publication, un échange sur la carrière, un retour sur un texte]\n\n"
            "Seriez-vous ouvert·e à un court échange en ligne dans les prochaines semaines ?\n\n"
            "Bien cordialement,\n[votre nom]"),
        "mentee": (
            "Bonjour {name},\n\n"
            "J'ai vu dans l'annuaire NetSec que vous recherchez un mentorat.{areas_line}\n\n"
            "Qui je suis : [votre nom, fonction, institution, et les domaines où vous pourriez aider]\n\n"
            "Si cela vous est utile, je serais heureux·se d'échanger brièvement sur vos objectifs.\n\n"
            "Bien cordialement,\n[votre nom]"),
        "stsm": (
            "Bonjour {name},\n\n"
            "Je vous ai trouvé·e dans l'annuaire NetSec comme hôte STSM possible.{areas_line}\n\n"
            "Qui je suis : [votre nom, niveau de carrière, institution]\n"
            "Idée de visite : [sujet et dates approximatives]\n\n"
            "Une STSM est une courte visite de recherche financée par l'Action COST NetSec. "
            "Si cela correspond, je déposerais une candidature via e-COST. "
            "Seriez-vous ouvert·e à en discuter ?\n\n"
            "Bien cordialement,\n[votre nom]"),
    },
    "de": {
        "subject_mentor": "Mentoring-Anfrage über das NetSec-Verzeichnis",
        "subject_mentee": "Mentoring über das NetSec-Verzeichnis",
        "subject_stsm": "STSM-Gastgeber-Anfrage über das NetSec-Verzeichnis",
        "areas_own": " Ihre Arbeit zu {areas} hat mein Interesse geweckt.",
        "mentor": (
            "Guten Tag {name},\n\n"
            "ich habe Ihr Profil im NetSec-Verzeichnis gefunden.{areas_line}\n\n"
            "Zu mir: [Ihr Name, Karrierestufe, Institution und eine Zeile zu Ihrer Forschung]\n"
            "Was ich mir erhoffe: [Publikationsberatung, ein Karrieregespräch, Feedback zu einem Entwurf]\n\n"
            "Wären Sie offen für ein kurzes Online-Gespräch in den kommenden Wochen?\n\n"
            "Mit freundlichen Grüßen\n[Ihr Name]"),
        "mentee": (
            "Guten Tag {name},\n\n"
            "ich habe im NetSec-Verzeichnis gesehen, dass Sie Mentoring suchen.{areas_line}\n\n"
            "Zu mir: [Ihr Name, Funktion, Institution und die Bereiche, in denen Sie helfen könnten]\n\n"
            "Falls hilfreich, würde ich mich über ein kurzes Gespräch über Ihre Ziele freuen.\n\n"
            "Mit freundlichen Grüßen\n[Ihr Name]"),
        "stsm": (
            "Guten Tag {name},\n\n"
            "ich habe Sie im NetSec-Verzeichnis als möglichen STSM-Gastgeber gefunden.{areas_line}\n\n"
            "Zu mir: [Ihr Name, Karrierestufe, Institution]\n"
            "Idee für den Besuch: [Thema und ungefähre Daten]\n\n"
            "Eine STSM ist ein kurzer, von der COST Action NetSec finanzierter Forschungsaufenthalt. "
            "Wenn es passt, würde ich mich über e-COST bewerben. "
            "Wären Sie offen, darüber zu sprechen?\n\n"
            "Mit freundlichen Grüßen\n[Ihr Name]"),
    },
}


def scaffold_body(m: dict, tag: str, lang: str) -> str:
    """Assemble the prefilled intro body for one member + intent + locale.
    Theme names stay as stored (English) in every locale: they are the
    directory's canonical research-area labels and the sentence around
    them is what localises."""
    sc = SCAFFOLDS[lang]
    themes = [t for t in (m.get("themes") or []) if t][:2]
    areas_line = sc["areas_own"].replace("{areas}", ", ".join(themes)) if themes else ""
    return (sc[tag]
            .replace("{name}", (m.get("name") or "").strip())
            .replace("{areas_line}", areas_line))

# Faces shown in the similar-people facepile before the "+N" overflow disc.
FACEPILE_MAX = 5


def esc(s) -> str:
    return html.escape(str(s or ""), quote=True)


def area_slug(s: str) -> str:
    """Slug a theme/region display name to the directory's filter slug.

    Mirrors people-directory.js's keywordSlug(): lowercase, collapse runs of
    non-alphanumerics to a hyphen, trim. The directory's slug is Unicode-aware
    (\\p{L}\\p{N}); the current theme + region vocab is ASCII, so this ASCII
    form produces identical slugs (asserted in the tests). If a non-ASCII
    theme is ever added, extend both sides together."""
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def similar_members(target: dict, members: list) -> list:
    """Members who work on related topics, most-similar first.

    Ranked by shared canonical-keyword count, then shared-theme count, then
    name. A candidate needs at least one shared keyword or theme to appear, so
    a member with no topic data simply gets no suggestions (graceful empty)."""
    t_kw = {k for k in (target.get("canonical_keywords") or []) if k}
    t_th = {t for t in (target.get("themes") or []) if t}
    if not t_kw and not t_th:
        return []
    scored = []
    for o in members:
        if o.get("id") == target.get("id") or not o.get("id"):
            continue
        shared_kw = len(t_kw & {k for k in (o.get("canonical_keywords") or []) if k})
        shared_th = len(t_th & {t for t in (o.get("themes") or []) if t})
        if not shared_kw and not shared_th:
            continue
        scored.append((-shared_kw, -shared_th, (o.get("name") or "").lower(), o))
    scored.sort(key=lambda x: x[:3])
    return [o for *_, o in scored]


def career_stage(m: dict) -> int:
    """Behind-the-scenes seniority signal (0 doctoral … 3 senior), inferred
    from the academic position (name honorific as a fallback). Mirrors
    careerStage() in assets/js/people-directory.js. Never shown: it only
    orders the mentor facepile so a more established mentor surfaces first
    among equally on-topic people."""
    name = m.get("name") or ""
    p = (m.get("position") or "").lower()
    if re.search(r"postdoc|post-?doctoral", p):
        return 1
    if ((re.search(r"\bprofessor\b", p) and not re.search(r"\b(assistant|associate)\b", p))
            or re.search(r"\b(director|head|dean|principal investigator)\b", p)
            or (re.search(r"\bprof\.?\b", name, re.I)
                and not re.search(r"\b(assistant|associate)\b", p))):
        return 3
    if re.search(r"\bassociate professor\b|\breader\b|\bsenior (lecturer|researcher|"
                 r"research fellow|fellow|analyst)\b|\bteam lead\b|\bprincipal\b", p):
        return 2
    if re.search(r"\bphd\b|\bdphil\b|doctoral (candidate|student|researcher|fellow)|"
                 r"\bdoctoral\b|doctorand|pre-?doctoral|\bcandidate\b|\bstudent\b", p):
        return 0
    if re.search(r"\bassistant professor\b|\blecturer\b|research fellow|"
                 r"research associate|\bresearcher\b|\banalyst\b", p):
        return 1
    if re.search(r"\bdr\.?\b", name, re.I):
        return 1
    return 1


def mentors_on_topics(target: dict, members: list) -> list:
    """Members who offer mentorship and share at least one topic with the
    target, most-relevant first. Ranked by shared canonical keywords, then
    shared themes, then seniority (a more established mentor first among equal
    topic fits), then name. Excludes the target. Empty when nothing matches, so
    the facepile simply does not render."""
    t_kw = {k for k in (target.get("canonical_keywords") or []) if k}
    t_th = {t for t in (target.get("themes") or []) if t}
    if not t_kw and not t_th:
        return []
    scored = []
    for o in members:
        if o.get("id") == target.get("id") or not o.get("id"):
            continue
        if "mentor" not in (o.get("mentorship") or []):
            continue
        shared_kw = len(t_kw & {k for k in (o.get("canonical_keywords") or []) if k})
        shared_th = len(t_th & {t for t in (o.get("themes") or []) if t})
        if not shared_kw and not shared_th:
            continue
        scored.append((-shared_kw, -shared_th, -career_stage(o),
                       (o.get("name") or "").lower(), o))
    scored.sort(key=lambda x: x[:4])
    return [o for *_, o in scored]


def render_areas(m: dict, loc: dict) -> str:
    """Research-theme and region chips, each deep-linking to the directory
    pre-filtered to that facet (#themes= / #regions=)."""
    out = []
    people = f'people{loc["suffix"]}.html'
    for label_key, field, key, extra in (
        (T_THEMES, "themes", "themes", ""),
        (T_REGIONS, "regions", "regions", " is-region"),
    ):
        vals = [v for v in (m.get(field) or []) if v]
        if not vals:
            continue
        chips = "".join(
            f'<a class="profile-area-chip{extra}" '
            f'href="{people}#{key}={esc(area_slug(v))}" '
            f'data-i18n="{esc(v)}">{esc(v)}</a>'
            for v in vals)
        out.append(f'<p class="profile-aside-label" data-i18n="{esc(label_key)}">{esc(label_key)}</p>'
                   f'<div class="profile-areas">{chips}</div>')
    return "".join(out)


def render_similar(target: dict, similar: list, loc: dict) -> str:
    """The field-guide-style facepile of people on related topics. Each face
    links straight to that member's own profile page; the trailing link opens
    the directory filtered to the target's themes."""
    if not similar:
        return ""
    visible = similar[:FACEPILE_MAX]
    overflow = len(similar) - len(visible)
    faces = []
    for o in visible:
        href = f'people/{esc(o["id"])}{loc["suffix"]}.html'
        photo = (o.get("photo") or "").strip()
        if photo:
            webp = re.sub(r"\.(jpe?g|png)$", ".webp", photo, flags=re.I)
            inner = (f'<picture><source srcset="{esc(webp)}" type="image/webp">'
                     f'<img src="{esc(photo)}" alt="" width="44" height="44" '
                     f'loading="lazy" decoding="async"></picture>')
        else:
            ini = "".join(w[0] for w in (o.get("name") or "?").split()[:2]).upper()
            inner = f'<span class="pf-initials" aria-hidden="true">{esc(ini)}</span>'
        # The member name is the accessible label (names aren't translated, so
        # this stays correct across locales without an aria template).
        faces.append(f'<a class="pf-face" href="{href}" '
                     f'aria-label="{esc(o.get("name"))}">{inner}</a>')
    if overflow > 0:
        faces.append(f'<span class="pf-face pf-more" aria-hidden="true">+{overflow}</span>')
    theme_slugs = [area_slug(t) for t in (target.get("themes") or []) if t]
    href = f'people{loc["suffix"]}.html'
    if theme_slugs:
        href += "#themes=" + ",".join(theme_slugs)
    return (f'<div class="profile-similar">'
            f'<p class="profile-aside-label" data-i18n="{esc(T_SIMILAR)}">{esc(T_SIMILAR)}</p>'
            f'<span class="pf-facepile">{"".join(faces)}</span>'
            f'<a class="profile-similar-link" href="{esc(href)}" '
            f'data-i18n="{esc(T_SEE_ALL)}">{esc(T_SEE_ALL)}</a></div>')


def render_mentors(target: dict, mentors: list, loc: dict) -> str:
    """A field-guide-style facepile of mentors working on the target's topics,
    reusing the similar-people styling. Each face links to that mentor's
    profile; the trailing link opens the directory filtered to the target's
    themes with the mentor filter on. Behind-the-scenes seniority orders the
    list (see mentors_on_topics)."""
    if not mentors:
        return ""
    visible = mentors[:FACEPILE_MAX]
    overflow = len(mentors) - len(visible)
    faces = []
    for o in visible:
        href = f'people/{esc(o["id"])}{loc["suffix"]}.html'
        photo = (o.get("photo") or "").strip()
        if photo:
            webp = re.sub(r"\.(jpe?g|png)$", ".webp", photo, flags=re.I)
            inner = (f'<picture><source srcset="{esc(webp)}" type="image/webp">'
                     f'<img src="{esc(photo)}" alt="" width="44" height="44" '
                     f'loading="lazy" decoding="async"></picture>')
        else:
            ini = "".join(w[0] for w in (o.get("name") or "?").split()[:2]).upper()
            inner = f'<span class="pf-initials" aria-hidden="true">{esc(ini)}</span>'
        faces.append(f'<a class="pf-face" href="{href}" '
                     f'aria-label="{esc(o.get("name"))}">{inner}</a>')
    if overflow > 0:
        faces.append(f'<span class="pf-face pf-more" aria-hidden="true">+{overflow}</span>')
    theme_slugs = [area_slug(t) for t in (target.get("themes") or []) if t]
    href = f'people{loc["suffix"]}.html#mentorship=mentor'
    if theme_slugs:
        href += "&themes=" + ",".join(theme_slugs)
    return (f'<div class="profile-similar profile-mentors">'
            f'<p class="profile-aside-label" data-i18n="{esc(T_MENTORS)}">{esc(T_MENTORS)}</p>'
            f'<span class="pf-facepile">{"".join(faces)}</span>'
            f'<a class="profile-similar-link" href="{esc(href)}" '
            f'data-i18n="{esc(T_SEE_MENTORS)}">{esc(T_SEE_MENTORS)}</a></div>')


# ──────────────────────── chrome extraction ────────────────────────


def extract_chrome(shell_html: str) -> dict:
    """Pull the reusable parts out of a people.*.html shell: the head
    asset block (favicons, fonts, theme script, stylesheet link), the
    nav header, the footer, and the site.js script tag. These are spliced
    verbatim so a profile page is visually identical to the directory."""
    def grab(pattern, label):
        m = re.search(pattern, shell_html, re.S)
        if not m:
            raise SystemExit(f"build-profile-pages: could not find {label} in shell")
        return m.group(1)

    # Everything from the end of the inject-seo block to </head> is the
    # asset chrome (theme script, font preloads, favicons, the versioned
    # stylesheet link). Reused so the ?v= hash always matches.
    head_assets = grab(r"<!-- seo:auto END -->(.*?)</head>", "head assets")
    nav = grab(r"(<header class=\"nav\".*?</header>)", "nav")
    footer = grab(r"(<footer class=\"footer\".*?</footer>)", "footer")
    sitejs = grab(r"(<script src=\"assets/js/site\.js[^\"]*\"[^>]*></script>)", "site.js tag")
    # Optional: the manual-translation beta ribbon. Present only in the
    # FR/DE shells (the EN shell has none). Spliced so a localised profile
    # page carries the same "manual translation, English authoritative"
    # cue as every other translated page (CLAUDE.md §1).
    rib = re.search(r'(<div class="i18n-beta-ribbon".*?</div>)', shell_html, re.S)
    return {"head_assets": head_assets.strip("\n"), "nav": nav,
            "footer": footer, "sitejs": sitejs,
            "ribbon": rib.group(1) if rib else ""}


# ──────────────────────── card rendering ────────────────────────


def render_contacts(m: dict) -> str:
    """The contact-icon row, mirroring the directory's set. Each entry is
    (href, label, css-extra, svg-inner). Brand glyphs reuse the same paths
    the directory uses so the icons match."""
    bits = []
    email = (m.get("email") or "").strip()
    if email:
        bits.append((f"mailto:{email}", "Email", "",
                     '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/></svg>'))
    web = (m.get("website") or "").strip()
    if web:
        bits.append((web, "Website", "",
                     '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 010 20M12 2a15.3 15.3 0 000 20"/></svg>'))
    orcid = (m.get("orcid") or "").strip()
    if orcid:
        bits.append((f"https://orcid.org/{orcid}", "ORCID iD", " contact-orcid",
                     '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M12 0C5.372 0 0 5.372 0 12s5.372 12 12 12 12-5.372 12-12S18.628 0 12 0zM7.369 4.378c.525 0 .947.431.947.947 0 .525-.422.947-.947.947a.95.95 0 01-.947-.947c0-.516.422-.947.947-.947zm-.722 3.038h1.444v10.041H6.647V7.416zm3.562 0h3.9c3.712 0 5.344 2.653 5.344 5.025 0 2.578-2.016 5.025-5.325 5.025h-3.919V7.416zm1.444 1.303v7.444h2.297c3.272 0 4.022-2.484 4.022-3.722 0-2.016-1.284-3.722-4.094-3.722H12.8z"/></svg>'))
    for field, label, path in (
        ("linkedin", "LinkedIn", '<path fill-rule="evenodd" d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.063 2.063 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>'),
        ("twitter", "X", '<path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>'),
        ("bluesky", "Bluesky", '<path d="M12 10.8c-1.087-2.114-4.046-6.053-6.798-7.995C2.566.944 1.561 1.266.902 1.565.139 1.908 0 3.08 0 3.768c0 .69.378 5.65.624 6.479.815 2.736 3.713 3.66 6.383 3.364.136-.02.275-.039.415-.056-.138.022-.276.04-.415.056-3.912.58-7.387 2.005-2.83 7.078 5.013 5.19 6.87-1.113 7.823-4.308.953 3.195 2.81 8.477 7.823 4.308 4.557-5.073 1.082-6.498-2.83-7.078a8.741 8.741 0 0 1-.415-.056c.14.017.279.036.415.056 2.67.297 5.568-.628 6.383-3.364.246-.829.624-5.79.624-6.479 0-.688-.139-1.86-.902-2.203-.659-.299-1.664-.621-4.3 1.24C16.046 4.748 13.087 8.687 12 10.8Z"/>'),
        ("mastodon", "Mastodon", '<path fill-rule="evenodd" d="M23.27 5.31c-.35-2.58-2.62-4.61-5.31-5C17.51.25 15.79 0 11.81 0h-.03c-3.98 0-4.83.25-5.29.31C3.88.7 1.5 2.52.92 5.13.64 6.41.61 7.84.66 9.14c.07 1.88.09 3.74.26 5.61.12 1.24.32 2.47.62 3.68.55 2.24 2.78 4.1 4.96 4.86 2.34.79 4.85.92 7.26.38.26-.06.53-.13.79-.21.59-.18 1.27-.39 1.77-.75v-1.85a20.28 20.28 0 01-4.71.54c-2.73 0-3.46-1.28-3.67-1.82a5.6 5.6 0 01-.32-1.43c1.51.36 3.07.55 4.63.55l1.13-.01c1.57-.04 3.22-.12 4.77-.42l.11-.02c2.43-.46 4.75-1.92 4.99-5.6.01-.15.03-1.52.03-1.67 0-.51.17-3.63-.02-5.55zm-3.75 9.19h-2.56V8.29c0-1.31-.55-1.98-1.67-1.98-1.23 0-1.85.79-1.85 2.35v3.4h-2.55V8.66c0-1.56-.62-2.35-1.85-2.35-1.11 0-1.67.67-1.67 1.98v6.22H4.82V8.1c0-1.31.34-2.35 1.01-3.12.7-.77 1.61-1.16 2.74-1.16 1.31 0 2.3.5 2.96 1.5l.64 1.06.64-1.06c.66-1 1.65-1.5 2.96-1.5 1.13 0 2.04.39 2.74 1.16.68.77 1.01 1.81 1.01 3.12v6.4z"/>'),
    ):
        v = (m.get(field) or "").strip()
        if v:
            bits.append((v, label, "",
                         f'<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">{path}</svg>'))
    if not bits:
        return ""
    out = ['<div class="member-contact" aria-label="Contact">']
    for href, label, extra, svg in bits:
        rel = ' target="_blank" rel="noopener"' if href.startswith("http") else ""
        out.append(f'<a href="{esc(href)}" aria-label="{esc(label)}" '
                   f'title="{esc(label)}" class="contact-link{extra}"{rel}>{svg}</a>')
    out.append("</div>")
    return "".join(out)


def render_actions(m: dict, loc: dict) -> str:
    """The founding badge plus the actionable mentor / STSM calls-to-action.

    On a full profile the mentorship + hosting badges become buttons: when the
    member has published an email they are a `mailto:` with a directory-aware
    subject and a short prefilled intro scaffold (#1171), turning the passive
    label into the "find a mentor / host" action from the directory's own
    framing. Without an email they fall back to the plain badge. Subject and
    body come from SCAFFOLDS in the page's own locale, since an href cannot be
    localised at runtime."""
    email = (m.get("email") or "").strip()
    lang = loc["lang"]

    def action(label: str, cls: str, tag: str) -> str:
        if email:
            subject = SCAFFOLDS[lang]["subject_" + tag]
            body = scaffold_body(m, tag, lang).replace("\n", "\r\n")
            href = (f"mailto:{esc(email)}?subject="
                    + urllib.parse.quote(subject)
                    + "&amp;body=" + urllib.parse.quote(body))
            return (f'<a class="{cls} is-action" href="{href}" '
                    f'data-i18n="{esc(label)}">{esc(label)}</a>')
        return f'<span class="{cls}" data-i18n="{esc(label)}">{esc(label)}</span>'

    bits = []
    if m.get("founding_contributor"):
        bits.append('<span class="founding-badge" '
                    'data-i18n="Founding contributor">Founding contributor</span>')
    for tag, cls, label in (
        ("mentor", "mentorship-badge is-offering", "Available to mentor"),
        ("mentee", "mentorship-badge is-seeking", "Seeking mentorship"),
    ):
        if tag in (m.get("mentorship") or []):
            bits.append(action(label, cls, tag))
    # At capacity (#1415) stays a plain pill even when the member publishes an
    # email: the state exists to stop the intro mail, so it must not offer one.
    if "mentor-full" in (m.get("mentorship") or []):
        bits.append('<span class="mentorship-badge is-full" '
                    'data-i18n="Mentoring, at capacity">'
                    'Mentoring, at capacity</span>')
    stsm = m.get("stsm_hosting")
    if stsm in ("yes", "ask"):
        label = "Open to hosting STSM visitors" if stsm == "ask" else "Can host STSM visitors"
        cls = "stsm-badge is-ask" if stsm == "ask" else "stsm-badge"
        bits.append(action(label, cls, "stsm"))
    if not bits:
        return ""
    return '<div class="profile-actions">' + "".join(bits) + "</div>"


# Trophy glyph for the prize pill, matching the EISS Anthology's prize chip.
_PRIZE_SVG = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" '
              'aria-hidden="true"><path d="m15.477 12.89 1.515 8.526a.5.5 0 0 1-.81.47'
              'l-3.58-2.687a1 1 0 0 0-1.197 0l-3.586 2.686a.5.5 0 0 1-.81-.469l1.514-8.526"/>'
              '<circle cx="12" cy="8" r="6"/></svg>')


def render_prize(prize: dict) -> str:
    """A gold prize pill, the NetSec counterpart of the EISS Anthology's
    `.paper-prize-chip`. Shown only here on the full profile page, never on the
    directory card. The prize name is a proper noun kept in English across
    locales (lang="en"), matching the EISS chip. Links to where the prize and
    the winning papers live."""
    if not prize:
        return ""
    award = prize.get("award") or "European Security Studies Prize"
    partner = prize.get("partner")
    title = award + (f" — EISS × {partner}" if partner else "")
    paper = prize.get("paper")
    if paper:
        title += f" — {paper}"
    href = prize.get("url") or "https://eiss-europa.com/prizes.html"
    return ('<div class="profile-prize">'
            f'<a class="profile-prize-chip" lang="en" href="{esc(href)}" '
            f'target="_blank" rel="noopener" title="{esc(title)}">'
            f'{_PRIZE_SVG}<span>{esc(award)}</span></a></div>')


def render_pubs(works: list) -> str:
    if not works:
        return ""
    items = []
    for w in works:
        title = esc(w.get("title"))
        if w.get("doi"):
            head = f'<a class="member-pubs-link" href="https://doi.org/{esc(w["doi"])}" target="_blank" rel="noopener">{title}</a>'
        else:
            head = f'<span class="member-pubs-link">{title}</span>'
        meta_bits = [str(x) for x in (w.get("year"), w.get("journal")) if x]
        meta = f' <span class="member-pubs-meta">({esc(", ".join(meta_bits))})</span>' if meta_bits else ""
        items.append(f"<li>{head}{meta}</li>")
    return ('<div class="member-pubs" aria-label="Recent publications">'
            f'<p class="member-pubs-title" data-i18n="{esc(T_PUBS)}">{esc(T_PUBS)}</p>'
            f'<ul class="member-pubs-list">{"".join(items)}</ul></div>')


def render_card(m: dict, works: list, similar: list, mentors: list, loc: dict, prize: dict | None = None) -> str:
    """The static profile card. A hero band (photo + identity + actions) over a
    two-column body: the bio + publications on the left, and a sidebar of
    research themes/regions, similar people, and contacts on the right. Reuses
    the directory's `.member-*` classes so chips and badges style identically;
    the two-column layout is scoped to `.is-profile` in site.css so directory
    cards are unaffected."""
    p = []
    p.append('<article class="member-card glass is-profile">')

    # ── Hero: photo + identity + actions ──
    p.append('<div class="profile-hero">')
    photo = (m.get("photo") or "").strip()
    p.append('<div class="member-photo">')
    if photo:
        webp = re.sub(r"\.(jpe?g|png)$", ".webp", photo, flags=re.I)
        p.append(f'<picture><source srcset="{esc(webp)}" type="image/webp">'
                 f'<img src="{esc(photo)}" alt="{esc(m.get("name"))}" loading="lazy"></picture>')
    else:
        initials = "".join(w[0] for w in (m.get("name") or "?").split()[:2]).upper()
        p.append(f'<span class="member-photo-fallback" aria-hidden="true">{esc(initials)}</span>')
    p.append("</div>")
    p.append('<div class="profile-hero-id">')
    p.append(f'<h1 class="member-name">{esc(m.get("name"))}</h1>')
    roles = m.get("roles") or []
    if roles:
        p.append(f'<p class="member-role" data-i18n-each>{esc(" · ".join(roles))}</p>')
    else:
        wg_leadership = m.get("wg_leadership") or {}
        has_wg = bool(m.get("wgs") or wg_leadership.get("lead") or wg_leadership.get("co_lead"))
        if has_wg:
            p.append('<p class="member-role is-soft" data-i18n="Working Group participant">'
                      'Working Group participant</p>')
    # A position that already names the institution ("guest lecturer at X
    # University") would otherwise print it twice in a row (#1506).
    pos = (m.get("position") or "").strip()
    aff = (m.get("affiliation") or "").strip()
    aff_parts = [x for x in (pos, "" if aff.lower() in pos.lower() else aff, m.get("country")) if x]
    if aff_parts:
        flag = ""
        if m.get("country_code"):
            flag = (f'<img class="member-flag" src="https://flagcdn.com/h20/'
                    f'{esc(m["country_code"])}.png" alt="" loading="lazy"> ')
        p.append(f'<p class="member-affiliation">{flag}'
                 f'<span class="aff-full">{esc(" · ".join(aff_parts))}</span></p>')
    wgs = m.get("wgs") or []
    lead = (m.get("wg_leadership") or {}).get("lead") or []
    colead = (m.get("wg_leadership") or {}).get("co_lead") or []
    chips = []
    for n in sorted({str(x) for x in (list(wgs) + list(lead) + list(colead))}):
        if n not in WG_NAMES:
            continue
        suffix = ""
        if n in [str(x) for x in lead]:
            suffix = " · lead"
        elif n in [str(x) for x in colead]:
            suffix = " · co-lead"
        chips.append(f'<span class="wg-chip wg-{esc(n)}">{esc(WG_NAMES[n])}{esc(suffix)}</span>')
    if chips:
        p.append('<div class="member-wgs" role="group" aria-label="Working-group membership">'
                 + "".join(chips) + "</div>")
    p.append(render_prize(prize))
    p.append(render_actions(m, loc))
    p.append("</div>")  # .profile-hero-id
    p.append("</div>")  # .profile-hero

    # ── Two-column body ──
    p.append('<div class="profile-cols">')
    p.append('<div class="profile-main">')
    bio = (m.get("bio") or "").strip()
    if bio:
        p.append(f'<p class="member-bio is-expanded">{esc(bio)}</p>')
    kws = m.get("canonical_keywords") or m.get("keywords") or []
    if kws:
        pills = "".join(f'<span class="member-keyword-chip is-static">{esc(k)}</span>'
                        for k in kws if k)
        p.append(f'<div class="member-keywords" aria-label="Research interests">{pills}</div>')
    p.append(render_pubs(works))
    p.append("</div>")  # .profile-main

    # The anthology slot is filled at runtime by the inline script below: it
    # matches this member against the EISS authors-index by name key and, on a
    # hit, injects an "In the EISS Anthology" link. Always present (hidden) so
    # the script has a mount point; the aside renders even if nothing else fills
    # it, because the slot might.
    anthology_slot = '<div class="profile-anthology-slot" hidden></div>'
    aside = (anthology_slot + render_areas(m, loc) + render_similar(m, similar, loc)
             + render_mentors(m, mentors, loc) + render_contacts(m))
    p.append(f'<aside class="profile-aside">{aside}</aside>')
    p.append("</div>")  # .profile-cols

    p.append("</article>")
    return "".join(p)


# ──────────────────────── page assembly ────────────────────────


def person_jsonld(m: dict, canonical: str) -> str:
    same = []
    if m.get("orcid"):
        same.append(f"https://orcid.org/{m['orcid']}")
    for f in ("website", "linkedin", "twitter", "bluesky", "mastodon"):
        if m.get(f):
            same.append(m[f])
    node = {"@context": "https://schema.org", "@type": "Person",
            "name": m.get("name"), "url": canonical}
    if m.get("position"):
        node["jobTitle"] = m["position"]
    if m.get("affiliation"):
        node["affiliation"] = {"@type": "Organization", "name": m["affiliation"]}
    if m.get("photo"):
        node["image"] = f"{SITE}/{m['photo'].lstrip('/')}"
    if same:
        node["sameAs"] = same
    return json.dumps(node, ensure_ascii=False, indent=2)


# Runtime enrichment: match this member against the EISS authors-index by
# name key and, on a hit, inject an "In the EISS Anthology" link into the
# sidebar slot. Done at runtime (not baked at build) for the same reason the
# ESSC programme consumes anthology-index.json live: it keeps the drift-gated
# static build a pure function of local data, and the link never goes stale.
# nk() is a faithful port of sync-bios.py::name_key(), the same canonical key
# EISS publishes in authors-index.json, so the two join cleanly. Raw string so
# the JS regex escapes (\u…, \., \s) reach the browser intact. Silent no-op on
# any fetch/parse failure, like the published-paper marker on the programme.
_ANTHOLOGY_SCRIPT = r'''<script>(function(){
var nameEl=document.querySelector('.member-name'),slot=document.querySelector('.profile-anthology-slot');
if(!nameEl||!slot)return;
function nk(s){
s=String(s||'').normalize('NFKD').replace(/[̀-ͯ]/g,'');
s=s.replace(/^(professor|prof|doctor|dr|mr|mrs|ms|mx)(?:\.\s*|\s+)/i,'');
s=s.replace(/[‘’ʼ'`]/g,'');
var t=s.split(/[^A-Za-z]+/).filter(Boolean).map(function(x){return x.toLowerCase();});
var skip={de:1,del:1,della:1,di:1,da:1,das:1,dos:1,van:1,von:1,vom:1,der:1,den:1,ter:1,ten:1,la:1,le:1,el:1,al:1,ibn:1,bin:1,bint:1,zu:1,auf:1,af:1,phd:1,jr:1,sr:1,ii:1,iii:1,iv:1,esq:1};
t=t.filter(function(x){return !skip[x];});
return t.length<2?'':t[0]+' '+t[t.length-1];
}
var key=nk(nameEl.textContent);
if(!key)return;
fetch('https://eiss-europa.com/data/authors-index.json').then(function(r){return r.ok?r.json():null;}).then(function(d){
if(!d||!d.authors)return;
var hit=null,i,a;
for(i=0;i<d.authors.length;i++){a=d.authors[i];if(a.name_key===key||(a.aliases&&a.aliases.indexOf(key)>-1)){hit=a;break;}}
if(!hit||!hit.url)return;
var label=(window.netsecT?window.netsecT('In the EISS Anthology'):'In the EISS Anthology');
var el=document.createElement('a');
el.className='profile-anthology-link';el.href=hit.url;el.target='_blank';el.rel='noopener';
el.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg><span></span>';
el.querySelector('span').textContent=label;
slot.appendChild(el);slot.hidden=false;
}).catch(function(){});
})();</script>'''


def build_page(m: dict, works: list, similar: list, mentors: list, loc_key: str,
               chrome: dict, prize: dict | None = None) -> str:
    loc = LOCALES[loc_key]
    slug = m["id"]
    rel = f"people/{slug}{loc['suffix']}.html"
    canonical = f"{SITE}/{rel}"
    name = m.get("name") or slug
    desc_bits = [x for x in (m.get("position"), m.get("affiliation"), m.get("country")) if x]
    desc = f"{name} — " + " · ".join(desc_bits) if desc_bits else name
    desc += ". NetSec directory profile, COST Action CA24154."
    hreflang = "\n".join(
        f'<link rel="alternate" hreflang="{hl}" href="{SITE}/people/{slug}{LOCALES[k]["suffix"]}.html">'
        for hl, k in (("en", "en"), ("fr", "fr"), ("de", "de"), ("x-default", "en")))
    # Per-member OG card (#1023). build-og-cards.py renders one for every
    # member carrying an id, falling back to an initials tile when there is no
    # headshot, so a member who gets a page also gets a card. The card is
    # locale-independent (name + affiliation aren't translated), so all three
    # locale pages share it.
    #
    # This used to test the PNG on disk. The cards are built at deploy time
    # now (#1716) and are not in the tree, so an existence test would point
    # all 252 pages at the generic card. Same predicate, no filesystem.
    og_image = f"{SITE}/assets/og/people/{slug}.png"

    seo = f"""<link rel="canonical" href="{canonical}">
<meta property="og:type" content="profile">
<meta property="og:site_name" content="NetSec, COST Action CA24154">
<meta property="og:title" content="{esc(name)} · NetSec directory">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{og_image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(name)} · NetSec directory">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{og_image}">
<meta name="robots" content="index, follow, max-image-preview:large">
<script type="application/ld+json">
{person_jsonld(m, canonical)}
</script>"""
    card = render_card(m, works, similar, mentors, loc, prize)
    back = (f'<p class="profile-back">'
            f'<a href="people{loc["suffix"]}.html#{esc(slug)}" '
            f'data-i18n="{esc(T_BACK)}">&larr; {esc(T_BACK)}</a>'
            f'<a class="profile-back-map" href="network-map{loc["suffix"]}.html?find={esc(slug)}" '
            f'data-i18n="{esc(T_MAP)}">{esc(T_MAP)}</a></p>')
    # site.js localises [data-i18n] chrome strings on load from the shared
    # catalog, the same window.netsecT the directory uses.
    i18n_script = (
        '<script>document.addEventListener("DOMContentLoaded",function(){'
        'if(!window.netsecT)return;'
        'document.querySelectorAll("[data-i18n]").forEach(function(e){'
        'e.textContent=window.netsecT(e.getAttribute("data-i18n"));});'
        '});</script>')
    # Point the ribbon's "see in English" link at this page's own EN
    # profile rather than the directory it links to in the shell.
    ribbon = (chrome["ribbon"].replace('href="people.html"', f'href="people/{esc(slug)}.html"') + "\n"
              if chrome.get("ribbon") else "")
    return f"""<!DOCTYPE html>
<html lang="{loc['lang']}"{loc['i18n']}>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<base href="/">
<title>{esc(name)} · NetSec, COST Action CA24154</title>
<meta name="description" content="{esc(desc)}">
{hreflang}
{seo}
{chrome['head_assets']}
</head>
<body>
{ribbon}{chrome['nav']}
<main id="main" class="profile-page">
  <div class="container profile-container">
    {card}
    {back}
  </div>
</main>
{chrome['footer']}
{chrome['sitejs']}
{i18n_script}
{_ANTHOLOGY_SCRIPT}
</body>
</html>
"""


# ──────────────────────── main ────────────────────────


def generate() -> dict[str, str]:
    bios = json.loads(BIOS.read_text(encoding="utf-8"))
    members = [m for m in bios.get("members", []) if m.get("id")]
    works_map = {}
    if WORKS.exists():
        works_map = json.loads(WORKS.read_text(encoding="utf-8")).get("works", {})
    prizes = {}
    if PRIZES.exists():
        prizes = {k: v for k, v in json.loads(PRIZES.read_text(encoding="utf-8")).items()
                  if not k.startswith("_")}
    chromes = {}
    for k, loc in LOCALES.items():
        shell = (ROOT / loc["shell"]).read_text(encoding="utf-8")
        chromes[k] = extract_chrome(shell)
    pages: dict[str, str] = {}
    for m in members:
        works = works_map.get(m["id"], [])
        # Similar-people ranking is locale-independent (names, keywords and
        # themes aren't translated), so compute it once per member.
        similar = similar_members(m, members)
        mentors = mentors_on_topics(m, members)
        prize = prizes.get(m["id"])
        for k, loc in LOCALES.items():
            rel = f"people/{m['id']}{loc['suffix']}.html"
            pages[rel] = build_page(m, works, similar, mentors, k, chromes[k], prize)
    return pages


def sitemap_urls(pages: dict[str, str]) -> list[str]:
    # One <url> per English page, with locale alternates, for sitemap.xml.
    slugs = sorted({p.split("/")[1].split(".")[0] for p in pages})
    return [f"{SITE}/people/{s}.html" for s in slugs]


def main(argv: list) -> int:
    ap = argparse.ArgumentParser()
    ap.parse_args(argv)
    pages = generate()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Remove orphaned pages (member removed) before writing the current set.
    current = {ROOT / rel for rel in pages}
    for existing in OUT_DIR.glob("*.html"):
        if existing not in current:
            existing.unlink()
            print(f"  removed orphan {existing.relative_to(ROOT)}")
    for rel, content in pages.items():
        (ROOT / rel).write_text(content, encoding="utf-8")
    print(f"Wrote {len(pages)} profile pages to {OUT_DIR.relative_to(ROOT)}/ "
          f"({len(pages) // len(LOCALES)} members × {len(LOCALES)} locales).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
