"""Выгрузка сайта в статику.

Сайт только читается, интерактива на нём нет, поэтому те же шаблоны можно
разложить в файлы и отдавать любым статическим хостингом. Приложение при этом
остаётся: оно и рендерит страницы при выгрузке, и служит сервером для разработки,
а когда появится админка — снова станет обычным бэкендом.

Каждый адрес кладётся папкой с `index.html`: на статике «/history» работает
только так.

    python -m app.web.export public
"""

from __future__ import annotations

import os
import shutil
import sys
from datetime import date as Day
from pathlib import Path

from app.core.view import ClubView
from app.web.app import GAME_DIR, STATIC, create_app


def page_paths(view: ClubView) -> list[str]:
    """Все адреса сайта: постоянные разделы плюс встречи и книги."""
    paths = ["/", "/history", "/about"]
    paths += [f"/meetings/{meeting.id}" for meeting in view.data.meetings]
    paths += [f"/books/{book.id}" for book in view.data.books]
    return paths


def export_site(
    view: ClubView,
    out_dir: str | Path,
    today: Day | None = None,
    base: str = "",
    origin: str = "",
) -> list[Path]:
    """Раскладывает сайт в папку. Возвращает список записанных файлов.

    `base` — папка, в которой сайт будет жить на хостинге. Файлы всегда
    раскладываются одинаково, меняются только ссылки внутри страниц.

    `origin` — схема и домен сайта. Задан — рядом появляются `sitemap.xml` и
    `robots.txt`; не задан — их нет, собирать абсолютные адреса не из чего.
    """
    from fastapi.testclient import TestClient

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    day = today or Day.today()
    client = TestClient(create_app(view=view, today=lambda: day, base=base, origin=origin))

    written: list[Path] = []
    for path in page_paths(view):
        response = client.get(path)
        if response.status_code != 200:
            raise RuntimeError(f"{path} ответил {response.status_code}, выгрузка прервана")
        target = out / "index.html" if path == "/" else out / path.strip("/") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(response.text, encoding="utf-8")
        written.append(target)

    _copy_tree(STATIC, out / "static")
    if (GAME_DIR / "index.html").exists():
        _copy_tree(GAME_DIR, out / "game", skip={".git", "test", "node_modules"})

    written += _write_sitemap(out, page_paths(view), origin, base)

    # GitHub Pages иначе прячет пути, начинающиеся с подчёркивания.
    (out / ".nojekyll").write_text("", encoding="utf-8")
    return written


def _write_sitemap(out: Path, paths: list[str], origin: str, base: str) -> list[Path]:
    """Карта сайта и `robots.txt` — только при заданном адресе сайта.

    Оба файла состоят из абсолютных ссылок целиком, поэтому без адреса их нечем
    наполнить: пустая карта увела бы поисковик вернее, чем её отсутствие.
    """
    origin = origin.rstrip("/")
    if not origin:
        return []

    folder = base.strip("/")
    prefix = f"/{folder}" if folder else ""
    locations = "\n".join(f"  <url><loc>{origin}{prefix}{path}</loc></url>" for path in paths)
    sitemap = out / "sitemap.xml"
    sitemap.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{locations}\n"
        "</urlset>\n",
        encoding="utf-8",
    )
    robots = out / "robots.txt"
    robots.write_text(
        f"User-agent: *\nAllow: /\nSitemap: {origin}{prefix}/sitemap.xml\n",
        encoding="utf-8",
    )
    return [sitemap, robots]


def _copy_tree(source: Path, target: Path, skip: set[str] | None = None) -> None:
    skip = skip or set()
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(
        source,
        target,
        ignore=lambda _directory, names: {name for name in names if name in skip},
    )


def main(argv: list[str]) -> int:
    from app.web.app import default_view

    out = argv[1] if len(argv) > 1 else "public"
    base = argv[2] if len(argv) > 2 else os.environ.get("SITE_BASE", "")
    origin = os.environ.get("SITE_URL", "")
    written = export_site(default_view(), out, base=base, origin=origin)
    print(f"выгружено файлов: {len(written)} в {Path(out).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
