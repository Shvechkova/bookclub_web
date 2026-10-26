"""Обложка книги на сайте и план ближайшей встречи в разделе «Сейчас»."""

from datetime import date

from fastapi.testclient import TestClient

from app.core.models import Chapter
from app.core.view import ClubView
from app.web.app import create_app
from tests.factories import a_book, a_meeting, some_data

TODAY = date(2026, 9, 21)

CHAPTERS = (
    Chapter(number=1, title="Смоляная яма"),
    Chapter(number=2, title="Закон Брукса"),
)


def page(path, books=(), meetings=(), today=TODAY) -> str:
    view = ClubView(some_data(books=books, meetings=meetings))
    response = TestClient(create_app(view=view, today=lambda: today)).get(path)
    assert response.status_code == 200, f"{path} ответил {response.status_code}"
    return response.text


def brooks(**overrides):
    return a_book(
        "brooks",
        chapters_override=CHAPTERS,
        title="Мифический человеко-месяц",
        author="Фредерик Брукс",
        **overrides,
    )


def upcoming():
    return a_meeting("m1", "2026-09-23", book="brooks", planned=(1, 2))


def test_the_book_page_shows_the_cover():
    html = page("/books/brooks", books=[brooks(cover="covers/brooks.jpg")])

    assert 'src="/static/covers/brooks.jpg"' in html
    assert 'alt="Обложка книги Мифический человеко-месяц"' in html


def test_the_reading_block_shows_the_cover_and_leads_to_the_book():
    html = page(
        "/",
        books=[brooks(cover="covers/brooks.jpg")],
        meetings=[upcoming()],
    )

    assert 'src="/static/covers/brooks.jpg"' in html
    assert 'class="cover" href="/books/brooks"' in html


def test_without_a_cover_the_place_is_taken_by_a_plate_with_title_and_author():
    for path in ("/books/brooks", "/"):
        html = page(path, books=[brooks()], meetings=[upcoming()])

        assert "cover-blank" in html, path
        assert "Фредерик Брукс" in html, path
        assert "/static/covers/" not in html, path


def test_the_reading_block_leads_with_the_chapters_of_the_next_meeting():
    html = page("/", books=[brooks()], meetings=[upcoming()])

    assert "Смоляная яма" in html
    assert "Закон Брукса" in html
    assert "Чтение ещё не начиналось" not in html


def test_without_a_next_meeting_the_reading_block_says_reading_has_not_started():
    """Плана нет — тогда честная строка лучше пустого места."""
    html = page("/", books=[brooks()])

    assert "Чтение ещё не начиналось" in html


def test_a_closed_book_gets_the_club_stamp_on_its_cover():
    from app.core.models import BookStatus

    closed = brooks(status=BookStatus.CLOSED, cover="covers/brooks.jpg")
    for path in ("/books/brooks", "/history"):
        html = page(path, books=[closed])
        cover = html[html.index('class="cover'):]
        cover = cover[: cover.index("</a>" if path == "/history" else "</span>\n</div>")]
        assert 'class="stamp"' in cover, f"{path}: на обложке закрытой книги нет печати"
    assert html.count('id="stamp"') == 1, "печать описана на странице один раз"


def test_a_book_being_read_has_no_stamp():
    html = page("/books/brooks", books=[brooks(cover="covers/brooks.jpg")])

    assert 'class="stamp"' not in html


def test_a_closed_book_is_marked_in_the_history_feed():
    from app.core.models import BookStatus

    closed = brooks(status=BookStatus.CLOSED, cover="covers/brooks.jpg")
    reading = a_book("next", number=2, title="Следующая")

    html = page("/history", books=[closed, reading])

    assert html.count('class="segment segment--closed"') == 1, (
        "название прочитанной книги приглушено, читаемой — нет"
    )


def test_the_book_being_read_wears_a_library_ticket_with_a_torn_stub():
    reading = brooks(number=5)
    meetings = [
        a_meeting("m1", "2026-09-09", book="brooks", closed=(1,)),
        a_meeting("m2", "2026-09-23", book="brooks", planned=(2,)),
    ]

    for path in ("/history", "/books/brooks"):
        html = page(path, books=[reading], meetings=meetings)
        ticket = html[html.index('class="status status--reading ticket"'):]
        ticket = ticket[: ticket.index("</span></span>") + len("</span></span>")]
        assert "читаем сейчас" in ticket.lower(), path
        assert '<span class="ticket-stub" aria-hidden="true">встреча №2</span>' in ticket, (
            f"{path}: на корешке номер встречи по книге, а не номер книги"
        )


def test_other_statuses_stay_plain_plates():
    from app.core.models import BookStatus

    html = page("/history", books=[brooks(status=BookStatus.CLOSED)])

    assert "ticket" not in html
