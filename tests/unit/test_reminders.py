import pytest

from backend.tools import reminder_tools as rt

pytestmark = pytest.mark.unit


def test_create_relative_reminder():
    r = rt.create_reminder("stretch", "in 10 minutes")
    assert r["status"] == "created" and r["verified"]


def test_missing_time_never_guesses():
    r = rt.create_reminder("stretch", "")
    assert r["status"] == "needs_time" and r["message"] == "When should I remind you?"


def test_unparseable_time_is_rejected():
    assert rt.create_reminder("stretch", "blargh zork")["status"] == "parse_error"


def test_list_then_delete_by_keyword():
    rt.create_reminder("submit assignment", "in 2 hours")
    assert len(rt.list_reminders()["reminders"]) == 1
    assert rt.delete_reminder("assignment")["status"] == "deleted"
    assert rt.list_reminders()["status"] == "empty"


def test_delete_all():
    rt.create_reminder("a", "in 1 hour")
    rt.create_reminder("b", "in 2 hours")
    assert rt.delete_reminder("all")["status"] == "deleted_all"
