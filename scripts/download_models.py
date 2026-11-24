"""Download the YOLOv5m ONNX weights used by AEGIS local vision (~42 MB, one time)."""
import sys
import urllib.request
from pathlib import Path

URL = "https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5m.onnx"
DEST = Path(__file__).resolve().parent.parent / "backend" / "models_cache" / "yolov5m.onnx"


def main() -> int:
    if DEST.exists() and DEST.stat().st_size > 10_000_000:
        print(f"[ok] {DEST.name} already present ({DEST.stat().st_size // 1_000_000} MB)")
        return 0
    DEST.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading YOLOv5m ONNX -> {DEST}")
    try:
        urllib.request.urlretrieve(URL, DEST)
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] download failed: {exc}\nAEGIS will fall back to the bundled YOLOX-tiny model.")
        DEST.unlink(missing_ok=True)
        return 1
    print("[ok] done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
