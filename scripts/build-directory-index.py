#!/usr/bin/env python3
"""Build directory-index.json — the public cross-site contract for linking
NetSec Directory members from other surfaces.

This is the deliberate, slim mirror of the `anthology-index.json` NetSec
already consumes from the EISS site: one row per directory member carrying
the canonical name key, any name aliases, the slug, and the absolute
profile-page URL. A consuming surface (notably the EISS Anthology, see
EISSeuropa/EISSeuropa.github.io#966) matches its name-only author records
against this index by name key, then links to `url`.

Why a purpose-built index rather than letting consumers read data/bios.json
directly: it is a stable contract decoupled from the internal bio schema, it
publishes the profile URL so a consumer never hardcodes the
`/people/<slug>.html` scheme (which would change if the directory cards ever
converge onto the profile pages, see #72), and it carries the canonical
`name_key` so a consumer can skip re-deriving it (and the middle-initial trap
that comes with that).

Usage:
  python3 scripts/build-directory-index.py            # write directory-index.json
  python3 scripts/build-directory-index.py --check    # exit 1 if it would change

The output is a pure function of data/bios.json (the freshness stamp mirrors
the source's `generated_at`, which only advances on substantive member
changes), so re-runs are idempotent and `--check` gates drift. The weekly
bios-sync regenerates it alongside the other derived artifacts.
"""
from __future__ import annotations

import argparse
import importlib.util
import io
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIOS = ROOT / "data" / "bios.json"
OUT = ROOT / "directory-index.json"
SITE = "https://netsec-cost.eu"

# Reuse sync-bios.py's canonical name_key() so the published key can never
# drift from the one the directory itself matches speakers on. name_key()
# itself is pure stdlib (re + unicodedata), but sync-bios.py guards a
# top-level `import requests` with a sys.exit() when the dependency is
# absent — and this index only reads JSON, so a consumer (CI's data-shape
# job) running it without the network deps installed would otherwise crash
# at import. Only when `requests` is genuinely unavailable do we register a
# minimal stub so that guard passes (we never call anything on it, only
# name_key()). When `requests` IS installed we import the real one, so we
# never shadow it for anything else sharing this interpreter — notably the
# combined pytest session, where other tests monkeypatch real requests.
try:
    import requests  # noqa: F401  (populate sys.modules with the real module if present)
except ImportError:
    sys.modules["requests"] = types.ModuleType("requests")
_spec = importlib.util.spec_from_file_location("sync_bios", ROOT / "scripts" / "sync-bios.py")
_sb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sb)
name_key = _sb.name_key


def build() -> str:
    data = json.load(io.open(BIOS, encoding="utf-8"))
    members = data["members"] if isinstance(data, dict) and "members" in data else data
    rows = []
    for m in members:
        slug = m.get("id")
        name = m.get("name")
        if not slug or not name:
            continue
        nk = name_key(name)  # (first, last) tuple, or None
        photo = (m.get("photo") or "").strip()
        rows.append({
            "name": name,
            # Joined canonical key, e.g. "mattia sguazzini". null when a first
            # and last token can't both be extracted (single-token names).
            "name_key": (nk[0] + " " + nk[1]) if nk else None,
            "aliases": list(m.get("name_aliases") or []),
            "slug": slug,
            "url": f"{SITE}/people/{slug}.html",
            "orcid": m.get("orcid") or None,  # for completeness, not a join key
            # Display fields so a consumer can render an informative chip (a
            # photo + who the person is) rather than a bare link. All optional;
            # null when the member hasn't supplied them.
            "role": " · ".join(m["roles"]) if m.get("roles") else None,
            "affiliation": m.get("affiliation") or None,
            "photo": f"{SITE}/{photo.lstrip('/')}" if photo else None,
        })
    rows.sort(key=lambda r: r["slug"])
    index = {
        "_documentation": "Public cross-site contract for linking NetSec Directory members. "
                          "Match author names against members[].name_key (or your own key over "
                          "members[].name), then link to members[].url. role, affiliation and "
                          "photo are optional display fields (null when unset) so a consumer can "
                          "render an informative chip rather than a bare link; orcid is for "
                          "completeness, not a join key. See scripts/build-directory-index.py.",
        "generated_at": data.get("generated_at") if isinstance(data, dict) else None,
        "source": f"{SITE}/data/bios.json",
        "count": len(rows),
        "members": rows,
    }
    return json.dumps(index, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate directory-index.json (cross-site member contract).")
    ap.add_argument("--check", action="store_true", help="exit 1 if directory-index.json would change")
    args = ap.parse_args()

    new = build()
    current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    n = json.loads(new)["count"]
    if args.check:
        if new != current:
            print("✗ directory-index.json is stale — run scripts/build-directory-index.py", file=sys.stderr)
            return 1
        print(f"✓ directory-index.json current ({n} members).")
        return 0
    OUT.write_text(new, encoding="utf-8")
    print(f"✓ wrote directory-index.json ({n} members).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
