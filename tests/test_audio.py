"""Tests for audio module: VoiceActivityDetector, AcousticClassifier, and synthesis."""
import unittest
import tempfile
from pathlib import Path
from src.audio.vad import VoiceActivityDetector
from src.audio.acoustic_classifier import AcousticClassifier, AcousticState
from src.audio.synthetic_audio import SyntheticAudioGenerator


class TestAudioModule(unittest.TestCase):

    def setUp(self):
        self.vad = VoiceActivityDetector(sample_rate=16000, frame_duration_ms=30)
        self.classifier = AcousticClassifier(monologue_threshold_sec=5.0, silence_threshold_sec=3.0)
        self.gen = SyntheticAudioGenerator(sample_rate=16000, frame_duration_ms=30)

    def test_vad_speech_detection(self):
        # Monologue frame should be classified as speech
        f_speech = self.gen.generate_frame("monologue", 1.0)
        self.assertTrue(f_speech.is_speech)
        self.assertGreater(f_speech.rms_energy, 0.02)

        # Silence frame should not be classified as speech
        f_silence = self.gen.generate_frame("silence", 2.0)
        self.assertFalse(f_silence.is_speech)
        self.assertLess(f_silence.rms_energy, 0.015)

    def test_acoustic_classifier_monologue(self):
        # Feed sufficient continuous speech frames to exceed 5.0s monologue threshold
        # (30ms per frame -> 200 frames = 6.0 seconds)
        snap = None
        for i in range(200):
            t = i * 0.03
            f = self.gen.generate_frame("monologue", t)
            snap = self.classifier.add_frame(f)

        self.assertIsNotNone(snap)
        self.assertEqual(snap.state, AcousticState.TEACHER_MONOLOGUE)
        self.assertGreater(snap.monologue_duration_sec, 5.0)

    def test_acoustic_classifier_silence(self):
        self.classifier.reset()
        snap = None
        # Feed sufficient silence frames to exceed 3.0s threshold
        # (30ms per frame -> 130 frames = 3.9 seconds)
        for i in range(130):
            t = i * 0.03
            f = self.gen.generate_frame("silence", t)
            snap = self.classifier.add_frame(f)

        self.assertIsNotNone(snap)
        self.assertEqual(snap.state, AcousticState.SUSTAINED_SILENCE)

    def test_synthetic_wav_export(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wav_path = Path(tmpdir) / "test.wav"
            self.gen.write_wav_file(str(wav_path), duration_sec=2.0)
            self.assertTrue(wav_path.exists())
            self.assertGreater(wav_path.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
