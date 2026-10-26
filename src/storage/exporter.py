"""Export suite for classroom intelligence telemetry.
Exports session logs to CSV, JSON, and prepares telemetry for reports.
"""
from pathlib import Path
from typing import Dict, List, Optional, Any
import csv
import json
import time

from .database import DatabaseManager


class DataExporter:
    """Handles structured data file exports from SQLite database."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def export_attendance_csv(self, session_id: str, filepath: str) -> str:
        """Exports attendance ledger for a given session to CSV."""
        records = self.db.get_attendance_records(session_id)
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Session ID",
                "Student ID",
                "Display Name",
                "Status",
                "First Seen (s)",
                "Last Seen (s)",
                "Active Duration (s)",
                "Presence Ratio",
                "Confidence",
                "Privacy Hash",
            ])
            for r in records:
                writer.writerow([
                    session_id,
                    r["student_id"],
                    r["display_name"],
                    r["status"],
                    f"{r['first_seen']:.1f}" if r.get("first_seen") is not None else "N/A",
                    f"{r['last_seen']:.1f}" if r.get("last_seen") is not None else "N/A",
                    f"{r['total_active_seconds']:.1f}",
                    f"{r['presence_ratio']:.2%}",
                    f"{r['confidence']:.2f}",
                    r.get("privacy_hash", "")[:16] + "...",
                ])
        return str(path)

    def export_session_json(self, session_id: str, filepath: str) -> str:
        """Exports full session metadata, attendance, timeline, and suggestions to JSON."""
        session = self.db.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found in database.")

        attendance = self.db.get_attendance_records(session_id)
        timeline = self.db.get_timeline(session_id)
        suggestions = self.db.get_suggestions(session_id)

        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "session": session,
            "attendance": attendance,
            "timeline": timeline,
            "suggestions": suggestions,
            "exported_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        return str(path)
