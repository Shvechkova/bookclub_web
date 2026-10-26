"""Место клуба: короткая форма для лент, полная — чтобы доехали."""

from app.core.models import Place


def test_full_form_lists_the_address_from_building_to_city():
    place = Place(
        venue="хакспейс s4m.space",
        building="Дом77",
        street="Ленинградская 77",
        floor="4 этаж",
        room="комната 413",
        city="Самара",
    )

    assert place.full == "Дом77, Ленинградская 77, 4 этаж, комната 413, Самара"


def test_short_form_names_the_venue_and_the_room():
    place = Place(
        venue="хакспейс s4m.space",
        building="Дом77",
        room="комната 413",
        city="Самара",
    )

    assert place.short == "хакспейс s4m.space, комната 413"


def test_a_missing_field_drops_out_without_leaving_a_gap():
    place = Place(
        venue="хакспейс s4m.space",
        building="Дом77",
        street="Ленинградская 77",
        room="комната 413",
        city="Самара",
    )

    assert place.full == "Дом77, Ленинградская 77, комната 413, Самара"
    assert ", ," not in place.full
    assert not place.full.endswith(",")


def test_place_prints_short_by_default():
    """В ленте место называют коротко, и шаблону для этого ничего не нужно знать."""
    place = Place(venue="хакспейс s4m.space", building="Дом77", room="комната 413")

    assert f"{place}" == "хакспейс s4m.space, комната 413"
