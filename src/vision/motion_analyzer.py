"""Kinetic motion analysis and participant inactivity/drowsiness detection module.
Evaluates micro-movements, restlessness, posture changes, and sustained immobility.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple, Any
import math
import time

from .head_pose import GazeState


class MotionState(str, Enum):
    OPTIMAL_ENGAGEMENT = "OPTIMAL_ENGAGEMENT"
    FIDGETING = "FIDGETING"
    STATIC_INACTIVE = "STATIC_INACTIVE"
    DROWSY_SUSPECTED = "DROWSY_SUSPECTED"


@dataclass
class BehavioralAnalysis:
    track_id: int
    motion_energy: float             # [0.0, 1.0]
    motion_state: MotionState
    inactivity_seconds: float
    is_drowsy: bool
    is_fidgeting: bool
    posture_stability_score: float   # [0.0, 1.0]


class MotionAnalyzer:
    """Tracks temporal kinetic energy and detects drowsiness or restlessness per student track."""

    def __init__(
        self,
        inactivity_drowsiness_sec: float = 12.0,
        fidget_threshold: float = 0.70,
        static_threshold: float = 0.05,
        smoothing_alpha: float = 0.75,
    ):
        self.inactivity_drowsiness_sec = inactivity_drowsiness_sec
        self.fidget_threshold = fidget_threshold
        self.static_threshold = static_threshold
        self.smoothing_alpha = smoothing_alpha

        # Track history: track_id -> dict of tracking state
        self._track_states: Dict[int, Dict[str, Any]] = {}

    def update_motion(
        self,
        track_id: int,
        current_bbox: Tuple[float, float, float, float],
        gaze_state: GazeState,
        timestamp: Optional[float] = None,
    ) -> BehavioralAnalysis:
        """Evaluates kinetic displacement and temporal behavioral state."""
        now = timestamp if timestamp is not None else time.time()
        cx = current_bbox[0] + current_bbox[2] / 2.0
        cy = current_bbox[1] + current_bbox[3] / 2.0

        if track_id not in self._track_states:
            self._track_states[track_id] = {
                "prev_center": (cx, cy),
                "prev_bbox": current_bbox,
                "prev_time": now,
                "smoothed_motion": 0.25,
                "inactivity_start": None,
                "drowsiness_flagged": False,
            }
            return BehavioralAnalysis(
                track_id=track_id,
                motion_energy=0.25,
                motion_state=MotionState.OPTIMAL_ENGAGEMENT,
                inactivity_seconds=0.0,
                is_drowsy=False,
                is_fidgeting=False,
                posture_stability_score=0.85,
            )

        state = self._track_states[track_id]
        dt = max(1e-3, now - state["prev_time"])

        # Spatial displacement of center normalized by bounding box size
        prev_cx, prev_cy = state["prev_center"]
        bw = max(1e-4, current_bbox[2])
        bh = max(1e-4, current_bbox[3])

        dx = (cx - prev_cx) / bw
        dy = (cy - prev_cy) / bh
        raw_velocity = math.sqrt(dx * dx + dy * dy) / dt

        # Normalize velocity to [0, 1] range (where 1.0 represents sudden rapid jerk/jump)
        raw_energy = min(1.0, raw_velocity * 0.15)

        # Exponential moving average smoothing
        smoothed = self.smoothing_alpha * state["smoothed_motion"] + (1 - self.smoothing_alpha) * raw_energy
        state["smoothed_motion"] = smoothed
        state["prev_center"] = (cx, cy)
        state["prev_bbox"] = current_bbox
        state["prev_time"] = now

        # Inactivity calculation
        is_subdued = smoothed < self.static_threshold or gaze_state == GazeState.LOOKING_DOWN
        if is_subdued:
            if state["inactivity_start"] is None:
                state["inactivity_start"] = now
            inactivity_duration = now - state["inactivity_start"]
        else:
            state["inactivity_start"] = None
            inactivity_duration = 0.0

        # Drowsiness detection: prolonged looking down or zero motion beyond threshold
        is_drowsy = (
            inactivity_duration >= self.inactivity_drowsiness_sec
            and (gaze_state == GazeState.LOOKING_DOWN or smoothed < self.static_threshold)
        )
        state["drowsiness_flagged"] = is_drowsy

        # State determination
        if is_drowsy:
            m_state = MotionState.DROWSY_SUSPECTED
        elif smoothed > self.fidget_threshold:
            m_state = MotionState.FIDGETING
        elif smoothed < self.static_threshold:
            m_state = MotionState.STATIC_INACTIVE
        else:
            m_state = MotionState.OPTIMAL_ENGAGEMENT

        # Posture stability score: optimal during calm engagement, lower when restless or slumped
        stability = 1.0 - min(1.0, abs(smoothed - 0.25) * 1.5)
        if is_drowsy:
            stability *= 0.3

        return BehavioralAnalysis(
            track_id=track_id,
            motion_energy=round(smoothed, 3),
            motion_state=m_state,
            inactivity_seconds=round(inactivity_duration, 1),
            is_drowsy=is_drowsy,
            is_fidgeting=m_state == MotionState.FIDGETING,
            posture_stability_score=round(max(0.0, stability), 3),
        )

    def reset_track(self, track_id: int):
        self._track_states.pop(track_id, None)
