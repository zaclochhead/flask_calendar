import pytest
from flask import Flask
from flask_calendar.app_utils import task_details_for_markup


SOURCE_STRING_PLACEHOLDER = "pre {} post"
EXPECTED_STRING_PLACEHOLDER = "pre <a href=\"{}\" target=\"_blank\">{}</a> post"


@pytest.mark.parametrize("url, description", [
    ("http://test.test", "standard http url"),
    ("https://test.test", "standard https url"),
    ("http://www.test.test", "www-prefixed url"),
    ("http://0.0.0.0", "ip url"),
    ("http://test.test/?test=test&test2=test2", "url with query string"),
])
def test_supported_task_details_for_markup(app: Flask, url: str, description: str) -> None:
    with app.app_context():
        expected = EXPECTED_STRING_PLACEHOLDER.format(url, url)
        actual = task_details_for_markup(SOURCE_STRING_PLACEHOLDER.format(url))
        assert expected == actual


@pytest.mark.parametrize("url, description", [
    ("http://test.test/#some=thing", "hash url"),
    ("http://localhost/", "localhost url"),
    ("http://test.test:8000", "specified port url"),
])
def test_unsupported_task_details_for_markup(app: Flask, url: str, description: str) -> None:
    with app.app_context():
        expected = EXPECTED_STRING_PLACEHOLDER.format(url, url)
        actual = task_details_for_markup(SOURCE_STRING_PLACEHOLDER.format(url))
        assert expected != actual
