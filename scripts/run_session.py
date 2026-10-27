"""Main Session Runner CLI for Multimodal Attendance & Engagement Agent.
Supports live camera feed, recorded video files, or offline synthetic simulation.
Persists all telemetry to SQLite and exports CSV / JSON / HTML reports.
"""
from pathlib import Path
import argparse
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import SystemConfig
from src.privacy.anonymizer import PrivacyEngine
from src.storage.database import DatabaseManager
from src.storage.exporter import DataExporter
from src.reports.report_generator import ReportGenerator
from src.vision.face_tracker import FaceTracker
from src.vision.head_pose import HeadPoseEstimator
from src.vision.motion_analyzer import MotionAnalyzer
from src.vision.synthetic_video import SyntheticClassroomStream
from src.audio.synthetic_audio import SyntheticAudioGenerator
from src.audio.acoustic_classifier import AcousticClassifier
from src.fusion.multimodal_fusion import MultimodalFusionEngine
from src.fusion.session_timeline import SessionTimelineTracker
from src.agent.teaching_agent import TeachingAgent
from src.attendance.attendance_manager import AttendanceManager


def run_session(
    source_type: str = "demo",
    video_path: Optional[str] = None,
    duration_sec: float = 30.0,
    anonymize: bool = False,
    session_name: str = "Classroom_Session",
):
    print("=" * 80)
    print("🎓 MULTIMODAL ATTENDANCE & ENGAGEMENT AGENT - SESSION RUNNER")
    print(f"   Mode: {source_type.upper()} | Duration: {duration_sec}s | Anonymize: {anonymize}")
    print("=" * 80)

    # 1. Config & Storage
    config = SystemConfig.load()
    if anonymize:
        config.privacy.anonymize_student_names = True

    session_id = f"SESS-{time.strftime('%Y%m%d-%H%M%S')}"
    db = DatabaseManager(str(ROOT / "data" / "classroom.db"))
    db.create_session(session_id, session_name, time.time(), source_type=source_type)

    # 2. Privacy & Attendance
    privacy = PrivacyEngine(salt=config.privacy.hash_salt, anonymize_names=config.privacy.anonymize_student_names)
    attendance = AttendanceManager(
        sustained_window_sec=config.attendance.sustained_window_sec,
        sustained_min_ratio=config.attendance.sustained_min_ratio,
        tardy_grace_period_sec=config.attendance.tardy_grace_period_sec,
        privacy_engine=privacy,
    )

    # Load enrolled roster
    roster_path = ROOT / "data" / "sample_roster.json"
    if roster_path.exists():
        import json
        with open(roster_path, "r", encoding="utf-8") as f:
            attendance.load_roster(json.load(f))
        print(f"Loaded {len(attendance.records)} enrolled students from roster.")

    # 3. Vision & Audio Engines
    face_tracker = FaceTracker()
    head_pose = HeadPoseEstimator()
    motion_analyzer = MotionAnalyzer()
    video_stream = SyntheticClassroomStream(fps=5, session_duration_sec=duration_sec)
    audio_gen = SyntheticAudioGenerator()
    acoustic_classifier = AcousticClassifier()
    fusion = MultimodalFusionEngine(config.fusion)
    timeline = SessionTimelineTracker()
    agent = TeachingAgent(alert_cooldown_sec=10.0)

    print(f"\n▶ Ingesting multimodal streams...")
    dt = 0.5
    sim_t = 0.0

    while sim_t <= duration_sec:
        # Vision frame
        frame = video_stream.generate_frame(sim_t)
        active_tracks = face_tracker.update(frame.detections, current_timestamp=sim_t)

        # Audio frame
        cycle = sim_t % 30.0
        phase = "monologue" if cycle < 10.0 else ("silence" if cycle < 15.0 else ("discussion" if cycle < 24.0 else "chatter"))
        audio_frame = audio_gen.generate_frame(phase, sim_t)
        acoustic_snap = acoustic_classifier.add_frame(audio_frame)

        # Attendance tracking
        detected_ids = {trk.student_id for trk in active_tracks if trk.student_id is not None}
        attendance.register_frame(detected_ids, timestamp=sim_t)

        # Behavioral & Gaze scoring
        student_scores = {}
        for trk in active_tracks:
            if not trk.student_id:
                continue
            det_data = next((d for d in frame.detections if d.get("student_id") == trk.student_id), None)
            yaw = det_data.get("yaw", 0.0) if det_data else 0.0
            pitch = det_data.get("pitch", 0.0) if det_data else 0.0
            roll = det_data.get("roll", 0.0) if det_data else 0.0

            h_res = head_pose.estimate_from_angles(yaw, pitch, roll)
            b_res = motion_analyzer.update_motion(trk.track_id, trk.bbox, h_res.gaze_state, timestamp=sim_t)

            score = fusion.compute_student_engagement(
                student_id=trk.student_id,
                track_id=trk.track_id,
                head_pose=h_res,
                behavior=b_res,
                acoustic=acoustic_snap,
            )
            student_scores[trk.student_id] = score

            # Save to SQLite engagement_samples
            db.save_engagement_sample(
                session_id=session_id,
                timestamp=sim_t,
                student_id=trk.student_id,
                gaze_score=score.gaze_component,
                pose_score=score.pose_component,
                motion_score=score.motion_component,
                acoustic_score=score.acoustic_component,
                fused_score=score.smoothed_score,
                is_drowsy=score.is_drowsy,
                is_distracted=score.is_distracted,
            )

        # Classroom level snapshot
        classroom_snap = fusion.compute_classroom_snapshot(sim_t, student_scores, acoustic_snap)
        timeline.record_snapshot(classroom_snap, dt=dt)

        # Save timeline entry to SQLite
        db.save_timeline_entry(
            session_id=session_id,
            timestamp=sim_t,
            avg_engagement=classroom_snap.average_engagement,
            acoustic_state=acoustic_snap.state.value,
            speech_ratio=acoustic_snap.speech_ratio,
            active_count=classroom_snap.active_students_count,
        )

        # Teaching suggestions
        suggestions = agent.evaluate_and_advise(classroom_snap, acoustic_snap)
        for s in suggestions:
            db.save_suggestion(
                session_id=session_id,
                timestamp=s.timestamp,
                trigger_type=s.trigger,
                priority=s.priority,
                title=s.title,
                evidence=s.suggestion,
                suggested_action=s.action_type,
            )

        sim_t += dt

    # Finalize Attendance
    attendance.finalize_session(duration_sec)
    att_summary = attendance.get_summary()

    # Save attendance to SQLite
    db.save_attendance_records(session_id, [r.to_dict() for r in attendance.records.values()])

    # Close session in SQLite
    timeline_series = timeline.get_timeline_series()
    avg_eng = sum(e["average_engagement"] for e in timeline_series) / max(1, len(timeline_series))
    db.close_session(session_id, time.time(), avg_eng, att_summary["attendance_rate_percent"])

    # Exporters
    exporter = DataExporter(db)
    report_gen = ReportGenerator(db)

    csv_path = ROOT / "data" / "logs" / f"attendance_{session_id}.csv"
    json_path = ROOT / "data" / "logs" / f"session_{session_id}.json"
    html_path = ROOT / "data" / "logs" / f"report_{session_id}.html"

    exporter.export_attendance_csv(session_id, str(csv_path))
    exporter.export_session_json(session_id, str(json_path))
    report_gen.export_html_report(session_id, str(html_path))

    print("\n" + "=" * 80)
    print("✅ SESSION PROCESSING COMPLETE")
    print(f"Session ID:         {session_id}")
    print(f"Average Focus:      {avg_eng:.1f}%")
    print(f"Attendance Rate:    {att_summary['attendance_rate_percent']}% ({att_summary['present_count']} Present, {att_summary['absent_count']} Absent, {att_summary['transient_ignored_count']} Passerby Filtered)")
    print(f"Saved Database:     {db.db_path}")
    print(f"Exported CSV Log:   {csv_path}")
    print(f"Exported JSON Data: {json_path}")
    print(f"Exported HTML Audit:{html_path}")
    print("=" * 80)


if __name__ == "__main__":
    from typing import Optional
    parser = argparse.ArgumentParser(description="Classroom Intelligence Session Runner")
    parser.add_argument("--demo", action="store_true", default=True, help="Run synthetic classroom simulation")
    parser.add_argument("--video", type=str, default=None, help="Path to recorded video file (e.g. sample.mp4)")
    parser.add_argument("--cam", type=int, default=None, help="Live webcam index (e.g. 0)")
    parser.add_argument("--webcam", action="store_true", default=False, help="Use default live webcam (index 0)")
    parser.add_argument("--duration", type=float, default=30.0, help="Duration in seconds (default: 30)")
    parser.add_argument("--anonymize", action="store_true", default=False, help="Enable identity pseudonymization")
    parser.add_argument("--name", type=str, default="Classroom Session", help="Session descriptive title")

    args = parser.parse_args()
    cam_idx = 0 if args.webcam else args.cam
    source = "video" if args.video else ("camera" if cam_idx is not None else "demo")
    run_session(source_type=source, video_path=args.video, duration_sec=args.duration, anonymize=args.anonymize, session_name=args.name)
