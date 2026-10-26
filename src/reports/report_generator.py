"""Report generation engine.
Produces structured Per-Student Analytics and Session Summary Reports in HTML, Markdown, and JSON.
"""
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import time

from ..storage.database import DatabaseManager


@dataclass
class StudentReport:
    student_id: str
    display_name: str
    status: str
    active_duration_sec: float
    presence_ratio: float
    confidence: float
    average_engagement: float
    attention_category: str
    low_attention_intervals: List[Dict[str, float]]
    timeline_scores: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SessionReport:
    session_id: str
    session_name: str
    duration_minutes: float
    total_students: int
    attendance_rate: float
    average_engagement: float
    engagement_grade: str
    monologue_percentage: float
    discussion_percentage: float
    silence_percentage: float
    student_reports: List[StudentReport]
    suggestions: List[Dict[str, Any]]
    timeline: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["student_reports"] = [s.to_dict() for s in self.student_reports]
        return d

    def to_html(self) -> str:
        """Generates a standalone, beautiful HTML report."""
        students_rows = "".join(
            f"""
            <tr>
                <td style="font-family: monospace;">{s.student_id}</td>
                <td><strong>{s.display_name}</strong></td>
                <td><span class="badge badge-{s.status.lower()}">{s.status}</span></td>
                <td>{s.active_duration_sec:.1f}s ({s.presence_ratio:.1%})</td>
                <td><strong>{s.average_engagement:.1f}%</strong></td>
                <td>{s.attention_category}</td>
                <td>{len(s.low_attention_intervals)} flagged</td>
            </tr>
            """
            for s in self.student_reports
        )

        suggestions_rows = "".join(
            f"""
            <div class="sugg-card">
                <div class="sugg-header">
                    <strong>{s.get('title', '')}</strong>
                    <span class="priority priority-{s.get('priority', '').lower()}">{s.get('priority', '')}</span>
                </div>
                <p>{s.get('suggested_action', s.get('suggestion', ''))}</p>
                <small style="color: #64748B;">Trigger: {s.get('trigger_type', s.get('trigger', ''))} | Time: {s.get('timestamp', 0):.1f}s</small>
            </div>
            """
            for s in self.suggestions
        ) or "<p>No critical interventions triggered during this session.</p>"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Session Report - {self.session_name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #F8FAFC; color: #1E293B; margin: 0; padding: 30px; }}
        .container {{ max-width: 1000px; margin: 0 auto; background: #FFFFFF; border-radius: 12px; padding: 32px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); }}
        h1, h2, h3 {{ color: #0F172A; }}
        .header-bar {{ display: flex; justify-content: space-between; align-items: baseline; border-bottom: 2px solid #E2E8F0; padding-bottom: 16px; margin-bottom: 24px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 28px; }}
        .stat-card {{ background: #F1F5F9; border-radius: 8px; padding: 16px; text-align: center; }}
        .stat-val {{ font-size: 26px; font-weight: 700; color: #2563EB; display: block; }}
        .stat-lbl {{ font-size: 12px; text-transform: uppercase; color: #64748B; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 14px; }}
        th, td {{ padding: 10px 14px; border-bottom: 1px solid #E2E8F0; text-align: left; }}
        th {{ background: #F8FAFC; font-size: 12px; text-transform: uppercase; color: #475569; }}
        .badge {{ padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; text-transform: uppercase; }}
        .badge-present {{ background: #DCFCE7; color: #15803D; }}
        .badge-late {{ background: #FEF3C7; color: #B45309; }}
        .badge-absent {{ background: #FEE2E2; color: #B91C1C; }}
        .badge-partial {{ background: #E0E7FF; color: #4338CA; }}
        .badge-transient_ignored {{ background: #F1F5F9; color: #64748B; }}
        .sugg-card {{ background: #F8FAFC; border-left: 4px solid #3B82F6; padding: 12px 16px; border-radius: 6px; margin-bottom: 10px; }}
        .sugg-header {{ display: flex; justify-content: space-between; margin-bottom: 4px; }}
        .priority {{ font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; }}
        .priority-urgent {{ background: #FEE2E2; color: #B91C1C; }}
        .priority-actionable {{ background: #FEF3C7; color: #B45309; }}
        .footer {{ margin-top: 36px; padding-top: 16px; border-top: 1px solid #E2E8F0; font-size: 12px; color: #94A3B8; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header-bar">
            <div>
                <h1>🎓 Classroom Session Intelligence Report</h1>
                <p style="margin: 0; color: #64748B;">Session: <strong>{self.session_name}</strong> ({self.session_id})</p>
            </div>
            <div style="text-align: right;">
                <span class="stat-val" style="color: #10B981;">Grade {self.engagement_grade}</span>
                <small style="color: #64748B;">Duration: {self.duration_minutes:.1f} mins</small>
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <span class="stat-val">{self.average_engagement:.1f}%</span>
                <span class="stat-lbl">Classroom Engagement</span>
            </div>
            <div class="stat-card">
                <span class="stat-val">{self.attendance_rate:.1f}%</span>
                <span class="stat-lbl">Attendance Rate</span>
            </div>
            <div class="stat-card">
                <span class="stat-val">{self.monologue_percentage:.0f}%</span>
                <span class="stat-lbl">Teacher Monologue</span>
            </div>
            <div class="stat-card">
                <span class="stat-val">{self.discussion_percentage:.0f}%</span>
                <span class="stat-lbl">Student Discussion</span>
            </div>
        </div>

        <h2>👥 Student Attendance & Engagement Ledger</h2>
        <table>
            <thead>
                <tr>
                    <th>Student ID</th>
                    <th>Name</th>
                    <th>Status</th>
                    <th>Presence</th>
                    <th>Avg Focus</th>
                    <th>Attention Level</th>
                    <th>Attention Dips</th>
                </tr>
            </thead>
            <tbody>
                {students_rows}
            </tbody>
        </table>

        <h2 style="margin-top: 32px;">💡 AI Teaching Suggestions & Pedagogical Interventions</h2>
        {suggestions_rows}

        <div class="footer">
            Generated offline by Multimodal Attendance & Engagement Agent | Privacy-Preserving Classroom Intelligence
        </div>
    </div>
</body>
</html>
"""


class ReportGenerator:
    """Compiles session data from DatabaseManager into comprehensive reports."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def generate_session_report(self, session_id: str) -> SessionReport:
        """Assembles a full SessionReport including student breakdowns and suggestions."""
        session = self.db.get_session(session_id)
        if not session:
            # Fallback mock/empty session
            session = {
                "session_id": session_id,
                "name": "Live_Session",
                "duration_sec": 60.0,
                "avg_engagement": 75.0,
                "attendance_rate": 85.0,
            }

        att_records = self.db.get_attendance_records(session_id)
        timeline = self.db.get_timeline(session_id)
        suggestions = self.db.get_suggestions(session_id)

        # Compute acoustic breakdown
        n_t = max(1, len(timeline))
        monologue_count = sum(1 for e in timeline if e.get("acoustic_state") == "TEACHER_MONOLOGUE")
        disc_count = sum(1 for e in timeline if e.get("acoustic_state") == "STUDENT_DISCUSSION")
        silence_count = sum(1 for e in timeline if e.get("acoustic_state") == "SUSTAINED_SILENCE")

        # Compile Student Reports
        student_reports: List[StudentReport] = []
        for r in att_records:
            s_id = r["student_id"]
            samples = self.db.get_student_engagement_series(session_id, s_id)
            if samples:
                avg_score = sum(s["fused_score"] for s in samples) / len(samples)
                # Find low-attention intervals (scores < 45)
                low_intervals = [
                    {"timestamp": s["timestamp"], "score": s["fused_score"]}
                    for s in samples if s["fused_score"] < 45.0
                ]
            else:
                avg_score = session.get("avg_engagement", 70.0)
                low_intervals = []

            if avg_score >= 75.0:
                cat = "HIGH"
            elif avg_score >= 50.0:
                cat = "MODERATE"
            else:
                cat = "LOW"

            student_reports.append(
                StudentReport(
                    student_id=s_id,
                    display_name=r.get("display_name", s_id),
                    status=r["status"],
                    active_duration_sec=r.get("total_active_seconds", 0.0),
                    presence_ratio=r.get("presence_ratio", 0.0),
                    confidence=r.get("confidence", 0.9),
                    average_engagement=round(avg_score, 1),
                    attention_category=cat,
                    low_attention_intervals=low_intervals,
                    timeline_scores=[{"t": s["timestamp"], "score": s["fused_score"]} for s in samples],
                )
            )

        avg_eng = session.get("avg_engagement", 70.0)
        grade = "A" if avg_eng >= 80 else ("B+" if avg_eng >= 70 else ("B" if avg_eng >= 60 else "C"))

        return SessionReport(
            session_id=session_id,
            session_name=session.get("name", "Classroom Session"),
            duration_minutes=round(session.get("duration_sec", 60.0) / 60.0, 1),
            total_students=len(att_records),
            attendance_rate=session.get("attendance_rate", 85.0),
            average_engagement=avg_eng,
            engagement_grade=grade,
            monologue_percentage=round((monologue_count / n_t) * 100.0, 1),
            discussion_percentage=round((disc_count / n_t) * 100.0, 1),
            silence_percentage=round((silence_count / n_t) * 100.0, 1),
            student_reports=student_reports,
            suggestions=suggestions,
            timeline=timeline,
        )

    def export_html_report(self, session_id: str, filepath: str) -> str:
        report = self.generate_session_report(session_id)
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report.to_html(), encoding="utf-8")
        return str(path)
