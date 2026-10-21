# Rahimi et al. (2025) — Methodology Summary

**Title:** Small vs. Large Language Models: Comparing Language Models in Generating Productive Failure Math Problems

**Authors:** Seyedahmad Rahimi (Georgia Tech), Salah Esmaeiligoujar, Deniz Ercan, Maryam Babaee, Ran Gao (University of Florida)

**Source:** [Repository PDF](paper_135.pdf), especially Table 1 on p. 2 and Table 2 on p. 3. This note separates the paper's human-rating study from this repository's later model-judged experiments. Repository status is updated through October 10, 2026.

---

## 1. Research Question

> Is there any difference between GPT-4o and Phi-3 in the quality of PF problems that they generate? If so, how large is this effect?

---

## 2. Experimental Design

### 2.1 Models Compared

| Model | Type | Parameters | Deployment |
|-------|------|-----------|------------|
| **GPT-4o** | LLM (proprietary) | Not disclosed; no size estimate assumed | API-based |
| **Phi-3 mini** | SLM (open) | 3.8B, as identified in the paper | API-based |

### 2.2 Problem Generation

- **Total problems:** 60 (GPT-4o = 30, Phi-3 = 30)
- **Domain:** 7th grade algebra — ratios and proportional relationships
- **Common Core standard:** `CCSS.Math.Content.7.RP.A.2`
- **Prior knowledge prerequisites:** Unit rates (`7.RP.A.1`) and the paper's "operations with rational numbers" (`7.NS.A.1`). The latter standard specifically concerns addition/subtraction; our benchmark does not silently expand its code to all rational-number operations.
- **Thematic context:** Sports (basketball, Stephen Curry)
- **Controlled variables (held constant across all 60 problems):** grade level, domain, Common Core standard, theme, student interest, prior knowledge concepts

### 2.3 Prompt Structure (identical for both models)

The prompt had **6 components:**

1. **Roles and objectives** — model positioned as an educational design assistant generating PF math problems
2. **Response rules** — narrative format, tone, open-endedness requirements, content restrictions
3. **PF overview** — description of Productive Failure phases and pedagogical purpose
4. **Detailed rubric** — the prose says six criteria, but Table 1 specifies five dimensions, each scored 1–3. The total is their sum, not a sixth 3-point dimension.
5. **Human-generated examples** — 5 example math problems illustrating expected quality and PF problem structure
6. **Generation instructions** — guidance to create a new open-ended narrative problem aligned with the specified standard, grade level, theme, interest, and prior knowledge

---

## 3. Evaluation Rubric (5 Dimensions, each 1–3)

| # | Dimension | 1 (Low) | 2 (Moderate) | 3 (High) |
|---|-----------|---------|--------------|----------|
| 1 | **Activation of Prior Knowledge (APK)** | No prerequisite concepts | Includes one prerequisite concept | Includes two or more prerequisite concepts |
| 2 | **Sweet Spot Calibration (SSC)** | Too easy or too difficult → disengagement | Moderate challenge with some failures | Well-calibrated: challenging but manageable, leading to productive engagement |
| 3 | **Affective Engagement (AE)** | Not relatable or meaningful; fails to engage | Somewhat engaging with relatable/realistic elements | Highly engaging, presented in meaningful narrative or real-world scenario |
| 4 | **Multiple Representations & Solutions (MR)** | Few or no representations or solution methods | Some diversity but limited | Wide range of representations and solution methods; fosters creativity and collaboration |
| 5 | **Open-endedness / Ill-structuredness (OE)** | Simple, well-structured, single path | Moderate complexity with limited variables | Highly complex, requiring integration of multiple variables and representations |

**Final Score** = sum across all 5 dimensions (range: 5–15)

MR does not count display formats using fixed one/two/three thresholds. A unique numerical answer does not by itself imply low OE. Later repository prompts clarify these anchors operationally; those additions are not verbatim paper guidance.

---

## 4. Evaluation Procedure

### 4.1 Human Rating Process

- **Two trained human raters** independently scored each problem using the PF rubric
- **Blinding:** Raters did not know which model generated each problem (unique identifiers, blinded database)
- **Adjudication rule:** Discrepancies ≥ 5 total points triggered a third rater (occurred in 16 of 60 cases)
- **Final score:** Mean of the two closest ratings in case of adjudication

### 4.2 Statistical Analysis

- **Test:** Independent-samples t-tests (two-tailed)
- **Comparisons:** GPT-4o vs. Phi-3 on (a) Final Score and (b) each of the 5 subscale scores
- **Effect size:** Cohen's d, with 95% confidence intervals
- **Significance threshold:** p < .05
- **Visualizations:** Box/violin plots for Final Score distribution and per-dimension subscore distributions

---

## 5. Key Design Decisions (Notable for Replication)

| Decision | Rationale |
|----------|-----------|
| Only 30 problems per model | A limited human-rating sample; the observed effect size is not a prospective power calculation |
| Single grade level & domain | Controls confounding; clean ablation |
| Identical prompts | Ensures fair comparison; isolates model capability |
| 5 human-written examples in prompt | Strong few-shot baseline; raises floor for both models |
| 6-component structured prompt | Mirrors real-world educational content creation workflow |
| Two raters + adjudication | Balances reliability and cost; 16/60 cases escalated |
| 3-point rubric scale | Five coarse task-quality judgments; scoring alone does not establish learning or approach diversity |

---

## 6. Results (for reference)

| Dimension | GPT-4o M (SD) | Phi-3 M (SD) | t | p | d |
|-----------|---------------|--------------|---|---|---|
| APK | 2.65 (0.35) | 2.42 (0.53) | 2.02 | .049 | 0.52 |
| SSC | 2.52 (0.55) | 2.08 (0.62) | 2.87 | .01 | 0.74 |
| AE | 2.75 (0.47) | 2.45 (0.71) | 1.93 | .06 | 0.50 |
| MR | 2.70 (0.43) | 1.83 (0.61) | 6.40 | <.001 | **1.65** |
| OE | 2.77 (0.47) | 1.88 (0.64) | 6.11 | <.001 | **1.58** |
| **Final** | **13.38 (1.88)** | **10.67 (2.73)** | **4.49** | **<.001** | **1.16** |

- The largest reported human-rating differences favor GPT-4o on **Multiple Representations & Solutions** (d = 1.65) and **Open-Endedness** (d = 1.58); these are standardized rating differences, not learning effects.
- No significant difference on **Affective Engagement** (p = .06)
- Phi-3 has the larger reported score spread (SD 2.73 versus 1.88), not evidence here of a verified bimodal distribution.
- These are the paper's results, not our model outputs, student responses, or a replicated human-rating result.

---

## 7. Limitations (as noted by authors)

- Only 60 problems, single domain, single grade level
- No classroom-based teacher review
- No observed student approach diversity or learning outcomes established by these rubric ratings
- No fine-tuning of the SLM (Phi-3 used off-the-shelf)
- Future work: improve SLM via prompt engineering, fine-tuning (QLoRA), retrieval-augmented generation, or multi-SLM ensemble systems

---

## 8. Relevance to Our Work

| Their Design | Current Repository Use |
|--------------|-------------|
| Direct PF generation | Reconstructed paper-setting V1/V2/V3 baseline, compared with a decomposed method; not the exact published prompt or model study |
| Five human-rated PF dimensions | Separately frozen Luna task-level rubrics; original v1 ratings and exploratory v2/v2.1 reratings remain distinct |
| GPT-4o vs Phi-3 mini | Our completed paper-setting generation and judging use GPT-5.6-luna; no claim of an SLM replication |
| Five human-generated prompt examples | Five attributed StratL task adaptations in our reconstruction; Rahimi's exact example texts are unknown |
| Human raters and adjudication | Our saved first-pool ratings are agent review; later comparisons are model judgments, not completed human participant evaluation |
| SSC, MR, and OE | Exercise affordances, distinct from MCQ incorrectness, plausibility, coherence, or conditional faulty-step diversity |
| Controlled setting | Each historical v1/v4 method comparison schedules 30 attempts per condition and reports ready-task denominators |
| Directions for later research | Our current next step is improving student-facing tasks and testing elicited approaches, not an established 7B fine-tuning plan |

The completed MCQ study is a separate design instrument: 11 conditions, 200 held-out questions, and 3 runs with GPT-4.1-mini. Its compact 0–2 plausibility score is a model estimate; `score >= 1` is broad screening, not human validity. Structured paths are optional outside the pathway study, and Eedi PM is secondary reference alignment. Better distractor scores do not demonstrate better PF exercises.

The historical paper-setting PIPELINE used mathematical-plan review and fill/check. Its v4 run delivered 22/30 tasks; the v2.1 rerating of those same tasks averaged 10.91/15, versus V1's 14.03/15 over 30/30 tasks. Higher means a stronger Luna rubric judgment, not improved learning. These results do not evaluate the newer default.

As of October 10, the default is resource context → selected design brief (D2a) → bounded data/check/values-only repair (D2b) → task writing (D3). D2b is frozen for its agreed scope, with a three-call budget including invalid proposal retries, exact checks of supplied predicates, separate model-judged textual claims, and visible uncertainty. Final continuations of three saved designs delivered three tasks using five data calls and three writer calls (two schema retries, no numerical repairs). Four preliminary live calibrations used eight calls separately. Offline phases reuse the same eight saved inputs; 551 affected software tests passed, not the full suite. None of these comparisons validates student behavior or learning.

Current qualitative concerns include a fixed-journey speed comparison instead of the expert's unknown bicycle-handover decision, announced equal averages and extremes in consistency, and supplied allocation values in fair division. These are assistant diagnoses, not human ratings. See the [canonical PF record](../../docs/pf-generation/PF_PIPELINE.md) for artifacts and remaining work.

**Citation role:** Rahimi establishes prior automatic PF generation and a published human-rating rubric, correcting an earlier "no prior work" claim. It does not independently validate our rubric judges, simulations, or generated tasks.
