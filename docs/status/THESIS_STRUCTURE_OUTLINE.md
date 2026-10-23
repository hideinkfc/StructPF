# Master's Thesis Structure Outline

**Thesis Title:** *StructPF: Towards Pedagogically Sound Productive Failure Task Generation with Large Language Models*

Add comments or adjustments directly under any chapter or section heading below.

---

## Overall Chapter Flow

```text
1. Introduction
      |
2. Background and Related Work
      |
3. One-Shot LLM Generation of PF Tasks
      |
      +-------------------------------------+
      |                                     |
4. The StructPF Generation Pipeline   5. Evaluation Framework for PF Tasks
   (3 stages + curriculum graph)         (validation folded in as 5.4)
      |                                     |
      +-------------------------------------+
      |
6. Results
   - 6.1-6.3 Main results (one-shot tasks, StructPF on the same settings, 30-topic grounding study)
   - 6.4 Signals that did not guide generation (MCQ pathways, simulated-student feedback)
      |
7. Discussion and Conclusion
      |
Appendices (A: Eedi MCQ distractor study; B: Rubrics, prompts, task examples)
```

---

## Chapter 1: Introduction
- **1.1 Productive Failure and the Effort of Designing PF Tasks**
- **1.2 Challenges in Generating and Evaluating PF Tasks with LLMs**
- **1.3 Purpose of this Research (`G1-G4`)**
- **1.4 Thesis Structure**

---

## Chapter 2: Background and Related Work
- **2.1 Productive Failure and Why It Works**
  - *2.1.1 Evidence that PF Improves Learning*
  - *2.1.2 Why Failure Becomes Productive*
- **2.2 LLMs for Generating Educational Tasks and Productive Failure**
  - *2.2.1 Generating Multiple-Choice Questions and Distractors*
  - *2.2.2 Applying LLMs to Productive Failure*
- **2.3 Evaluating Generated Educational Content with LLMs**
  - *2.3.1 Judging Task Text Directly with Rubrics and Checklists*
  - *2.3.2 Testing Tasks Behaviorally with Simulated Students*
- **2.4 Summary and Research Gap**

---

## Chapter 3: One-Shot LLM Generation of PF Tasks
- **3.1 Reproducing One-Shot PF Generation**
- **3.2 Failure Modes of One-Shot PF Tasks**
  - *3.2.1 Familiar Methods Remove the Impasse*
  - *3.2.2 Wording Gives Away the Target and Method*
  - *3.2.3 Worksheets Replace the Open Challenge*
  - *3.2.4 Tasks Miss Target Requirements, Contain Math Errors, or Repeat Templates*
- **3.3 Why the Rubric Gives High Scores to Flawed Tasks**

---

## Chapter 4: The `StructPF` Generation Pipeline
- **4.1 Designing PF Tasks the Way Human Designers Do**
- **4.2 Stage 1: Anticipating What Students Already Know** (code: `D1`)
  - *4.2.1 Why Prior Knowledge Must Come from Outside the LLM* (brief rationale; empirical comparison in Section 6.4 and Appendix A)
  - *4.2.2 The Learning Commons Knowledge Graph*
  - *4.2.3 From Graph Records to Prior-Skill Records*
- **4.3 Stage 2: Designing the Problem and Choosing Numbers Where Familiar Methods Fall Short** (code: `D2a`, `D2b`)
  - *4.3.1 Proposing and Selecting a Design Brief*
  - *4.3.2 Choosing and Checking the Numbers*
- **4.4 Stage 3: Writing an Open Task Without Giveaways** (code: `D3`)
- **4.5 Scope of the Pipeline** (Phase 2 teacher consolidation boundary, why simulated-student revision is excluded in Section 6.4, and call budget)
- **4.6 Summary of the Pipeline** (detailed architecture figure aligned with the human design steps; Figure 4.1 stays a simple process model with the bounded revision loops and tool calls)

---

## Chapter 5: Evaluation Framework for PF Tasks
- **5.1 From Expert Task Review to Requirement Checks**
- **5.2 Five Task-Design Measures**
- **5.3 Prior-Knowledge Solver and Evaluation Judges** (task judge, prior-knowledge solver, attempt judge)
- **5.4 Validating the Evaluation Framework** (the former Chapter 6)
  - *5.4.1 Testing the Solver on Expected Approaches*
  - *5.4.2 Validating the Complete Evaluator on Reference Tasks*

The two gate definitions (`Gate 1`, `Gate 2`) are no longer in Chapter 5. Their old
text is kept as a comment in `07-results.tex` under Section 6.3.

---

## Chapter 6: Results

**Status: proposed outline recorded for review. Not written; no new runs started.**
The order follows the goals. It starts with where one-shot tasks fall short, moves to
StructPF on the same settings, then to the broad 30-topic test, and ends with the
signals that did not help. All numbers are computational model judgments, not human
ratings or student outcomes.

- **6.1 Experiment Setup** (`6.1.1 Fixed Prior Knowledge`, `6.1.2 Proposed Prior Knowledge`)
  - Explains why student prior knowledge is specified via the curriculum (with student
    error logs and simulated students moved to Appendix C) and contrasts Study (a) (fixed
    prior knowledge on the four Grade 7 settings, 118 GPT-5 mini one-shot, 120 GPT-4.1
    one-shot, 120 GPT-5 mini StructPF tasks, evaluated with the five measures and pooled
    Luna + GPT-4.1 solvers) against Study (b) (proposed prior knowledge across 30 Common
    Core topics in Grades 5 to 10, three GPT-5 mini arms evaluated with the Two-Step Check).
- **6.2 One-Shot Tasks under the Evaluation Framework** (G1 to G3)
  - Question: where do one-shot tasks fall short when checked against the PF requirements?
  - Evidence: all ready Main30 one-shot tasks described in Chapter 3 (118 of 120 for
    GPT-5 mini, rubric mean 14.6; 120 of 120 for GPT-4.1, rubric mean 12.8) under
    `pf-three-role/v3.1` with pooled Luna and GPT-4.1 solvers
    (`experiments/results/pf_newest_pipeline_rahimi_eval_optA_v31_gpt5mini_20261021/main30_oneshot_v30`).
    Only 10 of 118 GPT-5 mini tasks (8.5%) and 4 of 120 GPT-4.1 tasks (3.3%) pass all five
    measures, and 98 of 118 (83.1%) and 102 of 120 (85.0%) fail on limits (`No`) because a
    one-step familiar method already solves the task (`12` and `13` tasks receive `Yes` on
    limits). Shown as grey grouped horizontal bars of Yes counts per measure (Figure 6.2,
    `scripts/render_fig6_2_oneshot_outcomes.py`).
- **6.3 `StructPF` on the Same Settings** (G2, G4)
  - Question: does staged generation with tied-baseline number design fix this when the
    generator model (`GPT-5 mini`), evaluator (`v3.1` with pooled Luna and GPT-4.1 solvers)
    and inputs are matched?
  - Evidence: 120 StructPF tasks on the four Rahimi settings generated with `GPT-5 mini`
    (`120 / 120` ready, `experiments/results/pf_newest_pipeline_rahimi_eval_optA_v31_gpt5mini_20261021/summary.json`).
    `68 of 120` (`56.7%`) pass all five measures (`25 of 30` in music, `17 of 30` in garden,
    `15 of 30` in basketball, `11 of 30` in shopping), and the limits measure is `Yes` for
    `96 of 120` (`80.0%`, `21 No`), while the Chapter 3 surface rubric mean is `12.1 / 15`.
    (Initial untuned run under `v3.0` passed `4 of 120`.)
- **6.4 Curriculum Grounding Across 30 Topics** (G4)
  - Question: do staging and curriculum grounding help across many topics?
  - Evidence: 30 topics by three arms (one-shot, StructPF without grounding, StructPF
    with Learning Commons grounding), all generated with `GPT-5 mini` and evaluated with
    the frozen Two-Gate Check (`experiments/results/pf_progression_bridge_30cases_3arms_gpt5mini_20261021/summary_three_arm.json`;
    30, 29 and 30 tasks produced). Prior-knowledge lists that already contain the target
    concept fall from 17 to 5 to 0 of 30 (valid sets rise from 13 to 24 to 30 of 30).
    Tasks where familiar methods fail for the reason the target concept is needed rise
    from 6 to 16 to 19 of 30 (mean score 0.633, 1.333 and 1.633 out of 2). (Earlier
    `GPT-5.6-luna` generator run gave 15, 4 and 0 spoilers and 6, 17 and 21 score-2 tasks.)
  - *6.3.1 Is the Proposed Prior Knowledge Valid?* (`Gate 1`)
  - *6.3.2 Do Familiar Methods Fail on the Student Task?* (`Gate 2`)
  - Planned figure: stacked bars of scores 0, 1 and 2 per arm, then one high-scoring and
    one low-scoring case side by side.
- **6.4 Signals That Did Not Guide Generation** (merges the former MCQ and
  simulated-student sections; the introduction roadmap already promises this content)
  - Role in the story (proposed, not yet approved): StructPF and the evaluator anticipate
    students from curriculum knowledge and design rather than from student data. 6.4 tests
    the two obvious alternatives and links each finding back to the design choice it
    supports. Real error logs lead to Stage 1 using the curriculum graph. Simulated
    students lead to the solver in Chapter 5 and to having no feedback loop after
    Stage 3. It also explains why the original plan (generate, simulate students,
    refine) became generate and then test with a solver.
  - Framing caution: the Eedi pilot does not show that the solver is weak. The solver
    tests the task and is not meant to imitate students. A single direct LLM call matches
    real errors equally poorly (13.2% versus 13.6% to 14.0%).
  - Multiple-choice error pathways: on 68 Eedi items, the solver reproduces wrong answers
    worth about 14% of the wrong-answer student share and faulty steps worth 7.5%.
  - Simulated-student feedback: the coverage-informed revision gave 3 of 3 versus 2 of 3
    tasks meeting the requirements, below the planned +2 margin. Whether a learner path
    was reached depended on the simulator (0 of 8 GPT-4.1 replies versus 4 of 4 GPT-5.4
    replies on the same task).

**Open gaps before writing (decision pending with the user):**
1. Section 6.3 was scored with the two-step gate check (Luna), not the five-measure
   evaluator validated in Section 5.4. Either define and justify the gates in 6.3, or
   run v3.0 on the 90 tasks (paid model calls, needs approval).
2. The one-shot v3.0 pass rates for the four settings in `PF_PIPELINE.md` (2.5% for
   GPT-4.1, 0.8% for GPT-5 mini) have no saved summary file. Only 16 of the 240 Main30
   one-shot tasks have v3.0 outcomes (1 of 16 passes all five). Either report only
   those 16, or run v3.0 on the 240 one-shot tasks for a like-for-like comparison with
   the 120 StructPF tasks.
3. The references in the reference-task pack were set by the assistant
   (`assistant_provisional`), and the 29 reference tasks are a tuning set, not a holdout.

Sources: [PF_PIPELINE.md](../pf-generation/PF_PIPELINE.md),
`experiments/results/pf_v30_calibration_20261015/`,
`experiments/results/pf_newest_pipeline_rahimi_eval_20261016/summary.json`,
`experiments/results/pf_progression_bridge_30cases_3arms_20261016/summary_three_arm.json`,
`experiments/results/pf_eedi_coverage_20261016/summary.json`.

---

## Chapter 7: Discussion and Conclusion
- **7.1 What the Findings Show About LLMs in PF Task Design**
- **7.2 Limitations**
- **7.3 Conclusion and Future Work**

---

## Appendices
- **Appendix A: Generating and Evaluating Multiple-Choice Distractors on Eedi Data**
- **Appendix B: Rubrics, Prompts, and Full Task Examples**


