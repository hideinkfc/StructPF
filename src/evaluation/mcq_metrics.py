"""MCQ distractor evaluation metrics.

Family 1 (reference-based, computed):
  - Proportional Match (normalized + exact)
  - Text similarity (ROUGE-L, edit distance)
  - Embedding similarity

Family 2 (misconception-grounded, hybrid LLM+computed):
  - Misconception Recovery @k
  - Self-label fidelity
  - Intra-question diversity
"""

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from src.generation.misconception_bank import MisconceptionBank
from src.utils.llm_client import LLMClient

# ── LaTeX / math normalization ───────────────────────────────────────────────

# LaTeX command → unicode/text mapping. Applied with word-boundary awareness
# (a command is only matched when not followed by another letter) so that, e.g.,
# `\left` does not corrupt `\leftarrow`.
_LATEX_COMMANDS = {
    # arithmetic / relational operators
    r"\times": "×",
    r"\cdot": "·",
    r"\div": "÷",
    r"\pm": "±",
    r"\mp": "∓",
    r"\sqrt": "√",
    r"\leq": "≤",
    r"\le": "≤",
    r"\geq": "≥",
    r"\ge": "≥",
    r"\neq": "≠",
    r"\approx": "≈",
    r"\equiv": "≡",
    r"\propto": "∝",
    r"\infty": "∞",
    # set notation
    r"\cup": "∪",
    r"\cap": "∩",
    r"\in": "∈",
    r"\subset": "⊂",
    r"\emptyset": "∅",
    # arrows (longer names first so prefixes don't shadow them)
    r"\Leftrightarrow": "↔",
    r"\leftrightarrow": "↔",
    r"\Rightarrow": "→",
    r"\rightarrow": "→",
    r"\Leftarrow": "←",
    r"\leftarrow": "←",
    r"\to": "→",
    # degrees / dots
    r"\degree": "°",
    r"\circ": "°",
    r"\ldots": "…",
    r"\cdots": "…",
    r"\dots": "…",
    # greek letters
    r"\pi": "π",
    r"\theta": "θ",
    r"\omega": "ω",
    r"\Delta": "Δ",
    r"\delta": "δ",
    r"\alpha": "α",
    r"\beta": "β",
    # formatting / spacing commands (dropped)
    r"\mathrm": "",
    r"\mathbf": "",
    r"\mathit": "",
    r"\operatorname": "",
    r"\text": "",
    r"\left": "",
    r"\right": "",
    r"\quad": " ",
    r"\qquad": "  ",
    r"\space": " ",
    r"\,": " ",
    r"\:": " ",
    r"\;": " ",
    r"\!": "",
}


def normalize_expression(text: str | None) -> str:
    """Normalize a math expression for comparison.

    Strips LaTeX formatting, normalizes math symbols, and standardizes
    whitespace so that semantically identical answers match.
    """
    if text is None:
        return ""

    result = str(text).strip()

    # Strip LaTeX delimiters: \(...\), \[...\], $$...$$, etc.
    result = re.sub(r"\\\(|\\\)|\\\[|\\\]|\$\$|\$", "", result)

    # Unescape literal braces \{ \} → { } (grouping braces are removed later)
    result = result.replace(r"\{", "{").replace(r"\}", "}")

    # Remove \begin{...} and \end{...} environments
    result = re.sub(r"\\begin\{[^}]*\}", "", result)
    result = re.sub(r"\\end\{[^}]*\}", "", result)

    # Convert fractions: \frac{a}{b} → a/b (run repeatedly for nested fractions)
    frac_pattern = re.compile(r"\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}")
    while frac_pattern.search(result):
        result = frac_pattern.sub(r"(\1)/(\2)", result)

    # Replace known LaTeX commands (longest first; a letter-command only matches
    # when not followed by another letter, so `\le` never breaks `\leq`).
    for cmd in sorted(_LATEX_COMMANDS, key=len, reverse=True):
        replacement = _LATEX_COMMANDS[cmd]
        pattern = re.escape(cmd)
        if cmd[-1].isalpha():
            pattern += r"(?![a-zA-Z])"
        result = re.sub(pattern, replacement, result)

    # Normalize \\ to space (LaTeX line breaks in arrays)
    result = result.replace("\\\\", " ")

    # Drop any remaining unknown control sequences, keeping their name so distinct
    # placeholders (\bigstar, \triangle, …) stay distinct rather than colliding.
    result = re.sub(r"\\([a-zA-Z]+)", r"\1", result)

    # Remove curly braces used for LaTeX grouping
    result = re.sub(r"[{}]", "", result)

    # Normalize superscripts: ^{...} → ^... then remove ^
    # e.g., x^{3} → x3, cm^{3} → cm3
    result = re.sub(r"\^\{[^}]*\}", lambda m: m.group()[1:-1], result)
    result = result.replace("^", "")

    # Collapse multiple whitespace
    result = re.sub(r"\s+", " ", result)

    # Convert unambiguous ASCII multiplication without changing variables such as x=0.
    result = re.sub(r"(?<=[0-9)])\s*[xX]\s*(?=[0-9(])", " × ", result)
    result = re.sub(r"(?<=[0-9)])\s*\*\s*(?=[0-9(])", " × ", result)

    # Normalize spacing around operator chars: ×9 ↔ × 9, etc.
    # (LaTeX \times→× preserves source spacing inconsistently)
    result = re.sub(r"\s*([×÷])\s*", r" \1 ", result)
    result = re.sub(r"\s*=\s*", "=", result)

    # Strip
    result = result.strip()

    return result


# ── Per-question metrics ─────────────────────────────────────────────────────


@dataclass
class PFRubricScores:
    """Rahimi et al. (2025) PF rubric adapted for distractor evaluation (Family 3).

    Each dimension scored 1 (Low) – 3 (High). Final = sum across dimensions (5–15).
    """

    activation_prior_knowledge: float = 0.0  # APK
    sweet_spot_calibration: float = 0.0  # SSC
    affective_engagement: float = 0.0  # AE
    multiple_representations: float = 0.0  # MR
    open_endedness: float = 0.0  # OE
    final_score: float = 0.0  # sum 5–15

    def to_dict(self) -> dict[str, float]:
        return {
            "APK": self.activation_prior_knowledge,
            "SSC": self.sweet_spot_calibration,
            "AE": self.affective_engagement,
            "MR": self.multiple_representations,
            "OE": self.open_endedness,
            "Final": self.final_score,
        }


@dataclass
class QuestionMetrics:
    """Metrics for a single question."""

    question_id: int
    n_generated: int = 0
    n_human: int = 0

    # Family 1
    pm: float = 0.0  # Proportional Match (normalized)
    text_similarity: float = 0.0  # Mean ROUGE-L across distractor pairs
    embed_similarity: float = 0.0  # Mean cosine sim across distractor pairs

    # Family 2
    self_label_fidelity: float = 0.0  # Agreement between generator's self-label
    # and independent classifier
    diversity: float = 0.0  # Mean pairwise distance across generated distractors
    validity: float = 0.0  # Fraction of distractors that are wrong but on-pathway

    # Family 3 — Rahimi et al. (2025) PF rubric
    pf_rubric: PFRubricScores | None = None


@dataclass
class ConditionResults:
    """Aggregated metrics for one experimental condition."""

    condition_name: str
    n_questions: int = 0
    metrics: list[QuestionMetrics] = field(default_factory=list)

    @property
    def avg_pm(self) -> float:
        return np.mean([m.pm for m in self.metrics]) if self.metrics else 0.0

    @property
    def avg_text_similarity(self) -> float:
        return np.mean([m.text_similarity for m in self.metrics]) if self.metrics else 0.0

    @property
    def avg_embed_similarity(self) -> float:
        return np.mean([m.embed_similarity for m in self.metrics]) if self.metrics else 0.0

    @property
    def avg_diversity(self) -> float:
        return np.mean([m.diversity for m in self.metrics]) if self.metrics else 0.0

    @property
    def avg_validity(self) -> float:
        return np.mean([m.validity for m in self.metrics]) if self.metrics else 0.0

    @property
    def std_pm(self) -> float:
        return np.std([m.pm for m in self.metrics]) if self.metrics else 0.0

    @property
    def std_validity(self) -> float:
        return np.std([m.validity for m in self.metrics]) if self.metrics else 0.0

    @property
    def std_diversity(self) -> float:
        return np.std([m.diversity for m in self.metrics]) if self.metrics else 0.0

    # Family 3 — PF rubric aggregates
    @property
    def avg_pf_final(self) -> float:
        return (
            np.mean([m.pf_rubric.final_score for m in self.metrics if m.pf_rubric])
            if self.metrics
            else 0.0
        )

    @property
    def std_pf_final(self) -> float:
        return (
            np.std([m.pf_rubric.final_score for m in self.metrics if m.pf_rubric])
            if self.metrics
            else 0.0
        )

    def summary(self) -> dict[str, Any]:
        s = {
            "condition": self.condition_name,
            "n_questions": self.n_questions,
            "PM": round(self.avg_pm, 4),
            "PM_std": round(self.std_pm, 4),
            "TextSim": round(self.avg_text_similarity, 4),
            "EmbedSim": round(self.avg_embed_similarity, 4),
            "Validity": round(self.avg_validity, 4),
            "Validity_std": round(self.std_validity, 4),
            "Diversity": round(self.avg_diversity, 4),
            "Diversity_std": round(self.std_diversity, 4),
        }
        if any(m.pf_rubric is not None for m in self.metrics):
            s["PF_Final"] = round(self.avg_pf_final, 4)
            s["PF_Final_std"] = round(self.std_pf_final, 4)
        return s


# ── Evaluator ────────────────────────────────────────────────────────────────


class MCQEvaluator:
    """Evaluates generated distractors against ground truth."""

    def __init__(
        self,
        bank: MisconceptionBank,
        judge_client: LLMClient | None = None,
        embed_client: LLMClient | None = None,
    ):
        self.bank = bank
        self.judge = judge_client or LLMClient.from_role("judge")
        self.embed = embed_client or LLMClient.from_role("embed")

    # ── Family 1 ────────────────────────────────────────────────────────────

    def compute_pm(
        self,
        generated: list[str],
        human: list[str],
    ) -> float:
        """Proportional Match (normalized).

        Each generated answer is normalized (strip LaTeX, unify symbols) then
        compared by exact string to each normalized human distractor.
        Returns fraction matched.
        """
        if not generated or not human:
            return 0.0

        gen_norm = [normalize_expression(t).casefold() for t in generated]
        remaining_human = [normalize_expression(t).casefold() for t in human]

        matches = 0
        for generated_answer in gen_norm:
            if generated_answer in remaining_human:
                matches += 1
                remaining_human.remove(generated_answer)
        return matches / len(generated)

    def compute_text_similarity(
        self,
        generated: list[str],
        human: list[str],
    ) -> float:
        """Mean ROUGE-L F1 between generated and best-matching human distractor."""
        scores = []
        for g in generated:
            g_norm = normalize_expression(g)
            best = max(self._rouge_l_f1(g_norm, normalize_expression(h)) for h in human)
            scores.append(best)
        return float(np.mean(scores)) if scores else 0.0

    def compute_embed_similarity(
        self,
        generated: list[str],
        human: list[str],
    ) -> float:
        """Mean cosine similarity between generated and closest human distractor."""
        if not generated or not human:
            return 0.0

        # Normalize both sides (strip LaTeX, unify formatting) before embedding
        gen_norm = [normalize_expression(g) for g in generated]
        human_norm = [normalize_expression(h) for h in human]

        all_texts = gen_norm + human_norm
        vectors = self.embed.embed(all_texts)
        gen_vecs = np.array(vectors[: len(generated)])
        human_vecs = np.array(vectors[len(generated) :])

        # For each generated, find max similarity to any human
        norms_gen = np.linalg.norm(gen_vecs, axis=1, keepdims=True)
        norms_human = np.linalg.norm(human_vecs, axis=1, keepdims=True)
        sims = (gen_vecs @ human_vecs.T) / (norms_gen * norms_human.T + 1e-8)
        max_sims = sims.max(axis=1)
        return float(np.mean(max_sims))

    # ── Family 2 ────────────────────────────────────────────────────────────

    def compute_self_label_fidelity(
        self,
        generated_misconceptions: list[str],
        generated_texts: list[str],
        question_text: str = "",
        correct_answer: str = "",
    ) -> float:
        """Agreement between generator's self-labeled misconception and independent judge.

        For each distractor, both the generator and the judge (Llama-3.3-70B)
        name the misconception. Fidelity = fraction where they agree.
        """
        if not generated_misconceptions or not generated_texts:
            return 0.0

        agreements = 0
        for text, gen_label in zip(generated_texts, generated_misconceptions):
            if not gen_label:
                continue
            judge_label = self._judge_classify(text, question_text, correct_answer)
            if judge_label and self._labels_match(gen_label, judge_label):
                agreements += 1

        return agreements / len(generated_misconceptions)

    def compute_validity(
        self,
        generated_texts: list[str],
        question_text: str,
        correct_answer: str,
        human_distractors: list[str] | None = None,
        executor: ThreadPoolExecutor | None = None,
    ) -> float:
        """Fraction of distractors that are 'wrong but on-pathway'.

        Uses a teacher-primed LLM judge with error-first reasoning:
        1. Judge lists common student errors for this problem type
        2. Judge articulates what a student was thinking for each distractor
        3. Judge gives binary valid/invalid for each
        4. Self-consistency: 3 parallel calls, majority vote per distractor.
        """
        if not generated_texts:
            return 0.0

        # Filter empty
        gen_texts = [t for t in generated_texts if t]
        if not gen_texts:
            return 0.0

        votes = {i: [] for i in range(len(gen_texts))}

        def _one_call():
            return self._judge_validity_batch(gen_texts, question_text, correct_answer)

        if executor is not None:
            futures = [executor.submit(_one_call) for _ in range(3)]
            for future in as_completed(futures):
                results = future.result()
                if results:
                    for i, valid in enumerate(results):
                        votes[i].append(valid)
        else:
            for _ in range(3):
                results = _one_call()
                if results:
                    for i, valid in enumerate(results):
                        votes[i].append(valid)

        valid_count = 0
        for i in range(len(gen_texts)):
            if not votes[i]:
                continue
            # Majority vote (≥2 of 3)
            if sum(votes[i]) >= 2:
                valid_count += 1

        return valid_count / len(gen_texts)

    def compute_diversity(
        self,
        texts: list[str],
        question_text: str = "",
        correct_answer: str = "",
        executor: ThreadPoolExecutor | None = None,
    ) -> float:
        """Conceptual diversity via LLM judge.

        Asks the teacher-primed judge: "Do these 3 distractors target
        3 mathematically distinct misconceptions, or are they paraphrases
        of the same error?"

        Uses 3-call self-consistency with majority vote.
        Returns 1.0 if all distinct, 0.0 if at least two are the same error.
        """
        if len(texts) < 2:
            return 0.0

        def _one_call():
            return self._judge_diversity_batch(texts, question_text, correct_answer)

        if executor is not None:
            futures = [executor.submit(_one_call) for _ in range(3)]
            votes = [f.result() for f in as_completed(futures)]
        else:
            votes = [_one_call() for _ in range(3)]

        votes = [v for v in votes if v is not None]
        if not votes:
            return 0.0

        # Median of 3 calls (each returns 0.0, 0.5, or 1.0)
        return float(np.median(votes))

    # ── Family 3 — Rahimi et al. (2025) PF Rubric ──────────────────────────

    def compute_pf_rubric(
        self,
        generated_texts: list[str],
        question_text: str,
        correct_answer: str,
        executor: ThreadPoolExecutor | None = None,
    ) -> PFRubricScores:
        """Evaluate distractors using the Rahimi et al. (2025) 5-dimension PF rubric.

        Adapted for distractor quality:
          - APK: Does the distractor require prior knowledge to produce this error?
          - SSC: Is the distractor at the right difficulty (plausible, not trivial)?
          - AE:  Would this distractor feel authentic to a real student?
          - MR:  Do the 3 distractors span different representational forms?
          - OE:  Do they stem from different solution strategies/error types?

        Uses 3-call self-consistency, median per dimension.
        """
        if not generated_texts:
            return PFRubricScores()

        gen_texts = [t for t in generated_texts if t]
        if not gen_texts:
            return PFRubricScores()

        def _one_call():
            return self._judge_pf_rubric_batch(gen_texts, question_text, correct_answer)

        if executor is not None:
            futures = [executor.submit(_one_call) for _ in range(3)]
            raw_scores = [f.result() for f in as_completed(futures)]
        else:
            raw_scores = [_one_call() for _ in range(3)]

        raw_scores = [s for s in raw_scores if s is not None]
        if not raw_scores:
            return PFRubricScores()

        # Median across 3 calls for each dimension
        apk_vals = sorted(s["APK"] for s in raw_scores)
        ssc_vals = sorted(s["SSC"] for s in raw_scores)
        ae_vals = sorted(s["AE"] for s in raw_scores)
        mr_vals = sorted(s["MR"] for s in raw_scores)
        oe_vals = sorted(s["OE"] for s in raw_scores)

        def _med(vals):
            return vals[len(vals) // 2]

        pf = PFRubricScores(
            activation_prior_knowledge=_med(apk_vals),
            sweet_spot_calibration=_med(ssc_vals),
            affective_engagement=_med(ae_vals),
            multiple_representations=_med(mr_vals),
            open_endedness=_med(oe_vals),
        )
        pf.final_score = (
            pf.activation_prior_knowledge
            + pf.sweet_spot_calibration
            + pf.affective_engagement
            + pf.multiple_representations
            + pf.open_endedness
        )
        return pf

    def _judge_pf_rubric_batch(
        self,
        gen_texts: list[str],
        question_text: str,
        correct_answer: str,
    ) -> dict[str, float] | None:
        """LLM judge scores all 5 PF rubric dimensions for a set of distractors."""
        from pydantic import BaseModel

        class PFRubricOutput(BaseModel):
            APK: int  # 1-3
            SSC: int  # 1-3
            AE: int  # 1-3
            MR: int  # 1-3
            OE: int  # 1-3
            reasoning: str

        labels = ["A", "B", "C"]
        distractor_lines = "\n".join(f'  {labels[i]}: "{t}"' for i, t in enumerate(gen_texts[:3]))

        prompt = (
            "You are an experienced math teacher evaluating the quality of "
            "multiple-choice distractors using a research-based rubric.\n\n"
            f"Question: {question_text}\n"
            f"Correct answer: {correct_answer}\n\n"
            f"Here are 3 generated distractors:\n"
            f"{distractor_lines}\n\n"
            f"Score ALL THREE DISTRACTORS COLLECTIVELY on these 5 dimensions "
            f"(each 1=Low, 2=Moderate, 3=High):\n\n"
            f"1. Activation of Prior Knowledge (APK): Do these distractors "
            f"require a student to have learned the relevant concept to produce "
            f"this error? 1=random guess could produce it, 2=requires some "
            f"content knowledge, 3=requires specific prior knowledge to make "
            f"this exact error.\n\n"
            f"2. Sweet Spot Calibration (SSC): Are these distractors at the "
            f"right difficulty level? 1=trivially eliminated or impossibly "
            f"hard, 2=moderate challenge — some students would be fooled, "
            f"3=well-calibrated — students who know SOME but not ALL of the "
            f"concept would plausibly pick it.\n\n"
            f"3. Affective Engagement (AE): How authentic do these distractors "
            f"feel? 1=obviously machine-generated or nonsensical, 2=somewhat "
            f'plausible but feels artificial, 3="I have seen real students '
            f'make exactly these mistakes."\n\n'
            f"4. Multiple Representations (MR): Do the 3 distractors "
            f"collectively span different representational forms? 1=all same "
            f"type (all numeric, or all algebraic), 2=two different forms, "
            f"3=three different forms (e.g., numeric + algebraic + geometric/"
            f"visual reasoning).\n\n"
            f"5. Open-Endedness (OE): Do the distractors stem from different "
            f"solution strategies or error types? 1=same error, different "
            f"surface forms only, 2=two distinct error types, 3=procedural + "
            f"conceptual + factual errors all represented.\n\n"
            f'JSON: {{"APK": int, "SSC": int, "AE": int, "MR": int, '
            f'"OE": int, "reasoning": "..."}}'
        )

        try:
            result = self.judge.generate_structured(
                messages=[{"role": "user", "content": prompt}],
                schema=PFRubricOutput,
                temperature=0.0,
                max_tokens=500,
            )
            return {
                "APK": float(result.APK),
                "SSC": float(result.SSC),
                "AE": float(result.AE),
                "MR": float(result.MR),
                "OE": float(result.OE),
            }
        except Exception:
            return None

    # ── Full evaluation ─────────────────────────────────────────────────────

    def evaluate_generation(
        self,
        question_id: int,
        generated_distractors: list[dict[str, Any]],
        condition_name: str = "",
    ) -> QuestionMetrics:
        """Compute all metrics for one question's generation output.

        Args:
            question_id: Eedi QuestionId.
            generated_distractors: List of dicts with 'text' and optionally
                                   'target_misconception' keys.
            condition_name: Label for the condition.

        Returns:
            QuestionMetrics with all fields populated.
        """
        # Ground truth
        gt = self.bank.get_ground_truth_distractors(question_id)
        human_texts = [d["text"] for d in gt if not d["is_correct"]]

        gen_texts = [d.get("text", "") for d in generated_distractors]

        # Compute metrics
        pm = self.compute_pm(gen_texts, human_texts)
        text_sim = self.compute_text_similarity(gen_texts, human_texts)
        embed_sim = self.compute_embed_similarity(gen_texts, human_texts)

        # ── Family 2: misconception-grounded ──
        # Resolve question context for judge-based metrics
        q_text = ""
        correct = ""
        if self.bank.questions is not None:
            row = self.bank.questions[self.bank.questions["QuestionId"] == question_id]
            if not row.empty:
                q_text = str(row.iloc[0].get("QuestionText", ""))
                correct_letter = row.iloc[0].get("CorrectAnswer", "")
                correct = str(row.iloc[0].get(f"Answer{correct_letter}Text", ""))

        # ── Family 2: run validity & diversity in parallel ──
        # All 6 self-consistency calls (3 validity + 3 diversity) fire concurrently
        with ThreadPoolExecutor(max_workers=12) as ex:
            val_future = ex.submit(
                self.compute_validity, gen_texts, q_text, correct, human_texts, ex
            )
            div_future = ex.submit(self.compute_diversity, gen_texts, q_text, correct, ex)
            pf_future = ex.submit(self.compute_pf_rubric, gen_texts, q_text, correct, ex)
            validity = val_future.result()
            diversity = div_future.result()
            pf_rubric = pf_future.result()

        return QuestionMetrics(
            question_id=question_id,
            n_generated=len(gen_texts),
            n_human=len(human_texts),
            pm=pm,
            text_similarity=text_sim,
            embed_similarity=embed_sim,
            self_label_fidelity=0.0,
            diversity=diversity,
            validity=validity,
            pf_rubric=pf_rubric,
        )

    # ── Internal ────────────────────────────────────────────────────────────

    def _judge_classify(
        self,
        distractor_text: str,
        question_text: str = "",
        correct_answer: str = "",
    ) -> str | None:
        """Ask judge model to classify what misconception this distractor targets."""
        from pydantic import BaseModel

        class Classification(BaseModel):
            misconception: str
            confidence: float

        try:
            context = f"Question: {question_text}\n" if question_text else ""
            context += f"Correct answer: {correct_answer}\n" if correct_answer else ""
            result = self.judge.generate_structured(
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"{context}"
                            f"A student picks the wrong answer '{distractor_text}'.\n"
                            f"What misconception does this distractor target? "
                            f"Name the misconception (1-5 words) and give a confidence score (0-1)."
                        ),
                    }
                ],
                schema=Classification,
                temperature=0.0,
                max_tokens=100,
            )
            return result.misconception
        except Exception:
            return None

    def _judge_validity_batch(
        self,
        gen_texts: list[str],
        question_text: str,
        correct_answer: str,
    ) -> list[bool] | None:
        """Teacher-primed batch validity judge with error-first reasoning.

        Evaluates all distractors in one call by:
        1. Listing common student errors for this problem
        2. Articulating what a student was thinking for each distractor
        3. Judging whether that reasoning is plausible for a real student.

        Returns list of bools (one per distractor), or None on failure.
        """
        from pydantic import BaseModel

        class BatchValidity(BaseModel):
            A: bool
            B: bool
            C: bool
            all_distinct: bool
            student_errors: list[str]
            student_thinking: dict[str, str]
            reasoning: str

        # Build labeled distractor list (A, B, C)
        labels = ["A", "B", "C"]
        distractor_lines = "\n".join(f'  {labels[i]}: "{t}"' for i, t in enumerate(gen_texts[:3]))

        prompt = (
            "You are an experienced math teacher who has graded thousands of "
            "student exams. You know exactly which mistakes students make on "
            "each type of problem.\n\n"
            f"Question: {question_text}\n"
            f"Correct answer: {correct_answer}\n\n"
            f"STEP 1: List the 3-4 most common student errors for this type "
            f"of problem. What mistakes have you seen real students make?\n\n"
            f"STEP 2: Here are 3 student wrong answers:\n"
            f"{distractor_lines}\n\n"
            f"For EACH answer, first write 1 sentence from the student's "
            f"perspective: 'I chose this because...' — articulate what the "
            f"student was thinking. Then judge whether that reasoning is "
            f"plausible for a real student who understands basic concepts "
            f"but makes a specific error.\n\n"
            f"Output true ONLY if there is a clear, named error path that "
            f"a real student would follow. Output false if the answer is "
            f"random, unreachable, or no real student would think that way.\n\n"
            f"STEP 3: Are these 3 wrong answers targeting 3 mathematically "
            f"DISTINCT misconceptions (different error types), or are some "
            f"paraphrases of the same error? all_distinct=true ONLY if each "
            f"targets a genuinely different error.\n\n"
            f'JSON: {{"A": bool, "B": bool, "C": bool, "all_distinct": bool, '
            f'"student_errors": [...], "student_thinking": {{"A": "...", ...}}, '
            f'"reasoning": "..."}}'
        )

        try:
            result = self.judge.generate_structured(
                messages=[{"role": "user", "content": prompt}],
                schema=BatchValidity,
                temperature=0.0,
                max_tokens=500,
            )
            # Map A/B/C back to list order
            return [result.A, result.B, result.C]
        except Exception:
            return None

    def _judge_diversity_batch(
        self,
        gen_texts: list[str],
        question_text: str,
        correct_answer: str,
    ) -> float | None:
        """Ask teacher judge: how many distinct error types do these target?

        Returns 0.0 (1 type), 0.5 (2 types), or 1.0 (3 distinct types).
        """
        from pydantic import BaseModel

        class DiversityOutput(BaseModel):
            distinct_types: int  # 1, 2, or 3
            reasoning: str

        labels = ["A", "B", "C"]
        distractor_lines = "\n".join(f'  {labels[i]}: "{t}"' for i, t in enumerate(gen_texts[:3]))

        prompt = (
            "You are an experienced math teacher.\n\n"
            f"Question: {question_text}\n"
            f"Correct answer: {correct_answer}\n\n"
            f"Here are 3 student wrong answers:\n"
            f"{distractor_lines}\n\n"
            f"How many MATHEMATICALLY DISTINCT error types do these 3 answers "
            f"represent? Count distinct types, not distinct surface forms.\n\n"
            f"  1 = all 3 are the same error (paraphrases or same misconception)\n"
            f"  2 = two distinct errors (one pair targets the same error)\n"
            f"  3 = all three target completely different misconceptions\n\n"
            f"Examples:\n"
            f"  '×9', '+9', '−9' → 3 (confusing ÷ with ×, +, −)\n"
            f"  '×9', 'multiply by 9', 'times 9' → 1 (all same error)\n"
            f"  '×9', '×3', '÷3' → 2 (×9 and ×3 both 'wrong operator', ÷3 is different)\n\n"
            f'JSON: {{"distinct_types": int, "reasoning": "..."}}'
        )

        try:
            result = self.judge.generate_structured(
                messages=[{"role": "user", "content": prompt}],
                schema=DiversityOutput,
                temperature=0.0,
                max_tokens=200,
            )
            return (result.distinct_types - 1) / 2.0  # → 0.0, 0.5, 1.0
        except Exception:
            return None

    @staticmethod
    def _labels_match(label1: str, label2: str) -> bool:
        """Check if two misconception labels refer to the same error.

        Uses significant word overlap (≥50% of shorter label's words overlap)
        to catch different phrasings of the same misconception.
        """
        if not label1 or not label2:
            return False

        norm1 = label1.lower().strip()
        norm2 = label2.lower().strip()

        # Direct match
        if norm1 == norm2:
            return True

        # Significant word overlap
        stop_words = {
            "the",
            "a",
            "an",
            "of",
            "in",
            "to",
            "and",
            "or",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "can",
            "shall",
            "not",
            "no",
            "nor",
            "with",
            "for",
            "on",
            "at",
            "by",
            "from",
            "as",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "between",
            "out",
            "off",
            "over",
            "under",
            "again",
            "further",
            "then",
            "once",
            "here",
            "there",
            "when",
            "where",
            "why",
            "how",
            "all",
            "each",
            "every",
            "both",
            "few",
            "more",
            "most",
            "other",
            "some",
            "such",
            "only",
            "own",
            "same",
            "so",
            "than",
            "too",
            "very",
            "just",
            "because",
            "as",
            "if",
        }

        words1 = {w for w in norm1.split() if w not in stop_words and len(w) > 2}
        words2 = {w for w in norm2.split() if w not in stop_words and len(w) > 2}

        # Also try: check if one label is contained in the other
        if norm1 in norm2 or norm2 in norm1:
            return True

        if not words1 or not words2:
            return False

        intersection = words1 & words2
        # Relaxed: ≥33% overlap of the shorter label's words
        return len(intersection) / min(len(words1), len(words2)) >= 0.33

    @staticmethod
    def _rouge_l_f1(text1: str, text2: str) -> float:
        """ROUGE-L F1 based on longest common subsequence."""
        if not text1 or not text2:
            return 0.0

        # LCS length
        m, n = len(text1), len(text2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if text1[i - 1] == text2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

        lcs = dp[m][n]
        precision = lcs / m if m > 0 else 0
        recall = lcs / n if n > 0 else 0
        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)
