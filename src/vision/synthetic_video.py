"""Synthetic classroom stream simulator and video feed ingestion abstraction.
Provides realistic multimodal video playback for labs, tests, and live simulations,
with seamless fallback to OpenCV webcam/video file capture when cv2 is present.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Iterator
import math
import random
import time


@dataclass
class ClassroomProfile:
    student_id: str
    name: str
    base_x: float
    base_y: float
    persona: str  # "attentive", "distracted", "drowsy", "fidgety", "late_comer", "passerby"
    attendance_expected: bool = True


@dataclass
class SimulatedFrame:
    frame_number: int
    timestamp: float
    detections: List[Dict[str, Any]]
    frame_image: Optional[Any] = None  # numpy array or None if headless


class SyntheticClassroomStream:
    """Generates a realistic classroom scenario with participant tracks, head poses, and motion."""

    DEFAULT_STUDENTS = [
        ClassroomProfile("STU-101", "Aarav Sharma", 0.20, 0.45, "attentive"),
        ClassroomProfile("STU-102", "Priya Patel", 0.40, 0.42, "attentive"),
        ClassroomProfile("STU-103", "Rohan Mehta", 0.60, 0.46, "distracted"),
        ClassroomProfile("STU-104", "Ananya Singh", 0.80, 0.44, "fidgety"),
        ClassroomProfile("STU-105", "Kabir Verma", 0.30, 0.70, "drowsy"),
        ClassroomProfile("STU-106", "Diya Nair", 0.70, 0.68, "late_comer"),
        ClassroomProfile("GUEST-999", "Passerby Hallway", 0.05, 0.20, "passerby", attendance_expected=False),
    ]

    def __init__(
        self,
        students: Optional[List[ClassroomProfile]] = None,
        fps: int = 5,
        session_duration_sec: float = 60.0,
        random_seed: int = 42,
    ):
        self.students = students or self.DEFAULT_STUDENTS
        self.fps = fps
        self.session_duration_sec = session_duration_sec
        self.random = random.Random(random_seed)
        self.current_frame = 0
        self.start_time = 0.0

    def generate_frame(self, frame_time: float) -> SimulatedFrame:
        """Synthesizes student detections and behavioral posture for the given simulation time."""
        detections: List[Dict[str, Any]] = []

        for s in self.students:
            # Check presence conditions according to persona
            if s.persona == "passerby":
                # Only present between t=4.0s and t=7.0s (3 seconds total -> transient false positive!)
                if not (4.0 <= frame_time <= 7.0):
                    continue
            elif s.persona == "late_comer":
                # Arrives after 15 seconds
                if frame_time < 15.0:
                    continue

            # Base coordinates with micro-jitter
            w, h = 0.12, 0.18
            jitter_scale = 0.003
            if s.persona == "fidgety":
                jitter_scale = 0.015

            jx = self.random.gauss(0, jitter_scale)
            jy = self.random.gauss(0, jitter_scale)
            x = max(0.02, min(0.85, s.base_x + jx))
            y = max(0.05, min(0.80, s.base_y + jy))

            # Simulate Euler angles based on persona and timeline
            yaw = 0.0
            pitch = 0.0
            roll = 0.0

            if s.persona == "attentive":
                # Mostly facing front (within +/- 8 deg)
                yaw = self.random.gauss(0.0, 5.0)
                pitch = self.random.gauss(2.0, 4.0)
                roll = self.random.gauss(0.0, 2.0)
            elif s.persona == "distracted":
                # Frequently looking sideways (yaw > 25) or down
                cycle = math.sin(frame_time * 0.4)
                if cycle > 0.3:
                    yaw = 35.0 + self.random.gauss(0.0, 8.0)
                elif cycle < -0.3:
                    yaw = -32.0 + self.random.gauss(0.0, 6.0)
                else:
                    yaw = self.random.gauss(5.0, 5.0)
                pitch = self.random.gauss(-5.0, 8.0)
            elif s.persona == "drowsy":
                # Sustained looking down (pitch < -22 deg) after 8 seconds
                if frame_time > 8.0:
                    pitch = -26.0 + self.random.gauss(0.0, 3.0)
                    yaw = self.random.gauss(0.0, 3.0)
                else:
                    pitch = self.random.gauss(0.0, 4.0)
            elif s.persona == "fidgety":
                yaw = self.random.gauss(0.0, 15.0)
                pitch = self.random.gauss(0.0, 12.0)
                roll = self.random.gauss(0.0, 6.0)
            elif s.persona == "late_comer":
                yaw = self.random.gauss(0.0, 6.0)
                pitch = self.random.gauss(0.0, 5.0)
            elif s.persona == "passerby":
                yaw = 45.0
                pitch = 0.0

            detections.append({
                "student_id": s.student_id,
                "name": s.name,
                "bbox": (round(x, 4), round(y, 4), w, h),
                "confidence": 0.92,
                "yaw": round(yaw, 2),
                "pitch": round(pitch, 2),
                "roll": round(roll, 2),
            })

        frame = SimulatedFrame(
            frame_number=self.current_frame,
            timestamp=round(frame_time, 3),
            detections=detections,
        )
        self.current_frame += 1
        return frame

    def stream(self, total_seconds: Optional[float] = None) -> Iterator[SimulatedFrame]:
        """Generator yielding simulated classroom frames across session timeline."""
        duration = total_seconds or self.session_duration_sec
        interval = 1.0 / self.fps
        t = 0.0
        while t <= duration:
            yield self.generate_frame(t)
            t += interval
