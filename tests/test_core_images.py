"""Картинка встречи: афиша до встречи, карточка итогов после."""

from datetime import date

from app.core.models import MeetingImage
from app.core.view import meeting_image
from tests.factories import a_meeting

TODAY = date(2026, 10, 15)

POSTER = MeetingImage(src="meetings/m-poster.jpg", alt="Афиша")
RECAP = MeetingImage(src="meetings/m-recap.jpg", alt="Итоги")


def test_an_upcoming_meeting_shows_its_poster_even_with_a_recap_card():
    meeting = a_meeting("m", "2026-10-21", poster=POSTER, recap_card=RECAP)

    assert meeting_image(meeting, TODAY) == POSTER


def test_a_past_meeting_shows_its_recap_card():
    meeting = a_meeting("m", "2026-10-07", poster=POSTER, recap_card=RECAP)

    assert meeting_image(meeting, TODAY) == RECAP


def test_a_past_meeting_without_a_recap_card_falls_back_to_the_poster():
    meeting = a_meeting("m", "2026-10-07", poster=POSTER)

    assert meeting_image(meeting, TODAY) == POSTER


def test_a_meeting_without_images_has_no_image():
    assert meeting_image(a_meeting("m", "2026-10-07"), TODAY) is None
    assert meeting_image(a_meeting("m", "2026-10-21"), TODAY) is None


def test_on_the_day_of_the_meeting_it_is_still_upcoming():
    """Как и везде на сайте: встреча прошла со следующего дня."""
    meeting = a_meeting("m", "2026-10-15", poster=POSTER, recap_card=RECAP)

    assert meeting_image(meeting, TODAY) == POSTER
