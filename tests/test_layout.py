"""Вёрстка на узком экране — проверка настоящим браузером.

Прокрутка и переносы — свойства раскладки, а не разметки: проверить их можно
только тем, что страницу действительно раскладывают. Поэтому здесь поднимается
сервер и открывается Chromium.
"""

from __future__ import annotations

import socket
import threading
import time
from datetime import date

import pytest
import uvicorn

from app.core.models import (
    BookStatus,
    Chapter,
    MeetingImage,
    Outcome,
    OutcomeItem,
    Quote,
    TermChapter,
    Warmup,
)
from app.core.view import ClubView
from app.web.app import create_app
from tests.factories import a_book, a_club, a_meeting, a_space, a_term, some_data

playwright_api = pytest.importorskip("playwright.sync_api")

TODAY = date(2026, 9, 21)
NARROW = {"width": 360, "height": 740}
PATHS = (
    "/",
    "/history",
    "/glossary",
    "/about",
    "/meetings/m1",
    "/meetings/m2",
    "/books/b1",
)


def crowded_view() -> ClubView:
    book = a_book(
        "b1",
        chapters_override=tuple(
            Chapter(
                number=number,
                title="Архитектура, управляемая событиями, и её последствия",
                notes_url="https://example.org/notes/chapter",
            )
            for number in range(1, 6)
        ),
        status=BookStatus.READING,
        title="Высоконагруженные приложения: проектирование систем",
        notes_url="https://example.org/notes/book",
    )
    outcome = Outcome(
        agreed="Согласились, что согласованное хеширование объясняется проще, чем написано.",
        argued="Спорили про уровни изоляции транзакций дольше всего.",
        taken="Забираем идею идемпотентных обработчиков в свои проекты.",
        quote=Quote(text="Архитектор — градостроитель, а не строитель.", chapter=16),
        lead="Разобрали две главы, и про согласованное хеширование спорили дольше всего.",
        by_chapter=(
            OutcomeItem(
                heading="Репликация без лидера и её последствия для согласованности",
                text="Одни считают, что кворум решает всё, другие — что он только прячет гонки.",
                chapters=(1, 2),
            ),
            OutcomeItem(heading=None, text="Пункт без заголовка.", chapters=(2,)),
        ),
        debates=(
            OutcomeItem(heading="Нужны ли распределённые транзакции", text="Сошлись на саге."),
        ),
        aside="Заодно уходили в дежурства, код-ревью и идемпотентность обработчиков.",
        verdict="Книга толстая, но каждая глава окупается на первом же инциденте.",
    )
    poster = MeetingImage(src="meetings/m-poster.jpg", alt="Афиша встречи")
    recap = MeetingImage(src="meetings/m-recap.jpg", alt="Карточка итогов встречи")
    meetings = [
        a_meeting(
            "m1",
            "2026-09-09",
            book="b1",
            closed=(1, 2),
            fmt="Петпроект-практика",
            host="Анастасия",
            outcome=outcome,
            topics=("Согласованное хеширование", "Уровни изоляции транзакций"),
            poster=poster,
            recap_card=recap,
        ),
        a_meeting(
            "m2", "2026-09-23", book="b1", planned=(3, 4), fmt="Лайтнинги", poster=poster
        ),
        a_meeting("lone", "2026-09-16", title="ADR-дуэль: выбираем хранилище"),
    ]
    club = a_club(
        telegram="https://t.me/example",
        marquee=("КНИЖНАЯ СРЕДА", "КОД · КНИГИ · СПОРЫ · КОФЕ · ГЛАВЫ"),
        about=(
            "Читаем техническую литературу и спорим о ней вслух.",
            "Собираемся только очно, в Самаре: трансляций и записей нет.",
        ),
        routine=(
            "Разбираем главы вслух. Это не лекция: главу берут по частям, "
            "и объясняют её разные люди, а не один.",
            "Ведущий у каждой встречи свой, и это не эксперт.",
        ),
        space=a_space(),
        tagline="IT-книжный клуб в Самаре",
        since=2023,
        manifesto="Читаем техническую литературу\nи спорим о ней вслух",
        terms=("Вход свободный, без регистраций", "Не прочитал — всё равно приходи"),
        warmup=Warmup(
            name="Тыжархитектор",
            lead=(
                "Карточный тренажёр по архитектуре: тянешь проблему системы — "
                "подбираешь решение"
            ),
            url="https://shvechkova.github.io/tyzharchitector/",
        ),
    )
    # Прочитанные книги — для сетки на «Сейчас» и обложек в «Истории»;
    # одна без обложки, чтобы в сетке стояла и плашка.
    finished = [
        a_book(
            f"done{number}",
            number=number,
            status=BookStatus.CLOSED,
            title="Фундаментальные основы архитектуры программного обеспечения",
            author="Марк Ричардс, Нил Форд",
            cover=None if number == 2 else "covers/fundamental-software-architecture.jpg",
        )
        for number in (2, 3, 4)
    ]
    # Понятия с длинными названиями и определениями: подсказка у плашки справа и
    # карточка словаря на узком экране не должны раздвигать страницу вбок.
    glossary = [
        a_term(
            "consistent-hashing",
            "Согласованное хеширование",
            aliases=("Consistent hashing", "Кольцо хеширования с виртуальными узлами"),
            summary=(
                "Способ раскладывать ключи по узлам так, чтобы при добавлении или "
                "уходе узла переезжала лишь малая доля ключей, а не почти все."
            ),
            article="https://github.com/example/notes/blob/main/topics/hashing.md",
            chapters=(TermChapter("b1", 1), TermChapter("b1", 2)),
            related=("isolation-levels",),
        ),
        a_term(
            "isolation-levels",
            "Уровни изоляции транзакций",
            summary=(
                "Насколько транзакции видят изменения друг друга: от чтения "
                "незафиксированного до сериализуемости, где всё как по очереди."
            ),
            related=("consistent-hashing",),
        ),
        a_term("adr", "ADR", summary="Короткая запись архитектурного решения и его причин."),
    ]
    return ClubView(
        some_data(books=[*finished, book], meetings=meetings, club=club, glossary=glossary)
    )


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.fixture(scope="module")
def site() -> str:
    port = free_port()
    app = create_app(view=crowded_view(), today=lambda: TODAY)
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    )
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(200):
        if server.started:
            break
        time.sleep(0.05)
    assert server.started, "сервер не поднялся"
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


def test_no_horizontal_scrolling_on_a_narrow_screen(site):
    with playwright_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=NARROW)
        # Шрифты с внешнего сервера тесту не нужны: раскладку проверяем свою.
        page.route("https://fonts.**", lambda route: route.abort())
        try:
            for path in PATHS:
                page.goto(site + path, wait_until="load")
                scroll_width = page.evaluate("document.documentElement.scrollWidth")
                client_width = page.evaluate("document.documentElement.clientWidth")
                assert scroll_width <= client_width, (
                    f"{path}: страница шире экрана — {scroll_width} против {client_width}"
                )
        finally:
            browser.close()


def test_the_main_heading_stays_inside_the_screen(site):
    with playwright_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=NARROW)
        page.route("https://fonts.**", lambda route: route.abort())
        try:
            page.goto(site + "/books/b1", wait_until="load")
            box = page.locator("h1").bounding_box()
            assert box is not None
            assert box["x"] >= 0
            assert box["x"] + box["width"] <= NARROW["width"] + 1
        finally:
            browser.close()


def test_the_footer_sits_at_the_bottom_of_a_short_page(site):
    """Короткая страница: подвал стоит внизу окна, а не посреди пустого экрана."""
    wide = {"width": 1280, "height": 900}
    with playwright_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=wide)
        page.route("https://fonts.**", lambda route: route.abort())
        try:
            page.goto(site + "/meetings/lone", wait_until="load")
            height = page.evaluate("document.documentElement.scrollHeight")
            assert height <= wide["height"] + 1, "короткая страница длиннее окна"
            box = page.locator("footer.bottom").bounding_box()
            assert box is not None
            bottom = box["y"] + box["height"]
            assert bottom >= wide["height"] - 40, (
                f"подвал кончается на {bottom} при высоте окна {wide['height']}"
            )
        finally:
            browser.close()


def test_the_footer_follows_the_content_on_a_long_page(site):
    wide = {"width": 1280, "height": 900}
    with playwright_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=wide)
        page.route("https://fonts.**", lambda route: route.abort())
        try:
            page.goto(site + "/books/b1", wait_until="load")
            height = page.evaluate("document.documentElement.scrollHeight")
            assert height > wide["height"], "длинная страница должна прокручиваться"
            main_box = page.locator("main").bounding_box()
            footer_box = page.locator("footer.bottom").bounding_box()
            assert main_box is not None and footer_box is not None
            assert footer_box["y"] >= main_box["y"] + main_box["height"] - 1, (
                "подвал наехал на содержимое"
            )
        finally:
            browser.close()


def test_the_logo_stands_in_one_line_on_a_wide_screen(site):
    """Знак, надпись и дескриптор — одной строкой: как в анонсах."""
    wide = {"width": 1280, "height": 900}
    with playwright_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=wide)
        page.route("https://fonts.**", lambda route: route.abort())
        try:
            page.goto(site + "/", wait_until="load")
            mark = page.locator(".logo-mark").bounding_box()
            words = page.locator(".logo-words img").bounding_box()
            descriptor = page.locator(".logo-descriptor").bounding_box()
            assert mark and words and descriptor
            assert mark["x"] + mark["width"] <= words["x"] + 1, "знак не слева от надписи"
            assert words["x"] + words["width"] <= descriptor["x"] + 1, (
                "дескриптор не справа от надписи"
            )
            middles = [box["y"] + box["height"] / 2 for box in (mark, words, descriptor)]
            assert max(middles) - min(middles) <= 12, "части логотипа не на одной строке"
        finally:
            browser.close()


def test_the_logo_keeps_its_parts_on_a_narrow_screen(site):
    with playwright_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=NARROW)
        page.route("https://fonts.**", lambda route: route.abort())
        try:
            page.goto(site + "/", wait_until="load")
            mark = page.locator(".logo-mark").bounding_box()
            words = page.locator(".logo-words img").bounding_box()
            descriptor = page.locator(".logo-descriptor").bounding_box()
            assert mark and words and descriptor
            assert mark["x"] + mark["width"] <= words["x"] + 1, "знак не слева от надписи"
            for box in (mark, words, descriptor):
                assert box["x"] + box["width"] <= NARROW["width"] + 1, "логотип вылез за экран"
        finally:
            browser.close()


def test_the_sticker_stays_inside_a_narrow_screen(site):
    """Наклейка наклонена: на узком экране наклон снимается, иначе она вылезает."""
    with playwright_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=NARROW)
        page.route("https://fonts.**", lambda route: route.abort())
        try:
            page.goto(site + "/meetings/m1", wait_until="load")
            box = page.locator(".sticker").bounding_box()
            assert box is not None, "наклейки нет на первой встрече книги"
            assert box["x"] >= 0
            assert box["x"] + box["width"] <= NARROW["width"] + 1
        finally:
            browser.close()


def test_the_meeting_image_fits_a_narrow_screen(site):
    """Афиша 1080 точек шириной: на телефоне она ужимается, а не растягивает страницу."""
    with playwright_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=NARROW)
        page.route("https://fonts.**", lambda route: route.abort())
        try:
            for path in ("/meetings/m1", "/meetings/m2"):
                page.goto(site + path, wait_until="load")
                box = page.locator(".meeting-image img").bounding_box()
                assert box is not None, f"{path}: картинки встречи нет"
                assert box["x"] >= 0, path
                assert box["x"] + box["width"] <= NARROW["width"] + 1, path
                # Пропорции 4:5 держатся и до загрузки файла: место под картинку
                # занято сразу, раскладка не прыгает.
                assert abs(box["height"] / box["width"] - 1350 / 1080) < 0.02, path
        finally:
            browser.close()


WIDE = {"width": 1280, "height": 900}


def test_the_sections_stand_on_one_line_with_the_logo_on_a_wide_screen(site):
    """Пункты шапки — в одну строку, на одной середине с логотипом; подчёркивание
    стоит сразу под текстом, а не уезжает вниз растянутым пунктом."""
    with playwright_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=WIDE)
        page.route("https://fonts.**", lambda route: route.abort())
        try:
            page.goto(site + "/", wait_until="load")
            links = page.locator(".sections a").all()
            assert len(links) == 4, "в шапке должны быть только четыре раздела"
            boxes = [link.bounding_box() for link in links]
            assert all(boxes)
            middles = [box["y"] + box["height"] / 2 for box in boxes]
            assert max(middles) - min(middles) <= 2, "пункты шапки стоят не на одной линии"
            logo = page.locator(".logo").bounding_box()
            assert logo is not None
            logo_middle = logo["y"] + logo["height"] / 2
            assert abs(middles[0] - logo_middle) <= 4, "пункты шапки не по середине логотипа"
            for link, box in zip(links, boxes):
                line = link.evaluate(
                    "node => parseFloat(getComputedStyle(node).lineHeight)"
                    " || parseFloat(getComputedStyle(node).fontSize) * 1.55"
                )
                # Высота пункта — строка текста плюс отступ и черта подчёркивания.
                assert box["height"] <= line + 6, (
                    "пункт шапки растянут — подчёркивание уехало от текста"
                )
            assert page.locator(".menu-toggle").is_hidden(), "кнопка меню видна на широком экране"
        finally:
            browser.close()


def _inside_the_narrow_screen(box, what):
    assert box is not None, f"{what}: не найдено"
    assert box["x"] >= 0, what
    assert box["x"] + box["width"] <= NARROW["width"] + 1, what


def test_finished_books_fit_a_narrow_screen(site):
    with playwright_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=NARROW)
        page.route("https://fonts.**", lambda route: route.abort())
        try:
            page.goto(site + "/", wait_until="load")
            covers = page.locator(".finished .cover").all()
            assert len(covers) == 3, "в сетке прочитанных не три книги"
            for cover in covers:
                _inside_the_narrow_screen(cover.bounding_box(), "обложка прочитанной книги")
            # Две колонки: обложки не сжимаются в марку и не идут по одной.
            first, second = (cover.bounding_box() for cover in covers[:2])
            assert abs(first["y"] - second["y"]) <= 1, "в сетке одна колонка"
            assert first["width"] >= 120, "обложка в сетке слишком мелкая"
        finally:
            browser.close()


def test_history_covers_fit_a_narrow_screen(site):
    with playwright_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=NARROW)
        page.route("https://fonts.**", lambda route: route.abort())
        try:
            page.goto(site + "/history", wait_until="load")
            covers = page.locator(".segment .cover").all()
            assert len(covers) == 4, "не у каждого отрезка книги есть обложка"
            for cover in covers:
                _inside_the_narrow_screen(cover.bounding_box(), "обложка в ленте истории")
        finally:
            browser.close()


def test_the_next_meeting_poster_fits_a_narrow_screen(site):
    with playwright_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=NARROW)
        page.route("https://fonts.**", lambda route: route.abort())
        try:
            page.goto(site + "/", wait_until="load")
            box = page.locator(".next .meeting-image img").bounding_box()
            _inside_the_narrow_screen(box, "афиша ближайшей встречи")
            assert abs(box["height"] / box["width"] - 1350 / 1080) < 0.02
        finally:
            browser.close()


def test_the_meeting_image_stands_beside_the_heading_on_a_wide_screen(site):
    with playwright_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=WIDE)
        page.route("https://fonts.**", lambda route: route.abort())
        try:
            # На главной заголовок встречи — h2: h1 там у заставки.
            for path, title in (("/", ".next-title"), ("/meetings/m1", "h1")):
                page.goto(site + path, wait_until="load")
                image = page.locator(".meeting-image img").first.bounding_box()
                heading = page.locator(title).first.bounding_box()
                assert image and heading, path
                assert heading["x"] + heading["width"] <= image["x"] + 1, (
                    f"{path}: картинка не справа от заголовка"
                )
                assert image["y"] < WIDE["height"], f"{path}: картинка не на первом экране"
        finally:
            browser.close()


def test_the_header_stays_on_top_while_scrolling(site):
    with playwright_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        # Окно пониже: страница из набора тестовых данных короткая.
        for viewport in ({"width": 1280, "height": 400}, {"width": 360, "height": 400}):
            page = browser.new_page(viewport=viewport)
            page.route("https://fonts.**", lambda route: route.abort())
            page.goto(site + "/history", wait_until="load")
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(200)
            assert page.evaluate("window.scrollY") > 0, "странице некуда прокручиваться"
            box = page.locator(".top").bounding_box()
            assert box is not None
            assert abs(box["y"]) <= 1, f"{viewport['width']}: шапка уехала при прокрутке"
            page.close()
        browser.close()


def test_the_sections_hide_behind_a_burger_on_a_narrow_screen(site):
    with playwright_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=NARROW)
        page.route("https://fonts.**", lambda route: route.abort())
        try:
            page.goto(site + "/", wait_until="load")
            toggle = page.locator(".menu-toggle")
            assert toggle.is_visible(), "кнопки меню нет на узком экране"
            assert toggle.get_attribute("aria-expanded") == "false"
            assert page.locator(".sections").is_hidden(), "меню раскрыто до нажатия"
            toggle.click()
            assert toggle.get_attribute("aria-expanded") == "true"
            for link in page.locator(".sections a").all():
                assert link.is_visible()
                box = link.bounding_box()
                assert box and box["x"] + box["width"] <= NARROW["width"] + 1
            toggle.click()
            assert page.locator(".sections").is_hidden(), "меню не закрылось"
        finally:
            browser.close()


def test_the_sections_stay_open_without_scripts(site):
    """Без скриптов кнопке нечем раскрыть меню — тогда пункты видны сразу."""
    with playwright_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport=NARROW, java_script_enabled=False)
        page = context.new_page()
        page.route("https://fonts.**", lambda route: route.abort())
        try:
            page.goto(site + "/", wait_until="load")
            assert page.locator(".sections").is_visible()
            assert page.locator(".menu-toggle").is_hidden()
        finally:
            browser.close()


# --- главная-витрина ----------------------------------------------------------


def _open_home(playwright, viewport, scripts=True):
    browser = playwright.chromium.launch()
    context = browser.new_context(viewport=viewport, java_script_enabled=scripts)
    page = context.new_page()
    page.route("https://fonts.**", lambda route: route.abort())
    return browser, page


def test_the_home_page_has_no_horizontal_scrolling_on_a_wide_screen(site):
    with playwright_api.sync_playwright() as playwright:
        browser, page = _open_home(playwright, WIDE)
        try:
            page.goto(site + "/", wait_until="load")
            scroll_width = page.evaluate("document.documentElement.scrollWidth")
            client_width = page.evaluate("document.documentElement.clientWidth")
            assert scroll_width <= client_width
        finally:
            browser.close()


def test_the_hero_columns_stand_side_by_side_only_on_a_wide_screen(site):
    with playwright_api.sync_playwright() as playwright:
        for viewport, side_by_side in ((WIDE, True), (NARROW, False)):
            browser, page = _open_home(playwright, viewport)
            try:
                page.goto(site + "/", wait_until="load")
                columns = page.locator(".hero-col").all()
                assert len(columns) == 2, "в заставке не две колонки"
                left, right = (column.bounding_box() for column in columns)
                if side_by_side:
                    assert abs(left["y"] - right["y"]) <= 1, "колонки не на одной высоте"
                    assert left["x"] + left["width"] <= right["x"], "колонки наехали"
                else:
                    assert right["y"] >= left["y"] + left["height"], "на телефоне колонки не друг под другом"
                    _inside_the_narrow_screen(right, "колонка понятий")
            finally:
                browser.close()


def test_the_manifesto_takes_two_lines_on_a_wide_screen(site):
    """Манифест делится по смыслу: «что делаем» и «как». Слово на строку рвёт
    фразу, а перенос не там прячет вторую половину."""
    with playwright_api.sync_playwright() as playwright:
        browser, page = _open_home(playwright, WIDE)
        try:
            page.goto(site + "/", wait_until="load")
            lines = page.locator(".hero-title .hero-line").all()
            assert [line.inner_text() for line in lines] == [
                "Читаем техническую литературу",
                "и спорим о ней вслух",
            ]
            for line in lines:
                rects = line.evaluate("node => node.getClientRects().length")
                assert rects == 1, f"строка «{line.inner_text()}» переносится"
        finally:
            browser.close()


def test_the_gallery_image_is_not_taller_than_the_screen(site):
    with playwright_api.sync_playwright() as playwright:
        for viewport in (WIDE, NARROW):
            browser, page = _open_home(playwright, viewport)
            try:
                page.goto(site + "/", wait_until="load")
                image = page.locator(".gallery-panel:not([hidden]) img")
                assert image.count() == 1, "в галерее показана не одна картинка"
                box = image.bounding_box()
                assert box is not None
                assert box["height"] <= viewport["height"], (
                    f"{viewport['width']}: картинка {box['height']} выше окна"
                )
                assert abs(box["height"] / box["width"] - 1350 / 1080) < 0.02
                assert box["x"] + box["width"] <= viewport["width"] + 1
                tabs = page.locator(".gallery-tabs").bounding_box()
                assert tabs["x"] + tabs["width"] <= viewport["width"] + 1, "вкладки шире экрана"
                if viewport is WIDE:
                    assert tabs["x"] >= box["x"] + box["width"], "вкладки не справа от картинки"
                else:
                    assert tabs["y"] + tabs["height"] <= box["y"], "вкладки не над картинкой"
            finally:
                browser.close()


def test_a_gallery_tab_switches_the_image_in_place(site):
    with playwright_api.sync_playwright() as playwright:
        browser, page = _open_home(playwright, WIDE)
        try:
            page.goto(site + "/", wait_until="load")
            first = page.locator("#gallery-tab-m1")
            second = page.locator("#gallery-tab-m2")
            assert first.get_attribute("aria-selected") == "true"
            assert page.locator("#gallery-panel-m2").is_hidden()
            second.click()
            assert page.url.rstrip("/") == site, "вкладка увела со страницы"
            assert second.get_attribute("aria-selected") == "true"
            assert first.get_attribute("aria-selected") == "false"
            assert page.locator("#gallery-panel-m2").is_visible()
            assert page.locator("#gallery-panel-m1").is_hidden()
            # Стрелкой — к следующей вкладке по кругу.
            second.press("ArrowDown")
            assert first.get_attribute("aria-selected") == "true"
            assert page.locator("#gallery-panel-m1").is_visible()
        finally:
            browser.close()


def test_without_scripts_a_gallery_tab_is_a_link_to_the_meeting(site):
    with playwright_api.sync_playwright() as playwright:
        browser, page = _open_home(playwright, WIDE, scripts=False)
        try:
            page.goto(site + "/", wait_until="load")
            assert page.locator("#gallery-panel-m1").is_visible()
            page.locator("#gallery-tab-m2").click()
            page.wait_for_url("**/meetings/m2")
        finally:
            browser.close()


# --- словарь и подсказки понятий --------------------------------------------


def test_the_glossary_has_no_horizontal_scrolling_on_a_wide_screen(site):
    with playwright_api.sync_playwright() as playwright:
        browser, page = _open_home(playwright, WIDE)
        try:
            page.goto(site + "/glossary", wait_until="load")
            scroll_width = page.evaluate("document.documentElement.scrollWidth")
            client_width = page.evaluate("document.documentElement.clientWidth")
            assert scroll_width <= client_width
        finally:
            browser.close()


def test_a_glossary_anchor_is_not_hidden_under_the_header(site):
    """Шапка закреплена: понятие, на которое перешли, должно стоять под ней."""
    with playwright_api.sync_playwright() as playwright:
        browser, page = _open_home(playwright, NARROW)
        try:
            page.goto(site + "/glossary#isolation-levels", wait_until="load")
            header = page.locator("header.top").bounding_box()
            entry = page.locator("#isolation-levels").bounding_box()
            assert entry["y"] >= header["y"] + header["height"] - 1, "понятие ушло под шапку"
        finally:
            browser.close()


@pytest.mark.parametrize("viewport", [NARROW, WIDE], ids=["360", "1280"])
@pytest.mark.parametrize(
    "path, link",
    [
        ("/", ".hero .plates a[href$='#isolation-levels']"),
        ("/meetings/m1", ".topics a[href$='#isolation-levels']"),
    ],
    ids=["home", "meeting"],
)
def test_a_term_tip_shows_on_hover_and_focus_inside_the_screen(site, viewport, path, link):
    with playwright_api.sync_playwright() as playwright:
        browser, page = _open_home(playwright, viewport)
        try:
            page.goto(site + path, wait_until="load")
            anchor = page.locator(link)
            tip = page.locator("#" + anchor.get_attribute("aria-describedby"))
            assert not tip.is_visible(), "подсказка видна без наведения"

            anchor.hover()
            assert tip.is_visible(), "на наведение подсказки нет"
            box = tip.bounding_box()
            assert box["x"] >= 0 and box["x"] + box["width"] <= viewport["width"] + 1
            scroll_width = page.evaluate("document.documentElement.scrollWidth")
            client_width = page.evaluate("document.documentElement.clientWidth")
            assert scroll_width <= client_width, "подсказка раздвинула страницу"

            page.mouse.move(0, 0)
            anchor.focus()
            assert tip.is_visible(), "на фокус с клавиатуры подсказки нет"
        finally:
            browser.close()


def test_the_warmup_block_fits_a_narrow_screen_with_the_button_under_the_text(site):
    """На телефоне кнопка «Играть» встаёт под текст, а не сжимает его в столбик."""
    with playwright_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=NARROW)
        page.route("https://fonts.**", lambda route: route.abort())
        try:
            page.goto(site + "/", wait_until="load")
            block = page.locator(".warmup").bounding_box()
            _inside_the_narrow_screen(block, "блок разминки")
            text = page.locator(".warmup-text").bounding_box()
            button = page.locator(".warmup-play").bounding_box()
            _inside_the_narrow_screen(button, "кнопка «Играть»")
            assert button["y"] >= text["y"] + text["height"], "кнопка не под текстом"
        finally:
            browser.close()


def test_the_warmup_button_stands_beside_the_text_on_a_wide_screen(site):
    with playwright_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=WIDE)
        page.route("https://fonts.**", lambda route: route.abort())
        try:
            page.goto(site + "/", wait_until="load")
            text = page.locator(".warmup-text").bounding_box()
            button = page.locator(".warmup-play").bounding_box()
            assert button["x"] >= text["x"] + text["width"], "кнопка не справа от текста"
            # Блок небольшой: не выше пары строк с кнопкой.
            assert page.locator(".warmup").bounding_box()["height"] <= 160
        finally:
            browser.close()
