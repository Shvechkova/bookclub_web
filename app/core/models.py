"""Сущности клуба.

Чистые данные: ни веб-фреймворка, ни шаблонов, ни формата файла. Всё, что можно
вывести из других полей — число встреч, пройденные главы, номер встречи, каталог
понятий — здесь не хранится: это вычисления, они живут в `app.core.view`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as Date
from enum import Enum


class BookStatus(Enum):
    """Состояние книги. У книги оно ровно одно."""

    VOTING = "voting"
    QUEUED = "queued"
    READING = "reading"
    CLOSED = "closed"
    DROPPED = "dropped"


class ChapterOutcome(Enum):
    """Чем кончился разбор главы на встрече.

    `PLANNED` — глава ещё не разбиралась: так выглядит план предстоящей встречи.
    """

    PLANNED = "planned"
    CLOSED = "closed"
    CARRIED = "carried"


@dataclass(frozen=True)
class Chapter:
    """Глава книги. Номер — позиция в оглавлении, с единицы."""

    number: int
    title: str
    notes_url: str | None = None


@dataclass(frozen=True)
class Book:
    """Книга, она же серия: один набор встреч по одной книге."""

    id: str
    number: int
    title: str
    author: str
    status: BookStatus
    chapters: tuple[Chapter, ...]
    taken_numbers: tuple[int, ...]
    period: str | None = None
    notes_url: str | None = None
    close_note: str | None = None
    takeaways: tuple[str, ...] = ()

    def chapter(self, number: int) -> Chapter | None:
        for chapter in self.chapters:
            if chapter.number == number:
                return chapter
        return None

    @property
    def is_read_selectively(self) -> bool:
        return len(self.taken_numbers) != len(self.chapters)


@dataclass(frozen=True)
class DiscussedChapter:
    """Глава, разобранная на встрече, и чем разбор кончился."""

    number: int
    outcome: ChapterOutcome


@dataclass(frozen=True)
class MeetingFormat:
    """Формат второго часа: сменная оболочка вокруг постоянного ядра."""

    name: str
    note: str | None = None


@dataclass(frozen=True)
class Quote:
    text: str
    chapter: int | None = None


@dataclass(frozen=True)
class Outcome:
    """Итоги встречи: три тезиса и цитата вечера."""

    agreed: str | None = None
    argued: str | None = None
    taken: str | None = None
    quote: Quote | None = None

    @property
    def is_empty(self) -> bool:
        return not any((self.agreed, self.argued, self.taken, self.quote))


@dataclass(frozen=True)
class Link:
    title: str
    url: str


@dataclass(frozen=True)
class Meeting:
    """Встреча клуба: книжная часть и формат, обе необязательны."""

    id: str
    date: Date
    time: str
    place: str
    host: str | None = None
    book_id: str | None = None
    chapters: tuple[DiscussedChapter, ...] = ()
    format: MeetingFormat | None = None
    title: str | None = None
    announce: tuple[str, ...] = ()
    outcome: Outcome | None = None
    topics: tuple[str, ...] = ()
    links: tuple[Link, ...] = ()

    @property
    def has_book_part(self) -> bool:
        return self.book_id is not None

    def closed_numbers(self) -> tuple[int, ...]:
        return tuple(c.number for c in self.chapters if c.outcome is ChapterOutcome.CLOSED)

    def carried_numbers(self) -> tuple[int, ...]:
        return tuple(c.number for c in self.chapters if c.outcome is ChapterOutcome.CARRIED)

    def planned_numbers(self) -> tuple[int, ...]:
        return tuple(c.number for c in self.chapters if c.outcome is ChapterOutcome.PLANNED)

    def discussed_numbers(self) -> tuple[int, ...]:
        """Главы, которые уже разбирали: закрытые и перенесённые."""
        return tuple(
            c.number
            for c in self.chapters
            if c.outcome in (ChapterOutcome.CLOSED, ChapterOutcome.CARRIED)
        )


@dataclass(frozen=True)
class Club:
    """Сам клуб: постоянные условия и договор."""

    name: str
    descriptor: str
    about: str
    place: str
    slot: str
    time: str
    duration: str
    rules: tuple[str, ...]
    telegram: str | None = None
    topic_notes: dict[str, str] = field(default_factory=dict)
    marquee: tuple[str, ...] = ()


@dataclass(frozen=True)
class ClubData:
    """Всё содержимое файла данных."""

    club: Club
    books: tuple[Book, ...]
    meetings: tuple[Meeting, ...]

    def book(self, book_id: str) -> Book | None:
        for book in self.books:
            if book.id == book_id:
                return book
        return None

    def meeting(self, meeting_id: str) -> Meeting | None:
        for meeting in self.meetings:
            if meeting.id == meeting_id:
                return meeting
        return None
