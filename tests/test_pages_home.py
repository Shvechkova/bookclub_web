"""«Сейчас»: витрина, прочитанные книги и афиша; обложки в «Истории»; шапка, подвал и
ссылки, открывающиеся в новой вкладке."""

import re
from datetime import date

from fastapi.testclient import TestClient

from app.core.models import BookStatus, Chapter, Link, MeetingImage, Outcome, OutcomeItem
from app.core.view import ClubView
from app.web.app import create_app
from tests.factories import a_book, a_club, a_meeting, a_space, some_data

TODAY = date(2026, 9, 21)
NEW_TAB = 'target="_blank" rel="noopener"'
POSTER = MeetingImage(src="meetings/m-poster.jpg", alt="Афиша: смоляная яма")


def page(path, books=(), meetings=(), club=None) -> str:
    view = ClubView(some_data(books=books, meetings=meetings, club=club))
    response = TestClient(create_app(view=view, today=lambda: TODAY)).get(path)
    assert response.status_code == 200, f"{path} ответил {response.status_code}"
    return response.text


def finished_block(html: str) -> str:
    found = re.search(r'<section class="finished">.*?</section>', html, re.S)
    assert found, "блока прочитанных книг нет"
    return found.group(0)


def header(html: str) -> str:
    return re.search(r'<header class="top">.*?</header>', html, re.S).group(0)


def closed(book_id, number, **overrides):
    return a_book(book_id, number=number, status=BookStatus.CLOSED, **overrides)


# --- прочитанные книги на «Сейчас» -------------------------------------------


def test_the_home_page_shows_finished_books_from_the_latest_one():
    html = page(
        "/",
        books=[
            closed("one", 1, cover="covers/one.jpg"),
            closed("two", 2, cover="covers/two.jpg"),
            closed("three", 3, cover="covers/three.jpg"),
        ],
    )

    block = finished_block(html)
    links = re.findall(r'href="/books/([^"]+)"', block)
    assert list(dict.fromkeys(links)) == ["three", "two", "one"]
    assert 'src="/static/covers/three.jpg"' in block
    assert 'alt="Обложка книги Книга three"' in block


def test_only_closed_books_are_among_the_finished():
    html = page(
        "/",
        books=[
            closed("done", 1),
            a_book("gave-up", number=2, status=BookStatus.DROPPED),
            a_book("now", number=3, status=BookStatus.READING),
        ],
    )

    block = finished_block(html)
    assert "/books/done" in block
    assert "/books/gave-up" not in block
    assert "/books/now" not in block


def test_a_finished_book_without_a_cover_gets_a_plate():
    block = finished_block(page("/", books=[closed("done", 1, author="Фредерик Брукс")]))

    assert "cover-blank" in block
    assert "Фредерик Брукс" in block


def test_without_finished_books_there_is_no_block():
    html = page("/", books=[a_book("now", status=BookStatus.READING)])

    assert 'class="finished"' not in html


# --- афиша ближайшей встречи --------------------------------------------------


def test_the_next_meeting_shows_its_poster_linked_to_the_full_file():
    html = page(
        "/",
        books=[a_book("b1")],
        meetings=[a_meeting("m1", "2026-09-23", book="b1", planned=(1,), poster=POSTER)],
    )

    next_block = re.search(r'<section class="next">.*?</section>', html, re.S).group(0)
    img = re.search(r"<img [^>]*m-poster\.jpg[^>]*>", next_block).group(0)
    assert 'alt="Афиша: смоляная яма"' in img
    assert 'width="1080"' in img and 'height="1350"' in img
    assert 'loading="lazy"' not in img
    assert re.search(r'<a href="/static/meetings/m-poster\.jpg">\s*<img ', next_block)


def test_without_a_poster_the_next_meeting_has_no_room_for_one():
    html = page(
        "/",
        books=[a_book("b1")],
        meetings=[a_meeting("m1", "2026-09-23", book="b1", planned=(1,))],
    )

    assert "meeting-image" not in html
    assert "/static/meetings/" not in html


# --- обложки в «Истории» ------------------------------------------------------


def test_every_book_segment_in_the_history_shows_its_cover():
    html = page(
        "/history",
        books=[closed("one", 1, cover="covers/one.jpg"), closed("two", 2)],
        meetings=[a_meeting("m1", "2026-09-09", book="one", closed=(1,))],
    )

    segments = re.findall(r'<section class="segment[^"]*">.*?</section>', html, re.S)
    assert len(segments) == 2
    with_cover = next(item for item in segments if "/books/one" in item)
    assert 'src="/static/covers/one.jpg"' in with_cover
    assert 'class="cover" href="/books/one"' in with_cover
    plate = next(item for item in segments if "/books/two" in item)
    assert "cover-blank" in plate


# --- шапка и подвал -----------------------------------------------------------


def test_the_header_has_no_telegram_link_and_the_footer_has_the_club_chat():
    html = page("/", club=a_club(telegram="https://t.me/kabanya"))

    assert "t.me/kabanya" not in header(html)
    assert "В телеграм" not in html
    footer = re.search(r"<footer.*?</footer>", html, re.S)
    assert footer, "без площадки чату клуба негде стоять"
    assert 'href="https://t.me/kabanya"' in footer.group(0)


# --- новая вкладка ------------------------------------------------------------


def _anchor(html: str, href: str) -> str:
    found = re.search(rf'<a [^>]*href="{re.escape(href)}[^"]*"[^>]*>', html)
    assert found, f"нет ссылки на {href}"
    return found.group(0)


def test_github_notes_open_in_a_new_tab():
    book = closed(
        "b1",
        1,
        notes_url="https://github.com/club/notes/book.md",
        chapters_override=(
            Chapter(number=1, title="Глава", notes_url="https://github.com/club/notes/ch1.md"),
        ),
    )
    html = page("/books/b1", books=[book])

    assert NEW_TAB in _anchor(html, "https://github.com/club/notes/book.md")
    assert NEW_TAB in _anchor(html, "https://github.com/club/notes/ch1.md")


def test_topic_notes_open_in_a_new_tab():
    club = a_club(topic_notes={"Кворум": "https://github.com/club/notes/quorum.md"})
    meetings = [a_meeting("m1", "2026-09-09", title="Встреча", topics=("Кворум",))]

    for path in ("/", "/meetings/m1"):
        html = page(path, meetings=meetings, club=club)
        assert NEW_TAB in _anchor(html, "https://github.com/club/notes/quorum.md"), path


def test_telegram_links_open_in_a_new_tab_and_others_do_not():
    club = a_club(space=a_space(), telegram="https://t.me/kabanya")

    for path in ("/", "/about"):
        html = page(path, club=club)
        assert NEW_TAB in _anchor(html, "https://t.me/kabanya"), path
        assert NEW_TAB in _anchor(html, "https://t.me/s4m_space"), path
        assert NEW_TAB in _anchor(html, "https://t.me/+chat"), path
        assert "target=" not in _anchor(html, "https://s4m.space/"), path
        assert "target=" not in _anchor(html, "/history"), path


def test_meeting_links_choose_the_tab_by_address():
    meeting = a_meeting(
        "m1",
        "2026-09-23",
        title="Встреча",
        links=(
            Link(title="Репозиторий", url="https://github.com/club/demo"),
            Link(title="Доклад", url="https://example.org/talk"),
        ),
    )
    html = page("/meetings/m1", meetings=[meeting])

    assert NEW_TAB in _anchor(html, "https://github.com/club/demo")
    assert "target=" not in _anchor(html, "https://example.org/talk")
    assert "target=" not in _anchor(html, "https://calendar.google.com")


# --- витрина: заставка --------------------------------------------------------

SHOWCASE_TODAY = date(2026, 10, 26)
RECAP = MeetingImage(src="meetings/m-recap.jpg", alt="Карточка итогов")
SHOWCASE_CLUB = dict(
    tagline="IT-книжный клуб в Самаре",
    since=2023,
    manifesto="Читаем техническую литературу\nи спорим о ней вслух",
    terms=("Вход свободный, без регистраций", "Не прочитал — всё равно приходи"),
    space=a_space(),
    telegram="https://t.me/kabanya",
)


def home(meetings=(), books=(), today=SHOWCASE_TODAY, **club) -> str:
    view = ClubView(
        some_data(books=books, meetings=meetings, club=a_club(**{**SHOWCASE_CLUB, **club}))
    )
    response = TestClient(create_app(view=view, today=lambda: today)).get("/")
    assert response.status_code == 200
    return response.text


def block(html: str, name: str) -> str:
    found = re.search(rf'<section class="{name}"[^>]*>.*?</section>', html, re.S)
    assert found, f"блока {name} нет"
    return found.group(0)


def brooks():
    return closed("brooks", 4, title="Мифический человеко-месяц")


def debated(meeting_id, day, *headings, **overrides):
    outcome = Outcome(
        agreed="Тезис главной больше не нужен.",
        debates=tuple(
            OutcomeItem(heading=item, text=f"Текст спора {item}") for item in headings
        ),
    )
    return a_meeting(meeting_id, day, book="brooks", closed=(1,), outcome=outcome, **overrides)


def test_the_home_page_opens_with_the_manifesto():
    html = home(meetings=[a_meeting("next", "2026-11-04", title="Старт")])

    hero = block(html, "hero")
    assert "IT-книжный клуб в Самаре · с 2023" in hero
    title = re.search(r"<h1[^>]*>(.*?)</h1>", hero, re.S).group(1)
    assert re.findall(r'<span class="hero-line">(.*?)</span>', title) == [
        "Читаем техническую литературу",
        "и спорим о ней вслух",
    ], "манифест делится на строки там, где в данных перевод строки"
    assert html.index('class="hero"') < html.index('class="next"')
    assert html.count("<h1") == 1, "на странице один главный заголовок"


def test_the_hero_lists_the_terms_in_order():
    hero = block(home(), "hero")

    assert "Как у нас" in hero
    assert hero.index("Вход свободный, без регистраций") < hero.index(
        "Не прочитал — всё равно приходи"
    )


def test_the_hero_button_leads_to_the_upcoming_meeting():
    hero = block(home(meetings=[a_meeting("next", "2026-11-04", title="Старт")]), "hero")

    assert re.search(r'<a class="button[^"]*" href="/meetings/next">Прийти 4 ноября</a>', hero)


def test_without_an_upcoming_meeting_the_hero_button_leads_to_how_to_come():
    html = home(meetings=[a_meeting("past", "2026-10-07", title="Было")])

    hero = block(html, "hero")
    assert re.search(r'<a class="button[^"]*" href="#how-to-come">Как прийти</a>', hero)
    assert 'id="how-to-come"' in html


def test_the_hero_shows_no_numbers_and_no_address():
    hero = block(home(meetings=[a_meeting("next", "2026-11-04", title="Старт")]), "hero")

    assert "Ленинградская" not in hero
    assert "19:30" not in hero


def test_the_hero_shows_recent_topics_newest_first_linked_to_notes():
    meetings = [
        a_meeting("old", "2026-09-23", title="Старая", topics=("Закон Брукса", "ADR")),
        a_meeting("new", "2026-10-07", title="Новая", topics=("Закон Конвея", "ADR")),
        a_meeting("next", "2026-11-04", title="Будущая", topics=("Шардирование",)),
    ]
    notes = {"ADR": "https://github.com/club/adr.md"}
    hero = block(home(meetings=meetings, topic_notes=notes), "hero")

    assert "О чём говорили недавно" in hero
    names = re.findall(r'class="plate [^"]*"[^>]*>([^<]+)<', hero)
    assert names == ["Закон Конвея", "ADR", "Закон Брукса"]
    assert re.search(
        r'<a class="plate[^"]*" href="https://github.com/club/adr.md"'
        r' target="_blank" rel="noopener">ADR</a>',
        hero,
    )
    assert "Шардирование" not in hero


def test_without_topics_the_hero_has_no_topics_column():
    hero = block(home(), "hero")

    assert "О чём говорили недавно" not in hero
    assert "hero-cols--single" in hero


def test_the_old_three_theses_are_gone_from_the_home_page():
    html = home(books=[brooks()], meetings=[debated("past", "2026-10-07", "Блок-схемы")])

    assert "Итоги прошлой встречи" not in html
    assert "Тезис главной больше не нужен." not in html


# --- витрина: о чём спорим ----------------------------------------------------


def test_the_debates_block_shows_the_three_freshest_debates():
    html = home(
        books=[brooks()],
        meetings=[
            debated("old", "2026-09-23", "Комментарии в коде", "Документация"),
            debated("new", "2026-10-07", "Блок-схемы"),
        ],
    )

    debates = block(html, "debates")
    headings = re.findall(r"<h3[^>]*>([^<]+)</h3>", debates)
    assert headings == ["Блок-схемы", "Комментарии в коде", "Документация"]
    assert "Текст спора Блок-схемы" in debates
    assert "07.10 · Мифический человеко-месяц" in debates
    assert "23.09 · Мифический человеко-месяц" in debates
    assert re.search(r'<a href="/history">Все итоги встреч →</a>', debates)


def test_without_debates_there_is_no_debates_block():
    html = home(
        books=[brooks()], meetings=[a_meeting("m1", "2026-10-07", book="brooks", closed=(1,))]
    )

    assert 'class="debates"' not in html


# --- витрина: как это было ----------------------------------------------------


def gallery_meetings():
    return [
        a_meeting("first", "2026-09-23", book="brooks", closed=(1,), poster=POSTER),
        a_meeting("plain", "2026-09-30", book="brooks", closed=(2,)),
        a_meeting(
            "second", "2026-10-07", book="brooks", closed=(3,), poster=POSTER, recap_card=RECAP
        ),
        a_meeting("next", "2026-11-04", book="brooks", planned=(4,), poster=POSTER),
    ]


def test_the_gallery_has_accessible_tabs_newest_first():
    gallery = block(home(books=[brooks()], meetings=gallery_meetings()), "gallery")

    assert 'role="tablist"' in gallery
    tabs = re.findall(r'<a [^>]*role="tab"[^>]*>', gallery)
    assert [re.search(r'href="/meetings/([^"]+)"', tab).group(1) for tab in tabs] == [
        "next",
        "second",
        "first",
    ]
    selected = [tab for tab in tabs if 'aria-selected="true"' in tab]
    assert len(selected) == 1 and "/meetings/second" in selected[0]
    assert "скоро" in gallery
    assert "/meetings/plain" not in gallery


def test_gallery_tabs_carry_the_meeting_number_within_the_book():
    gallery = block(home(books=[brooks()], meetings=gallery_meetings()), "gallery")

    numbers = re.findall(r'<span class="gallery-tab-number">([^<]*)</span>', gallery)
    # «plain» без картинки в галерею не попал, но счёт встреч по книге идёт
    # по всем встречам: «second» — третья, «next» — четвёртая.
    assert numbers == ["встреча #4", "встреча #3", "встреча #1"]


def test_the_gallery_shows_the_default_image_and_hides_the_rest():
    gallery = block(home(books=[brooks()], meetings=gallery_meetings()), "gallery")

    panels = re.findall(r'<figure [^>]*role="tabpanel"[^>]*>.*?</figure>', gallery, re.S)
    assert len(panels) == 3
    shown = [panel for panel in panels if " hidden" not in panel.split(">", 1)[0]]
    assert len(shown) == 1
    assert "m-recap.jpg" in shown[0]
    assert "итоги · 07.10" in shown[0]
    assert re.search(r'href="/meetings/second">встреча целиком →</a>', shown[0])
    poster_panel = next(panel for panel in panels if "gallery-panel-first" in panel)
    assert "афиша · 23.09" in poster_panel


def test_without_images_there_is_no_gallery_but_the_game_plate_stays():
    html = home(
        books=[brooks()], meetings=[a_meeting("m1", "2026-10-07", book="brooks", closed=(1,))]
    )

    assert 'class="gallery"' not in html
    assert re.search(r'Разминка перед встречей.*?<a href="/game/">Играть →</a>', html, re.S)


# --- витрина: как прийти ------------------------------------------------------


def test_how_to_come_has_four_steps_and_buttons_in_order():
    html = home(meetings=[a_meeting("next", "2026-11-04", title="Старт")])

    how = block(html, "how")
    assert 'id="how-to-come"' in how
    steps = re.findall(r"<h3[^>]*>([^<]+)</h3>", how)
    assert steps == [
        "Глянь ближайшую",
        "Прочитай. Или нет",
        "Приходи в среду",
        "Заходи в чат спейса",
    ]
    assert "19:30" in how
    assert "Дом77, Ленинградская 77, 4 этаж, комната 413, Самара" in how
    buttons = re.findall(r'<a class="button[^"]*" href="([^"]+)"[^>]*>([^<]+)</a>', how)
    assert buttons == [
        ("/meetings/next", "Ближайшая встреча — 4 ноября"),
        ("https://t.me/+chat", "Вступить в чат s4m.space"),
        ("https://t.me/c/1/2", "Ветка книжного клуба"),
    ]
    assert "t.me/kabanya" not in how
    assert NEW_TAB in _anchor(how, "https://t.me/+chat")


def test_how_to_come_without_an_upcoming_meeting_has_no_meeting_button():
    how = block(home(meetings=[a_meeting("past", "2026-10-07", title="Было")]), "how")

    assert "Ближайшая встреча —" not in how
    assert "Вступить в чат s4m.space" in how
    assert "Приходи в среду" not in how
