# Кабанья Читальня — сайт клуба

Сайт IT-книжного клуба: что читаем, когда встреча, что уже прошло и что клуб
произвёл. Версия только для чтения — входа для участников нет, данные правятся
в файле.

## Как запустить

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"   # Linux/macOS: .venv/bin/python
git submodule update --init vendor/tyzharchitector

.venv/Scripts/python -m uvicorn app.web.asgi:app --reload
```

Открыть http://127.0.0.1:8000

Рабочий режим — та же команда без `--reload`:

```bash
.venv/Scripts/python -m uvicorn app.web.asgi:app --host 0.0.0.0 --port 8000
```

Путь к данным переопределяется переменной `CLUB_DATA`.

## Выгрузка в статику

```bash
PYTHONPATH=. .venv/Scripts/python -m app.web.export public
```

Кладёт сайт в `public/`: каждый адрес — папка с `index.html`, рядом `static/` и
`game/`. Отдаётся любым статическим хостингом.

Посмотреть выгрузку:

```bash
cd public && python -m http.server 8090
```

Если сайт живёт не в корне домена, а в папке — как страница проекта на GitHub
Pages, — префикс задаётся переменной `SITE_BASE`, иначе абсолютные ссылки уедут
в корень чужого сайта:

```bash
MSYS_NO_PATHCONV=1 SITE_BASE=/bookclub_web python -m app.web.export public
```

`MSYS_NO_PATHCONV=1` нужен только в Git Bash на Windows — см. `PITFALLS.md`.

## Выкатка на GitHub Pages

`.github/workflows/pages.yml` собирает и публикует сайт при каждом push в `main`:
выкачивает подмодуль с игрой, ставит зависимости, прогоняет тесты и выгружает
сайт с префиксом по имени репозитория. Перед первой выкаткой в настройках
репозитория нужно включить **Settings → Pages → Source: GitHub Actions**.

## Тесты

```bash
.venv/Scripts/python -m pytest
```

Проверка вёрстки на узком экране поднимает Chromium через Playwright:

```bash
.venv/Scripts/python -m playwright install chromium
```

## Что где лежит

```
app/core/     ядро: модель клуба и вычисления. Без HTTP, шаблонов и YAML
app/data/     чтение файла данных и проверка инвариантов
app/web/      маршруты, шаблоны, оформление
data/         данные клуба (club.yaml) и описание формата
vendor/       чужой код: игра-разминка подмодулем, закреплённой версией
tests/        тесты; ядро проверяется напрямую, страницы — через клиент
```

Граница «ядро — рендер» проведена намеренно: поверх ядра позже лягут генерация
картинок-анонсов и телеграм-бот, и переписывать ради них рендер не придётся.
Проверка границы — в `tests/test_boundaries.py`: ядро не должно тянуть ни
веб-фреймворк, ни шаблоны, ни YAML.

## Данные клуба

Формат описан в [`data/README.md`](data/README.md). Коротко: три раздела —
`club`, `books`, `meetings`. Книга хранит оглавление, встреча перечисляет
разобранные главы с отметкой «закрыли / перенесли / ещё не разбирали».

Вычисляемое в данных не хранится: номер встречи, пройденные главы, число встреч
по книге, темп и каталог понятий выводятся из встреч каждый раз заново.

Конспекты остаются в [Shvechkova/summary](https://github.com/Shvechkova/summary):
сайт хранит адреса, а не тексты.

## Грабли

Неочевидное, что уже стоило времени, — в [`PITFALLS.md`](PITFALLS.md).
