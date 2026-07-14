# Phase 1a — MCQ Distractor Generation: Research Design & Prompt Variants

## Research Questions

| RQ | Question | Independent variable | Dependent variable |
|----|----------|---------------------|-------------------|
| 1 | Does **pedagogical framing** improve distractor quality? | System prompt depth (basic → expert → pedagogical) | Misconception Recovery, Proportional Match |
| 2 | Does **explicit reasoning** (CoT) improve quality? | Instruction strategy (direct → chain-of-thought) | Misconception Recovery, error rationale quality |
| 3 | Does **self-critique** improve quality? | Instruction strategy (direct → self-critique) | Mean quality, failure rate |
| 4 | Does **student simulation** improve quality? | System persona (expert → lookalike) | Plausibility (LLM-judge), distribution alignment |
| 5 | Does **misconception grounding** improve quality? | Strategy (zero-shot → MC conditioned) | Misconception Recovery @k |
| 6 | What is the **upper bound** of pure prompting? | Kitchen sink (pedagogical + CoT + MC conditioned) | All metrics |

Every comparison is a **1-axis ablation** against the standard baseline (expert system + direct instruction + zero-shot).

## Experimental Conditions (9 total)

| # | System | Instruction | Strategy | Tests | Expected finding |
|---|--------|-------------|----------|-------|-----------------|
| 1 | `basic` | `direct` | zero_shot | Lower bound | Calibrates the floor |
| 2 | `expert` | `direct` | zero_shot | **Standard baseline** | All comparisons reference this |
| 3 | `pedagogical` | `direct` | zero_shot | RQ1 | Error taxonomy → better diagnosis |
| 4 | `expert` | `cot` | zero_shot | RQ2 | Explicit reasoning → better rationales |
| 5 | `expert` | `self_critique` | zero_shot | RQ3 | Self-review filters bad distractors |
| 6 | `lookalike` | `direct` | zero_shot | RQ4 | Student simulation feels more authentic |
| 7 | `expert` | `direct` | misccon_names | RQ5 (shallow) | Even listing names helps |
| 8 | `expert` | `direct` | misccon_taxonomy | RQ5 (deep) | Full grounding → causal linking |
| 9 | `pedagogical` | `cot` | misccon_taxonomy | Upper bound | Diminishing returns after taxonomy |

## External Baseline: Feng et al. (2024)

Feng et al. (NAACL 2024 Findings) is the most comparable prior work — same data source (Eedi), same task (generate 3 distractors per MCQ), same metric (Proportional Match). Their best approach (kNN) achieves **38.52% PM**.

We directly match their four approaches:

| Feng approach | Their PM | Our comparable condition | Key difference |
|:---|---:|:---|---|
| **kNN** (retrieve 3 similar questions via SBERT MPNet → few-shot prompt) | **38.52** | `fewshot_rag` strategy (Arctic-embed retrieval) | Different encoder (SBERT MPNet vs Arctic-embed), same idea |
| **CoT** (GPT-4, zero-shot: generate errors → feedback → distractor) | **30.39** | `expert + cot` (condition #4) | Our CoT adds 4-step structured reasoning (not just "generate errors") |
| **RB** (Rule-Based: 444 hand-written error rules → select 3 relevant → generate) | **27.21** | `expert + misccon_taxonomy` (condition #8) | They use 444 rules; we use 2,587 Eedi misconceptions |
| **Random examples** (few-shot with random irrelevant questions) | **23.56** | `expert + direct` (condition #2, our baseline) | Closest proxy for zero-shot on the same metric |

**Proportional Match (PM)** is Feng's primary metric. Per question:
```
PM = (number of generated distractors that match any human distractor) / 3
```
Averaged over all test questions.

**Normalization** (Option B): Raw string match is too strict — Eedi distractors use LaTeX formatting (`\( 3 \times(2+4)-5 \)`) while the LLM outputs plain text (`3 × (2+4) − 5`). Before matching, both sides are normalized:
- Strip LaTeX delimiters `\(...\)`, `\[...\]`
- Normalize math symbols: `\times` → `×`, `\cdot` → `·`, `\div` → `÷`
- Unify whitespace and trim
- Strip extraneous punctuation

This makes PM reflect *math answer similarity* rather than *formatting coincidence*.

**Feng comparison caveat:** Feng uses exact string match (no normalization). We report both variants:
- `PM_normalized` (our primary Family 1 metric — fairer)
- `PM_exact` (for rough Feng comparison — they report ~38.52% for their best system)

**What Feng cannot do** (our contribution): They only measure string-match against human distractors. They lack misconception labels, so they cannot compute Misconception Recovery, causal linking, or diagnostic value. Our Family 2 metrics address the gap identified in both papers.

**Model:** Feng uses GPT-4 (CoT, RB) and gpt-3.5-turbo (kNN). We use Qwen3.5-27B / Apertus-70B. Any PM difference will reflect model capability + prompt quality — we cite Feng numbers as external reference, not direct replication.

### System prompts (4 levels)

**basic** — No domain knowledge:
```
You are a helpful assistant that generates wrong answers for
multiple-choice math questions.
```

**expert** (baseline) — Generic domain expert:
```
You are a mathematics education expert specializing in diagnosing
student misconceptions. Your task is to generate plausible wrong
answers (distractors) for multiple-choice math questions. Each
distractor should reflect a real error that a student might make,
based on common mathematical misconceptions.
```

**pedagogical** (RQ1) — Structured error taxonomy + diagnostic reasoning:
```
You are a mathematics education researcher with 15 years of classroom
experience diagnosing student errors. You have deep knowledge of the
following error categories:

1. PROCEDURAL errors — mistakes in executing a correct procedure
2. CONCEPTUAL errors — misunderstanding the underlying concept
3. FACTUAL errors — incorrect recall of facts
4. STRATEGIC errors — right strategy, wrong problem type

For each distractor you generate, you must:
- Classify it into one of the four error categories
- Explain the step-by-step reasoning path a student would take
- Ensure the distractor is diagnostically useful
```

**lookalike** (RQ4) — Simulates student thought process (Parikh 2025):
```
You are simulating the thought process of a real middle-school student.
Your job is NOT to be correct — it is to make the same kinds of
mistakes that real students make every day in math class.

Think about what WRONG answers feel intuitively correct to someone who:
- Recently learned the topic but hasn't practiced enough
- Mixes up similar-looking operations
- Remembers the right formula but plugs numbers in the wrong order
- Gets the right answer but for a slightly different question
- Follows a "shortcut" that works 80% of the time but fails here

Your distractors should feel authentic — a teacher should look at
your wrong answers and say "Yes, I've seen students make exactly
that mistake."
```

### Instruction strategies (3 levels)

**direct** (baseline) — Generate immediately:
```
Generate {n} plausible wrong distractors for the following math question.
[question + answer]

For each distractor, provide:
- "text": The wrong answer
- "target_misconception": The misconception name
- "error_rationale": 1-sentence explanation
```

**chain-of-thought** (RQ2) — Think before generating (Feng 2024):
```
STEP 1: Identify the core mathematical concept being tested.
STEP 2: List 5-8 common errors students make on this type of problem.
STEP 3: For each error, compute what WRONG answer that error would produce.
STEP 4: Select the {n} most PLAUSIBLE wrong answers.

Then output: text, target_misconception, error_rationale, error_category.
```

**self-critique** (RQ3) — Generate → review → revise (Madaan 2023):
```
PHASE 1 — Generate: Draft {n} distractors.
PHASE 2 — Self-Critique: Review each against 4 checks:
  1. Would a real student pick this? (plausibility)
  2. Does this diagnostic a specific misconception? (diagnostic value)
  3. Is this too easy to eliminate? (discrimination)
  4. Are the distractors diverse? (diversity)
PHASE 3 — Revise: Replace any that failed.

Output with: text, target_misconception, error_rationale, quality_notes.
```

### Misconception conditioning (2 depths)

**names** (RQ5a) — Inject misconception labels:
```
Target these known student misconceptions:
  - Confuses addition with multiplication
  - Forgets order of operations
  - Incorrectly applies BIDMAS

Each distractor should be designed so that a student holding that
misconception would select it.
```

**taxonomy** (RQ5b) — Full grounding (thesis core mechanism):
```
Below is a taxonomy of REAL misconceptions documented in large-scale
student assessments. For each misconception, a real student would
produce a specific wrong answer. Your task is to compute what that
wrong answer WOULD BE for this question.

  - Confuses addition with multiplication
  - Forgets order of operations
  - ...

IMPORTANT: The wrong answer MUST be causally linked to the
misconception. Do NOT assign misconceptions to arbitrary wrong numbers.
```

## Evaluation Protocol

Each condition is run on N test questions (stratified by subject from Eedi held-out set), 3 stochastic runs, temperature=0.7. Metrics:

| Family | Metric | Computation |
|--------|--------|-------------|
| F1 | Proportional Match (normalized) | **Primary.** String match after LaTeX normalization (strip `\(...\)`, unify `\times`→`×`, etc.) |
| F1 | Proportional Match (exact) | Raw string match — for rough Feng 2024 comparison |
| F1 | Text similarity | ROUGE-L, edit distance between normalized expressions |
| F1 | Embedding similarity | Arctic-embed cosine between generated and human distractor |
| F2 | Misconception Recovery @k | LLM maps distractor → closest misconception → recall vs ground truth |
| F2 | Self-label fidelity | Generator's self-declared misconception vs independent classifier |
| F2 | Distractor validity | Symbolic solver: wrong but on-pathway |
| F2 | Intra-question diversity | Embedding spread across k distractors |

Model assignment (anti-leakage):
- **Generator**: Qwen3.5-27B (or Apertus-70B for structured output)
- **Judge/Classifier**: Apertus-70B (≠ generator)
- **Embedder**: Arctic-embed-l-v2.0 (≠ retrieval encoder, held out)

## References

- Feng et al. 2024 — RAG + error rationales for math MCQ distractor generation
- Parikh et al. 2025 (LookAlike) — grounding distractors in real student errors
- Alhazmi et al. 2024 — survey of distractor generation methods
- Madaan et al. 2023 (Self-Refine) — generate-critique-revise loop
- Puech et al. 2025 (StratL) — pedagogical steering with intent labels
- Zheng et al. 2023 — LLM-as-judge, judge ≠ generator to avoid self-preference
