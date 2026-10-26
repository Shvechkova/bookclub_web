"""Визуальная система клуба: логотип, плашки состояний, бегущие строки."""

from datetime import date

from fastapi.testclient import TestClient

from app.core.models import BookStatus
from app.core.view import ClubView
from app.web.app import create_app
from tests.factories import a_book, a_club, a_meeting, some_data

TODAY = date(2026, 9, 21)
PATHS = ("/", "/history", "/about")


def page(path, books=(), meetings=(), club=None) -> str:
    view = ClubView(some_data(books=books, meetings=meetings, club=club))
    response = TestClient(create_app(view=view, today=lambda: TODAY)).get(path)
    assert response.status_code == 200
    return response.text


# --- 5.2 логотип -------------------------------------------------------------


def test_the_logo_is_on_every_page_and_leads_home():
    for path in PATHS:
        html = page(path)
        assert "Кабанья Читальня" in html
        assert "IT книжный клуб" in html
        assert 'class="logo" href="/"' in html


def test_the_mascot_is_shown_next_to_the_name():
    html = page("/")

    assert "/static/logo" in html


# --- 5.3 плашки состояний ----------------------------------------------------


def test_each_book_status_gets_its_own_badge_class():
    statuses = [
        (BookStatus.READING, "reading"),
        (BookStatus.QUEUED, "queued"),
        (BookStatus.CLOSED, "closed"),
        (BookStatus.DROPPED, "dropped"),
        (BookStatus.VOTING, "voting"),
    ]
    seen = set()
    for number, (status, slug) in enumerate(statuses, start=1):
        html = page(
            f"/books/b{number}",
            books=[a_book(f"b{number}", number=number, status=status)],
        )
        expected = f"status status--{slug}"
        assert expected in html
        seen.add(expected)

    assert len(seen) == len(statuses)


def test_the_status_badge_is_also_shown_in_the_history_feed():
    html = page(
        "/history",
        books=[a_book("b1", status=BookStatus.CLOSED)],
        meetings=[a_meeting("m1", "2026-01-07", book="b1", closed=(1,))],
    )

    assert "status status--closed" in html


# --- 5.4 бегущие строки ------------------------------------------------------


def test_the_marquee_repeats_its_text_so_it_is_cut_on_both_sides():
    html = page("/", club=a_club(marquee=("КНИЖНАЯ СРЕДА",)))

    assert html.count("КНИЖНАЯ СРЕДА") >= 4


def test_the_marquee_texts_come_from_the_club_data():
    html = page("/", club=a_club(marquee=("НАБОР ОТКРЫТ", "КОД · КНИГИ · СПОРЫ")))

    assert "НАБОР ОТКРЫТ" in html
    assert "КОД · КНИГИ · СПОРЫ" in html


def test_without_marquee_texts_there_are_no_running_lines():
    html = page("/", club=a_club(marquee=()))

    assert "marquee" not in html


# --- 5.5 приёмы анонса: рукописная подпись и наклейка ------------------------


def test_the_author_is_signed_by_hand_on_the_book_page():
    book = a_book("b1", status=BookStatus.READING, author="Фредерик Брукс")
    html = page("/books/b1", books=[book])

    assert '<span class="author-hand">Фредерик Брукс</span>' in html
    assert "family=Caveat" in html


def test_the_author_is_signed_by_hand_in_the_reading_block():
    book = a_book("b1", status=BookStatus.READING, author="Фредерик Брукс")
    meeting = a_meeting("m1", "2026-09-23", book="b1", planned=(1,))
    html = page("/", books=[book], meetings=[meeting])

    assert '<span class="author-hand">Фредерик Брукс</span>' in html


def test_the_first_meeting_of_a_book_wears_a_sticker():
    book = a_book("b1", chapters=6, status=BookStatus.READING)
    meetings = [
        a_meeting("m1", "2026-09-23", book="b1", planned=(1, 2)),
        a_meeting("m2", "2026-10-07", book="b1", planned=(3, 4)),
    ]

    for path in ("/", "/meetings/m1"):
        html = page(path, books=[book], meetings=meetings)
        assert "Начинаем новую книгу" in html, path
        assert "встреча #1" in html, path


def test_a_meeting_in_the_middle_of_a_book_has_no_sticker():
    book = a_book("b1", chapters=6, status=BookStatus.READING)
    meetings = [
        a_meeting("m1", "2026-09-09", book="b1", closed=(1, 2)),
        a_meeting("m2", "2026-10-07", book="b1", planned=(3, 4)),
    ]

    html = page("/meetings/m2", books=[book], meetings=meetings)

    assert "Начинаем новую книгу" not in html


def test_a_meeting_without_a_book_has_no_sticker():
    html = page("/meetings/lone", meetings=[a_meeting("lone", "2026-09-23", title="ADR-дуэль")])

    assert "Начинаем новую книгу" not in html
