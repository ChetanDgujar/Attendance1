# 📋 Project Epics & Tasks Breakdown

### Project: Multimodal Attendance & Engagement Agent
**Total Epics:** 9  
**Total Tasks:** 17  
**Total Subtasks:** 0  

---

## 🏛 Epic 1: System Architecture & Privacy-First Foundations
- **Task 1: Configuration Management & Architecture Orchestration**  
  *Files:* `src/config.py`, `config/default_config.yaml`  
  *Scope:* Establish modular system configuration with typed dataclasses, threshold definitions for vision, audio, fusion, agent alerts, and fallback parsers supporting zero-dependency execution.
- **Task 2: Privacy Engine, Pseudonymization & One-Way Hashing**  
  *Files:* `src/privacy/anonymizer.py`  
  *Scope:* Implement cryptographic identity pseudonymization (`Learner-XXXX`), SHA-256 HMAC feature-level perceptual hashing, and real-time telemetry scrubber ensuring zero raw video or biometrics persist to disk.

---

## 🎥 Epic 2: Video Stream Processing & Spatial Perception
- **Task 3: Video Ingestion & Stream Simulation Engine**  
  *Files:* `src/vision/synthetic_video.py`  
  *Scope:* Implement flexible video stream ingestion supporting live webcam, recorded video files (MP4/AVI), and a classroom multi-student persona simulation engine (attentive, distracted, drowsy, late-comer, transient passerby).
- **Task 4: Multi-Object Spatial Participant Tracking**  
  *Files:* `src/vision/face_tracker.py`  
  *Scope:* Build multi-target spatial bounding tracker with IoU matching, Euclidean center distance association, track lifetime management, and visibility filtering.

---

## 📋 Epic 3: Sustained Presence & Automated Attendance Tracking Engine
- **Task 5: Sustained Presence Temporal Filter & Anti-Glitch Verification**  
  *Files:* `src/attendance/attendance_manager.py`  
  *Scope:* Implement sliding time window verification (`sustained_window_sec = 10s`) that filters out momentary appearances (such as hallway passersby or lighting glitches) and marks presence based on continuous observation.
- **Task 6: Automated Attendance Ledger, Tardy Detection & Export Suite**  
  *Files:* `src/attendance/attendance_manager.py`  
  *Scope:* Classify attendance states (`PRESENT`, `TARDY`, `ABSENT`, `TRANSIENT_IGNORED`), compute presence ratios and confidence scores, and generate automated CSV and JSON logs.

---

## 👁️ Epic 4: Visual Engagement & Behavioral Dynamics Analysis
- **Task 7: 3D Head Pose Estimation & Gaze Classification**  
  *Files:* `src/vision/head_pose.py`  
  *Scope:* Compute rotational Euler angles (Yaw, Pitch, Roll) and classify visual attention states (`FOCUSED`, `DISTRACTED_LEFT`, `DISTRACTED_RIGHT`, `LOOKING_DOWN`, `LOOKING_UP`) with normalized gaze focus metrics.
- **Task 8: Micro-Motion Energy & Inactivity/Drowsiness Detection**  
  *Files:* `src/vision/motion_analyzer.py`  
  *Scope:* Track frame-to-frame kinetic displacement, distinguish natural note-taking micro-motions from restless fidgeting, and detect sustained downward immobility (>12s) to trigger drowsiness alerts.

---

## 🎙️ Epic 5: Classroom Acoustic Dynamics & Audio Signal Processing
- **Task 9: Voice Activity Detection (VAD) & Frame-Level RMS Energy**  
  *Files:* `src/audio/vad.py`  
  *Scope:* Implement frame-level Root Mean Square (RMS) energy extraction and Zero Crossing Rate (ZCR) analysis to determine human vocal presence without external cloud dependencies.
- **Task 10: Classroom Acoustic State Classifier & WAV Processor**  
  *Files:* `src/audio/acoustic_classifier.py`, `src/audio/synthetic_audio.py`  
  *Scope:* Categorize classroom acoustic environment over rolling temporal horizons into `TEACHER_MONOLOGUE`, `STUDENT_DISCUSSION`, `CHATTER_SURGE`, `SUSTAINED_SILENCE`, and `BALANCED_ENGAGEMENT`.

---

## 🔀 Epic 6: Multimodal Fusion & Temporal Session Dynamics
- **Task 11: Multimodal Composite Engagement Scoring Engine**  
  *Files:* `src/fusion/multimodal_fusion.py`  
  *Scope:* Compute calibrated individual and classroom-level engagement indices by fusing gaze alignment, head pose stability, posture kinetics, and acoustic context with penalty terms for drowsiness and distraction.
- **Task 12: Session Timeline Tracker & Critical Event Detector**  
  *Files:* `src/fusion/session_timeline.py`  
  *Scope:* Maintain chronological telemetry time-series and detect macro milestones including sustained attention dips, interaction peaks, chatter surges, and dead silences.

---

## 🤖 Epic 7: AI-Driven Pedagogical Decision Support Agent
- **Task 13: Context-Aware Pedagogical Rule Engine**  
  *Files:* `src/agent/decision_rules.py`  
  *Scope:* Formulate evidence-based educational heuristics that trigger actionable teaching recommendations (e.g. quick formative polling, think-pair-share, scaffolding hints, stretch breaks) based on real-time classroom telemetry.
- **Task 14: Autonomous Teaching Advisor & Post-Session Pedagogical Audit**  
  *Files:* `src/agent/teaching_agent.py`  
  *Scope:* Provide alert cooldown management to prevent cognitive overload for the teacher, generate structured LLM-compatible prompts, and compile end-of-session pedagogical audits with letter grades, strengths, and recommendations.

---

## 🖥️ Epic 8: Interactive Classroom Intelligence Web Dashboard
- **Task 15: High-Concurrency REST Telemetry Server**  
  *Files:* `src/web/server.py`  
  *Scope:* Multi-threaded zero-dependency HTTP server delivering real-time REST endpoints (`/api/telemetry`, `/api/attendance`, `/api/timeline`, `/api/suggestions`, `/api/audit`, `/api/action`) and session controls.
- **Task 16: Interactive Glassmorphic Web Dashboard UI**  
  *Files:* `src/web/static/index.html`, `style.css`, `app.js`, `src/web/app_streamlit.py`  
  *Scope:* Single-page web dashboard featuring real-time radial engagement gauges, animated audio waveform, HTML5 Canvas spatial seating HUD with gaze arrows, interactive timeline charts, and live attendance ledger.

---

## 🧪 Epic 9: Verification, Testing & System Validation
- **Task 17: Comprehensive Unit & Integration Test Suite**  
  *Files:* `tests/test_*.py`, `scripts/run_tests.bat`, `scripts/run_demo.py`  
  *Scope:* 30 comprehensive unit and integration tests covering privacy hashing, sustained presence, head pose classification, VAD audio processing, multimodal fusion, agent decision rules, and HTTP REST APIs.
