"""Tests for vision module: FaceTracker, HeadPoseEstimator, MotionAnalyzer."""
import unittest
from src.vision.face_tracker import FaceTracker
from src.vision.head_pose import HeadPoseEstimator, GazeState
from src.vision.motion_analyzer import MotionAnalyzer, MotionState


class TestVisionModule(unittest.TestCase):

    def test_face_tracker_association(self):
        tracker = FaceTracker(iou_threshold=0.2, distance_threshold=0.3)
        # Frame 1: student at (0.2, 0.2, 0.1, 0.1)
        dets1 = [{"bbox": (0.2, 0.2, 0.1, 0.1), "confidence": 0.9, "student_id": "STU-A"}]
        tracks1 = tracker.update(dets1, current_timestamp=0.0)
        self.assertEqual(len(tracks1), 1)
        track_id = tracks1[0].track_id

        # Frame 2: slightly shifted (0.21, 0.20, 0.1, 0.1)
        dets2 = [{"bbox": (0.21, 0.20, 0.1, 0.1), "confidence": 0.92, "student_id": "STU-A"}]
        tracks2 = tracker.update(dets2, current_timestamp=0.2)
        self.assertEqual(len(tracks2), 1)
        # Same track id must persist
        self.assertEqual(tracks2[0].track_id, track_id)
        self.assertEqual(tracks2[0].total_detections, 2)

    def test_head_pose_classification(self):
        estimator = HeadPoseEstimator(yaw_limit_deg=25.0, pitch_down_limit_deg=-20.0)

        # Frontal focus
        res_front = estimator.estimate_from_angles(yaw=5.0, pitch=3.0)
        self.assertEqual(res_front.gaze_state, GazeState.FOCUSED)
        self.assertGreater(res_front.focus_score, 0.85)

        # Distracted Left
        res_left = estimator.estimate_from_angles(yaw=-35.0, pitch=0.0)
        self.assertEqual(res_left.gaze_state, GazeState.DISTRACTED_LEFT)
        self.assertLess(res_left.focus_score, 0.80)

        # Looking Down
        res_down = estimator.estimate_from_angles(yaw=0.0, pitch=-30.0)
        self.assertEqual(res_down.gaze_state, GazeState.LOOKING_DOWN)
        self.assertLess(res_down.focus_score, 0.80)

    def test_motion_analyzer_and_drowsiness(self):
        analyzer = MotionAnalyzer(inactivity_drowsiness_sec=5.0, static_threshold=0.05)

        # Normal active movement
        b1 = analyzer.update_motion(1, (0.2, 0.2, 0.1, 0.1), GazeState.FOCUSED, timestamp=0.0)
        b2 = analyzer.update_motion(1, (0.24, 0.21, 0.1, 0.1), GazeState.FOCUSED, timestamp=1.0)
        self.assertFalse(b2.is_drowsy)

        # Prolonged downward posture without motion -> triggers drowsiness
        for t in range(2, 9):
            b_drowsy = analyzer.update_motion(
                1, (0.24, 0.21, 0.1, 0.1), GazeState.LOOKING_DOWN, timestamp=float(t)
            )

        self.assertTrue(b_drowsy.is_drowsy)
        self.assertEqual(b_drowsy.motion_state, MotionState.DROWSY_SUSPECTED)


if __name__ == "__main__":
    unittest.main()
