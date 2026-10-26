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
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.view import (
    ClubView,
    chapter_phrase,
    google_calendar_url,
    is_past,
    meeting_image,
)
from app.data.loader import load_club_data
from app.web import humanize, links, seo

LOGO = "/static/logo-mark.png"

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
    """
    folder = base.strip("/")
    prefix = f"/{folder}" if folder else ""
    origin = origin.rstrip("/")
    club_view = view if view is not None else default_view()
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    def absolute(path: str) -> str:
        return f"{origin}{prefix}{path}" if origin else ""

    templates = Jinja2Templates(directory=str(TEMPLATES))
    templates.env.globals.update(
        url=lambda path: prefix + path if prefix else path,
        absolute=absolute,
        club=club_view.club,
        view=club_view,
        chapter_phrase=chapter_phrase,
        site_title=seo.site_title(club_view.club),
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
    )

    def render(request: Request, name: str, section: str, **context) -> HTMLResponse:
        context.setdefault("description", seo.club_description(club_view.club))
        return templates.TemplateResponse(
            request=request,
            name=name,
            context={
                "section": section,
                "canonical": absolute(request.url.path),
                "organization": seo.organization(
                    club_view.club, absolute("/"), absolute(LOGO)
                ),
                **context,
            },
        )

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
        )

    @app.get("/history", response_class=HTMLResponse)
    def history(request: Request) -> HTMLResponse:
        return render(
            request,
            "history.html",
            section="history",
            feed=club_view.history(),
            description=seo.history_description(club_view.club),
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
        return render(
            request,
            "meeting.html",
            # Предстоящая встреча — это раздел «Сейчас», прошедшая — «Полка»:
            # подсветка раздела должна совпадать с тем, откуда на страницу пришли.
            section="history" if past else "now",
            meeting=found,
            number=number,
            book=club_view.data.book(found.book_id) if found.book_id else None,
            chapters=club_view.chapters_of_meeting(found),
            calendar_url=(
                None if past else google_calendar_url(club_view.calendar_event(found))
            ),
            is_past=past,
            image=meeting_image(found, day),
            description=seo.meeting_description(found, number, heading, club_view.club),
            event=seo.event(
                found,
                heading,
                club_view.club,
                absolute(f"/meetings/{meeting_id}"),
                absolute("/"),
            ),
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
            description=seo.book_description(found, club_view.club),
        )

    @app.get("/glossary", response_class=HTMLResponse)
    def glossary(request: Request) -> HTMLResponse:
        return render(
            request,
            "glossary.html",
            section="glossary",
            index=club_view.glossary_index(),
            description=seo.glossary_description(club_view.club),
        )

    @app.get("/about", response_class=HTMLResponse)
    def about(request: Request) -> HTMLResponse:
        return render(
            request,
            "about.html",
            section="about",
            description=seo.about_description(club_view.club),
        )

    return app
