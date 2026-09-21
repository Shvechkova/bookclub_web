"""Проверка границ между слоями.

Ядро клуба не должно знать ни про веб-фреймворк, ни про шаблоны, ни про формат
файла данных. Проверка делается импортом в отдельном процессе: так ловятся и
косвенные зависимости, а не только те, что видно в тексте модуля.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

FORBIDDEN_IN_CORE = ("fastapi", "starlette", "jinja2", "yaml")

ROOT = Path(__file__).resolve().parent.parent


def forbidden_imports(module: str, forbidden: tuple[str, ...] = FORBIDDEN_IN_CORE) -> list[str]:
    """Импортирует модуль в отдельном процессе и возвращает загруженные им запрещённые пакеты."""
    source = (
        "import json, sys;"
        f"__import__({module!r});"
        f"print(json.dumps([name for name in {list(forbidden)!r} if name in sys.modules]))"
    )
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONIOENCODING="utf-8")
    result = subprocess.run(
        [sys.executable, "-c", source],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
        env=env,
    )
    if result.returncode != 0:
        raise AssertionError("не удалось импортировать " + module + ": " + result.stderr)
    return json.loads(result.stdout)
