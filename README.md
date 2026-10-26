# 🎓 Multimodal Attendance & Engagement Agent
### AI-Powered, Privacy-Preserving Classroom Intelligence System

[![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Privacy Preserving](https://img.shields.io/badge/Privacy-100%25%20Offline%20%7C%20Zero--Cloud-emerald.svg)](#privacy-preserving-guarantees)
[![Unit Tests](https://img.shields.io/badge/Tests-30%20Passed%20%28100%25%29-brightgreen.svg)](#test-suite)
[![Architecture](https://img.shields.io/badge/Epics-9%20%7C%20Tasks%3A%2017-purple.svg)](EPICS_AND_TASKS.md)

---

## 📌 Executive Overview

In educational institutions and professional training environments, attendance tracking remains largely manual or limited to basic biometric systems that fail to capture meaningful engagement and participation context. These traditional approaches are time-consuming, prone to inaccuracies, and provide no insight into learner attention, interaction patterns, or session effectiveness.

The **Multimodal Attendance & Engagement Agent** is an AI-powered, privacy-preserving classroom intelligence system. The system integrates **computer vision**, **audio signal processing**, and **agent-based reasoning** to:
1. Automatically track attendance via **sustained presence verification** (eliminating false positives from hallway passersby or brief glitches).
2. Continuously analyze **multimodal engagement trends** (head pose, kinetic movement, inactivity duration, voice activity detection).
3. Generate **real-time, context-aware AI teaching suggestions** to assist educators in adjusting pacing, launching polls, or managing classroom attention drops.
4. Provide comprehensive student session analytics and exportable pedagogical audits.

Designed to operate **entirely offline**, the system ensures ethical deployment and full privacy preservation while providing actionable insights that support both educators and learners.

---

## 🎯 Supported Scenarios

### 🔹 Scenario 1: Automated Attendance Tracking
- Processes video feeds to detect and track participants with persistent multi-object tracking.
- Attendance is evaluated based on **sustained presence** (e.g. participant present for > 60% of rolling session window or > 10 consecutive seconds) rather than single-frame detection, completely eliminating false positives caused by temporary appearances or passersby.
- Automatically generates timestamped attendance ledgers (`PRESENT`, `TARDY`, `ABSENT`, `TRANSIENT_IGNORED`) with export to CSV and JSON formats.

### 🔹 Scenario 2: Engagement and Session Dynamics Analysis
- Continuously analyzes behavioral indicators:
  - **Head Pose & 3D Gaze Orientation:** Yaw, Pitch, Roll estimation to identify frontal focus vs. looking at neighbors or smartphone/desk.
  - **Movement Patterns:** Kinetic displacement metrics distinguishing attentive note-taking from restless fidgeting.
  - **Inactivity & Drowsiness Detection:** Flags sustained immobility and downward head posture (> 12 seconds).
  - **Audio Activity & Classroom Acoustics:** Frame-level RMS energy and Voice Activity Detection (VAD) categorizing instructional states (`TEACHER_MONOLOGUE`, `STUDENT_DISCUSSION`, `CHATTER_SURGE`, `SUSTAINED_SILENCE`).
- Fuses vision and audio signals into a calibrated 0–100% engagement index with session timeline tracking.

### 🔹 Scenario 3: AI-Driven Teaching Suggestions
- An autonomous pedagogical decision-support agent evaluates real-time classroom telemetry and delivers non-intrusive, actionable interventions:
  - *"Attention dip detected across 60% of students during monologue → Suggestion: Introduce a quick poll or 2-minute Think-Pair-Share."*
  - *"Continuous teacher monologue exceeding 90 seconds → Suggestion: Check student comprehension with a cold-call prompt."*
  - *"Sustained silence detected → Suggestion: Offer a scaffolding hint."*
- Generates post-session pedagogical audit reports with engagement letter grades (A, B+, B, C, D), pacing breakdowns, strengths, and growth recommendations.

---

## 📊 Project Statistics & Structure

- **Total Epics:** 9
- **Total Tasks:** 17
- **Total Subtasks:** 0
- **Automated Tests:** 30 (100% passing)

See [EPICS_AND_TASKS.md](EPICS_AND_TASKS.md) for detailed task breakdowns and [ARCHITECTURE.md](ARCHITECTURE.md) for mathematical models.

```
multimodal-attendance-engagement-agent/
├── README.md                          # Comprehensive documentation
├── ARCHITECTURE.md                    # In-depth architectural & mathematical design
├── EPICS_AND_TASKS.md                 # 9 Epics and 17 Tasks tracking matrix
├── requirements.txt                   # Optional dependencies (pure Python core runs out-of-the-box)
├── pyproject.toml                     # Modern package manifest
├── config/
│   └── default_config.yaml            # System thresholds, temporal windows, fusion weights
├── data/
│   ├── sample_roster.json             # Enrolled student roster
│   ├── sample_session.wav             # Synthesized classroom audio
│   └── logs/                          # Output attendance logs & audit reports
├── src/
│   ├── __init__.py
│   ├── config.py                      # Strongly-typed configuration dataclasses & parsers
│   ├── privacy/
│   │   └── anonymizer.py              # HMAC-SHA256 pseudonymization & telemetry scrubber
│   ├── vision/
│   │   ├── face_tracker.py            # Multi-target spatial tracker & sustained presence
│   │   ├── head_pose.py               # Yaw, Pitch, Roll & 3D gaze focus classifier
│   │   ├── motion_analyzer.py         # Kinetic energy, micro-motion, and drowsiness detector
│   │   └── synthetic_video.py         # Classroom camera & multi-student stream simulator
│   ├── audio/
│   │   ├── vad.py                     # Voice Activity Detection & frame RMS energy
│   │   ├── acoustic_classifier.py     # Classroom acoustic dynamic state classifier
│   │   └── synthetic_audio.py         # Waveform synthesis & WAV stream reader
│   ├── fusion/
│   │   ├── multimodal_fusion.py       # Calibrated vision + audio composite engagement index
│   │   └── session_timeline.py        # Historical timeseries & milestone event detection
│   ├── agent/
│   │   ├── decision_rules.py          # Evidence-based pedagogical rule engine
│   │   └── teaching_agent.py          # Decision-support agent & post-session auditor
│   ├── attendance/
│   │   └── attendance_manager.py      # Sustained presence ledger, tardiness, & CSV/JSON export
│   └── web/
│       ├── server.py                  # High-concurrency HTTP server & REST API
│       ├── app_streamlit.py           # Optional Streamlit UI interface
│       └── static/
│           ├── index.html             # Glassmorphic single-page classroom dashboard
│           ├── style.css              # Modern dark-mode styling & canvas visualizer
│           └── app.js                 # Real-time WebSocket/polling live client controller
├── tests/
│   ├── test_privacy.py                # Pseudonymization & hashing tests
│   ├── test_attendance.py             # Sustained presence & passerby rejection tests
│   ├── test_vision.py                 # Face tracking, head pose, & motion tests
│   ├── test_audio.py                  # VAD & acoustic classification tests
│   ├── test_fusion.py                 # Multimodal fusion & timeline tests
│   ├── test_agent.py                  # Rule triggers & pedagogical audit tests
│   └── test_integration.py           # In-memory HTTP server & REST endpoint tests
└── scripts/
    ├── run_demo.py                    # Terminal simulation runner
    ├── generate_sample_data.py        # Sample roster and audio generator
    ├── run_dashboard.bat              # One-click Windows dashboard launcher
    ├── run_demo.bat                   # One-click Windows simulation demo launcher
    └── run_tests.bat                  # One-click Windows test runner
```

---

## 💻 System Requirements

### Hardware Requirements
- **Processor:** Intel Core i5 (8th Gen or above) / AMD Ryzen 5 or equivalent
- **RAM:** Minimum 8 GB (Recommended: 16 GB for concurrent vision streaming & multitasking)
- **Storage:** 256 GB SSD (or 500 GB HDD minimum)
- **Camera & Microphone (Optional for live classroom capture):** Standard 720p/1080p USB webcam & omnidirectional microphone

### Software Requirements
- **Operating System:** Windows 10 / 11, macOS (Monterey or later), or Linux (Ubuntu 20.04+)
- **Python:** Version 3.8 or above
- **Web Browser:** Latest version of Google Chrome, Mozilla Firefox, or Microsoft Edge

---

## 🚀 Quick Start Guide

### 1. Launch the Interactive Web Dashboard
Run the built-in HTTP dashboard server (starts in < 1 second, zero external packages needed):

```bash
python main.py dashboard --port 8080
```
Or double-click `scripts\run_dashboard.bat` on Windows.  
Open your browser to: **[http://127.0.0.1:8080](http://127.0.0.1:8080)**

#### Features in the Web Dashboard:
- **Spatial Perception HUD:** Real-time canvas rendering of classroom seating, bounding boxes, gaze orientation arrows, and colored attention auras.
- **Radial Engagement Gauge:** Instantaneous classroom attention index (0–100%) with focus category distribution.
- **Acoustic Waveform Visualizer:** Live classification of teacher monologue vs. collaborative dialogue vs. chatter vs. silence.
- **AI Teaching Suggestions Feed:** Real-time priority alerts with pedagogical rationale and recommendations.
- **Sustained Presence Attendance Ledger:** Live attendance records with one-click CSV export and privacy mode toggling.

---

### 2. Run the Terminal Simulation Demo
To observe the complete multimodal processing lifecycle in terminal:

```bash
python main.py demo --duration 30
```
Or double-click `scripts\run_demo.bat`.

Output showcases:
- Real-time ASCII telemetry ticks.
- Dynamic detection of active student engagement and drowsiness alerts.
- Automated attendance reconciliation verifying that sustained participants are marked `PRESENT`, late arrivals marked `TARDY`, and transient hallway passersby (`GUEST-999`) are filtered out as `TRANSIENT_IGNORED`.
- Automated export of `data/logs/demo_attendance.csv` and `data/logs/demo_audit.md`.

---

### 3. Run the Automated Test Suite
To verify all 30 unit and integration tests:

```bash
python main.py test
```
Or double-click `scripts\run_tests.bat`.

---

## 🔒 Privacy-Preserving Guarantees

Classroom deployments must respect student privacy and data sovereignty. This system is architected around 4 core privacy principles:
1. **Zero Raw Video Persistence:** Raw camera frames and audio buffers are processed transiently in volatile RAM and immediately discarded. No video is ever stored to disk.
2. **Cryptographic Pseudonymization:** Student identifiers can be masked into collision-resistant pseudonyms (`Learner-XXXX`) via HMAC-SHA256.
3. **One-Way Feature Hashing:** Facial geometric vectors are quantized and cryptographically hashed before audit logging, preventing biometric reconstruction.
4. **100% Offline Edge Execution:** All vision, acoustic, and decision reasoning operates strictly on-premise without cloud transmission.

---

## 📄 License
This project is licensed under the MIT License.
