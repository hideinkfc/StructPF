# Historical: Thesis Framing - The Two Branches of Anticipating Student Methods

> This framing note has been folded into the current
> [PF_PIPELINE.md](../PF_PIPELINE.md). It is retained as the earlier
> formulation of the two-branch argument.
> The comparisons below used the older curated-record-preserving recommender.
> Current grounded D1 holds expert lists out and uses curriculum/textbook excerpts;
> current generation uses design briefs, bounded data/check/repair, then writing.
> The earlier wording is not current validation evidence.

> Status: framing note for the thesis narrative. Records how the MCQ work and
> the grounding work fit together under the main research question, and why the
> pipeline builds on literature grounding rather than LLM error generation.

---

## 1. The research question

> **Can an LLM pipeline generate Productive Failure exercises that actually
> elicit multiple meaningful student approaches, rather than producing a
> polished story wrapped around a single procedure?**

A PF exercise needs plausible accessible starts and a useful learning
opportunity. The historical framing emphasized breaking a named prior method;
it should not be read as requiring every valid method to fail. D1 proposes
resources and possible approaches; which methods students actually bring
requires response evidence.

**D1 has a source problem:** where does that list come from?

---

## 2. The two branches

```text
                    D1: Where do prior methods come from?
                                │
          ┌─────────────────────┴─────────────────────┐
          │                                           │
Branch A: LLM error generation             Branch B: Literature grounding
(MCQ distractors, Eedi-anchored)           (curriculum + expert papers)
          │                                           │
Plausible-sounding but low                 Paper/curriculum-verified prior
fidelity to real errors                    resources with provenance
```

| | **Branch A: MCQ error generation** | **Branch B: Literature grounding** |
|---|---|---|
| Source | LLM + Eedi misconception labels | Official curricula + expert papers |
| What it produces | Wrong-answer pathways (distractors) | Correct-but-insufficient prior tools |
| Compared against | Documented Eedi wrong answers | Author-reported prior resources |
| Historical result | PM ≈ 22%, diversity–fidelity tradeoff | Expert labels retained from supplied curated records |
| Limitation | Low answer matching is not proof of implausibility or confabulation | Resource labels do not establish student methods |

---

## 3. Branch A: what the MCQ study found

The MCQ distractor study (9 conditions, ~5,400 question-evaluations,
Llama-3.3-70B, plus Azure replications) tested whether an LLM can produce
student error pathways that match reality.

**Findings:**

1. **Prompting has a ceiling.** No prompt variant (CoT, self-critique,
   personas) broke through the performance barrier. Best PM ≈ 21.9% (near
   Feng et al.'s zero-shot bound of 23.6%).
2. **The PM–diversity tradeoff.** Grounding distractors in real misconceptions
   increased diversity (+~33%) but cost match-rate (−~30%) and validity
   (−~10%). Both objectives cannot be maximized with prompting alone.
3. **Judge ceiling effect.** LLM-as-judge gave 15/15 to 8 of 9 exercises — no
   discrimination —    motivating a separate agent-review diagnostic, not establishing completed
   human evaluation.
4. **Structured pathways work as an instrument.** Distractors with
   `faulty_step` + `reasoning_steps` enable clustering and verification that
   bare answer text cannot — but this improves the *instrument*, not the
   *fidelity*.

**Honest reading:** the distractors were weak as a source of prior methods.
That is a finding, not an embarrassment — it is the evidence that Branch A
alone cannot supply D1.

---

## 4. Branch B: what the grounding study found

The grounded prior-method recommender
([run_prior_recommendations.py](../../../scripts/run_prior_recommendations.py))
sources prior methods from curriculum documents (MOE, CBSE, NRW, Lippman OER,
CCSS) and curated expert-paper records, with page-level provenance.

**Findings (functional comparison, GPT-4.1-mini and GPT-5.6-luna):**

1. **Historical grounded output contains the expert lists.** On the three topic-diverse expert
   cells (Kapur average speed, Loibl variance, Kerrigan fair division), the
   historical grounded condition retained the documented resources with
   checkable provenance; the ungrounded condition missed resources.
2. **Curated preservation explains the label agreement.** Both models retained
   the same resources because the historical runner preserved curated records.
   This was not independent model recovery or proof of model-independent
   curriculum retrieval.
3. **Historical trace limitation.** The saved student-move expansion is procedurally narrow: it
   misses qualitative insights, diagrammatic approaches, and algebraic
   attempts that Kapur's observed RSMs document. (See
   [PRIOR_RECOMMENDATIONS_TRACE.md](../PRIOR_RECOMMENDATIONS_TRACE.md), §5.)

---

## 5. Why this framing is honest and strong

1. **The bad distractors are the evidence for the pivot.** Branch A's
   documented failure is what justifies Branch B's design. Without the
   contrast, grounding's success has no baseline.
2. **It matches the real research arc.** Error generation was tried first,
   found insufficient, and the pipeline pivoted to curriculum resources.
3. **The claim is falsifiable.** "For PF design, prior methods are better
   sourced from what students were taught than from what LLMs infer about
   student errors" is a citable, testable claim.

---

## 6. Where each branch ends up in the pipeline

```text
Branch B (literature grounding) ──> D1 Anticipate  [primary source]
                                    D2 Calibrate    [falls_short_because feeds trap design]

Branch A (MCQ error generation) ──> D4 Verify       [optional probe only:
                                                     is a specific tempting error plausible?]
```

Branch A is retained, but demoted: from a *source* of prior methods to an
*optional verification probe* for tempting errors. This matches the pathway
doc's rule that MCQ output is never input text for the PF writer
([PF_GENERATION_FROM_PATHWAYS.md](PF_GENERATION_FROM_PATHWAYS.md), §11-12).

---

## 7. The two sentences for the paper

**Introduction:**

> "A PF exercise is only as good as its model of what students will try. We
> compare two ways to obtain that model: generating error pathways with an
> LLM, versus grounding them in curriculum documents and expert-published
> prior knowledge."

**Historical proposed results wording (not a current thesis claim):**

> "LLM-generated error pathways were plausible-sounding but poorly anchored to
> real student errors (PM ≈ 22%), and exhibited a diversity–fidelity tradeoff
> that prompting could not resolve. Literature-grounded resources, by contrast,
> recovered the complete expert prior-resource lists on all tested cells with
> checkable provenance. The pipeline therefore builds on grounding, and the
> error-generation branch is retained only as an optional tempting-error probe."

This draft wording overstates independent recovery: the grounded arm received
the curated resource lists. PM is secondary Eedi reference alignment, not a
behavioral fidelity score. A current claim must retain those limitations and
must not equate a resource inventory with observed methods.

---

## 8. Caveat: the comparison is not yet apples-to-apples

Branch A was evaluated on answer-level match to Eedi errors; Branch B on
resource recovery on expert tasks. The airtight version evaluates both on the
same downstream criterion: does the D1 list, however produced, lead to better
PF exercises (RSM diversity, open-endedness)? That is the full uplift study —
currently open.

---

## Key artifacts

- MCQ study: [MCQ_EVALUATION_OVERVIEW.md](../../mcq/MCQ_EVALUATION_OVERVIEW.md),
  [MCQ_GENERATION_OVERVIEW.md](../../mcq/MCQ_GENERATION_OVERVIEW.md)
- Grounding corpus: [data/curriculum_grounding](../../../data/curriculum_grounding/README.md)
- Grounded/ungrounded comparison:
  [expert_comparison_gpt41mini_final.json](../../../experiments/results/prior_recommendations/expert_comparison_gpt41mini_final.json),
  [expert_comparison_gpt56luna.json](../../../experiments/results/prior_recommendations/expert_comparison_gpt56luna.json)
- Real-run trace: [PRIOR_RECOMMENDATIONS_TRACE.md](../PRIOR_RECOMMENDATIONS_TRACE.md)
