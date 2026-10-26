"""Tests for ReportGenerator and HTML/JSON report formats."""
import unittest
import tempfile
from pathlib import Path
from src.storage.database import DatabaseManager
from src.reports.report_generator import ReportGenerator


class TestReportsModule(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test_reports.db"
        self.db = DatabaseManager(str(self.db_path))
        self.report_gen = ReportGenerator(self.db)

        # Seed test session
        self.db.create_session("SESS-REP", "Physics 101", 0.0)
        self.db.save_attendance_records("SESS-REP", [
            {"student_id": "STU-A", "display_name": "Alex", "status": "PRESENT", "first_seen": 0.0, "last_seen": 60.0, "total_active_seconds": 60.0, "presence_ratio": 1.0, "confidence": 0.99},
        ])
        self.db.save_timeline_entry("SESS-REP", 10.0, 80.0, "STUDENT_DISCUSSION", 0.5, 1)
        self.db.close_session("SESS-REP", 60.0, 80.0, 100.0)

    def tearDown(self):
        try:
            self.tmpdir.cleanup()
        except Exception:
            pass

    def test_session_report_generation(self):
        rep = self.report_gen.generate_session_report("SESS-REP")
        self.assertEqual(rep.session_id, "SESS-REP")
        self.assertEqual(rep.engagement_grade, "A")
        self.assertEqual(len(rep.student_reports), 1)

    def test_export_html_report(self):
        html_out = Path(self.tmpdir.name) / "report.html"
        self.report_gen.export_html_report("SESS-REP", str(html_out))
        self.assertTrue(html_out.exists())
        content = html_out.read_text(encoding="utf-8")
        self.assertIn("Physics 101", content)
        self.assertIn("Alex", content)
        self.assertIn("Classroom Session Intelligence Report", content)


if __name__ == "__main__":
    unittest.main()
