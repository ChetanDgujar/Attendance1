# ⚖️ Ethical Guidelines & Responsible AI Framework
## Multimodal Attendance & Engagement Agent

The **Multimodal Attendance & Engagement Agent** is designed exclusively as an **assistive, decision-support tool** for educators. It provides macro-level classroom dynamics, pacing telemetry, and objective attendance tracking. 

This document outlines the core ethical principles, algorithmic limitations, demographic bias mitigations, and operational guardrails governing its deployment.

---

## 1. Core Ethical Principles

### 1.1 Non-Punitive & Assistive Purpose
- **Estimates, Not Judgments:** All calculated engagement scores (0–100) are **probabilistic estimates** of physical behavioral cues (gaze alignment, motion energy, vocal dynamics). They do **NOT** measure cognitive absorption, intelligence, character, or academic dedication.
- **Never Rank or Punish Students:** The system must never be used to grade, punish, discipline, or publicly rank individual learners.
- **Decision Support, Not Decision Automation:** The system generates pedagogical suggestions (e.g. "consider an interactive poll"). It never enforces instructional actions or automatic disciplinary measures.

### 1.2 Data Sovereignty & Zero Cloud Telemetry
- **100% Offline Edge Processing:** All computer vision, acoustic signal processing, and agent reasoning run locally on the host CPU. Zero telemetry, biometric data, or analytics leave the local machine.
- **Ephemeral Frame Analysis:** Raw camera video frames are processed transiently in memory and immediately discarded. No video recordings are persisted by default.
- **Cryptographic Pseudonymization:** All student identifiers can be masked using one-way HMAC-SHA256 hashes (`Learner-XXXX` or `Student_01`).
- **Configurable Data Retention:** Automated database purge cleans up session telemetry older than $N$ days (default: 30 days).

---

## 2. Technical Limitations & Bias Considerations

Educators and administrators must recognize that computer vision and acoustic sensors are subject to systematic physical and algorithmic biases:

| Factor | Algorithmic Risk / Bias | Mitigation Built Into System |
| :--- | :--- | :--- |
| **Camera Angle & Seating** | Students seated at the extreme periphery or in back rows appear at oblique angles, skewing Euler head pose estimation. | Bounding-box scale normalization; configurable yaw/pitch limits; multi-camera or front-facing calibration. |
| **Lighting & Shadows** | Poor illumination, backlighting from windows, or harsh shadows degrade facial landmark detection confidence. | Frame-level confidence thresholding; missing detections default to neutral score rather than penalizing. |
| **Skin Tone Variance** | Standard computer vision models can exhibit disparate accuracy across different Fitzpatrick skin tones under low lighting. | Offline contrast equalization; multi-modal fusion prevents reliance on vision alone. |
| **Eyeglasses & Headwear** | Thick frames, glare, hijabs, turbans, or masks may occlude landmarks. | Temporal sliding window smoothing; pose estimation uses multi-point facial aspect ratios. |
| **Disabilities & Neurodivergence** | Autistic students, individuals with ADHD, or motor conditions may avoid eye contact or display fidgeting while being intensely engaged. | Kinetic motion model distinguishes calm note-taking from restlessness; flags are surfaced privately to instructor as assistive cues only. |
| **Classroom Acoustics** | Omnidirectional microphones capture outside ambient noise, hallway footsteps, or HVAC hum. | Dual-threshold Voice Activity Detection (RMS energy + Zero Crossing Rate); transient noise filtering. |

---

## 3. Explicit Consent & Transparency Protocol

1. **Classroom Disclosure Notice:**  
   Prior to using the system in any educational setting, instructors must inform students:
   - What data is processed (facial orientation and classroom acoustic levels).
   - What data is NOT stored (no video or audio recordings are saved).
   - How insights are used (to help the teacher improve lesson pacing and timing).
2. **Opt-In Face Enrollment:**  
   Named student rosters are opt-in. In default mode, students are assigned anonymous identifiers (`Student_01`, `Student_02`, ...).
3. **Privacy Face Blurring:**  
   When preview frames are displayed in the dashboard, the optional `blur_faces: true` setting can obfuscate facial features.

---

## 4. Summary for Educators
> *"Technology in the classroom should illuminate teaching effectiveness, never diminish student dignity. Use this agent to reflect on your pacing, encourage quiet students, and break up long monologues—never to evaluate a learner's worth."*
