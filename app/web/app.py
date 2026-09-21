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

from app.core.view import ClubView, chapter_phrase
from app.data.loader import load_club_data
from app.web import humanize

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / "templates"
STATIC = HERE / "static"
ROOT = HERE.parent.parent
DEFAULT_DATA = ROOT / "data" / "club.yaml"
GAME_DIR = ROOT / "vendor" / "tyzharchitector"
GAME_PATH = "/game/"
TOPICS_ON_SHELF = 6


def default_view() -> ClubView:
    """Данные клуба из файла. Путь можно переопределить переменной CLUB_DATA."""
    return ClubView(load_club_data(os.environ.get("CLUB_DATA", DEFAULT_DATA)))


def _mount_game(app: FastAPI) -> None:
    """Раздаёт игру-разминку с нашего домена.

    Игра подключена подмодулем закреплённой версии: её код мы не копируем и не
    правим. Если подмодуль не выкачан, страница честно говорит, чего не хватает,
    и остальной сайт от этого не страдает.
    """
    if (GAME_DIR / "index.html").exists():
        app.mount(GAME_PATH, StaticFiles(directory=GAME_DIR, html=True), name="game")
        return

    @app.get(GAME_PATH, response_class=HTMLResponse)
    def game_missing() -> HTMLResponse:
        return HTMLResponse(
            "<!doctype html><meta charset=utf-8>"
            "<p>Разминка не выкачана. Выполните: "
            "<code>git submodule update --init vendor/tyzharchitector</code>",
            status_code=503,
        )


def create_app(
    view: ClubView | None = None,
    today: Callable[[], Day] = Day.today,
    base: str = "",
) -> FastAPI:
    """Собирает приложение сайта клуба.

    `base` — папка, в которой сайт живёт на хостинге. Пустая для корня домена,
    «/bookclub_web» для страницы проекта на GitHub Pages: там все адреса
    вложены, и абсолютная ссылка без префикса уедет в корень чужого сайта.
    """
    folder = base.strip("/")
    prefix = f"/{folder}" if folder else ""
    club_view = view if view is not None else default_view()
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    _mount_game(app)

    templates = Jinja2Templates(directory=str(TEMPLATES))
    templates.env.globals.update(
        url=lambda path: prefix + path if prefix else path,
        club=club_view.club,
        view=club_view,
        chapter_phrase=chapter_phrase,
    )
    templates.env.filters.update(
        day_month=humanize.day_month,
        full_date=humanize.full_date,
        weekday=humanize.weekday,
        status_label=humanize.status_label,
        meetings_count=humanize.meetings_count,
        chapters_count=humanize.chapters_count,
        chapters_of=humanize.chapters_of,
    )

    def render(request: Request, name: str, section: str, **context) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request, name=name, context={"section": section, **context}
        )

    @app.get("/", response_class=HTMLResponse)
    def now(request: Request) -> HTMLResponse:
        day = today()
        book = club_view.reading_book()
        return render(
            request,
            "now.html",
            section="now",
            upcoming=club_view.upcoming_meeting(day),
            latest=club_view.latest_past_meeting(day),
            book=book,
            progress=club_view.progress(book) if book else None,
        )

    @app.get("/history", response_class=HTMLResponse)
    def history(request: Request) -> HTMLResponse:
        return render(request, "history.html", section="history", feed=club_view.history())

    @app.get("/meetings/{meeting_id}", response_class=HTMLResponse)
    def meeting(request: Request, meeting_id: str) -> HTMLResponse:
        found = club_view.data.meeting(meeting_id)
        if found is None:
            raise HTTPException(status_code=404, detail="встреча не найдена")
        return render(
            request,
            "meeting.html",
            section="history",
            meeting=found,
            number=club_view.number_of(meeting_id),
            book=club_view.data.book(found.book_id) if found.book_id else None,
            is_past=found.date < today(),
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
        )

    @app.get("/shelf", response_class=HTMLResponse)
    def shelf(request: Request) -> HTMLResponse:
        catalogue = club_view.topics()
        return render(
            request,
            "shelf.html",
            section="shelf",
            topics=catalogue,
            recent=tuple(reversed(catalogue))[:TOPICS_ON_SHELF],
            game_url=GAME_PATH,
        )

    @app.get("/shelf/topics", response_class=HTMLResponse)
    def topics(request: Request) -> HTMLResponse:
        return render(request, "topics.html", section="shelf", topics=club_view.topics())

    @app.get("/about", response_class=HTMLResponse)
    def about(request: Request) -> HTMLResponse:
        return render(request, "about.html", section="about")

    return app
