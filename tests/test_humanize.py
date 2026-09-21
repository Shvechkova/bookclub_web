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
