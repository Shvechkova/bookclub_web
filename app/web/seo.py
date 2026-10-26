"""Что видят поисковик и телеграм: описание страницы, карточка, schema.org.

Слой представления. Правил клуба здесь нет, вычислений по данным тоже: всё
приходит готовым из ядра, а здесь только складывается во фразы и словари.

Абсолютные адреса приходят снаружи: собрать их из заголовков запроса нельзя —
за прокси и на статике они врут, а неверный канонический адрес хуже, чем его
отсутствие.
"""

from __future__ import annotations

from app.core.models import Book, Club, Meeting
from app.web import humanize

LIMIT = 160


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


def site_title(club: Club) -> str:
    """Заголовок главной: название и чем клуб является. Город — в `tagline`."""
    return f"{club.name} — {club.tagline or club.descriptor}"


def club_description(club: Club) -> str:
    """Город идёт первым: по нему клуб и ищут, а выдача режет описание с хвоста."""
    what = club.tagline or club.descriptor
    lead = club.about[0] if club.about else ""
    return shorten(f"{what}. {lead}".strip())


def about_description(club: Club) -> str:
    """Адрес и слот прямо в описании: по ним клуб и ищут в своём городе."""
    return shorten(
        f"{club.tagline or club.descriptor}. Как проходит встреча, где и когда "
        f"собираемся: {club.place.full}, {club.slot}, в {club.time}."
    )


def history_description(club: Club) -> str:
    return shorten(
        f"Все книги и встречи книжного клуба «{club.name}»: что читали, "
        f"что разобрали и чем кончилось."
    )


def glossary_description(club: Club) -> str:
    return shorten(
        f"Словарь книжного клуба «{club.name}»: понятия, о которых говорим на "
        f"встречах, коротко и со ссылками на конспекты глав."
    )


def book_description(book: Book, club: Club) -> str:
    return shorten(
        f"{book.title} — {book.author}. "
        f"Разбираем по главам в книжном клубе «{club.name}»."
    )


def meeting_description(
    meeting: Meeting, number: int | None, heading: str, club: Club
) -> str:
    numbered = f"Встреча #{number}" if number else "Встреча"
    return shorten(
        f"{numbered}, {humanize.full_date(meeting.date)}, {meeting.time}, "
        f"{meeting.place.short}. {heading}"
    )


def organization(club: Club, home: str, logo: str) -> dict:
    """Сведения о клубе — одинаковые на всех страницах."""
    links = [club.telegram]
    if club.space:
        links += [club.space.site, club.space.channel, club.space.chat]
    return {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": club.name,
        "description": club_description(club),
        "url": home,
        "logo": logo,
        "sameAs": [link for link in links if link],
    }


def event(meeting: Meeting, heading: str, club: Club, url: str, home: str) -> dict:
    """Встреча как событие: очное и бесплатное — таким клуб и является."""
    place = meeting.place
    return {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": heading,
        "startDate": f"{meeting.date.isoformat()}T{meeting.time}",
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "eventStatus": "https://schema.org/EventScheduled",
        "location": {"@type": "Place", "name": place.short, "address": place.full},
        "organizer": {"@type": "Organization", "name": club.name, "url": home},
        "isAccessibleForFree": True,
        "url": url,
    }
