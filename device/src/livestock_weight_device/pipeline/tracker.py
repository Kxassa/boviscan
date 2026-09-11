"""Simple multi-object tracker for mock / early field use (IoU association)."""

from __future__ import annotations

from .types import Track
from ..inference.base import Detection


def _iou(a: Track | Detection, b: Detection | Track) -> float:
    ax1, ay1, ax2, ay2 = a.x1, a.y1, a.x2, a.y2
    bx1, by1, bx2, by2 = b.x1, b.y1, b.x2, b.y2
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


class SimpleTracker:
    """
    Assign stable track IDs across frames via greedy IoU matching.

    One animal ≈ one track_id ≈ one session weight estimate (pipeline emits once
    after ``min_hits`` consecutive associations).
    """

    def __init__(self, iou_threshold: float = 0.3, max_age: int = 8) -> None:
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self._tracks: dict[str, Track] = {}
        self._ages: dict[str, int] = {}
        self._counter = 0

    def update(self, detections: list[Detection]) -> list[Track]:
        # Age existing tracks
        for tid in list(self._ages.keys()):
            self._ages[tid] += 1

        unmatched_dets = list(range(len(detections)))
        matched: list[tuple[str, int]] = []

        # Greedy match highest IoU first
        candidates: list[tuple[float, str, int]] = []
        for tid, track in self._tracks.items():
            for di, det in enumerate(detections):
                score = _iou(track, det)
                if score >= self.iou_threshold:
                    candidates.append((score, tid, di))
        candidates.sort(reverse=True)
        used_tracks: set[str] = set()
        used_dets: set[int] = set()
        for score, tid, di in candidates:
            if tid in used_tracks or di in used_dets:
                continue
            used_tracks.add(tid)
            used_dets.add(di)
            matched.append((tid, di))

        for tid, di in matched:
            d = detections[di]
            tr = self._tracks[tid]
            tr.x1, tr.y1, tr.x2, tr.y2 = d.x1, d.y1, d.x2, d.y2
            tr.confidence = d.confidence
            tr.label = d.label
            tr.hits += 1
            self._ages[tid] = 0
            if di in unmatched_dets:
                unmatched_dets.remove(di)

        for di in unmatched_dets:
            d = detections[di]
            self._counter += 1
            tid = f"trk-{self._counter}"
            self._tracks[tid] = Track(
                track_id=tid,
                label=d.label,
                confidence=d.confidence,
                x1=d.x1,
                y1=d.y1,
                x2=d.x2,
                y2=d.y2,
                hits=1,
            )
            self._ages[tid] = 0

        # Drop stale tracks
        for tid in list(self._tracks.keys()):
            if self._ages.get(tid, 0) > self.max_age:
                del self._tracks[tid]
                self._ages.pop(tid, None)

        return [t for tid, t in self._tracks.items() if self._ages.get(tid, 0) == 0]
