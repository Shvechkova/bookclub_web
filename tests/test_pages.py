"""Страницы сайта: навигация, «Сейчас», лента истории, страница встречи."""

import re
from datetime import date

from fastapi.testclient import TestClient

from app.core.models import BookStatus, Outcome, Quote
from app.core.view import ClubView
from app.web.app import create_app
from tests.factories import a_book, a_club, a_meeting, a_space, a_term, some_data

TODAY = date(2026, 9, 21)


def client(books=(), meetings=(), club=None, today=TODAY) -> TestClient:
    view = ClubView(some_data(books=books, meetings=meetings, club=club))
    return TestClient(create_app(view=view, today=lambda: today))


def page(path, **kwargs) -> str:
    response = client(**kwargs).get(path)
    assert response.status_code == 200, f"{path} ответил {response.status_code}"
    return response.text


# --- 4.1 навигация и адреса --------------------------------------------------


def test_every_page_carries_the_same_three_sections():
    setup = dict(
        club=a_club(telegram="https://t.me/kabanya"),
        books=[a_book("b1", status=BookStatus.CLOSED)],
        meetings=[a_meeting("m1", "2026-09-09", book="b1", closed=(1,))],
    )

    for path in ("/", "/history", "/glossary", "/about", "/meetings/m1", "/books/b1"):
        html = page(path, **setup)
        assert 'href="/"' in html
        assert 'href="/history"' in html
        assert 'href="/glossary"' in html
        assert 'href="/shelf"' not in html
        assert 'href="/about"' in html
        assert "https://t.me/kabanya" in html


def test_every_page_ends_with_a_footer_linking_to_the_space():
    setup = dict(
        club=a_club(space=a_space()),
        books=[a_book("b1", status=BookStatus.CLOSED)],
        meetings=[a_meeting("m1", "2026-09-09", book="b1", closed=(1,))],
    )

    for path in ("/", "/history", "/about", "/meetings/m1", "/books/b1"):
        html = page(path, **setup)
        assert "<footer" in html
        assert "https://s4m.space/" in html
        assert "https://t.me/s4m_space" in html
        assert "https://t.me/+chat" in html


def test_without_a_space_the_footer_is_not_shown():
    html = page("/about")

    assert "<footer" not in html


def test_the_current_section_is_marked_as_active():
    html = page("/history", meetings=[a_meeting("m1", "2026-09-09", title="Встреча")])

    assert 'aria-current="page"' in html


def test_a_link_to_a_meeting_opens_that_meeting_directly():
    html = page(
        "/meetings/m1",
        meetings=[a_meeting("m1", "2026-09-09", title="ADR-дуэль")],
    )

    assert "ADR-дуэль" in html


def test_an_unknown_meeting_is_not_found():
    response = client().get("/meetings/нет-такой")

    assert response.status_code == 404


# --- 4.2 раздел «Сейчас» -----------------------------------------------------


def test_now_shows_the_upcoming_meeting():
    html = page(
        "/",
        books=[a_book("b1", chapters=12, title="Мифический человеко-месяц")],
        meetings=[
            a_meeting(
                "next",
                "2026-09-23",
                book="b1",
                planned=(1, 2),
                fmt="Лайтнинги",
                host="Настя",
            )
        ],
    )

    assert "23 сентября" in html
    assert "19:30" in html
    assert "хакспейс s4m.space" in html
    assert "Дом77, Ленинградская 77, 4 этаж, комната 413, Самара" in html
    assert "Настя" in html
    assert "Мифический человеко-месяц" in html
    assert "главы 1–2" in html
    assert "Лайтнинги" in html


def test_now_shows_how_much_of_the_book_is_done():
    html = page(
        "/",
        books=[a_book("b1", chapters=12, taken=(1, 3, 5))],
        meetings=[
            a_meeting("past", "2026-09-09", book="b1", closed=(1,)),
            a_meeting("next", "2026-09-23", book="b1", planned=(3,)),
        ],
    )

    assert "1 из 3" in html


def test_now_says_plainly_when_no_meeting_is_scheduled():
    html = page(
        "/",
        books=[a_book("b1", chapters=12)],
        meetings=[a_meeting("past", "2026-09-09", book="b1", closed=(1,))],
    )

    assert "не назначена" in html
    assert "9 сентября" in html


# --- 4.3 лента истории -------------------------------------------------------


def test_history_groups_meetings_under_their_books():
    html = page(
        "/history",
        books=[
            a_book("b1", number=1, status=BookStatus.CLOSED, title="Первая книга"),
            a_book("b2", number=2, status=BookStatus.READING, title="Вторая книга"),
        ],
        meetings=[
            a_meeting("m1", "2026-01-07", book="b1", closed=(1,)),
            a_meeting("m2", "2026-02-04", book="b2", closed=(1,)),
        ],
    )

    assert html.index("Вторая книга") < html.index("Первая книга")
    assert html.count('<span class="num">#1</span>') == 2, "каждая книга считает встречи с единицы"


def test_history_shows_a_meeting_outside_any_book_in_place():
    html = page(
        "/history",
        books=[a_book("b1", number=1, status=BookStatus.CLOSED)],
        meetings=[
            a_meeting("m1", "2026-01-07", book="b1", closed=(1,)),
            a_meeting("lone", "2026-02-04", title="Голосование за книгу", fmt="Голосование"),
        ],
    )

    assert "Голосование за книгу" in html


def test_history_shows_the_period_of_a_book_without_meetings():
    html = page(
        "/history",
        books=[
            a_book(
                "archive",
                number=1,
                status=BookStatus.CLOSED,
                title="Книга из архива",
                period="весна 2025",
            )
        ],
    )

    assert "Книга из архива" in html
    assert "весна 2025" in html


# --- 4.4 страница встречи ----------------------------------------------------


def test_an_upcoming_meeting_shows_its_plan_and_announcement():
    html = page(
        "/meetings/next",
        books=[a_book("b1", chapters=12, title="Брукс")],
        meetings=[
            a_meeting(
                "next",
                "2026-09-23",
                book="b1",
                planned=(1, 7),
                announce=("Кто видел, как кидали людей на горящий проект",),
            )
        ],
    )

    assert "главы 1, 7" in html
    assert "Кто видел, как кидали людей на горящий проект" in html
    assert "Итоги" not in html


def test_a_past_meeting_shows_its_outcome_and_quote():
    outcome = Outcome(
        agreed="Согласились с законом Брукса.",
        argued="Спорили про вторую систему.",
        taken="Забираем приём с ранними оценками.",
        quote=Quote(text="Серебряной пули нет.", chapter=16),
    )
    html = page(
        "/meetings/past",
        books=[a_book("b1", chapters=19, title="Брукс")],
        meetings=[
            a_meeting("past", "2026-09-09", book="b1", closed=(16,), outcome=outcome)
        ],
    )

    assert "Согласились с законом Брукса." in html
    assert "Серебряной пули нет." in html
    assert "глава 16" in html


def test_meeting_topics_link_to_the_glossary_and_nowhere_else():
    view = ClubView(
        some_data(
            meetings=[a_meeting("m1", "2026-09-09", title="Встреча", topics=("Саги", "Кворум"))],
            glossary=[a_term("saga", "Сага", aliases=("Саги",), summary="Цепочка шагов.")],
        )
    )
    html = TestClient(create_app(view=view, today=lambda: TODAY)).get("/meetings/m1").text

    topics = html[html.index('<p class="topics">'):]
    topics = topics[: topics.index("</p>")]
    assert '<a href="/glossary#saga" aria-describedby="topic-tip-1">Саги</a>' in topics
    assert 'id="topic-tip-1">Цепочка шагов.</span>' in topics
    assert "Кворум" in topics and ">Кворум</a>" not in topics
    assert "/shelf" not in html


def test_the_site_has_four_sections_and_the_feed_is_called_shelf():
    html = page("/history")

    nav = html[html.index('<nav class="sections"'):]
    nav = nav[: nav.index("</nav>")]
    assert nav.count("<a ") == 4
    assert re.findall(r">([^<]+)</a>", nav) == ["Сейчас", "Полка", "Словарь", "О клубе"]
    assert '<a href="/history" aria-current="page">Полка</a>' in nav
    assert "История" not in nav
    assert "<h1>Полка</h1>" in html
    assert "<title>Полка ·" in html


def test_the_concept_catalogue_section_is_gone():
    for path in ("/shelf", "/shelf/topics"):
        assert client().get(path).status_code == 404, path


def test_a_past_meeting_without_an_outcome_says_so():
    html = page(
        "/meetings/past",
        books=[a_book("b1", chapters=12)],
        meetings=[a_meeting("past", "2026-09-09", book="b1", closed=(1,))],
    )

    assert "итоги" in html.lower()
    assert "не записаны" in html
