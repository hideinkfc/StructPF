"""PF exercise generator — Phase 1b.

Three input versions, one system prompt:
  V1 (Blind):           grade + topic + theme — no misconception data
  V2 (Eedi-grounded):   grade + topic + theme + real Eedi misconceptions
  V3 (LLM-inferred):    two-step — LLM infers misconceptions, then generates
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from src.utils.llm_client import LLMClient, LLMResponse

logger = logging.getLogger(__name__)

PROMPT_DIR = Path(__file__).resolve().parent / "prompts"


@dataclass
class PFExercise:
    """A generated PF exercise with parsed sections."""

    version: str  # V1, V2, V3
    topic: str
    grade: str
    raw_output: str
    sections: dict[str, str] = field(default_factory=dict)
    n_misconceptions: int = 0
    metadata: dict = field(default_factory=dict)

    def is_valid(self) -> bool:
        """Check that all 4 required sections are present."""
        required = {"TOPIC", "NARRATIVE", "TASK", "CONSOLIDATION NOTE"}
        found = set(self.sections.keys())
        return required.issubset(found)


class PFGenerator:
    """Generates PF exercises using an LLM, with three input versions."""

    SECTION_NAMES = [
        "TOPIC",
        "NARRATIVE",
        "TASK",
        "CONSOLIDATION NOTE",
    ]

    def __init__(self, client: LLMClient):
        self._client = client
        self._prompts = self._load_prompts()

    def _load_prompts(self) -> dict:
        path = PROMPT_DIR / "pf_generation.yaml"
        with open(path) as f:
            return yaml.safe_load(f)

    # ── V1: Blind (grade + topic only) ───────────────────────────────────

    def generate_v1(
        self,
        grade: str,
        topic: str,
        max_tokens: int | None = None,
        temperature: float = 0.7,
        variation_hint: str = "",
    ) -> PFExercise:
        system = self._prompts["SYSTEM_PROMPT"]
        user = self._prompts["USER_V1"].format(
            grade=grade,
            topic=topic,
            variation_hint=variation_hint,
        )
        response = self._chat(system, user, max_tokens=max_tokens, temperature=temperature)
        sections = self._parse_sections(response.text)
        return PFExercise(
            version="V1",
            topic=topic,
            grade=grade,
            raw_output=response.text,
            sections=sections,
            n_misconceptions=0,
            metadata={"usage": response.usage},
        )

    # ── V2: Eedi-grounded (real misconception data) ──────────────────────

    def generate_v2(
        self,
        grade: str,
        topic: str,
        misconceptions: list[str] | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.7,
        variation_hint: str = "",
    ) -> PFExercise:
        if misconceptions is None:
            misconceptions = self._prompts.get("EEDI_MISCONCEPTIONS", [])

        misc_text = "\n".join(f"  - {m}" for m in misconceptions)
        system = self._prompts["SYSTEM_PROMPT"]
        user = self._prompts["USER_V2"].format(
            grade=grade,
            topic=topic,
            misconceptions=misc_text,
            variation_hint=variation_hint,
        )
        response = self._chat(system, user, max_tokens=max_tokens, temperature=temperature)
        sections = self._parse_sections(response.text)
        return PFExercise(
            version="V2",
            topic=topic,
            grade=grade,
            raw_output=response.text,
            sections=sections,
            n_misconceptions=len(misconceptions),
            metadata={"usage": response.usage, "misconceptions": misconceptions},
        )

    # ── V3: LLM-inferred (two-step) ──────────────────────────────────────

    def generate_v3(
        self,
        grade: str,
        topic: str,
        max_tokens: int | None = None,
        temperature: float = 0.7,
        misconception_max_tokens: int = 512,
        variation_hint: str = "",
    ) -> PFExercise:
        # Step 1: infer misconceptions
        step1 = self._prompts["USER_V3_STEP1"].format(grade=grade, topic=topic)
        resp_step1 = self._chat(
            self._prompts["SYSTEM_PROMPT"],
            step1,
            max_tokens=misconception_max_tokens,
            temperature=temperature,
        )
        inferred = self._parse_misconception_list(resp_step1.text)

        # Step 2: generate PF exercise
        misc_text = "\n".join(f"  - {m}" for m in inferred) if inferred else "(none inferred)"
        step2 = self._prompts["USER_V3_STEP2"].format(
            grade=grade,
            topic=topic,
            misconceptions=misc_text,
            variation_hint=variation_hint,
        )
        resp_step2 = self._chat(
            self._prompts["SYSTEM_PROMPT"], step2, max_tokens=max_tokens, temperature=temperature
        )
        sections = self._parse_sections(resp_step2.text)

        return PFExercise(
            version="V3",
            topic=topic,
            grade=grade,
            raw_output=resp_step2.text,
            sections=sections,
            n_misconceptions=len(inferred),
            metadata={
                "usage_step1": resp_step1.usage,
                "usage_step2": resp_step2.usage,
                "inferred_misconceptions": inferred,
            },
        )

    # ── Helpers ──────────────────────────────────────────────────────────

    def _chat(
        self,
        system: str,
        user: str,
        max_tokens: int | None = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        return self._client.generate(
            messages,
            max_tokens=max_tokens or 3072,
            temperature=temperature,
        )

    def _parse_sections(self, text: str) -> dict[str, str]:
        """Parse generated output into named sections. Handles multiple formats:
        'TOPIC:', '## TOPIC', '**TOPIC:**', '1. TOPIC', '## Step 1: TOPIC', etc.
        """
        sections = {}
        # Flexible pattern: optional prefix (##, 1., Step N:, *, **, etc.) + section name + optional colon/dash
        section_prefix = (
            r"(?:(?:\#{1,3}\s*)?(?:Step\s+[\d]+[:\)]\s*|[\d]+[\.\)]\s*)"
            r"|\#{1,3}\s+|[-•*]\s+|\*\*)?"
        )
        patterns = {
            name: re.compile(
                rf"(?:^|\n)\s*{section_prefix}\s*{re.escape(name)}\s*(?::|—|-|–)?\s*(?:\*\*)?\s*\n?",
                re.MULTILINE | re.IGNORECASE,
            )
            for name in self.SECTION_NAMES
        }

        occurrences = []
        for name, pat in patterns.items():
            for match in pat.finditer(text):
                occurrences.append((match.start(), match.end(), name))

        occurrences.sort(key=lambda x: x[0])

        for i, (start, end, name) in enumerate(occurrences):
            if i + 1 < len(occurrences):
                next_start = occurrences[i + 1][0]
                content = text[end:next_start].strip()
            else:
                content = text[end:].strip()
            if name not in sections and content:
                sections[name] = content

        return {k: v.strip() for k, v in sections.items() if v.strip()}

    def _parse_misconception_list(self, text: str) -> list[str]:
        """Parse a flat or bulleted list of misconceptions."""
        lines = text.strip().split("\n")
        misconceptions = []
        for line in lines:
            line = line.strip()
            # Remove bullet markers and numbering
            line = re.sub(r"^[\d]+[\.\)]\s*", "", line)
            line = re.sub(r"^[-•*]\s*", "", line)
            line = line.strip().strip('"').strip("'")
            if line and len(line) > 10:  # skip empty or too-short lines
                misconceptions.append(line)
        return misconceptions[:8]  # cap at 8
