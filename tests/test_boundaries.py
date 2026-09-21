"""Граница между слоями: ядро не знает про веб, шаблоны и чтение файлов."""

from tests.boundaries import forbidden_imports


def test_check_catches_a_violation():
    """Проверка должна ловить модуль, который тянет веб-слой."""
    assert "fastapi" in forbidden_imports("tests.fixtures.violator")


def test_core_does_not_pull_the_web_layer():
    assert forbidden_imports("app.core") == []
