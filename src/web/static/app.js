/**
 * Multimodal Attendance & Engagement Agent - Frontend Controller
 * Real-time classroom telemetry, spatial canvas HUD, and pedagogical advisor.
 */

// State
let isPaused = false;
let privacyMode = false;
let currentAuditMarkdown = "";
let sessionElapsed = 0;

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
setInterval(fetchAllTelemetry, 800);
fetchAllTelemetry();

// ==============================================================================
// Telemetry Fetchers
// ==============================================================================

async function fetchAllTelemetry() {
  await Promise.all([
    fetchStatus(),
    fetchTelemetry(),
    fetchAttendance(),
    fetchTimeline(),
    fetchSuggestions()
  ]);
}

async function fetchStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    isPaused = data.paused;
    sessionElapsed = data.session_time_seconds;
    privacyMode = data.anonymize_privacy;

    // Timer format MM:SS
    const mins = Math.floor(sessionElapsed / 60);
    const secs = Math.floor(sessionElapsed % 60);
    sessionTimerText.innerText = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

    playPauseIcon.innerText = isPaused ? "▶️" : "⏸️";
    playPauseLabel.innerText = isPaused ? "Resume Session" : "Pause Session";
    privacyLabel.innerText = privacyMode ? "Privacy Mode: ON" : "Privacy Mode: OFF";
  } catch (e) {
    console.error("Status fetch error", e);
  }
}

async function fetchTelemetry() {
  try {
    const res = await fetch("/api/telemetry");
    const data = await res.json();

    // 1. Update KPI Engagement
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

    // 2. Update Acoustic State
    badgeAcousticState.innerText = (data.acoustic_state || "").replace("_", " ");
    acousticDescription.innerText = data.acoustic_desc || "";
    kpiSpeechRatio.innerText = `${Math.round((data.acoustic_speech_ratio || 0) * 100)}%`;
    kpiAcousticRMS.innerText = (data.acoustic_rms || 0).toFixed(3);

    // 3. Render Classroom Spatial Canvas
    renderClassroomHUD(data.tracks || []);
  } catch (e) {
    console.error("Telemetry fetch error", e);
  }
}

async function fetchAttendance() {
  try {
    const res = await fetch("/api/attendance");
    const data = await res.json();
    const sum = data.summary || {};

    kpiAttendanceRate.innerText = `${sum.attendance_rate_percent || 0}%`;
    kpiPresentCount.innerText = sum.present_count || 0;
    kpiTardyCount.innerText = sum.tardy_count || 0;
    kpiAbsentCount.innerText = sum.absent_count || 0;
    kpiTransientCount.innerText = sum.transient_ignored_count || 0;

    const total = sum.total_students || 1;
    barPresent.style.width = `${((sum.present_count || 0) / total) * 100}%`;
    barTardy.style.width = `${((sum.tardy_count || 0) / total) * 100}%`;
    barAbsent.style.width = `${((sum.absent_count || 0) / total) * 100}%`;

    // Render Table
    renderAttendanceTable(data.records || []);
  } catch (e) {
    console.error("Attendance fetch error", e);
  }
}

async function fetchTimeline() {
  try {
    const res = await fetch("/api/timeline");
    const data = await res.json();
    renderTimelineChart(data.timeline || []);
  } catch (e) {
    console.error("Timeline fetch error", e);
  }
}

async function fetchSuggestions() {
  try {
    const res = await fetch("/api/suggestions");
    const data = await res.json();
    const suggs = data.suggestions || [];
    suggCountBadge.innerText = `${suggs.length} alerts`;

    if (suggs.length > 0) {
      const top = suggs[0];
      advisorTopPriority.innerText = top.priority;
      advisorTopTitle.innerText = top.title;
      advisorTopSuggestion.innerText = top.suggestion;

      // Render suggestions feed
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
  } catch (e) {
    console.error("Suggestions fetch error", e);
  }
}

// ==============================================================================
// Canvas Visualizer HUD (Classroom Seating & Bounding Boxes)
// ==============================================================================

function renderClassroomHUD(tracks) {
  const w = classroomCanvas.width;
  const h = classroomCanvas.height;

  // Background Classroom Floor & Desks
  classroomCtx.fillStyle = "#0A0F1D";
  classroomCtx.fillRect(0, 0, w, h);

  // Grid lines
  classroomCtx.strokeStyle = "rgba(255, 255, 255, 0.03)";
  classroomCtx.lineWidth = 1;
  for (let x = 0; x < w; x += 40) {
    classroomCtx.beginPath(); classroomCtx.moveTo(x, 0); classroomCtx.lineTo(x, h); classroomCtx.stroke();
  }
  for (let y = 0; y < h; y += 40) {
    classroomCtx.beginPath(); classroomCtx.moveTo(0, y); classroomCtx.lineTo(w, y); classroomCtx.stroke();
  }

  // Draw Whiteboard / Front Stage at Top
  classroomCtx.fillStyle = "rgba(59, 130, 246, 0.15)";
  classroomCtx.strokeStyle = "rgba(59, 130, 246, 0.4)";
  classroomCtx.lineWidth = 2;
  classroomCtx.fillRect(w * 0.25, 10, w * 0.5, 24);
  classroomCtx.strokeRect(w * 0.25, 10, w * 0.5, 24);
  classroomCtx.fillStyle = "#93C5FD";
  classroomCtx.font = "11px 'Plus Jakarta Sans'";
  classroomCtx.textAlign = "center";
  classroomCtx.fillText("FRONT OF CLASSROOM / WHITEBOARD", w * 0.5, 26);

  // Render each participant track
  tracks.forEach(trk => {
    const [nx, ny, nw, nh] = trk.bbox;
    const x = nx * w;
    const y = ny * h;
    const bw = nw * w;
    const bh = nh * h;

    let color = "#10B981"; // green
    if (trk.is_drowsy) {
      color = "#EF4444"; // red
    } else if (trk.is_distracted) {
      color = "#F97316"; // orange
    } else if (trk.engagement_score < 60) {
      color = "#F59E0B"; // yellow
    }

    // Aura Glow
    classroomCtx.shadowColor = color;
    classroomCtx.shadowBlur = 10;
    classroomCtx.strokeStyle = color;
    classroomCtx.lineWidth = 2;
    classroomCtx.strokeRect(x, y, bw, bh);
    classroomCtx.shadowBlur = 0; // reset

    // Corner Accents
    const corner = 8;
    classroomCtx.lineWidth = 3;
    classroomCtx.beginPath();
    classroomCtx.moveTo(x, y + corner); classroomCtx.lineTo(x, y); classroomCtx.lineTo(x + corner, y);
    classroomCtx.moveTo(x + bw - corner, y); classroomCtx.lineTo(x + bw, y); classroomCtx.lineTo(x + bw, y + corner);
    classroomCtx.moveTo(x, y + bh - corner); classroomCtx.lineTo(x, y + bh); classroomCtx.lineTo(x + corner, y + bh);
    classroomCtx.moveTo(x + bw - corner, y + bh); classroomCtx.lineTo(x + bw, y + bh); classroomCtx.lineTo(x + bw, y + bh - corner);
    classroomCtx.stroke();

    // Name Tag Box
    classroomCtx.fillStyle = "rgba(11, 15, 25, 0.85)";
    classroomCtx.fillRect(x, y - 22, bw + 20, 20);
    classroomCtx.fillStyle = "#F3F4F6";
    classroomCtx.font = "bold 10px 'JetBrains Mono'";
    classroomCtx.textAlign = "left";
    classroomCtx.fillText(`${trk.display_name}`, x + 4, y - 8);

    // Engagement score badge
    classroomCtx.fillStyle = color;
    classroomCtx.font = "bold 9px 'JetBrains Mono'";
    classroomCtx.fillText(`${Math.round(trk.engagement_score)}%`, x + 4, y + bh + 14);

    // Drowsy / Disengaged Alert Tag
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
// Timeline Chart (Engagement & Speech Activity Over Time)
// ==============================================================================

function renderTimelineChart(timeline) {
  const w = timelineCanvas.width;
  const h = timelineCanvas.height;

  timelineCtx.fillStyle = "#080D1A";
  timelineCtx.fillRect(0, 0, w, h);

  if (timeline.length < 2) return;

  // Grid lines
  timelineCtx.strokeStyle = "rgba(255, 255, 255, 0.05)";
  timelineCtx.lineWidth = 1;
  for (let p = 0; p <= 100; p += 25) {
    const y = h - (p / 100) * (h - 20) - 10;
    timelineCtx.beginPath(); timelineCtx.moveTo(30, y); timelineCtx.lineTo(w - 10, y); timelineCtx.stroke();
    timelineCtx.fillStyle = "#6B7280";
    timelineCtx.font = "9px 'JetBrains Mono'";
    timelineCtx.fillText(`${p}%`, 5, y + 3);
  }

  // Draw 50% Threshold Dotted Line
  const yMid = h - 0.5 * (h - 20) - 10;
  timelineCtx.setLineDash([4, 4]);
  timelineCtx.strokeStyle = "rgba(239, 68, 68, 0.4)";
  timelineCtx.beginPath(); timelineCtx.moveTo(30, yMid); timelineCtx.lineTo(w - 10, yMid); timelineCtx.stroke();
  timelineCtx.setLineDash([]);

  // Draw Engagement Curve
  const xStep = (w - 50) / Math.max(1, timeline.length - 1);

  // Gradient fill under engagement line
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

  // Speech activity stroke
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
// Table & Modal Helpers
// ==============================================================================

function renderAttendanceTable(records) {
  if (!records || records.length === 0) {
    attendanceTableBody.innerHTML = `<tr><td colspan="9" class="table-empty">No student records registered yet.</td></tr>`;
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
    </tr>
  `).join("");
}

async function togglePauseResume() {
  const action = isPaused ? "resume" : "pause";
  await fetch("/api/action", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action })
  });
  fetchStatus();
}

async function togglePrivacy() {
  await fetch("/api/action", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "toggle_privacy" })
  });
  fetchStatus();
  fetchAttendance();
}

async function openAuditModal() {
  auditModal.style.display = "flex";
  auditModalContent.innerHTML = `<div class="audit-loading">Generating session pedagogical audit...</div>`;
  try {
    const res = await fetch("/api/audit");
    const data = await res.json();
    const a = data.audit;
    currentAuditMarkdown = a.markdown;

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
        ${a.strengths.map(s => `<li>${escapeHtml(s)}</li>`).join("")}
      </ul>
      <h4 style="margin-bottom: 8px; color: #F59E0B;">💡 Actionable Growth Recommendations</h4>
      <ul style="margin-left: 20px;">
        ${a.recommendations.map(r => `<li>${escapeHtml(r)}</li>`).join("")}
      </ul>
    `;
  } catch (e) {
    auditModalContent.innerHTML = `<div style="color: #EF4444;">Failed to generate audit report.</div>`;
  }
}

function copyAuditReport() {
  if (navigator.clipboard && currentAuditMarkdown) {
    navigator.clipboard.writeText(currentAuditMarkdown);
    alert("Pedagogical Audit Markdown copied to clipboard!");
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
