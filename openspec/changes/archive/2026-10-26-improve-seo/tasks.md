# Tasks

## 1. Заголовки и описания

- [x] 1.1 `seo.fit` и заголовки страниц (`home_title`, `history_title`, `glossary_title`, `about_title`, `book_title`, `meeting_title`) — маршруты передают `title`, блоки `title` из шаблонов убраны; проверка: `tests/test_seo.py` — «Две встречи с одним номером», «Длинное название книги», заголовок главной называет город, `tests/test_pages.py` и `tests/test_pages_glossary.py` на новые заголовки разделов
- [x] 1.2 Описания из данных: главная со слотом и площадкой, встреча с городом и первой фразой итогов или анонса, книга со статусом, словарь с числом понятий; проверка: `tests/test_seo.py` — описания не длиннее 160 знаков, у каждой страницы своё
- [x] 1.3 Уникальность по всей выгрузке; проверка: `tests/test_export.py` — «Вся выгрузка»: заголовки и описания всех страниц попарно различны

## 2. Канон и карточка

- [x] 2.1 `seo.page_url`: канон, `og:url`, адреса в разметке и карте сайта со слешем; проверка: `tests/test_seo.py` — «Канон без переадресации», `tests/test_export.py` — карта сайта
- [x] 2.2 `og:type` по странице, `og:image:width/height/alt`, карточка клуба `static/og-card.jpg` 1200×630 по умолчанию; проверка: `tests/test_seo.py` — «Тип страницы в карточке», «У встречи картинки нет», размеры афиши 1080×1350, файл карточки не больше 300 КБ

## 3. schema.org

- [x] 3.1 `Organization` с адресом, городом и `sameAs` только из чата клуба; `WebSite` на главной; проверка: `tests/test_seo.py` — «Площадка — не клуб», `WebSite` только на главной
- [x] 3.2 `Event`: пояс клуба через `zoneinfo` (+ `tzdata` в зависимостях), конец по продолжительности, `PostalAddress`, `offers`, `image`, `workFeatured`; проверка: `tests/test_seo.py` — «Событие с часовым поясом», «Встреча размечена как очное событие»
- [x] 3.3 `Book`, `DefinedTermSet`, `BreadcrumbList`; проверка: `tests/test_seo.py` — «Понятия словаря», «Хлебные крошки книги», книга с авторами
- [x] 3.4 Каждый блок JSON-LD разбирается как JSON; проверка: `tests/test_export.py` — все блоки всех выгруженных страниц проходят `json.loads` и несут `@context` и `@type`

## 4. 404, иконки, подтверждение прав

- [x] 4.1 Шаблон `not_found.html`, обработчик 404, `404.html` в выгрузке, `noindex`, не в карте сайта; проверка: `tests/test_seo.py` — «Опечатка в адресе», `tests/test_export.py` — «Выгрузка страницы 404» и ссылки из него, `noindex` только на 404
- [x] 4.2 Иконки в `static/`, `favicon.ico` в корне выгрузки и маршрут `/favicon.ico`, манифест `manifest.webmanifest` из данных, `theme-color`; проверка: `tests/test_seo.py` — «Иконка во вкладке», манифест называет клуб и иконки 192 и 512, `tests/test_export.py` — файлы на месте
- [x] 4.3 `verification` в `create_app`, `seo.verification_from_env`, переменные в `.github/workflows/pages.yml` и `README.md`; проверка: `tests/test_seo.py` — «Задан код Яндекса», без переменных тегов нет

## 5. Проверка целиком

- [x] 5.1 Полный `pytest`, `openspec validate improve-seo --strict`, выгрузка с `SITE_URL`, `docker compose up -d --build`; проверка: тесты зелёные, `http://127.0.0.1:8737/` отвечает 200, `404.html`, `sitemap.xml`, `robots.txt` в выгрузке
