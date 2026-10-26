"""Classroom acoustic state classification.
Analyzes voice activity patterns and acoustic energy over temporal windows to identify
teaching monologues, collaborative discussions, chatter surges, and dead silences.
"""
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Deque, List, Optional
import time

from .vad import AudioFrame


class AcousticState(str, Enum):
    BALANCED_ENGAGEMENT = "BALANCED_ENGAGEMENT"
    TEACHER_MONOLOGUE = "TEACHER_MONOLOGUE"
    STUDENT_DISCUSSION = "STUDENT_DISCUSSION"
    CHATTER_SURGE = "CHATTER_SURGE"
    SUSTAINED_SILENCE = "SUSTAINED_SILENCE"


@dataclass
class AcousticSnapshot:
    timestamp: float
    state: AcousticState
    speech_ratio: float           # [0.0, 1.0] in recent rolling window
    average_rms: float            # Average RMS energy in window
    monologue_duration_sec: float # Sustained monologue timer
    silence_duration_sec: float   # Sustained silence timer
    turn_taking_events: int       # Detected conversational turns
    description: str


class AcousticClassifier:
    """Classifies classroom acoustic environment over rolling temporal horizons."""

    def __init__(
        self,
        window_seconds: float = 8.0,
        fps_or_hz: float = 30.0,  # Audio frames per second (approx ~33ms frames)
        monologue_threshold_sec: float = 90.0,
        silence_threshold_sec: float = 20.0,
        chatter_energy_threshold: float = 0.07,
    ):
        self.window_size = int(window_seconds * fps_or_hz)
        self.monologue_threshold_sec = monologue_threshold_sec
        self.silence_threshold_sec = silence_threshold_sec
        self.chatter_energy_threshold = chatter_energy_threshold

        self._frame_buffer: Deque[AudioFrame] = deque(maxlen=max(10, self.window_size))
        self._current_monologue_time: float = 0.0
        self._current_silence_time: float = 0.0
        self._prev_frame_speech: Optional[bool] = None
        self._turn_takes: int = 0

    def add_frame(self, frame: AudioFrame) -> AcousticSnapshot:
        """Appends an audio frame and computes the updated acoustic classification snapshot."""
        self._frame_buffer.append(frame)
        dt = frame.duration_ms / 1000.0

        # Monologue / Silence temporal tracking
        if frame.is_speech:
            self._current_monologue_time += dt
            self._current_silence_time = 0.0
        else:
            self._current_silence_time += dt
            # If silence extends beyond 3 seconds, reset monologue counter
            if self._current_silence_time > 3.0:
                self._current_monologue_time = 0.0

        # Turn taking detection (transitions between speech and silence)
        if self._prev_frame_speech is not None and frame.is_speech != self._prev_frame_speech:
            self._turn_takes += 1
        self._prev_frame_speech = frame.is_speech

        # Window metrics
        if not self._frame_buffer:
            return AcousticSnapshot(
                frame.timestamp,
                AcousticState.BALANCED_ENGAGEMENT,
                0.0,
                0.0,
                0.0,
                0.0,
                0,
                "Initializing audio buffer",
            )

        speech_count = sum(1 for f in self._frame_buffer if f.is_speech)
        speech_ratio = speech_count / len(self._frame_buffer)
        avg_rms = sum(f.rms_energy for f in self._frame_buffer) / len(self._frame_buffer)

        # State classification logic
        if self._current_silence_time >= self.silence_threshold_sec:
            state = AcousticState.SUSTAINED_SILENCE
            desc = f"Prolonged silence detected ({int(self._current_silence_time)}s). Class may need prompt."
        elif avg_rms >= self.chatter_energy_threshold and speech_ratio > 0.75 and self._turn_takes > 8:
            state = AcousticState.CHATTER_SURGE
            desc = "High volume acoustic chatter surge detected across classroom."
        elif self._current_monologue_time >= self.monologue_threshold_sec:
            state = AcousticState.TEACHER_MONOLOGUE
            desc = f"Sustained continuous monologue ({int(self._current_monologue_time)}s). Pacing check recommended."
        elif speech_ratio >= 0.30 and self._turn_takes >= 4:
            state = AcousticState.STUDENT_DISCUSSION
            desc = "Active conversational exchange / collaborative discussion underway."
        else:
            state = AcousticState.BALANCED_ENGAGEMENT
            desc = "Normal instructional acoustic dynamic."

        return AcousticSnapshot(
            timestamp=frame.timestamp,
            state=state,
            speech_ratio=round(speech_ratio, 3),
            average_rms=round(avg_rms, 4),
            monologue_duration_sec=round(self._current_monologue_time, 1),
            silence_duration_sec=round(self._current_silence_time, 1),
            turn_taking_events=self._turn_takes,
            description=desc,
        )

    def reset(self):
        self._frame_buffer.clear()
        self._current_monologue_time = 0.0
        self._current_silence_time = 0.0
        self._turn_takes = 0
        self._prev_frame_speech = None
