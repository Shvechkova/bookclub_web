"""Страница «О клубе»: заголовок с кабаном, факты, правила встречи, место."""

import re
from pathlib import Path
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.core.models import Card
from app.core.view import ClubView
from app.data.loader import DataError, load_club_data as load
from app.web.app import create_app
from tests.factories import a_club, a_space, some_data

TODAY = date(2026, 10, 26)

ABOUT = dict(
    since=2023,
    about_title="Первый IT-книжный клуб Самары",
    about_hand="читаем, спорим,\nтащим на свой опыт",
    about=("Не пересказываем главы.", "Собираемся только очно."),
    facts=(
        Card(label="Только очно", text="Трансляций и записей нет"),
        Card(label="Открытый", text="Прийти может кто угодно"),
    ),
    rules=(
        Card(label="Разбираем вслух", text="Главу берут по частям."),
        Card(label="Ведущий — не эксперт", text="Держит время."),
    ),
    space=a_space(),
)


def page(**club) -> str:
    view = ClubView(some_data(club=a_club(**club)))
    response = TestClient(create_app(view=view, today=lambda: TODAY)).get("/about")
    assert response.status_code == 200
    return response.text


def test_the_about_page_opens_with_its_title_and_the_boar():
    html = page(**ABOUT)

    head = html[html.index('class="about-head"'):]
    head = head[: head.index("</section>")]
    assert "О клубе · с 2023" in head
    assert re.search(r"<h1[^>]*>\s*Первый IT-книжный клуб Самары\s*</h1>", head)
    assert re.findall(r'<span class="about-hand-line">(.*?)</span>', head) == [
        "читаем, спорим,",
        "тащим на свой опыт",
    ]
    assert 'class="about-boar"' in head, "кабан стоит в заставке страницы"
    assert 'alt=""' in head, "кабан — украшение, читалке экрана он не нужен"
    assert "Не пересказываем главы." in head, "первый абзац — лид заставки"


def test_facts_replace_the_rest_of_the_about_text():
    assert "Собираемся только очно." not in page(**ABOUT), (
        "карточки фактов говорят то же короче — абзацы не повторяются"
    )
    plain = dict(ABOUT, facts=())
    assert "Собираемся только очно." in page(**plain)


def test_facts_and_rules_are_cards_in_order():
    html = page(**ABOUT)

    facts = re.findall(r'<p class="about-fact-label">(.*?)</p>', html)
    rules = re.findall(r'<h3 class="about-rule-title">(.*?)</h3>', html)
    assert facts == ["Только очно", "Открытый"]
    assert rules == ["Разбираем вслух", "Ведущий — не эксперт"]


def test_the_about_page_no_longer_lists_formats():
    assert "Форматы" not in page(**ABOUT)


def test_contacts_lead_to_the_space_chat_first():
    html = page(**ABOUT)

    links = html[html.index('class="about-contacts"'):]
    assert links.index(a_space().chat) < links.index(a_space().thread)


def test_without_the_new_fields_the_page_falls_back_to_plain_text():
    html = page(about=("Читаем и спорим.",), routine=("Разбираем главы вслух.",))

    assert re.search(r"<h1[^>]*>\s*О клубе\s*</h1>", html)
    assert "Читаем и спорим." in html
    assert "Разбираем главы вслух." in html


def test_a_card_without_text_is_rejected(tmp_path):
    source = tmp_path / "club.yaml"
    example = Path("data/club.example.yaml").read_text(encoding="utf-8")
    source.write_text(
        example.replace("  facts:\n", "  facts:\n    - label: Пустая\n", 1),
        encoding="utf-8",
    )

    with pytest.raises(DataError, match="facts"):
        load(source)


def test_the_example_data_fills_the_about_page():
    club = load("data/club.example.yaml").club

    assert club.about_title
    assert club.facts and club.rules


def test_the_club_chat_is_offered_after_the_first_visit():
    html = page(**ABOUT, telegram="https://t.me/kabanya")

    chat = html[html.index('class="about-club-chat"'):]
    assert 'href="https://t.me/kabanya" target="_blank" rel="noopener">Чат читальни</a>' in chat
    assert "после первого посещения" in chat
    assert html.index(a_space().site) < html.index("https://t.me/kabanya"), (
        "чат читальни — последним, после всех ссылок площадки"
    )


def test_the_address_links_to_the_map_with_a_pin():
    from tests.factories import a_place

    place = a_place(map="https://2gis.ru/samara/firm/70000001104494028")
    html = page(**ABOUT, place=place)

    card = html[html.index('class="about-when"'):]
    link = re.search(r'<a class="about-map"[^>]*>(.*?)</a>', card, re.S)
    assert link, "адрес не ведёт на карту"
    assert 'href="https://2gis.ru/samara/firm/70000001104494028"' in link.group(0)
    assert "<svg" in link.group(1), "у адреса нет значка места"
    assert place.full in link.group(1)


def test_without_a_map_the_address_is_plain_text():
    html = page(**ABOUT)

    assert 'class="about-map"' not in html


def test_the_map_link_is_loaded_from_the_data():
    assert load("data/club.example.yaml").club.place.map


def test_the_footer_calls_it_the_reading_room_chat():
    html = page(**ABOUT, telegram="https://t.me/kabanya")

    footer = html[html.index("<footer"):]
    assert ">чат читальни</a>" in footer


def test_the_venue_links_to_the_space_site():
    html = page(**ABOUT)

    card = html[html.index('class="about-when"'):]
    assert re.search(
        rf'<a class="about-venue" href="{re.escape(a_space().site)}"[^>]*>[^<]*</a>', card
    ), "площадка не ведёт на свой сайт"
