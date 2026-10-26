"""Vision processing module for classroom participant tracking and behavioral analysis."""
from .face_tracker import FaceTracker, ParticipantDetection
from .head_pose import HeadPoseEstimator, HeadPoseResult, GazeState
from .motion_analyzer import MotionAnalyzer, MotionState, BehavioralAnalysis
from .synthetic_video import SyntheticClassroomStream, ClassroomProfile

__all__ = [
    "FaceTracker",
    "ParticipantDetection",
    "HeadPoseEstimator",
    "HeadPoseResult",
    "GazeState",
    "MotionAnalyzer",
    "BehavioralAnalysis",
    "MotionState",
    "SyntheticClassroomStream",
    "ClassroomProfile",
]
