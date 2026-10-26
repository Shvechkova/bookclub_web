"""Человеческие формулировки для страниц.

Это слой представления: даты по-русски, склонения, короткие подписи. Правила
клуба сюда не попадают — они в ядре.
"""

from __future__ import annotations

from datetime import date as Day

MONTHS = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}

WEEKDAYS = (
    "понедельник",
    "вторник",
    "среда",
    "четверг",
    "пятница",
    "суббота",
    "воскресенье",
)

# «Когда?» — винительный падеж с предлогом: «приходи в среду».
ON_WEEKDAYS = (
    "в понедельник",
    "во вторник",
    "в среду",
    "в четверг",
    "в пятницу",
    "в субботу",
    "в воскресенье",
)

STATUS_LABELS = {
    "voting": "голосуем",
    "queued": "в списке",
    "reading": "читаем сейчас",
    "closed": "закрыта",
    "dropped": "дропнули",
}


def day_month(day: Day) -> str:
    """«23 сентября»."""
    return f"{day.day} {MONTHS[day.month]}"


def full_date(day: Day) -> str:
    """«23 сентября 2026»."""
    return f"{day_month(day)} {day.year}"


def weekday(day: Day) -> str:
    return WEEKDAYS[day.weekday()]


def on_weekday(day: Day) -> str:
    """«в среду»."""
    return ON_WEEKDAYS[day.weekday()]


def short_date(day: Day) -> str:
    """«07.10» — как дата стоит на афишах и в подписях карточек."""
    return f"{day.day:02d}.{day.month:02d}"


def status_label(status) -> str:
    return STATUS_LABELS.get(getattr(status, "value", status), str(status))


def plural(count: int, one: str, few: str, many: str) -> str:
    """«1 встреча», «2 встречи», «5 встреч»."""
    tens, hundreds = count % 10, count % 100
    if tens == 1 and hundreds != 11:
        return one
    if 2 <= tens <= 4 and not 12 <= hundreds <= 14:
        return few
    return many


def meetings_count(count: int) -> str:
    return f"{count} {plural(count, 'встреча', 'встречи', 'встреч')}"


def chapters_count(count: int) -> str:
    return f"{count} {plural(count, 'глава', 'главы', 'глав')}"


def chapters_of(count: int) -> str:
    """Родительный падеж после «из»: «из 1 главы», «из 3 глав»."""
    return f"{count} {plural(count, 'главы', 'глав', 'глав')}"


def minutes(count: int) -> str:
    """«90 минут», «31 минута»: длительность хранится числом, склоняем при выводе."""
    tail = count % 100
    if 11 <= tail <= 14:
        word = "минут"
    elif count % 10 == 1:
        word = "минута"
    elif count % 10 in (2, 3, 4):
        word = "минуты"
    else:
        word = "минут"
    return f"{count} {word}"


def chapter_numbers(numbers) -> str:
    """«08», «06–07», «03, 07»: номера глав плашкой, как в оглавлении встречи.

    Тот же разбор, что у `chapter_phrase`, только без слова «глава»: плашка
    стоит перед пунктом итогов, и слово там лишнее.
    """
    numbers = sorted(numbers)
    if not numbers:
        return ""
    if len(numbers) > 1 and numbers[-1] - numbers[0] + 1 == len(numbers):
        return f"{numbers[0]:02d}–{numbers[-1]:02d}"
    return ", ".join(f"{number:02d}" for number in numbers)
