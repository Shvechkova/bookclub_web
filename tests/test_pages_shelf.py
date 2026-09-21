"""Полка, каталог понятий, «О клубе», пустые состояния и отсутствие входа."""

from datetime import date

from fastapi.testclient import TestClient

from app.core.models import BookStatus
from app.core.view import ClubView
from app.web.app import create_app
from tests.factories import a_book, a_club, a_meeting, some_data

TODAY = date(2026, 9, 21)


def client(books=(), meetings=(), club=None) -> TestClient:
    view = ClubView(some_data(books=books, meetings=meetings, club=club))
    return TestClient(create_app(view=view, today=lambda: TODAY))


def page(path, **kwargs) -> str:
    response = client(**kwargs).get(path)
    assert response.status_code == 200
    return response.text


# --- 4.6 полка ---------------------------------------------------------------


def test_the_shelf_has_three_blocks():
    html = page(
        "/shelf",
        books=[
            a_book("b1", status=BookStatus.CLOSED, title="С конспектом", notes_url="https://notes/b1"),
            a_book("b2", number=2, status=BookStatus.CLOSED, title="Без конспекта"),
        ],
        meetings=[a_meeting("m1", "2026-01-07", title="Встреча", topics=("Саги",))],
    )

    assert "https://notes/b1" in html
    assert "Без конспекта" not in html
    assert "Саги" in html
    assert 'href="/shelf/topics"' in html
    assert 'href="/game/' in html


def test_the_shelf_does_not_repeat_the_whole_catalogue():
    topics = tuple(f"Понятие {number}" for number in range(1, 13))
    html = page(
        "/shelf",
        meetings=[a_meeting("m1", "2026-01-07", title="Встреча", topics=topics)],
    )

    shown = sum(1 for topic in topics if topic in html)
    assert shown < len(topics)
    assert 'href="/shelf/topics"' in html


# --- 4.7 каталог понятий -----------------------------------------------------


def test_a_topic_leads_to_its_meetings_and_notes():
    html = page(
        "/shelf/topics",
        club=a_club(topic_notes={"Саги": "https://notes/saga"}),
        meetings=[
            a_meeting("m1", "2026-01-07", title="Раз", topics=("Саги", "Кворум")),
            a_meeting("m2", "2026-01-21", title="Два", topics=("Саги",)),
        ],
    )

    assert "https://notes/saga" in html
    assert 'href="/meetings/m1"' in html
    assert 'href="/meetings/m2"' in html
    assert "Кворум" in html


# --- 4.8 о клубе -------------------------------------------------------------


def test_about_explains_the_club_and_lists_its_agreement():
    html = page(
        "/about",
        club=a_club(
            about="Читаем техническую литературу и спорим о ней вслух.",
            rules=("Читаем главу до встречи.", "Ведущий не лектор."),
            telegram="https://t.me/kabanya",
        ),
    )

    assert "Читаем техническую литературу и спорим о ней вслух." in html
    assert "дом77, комната 413" in html
    assert "среда, раз в две недели" in html
    assert "90 минут" in html
    assert "Читаем главу до встречи." in html
    assert "https://t.me/kabanya" in html


# --- 4.9 пустые состояния ----------------------------------------------------


def test_an_empty_topic_catalogue_explains_what_fills_it():
    html = page("/shelf/topics")

    assert "из тем встреч" in html
    assert 'class="empty"' in html


def test_an_empty_history_explains_what_fills_it():
    html = page("/history")

    assert 'class="empty"' in html
    assert "встречами" in html


def test_an_empty_agreement_explains_what_fills_it():
    html = page("/about", club=a_club(rules=()))

    assert 'class="empty"' in html


def test_every_empty_state_uses_the_same_markup():
    pages = [page("/history"), page("/shelf/topics"), page("/about", club=a_club(rules=()))]

    for html in pages:
        assert html.count('class="empty"') >= 1


# --- 4.10 сайт только для чтения ---------------------------------------------


def test_no_page_offers_a_login_or_changes_anything():
    setup = dict(
        club=a_club(telegram="https://t.me/kabanya"),
        books=[a_book("b1", status=BookStatus.CLOSED)],
        meetings=[a_meeting("m1", "2026-01-07", book="b1", closed=(1,), topics=("Саги",))],
    )
    paths = ("/", "/history", "/shelf", "/shelf/topics", "/about", "/meetings/m1", "/books/b1")

    for path in paths:
        html = page(path, **setup)
        assert "<form" not in html
        assert "<input" not in html
        assert "<button" not in html
        assert "Войти" not in html
        assert "Записаться" not in html
