"""Ядро: номера встреч, пройденные главы, прогресс, связь главы со встречами."""

from app.core.models import BookStatus
from app.core.view import ClubView
from tests.factories import a_book, a_meeting, some_data


def view(books=(), meetings=()) -> ClubView:
    return ClubView(some_data(books=books, meetings=meetings))


# --- 3.1 сквозной номер встречи ---------------------------------------------


def test_meeting_number_comes_from_the_order_of_dates():
    club = view(
        meetings=[
            a_meeting("m1", "2026-01-07", title="Первая"),
            a_meeting("m2", "2026-01-21", title="Вторая"),
            a_meeting("m3", "2026-02-04", title="Третья"),
        ]
    )

    assert [(m.number, m.meeting.id) for m in club.numbered_meetings()] == [
        (1, "m1"),
        (2, "m2"),
        (3, "m3"),
    ]


def test_a_meeting_inserted_in_the_middle_shifts_the_rest():
    before = view(
        meetings=[
            a_meeting("m1", "2026-01-07", title="Первая"),
            a_meeting("m2", "2026-02-04", title="Вторая"),
        ]
    )
    assert before.number_of("m2") == 2

    after = view(
        meetings=[
            a_meeting("m1", "2026-01-07", title="Первая"),
            a_meeting("m2", "2026-02-04", title="Вторая"),
            a_meeting("inserted", "2026-01-21", title="Вставленная"),
        ]
    )

    assert after.number_of("inserted") == 2
    assert after.number_of("m2") == 3


def test_each_book_counts_its_meetings_from_one():
    club = view(
        books=[a_book("b1"), a_book("b2", number=2)],
        meetings=[
            a_meeting("m1", "2026-01-07", book="b1", closed=(1,)),
            a_meeting("m2", "2026-01-21", book="b1", closed=(2,)),
            a_meeting("m3", "2026-02-04", book="b2", closed=(1,)),
        ]
    )

    assert club.number_of("m2") == 2
    assert club.number_of("m3") == 1, "у новой книги счёт встреч начинается заново"


def test_meetings_without_a_book_are_counted_among_themselves():
    club = view(
        books=[a_book("b1")],
        meetings=[
            a_meeting("m1", "2026-01-07", book="b1", closed=(1,)),
            a_meeting("m2", "2026-01-21", title="Голосование"),
            a_meeting("m3", "2026-02-04", book="b1", closed=(2,)),
            a_meeting("m4", "2026-02-18", title="Разбор года"),
        ]
    )

    assert club.number_of("m3") == 2
    assert club.number_of("m4") == 2


# --- 3.2 пройденные главы ----------------------------------------------------


def test_passed_chapters_are_the_union_of_closed_ones():
    book = a_book("b1", chapters=5)
    club = view(
        books=[book],
        meetings=[
            a_meeting("m1", "2026-01-07", book="b1", closed=(1, 2)),
            a_meeting("m2", "2026-01-21", book="b1", closed=(3,)),
        ],
    )

    assert club.passed_numbers(book) == (1, 2, 3)


def test_a_carried_chapter_is_not_passed_until_it_is_closed():
    book = a_book("b1", chapters=5)
    carried_only = view(
        books=[book],
        meetings=[a_meeting("m1", "2026-01-07", book="b1", closed=(1,), carried=(2,))],
    )

    assert carried_only.passed_numbers(book) == (1,)
    assert carried_only.started_numbers(book) == (2,)

    closed_later = view(
        books=[book],
        meetings=[
            a_meeting("m1", "2026-01-07", book="b1", closed=(1,), carried=(2,)),
            a_meeting("m2", "2026-01-21", book="b1", closed=(2,)),
        ],
    )

    assert closed_later.passed_numbers(book) == (1, 2)
    assert closed_later.started_numbers(book) == ()


def test_reading_has_not_started_when_nothing_is_closed():
    book = a_book("b1", chapters=5)
    club = view(books=[book], meetings=[a_meeting("m1", "2026-01-07", book="b1")])

    assert club.passed_numbers(book) == ()
    assert club.reading_has_started(book) is False


# --- 3.3 прогресс от взятых глав --------------------------------------------


def test_progress_counts_only_the_chapters_taken_for_reading():
    book = a_book("b1", chapters=12, taken=(1, 3, 5))
    club = view(
        books=[book],
        meetings=[a_meeting("m1", "2026-01-07", book="b1", closed=(1, 3))],
    )

    progress = club.progress(book)

    assert progress is not None
    assert (progress.done, progress.taken) == (2, 3)


def test_a_book_read_in_full_takes_all_of_its_chapters():
    book = a_book("b1", chapters=3)
    club = view(
        books=[book], meetings=[a_meeting("m1", "2026-01-07", book="b1", closed=(1,))]
    )

    progress = club.progress(book)

    assert progress is not None
    assert (progress.done, progress.taken) == (1, 3)


def test_closing_a_chapter_outside_the_taken_set_does_not_inflate_progress():
    book = a_book("b1", chapters=12, taken=(1, 3, 5))
    club = view(
        books=[book],
        meetings=[a_meeting("m1", "2026-01-07", book="b1", closed=(1, 2))],
    )

    progress = club.progress(book)

    assert progress is not None
    assert (progress.done, progress.taken) == (1, 3)


# --- 3.4 глава и встреча: многие ко многим ----------------------------------


def test_one_meeting_can_close_several_chapters():
    book = a_book("b1", chapters=5)
    club = view(
        books=[book], meetings=[a_meeting("m1", "2026-01-07", book="b1", closed=(1, 2))]
    )

    chapters = club.chapters_of(book)

    assert [c.chapter.number for c in chapters[:2]] == [1, 2]
    assert [m.id for m in chapters[0].meetings] == ["m1"]
    assert [m.id for m in chapters[1].meetings] == ["m1"]


def test_one_chapter_can_have_several_meetings():
    book = a_book("b1", chapters=5)
    club = view(
        books=[book],
        meetings=[
            a_meeting("m1", "2026-01-07", book="b1", carried=(3,)),
            a_meeting("m2", "2026-01-21", book="b1", closed=(3,)),
        ],
    )

    third = club.chapters_of(book)[2]

    assert [m.id for m in third.meetings] == ["m1", "m2"]
    assert third.is_passed is True


def test_chapters_do_not_have_to_be_consecutive():
    book = a_book("b1", chapters=7, taken=(3, 7))
    club = view(
        books=[book],
        meetings=[a_meeting("m1", "2026-01-07", book="b1", closed=(3, 7))],
    )

    chapters = club.chapters_of(book)
    passed = [c.chapter.number for c in chapters if c.is_passed]
    skipped = [c.chapter.number for c in chapters if not c.is_taken]

    assert passed == [3, 7]
    assert skipped == [1, 2, 4, 5, 6]


# --- 3.5 число встреч по книге ----------------------------------------------


def test_a_book_being_read_does_not_show_a_meeting_count():
    book = a_book("b1", status=BookStatus.READING)
    club = view(
        books=[book],
        meetings=[
            a_meeting("m1", "2026-01-07", book="b1", closed=(1,)),
            a_meeting("m2", "2026-01-21", book="b1", closed=(2,)),
        ],
    )

    assert club.meeting_count(book) is None


def test_a_closed_book_shows_how_many_meetings_it_took():
    book = a_book("b1", status=BookStatus.CLOSED)
    club = view(
        books=[book],
        meetings=[
            a_meeting("m1", "2026-01-07", book="b1", closed=(1,)),
            a_meeting("m2", "2026-01-21", book="b1", closed=(2, 3)),
        ],
    )

    assert club.meeting_count(book) == 2


def test_a_book_read_before_the_club_kept_records_shows_no_count():
    book = a_book("b1", status=BookStatus.CLOSED, period="весна 2025")
    club = view(books=[book], meetings=[])

    assert club.meeting_count(book) is None
    assert club.has_recorded_history(book) is False
    assert club.progress(book) is None
