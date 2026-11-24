import pytest

from backend import main as app_main
from backend.services.visual_memory import visual_memory_engine as vm

pytestmark = pytest.mark.unit


def target(name="phone", stable=True, age_ms=0, loc="on the desk"):
    return {"name": name, "stable": stable, "age_ms": age_ms, "confidence": 0.9, "location": loc,
            "spatial_relationship": f"{loc} on the left", "track_id": 1, "bbox": (0, 0, 10, 10)}


@pytest.fixture(autouse=True)
def reset_throttle():
    app_main._last_remembered.clear()


def test_stable_visible_target_is_remembered_with_category_and_relation_only():
    assert app_main.remember_stable_targets([target()]) == 1
    mem = vm.get_all_memories()[0]
    assert mem["object"] == "phone" and mem["room"] == "workspace" and "left" in mem["spatial_relationship"]


def test_unstable_or_lingering_targets_are_not_remembered():
    assert app_main.remember_stable_targets([target(stable=False), target("mug", age_ms=400)]) == 0
    assert vm.get_all_memories() == []


def test_remembering_is_throttled_per_object():
    assert app_main.remember_stable_targets([target()]) == 1
    assert app_main.remember_stable_targets([target()]) == 0


def test_header_latency_is_rolling_median():
    app_main._router_samples.clear()
    for v in (1, 2, 100):
        app_main._router_samples.append(v)
    import statistics
    assert statistics.median(app_main._router_samples) == 2
