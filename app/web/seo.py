"""Что видят поисковик и телеграм: заголовок и описание страницы, карточка, schema.org.

Слой представления. Правил клуба здесь нет, вычислений по данным тоже: всё
приходит готовым из ядра, а здесь только складывается во фразы и словари.

Абсолютные адреса приходят снаружи: собрать их из заголовков запроса нельзя —
за прокси и на статике они врут, а неверный канонический адрес хуже, чем его
отсутствие.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date as Day
from datetime import datetime, timedelta
from typing import NamedTuple
from zoneinfo import ZoneInfo

from app.core.models import Book, BookStatus, Club, Meeting, Place, Term
from app.web import humanize

LIMIT = 160
# Длиннее поисковики заголовок обрезают, и обрыв приходится на самое нужное —
# книгу или дату.
TITLE_LIMIT = 65

SCHEMA = "https://schema.org"
# Страны в данных нет: клуб очный и самарский. Без страны Google считает адрес
# неполным.
COUNTRY = "RU"

# Что клуб делает с книгой — по её состоянию, для описания страницы книги.
BOOK_VERBS = {
    BookStatus.VOTING: "выбираем на голосовании",
    BookStatus.QUEUED: "читаем следующей",
    BookStatus.READING: "читаем сейчас",
    BookStatus.CLOSED: "прочитали",
    BookStatus.DROPPED: "читали и отложили",
}



class Card(NamedTuple):
    """Картинка карточки пересылки: путь внутри `static`, размеры и подпись.

    Размеры нужны в разметке: без них телеграм и ВКонтакте иногда показывают
    маленькую карточку вместо большой.
    """

    src: str
    width: int
    height: int
    alt: str = ""


VERIFICATION_ENV = {
    "YANDEX_VERIFICATION": "yandex-verification",
    "GOOGLE_SITE_VERIFICATION": "google-site-verification",
}


def shorten(text: str, limit: int = LIMIT) -> str:
    """Укорачивает описание: длинное поисковик всё равно обрежет, и как попало.

    Сначала пробует оборвать на конце предложения — тогда описание выглядит
    дописанным. Если ни одно предложение не помещается, режет по слову и ставит
    многоточие: обрыв посреди слова или внутри открытой кавычки читается как
    поломка.
    """
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    whole = text[:limit].rsplit(". ", 1)
    if len(whole) == 2:
        return whole[0] + "."
    return text[: limit - 1].rsplit(" ", 1)[0].rstrip(" ,.;:—-«(") + "…"


def fit(*variants: str, limit: int = TITLE_LIMIT) -> str:
    """Первый вариант заголовка, что помещается; варианты — от полного к краткому.

    Заголовок не режется: обрезанное название книги хуже, чем отброшенный хвост
    с именем клуба, которое поисковик и так показывает рядом.
    """
    for variant in variants:
        if len(variant) <= limit:
            return variant
    return variants[-1]


def page_url(path: str) -> str:
    """Адрес страницы в той форме, в которой её отдаёт статика.

    Выгрузка кладёт страницу папкой с `index.html`, и GitHub Pages отвечает на
    `/history/`, а `/history` переадресует. Канон, ведущий на переадресацию,
    поисковики считают ошибкой.
    """
    return "/" if path in ("", "/") else path.rstrip("/") + "/"


def _sentence(text: str) -> str:
    """Первое предложение без точки на конце — чтобы склеить с другими."""
    return " ".join(text.split()).split(". ", 1)[0].rstrip(".")


def _what(club: Club) -> str:
    return club.tagline or club.descriptor


def _where(club: Club) -> str:
    return f"{club.name}, {club.place.city}" if club.place.city else club.name


# --- заголовки --------------------------------------------------------------


def site_title(club: Club) -> str:
    """Заголовок главной: название и чем клуб является. Город — в `tagline`."""
    return f"{club.name} — {_what(club)}"


def history_title(club: Club) -> str:
    return fit(f"Полка: книги и итоги встреч — {_where(club)}", f"Полка — {club.name}")


def glossary_title(club: Club) -> str:
    return fit(
        f"Словарь: понятия со встреч клуба — {_where(club)}", f"Словарь — {club.name}"
    )


def about_title(club: Club) -> str:
    if club.about_title:
        return fit(f"{club.about_title} — {club.name}", club.about_title)
    return fit(f"О клубе — {_where(club)}", f"О клубе — {club.name}")


def not_found_title(club: Club) -> str:
    return f"Страница не найдена — {club.name}"


def book_title(book: Book, club: Club) -> str:
    """Название — целиком, с «обсуждением»: так книгу и ищут, чтобы её обсудить."""
    name, author = f"«{book.title}»", book.author
    return fit(
        f"{name}, {author} — обсуждение по главам · {club.name}",
        f"{name}, {author} — обсуждение · {club.name}",
        f"{name} — обсуждение по главам · {club.name}",
        f"{name}, {author} — обсуждение по главам",
        f"{name}, {author} — обсуждение",
        f"{name} — обсуждение по главам",
        f"{name} — обсуждение",
        name,
    )


def meeting_title(meeting: Meeting, heading: str, short: str, club: Club) -> str:
    """Дата делает заголовок единственным; номер «#1» — нет, он свой у каждой книги."""
    when = humanize.full_date(meeting.date)
    return fit(
        f"{heading} — обсуждение {when} · {club.name}",
        f"{heading} — обсуждение {when}",
        f"{heading} — встреча {when}",
        f"{short} — обсуждение {when}",
        f"{short} — {when}",
    )


# --- описания ---------------------------------------------------------------


def club_description(club: Club) -> str:
    """Город идёт первым: по нему клуб и ищут, а выдача режет описание с хвоста.

    Дальше — одна фраза о клубе и когда и где собираемся: «книжный клуб Самара»
    ищут, чтобы прийти.
    """
    parts = [_what(club)]
    if club.about:
        parts.append(_sentence(club.about[0]))
    parts.append(f"Очно: {club.slot}, {club.time}, {club.place.venue}")
    return shorten(". ".join(parts) + ".")


def about_description(club: Club) -> str:
    """Адрес и слот прямо в описании: по ним клуб и ищут в своём городе."""
    return shorten(
        f"{_what(club)}. Как проходит встреча, где и когда "
        f"собираемся: {club.place.full}, {club.slot}, в {club.time}."
    )


def history_description(club: Club, books: int = 0, meetings: int = 0) -> str:
    counted = ""
    if books or meetings:
        counted = (
            f" {books} {humanize.plural(books, 'книга', 'книги', 'книг')} и "
            f"{humanize.meetings_count(meetings)}:"
        )
    return shorten(
        f"Полка книжного клуба «{club.name}» — {_what(club)}.{counted} "
        f"что читали, что разобрали по главам и чем кончились споры."
    )


def glossary_description(club: Club, terms: tuple[Term, ...] = ()) -> str:
    if not terms:
        return shorten(
            f"Словарь книжного клуба «{club.name}»: понятия, о которых говорим на "
            f"встречах, коротко и со ссылками на конспекты глав."
        )
    count = len(terms)
    names = ", ".join(term.name for term in terms[:3])
    return shorten(
        f"Словарь книжного клуба «{club.name}»: {count} "
        f"{humanize.plural(count, 'понятие', 'понятия', 'понятий')} со встреч — "
        f"{names} и другие. Коротко, со ссылками на конспекты глав."
    )


def book_description(book: Book, club: Club) -> str:
    """Книга и автор, что клуб с ней делает и где. Хвост про оглавление и итоги
    отдельным предложением: у длинных названий `shorten` отбросит его целиком,
    а не оборвёт на полуслове."""
    verb = BOOK_VERBS.get(book.status, "читаем")
    where = f"«{club.name}», {club.place.city}" if club.place.city else f"«{club.name}»"
    return shorten(
        f"«{book.title}», {book.author} — {verb} по главам в книжном клубе {where}. "
        f"Оглавление, встречи и итоги обсуждений."
    )


def meeting_description(
    meeting: Meeting, number: int | None, heading: str, club: Club
) -> str:
    """Номер, дата и место — первыми; дальше — о чём встреча своими словами.

    Для прошедшей это первая фраза итогов, для предстоящей — анонса.
    """
    numbered = f"Встреча #{number}" if number else "Встреча"
    place = meeting.place
    where = ", ".join(part for part in (place.short, place.city) if part)
    outcome = meeting.outcome
    said = next(
        (
            text
            for text in (
                outcome.lead if outcome else None,
                outcome.verdict if outcome else None,
                outcome.agreed if outcome else None,
                *meeting.announce,
            )
            if text
        ),
        "",
    )
    said = " ".join(said.split())
    # Анонс пишут строками без точки — без неё описание читается оборванным.
    if said and said[-1] not in ".!?…»":
        said += "."
    return shorten(
        f"{numbered}, {humanize.full_date(meeting.date)}, {meeting.time}, {where}. "
        f"{heading}. {said}"
    )


def not_found_description(club: Club) -> str:
    return f"Такой страницы на сайте клуба «{club.name}» нет."


# --- schema.org -------------------------------------------------------------


def club_id(home: str) -> str:
    """`@id` клуба: по нему событие и сайт ссылаются на организатора."""
    return f"{home}#club"


def postal_address(place: Place) -> dict:
    street = ", ".join(
        part for part in (place.street, place.building, place.floor, place.room) if part
    )
    address = {"@type": "PostalAddress", "streetAddress": street}
    if place.city:
        address["addressLocality"] = place.city
    address["addressCountry"] = COUNTRY
    return address


def place_of(place: Place) -> dict:
    found = {"@type": "Place", "name": place.venue, "address": postal_address(place)}
    if place.map:
        found["hasMap"] = place.map
    return found


def organization(club: Club, home: str, logo: str) -> dict:
    """Сведения о клубе — одинаковые на всех страницах.

    В `sameAs` — только чат клуба: сайт и каналы площадки принадлежат другой
    организации, а `sameAs` значит «это тоже мы».
    """
    found = {
        "@context": SCHEMA,
        "@type": "Organization",
        "@id": club_id(home),
        "name": club.name,
        "description": club_description(club),
        "url": home,
        "logo": logo,
        "address": postal_address(club.place),
        "location": place_of(club.place),
        "sameAs": [link for link in (club.telegram,) if link],
    }
    if club.place.city:
        found["areaServed"] = {"@type": "City", "name": club.place.city}
    if club.since:
        found["foundingDate"] = str(club.since)
    return found


def website(club: Club, home: str) -> dict:
    return {
        "@context": SCHEMA,
        "@type": "WebSite",
        "@id": f"{home}#site",
        "name": club.name,
        "url": home,
        "inLanguage": "ru",
        "publisher": {"@id": club_id(home)},
    }


def local_time(day: Day, time: str, timezone: str, after_minutes: int = 0) -> str:
    """Время встречи со смещением пояса клуба: без смещения Google читает его как UTC."""
    hours, minutes = (int(part) for part in time.split(":"))
    start = datetime(day.year, day.month, day.day, hours, minutes, tzinfo=ZoneInfo(timezone))
    return (start + timedelta(minutes=after_minutes)).isoformat()


def book_ref(book: Book, url: str, cover: str = "") -> dict:
    """Книга для schema.org. Авторы в данных — одной строкой через запятую."""
    found = {
        "@type": "Book",
        "@id": f"{url}#book",
        "name": book.title,
        "author": [
            {"@type": "Person", "name": name.strip()}
            for name in book.author.split(",")
            if name.strip()
        ],
        "url": url,
    }
    if cover:
        found["image"] = cover
    return found


def book(found: Book, url: str, cover: str = "") -> dict:
    return {"@context": SCHEMA, **book_ref(found, url, cover)}


def event(
    meeting: Meeting,
    heading: str,
    club: Club,
    url: str,
    home: str,
    *,
    description: str = "",
    image: str = "",
    featured: dict | None = None,
) -> dict:
    """Встреча как событие: очное и бесплатное — таким клуб и является."""
    found = {
        "@context": SCHEMA,
        "@type": "Event",
        "name": heading,
        "startDate": local_time(meeting.date, meeting.time, club.timezone),
        "endDate": local_time(
            meeting.date, meeting.time, club.timezone, club.duration_minutes
        ),
        "eventAttendanceMode": f"{SCHEMA}/OfflineEventAttendanceMode",
        "eventStatus": f"{SCHEMA}/EventScheduled",
        "location": place_of(meeting.place),
        "organizer": {
            "@type": "Organization",
            "@id": club_id(home),
            "name": club.name,
            "url": home,
        },
        "isAccessibleForFree": True,
        # Вход свободный — это цена ноль; без `offers` Google считает событие неполным.
        "offers": {
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "RUB",
            "availability": f"{SCHEMA}/InStock",
            "url": url,
        },
        "inLanguage": "ru",
        "url": url,
    }
    if description:
        found["description"] = description
    if image:
        found["image"] = [image]
    if featured:
        found["workFeatured"] = featured
    return found


def term_set(terms: tuple[Term, ...], url: str, club: Club) -> dict:
    """Словарь как набор понятий; у понятия свой адрес — якорь на странице."""
    set_id = f"{url}#terms"
    defined = []
    for term in terms:
        found = {
            "@type": "DefinedTerm",
            "@id": f"{url}#{term.id}",
            "name": term.name,
            "description": term.summary,
            "url": f"{url}#{term.id}",
            "inDefinedTermSet": {"@id": set_id},
        }
        if term.aliases:
            found["alternateName"] = list(term.aliases)
        defined.append(found)
    return {
        "@context": SCHEMA,
        "@type": "DefinedTermSet",
        "@id": set_id,
        "name": f"Словарь клуба «{club.name}»",
        "url": url,
        "inLanguage": "ru",
        "hasDefinedTerm": defined,
    }


def breadcrumbs(items: list[tuple[str, str]]) -> dict:
    """Цепочка от главной: пары «подпись — абсолютный адрес»."""
    return {
        "@context": SCHEMA,
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": position, "name": name, "item": url}
            for position, (name, url) in enumerate(items, start=1)
        ],
    }


# --- иконки и подтверждение прав --------------------------------------------


def manifest(club: Club, url) -> dict:
    """Манифест сайта. `url` — функция, добавляющая папку сайта к пути."""
    return {
        "name": club.name,
        "short_name": club.name,
        "description": club_description(club),
        "lang": "ru",
        "start_url": url("/"),
        "display": "browser",
        "background_color": "#0a0a0a",
        "theme_color": "#0a0a0a",
        "icons": [
            {"src": url(f"/static/icon-{size}.png"), "sizes": f"{size}x{size}", "type": "image/png"}
            for size in (192, 512)
        ],
    }


def verification_from_env(environ: Mapping[str, str]) -> dict[str, str]:
    """Коды подтверждения прав из окружения: имя мета-тега → значение. Пустые — мимо."""
    return {
        tag: environ[name].strip()
        for name, tag in VERIFICATION_ENV.items()
        if environ.get(name, "").strip()
    }
