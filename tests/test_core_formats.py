"""Перечень форматов: собирается из прошедших встреч, а не из списка в данных."""

from datetime import date

from app.core.view import ClubView
from tests.factories import a_meeting, some_data

TODAY = date(2026, 9, 21)


def formats(meetings):
    return ClubView(some_data(meetings=meetings)).formats(TODAY)


def test_a_format_of_a_past_meeting_is_listed():
    entries = formats([a_meeting("m1", "2026-09-09", title="Раз", fmt="ADR-дуэль")])

    assert [entry.name for entry in entries] == ["ADR-дуэль"]
    assert [meeting.id for meeting in entries[0].meetings] == ["m1"]


def test_a_format_of_a_future_meeting_is_not_listed():
    entries = formats([a_meeting("m1", "2026-10-07", title="Раз", fmt="Architecture Kata")])

    assert entries == ()


def test_a_format_of_a_meeting_happening_today_is_not_listed_yet():
    entries = formats([a_meeting("m1", "2026-09-21", title="Раз", fmt="Event Storming")])

    assert entries == ()


def test_a_format_held_twice_takes_one_entry_with_both_meetings():
    entries = formats(
        [
            a_meeting("m1", "2026-09-09", title="Раз", fmt="ADR-дуэль"),
            a_meeting("m2", "2026-09-02", title="Два", fmt="ADR-дуэль"),
        ]
    )

    assert [entry.name for entry in entries] == ["ADR-дуэль"]
    assert [meeting.id for meeting in entries[0].meetings] == ["m2", "m1"]


def test_a_meeting_without_a_format_adds_nothing():
    entries = formats([a_meeting("m1", "2026-09-09", title="Раз")])

    assert entries == ()
