import numpy as np
import pytest

from backend.services.neural_detector import NeuralObjectDetector, neural_detector

pytestmark = pytest.mark.unit


def test_letterbox_preserves_aspect_ratio():
    img = np.zeros((480, 640, 3), np.uint8)
    boxed, scale, pad_x, pad_y = NeuralObjectDetector.letterbox(img, (640, 640))
    assert boxed.shape == (640, 640, 3)
    assert scale == pytest.approx(1.0)
    assert (pad_x, pad_y) == (0, 80)


def _prediction(cx, cy, w, h, obj, cls_id, cls_p):
    row = np.zeros(85, np.float32)
    row[:4] = [cx, cy, w, h]
    row[4] = obj
    row[5 + cls_id] = cls_p
    return row[None, :]


def test_decode_yolov5_maps_box_back_to_original_frame():
    d = neural_detector
    pred = _prediction(320, 400, 200, 300, 0.95, 0, 0.95)  # person in letterboxed 640x640 space
    out = d.decode_yolov5(pred, scale=1.0, pad_x=0, pad_y=80, w_orig=640, h_orig=480)
    assert len(out) == 1
    x, y, w, h = out[0]["bbox"]
    assert out[0]["name"] == "person"
    assert (x, y, w, h) == (220, 170, 200, 300)  # pad_y removed
    assert out[0]["source"] == "yolov5m"


def test_decode_yolov5_filters_low_confidence():
    pred = _prediction(320, 320, 100, 100, 0.3, 0, 0.3)
    assert neural_detector.decode_yolov5(pred, 1.0, 0, 0, 640, 640) == []


def test_decode_yolov5_applies_friendly_labels():
    pred = _prediction(320, 320, 100, 100, 0.9, 67, 0.9)  # COCO 67 = cell phone
    out = neural_detector.decode_yolov5(pred, 1.0, 0, 0, 640, 640)
    assert out and out[0]["name"] == "phone"


def test_nms_removes_duplicate_boxes():
    a = _prediction(320, 320, 100, 100, 0.9, 0, 0.9)
    b = _prediction(324, 322, 100, 100, 0.8, 0, 0.8)
    out = neural_detector.decode_yolov5(np.vstack([a, b]), 1.0, 0, 0, 640, 640)
    assert len(out) == 1


def test_model_loaded_and_detect_returns_list():
    assert neural_detector.model_loaded, "no ONNX detector found - run scripts/download_models.py"
    out = neural_detector.detect(np.full((480, 640, 3), 100, np.uint8))
    assert isinstance(out, list)


def test_two_overlapping_people_are_both_kept(monkeypatch):
    """Regression: a person standing in front of another must not be merged away (YOLOv5m path)."""
    d = neural_detector
    people = [
        {"name": "person", "confidence": 0.9, "bbox": (100, 50, 400, 400), "source": "yolov5m"},
        {"name": "person", "confidence": 0.8, "bbox": (300, 120, 200, 300), "source": "yolov5m"},  # mostly inside the first
    ]
    monkeypatch.setattr(d, "_run_model", lambda img: list(people))
    out = d.detect(np.full((480, 640, 3), 120, np.uint8))
    assert [o["name"] for o in out if o["name"] == "person"] == ["person", "person"]


def test_heuristic_guess_cannot_fill_the_frame():
    """Regression: saliency guesses (phone/painting...) used to produce frame-sized boxes."""
    import cv2
    img = np.full((480, 640, 3), 30, np.uint8)
    cv2.rectangle(img, (20, 20), (620, 460), (230, 230, 230), 3)     # huge outline
    skin = np.zeros((480, 640), np.uint8)
    out = neural_detector._heuristic_fallback(img, skin, [])
    frame = 480 * 640
    assert all(o["bbox"][2] * o["bbox"][3] <= 0.30 * frame for o in out)
