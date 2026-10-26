"""Tests for TeachingAgent and PedagogicalRuleEngine."""
import unittest
from src.agent.decision_rules import PedagogicalRuleEngine, RuleTrigger
from src.agent.teaching_agent import TeachingAgent
from src.fusion.multimodal_fusion import ClassroomEngagementSnapshot, StudentEngagementScore
from src.audio.acoustic_classifier import AcousticSnapshot, AcousticState
from src.attendance.attendance_manager import AttendanceManager


class TestTeachingAgent(unittest.TestCase):

    def setUp(self):
        self.rules = PedagogicalRuleEngine(
            attention_dip_threshold=50.0,
            monologue_limit_sec=60.0,
            silence_limit_sec=15.0,
        )
        self.agent = TeachingAgent(alert_cooldown_sec=5.0, rule_engine=self.rules)

    def test_prolonged_monologue_trigger(self):
        classroom = ClassroomEngagementSnapshot(
            timestamp=100.0,
            average_engagement=65.0,
            high_engagement_count=4,
            moderate_engagement_count=2,
            low_engagement_count=0,
            disengaged_count=0,
            active_students_count=6,
            acoustic_state=AcousticState.TEACHER_MONOLOGUE,
            acoustic_speech_ratio=0.8,
        )
        acoustic = AcousticSnapshot(
            timestamp=100.0,
            state=AcousticState.TEACHER_MONOLOGUE,
            speech_ratio=0.8,
            average_rms=0.04,
            monologue_duration_sec=75.0,
            silence_duration_sec=0.0,
            turn_taking_events=1,
            description="monologue",
        )

        suggestions = self.agent.evaluate_and_advise(classroom, acoustic)
        self.assertGreaterEqual(len(suggestions), 1)
        triggers = [s.trigger for s in suggestions]
        self.assertIn(RuleTrigger.PROLONGED_MONOLOGUE.value, triggers)

    def test_post_session_audit_generation(self):
        att = AttendanceManager()
        timeline = [
            {"timestamp": 0.0, "average_engagement": 75.0, "acoustic_state": "BALANCED_ENGAGEMENT"},
            {"timestamp": 30.0, "average_engagement": 80.0, "acoustic_state": "STUDENT_DISCUSSION"},
            {"timestamp": 60.0, "average_engagement": 72.0, "acoustic_state": "STUDENT_DISCUSSION"},
        ]
        audit = self.agent.generate_post_session_audit("TEST-SESS", timeline, att)
        self.assertEqual(audit.session_id, "TEST-SESS")
        self.assertIn(audit.engagement_grade, ["A", "B+", "B"])
        self.assertIn("Classroom Session Pedagogical Audit Report", audit.to_markdown())


if __name__ == "__main__":
    unittest.main()
