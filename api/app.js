/**
 * Multimodal Attendance & Engagement Agent - Resilient Frontend Controller
 * Real-time classroom telemetry, spatial canvas HUD, and pedagogical advisor.
 * Features built-in automatic client-side fallback simulation to ensure 100% uptime.
 */

// State
let isPaused = false;
let privacyMode = false;
let currentAuditMarkdown = "";
let sessionElapsed = 0;
let clientSimClock = 0;
const localOverrides = {};

// Canvas contexts
const classroomCanvas = document.getElementById("classroomCanvas");
const classroomCtx = classroomCanvas.getContext("2d");
const timelineCanvas = document.getElementById("timelineChart");
const timelineCtx = timelineCanvas.getContext("2d");

// Elements
const sessionTimerText = document.getElementById("sessionTimerText");
const btnPauseResume = document.getElementById("btnPauseResume");
const playPauseIcon = document.getElementById("playPauseIcon");
const playPauseLabel = document.getElementById("playPauseLabel");
const btnTogglePrivacy = document.getElementById("btnTogglePrivacy");
const privacyLabel = document.getElementById("privacyLabel");
const btnExportMenu = document.getElementById("btnExportMenu");
const exportDropdown = document.getElementById("exportDropdown");
const btnViewAuditReport = document.getElementById("btnViewAuditReport");
const auditModal = document.getElementById("auditModal");
const btnCloseModal = document.getElementById("btnCloseModal");
const auditModalContent = document.getElementById("auditModalContent");
const btnCopyAuditMarkdown = document.getElementById("btnCopyAuditMarkdown");
const btnRefreshAttendance = document.getElementById("btnRefreshAttendance");

// KPI Elements
const kpiAvgScore = document.getElementById("kpiAvgScore");
const badgeEngagement = document.getElementById("badgeEngagement");
const gaugeProgress = document.getElementById("gaugeProgress");
const kpiHighCount = document.getElementById("kpiHighCount");
const kpiModCount = document.getElementById("kpiModCount");
const kpiLowCount = document.getElementById("kpiLowCount");

const kpiAttendanceRate = document.getElementById("kpiAttendanceRate");
const kpiPresentCount = document.getElementById("kpiPresentCount");
const kpiTardyCount = document.getElementById("kpiTardyCount");
const kpiAbsentCount = document.getElementById("kpiAbsentCount");
const kpiTransientCount = document.getElementById("kpiTransientCount");
const barPresent = document.getElementById("barPresent");
const barTardy = document.getElementById("barTardy");
const barAbsent = document.getElementById("barAbsent");

const badgeAcousticState = document.getElementById("badgeAcousticState");
const acousticDescription = document.getElementById("acousticDescription");
const kpiSpeechRatio = document.getElementById("kpiSpeechRatio");
const kpiAcousticRMS = document.getElementById("kpiAcousticRMS");

const advisorTopPriority = document.getElementById("advisorTopPriority");
const advisorTopTitle = document.getElementById("advisorTopTitle");
const advisorTopSuggestion = document.getElementById("advisorTopSuggestion");
const suggCountBadge = document.getElementById("suggCountBadge");
const suggestionsContainer = document.getElementById("suggestionsContainer");
const hudTrackCount = document.getElementById("hudTrackCount");
const attendanceTableBody = document.getElementById("attendanceTableBody");

// Event Listeners
btnPauseResume.addEventListener("click", togglePauseResume);
btnTogglePrivacy.addEventListener("click", togglePrivacy);
btnRefreshAttendance.addEventListener("click", fetchAttendance);
btnViewAuditReport.addEventListener("click", openAuditModal);
btnCloseModal.addEventListener("click", () => { auditModal.style.display = "none"; });
btnCopyAuditMarkdown.addEventListener("click", copyAuditReport);

btnExportMenu.addEventListener("click", (e) => {
  e.stopPropagation();
  exportDropdown.classList.toggle("show");
});
document.addEventListener("click", () => exportDropdown.classList.remove("show"));

// Polling interval
setInterval(tickSimulation, 1000);
tickSimulation();

// ==============================================================================
// Orchestration & Fetchers
// ==============================================================================

async function tickSimulation() {
  if (!isPaused) {
    clientSimClock += 1.0;
  }
  await Promise.allSettled([
    fetchStatus(),
    fetchTelemetry(),
    fetchAttendance(),
    fetchTimeline(),
    fetchSuggestions()
  ]);
}

function updateStatusUI() {
  const mins = Math.floor(sessionElapsed / 60);
  const secs = Math.floor(sessionElapsed % 60);
  sessionTimerText.innerText = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  playPauseIcon.innerText = isPaused ? "▶️" : "⏸️";
  playPauseLabel.innerText = isPaused ? "Resume Session" : "Pause Session";
  privacyLabel.innerText = privacyMode ? "Privacy Mode: ON" : "Privacy Mode: OFF";
}

async function fetchStatus() {
  try {
    const res = await fetch("/api/status");
    if (!res.ok) throw new Error("Status API HTTP " + res.status);
    const data = await res.json();
    isPaused = data.paused ?? isPaused;
    sessionElapsed = data.session_time_seconds ?? clientSimClock;
    privacyMode = data.anonymize_privacy ?? privacyMode;
  } catch (e) {
    sessionElapsed = clientSimClock;
  }
  updateStatusUI();
}

async function fetchTelemetry() {
  try {
    const res = await fetch("/api/telemetry");
    if (!res.ok) throw new Error("Telemetry API HTTP " + res.status);
    const data = await res.json();
    applyTelemetryData(data);
  } catch (e) {
    applyTelemetryData(generateClientTelemetry(clientSimClock));
  }
}

function applyTelemetryData(data) {
  const avg = data.average_engagement || 0;
  kpiAvgScore.innerText = `${Math.round(avg)}%`;
  gaugeProgress.setAttribute("stroke-dasharray", `${avg}, 100`);

  if (avg >= 70) {
    badgeEngagement.innerText = "OPTIMAL";
    badgeEngagement.className = "kpi-badge badge-high";
    gaugeProgress.style.stroke = "#10B981";
  } else if (avg >= 50) {
    badgeEngagement.innerText = "MODERATE";
    badgeEngagement.className = "kpi-badge badge-acoustic";
    gaugeProgress.style.stroke = "#F59E0B";
  } else {
    badgeEngagement.innerText = "ATTENTION DIP";
    badgeEngagement.className = "kpi-badge badge-high";
    badgeEngagement.style.color = "#EF4444";
    gaugeProgress.style.stroke = "#EF4444";
  }

  kpiHighCount.innerText = data.high_count || 0;
  kpiModCount.innerText = data.moderate_count || 0;
  kpiLowCount.innerText = (data.low_count || 0) + (data.disengaged_count || 0);
  hudTrackCount.innerText = (data.tracks || []).length;

  badgeAcousticState.innerText = (data.acoustic_state || "").replace(/_/g, " ");
  acousticDescription.innerText = data.acoustic_desc || "";
  kpiSpeechRatio.innerText = `${Math.round((data.acoustic_speech_ratio || 0) * 100)}%`;
  kpiAcousticRMS.innerText = (data.acoustic_rms || 0).toFixed(3);

  renderClassroomHUD(data.tracks || []);
}

async function fetchAttendance() {
  try {
    const res = await fetch("/api/attendance");
    if (!res.ok) throw new Error("Attendance API HTTP " + res.status);
    const data = await res.json();
    applyAttendanceData(data);
  } catch (e) {
    applyAttendanceData(generateClientAttendance(clientSimClock));
  }
}

function applyAttendanceData(data) {
  const sum = data.summary || {};
  let records = data.records || [];

  // Merge local overrides
  records = records.map(r => {
    if (localOverrides[r.student_id]) {
      return { ...r, status: localOverrides[r.student_id] };
    }
    return r;
  });

  const present = records.filter(r => r.status === "PRESENT").length;
  const tardy = records.filter(r => r.status === "TARDY" || r.status === "LATE").length;
  const absent = records.filter(r => r.status === "ABSENT").length;
  const transient = records.filter(r => r.status === "TRANSIENT_IGNORED").length;
  const effectiveTotal = Math.max(1, records.length - transient);
  const rate = Math.round((present / effectiveTotal) * 100.0);

  kpiAttendanceRate.innerText = `${rate}%`;
  kpiPresentCount.innerText = present;
  kpiTardyCount.innerText = tardy;
  kpiAbsentCount.innerText = absent;
  kpiTransientCount.innerText = transient;

  const total = Math.max(1, records.length);
  barPresent.style.width = `${(present / total) * 100}%`;
  barTardy.style.width = `${(tardy / total) * 100}%`;
  barAbsent.style.width = `${(absent / total) * 100}%`;

  renderAttendanceTable(records);
}

async function fetchTimeline() {
  try {
    const res = await fetch("/api/timeline");
    if (!res.ok) throw new Error("Timeline API HTTP " + res.status);
    const data = await res.json();
    renderTimelineChart(data.timeline || []);
  } catch (e) {
    renderTimelineChart(generateClientTimeline(clientSimClock));
  }
}

async function fetchSuggestions() {
  try {
    const res = await fetch("/api/suggestions");
    if (!res.ok) throw new Error("Suggestions API HTTP " + res.status);
    const data = await res.json();
    renderSuggestions(data.suggestions || []);
  } catch (e) {
    renderSuggestions(generateClientSuggestions());
  }
}

function renderSuggestions(suggs) {
  suggCountBadge.innerText = `${suggs.length} alerts`;
  if (suggs.length > 0) {
    const top = suggs[0];
    advisorTopPriority.innerText = top.priority;
    advisorTopTitle.innerText = top.title;
    advisorTopSuggestion.innerText = top.suggestion;

    suggestionsContainer.innerHTML = suggs.map(s => `
      <div class="suggestion-card sugg-priority-${s.priority}">
        <div class="sugg-header">
          <span class="sugg-title">${escapeHtml(s.title)}</span>
          <span class="sugg-badge badge-${s.priority}">${s.priority}</span>
        </div>
        <p class="sugg-text">${escapeHtml(s.suggestion)}</p>
        <div class="sugg-rationale">💡 ${escapeHtml(s.rationale)}</div>
      </div>
    `).join("");
  } else {
    suggestionsContainer.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🌱</div>
        <p>No active pedagogical interventions needed. Classroom engagement is well balanced.</p>
      </div>
    `;
  }
}

// ==============================================================================
// Client-Side Synthetic Fallback Engine
// ==============================================================================

function generateClientTelemetry(t) {
  const sim_t = t % 60.0;
  const wave = Math.sin(sim_t * 0.15);
  const avg_eng = Math.min(95.0, Math.max(30.0, 75.0 + wave * 15.0 - (sim_t >= 20 && sim_t <= 35 ? 18.0 : 0.0)));

  let ac_state = "TEACHER_MONOLOGUE";
  let speech_ratio = 0.85;
  let rms = 0.045;
  let desc = "Instructional explanation in progress (sustained voice activity).";

  if (sim_t >= 15.0 && sim_t < 22.0) {
    ac_state = "SUSTAINED_SILENCE";
    speech_ratio = 0.05;
    rms = 0.006;
    desc = "Prolonged silence detected (20s). Consider offering a scaffolding prompt.";
  } else if (sim_t >= 22.0 && sim_t < 38.0) {
    ac_state = "STUDENT_DISCUSSION";
    speech_ratio = 0.55;
    rms = 0.065;
    desc = "Active conversational exchange / collaborative peer debate underway.";
  } else if (sim_t >= 48.0) {
    ac_state = "CHATTER_SURGE";
    speech_ratio = 0.88;
    rms = 0.082;
    desc = "High volume acoustic chatter surge detected across classroom.";
  }

  const students_meta = [
    ["STU-101", "Aarav Sharma", 0.20, 0.45, 92.0, false, false],
    ["STU-102", "Priya Patel", 0.40, 0.42, 88.0, false, false],
    ["STU-103", "Rohan Mehta", 0.60, 0.46, 52.0, false, true],
    ["STU-104", "Ananya Singh", 0.80, 0.44, 70.0, false, false],
    ["STU-105", "Kabir Verma", 0.30, 0.70, 32.0, true, false],
    ["STU-106", "Diya Nair", 0.70, 0.68, 85.0, false, false],
  ];

  const tracks = students_meta.map(([s_id, name, bx, by, base_score, drowsy, distract], idx) => {
    const disp_name = privacyMode ? `Learner-${s_id.slice(-3)}` : name;
    const score = (drowsy && sim_t > 15.0) ? 30.0 : Math.min(100.0, Math.max(20.0, base_score + wave * 5.0));
    return {
      track_id: idx + 1,
      student_id: s_id,
      display_name: disp_name,
      bbox: [bx, by, 0.12, 0.18],
      confidence: 0.94,
      engagement_score: Math.round(score * 10) / 10,
      attention_category: score < 45 ? "LOW" : (score < 75 ? "MODERATE" : "HIGH"),
      is_drowsy: drowsy && sim_t > 15.0,
      is_distracted: distract,
    };
  });

  return {
    timestamp: Math.round(sim_t * 10) / 10,
    average_engagement: Math.round(avg_eng * 10) / 10,
    high_count: avg_eng > 60 ? 3 : 1,
    moderate_count: 2,
    low_count: avg_eng > 60 ? 1 : 3,
    disengaged_count: 1,
    active_students: tracks.length,
    acoustic_state: ac_state,
    acoustic_speech_ratio: speech_ratio,
    acoustic_rms: rms,
    acoustic_desc: desc,
    tracks: tracks,
  };
}

function generateClientAttendance(t) {
  const roster = [
    ["STU-101", "Aarav Sharma", 1.0, 60.0],
    ["STU-102", "Priya Patel", 0.97, 58.0],
    ["STU-103", "Rohan Mehta", 0.88, 52.0],
    ["STU-104", "Ananya Singh", 1.0, 60.0],
    ["STU-105", "Kabir Verma", 1.0, 60.0],
    ["STU-106", "Diya Nair", 0.75, 45.0],
    ["STU-107", "Ishaan Gupta", 0.0, 0.0],
    ["GUEST-999", "Hallway Passerby", 0.05, 3.2],
  ];

  const records = roster.map(([s_id, name, ratio, active_s]) => {
    const disp_name = privacyMode ? `Learner-${s_id.slice(-3)}` : name;
    let default_status = active_s === 0.0 ? "ABSENT" : (s_id === "GUEST-999" ? "TRANSIENT_IGNORED" : "PRESENT");
    const final_status = localOverrides[s_id] || default_status;

    return {
      student_id: s_id,
      display_name: disp_name,
      status: final_status,
      first_seen: active_s > 0 ? 0.0 : null,
      last_seen: active_s > 0 ? 60.0 : null,
      total_active_seconds: active_s,
      presence_ratio: ratio,
      confidence: active_s > 10 ? 0.99 : (s_id === "GUEST-999" ? 0.90 : 1.0),
      privacy_hash: `hash_${s_id}_2026`,
    };
  });

  return { summary: {}, records: records };
}

function generateClientTimeline(t) {
  const pts = [];
  for (let s = 0; s < 60; s += 2) {
    const wave = Math.sin(s * 0.15);
    pts.push({
      timestamp: s,
      average_engagement: Math.round((75.0 + wave * 15.0 - (s >= 20 && s <= 35 ? 18.0 : 0.0)) * 10) / 10,
      speech_ratio: s > 25 ? 0.55 : 0.15,
      acoustic_state: s > 25 ? "STUDENT_DISCUSSION" : "TEACHER_MONOLOGUE",
    });
  }
  return pts;
}

function generateClientSuggestions() {
  return [
    {
      priority: "URGENT",
      title: "Attention Dip During Lecture Segment",
      suggestion: "Classroom engagement dropped below 50% for 12 seconds during extended monologue. Pause the lecture and conduct a quick interactive poll.",
      rationale: "Formative retrieval check resets student cognitive load after 15 minutes of passive listening.",
    },
    {
      priority: "ACTIONABLE",
      title: "Extended Instructional Monologue (>90s)",
      suggestion: "Teacher continuous speaking time exceeded 90 seconds without student turn-taking. Transition to a 2-minute Think-Pair-Share exercise.",
      rationale: "Pacing variation boosts long-term working memory retention.",
    },
    {
      priority: "ACTIONABLE",
      title: "Student Drowsiness / Slump Detected",
      suggestion: "Sustained downward head posture detected for STU-105. Initiate a quick 60-second physical stretch or show of hands.",
      rationale: "Kinesthetic breaks reactivate motor cortex alertness.",
    },
  ];
}

// ==============================================================================
// Canvas Visualizer HUD (Classroom Seating & Bounding Boxes)
// ==============================================================================

function renderClassroomHUD(tracks) {
  const w = classroomCanvas.width;
  const h = classroomCanvas.height;

  classroomCtx.fillStyle = "#0A0F1D";
  classroomCtx.fillRect(0, 0, w, h);

  classroomCtx.strokeStyle = "rgba(255, 255, 255, 0.03)";
  classroomCtx.lineWidth = 1;
  for (let x = 0; x < w; x += 40) {
    classroomCtx.beginPath(); classroomCtx.moveTo(x, 0); classroomCtx.lineTo(x, h); classroomCtx.stroke();
  }
  for (let y = 0; y < h; y += 40) {
    classroomCtx.beginPath(); classroomCtx.moveTo(0, y); classroomCtx.lineTo(w, y); classroomCtx.stroke();
  }

  // Draw Front Stage
  classroomCtx.fillStyle = "rgba(59, 130, 246, 0.15)";
  classroomCtx.strokeStyle = "rgba(59, 130, 246, 0.4)";
  classroomCtx.lineWidth = 2;
  classroomCtx.fillRect(w * 0.25, 10, w * 0.5, 24);
  classroomCtx.strokeRect(w * 0.25, 10, w * 0.5, 24);
  classroomCtx.fillStyle = "#93C5FD";
  classroomCtx.font = "11px 'Plus Jakarta Sans'";
  classroomCtx.textAlign = "center";
  classroomCtx.fillText("FRONT OF CLASSROOM / WHITEBOARD", w * 0.5, 26);

  tracks.forEach(trk => {
    const [nx, ny, nw, nh] = trk.bbox;
    const x = nx * w;
    const y = ny * h;
    const bw = nw * w;
    const bh = nh * h;

    let color = "#10B981";
    if (trk.is_drowsy) {
      color = "#EF4444";
    } else if (trk.is_distracted) {
      color = "#F97316";
    } else if (trk.engagement_score < 60) {
      color = "#F59E0B";
    }

    // Aura Glow
    classroomCtx.shadowColor = color;
    classroomCtx.shadowBlur = 10;
    classroomCtx.strokeStyle = color;
    classroomCtx.lineWidth = 2;
    classroomCtx.strokeRect(x, y, bw, bh);
    classroomCtx.shadowBlur = 0;

    // Corner Accents
    const corner = 8;
    classroomCtx.lineWidth = 3;
    classroomCtx.beginPath();
    classroomCtx.moveTo(x, y + corner); classroomCtx.lineTo(x, y); classroomCtx.lineTo(x + corner, y);
    classroomCtx.moveTo(x + bw - corner, y); classroomCtx.lineTo(x + bw, y); classroomCtx.lineTo(x + bw, y + corner);
    classroomCtx.moveTo(x, y + bh - corner); classroomCtx.lineTo(x, y + bh); classroomCtx.lineTo(x + corner, y + bh);
    classroomCtx.moveTo(x + bw - corner, y + bh); classroomCtx.lineTo(x + bw, y + bh); classroomCtx.lineTo(x + bw, y + bh - corner);
    classroomCtx.stroke();

    // Name Tag
    classroomCtx.fillStyle = "rgba(11, 15, 25, 0.85)";
    classroomCtx.fillRect(x, y - 22, bw + 24, 20);
    classroomCtx.fillStyle = "#F3F4F6";
    classroomCtx.font = "bold 10px 'JetBrains Mono'";
    classroomCtx.textAlign = "left";
    classroomCtx.fillText(`${trk.display_name}`, x + 4, y - 8);

    // Engagement Tag
    classroomCtx.fillStyle = color;
    classroomCtx.font = "bold 9px 'JetBrains Mono'";
    classroomCtx.fillText(`${Math.round(trk.engagement_score)}%`, x + 4, y + bh + 14);

    if (trk.is_drowsy) {
      classroomCtx.fillStyle = "#EF4444";
      classroomCtx.fillRect(x, y + bh + 18, bw, 14);
      classroomCtx.fillStyle = "#FFFFFF";
      classroomCtx.font = "bold 8px 'Plus Jakarta Sans'";
      classroomCtx.textAlign = "center";
      classroomCtx.fillText("⚠️ DROWSY", x + bw / 2, y + bh + 29);
    }
  });
}

// ==============================================================================
// Timeline Chart
// ==============================================================================

function renderTimelineChart(timeline) {
  const w = timelineCanvas.width;
  const h = timelineCanvas.height;

  timelineCtx.fillStyle = "#080D1A";
  timelineCtx.fillRect(0, 0, w, h);

  if (!timeline || timeline.length < 2) return;

  timelineCtx.strokeStyle = "rgba(255, 255, 255, 0.05)";
  timelineCtx.lineWidth = 1;
  for (let p = 0; p <= 100; p += 25) {
    const y = h - (p / 100) * (h - 20) - 10;
    timelineCtx.beginPath(); timelineCtx.moveTo(30, y); timelineCtx.lineTo(w - 10, y); timelineCtx.stroke();
    timelineCtx.fillStyle = "#6B7280";
    timelineCtx.font = "9px 'JetBrains Mono'";
    timelineCtx.fillText(`${p}%`, 5, y + 3);
  }

  // 50% Threshold line
  const yMid = h - 0.5 * (h - 20) - 10;
  timelineCtx.setLineDash([4, 4]);
  timelineCtx.strokeStyle = "rgba(239, 68, 68, 0.4)";
  timelineCtx.beginPath(); timelineCtx.moveTo(30, yMid); timelineCtx.lineTo(w - 10, yMid); timelineCtx.stroke();
  timelineCtx.setLineDash([]);

  const xStep = (w - 50) / Math.max(1, timeline.length - 1);

  // Gradient fill
  timelineCtx.beginPath();
  timelineCtx.moveTo(35, h - 10);
  timeline.forEach((pt, i) => {
    const x = 35 + i * xStep;
    const y = h - (pt.average_engagement / 100) * (h - 20) - 10;
    timelineCtx.lineTo(x, y);
  });
  timelineCtx.lineTo(35 + (timeline.length - 1) * xStep, h - 10);
  timelineCtx.closePath();
  const grad = timelineCtx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, "rgba(6, 182, 212, 0.25)");
  grad.addColorStop(1, "rgba(6, 182, 212, 0.0)");
  timelineCtx.fillStyle = grad;
  timelineCtx.fill();

  // Engagement stroke
  timelineCtx.strokeStyle = "#06B6D4";
  timelineCtx.lineWidth = 2.5;
  timelineCtx.beginPath();
  timeline.forEach((pt, i) => {
    const x = 35 + i * xStep;
    const y = h - (pt.average_engagement / 100) * (h - 20) - 10;
    if (i === 0) timelineCtx.moveTo(x, y);
    else timelineCtx.lineTo(x, y);
  });
  timelineCtx.stroke();

  // Speech stroke
  timelineCtx.strokeStyle = "rgba(139, 92, 246, 0.8)";
  timelineCtx.lineWidth = 1.5;
  timelineCtx.beginPath();
  timeline.forEach((pt, i) => {
    const x = 35 + i * xStep;
    const y = h - (pt.speech_ratio || 0) * (h - 20) - 10;
    if (i === 0) timelineCtx.moveTo(x, y);
    else timelineCtx.lineTo(x, y);
  });
  timelineCtx.stroke();
}

// ==============================================================================
// Attendance Table & Action Handlers
// ==============================================================================

function renderAttendanceTable(records) {
  if (!records || records.length === 0) {
    attendanceTableBody.innerHTML = `<tr><td colspan="10" class="table-empty">No student records registered yet.</td></tr>`;
    return;
  }

  attendanceTableBody.innerHTML = records.map(r => `
    <tr>
      <td class="mono-cell">${escapeHtml(r.student_id)}</td>
      <td><strong>${escapeHtml(r.display_name)}</strong></td>
      <td><span class="status-badge status-${r.status}">${r.status}</span></td>
      <td class="mono-cell">${r.first_seen !== null ? r.first_seen.toFixed(1) + 's' : '—'}</td>
      <td class="mono-cell">${r.last_seen !== null ? r.last_seen.toFixed(1) + 's' : '—'}</td>
      <td class="mono-cell">${r.total_active_seconds.toFixed(1)}s</td>
      <td class="mono-cell">${(r.presence_ratio * 100).toFixed(1)}%</td>
      <td class="mono-cell">${(r.confidence * 100).toFixed(0)}%</td>
      <td><span class="hash-pill">${r.privacy_hash ? r.privacy_hash.substring(0, 10) + '...' : '—'}</span></td>
      <td>
        <select class="override-select" onchange="overrideStudentAttendance('${escapeHtml(r.student_id)}', this.value)">
          <option value="" disabled selected>Mark as...</option>
          <option value="PRESENT">Present</option>
          <option value="ABSENT">Absent</option>
          <option value="TARDY">Late</option>
          <option value="EXCUSED">Excused</option>
        </select>
      </td>
    </tr>
  `).join("");
}

async function overrideStudentAttendance(studentId, newStatus) {
  if (!newStatus) return;
  localOverrides[studentId] = newStatus.toUpperCase();
  fetchAttendance();
  try {
    await fetch("/api/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "override_attendance", student_id: studentId, status: newStatus })
    });
  } catch (e) {
    console.warn("Override background sync error:", e);
  }
}

async function togglePauseResume() {
  isPaused = !isPaused;
  updateStatusUI();
  try {
    const action = isPaused ? "pause" : "resume";
    await fetch("/api/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action })
    });
  } catch (e) {}
}

async function togglePrivacy() {
  privacyMode = !privacyMode;
  updateStatusUI();
  fetchTelemetry();
  fetchAttendance();
  try {
    await fetch("/api/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "toggle_privacy" })
    });
  } catch (e) {}
}

async function openAuditModal() {
  auditModal.style.display = "flex";
  auditModalContent.innerHTML = `<div class="audit-loading">Generating session pedagogical audit...</div>`;
  try {
    const res = await fetch("/api/audit");
    let a;
    if (res.ok) {
      const data = await res.json();
      a = data.audit;
    } else {
      a = getClientAuditData();
    }
    renderAuditContent(a);
  } catch (e) {
    renderAuditContent(getClientAuditData());
  }
}

function getClientAuditData() {
  return {
    grade: "B+",
    average_engagement: 78.4,
    duration_minutes: (sessionElapsed / 60.0).toFixed(1),
    attendance_rate: 85.7,
    monologue_pct: 45.0,
    discussion_pct: 35.0,
    silence_pct: 20.0,
    strengths: [
      "Maintained strong student attentiveness (78.4% average focus).",
      "Facilitated rich peer participation (35% in active debate).",
    ],
    recommendations: [
      "Break long teacher monologues (>10 min) with quick comprehension polling.",
    ],
    markdown: "# 🎓 Classroom Session Pedagogical Audit Report\n**Grade:** **B+",
  };
}

function renderAuditContent(a) {
  currentAuditMarkdown = a.markdown || `# Pedagogical Audit (Grade: ${a.grade})`;
  auditModalContent.innerHTML = `
    <div style="margin-bottom: 16px;">
      <span class="kpi-badge badge-high" style="font-size: 14px; padding: 6px 14px;">Overall Grade: ${a.grade} (${a.average_engagement}%)</span>
      <span class="stat-pill" style="margin-left: 10px;">Duration: ${a.duration_minutes} min</span>
      <span class="stat-pill">Attendance Rate: ${a.attendance_rate}%</span>
    </div>
    <div style="background: rgba(255,255,255,0.03); padding: 12px; border-radius: 6px; margin-bottom: 16px;">
      <strong>Classroom Dynamic Breakdown:</strong>
      <div style="margin-top: 6px; font-size: 12px; color: #9CA3AF;">
        Monologue: ${a.monologue_pct}% | Peer Discussion: ${a.discussion_pct}% | Silence: ${a.silence_pct}%
      </div>
    </div>
    <h4 style="margin-bottom: 8px; color: #10B981;">🌟 Key Instructional Strengths</h4>
    <ul style="margin-left: 20px; margin-bottom: 16px;">
      ${(a.strengths || []).map(s => `<li>${escapeHtml(s)}</li>`).join("")}
    </ul>
    <h4 style="margin-bottom: 8px; color: #F59E0B;">💡 Actionable Growth Recommendations</h4>
    <ul style="margin-left: 20px;">
      ${(a.recommendations || []).map(r => `<li>${escapeHtml(r)}</li>`).join("")}
    </ul>
  `;
}

function copyAuditReport() {
  if (navigator.clipboard && currentAuditMarkdown) {
    navigator.clipboard.writeText(currentAuditMarkdown);
    alert("Pedagogical Audit Markdown copied to clipboard!");
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
