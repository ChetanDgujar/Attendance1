"""Tests for DatabaseManager and DataExporter."""
import unittest
import tempfile
from pathlib import Path
from src.storage.database import DatabaseManager
from src.storage.exporter import DataExporter


class TestStorageModule(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test_classroom.db"
        self.db = DatabaseManager(str(self.db_path))
        self.exporter = DataExporter(self.db)

    def tearDown(self):
        try:
            self.tmpdir.cleanup()
        except Exception:
            pass

    def test_session_lifecycle(self):
        self.db.create_session("SESS-01", "Math Class", 1000.0, "demo")
        sess = self.db.get_session("SESS-01")
        self.assertIsNotNone(sess)
        self.assertEqual(sess["name"], "Math Class")

        self.db.close_session("SESS-01", 1060.0, 82.5, 90.0)
        updated = self.db.get_session("SESS-01")
        self.assertEqual(updated["duration_sec"], 60.0)
        self.assertEqual(updated["avg_engagement"], 82.5)

    def test_attendance_and_export(self):
        self.db.create_session("SESS-02", "History", 0.0)
        records = [
            {"student_id": "STU-1", "display_name": "Alice", "status": "PRESENT", "first_seen": 0.0, "last_seen": 60.0, "total_active_seconds": 60.0, "presence_ratio": 1.0, "confidence": 0.99},
            {"student_id": "STU-2", "display_name": "Bob", "status": "ABSENT", "first_seen": None, "last_seen": None, "total_active_seconds": 0.0, "presence_ratio": 0.0, "confidence": 1.0},
        ]
        self.db.save_attendance_records("SESS-02", records)

        saved = self.db.get_attendance_records("SESS-02")
        self.assertEqual(len(saved), 2)

        # Test CSV export
        csv_file = Path(self.tmpdir.name) / "attendance.csv"
        self.exporter.export_attendance_csv("SESS-02", str(csv_file))
        self.assertTrue(csv_file.exists())
        content = csv_file.read_text(encoding="utf-8")
        self.assertIn("STU-1", content)
        self.assertIn("Alice", content)

    def test_cleanup_retention(self):
        # Create session with old timestamp (e.g. 40 days ago)
        self.db.create_session("SESS-OLD", "Old Session", 0.0)
        # Verify cleanup method runs safely
        cleaned = self.db.cleanup_old_sessions(retention_days=1)
        self.assertIsInstance(cleaned, int)


if __name__ == "__main__":
    unittest.main()
