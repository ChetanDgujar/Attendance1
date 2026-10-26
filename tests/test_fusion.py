"""Tests for MultimodalFusionEngine and SessionTimelineTracker."""
import unittest
from src.fusion.multimodal_fusion import MultimodalFusionEngine
from src.fusion.session_timeline import SessionTimelineTracker, EventType
from src.vision.head_pose import HeadPoseResult, GazeState
from src.vision.motion_analyzer import BehavioralAnalysis, MotionState
from src.audio.acoustic_classifier import AcousticSnapshot, AcousticState


class TestFusionModule(unittest.TestCase):

    def setUp(self):
        self.fusion = MultimodalFusionEngine()
        self.timeline = SessionTimelineTracker(attention_dip_threshold=50.0, interaction_peak_threshold=75.0)

    def test_high_engagement_score_computation(self):
        head = HeadPoseResult(0.0, 0.0, 0.0, GazeState.FOCUSED, 1.0, True)
        motion = BehavioralAnalysis(1, 0.3, MotionState.OPTIMAL_ENGAGEMENT, 0.0, False, False, 0.95)
        acoustic = AcousticSnapshot(0.0, AcousticState.BALANCED_ENGAGEMENT, 0.4, 0.03, 0.0, 0.0, 4, "OK")

        score = self.fusion.compute_student_engagement("STU-101", 1, head, motion, acoustic)
        self.assertGreaterEqual(score.smoothed_score, 75.0)
        self.assertEqual(score.attention_category, "HIGH")

    def test_drowsiness_penalty_reduces_score(self):
        head = HeadPoseResult(0.0, -25.0, 0.0, GazeState.LOOKING_DOWN, 0.4, False)
        motion = BehavioralAnalysis(1, 0.01, MotionState.DROWSY_SUSPECTED, 15.0, True, False, 0.2)
        acoustic = AcousticSnapshot(0.0, AcousticState.TEACHER_MONOLOGUE, 0.6, 0.03, 50.0, 0.0, 1, "OK")

        score = self.fusion.compute_student_engagement("STU-101", 1, head, motion, acoustic)
        self.assertLess(score.smoothed_score, 45.0)
        self.assertTrue(score.is_drowsy)

    def test_timeline_attention_drop_event(self):
        # Feed snapshots below threshold for 10 consecutive ticks
        events = []
        for i in range(12):
            t = float(i)
            snap = self.fusion.compute_classroom_snapshot(
                t,
                student_scores={},
                acoustic=AcousticSnapshot(t, AcousticState.BALANCED_ENGAGEMENT, 0.0, 0.0, 0.0, 0.0, 0, ""),
            )
            # Simulate active students with low score
            snap.average_engagement = 35.0
            snap.active_students_count = 5
            snap.low_engagement_count = 5
            evs = self.timeline.record_snapshot(snap, dt=1.0)
            events.extend(evs)

        types = [e.event_type for e in events]
        self.assertIn(EventType.ATTENTION_DROP, types)


if __name__ == "__main__":
    unittest.main()
