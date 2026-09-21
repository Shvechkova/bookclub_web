"""Загрузка файла данных клуба в объекты модели."""

from datetime import date
from pathlib import Path

from app.core.models import BookStatus, ChapterOutcome
from app.data.loader import load_club_data

EXAMPLE = Path(__file__).resolve().parent.parent / "data" / "club.example.yaml"


def example():
    return load_club_data(EXAMPLE)


def test_loads_club_details():
    club = example().club

    assert club.name == "Кабанья Читальня"
    assert club.descriptor == "IT книжный клуб"
    assert club.slot == "среда, раз в две недели"
    assert club.place == "дом77, комната 413"
    assert len(club.rules) == 3


def test_loads_books_in_order_with_chapters():
    books = example().books

    assert [book.number for book in books] == [1, 2, 3, 4, 5]
    reading = example().book("reading-example")
    assert reading.status is BookStatus.READING
    assert [chapter.number for chapter in reading.chapters] == [1, 2, 3, 4, 5]
    assert reading.chapters[0].title == "Глава первая"


def test_chapter_notes_url_is_optional():
    archive = example().book("archive-example")

    assert archive.chapters[0].notes_url == "https://example.org/notes/archive/1"
    assert archive.chapters[1].notes_url is None


def test_taken_chapters_default_to_the_whole_book():
    data = example()

    assert data.book("reading-example").taken_numbers == (1, 3, 5)
    assert data.book("closed-example").taken_numbers == (1, 2, 3)


def test_loads_meeting_chapters_with_outcomes():
    meeting = example().meeting("m-2026-06-17")

    assert meeting.book_id == "closed-example"
    assert [(c.number, c.outcome) for c in meeting.chapters] == [
        (3, ChapterOutcome.CARRIED)
    ]


def test_meeting_without_a_book_keeps_its_own_title():
    meeting = example().meeting("m-2026-07-29")

    assert meeting.book_id is None
    assert meeting.title == "Голосование за следующую книгу"
    assert meeting.chapters == ()
    assert meeting.format is None


def test_meeting_inherits_time_and_place_from_the_club():
    meeting = example().meeting("m-2026-06-03")

    assert meeting.date == date(2026, 6, 3)
    assert meeting.time == "19:30"
    assert meeting.place == "дом77, комната 413"


def test_loads_outcome_and_quote():
    meeting = example().meeting("m-2026-06-03")

    assert meeting.outcome is not None
    assert meeting.outcome.argued == "Дольше всего спорили про вторую."
    assert meeting.outcome.quote is not None
    assert meeting.outcome.quote.chapter == 2
    assert meeting.topics == ("Закон Конвея",)


def test_loads_format_of_the_second_hour():
    meeting = example().meeting("m-2026-06-03")

    assert meeting.format is not None
    assert meeting.format.name == "Лайтнинги"
    assert meeting.format.note == "пять минут на человека, без слайдов"


def test_loads_topic_notes_as_a_map_of_addresses():
    club = example().club

    assert club.topic_notes["Закон Конвея"] == "https://example.org/notes/conway"
