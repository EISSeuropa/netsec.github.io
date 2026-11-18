#!/usr/bin/env python3
"""Test suite for scripts/build-welcome-card.py (browser-free, #2237).

Run standalone:  /usr/bin/python3 scripts/test-build-welcome-card.py
Or under pytest: python3 -m pytest scripts/test-build-welcome-card.py -q
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

_MOD = Path(__file__).resolve().parent / "build-welcome-card.py"
_spec = importlib.util.spec_from_file_location("build_welcome_card", _MOD)
bwc = importlib.util.module_from_spec(_spec)
sys.modules["build_welcome_card"] = bwc
_spec.loader.exec_module(bwc)
sp = bwc.sp


def _member(i: int, **kw) -> dict:
    m = {"id": f"member-{i:02d}", "name": f"Dr Example Person{i:02d}", "joined": "2026-11-23"}
    m.update(kw)
    return m


def _tiles(markup: str) -> int:
    return len(re.findall(r'<div class="face">', markup))


def test_display_name_drops_the_honorific():
    assert bwc.display_name("Prof. Carmen Márquez Carrasco") == "Carmen Márquez Carrasco"
    assert bwc.display_name("Dr Mir Hassan") == "Mir Hassan"
    assert bwc.display_name("Ms Skender Jashari") == "Skender Jashari"
    assert bwc.display_name("Dr") == "Dr"  # a lone title is kept rather than emptied


def test_one_member():
    html = bwc.card_markup([_member(1)])
    assert _tiles(html) == 1
    assert "One new member" in html and "Example Person01" in html
    assert '<div class="more">' not in html


def test_seven_members_all_pictured():
    html = bwc.card_markup([_member(i) for i in range(7)])
    assert _tiles(html) == 7
    assert "Seven new members" in html and 'class="more"' not in html


def test_eight_members_six_faces_and_a_plus_two_tile():
    html = bwc.card_markup([_member(i) for i in range(8)])
    assert _tiles(html) == 7
    assert '<div class="more">+2</div>' in html and "more members" in html
    assert "Person06" not in html


def test_plus_one_reads_more_member():
    assert "more member<" in bwc.more_html(1) and "+1" in bwc.more_html(1)


def test_member_without_photo_gets_initials():
    html = bwc.face_html(_member(1, name="Dr Mir Hassan", photo="assets/images/people/nobody-here.jpg"))
    assert '<div class="initials">MH</div>' in html and "<img" not in html


def test_member_with_photo_gets_it():
    photo = next(p for p in (bwc.ROOT / "assets" / "images" / "people").glob("*.jpg"))
    rel = photo.relative_to(bwc.ROOT).as_posix()
    html = bwc.face_html(_member(1, photo=rel))
    assert f'<img src="/{rel}"' in html


def test_names_are_escaped():
    html = bwc.card_markup([_member(1, name="Dr <b>Bold</b> & Co")])
    assert "<b>Bold</b>" not in html and "&lt;b&gt;Bold&lt;/b&gt; &amp; Co" in html


def test_card_path_follows_the_members():
    a = sp.welcome_card_path([_member(1), _member(2)])
    assert a == sp.welcome_card_path([_member(1), _member(2)])
    assert a != sp.welcome_card_path([_member(1)])
    assert a.parent == sp.WELCOME_CARDS and a.suffix == ".png"


def test_card_directory_is_gitignored():
    assert "assets/og/welcome/" in (bwc.ROOT / ".gitignore").read_text(encoding="utf-8")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")


def _photo() -> str:
    return next((bwc.ROOT / "assets" / "images" / "people").glob("*.jpg")).relative_to(bwc.ROOT).as_posix()


def test_members_with_a_photo_are_pictured_first():
    members = [_member(1), _member(2, photo=_photo()), _member(3), _member(4, photo=_photo())]
    faces = sp.welcome_card_faces(members)
    assert [m["id"] for m in faces] == ["member-02", "member-04"]
    html = bwc.card_markup(members)
    assert _tiles(html) == 3 and '<div class="more">+2</div>' in html
    assert '<div class="initials">' not in html


def test_seven_with_photos_and_one_without_shows_six_and_plus_two():
    members = [_member(i, photo=_photo()) for i in range(7)] + [_member(7)]
    faces = sp.welcome_card_faces(members)
    assert len(faces) == 6 and all(sp.has_photo(m) for m in faces)
    assert '<div class="more">+2</div>' in bwc.card_markup(members)


def test_everyone_with_a_photo_up_to_seven_is_pictured():
    members = [_member(i, photo=_photo()) for i in range(7)]
    assert sp.welcome_card_faces(members) == members


def test_nobody_with_a_photo_falls_back_to_initials():
    members = [_member(1), _member(2)]
    assert sp.welcome_card_faces(members) == members
    assert bwc.card_markup(members).count('<div class="initials">') == 2
    assert sp.welcome_card_alt(members).startswith("Welcome to the NetSec Directory: tiles for the two new members")


def test_one_photo_among_many_without():
    members = [_member(1)] + [_member(2, photo=_photo())] + [_member(i) for i in range(3, 12)]
    html = bwc.card_markup(members)
    assert _tiles(html) == 2 and '<div class="more">+10</div>' in html
    assert sp.welcome_card_alt(members) == ("Welcome to the NetSec Directory: photos of one of the 11 new "
                                            "members, Dr Example Person02, and a tile for ten more")
