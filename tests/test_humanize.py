"""Русские формулировки: склонения и даты."""

from datetime import date

from app.web import humanize


def test_meetings_are_counted_with_the_right_ending():
    assert humanize.meetings_count(1) == "1 встреча"
    assert humanize.meetings_count(2) == "2 встречи"
    assert humanize.meetings_count(5) == "5 встреч"
    assert humanize.meetings_count(11) == "11 встреч"
    assert humanize.meetings_count(21) == "21 встреча"


def test_chapters_are_counted_with_the_right_ending():
    assert humanize.chapters_count(1) == "1 глава"
    assert humanize.chapters_count(3) == "3 главы"
    assert humanize.chapters_count(7) == "7 глав"


def test_after_the_word_iz_chapters_take_the_genitive():
    """«Пройдено 2 из 3 глав», а не «из 3 главы»."""
    assert humanize.chapters_of(1) == "1 главы"
    assert humanize.chapters_of(2) == "2 глав"
    assert humanize.chapters_of(3) == "3 глав"
    assert humanize.chapters_of(12) == "12 глав"


def test_dates_are_written_the_russian_way():
    assert humanize.day_month(date(2026, 9, 23)) == "23 сентября"
    assert humanize.full_date(date(2026, 9, 23)) == "23 сентября 2026"
    assert humanize.weekday(date(2026, 9, 23)) == "среда"


def test_chapter_numbers_are_written_as_a_two_digit_badge():
    """Номер главы в пункте итогов — как в оглавлении встречи: «08»."""
    assert humanize.chapter_numbers((8,)) == "08"
    assert humanize.chapter_numbers((6, 7)) == "06–07"
    assert humanize.chapter_numbers((12, 13, 14)) == "12–14"
    assert humanize.chapter_numbers((7, 3)) == "03, 07"
    assert humanize.chapter_numbers(()) == ""


def test_short_date_is_day_and_month_with_dots():
    assert humanize.short_date(date(2026, 10, 7)) == "07.10"


def test_on_weekday_answers_when():
    assert humanize.on_weekday(date(2026, 11, 4)) == "в среду"
    assert humanize.on_weekday(date(2026, 11, 3)) == "во вторник"
    assert humanize.on_weekday(date(2026, 11, 8)) == "в воскресенье"
