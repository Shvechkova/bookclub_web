"""Какие ссылки открываются в новой вкладке."""

import pytest

from app.web.links import new_tab, opens_elsewhere


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/club/notes/blob/main/brooks.md",
        "https://gist.github.com/someone/1",
        "https://t.me/kabanya",
        "https://t.me/+chat",
        "http://GitHub.com/club",
    ],
)
def test_github_and_telegram_open_in_a_new_tab(url):
    assert opens_elsewhere(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://s4m.space/",
        "https://calendar.google.com/calendar/render?action=TEMPLATE",
        "https://notgithub.com/club",
        "https://github.com.example.org/",
        "/books/brooks",
        "",
        None,
    ],
)
def test_other_links_stay_in_the_same_tab(url):
    assert not opens_elsewhere(url)


def test_the_filter_gives_attributes_for_the_link_tag():
    assert new_tab("https://t.me/kabanya") == ' target="_blank" rel="noopener"'
    assert new_tab("https://s4m.space/") == ""
