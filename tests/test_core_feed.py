"""Ядро: темп, каталог понятий, заголовок встречи, лента истории."""

from app.core.models import BookStatus
from app.core.view import BookSegment, ClubView, LoneMeeting
from tests.factories import a_book, a_club, a_meeting, a_term, some_data


def view(books=(), meetings=(), club=None) -> ClubView:
    return ClubView(some_data(books=books, meetings=meetings, club=club))


# --- 3.6 темп ----------------------------------------------------------------


def test_pace_is_averaged_over_the_last_three_meetings():
    book = a_book("b1", chapters=12)
    club = view(
        books=[book],
        meetings=[
            a_meeting("m1", "2026-01-07", book="b1", closed=(1, 2, 3, 4)),
            a_meeting("m2", "2026-01-21", book="b1", closed=(5, 6, 7, 8)),
            a_meeting("m3", "2026-02-04", book="b1", closed=(9,)),
            a_meeting("m4", "2026-02-18", book="b1", closed=(10,)),
            a_meeting("m5", "2026-03-04", book="b1", closed=(11,)),
        ],
    )

    assert club.pace(book) == 1.0


def test_pace_is_unknown_when_nothing_has_been_closed():
    book = a_book("b1", chapters=5)
    club = view(books=[book], meetings=[a_meeting("m1", "2026-01-07", book="b1")])

    assert club.pace(book) is None


def test_meetings_without_closed_chapters_do_not_drag_the_pace_down():
    book = a_book("b1", chapters=12)
    club = view(
        books=[book],
        meetings=[
            a_meeting("m1", "2026-01-07", book="b1", closed=(1, 2)),
            a_meeting("m2", "2026-01-21", book="b1", carried=(3,)),
            a_meeting("m3", "2026-02-04", book="b1", closed=(3, 4)),
        ],
    )

    assert club.pace(book) == 2.0


# --- 3.7 каталог понятий -----------------------------------------------------


def test_a_topic_comes_from_a_meeting():
    club = view(
        meetings=[
            a_meeting("m1", "2026-01-07", title="Встреча", topics=("Уровни изоляции",))
        ]
    )

    catalogue = club.topics()

    assert [entry.name for entry in catalogue] == ["Уровни изоляции"]
    assert [m.id for m in catalogue[0].meetings] == ["m1"]


def test_one_topic_on_several_meetings_is_a_single_entry():
    club = view(
        meetings=[
            a_meeting("m1", "2026-01-07", title="Раз", topics=("Саги",)),
            a_meeting("m2", "2026-01-21", title="Два", topics=("Саги",)),
            a_meeting("m3", "2026-02-04", title="Три", topics=("Саги",)),
        ]
    )

    catalogue = club.topics()

    assert len(catalogue) == 1
    assert [m.id for m in catalogue[0].meetings] == ["m1", "m2", "m3"]


def test_a_topic_knows_its_glossary_term_when_there_is_one():
    saga = a_term("saga", "Сага", aliases=("Саги",))
    club = ClubView(
        some_data(
            meetings=[a_meeting("m1", "2026-01-07", title="Раз", topics=("Саги", "Кворум"))],
            glossary=[saga],
        )
    )

    by_name = {entry.name: entry for entry in club.topics()}

    assert by_name["Саги"].term == saga
    assert by_name["Кворум"].term is None


# --- 3.8 заголовок встречи и формат -----------------------------------------


def test_a_meeting_with_a_book_is_titled_by_book_and_chapters():
    book = a_book("b1", chapters=12, title="Создание микросервисов")
    club = view(
        books=[book],
        meetings=[a_meeting("m1", "2026-01-07", book="b1", closed=(1, 2), fmt="Лайтнинги")],
    )
    meeting = club.data.meeting("m1")

    assert club.title_of(meeting) == "Создание микросервисов · главы 1–2"
    assert meeting.format is not None
    assert meeting.format.name == "Лайтнинги"


def test_chapters_that_are_not_consecutive_are_listed_one_by_one():
    book = a_book("b1", chapters=12, title="Кабанчик")
    club = view(
        books=[book], meetings=[a_meeting("m1", "2026-01-07", book="b1", closed=(3, 7))]
    )

    assert club.title_of(club.data.meeting("m1")) == "Кабанчик · главы 3, 7"


def test_a_single_chapter_is_named_in_the_singular():
    book = a_book("b1", chapters=12, title="Брукс")
    club = view(
        books=[book], meetings=[a_meeting("m1", "2026-01-07", book="b1", closed=(4,))]
    )

    assert club.title_of(club.data.meeting("m1")) == "Брукс · глава 4"


def test_an_upcoming_meeting_is_titled_by_its_planned_chapters():
    book = a_book("b1", chapters=12, title="Брукс")
    club = view(
        books=[book], meetings=[a_meeting("m1", "2026-12-02", book="b1", planned=(8, 9))]
    )
    meeting = club.data.meeting("m1")

    assert club.title_of(meeting) == "Брукс · главы 8–9"
    assert club.planned_numbers(meeting) == (8, 9)
    assert club.passed_numbers(book) == ()


def test_a_meeting_without_a_book_keeps_its_own_title():
    club = view(
        meetings=[a_meeting("m1", "2026-01-07", title="ADR-дуэль", fmt="ADR-дуэль")]
    )

    assert club.title_of(club.data.meeting("m1")) == "ADR-дуэль"


def test_a_meeting_without_a_book_and_without_a_format_keeps_its_title():
    club = view(meetings=[a_meeting("m1", "2026-01-07", title="Голосование")])
    meeting = club.data.meeting("m1")

    assert club.title_of(meeting) == "Голосование"
    assert meeting.format is None


# --- 3.9 лента истории -------------------------------------------------------


def test_books_are_segments_and_their_meetings_sit_inside():
    first = a_book("b1", number=1, status=BookStatus.CLOSED)
    second = a_book("b2", number=2, status=BookStatus.READING)
    club = view(
        books=[first, second],
        meetings=[
            a_meeting("m1", "2026-01-07", book="b1", closed=(1,)),
            a_meeting("m2", "2026-01-21", book="b1", closed=(2,)),
            a_meeting("m3", "2026-02-04", book="b2", closed=(1,)),
        ],
    )

    feed = club.history()

    assert [type(entry) for entry in feed] == [BookSegment, BookSegment]
    assert feed[0].book.id == "b2"
    assert [m.meeting.id for m in feed[0].meetings] == ["m3"]
    assert [m.meeting.id for m in feed[1].meetings] == ["m1", "m2"], (
        "внутри книги встречи идут по порядку чтения: с первой"
    )


def test_a_meeting_outside_any_book_sits_between_segments():
    first = a_book("b1", number=1, status=BookStatus.CLOSED)
    second = a_book("b2", number=2, status=BookStatus.READING)
    club = view(
        books=[first, second],
        meetings=[
            a_meeting("m1", "2026-01-07", book="b1", closed=(1,)),
            a_meeting("lone", "2026-01-28", title="Голосование"),
            a_meeting("m3", "2026-02-04", book="b2", closed=(1,)),
        ],
    )

    feed = club.history()

    assert [type(entry) for entry in feed] == [BookSegment, LoneMeeting, BookSegment]
    assert feed[1].meeting.meeting.id == "lone"


def test_a_book_without_meetings_keeps_its_place_by_number():
    archive = a_book("archive", number=1, status=BookStatus.CLOSED, period="весна 2025")
    current = a_book("current", number=2, status=BookStatus.READING)
    club = view(
        books=[archive, current],
        meetings=[a_meeting("m1", "2026-02-04", book="current", closed=(1,))],
    )

    feed = club.history()

    assert [entry.book.id for entry in feed] == ["current", "archive"]
    assert feed[1].meetings == ()
    assert feed[1].book.period == "весна 2025"


# --- прочитанные книги -------------------------------------------------------


def test_finished_books_go_from_the_latest_closed_to_the_first():
    club = view(
        books=[
            a_book("first", number=1, status=BookStatus.CLOSED),
            a_book("third", number=3, status=BookStatus.CLOSED),
            a_book("second", number=2, status=BookStatus.CLOSED),
        ]
    )

    assert [book.id for book in club.finished_books()] == ["third", "second", "first"]


def test_only_closed_books_count_as_finished():
    club = view(
        books=[
            a_book("closed", number=1, status=BookStatus.CLOSED),
            a_book("dropped", number=2, status=BookStatus.DROPPED),
            a_book("reading", number=3, status=BookStatus.READING),
            a_book("queued", number=4, status=BookStatus.QUEUED),
        ]
    )

    assert [book.id for book in club.finished_books()] == ["closed"]


def test_without_closed_books_nothing_is_finished():
    club = view(books=[a_book("reading", status=BookStatus.READING)])

    assert club.finished_books() == ()
