"""Session timeline tracking and historical engagement analytics.
Identifies attention drops, interaction peaks, and classroom dynamic milestones over time.
"""
from collections import deque
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Deque, Dict, List, Optional, Any
import json
import time

from .multimodal_fusion import ClassroomEngagementSnapshot
from ..audio.acoustic_classifier import AcousticState


class EventType(str, Enum):
    ATTENTION_DROP = "ATTENTION_DROP"
    INTERACTION_PEAK = "INTERACTION_PEAK"
    DROWSINESS_DETECTED = "DROWSINESS_DETECTED"
    PROLONGED_MONOLOGUE = "PROLONGED_MONOLOGUE"
    CHATTER_SURGE = "CHATTER_SURGE"
    SUSTAINED_SILENCE = "SUSTAINED_SILENCE"
    INFO = "INFO"


@dataclass
class SessionEvent:
    timestamp: float
    event_type: EventType
    severity: str  # "INFO", "WARNING", "CRITICAL"
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["event_type"] = self.event_type.value
        return d


class SessionTimelineTracker:
    """Maintains time-series telemetry and detects macro engagement milestones."""

    def __init__(
        self,
        history_limit: int = 600,
        attention_dip_threshold: float = 50.0,
        interaction_peak_threshold: float = 75.0,
    ):
        self.history_limit = history_limit
        self.attention_dip_threshold = attention_dip_threshold
        self.interaction_peak_threshold = interaction_peak_threshold

        self.timeline: Deque[Dict[str, Any]] = deque(maxlen=history_limit)
        self.events: List[SessionEvent] = []
        self._last_event_timestamps: Dict[str, float] = {}
        self._low_attention_streak_sec: float = 0.0

    def record_snapshot(self, snapshot: ClassroomEngagementSnapshot, dt: float = 1.0) -> List[SessionEvent]:
        """Appends snapshot to timeline and checks for milestone events."""
        entry = {
            "timestamp": snapshot.timestamp,
            "average_engagement": snapshot.average_engagement,
            "high_count": snapshot.high_engagement_count,
            "mod_count": snapshot.moderate_engagement_count,
            "low_count": snapshot.low_engagement_count,
            "disengaged_count": snapshot.disengaged_count,
            "active_students": snapshot.active_students_count,
            "acoustic_state": snapshot.acoustic_state.value,
            "speech_ratio": snapshot.acoustic_speech_ratio,
        }
        self.timeline.append(entry)

        detected_events: List[SessionEvent] = []
        now = snapshot.timestamp

        # 1. Attention Dip Detection
        if snapshot.active_students_count > 0:
            if snapshot.average_engagement < self.attention_dip_threshold:
                self._low_attention_streak_sec += dt
                if self._low_attention_streak_sec >= 8.0 and self._can_emit("ATTENTION_DROP", now, cooldown=20.0):
                    ev = SessionEvent(
                        timestamp=now,
                        event_type=EventType.ATTENTION_DROP,
                        severity="WARNING",
                        message=f"Attention dip ({snapshot.average_engagement}% avg) across {snapshot.low_engagement_count + snapshot.disengaged_count} students.",
                        metadata={"avg_score": snapshot.average_engagement, "streak_sec": self._low_attention_streak_sec},
                    )
                    detected_events.append(ev)
                    self.events.append(ev)
            else:
                self._low_attention_streak_sec = 0.0

        # 2. Interaction Peak Detection
        if (
            snapshot.average_engagement >= self.interaction_peak_threshold
            and snapshot.acoustic_state in (AcousticState.STUDENT_DISCUSSION, AcousticState.BALANCED_ENGAGEMENT)
            and self._can_emit("INTERACTION_PEAK", now, cooldown=30.0)
        ):
            ev = SessionEvent(
                timestamp=now,
                event_type=EventType.INTERACTION_PEAK,
                severity="INFO",
                message=f"Interaction peak ({snapshot.average_engagement}% avg) with active student dialogue.",
                metadata={"avg_score": snapshot.average_engagement},
            )
            detected_events.append(ev)
            self.events.append(ev)

        # 3. Individual Student Drowsiness Detection
        for s_id, s_score in snapshot.student_scores.items():
            if s_score.is_drowsy and self._can_emit(f"DROWSY_{s_id}", now, cooldown=30.0):
                ev = SessionEvent(
                    timestamp=now,
                    event_type=EventType.DROWSINESS_DETECTED,
                    severity="WARNING",
                    message=f"Drowsiness / prolonged downward posture flagged for {s_id}.",
                    metadata={"student_id": s_id},
                )
                detected_events.append(ev)
                self.events.append(ev)

        # 4. Acoustic Events
        if snapshot.acoustic_state == AcousticState.CHATTER_SURGE and self._can_emit("CHATTER", now, cooldown=25.0):
            ev = SessionEvent(
                timestamp=now,
                event_type=EventType.CHATTER_SURGE,
                severity="WARNING",
                message="High noise / chatter surge detected in the classroom.",
            )
            detected_events.append(ev)
            self.events.append(ev)
        elif snapshot.acoustic_state == AcousticState.SUSTAINED_SILENCE and self._can_emit("SILENCE", now, cooldown=30.0):
            ev = SessionEvent(
                timestamp=now,
                event_type=EventType.SUSTAINED_SILENCE,
                severity="INFO",
                message="Extended silence observed. Consider posing a guiding prompt.",
            )
            detected_events.append(ev)
            self.events.append(ev)

        return detected_events

    def _can_emit(self, key: str, timestamp: float, cooldown: float) -> bool:
        last = self._last_event_timestamps.get(key, -999.0)
        if (timestamp - last) >= cooldown:
            self._last_event_timestamps[key] = timestamp
            return True
        return False

    def get_timeline_series(self) -> List[Dict[str, Any]]:
        return list(self.timeline)

    def export_telemetry_json(self, filepath: str):
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "timeline": list(self.timeline),
            "events": [e.to_dict() for e in self.events],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
