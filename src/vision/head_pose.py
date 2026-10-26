"""Head pose estimation and visual gaze classification module.
Calculates 3D rotational Euler angles (Yaw, Pitch, Roll) and determines participant attentiveness.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, Tuple
import math


class GazeState(str, Enum):
    FOCUSED = "FOCUSED"
    DISTRACTED_LEFT = "DISTRACTED_LEFT"
    DISTRACTED_RIGHT = "DISTRACTED_RIGHT"
    LOOKING_DOWN = "LOOKING_DOWN"
    LOOKING_UP = "LOOKING_UP"


@dataclass
class HeadPoseResult:
    yaw: float    # Rotation left (-) to right (+) in degrees
    pitch: float  # Down (-) to up (+) in degrees
    roll: float   # Tilt left (-) to right (+) in degrees
    gaze_state: GazeState
    focus_score: float  # 0.0 (totally distracted) to 1.0 (optimally focused)
    is_facing_front: bool


class HeadPoseEstimator:
    """Estimates Euler angles from facial geometric landmarks or projection coordinates."""

    def __init__(
        self,
        yaw_limit_deg: float = 25.0,
        pitch_down_limit_deg: float = -20.0,
        pitch_up_limit_deg: float = 25.0,
    ):
        self.yaw_limit = yaw_limit_deg
        self.pitch_down_limit = pitch_down_limit_deg
        self.pitch_up_limit = pitch_up_limit_deg

    def estimate_from_angles(self, yaw: float, pitch: float, roll: float = 0.0) -> HeadPoseResult:
        """Classifies gaze state and computes normalized focus score from explicit Euler angles."""
        # Clamp angles
        yaw = max(-90.0, min(90.0, yaw))
        pitch = max(-90.0, min(90.0, pitch))
        roll = max(-90.0, min(90.0, roll))

        # Classify state
        if pitch < self.pitch_down_limit:
            state = GazeState.LOOKING_DOWN
        elif pitch > self.pitch_up_limit:
            state = GazeState.LOOKING_UP
        elif yaw < -self.yaw_limit:
            state = GazeState.DISTRACTED_LEFT
        elif yaw > self.yaw_limit:
            state = GazeState.DISTRACTED_RIGHT
        else:
            state = GazeState.FOCUSED

        # Focus score computation
        # Perfectly frontal = 1.0, falls off as angle increases
        yaw_penalty = (abs(yaw) / 60.0) ** 1.5
        pitch_penalty = (abs(pitch) / 45.0) ** 1.5
        focus_score = max(0.0, min(1.0, 1.0 - 0.6 * yaw_penalty - 0.4 * pitch_penalty))

        is_front = state == GazeState.FOCUSED

        return HeadPoseResult(
            yaw=round(yaw, 2),
            pitch=round(pitch, 2),
            roll=round(roll, 2),
            gaze_state=state,
            focus_score=round(focus_score, 3),
            is_facing_front=is_front,
        )

    def estimate_from_landmarks(
        self,
        nose_tip: Tuple[float, float],
        left_eye: Tuple[float, float],
        right_eye: Tuple[float, float],
        mouth_center: Tuple[float, float],
        bbox: Tuple[float, float, float, float],
    ) -> HeadPoseResult:
        """Estimates 3D Euler angles geometrically from 2D landmark coordinates relative to bounding box."""
        bx, by, bw, bh = bbox
        if bw <= 0 or bh <= 0:
            return self.estimate_from_angles(0.0, 0.0, 0.0)

        # Eye midpoint
        eye_mid_x = (left_eye[0] + right_eye[0]) / 2.0
        eye_mid_y = (left_eye[1] + right_eye[1]) / 2.0

        # Eye distance for scale normalization
        eye_dist = math.sqrt((right_eye[0] - left_eye[0]) ** 2 + (right_eye[1] - left_eye[1]) ** 2)
        if eye_dist <= 0:
            eye_dist = bw * 0.4

        # Roll: angle of eye line relative to horizontal
        dx = right_eye[0] - left_eye[0]
        dy = right_eye[1] - left_eye[1]
        roll = math.degrees(math.atan2(dy, dx))

        # Yaw: displacement of nose from eye midpoint along horizontal axis
        nose_offset_x = (nose_tip[0] - eye_mid_x) / (eye_dist * 0.5)
        yaw = max(-90.0, min(90.0, nose_offset_x * 50.0))

        # Pitch: displacement of nose from vertical center of eye-to-mouth
        face_height = max(1e-4, mouth_center[1] - eye_mid_y)
        expected_nose_y = eye_mid_y + face_height * 0.45
        nose_offset_y = (nose_tip[1] - expected_nose_y) / face_height
        pitch = max(-90.0, min(90.0, -nose_offset_y * 60.0))

        return self.estimate_from_angles(yaw, pitch, roll)
