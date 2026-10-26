"""Generates rich demonstration datasets for offline exploration.
Populates SQLite database with multiple historical sessions, student rosters,
multimodal timeline series, and pedagogical teaching suggestions.
"""
from pathlib import Path
import json
import math
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.storage.database import DatabaseManager
from src.storage.exporter import DataExporter
from src.reports.report_generator import ReportGenerator
from src.audio.synthetic_audio import SyntheticAudioGenerator


def generate_demo_dataset():
    print("=" * 80)
    print("📦 GENERATING SYNTHETIC CLASSROOM DATASET & HISTORICAL SESSIONS")
    print("=" * 80)

    data_dir = ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = data_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    db = DatabaseManager(str(data_dir / "classroom.db"))
    exporter = DataExporter(db)
    report_gen = ReportGenerator(db)

    # 1. Roster
    roster_path = data_dir / "sample_roster.json"
    students = [
        {"student_id": "STU-101", "name": "Aarav Sharma", "seat": "Row 1, Seat 1"},
        {"student_id": "STU-102", "name": "Priya Patel", "seat": "Row 1, Seat 2"},
        {"student_id": "STU-103", "name": "Rohan Mehta", "seat": "Row 1, Seat 3"},
        {"student_id": "STU-104", "name": "Ananya Singh", "seat": "Row 1, Seat 4"},
        {"student_id": "STU-105", "name": "Kabir Verma", "seat": "Row 2, Seat 1"},
        {"student_id": "STU-106", "name": "Diya Nair", "seat": "Row 2, Seat 2"},
        {"student_id": "STU-107", "name": "Ishaan Gupta", "seat": "Row 2, Seat 3"},
    ]
    with open(roster_path, "w", encoding="utf-8") as f:
        json.dump(students, f, indent=2)
    print(f"✅ Enrolled student roster created: {roster_path}")

    # 2. Audio WAV
    audio_path = data_dir / "sample_session.wav"
    audio_gen = SyntheticAudioGenerator()
    audio_gen.write_wav_file(str(audio_path), duration_sec=15.0)
    print(f"✅ Synthesized classroom WAV created: {audio_path}")

    # 3. Create 3 Historical Sessions in SQLite
    sessions_to_create = [
        {
            "id": "SESS-HIST-01",
            "name": "Introduction to AI & Ethics",
            "avg_eng": 82.4,
            "att_rate": 87.5,
            "duration": 60.0,
        },
        {
            "id": "SESS-HIST-02",
            "name": "Machine Learning Lab & Workshop",
            "avg_eng": 76.8,
            "att_rate": 100.0,
            "duration": 60.0,
        },
        {
            "id": "SESS-HIST-03",
            "name": "Linear Algebra Seminar",
            "avg_eng": 68.2,
            "att_rate": 75.0,
            "duration": 60.0,
        },
    ]

    base_time = time.time() - 86400 * 3 # 3 days ago

    for idx, s_info in enumerate(sessions_to_create):
        s_id = s_info["id"]
        s_start = base_time + idx * 86400
        s_end = s_start + s_info["duration"]

        db.create_session(s_id, s_info["name"], s_start, source_type="demo")

        # Students & Attendance Records
        att_records = []
        for s in students:
            is_present = not (s["student_id"] == "STU-107" and idx == 0) # STU-107 absent in first
            status = "PRESENT" if is_present else "ABSENT"
            active_sec = s_info["duration"] if is_present else 0.0
            ratio = 1.0 if is_present else 0.0

            att_records.append({
                "student_id": s["student_id"],
                "display_name": s["name"],
                "privacy_hash": f"hash_{s['student_id']}_salt",
                "status": status,
                "first_seen": 0.0 if is_present else None,
                "last_seen": s_info["duration"] if is_present else None,
                "total_active_seconds": active_sec,
                "presence_ratio": ratio,
                "confidence": 0.98 if is_present else 1.0,
            })

        # Add 1 transient passerby to test anti-glitch
        att_records.append({
            "student_id": "GUEST-999",
            "display_name": "Hallway Passerby",
            "privacy_hash": "hash_passerby",
            "status": "TRANSIENT_IGNORED",
            "first_seen": 4.0,
            "last_seen": 7.0,
            "total_active_seconds": 3.0,
            "presence_ratio": 0.05,
            "confidence": 0.90,
        })

        db.save_attendance_records(s_id, att_records)

        # Timeline entries
        for t in range(0, int(s_info["duration"]), 2):
            wave = math.sin(t * 0.15)
            eng = min(100.0, max(20.0, s_info["avg_eng"] + wave * 12.0))
            speech = 0.5 if t > 25 else 0.15
            ac_state = "STUDENT_DISCUSSION" if t > 25 else ("TEACHER_MONOLOGUE" if t < 15 else "SUSTAINED_SILENCE")

            db.save_timeline_entry(s_id, float(t), round(eng, 1), ac_state, speech, active_count=6)

            # Per student engagement samples
            for st_rec in att_records:
                if st_rec["status"] == "PRESENT":
                    is_drowsy = (st_rec["student_id"] == "STU-105" and t >= 30)
                    s_score = 30.0 if is_drowsy else min(100.0, eng + 5.0)
                    db.save_engagement_sample(
                        s_id, float(t), st_rec["student_id"],
                        gaze_score=0.3 if is_drowsy else 0.9,
                        pose_score=0.4 if is_drowsy else 0.85,
                        motion_score=0.1 if is_drowsy else 0.8,
                        acoustic_score=0.7,
                        fused_score=s_score,
                        is_drowsy=is_drowsy,
                        is_distracted=False,
                    )

        # Teaching Suggestions
        db.save_suggestion(
            s_id, 20.0, "PROLONGED_MONOLOGUE", "ACTIONABLE",
            "Extended Instructional Monologue",
            "Monologue time exceeded 90 seconds without student articulation.",
            "THINK_PAIR_SHARE",
        )
        db.save_suggestion(
            s_id, 35.0, "DROWSINESS_ALERT", "ACTIONABLE",
            "Student Drowsiness / Slump Detected",
            "Sustained downward head posture detected for STU-105.",
            "STRETCH_BREAK",
        )

        db.close_session(s_id, s_end, s_info["avg_eng"], s_info["att_rate"])

        # Pre-export HTML reports
        html_out = logs_dir / f"report_{s_id}.html"
        report_gen.export_html_report(s_id, str(html_out))

    print(f"✅ Generated {len(sessions_to_create)} complete historical classroom sessions in SQLite.")
    print("=" * 80)


if __name__ == "__main__":
    generate_demo_dataset()
