"""
Temporal target tracker for the AEGIS AR vision HUD.

Raw per-frame detector output jitters: boxes wobble by a few pixels and targets
flicker in and out when confidence hovers around the threshold. This tracker
fixes both problems:

* EMA smoothing  - box coordinates and confidence are exponentially smoothed
                   (new = alpha * observed + (1 - alpha) * previous).
* Persistence    - a target that disappears is still reported for
                   `persistence_ms` (850 ms by default) before being dropped.

Matching is greedy by IoU between detections and existing tracks of the same
class. The clock is injectable so behaviour is deterministic in tests.
"""
from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.config import settings

BBox = Tuple[float, float, float, float]  # x, y, w, h (pixels)


def iou(a: BBox, b: BBox) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0.0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


@dataclass
class Track:
    track_id: int
    name: str
    bbox: BBox
    confidence: float
    location: str = ""
    spatial_relationship: str = ""
    last_seen_ms: float = 0.0
    hits: int = 1
    extra: Dict[str, Any] = field(default_factory=dict)


class DetectionTracker:
    def __init__(
        self,
        alpha: Optional[float] = None,
        persistence_ms: Optional[int] = None,
        iou_match: float = 0.25,
        clock: Optional[Callable[[], float]] = None,
    ):
        self.alpha = settings.TRACK_EMA_ALPHA if alpha is None else alpha
        self.persistence_ms = settings.TRACK_PERSISTENCE_MS if persistence_ms is None else persistence_ms
        self.iou_match = iou_match
        self._clock = clock or (lambda: time.monotonic() * 1000.0)
        self._ids = itertools.count(1)
        self.tracks: List[Track] = []

    def reset(self) -> None:
        self.tracks = []

    def update(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Feed one frame of detections; returns smoothed, persistence-filtered targets."""
        now = self._clock()
        unmatched_tracks = set(range(len(self.tracks)))

        # Highest confidence detections claim tracks first.
        for det in sorted(detections, key=lambda d: d.get("confidence", 0.0), reverse=True):
            bbox = tuple(float(v) for v in det["bbox"])
            best_idx, best_iou = None, self.iou_match
            for idx in unmatched_tracks:
                tr = self.tracks[idx]
                if tr.name != det["name"]:
                    continue
                score = iou(tr.bbox, bbox)
                if score >= best_iou:
                    best_idx, best_iou = idx, score

            if best_idx is None:
                self.tracks.append(
                    Track(
                        track_id=next(self._ids),
                        name=det["name"],
                        bbox=bbox,  # type: ignore[arg-type]
                        confidence=float(det.get("confidence", 0.0)),
                        location=det.get("location", ""),
                        spatial_relationship=det.get("spatial_relationship", ""),
                        last_seen_ms=now,
                    )
                )
            else:
                tr = self.tracks[best_idx]
                a = self.alpha
                tr.bbox = tuple(a * n + (1 - a) * o for n, o in zip(bbox, tr.bbox))  # type: ignore[assignment]
                tr.confidence = a * float(det.get("confidence", 0.0)) + (1 - a) * tr.confidence
                tr.location = det.get("location", tr.location)
                tr.spatial_relationship = det.get("spatial_relationship", tr.spatial_relationship)
                tr.last_seen_ms = now
                tr.hits += 1
                unmatched_tracks.discard(best_idx)

        # Drop tracks that have been missing longer than the persistence window.
        self.tracks = [t for t in self.tracks if now - t.last_seen_ms <= self.persistence_ms]

        return [
            {
                "track_id": t.track_id,
                "name": t.name,
                "confidence": round(t.confidence, 3),
                "bbox": tuple(round(v, 1) for v in t.bbox),
                "location": t.location,
                "spatial_relationship": t.spatial_relationship,
                "age_ms": int(now - t.last_seen_ms),
                "stable": t.hits >= 3,
            }
            for t in self.tracks
        ]


detection_tracker = DetectionTracker()
