"""Загрузка файла данных клуба в объекты модели."""

from datetime import date
from pathlib import Path

import pytest
import yaml

from app.core.models import BookStatus, ChapterOutcome
from app.data.loader import DataError, load_club_data

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "data" / "club.example.yaml"
CLUB = ROOT / "data" / "club.yaml"
STATIC = ROOT / "app" / "web" / "static"


def example():
    return load_club_data(EXAMPLE)


def test_loads_club_details():
    club = example().club

    assert club.name == "Кабанья Читальня"
    assert club.descriptor == "IT книжный клуб"
    assert club.slot == "среда, раз в две недели"
    assert club.place.short == "площадка клуба, комната 413"
    assert club.place.full == "Дом77, Ленинградская 77, 4 этаж, комната 413, Самара"
    assert club.duration_minutes == 90
    assert club.timezone == "Europe/Samara"
    assert len(club.about) == 3
    assert len(club.routine) == 3


def test_loads_books_in_order_with_chapters():
    books = example().books

    assert [book.number for book in books] == [1, 2, 3, 4, 5]
    reading = example().book("reading-example")
    assert reading.status is BookStatus.READING
    assert [chapter.number for chapter in reading.chapters] == [1, 2, 3, 4, 5]
    assert reading.chapters[0].title == "Глава первая"


def test_chapter_notes_url_is_optional():
    archive = example().book("archive-example")

    assert archive.chapters[0].notes_url == "https://example.org/notes/archive/1"
    assert archive.chapters[1].notes_url is None


def test_taken_chapters_default_to_the_whole_book():
    data = example()

    assert data.book("reading-example").taken_numbers == (1, 3, 5)
    assert data.book("closed-example").taken_numbers == (1, 2, 3)


def test_loads_meeting_chapters_with_outcomes():
    meeting = example().meeting("m-2026-06-17")

    assert meeting.book_id == "closed-example"
    assert [(c.number, c.outcome) for c in meeting.chapters] == [
        (3, ChapterOutcome.CARRIED)
    ]


def test_meeting_without_a_book_keeps_its_own_title():
    meeting = example().meeting("m-2026-07-29")

    assert meeting.book_id is None
    assert meeting.title == "Голосование за следующую книгу"
    assert meeting.chapters == ()
    assert meeting.format is None


def test_meeting_inherits_time_and_place_from_the_club():
    meeting = example().meeting("m-2026-06-03")

    assert meeting.date == date(2026, 6, 3)
    assert meeting.time == "19:30"
    assert meeting.place.short == "площадка клуба, комната 413"


def test_loads_outcome_and_quote():
    meeting = example().meeting("m-2026-06-03")

    assert meeting.outcome is not None
    assert meeting.outcome.argued == "Дольше всего спорили про вторую."
    assert meeting.outcome.quote is not None
    assert meeting.outcome.quote.chapter == 2
    assert meeting.topics == ("Закон Конвея",)


FULL_OUTCOME = {
    "agreed": "Согласились, что оценки врут.",
    "lead": "Разобрали три главы и почти все спорили.",
    "by_chapter": [
        {"chapters": [1], "heading": "Начало", "text": "Про начало."},
        {"chapters": [2], "heading": "Середина", "text": "Про середину."},
        {"heading": "Бюджеты", "text": "Про бюджеты."},
        {"chapters": [2, 3], "text": "Про переход."},
        {"chapters": [3], "heading": "Конец", "text": "Про конец."},
    ],
    "debates": [
        {"heading": "Блок-схемы", "text": "Нужны ли они."},
        {"heading": "Документация", "text": "Кто её пишет."},
        {"text": "Спор без заголовка."},
    ],
    "aside": "Заодно уходили в код-ревью и дежурства.",
    "verdict": "Книга старая, а проблемы те же.",
}


def test_a_full_outcome_loads_every_part_in_the_written_order(tmp_path):
    outcome = _with_outcome(tmp_path, FULL_OUTCOME).meeting("m-2026-06-03").outcome

    assert outcome.agreed == "Согласились, что оценки врут."
    assert outcome.lead == "Разобрали три главы и почти все спорили."
    assert [item.heading for item in outcome.by_chapter] == [
        "Начало",
        "Середина",
        "Бюджеты",
        None,
        "Конец",
    ]
    assert outcome.by_chapter[3].chapters == (2, 3)
    assert outcome.by_chapter[3].text == "Про переход."
    assert [item.text for item in outcome.debates] == [
        "Нужны ли они.",
        "Кто её пишет.",
        "Спор без заголовка.",
    ]
    assert outcome.debates[2].heading is None
    assert outcome.aside == "Заодно уходили в код-ревью и дежурства."
    assert outcome.verdict == "Книга старая, а проблемы те же."


def test_an_outcome_item_without_chapters_loads_without_them(tmp_path):
    outcome = _with_outcome(tmp_path, FULL_OUTCOME).meeting("m-2026-06-03").outcome

    budgets = outcome.by_chapter[2]
    assert budgets.heading == "Бюджеты"
    assert budgets.chapters == ()


def test_an_outcome_of_three_theses_has_an_empty_full_form():
    outcome = example().meeting("m-2026-07-01").outcome

    assert outcome.agreed == "Дожали третью главу и на этом книгу закрыли."
    assert outcome.lead is None
    assert outcome.by_chapter == ()
    assert outcome.debates == ()
    assert outcome.aside is None
    assert outcome.verdict is None


def test_an_outcome_written_only_in_full_form_is_kept(tmp_path):
    """Итоги без трёх тезисов — всё равно итоги: молча пропасть им нельзя."""
    outcome = _with_outcome(tmp_path, {"verdict": "Только общий итог."}).meeting(
        "m-2026-06-03"
    ).outcome

    assert outcome is not None
    assert outcome.verdict == "Только общий итог."


def test_the_example_shows_the_full_form_of_an_outcome():
    outcome = example().meeting("m-2026-06-03").outcome

    assert outcome.lead
    assert outcome.by_chapter[0].chapters == (1,)
    assert any(not item.chapters for item in outcome.by_chapter)
    assert any(item.heading is None for item in outcome.by_chapter)
    assert outcome.debates
    assert outcome.aside
    assert outcome.verdict


def test_an_outcome_item_without_text_is_rejected(tmp_path):
    with pytest.raises(DataError) as error:
        _with_outcome(tmp_path, {"debates": [{"heading": "Блок-схемы"}]})

    assert "m-2026-06-03" in str(error.value)
    assert "text" in str(error.value)


def test_a_meeting_loads_both_images_with_their_captions(tmp_path):
    images = {
        "poster": {"src": "meetings/m-poster.jpg", "alt": "Афиша: главы 8–15"},
        "recap": {"src": "meetings/m-recap.jpg", "alt": "Итоги: оценки врут"},
    }
    meeting = _with_meeting(tmp_path, images=images).meeting("m-2026-06-03")

    assert meeting.poster.src == "meetings/m-poster.jpg"
    assert meeting.poster.alt == "Афиша: главы 8–15"
    assert meeting.recap_card.src == "meetings/m-recap.jpg"
    assert meeting.recap_card.alt == "Итоги: оценки врут"


def test_the_example_meeting_has_a_poster_and_a_recap_card():
    meeting = example().meeting("m-2026-06-03")

    assert meeting.poster.src.startswith("meetings/")
    assert meeting.poster.alt
    assert meeting.recap_card.alt


def test_a_meeting_without_images_has_none():
    meeting = example().meeting("m-2026-06-17")

    assert meeting.poster is None
    assert meeting.recap_card is None


def test_an_image_without_a_caption_is_rejected(tmp_path):
    """Подпись не собирается сама: на афише текст, которого нет больше нигде."""
    with pytest.raises(DataError) as error:
        _with_meeting(tmp_path, images={"poster": {"src": "meetings/m-poster.jpg"}})

    assert "m-2026-06-03" in str(error.value)
    assert "alt" in str(error.value)


def test_an_image_without_an_address_is_rejected(tmp_path):
    with pytest.raises(DataError) as error:
        _with_meeting(tmp_path, images={"recap": {"alt": "Итоги"}})

    assert "m-2026-06-03" in str(error.value)
    assert "src" in str(error.value)


def test_an_unknown_kind_of_image_is_rejected(tmp_path):
    """Опечатка в роли картинки молча оставила бы встречу без неё."""
    with pytest.raises(DataError) as error:
        _with_meeting(
            tmp_path, images={"recap_card": {"src": "meetings/m.jpg", "alt": "Итоги"}}
        )

    assert "recap_card" in str(error.value)


def _with_outcome(tmp_path, outcome):
    return _with_meeting(tmp_path, outcome=outcome)


def _with_meeting(tmp_path, **fields):
    source = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    for meeting in source["meetings"]:
        if meeting["id"] == "m-2026-06-03":
            meeting.update(fields)
    target = tmp_path / "club.yaml"
    target.write_text(yaml.safe_dump(source, allow_unicode=True), encoding="utf-8")
    return load_club_data(target)


def test_loads_format_of_the_second_hour():
    meeting = example().meeting("m-2026-06-03")

    assert meeting.format is not None
    assert meeting.format.name == "Лайтнинги"
    assert meeting.format.note == "пять минут на человека, без слайдов"


def test_loads_the_tagline_that_names_the_city():
    club = example().club

    assert club.tagline == "IT-книжный клуб в Самаре"


def test_loads_the_space_the_club_lives_in():
    space = example().club.space

    assert space.name == "example.space"
    assert space.site == "https://example.space/"
    assert space.channel == "https://t.me/example_channel"
    assert space.chat == "https://t.me/+examplechat"
    assert space.thread == "https://t.me/c/1234567890/1"


def test_a_club_without_a_space_loads_without_one(tmp_path):
    club = _loaded_without(tmp_path, "space").club

    assert club.space is None


def test_about_written_as_one_string_is_rejected(tmp_path):
    """Строка вместо списка разошлась бы на буквы вместо абзацев."""
    source = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    source["club"]["about"] = "Один абзац строкой"
    target = tmp_path / "club.yaml"
    target.write_text(yaml.safe_dump(source, allow_unicode=True), encoding="utf-8")

    with pytest.raises(DataError) as error:
        load_club_data(target)

    assert "about" in str(error.value)


def _loaded_without(tmp_path, key):
    source = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    source["club"].pop(key)
    target = tmp_path / "club.yaml"
    target.write_text(yaml.safe_dump(source, allow_unicode=True), encoding="utf-8")
    return load_club_data(target)


def test_club_data_loads_and_every_cover_points_at_a_file():
    """Рабочие данные грузятся, а прописанные обложки лежат в статике.

    Обложка — путь в данных и файл на диске: разъехаться им нечего стоит, и
    тогда на странице книги останется битая картинка.
    """
    data = load_club_data(CLUB)

    assert data.club.place.full
    for book in data.books:
        if book.cover:
            assert (STATIC / book.cover).is_file(), (
                f"книга {book.id}: обложка {book.cover} не найдена в статике"
            )


def test_club_data_meeting_images_point_at_files():
    """То же для картинок встреч: афиша и карточка итогов лежат в статике."""
    for meeting in load_club_data(CLUB).meetings:
        for image in (meeting.poster, meeting.recap_card):
            if image is not None:
                assert (STATIC / image.src).is_file(), (
                    f"встреча {meeting.id}: картинка {image.src} не найдена в статике"
                )


def test_terms_keep_their_order_and_may_be_absent(tmp_path):
    """Условия прихода — список строк клуба; их отсутствие не ошибка."""
    raw = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    raw["club"]["terms"] = ["Вход свободный", "Без регистраций", "Не прочитал — приходи"]
    with_terms = tmp_path / "with_terms.yaml"
    with_terms.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")

    assert load_club_data(with_terms).club.terms == (
        "Вход свободный",
        "Без регистраций",
        "Не прочитал — приходи",
    )

    raw["club"].pop("terms")
    without = tmp_path / "without_terms.yaml"
    without.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")

    assert load_club_data(without).club.terms == ()


# --- витрина главной: год основания, манифест, короткое название ------------


def _loaded_with(tmp_path, change):
    raw = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    change(raw)
    target = tmp_path / "club.yaml"
    target.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    return load_club_data(target)


def test_loads_the_founding_year_and_the_manifesto():
    club = example().club

    assert club.since == 2023
    assert club.manifesto == "Читаем техническую литературу\nи спорим о ней вслух"


def test_the_founding_year_and_the_manifesto_may_be_absent(tmp_path):
    def drop(raw):
        raw["club"].pop("since")
        raw["club"].pop("manifesto")

    club = _loaded_with(tmp_path, drop).club

    assert club.since is None
    assert club.manifesto is None


def test_a_founding_year_that_is_not_a_number_is_rejected(tmp_path):
    def spoil(raw):
        raw["club"]["since"] = "давно"

    with pytest.raises(DataError, match="since"):
        _loaded_with(tmp_path, spoil)


def test_a_book_may_have_a_short_title():
    data = example()

    assert data.book("reading-example").short_title == "Читаемая"
    assert data.book("closed-example").short_title is None


def _loaded_with_warmup(tmp_path, warmup):
    source = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    source["club"]["warmup"] = warmup
    target = tmp_path / "club.yaml"
    target.write_text(yaml.safe_dump(source, allow_unicode=True), encoding="utf-8")
    return load_club_data(target)


def test_loads_the_warmup_game_with_its_name_lead_and_address(tmp_path):
    warmup = _loaded_with_warmup(
        tmp_path,
        {
            "name": "Тыжархитектор",
            "lead": "Карточный тренажёр по архитектуре.",
            "url": "https://example.github.io/game/",
        },
    ).club.warmup

    assert warmup.name == "Тыжархитектор"
    assert warmup.lead == "Карточный тренажёр по архитектуре."
    assert warmup.url == "https://example.github.io/game/"


def test_a_club_without_a_warmup_loads_without_one(tmp_path):
    assert _loaded_without(tmp_path, "warmup").club.warmup is None


def test_a_warmup_without_an_address_is_rejected_naming_the_field(tmp_path):
    with pytest.raises(DataError) as error:
        _loaded_with_warmup(tmp_path, {"name": "Тыжархитектор", "lead": "Тренажёр."})

    assert "url" in str(error.value)
    assert "warmup" in str(error.value)


def test_a_warmup_written_as_a_string_is_rejected(tmp_path):
    with pytest.raises(DataError) as error:
        _loaded_with_warmup(tmp_path, "https://example.github.io/game/")

    assert "warmup" in str(error.value)


def test_the_example_and_the_club_describe_the_warmup_game():
    for source in (EXAMPLE, CLUB):
        warmup = load_club_data(source).club.warmup

        assert warmup.name == "Тыжархитектор"
        assert warmup.url == "https://shvechkova.github.io/tyzharchitector/"
        assert warmup.lead
