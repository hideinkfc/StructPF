"""Student profile definitions based on Knowledge Components (KCs).

A profile assigns each KC a mastery level:
  MASTERED (1.0):   student reliably uses the correct procedure.
  PARTIAL  (0.5):   student uses the correct rule about half the time;
                    when confused they fall back to a known error.
  UNMASTERED (0.0): student consistently applies a specific buggy procedure.

Each UNMASTERED KC carries a concrete error-behavior description drawn
from real Eedi misconception explanations so the LLM can faithfully
reproduce the systematic mistake.
"""

from __future__ import annotations

import json
import random
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

# ── Mastery levels ──────────────────────────────────────────────────

MASTERED = 1.0
PARTIAL = 0.5
UNMASTERED = 0.0

LEVEL_LABELS = {MASTERED: "mastered", PARTIAL: "partial", UNMASTERED: "not mastered"}


# ── Error behaviour ─────────────────────────────────────────────────


@dataclass
class ErrorBehavior:
    """A concrete, systematic error a student makes for a given KC."""

    description: str  # teacher-facing: "Sign-only-applies-to-first-term"
    rule: str  # student-facing procedure: "When you see a minus..."
    example: str  # worked example of the buggy procedure
    pct_students: int = 0  # prevalence in Eedi data (0 if LLM-generated)
    source: str = "llm"  # "eedi" | "llm"


# ── Knowledge component ─────────────────────────────────────────────


@dataclass
class KnowledgeComponent:
    """A skill a student can master, partially master, or fail."""

    skill_id: str
    description: str
    topic: str
    subject: str
    error_behaviors: list[ErrorBehavior] = field(default_factory=list)

    def random_error(self) -> Optional[ErrorBehavior]:
        """Pick a random error behavior for this KC."""
        if not self.error_behaviors:
            return None
        return random.choice(self.error_behaviors)


# ── Student profile ─────────────────────────────────────────────────


@dataclass
class StudentProfile:
    """A simulated student defined by per-KC mastery levels."""

    profile_id: str
    ability: float  # 0.0–1.0 overall ability
    kc_mastery: dict[str, float] = field(default_factory=dict)  # skill_id → mastery
    active_errors: dict[str, ErrorBehavior] = field(default_factory=dict)  # skill_id → error

    # ── legacy compat ────────────────────────────────────────────────
    ability_level: str = ""
    knowledge_components: dict[str, float] = field(default_factory=dict)
    misconceptions: list[str] = field(default_factory=list)

    @classmethod
    def from_config(cls, config: dict) -> "StudentProfile":
        """Create a profile from a YAML config (legacy)."""
        return cls(
            profile_id=config["id"],
            ability=0.5,
            ability_level=config["ability_level"],
            knowledge_components=config.get("kcs", {}),
            misconceptions=config.get("misconceptions", []),
        )

    def mastery_of(self, skill_id: str) -> float:
        """Return mastery level for a skill (default: mastered if unknown)."""
        return self.kc_mastery.get(skill_id, MASTERED)

    def is_unmastered(self, skill_id: str) -> bool:
        return self.mastery_of(skill_id) == UNMASTERED

    def error_for(self, skill_id: str) -> Optional[ErrorBehavior]:
        return self.active_errors.get(skill_id)

    def to_prompt_block(self, kc_map: dict[str, KnowledgeComponent]) -> str:
        """Render this profile as a student-facing prompt block.

        Only lists KCs where mastery is not full — a fully-mastered
        student produces a short, clean profile.
        """
        weak = [(sid, lvl) for sid, lvl in self.kc_mastery.items() if lvl < MASTERED]
        if not weak:
            return "You have mastered all relevant skills for this topic."

        lines = []
        for sid, lvl in sorted(weak, key=lambda x: x[1]):
            kc = kc_map.get(sid)
            desc = kc.description if kc else sid
            label = LEVEL_LABELS[lvl]

            if lvl == UNMASTERED:
                err = self.active_errors.get(sid)
                if err:
                    lines.append(f"- {label.upper()}: {desc}")
                    lines.append(f"  What you do instead: {err.rule}")
                else:
                    lines.append(f"- {label.upper()}: {desc}")
            elif lvl == PARTIAL:
                lines.append(f"- PARTIAL: {desc}")
                lines.append("  You can sometimes do this correctly, but you are inconsistent.")

        return "\n".join(lines) if lines else "You have mastered all relevant skills."


# ── Skill bank (built from scraped Eedi data) ────────────────────────


class SkillBank:
    """Collection of KCs with their error behaviors, loaded from Eedi data."""

    def __init__(self):
        self.kcs: dict[str, KnowledgeComponent] = {}
        self.by_topic: dict[str, list[str]] = defaultdict(list)  # topic → skill_ids

    @classmethod
    def from_scraped_eedi(
        cls, aggregate_path: str = "data/eedi_scraped/_aggregated.json"
    ) -> "SkillBank":
        """Build a skill bank from scraped Eedi quiz data."""
        with open(aggregate_path) as f:
            quizzes = json.load(f)

        bank = cls()
        seen = {}

        for quiz in quizzes:
            topic = quiz.get("topic_csv", quiz.get("topic", "Unknown"))
            subject = quiz.get("subject", "Unknown")

            for skill_desc in quiz.get("skills", []):
                sid = _skill_to_id(skill_desc)

                if sid not in seen:
                    seen[sid] = {
                        "description": skill_desc,
                        "topic": topic,
                        "subject": subject,
                    }
                # Index topic → skill_ids
                if sid not in bank.by_topic[topic]:
                    bank.by_topic[topic].append(sid)

            # Attach misconception explanations as error behaviors
            for q in quiz.get("questions", []):
                for label, ans in q.get("answers", {}).items():
                    if ans.get("is_correct"):
                        continue
                    if ans.get("heading") != "Common misconception":
                        continue
                    explanation = ans.get("explanation", "")
                    pct = ans.get("pct_students", 0)

                    # Heuristic: assign this misconception to the most relevant skill
                    for skill_desc in quiz.get("skills", []):
                        sid = _skill_to_id(skill_desc)
                        if sid not in bank.kcs:
                            bank.kcs[sid] = KnowledgeComponent(
                                skill_id=sid,
                                description=skill_desc,
                                topic=topic,
                                subject=subject,
                            )

                        # Deduplicate by rule text prefix
                        short = explanation[:60]
                        existing = [
                            e
                            for e in bank.kcs[sid].error_behaviors
                            if e.rule.startswith(short[:30])
                        ]
                        if not existing:
                            bank.kcs[sid].error_behaviors.append(
                                ErrorBehavior(
                                    description=f"Distractor {label}",
                                    rule=_invert_explanation_to_error_rule(explanation),
                                    example="",
                                    pct_students=pct,
                                    source="eedi",
                                )
                            )

        # Fill in any skill seen but not yet stored
        for sid, info in seen.items():
            if sid not in bank.kcs:
                bank.kcs[sid] = KnowledgeComponent(
                    skill_id=sid,
                    description=info["description"],
                    topic=info["topic"],
                    subject=info["subject"],
                )

        return bank

    def get(self, skill_id: str) -> Optional[KnowledgeComponent]:
        return self.kcs.get(skill_id)

    def skills_for_topic(self, topic: str) -> list[KnowledgeComponent]:
        return [self.kcs[sid] for sid in self.by_topic.get(topic, []) if sid in self.kcs]

    def all_skill_ids(self) -> list[str]:
        return list(self.kcs.keys())

    def to_dict(self) -> dict:
        return {
            sid: {
                "description": kc.description,
                "topic": kc.topic,
                "subject": kc.subject,
                "n_errors": len(kc.error_behaviors),
                "errors": [
                    {
                        "description": e.description,
                        "rule": e.rule,
                        "pct_students": e.pct_students,
                        "source": e.source,
                    }
                    for e in kc.error_behaviors
                ],
            }
            for sid, kc in self.kcs.items()
        }


# ── Profile generator ───────────────────────────────────────────────


class ProfileGenerator:
    """Generates student profiles by sampling mastery levels over a skill bank."""

    def __init__(self, skill_bank: SkillBank, seed: int = 42):
        self.bank = skill_bank
        self.rng = random.Random(seed)

    def generate(
        self,
        profile_id: str,
        ability: Optional[float] = None,
        topic: Optional[str] = None,
        skill_ids: Optional[list[str]] = None,
    ) -> StudentProfile:
        """Generate a profile.

        Args:
            profile_id: unique label, e.g. 'student_01_low'
            ability: overall ability 0.0–1.0. If None, sampled from U(0.2, 0.95).
            topic: if given, only sample skills for this topic.
            skill_ids: if given, only use these specific skills.
        """
        if ability is None:
            ability = self.rng.uniform(0.2, 0.95)

        # Determine which skills to sample
        if skill_ids:
            kc_list = [self.bank.get(sid) for sid in skill_ids if self.bank.get(sid)]
        elif topic:
            kc_list = self.bank.skills_for_topic(topic)
        else:
            kc_list = list(self.bank.kcs.values())

        # Assign mastery level per KC
        kc_mastery: dict[str, float] = {}
        active_errors: dict[str, ErrorBehavior] = {}

        for kc in kc_list:
            if kc is None:
                continue
            # Ability-correlated mastery: high-ability students master more
            p_master = min(ability + self.rng.uniform(-0.1, 0.15), 1.0)
            roll = self.rng.random()

            if roll < p_master:
                kc_mastery[kc.skill_id] = MASTERED
            elif roll < p_master + (1.0 - p_master) * 0.6:
                kc_mastery[kc.skill_id] = PARTIAL
            else:
                kc_mastery[kc.skill_id] = UNMASTERED
                err = kc.random_error()
                if err:
                    active_errors[kc.skill_id] = err

        # Build legacy-compatible fields
        ability_label = "high" if ability > 0.7 else ("low" if ability < 0.4 else "medium")

        return StudentProfile(
            profile_id=profile_id,
            ability=ability,
            ability_level=ability_label,
            kc_mastery=kc_mastery,
            active_errors=active_errors,
            knowledge_components=kc_mastery,
            misconceptions=[e.rule for e in active_errors.values()],
        )

    def generate_batch(
        self,
        n: int,
        topic: Optional[str] = None,
        skill_ids: Optional[list[str]] = None,
        id_prefix: str = "student",
    ) -> list[StudentProfile]:
        """Generate n diverse profiles, spread evenly across ability levels."""
        profiles = []
        for i in range(n):
            # Spread abilities evenly
            ability = 0.2 + (i / max(n - 1, 1)) * 0.75
            pid = f"{id_prefix}_{i:02d}"
            profiles.append(
                self.generate(profile_id=pid, ability=ability, topic=topic, skill_ids=skill_ids)
            )
        return profiles


# ── Helpers ──────────────────────────────────────────────────────────


def _skill_to_id(desc: str) -> str:
    """Hash a skill description into a stable ID."""
    return desc.lower().strip().replace(" ", "_")[:80]


def _invert_explanation_to_error_rule(explanation: str) -> str:
    """Convert a teacher-facing explanation into a student-facing error rule.

    Strips prefixes, percentage tails, and reformats into a
    procedural 'you believe / you do' pattern.
    """

    text = explanation.replace("Common misconception", "").replace("Eedi explanation", "").strip()
    # Strip trailing "% of students on Eedi chose X" tails
    text = re.sub(r"\d+% of students on Eedi chose\s+[A-D]\.?", "", text).strip()
    # Strip stray "5.5% of students on Eedi cho" etc
    text = re.sub(r"\d+\.?\d*% of students.*$", "", text).strip()
    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text)

    # Truncate to first two sentences
    sentences = [s.strip() for s in text.split(". ") if s.strip()]
    core = ". ".join(sentences[:2]).rstrip(".").strip()
    if not core:
        return "No specific error rule available."

    # Convert teacher tone → student rule
    core = core.replace("The student may have", "You")
    core = core.replace("I think you have", "You")
    core = core.replace("I think you", "You")
    core = core.replace("Not quite.", "")
    core = core.replace("Almost.", "")
    core = core.replace("Be careful when", "When you")
    core = core.replace("Remember we are", "When you see")
    core = core.replace("It looks like you", "You")
    core = core.replace("Have you", "Have you")
    core = core.replace("you can", "you can")

    return core.strip()
