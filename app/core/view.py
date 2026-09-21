"""Вычисления по данным клуба.

Ни одна величина отсюда в данных не хранится: номер встречи, пройденные главы,
число встреч по книге, темп и каталог понятий выводятся каждый раз заново. Так
их невозможно рассогласовать с данными — расходиться просто нечему.

Модуль ничего не знает ни про HTTP, ни про шаблоны: поверх него одинаково
ложатся веб-страницы, картинки-анонсы и телеграм-бот.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as Day

from app.core.models import Book, BookStatus, Chapter, Club, ClubData, Meeting


@dataclass(frozen=True)
class NumberedMeeting:
    """Встреча со сквозным номером по клубу."""

    number: int
    meeting: Meeting


@dataclass(frozen=True)
class Progress:
    """Пройдено глав из взятых в чтение."""

    done: int
    taken: int


@dataclass(frozen=True)
class TopicEntry:
    """Понятие клуба: где обсуждали и где про него прочитать."""

    name: str
    notes_url: str | None
    meetings: tuple[Meeting, ...]


@dataclass(frozen=True)
class BookSegment:
    """Отрезок ленты истории: книга и её встречи, свежие сверху."""

    book: Book
    meetings: tuple[NumberedMeeting, ...]


@dataclass(frozen=True)
class LoneMeeting:
    """Запись ленты истории: встреча без книжной части."""

    meeting: NumberedMeeting


@dataclass(frozen=True)
class ChapterView:
    """Глава книги вместе со встречами, на которых её разбирали."""

    chapter: Chapter
    meetings: tuple[Meeting, ...]
    is_taken: bool
    is_passed: bool
    is_started: bool


class ClubView:
    """Read-модель клуба: данные плюс всё, что из них выводится."""

    def __init__(self, data: ClubData) -> None:
        self._data = data

    @property
    def data(self) -> ClubData:
        return self._data

    @property
    def club(self):
        return self._data.club

    @property
    def books(self) -> tuple[Book, ...]:
        return self._data.books

    # --- встречи -------------------------------------------------------------

    def numbered_meetings(self) -> tuple[NumberedMeeting, ...]:
        """Все встречи по датам, со сквозной нумерацией с единицы."""
        ordered = sorted(self._data.meetings, key=lambda meeting: (meeting.date, meeting.id))
        return tuple(
            NumberedMeeting(number=position, meeting=meeting)
            for position, meeting in enumerate(ordered, start=1)
        )

    def number_of(self, meeting_id: str) -> int | None:
        for numbered in self.numbered_meetings():
            if numbered.meeting.id == meeting_id:
                return numbered.number
        return None

    def meetings_of(self, book: Book) -> tuple[Meeting, ...]:
        """Встречи книги по датам."""
        return tuple(
            numbered.meeting
            for numbered in self.numbered_meetings()
            if numbered.meeting.book_id == book.id
        )

    def has_recorded_history(self, book: Book) -> bool:
        """Записаны ли встречи по книге. Нет — значит хронику тогда не вели."""
        return bool(self.meetings_of(book))

    def upcoming_meeting(self, today: Day) -> NumberedMeeting | None:
        """Ближайшая встреча: первая по дате, которая ещё не прошла."""
        for numbered in self.numbered_meetings():
            if numbered.meeting.date >= today:
                return numbered
        return None

    def latest_past_meeting(self, today: Day) -> NumberedMeeting | None:
        """Последняя прошедшая встреча."""
        past = [item for item in self.numbered_meetings() if item.meeting.date < today]
        return past[-1] if past else None

    def reading_book(self) -> Book | None:
        """Книга, которую читают сейчас. Такая может быть только одна."""
        for book in self._data.books:
            if book.status is BookStatus.READING:
                return book
        return None

    # --- главы ---------------------------------------------------------------

    def passed_numbers(self, book: Book) -> tuple[int, ...]:
        """Главы, закрытые хотя бы на одной встрече."""
        closed: set[int] = set()
        for meeting in self.meetings_of(book):
            closed.update(meeting.closed_numbers())
        return tuple(sorted(closed))

    def started_numbers(self, book: Book) -> tuple[int, ...]:
        """Главы, которые разбирали, но так и не закрыли."""
        carried: set[int] = set()
        for meeting in self.meetings_of(book):
            carried.update(meeting.carried_numbers())
        return tuple(sorted(carried - set(self.passed_numbers(book))))

    def reading_has_started(self, book: Book) -> bool:
        return bool(self.passed_numbers(book))

    def progress(self, book: Book) -> Progress | None:
        """Пройдено из взятых. Без записанных встреч прогресса нет — он неизвестен."""
        if not self.has_recorded_history(book):
            return None
        passed = set(self.passed_numbers(book)) & set(book.taken_numbers)
        return Progress(done=len(passed), taken=len(book.taken_numbers))

    def chapters_of(self, book: Book) -> tuple[ChapterView, ...]:
        """Оглавление книги со встречами по каждой главе."""
        passed = set(self.passed_numbers(book))
        started = set(self.started_numbers(book))
        taken = set(book.taken_numbers)
        meetings = self.meetings_of(book)
        return tuple(
            ChapterView(
                chapter=chapter,
                meetings=tuple(
                    meeting
                    for meeting in meetings
                    if any(item.number == chapter.number for item in meeting.chapters)
                ),
                is_taken=chapter.number in taken,
                is_passed=chapter.number in passed,
                is_started=chapter.number in started,
            )
            for chapter in book.chapters
        )

    def meeting_count(self, book: Book) -> int | None:
        """Сколько встреч ушло на книгу.

        Показывается только у закрытой книги и только если встречи записаны:
        ноль встреч означает «неизвестно», а не «встреч не было».
        """
        if book.status is not BookStatus.CLOSED:
            return None
        count = len(self.meetings_of(book))
        return count or None

    # --- темп ---------------------------------------------------------------

    def pace(self, book: Book) -> float | None:
        """Среднее число глав, закрытых на трёх последних встречах. Это прикидка."""
        counts = [
            len(meeting.closed_numbers())
            for meeting in self.meetings_of(book)
            if meeting.closed_numbers()
        ]
        if not counts:
            return None
        recent = counts[-3:]
        return sum(recent) / len(recent)

    # --- понятия ------------------------------------------------------------

    def topics(self) -> tuple[TopicEntry, ...]:
        """Каталог понятий: собирается из тем встреч, отдельного списка тем нет."""
        order: list[str] = []
        by_name: dict[str, list[Meeting]] = {}
        for numbered in self.numbered_meetings():
            for topic in numbered.meeting.topics:
                if topic not in by_name:
                    order.append(topic)
                    by_name[topic] = []
                by_name[topic].append(numbered.meeting)
        return tuple(
            TopicEntry(
                name=name,
                notes_url=self.club.topic_notes.get(name),
                meetings=tuple(by_name[name]),
            )
            for name in order
        )

    # --- заголовок встречи --------------------------------------------------

    def planned_numbers(self, meeting: Meeting) -> tuple[int, ...]:
        return tuple(sorted(meeting.planned_numbers()))

    def title_of(self, meeting: Meeting) -> str:
        """Заголовок встречи: из книжной части, если она есть, иначе собственный."""
        book = self._data.book(meeting.book_id) if meeting.book_id else None
        if book is None:
            return meeting.title or ""
        numbers = sorted(meeting.discussed_numbers()) or sorted(meeting.planned_numbers())
        phrase = chapter_phrase(numbers)
        return f"{book.title} · {phrase}" if phrase else book.title

    # --- лента истории ------------------------------------------------------

    def history(self) -> tuple[BookSegment | LoneMeeting, ...]:
        """Вся жизнь клуба одной лентой, свежее сверху.

        Книга — заголовок отрезка, её встречи — записи внутри. Встречи без
        книжной части идут той же лентой по своей дате. Книга, к которой встреч
        не отнесено, держится своего номера: датами её разместить не по чему.
        """
        numbered = self.numbered_meetings()
        lone = [item for item in numbered if item.meeting.book_id is None]
        entries: list[BookSegment | LoneMeeting] = []
        position = 0
        for book in sorted(self._data.books, key=lambda item: item.number):
            inside = tuple(
                item for item in numbered if item.meeting.book_id == book.id
            )
            start = inside[0].meeting.date if inside else None
            while (
                position < len(lone)
                and start is not None
                and lone[position].meeting.date < start
            ):
                entries.append(LoneMeeting(meeting=lone[position]))
                position += 1
            entries.append(BookSegment(book=book, meetings=tuple(reversed(inside))))
        entries.extend(LoneMeeting(meeting=item) for item in lone[position:])
        return tuple(reversed(entries))


def chapter_phrase(numbers: list[int] | tuple[int, ...]) -> str:
    """«глава 4», «главы 8–9», «главы 3, 7» — в зависимости от того, что разбирали."""
    numbers = sorted(numbers)
    if not numbers:
        return ""
    if len(numbers) == 1:
        return f"глава {numbers[0]}"
    if numbers[-1] - numbers[0] + 1 == len(numbers):
        return f"главы {numbers[0]}–{numbers[-1]}"
    return "главы " + ", ".join(str(number) for number in numbers)
