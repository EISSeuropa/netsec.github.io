#!/usr/bin/env python3
"""The aggregate visitor counter's script tag, in one place.

GoatCounter (#727): hosted in the Netherlands, sets no cookies, keeps
no per-visitor identifier, and needs one async tag. It exists so the
Action can evidence dissemination reach in COST reporting, which
"the website is online" does not do.

Two generators stamp the tag, because they build the site's two kinds
of page from different code: `inject-seo.py` writes the managed head
block on every top-level page, and `build-profile-pages.py` writes its
own head for each /people/<slug> profile. The tag lives here so the
site code is pasted once rather than kept in step across both.

`SITE_CODE` is the subdomain of the GoatCounter account, the "xxx" in
https://xxx.goatcounter.com. While it is empty `tag()` returns nothing
and no page carries a counter, which is what keeps the privacy notice
honest: the notice describes the collection, so the notice and the
account land together.
"""
from __future__ import annotations

# Set to the GoatCounter account subdomain to switch the counter on.
SITE_CODE = ""

ENDPOINT = "https://{code}.goatcounter.com/count"
COUNTER_JS = "https://gc.zgo.at/count.js"


def tag() -> str:
    """The script tag, or an empty string while no account is set."""
    if not SITE_CODE:
        return ""
    return (
        f'<script data-goatcounter="{ENDPOINT.format(code=SITE_CODE)}"'
        f' async src="{COUNTER_JS}"></script>'
    )


def lines() -> list[str]:
    """The tag as head lines, ready to splice into a generated block.

    Empty while no account is set, so a generator can extend its line
    list unconditionally.
    """
    snippet = tag()
    if not snippet:
        return []
    return ["", "<!-- Aggregate visitor statistics (cookieless) -->", snippet]
