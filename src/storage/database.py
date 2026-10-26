"""SQLite database manager for classroom intelligence telemetry and attendance.
Provides structured storage, queries, and automated data retention cleanup.
"""
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import datetime
import sqlite3
import time


class DatabaseManager:
    """Manages SQLite storage for classroom sessions, attendance, and multimodal telemetry."""

    def __init__(self, db_path: str = "data/classroom.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_db(self):
        """Initializes database schema with indexing."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Sessions Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                start_time REAL NOT NULL,
                end_time REAL,
                duration_sec REAL,
                source_type TEXT DEFAULT 'demo',
                avg_engagement REAL DEFAULT 0.0,
                attendance_rate REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # 2. Students Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                privacy_hash TEXT NOT NULL,
                enrolled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # 3. Attendance Records Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                student_id TEXT NOT NULL,
                status TEXT NOT NULL,
                first_seen REAL,
                last_seen REAL,
                total_active_seconds REAL NOT NULL,
                presence_ratio REAL NOT NULL,
                confidence REAL NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id),
                FOREIGN KEY (student_id) REFERENCES students(student_id)
            )
            """)

            # 4. Engagement Samples Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS engagement_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                student_id TEXT NOT NULL,
                gaze_score REAL NOT NULL,
                pose_score REAL NOT NULL,
                motion_score REAL NOT NULL,
                acoustic_score REAL NOT NULL,
                fused_score REAL NOT NULL,
                is_drowsy INTEGER DEFAULT 0,
                is_distracted INTEGER DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
            """)

            # 5. Classroom Timeline Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS classroom_timeline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                avg_engagement REAL NOT NULL,
                acoustic_state TEXT NOT NULL,
                speech_ratio REAL NOT NULL,
                active_count INTEGER NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
            """)

            # 6. Teaching Suggestions Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS teaching_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                trigger_type TEXT NOT NULL,
                priority TEXT NOT NULL,
                title TEXT NOT NULL,
                evidence TEXT NOT NULL,
                suggested_action TEXT NOT NULL,
                confidence REAL DEFAULT 0.90,
                acknowledged INTEGER DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
            """)

            # Indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_att_sess ON attendance_records(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_eng_sess ON engagement_samples(session_id, timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_time_sess ON classroom_timeline(session_id, timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sugg_sess ON teaching_suggestions(session_id)")
            conn.commit()

    # --- Session Management ---

    def create_session(self, session_id: str, name: str, start_time: float, source_type: str = "demo"):
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sessions (session_id, name, start_time, source_type) VALUES (?, ?, ?, ?)",
                (session_id, name, start_time, source_type),
            )
            conn.commit()

    def close_session(self, session_id: str, end_time: float, avg_engagement: float, attendance_rate: float):
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE sessions 
                SET end_time = ?, duration_sec = (? - start_time), avg_engagement = ?, attendance_rate = ?
                WHERE session_id = ?
                """,
                (end_time, end_time, avg_engagement, attendance_rate, session_id),
            )
            conn.commit()

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
            return dict(row) if row else None

    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    # --- Students & Attendance ---

    def upsert_student(self, student_id: str, display_name: str, privacy_hash: str, enrolled: bool = True):
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO students (student_id, display_name, privacy_hash, enrolled)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(student_id) DO UPDATE SET display_name=excluded.display_name, privacy_hash=excluded.privacy_hash
                """,
                (student_id, display_name, privacy_hash, 1 if enrolled else 0),
            )
            conn.commit()

    def save_attendance_records(self, session_id: str, records: List[Dict[str, Any]]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for r in records:
                # Ensure student exists
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO students (student_id, display_name, privacy_hash, enrolled)
                    VALUES (?, ?, ?, 1)
                    """,
                    (r["student_id"], r["display_name"], r.get("privacy_hash", "")),
                )
                cursor.execute(
                    """
                    INSERT INTO attendance_records 
                    (session_id, student_id, status, first_seen, last_seen, total_active_seconds, presence_ratio, confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        r["student_id"],
                        r["status"],
                        r.get("first_seen"),
                        r.get("last_seen"),
                        r.get("total_active_seconds", 0.0),
                        r.get("presence_ratio", 0.0),
                        r.get("confidence", 0.9),
                    ),
                )
            conn.commit()

    def get_attendance_records(self, session_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT a.*, s.display_name, s.privacy_hash 
                FROM attendance_records a
                JOIN students s ON a.student_id = s.student_id
                WHERE a.session_id = ?
                ORDER BY a.student_id ASC
                """,
                (session_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    # --- Engagement Telemetry ---

    def save_engagement_sample(
        self,
        session_id: str,
        timestamp: float,
        student_id: str,
        gaze_score: float,
        pose_score: float,
        motion_score: float,
        acoustic_score: float,
        fused_score: float,
        is_drowsy: bool,
        is_distracted: bool,
    ):
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO engagement_samples 
                (session_id, timestamp, student_id, gaze_score, pose_score, motion_score, acoustic_score, fused_score, is_drowsy, is_distracted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    timestamp,
                    student_id,
                    gaze_score,
                    pose_score,
                    motion_score,
                    acoustic_score,
                    fused_score,
                    1 if is_drowsy else 0,
                    1 if is_distracted else 0,
                ),
            )
            conn.commit()

    def save_timeline_entry(
        self,
        session_id: str,
        timestamp: float,
        avg_engagement: float,
        acoustic_state: str,
        speech_ratio: float,
        active_count: int,
    ):
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO classroom_timeline (session_id, timestamp, avg_engagement, acoustic_state, speech_ratio, active_count)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, timestamp, avg_engagement, acoustic_state, speech_ratio, active_count),
            )
            conn.commit()

    def get_timeline(self, session_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM classroom_timeline WHERE session_id = ? ORDER BY timestamp ASC",
                (session_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_student_engagement_series(self, session_id: str, student_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM engagement_samples WHERE session_id = ? AND student_id = ? ORDER BY timestamp ASC",
                (session_id, student_id),
            ).fetchall()
            return [dict(r) for r in rows]

    # --- Suggestions ---

    def save_suggestion(
        self,
        session_id: str,
        timestamp: float,
        trigger_type: str,
        priority: str,
        title: str,
        evidence: str,
        suggested_action: str,
        confidence: float = 0.90,
    ):
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO teaching_suggestions 
                (session_id, timestamp, trigger_type, priority, title, evidence, suggested_action, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, timestamp, trigger_type, priority, title, evidence, suggested_action, confidence),
            )
            conn.commit()

    def get_suggestions(self, session_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM teaching_suggestions WHERE session_id = ? ORDER BY timestamp DESC",
                (session_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    # --- Automated Retention Cleanup ---

    def cleanup_old_sessions(self, retention_days: int = 30) -> int:
        """Deletes sessions and related telemetry older than retention_days."""
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=retention_days)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Find expired sessions
            rows = cursor.execute(
                "SELECT session_id FROM sessions WHERE created_at < ?", (cutoff_date,)
            ).fetchall()
            expired_ids = [r["session_id"] for r in rows]

            if not expired_ids:
                return 0

            placeholders = ",".join("?" for _ in expired_ids)
            cursor.execute(f"DELETE FROM attendance_records WHERE session_id IN ({placeholders})", expired_ids)
            cursor.execute(f"DELETE FROM engagement_samples WHERE session_id IN ({placeholders})", expired_ids)
            cursor.execute(f"DELETE FROM classroom_timeline WHERE session_id IN ({placeholders})", expired_ids)
            cursor.execute(f"DELETE FROM teaching_suggestions WHERE session_id IN ({placeholders})", expired_ids)
            cursor.execute(f"DELETE FROM sessions WHERE session_id IN ({placeholders})", expired_ids)
            conn.commit()
            return len(expired_ids)
