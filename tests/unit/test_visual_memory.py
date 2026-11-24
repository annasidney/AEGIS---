import pytest

from backend.services.visual_memory import visual_memory_engine as vm

pytestmark = pytest.mark.unit


def test_store_then_find_object_by_alias():
    vm.store_observation("phone", "on the desk", room="workspace", spatial_relationship="on the desk on the left")
    r = vm.query_object_location("where is my mobile")
    assert r["found"] and r["object"] == "phone"


def test_store_updates_existing_observation():
    vm.store_observation("bottle", "on the desk")
    res = vm.store_observation("bottle", "on the floor")
    assert res["status"] == "updated"
    assert len(vm.get_all_memories()) == 1


def test_unknown_object_not_found():
    assert vm.query_object_location("where is my guitar")["found"] is False


def test_clear_keeps_user_saved_memories():
    vm.store_observation("keys", "on the desk", is_user_saved=True)
    vm.store_observation("mug", "on the desk")
    vm.clear_visual_memories()
    assert [m["object"] for m in vm.get_all_memories()] == ["keys"]
