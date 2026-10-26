"""«О клубе», пустые состояния и отсутствие входа."""

from datetime import date

from fastapi.testclient import TestClient

from app.core.models import BookStatus
from app.core.view import ClubView
from app.web.app import create_app
from tests.factories import a_book, a_club, a_meeting, a_space, some_data

TODAY = date(2026, 9, 21)


def client(books=(), meetings=(), club=None) -> TestClient:
    view = ClubView(some_data(books=books, meetings=meetings, club=club))
    return TestClient(create_app(view=view, today=lambda: TODAY))


def page(path, **kwargs) -> str:
    response = client(**kwargs).get(path)
    assert response.status_code == 200
    return response.text


# --- 4.8 о клубе -------------------------------------------------------------


def test_about_explains_the_club_and_how_a_meeting_goes():
    html = page(
        "/about",
        club=a_club(
            about=(
                "Читаем техническую литературу и спорим о ней вслух.",
                "Собираемся только очно, в Самаре.",
            ),
            routine=("Разбираем главы вслух.", "Ведущий у каждой встречи свой."),
            telegram="https://t.me/kabanya",
        ),
    )

    assert "Читаем техническую литературу и спорим о ней вслух." in html
    assert "Собираемся только очно, в Самаре." in html
    assert "Разбираем главы вслух." in html
    assert "Ведущий у каждой встречи свой." in html
    assert "Дом77, Ленинградская 77, 4 этаж, комната 413, Самара" in html
    assert "среда, раз в две недели" in html
    assert "90 минут" in html
    assert "https://t.me/kabanya" in html


def test_about_links_to_the_space_and_to_the_club_thread_in_it():
    html = page("/about", club=a_club(space=a_space()))

    assert "https://s4m.space/" in html
    assert "https://t.me/s4m_space" in html
    assert "https://t.me/+chat" in html
    assert "https://t.me/c/1/2" in html


# --- 4.9 пустые состояния ----------------------------------------------------


def test_an_empty_history_explains_what_fills_it():
    html = page("/history")

    assert 'class="empty"' in html
    assert "встречами" in html


def test_every_empty_state_uses_the_same_markup():
    # «Форматы» с пустым состоянием ушли со страницы «О клубе»; пустая
    # лента остаётся единственной.
    assert page("/history").count('class="empty"') >= 1


# --- 4.10 сайт только для чтения ---------------------------------------------


def test_no_page_offers_a_login_or_changes_anything():
    setup = dict(
        club=a_club(telegram="https://t.me/kabanya"),
        books=[a_book("b1", status=BookStatus.CLOSED)],
        meetings=[a_meeting("m1", "2026-01-07", book="b1", closed=(1,), topics=("Саги",))],
    )
    paths = ("/", "/history", "/about", "/meetings/m1", "/books/b1")

    for path in paths:
        html = page(path, **setup)
        assert "<form" not in html
        assert "<input" not in html
        # Единственная кнопка — бургер меню: она раскрывает разделы и ничего не меняет.
        assert html.count("<button") == html.count('<button class="menu-toggle"')
        assert "Войти" not in html
        assert "Записаться" not in html
