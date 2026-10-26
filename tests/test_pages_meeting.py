"""Страница встречи как анонс: главы, адрес, условия прихода, календарь.

Человек приходит сюда по ссылке из поста и должен узнать то же, что было в
посте: что разбираем, когда, где и на каких условиях.
"""

import re
from datetime import date
from html import unescape
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app.core.models import Chapter, MeetingImage, Outcome, OutcomeItem, Quote
from app.core.view import ClubView
from app.web.app import create_app
from tests.factories import a_book, a_club, a_meeting, some_data

TODAY = date(2026, 9, 21)

CHAPTERS = (
    Chapter(number=1, title="Смоляная яма"),
    Chapter(number=2, title="Закон Брукса"),
    Chapter(number=3, title="Хирургическая бригада"),
)


def page(path, books=(), meetings=(), club=None, today=TODAY) -> str:
    view = ClubView(some_data(books=books, meetings=meetings, club=club))
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


def upcoming(**overrides):
    return a_meeting("m1", "2026-09-23", book="brooks", planned=(1, 2, 3), **overrides)


def past():
    return a_meeting("m0", "2026-09-09", book="brooks", closed=(1,))


def test_an_upcoming_meeting_lists_the_chapters_by_title():
    html = page("/meetings/m1", books=[brooks()], meetings=[upcoming()])

    assert "Смоляная яма" in html
    assert "Закон Брукса" in html
    assert "Хирургическая бригада" in html


def test_an_upcoming_meeting_gives_the_full_address():
    html = page("/meetings/m1", books=[brooks()], meetings=[upcoming()])

    assert "хакспейс s4m.space" in html
    assert "Дом77, Ленинградская 77, 4 этаж, комната 413, Самара" in html


def test_an_upcoming_meeting_states_the_terms_of_coming():
    club = a_club(terms=("Вход свободный, без регистраций", "Не прочитал — всё равно приходи"))
    html = page("/meetings/m1", books=[brooks()], meetings=[upcoming()], club=club)

    assert "Вход свободный, без регистраций" in html
    assert "Не прочитал — всё равно приходи" in html


def test_an_upcoming_meeting_links_to_the_calendar_with_time_and_address():
    html = page("/meetings/m1", books=[brooks()], meetings=[upcoming()])

    link = _calendar_link(html)
    query = parse_qs(urlparse(link).query)

    assert query["dates"] == ["20260923T193000/20260923T210000"]
    assert query["ctz"] == ["Europe/Samara"]
    assert query["location"] == ["Дом77, Ленинградская 77, 4 этаж, комната 413, Самара"]


def test_a_meeting_without_a_book_keeps_place_terms_and_calendar():
    club = a_club(terms=("Вход свободный, без регистраций",))
    meeting = a_meeting("m1", "2026-09-23", title="День открытых дверей")
    html = page("/meetings/m1", meetings=[meeting], club=club)

    assert "Дом77, Ленинградская 77, 4 этаж, комната 413, Самара" in html
    assert "Вход свободный, без регистраций" in html
    assert _calendar_link(html)


def test_a_past_meeting_shows_neither_terms_nor_a_calendar_link():
    club = a_club(terms=("Вход свободный, без регистраций",))
    html = page("/meetings/m0", books=[brooks()], meetings=[past()], club=club)

    assert "calendar.google.com" not in html
    assert "Вход свободный, без регистраций" not in html
    assert "Смоляная яма" in html


def test_an_upcoming_meeting_belongs_to_the_now_section():
    html = page("/meetings/m1", books=[brooks()], meetings=[upcoming()])

    assert '<a href="/" aria-current="page">Сейчас</a>' in html


def test_a_past_meeting_belongs_to_the_history_section():
    html = page("/meetings/m0", books=[brooks()], meetings=[past()])

    assert '<a href="/history" aria-current="page">Полка</a>' in html


def test_a_book_page_belongs_to_the_history_section():
    html = page("/books/brooks", books=[brooks()], meetings=[past()])

    assert '<a href="/history" aria-current="page">Полка</a>' in html


# --- полные итоги ------------------------------------------------------------


def full_outcome(**overrides):
    values = dict(
        agreed="Согласились, что оценки врут.",
        argued="Спорили про блок-схемы.",
        taken="Забираем правило ранних оценок.",
        quote=Quote(text="Серебряной пули нет.", chapter=2),
        lead="Разобрали три главы, и вторая съела почти всё время.",
        by_chapter=(
            OutcomeItem(heading="Оценка сроков", text="Сроки врут всегда.", chapters=(2,)),
            OutcomeItem(heading="Бюджеты", text="Бюджет — тоже оценка."),
            OutcomeItem(heading=None, text="Переход от плана к делу.", chapters=(2, 3)),
        ),
        debates=(
            OutcomeItem(heading="Блок-схемы", text="Нужны ли они сегодня."),
        ),
        aside="Заодно уходили в код-ревью и дежурства.",
    )
    values.update(overrides)
    return Outcome(**values)


def recapped(outcome):
    return a_meeting("m0", "2026-09-09", book="brooks", closed=(1, 2, 3), outcome=outcome)


def test_a_past_meeting_with_a_full_outcome_shows_it_under_the_theses():
    html = page("/meetings/m0", books=[brooks()], meetings=[recapped(full_outcome())])

    assert "Согласились, что оценки врут." in html
    assert "Разобрали три главы, и вторая съела почти всё время." in html
    assert "По главам" in html
    assert "Оценка сроков" in html
    assert "Главные споры" in html
    assert "Блок-схемы" in html
    assert "Заодно уходили в код-ревью и дежурства." in html


def test_an_outcome_item_with_chapters_carries_their_numbers():
    html = page("/meetings/m0", books=[brooks()], meetings=[recapped(full_outcome())])

    assert '<span class="num" title="глава 2">02</span>' in html
    assert '<span class="num" title="главы 2–3">02–03</span>' in html


def test_an_outcome_item_without_chapters_has_no_number():
    html = page("/meetings/m0", books=[brooks()], meetings=[recapped(full_outcome())])

    item = html[html.index("Бюджеты") - 200 : html.index("Бюджеты")]
    assert 'class="num"' not in item.rsplit("<li", 1)[-1]


def test_the_full_outcome_goes_in_the_order_of_the_post():
    outcome = full_outcome(verdict="Книга старая, а проблемы те же.")
    html = page("/meetings/m0", books=[brooks()], meetings=[recapped(outcome)])

    order = [
        "Забираем правило ранних оценок.",
        "Разобрали три главы",
        "По главам",
        "Главные споры",
        "Заодно уходили",
        "Книга старая, а проблемы те же.",
    ]
    positions = [html.index(text) for text in order]
    assert positions == sorted(positions)


def test_an_unwritten_verdict_leaves_no_empty_heading():
    html = page("/meetings/m0", books=[brooks()], meetings=[recapped(full_outcome())])

    assert "Общий итог" not in html


def test_an_outcome_of_three_theses_leaves_no_empty_headings():
    outcome = Outcome(agreed="Согласились.", argued="Спорили.", taken="Забираем.")
    html = page("/meetings/m0", books=[brooks()], meetings=[recapped(outcome)])

    assert "Согласились." in html
    for heading in ("По главам", "Главные споры", "Общий итог"):
        assert heading not in html
    assert "recap" not in html


def test_an_outcome_written_only_in_full_form_has_no_empty_list_of_theses():
    outcome = Outcome(verdict="Книга старая, а проблемы те же.")
    html = page("/meetings/m0", books=[brooks()], meetings=[recapped(outcome)])

    assert "Книга старая, а проблемы те же." in html
    assert not re.search(r"<ol>\s*</ol>", html)


def test_the_now_page_takes_only_the_debates_from_the_outcome():
    """Главная берёт из итогов одни споры: тезисы, пункты по главам и общий
    итог остаются на странице встречи."""
    outcome = full_outcome(verdict="Книга старая, а проблемы те же.")
    html = page(
        "/",
        books=[brooks()],
        meetings=[recapped(outcome), upcoming(id="m1", date=TODAY)],
    )

    assert "Нужны ли они сегодня." in html
    assert "Согласились, что оценки врут." not in html
    assert "По главам" not in html
    assert "Сроки врут всегда." not in html
    assert "Книга старая, а проблемы те же." not in html


def test_an_upcoming_meeting_shows_no_outcome_even_if_one_is_written():
    html = page(
        "/meetings/m1",
        books=[brooks()],
        meetings=[upcoming(outcome=full_outcome())],
    )

    assert "По главам" not in html
    assert "Согласились, что оценки врут." not in html


# --- картинка встречи ---------------------------------------------------------

POSTER = MeetingImage(
    src="meetings/m-poster.jpg", alt="Афиша: главы 8–15, среда, 19:30"
)
RECAP = MeetingImage(src="meetings/m-recap.jpg", alt="Итоги: серебряной пули нет")


def test_an_upcoming_meeting_shows_its_poster_with_the_caption_from_data():
    html = page(
        "/meetings/m1",
        books=[brooks()],
        meetings=[upcoming(poster=POSTER, recap_card=RECAP)],
    )

    assert 'src="/static/meetings/m-poster.jpg"' in html
    assert 'alt="Афиша: главы 8–15, среда, 19:30"' in html
    assert "m-recap.jpg" not in html


def test_a_past_meeting_shows_its_recap_card_and_not_the_poster():
    meeting = a_meeting(
        "m0", "2026-09-09", book="brooks", closed=(1,), poster=POSTER, recap_card=RECAP
    )
    html = page("/meetings/m0", books=[brooks()], meetings=[meeting])

    assert 'src="/static/meetings/m-recap.jpg"' in html
    assert 'alt="Итоги: серебряной пули нет"' in html
    assert "m-poster.jpg" not in html


def test_the_image_opens_full_size_and_keeps_its_place_while_loading():
    html = page("/meetings/m1", books=[brooks()], meetings=[upcoming(poster=POSTER)])

    img = re.search(r"<img [^>]*m-poster\.jpg[^>]*>", html).group(0)
    assert 'width="1080"' in img
    assert 'height="1350"' in img
    # Картинка стоит на первом экране: отложенная загрузка её только задержит.
    assert 'loading="lazy"' not in img
    assert re.search(r'<a href="/static/meetings/m-poster\.jpg">\s*<img ', html)


def test_the_image_stands_under_the_heading_before_chapters_and_recap():
    meeting = a_meeting(
        "m0",
        "2026-09-09",
        book="brooks",
        closed=(1,),
        recap_card=RECAP,
        outcome=Outcome(agreed="Согласились, что серебряной пули нет."),
    )
    html = page("/meetings/m0", books=[brooks()], meetings=[meeting])

    image = html.index("meeting-image")
    assert html.index("<h1>") < image
    assert image < html.index("Разобрали")
    assert image < html.index("Итоги</h2>")


def test_a_meeting_without_images_has_no_image_and_no_room_for_one():
    html = page("/meetings/m1", books=[brooks()], meetings=[upcoming()])

    assert "/static/meetings/" not in html
    assert "meeting-image" not in html


def test_the_image_address_keeps_the_subpath():
    view = ClubView(some_data(books=[brooks()], meetings=[upcoming(poster=POSTER)]))
    app = create_app(view=view, today=lambda: TODAY, base="/bookclub_web")
    html = TestClient(app).get("/meetings/m1").text

    assert 'src="/bookclub_web/static/meetings/m-poster.jpg"' in html


def _calendar_link(html: str) -> str:
    """Адрес из атрибута: в разметке амперсанды экранированы, браузер их разворачивает."""
    marker = 'href="https://calendar.google.com'
    assert marker in html, "на странице нет ссылки в календарь"
    start = html.index(marker) + len('href="')
    return unescape(html[start : html.index('"', start)])
