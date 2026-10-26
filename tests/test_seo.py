"""Описания страниц, карточки для пересылки и разметка для поисковиков."""

from __future__ import annotations

import json
import re
from datetime import date

from fastapi.testclient import TestClient

from app.core.models import BookStatus, MeetingImage
from app.core.view import ClubView
from app.web import seo
from app.web.app import create_app
from tests.factories import a_book, a_club, a_meeting, a_space, some_data

TODAY = date(2026, 9, 21)
ORIGIN = "https://example.org"


def page(path, *, origin=ORIGIN, base="", club=None, meetings=None) -> str:
    books = [
        a_book(
            "b1",
            title="Мифический человеко-месяц",
            author="Фредерик Брукс",
            status=BookStatus.READING,
        )
    ]
    meetings = meetings or [a_meeting("m1", "2026-09-09", book="b1", closed=(1,))]
    view = ClubView(
        some_data(
            books=books,
            meetings=meetings,
            club=club or a_club(space=a_space(), telegram="https://t.me/kabanya"),
        )
    )
    app = create_app(view=view, today=lambda: TODAY, base=base, origin=origin)
    response = TestClient(app).get(path)
    assert response.status_code == 200, f"{path} ответил {response.status_code}"
    return response.text


def meta(html: str, name: str) -> str:
    found = re.search(rf'<meta name="{name}" content="([^"]*)"', html)
    return found.group(1) if found else ""


def og(html: str, prop: str) -> str:
    found = re.search(rf'<meta property="{prop}" content="([^"]*)"', html)
    return found.group(1) if found else ""


def linked_data(html: str) -> list[dict]:
    blocks = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL
    )
    return [json.loads(block) for block in blocks]


# --- как складывается описание ----------------------------------------------


def test_a_long_text_is_cut_at_a_sentence_and_not_mid_phrase():
    text = "Первое предложение. Второе предложение, в котором " + "слово " * 30

    assert seo.shorten(text) == "Первое предложение."


def test_a_text_without_a_sentence_end_is_cut_at_a_word():
    cut = seo.shorten("слово " * 40)

    assert len(cut) <= seo.LIMIT
    assert cut.endswith("…")
    assert cut.removesuffix("…").endswith("слово")


def test_a_short_text_is_left_alone():
    assert seo.shorten("Коротко и ясно.") == "Коротко и ясно."


def test_the_home_description_names_the_city_and_what_the_club_does():
    club = a_club(
        tagline="IT-книжный клуб в Самаре",
        about=("Читаем техническую литературу и спорим о ней вслух.",),
    )

    assert seo.club_description(club) == (
        "IT-книжный клуб в Самаре. Читаем техническую литературу и спорим о ней вслух."
    )


# --- описание страницы -------------------------------------------------------


def test_each_page_describes_itself_and_not_the_whole_site():
    book = meta(page("/books/b1"), "description")
    meeting = meta(page("/meetings/m1"), "description")

    assert "Мифический человеко-месяц" in book
    assert "Фредерик Брукс" in book
    assert "#1" in meeting
    assert "9 сентября" in meeting
    assert book != meeting


def test_no_two_sections_share_one_description():
    described = {
        path: meta(page(path), "description")
        for path in ("/", "/history", "/about")
    }

    assert len(set(described.values())) == len(described), described


def test_the_about_description_carries_the_address_and_the_slot():
    description = meta(page("/about"), "description")

    assert "Дом77, Ленинградская 77, 4 этаж, комната 413, Самара" in description
    assert "среда, раз в две недели" in description


def test_the_home_title_names_the_city():
    html = page("/", club=a_club(tagline="IT-книжный клуб в Самаре"))

    assert "<title>Кабанья Читальня — IT-книжный клуб в Самаре</title>" in html


# --- канонический адрес ------------------------------------------------------


def test_a_page_carries_its_canonical_address():
    html = page("/about")

    assert '<link rel="canonical" href="https://example.org/about">' in html


def test_the_home_page_is_canonical_at_the_root():
    html = page("/")

    assert '<link rel="canonical" href="https://example.org/">' in html


def test_the_canonical_address_keeps_the_subpath():
    html = page("/about", base="/bookclub_web")

    assert '<link rel="canonical" href="https://example.org/bookclub_web/about">' in html


# --- карточка для пересылки --------------------------------------------------


def test_a_page_carries_a_card_for_sharing():
    html = page("/meetings/m1")

    assert og(html, "og:title")
    assert og(html, "og:description") == meta(html, "description")
    assert og(html, "og:url") == "https://example.org/meetings/m1"
    assert og(html, "og:image") == "https://example.org/static/logo-mark.png"
    assert og(html, "og:site_name") == "Кабанья Читальня"
    assert og(html, "og:locale") == "ru_RU"


POSTER = MeetingImage(src="meetings/m1-poster.jpg", alt="Афиша встречи")
RECAP = MeetingImage(src="meetings/m1-recap.jpg", alt="Карточка итогов")


def test_the_card_of_a_meeting_with_a_poster_shows_the_poster():
    upcoming = a_meeting("m1", "2026-09-23", book="b1", planned=(1,), poster=POSTER)
    html = page("/meetings/m1", meetings=[upcoming])

    assert og(html, "og:image") == "https://example.org/static/meetings/m1-poster.jpg"


def test_the_card_of_a_past_meeting_shows_the_recap_card():
    past = a_meeting(
        "m1", "2026-09-09", book="b1", closed=(1,), poster=POSTER, recap_card=RECAP
    )
    html = page("/meetings/m1", meetings=[past])

    assert og(html, "og:image") == "https://example.org/static/meetings/m1-recap.jpg"


def test_the_card_of_a_meeting_without_images_shows_the_logo():
    html = page("/meetings/m1")

    assert og(html, "og:image") == "https://example.org/static/logo-mark.png"


def test_the_card_image_of_a_meeting_keeps_the_subpath():
    upcoming = a_meeting("m1", "2026-09-23", book="b1", planned=(1,), poster=POSTER)
    html = page("/meetings/m1", meetings=[upcoming], base="/bookclub_web")

    assert og(html, "og:image") == (
        "https://example.org/bookclub_web/static/meetings/m1-poster.jpg"
    )


def test_other_pages_keep_the_logo_in_the_card():
    upcoming = a_meeting("m1", "2026-09-23", book="b1", planned=(1,), poster=POSTER)
    for path in ("/", "/history", "/books/b1"):
        html = page(path, meetings=[upcoming])

        assert og(html, "og:image") == "https://example.org/static/logo-mark.png", path


def test_without_a_site_address_a_meeting_with_a_poster_has_no_card():
    upcoming = a_meeting("m1", "2026-09-23", book="b1", planned=(1,), poster=POSTER)
    html = page("/meetings/m1", meetings=[upcoming], origin="")

    assert 'property="og:image"' not in html


# --- разметка для поисковиков ------------------------------------------------


def test_every_page_describes_the_club_for_search_engines():
    for path in ("/", "/history", "/about", "/books/b1", "/meetings/m1"):
        blocks = [
            block for block in linked_data(page(path)) if block["@type"] == "Organization"
        ]

        assert len(blocks) == 1, path
        assert blocks[0]["name"] == "Кабанья Читальня"
        assert "https://t.me/kabanya" in blocks[0]["sameAs"]


def test_a_meeting_is_marked_up_as_an_offline_free_event():
    events = [block for block in linked_data(page("/meetings/m1")) if block["@type"] == "Event"]

    assert len(events) == 1
    event = events[0]
    assert event["startDate"] == "2026-09-09T19:30"
    assert event["eventAttendanceMode"] == "https://schema.org/OfflineEventAttendanceMode"
    assert event["isAccessibleForFree"] is True
    assert event["location"]["name"] == "хакспейс s4m.space, комната 413"
    assert event["location"]["address"] == "Дом77, Ленинградская 77, 4 этаж, комната 413, Самара"
    assert event["url"] == "https://example.org/meetings/m1"


def test_a_page_without_a_meeting_carries_no_event():
    events = [block for block in linked_data(page("/about")) if block["@type"] == "Event"]

    assert events == []


# --- адрес сайта не задан ----------------------------------------------------


def test_without_a_site_address_the_absolute_markup_is_skipped():
    html = page("/about", origin="")

    assert 'rel="canonical"' not in html
    assert 'property="og:' not in html
    assert "application/ld+json" not in html
    assert meta(html, "description")
