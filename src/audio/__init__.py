"""Audio processing module for classroom acoustic dynamics and voice activity detection."""
from .vad import VoiceActivityDetector, AudioFrame
from .acoustic_classifier import AcousticClassifier, AcousticState, AcousticSnapshot
from .synthetic_audio import SyntheticAudioGenerator

__all__ = [
    "VoiceActivityDetector",
    "AudioFrame",
    "AcousticClassifier",
    "AcousticState",
    "AcousticSnapshot",
    "SyntheticAudioGenerator",
]
