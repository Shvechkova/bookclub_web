"""Заводит в счётчике Яндекс.Метрики цели, которые отправляет сайт.

Цели — «JavaScript-событие»: ссылка с `data-goal="<id>"` при клике шлёт
`reachGoal` с этим идентификатором (см. `app/web/templates/base.html`).
Скрипт читает цели счётчика и создаёт только недостающие, поэтому запускать
его можно сколько угодно раз.

Запуск:

    YM_TOKEN=... python scripts/metrika_goals.py [номер_счётчика]

Номер берётся из аргумента, иначе из `YANDEX_METRIKA_ID`. Токен — OAuth-токен
с правом `metrika:write`; он читается только из `YM_TOKEN` и не печатается.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api-metrika.yandex.net/management/v1/counter/{counter}/goals"

# Идентификатор цели на сайте → название в кабинете Метрики.
GOALS = {
    "calendar": "Добавили встречу в календарь",
    "chat": "Перешли в чат читальни",
    "notes": "Открыли конспект",
    "warmup": "Нажали «Играть» в разминке",
}


def _request(url: str, token: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method="POST" if body is not None else "GET",
        headers={"Authorization": f"OAuth {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def existing_goal_ids(goals: list[dict]) -> set[str]:
    """Идентификаторы событий, на которые цели уже заведены."""
    found = set()
    for goal in goals:
        if goal.get("type") != "action":
            continue
        for condition in goal.get("conditions") or []:
            if condition.get("type") == "exact" and condition.get("url"):
                found.add(condition["url"])
    return found


def main(argv: list[str]) -> int:
    token = os.environ.get("YM_TOKEN", "").strip()
    counter = (argv[1] if len(argv) > 1 else os.environ.get("YANDEX_METRIKA_ID", "")).strip()
    if not token:
        print("Нет токена: задайте переменную YM_TOKEN", file=sys.stderr)
        return 2
    if not counter.isdigit():
        print("Нет номера счётчика: аргументом или в YANDEX_METRIKA_ID", file=sys.stderr)
        return 2

    url = API.format(counter=counter)
    try:
        present = existing_goal_ids(_request(url, token).get("goals", []))
        created = []
        for goal_id, name in GOALS.items():
            if goal_id in present:
                print(f"есть: {goal_id}")
                continue
            body = {
                "goal": {
                    "name": name,
                    "type": "action",
                    "conditions": [{"type": "exact", "url": goal_id}],
                }
            }
            made = _request(url, token, body)["goal"]
            created.append(goal_id)
            print(f"создана: {goal_id} (№ {made.get('id')})")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:300]
        print(f"Метрика ответила {error.code}: {detail}", file=sys.stderr)
        if error.code == 403:
            print("У токена нет права metrika:write — заведите цели в кабинете руками.", file=sys.stderr)
        return 1

    print(f"готово: создано {len(created)}, уже было {len(GOALS) - len(created)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
