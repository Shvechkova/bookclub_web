"""Ядро: словарь клуба — поиск понятия по теме, указатель по буквам, главы и связи."""

from datetime import date

from app.core.models import Chapter, TermChapter
from app.core.view import ClubView
from tests.factories import a_book, a_meeting, a_term, some_data

TODAY = date(2026, 10, 26)


def view(terms=(), books=(), meetings=()) -> ClubView:
    return ClubView(some_data(books=books, meetings=meetings, glossary=terms))


# --- тема находит понятие ----------------------------------------------------


def test_a_topic_finds_its_term_by_name_regardless_of_case():
    conway = a_term("conway-law", "Закон Конвея")

    assert view([conway]).term_for("закон КОНВЕЯ") == conway


def test_a_topic_finds_its_term_by_alias():
    adr = a_term("adr", "Запись архитектурного решения", aliases=("ADR",))

    assert view([adr]).term_for("adr") == adr


def test_yo_and_ye_are_the_same_letter_when_matching():
    term = a_term("yo", "Ёлочная гирлянда")

    assert view([term]).term_for("елочная гирлянда") == term


def test_a_topic_outside_the_glossary_has_no_term():
    assert view([a_term("adr", "ADR")]).term_for("Шардирование") is None


def test_the_topic_catalogue_knows_the_term_of_each_topic():
    adr = a_term("adr", "ADR")
    club = view(
        [adr], meetings=[a_meeting("m1", "2026-10-07", title="Раз", topics=("ADR", "Кворум"))]
    )

    by_name = {entry.name: entry for entry in club.topics()}
    assert by_name["ADR"].term == adr
    assert by_name["Кворум"].term is None


def test_recent_topics_carry_their_terms():
    adr = a_term("adr", "ADR")
    club = view([adr], meetings=[a_meeting("m1", "2026-10-07", title="Раз", topics=("adr",))])

    (topic,) = club.recent_topics(TODAY)
    assert topic.name == "adr"
    assert topic.term == adr


# --- указатель по буквам -----------------------------------------------------


def test_letters_go_cyrillic_first_then_latin_alphabetically():
    terms = [
        a_term("uml", "UML"),
        a_term("second-system", "Эффект второй системы"),
        a_term("adr", "ADR"),
        a_term("conway-law", "Закон Конвея"),
        a_term("brooks-law", "Закон Брукса"),
    ]

    index = view(terms).glossary_index()

    assert [letter.letter for letter in index] == ["З", "Э", "A", "U"]
    assert [term.name for term in index[0].terms] == ["Закон Брукса", "Закон Конвея"]


def test_lowercase_names_go_under_their_capital_letter():
    index = view([a_term("bpmn", "bpmn"), a_term("bfs", "BFS")]).glossary_index()

    assert [(letter.letter, [t.id for t in letter.terms]) for letter in index] == [
        ("B", ["bfs", "bpmn"])
    ]


def test_yo_stands_under_ye():
    index = view([a_term("yo", "Ёмкость"), a_term("ye", "Емкий")]).glossary_index()

    assert [letter.letter for letter in index] == ["Е"]


def test_names_starting_with_a_digit_go_last():
    index = view([a_term("c4", "4+1"), a_term("adr", "ADR")]).glossary_index()

    assert [letter.letter for letter in index] == ["A", "#"]


def test_an_empty_glossary_has_no_letters():
    assert view().glossary_index() == ()


# --- главы и связанные понятия ----------------------------------------------


def test_a_chapter_is_signed_by_the_short_title_and_leads_to_its_notes():
    book = a_book(
        "ddia",
        title="Высоконагруженные приложения, 2-е издание",
        short_title="Высоконагруженные приложения",
        chapters_override=(
            Chapter(number=1, title="Раз"),
            Chapter(number=2, title="Два", notes_url="https://github.com/club/ddia/2.md"),
        ),
    )
    term = a_term("replication", "Репликация", chapters=(TermChapter("ddia", 2),))

    (chapter,) = view([term], books=[book]).term_chapters(term)

    assert chapter.label == "Высоконагруженные приложения, гл. 2"
    assert chapter.url == "https://github.com/club/ddia/2.md"


def test_a_chapter_without_notes_has_no_address():
    book = a_book("b1", title="Книга", chapters=3)
    term = a_term("t", "Понятие", chapters=(TermChapter("b1", 3),))

    (chapter,) = view([term], books=[book]).term_chapters(term)

    assert chapter.label == "Книга, гл. 3"
    assert chapter.url is None


def test_related_terms_keep_the_order_of_the_record():
    adr = a_term("adr", "ADR")
    c4 = a_term("c4", "Модель C4")
    uml = a_term("uml", "UML", related=("c4", "adr"))

    assert view([adr, c4, uml]).related_of(uml) == (c4, adr)
