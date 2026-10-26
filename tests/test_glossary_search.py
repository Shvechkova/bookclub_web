"""Поиск по словарю: нормализация текста и разметка, которую сервер отдаёт скрипту."""

import html as markup
import re
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.core.view import ClubView
from app.web.app import create_app
from app.web.search import normalize, search_names, search_text
from tests.factories import a_term, some_data

TODAY = date(2026, 10, 26)


def glossary(terms) -> str:
    view = ClubView(some_data(glossary=terms))
    response = TestClient(create_app(view=view, today=lambda: TODAY)).get("/glossary")
    assert response.status_code == 200
    return response.text


def card(html: str, term_id: str) -> str:
    found = re.search(rf'<article class="entry" id="{term_id}"[^>]*>', html)
    assert found, f"карточки {term_id} нет"
    return found.group(0)


def attribute(tag: str, name: str) -> str:
    found = re.search(rf'{name}="([^"]*)"', tag)
    assert found, f"у карточки нет {name}: {tag}"
    return markup.unescape(found.group(1))


# --- нормализация -------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Закон Конвея", "закон конвея"),
        ("Ребёнок ЁЖ", "ребенок еж"),
        ("Brooks's law", "brooks s law"),
        ("  CQRS —   и   event-sourcing!  ", "cqrs и event sourcing"),
        ("snake_case", "snake case"),
        ("", ""),
    ],
)
def test_normalize_lowercases_folds_yo_and_drops_punctuation(raw, expected):
    assert normalize(raw) == expected


def test_search_text_joins_name_aliases_and_summary():
    term = a_term(
        "conway-law",
        "Закон Конвея",
        aliases=("Conway's law",),
        summary="Структура системы повторяет структуру организации.",
    )
    assert search_text(term) == (
        "закон конвея conway s law структура системы повторяет структуру организации"
    )


def test_search_names_keeps_name_and_each_alias_apart():
    term = a_term("ddd", "DDD", aliases=("Domain-Driven Design", "Предметно-ориентированное проектирование"))
    assert search_names(term) == "ddd|domain driven design|предметно ориентированное проектирование"


# --- разметка страницы ----------------------------------------------------------


TERMS = [
    a_term("conway-law", "Закон Конвея", aliases=("Conway's law",)),
    a_term("ddd", "DDD", aliases=("Domain-Driven Design",), summary="Проектирование от «предметной области»."),
    a_term("yolk", "Ёлка"),
]


def test_the_search_form_has_a_role_a_label_and_a_search_field():
    html = glossary(TERMS)

    form = re.search(r'<form class="glossary-search"[^>]*>.*?</form>', html, re.S)
    assert form, "формы поиска нет"
    form = form.group(0)
    assert 'role="search"' in form
    field = re.search(r"<input[^>]*>", form).group(0)
    field_id = attribute(field, "id")
    assert f'<label for="{field_id}"' in form
    assert re.search(rf'<label for="{field_id}"[^>]*>Поиск по словарю</label>', form)
    assert 'type="search"' in field
    assert 'autocomplete="off"' in field
    assert 'name="q"' in field
    assert "закон Конвея" in attribute(field, "placeholder")


def test_the_form_sits_above_the_letters_and_announces_the_count():
    html = glossary(TERMS)

    assert html.index('class="glossary-search"') < html.index('class="letters"')
    assert re.search(r'<p class="glossary-found"[^>]*aria-live="polite"', html)
    nothing = re.search(r'<p class="glossary-nothing"[^>]*>(.*?)</p>', html, re.S)
    assert nothing and "hidden" in nothing.group(0)
    assert "Ничего не нашлось" in nothing.group(1)


def test_the_script_is_loaded_deferred_from_static():
    html = glossary(TERMS)

    assert re.search(r'<script src="/static/glossary-search\.js" defer></script>', html)


def test_every_card_carries_its_normalized_name_and_aliases():
    html = glossary(TERMS)

    conway = card(html, "conway-law")
    assert "закон конвея" in attribute(conway, "data-search")
    assert "conway s law" in attribute(conway, "data-search")
    assert attribute(conway, "data-names") == "закон конвея|conway s law"

    ddd = card(html, "ddd")
    assert "предметной области" in attribute(ddd, "data-search")
    assert attribute(ddd, "data-names") == "ddd|domain driven design"

    assert attribute(card(html, "yolk"), "data-names") == "елка"


def test_the_server_hides_nothing_so_the_glossary_works_without_scripts():
    html = glossary(TERMS)

    for term_id in ("conway-law", "ddd", "yolk"):
        assert " hidden" not in card(html, term_id)
    for section in re.findall(r'<section class="letter"[^>]*>', html):
        assert "hidden" not in section


def test_an_empty_glossary_has_no_search():
    assert 'class="glossary-search"' not in glossary([])
