"""Заголовки и описания страниц, карточки для пересылки и разметка для поисковиков."""

from __future__ import annotations

import json
import re
from datetime import date

from fastapi.testclient import TestClient

from app.core.models import BookStatus, MeetingImage, Outcome
from app.core.view import ClubView
from app.web import seo
from app.web.app import STATIC, create_app
from tests.factories import a_book, a_club, a_meeting, a_space, a_term, some_data

TODAY = date(2026, 9, 21)
ORIGIN = "https://example.org"


def site(*, origin=ORIGIN, base="", club=None, meetings=None, books=None,
         glossary=(), verification=None) -> TestClient:
    books = books or [
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
            glossary=glossary,
        )
    )
    app = create_app(
        view=view, today=lambda: TODAY, base=base, origin=origin,
        verification=verification,
    )
    return TestClient(app)


def page(path, **options) -> str:
    response = site(**options).get(path)
    assert response.status_code == 200, f"{path} ответил {response.status_code}"
    return response.text


def meta(html: str, name: str) -> str:
    found = re.search(rf'<meta name="{name}" content="([^"]*)"', html)
    return found.group(1) if found else ""


def og(html: str, prop: str) -> str:
    found = re.search(rf'<meta property="{prop}" content="([^"]*)"', html)
    return found.group(1) if found else ""


def title(html: str) -> str:
    return re.search(r"<title>([^<]*)</title>", html).group(1)


def linked_data(html: str) -> list[dict]:
    blocks = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL
    )
    return [json.loads(block) for block in blocks]


def of_type(html: str, kind: str) -> list[dict]:
    return [block for block in linked_data(html) if block["@type"] == kind]


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


def test_the_home_description_names_the_city_the_slot_and_the_place():
    club = a_club(
        tagline="IT-книжный клуб в Самаре",
        about=("Читаем техническую литературу и спорим о ней вслух. Второе предложение.",),
    )

    assert seo.club_description(club) == (
        "IT-книжный клуб в Самаре. Читаем техническую литературу и спорим о ней "
        "вслух. Очно: среда, раз в две недели, 19:30, хакспейс s4m.space."
    )


# --- как складывается заголовок ----------------------------------------------


def test_fit_takes_the_first_variant_that_fits():
    assert seo.fit("а" * 70, "б" * 60, "в") == "б" * 60


def test_fit_falls_back_to_the_last_variant():
    assert seo.fit("а" * 70, "б" * 80) == "б" * 80


def test_the_home_title_names_the_city():
    html = page("/", club=a_club(tagline="IT-книжный клуб в Самаре"))

    assert "<title>Кабанья Читальня — IT-книжный клуб в Самаре</title>" in html


def test_two_meetings_with_one_number_have_different_titles():
    books = [
        a_book("b1", title="Мифический человеко-месяц", author="Фредерик Брукс"),
        a_book("b2", number=2, title="Высоконагруженные приложения", author="Клеппман"),
    ]
    meetings = [
        a_meeting("m1", "2026-09-09", book="b1", closed=(1,)),
        a_meeting("m2", "2026-11-04", book="b2", planned=(1,)),
    ]
    first = title(page("/meetings/m1", books=books, meetings=meetings))
    second = title(page("/meetings/m2", books=books, meetings=meetings))

    assert first != second
    assert "9 сентября 2026" in first and "Мифический человеко-месяц" in first
    assert "4 ноября 2026" in second
    assert "#1" not in first


def test_a_long_book_title_is_kept_whole_within_the_limit():
    long = "Фундаментальный подход к программной архитектуре"
    books = [a_book("b1", title=long, author="Марк Ричардс, Нил Форд")]
    heading = title(page("/books/b1", books=books))

    assert len(heading) <= seo.TITLE_LIMIT
    assert f"«{long}»" in heading
    assert "обсуждение" in heading


def test_a_short_book_title_carries_the_author():
    heading = title(page("/books/b1"))

    assert heading.startswith("«Мифический человеко-месяц», Фредерик Брукс — обсуждение")
    assert len(heading) <= seo.TITLE_LIMIT


def test_section_titles_say_what_is_inside_and_where():
    assert title(page("/history")) == "Полка: книги и итоги встреч — Кабанья Читальня, Самара"
    assert title(page("/glossary")) == "Словарь: понятия со встреч клуба — Кабанья Читальня, Самара"
    about = title(page("/about", club=a_club(about_title="Первый IT-книжный клуб Самары")))
    assert about == "Первый IT-книжный клуб Самары — Кабанья Читальня"


# --- описание страницы -------------------------------------------------------


def test_each_page_describes_itself_and_not_the_whole_site():
    book = meta(page("/books/b1"), "description")
    meeting = meta(page("/meetings/m1"), "description")

    assert "Мифический человеко-месяц" in book
    assert "Фредерик Брукс" in book
    assert "#1" in meeting
    assert "9 сентября" in meeting
    assert "Самара" in meeting
    assert book != meeting


def test_a_past_meeting_description_carries_the_recap_lead():
    past = a_meeting(
        "m1", "2026-09-09", book="b1", closed=(1,),
        outcome=Outcome(lead="Спорили, растёт ли команда быстрее проекта."),
    )
    description = meta(page("/meetings/m1", meetings=[past]), "description")

    assert "Спорили, растёт ли команда быстрее проекта." in description


def test_an_upcoming_meeting_description_ends_the_announce_with_a_period():
    upcoming = a_meeting(
        "m1", "2026-09-23", book="b1", planned=(1,), announce=("Старт новой книги",)
    )
    description = meta(page("/meetings/m1", meetings=[upcoming]), "description")

    assert description.endswith("Старт новой книги.")


def test_a_multiline_image_caption_becomes_one_line_in_the_card():
    poster = MeetingImage(src="meetings/m1-poster.jpg", alt="Афиша:\nглавы 1–3")
    upcoming = a_meeting("m1", "2026-09-23", book="b1", planned=(1,), poster=poster)

    assert og(page("/meetings/m1", meetings=[upcoming]), "og:image:alt") == "Афиша: главы 1–3"


def test_the_glossary_description_counts_the_terms():
    glossary = [a_term("saga", "Саги"), a_term("adr", "ADR"), a_term("cqrs", "CQRS")]
    description = meta(page("/glossary", glossary=glossary), "description")

    assert "3 понятия" in description
    assert "ADR" in description


def test_no_description_is_longer_than_the_limit():
    for path in ("/", "/history", "/glossary", "/about", "/books/b1", "/meetings/m1"):
        assert len(meta(page(path), "description")) <= seo.LIMIT, path


def test_no_two_sections_share_one_description_or_title():
    pages = {path: page(path) for path in ("/", "/history", "/glossary", "/about")}

    descriptions = {meta(html, "description") for html in pages.values()}
    titles = {title(html) for html in pages.values()}
    assert len(descriptions) == len(pages)
    assert len(titles) == len(pages)


def test_the_about_description_carries_the_address_and_the_slot():
    description = meta(page("/about"), "description")

    assert "Дом77, Ленинградская 77, 4 этаж, комната 413, Самара" in description
    assert "среда, раз в две недели" in description


# --- канонический адрес ------------------------------------------------------


def test_a_page_is_canonical_in_the_form_static_hosting_serves():
    html = page("/history")

    assert '<link rel="canonical" href="https://example.org/history/">' in html
    assert og(html, "og:url") == "https://example.org/history/"


def test_the_home_page_is_canonical_at_the_root():
    html = page("/")

    assert '<link rel="canonical" href="https://example.org/">' in html


def test_the_canonical_address_keeps_the_subpath():
    html = page("/about", base="/bookclub_web")

    assert '<link rel="canonical" href="https://example.org/bookclub_web/about/">' in html


def test_page_url_adds_one_trailing_slash():
    assert seo.page_url("/") == "/"
    assert seo.page_url("/history") == "/history/"
    assert seo.page_url("/history/") == "/history/"


def test_no_page_is_closed_from_indexing():
    for path in ("/", "/history", "/glossary", "/about", "/books/b1", "/meetings/m1"):
        assert 'name="robots"' not in page(path), path


# --- карточка для пересылки --------------------------------------------------


CARD = "https://example.org/static/og-card.jpg"


def test_a_page_carries_a_card_for_sharing():
    html = page("/meetings/m1")

    assert og(html, "og:title") == title(html)
    assert og(html, "og:description") == meta(html, "description")
    assert og(html, "og:url") == "https://example.org/meetings/m1/"
    assert og(html, "og:image") == CARD
    assert og(html, "og:image:width") == "1200"
    assert og(html, "og:image:height") == "630"
    assert og(html, "og:image:alt")
    assert og(html, "og:site_name") == "Кабанья Читальня"
    assert og(html, "og:locale") == "ru_RU"
    assert meta(html, "twitter:card") == "summary_large_image"


def test_the_club_card_is_a_large_light_image():
    card = STATIC / "og-card.jpg"

    assert jpeg_size(card.read_bytes()) == (1200, 630)
    assert card.stat().st_size <= 300 * 1024


def jpeg_size(data: bytes) -> tuple[int, int]:
    """Ширина и высота из заголовка кадра JPEG — без Pillow."""
    assert data[:2] == b"\xff\xd8", "не JPEG"
    at = 2
    while at < len(data):
        marker, length = data[at + 1], int.from_bytes(data[at + 2 : at + 4], "big")
        if marker in (0xC0, 0xC1, 0xC2):
            height = int.from_bytes(data[at + 5 : at + 7], "big")
            width = int.from_bytes(data[at + 7 : at + 9], "big")
            return width, height
        at += 2 + length
    raise AssertionError("в JPEG нет заголовка кадра")


def test_a_book_page_is_typed_as_a_book():
    assert og(page("/books/b1"), "og:type") == "book"
    for path in ("/", "/history", "/glossary", "/about", "/meetings/m1"):
        assert og(page(path), "og:type") == "website", path


POSTER = MeetingImage(src="meetings/m1-poster.jpg", alt="Афиша встречи")
RECAP = MeetingImage(src="meetings/m1-recap.jpg", alt="Карточка итогов")


def test_the_card_of_a_meeting_with_a_poster_shows_the_poster():
    upcoming = a_meeting("m1", "2026-09-23", book="b1", planned=(1,), poster=POSTER)
    html = page("/meetings/m1", meetings=[upcoming])

    assert og(html, "og:image") == "https://example.org/static/meetings/m1-poster.jpg"
    assert og(html, "og:image:width") == "1080"
    assert og(html, "og:image:height") == "1350"
    assert og(html, "og:image:alt") == "Афиша встречи"


def test_the_card_of_a_past_meeting_shows_the_recap_card():
    past = a_meeting(
        "m1", "2026-09-09", book="b1", closed=(1,), poster=POSTER, recap_card=RECAP
    )
    html = page("/meetings/m1", meetings=[past])

    assert og(html, "og:image") == "https://example.org/static/meetings/m1-recap.jpg"


def test_the_card_of_a_meeting_without_images_shows_the_club_card():
    html = page("/meetings/m1")

    assert og(html, "og:image") == CARD


def test_the_card_image_of_a_meeting_keeps_the_subpath():
    upcoming = a_meeting("m1", "2026-09-23", book="b1", planned=(1,), poster=POSTER)
    html = page("/meetings/m1", meetings=[upcoming], base="/bookclub_web")

    assert og(html, "og:image") == (
        "https://example.org/bookclub_web/static/meetings/m1-poster.jpg"
    )


def test_other_pages_keep_the_club_card():
    upcoming = a_meeting("m1", "2026-09-23", book="b1", planned=(1,), poster=POSTER)
    for path in ("/", "/history", "/books/b1"):
        html = page(path, meetings=[upcoming])

        assert og(html, "og:image") == CARD, path


def test_without_a_site_address_a_meeting_with_a_poster_has_no_card():
    upcoming = a_meeting("m1", "2026-09-23", book="b1", planned=(1,), poster=POSTER)
    html = page("/meetings/m1", meetings=[upcoming], origin="")

    assert 'property="og:image"' not in html


# --- разметка для поисковиков: клуб и сайт ------------------------------------


def test_every_page_describes_the_club_for_search_engines():
    for path in ("/", "/history", "/glossary", "/about", "/books/b1", "/meetings/m1"):
        blocks = of_type(page(path), "Organization")

        assert len(blocks) == 1, path
        club = blocks[0]
        assert club["@id"] == "https://example.org/#club"
        assert club["name"] == "Кабанья Читальня"
        assert club["logo"] == "https://example.org/static/logo-mark.png"
        assert club["areaServed"] == {"@type": "City", "name": "Самара"}
        assert club["address"]["@type"] == "PostalAddress"
        assert club["address"]["addressLocality"] == "Самара"


def test_the_space_links_are_not_the_club():
    club = of_type(page("/"), "Organization")[0]

    assert club["sameAs"] == ["https://t.me/kabanya"]


def test_the_home_page_describes_the_site():
    websites = of_type(page("/"), "WebSite")

    assert len(websites) == 1
    assert websites[0]["url"] == "https://example.org/"
    assert websites[0]["inLanguage"] == "ru"
    assert websites[0]["publisher"] == {"@id": "https://example.org/#club"}
    assert of_type(page("/about"), "WebSite") == []


def test_inner_pages_carry_breadcrumbs_from_home():
    crumbs = of_type(page("/books/b1"), "BreadcrumbList")

    assert len(crumbs) == 1
    items = crumbs[0]["itemListElement"]
    assert [item["position"] for item in items] == [1, 2, 3]
    assert [item["name"] for item in items] == [
        "Кабанья Читальня",
        "Полка",
        "Мифический человеко-месяц",
    ]
    assert items[0]["item"] == "https://example.org/"
    assert items[1]["item"] == "https://example.org/history/"
    assert items[2]["item"] == "https://example.org/books/b1/"
    assert of_type(page("/"), "BreadcrumbList") == []


def test_a_meeting_breadcrumb_goes_through_its_book():
    items = of_type(page("/meetings/m1"), "BreadcrumbList")[0]["itemListElement"]

    assert [item["name"] for item in items][:3] == [
        "Кабанья Читальня",
        "Полка",
        "Мифический человеко-месяц",
    ]
    assert items[-1]["item"] == "https://example.org/meetings/m1/"


# --- разметка для поисковиков: встреча, книга, словарь ------------------------


def test_a_meeting_is_marked_up_as_an_offline_free_event():
    events = of_type(page("/meetings/m1"), "Event")

    assert len(events) == 1
    event = events[0]
    assert event["startDate"] == "2026-09-09T19:30:00+04:00"
    assert event["endDate"] == "2026-09-09T21:00:00+04:00"
    assert event["eventAttendanceMode"] == "https://schema.org/OfflineEventAttendanceMode"
    assert event["eventStatus"] == "https://schema.org/EventScheduled"
    assert event["isAccessibleForFree"] is True
    assert event["offers"]["price"] == "0"
    assert event["location"]["@type"] == "Place"
    assert event["location"]["name"] == "хакспейс s4m.space"
    address = event["location"]["address"]
    assert address["@type"] == "PostalAddress"
    assert address["addressLocality"] == "Самара"
    assert "Ленинградская 77" in address["streetAddress"]
    assert event["organizer"]["@id"] == "https://example.org/#club"
    assert event["url"] == "https://example.org/meetings/m1/"
    assert event["image"] == [CARD]
    assert event["description"] == meta(page("/meetings/m1"), "description")
    assert event["workFeatured"]["@type"] == "Book"


def test_the_event_time_follows_the_club_timezone():
    club = a_club(timezone="Europe/Moscow", duration_minutes=120)
    event = of_type(page("/meetings/m1", club=club), "Event")[0]

    assert event["startDate"] == "2026-09-09T19:30:00+03:00"
    assert event["endDate"] == "2026-09-09T21:30:00+03:00"


def test_a_page_without_a_meeting_carries_no_event():
    assert of_type(page("/about"), "Event") == []


def test_a_book_is_marked_up_with_its_authors():
    books = [a_book("b1", title="Фундаментальный подход", author="Марк Ричардс, Нил Форд",
                    cover="covers/b1.jpg")]
    marked = of_type(page("/books/b1", books=books), "Book")

    assert len(marked) == 1
    book = marked[0]
    assert book["name"] == "Фундаментальный подход"
    assert book["author"] == [
        {"@type": "Person", "name": "Марк Ричардс"},
        {"@type": "Person", "name": "Нил Форд"},
    ]
    assert book["url"] == "https://example.org/books/b1/"
    assert book["image"] == "https://example.org/static/covers/b1.jpg"
    assert "isbn" not in book


def test_the_glossary_is_marked_up_as_a_set_of_terms():
    glossary = [
        a_term("saga", "Саги", aliases=("Сага",)),
        a_term("adr", "ADR"),
    ]
    sets = of_type(page("/glossary", glossary=glossary), "DefinedTermSet")

    assert len(sets) == 1
    terms = {term["name"]: term for term in sets[0]["hasDefinedTerm"]}
    assert set(terms) == {"Саги", "ADR"}
    saga = terms["Саги"]
    assert saga["@type"] == "DefinedTerm"
    assert saga["description"] == "Что такое Саги."
    assert saga["url"] == "https://example.org/glossary/#saga"
    assert saga["alternateName"] == ["Сага"]
    assert saga["inDefinedTermSet"] == {"@id": sets[0]["@id"]}
    assert "alternateName" not in terms["ADR"]


def test_an_empty_glossary_carries_no_set_of_terms():
    assert of_type(page("/glossary"), "DefinedTermSet") == []


# --- иконки и манифест --------------------------------------------------------


def test_every_page_links_the_icons_and_the_manifest():
    for path in ("/", "/about", "/meetings/m1"):
        html = page(path, base="/bookclub_web")

        assert 'href="/bookclub_web/static/favicon.ico"' in html, path
        assert 'href="/bookclub_web/static/favicon-32.png"' in html
        assert '<link rel="apple-touch-icon" href="/bookclub_web/static/apple-touch-icon.png">' in html
        assert '<link rel="manifest" href="/bookclub_web/manifest.webmanifest">' in html
        assert '<meta name="theme-color" content="#0a0a0a">' in html


def test_the_icon_files_exist():
    for name in ("favicon.ico", "favicon-32.png", "apple-touch-icon.png", "icon-192.png", "icon-512.png"):
        assert (STATIC / name).exists(), name


def test_the_manifest_names_the_club_and_its_icons():
    response = site(base="/bookclub_web").get("/manifest.webmanifest")

    assert response.status_code == 200
    manifest = response.json()
    assert manifest["name"] == "Кабанья Читальня"
    assert manifest["lang"] == "ru"
    assert manifest["start_url"] == "/bookclub_web/"
    sizes = {icon["sizes"]: icon["src"] for icon in manifest["icons"]}
    assert sizes == {
        "192x192": "/bookclub_web/static/icon-192.png",
        "512x512": "/bookclub_web/static/icon-512.png",
    }


def test_the_root_favicon_answers():
    assert site().get("/favicon.ico").status_code == 200


# --- страница «не найдено» ----------------------------------------------------


def test_an_unknown_address_answers_with_the_not_found_page():
    response = site().get("/no-such-page")

    assert response.status_code == 404
    html = response.text
    assert '<meta name="robots" content="noindex">' in html
    assert 'href="/"' in html
    assert "<h1>" in html
    assert 'rel="canonical"' not in html
    assert 'property="og:' not in html
    assert "application/ld+json" not in html


def test_an_unknown_meeting_answers_with_the_same_page():
    response = site().get("/meetings/nope")

    assert response.status_code == 404
    assert 'content="noindex"' in response.text


# --- подтверждение прав ------------------------------------------------------


def test_the_yandex_code_is_put_on_the_pages():
    verification = seo.verification_from_env({"YANDEX_VERIFICATION": "abc"})
    html = page("/about", verification=verification)

    assert '<meta name="yandex-verification" content="abc">' in html
    assert "google-site-verification" not in html


def test_both_codes_are_put_on_the_pages():
    verification = seo.verification_from_env(
        {"YANDEX_VERIFICATION": "abc", "GOOGLE_SITE_VERIFICATION": "xyz"}
    )
    html = page("/", verification=verification)

    assert '<meta name="yandex-verification" content="abc">' in html
    assert '<meta name="google-site-verification" content="xyz">' in html


def test_without_codes_there_are_no_verification_tags():
    assert seo.verification_from_env({"YANDEX_VERIFICATION": "  "}) == {}
    html = page("/")

    assert "verification" not in html


# --- адрес сайта не задан ----------------------------------------------------


def test_without_a_site_address_the_absolute_markup_is_skipped():
    html = page("/about", origin="")

    assert 'rel="canonical"' not in html
    assert 'property="og:' not in html
    assert "application/ld+json" not in html
    assert meta(html, "description")

