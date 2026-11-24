import pytest
from backend.services.tracker import DetectionTracker, iou

pytestmark = pytest.mark.unit


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def det(x=100, y=100, w=100, h=100, name="person", conf=0.9):
    return {"name": name, "bbox": (x, y, w, h), "confidence": conf}


def make(alpha=0.5, persistence=850):
    clock = Clock()
    return DetectionTracker(alpha=alpha, persistence_ms=persistence, clock=clock), clock


def test_iou_identical_and_disjoint():
    assert iou((0, 0, 10, 10), (0, 0, 10, 10)) == pytest.approx(1.0)
    assert iou((0, 0, 10, 10), (50, 50, 10, 10)) == 0.0


def test_ema_smooths_box_coordinates():
    tr, clock = make(alpha=0.5)
    tr.update([det(x=100)])
    clock.t += 33
    out = tr.update([det(x=120)])
    assert out[0]["bbox"][0] == pytest.approx(110.0)  # 0.5*120 + 0.5*100


def test_ema_smooths_confidence():
    tr, clock = make(alpha=0.5)
    tr.update([det(conf=0.9)])
    clock.t += 33
    out = tr.update([det(conf=0.5)])
    assert out[0]["confidence"] == pytest.approx(0.7)


def test_track_id_is_stable_across_frames():
    tr, clock = make()
    first = tr.update([det()])[0]["track_id"]
    clock.t += 33
    assert tr.update([det(x=104)])[0]["track_id"] == first


def test_lost_target_persists_within_850ms():
    tr, clock = make()
    tr.update([det()])
    clock.t += 800
    out = tr.update([])
    assert len(out) == 1 and out[0]["age_ms"] == 800


def test_lost_target_dropped_after_850ms():
    tr, clock = make()
    tr.update([det()])
    clock.t += 851
    assert tr.update([]) == []


def test_different_class_does_not_match():
    tr, clock = make()
    tr.update([det(name="person")])
    clock.t += 33
    out = tr.update([det(name="chair")])
    assert {o["name"] for o in out} == {"person", "chair"}


def test_stable_flag_after_three_hits():
    tr, clock = make()
    flags = []
    for _ in range(3):
        flags.append(tr.update([det()])[0]["stable"])
        clock.t += 33
    assert flags == [False, False, True]


def test_reset_clears_tracks():
    tr, _ = make()
    tr.update([det()])
    tr.reset()
    assert tr.tracks == []
