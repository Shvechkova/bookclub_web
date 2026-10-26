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
    cover: str | None = None
    # Для подписей в одну строку: карточка спора, кнопка встречи. Полное
    # «…, 2-е издание» туда не влезает, а обрезать название наугад нельзя.
    short_title: str | None = None

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
class OutcomeItem:
    """Пункт полных итогов: что говорили по главам или о чём спорили.

    Один тип на оба списка: у спора номера глав тоже допустимы, в посте канала
    их просто не ставят. Заголовок и главы необязательны, текст — нет.
    """

    heading: str | None
    text: str
    chapters: tuple[int, ...] = ()


@dataclass(frozen=True)
class Outcome:
    """Итоги встречи.

    Три тезиса и цитата — короткая выжимка для раздела «Сейчас». Остальное —
    полная форма, как итоги уходят постом в канал: вступление, пункты по
    главам, главные споры, побочные темы и общий итог. Любая часть может быть
    не записана.
    """

    agreed: str | None = None
    argued: str | None = None
    taken: str | None = None
    quote: Quote | None = None
    lead: str | None = None
    by_chapter: tuple[OutcomeItem, ...] = ()
    debates: tuple[OutcomeItem, ...] = ()
    aside: str | None = None
    verdict: str | None = None

    @property
    def is_empty(self) -> bool:
        """Пусто, только если не записано ничего: итоги из одной полной формы
        тоже итоги, и молча пропасть им нельзя."""
        return not any(
            (
                self.agreed,
                self.argued,
                self.taken,
                self.quote,
                self.lead,
                self.by_chapter,
                self.debates,
                self.aside,
                self.verdict,
            )
        )

    def items(self) -> tuple[OutcomeItem, ...]:
        """Все пункты полной формы: по главам и споры, по порядку."""
        return self.by_chapter + self.debates


@dataclass(frozen=True)
class Link:
    title: str
    url: str


@dataclass(frozen=True)
class Place:
    """Место встречи по частям.

    Две формы нужны для разных задач: короткая («хакспейс s4m.space, комната
    413») отличает место в ленте, полная («Дом77, Ленинградская 77, 4 этаж,
    комната 413, Самара») доводит до двери того, кто едет впервые. Собирать
    полную форму из короткой обратным разбором строки было бы гаданием, поэтому
    части хранятся раздельно.
    """

    venue: str
    building: str
    room: str
    street: str | None = None
    floor: str | None = None
    city: str | None = None
    # Карточка места на карте: по ней доходят до двери быстрее, чем по адресу.
    map: str | None = None

    @property
    def short(self) -> str:
        return ", ".join(part for part in (self.venue, self.room) if part)

    @property
    def full(self) -> str:
        parts = (self.building, self.street, self.floor, self.room, self.city)
        return ", ".join(part for part in parts if part)

    def __str__(self) -> str:
        """По умолчанию место называют коротко: так оно стоит в лентах."""
        return self.short


@dataclass(frozen=True)
class MeetingImage:
    """Картинка встречи: путь внутри `app/web/static` и подпись.

    Подпись не собирается сама, как у обложки: на афише и карточке итогов
    текст, которого больше нигде на странице нет, и «афиша встречи #5» его не
    передаст.
    """

    src: str
    alt: str


@dataclass(frozen=True)
class Meeting:
    """Встреча клуба: книжная часть и формат, обе необязательны.

    `poster` — афиша, с которой встречу анонсировали, `recap_card` — карточка
    итогов. Какую из них показывать, решает `app.core.view.meeting_image`.
    """

    id: str
    date: Date
    time: str
    place: Place
    host: str | None = None
    book_id: str | None = None
    chapters: tuple[DiscussedChapter, ...] = ()
    format: MeetingFormat | None = None
    title: str | None = None
    announce: tuple[str, ...] = ()
    outcome: Outcome | None = None
    topics: tuple[str, ...] = ()
    links: tuple[Link, ...] = ()
    poster: MeetingImage | None = None
    recap_card: MeetingImage | None = None

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
class Space:
    """Площадка, в которой живёт клуб: её сайт и каналы связи.

    `thread` — ветка клуба внутри общего чата площадки, а не отдельный чат.
    """

    name: str
    site: str | None = None
    channel: str | None = None
    chat: str | None = None
    thread: str | None = None


@dataclass(frozen=True)
class Card:
    """Карточка на странице «О клубе»: короткий заголовок и строка пояснения."""

    label: str
    text: str


@dataclass(frozen=True)
class Club:
    """Сам клуб: постоянные условия, порядок встречи и связь."""

    name: str
    descriptor: str
    about: tuple[str, ...]
    place: Place
    slot: str
    time: str
    duration_minutes: int
    timezone: str
    tagline: str | None = None
    routine: tuple[str, ...] = ()
    terms: tuple[str, ...] = ()
    telegram: str | None = None
    space: Space | None = None
    topic_notes: dict[str, str] = field(default_factory=dict)
    marquee: tuple[str, ...] = ()
    # Год основания и фраза-манифест — для заставки главной. Год есть и в
    # тексте «О клубе», но разбирать прозу ради числа — гадание.
    since: int | None = None
    manifesto: str | None = None
    # Страница «О клубе»: заголовок, рукописная строка (перевод строки делит её
    # на строки), факты о клубе и правила встречи карточками. Без них страница
    # собирается из `about` и `routine`, как раньше.
    about_title: str | None = None
    about_hand: str | None = None
    facts: tuple[Card, ...] = ()
    rules: tuple[Card, ...] = ()


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
