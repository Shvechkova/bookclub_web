"""Веб-слой: сборка приложения и маршруты.

Страницы — адаптер поверх `app.core.view`. Ни одного вычисления здесь нет:
всё, что показывается, приходит из ядра готовым.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import date as Day
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.view import (
    ClubView,
    chapter_phrase,
    google_calendar_url,
    is_past,
    meeting_image,
)
from app.data.loader import load_club_data
from app.web import humanize, links, search, seo

LOGO = "/static/logo-mark.png"
# Карточка пересылки страниц без картинки встречи. Логотип для большой
# карточки не годится: он почти квадратный, и телеграм обрезает его по краям.
CARD = seo.Card(src="og-card.jpg", width=1200, height=630)
# Размер афиш и карточек итогов — тот же, что в шаблоне картинки встречи.
MEETING_IMAGE = (1080, 1350)

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / "templates"
STATIC = HERE / "static"
ROOT = HERE.parent.parent
DEFAULT_DATA = ROOT / "data" / "club.yaml"


def default_view() -> ClubView:
    """Данные клуба из файла. Путь можно переопределить переменной CLUB_DATA,
    словарь — переменной CLUB_GLOSSARY; без неё словарь лежит рядом с данными."""
    return ClubView(
        load_club_data(
            os.environ.get("CLUB_DATA", DEFAULT_DATA),
            os.environ.get("CLUB_GLOSSARY") or None,
        )
    )


def create_app(
    view: ClubView | None = None,
    today: Callable[[], Day] = Day.today,
    base: str = "",
    origin: str = "",
    verification: dict[str, str] | None = None,
) -> FastAPI:
    """Собирает приложение сайта клуба.

    `base` — папка, в которой сайт живёт на хостинге. Пустая для корня домена,
    «/bookclub_web» для страницы проекта на GitHub Pages: там все адреса
    вложены, и абсолютная ссылка без префикса уедет в корень чужого сайта.

    `origin` — схема и домен сайта, «https://example.org». Нужен там, где
    относительного адреса не хватает: канонический адрес, карточка для
    пересылки, карта сайта. Не задан — этой разметки на страницах нет: адрес,
    собранный из заголовков запроса, врёт за прокси и на статике, а неверный
    канонический адрес хуже отсутствующего.

    `verification` — коды подтверждения прав в Яндексе и Google: имя мета-тега
    → значение, см. `seo.verification_from_env`.
    """
    folder = base.strip("/")
    prefix = f"/{folder}" if folder else ""
    origin = origin.rstrip("/")
    club_view = view if view is not None else default_view()
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    club = club_view.club

    def absolute(path: str) -> str:
        return f"{origin}{prefix}{path}" if origin else ""

    def url(path: str) -> str:
        return prefix + path if prefix else path

    def page(path: str) -> str:
        """Абсолютный адрес страницы — в форме, которую отдаёт статика."""
        return absolute(seo.page_url(path))

    def crumbs(*items: tuple[str, str]) -> list[dict]:
        """Цепочка от главной до страницы; без адреса сайта её не из чего собрать."""
        if not origin:
            return []
        return [seo.breadcrumbs([(club.name, page("/")), *items])]

    def cover(book) -> str:
        return absolute(f"/static/{book.cover}") if book.cover else ""

    templates = Jinja2Templates(directory=str(TEMPLATES))
    templates.env.globals.update(
        url=url,
        absolute=absolute,
        club=club,
        view=club_view,
        chapter_phrase=chapter_phrase,
        verification=verification or {},
    )
    templates.env.filters.update(
        day_month=humanize.day_month,
        full_date=humanize.full_date,
        weekday=humanize.weekday,
        on_weekday=humanize.on_weekday,
        short_date=humanize.short_date,
        status_label=humanize.status_label,
        meetings_count=humanize.meetings_count,
        chapters_count=humanize.chapters_count,
        chapters_of=humanize.chapters_of,
        minutes=humanize.minutes,
        chapter_numbers=humanize.chapter_numbers,
        new_tab=links.new_tab,
        search_text=search.search_text,
        search_names=search.search_names,
    )

    def render(
        request: Request,
        name: str,
        section: str,
        linked: list[dict] | None = None,
        status_code: int = 200,
        **context,
    ) -> HTMLResponse:
        context.setdefault("title", seo.site_title(club))
        context.setdefault("description", seo.club_description(club))
        context.setdefault("og_type", "website")
        context.setdefault("card", CARD._replace(alt=seo.site_title(club)))
        # Закрытой от индекса странице канон и карточка ни к чему.
        canonical = "" if context.get("noindex") else page(request.url.path)
        # Сведения о клубе — на каждой странице с каноном.
        linked_data = (
            [seo.organization(club, page("/"), absolute(LOGO)), *(linked or [])]
            if canonical
            else []
        )
        return templates.TemplateResponse(
            request=request,
            name=name,
            status_code=status_code,
            context={
                "section": section,
                "canonical": canonical,
                "linked_data": linked_data,
                **context,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def not_found(request: Request, error: StarletteHTTPException):
        """Неизвестный адрес — страницей сайта, а не голым JSON.

        Та же страница ложится при выгрузке в `404.html`: GitHub Pages отдаёт её
        на любой неизвестный адрес. От индекса закрыта — это не страница клуба.
        """
        if error.status_code != 404:
            return JSONResponse({"detail": error.detail}, status_code=error.status_code)
        return render(
            request,
            "not_found.html",
            section="",
            status_code=404,
            noindex=True,
            title=seo.not_found_title(club),
            description=seo.not_found_description(club),
        )

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> FileResponse:
        # Иконку запрашивают из корня сайта, не глядя на ссылки в странице.
        return FileResponse(STATIC / "favicon.ico", media_type="image/x-icon")

    @app.get("/manifest.webmanifest", include_in_schema=False)
    def manifest() -> JSONResponse:
        return JSONResponse(seo.manifest(club, url), media_type="application/manifest+json")

    @app.get("/", response_class=HTMLResponse)
    def now(request: Request) -> HTMLResponse:
        day = today()
        book = club_view.reading_book()
        upcoming = club_view.upcoming_meeting(day)
        return render(
            request,
            "now.html",
            section="now",
            upcoming=upcoming,
            upcoming_image=meeting_image(upcoming.meeting, day) if upcoming else None,
            upcoming_chapters=(
                club_view.chapters_of_meeting(upcoming.meeting) if upcoming else ()
            ),
            latest=club_view.latest_past_meeting(day),
            book=book,
            progress=club_view.progress(book) if book else None,
            finished=club_view.finished_books(),
            recent_topics=club_view.recent_topics(day),
            debates=club_view.recent_debates(day),
            gallery=club_view.gallery(day),
            gallery_default=club_view.gallery_default(day),
            linked=[seo.website(club, page("/"))] if origin else [],
        )

    @app.get("/history", response_class=HTMLResponse)
    def history(request: Request) -> HTMLResponse:
        return render(
            request,
            "history.html",
            section="history",
            feed=club_view.history(),
            title=seo.history_title(club),
            description=seo.history_description(
                club, len(club_view.books), len(club_view.data.meetings)
            ),
            linked=crumbs(("Полка", page("/history"))),
        )

    @app.get("/meetings/{meeting_id}", response_class=HTMLResponse)
    def meeting(request: Request, meeting_id: str) -> HTMLResponse:
        found = club_view.data.meeting(meeting_id)
        if found is None:
            raise HTTPException(status_code=404, detail="встреча не найдена")
        number = club_view.number_of(meeting_id)
        heading = club_view.title_of(found)
        day = today()
        past = is_past(found, day)
        image = meeting_image(found, day)
        # Подпись картинки в данных бывает в несколько строк — в мета-теге одной.
        card = (
            seo.Card(image.src, *MEETING_IMAGE, alt=" ".join(image.alt.split()))
            if image
            else None
        )
        book = club_view.data.book(found.book_id) if found.book_id else None
        description = seo.meeting_description(found, number, heading, club)
        here = page(f"/meetings/{meeting_id}")
        linked = []
        if origin:
            # Цепочка идёт через книгу: на полке встреча стоит под ней.
            trail = [("Полка", page("/history"))]
            if book:
                trail.append((book.title, page(f"/books/{book.id}")))
            trail.append((f"Встреча {humanize.full_date(found.date)}", here))
            featured = (
                seo.book_ref(book, page(f"/books/{book.id}"), cover(book)) if book else None
            )
            linked = [
                seo.event(
                    found,
                    heading,
                    club,
                    here,
                    page("/"),
                    description=description,
                    image=absolute("/static/" + (card or CARD).src),
                    featured=featured,
                ),
                *crumbs(*trail),
            ]
        return render(
            request,
            "meeting.html",
            # Предстоящая встреча — это раздел «Сейчас», прошедшая — «Полка»:
            # подсветка раздела должна совпадать с тем, откуда на страницу пришли.
            section="history" if past else "now",
            meeting=found,
            number=number,
            book=book,
            chapters=club_view.chapters_of_meeting(found),
            calendar_url=(
                None if past else google_calendar_url(club_view.calendar_event(found))
            ),
            is_past=past,
            image=image,
            title=seo.meeting_title(found, heading, club_view.short_title_of(found), club),
            description=description,
            linked=linked,
            **({"card": card} if card else {}),
        )

    @app.get("/books/{book_id}", response_class=HTMLResponse)
    def book_page(request: Request, book_id: str) -> HTMLResponse:
        found = club_view.data.book(book_id)
        if found is None:
            raise HTTPException(status_code=404, detail="книга не найдена")
        return render(
            request,
            "book.html",
            section="history",
            book=found,
            chapters=club_view.chapters_of(found),
            progress=club_view.progress(found),
            meeting_count=club_view.meeting_count(found),
            has_history=club_view.has_recorded_history(found),
            passed=club_view.passed_numbers(found),
            title=seo.book_title(found, club),
            description=seo.book_description(found, club),
            og_type="book",
            linked=[
                seo.book(found, page(f"/books/{book_id}"), cover(found)),
                *crumbs(("Полка", page("/history")), (found.title, page(f"/books/{book_id}"))),
            ]
            if origin
            else [],
        )

    @app.get("/glossary", response_class=HTMLResponse)
    def glossary(request: Request) -> HTMLResponse:
        index = club_view.glossary_index()
        # Понятия по алфавиту — в том же порядке, что на странице.
        terms = tuple(term for letter in index for term in letter.terms)
        return render(
            request,
            "glossary.html",
            section="glossary",
            index=index,
            title=seo.glossary_title(club),
            description=seo.glossary_description(club, terms),
            linked=(
                [seo.term_set(terms, page("/glossary"), club)] if origin and terms else []
            )
            + crumbs(("Словарь", page("/glossary"))),
        )

    @app.get("/about", response_class=HTMLResponse)
    def about(request: Request) -> HTMLResponse:
        return render(
            request,
            "about.html",
            section="about",
            title=seo.about_title(club),
            description=seo.about_description(club),
            linked=crumbs(("О клубе", page("/about"))),
        )

    return app
