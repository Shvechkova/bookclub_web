"""Игра-разминка: главная зовёт в неё ссылкой, сайт её у себя не держит.

`tyzharchitector` — отдельный проект со своим адресом. Адрес и пара строк об
игре приходят из данных клуба, копии игры на сайте нет.
"""

import re
from datetime import date

from fastapi.testclient import TestClient

from app.core.models import Warmup
from app.core.view import ClubView
from app.web.app import create_app
from tests.factories import a_club, some_data

TODAY = date(2026, 9, 21)
GAME = Warmup(
    name="Тыжархитектор",
    lead="Карточный тренажёр по архитектуре: тянешь проблему системы — подбираешь решение",
    url="https://shvechkova.github.io/tyzharchitector/",
)


def client(warmup=None) -> TestClient:
    view = ClubView(some_data(books=(), meetings=(), club=a_club(warmup=warmup)))
    return TestClient(create_app(view=view, today=lambda: TODAY))


def warmup_block(html: str) -> str | None:
    found = re.search(r'<aside class="warmup"[^>]*>.*?</aside>', html, re.S)
    return found.group(0) if found else None


def test_the_home_page_highlights_the_warmup_game_with_a_lead():
    block = warmup_block(client(GAME).get("/").text)

    assert block, "блока разминки нет"
    assert "Разминка" in block
    assert "Тыжархитектор" in block
    assert "Карточный тренажёр по архитектуре" in block


def test_the_play_button_leads_to_the_game_address_from_the_data():
    block = warmup_block(client(GAME).get("/").text)

    button = re.search(r"<a [^>]*>Играть</a>", block).group(0)
    assert f'href="{GAME.url}"' in button
    assert "button" in button
    # github.io — не github.com: игра открывается в той же вкладке.
    assert 'target="_blank"' not in button


def test_without_a_warmup_there_is_no_block():
    html = client().get("/").text

    assert warmup_block(html) is None
    assert "Играть" not in html


def test_the_site_no_longer_serves_the_game():
    assert client(GAME).get("/game/").status_code == 404
