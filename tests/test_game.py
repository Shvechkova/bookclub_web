"""Игра-разминка раздаётся сайтом.

`tyzharchitector` подключён закреплённой версией и отдаётся с нашего домена:
свой код у него остаётся свой, мы его только раздаём.
"""

from datetime import date

from fastapi.testclient import TestClient

from app.core.view import ClubView
from app.web.app import GAME_PATH, create_app
from tests.factories import some_data

TODAY = date(2026, 9, 21)


def empty_club() -> TestClient:
    view = ClubView(some_data(books=(), meetings=()))
    return TestClient(create_app(view=view, today=lambda: TODAY))


def test_the_game_opens_on_our_own_domain():
    response = empty_club().get(GAME_PATH)

    assert response.status_code == 200
    assert "Тыжархитектор" in response.text


def test_the_game_does_not_depend_on_club_data():
    """Данных клуба нет вовсе, а разминка всё равно работает."""
    client = empty_club()

    assert client.get(GAME_PATH).status_code == 200
    assert client.get(GAME_PATH + "src/game-core.js").status_code == 200
    assert client.get(GAME_PATH + "style.css").status_code == 200


def test_the_home_page_sends_the_visitor_to_the_game_on_this_site():
    html = empty_club().get("/").text

    assert f'href="{GAME_PATH}"' in html
    assert "github.com" not in html
