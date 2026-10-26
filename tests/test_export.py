"""Выгрузка сайта в статику.

Сайт читается и не имеет интерактива, поэтому те же шаблоны раскладываются в
файлы. Главное, что тут проверяется, — все ссылки продолжают вести в
существующие файлы: на статике «/history» обязано быть «/history/index.html».
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from app.core.models import BookStatus
from app.core.view import ClubView
from app.web.export import export_site
from app.core.models import TermChapter
from tests.factories import a_book, a_club, a_meeting, a_term, some_data

TODAY = date(2026, 9, 21)


def a_site() -> ClubView:
    club = a_club(telegram="https://t.me/example", marquee=("КНИЖНАЯ СРЕДА",))
    books = [
        a_book("closed-one", number=1, status=BookStatus.CLOSED, notes_url="https://notes/1"),
        a_book("reading-one", number=2, status=BookStatus.READING),
    ]
    meetings = [
        a_meeting("m1", "2026-09-09", book="closed-one", closed=(1,), topics=("Саги",)),
        a_meeting("m2", "2026-09-23", book="reading-one", planned=(1,)),
        a_meeting("lone", "2026-09-16", title="ADR-дуэль"),
    ]
    # Тема «Саги» есть в словаре: плашка и тема встречи ведут на его якорь,
    # и проверка ссылок ниже заодно проверяет, что страница словаря выгружена.
    glossary = [
        a_term("saga", "Саги", chapters=(TermChapter("closed-one", 1),), related=("adr",)),
        a_term("adr", "ADR"),
    ]
    return ClubView(some_data(books=books, meetings=meetings, club=club, glossary=glossary))


def broken_links(root: Path, base: str = "") -> list[str]:
    """Внутренние ссылки, которым не соответствует ни один выгруженный файл."""
    broken = []
    for page in root.rglob("*.html"):
        for link in re.findall(r'(?:href|src)="(/[^"#?]*)"', page.read_text(encoding="utf-8")):
            if base and not link.startswith(base + "/") and link != base:
                broken.append(f"{page.relative_to(root)} -> {link} (мимо базового пути)")
                continue
            relative = link[len(base):].strip("/")
            target = root / relative if relative else root
            if target.is_dir() or target.suffix == "":
                target = (root / relative) / "index.html"
            if not target.exists():
                broken.append(f"{page.relative_to(root)} -> {link}")
    return sorted(set(broken))


def test_export_writes_a_file_for_every_address(tmp_path):
    export_site(a_site(), tmp_path, today=TODAY)

    expected = [
        "index.html",
        "history/index.html",
        "glossary/index.html",
        "about/index.html",
        "meetings/m1/index.html",
        "meetings/m2/index.html",
        "meetings/lone/index.html",
        "books/closed-one/index.html",
        "books/reading-one/index.html",
    ]
    for relative in expected:
        assert (tmp_path / relative).exists(), f"не выгружено: {relative}"


def test_export_copies_styles_but_not_the_game(tmp_path):
    """Игра живёт по своему адресу: копии в выгрузке нет."""
    export_site(a_site(), tmp_path, today=TODAY)

    assert (tmp_path / "static" / "style.css").exists()
    assert (tmp_path / "static" / "logo-mark.png").exists()
    assert not (tmp_path / "game").exists()


def test_every_internal_link_leads_to_a_file_that_exists(tmp_path):
    export_site(a_site(), tmp_path, today=TODAY)

    assert broken_links(tmp_path) == []


def test_export_is_repeatable(tmp_path):
    export_site(a_site(), tmp_path, today=TODAY)
    first = (tmp_path / "index.html").read_text(encoding="utf-8")

    export_site(a_site(), tmp_path, today=TODAY)
    second = (tmp_path / "index.html").read_text(encoding="utf-8")

    assert first == second


# --- сайт во вложенной папке (GitHub Pages для проекта) ---------------------


def test_export_can_live_under_a_subpath(tmp_path):
    export_site(a_site(), tmp_path, today=TODAY, base="/bookclub_web")
    home = (tmp_path / "index.html").read_text(encoding="utf-8")

    assert 'href="/bookclub_web/history"' in home
    assert 'href="/bookclub_web/static/style.css"' in home
    assert 'href="/history"' not in home
    assert 'src="/static/' not in home


def test_links_under_a_subpath_still_lead_to_files(tmp_path):
    export_site(a_site(), tmp_path, today=TODAY, base="/bookclub_web")

    assert broken_links(tmp_path, base="/bookclub_web") == []


# --- карта сайта -------------------------------------------------------------


def test_export_writes_a_sitemap_and_robots(tmp_path):
    export_site(
        a_site(), tmp_path, today=TODAY, base="/bookclub_web", origin="https://example.org"
    )

    sitemap = (tmp_path / "sitemap.xml").read_text(encoding="utf-8")
    robots = (tmp_path / "robots.txt").read_text(encoding="utf-8")

    assert "<loc>https://example.org/bookclub_web/</loc>" in sitemap
    assert "<loc>https://example.org/bookclub_web/about</loc>" in sitemap
    assert "<loc>https://example.org/bookclub_web/glossary</loc>" in sitemap
    assert "<loc>https://example.org/bookclub_web/meetings/m1</loc>" in sitemap
    assert "<loc>https://example.org/bookclub_web/books/closed-one</loc>" in sitemap
    assert "Sitemap: https://example.org/bookclub_web/sitemap.xml" in robots


def test_export_without_a_site_address_writes_no_sitemap(tmp_path):
    export_site(a_site(), tmp_path, today=TODAY)

    assert not (tmp_path / "sitemap.xml").exists()
    assert not (tmp_path / "robots.txt").exists()


def test_a_trailing_slash_in_the_base_is_ignored(tmp_path):
    export_site(a_site(), tmp_path, today=TODAY, base="/bookclub_web/")
    home = (tmp_path / "index.html").read_text(encoding="utf-8")

    assert 'href="/bookclub_web/history"' in home
    assert "/bookclub_web//" not in home


def test_every_link_into_the_glossary_finds_its_term(tmp_path):
    """Якорь без понятия на статике молча открывает словарь сверху."""
    export_site(a_site(), tmp_path, today=TODAY)
    glossary = (tmp_path / "glossary" / "index.html").read_text(encoding="utf-8")
    anchors = set(re.findall(r' id="([^"]+)"', glossary))

    wanted = set()
    for page in tmp_path.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        wanted |= set(re.findall(r'href="/glossary#([^"]+)"', text))
    wanted |= set(re.findall(r'href="#([^"]+)"', glossary))

    assert wanted, "ни одна страница не ведёт в словарь"
    assert wanted <= anchors, wanted - anchors
