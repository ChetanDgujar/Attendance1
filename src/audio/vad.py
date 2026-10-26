"""Voice Activity Detection (VAD) and acoustic energy extraction.
Processes frame-level audio signals, computes Root Mean Square (RMS) energy,
and determines human vocal activity presence.
"""
from dataclasses import dataclass
from typing import List, Union, Tuple
import math
import struct


@dataclass
class AudioFrame:
    timestamp: float
    duration_ms: float
    rms_energy: float
    zero_crossing_rate: float
    is_speech: bool


class VoiceActivityDetector:
    """Detects voice activity using energy thresholds and zero-crossing dynamics."""

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
        energy_threshold: float = 0.025,
        zcr_min: float = 0.04,
        zcr_max: float = 0.45,
    ):
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.energy_threshold = energy_threshold
        self.zcr_min = zcr_min
        self.zcr_max = zcr_max
        self.samples_per_frame = int(sample_rate * (frame_duration_ms / 1000.0))

    def compute_rms(self, samples: List[float]) -> float:
        """Computes Root Mean Square (RMS) amplitude of audio samples normalized in [-1.0, 1.0]."""
        if not samples:
            return 0.0
        sum_sq = sum(s * s for s in samples)
        return math.sqrt(sum_sq / len(samples))

    def compute_zcr(self, samples: List[float]) -> float:
        """Computes normalized Zero Crossing Rate for speech frequency discrimination."""
        if len(samples) < 2:
            return 0.0
        crossings = 0
        for i in range(1, len(samples)):
            if (samples[i] >= 0 and samples[i - 1] < 0) or (samples[i] < 0 and samples[i - 1] >= 0):
                crossings += 1
        return crossings / float(len(samples) - 1)

    def process_raw_bytes(self, pcm_data: bytes, timestamp: float = 0.0) -> AudioFrame:
        """Processes 16-bit signed PCM audio bytes."""
        count = len(pcm_data) // 2
        if count == 0:
            return AudioFrame(timestamp, self.frame_duration_ms, 0.0, 0.0, False)

        shorts = struct.unpack(f"<{count}h", pcm_data[:count * 2])
        # Normalize to [-1.0, 1.0]
        samples = [s / 32768.0 for s in shorts]
        return self.process_samples(samples, timestamp)

    def process_samples(self, samples: List[float], timestamp: float = 0.0) -> AudioFrame:
        """Evaluates speech presence on normalized float samples."""
        rms = self.compute_rms(samples)
        zcr = self.compute_zcr(samples)

        # Voice criteria: energy above acoustic background noise and ZCR within human vocal range
        is_speech = rms >= self.energy_threshold and (self.zcr_min <= zcr <= self.zcr_max)

        return AudioFrame(
            timestamp=round(timestamp, 3),
            duration_ms=self.frame_duration_ms,
            rms_energy=round(rms, 4),
            zero_crossing_rate=round(zcr, 4),
            is_speech=is_speech,
        )
