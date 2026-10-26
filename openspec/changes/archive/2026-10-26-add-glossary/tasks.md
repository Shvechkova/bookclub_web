# Tasks

## 1. Данные словаря

- [x] 1.1 Модель `Term`, `TermChapter`, `ClubData.glossary`; загрузчик читает соседний `glossary*.yaml` или путь из аргумента, нет файла — пустой словарь, неверная форма — `DataError`; проверка: `tests/test_glossary_loading.py` (файл есть, файла нет, нет определения, неверный id, не список)
- [x] 1.2 Проверки словаря в `validation.py`: повтор id, названия, синонима; неизвестная книга; глава вне книги; связь на неизвестное понятие и на себя; проверка: `tests/test_glossary_loading.py`, по тесту на каждую ошибку
- [x] 1.3 Убрать `club.topic_notes` из модели, загрузчика, проверки и образца, поле в данных — ошибка с подсказкой; проверка: `tests/test_loading.py`, `tests/test_validation.py`
- [x] 1.4 `data/glossary.example.yaml`, раздел словаря в `data/README.md`; проверка: образец данных грузится вместе со словарём (`tests/test_glossary_loading.py`)

## 2. Ядро

- [x] 2.1 `term_for`, `glossary_index`, `term_chapters`, `related_of`, `TopicEntry.term`; проверка: `tests/test_core_glossary.py` (синоним и регистр, «ё», порядок букв кириллица → латиница, подпись и адрес главы, глава без конспекта, связанные), `tests/test_core_feed.py`, `tests/test_core_showcase.py`

## 3. Сайт

- [x] 3.1 Страница `/glossary`: заголовок, пояснение, указатель, буквы, карточки с якорями, статья, главы, связи, пустое состояние; пункт «Словарь» в шапке; описание для поиска; выгрузка и карта сайта; проверка: `tests/test_pages_glossary.py`, `tests/test_pages.py` (четыре раздела), `tests/test_export.py` (файл `/glossary` и внутренние ссылки), `tests/test_seo.py`
- [x] 3.2 Темы на главной и на странице встречи ведут в словарь с подсказкой; проверка: `tests/test_pages_glossary.py` (ссылка на якорь, `aria-describedby`, текст подсказки, тема без понятия текстом), `tests/test_pages_home.py`, `tests/test_pages.py`
- [x] 3.3 Стили словаря и подсказки; проверка: `tests/test_layout.py` — нет горизонтальной прокрутки на `/glossary` и на главной с открытой подсказкой на 360 и 1280, подсказка в пределах окна

## 4. Наполнение

- [x] 4.1 `data/glossary.yaml`: темы встреч и статьи `topics/` репозитория конспектов, определения из конспектов; адреса конспектов глав Брукса в `data/club.yaml`; проверка: рабочие данные грузятся (`tests/test_loading.py`), каждая тема встреч находит понятие (`tests/test_glossary_loading.py`)

## 5. Скилл

- [x] 5.1 `.claude/skills/club-ingest/SKILL.md`; проверка: фронтматтер с `name` и `description`, файл короче 150 строк, все пути и команды в нём существуют

## 6. Проверка целиком

- [x] 6.1 Полный `pytest`, `python -m app.web.export public`, снимки `/glossary` на 1280 и 360 и подсказки на главной; проверка: тесты зелёные, выгрузка без ошибок, на снимках нет наползаний и прокрутки вбок
- [x] 6.2 `openspec validate add-glossary --strict` без ошибок

## Workflow follow-up

- Архивировать изменение после проверки пользователем.
