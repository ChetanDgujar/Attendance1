"""Shared simulated data provider for Vercel serverless endpoints.
Provides realistic classroom telemetry, attendance rosters, and pedagogical suggestions.
"""
import json
import math
import time

_start_time = time.time()
_privacy_mode = False
_manual_overrides = {}


def get_session_elapsed() -> float:
    return time.time() - _start_time


def get_privacy_mode() -> bool:
    return _privacy_mode


def toggle_privacy_mode() -> bool:
    global _privacy_mode
    _privacy_mode = not _privacy_mode
    return _privacy_mode


def set_manual_override(student_id: str, status: str) -> None:
    if student_id:
        _manual_overrides[student_id] = status.upper()


def get_status_payload() -> dict:
    elapsed = get_session_elapsed()
    return {
        "running": True,
        "paused": False,
        "session_time_seconds": round(elapsed, 1),
        "anonymize_privacy": _privacy_mode,
    }


def get_telemetry_payload() -> dict:
    sim_t = get_session_elapsed() % 60.0
    wave = math.sin(sim_t * 0.15)
    avg_eng = min(95.0, max(30.0, 75.0 + wave * 15.0 - (18.0 if 20 <= sim_t <= 35 else 0.0)))

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

    return {
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
    }


def get_attendance_payload() -> dict:
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
    effective_total = max(1, len(records) - transient)

    return {
        "summary": {
            "total_students": len(records),
            "present_count": present,
            "tardy_count": tardy,
            "absent_count": absent,
            "transient_ignored_count": transient,
            "attendance_rate_percent": round((present / effective_total) * 100.0, 1),
        },
        "records": records,
    }


def get_timeline_payload() -> dict:
    pts = []
    for t in range(0, 60, 2):
        wave = math.sin(t * 0.15)
        pts.append({
            "timestamp": t,
            "average_engagement": round(75.0 + wave * 15.0 - (18.0 if 20 <= t <= 35 else 0.0), 1),
            "speech_ratio": 0.55 if t > 25 else 0.15,
            "acoustic_state": "STUDENT_DISCUSSION" if t > 25 else "TEACHER_MONOLOGUE",
        })
    return {"timeline": pts}


def get_suggestions_payload() -> dict:
    return {
        "suggestions": [
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
    }


def get_audit_payload() -> dict:
    return {
        "audit": {
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
    }
