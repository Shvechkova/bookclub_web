"""Ядро: какая встреча ближайшая и какая была последней."""

from datetime import date

from app.core.view import ClubView
from tests.factories import a_book, a_meeting, some_data


def view(meetings=()) -> ClubView:
    return ClubView(some_data(meetings=meetings))


def test_the_upcoming_meeting_is_the_first_one_that_has_not_happened():
    club = view(
        [
            a_meeting("past", "2026-09-09", title="Прошлая"),
            a_meeting("next", "2026-09-23", title="Ближайшая"),
            a_meeting("later", "2026-10-07", title="Дальняя"),
        ]
    )

    upcoming = club.upcoming_meeting(date(2026, 9, 21))

    assert upcoming is not None
    assert upcoming.meeting.id == "next"


def test_a_meeting_today_still_counts_as_upcoming():
    club = view([a_meeting("today", "2026-09-23", title="Сегодня")])

    upcoming = club.upcoming_meeting(date(2026, 9, 23))

    assert upcoming is not None
    assert upcoming.meeting.id == "today"


def test_there_is_no_upcoming_meeting_when_all_of_them_have_passed():
    club = view([a_meeting("past", "2026-09-09", title="Прошлая")])

    assert club.upcoming_meeting(date(2026, 9, 21)) is None


def test_the_latest_past_meeting_is_the_most_recent_one_behind_us():
    club = view(
        [
            a_meeting("older", "2026-08-26", title="Раньше"),
            a_meeting("recent", "2026-09-09", title="Позже"),
            a_meeting("future", "2026-09-23", title="Впереди"),
        ]
    )

    latest = club.latest_past_meeting(date(2026, 9, 21))

    assert latest is not None
    assert latest.meeting.id == "recent"


# --- первая встреча по книге -------------------------------------------------


def test_the_earliest_meeting_of_a_book_is_its_first():
    view = ClubView(
        some_data(
            books=[a_book("b1", chapters=9)],
            meetings=[
                a_meeting("m1", "2026-09-23", book="b1", planned=(1, 2)),
                a_meeting("m2", "2026-10-07", book="b1", planned=(3, 4)),
                a_meeting("m3", "2026-10-21", book="b1", planned=(5, 6)),
            ],
        )
    )

    assert view.is_first_of_book(view.data.meeting("m1"))
    assert not view.is_first_of_book(view.data.meeting("m2"))
    assert not view.is_first_of_book(view.data.meeting("m3"))


def test_a_meeting_without_a_book_is_never_first():
    view = ClubView(some_data(meetings=[a_meeting("lone", "2026-09-23", title="ADR-дуэль")]))

    assert not view.is_first_of_book(view.data.meeting("lone"))


def test_a_meeting_added_earlier_takes_the_first_place():
    """Встречу могут записать задним числом — первой становится она."""
    view = ClubView(
        some_data(
            books=[a_book("b1", chapters=9)],
            meetings=[
                a_meeting("m1", "2026-09-23", book="b1", planned=(1, 2)),
                a_meeting("m0", "2026-09-09", book="b1", closed=(1,)),
            ],
        )
    )

    assert view.is_first_of_book(view.data.meeting("m0"))
    assert not view.is_first_of_book(view.data.meeting("m1"))
