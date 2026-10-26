"""Generates sample classroom roster and sample session audio WAV."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.audio.synthetic_audio import SyntheticAudioGenerator


def generate_all():
    data_dir = ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = data_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # 1. Roster
    roster_path = data_dir / "sample_roster.json"
    if not roster_path.exists():
        roster = [
            {"student_id": "STU-101", "name": "Aarav Sharma", "seat": "Row 1, Seat 1"},
            {"student_id": "STU-102", "name": "Priya Patel", "seat": "Row 1, Seat 2"},
            {"student_id": "STU-103", "name": "Rohan Mehta", "seat": "Row 1, Seat 3"},
            {"student_id": "STU-104", "name": "Ananya Singh", "seat": "Row 1, Seat 4"},
            {"student_id": "STU-105", "name": "Kabir Verma", "seat": "Row 2, Seat 1"},
            {"student_id": "STU-106", "name": "Diya Nair", "seat": "Row 2, Seat 2"},
            {"student_id": "STU-107", "name": "Ishaan Gupta", "seat": "Row 2, Seat 3"},
        ]
        with open(roster_path, "w", encoding="utf-8") as f:
            json.dump(roster, f, indent=2)
        print(f"Generated sample roster at {roster_path}")

    # 2. Audio WAV
    audio_path = data_dir / "sample_session.wav"
    gen = SyntheticAudioGenerator()
    gen.write_wav_file(str(audio_path), duration_sec=15.0)
    print(f"Generated sample session audio WAV at {audio_path}")


if __name__ == "__main__":
    generate_all()
