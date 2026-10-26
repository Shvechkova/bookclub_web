"""Встреча как событие календаря и ссылка «в календарь»."""

from datetime import datetime
from urllib.parse import parse_qs, unquote, urlparse

from app.core.view import ClubView, google_calendar_url
from tests.factories import a_book, a_club, a_meeting, a_place, some_data


def view(books=(), meetings=(), club=None) -> ClubView:
    return ClubView(some_data(books=books, meetings=meetings, club=club))


def test_event_of_a_book_meeting_names_the_book_and_lasts_the_club_hour():
    club = ClubView(
        some_data(
            books=[a_book("b1", chapters=7, title="Мифический человеко-месяц")],
            meetings=[
                a_meeting(
                    "m1",
                    "2026-09-23",
                    book="b1",
                    planned=(1, 2, 3, 4, 5, 6, 7),
                )
            ],
        )
    )
    event = club.calendar_event(club.data.meeting("m1"))

    assert event.title == "Мифический человеко-месяц · главы 1–7"
    assert event.start == datetime(2026, 9, 23, 19, 30)
    assert event.end == datetime(2026, 9, 23, 21, 0)
    assert event.location == "Дом77, Ленинградская 77, 4 этаж, комната 413, Самара"
    assert event.timezone == "Europe/Samara"


def test_event_of_a_meeting_without_a_book_takes_its_own_title():
    club = view(meetings=[a_meeting("m1", "2026-09-23", title="День открытых дверей")])
    event = club.calendar_event(club.data.meeting("m1"))

    assert event.title == "День открытых дверей"


def test_event_takes_the_place_of_the_meeting_when_it_differs_from_the_club():
    elsewhere = a_place(venue="летник Дома 77", building="Дом77", room="летник")
    club = view(meetings=[a_meeting("m1", "2026-09-23", title="Выездная", place=elsewhere)])
    event = club.calendar_event(club.data.meeting("m1"))

    assert event.location == elsewhere.full


def test_the_calendar_link_carries_title_time_zone_and_address():
    club = view(
        books=[a_book("b1", chapters=7, title="Мифический человеко-месяц")],
        meetings=[a_meeting("m1", "2026-09-23", book="b1", planned=(1, 2))],
    )
    event = club.calendar_event(club.data.meeting("m1"))

    url = google_calendar_url(event)
    query = parse_qs(urlparse(url).query)

    assert urlparse(url).netloc == "calendar.google.com"
    assert query["action"] == ["TEMPLATE"]
    assert query["text"] == ["Мифический человеко-месяц · главы 1–2"]
    assert query["dates"] == ["20260923T193000/20260923T210000"]
    assert query["ctz"] == ["Europe/Samara"]
    assert query["location"] == ["Дом77, Ленинградская 77, 4 этаж, комната 413, Самара"]


def test_the_link_escapes_values_instead_of_breaking_the_query():
    club = view(meetings=[a_meeting("m1", "2026-09-23", title="Брукс & главы 1–7")])

    url = google_calendar_url(club.calendar_event(club.data.meeting("m1")))

    assert "&главы" not in url
    assert unquote(parse_qs(urlparse(url).query)["text"][0]) == "Брукс & главы 1–7"
