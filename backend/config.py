import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

BASE_DIR_PATH = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_config = ConfigDict(extra="allow", env_file=".env", env_file_encoding="utf-8")

    # Base Paths
    BASE_DIR: str = str(BASE_DIR_PATH)

    # App Settings
    APP_NAME: str = "AEGIS — Assisted Executive Guidance and Intelligence System"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # AI Model Settings (Gemini 2.5 Flash primary, OpenRouter optional fallback)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"
    AGENT_MAX_STEPS: int = 6
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "google/gemini-2.0-flash-001"
    VISION_MODEL: str = "google/gemini-2.0-flash-001"

    # Local vision (YOLOv5m ONNX + temporal smoothing)
    YOLO_MODEL_FILE: str = "yolov5m.onnx"
    YOLO_CONF_THRESHOLD: float = 0.35
    YOLO_IOU_THRESHOLD: float = 0.45
    TRACK_EMA_ALPHA: float = 0.45        # EMA smoothing factor for box coordinates / confidence
    TRACK_PERSISTENCE_MS: int = 850      # keep a lost target visible for this long (reduces jitter)

    # Auth (Google Sign-In). Leave empty to run in local-profile mode.
    GOOGLE_CLIENT_ID: str = ""
    AUTH_SECRET: str = "change-me-aegis-local-secret"
    AUTH_TOKEN_TTL_HOURS: int = 72

    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR_PATH / 'aegis.db'}"

    # TTS Settings ('edge-tts' or 'pyttsx3' or 'web')
    TTS_PROVIDER: str = "edge-tts"
    TTS_VOICE: str = "en-US-ChristopherNeural"
    TTS_SPEED: str = "+0%"
    TTS_PITCH: str = "+0Hz"

    # STT Settings ('faster-whisper' or 'web')
    STT_PROVIDER: str = "faster-whisper"
    WHISPER_MODEL_SIZE: str = "base"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"

    # Privacy and Feature Toggles
    CAMERA_ENABLED: bool = False
    CONTINUOUS_CAMERA: bool = False
    LOCATION_ENABLED: bool = True
    AUTOMATION_ENABLED: bool = True
    LEARNING_ENABLED: bool = True
    CLOUD_VISION_ENABLED: bool = True
    WAKE_WORD_ENABLED: bool = False
    VOICE_FIRST_MODE: bool = False

    # Default Paths
    DESKTOP_DIR: str = str(Path.home() / "Desktop")
    DOCUMENTS_DIR: str = str(Path.home() / "Documents")
    DOWNLOADS_DIR: str = str(Path.home() / "Downloads")

settings = Settings()
