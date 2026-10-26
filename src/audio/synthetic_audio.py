"""Classroom audio simulation and standard WAV file streaming.
Generates realistic acoustic timelines or reads real mono/stereo WAV files using standard library.
"""
from dataclasses import dataclass
from typing import Iterator, List, Optional
import math
import random
import struct
import wave

from .vad import AudioFrame, VoiceActivityDetector


class SyntheticAudioGenerator:
    """Generates synthetic audio PCM signals matching classroom pedagogical phases."""

    def __init__(self, sample_rate: int = 16000, frame_duration_ms: int = 30):
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.samples_per_frame = int(sample_rate * (frame_duration_ms / 1000.0))
        self.vad = VoiceActivityDetector(sample_rate, frame_duration_ms)
        self.random = random.Random(1337)

    def generate_frame(self, phase: str, timestamp: float) -> AudioFrame:
        """Synthesizes an audio frame with specific acoustic characteristics.
        phase: 'monologue', 'discussion', 'silence', 'chatter'
        """
        samples: List[float] = []

        if phase == "monologue":
            # Sustained fundamental speech frequencies (150-300 Hz) with moderate amplitude
            amp = 0.08 + self.random.gauss(0, 0.02)
            f0 = 180.0
            for i in range(self.samples_per_frame):
                t = (timestamp * self.sample_rate + i) / self.sample_rate
                # Harmonic sum for human vocal timbre
                val = amp * (0.6 * math.sin(2 * math.pi * f0 * t) + 0.3 * math.sin(2 * math.pi * 2 * f0 * t))
                val += self.random.gauss(0, 0.005)
                samples.append(max(-1.0, min(1.0, val)))

        elif phase == "discussion":
            # Burst of speech with occasional pauses
            is_active = (int(timestamp * 2) % 3) != 0
            amp = 0.07 if is_active else 0.008
            f0 = 240.0
            for i in range(self.samples_per_frame):
                t = (timestamp * self.sample_rate + i) / self.sample_rate
                val = amp * math.sin(2 * math.pi * f0 * t) + self.random.gauss(0, 0.008)
                samples.append(max(-1.0, min(1.0, val)))

        elif phase == "chatter":
            # High energy noise with overlapping frequencies
            amp = 0.12
            for i in range(self.samples_per_frame):
                t = (timestamp * self.sample_rate + i) / self.sample_rate
                val = amp * (
                    0.4 * math.sin(2 * math.pi * 220 * t)
                    + 0.4 * math.sin(2 * math.pi * 380 * t)
                    + 0.3 * math.sin(2 * math.pi * 520 * t)
                )
                val += self.random.gauss(0, 0.02)
                samples.append(max(-1.0, min(1.0, val)))

        else:  # "silence" or background room ambience
            amp = 0.004
            for _ in range(self.samples_per_frame):
                samples.append(self.random.gauss(0, amp))

        return self.vad.process_samples(samples, timestamp)

    def write_wav_file(self, filepath: str, duration_sec: float = 30.0):
        """Generates a complete simulated classroom WAV audio file."""
        total_samples = int(self.sample_rate * duration_sec)
        num_frames = int(duration_sec / (self.frame_duration_ms / 1000.0))

        with wave.open(filepath, "wb") as wav_out:
            wav_out.setnchannels(1)  # Mono
            wav_out.setsampwidth(2)  # 16-bit
            wav_out.setframerate(self.sample_rate)

            for f_idx in range(num_frames):
                t = f_idx * (self.frame_duration_ms / 1000.0)
                # Pacing phase simulation:
                # 0-10s: Monologue, 10-15s: Silence, 15-25s: Discussion, 25-30s: Chatter
                if t < 10.0:
                    phase = "monologue"
                elif t < 15.0:
                    phase = "silence"
                elif t < 25.0:
                    phase = "discussion"
                else:
                    phase = "chatter"

                # Generate samples
                samples: List[int] = []
                frame_data = self.generate_frame(phase, t)
                # Write sine-based samples
                amp = frame_data.rms_energy * 2.0
                for i in range(self.samples_per_frame):
                    val = int(amp * 32767.0 * math.sin(2 * math.pi * 200.0 * (i / self.sample_rate)))
                    samples.append(max(-32768, min(32767, val)))

                raw_bytes = struct.pack(f"<{len(samples)}h", *samples)
                wav_out.writeframes(raw_bytes)
