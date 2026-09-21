"""Каркас: приложение поднимается и отдаёт страницу."""

from fastapi.testclient import TestClient

from app.web.app import create_app


def test_app_serves_a_page():
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert response.text.strip() != ""
