"""Privacy-Preserving Engine.
Ensures zero raw biometric data persistence, implements cryptographic pseudonymization,
and provides feature-level one-way hashing for ethical classroom deployment.
"""
import hashlib
import hmac
from dataclasses import dataclass
from typing import Dict, Any, List, Optional


@dataclass
class PrivacyProfile:
    student_id: str
    pseudonym: str
    privacy_hash: str
    enrolled_at: str


class PrivacyEngine:
    """Manages student identity masking, cryptographic hashing, and privacy-preserving audit logs."""

    def __init__(self, salt: str = "classroom_agent_privacy_salt_2026", anonymize_names: bool = False):
        self.salt = salt.encode("utf-8")
        self.anonymize_names = anonymize_names
        self._pseudonym_cache: Dict[str, str] = {}
        self._hash_cache: Dict[str, str] = {}

    def generate_pseudonym(self, student_id: str) -> str:
        """Generates a deterministic, collision-resistant pseudonym (e.g. Learner_7a2e)."""
        if student_id in self._pseudonym_cache:
            return self._pseudonym_cache[student_id]

        digest = hmac.new(self.salt, student_id.encode("utf-8"), hashlib.sha256).hexdigest()
        short_id = digest[:6].upper()
        pseudonym = f"Learner-{short_id}"
        self._pseudonym_cache[student_id] = pseudonym
        return pseudonym

    def hash_identity(self, student_id: str) -> str:
        """Computes a secure one-way cryptographic hash of a student identity."""
        if student_id in self._hash_cache:
            return self._hash_cache[student_id]

        digest = hmac.new(self.salt, student_id.encode("utf-8"), hashlib.sha256).hexdigest()
        self._hash_cache[student_id] = digest
        return digest

    def hash_feature_vector(self, vector: List[float], precision: int = 4) -> str:
        """Computes an irreversible perceptual hash from facial/behavioral feature coordinates.
        Never saves the raw floating-point features to persistent disk.
        """
        quantized = [round(v, precision) for v in vector]
        vector_str = ",".join(map(str, quantized))
        return hmac.new(self.salt, vector_str.encode("utf-8"), hashlib.sha256).hexdigest()

    def get_display_name(self, student_id: str, real_name: Optional[str] = None) -> str:
        """Returns the appropriate student identifier according to privacy settings."""
        if self.anonymize_names:
            return self.generate_pseudonym(student_id)
        return real_name if real_name else student_id

    def sanitize_telemetry(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Scrubs any raw biometric vectors or sensitive student data from session telemetry."""
        sanitized = dict(telemetry)
        # Remove any raw coordinate arrays or biometric embeddings if present
        for key in ["raw_landmarks", "facial_embedding", "raw_audio_buffer"]:
            sanitized.pop(key, None)

        if self.anonymize_names and "student_id" in sanitized:
            sanitized["student_id"] = self.generate_pseudonym(sanitized["student_id"])
            if "student_name" in sanitized:
                sanitized["student_name"] = sanitized["student_id"]

        return sanitized

    def verify_hash(self, student_id: str, expected_hash: str) -> bool:
        """Verifies if a candidate student ID matches a stored privacy hash."""
        computed = self.hash_identity(student_id)
        return hmac.compare_digest(computed, expected_hash)
