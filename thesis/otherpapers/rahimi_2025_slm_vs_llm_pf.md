# Rahimi et al. (2025) — Methodology Summary

**Title:** Small vs. Large Language Models: Comparing Language Models in Generating Productive Failure Math Problems

**Authors:** Seyedahmad Rahimi (Georgia Tech), Salah Esmaeiligoujar, Deniz Ercan, Maryam Babaee, Ran Gao (University of Florida)

---

## 1. Research Question

> Is there any difference between GPT-4o and Phi-3 in the quality of PF problems that they generate? If so, how large is this effect?

---

## 2. Experimental Design

### 2.1 Models Compared

| Model | Type | Parameters | Deployment |
|-------|------|-----------|------------|
| **GPT-4o** | LLM (proprietary) | Unknown (est. >1T) | API-based (OpenAI) |
| **Phi-3** | SLM (open) | ~3.8B | API-based (Microsoft) |

### 2.2 Problem Generation

- **Total problems:** 60 (GPT-4o = 30, Phi-3 = 30)
- **Domain:** 7th grade algebra — ratios and proportional relationships
- **Common Core standard:** `CCSS.Math.Content.7.RP.A.2`
- **Prior knowledge prerequisites:** Unit rates (`7.RP.A.1`), operations with rational numbers (`7.NS.A.1`)
- **Thematic context:** Sports (basketball, Stephen Curry)
- **Controlled variables (held constant across all 60 problems):** grade level, domain, Common Core standard, theme, student interest, prior knowledge concepts

### 2.3 Prompt Structure (identical for both models)

The prompt had **6 components:**

1. **Roles and objectives** — model positioned as an educational design assistant generating PF math problems
2. **Response rules** — narrative format, tone, open-endedness requirements, content restrictions
3. **PF overview** — description of Productive Failure phases and pedagogical purpose
4. **Detailed rubric** — 6 evaluation criteria (5 dimensions + overall), each scored on a 3-point scale (1 = Low, 2 = Moderate, 3 = High)
5. **Human-generated examples** — 5 example math problems illustrating expected quality and PF problem structure
6. **Generation instructions** — guidance to create a new open-ended narrative problem aligned with the specified standard, grade level, theme, interest, and prior knowledge

---

## 3. Evaluation Rubric (5 Dimensions, each 1–3)

| # | Dimension | 1 (Low) | 2 (Moderate) | 3 (High) |
|---|-----------|---------|--------------|----------|
| 1 | **Activation of Prior Knowledge (APK)** | No prerequisite concepts | Includes one prerequisite concept | Includes two or more prerequisite concepts |
| 2 | **Sweet Spot Calibration (SSC)** | Too easy or too difficult → disengagement | Moderate challenge with some failures | Well-calibrated: challenging but manageable, leading to productive engagement |
| 3 | **Affective Engagement (AE)** | Not relatable or meaningful; fails to engage | Somewhat engaging, with relatable/realistic elements | Highly engaging, connects to personal interests and real-world contexts |
| 4 | **Multiple Representations (MR)** | Single representation only (text-only) | Two representations (e.g., text + table) | Three or more representations (e.g., text + table + graph + diagram) |
| 5 | **Open-Endedness (OE)** | Single correct answer; one solution path | Some flexibility; limited interpretation | Multiple solution pathways; divergent thinking encouraged |

**Final Score** = sum across all 5 dimensions (range: 5–15)

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
| Only 30 problems per model | Manageable for human evaluation; enough for statistical power (d = 1.16 detected) |
| Single grade level & domain | Controls confounding; clean ablation |
| Identical prompts | Ensures fair comparison; isolates model capability |
| 5 human-written examples in prompt | Strong few-shot baseline; raises floor for both models |
| 6-component structured prompt | Mirrors real-world educational content creation workflow |
| Two raters + adjudication | Balances reliability and cost; 16/60 cases escalated |
| 3-point rubric scale | Coarse enough for inter-rater reliability; fine enough to detect differences |

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

- GPT-4o dominates on **Multiple Representations** (d = 1.65) and **Open-Endedness** (d = 1.58)
- No significant difference on **Affective Engagement** (p = .06)
- Phi-3 distribution is bimodal — some very weak (score ~6), some near GPT-4o quality (score ~14)
- GPT-4o scores tightly clustered at high end (13–15) with low variance

---

## 7. Limitations (as noted by authors)

- Only 60 problems, single domain, single grade level
- No classroom-based teacher review
- No fine-tuning of the SLM (Phi-3 used off-the-shelf)
- Future work: improve SLM via prompt engineering, fine-tuning (QLoRA), retrieval-augmented generation, or multi-SLM ensemble systems

---

## 8. Relevance to Our Work

| Their Design | Our Parallel |
|--------------|-------------|
| PF problem generation via LLM | MCQ distractor generation via LLM (Phase 1a) |
| 5-dimension human-evaluated rubric | 5 metrics: PM, TextSim, EmbedSim (F1) + Validity, Diversity (F2) |
| LLM vs SLM comparison | Our Llama-3.3-70B vs future SLM (Phase 1b) |
| Controlled prompt ablation (identical prompts) | Our 9-condition systematic prompt ablation |
| Human raters + Cohen's d | Our LLM-judge + self-consistency (3-call majority vote) |
| Sweet Spot Calibration (SSC) | Our Validity metric ("wrong but on-pathway?") |
| Multiple Representations (MR) + Open-Endedness (OE) | Our Diversity metric (distinct error types) |
| Prompt engineering as key lever | Our 4 system × 3 instruction × MC-conditioned design |
| Call for SLM fine-tuning | Our next step: fine-tune a 7B model on Eedi distractors |

**Key citation for our thesis:** This paper provides a human-validated PF quality framework and demonstrates that structured prompt ablation + rubric-based evaluation is a publishable methodology in AI & education venues.
