"""Participant tracking and face detection manager.
Provides spatial tracking, identity association, and sustained presence verification.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import math
import time


@dataclass
class ParticipantDetection:
    track_id: int
    student_id: Optional[str]
    bbox: Tuple[float, float, float, float]  # (norm_x, norm_y, norm_w, norm_h) in [0, 1]
    confidence: float
    first_seen: float
    last_seen: float
    total_detections: int = 1
    consecutive_misses: int = 0
    assigned_seat: Optional[str] = None
    feature_hash: Optional[str] = None

    @property
    def center(self) -> Tuple[float, float]:
        x, y, w, h = self.bbox
        return (x + w / 2.0, y + h / 2.0)

    @property
    def duration_seconds(self) -> float:
        return max(0.0, self.last_seen - self.first_seen)

    @property
    def is_visible(self) -> bool:
        return self.consecutive_misses == 0


class FaceTracker:
    """Multi-object spatial tracker for classroom participants with identity persistence."""

    def __init__(
        self,
        max_missed_frames: int = 15,
        iou_threshold: float = 0.25,
        distance_threshold: float = 0.20,
    ):
        self.max_missed_frames = max_missed_frames
        self.iou_threshold = iou_threshold
        self.distance_threshold = distance_threshold
        self._next_track_id: int = 1
        self.active_tracks: Dict[int, ParticipantDetection] = {}
        self.student_to_track: Dict[str, int] = {}

    def update(
        self,
        raw_detections: List[Dict[str, Any]],
        current_timestamp: Optional[float] = None,
    ) -> List[ParticipantDetection]:
        """Updates active tracks with new frame detections.
        raw_detections: list of dicts with 'bbox': (x,y,w,h), 'confidence': float, optional 'student_id': str
        """
        now = current_timestamp if current_timestamp is not None else time.time()

        # Step 1: Match detections to existing tracks using IoU & center distance
        unmatched_dets = list(range(len(raw_detections)))
        matched_pairs: List[Tuple[int, int]] = []  # (track_id, det_idx)
        occupied_tracks = set()

        for track_id, track in self.active_tracks.items():
            best_det_idx = -1
            best_score = -1.0

            for idx in unmatched_dets:
                det = raw_detections[idx]
                iou = self._compute_iou(track.bbox, det["bbox"])
                dist = self._compute_distance(track.center, self._bbox_center(det["bbox"]))

                # Combined proximity score
                score = iou - (dist if dist < self.distance_threshold else 1.0)
                if (iou >= self.iou_threshold or dist <= self.distance_threshold) and score > best_score:
                    best_score = score
                    best_det_idx = idx

            if best_det_idx != -1:
                matched_pairs.append((track_id, best_det_idx))
                unmatched_dets.remove(best_det_idx)
                occupied_tracks.add(track_id)

        # Step 2: Update matched tracks
        for track_id, det_idx in matched_pairs:
            det = raw_detections[det_idx]
            track = self.active_tracks[track_id]
            # Smooth bounding box
            alpha = 0.7
            old_b = track.bbox
            new_b = det["bbox"]
            track.bbox = (
                alpha * new_b[0] + (1 - alpha) * old_b[0],
                alpha * new_b[1] + (1 - alpha) * old_b[1],
                alpha * new_b[2] + (1 - alpha) * old_b[2],
                alpha * new_b[3] + (1 - alpha) * old_b[3],
            )
            track.confidence = 0.5 * track.confidence + 0.5 * det.get("confidence", 0.9)
            track.last_seen = now
            track.total_detections += 1
            track.consecutive_misses = 0
            if "student_id" in det and det["student_id"]:
                track.student_id = det["student_id"]
                self.student_to_track[track.student_id] = track_id
            if "feature_hash" in det:
                track.feature_hash = det["feature_hash"]

        # Step 3: Increment misses for unoccupied tracks
        tracks_to_delete = []
        for track_id, track in self.active_tracks.items():
            if track_id not in occupied_tracks:
                track.consecutive_misses += 1
                if track.consecutive_misses > self.max_missed_frames:
                    tracks_to_delete.append(track_id)

        for tid in tracks_to_delete:
            del self.active_tracks[tid]

        # Step 4: Create new tracks for unmatched detections
        for det_idx in unmatched_dets:
            det = raw_detections[det_idx]
            student_id = det.get("student_id")
            new_track = ParticipantDetection(
                track_id=self._next_track_id,
                student_id=student_id,
                bbox=det["bbox"],
                confidence=det.get("confidence", 0.85),
                first_seen=now,
                last_seen=now,
                total_detections=1,
                consecutive_misses=0,
                assigned_seat=det.get("assigned_seat"),
                feature_hash=det.get("feature_hash"),
            )
            self.active_tracks[self._next_track_id] = new_track
            if student_id:
                self.student_to_track[student_id] = self._next_track_id
            self._next_track_id += 1

        return [t for t in self.active_tracks.values() if t.is_visible]

    def get_all_tracks(self) -> List[ParticipantDetection]:
        return list(self.active_tracks.values())

    @staticmethod
    def _compute_iou(box1: Tuple[float, float, float, float], box2: Tuple[float, float, float, float]) -> float:
        x1, y1, w1, h1 = box1
        x2, y2, w2, h2 = box2

        xi1 = max(x1, x2)
        yi1 = max(y1, y2)
        xi2 = min(x1 + w1, x2 + w2)
        yi2 = min(y1 + h1, y2 + h2)

        inter_w = max(0.0, xi2 - xi1)
        inter_h = max(0.0, yi2 - yi1)
        inter_area = inter_w * inter_h

        box1_area = w1 * h1
        box2_area = w2 * h2
        union_area = box1_area + box2_area - inter_area
        return inter_area / union_area if union_area > 0 else 0.0

    @staticmethod
    def _compute_distance(c1: Tuple[float, float], c2: Tuple[float, float]) -> float:
        return math.sqrt((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2)

    @staticmethod
    def _bbox_center(bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
        return (bbox[0] + bbox[2] / 2.0, bbox[1] + bbox[3] / 2.0)
