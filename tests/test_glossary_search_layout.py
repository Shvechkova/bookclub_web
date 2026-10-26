"""Поиск по словарю в настоящем браузере: отбор, порядок, адрес, клавиатура, якоря.

Поиск живёт в скрипте страницы — сервера у статической выгрузки нет, — поэтому
проверить его можно только тем, что страницу открывают и печатают в поле.
"""

from __future__ import annotations

import threading
import time
from datetime import date
from urllib.parse import parse_qs, urlparse

import pytest
import uvicorn

from app.core.view import ClubView
from app.web.app import create_app
from tests.factories import a_term, some_data
from tests.test_layout import NARROW, WIDE, _open_home, free_port

playwright_api = pytest.importorskip("playwright.sync_api")
expect = playwright_api.expect

TODAY = date(2026, 10, 26)
FIELD = "#glossary-q"


def search_view() -> ClubView:
    terms = [
        # Буква «А» стоит раньше «З»: понятие, найденное только по определению,
        # без ранжирования встало бы над «Законом Конвея».
        a_term(
            "autonomous-team",
            "Автономная команда",
            summary="Команда, нарезанная по закону Конвея вокруг своей части системы.",
        ),
        a_term(
            "brooks-law",
            "Закон Брукса",
            aliases=("Brooks's law",),
            summary="Добавление людей в опаздывающий проект задерживает его ещё больше.",
            related=("conway-law",),
        ),
        a_term(
            "conway-law",
            "Закон Конвея",
            aliases=("Conway's law",),
            summary="Система повторяет структуру общения команд, которые её строят.",
            related=("brooks-law",),
        ),
        a_term("black-box", "Чёрный ящик", summary="Модуль, который видно только снаружи."),
        a_term(
            "ddd",
            "DDD",
            aliases=("Domain-Driven Design",),
            summary="Проектирование от предметной области и её языка.",
        ),
    ]
    return ClubView(some_data(glossary=terms))


@pytest.fixture(scope="module")
def site() -> str:
    port = free_port()
    app = create_app(view=search_view(), today=lambda: TODAY)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(200):
        if server.started:
            break
        time.sleep(0.05)
    assert server.started, "сервер не поднялся"
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


@pytest.fixture
def page(site):
    with playwright_api.sync_playwright() as playwright:
        browser, page = _open_home(playwright, WIDE)
        try:
            yield page
        finally:
            browser.close()


def open_glossary(page, site, query: str = ""):
    page.goto(site + "/glossary" + query, wait_until="load")


def visible_ids(page) -> list[str]:
    return page.eval_on_selector_all(
        "article.entry", "nodes => nodes.filter(n => !n.closest('[hidden]')).map(n => n.id)"
    )


def test_a_part_of_the_name_finds_the_term_and_hides_the_others(page, site):
    open_glossary(page, site)
    page.fill(FIELD, "конвея")

    expect(page.locator("#brooks-law")).to_be_hidden()
    expect(page.locator("#conway-law")).to_be_visible()
    expect(page.locator("#black-box")).to_be_hidden()
    # Название раньше определения: «Автономная команда» найдена только по нему.
    assert visible_ids(page) == ["conway-law", "autonomous-team"]
    expect(page.locator("#conway-law .entry-name mark")).to_have_text("Конвея")


def test_an_english_alias_finds_the_term(page, site):
    open_glossary(page, site)
    page.fill(FIELD, "conway's law")
    expect(page.locator("#brooks-law")).to_be_hidden()
    assert visible_ids(page) == ["conway-law"]
    expect(page.locator("#conway-law .entry-aliases mark").first).to_have_text("Conway")

    page.fill(FIELD, "Domain driven")
    expect(page.locator("#conway-law")).to_be_hidden()
    assert visible_ids(page) == ["ddd"]


def test_yo_and_ye_are_the_same_letter(page, site):
    open_glossary(page, site)
    page.fill(FIELD, "черный")
    expect(page.locator("#conway-law")).to_be_hidden()
    assert visible_ids(page) == ["black-box"]
    expect(page.locator("#black-box .entry-name mark")).to_have_text("Чёрный")


def test_every_word_of_the_query_must_match(page, site):
    open_glossary(page, site)
    page.fill(FIELD, "закон  команд")
    expect(page.locator("#brooks-law")).to_be_hidden()
    # Оба найдены не по названию целиком — стоят по алфавиту.
    assert visible_ids(page) == ["autonomous-team", "conway-law"]


def test_the_count_follows_the_query(page, site):
    open_glossary(page, site)
    found = page.locator(".glossary-found")
    expect(found).to_have_attribute("aria-live", "polite")

    page.fill(FIELD, "брукса")
    expect(found).to_have_text("Найдено: 1")
    page.fill(FIELD, "закон")
    expect(found).to_have_text("Найдено: 3")


def test_nonsense_shows_the_empty_state(page, site):
    open_glossary(page, site)
    page.fill(FIELD, "zzqqxx")

    expect(page.locator(".glossary-nothing")).to_be_visible()
    expect(page.locator(".glossary-nothing")).to_contain_text("Ничего не нашлось")
    expect(page.locator(".glossary-found")).to_have_text("Найдено: 0")
    expect(page.locator("section.letter").first).to_be_hidden()
    assert visible_ids(page) == []
    assert page.locator(".letters a:visible").count() == 0


def test_an_empty_query_brings_everything_back_in_order(page, site):
    open_glossary(page, site)
    everything = visible_ids(page)
    page.fill(FIELD, "конвея")
    expect(page.locator("#brooks-law")).to_be_hidden()

    page.fill(FIELD, "")
    expect(page.locator("#brooks-law")).to_be_visible()
    assert visible_ids(page) == everything
    expect(page.locator(".glossary-nothing")).to_be_hidden()
    assert page.locator("#conway-law mark").count() == 0


def test_the_query_from_the_address_filters_on_load(page, site):
    open_glossary(page, site, "?q=%D0%BA%D0%BE%D0%BD%D0%B2%D0%B5%D1%8F")

    expect(page.locator(FIELD)).to_have_value("конвея")
    expect(page.locator("#brooks-law")).to_be_hidden()
    assert visible_ids(page) == ["conway-law", "autonomous-team"]


def test_the_query_goes_to_the_address_and_leaves_it_when_cleared(page, site):
    open_glossary(page, site)
    page.fill(FIELD, "ddd")
    expect(page.locator("#conway-law")).to_be_hidden()
    assert parse_qs(urlparse(page.url).query) == {"q": ["ddd"]}

    page.fill(FIELD, "")
    expect(page.locator("#conway-law")).to_be_visible()
    assert urlparse(page.url).query == ""


def test_slash_focuses_the_field_and_escape_clears_it(page, site):
    open_glossary(page, site)
    page.locator("h1").click()
    page.keyboard.press("/")
    expect(page.locator(FIELD)).to_be_focused()
    assert page.locator(FIELD).input_value() == "", "«/» попал в поле"

    page.keyboard.type("брукса")
    expect(page.locator("#conway-law")).to_be_hidden()
    page.keyboard.press("Escape")
    expect(page.locator(FIELD)).to_have_value("")
    expect(page.locator("#conway-law")).to_be_visible()


def test_a_related_link_clears_the_query_and_shows_its_term(page, site):
    open_glossary(page, site)
    page.fill(FIELD, "конвея")
    expect(page.locator("#brooks-law")).to_be_hidden()

    page.locator("#conway-law a[href='#brooks-law']").click()
    expect(page.locator("#brooks-law")).to_be_visible()
    expect(page.locator(FIELD)).to_have_value("")
    expect(page.locator("#brooks-law")).to_be_in_viewport()


def test_an_anchor_wins_over_the_query_on_load(page, site):
    open_glossary(page, site, "?q=ddd#brooks-law")
    expect(page.locator("#brooks-law")).to_be_visible()
    expect(page.locator("#brooks-law")).to_be_in_viewport()


def test_the_field_fills_a_narrow_screen_without_side_scrolling(site):
    with playwright_api.sync_playwright() as playwright:
        browser, page = _open_home(playwright, NARROW)
        try:
            open_glossary(page, site)
            page.fill(FIELD, "закон конвея")
            expect(page.locator("#brooks-law")).to_be_hidden()
            field = page.locator(FIELD).bounding_box()
            main = page.locator("main").bounding_box()
            assert field["x"] >= 0 and field["x"] + field["width"] <= NARROW["width"]
            assert field["width"] >= NARROW["width"] - 2 * 16 - 2, "поле не во всю ширину"
            assert field["width"] <= main["width"]
            assert page.evaluate(
                "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
            )
        finally:
            browser.close()
