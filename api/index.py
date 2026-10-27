"""Vercel Serverless Function entrypoint for Multimodal Attendance & Engagement Agent.
Handles all /api/* requests on Vercel serverless environment.
"""
from http.server import BaseHTTPRequestHandler
from pathlib import Path
import json
import math
import os
import sys
import time
import urllib.parse

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import SystemConfig
from src.privacy.anonymizer import PrivacyEngine
from src.attendance.attendance_manager import AttendanceManager, AttendanceStatus
from src.vision.face_tracker import FaceTracker
from src.vision.head_pose import HeadPoseEstimator
from src.vision.motion_analyzer import MotionAnalyzer
from src.vision.synthetic_video import SyntheticClassroomStream
from src.audio.synthetic_audio import SyntheticAudioGenerator
from src.audio.acoustic_classifier import AcousticClassifier
from src.fusion.multimodal_fusion import MultimodalFusionEngine
from src.fusion.session_timeline import SessionTimelineTracker
from src.agent.teaching_agent import TeachingAgent

# Global state for serverless execution
_start_time = time.time()
_privacy_mode = False
_manual_overrides = {}


class handler(BaseHTTPRequestHandler):
    """Vercel serverless handler for /api/* routes."""

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        now = time.time()
        elapsed = now - _start_time

        # Simulation clock in [0, 60] seconds
        sim_t = elapsed % 60.0

        if path.endswith("/api/status") or path == "/api/status":
            self._send_json({
                "running": True,
                "paused": False,
                "session_time_seconds": round(elapsed, 1),
                "anonymize_privacy": _privacy_mode,
            })
        elif path.endswith("/api/telemetry") or path == "/api/telemetry":
            self._handle_telemetry(sim_t)
        elif path.endswith("/api/attendance") or path == "/api/attendance":
            self._handle_attendance(sim_t)
        elif path.endswith("/api/timeline") or path == "/api/timeline":
            self._handle_timeline(sim_t)
        elif path.endswith("/api/suggestions") or path == "/api/suggestions":
            self._handle_suggestions(sim_t)
        elif path.endswith("/api/audit") or path == "/api/audit":
            self._handle_audit()
        elif path.endswith("/api/download/attendance.csv"):
            self._handle_csv_download()
        else:
            self.send_error(404, "Endpoint not found")

    def do_POST(self):
        global _privacy_mode
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path.endswith("/api/action") or path == "/api/action":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode("utf-8")
            data = json.loads(body) if body else {}

            action = data.get("action")
            if action == "toggle_privacy":
                _privacy_mode = not _privacy_mode
                self._send_json({"success": True, "anonymize_privacy": _privacy_mode})
            elif action == "override_attendance":
                student_id = data.get("student_id")
                new_status = data.get("status", "PRESENT")
                if student_id:
                    _manual_overrides[student_id] = new_status.upper()
                self._send_json({"success": True, "student_id": student_id, "status": new_status})
            else:
                self._send_json({"success": True, "message": f"Action {action} acknowledged."})
        else:
            self.send_error(404, "Not Found")

    def _handle_telemetry(self, sim_t: float):
        # Compute dynamic engagement wave
        wave = math.sin(sim_t * 0.15)
        avg_eng = min(95.0, max(30.0, 75.0 + wave * 15.0 - (18.0 if 20 <= sim_t <= 35 else 0.0)))

        # Determine acoustic dynamic
        if sim_t < 15.0 or (38.0 <= sim_t < 48.0):
            ac_state = "TEACHER_MONOLOGUE"
            speech_ratio = 0.85
            rms = 0.045
            desc = "Instructional explanation in progress (sustained voice activity)."
        elif 15.0 <= sim_t < 22.0:
            ac_state = "SUSTAINED_SILENCE"
            speech_ratio = 0.05
            rms = 0.006
            desc = "Prolonged silence detected (20s). Consider offering a scaffolding prompt."
        elif 22.0 <= sim_t < 38.0:
            ac_state = "STUDENT_DISCUSSION"
            speech_ratio = 0.55
            rms = 0.065
            desc = "Active conversational exchange / collaborative peer debate underway."
        else:
            ac_state = "CHATTER_SURGE"
            speech_ratio = 0.88
            rms = 0.082
            desc = "High volume acoustic chatter surge detected across classroom."

        # Synthetic tracks
        students_meta = [
            ("STU-101", "Aarav Sharma", 0.20, 0.45, 92.0, "FOCUSED", False, False),
            ("STU-102", "Priya Patel", 0.40, 0.42, 88.0, "FOCUSED", False, False),
            ("STU-103", "Rohan Mehta", 0.60, 0.46, 52.0, "DISTRACTED", False, True),
            ("STU-104", "Ananya Singh", 0.80, 0.44, 70.0, "MODERATE", False, False),
            ("STU-105", "Kabir Verma", 0.30, 0.70, 32.0, "DROWSY", True, False),
            ("STU-106", "Diya Nair", 0.70, 0.68, 85.0, "FOCUSED", False, False),
        ]

        tracks = []
        for idx, (s_id, name, bx, by, base_score, cat, drowsy, distract) in enumerate(students_meta, 1):
            disp_name = f"Learner-{s_id[-3:]}" if _privacy_mode else name
            score = 30.0 if (drowsy and sim_t > 15.0) else min(100.0, max(20.0, base_score + wave * 5.0))
            tracks.append({
                "track_id": idx,
                "student_id": s_id,
                "display_name": disp_name,
                "bbox": [bx, by, 0.12, 0.18],
                "confidence": 0.94,
                "engagement_score": round(score, 1),
                "attention_category": "LOW" if score < 45 else ("MODERATE" if score < 75 else "HIGH"),
                "is_drowsy": drowsy and sim_t > 15.0,
                "is_distracted": distract,
            })

        self._send_json({
            "timestamp": round(sim_t, 1),
            "average_engagement": round(avg_eng, 1),
            "high_count": 3 if avg_eng > 60 else 1,
            "moderate_count": 2,
            "low_count": 1 if avg_eng > 60 else 3,
            "disengaged_count": 1,
            "active_students": len(tracks),
            "acoustic_state": ac_state,
            "acoustic_speech_ratio": speech_ratio,
            "acoustic_rms": rms,
            "acoustic_desc": desc,
            "tracks": tracks,
        })

    def _handle_attendance(self, sim_t: float):
        roster = [
            ("STU-101", "Aarav Sharma", 1.0, 60.0),
            ("STU-102", "Priya Patel", 0.97, 58.0),
            ("STU-103", "Rohan Mehta", 0.88, 52.0),
            ("STU-104", "Ananya Singh", 1.0, 60.0),
            ("STU-105", "Kabir Verma", 1.0, 60.0),
            ("STU-106", "Diya Nair", 0.75, 45.0),
            ("STU-107", "Ishaan Gupta", 0.0, 0.0),
            ("GUEST-999", "Hallway Passerby", 0.05, 3.2),
        ]

        records = []
        for s_id, name, ratio, active_s in roster:
            disp_name = f"Learner-{s_id[-3:]}" if _privacy_mode else name
            default_status = "ABSENT" if active_s == 0.0 else ("TRANSIENT_IGNORED" if s_id == "GUEST-999" else "PRESENT")
            final_status = _manual_overrides.get(s_id, default_status)

            records.append({
                "student_id": s_id,
                "display_name": disp_name,
                "status": final_status,
                "first_seen": 0.0 if active_s > 0 else None,
                "last_seen": 60.0 if active_s > 0 else None,
                "total_active_seconds": active_s,
                "presence_ratio": ratio,
                "confidence": 0.99 if active_s > 10 else (0.90 if s_id == "GUEST-999" else 1.0),
                "privacy_hash": f"hash_{s_id}_2026",
            })

        present = sum(1 for r in records if r["status"] == "PRESENT")
        tardy = sum(1 for r in records if r["status"] in ("TARDY", "LATE"))
        absent = sum(1 for r in records if r["status"] == "ABSENT")
        transient = sum(1 for r in records if r["status"] == "TRANSIENT_IGNORED")

        self._send_json({
            "summary": {
                "total_students": len(records),
                "present_count": present,
                "tardy_count": tardy,
                "absent_count": absent,
                "transient_ignored_count": transient,
                "attendance_rate_percent": round((present / (len(records) - transient)) * 100.0, 1),
            },
            "records": records,
        })

    def _handle_timeline(self, sim_t: float):
        pts = []
        for t in range(0, 60, 2):
            wave = math.sin(t * 0.15)
            pts.append({
                "timestamp": t,
                "average_engagement": round(75.0 + wave * 15.0 - (18.0 if 20 <= t <= 35 else 0.0), 1),
                "speech_ratio": 0.55 if t > 25 else 0.15,
                "acoustic_state": "STUDENT_DISCUSSION" if t > 25 else "TEACHER_MONOLOGUE",
            })
        self._send_json({"timeline": pts})

    def _handle_suggestions(self, sim_t: float):
        suggs = [
            {
                "priority": "URGENT",
                "title": "Attention Dip During Lecture Segment",
                "suggestion": "Classroom engagement dropped below 50% for 12 seconds during extended monologue. Pause the lecture and conduct a quick interactive poll.",
                "rationale": "Formative retrieval check resets student cognitive load after 15 minutes of passive listening.",
                "timestamp": 25.0,
            },
            {
                "priority": "ACTIONABLE",
                "title": "Extended Instructional Monologue (>90s)",
                "suggestion": "Teacher continuous speaking time exceeded 90 seconds without student turn-taking. Transition to a 2-minute Think-Pair-Share exercise.",
                "rationale": "Pacing variation boosts long-term working memory retention.",
                "timestamp": 12.0,
            },
            {
                "priority": "ACTIONABLE",
                "title": "Student Drowsiness / Slump Detected",
                "suggestion": "Sustained downward head posture detected for STU-105. Initiate a quick 60-second physical stretch or show of hands.",
                "rationale": "Kinesthetic breaks reactivate motor cortex alertness.",
                "timestamp": 35.0,
            },
        ]
        self._send_json({"suggestions": suggs})

    def _handle_audit(self):
        audit = {
            "session_id": "SESSION-VERCEL-DEMO",
            "duration_minutes": 1.0,
            "average_engagement": 78.4,
            "grade": "B+",
            "attendance_rate": 85.7,
            "monologue_pct": 45.0,
            "discussion_pct": 35.0,
            "silence_pct": 20.0,
            "total_suggestions": 3,
            "strengths": [
                "Maintained strong student attentiveness (78.4% average focus).",
                "Facilitated rich peer participation (35% in active debate).",
            ],
            "recommendations": [
                "Break long teacher monologues (>10 min) with quick comprehension polling.",
            ],
            "markdown": "# 🎓 Classroom Session Pedagogical Audit Report\n**Grade:** **B+** (78.4%)\n\n## 📊 Summary\n- **Attendance Compliance:** 85.7%\n- **Discussion Ratio:** 35.0%\n\n## 💡 Recommendations\n- 📌 Incorporate more student-led discussion periods.",
        }
        self._send_json({"audit": audit})

    def _handle_csv_download(self):
        csv_text = "Student ID,Display Name,Status,First Seen (s),Last Seen (s),Active Duration (s),Presence Ratio,Confidence\n"
        csv_text += "STU-101,Aarav Sharma,PRESENT,0.0,60.0,60.0,100.0%,0.99\n"
        csv_text += "STU-102,Priya Patel,PRESENT,0.0,58.0,58.0,97.0%,0.99\n"
        csv_text += "STU-107,Ishaan Gupta,ABSENT,N/A,N/A,0.0,0.0%,1.00\n"
        csv_text += "GUEST-999,Hallway Passerby,TRANSIENT_IGNORED,4.0,7.2,3.2,5.0%,0.90\n"

        csv_bytes = csv_text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv")
        self.send_header("Content-Disposition", 'attachment; filename="attendance.csv"')
        self.send_header("Content-Length", str(len(csv_bytes)))
        self.end_headers()
        self.wfile.write(csv_bytes)

    def _send_json(self, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
