"""Конструкторы данных для тестов ядра.

Тесты ядра работают с моделью напрямую: формат файла к вычислениям отношения не
имеет, и гонять их через YAML значило бы проверять заодно загрузчик.
"""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime

from app.core.models import (
    Book,
    BookStatus,
    Chapter,
    ChapterOutcome,
    Club,
    ClubData,
    DiscussedChapter,
    Meeting,
    MeetingFormat,
    Place,
    Space,
)


def a_place(**overrides) -> Place:
    values = dict(
        venue="хакспейс s4m.space",
        building="Дом77",
        room="комната 413",
        street="Ленинградская 77",
        floor="4 этаж",
        city="Самара",
    )
    values.update(overrides)
    return Place(**values)


def a_club(**overrides) -> Club:
    values = dict(
        name="Кабанья Читальня",
        descriptor="IT книжный клуб",
        about=("О клубе",),
        place=a_place(),
        slot="среда, раз в две недели",
        time="19:30",
        duration_minutes=90,
        timezone="Europe/Samara",
    )
    values.update(overrides)
    return Club(**values)


def a_space(**overrides) -> Space:
    values = dict(
        name="s4m.space",
        site="https://s4m.space/",
        channel="https://t.me/s4m_space",
        chat="https://t.me/+chat",
        thread="https://t.me/c/1/2",
    )
    values.update(overrides)
    return Space(**values)


def a_book(
    book_id: str = "b1",
    *,
    number: int = 1,
    chapters: int = 3,
    chapters_override: tuple[Chapter, ...] | None = None,
    taken: tuple[int, ...] | None = None,
    status: BookStatus = BookStatus.READING,
    **overrides,
) -> Book:
    titles = chapters_override or tuple(
        Chapter(number=position, title=f"Глава {position}")
        for position in range(1, chapters + 1)
    )
    values = dict(
        id=book_id,
        number=number,
        title=f"Книга {book_id}",
        author="Автор",
        status=status,
        chapters=titles,
        taken_numbers=(
            taken
            if taken is not None
            else tuple(chapter.number for chapter in titles)
        ),
    )
    values.update(overrides)
    return Book(**values)


def a_meeting(
    meeting_id: str,
    day: str,
    *,
    book: str | None = None,
    closed: tuple[int, ...] = (),
    carried: tuple[int, ...] = (),
    planned: tuple[int, ...] = (),
    fmt: str | None = None,
    **overrides,
) -> Meeting:
    discussed = (
        tuple(
            DiscussedChapter(number=number, outcome=ChapterOutcome.CLOSED)
            for number in closed
        )
        + tuple(
            DiscussedChapter(number=number, outcome=ChapterOutcome.CARRIED)
            for number in carried
        )
        + tuple(
            DiscussedChapter(number=number, outcome=ChapterOutcome.PLANNED)
            for number in planned
        )
    )
    values = dict(
        id=meeting_id,
        date=_day(day),
        time="19:30",
        place=a_place(),
        book_id=book,
        chapters=discussed,
        format=MeetingFormat(name=fmt) if fmt else None,
    )
    values.update(overrides)
    return Meeting(**values)


def some_data(books=(), meetings=(), club: Club | None = None) -> ClubData:
    return ClubData(
        club=club or a_club(),
        books=tuple(books),
        meetings=tuple(meetings),
    )


def _day(value: str) -> Date:
    return datetime.strptime(value, "%Y-%m-%d").date()
