"""Проверка данных при загрузке.

Инварианты проверяются один раз, на входе. На неверных данных приложение не
поднимается и называет конкретную ошибку — вместо того чтобы показать страницу
наполовину.
"""

import copy

import pytest
import yaml

from app.data.loader import DataError, load_club_data

BASE = {
    "club": {
        "name": "Клуб",
        "descriptor": "IT книжный клуб",
        "about": ["О клубе"],
        "place": {
            "venue": "хакспейс s4m.space",
            "building": "Дом77",
            "street": "Ленинградская 77",
            "room": "комната 413",
            "city": "Самара",
        },
        "slot": "среда, раз в две недели",
        "time": "19:30",
        "duration_minutes": 90,
        "timezone": "Europe/Samara",
    },
    "books": [
        {
            "id": "b1",
            "number": 1,
            "title": "Книга",
            "author": "Автор",
            "status": "reading",
            "chapters": [{"title": "Глава один"}, {"title": "Глава два"}],
        }
    ],
    "meetings": [
        {
            "id": "m1",
            "date": "2026-01-07",
            "book": "b1",
            "chapters": [{"number": 1, "outcome": "closed"}],
            "topics": ["Закон Конвея"],
        }
    ],
}


def data_file(tmp_path, mutate=None):
    raw = copy.deepcopy(BASE)
    if mutate is not None:
        mutate(raw)
    path = tmp_path / "club.yaml"
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    return path


def failure(tmp_path, mutate):
    with pytest.raises(DataError) as error:
        load_club_data(data_file(tmp_path, mutate))
    return str(error.value)


def test_base_data_is_valid(tmp_path):
    assert load_club_data(data_file(tmp_path)).book("b1") is not None


def test_two_reading_books_are_rejected(tmp_path):
    def mutate(raw):
        second = copy.deepcopy(raw["books"][0])
        second["id"] = "b2"
        second["number"] = 2
        raw["books"].append(second)

    assert "читаем" in failure(tmp_path, mutate)


def test_unknown_status_is_rejected(tmp_path):
    def mutate(raw):
        raw["books"][0]["status"] = "полузакрыта"

    assert "полузакрыта" in failure(tmp_path, mutate)


def test_unparsable_date_is_rejected(tmp_path):
    def mutate(raw):
        raw["meetings"][0]["date"] = "седьмое января"

    assert "дата" in failure(tmp_path, mutate)


def test_duplicate_meeting_ids_are_rejected(tmp_path):
    def mutate(raw):
        raw["meetings"].append(copy.deepcopy(raw["meetings"][0]))

    assert "m1" in failure(tmp_path, mutate)


def test_duplicate_book_ids_are_rejected(tmp_path):
    def mutate(raw):
        raw["books"].append(copy.deepcopy(raw["books"][0]))

    assert "b1" in failure(tmp_path, mutate)


def test_meeting_without_a_book_needs_its_own_title(tmp_path):
    def mutate(raw):
        del raw["meetings"][0]["book"]
        del raw["meetings"][0]["chapters"]

    assert "название" in failure(tmp_path, mutate)


def test_chapters_without_a_book_are_rejected(tmp_path):
    def mutate(raw):
        del raw["meetings"][0]["book"]
        raw["meetings"][0]["title"] = "Лайвкодинг"

    assert "без книги" in failure(tmp_path, mutate)


def test_meeting_chapter_must_exist_in_the_book(tmp_path):
    def mutate(raw):
        raw["meetings"][0]["chapters"] = [{"number": 9, "outcome": "closed"}]

    assert "9" in failure(tmp_path, mutate)


def test_an_outcome_item_must_point_at_a_chapter_of_the_book(tmp_path):
    def mutate(raw):
        raw["meetings"][0]["outcome"] = {
            "by_chapter": [{"chapters": [40], "heading": "Оценка сроков", "text": "…"}]
        }

    message = failure(tmp_path, mutate)

    assert "m1" in message
    assert "40" in message


def test_a_debate_must_point_at_a_chapter_of_the_book_too(tmp_path):
    def mutate(raw):
        raw["meetings"][0]["outcome"] = {"debates": [{"chapters": [3], "text": "…"}]}

    message = failure(tmp_path, mutate)

    assert "m1" in message
    assert "3" in message


def test_an_outcome_item_with_chapters_needs_a_book(tmp_path):
    def mutate(raw):
        meeting = raw["meetings"][0]
        del meeting["book"]
        del meeting["chapters"]
        meeting["title"] = "Лайвкодинг"
        meeting["outcome"] = {"by_chapter": [{"chapters": [1], "text": "…"}]}

    message = failure(tmp_path, mutate)

    assert "m1" in message
    assert "без книги" in message


def test_an_outcome_item_without_chapters_is_fine_without_a_book(tmp_path):
    def mutate(raw):
        meeting = raw["meetings"][0]
        del meeting["book"]
        del meeting["chapters"]
        meeting["title"] = "Лайвкодинг"
        meeting["outcome"] = {"debates": [{"heading": "Бюджеты", "text": "…"}]}

    data = load_club_data(data_file(tmp_path, mutate))

    assert data.meeting("m1").outcome.debates[0].heading == "Бюджеты"


def test_meeting_book_must_exist(tmp_path):
    def mutate(raw):
        raw["meetings"][0]["book"] = "нет-такой"

    assert "нет-такой" in failure(tmp_path, mutate)


def test_taken_chapters_must_exist(tmp_path):
    def mutate(raw):
        raw["books"][0]["taken_chapters"] = [1, 7]

    assert "7" in failure(tmp_path, mutate)


def test_topic_notes_key_must_be_used_by_a_meeting(tmp_path):
    def mutate(raw):
        raw["club"]["topic_notes"] = {"Закон Кнвея": "https://example.org"}

    assert "Закон Кнвея" in failure(tmp_path, mutate)


def test_a_list_item_that_parsed_into_a_mapping_is_rejected(tmp_path):
    """«Вход свободный: без регистраций» YAML читает как словарь.

    Без проверки такая строка молча доезжает до страницы в виде словаря, а не
    падает: ошибка данных должна называться на входе.
    """

    def mutate(raw):
        raw["club"]["terms"] = [{"Вход свободный": "без регистраций"}]

    assert "кавычки" in failure(tmp_path, mutate)


def test_place_as_a_string_is_rejected(tmp_path):
    """Строкой место больше не задаётся: из неё не собрать полный адрес."""

    def mutate(raw):
        raw["club"]["place"] = "дом77, комната 413"

    assert "venue" in failure(tmp_path, mutate)


def test_place_without_a_venue_is_rejected(tmp_path):
    def mutate(raw):
        del raw["club"]["place"]["venue"]

    assert "venue" in failure(tmp_path, mutate)


def test_place_without_a_room_is_rejected(tmp_path):
    def mutate(raw):
        del raw["club"]["place"]["room"]

    assert "room" in failure(tmp_path, mutate)


def test_a_club_without_a_timezone_is_rejected(tmp_path):
    """Без пояса ссылка «в календарь» поставит встречу не на тот час."""

    def mutate(raw):
        del raw["club"]["timezone"]

    assert "timezone" in failure(tmp_path, mutate)


def test_duration_must_be_a_positive_number_of_minutes(tmp_path):
    def mutate(raw):
        raw["club"]["duration_minutes"] = "90 минут"

    assert "duration_minutes" in failure(tmp_path, mutate)

    def zero(raw):
        raw["club"]["duration_minutes"] = 0

    assert "duration_minutes" in failure(tmp_path, zero)
