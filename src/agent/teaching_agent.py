"""Autonomous AI Teaching Decision-Support Agent.
Monitors classroom state, filters pedagogical recommendations using cooldowns,
and generates structured post-session pedagogical audits and action plans.
"""
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import time

from .decision_rules import PedagogicalRuleEngine, TriggeredRule, RuleTrigger
from ..fusion.multimodal_fusion import ClassroomEngagementSnapshot
from ..audio.acoustic_classifier import AcousticSnapshot
from ..attendance.attendance_manager import AttendanceManager


@dataclass
class TeachingSuggestion:
    suggestion_id: str
    timestamp: float
    trigger: str
    priority: str
    title: str
    suggestion: str
    rationale: str
    action_type: str
    acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SessionPedagogicalAudit:
    session_id: str
    session_duration_minutes: float
    average_engagement_score: float
    engagement_grade: str
    attendance_rate_percent: float
    monologue_percentage: float
    discussion_percentage: float
    silence_percentage: float
    total_suggestions_issued: int
    key_strengths: List[str]
    growth_recommendations: List[str]

    def to_markdown(self) -> str:
        md = [
            f"# 🎓 Classroom Session Pedagogical Audit Report",
            f"**Session ID:** `{self.session_id}` | **Duration:** {self.session_duration_minutes:.1f} mins | **Overall Grade:** **{self.engagement_grade}** ({self.average_engagement_score:.1f}%)\n",
            "## 📊 Executive Engagement & Attendance Summary",
            f"- **Classroom Average Engagement:** `{self.average_engagement_score:.1f}%`",
            f"- **Attendance Compliance Rate:** `{self.attendance_rate_percent:.1f}%`",
            f"- **Instructional Monologue Ratio:** `{self.monologue_percentage:.1f}%` of session",
            f"- **Collaborative Discussion Ratio:** `{self.discussion_percentage:.1f}%` of session",
            f"- **Classroom Silence Ratio:** `{self.silence_percentage:.1f}%` of session",
            f"- **Real-time Pedagogical Cues Generated:** `{self.total_suggestions_issued}`",
            "\n## 🌟 Identified Instructional Strengths",
        ]
        for s in self.key_strengths:
            md.append(f"- ✅ {s}")

        md.append("\n## 💡 Actionable Growth Recommendations")
        for r in self.growth_recommendations:
            md.append(f"- 📌 {r}")

        md.append("\n---\n*Report generated offline by Multimodal Attendance & Engagement Agent.*")
        return "\n".join(md)


class TeachingAgent:
    """Classroom decision-support agent providing real-time assistive guidance and post-session analysis."""

    def __init__(
        self,
        alert_cooldown_sec: float = 20.0,
        enable_suggestions: bool = True,
        rule_engine: Optional[PedagogicalRuleEngine] = None,
    ):
        self.alert_cooldown_sec = alert_cooldown_sec
        self.enable_suggestions = enable_suggestions
        self.rules = rule_engine or PedagogicalRuleEngine()

        self.suggestion_history: List[TeachingSuggestion] = []
        self._last_trigger_times: Dict[str, float] = {}
        self._next_id: int = 1

    def evaluate_and_advise(
        self,
        classroom_snapshot: ClassroomEngagementSnapshot,
        acoustic_snapshot: AcousticSnapshot,
    ) -> List[TeachingSuggestion]:
        """Evaluates classroom telemetry and produces fresh actionable pedagogical recommendations."""
        if not self.enable_suggestions:
            return []

        triggered_rules = self.rules.evaluate(classroom_snapshot, acoustic_snapshot)
        now = classroom_snapshot.timestamp
        fresh_suggestions: List[TeachingSuggestion] = []

        for r in triggered_rules:
            key = r.trigger.value
            last_t = self._last_trigger_times.get(key, -999.0)

            # Enforce cooldown per trigger type to avoid cognitive overwhelm
            if (now - last_t) >= self.alert_cooldown_sec:
                self._last_trigger_times[key] = now
                s = TeachingSuggestion(
                    suggestion_id=f"SUGG-{self._next_id:04d}",
                    timestamp=round(now, 1),
                    trigger=r.trigger.value,
                    priority=r.priority,
                    title=r.title,
                    suggestion=r.suggestion,
                    rationale=r.rationale,
                    action_type=r.action_type,
                )
                self._next_id += 1
                self.suggestion_history.append(s)
                fresh_suggestions.append(s)

        return fresh_suggestions

    def get_recent_suggestions(self, limit: int = 10) -> List[TeachingSuggestion]:
        """Returns the most recent suggestions ordered newest first."""
        return list(reversed(self.suggestion_history[-limit:]))

    def generate_post_session_audit(
        self,
        session_id: str,
        timeline_series: List[Dict[str, Any]],
        attendance_manager: AttendanceManager,
    ) -> SessionPedagogicalAudit:
        """Synthesizes a holistic post-session pedagogical review from timeline telemetry."""
        if not timeline_series:
            return SessionPedagogicalAudit(
                session_id=session_id,
                session_duration_minutes=0.0,
                average_engagement_score=0.0,
                engagement_grade="N/A",
                attendance_rate_percent=0.0,
                monologue_percentage=0.0,
                discussion_percentage=0.0,
                silence_percentage=0.0,
                total_suggestions_issued=len(self.suggestion_history),
                key_strengths=["No session telemetry recorded."],
                growth_recommendations=["Ensure camera and microphone are running."],
            )

        start_t = timeline_series[0]["timestamp"]
        end_t = timeline_series[-1]["timestamp"]
        duration_min = max(0.1, (end_t - start_t) / 60.0)

        # Averages
        avg_eng = sum(e["average_engagement"] for e in timeline_series) / len(timeline_series)

        # Acoustic breakdowns
        n = len(timeline_series)
        monologue_count = sum(1 for e in timeline_series if e.get("acoustic_state") == "TEACHER_MONOLOGUE")
        disc_count = sum(1 for e in timeline_series if e.get("acoustic_state") == "STUDENT_DISCUSSION")
        silence_count = sum(1 for e in timeline_series if e.get("acoustic_state") == "SUSTAINED_SILENCE")

        monologue_pct = (monologue_count / n) * 100.0
        disc_pct = (disc_count / n) * 100.0
        silence_pct = (silence_count / n) * 100.0

        # Grade assignment
        if avg_eng >= 80.0:
            grade = "A"
        elif avg_eng >= 70.0:
            grade = "B+"
        elif avg_eng >= 60.0:
            grade = "B"
        elif avg_eng >= 50.0:
            grade = "C"
        else:
            grade = "D"

        # Strengths & Recommendations
        strengths = []
        recommendations = []

        if avg_eng >= 70.0:
            strengths.append(f"Maintained strong student attentiveness ({avg_eng:.1f}% average engagement).")
        if disc_pct >= 20.0:
            strengths.append(f"Facilitated rich peer participation ({disc_pct:.1f}% of session in active dialogue).")
        else:
            recommendations.append("Incorporate more student-led discussion periods to boost verbal engagement.")

        att_summary = attendance_manager.get_summary()
        att_rate = att_summary.get("attendance_rate_percent", 0.0)
        if att_rate >= 85.0:
            strengths.append(f"Excellent sustained attendance retention ({att_rate:.1f}%).")
        else:
            recommendations.append(f"Attendance rate was {att_rate:.1f}%; follow up with absent or late attendees.")

        if monologue_pct > 60.0:
            recommendations.append("Teacher monologue exceeded 60% of class time; break explanations into 8-10 minute chunks followed by rapid retrieval checks.")
        if silence_pct > 25.0:
            recommendations.append("High silence duration detected; provide structured thinking prompts or worksheet exercises during quiet intervals.")

        if not strengths:
            strengths.append("Established consistent session pacing.")
        if not recommendations:
            recommendations.append("Continue current pedagogical methodology while introducing spontaneous polling.")

        return SessionPedagogicalAudit(
            session_id=session_id,
            session_duration_minutes=round(duration_min, 1),
            average_engagement_score=round(avg_eng, 1),
            engagement_grade=grade,
            attendance_rate_percent=round(att_rate, 1),
            monologue_percentage=round(monologue_pct, 1),
            discussion_percentage=round(disc_pct, 1),
            silence_percentage=round(silence_pct, 1),
            total_suggestions_issued=len(self.suggestion_history),
            key_strengths=strengths,
            growth_recommendations=recommendations,
        )

    def build_llm_prompt(self, snapshot: ClassroomEngagementSnapshot, acoustic: AcousticSnapshot) -> str:
        """Constructs an LLM prompt for external inference when connected to an AI model."""
        return (
            "You are an expert pedagogical classroom AI coach. Analyze the current live classroom state:\n"
            f"- Average Student Engagement: {snapshot.average_engagement}%\n"
            f"- High Engagement Count: {snapshot.high_engagement_count}/{snapshot.active_students_count}\n"
            f"- Low / Disengaged Count: {snapshot.low_engagement_count + snapshot.disengaged_count}\n"
            f"- Classroom Acoustic Dynamic: {acoustic.state.value}\n"
            f"- Continuous Monologue Duration: {acoustic.monologue_duration_sec:.1f}s\n"
            "Provide 1 immediate, non-disruptive, 1-sentence teaching recommendation for the educator."
        )
