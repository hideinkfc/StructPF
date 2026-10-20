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
   (3 stages + curriculum graph)            |
      |                               6. Validating the Evaluation Framework
      |                                     |
      +-------------------------------------+
      |
7. Results
   - 7.1-7.3 Main results (previous tasks, StructPF vs. one-shot, 30-topic grounding study)
   - 7.4-7.5 Alternatives and negative results (MCQ pathways, simulated-student feedback)
      |
8. Discussion and Conclusion
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
  - *4.2.1 Why Prior Knowledge Must Come from Outside the LLM* (brief rationale; empirical comparison in Section 7.4 and Appendix A)
  - *4.2.2 The Learning Commons Knowledge Graph*
  - *4.2.3 From Graph Records to Prior-Skill Records*
- **4.3 Stage 2: Designing the Problem and Choosing Numbers Where Familiar Methods Fall Short** (code: `D2a`, `D2b`)
  - *4.3.1 Proposing and Selecting a Design Brief*
  - *4.3.2 Choosing and Checking the Numbers*
- **4.4 Stage 3: Writing an Open Task Without Giveaways** (code: `D3`)
- **4.5 Scope of the Pipeline** (Phase 2 teacher consolidation boundary, why simulated-student revision is excluded in Section 7.5, and call budget)
- **4.6 Summary of the Pipeline** (detailed architecture figure aligned with the human design steps; Figure 4.1 stays a simple process model with the bounded revision loops and tool calls)

---

## Chapter 5: Evaluation Framework for PF Tasks
- **5.1 Five Task-Design Measures Derived from PF Theory**
- **5.2 A Prior-Knowledge Solver and Two Judges** (constrained solver, task judge, attempt judge)
- **5.3 Checking Prior-Knowledge Validity and the Failure of Familiar Methods** (`Gate 1`, `Gate 2`)

---

## Chapter 6: Validating the Evaluation Framework
- **6.1 Scoring Expert PF Tasks, Routine Problems, and Control Tasks**
- **6.2 Checking Whether the Solver Finds the Expected Student Approaches**

---

## Chapter 7: Results
- **7.1 Evaluating Previously Generated Tasks**
- **7.2 `StructPF` Compared with One-Shot Generation**
- **7.3 The Effect of Curriculum Grounding Across 30 Topics**
  - *7.3.1 Is the Proposed Prior Knowledge Valid?* (`Gate 1`)
  - *7.3.2 Do Familiar Methods Fail on the Student Task?* (`Gate 2`)
- **7.4 Why Multiple-Choice Error Pathways Were Not Sufficient**
- **7.5 Why Simulated-Student Feedback Did Not Improve the Tasks**

---

## Chapter 8: Discussion and Conclusion
- **8.1 What the Findings Show About LLMs in PF Task Design**
- **8.2 Limitations**
- **8.3 Conclusion and Future Work**

---

## Appendices
- **Appendix A: Generating and Evaluating Multiple-Choice Distractors on Eedi Data**
- **Appendix B: Rubrics, Prompts, and Full Task Examples**


