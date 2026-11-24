import pytest

from backend.services.routine_learner import routine_learner as rl

pytestmark = pytest.mark.unit


def test_log_action_increments_frequency():
    for _ in range(3):
        rl.log_action("app_launch", "Google Maps")
    routines = rl.get_all_routines()
    assert routines[0]["frequency"] == 3


def test_suggestion_after_three_uses_in_same_time_slot():
    for _ in range(3):
        rl.log_action("website_open", "YouTube")
    suggestions = rl.get_proactive_suggestions()
    assert any("YouTube" in s["message"] for s in suggestions)


def test_no_suggestion_before_threshold():
    rl.log_action("website_open", "Reddit")
    assert rl.get_proactive_suggestions() == []


def test_clear_all_routines():
    rl.log_action("app_launch", "Notepad")
    assert rl.clear_all_routines() >= 1
    assert rl.get_all_routines() == []
