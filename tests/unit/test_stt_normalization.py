import pytest
from backend.services.stt import normalize_transcription_text as norm

pytestmark = pytest.mark.unit


def test_slash_time_is_fixed():
    assert norm("remind me at 12/7 AM") == "remind me at 12:07 AM"


def test_dot_time_is_fixed():
    assert norm("meet at 5.30 PM") == "meet at 5:30 PM"


def test_plain_text_untouched():
    assert norm("hello world") == "hello world"


def test_empty_text():
    assert norm("") == ""
