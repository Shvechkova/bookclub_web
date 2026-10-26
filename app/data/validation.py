"""Проверка инвариантов клуба — одна, на входе.

Проверки собраны в одном месте намеренно. Разложенные по месту использования,
они оставляют пути, где проверки нет, и ошибка в данных превращается в страницу,
где часть блоков верна, а часть молча пуста.
"""

from __future__ import annotations

from app.core.models import BookStatus, ClubData
from app.core.view import fold_name


class DataError(Exception):
    """Ошибка в файле данных: называет, что именно не так."""


def validate(data: ClubData) -> None:
    """Проверяет данные целиком. Собирает все нарушения, а не первое."""
    problems: list[str] = []
    problems += _unique_ids(data)
    problems += _single_reading_book(data)
    problems += _chapters_taken_exist(data)
    problems += _meetings_make_sense(data)
    problems += _glossary_names_are_unique(data)
    problems += _glossary_refers_to_what_exists(data)
    if problems:
        raise DataError("данные клуба не прошли проверку:\n- " + "\n- ".join(problems))


def _unique_ids(data: ClubData) -> list[str]:
    problems = []
    for what, ids in (
        ("книги", [book.id for book in data.books]),
        ("встречи", [meeting.id for meeting in data.meetings]),
    ):
        seen: set[str] = set()
        for identifier in ids:
            if identifier in seen:
                problems.append(f"{what}: идентификатор {identifier} повторяется")
            seen.add(identifier)
    return problems


def _single_reading_book(data: ClubData) -> list[str]:
    reading = [book.id for book in data.books if book.status is BookStatus.READING]
    if len(reading) > 1:
        return [
            "в состоянии «читаем» может быть не больше одной книги, "
            f"а их {len(reading)}: {', '.join(reading)}"
        ]
    return []


def _chapters_taken_exist(data: ClubData) -> list[str]:
    problems = []
    for book in data.books:
        numbers = {chapter.number for chapter in book.chapters}
        for taken in book.taken_numbers:
            if taken not in numbers:
                problems.append(
                    f"книга {book.id}: в чтение взята глава {taken}, "
                    f"а в оглавлении глав {len(numbers)}"
                )
    return problems


def _meetings_make_sense(data: ClubData) -> list[str]:
    problems = []
    for meeting in data.meetings:
        book = data.book(meeting.book_id) if meeting.book_id else None
        if meeting.book_id and book is None:
            problems.append(
                f"встреча {meeting.id}: ссылается на книгу {meeting.book_id}, которой нет"
            )
        if not meeting.book_id and not meeting.title:
            problems.append(
                f"встреча {meeting.id}: без книги у встречи должно быть собственное название"
            )
        # Главы в пунктах итогов проверяются тем же правилом, что и разобранные:
        # номер, которого нет в книге, на странице встал бы ссылкой в никуда.
        referenced = [("разобрана", discussed.number) for discussed in meeting.chapters]
        if meeting.outcome is not None:
            referenced += [
                ("в итогах упомянута", number)
                for item in meeting.outcome.items()
                for number in item.chapters
            ]
        if referenced and not meeting.book_id:
            problems.append(
                f"встреча {meeting.id}: главы указаны без книги — "
                "разобранные главы и главы в итогах бывают только у встречи "
                "с книжной частью"
            )
        if book is not None:
            numbers = {chapter.number for chapter in book.chapters}
            for verb, number in referenced:
                if number not in numbers:
                    problems.append(
                        f"встреча {meeting.id}: {verb} глава {number}, "
                        f"а в книге {book.id} глав {len(numbers)}"
                    )
    return problems


def _glossary_names_are_unique(data: ClubData) -> list[str]:
    """Id, названия и синонимы словаря не повторяются, регистр не в счёт.

    Тема находит понятие по любому из имён без учёта регистра, поэтому два
    понятия с именем «ADR» и «adr» сделали бы ссылку темы делом случая.
    """
    problems = []
    ids: set[str] = set()
    owners: dict[str, str] = {}
    for term in data.glossary:
        if term.id in ids:
            problems.append(f"словарь: id {term.id} повторяется")
        ids.add(term.id)
        for name in dict.fromkeys(fold_name(name) for name in term.names):
            owner = owners.get(name)
            if owner is not None:
                problems.append(
                    f"словарь: имя «{name}» есть и у понятия {owner}, и у {term.id}"
                    " — одно из них лишнее или это синоним одного понятия"
                )
            else:
                owners[name] = term.id
    return problems


def _glossary_refers_to_what_exists(data: ClubData) -> list[str]:
    """Главы понятия есть в книгах клуба, связанные понятия — в словаре."""
    problems = []
    ids = {term.id for term in data.glossary}
    for term in data.glossary:
        for reference in term.chapters:
            book = data.book(reference.book_id)
            if book is None:
                problems.append(
                    f"словарь, понятие {term.id}: глава из книги {reference.book_id}, "
                    "которой нет в данных клуба"
                )
            elif book.chapter(reference.number) is None:
                problems.append(
                    f"словарь, понятие {term.id}: глава {reference.number}, "
                    f"а в книге {book.id} глав {len(book.chapters)}"
                )
        for related in term.related:
            if related == term.id:
                problems.append(f"словарь, понятие {term.id}: связано само с собой")
            elif related not in ids:
                problems.append(
                    f"словарь, понятие {term.id}: связано с {related}, "
                    "а такого понятия в словаре нет"
                )
    return problems

