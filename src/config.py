"""Configuration module for Multimodal Attendance & Engagement Agent.
Provides strongly typed dataclasses and fallback parsers.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional
import os


@dataclass
class PrivacyConfig:
    anonymize_student_names: bool = False
    hash_salt: str = "privacy_salt_classroom_agent_2026"
    store_raw_frames: bool = False
    retention_days: int = 30
    local_inference_only: bool = True


@dataclass
class AttendanceConfig:
    sustained_window_sec: float = 10.0
    sustained_presence_window_sec: float = 10.0
    sustained_min_ratio: float = 0.60
    sustained_presence_min_ratio: float = 0.60
    tardy_grace_period_sec: float = 300.0
    absence_timeout_sec: float = 60.0
    export_format: str = "csv"
    auto_export_on_session_end: bool = True


@dataclass
class VisionConfig:
    sample_fps: int = 5
    face_detection_confidence: float = 0.65
    head_pose_yaw_limit_deg: float = 25.0
    head_pose_pitch_down_limit_deg: float = -20.0
    head_pose_pitch_up_limit_deg: float = 25.0
    inactivity_drowsiness_sec: float = 12.0
    motion_activity_smoothing: float = 0.8
    motion_fidget_threshold: float = 0.70


@dataclass
class AudioConfig:
    sample_rate_hz: int = 16000
    frame_duration_ms: int = 30
    vad_rms_threshold: float = 0.025
    monologue_threshold_sec: float = 90.0
    sustained_silence_threshold_sec: float = 25.0
    chatter_energy_threshold: float = 0.06


@dataclass
class FusionWeights:
    gaze_alignment: float = 0.35
    head_pose_stability: float = 0.25
    body_kinetic_activity: float = 0.20
    acoustic_context: float = 0.20


@dataclass
class FusionPenalties:
    drowsiness_penalty: float = 0.45
    persistent_distraction_penalty: float = 0.30


@dataclass
class FusionConfig:
    weights: FusionWeights = field(default_factory=FusionWeights)
    penalties: FusionPenalties = field(default_factory=FusionPenalties)
    score_smoothing_alpha: float = 0.30


@dataclass
class AgentConfig:
    evaluation_interval_sec: float = 5.0
    alert_cooldown_sec: float = 15.0
    attention_dip_threshold: float = 50.0
    chatter_surge_threshold: float = 75.0
    pacing_monologue_limit_sec: float = 120.0
    enable_pedagogical_suggestions: bool = True
    decision_engine_mode: str = "hybrid"


@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8080
    debug: bool = False


@dataclass
class SystemConfig:
    privacy: PrivacyConfig = field(default_factory=PrivacyConfig)
    attendance: AttendanceConfig = field(default_factory=AttendanceConfig)
    vision: VisionConfig = field(default_factory=VisionConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    fusion: FusionConfig = field(default_factory=FusionConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    server: ServerConfig = field(default_factory=ServerConfig)

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "SystemConfig":
        """Load configuration from a YAML or JSON file, falling back to defaults."""
        config = cls()
        if not config_path:
            # Check default path
            default_p = Path(__file__).resolve().parent.parent / "config" / "default_config.yaml"
            if default_p.exists():
                config_path = str(default_p)
            else:
                return config

        p = Path(config_path)
        if not p.exists():
            return config

        data = cls._parse_simple_yaml_or_json(p)
        if not data:
            return config

        if "privacy" in data and isinstance(data["privacy"], dict):
            for k, v in data["privacy"].items():
                if hasattr(config.privacy, k):
                    setattr(config.privacy, k, v)

        if "attendance" in data and isinstance(data["attendance"], dict):
            for k, v in data["attendance"].items():
                if hasattr(config.attendance, k):
                    setattr(config.attendance, k, v)
            if "sustained_presence_window_sec" in data["attendance"]:
                config.attendance.sustained_window_sec = float(data["attendance"]["sustained_presence_window_sec"])
            if "sustained_presence_min_ratio" in data["attendance"]:
                config.attendance.sustained_min_ratio = float(data["attendance"]["sustained_presence_min_ratio"])

        if "vision" in data and isinstance(data["vision"], dict):
            for k, v in data["vision"].items():
                if hasattr(config.vision, k):
                    setattr(config.vision, k, v)

        if "audio" in data and isinstance(data["audio"], dict):
            for k, v in data["audio"].items():
                if hasattr(config.audio, k):
                    setattr(config.audio, k, v)

        if "fusion" in data and isinstance(data["fusion"], dict):
            f_data = data["fusion"]
            if "weights" in f_data and isinstance(f_data["weights"], dict):
                for k, v in f_data["weights"].items():
                    if hasattr(config.fusion.weights, k):
                        setattr(config.fusion.weights, k, float(v))
            if "penalties" in f_data and isinstance(f_data["penalties"], dict):
                for k, v in f_data["penalties"].items():
                    if hasattr(config.fusion.penalties, k):
                        setattr(config.fusion.penalties, k, float(v))
            if "score_smoothing_alpha" in f_data:
                config.fusion.score_smoothing_alpha = float(f_data["score_smoothing_alpha"])

        if "agent" in data and isinstance(data["agent"], dict):
            for k, v in data["agent"].items():
                if hasattr(config.agent, k):
                    setattr(config.agent, k, v)

        if "server" in data and isinstance(data["server"], dict):
            for k, v in data["server"].items():
                if hasattr(config.server, k):
                    setattr(config.server, k, v)

        return config

    @staticmethod
    def _parse_simple_yaml_or_json(path: Path) -> Dict[str, Any]:
        """Robust parser that parses JSON or simple nested YAML without external dependencies."""
        content = path.read_text(encoding="utf-8")
        # Try JSON first
        import json
        try:
            return json.loads(content)
        except Exception:
            pass

        # Simple YAML dictionary parser
        root: Dict[str, Any] = {}
        stack = [(0, root)]

        for line in content.splitlines():
            # Strip comments
            comment_idx = line.find("#")
            if comment_idx != -1:
                line = line[:comment_idx]
            if not line.strip():
                continue

            indent = len(line) - len(line.lstrip())
            parts = line.strip().split(":", 1)
            if len(parts) != 2:
                continue

            key = parts[0].strip()
            raw_val = parts[1].strip()

            # Find matching parent in stack
            while stack and stack[-1][0] >= indent and len(stack) > 1:
                stack.pop()

            parent = stack[-1][1]

            if not raw_val:
                new_dict: Dict[str, Any] = {}
                parent[key] = new_dict
                stack.append((indent + 2, new_dict))
            else:
                # Value parsing
                val: Any = raw_val.strip("\"'")
                low_val = val.lower()
                if low_val == "true":
                    val = True
                elif low_val == "false":
                    val = False
                elif low_val in ("null", "none"):
                    val = None
                else:
                    try:
                        if "." in val:
                            val = float(val)
                        else:
                            val = int(val)
                    except ValueError:
                        pass
                parent[key] = val

        return root
