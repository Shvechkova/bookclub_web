"""Чтение файла данных клуба.

Слой доступа к данным: знает про YAML и про диск, модель — нет. Когда появится
админка, за этим же интерфейсом окажется хранилище с записью.
"""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from app.data.validation import DataError, validate

from app.core.models import (
    Book,
    BookStatus,
    Chapter,
    ChapterOutcome,
    Club,
    ClubData,
    DiscussedChapter,
    Link,
    Meeting,
    MeetingFormat,
    Outcome,
    Quote,
)


__all__ = ["DataError", "load_club_data"]


def load_club_data(path: str | Path) -> ClubData:
    """Читает файл данных и собирает модель клуба."""
    path = Path(path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise DataError(f"не удалось разобрать {path.name}: {error}") from error
    if not isinstance(raw, dict):
        raise DataError(f"{path.name}: ожидался словарь с разделами club, books, meetings")

    club = _club(_section(raw, "club", dict, path.name))
    books = tuple(
        _book(item, path.name) for item in _section(raw, "books", list, path.name)
    )
    meetings = tuple(
        _meeting(item, club, path.name)
        for item in _section(raw, "meetings", list, path.name)
    )
    data = ClubData(club=club, books=books, meetings=meetings)
    validate(data)
    return data


def _section(raw: dict[str, Any], name: str, kind: type, source: str) -> Any:
    if name not in raw:
        raise DataError(f"{source}: нет раздела {name}")
    value = raw[name]
    if not isinstance(value, kind):
        raise DataError(f"{source}: раздел {name} должен быть {kind.__name__}")
    return value


def _required(item: dict[str, Any], key: str, where: str) -> Any:
    if item.get(key) in (None, ""):
        raise DataError(f"{where}: не заполнено поле {key}")
    return item[key]


def _texts(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    return tuple(str(line) for line in value)


def _club(raw: dict[str, Any]) -> Club:
    where = "раздел club"
    return Club(
        name=_required(raw, "name", where),
        descriptor=_required(raw, "descriptor", where),
        about=_required(raw, "about", where),
        place=_required(raw, "place", where),
        slot=_required(raw, "slot", where),
        time=str(_required(raw, "time", where)),
        duration=_required(raw, "duration", where),
        rules=_texts(raw.get("rules")),
        telegram=raw.get("telegram"),
        topic_notes=dict(raw.get("topic_notes") or {}),
        marquee=_texts(raw.get("marquee")),
    )


def _book(raw: dict[str, Any], source: str) -> Book:
    book_id = _required(raw, "id", f"{source}: книга без id")
    where = f"книга {book_id}"
    chapters = tuple(
        Chapter(
            number=position,
            title=_required(chapter, "title", f"{where}, глава {position}"),
            notes_url=chapter.get("notes_url"),
        )
        for position, chapter in enumerate(raw.get("chapters") or [], start=1)
    )
    taken = raw.get("taken_chapters")
    taken_numbers = (
        tuple(int(number) for number in taken)
        if taken
        else tuple(chapter.number for chapter in chapters)
    )
    return Book(
        id=book_id,
        number=int(_required(raw, "number", where)),
        title=_required(raw, "title", where),
        author=_required(raw, "author", where),
        status=_status(raw.get("status"), where),
        chapters=chapters,
        taken_numbers=taken_numbers,
        period=raw.get("period"),
        notes_url=raw.get("notes_url"),
        close_note=raw.get("close_note"),
        takeaways=_texts(raw.get("takeaways")),
    )


def _status(value: Any, where: str) -> BookStatus:
    try:
        return BookStatus(value)
    except ValueError:
        known = ", ".join(status.value for status in BookStatus)
        raise DataError(f"{where}: неизвестное состояние {value!r}, известны: {known}") from None


def _meeting(raw: dict[str, Any], club: Club, source: str) -> Meeting:
    meeting_id = _required(raw, "id", f"{source}: встреча без id")
    where = f"встреча {meeting_id}"
    return Meeting(
        id=meeting_id,
        date=_date(_required(raw, "date", where), where),
        time=str(raw.get("time") or club.time),
        place=raw.get("place") or club.place,
        host=raw.get("host"),
        book_id=raw.get("book"),
        chapters=tuple(
            _discussed(chapter, where) for chapter in raw.get("chapters") or []
        ),
        format=_format(raw.get("format")),
        title=raw.get("title"),
        announce=_texts(raw.get("announce")),
        outcome=_outcome(raw.get("outcome")),
        topics=_texts(raw.get("topics")),
        links=tuple(
            Link(title=_required(link, "title", where), url=_required(link, "url", where))
            for link in raw.get("links") or []
        ),
    )


def _date(value: Any, where: str) -> Date:
    if isinstance(value, Date):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        raise DataError(f"{where}: дата {value!r} не разбирается как ГГГГ-ММ-ДД") from None


def _discussed(raw: Any, where: str) -> DiscussedChapter:
    if not isinstance(raw, dict):
        raise DataError(f"{where}: глава должна задаваться парой number и outcome")
    try:
        outcome = ChapterOutcome(raw.get("outcome") or ChapterOutcome.PLANNED.value)
    except ValueError:
        known = ", ".join(item.value for item in ChapterOutcome)
        raise DataError(
            f"{where}: у главы {raw.get('number')!r} неизвестный исход "
            f"{raw.get('outcome')!r}, известны: {known}"
        ) from None
    return DiscussedChapter(number=int(_required(raw, "number", where)), outcome=outcome)


def _format(raw: Any) -> MeetingFormat | None:
    if not raw:
        return None
    if isinstance(raw, str):
        return MeetingFormat(name=raw)
    return MeetingFormat(name=raw["name"], note=raw.get("note"))


def _outcome(raw: Any) -> Outcome | None:
    if not raw:
        return None
    quote_raw = raw.get("quote")
    quote = None
    if quote_raw:
        quote = Quote(text=quote_raw["text"], chapter=quote_raw.get("chapter"))
    outcome = Outcome(
        agreed=raw.get("agreed"),
        argued=raw.get("argued"),
        taken=raw.get("taken"),
        quote=quote,
    )
    return None if outcome.is_empty else outcome
