"""Вёрстка на узком экране — проверка настоящим браузером.

Прокрутка и переносы — свойства раскладки, а не разметки: проверить их можно
только тем, что страницу действительно раскладывают. Поэтому здесь поднимается
сервер и открывается Chromium.
"""

from __future__ import annotations

import socket
import threading
import time
from datetime import date

import pytest
import uvicorn

from app.core.models import BookStatus, Chapter, Outcome, Quote
from app.core.view import ClubView
from app.web.app import create_app
from tests.factories import a_book, a_club, a_meeting, some_data

playwright_api = pytest.importorskip("playwright.sync_api")

TODAY = date(2026, 9, 21)
NARROW = {"width": 360, "height": 740}
PATHS = ("/", "/history", "/shelf", "/shelf/topics", "/about", "/meetings/m1", "/books/b1")


def crowded_view() -> ClubView:
    book = a_book(
        "b1",
        chapters_override=tuple(
            Chapter(
                number=number,
                title="Архитектура, управляемая событиями, и её последствия",
                notes_url="https://example.org/notes/chapter",
            )
            for number in range(1, 6)
        ),
        status=BookStatus.READING,
        title="Высоконагруженные приложения: проектирование систем",
        notes_url="https://example.org/notes/book",
    )
    outcome = Outcome(
        agreed="Согласились, что согласованное хеширование объясняется проще, чем написано.",
        argued="Спорили про уровни изоляции транзакций дольше всего.",
        taken="Забираем идею идемпотентных обработчиков в свои проекты.",
        quote=Quote(text="Архитектор — градостроитель, а не строитель.", chapter=16),
    )
    meetings = [
        a_meeting(
            "m1",
            "2026-09-09",
            book="b1",
            closed=(1, 2),
            fmt="Петпроект-практика",
            host="Анастасия",
            outcome=outcome,
            topics=("Согласованное хеширование", "Уровни изоляции транзакций"),
        ),
        a_meeting("m2", "2026-09-23", book="b1", planned=(3, 4), fmt="Лайтнинги"),
        a_meeting("lone", "2026-09-16", title="ADR-дуэль: выбираем хранилище"),
    ]
    club = a_club(
        telegram="https://t.me/example",
        marquee=("КНИЖНАЯ СРЕДА", "КОД · КНИГИ · СПОРЫ · КОФЕ · ГЛАВЫ"),
        topic_notes={"Согласованное хеширование": "https://example.org/notes/hashing"},
        rules=("Читаем главу до встречи.", "Ведущий не лектор."),
    )
    return ClubView(some_data(books=[book], meetings=meetings, club=club))


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.fixture(scope="module")
def site() -> str:
    port = free_port()
    app = create_app(view=crowded_view(), today=lambda: TODAY)
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    )
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(200):
        if server.started:
            break
        time.sleep(0.05)
    assert server.started, "сервер не поднялся"
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


def test_no_horizontal_scrolling_on_a_narrow_screen(site):
    with playwright_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=NARROW)
        # Шрифты с внешнего сервера тесту не нужны: раскладку проверяем свою.
        page.route("https://fonts.**", lambda route: route.abort())
        try:
            for path in PATHS:
                page.goto(site + path, wait_until="load")
                scroll_width = page.evaluate("document.documentElement.scrollWidth")
                client_width = page.evaluate("document.documentElement.clientWidth")
                assert scroll_width <= client_width, (
                    f"{path}: страница шире экрана — {scroll_width} против {client_width}"
                )
        finally:
            browser.close()


def test_the_main_heading_stays_inside_the_screen(site):
    with playwright_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=NARROW)
        page.route("https://fonts.**", lambda route: route.abort())
        try:
            page.goto(site + "/books/b1", wait_until="load")
            box = page.locator("h1").bounding_box()
            assert box is not None
            assert box["x"] >= 0
            assert box["x"] + box["width"] <= NARROW["width"] + 1
        finally:
            browser.close()
