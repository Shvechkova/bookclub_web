# Tasks

## 1. Номер счётчика из окружения

- [x] 1.1 Написать в `tests/test_seo.py` тесты на `seo.metrika_id_from_env`: `{"YANDEX_METRIKA_ID": "114153922"}` → `"114153922"`, значение с пробелами по краям обрезается, пустое, из пробелов и нецифровое (`abc"`) → `None`; убедиться, что тесты падают
- [x] 1.2 Добавить `metrika_id_from_env` в `app/web/seo.py`; тесты из 1.1 проходят

## 2. Код счётчика на страницах

- [x] 2.1 Написать в `tests/test_seo.py` тесты страниц: с `metrika_id="114153922"` на `/`, `/about` и на странице «не найдено» есть `mc.yandex.ru/metrika/tag.js?id=114153922`, `ym(114153922, 'init'` и картинка `mc.yandex.ru/watch/114153922` в `<noscript>`; без номера строки `mc.yandex.ru` нет; убедиться, что тесты падают
- [x] 2.2 Добавить параметр `metrika_id` в `create_app` (`app/web/app.py`) и передать его в шаблоны рядом с `verification`
- [x] 2.3 Вставить код счётчика в `app/web/templates/base.html` под условием `{% if metrika_id %}`: скрипт в конце `<head>`, `<noscript>` первым в `<body>`; тесты из 2.1 проходят
- [x] 2.4 Прокинуть номер в `app/web/asgi.py` и `app/web/export.py` (параметр выгрузки и чтение из `os.environ`); добавить в `tests/test_export.py` проверку, что выгрузка с номером кладёт код счётчика в `404.html`, тест проходит

## 3. Выкатка и документация

- [x] 3.1 Добавить `YANDEX_METRIKA_ID: ${{ vars.YANDEX_METRIKA_ID }}` и строку комментария в шаг «Выгрузить сайт» в `.github/workflows/pages.yml`; проверить локально: `YANDEX_METRIKA_ID=114153922 python -m app.web.export <папка>` даёт `index.html` с кодом счётчика, а без переменной — без него
- [x] 3.2 Дописать в `README.md` раздел «Счётчик Яндекс.Метрики»: переменная, где её завести, как проверить счётчик (`?_ym_debug=2`), как выключить вебвизор
- [x] 3.3 Прогнать весь `pytest` — зелёный

## Workflow follow-up

- После выкатки завести переменную репозитория `YANDEX_METRIKA_ID=114153922` (Settings → Secrets and variables → Actions → Variables) и перезапустить выкатку — это делает владелец репозитория.
- Проверить в Метрике, что счётчик на `kabanya-chitalnya.ru` отвечает.
