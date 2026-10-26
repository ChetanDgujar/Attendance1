"""Tests for AttendanceManager: sustained presence, anti-glitch rejection, and exports."""
import unittest
import tempfile
from pathlib import Path
from src.attendance.attendance_manager import AttendanceManager, AttendanceStatus


class TestAttendanceManager(unittest.TestCase):

    def setUp(self):
        self.mgr = AttendanceManager(
            sustained_window_sec=5.0,
            sustained_min_ratio=0.50,
            tardy_grace_period_sec=10.0,
        )
        self.roster = [
            {"student_id": "STU-1", "name": "Alice"},
            {"student_id": "STU-2", "name": "Bob"},
            {"student_id": "STU-3", "name": "Charlie"},
        ]
        self.mgr.load_roster(self.roster)

    def test_roster_loaded_as_absent_initially(self):
        for s_id in ["STU-1", "STU-2", "STU-3"]:
            self.assertIn(s_id, self.mgr.records)
            self.assertEqual(self.mgr.records[s_id].status, AttendanceStatus.ABSENT)

    def test_sustained_presence_marks_present(self):
        # STU-1 detected from t=0 to t=8 (8 seconds > 5.0s sustained threshold)
        for t in range(9):
            self.mgr.register_frame({"STU-1"}, float(t))
        self.mgr.finalize_session(8.0)

        rec = self.mgr.records["STU-1"]
        self.assertEqual(rec.status, AttendanceStatus.PRESENT)
        self.assertGreater(rec.confidence, 0.70)
        self.assertGreater(rec.total_active_seconds, 5.0)

    def test_transient_appearance_marked_transient_ignored(self):
        # GUEST-PASS appears only at t=2.0 and t=3.0 (1.0 second total active time)
        self.mgr.register_frame({"STU-1", "GUEST-PASS"}, 0.0)
        self.mgr.register_frame({"STU-1", "GUEST-PASS"}, 1.0)
        # Session continues until t=12 without GUEST-PASS
        for t in range(2, 13):
            self.mgr.register_frame({"STU-1"}, float(t))
        self.mgr.finalize_session(12.0)

        passerby = self.mgr.records["GUEST-PASS"]
        self.assertEqual(passerby.status, AttendanceStatus.TRANSIENT_IGNORED)

    def test_tardy_status(self):
        # STU-2 arrives at t=15 (grace period is 10s) and stays until t=25
        for t in range(0, 15):
            self.mgr.register_frame({"STU-1"}, float(t))
        for t in range(15, 26):
            self.mgr.register_frame({"STU-1", "STU-2"}, float(t))
        self.mgr.finalize_session(25.0)

        rec2 = self.mgr.records["STU-2"]
        self.assertEqual(rec2.status, AttendanceStatus.TARDY)

    def test_export_csv_and_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "test_attendance.csv"
            json_path = Path(tmpdir) / "test_attendance.json"

            self.mgr.register_frame({"STU-1"}, 0.0)
            self.mgr.register_frame({"STU-1"}, 6.0)
            self.mgr.finalize_session(6.0)

            self.mgr.export_csv(str(csv_file := csv_path))
            self.mgr.export_json(str(json_path))

            self.assertTrue(csv_file.exists())
            self.assertTrue(json_path.exists())
            content = csv_file.read_text(encoding="utf-8")
            self.assertIn("STU-1", content)
            self.assertIn("PRESENT", content)


if __name__ == "__main__":
    unittest.main()
