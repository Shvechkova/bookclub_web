"""Куда открывается ссылка.

Конспекты лежат на GitHub, чаты и канал — в телеграме: человек уходит туда
почитать или написать и возвращается на сайт клуба. Такие ссылки открываются в
новой вкладке, чтобы сайт не терялся за ними. Остальные ведут себя как обычно:
новая вкладка без спроса раздражает, и пользователь назвал только эти две.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from markupsafe import Markup

ELSEWHERE = ("github.com", "t.me")


def opens_elsewhere(url: str | None) -> bool:
    """Ведёт ли адрес на GitHub или в телеграм, включая их поддомены."""
    if not url:
        return False
    host = (urlsplit(url).hostname or "").lower()
    return any(host == known or host.endswith("." + known) for known in ELSEWHERE)


def new_tab(url: str | None) -> Markup:
    """Атрибуты ссылки для шаблона: новая вкладка или ничего.

    `noopener` не даёт открытой странице дотянуться до вкладки клуба.
    """
    return Markup(' target="_blank" rel="noopener"') if opens_elsewhere(url) else Markup("")
