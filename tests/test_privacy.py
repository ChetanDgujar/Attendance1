"""Tests for PrivacyEngine: pseudonymization, one-way hashing, telemetry sanitization."""
import unittest
from src.privacy.anonymizer import PrivacyEngine


class TestPrivacyEngine(unittest.TestCase):

    def setUp(self):
        self.privacy = PrivacyEngine(salt="test_salt_123", anonymize_names=True)

    def test_deterministic_pseudonym(self):
        p1 = self.privacy.generate_pseudonym("STU-101")
        p2 = self.privacy.generate_pseudonym("STU-101")
        self.assertEqual(p1, p2)
        self.assertTrue(p1.startswith("Learner-"))

    def test_different_ids_have_different_pseudonyms(self):
        p1 = self.privacy.generate_pseudonym("STU-101")
        p2 = self.privacy.generate_pseudonym("STU-102")
        self.assertNotEqual(p1, p2)

    def test_hash_identity_and_verification(self):
        h = self.privacy.hash_identity("STU-101")
        self.assertTrue(self.privacy.verify_hash("STU-101", h))
        self.assertFalse(self.privacy.verify_hash("STU-999", h))

    def test_feature_vector_hashing(self):
        v1 = [0.12345, 0.67891, 0.45678]
        v2 = [0.12345, 0.67891, 0.45678]
        v3 = [0.99999, 0.11111, 0.22222]
        h1 = self.privacy.hash_feature_vector(v1)
        h2 = self.privacy.hash_feature_vector(v2)
        h3 = self.privacy.hash_feature_vector(v3)
        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, h3)

    def test_sanitize_telemetry(self):
        raw = {
            "student_id": "STU-101",
            "student_name": "Aarav Sharma",
            "raw_landmarks": [[0.1, 0.2], [0.3, 0.4]],
            "raw_audio_buffer": b"\x00\x01\x02",
            "engagement_score": 85.0,
        }
        clean = self.privacy.sanitize_telemetry(raw)
        self.assertNotIn("raw_landmarks", clean)
        self.assertNotIn("raw_audio_buffer", clean)
        self.assertTrue(clean["student_id"].startswith("Learner-"))
        self.assertEqual(clean["engagement_score"], 85.0)


if __name__ == "__main__":
    unittest.main()
