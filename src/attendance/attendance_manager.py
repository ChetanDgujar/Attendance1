"""Automated attendance tracking engine with sustained presence verification.
Eliminates single-frame false positives, tracks presence windows, and generates
timestamped attendance logs with privacy hashing.
"""
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
import csv
import json
import time

from ..privacy.anonymizer import PrivacyEngine


class AttendanceStatus(str, Enum):
    PRESENT = "PRESENT"
    TARDY = "TARDY"
    ABSENT = "ABSENT"
    TRANSIENT_IGNORED = "TRANSIENT_IGNORED"


@dataclass
class StudentAttendanceRecord:
    student_id: str
    display_name: str
    privacy_hash: str
    first_seen: Optional[float] = None
    last_seen: Optional[float] = None
    total_active_seconds: float = 0.0
    presence_ratio: float = 0.0
    status: AttendanceStatus = AttendanceStatus.ABSENT
    confidence: float = 0.0
    sustained_intervals: List[Tuple[float, float]] = field(default_factory=list)
    enrolled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


class AttendanceManager:
    """Manages classroom roll call, sliding window persistence, and attendance logs."""

    def __init__(
        self,
        sustained_window_sec: float = 10.0,
        sustained_min_ratio: float = 0.60,
        tardy_grace_period_sec: float = 300.0,
        privacy_engine: Optional[PrivacyEngine] = None,
    ):
        self.sustained_window_sec = sustained_window_sec
        self.sustained_min_ratio = sustained_min_ratio
        self.tardy_grace_period_sec = tardy_grace_period_sec
        self.privacy = privacy_engine or PrivacyEngine()

        self.records: Dict[str, StudentAttendanceRecord] = {}
        self.session_start_time: Optional[float] = None
        self.session_end_time: Optional[float] = None
        self._last_frame_time: Optional[float] = None
        self._active_intervals: Dict[str, float] = {}  # student_id -> start_time

    def load_roster(self, roster: List[Dict[str, str]]):
        """Loads enrolled students from a roster dictionary or file.
        Each entry has 'student_id' and 'name'.
        """
        for item in roster:
            s_id = item["student_id"]
            name = item.get("name", s_id)
            disp_name = self.privacy.get_display_name(s_id, name)
            p_hash = self.privacy.hash_identity(s_id)

            self.records[s_id] = StudentAttendanceRecord(
                student_id=s_id,
                display_name=disp_name,
                privacy_hash=p_hash,
                enrolled=True,
            )

    def register_frame(self, detected_student_ids: Set[str], timestamp: float):
        """Updates attendance observations for the given timestamp."""
        if self.session_start_time is None:
            self.session_start_time = timestamp

        dt = 0.0
        if self._last_frame_time is not None:
            dt = max(0.0, timestamp - self._last_frame_time)
        self._last_frame_time = timestamp

        # Process detected students
        for s_id in detected_student_ids:
            if s_id not in self.records:
                # Unenrolled / visitor
                disp = self.privacy.get_display_name(s_id, s_id)
                self.records[s_id] = StudentAttendanceRecord(
                    student_id=s_id,
                    display_name=disp,
                    privacy_hash=self.privacy.hash_identity(s_id),
                    enrolled=False,
                )

            rec = self.records[s_id]
            if rec.first_seen is None:
                rec.first_seen = timestamp
                self._active_intervals[s_id] = timestamp

            rec.last_seen = timestamp
            rec.total_active_seconds += dt

        # Close intervals for students no longer detected in this frame
        closed_ids = []
        for s_id, start_t in self._active_intervals.items():
            if s_id not in detected_student_ids:
                if s_id in self.records:
                    rec = self.records[s_id]
                    rec.sustained_intervals.append((round(start_t, 2), round(timestamp, 2)))
                closed_ids.append(s_id)
        for s_id in closed_ids:
            del self._active_intervals[s_id]

        # Re-evaluate statuses
        session_elapsed = max(1.0, timestamp - self.session_start_time)
        self._recalculate_statuses(session_elapsed)

    def _recalculate_statuses(self, session_elapsed: float):
        for rec in self.records.values():
            if rec.first_seen is None or rec.total_active_seconds < 1e-3:
                rec.status = AttendanceStatus.ABSENT
                rec.confidence = 1.0
                rec.presence_ratio = 0.0
                continue

            # Check if appearance was purely transient (less than minimum sustained window)
            if rec.total_active_seconds < self.sustained_window_sec and session_elapsed > self.sustained_window_sec:
                rec.status = AttendanceStatus.TRANSIENT_IGNORED
                rec.confidence = 0.90
                rec.presence_ratio = round(rec.total_active_seconds / session_elapsed, 3)
                continue

            # Presence ratio over elapsed session
            ratio = rec.total_active_seconds / session_elapsed
            rec.presence_ratio = round(min(1.0, ratio), 3)

            # Check Tardy: arrived after grace period
            rel_arrival = rec.first_seen - (self.session_start_time or 0.0)
            is_tardy = rel_arrival > self.tardy_grace_period_sec

            if rec.total_active_seconds >= self.sustained_window_sec and ratio >= (self.sustained_min_ratio * 0.5):
                rec.status = AttendanceStatus.TARDY if is_tardy else AttendanceStatus.PRESENT
                # Confidence proportional to sustained presence ratio
                rec.confidence = round(min(0.99, 0.70 + (rec.presence_ratio * 0.29)), 3)
            else:
                rec.status = AttendanceStatus.ABSENT
                rec.confidence = 0.80

    def finalize_session(self, end_timestamp: float):
        """Finalizes all active attendance records when session ends."""
        self.session_end_time = end_timestamp
        for s_id, start_t in list(self._active_intervals.items()):
            if s_id in self.records:
                self.records[s_id].sustained_intervals.append((round(start_t, 2), round(end_timestamp, 2)))
        self._active_intervals.clear()

        session_duration = max(1.0, (self.session_end_time or 0.0) - (self.session_start_time or 0.0))
        self._recalculate_statuses(session_duration)

    def get_summary(self) -> Dict[str, Any]:
        """Returns statistical overview of attendance."""
        total = len(self.records)
        present = sum(1 for r in self.records.values() if r.status == AttendanceStatus.PRESENT)
        tardy = sum(1 for r in self.records.values() if r.status == AttendanceStatus.TARDY)
        absent = sum(1 for r in self.records.values() if r.status == AttendanceStatus.ABSENT)
        transient = sum(1 for r in self.records.values() if r.status == AttendanceStatus.TRANSIENT_IGNORED)

        return {
            "total_students": total,
            "present_count": present,
            "tardy_count": tardy,
            "absent_count": absent,
            "transient_ignored_count": transient,
            "attendance_rate_percent": round(((present + tardy) / total * 100.0), 1) if total > 0 else 0.0,
        }

    def export_csv(self, filepath: str):
        """Exports timestamped attendance log to CSV."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
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
            for rec in self.records.values():
                writer.writerow([
                    rec.student_id,
                    rec.display_name,
                    rec.status.value,
                    f"{rec.first_seen:.1f}" if rec.first_seen is not None else "N/A",
                    f"{rec.last_seen:.1f}" if rec.last_seen is not None else "N/A",
                    f"{rec.total_active_seconds:.1f}",
                    f"{rec.presence_ratio:.2%}",
                    f"{rec.confidence:.2f}",
                    rec.privacy_hash[:16] + "...",
                ])

    def export_json(self, filepath: str):
        """Exports structured JSON attendance telemetry."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "session_start": self.session_start_time,
            "session_end": self.session_end_time,
            "summary": self.get_summary(),
            "records": [r.to_dict() for r in self.records.values()],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
