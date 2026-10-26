"""End-to-End Simulation Demo for Multimodal Attendance & Engagement Agent.
Simulates a live classroom session with diverse student personas, multimodal perception,
sustained presence verification, and AI-driven pedagogical decision support.
"""
from pathlib import Path
import sys
import time

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


def run_classroom_simulation(duration_sec: float = 30.0, print_interval_sec: float = 5.0):
    print("=" * 80)
    print("🎓 MULTIMODAL ATTENDANCE & ENGAGEMENT AGENT - END-TO-END DEMO")
    print("   AI-Powered, Privacy-Preserving Classroom Intelligence System")
    print("=" * 80)

    config = SystemConfig.load()
    privacy = PrivacyEngine(salt=config.privacy.hash_salt, anonymize_names=config.privacy.anonymize_student_names)
    attendance = AttendanceManager(
        sustained_window_sec=config.attendance.sustained_window_sec,
        sustained_min_ratio=config.attendance.sustained_min_ratio,
        tardy_grace_period_sec=config.attendance.tardy_grace_period_sec,
        privacy_engine=privacy,
    )
    face_tracker = FaceTracker()
    head_pose = HeadPoseEstimator()
    motion_analyzer = MotionAnalyzer()
    video_stream = SyntheticClassroomStream(fps=5, session_duration_sec=duration_sec)
    audio_gen = SyntheticAudioGenerator()
    acoustic_classifier = AcousticClassifier()
    fusion = MultimodalFusionEngine(config.fusion)
    timeline = SessionTimelineTracker()
    agent = TeachingAgent(alert_cooldown_sec=10.0)

    # Load enrolled roster
    roster_path = ROOT / "data" / "sample_roster.json"
    if roster_path.exists():
        import json
        with open(roster_path, "r", encoding="utf-8") as f:
            attendance.load_roster(json.load(f))
        print(f"Loaded {len(attendance.records)} enrolled students from roster.")

    print(f"\n▶ Starting classroom simulation for {duration_sec} simulated seconds...")
    dt = 0.5
    sim_t = 0.0
    last_print_t = -999.0

    while sim_t <= duration_sec:
        # 1. Vision: Generate simulated video frame
        frame = video_stream.generate_frame(sim_t)
        active_tracks = face_tracker.update(frame.detections, current_timestamp=sim_t)

        # 2. Audio: Synthesize acoustic phase
        cycle = sim_t % 30.0
        if cycle < 10.0:
            phase = "monologue"
        elif cycle < 15.0:
            phase = "silence"
        elif cycle < 24.0:
            phase = "discussion"
        else:
            phase = "chatter"

        audio_frame = audio_gen.generate_frame(phase, sim_t)
        acoustic_snap = acoustic_classifier.add_frame(audio_frame)

        # 3. Attendance: Register observations
        detected_ids = {trk.student_id for trk in active_tracks if trk.student_id is not None}
        attendance.register_frame(detected_ids, timestamp=sim_t)

        # 4. Behavioral & Gaze Analysis
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

        # 5. Fusion & Timeline
        classroom_snap = fusion.compute_classroom_snapshot(sim_t, student_scores, acoustic_snap)
        timeline.record_snapshot(classroom_snap, dt=dt)

        # 6. Pedagogical Agent
        suggestions = agent.evaluate_and_advise(classroom_snap, acoustic_snap)

        # Console logging
        if (sim_t - last_print_t) >= print_interval_sec:
            last_print_t = sim_t
            print("-" * 80)
            print(f"⏱ Time: {sim_t:4.1f}s | Avg Engagement: {classroom_snap.average_engagement:5.1f}% | Acoustic: {acoustic_snap.state.value}")
            print(f"   Active Students: {classroom_snap.active_students_count} | High: {classroom_snap.high_engagement_count} | Mod: {classroom_snap.moderate_engagement_count} | Low: {classroom_snap.low_engagement_count}")
            if suggestions:
                for s in suggestions:
                    print(f"   💡 [AI Suggestion - {s.priority}] {s.title}: {s.suggestion}")

        sim_t += dt

    # Finalize attendance
    attendance.finalize_session(duration_sec)

    print("\n" + "=" * 80)
    print("📊 FINAL ATTENDANCE SUMMARY (Scenario 1: Sustained Presence Verification)")
    print("=" * 80)
    summary = attendance.get_summary()
    print(f"Total Enrolled / Observed: {summary['total_students']}")
    print(f"Present:                   {summary['present_count']}")
    print(f"Tardy:                     {summary['tardy_count']}")
    print(f"Absent:                    {summary['absent_count']}")
    print(f"Transient Passerby Ignored:{summary['transient_ignored_count']} (Filtered out false positives!)")
    print(f"Attendance Rate:           {summary['attendance_rate_percent']}%")

    print("\nDetailed Student Ledger:")
    for r in attendance.records.values():
        print(f" - [{r.status.value:<17}] {r.student_id:<9} | {r.display_name:<18} | Active: {r.total_active_seconds:4.1f}s | Ratio: {r.presence_ratio * 100:4.1f}% | Conf: {r.confidence:.2f}")

    # Generate Audit
    audit = agent.generate_post_session_audit(
        session_id="DEMO-SIM-01",
        timeline_series=timeline.get_timeline_series(),
        attendance_manager=attendance,
    )

    # Export CSV & Markdown
    log_dir = ROOT / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    csv_file = log_dir / "demo_attendance.csv"
    audit_file = log_dir / "demo_audit.md"

    attendance.export_csv(str(csv_file))
    audit_file.write_text(audit.to_markdown(), encoding="utf-8")

    print("\n" + "=" * 80)
    print("🎓 SESSION PEDAGOGICAL AUDIT (Scenario 3: Decision Support Agent)")
    print("=" * 80)
    print(f"Overall Session Grade:   {audit.engagement_grade} ({audit.average_engagement_score:.1f}%)")
    print(f"Monologue Ratio:         {audit.monologue_percentage:.1f}%")
    print(f"Discussion Ratio:        {audit.discussion_percentage:.1f}%")
    print(f"Silence Ratio:           {audit.silence_percentage:.1f}%")
    print(f"Key Strengths:           {', '.join(audit.key_strengths)}")
    print(f"Growth Recommendations:  {', '.join(audit.growth_recommendations)}")
    print(f"\nSaved CSV attendance log:  {csv_file}")
    print(f"Saved Markdown audit:      {audit_file}")
    print("=" * 80)


if __name__ == "__main__":
    run_classroom_simulation()
