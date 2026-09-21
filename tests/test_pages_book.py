"""Страница книги: оглавление со встречами и конспектами, выборочное чтение,
архивная и дропнутая книга."""

import re
from datetime import date

from fastapi.testclient import TestClient

from app.core.models import BookStatus, Chapter
from app.core.view import ClubView
from app.web.app import create_app
from tests.factories import a_book, a_meeting, some_data

TODAY = date(2026, 9, 21)


def page(path, books=(), meetings=()) -> str:
    view = ClubView(some_data(books=books, meetings=meetings))
    response = TestClient(create_app(view=view, today=lambda: TODAY)).get(path)
    assert response.status_code == 200
    return response.text


def chapter_row(html: str, number: int) -> str:
    found = re.search(
        rf'<li class="chapter"[^>]*data-chapter="{number}".*?</li>', html, re.S
    )
    assert found is not None, f"строки главы {number} на странице нет"
    return found.group(0)


def test_passed_chapters_show_the_meetings_that_covered_them():
    book = a_book("b1", chapters=3)
    html = page(
        "/books/b1",
        books=[book],
        meetings=[
            a_meeting("m1", "2026-01-07", book="b1", closed=(1,)),
            a_meeting("m2", "2026-01-21", book="b1", closed=(2,)),
        ],
    )

    assert "/meetings/m1" in chapter_row(html, 1)
    assert "/meetings/m2" in chapter_row(html, 2)
    assert "/meetings/" not in chapter_row(html, 3)


def test_a_chapter_discussed_twice_shows_both_meetings():
    book = a_book("b1", chapters=3)
    html = page(
        "/books/b1",
        books=[book],
        meetings=[
            a_meeting("m1", "2026-01-07", book="b1", carried=(2,)),
            a_meeting("m2", "2026-01-21", book="b1", closed=(2,)),
        ],
    )
    row = chapter_row(html, 2)

    assert "/meetings/m1" in row
    assert "/meetings/m2" in row


def test_a_selectively_read_book_marks_the_chapters_left_out():
    book = a_book("b1", chapters=5, taken=(1, 3))
    html = page(
        "/books/b1",
        books=[book],
        meetings=[a_meeting("m1", "2026-01-07", book="b1", closed=(1,))],
    )

    assert "не взята" in chapter_row(html, 2)
    assert "не взята" not in chapter_row(html, 3)
    assert "1 из 2" in html


def test_a_chapter_shows_its_notes_next_to_its_meeting():
    book = a_book(
        "b1",
        chapters=1,
        chapters_override=(Chapter(number=1, title="Введение", notes_url="https://notes/1"),),
    )
    html = page(
        "/books/b1",
        books=[book],
        meetings=[a_meeting("m1", "2026-01-07", book="b1", closed=(1,))],
    )
    row = chapter_row(html, 1)

    assert "/meetings/m1" in row
    assert "https://notes/1" in row


def test_a_closed_book_shows_its_meeting_count_and_conclusions():
    book = a_book(
        "b1",
        chapters=3,
        status=BookStatus.CLOSED,
        close_note="Дочитали и закрыли.",
        takeaways=("Первый вывод.", "Второй вывод."),
    )
    html = page(
        "/books/b1",
        books=[book],
        meetings=[
            a_meeting("m1", "2026-01-07", book="b1", closed=(1, 2)),
            a_meeting("m2", "2026-01-21", book="b1", closed=(3,)),
        ],
    )

    assert "2 встречи" in html
    assert "Дочитали и закрыли." in html
    assert "Первый вывод." in html


def test_an_archived_book_shows_its_period_instead_of_meetings():
    book = a_book(
        "archive",
        chapters=2,
        status=BookStatus.CLOSED,
        period="весна 2025",
        close_note="Прочитали до того, как начали записывать встречи.",
    )
    html = page("/books/archive", books=[book])

    assert "весна 2025" in html
    assert "не начиналось" not in html
    assert "встреч" not in html.split("<main>")[1].split("Прочитали")[0]


def test_a_dropped_book_shows_how_far_it_got_without_a_ratio():
    book = a_book(
        "b1",
        chapters=10,
        status=BookStatus.DROPPED,
        close_note="Бросили: язык оказался неподъёмным.",
    )
    html = page(
        "/books/b1",
        books=[book],
        meetings=[a_meeting("m1", "2026-01-07", book="b1", closed=(1, 2))],
    )

    assert "Закрыто 2 главы" in html
    assert "Бросили" in html
    assert "2 из 10" not in html


def test_a_book_links_to_its_notes():
    book = a_book("b1", chapters=2, notes_url="https://notes/book")
    html = page("/books/b1", books=[book])

    assert "https://notes/book" in html


def test_an_unknown_book_is_not_found():
    view = ClubView(some_data())
    response = TestClient(create_app(view=view, today=lambda: TODAY)).get("/books/нет")

    assert response.status_code == 404
