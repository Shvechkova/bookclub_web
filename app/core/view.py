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
from datetime import datetime, timedelta
from urllib.parse import quote

from app.core.models import (
    Book,
    BookStatus,
    Chapter,
    Club,
    ClubData,
    Meeting,
    MeetingImage,
    OutcomeItem,
    Term,
)

# Сколько чего показывает главная. Границы — часть выборки, а не вёрстки:
# «восемь свежих понятий» должно совпадать у сайта и у анонса.
RECENT_TOPICS = 8
RECENT_DEBATES = 3
GALLERY_SIZE = 6


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
    """Тема встреч: где обсуждали и какое понятие словаря за ней стоит.

    `term` пуст, если темы нет в словаре: словарь — справочник, а не обязательный
    список тем, и тема без определения остаётся просто темой.
    """

    name: str
    term: Term | None
    meetings: tuple[Meeting, ...]


@dataclass(frozen=True)
class GlossaryLetter:
    """Буква указателя словаря и понятия на неё, по алфавиту."""

    letter: str
    terms: tuple[Term, ...]


@dataclass(frozen=True)
class TermChapterView:
    """Глава, где разобрано понятие, с подписью и адресом конспекта.

    Адрес пуст, если у главы в данных книги конспекта нет: подпись тогда
    стоит текстом, а догадку на месте адреса сайт не подставляет.
    """

    book: Book
    chapter: Chapter
    label: str
    url: str | None


@dataclass(frozen=True)
class FormatEntry:
    """Формат встречи и встречи, на которых его проводили."""

    name: str
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
class CalendarEvent:
    """Встреча как событие календаря.

    Собрана здесь, а не в шаблоне: то же событие нужно и сайту, и анонсу в
    канале, и боту — расходиться им незачем.
    """

    title: str
    start: datetime
    end: datetime
    location: str
    timezone: str


@dataclass(frozen=True)
class DebateCard:
    """Спор из итогов вместе со встречей, на которой о нём спорили."""

    meeting: Meeting
    debate: OutcomeItem


@dataclass(frozen=True)
class GalleryItem:
    """Встреча с картинкой для блока «Как это было».

    Картинку выбирает `meeting_image`: витрина показывает то же, что страница
    встречи, и разойтись им не в чем.
    """

    meeting: Meeting
    image: MeetingImage
    is_upcoming: bool

    @property
    def is_recap(self) -> bool:
        return self.image == self.meeting.recap_card and not self.is_upcoming


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
        """Все встречи по датам; номер — порядковый внутри своей книги.

        Сквозной номер через все книги ничего не говорит читателю: «#4» у
        первой встречи по новой книге выглядит как пропуск трёх. Встречи без
        книжной части считаются отдельным рядом, между собой.
        """
        ordered = sorted(self._data.meetings, key=lambda meeting: (meeting.date, meeting.id))
        counters: dict[str | None, int] = {}
        numbered = []
        for meeting in ordered:
            counters[meeting.book_id] = counters.get(meeting.book_id, 0) + 1
            numbered.append(NumberedMeeting(number=counters[meeting.book_id], meeting=meeting))
        return tuple(numbered)

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

    def is_first_of_book(self, meeting: Meeting) -> bool:
        """Первая ли это встреча по своей книге.

        Считается по датам, а не по признаку в данных: встречу могут добавить
        задним числом, и тогда первой становится она — без правки прежней.
        """
        if meeting.book_id is None:
            return False
        book = self._data.book(meeting.book_id)
        if book is None:
            return False
        of_book = self.meetings_of(book)
        return bool(of_book) and of_book[0].id == meeting.id

    def reading_book(self) -> Book | None:
        """Книга, которую читают сейчас. Такая может быть только одна."""
        for book in self._data.books:
            if book.status is BookStatus.READING:
                return book
        return None

    def finished_books(self) -> tuple[Book, ...]:
        """Прочитанные клубом книги, последняя закрытая первой.

        Порядок — по номеру книги: книги берут и закрывают по очереди, так что
        больший номер закрыт позже. Брошенная книга сюда не попадает —
        «прочитали» про неё неправда.
        """
        closed = (book for book in self._data.books if book.status is BookStatus.CLOSED)
        return tuple(sorted(closed, key=lambda book: book.number, reverse=True))

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
                term=self.term_for(name),
                meetings=tuple(by_name[name]),
            )
            for name in order
        )

    # --- словарь ------------------------------------------------------------

    def term_for(self, name: str) -> Term | None:
        """Понятие словаря по теме: совпадение с названием или синонимом.

        Регистр и «ё» не различаются: тему пишут как придётся — «adr», «ADR»,
        «Ёмкость» и «Емкость» — и ссылка не должна пропадать из-за этого.
        """
        wanted = fold_name(name)
        for term in self._data.glossary:
            if any(fold_name(known) == wanted for known in term.names):
                return term
        return None

    def term(self, term_id: str) -> Term | None:
        for term in self._data.glossary:
            if term.id == term_id:
                return term
        return None

    def glossary_index(self) -> tuple[GlossaryLetter, ...]:
        """Словарь по буквам: сначала кириллица, потом латиница, потом прочее.

        Понятия клуба — вперемешку русские и английские («ADR», «UML»), и общий
        алфавитный порядок по кодам символов поставил бы латиницу перед
        кириллицей. Читатель сайта ищет по-русски, поэтому русские буквы первыми.
        """
        ordered = sorted(self._data.glossary, key=lambda term: _alphabet_key(term.name))
        letters: list[str] = []
        by_letter: dict[str, list[Term]] = {}
        for term in ordered:
            letter = _letter_of(term.name)
            if letter not in by_letter:
                letters.append(letter)
                by_letter[letter] = []
            by_letter[letter].append(term)
        return tuple(
            GlossaryLetter(letter=letter, terms=tuple(by_letter[letter])) for letter in letters
        )

    def term_chapters(self, term: Term) -> tuple[TermChapterView, ...]:
        """Главы понятия с подписью «книга, гл. N» и адресом конспекта главы.

        Подпись — по короткому названию книги: полное «…, 2-е издание» в строку
        ссылок не помещается. Книга и глава существуют — это проверено на входе.
        """
        views = []
        for reference in term.chapters:
            book = self._data.book(reference.book_id)
            chapter = book.chapter(reference.number) if book else None
            if book is None or chapter is None:
                continue
            views.append(
                TermChapterView(
                    book=book,
                    chapter=chapter,
                    label=f"{book.short_title or book.title}, гл. {chapter.number}",
                    url=chapter.notes_url,
                )
            )
        return tuple(views)

    def related_of(self, term: Term) -> tuple[Term, ...]:
        """Связанные понятия в том порядке, в каком их записали."""
        found = (self.term(term_id) for term_id in term.related)
        return tuple(item for item in found if item is not None)

    # --- форматы ------------------------------------------------------------

    def formats(self, today: Day) -> tuple[FormatEntry, ...]:
        """Форматы, которые клуб уже проводил. Отдельного списка форматов нет.

        Формат, назначенный будущей встрече, сюда не попадает: перечень отвечает
        на вопрос «что клуб делал», а не «что собирается».
        """
        order: list[str] = []
        by_name: dict[str, list[Meeting]] = {}
        for numbered in self.numbered_meetings():
            meeting = numbered.meeting
            if meeting.date >= today or meeting.format is None:
                continue
            if meeting.format.name not in by_name:
                order.append(meeting.format.name)
                by_name[meeting.format.name] = []
            by_name[meeting.format.name].append(meeting)
        return tuple(
            FormatEntry(name=name, meetings=tuple(by_name[name])) for name in order
        )

    # --- календарь -----------------------------------------------------------

    def chapters_of_meeting(self, meeting: Meeting) -> tuple[Chapter, ...]:
        """Главы встречи с названиями, по порядку номеров."""
        book = self._data.book(meeting.book_id) if meeting.book_id else None
        if book is None:
            return ()
        numbers = sorted({item.number for item in meeting.chapters})
        found = (book.chapter(number) for number in numbers)
        return tuple(chapter for chapter in found if chapter is not None)

    def calendar_event(self, meeting: Meeting) -> CalendarEvent:
        """Данные события: название, начало, конец по длительности клуба, адрес."""
        hour, minute = (int(part) for part in meeting.time.split(":", 1))
        start = datetime.combine(meeting.date, datetime.min.time()).replace(
            hour=hour, minute=minute
        )
        return CalendarEvent(
            title=self.title_of(meeting),
            start=start,
            end=start + timedelta(minutes=self.club.duration_minutes),
            location=meeting.place.full,
            timezone=self.club.timezone,
        )

    # --- заголовок встречи --------------------------------------------------

    def planned_numbers(self, meeting: Meeting) -> tuple[int, ...]:
        return tuple(sorted(meeting.planned_numbers()))

    def short_title_of(self, meeting: Meeting) -> str:
        """Подпись встречи в одну строку: короткое название книги или своё."""
        book = self._data.book(meeting.book_id) if meeting.book_id else None
        if book is None:
            return meeting.title or ""
        return book.short_title or book.title

    def title_of(self, meeting: Meeting) -> str:
        """Заголовок встречи: из книжной части, если она есть, иначе собственный."""
        book = self._data.book(meeting.book_id) if meeting.book_id else None
        if book is None:
            return meeting.title or ""
        numbers = sorted(meeting.discussed_numbers()) or sorted(meeting.planned_numbers())
        phrase = chapter_phrase(numbers)
        return f"{book.title} · {phrase}" if phrase else book.title

    # --- витрина главной ---------------------------------------------------

    def _past_newest_first(self, today: Day) -> list[Meeting]:
        return [
            numbered.meeting
            for numbered in reversed(self.numbered_meetings())
            if is_past(numbered.meeting, today)
        ]

    def recent_topics(self, today: Day, limit: int = RECENT_TOPICS) -> tuple[TopicEntry, ...]:
        """Понятия прошедших встреч, свежие первыми, без повторов.

        Тема будущей встречи сюда не идёт: заставка говорит «о чём говорили»,
        а не «о чём собираемся». Запись берётся из каталога — с понятием
        словаря и всеми встречами темы.
        """
        catalogue = {entry.name: entry for entry in self.topics()}
        seen: list[str] = []
        for meeting in self._past_newest_first(today):
            for topic in meeting.topics:
                if topic not in seen:
                    seen.append(topic)
        return tuple(catalogue[name] for name in seen[:limit])

    def recent_debates(self, today: Day, limit: int = RECENT_DEBATES) -> tuple[DebateCard, ...]:
        """Свежие споры: от последней прошедшей встречи, внутри — по порядку записи."""
        cards = [
            DebateCard(meeting=meeting, debate=debate)
            for meeting in self._past_newest_first(today)
            if meeting.outcome is not None
            for debate in meeting.outcome.debates
        ]
        return tuple(cards[:limit])

    def gallery(self, today: Day, limit: int = GALLERY_SIZE) -> tuple[GalleryItem, ...]:
        """Встречи с картинкой, свежие первыми: ближайшая и прошедшие.

        Из будущих — только ближайшая: афиша дальних встреч ещё может
        поменяться, и витрина не должна обещать того, что не назначено.
        """
        upcoming = self.upcoming_meeting(today)
        candidates = ([upcoming.meeting] if upcoming else []) + self._past_newest_first(today)
        items = []
        for meeting in candidates:
            image = meeting_image(meeting, today)
            if image is not None:
                items.append(
                    GalleryItem(meeting=meeting, image=image, is_upcoming=not is_past(meeting, today))
                )
        return tuple(items[:limit])

    def gallery_default(self, today: Day) -> GalleryItem | None:
        """Что показано сразу: последняя прошедшая встреча с картинкой.

        Прошедшая, а не ближайшая: афиша ближайшей и так стоит выше, а блок
        отвечает на вопрос «как это было». Прошедших с картинкой нет — тогда
        ближайшая, лишь бы блок не стоял пустым.
        """
        items = self.gallery(today)
        for item in items:
            if not item.is_upcoming:
                return item
        return items[0] if items else None

    # --- лента истории ------------------------------------------------------

    def history(self) -> tuple[BookSegment | LoneMeeting, ...]:
        """Вся жизнь клуба одной лентой, свежее сверху.

        Книга — заголовок отрезка, её встречи — записи внутри, по порядку
        чтения: отрезок читается как оглавление, с первой встречи. Встречи без
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
            entries.append(BookSegment(book=book, meetings=inside))
        entries.extend(LoneMeeting(meeting=item) for item in lone[position:])
        return tuple(reversed(entries))


def fold_name(text: str) -> str:
    """Имя понятия для сравнения: без регистра, «ё» как «е», без краевых пробелов.

    Одно правило на поиск понятия по теме и на проверку словаря: разойдись они,
    проверка пропустила бы два понятия, которые тема не различает.
    """
    return text.strip().casefold().replace("ё", "е")


def _script_rank(char: str) -> int:
    """Кириллица — 0, латиница — 1, всё прочее (цифры, знаки) — 2."""
    if "\u0400" <= char <= "\u04ff":
        return 0
    if char.isascii() and char.isalpha():
        return 1
    return 2


def _letter_of(name: str) -> str:
    """Буква указателя: первая буква названия, «Ё» — под «Е», не буква — «#»."""
    first = fold_name(name)[:1]
    if not first or _script_rank(first) == 2:
        return "#"
    return first.upper()


def _alphabet_key(name: str) -> tuple[int, str]:
    folded = fold_name(name)
    return (_script_rank(folded[:1]) if folded else 2, folded)


def is_past(meeting: Meeting, today: Day) -> bool:
    """Прошла ли встреча. В свой день она ещё предстоящая."""
    return meeting.date < today


def meeting_image(meeting: Meeting, today: Day) -> MeetingImage | None:
    """Картинка встречи: до встречи — афиша, после — карточка итогов.

    Если карточки итогов нет, прошедшая встреча остаётся при афише: картинка с
    анонсом лучше пустого места, а неверной она не станет.
    """
    if is_past(meeting, today) and meeting.recap_card is not None:
        return meeting.recap_card
    return meeting.poster


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


def google_calendar_url(event: CalendarEvent, details: str = "") -> str:
    """Ссылка «в календарь» для Google.

    Время идёт локальным, а пояс — отдельным параметром `ctz`: так событие
    встаёт на правильный час и у того, кто живёт в другом поясе.
    """
    stamp = "%Y%m%dT%H%M%S"
    dates = f"{event.start.strftime(stamp)}/{event.end.strftime(stamp)}"
    parts = [
        "action=TEMPLATE",
        f"text={quote(event.title)}",
        f"dates={dates}",
        f"ctz={quote(event.timezone)}",
        f"location={quote(event.location)}",
    ]
    if details:
        parts.append(f"details={quote(details)}")
    return "https://calendar.google.com/calendar/render?" + "&".join(parts)
