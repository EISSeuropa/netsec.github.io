"""Shared name-identity helpers for the directory build/sync scripts.

`slugify` (name -> stable id) and `name_key` (name -> first/last token pair)
were forked between sync-bios.py and sync-cost.py and had drifted: sync-cost's
copies stripped fewer honorifics and, crucially, did not strip apostrophes
before tokenising, so "Silvia D'Amato" keyed as (silvia, amato) there but
(silvia, damato) in sync-bios. Since data/bios.json is keyed with sync-bios's
version, sync-cost's fallback match mis-keyed every apostrophe surname. These
are the sync-bios (canonical) versions; both scripts now import them.

Dependency-free on purpose (only re + unicodedata): importable from any sync
script without dragging in requests, so no conditional-stub gymnastics.
"""

from __future__ import annotations

import re
import unicodedata


def slugify(name: str) -> str:
    """Stable slug from a person's name. Strips diacritics, titles, and
    apostrophes BEFORE collapsing non-alphanumerics to hyphens, so that
    e.g. "Dr Silvia D'Amato" -> "silvia-damato" (matches the existing
    seed id) rather than "silvia-d-amato"."""
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    # Strip a leading honorific. The trailing group accepts either a dot
    # (optionally followed by spaces) or whitespace, so a title glued to
    # the name with a dot and no space ("Mrs.Yanina") strips too — that
    # form otherwise kept the title in the slug and split the person into
    # a second card. A bare "Drew" is safe: the title must be followed by
    # a dot or a space, never a letter. The written-out forms (Professor,
    # Doctor) strip too, so they don't leak into the slug.
    s = re.sub(r"^(Professor|Prof|Doctor|Dr|Mr|Mrs|Ms|Mx)(?:\.\s*|\s+)", "", s)
    s = s.lower()
    # Drop apostrophes / curly quotes / similar marks first — they
    # shouldn't introduce a hyphen between adjacent letters.
    s = re.sub(r"[‘’ʼ'`]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "member"


def name_key(name: str) -> tuple[str, str] | None:
    """Reduce a name to (first_token, last_token), lowercased and
    diacritic-stripped, dropping titles and any middle names / initials.

    Used as a fallback dedup / match signal: collapses cases where the same
    person is written with a slightly different spelling ("Dr John Helferich"
    vs "Dr John N.T. Helferich"). slugify() would treat those as different ids.

    Returns None when we can't extract both a first and a last token — the
    caller treats that as "no fallback match available". Conservative on
    purpose: only the first and last token are used, so middle names,
    suffixes, and academic post-nominals don't affect the key.
    """
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    # Same honorific strip as slugify(): the trailing group also catches a
    # title glued to the name by a dot with no space ("Mrs.Yanina").
    s = re.sub(r"^(Professor|Prof|Doctor|Dr|Mr|Mrs|Ms|Mx)(?:\.\s*|\s+)", "", s, flags=re.I)
    s = re.sub(r"[‘’ʼ'`]", "", s)
    # Tokenise on any non-letter so "N.T." becomes ["N", "T"] (initials get
    # dropped by the first/last selection below).
    tokens = [t.lower() for t in re.split(r"[^A-Za-z]+", s) if t]
    POST_NOMINALS = {"phd", "jr", "sr", "ii", "iii", "iv", "esq"}
    # Strip nobiliary / patronymic particles too, so "Jéssica da Costa Pereira"
    # and a bios.json "Jéssica da Costa" reduce on their actual surname tokens.
    # Conservative list — only reliable connectors, not standalone names.
    PARTICLES = {
        "de", "del", "della", "di", "da", "das", "dos",
        "van", "von", "vom", "der", "den", "ter", "ten",
        "la", "le", "el", "al", "ibn", "bin", "bint",
        "zu", "auf", "af",
    }
    tokens = [t for t in tokens if t not in POST_NOMINALS and t not in PARTICLES]
    if len(tokens) < 2:
        return None
    return (tokens[0], tokens[-1])


if __name__ == "__main__":
    # ponytail: smallest check that fails if the honorific/apostrophe/particle
    # edge cases regress — the exact reasons these were forked and drifted.
    assert slugify("Dr Silvia D'Amato") == "silvia-damato"
    assert slugify("Mrs.Yanina Shved") == "yanina-shved"
    assert slugify("Professor Jane Doe") == "jane-doe"
    assert slugify("") == "member"
    assert name_key("Dr John N.T. Helferich") == ("john", "helferich")
    assert name_key("Silvia D'Amato") == ("silvia", "damato")
    assert name_key("Jéssica da Costa Pereira") == ("jessica", "pereira")
    assert name_key("Madonna") is None
    print("ok")
