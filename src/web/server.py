"""Classroom Intelligence HTTP Server & Real-Time Orchestrator.
Runs a zero-dependency high-concurrency HTTP server serving the interactive dashboard,
REST telemetry APIs, and managing the live multimodal processing pipeline.
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any, Optional
import json
import mimetypes
import os
import threading
import time
import urllib.parse

from ..config import SystemConfig
from ..privacy.anonymizer import PrivacyEngine
from ..attendance.attendance_manager import AttendanceManager
from ..vision.face_tracker import FaceTracker
from ..vision.head_pose import HeadPoseEstimator
from ..vision.motion_analyzer import MotionAnalyzer
from ..vision.synthetic_video import SyntheticClassroomStream
from ..audio.synthetic_audio import SyntheticAudioGenerator
from ..audio.acoustic_classifier import AcousticClassifier
from ..fusion.multimodal_fusion import MultimodalFusionEngine, ClassroomEngagementSnapshot
from ..fusion.session_timeline import SessionTimelineTracker
from ..agent.teaching_agent import TeachingAgent


class SessionOrchestrator:
    """Coordinates the continuous end-to-end multimodal perception, fusion, attendance, and agent loop."""

    def __init__(self, config: SystemConfig):
        self.config = config
        self.privacy = PrivacyEngine(
            salt=config.privacy.hash_salt,
            anonymize_names=config.privacy.anonymize_student_names,
        )
        self.attendance = AttendanceManager(
            sustained_window_sec=config.attendance.sustained_window_sec,
            sustained_min_ratio=config.attendance.sustained_min_ratio,
            tardy_grace_period_sec=config.attendance.tardy_grace_period_sec,
            privacy_engine=self.privacy,
        )
        self.face_tracker = FaceTracker()
        self.head_pose = HeadPoseEstimator(
            yaw_limit_deg=config.vision.head_pose_yaw_limit_deg,
            pitch_down_limit_deg=config.vision.head_pose_pitch_down_limit_deg,
            pitch_up_limit_deg=config.vision.head_pose_pitch_up_limit_deg,
        )
        self.motion_analyzer = MotionAnalyzer(
            inactivity_drowsiness_sec=config.vision.inactivity_drowsiness_sec,
            fidget_threshold=config.vision.motion_fidget_threshold,
        )
        self.video_stream = SyntheticClassroomStream(fps=config.vision.sample_fps)
        self.audio_gen = SyntheticAudioGenerator()
        self.acoustic_classifier = AcousticClassifier(
            monologue_threshold_sec=config.audio.monologue_threshold_sec,
            silence_threshold_sec=config.audio.sustained_silence_threshold_sec,
        )
        self.fusion = MultimodalFusionEngine(config.fusion)
        self.timeline = SessionTimelineTracker(
            attention_dip_threshold=config.agent.attention_dip_threshold
        )
        self.agent = TeachingAgent(
            alert_cooldown_sec=config.agent.alert_cooldown_sec,
            enable_suggestions=config.agent.enable_pedagogical_suggestions,
        )

        # Load default roster
        roster_path = Path(__file__).resolve().parent.parent.parent / "data" / "sample_roster.json"
        if roster_path.exists():
            try:
                with open(roster_path, "r", encoding="utf-8") as f:
                    self.attendance.load_roster(json.load(f))
            except Exception:
                pass

        # Execution state
        self.is_running = False
        self.is_paused = False
        self.session_time = 0.0
        self.latest_snapshot: Optional[ClassroomEngagementSnapshot] = None
        self.latest_acoustic: Optional[Any] = None
        self.lock = threading.Lock()
        self._worker_thread: Optional[threading.Thread] = None

    def start(self):
        with self.lock:
            if not self.is_running:
                self.is_running = True
                self.is_paused = False
                self._worker_thread = threading.Thread(target=self._run_loop, daemon=True)
                self._worker_thread.start()

    def pause(self):
        with self.lock:
            self.is_paused = True

    def resume(self):
        with self.lock:
            self.is_paused = False

    def toggle_privacy(self) -> bool:
        with self.lock:
            self.privacy.anonymize_names = not self.privacy.anonymize_names
            # Refresh roster display names
            for rec in self.attendance.records.values():
                rec.display_name = self.privacy.get_display_name(rec.student_id, rec.display_name)
            return self.privacy.anonymize_names

    def _run_loop(self):
        """Simulation tick loop running at ~2-5 ticks per second."""
        dt = 0.5
        while self.is_running:
            if self.is_paused:
                time.sleep(0.2)
                continue

            with self.lock:
                self.session_time += dt
                t = self.session_time

                # 1. Vision: Generate simulated or camera frame
                frame = self.video_stream.generate_frame(t)
                active_tracks = self.face_tracker.update(frame.detections, current_timestamp=t)

                # 2. Audio: Synthesize/ingest acoustic frame
                # Pacing profile:
                # 0-15s lecture, 15-22s silence, 22-38s discussion, 38-48s monologue, 48-60s chatter
                cycle_t = t % 60.0
                if cycle_t < 15.0 or (38.0 <= cycle_t < 48.0):
                    phase = "monologue"
                elif 15.0 <= cycle_t < 22.0:
                    phase = "silence"
                elif 22.0 <= cycle_t < 38.0:
                    phase = "discussion"
                else:
                    phase = "chatter"

                audio_frame = self.audio_gen.generate_frame(phase, t)
                acoustic_snapshot = self.acoustic_classifier.add_frame(audio_frame)
                self.latest_acoustic = acoustic_snapshot

                # 3. Attendance: Register detected students
                detected_student_ids = {
                    trk.student_id for trk in active_tracks if trk.student_id is not None
                }
                self.attendance.register_frame(detected_student_ids, timestamp=t)

                # 4. Behavioral & Gaze Analysis per track
                student_scores = {}
                for trk in active_tracks:
                    if not trk.student_id:
                        continue

                    # Find corresponding detection for euler angles
                    det_data = next((d for d in frame.detections if d.get("student_id") == trk.student_id), None)
                    yaw = det_data.get("yaw", 0.0) if det_data else 0.0
                    pitch = det_data.get("pitch", 0.0) if det_data else 0.0
                    roll = det_data.get("roll", 0.0) if det_data else 0.0

                    head_res = self.head_pose.estimate_from_angles(yaw, pitch, roll)
                    beh_res = self.motion_analyzer.update_motion(trk.track_id, trk.bbox, head_res.gaze_state, timestamp=t)

                    s_score = self.fusion.compute_student_engagement(
                        student_id=trk.student_id,
                        track_id=trk.track_id,
                        head_pose=head_res,
                        behavior=beh_res,
                        acoustic=acoustic_snapshot,
                    )
                    student_scores[trk.student_id] = s_score

                # 5. Multimodal Fusion: Classroom Level
                classroom_snap = self.fusion.compute_classroom_snapshot(t, student_scores, acoustic_snapshot)
                self.latest_snapshot = classroom_snap

                # 6. Timeline Milestone Events
                self.timeline.record_snapshot(classroom_snap, dt=dt)

                # 7. Pedagogical Teaching Agent
                self.agent.evaluate_and_advise(classroom_snap, acoustic_snapshot)

            time.sleep(dt)


class ClassroomIntelligenceHandler(BaseHTTPRequestHandler):
    """Handles REST requests and serves static web assets."""

    orchestrator: SessionOrchestrator
    static_dir: Path

    def log_message(self, format, *args):
        # Suppress routine log clutter
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            self._serve_file(self.static_dir / "index.html", "text/html")
        elif path == "/style.css":
            self._serve_file(self.static_dir / "style.css", "text/css")
        elif path == "/app.js":
            self._serve_file(self.static_dir / "app.js", "application/javascript")
        elif path == "/api/status":
            self._send_json({
                "running": self.orchestrator.is_running,
                "paused": self.orchestrator.is_paused,
                "session_time_seconds": round(self.orchestrator.session_time, 1),
                "anonymize_privacy": self.orchestrator.privacy.anonymize_names,
            })
        elif path == "/api/telemetry":
            self._handle_telemetry()
        elif path == "/api/attendance":
            self._handle_attendance()
        elif path == "/api/timeline":
            self._send_json({"timeline": self.orchestrator.timeline.get_timeline_series()})
        elif path == "/api/suggestions":
            self._send_json({
                "suggestions": [s.to_dict() for s in self.orchestrator.agent.get_recent_suggestions(15)]
            })
        elif path == "/api/audit":
            audit = self.orchestrator.agent.generate_post_session_audit(
                session_id="SESSION-" + time.strftime("%Y%m%d-%H%M"),
                timeline_series=self.orchestrator.timeline.get_timeline_series(),
                attendance_manager=self.orchestrator.attendance,
            )
            self._send_json({
                "audit": {
                    "session_id": audit.session_id,
                    "duration_minutes": audit.session_duration_minutes,
                    "average_engagement": audit.average_engagement_score,
                    "grade": audit.engagement_grade,
                    "attendance_rate": audit.attendance_rate_percent,
                    "monologue_pct": audit.monologue_percentage,
                    "discussion_pct": audit.discussion_percentage,
                    "silence_pct": audit.silence_percentage,
                    "total_suggestions": audit.total_suggestions_issued,
                    "strengths": audit.key_strengths,
                    "recommendations": audit.growth_recommendations,
                    "markdown": audit.to_markdown(),
                }
            })
        elif path == "/api/download/attendance.csv":
            self._download_attendance_csv()
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/action":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode("utf-8")
            data = json.loads(body) if body else {}

            action = data.get("action")
            if action == "start":
                self.orchestrator.start()
                self._send_json({"success": True, "message": "Session started."})
            elif action == "pause":
                self.orchestrator.pause()
                self._send_json({"success": True, "message": "Session paused."})
            elif action == "resume":
                self.orchestrator.resume()
                self._send_json({"success": True, "message": "Session resumed."})
            elif action == "toggle_privacy":
                is_anon = self.orchestrator.toggle_privacy()
                self._send_json({"success": True, "anonymize_privacy": is_anon})
            elif action == "export_csv":
                log_dir = Path(__file__).resolve().parent.parent.parent / "data" / "logs"
                filepath = log_dir / f"attendance_{int(time.time())}.csv"
                self.orchestrator.attendance.export_csv(str(filepath))
                self._send_json({"success": True, "filepath": str(filepath)})
            elif action == "export_audit":
                log_dir = Path(__file__).resolve().parent.parent.parent / "data" / "logs"
                audit = self.orchestrator.agent.generate_post_session_audit(
                    session_id="SESSION-" + time.strftime("%Y%m%d-%H%M"),
                    timeline_series=self.orchestrator.timeline.get_timeline_series(),
                    attendance_manager=self.orchestrator.attendance,
                )
                md_path = log_dir / f"audit_{int(time.time())}.md"
                md_path.write_text(audit.to_markdown(), encoding="utf-8")
                self._send_json({"success": True, "filepath": str(md_path)})
            else:
                self.send_error(400, "Unknown action")
        else:
            self.send_error(404, "Not Found")

    def _handle_telemetry(self):
        snap = self.orchestrator.latest_snapshot
        ac = self.orchestrator.latest_acoustic

        tracks_data = []
        for trk in self.orchestrator.face_tracker.active_tracks.values():
            if not trk.is_visible:
                continue
            s_score = snap.student_scores.get(trk.student_id) if snap and trk.student_id else None
            tracks_data.append({
                "track_id": trk.track_id,
                "student_id": trk.student_id,
                "display_name": self.orchestrator.privacy.get_display_name(trk.student_id or "", trk.student_id),
                "bbox": trk.bbox,
                "confidence": trk.confidence,
                "engagement_score": s_score.smoothed_score if s_score else 0.0,
                "attention_category": s_score.attention_category if s_score else "UNKNOWN",
                "is_drowsy": s_score.is_drowsy if s_score else False,
                "is_distracted": s_score.is_distracted if s_score else False,
            })

        payload = {
            "timestamp": snap.timestamp if snap else 0.0,
            "average_engagement": snap.average_engagement if snap else 0.0,
            "high_count": snap.high_engagement_count if snap else 0,
            "moderate_count": snap.moderate_engagement_count if snap else 0,
            "low_count": snap.low_engagement_count if snap else 0,
            "disengaged_count": snap.disengaged_count if snap else 0,
            "active_students": snap.active_students_count if snap else 0,
            "acoustic_state": ac.state.value if ac else "INITIALIZING",
            "acoustic_speech_ratio": ac.speech_ratio if ac else 0.0,
            "acoustic_rms": ac.average_rms if ac else 0.0,
            "acoustic_desc": ac.description if ac else "Initializing audio feed...",
            "tracks": tracks_data,
        }
        self._send_json(payload)

    def _handle_attendance(self):
        mgr = self.orchestrator.attendance
        records = [r.to_dict() for r in mgr.records.values()]
        self._send_json({
            "summary": mgr.get_summary(),
            "records": records,
        })

    def _download_attendance_csv(self):
        import io
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Student ID", "Display Name", "Status", "First Seen (s)", "Last Seen (s)", "Active Duration (s)", "Presence Ratio", "Confidence"])
        for rec in self.orchestrator.attendance.records.values():
            writer.writerow([
                rec.student_id,
                rec.display_name,
                rec.status.value,
                f"{rec.first_seen:.1f}" if rec.first_seen is not None else "N/A",
                f"{rec.last_seen:.1f}" if rec.last_seen is not None else "N/A",
                f"{rec.total_active_seconds:.1f}",
                f"{rec.presence_ratio:.2%}",
                f"{rec.confidence:.2f}",
            ])
        csv_bytes = output.getvalue().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv")
        self.send_header("Content-Disposition", 'attachment; filename="attendance_report.csv"')
        self.send_header("Content-Length", str(len(csv_bytes)))
        self.end_headers()
        self.wfile.write(csv_bytes)

    def _serve_file(self, path: Path, content_type: str):
        if not path.exists():
            self.send_error(404, "File not found")
            return
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, data: Dict[str, Any]):
        content = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


class ClassroomIntelligenceServer:
    """Manages server startup, lifecycle, and orchestrator binding."""

    def __init__(self, config: Optional[SystemConfig] = None):
        self.config = config or SystemConfig.load()
        self.orchestrator = SessionOrchestrator(self.config)
        self.static_dir = Path(__file__).resolve().parent / "static"
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None

    def start(self, auto_start_simulation: bool = True):
        handler_class = ClassroomIntelligenceHandler
        handler_class.orchestrator = self.orchestrator
        handler_class.static_dir = self.static_dir

        host = self.config.server.host
        port = self.config.server.port

        self.server = HTTPServer((host, port), handler_class)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()

        if auto_start_simulation:
            self.orchestrator.start()

        return f"http://{host}:{port}"

    def stop(self):
        if self.orchestrator:
            self.orchestrator.is_running = False
        if self.server:
            self.server.shutdown()
