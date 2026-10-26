# Tasks

## 1. Ядро: номер и лента

- [x] 1.1 `ClubView.numbered_meetings`: номер — порядковый внутри книги с единицы, встречи без книги — свой ряд; проверка: `tests/test_core_chapters.py::test_each_book_counts_its_meetings_from_one`, `::test_meetings_without_a_book_are_counted_among_themselves`, `::test_meeting_number_comes_from_the_order_of_dates`
- [x] 1.2 `ClubView.history`: книги свежими сверху, встречи внутри отрезка по порядку; проверка: `tests/test_core_feed.py::test_books_are_segments_and_their_meetings_sit_inside`, `tests/test_pages.py::test_history_groups_meetings_under_their_books`

## 2. Номер на страницах

- [x] 2.1 Наклейка «Начинаем новую книгу» с «встреча #1» на главной и странице встречи; проверка: `tests/test_brand.py::test_the_first_meeting_of_a_book_wears_a_sticker`, `::test_a_meeting_in_the_middle_of_a_book_has_no_sticker`, `::test_a_meeting_without_a_book_has_no_sticker`

## 3. Состояние книги

- [x] 3.1 Печать `#stamp` один раз в `base.html`, макрос `cover` ставит её на обложку закрытой книги, `aria-hidden`; приглушённые названия закрытых книг (`segment--closed`, «Уже прочитали»); проверка: `tests/test_pages_cover.py::test_a_closed_book_gets_the_club_stamp_on_its_cover`, `::test_a_book_being_read_has_no_stamp`, `::test_a_closed_book_is_marked_in_the_history_feed`
- [x] 3.2 Печать без горизонтальной прокрутки на 360 точках, в сетке «Уже прочитали» внутри обложки; проверка: `tests/test_layout.py::test_finished_books_fit_a_narrow_screen`, `::test_history_covers_fit_a_narrow_screen`, `::test_no_horizontal_scrolling_on_a_narrow_screen`
- [x] 3.3 Макрос `book_status`: билет «Читаем сейчас · билет» с корешком «встреча №N», без встреч — без корешка, остальные состояния — плашки; проверка: `tests/test_pages_cover.py::test_the_book_being_read_wears_a_library_ticket_with_a_torn_stub`, `::test_other_statuses_stay_plain_plates`, `tests/test_brand.py::test_each_book_status_gets_its_own_badge_class`

## 4. Главная и данные

- [x] 4.1 Манифест делится на строки `span.hero-line` по переводу строки в данных; проверка: `tests/test_pages_home.py::test_the_home_page_opens_with_the_manifesto`, `tests/test_layout.py::test_the_manifesto_takes_two_lines_on_a_wide_screen`
- [x] 4.2 `data/club.yaml`: дескриптор «IT книжный клуб · Самара», бегущая строка «всегда живые встречи», убран «Кворум три человека…», убран спор «Мой код» у 07.10, обложка и авторы книги Клеппмана, манифест в две строки; проверка: рабочие данные загружаются (`tests/test_loading.py::test_loads_club_details`), `grep` по `data/club.yaml` не находит «Кворум» и «Мой код»

## 5. «Полка» вместо «Истории», каталог понятий убран

- [x] 5.1 Пункт шапки, `<h1>` и `<title>` ленты — «Полка», адрес `/history` и `section="history"` прежние, комментарий в `app.py`; проверка: `tests/test_pages.py::test_the_site_has_three_sections_and_the_feed_is_called_shelf`, `tests/test_pages_meeting.py::test_a_past_meeting_belongs_to_the_history_section`, `::test_a_book_page_belongs_to_the_history_section`
- [x] 5.2 Убраны маршруты `/shelf` и `/shelf/topics`, шаблоны `shelf.html` и `topics.html`, `TOPICS_ON_SHELF`, адреса в `export.py`, `seo.shelf_description` и `seo.topics_description`; `ClubView.topics()` оставлен для заставки; проверка: `tests/test_pages.py::test_the_concept_catalogue_section_is_gone`, `tests/test_export.py::test_export_writes_a_file_for_every_address`, `::test_every_internal_link_leads_to_a_file_that_exists`, `tests/test_seo.py::test_no_two_sections_share_one_description`
- [x] 5.3 Темы на странице встречи ведут на конспект понятия или стоят текстом; проверка: `tests/test_pages.py::test_meeting_topics_link_to_their_notes_and_nowhere_else`, `tests/test_pages_home.py::test_topic_notes_open_in_a_new_tab`
- [x] 5.4 Игра остаётся на `/game/`, на неё ведёт плашка главной; проверка: `tests/test_game.py::test_the_home_page_sends_the_visitor_to_the_game_on_this_site`, `::test_the_game_does_not_depend_on_club_data`
- [x] 5.5 В шапке три раздела, бургер раскрывает три; проверка: `tests/test_layout.py::test_the_sections_stand_on_one_line_with_the_logo_on_a_wide_screen`, `::test_the_sections_hide_behind_a_burger_on_a_narrow_screen`, `tests/test_pages.py::test_every_page_carries_the_same_three_sections` (проверяет и отсутствие `/shelf`)
- [x] 5.6 Тесты прежней «Полки» и каталога убраны из `tests/test_pages_shelf.py`, списки адресов обновлены в `test_brand.py`, `test_layout.py`, `test_pages.py`, `test_seo.py`, `test_export.py`; проверка: полный `pytest` зелёный

## 7. «О клубе»

- [x] 7.1 Модель `Card(label, text)`, поля клуба `about_title`, `about_hand`, `facts`, `rules`; загрузчик `_cards` отвергает карточку без `label` или `text`; заполнены `data/club.yaml`, `data/club.example.yaml`, поля описаны в `data/README.md`; проверка: `tests/test_pages_about.py::test_a_card_without_text_is_rejected`, `::test_the_example_data_fills_the_about_page`
- [x] 7.2 Заставка `.about-head`: «О клубе · с {since}», заголовок с запасным «О клубе», рукописная строка по строкам, лид, отражённый кабан с `alt=""`; проверка: `tests/test_pages_about.py::test_the_about_page_opens_with_its_title_and_the_boar`, `::test_without_the_new_fields_the_page_falls_back_to_plain_text`, `tests/test_layout.py::test_no_horizontal_scrolling_on_a_narrow_screen` (включает `/about`)
- [x] 7.3 Карточки фактов вместо абзацев после первого, карточки порядка встречи вместо списка `routine`; проверка: `tests/test_pages_about.py::test_facts_replace_the_rest_of_the_about_text`, `::test_facts_and_rules_are_cards_in_order`, `::test_without_the_new_fields_the_page_falls_back_to_plain_text`
- [x] 7.4 «Где и когда» карточкой, «Куда писать»: чат площадки, ветка клуба, канал, сайт, затем «Чат читальни» с пометкой «— после первого посещения»; перечень форматов убран со страницы, `ClubView.formats()` оставлен; проверка: `tests/test_pages_about.py::test_contacts_lead_to_the_space_chat_first`, `::test_the_about_page_no_longer_lists_formats`, тесты ядра на форматы зелёные
- [x] 7.5 «Где и когда»: площадка — ссылка `about-venue` на сайт площадки, адрес — ссылка `about-map` на карту с розовым значком места (встроенный SVG, `aria-hidden`), обе по правилу `new_tab` (в той же вкладке); необязательное поле `place.map` в `Place` (`app/core/models.py`), загрузчике (`app/data/loader.py`) и `data/README.md`; проверка: `tests/test_pages_about.py::test_the_venue_links_to_the_space_site`, `::test_the_address_links_to_the_map_with_a_pin`, `::test_without_a_map_the_address_is_plain_text`, `::test_the_map_link_is_loaded_from_the_data`
- [x] 7.6 Чат клуба подписан «Чат читальни» и стоит последним в «Куда писать», после «Сайт s4m.space», с пометкой «— после первого посещения»; в подвале — «чат читальни»; проверка: `tests/test_pages_about.py::test_the_club_chat_is_offered_after_the_first_visit`, `::test_the_footer_calls_it_the_reading_room_chat`
- [x] 7.7 Данные: споры «Мидлы и джуны» и «Регрессионные тесты» у встречи 07.10 заменены на «Waterfall или Agile?», тексты карточек «О клубе» переписаны, третье правило — «Неси свой опыт»; проверка: `tests/test_loading.py::test_loads_club_details`

## 8. Номер в галерее

- [x] 8.1 Кнопки «Как это было» показывают «встреча #N» (номер по книге) между датой и заголовком; проверка: `tests/test_pages_home.py::test_gallery_tabs_carry_the_meeting_number_within_the_book`

## 6. Проверка целиком

- [x] 6.1 Полный набор тестов, экспорт и контейнер; проверка: `pytest` зелёный, `PYTHONPATH=. python -m app.web.export public` без ошибок, `docker compose up -d --build`, `/` и `/history` отвечают 200, `/shelf` — 404, снимки шапки на 1280 и 360 точках (меню раскрыто)
- [x] 6.2 `openspec validate polish-history-and-numbering --strict` без ошибок

## Workflow follow-up

- Архивировать `add-meeting-recaps`, `improve-home-and-navigation` и `enrich-home-showcase` раньше этого изменения: оно меняет требования, которые вводят они.
