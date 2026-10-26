"""Pedagogical decision rules and context-aware heuristic triggers.
Encapsulates educational psychology principles to detect teaching bottlenecks and suggest real-time interventions.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any

from ..fusion.multimodal_fusion import ClassroomEngagementSnapshot
from ..audio.acoustic_classifier import AcousticSnapshot, AcousticState


class RuleTrigger(str, Enum):
    ATTENTION_DROP_PACING = "ATTENTION_DROP_PACING"
    PROLONGED_MONOLOGUE = "PROLONGED_MONOLOGUE"
    DEAD_SILENCE_HURDLE = "DEAD_SILENCE_HURDLE"
    CHATTER_SURGE = "CHATTER_SURGE"
    DROWSINESS_ALERT = "DROWSINESS_ALERT"
    INTERACTION_PEAK = "INTERACTION_PEAK"
    ROUTINE_CHECKIN = "ROUTINE_CHECKIN"


@dataclass
class TriggeredRule:
    trigger: RuleTrigger
    priority: str  # "URGENT", "ACTIONABLE", "PEDAGOGICAL_TIP"
    title: str
    suggestion: str
    rationale: str
    action_type: str


class PedagogicalRuleEngine:
    """Evaluates multimodal classroom snapshots against evidence-based pedagogical rules."""

    def __init__(
        self,
        attention_dip_threshold: float = 50.0,
        monologue_limit_sec: float = 90.0,
        silence_limit_sec: float = 20.0,
    ):
        self.attention_dip_threshold = attention_dip_threshold
        self.monologue_limit_sec = monologue_limit_sec
        self.silence_limit_sec = silence_limit_sec

    def evaluate(
        self,
        classroom_snapshot: ClassroomEngagementSnapshot,
        acoustic_snapshot: AcousticSnapshot,
    ) -> List[TriggeredRule]:
        """Runs the rule matrix over current classroom telemetry."""
        triggered: List[TriggeredRule] = []

        # Rule 1: Drowsiness Alert
        drowsy_students = [
            s_id for s_id, score in classroom_snapshot.student_scores.items() if score.is_drowsy
        ]
        if drowsy_students:
            s_list = ", ".join(drowsy_students[:3])
            triggered.append(
                TriggeredRule(
                    trigger=RuleTrigger.DROWSINESS_ALERT,
                    priority="ACTIONABLE",
                    title="Student Drowsiness / Slump Detected",
                    suggestion=f"Sustained downward head posture detected for {s_list}. Initiate a quick 60-second physical stretch or call for a show of hands.",
                    rationale="Kinesthetic micro-breaks reactivate motor cortex alertness and reset circadian afternoon slumps.",
                    action_type="STRETCH_BREAK",
                )
            )

        # Rule 2: Attention Dip during Monologue
        if (
            classroom_snapshot.average_engagement < self.attention_dip_threshold
            and classroom_snapshot.active_students_count > 0
        ):
            if acoustic_snapshot.monologue_duration_sec > 45.0:
                triggered.append(
                    TriggeredRule(
                        trigger=RuleTrigger.ATTENTION_DROP_PACING,
                        priority="URGENT",
                        title="Attention Dip During Lecture Segment",
                        suggestion="Classroom engagement has dropped below 50%. Pause the monologue and launch a quick interactive poll or pose a conceptual check-in question.",
                        rationale="Continuous passive listening without retrieval practice leads to cognitive overload after 10-15 minutes.",
                        action_type="FORMATIVE_POLL",
                    )
                )

        # Rule 3: Prolonged Monologue Warning
        if acoustic_snapshot.monologue_duration_sec >= self.monologue_limit_sec:
            triggered.append(
                TriggeredRule(
                    trigger=RuleTrigger.PROLONGED_MONOLOGUE,
                    priority="ACTIONABLE",
                    title="Extended Instructional Monologue",
                    suggestion=f"You have spoken continuously for {int(acoustic_snapshot.monologue_duration_sec)}s without student interaction. Transition to a 2-minute Think-Pair-Share exercise.",
                    rationale="Pacing variation enhances working memory retention by alternating between information delivery and peer articulation.",
                    action_type="THINK_PAIR_SHARE",
                )
            )

        # Rule 4: Dead Silence Hurdle
        if (
            acoustic_snapshot.state == AcousticState.SUSTAINED_SILENCE
            and acoustic_snapshot.silence_duration_sec >= self.silence_limit_sec
        ):
            triggered.append(
                TriggeredRule(
                    trigger=RuleTrigger.DEAD_SILENCE_HURDLE,
                    priority="ACTIONABLE",
                    title="Prolonged Class Silence Detected",
                    suggestion=f"Silence has persisted for {int(acoustic_snapshot.silence_duration_sec)}s. Break the ice by offering a scaffolding hint or rephrasing the question into a true/false format.",
                    rationale="Students often hesitate due to fear of giving an imperfect answer; scaffolding removes anxiety barriers.",
                    action_type="SCAFFOLDING_HINT",
                )
            )

        # Rule 5: Chatter Surge
        if acoustic_snapshot.state == AcousticState.CHATTER_SURGE:
            triggered.append(
                TriggeredRule(
                    trigger=RuleTrigger.CHATTER_SURGE,
                    priority="URGENT",
                    title="Acoustic Chatter Surge",
                    suggestion="Cross-talk and noise levels have surged. Ring an auditory attention chime, count down from 3, or re-clarify the current task instructions.",
                    rationale="Immediate non-confrontational cueing resets classroom baseline noise before learning task drift occurs.",
                    action_type="ATTENTION_CUE",
                )
            )

        # Rule 6: Interaction Peak Reinforcement
        if (
            classroom_snapshot.average_engagement >= 75.0
            and acoustic_snapshot.state in (AcousticState.STUDENT_DISCUSSION, AcousticState.BALANCED_ENGAGEMENT)
        ):
            triggered.append(
                TriggeredRule(
                    trigger=RuleTrigger.INTERACTION_PEAK,
                    priority="PEDAGOGICAL_TIP",
                    title="High Collaborative Momentum",
                    suggestion="Students are actively debating and highly focused. Capture key student contributions on the whiteboard to validate peer learning.",
                    rationale="Visible validation of student contributions cements conceptual mastery and encourages broader classroom participation.",
                    action_type="WHITEBOARD_SYNTHESIS",
                )
            )

        return triggered
