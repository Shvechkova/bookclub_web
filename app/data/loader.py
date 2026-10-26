"""Чтение данных клуба: файл клуба и словарь рядом с ним.

Слой доступа к данным: знает про YAML и про диск, модель — нет. Когда появится
админка, за этим же интерфейсом окажется хранилище с записью.
"""

from __future__ import annotations

import re
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
    Card,
    Club,
    ClubData,
    DiscussedChapter,
    Link,
    Meeting,
    MeetingFormat,
    MeetingImage,
    Outcome,
    OutcomeItem,
    Place,
    Quote,
    Space,
    Term,
    TermChapter,
    Warmup,
)


__all__ = ["DataError", "glossary_beside", "load_club_data"]

# id понятия попадает в якорь адреса словаря: только то, что не надо кодировать.
TERM_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def glossary_beside(path: str | Path) -> Path:
    """Словарь, который лежит рядом с файлом клуба: `glossary` и те же расширения.

    `club.yaml` → `glossary.yaml`, `club.example.yaml` → `glossary.example.yaml`:
    образец данных подхватывает образец словаря, а рабочий — рабочий, и одно
    правило обходится без настройки.
    """
    path = Path(path)
    return path.with_name("glossary" + "".join(path.suffixes))


def load_club_data(path: str | Path, glossary: str | Path | None = None) -> ClubData:
    """Читает файл данных и словарь рядом с ним и собирает модель клуба.

    `glossary` — путь к словарю, если он лежит не рядом. Файла словаря нет —
    словарь пуст: сайт работает и без определений, просто темы стоят текстом.
    """
    path = Path(path)
    raw = _read(path)
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
    terms = _glossary(Path(glossary) if glossary is not None else glossary_beside(path))
    data = ClubData(club=club, books=books, meetings=meetings, glossary=terms)
    validate(data)
    return data


def _read(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise DataError(f"не удалось разобрать {path.name}: {error}") from error


def _glossary(path: Path) -> tuple[Term, ...]:
    if not path.exists():
        return ()
    raw = _read(path)
    if raw is None:
        return ()
    if not isinstance(raw, dict) or not isinstance(raw.get("terms") or [], list):
        raise DataError(f"{path.name}: ожидался словарь с разделом terms — списком понятий")
    return tuple(
        _term(item, position, path.name)
        for position, item in enumerate(raw.get("terms") or [], start=1)
    )


def _term(raw: Any, position: int, source: str) -> Term:
    if not isinstance(raw, dict):
        raise DataError(f"{source}: понятие {position} задаётся полями id, name, summary")
    term_id = str(_required(raw, "id", f"{source}: понятие {position}"))
    where = f"{source}: понятие {term_id}"
    if not TERM_ID.match(term_id):
        raise DataError(
            f"{where}: id {term_id!r} — только строчные латинские буквы, цифры и "
            "дефис, например conway-law: он стоит в адресе словаря"
        )
    return Term(
        id=term_id,
        name=str(_required(raw, "name", where)).strip(),
        summary=_text(_required(raw, "summary", where), "summary", where).strip(),
        aliases=_names(raw.get("aliases"), "aliases", where),
        article=raw.get("article") or None,
        chapters=_term_chapters(raw.get("chapters"), where),
        related=_names(raw.get("related"), "related", where),
    )


def _names(value: Any, key: str, where: str) -> tuple[str, ...]:
    """Список имён. Строка вместо списка — ошибка: `_texts` разложил бы её на буквы."""
    if value in (None, ""):
        return ()
    if not isinstance(value, list):
        raise DataError(f"{where}: поле {key} — список, например [ADR]")
    return tuple(name.strip() for name in _texts(value))


def _term_chapters(value: Any, where: str) -> tuple[TermChapter, ...]:
    """Главы конспектов: `{book, chapter}`. Адрес главы берётся из данных книги."""
    if value in (None, ""):
        return ()
    if not isinstance(value, list):
        raise DataError(f"{where}: поле chapters — список {{book, chapter}}")
    chapters = []
    for item in value:
        # `type(...) is int`, а не isinstance: `true` из YAML — тоже int.
        if (
            not isinstance(item, dict)
            or not item.get("book")
            or type(item.get("chapter")) is not int
        ):
            raise DataError(
                f"{where}: глава задаётся книгой и номером, "
                f"{{book: brooks-mythical-man-month, chapter: 5}}, а не {item!r}"
            )
        chapters.append(TermChapter(book_id=str(item["book"]), number=item["chapter"]))
    return tuple(chapters)


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
    """Список строк.

    Вложенную структуру здесь ловим специально: строка «Вход свободный:
    без регистраций» разбирается YAML как словарь, и без проверки она молча
    доезжала бы до страницы в виде `{'Вход свободный': '...'}`.
    """
    if value is None:
        return ()
    lines = []
    for line in value:
        if isinstance(line, (dict, list)):
            raise DataError(
                f"строка списка разобралась как вложенная структура: {line!r}. "
                "Если внутри есть двоеточие с пробелом, возьмите строку в кавычки"
            )
        lines.append(str(line))
    return tuple(lines)


def _paragraphs(value: Any, key: str, where: str) -> tuple[str, ...]:
    """Абзацы списком.

    Строка тоже перебирается по элементам, и `_texts` разложил бы её на буквы:
    страница молча показала бы абзац из одного символа. Поэтому строка здесь —
    ошибка данных, а не короткая запись одного абзаца.
    """
    if isinstance(value, str):
        raise DataError(f"{where}: поле {key} — список абзацев, а не строка")
    return _texts(value)


def _place(raw: Any, where: str) -> Place:
    """Место по частям. Строкой место больше не задаётся: из неё не собрать
    полную форму адреса, а без неё место ищут по карте наугад."""
    if not isinstance(raw, dict):
        raise DataError(
            f"{where}: место задаётся полями venue, building, room "
            f"и необязательными street, floor, city, а не строкой"
        )
    return Place(
        venue=_required(raw, "venue", f"{where}, place"),
        building=_required(raw, "building", f"{where}, place"),
        room=_required(raw, "room", f"{where}, place"),
        street=raw.get("street"),
        floor=raw.get("floor"),
        city=raw.get("city"),
        map=raw.get("map"),
    )


def _space(raw: Any) -> Space | None:
    """Площадка клуба. Не задана — ссылок на неё на сайте нет."""
    if not raw:
        return None
    return Space(
        name=_required(raw, "name", "раздел club, space"),
        site=raw.get("site"),
        channel=raw.get("channel"),
        chat=raw.get("chat"),
        thread=raw.get("thread"),
    )


def _club(raw: dict[str, Any]) -> Club:
    where = "раздел club"
    # Поле убрано, а не забыто: молча пропущенное, оно оставило бы тему без
    # ссылки, и никто бы не узнал почему.
    if raw.get("topic_notes"):
        raise DataError(
            f"{where}: поля topic_notes больше нет — понятия и адреса статей "
            "живут в glossary.yaml рядом с данными, адрес идёт в article понятия"
        )
    return Club(
        name=_required(raw, "name", where),
        descriptor=_required(raw, "descriptor", where),
        about=_paragraphs(_required(raw, "about", where), "about", where),
        place=_place(_required(raw, "place", where), where),
        slot=_required(raw, "slot", where),
        time=str(_required(raw, "time", where)),
        duration_minutes=_minutes(_required(raw, "duration_minutes", where), where),
        timezone=str(_required(raw, "timezone", where)),
        tagline=raw.get("tagline"),
        routine=_paragraphs(raw.get("routine"), "routine", where),
        terms=_paragraphs(raw.get("terms"), "terms", where),
        telegram=raw.get("telegram"),
        space=_space(raw.get("space")),
        marquee=_texts(raw.get("marquee")),
        since=_year(raw.get("since"), where),
        manifesto=_text(raw.get("manifesto"), "manifesto", where),
        about_title=_text(raw.get("about_title"), "about_title", where),
        about_hand=_text(raw.get("about_hand"), "about_hand", where),
        facts=_cards(raw.get("facts"), "facts", where),
        rules=_cards(raw.get("rules"), "rules", where),
        warmup=_warmup(raw.get("warmup"), where),
    )


def _warmup(raw: Any, where: str) -> Warmup | None:
    """Игра-разминка. Адрес строкой вместо раздела — ошибка, а не короткая
    запись: без названия и фразы блок на главной звал бы непонятно куда."""
    if raw in (None, ""):
        return None
    at = f"{where}, warmup"
    if not isinstance(raw, dict):
        raise DataError(f"{at}: разминка задаётся полями name, lead и url, а не строкой")
    return Warmup(
        name=str(_required(raw, "name", at)).strip(),
        lead=str(_required(raw, "lead", at)).strip(),
        url=str(_required(raw, "url", at)).strip(),
    )


def _cards(value: Any, key: str, where: str) -> tuple[Card, ...]:
    """Карточки списком: у каждой заголовок `label` и текст `text`.

    Карточка без текста — пустой прямоугольник на странице, поэтому оба поля
    обязательны и пропуск называется на входе."""
    if value in (None, ""):
        return ()
    if not isinstance(value, list):
        raise DataError(f"{where}: поле {key} — список карточек с полями label и text")
    cards = []
    for position, item in enumerate(value, start=1):
        if not isinstance(item, dict) or not item.get("label") or not item.get("text"):
            raise DataError(
                f"{where}: карточка {position} в поле {key} должна иметь label и text"
            )
        cards.append(Card(label=str(item["label"]).strip(), text=str(item["text"]).strip()))
    return tuple(cards)


def _year(value: Any, where: str) -> int | None:
    """Год числом. «2023» в кавычках тоже год, а «давно» — ошибка данных:
    иначе заставка молча показала бы «с давно»."""
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise DataError(f"{where}: since {value!r} — не год")
    try:
        return int(value)
    except (TypeError, ValueError):
        raise DataError(f"{where}: since {value!r} — не год числом, например 2023") from None


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
        cover=raw.get("cover"),
        short_title=raw.get("short_title"),
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
        place=_place(raw["place"], where) if raw.get("place") else club.place,
        host=raw.get("host"),
        book_id=raw.get("book"),
        chapters=tuple(
            _discussed(chapter, where) for chapter in raw.get("chapters") or []
        ),
        format=_format(raw.get("format")),
        title=raw.get("title"),
        announce=_texts(raw.get("announce")),
        outcome=_outcome(raw.get("outcome"), where),
        topics=_texts(raw.get("topics")),
        links=tuple(
            Link(title=_required(link, "title", where), url=_required(link, "url", where))
            for link in raw.get("links") or []
        ),
        **_images(raw.get("images"), where),
    )


IMAGE_KINDS = {"poster": "poster", "recap": "recap_card"}


def _images(raw: Any, where: str) -> dict[str, MeetingImage]:
    """Картинки встречи: `images: {poster, recap}`, у каждой `src` и `alt`.

    Неизвестная роль — ошибка, а не пропуск: опечатка `recap_card` вместо
    `recap` молча оставила бы встречу без карточки.
    """
    if not raw:
        return {}
    if not isinstance(raw, dict):
        raise DataError(f"{where}: images задаются словарём с полями poster и recap")
    images = {}
    for kind, image in raw.items():
        if kind not in IMAGE_KINDS:
            known = ", ".join(IMAGE_KINDS)
            raise DataError(f"{where}: неизвестная картинка {kind!r}, известны: {known}")
        at = f"{where}, images, {kind}"
        if not isinstance(image, dict):
            raise DataError(f"{at}: картинка задаётся полями src и alt")
        images[IMAGE_KINDS[kind]] = MeetingImage(
            src=_required(image, "src", at),
            alt=_required(image, "alt", at),
        )
    return images


def _minutes(value: Any, where: str) -> int:
    """Длительность встречи числом минут: из числа собирается и подпись, и время
    окончания для календаря, а из строки «90 минут» — только подпись."""
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        raise DataError(f"{where}: duration_minutes {value!r} — не число минут") from None
    if minutes <= 0:
        raise DataError(f"{where}: duration_minutes должно быть больше нуля")
    return minutes


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


def _outcome(raw: Any, where: str) -> Outcome | None:
    if not raw:
        return None
    where = f"{where}, outcome"
    quote_raw = raw.get("quote")
    quote = None
    if quote_raw:
        quote = Quote(text=quote_raw["text"], chapter=quote_raw.get("chapter"))
    outcome = Outcome(
        agreed=raw.get("agreed"),
        argued=raw.get("argued"),
        taken=raw.get("taken"),
        quote=quote,
        lead=_text(raw.get("lead"), "lead", where),
        by_chapter=_outcome_items(raw.get("by_chapter"), "by_chapter", where),
        debates=_outcome_items(raw.get("debates"), "debates", where),
        aside=_text(raw.get("aside"), "aside", where),
        verdict=_text(raw.get("verdict"), "verdict", where),
    )
    return None if outcome.is_empty else outcome


def _text(value: Any, key: str, where: str) -> str | None:
    """Абзац строкой.

    Та же ловушка, что в `_texts`: абзац с двоеточием и пробелом без кавычек
    YAML отдаёт словарём, и на странице встал бы `{'…': '…'}` вместо текста.
    """
    if value in (None, ""):
        return None
    if isinstance(value, (dict, list)):
        raise DataError(
            f"{where}: поле {key} разобралось как вложенная структура. "
            "Если внутри есть двоеточие с пробелом, возьмите строку в кавычки"
        )
    return str(value)


def _outcome_items(value: Any, key: str, where: str) -> tuple[OutcomeItem, ...]:
    """Пункты итогов по порядку записи: `{heading, text, chapters}`, текст обязателен."""
    if value is None:
        return ()
    if not isinstance(value, list):
        raise DataError(f"{where}: поле {key} — список пунктов {{heading, text, chapters}}")
    items = []
    for position, raw in enumerate(value, start=1):
        at = f"{where}, {key}, пункт {position}"
        if not isinstance(raw, dict):
            raise DataError(f"{at}: пункт задаётся полями heading, text и chapters")
        chapters = raw.get("chapters") or []
        if not isinstance(chapters, list) or not all(
            isinstance(number, int) for number in chapters
        ):
            raise DataError(f"{at}: chapters — список номеров глав, например [6, 7]")
        items.append(
            OutcomeItem(
                heading=_text(raw.get("heading"), "heading", at),
                text=_text(_required(raw, "text", at), "text", at),
                chapters=tuple(chapters),
            )
        )
    return tuple(items)
