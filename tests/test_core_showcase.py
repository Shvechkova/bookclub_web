"""Выборки для главной-витрины: свежие понятия, споры и встречи с картинками."""

from datetime import date

from app.core.models import MeetingImage, Outcome, OutcomeItem
from app.core.view import ClubView
from tests.factories import a_book, a_club, a_meeting, some_data

TODAY = date(2026, 10, 26)
POSTER = MeetingImage(src="meetings/poster.jpg", alt="Афиша")
RECAP = MeetingImage(src="meetings/recap.jpg", alt="Итоги")


def view(meetings=(), books=(), club=None) -> ClubView:
    return ClubView(some_data(books=books, meetings=meetings, club=club))


def debates(*headings: str) -> Outcome:
    return Outcome(
        debates=tuple(OutcomeItem(heading=item, text=f"Текст: {item}") for item in headings)
    )


# --- короткое название ------------------------------------------------------


def test_the_short_title_of_a_meeting_is_the_short_title_of_its_book():
    book = a_book("ddia", title="Высоконагруженные приложения, 2-е издание",
                  short_title="Высоконагруженные приложения")
    meeting = a_meeting("m1", "2026-11-04", book="ddia", planned=(1,))

    assert view([meeting], [book]).short_title_of(meeting) == "Высоконагруженные приложения"


def test_without_a_short_title_the_full_one_is_used():
    book = a_book("brooks", title="Мифический человеко-месяц")
    meeting = a_meeting("m1", "2026-11-04", book="brooks", planned=(1,))

    assert view([meeting], [book]).short_title_of(meeting) == "Мифический человеко-месяц"


def test_a_meeting_without_a_book_is_titled_by_itself():
    meeting = a_meeting("lone", "2026-11-04", title="ADR-дуэль")

    assert view([meeting]).short_title_of(meeting) == "ADR-дуэль"


# --- свежие понятия -----------------------------------------------------------


def test_recent_topics_go_from_the_latest_past_meeting_without_repeats():
    meetings = [
        a_meeting("old", "2026-09-23", title="Старая", topics=("Закон Брукса", "ADR")),
        a_meeting("new", "2026-10-07", title="Новая", topics=("Закон Конвея", "ADR")),
        a_meeting("next", "2026-11-04", title="Будущая", topics=("Шардирование",)),
    ]

    names = [item.name for item in view(meetings).recent_topics(TODAY)]

    assert names == ["Закон Конвея", "ADR", "Закон Брукса"]


def test_recent_topics_are_limited_to_eight():
    meeting = a_meeting(
        "m1", "2026-10-07", title="Встреча", topics=tuple(f"Тема {n}" for n in range(12))
    )

    assert len(view([meeting]).recent_topics(TODAY)) == 8


def test_a_recent_topic_knows_its_notes():
    club = a_club(topic_notes={"ADR": "https://example.org/adr"})
    meeting = a_meeting("m1", "2026-10-07", title="Встреча", topics=("ADR",))

    (topic,) = view([meeting], club=club).recent_topics(TODAY)

    assert topic.notes_url == "https://example.org/adr"


def test_no_topics_means_an_empty_selection():
    assert view([a_meeting("m1", "2026-10-07", title="Встреча")]).recent_topics(TODAY) == ()


# --- свежие споры -------------------------------------------------------------


def test_recent_debates_are_the_first_three_of_the_latest_meeting():
    meetings = [
        a_meeting("old", "2026-09-23", title="Старая", outcome=debates("Старый спор")),
        a_meeting("new", "2026-10-07", title="Новая", outcome=debates("А", "Б", "В", "Г", "Д")),
    ]

    found = view(meetings).recent_debates(TODAY)

    assert [item.debate.heading for item in found] == ["А", "Б", "В"]
    assert {item.meeting.id for item in found} == {"new"}


def test_recent_debates_continue_with_the_previous_meeting():
    meetings = [
        a_meeting("old", "2026-09-23", title="Старая", outcome=debates("1", "2", "3", "4")),
        a_meeting("new", "2026-10-07", title="Новая", outcome=debates("Свежий")),
    ]

    found = view(meetings).recent_debates(TODAY)

    assert [item.debate.heading for item in found] == ["Свежий", "1", "2"]
    assert [item.meeting.id for item in found] == ["new", "old", "old"]


def test_debates_of_a_future_meeting_are_not_counted():
    meetings = [a_meeting("next", "2026-11-04", title="Будущая", outcome=debates("Рано"))]

    assert view(meetings).recent_debates(TODAY) == ()


def test_no_debates_means_an_empty_selection():
    meetings = [a_meeting("m1", "2026-10-07", title="Встреча", outcome=Outcome(agreed="Да."))]

    assert view(meetings).recent_debates(TODAY) == ()


# --- встречи с картинками -----------------------------------------------------


def test_the_gallery_holds_meetings_with_images_newest_first():
    meetings = [
        a_meeting("first", "2026-09-23", title="Первая", poster=POSTER),
        a_meeting("plain", "2026-09-30", title="Без картинок"),
        a_meeting("second", "2026-10-07", title="Вторая", poster=POSTER, recap_card=RECAP),
        a_meeting("next", "2026-11-04", title="Ближайшая", poster=POSTER),
        a_meeting("later", "2026-11-18", title="Потом", poster=POSTER),
    ]

    gallery = view(meetings).gallery(TODAY)

    assert [item.meeting.id for item in gallery] == ["next", "second", "first"]
    assert [item.is_upcoming for item in gallery] == [True, False, False]
    assert gallery[1].image == RECAP and gallery[1].is_recap
    assert gallery[0].image == POSTER and not gallery[0].is_recap


def test_a_past_meeting_without_a_recap_card_shows_its_poster():
    meetings = [a_meeting("m1", "2026-10-21", title="Встреча", poster=POSTER)]

    (item,) = view(meetings).gallery(TODAY)

    assert item.image == POSTER and not item.is_recap


def test_the_gallery_holds_at_most_six_meetings():
    meetings = [
        a_meeting(f"m{n}", f"2026-09-{n + 10:02d}", title=f"Встреча {n}", poster=POSTER)
        for n in range(9)
    ]

    gallery = view(meetings).gallery(TODAY)

    assert len(gallery) == 6
    assert gallery[0].meeting.id == "m8"


def test_the_default_is_the_latest_past_meeting_with_an_image():
    meetings = [
        a_meeting("past", "2026-10-07", title="Прошедшая", recap_card=RECAP),
        a_meeting("next", "2026-11-04", title="Ближайшая", poster=POSTER),
    ]

    assert view(meetings).gallery_default(TODAY).meeting.id == "past"


def test_without_past_images_the_default_is_the_upcoming_meeting():
    meetings = [a_meeting("next", "2026-11-04", title="Ближайшая", poster=POSTER)]

    assert view(meetings).gallery_default(TODAY).meeting.id == "next"


def test_without_images_there_is_no_gallery():
    meetings = [a_meeting("m1", "2026-10-07", title="Встреча")]

    assert view(meetings).gallery(TODAY) == ()
    assert view(meetings).gallery_default(TODAY) is None
