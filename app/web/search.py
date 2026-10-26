"""Текст понятия для поиска по словарю.

Ищет скрипт в браузере: у статической выгрузки нет сервера. Сервер только
кладёт в карточку уже нормализованный текст, чтобы скрипту не пришлось
разбирать разметку. Те же правила повторяет `static/glossary-search.js` для
запроса: строчные буквы, «ё» как «е», всё, что не буква и не цифра, — пробел.
"""

from __future__ import annotations

import re

from app.core.models import Term

_NOT_A_WORD = re.compile(r"[\W_]+")

# Разделитель названий в `data-names`: после нормализации его в тексте нет.
NAMES_SEPARATOR = "|"


def normalize(text: str) -> str:
    """Строчные буквы, «ё» → «е», знаки препинания и лишние пробелы — один пробел."""
    folded = text.lower().replace("ё", "е")
    return _NOT_A_WORD.sub(" ", folded).strip()


def search_text(term: Term) -> str:
    """Всё, по чему ищется понятие: название, синонимы, определение."""
    return normalize(" ".join((term.name, *term.aliases, term.summary)))


def search_names(term: Term) -> str:
    """Название и синонимы порознь: по ним скрипт ставит понятие выше в выдаче."""
    return NAMES_SEPARATOR.join(normalize(name) for name in (term.name, *term.aliases))
