"""Shared fixtures. The environment is configured BEFORE any backend module is imported so the
whole suite runs against a throw-away SQLite file and never touches real data, keys or desktop."""
import base64
import os
import sys
import tempfile
import types
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="aegis_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_TMP) / 'test.db'}"
os.environ["GEMINI_API_KEY"] = ""
os.environ["OPENROUTER_API_KEY"] = ""
os.environ["GOOGLE_CLIENT_ID"] = "test-client-id.apps.googleusercontent.com"
os.environ["AUTH_SECRET"] = "unit-test-secret"
os.environ["VOICE_FIRST_MODE"] = "false"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# pyautogui needs a desktop session to import; tests must never drive the real mouse/keyboard.
try:  # pragma: no cover
    import pyautogui  # noqa: F401
except Exception:  # headless CI / Linux
    fake = types.ModuleType("pyautogui")
    fake.press = lambda *a, **k: None
    fake.click = lambda *a, **k: None
    fake.typewrite = lambda *a, **k: None
    fake.hotkey = lambda *a, **k: None
    sys.modules["pyautogui"] = fake

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402

from backend.database import Base, engine  # noqa: E402


@pytest.fixture(autouse=True)
def clean_db():
    """Fresh tables for every test."""
    import backend.models  # noqa: F401  (register models)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def jpeg_b64():
    """A synthetic 640x480 JPEG (base64) with some structure, usable as a camera frame."""
    img = np.full((480, 640, 3), 90, np.uint8)
    cv2.rectangle(img, (200, 100), (440, 440), (180, 150, 130), -1)
    cv2.circle(img, (320, 180), 60, (150, 170, 220), -1)
    cv2.randn(img, (0, 0, 0), (12, 12, 12))  # noise so it is not flagged as a covered lens
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return base64.b64encode(buf.tobytes()).decode()


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    from backend.main import app
    with TestClient(app) as c:  # runs lifespan (DB init + scheduler)
        yield c
