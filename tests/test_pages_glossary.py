"""Страница «Словарь»: указатель, карточки понятий с якорями, ссылки и пустое состояние."""

import re
from datetime import date

from fastapi.testclient import TestClient

from app.core.models import Chapter, TermChapter
from app.core.view import ClubView
from app.web.app import create_app
from tests.factories import a_book, a_meeting, a_term, some_data

TODAY = date(2026, 10, 26)
NEW_TAB = 'target="_blank" rel="noopener"'


def glossary(terms=(), books=(), meetings=(), path="/glossary", base="") -> str:
    view = ClubView(some_data(books=books, meetings=meetings, glossary=terms))
    response = TestClient(create_app(view=view, today=lambda: TODAY, base=base)).get(path)
    assert response.status_code == 200, f"{path} ответил {response.status_code}"
    return response.text


def entry(html: str, term_id: str) -> str:
    found = re.search(rf'<article class="entry" id="{term_id}">.*?</article>', html, re.S)
    assert found, f"карточки {term_id} нет"
    return found.group(0)


def brooks():
    return a_book(
        "brooks",
        title="Мифический человеко-месяц",
        chapters_override=(
            Chapter(number=1, title="Смоляная яма"),
            Chapter(number=2, title="Закон Брукса", notes_url="https://github.com/s/ch2.md"),
        ),
    )


def test_the_page_has_a_heading_a_lead_and_the_glossary_section_is_current():
    html = glossary([a_term("adr", "ADR")])

    assert "<h1>Словарь</h1>" in html
    assert '<p class="lead">' in html
    assert "<title>Словарь ·" in html
    assert '<a href="/glossary" aria-current="page">Словарь</a>' in html


def test_letters_stand_cyrillic_first_and_lead_to_their_groups():
    html = glossary(
        [
            a_term("adr", "ADR"),
            a_term("conway-law", "Закон Конвея"),
            a_term("second-system", "Эффект второй системы"),
        ]
    )

    nav = re.search(r'<nav class="letters".*?</nav>', html, re.S).group(0)
    assert re.findall(r'<a href="#(letter-\d+)">([^<]+)</a>', nav) == [
        ("letter-1", "З"),
        ("letter-2", "Э"),
        ("letter-3", "A"),
    ]
    assert '<section class="letter" id="letter-3">' in html
    assert html.index('id="conway-law"') < html.index('id="second-system"') < html.index('id="adr"')


def test_a_term_card_shows_name_aliases_summary_and_its_anchor():
    card = entry(
        glossary([a_term("adr", "ADR", aliases=("Architecture Decision Record",), summary="Запись решения.")]),
        "adr",
    )

    assert '<h3 class="entry-name">ADR</h3>' in card
    assert '<p class="entry-aliases">Architecture Decision Record</p>' in card
    assert "Запись решения." in card


def test_a_term_links_to_its_article_chapters_and_related_terms():
    terms = [
        a_term(
            "brooks-law",
            "Закон Брукса",
            article="https://github.com/s/topics/brooks.md",
            chapters=(TermChapter("brooks", 2), TermChapter("brooks", 1)),
            related=("second-system",),
        ),
        a_term("second-system", "Эффект второй системы"),
    ]
    card = entry(glossary(terms, books=[brooks()]), "brooks-law")

    assert f'<a href="https://github.com/s/topics/brooks.md" {NEW_TAB}>статья</a>' in card
    assert f'<a href="https://github.com/s/ch2.md" {NEW_TAB}>Мифический человеко-месяц, гл. 2</a>' in card
    # Без конспекта глава подписана текстом, без ссылки.
    assert "Мифический человеко-месяц, гл. 1</p>" in card
    assert '<a href="#second-system">Эффект второй системы</a>' in card


def test_a_bare_term_has_no_empty_lines():
    card = entry(glossary([a_term("adr", "ADR")]), "adr")

    assert "entry-aliases" not in card
    assert "Подробно" not in card
    assert "В конспектах" not in card
    assert "Связано" not in card


def test_an_empty_glossary_explains_how_it_fills():
    html = glossary()

    assert '<p class="empty">' in html
    assert "Словарь наполняется" in html
    assert '<nav class="letters"' not in html


def test_the_glossary_has_no_list_of_meetings_per_term():
    """Пользователь отказался от списка встреч по понятию: его и нет."""
    meetings = [a_meeting("m1", "2026-10-07", title="Встреча", topics=("ADR",))]
    card = entry(glossary([a_term("adr", "ADR")], meetings=meetings), "adr")

    assert "/meetings/" not in card


def test_topic_links_respect_the_base_path():
    meetings = [a_meeting("m1", "2026-10-07", title="Встреча", topics=("ADR",))]
    html = glossary([a_term("adr", "ADR")], meetings=meetings, path="/meetings/m1", base="/bookclub_web")

    assert 'href="/bookclub_web/glossary#adr"' in html
    assert 'href="/bookclub_web/glossary"' in html


def test_a_topic_matches_its_term_by_alias_regardless_of_case():
    meetings = [a_meeting("m1", "2026-10-07", title="Встреча", topics=("adr",))]
    html = glossary(
        [a_term("adr", "Запись архитектурного решения", aliases=("ADR",), summary="Коротко.")],
        meetings=meetings,
        path="/meetings/m1",
    )

    assert '<a href="/glossary#adr" aria-describedby="topic-tip-1">adr</a>' in html
    assert 'role="tooltip" id="topic-tip-1">Коротко.</span>' in html
