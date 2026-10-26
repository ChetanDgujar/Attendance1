"""Multimodal fusion engine.
Fuses visual behavioral indicators (gaze, head pose, kinetic motion, inactivity)
with acoustic signals to compute calibrated, continuous student & classroom engagement indices.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import math

from ..config import FusionConfig
from ..vision.head_pose import HeadPoseResult, GazeState
from ..vision.motion_analyzer import BehavioralAnalysis, MotionState
from ..audio.acoustic_classifier import AcousticSnapshot, AcousticState


@dataclass
class StudentEngagementScore:
    student_id: str
    track_id: int
    raw_score: float              # [0.0, 100.0]
    smoothed_score: float         # [0.0, 100.0]
    gaze_component: float         # [0.0, 1.0]
    pose_component: float         # [0.0, 1.0]
    motion_component: float       # [0.0, 1.0]
    acoustic_component: float     # [0.0, 1.0]
    penalties_applied: float      # Subtracted penalty
    is_drowsy: bool
    is_distracted: bool
    attention_category: str       # "HIGH", "MODERATE", "LOW", "DISENGAGED"


@dataclass
class ClassroomEngagementSnapshot:
    timestamp: float
    average_engagement: float     # [0.0, 100.0]
    high_engagement_count: int
    moderate_engagement_count: int
    low_engagement_count: int
    disengaged_count: int
    active_students_count: int
    acoustic_state: AcousticState
    acoustic_speech_ratio: float
    student_scores: Dict[str, StudentEngagementScore] = field(default_factory=dict)


class MultimodalFusionEngine:
    """Combines heterogeneous vision and audio telemetry into unified engagement metrics."""

    def __init__(self, config: Optional[FusionConfig] = None):
        self.config = config or FusionConfig()
        self._prev_student_scores: Dict[str, float] = {}
        self._prev_classroom_average: Optional[float] = None

    def compute_student_engagement(
        self,
        student_id: str,
        track_id: int,
        head_pose: HeadPoseResult,
        behavior: BehavioralAnalysis,
        acoustic: AcousticSnapshot,
    ) -> StudentEngagementScore:
        """Fuses individual visual and shared acoustic telemetry for a single student."""
        w = self.config.weights
        p = self.config.penalties

        # 1. Gaze Alignment component
        gaze_comp = head_pose.focus_score

        # 2. Head Pose Stability component (penalizes extreme yaw/pitch)
        pose_penalty = min(1.0, (abs(head_pose.yaw) / 50.0) + (abs(head_pose.pitch) / 40.0))
        pose_comp = max(0.0, 1.0 - 0.7 * pose_penalty)

        # 3. Motion & Posture component
        motion_comp = behavior.posture_stability_score

        # 4. Acoustic Context component
        # In a discussion or monologue, conversational presence supports engagement
        if acoustic.state in (AcousticState.STUDENT_DISCUSSION, AcousticState.BALANCED_ENGAGEMENT):
            acoustic_comp = 0.85
        elif acoustic.state == AcousticState.TEACHER_MONOLOGUE:
            # During lecture, attentive visual posture is paramount
            acoustic_comp = 0.70
        elif acoustic.state == AcousticState.CHATTER_SURGE:
            # High chaotic chatter degrades individual focus
            acoustic_comp = 0.40
        else:  # SUSTAINED_SILENCE
            acoustic_comp = 0.50

        # Calculate weighted base score in [0.0, 1.0]
        base_score = (
            w.gaze_alignment * gaze_comp
            + w.head_pose_stability * pose_comp
            + w.body_kinetic_activity * motion_comp
            + w.acoustic_context * acoustic_comp
        )

        # Penalty evaluations
        penalties = 0.0
        is_distracted = head_pose.gaze_state in (GazeState.DISTRACTED_LEFT, GazeState.DISTRACTED_RIGHT, GazeState.LOOKING_DOWN)
        if is_distracted:
            penalties += p.persistent_distraction_penalty

        if behavior.is_drowsy:
            penalties += p.drowsiness_penalty

        raw_unit = max(0.0, min(1.0, base_score - penalties))
        raw_score = raw_unit * 100.0

        # Temporal smoothing
        prev = self._prev_student_scores.get(student_id, raw_score)
        alpha = self.config.score_smoothing_alpha
        smoothed = alpha * raw_score + (1.0 - alpha) * prev
        self._prev_student_scores[student_id] = smoothed

        # Category mapping
        if smoothed >= 75.0:
            category = "HIGH"
        elif smoothed >= 50.0:
            category = "MODERATE"
        elif smoothed >= 30.0:
            category = "LOW"
        else:
            category = "DISENGAGED"

        return StudentEngagementScore(
            student_id=student_id,
            track_id=track_id,
            raw_score=round(raw_score, 1),
            smoothed_score=round(smoothed, 1),
            gaze_component=round(gaze_comp, 3),
            pose_component=round(pose_comp, 3),
            motion_component=round(motion_comp, 3),
            acoustic_component=round(acoustic_comp, 3),
            penalties_applied=round(penalties, 3),
            is_drowsy=behavior.is_drowsy,
            is_distracted=is_distracted,
            attention_category=category,
        )

    def compute_classroom_snapshot(
        self,
        timestamp: float,
        student_scores: Dict[str, StudentEngagementScore],
        acoustic: AcousticSnapshot,
    ) -> ClassroomEngagementSnapshot:
        """Aggregates individual student scores into a classroom-level engagement snapshot."""
        if not student_scores:
            return ClassroomEngagementSnapshot(
                timestamp=round(timestamp, 2),
                average_engagement=0.0,
                high_engagement_count=0,
                moderate_engagement_count=0,
                low_engagement_count=0,
                disengaged_count=0,
                active_students_count=0,
                acoustic_state=acoustic.state,
                acoustic_speech_ratio=acoustic.speech_ratio,
                student_scores={},
            )

        scores = [s.smoothed_score for s in student_scores.values()]
        avg_score = sum(scores) / len(scores)

        # Apply classroom level smoothing
        if self._prev_classroom_average is not None:
            avg_score = 0.3 * avg_score + 0.7 * self._prev_classroom_average
        self._prev_classroom_average = avg_score

        high = sum(1 for s in student_scores.values() if s.attention_category == "HIGH")
        mod = sum(1 for s in student_scores.values() if s.attention_category == "MODERATE")
        low = sum(1 for s in student_scores.values() if s.attention_category == "LOW")
        dis = sum(1 for s in student_scores.values() if s.attention_category == "DISENGAGED")

        return ClassroomEngagementSnapshot(
            timestamp=round(timestamp, 2),
            average_engagement=round(avg_score, 1),
            high_engagement_count=high,
            moderate_engagement_count=mod,
            low_engagement_count=low,
            disengaged_count=dis,
            active_students_count=len(student_scores),
            acoustic_state=acoustic.state,
            acoustic_speech_ratio=acoustic.speech_ratio,
            student_scores=student_scores,
        )
