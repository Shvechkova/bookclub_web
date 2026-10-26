"""Словарь клуба: чтение отдельного файла и проверка на входе.

Словарь лежит рядом с данными клуба своим файлом. Его ошибки ловятся там же,
где ошибки клуба, — при загрузке, с названием понятия и того, что не так.
"""

import copy
from pathlib import Path

import pytest
import yaml

from app.data.loader import DataError, glossary_beside, load_club_data
from tests.test_validation import data_file

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "data" / "club.example.yaml"
CLUB = ROOT / "data" / "club.yaml"

TERMS = [
    {
        "id": "conway-law",
        "name": "Закон Конвея",
        "aliases": ["Conway's law"],
        "summary": "Система повторяет структуру общения в организации.",
        "article": "https://github.com/club/notes/conway.md",
        "chapters": [{"book": "b1", "chapter": 2}],
        "related": ["adr"],
    },
    {
        "id": "adr",
        "name": "ADR",
        "summary": "Короткая запись архитектурного решения и его причин.",
    },
]


def with_glossary(tmp_path, mutate=None):
    """Данные клуба из проверок загрузки и словарь рядом с ними."""
    club = data_file(tmp_path)
    terms = copy.deepcopy(TERMS)
    if mutate is not None:
        mutate(terms)
    (tmp_path / "glossary.yaml").write_text(
        yaml.safe_dump({"terms": terms}, allow_unicode=True), encoding="utf-8"
    )
    return club


def failure(tmp_path, mutate):
    with pytest.raises(DataError) as error:
        load_club_data(with_glossary(tmp_path, mutate))
    return str(error.value)


# --- где лежит словарь -------------------------------------------------------


def test_the_glossary_lies_beside_the_club_data():
    assert glossary_beside(Path("data/club.yaml")) == Path("data/glossary.yaml")
    assert glossary_beside(Path("data/club.example.yaml")) == Path(
        "data/glossary.example.yaml"
    )


def test_terms_are_read_from_the_file_beside_the_club_data(tmp_path):
    data = load_club_data(with_glossary(tmp_path))

    conway, adr = data.glossary
    assert conway.id == "conway-law"
    assert conway.name == "Закон Конвея"
    assert conway.aliases == ("Conway's law",)
    assert conway.summary == "Система повторяет структуру общения в организации."
    assert conway.article == "https://github.com/club/notes/conway.md"
    assert [(item.book_id, item.number) for item in conway.chapters] == [("b1", 2)]
    assert conway.related == ("adr",)
    assert adr.aliases == () and adr.article is None and adr.chapters == ()


def test_without_a_glossary_file_the_glossary_is_empty(tmp_path):
    assert load_club_data(data_file(tmp_path)).glossary == ()


def test_an_explicit_glossary_path_wins(tmp_path):
    club = with_glossary(tmp_path)
    other = tmp_path / "other.yaml"
    other.write_text(yaml.safe_dump({"terms": TERMS[1:]}, allow_unicode=True), encoding="utf-8")

    assert [term.id for term in load_club_data(club, other).glossary] == ["adr"]


def test_the_example_data_loads_with_its_glossary():
    data = load_club_data(EXAMPLE)

    assert data.glossary, "образец словаря пуст или не найден"


def test_every_meeting_topic_of_the_working_data_has_a_term():
    """Рабочий словарь покрывает все темы встреч: плашка без определения —
    ровно то, ради чего словарь заводили."""
    data = load_club_data(CLUB)
    known = {
        name.casefold()
        for term in data.glossary
        for name in (term.name, *term.aliases)
    }

    missing = [
        topic
        for meeting in data.meetings
        for topic in meeting.topics
        if topic.casefold() not in known
    ]
    assert missing == []


# --- неверная форма ----------------------------------------------------------


def test_a_term_without_a_summary_is_rejected(tmp_path):
    def mutate(terms):
        del terms[1]["summary"]

    message = failure(tmp_path, mutate)
    assert "adr" in message and "summary" in message


def test_a_term_id_must_be_a_slug(tmp_path):
    def mutate(terms):
        terms[1]["id"] = "ADR record"

    assert "ADR record" in failure(tmp_path, mutate)


def test_aliases_must_be_a_list(tmp_path):
    def mutate(terms):
        terms[0]["aliases"] = "Conway's law"

    assert "aliases" in failure(tmp_path, mutate)


def test_a_chapter_reference_needs_a_book_and_a_number(tmp_path):
    def mutate(terms):
        terms[0]["chapters"] = [{"book": "b1", "chapter": "вторая"}]

    assert "conway-law" in failure(tmp_path, mutate)


def test_the_glossary_must_list_terms(tmp_path):
    club = data_file(tmp_path)
    (tmp_path / "glossary.yaml").write_text("- просто список\n", encoding="utf-8")

    with pytest.raises(DataError) as error:
        load_club_data(club)
    assert "terms" in str(error.value)


def test_topic_notes_are_gone_from_the_club_data(tmp_path):
    def mutate(raw):
        raw["club"]["topic_notes"] = {"Закон Конвея": "https://example.org"}

    with pytest.raises(DataError) as error:
        load_club_data(data_file(tmp_path, mutate))
    assert "glossary" in str(error.value)


# --- проверки словаря целиком ------------------------------------------------


def test_a_repeated_id_is_rejected(tmp_path):
    def mutate(terms):
        terms[1]["id"] = "conway-law"

    assert "conway-law" in failure(tmp_path, mutate)


def test_a_repeated_name_is_rejected_regardless_of_case(tmp_path):
    def mutate(terms):
        terms[1]["name"] = "закон конвея"

    message = failure(tmp_path, mutate)
    assert "conway-law" in message and "adr" in message


def test_an_alias_equal_to_another_terms_name_is_rejected(tmp_path):
    def mutate(terms):
        terms[0]["aliases"] = ["adr"]

    message = failure(tmp_path, mutate)
    assert "conway-law" in message and "adr" in message


def test_an_unknown_book_is_rejected(tmp_path):
    def mutate(terms):
        terms[0]["chapters"] = [{"book": "nope", "chapter": 1}]

    message = failure(tmp_path, mutate)
    assert "conway-law" in message and "nope" in message


def test_a_chapter_outside_the_book_is_rejected(tmp_path):
    def mutate(terms):
        terms[0]["chapters"] = [{"book": "b1", "chapter": 40}]

    message = failure(tmp_path, mutate)
    assert "conway-law" in message and "b1" in message and "40" in message


def test_a_relation_to_an_unknown_term_is_rejected(tmp_path):
    def mutate(terms):
        terms[0]["related"] = ["nope"]

    message = failure(tmp_path, mutate)
    assert "conway-law" in message and "nope" in message


def test_a_term_cannot_be_related_to_itself(tmp_path):
    def mutate(terms):
        terms[0]["related"] = ["conway-law"]

    assert "conway-law" in failure(tmp_path, mutate)
