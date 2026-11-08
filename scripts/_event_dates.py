"""Event dates written out in English, French and German.

Shared by inject-seo.py (which reads and checks dates in page copy),
sync-indico.py and sync-calendar-dates.py (which rewrite an event's
displayDate when its start or end moves). The forms are the ones
data/events.json already uses: "8–11 June 2027", "8–11 juin 2027",
"8.–11. Juni 2027", "30 June – 2 July 2026", "13 September 2026".
"""
from __future__ import annotations

from datetime import date

MONTHS = {
    "en": ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"],
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
           "août", "septembre", "octobre", "novembre", "décembre"],
    "de": ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
           "August", "September", "Oktober", "November", "Dezember"],
}


def _day(lang: str, d: date) -> str:
    if lang == "de":
        return f"{d.day}."
    if lang == "fr" and d.day == 1:
        return "1er"
    return str(d.day)


def format_day(lang: str, d: date) -> str:
    """'7 December 2026', '7 décembre 2026', '7. Dezember 2026'."""
    return f"{_day(lang, d)} {MONTHS[lang][d.month - 1]} {d.year}"


def format_range(lang: str, start: date, end: date) -> str:
    """The displayDate form of an event running from start to end."""
    if end <= start:
        return format_day(lang, start)
    if (start.year, start.month) == (end.year, end.month):
        return f"{_day(lang, start)}–{format_day(lang, end)}"
    if start.year == end.year:
        return f"{_day(lang, start)} {MONTHS[lang][start.month - 1]} – {format_day(lang, end)}"
    return f"{format_day(lang, start)} – {format_day(lang, end)}"


def display_dates(start: str, end: str) -> dict[str, str]:
    """displayDate for every locale from two ISO stamps ('2027-06-08T09:00')."""
    a, b = date.fromisoformat(start[:10]), date.fromisoformat((end or start)[:10])
    return {lang: format_range(lang, a, b) for lang in MONTHS}
