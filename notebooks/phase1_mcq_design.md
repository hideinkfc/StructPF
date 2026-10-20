# Phase 1a — MCQ Distractor Generation: Research Design & Prompt Variants

## Current Status And Evidence Boundary

This note describes the current 11-condition design, not the older nine-condition evaluation in
notebook 02. The latest saved structured run has 200 frozen questions, three repeats per condition,
6,600 question-runs and 19,800 distractors. Generation uses Azure GPT-4.1-mini routing and retrieval
uses `text-embedding-3-small-EU`; environment overrides can change future deployments.

Read the [generation overview](../docs/mcq/MCQ_GENERATION_OVERVIEW.md) for the schema and runner,
and the [evaluation overview](../docs/mcq/MCQ_EVALUATION_OVERVIEW.md) for artifact-backed results
and coverage. MCQs supply candidate error pathways for Productive Failure (PF) design. These
software and model judgments do not establish real student errors, behaviorally distinct approaches,
or learning. The [PF pipeline](../docs/pf-generation/PF_PIPELINE.md) records downstream work separately.

## Research Questions

| RQ | Question | Independent variable | Dependent variable |
|----|----------|---------------------|-------------------|
| 1 | Does **pedagogical framing** change distractor quality? | System prompt (basic / expert / pedagogical) | Incorrectness, plausibility, optional coherence/diversity; secondary PM |
| 2 | Does **explicit reasoning** (CoT, chain-of-thought guidance) help? | Direct / CoT instruction | Same separate measures; no assumed rationale-quality score |
| 3 | Does **self-critique** help? | Direct / draft-critique-revise instruction | Same measures plus recorded generation failures |
| 4 | Does a **student-like persona** help? | Expert / lookalike system role | Blinded 0--2 plausibility; not real-student distribution alignment |
| 5 | Does **misconception grounding** help? | Random labels / retrieved names / retrieved causal linking | Plausibility and optional pathway coherence/diversity; secondary PM |
| 6 | Does **combined guidance** help? | Pedagogical + CoT + causal grounding | Same measures; a combined condition, not a proven upper bound |
| 7 | Does **question retrieval** help? | Zero-shot / three retrieved training examples | Secondary Eedi PM plus plausibility and optional path measures |

The baseline is `02_expert_direct` (expert system + direct instruction + zero-shot). Conditions
1, 3--6, 7, 8, and 11 isolate one main intervention against it. Compare 9 against 8 to isolate causal
linking; condition 10 combines several changes and is **not** a one-axis ablation or upper bound.

## Experimental Conditions (11 total)

| # | System | Instruction | Strategy | Tests | Expected finding |
|---|--------|-------------|----------|-------|-----------------|
| 1 | `basic` | `direct` | zero_shot | Lower bound | Calibrates the floor |
| 2 | `expert` | `direct` | zero_shot | **Standard baseline** | All comparisons reference this |
| 3 | `pedagogical` | `direct` | zero_shot | RQ1 | Error taxonomy → better diagnosis |
| 4 | `expert` | `cot` | zero_shot | RQ2 | Explicit reasoning → better rationales |
| 5 | `expert` | `self_critique` | zero_shot | RQ3 | Self-review filters bad distractors |
| 6 | `lookalike` | `direct` | zero_shot | RQ4 | Student-like role may improve plausibility; this is not independent student simulation |
| 7 | `expert` | `direct` | misconception_random | Random misconception control | Any benefit must exceed arbitrary labels |
| 8 | `expert` | `direct` | misconception_conditioned + names | RQ5 (retrieved labels) | Semantic candidate labels improve grounding |
| 9 | `expert` | `direct` | misconception_conditioned + causal | RQ5 (causal linking) | Explicit answer-to-misconception linking improves validity |
| 10 | `pedagogical` | `cot` | misconception_conditioned + causal | RQ6, combined guidance | Tests several changes jointly; no assumed upper bound |
| 11 | `expert` | `direct` | fewshot_rag | Feng-style kNN analogue | Retrieved Eedi examples improve alignment |

The misconception candidates in conditions 8--10 are retrieved from the Eedi misconception
embedding index using the question stem, `SubjectName`, and `ConstructName`. Condition 7 is an
explicit control that samples the full misconception bank at random. The Eedi mapping contains
names but no human-authored descriptions, so condition 9 is a causal-linking prompt rather than a
full taxonomy-depth condition. Gold misconception IDs are never sent to the generator; when they
are available in the held-out record, `gold_in_retrieved` is logged after generation.
The "Expected finding" column records hypotheses, not confirmed effects. The saved evaluation shows
different descriptive strengths and incomplete answer-check coverage, not a universally best condition.

## External Baseline: Feng et al. (2024)

Feng et al. (NAACL 2024 Findings) is a relevant historical comparator: Eedi data, three distractors
per MCQ, and Proportional Match. The previously recorded best kNN result is **38.52% PM**;
the paper-level numbers below are retained as literature references, not reverified local results.

These are conceptual comparisons, not four direct replications:

| Feng approach | Their PM | Our comparable condition | Key difference |
|:---|---:|:---|---|
| **kNN** (retrieve 3 similar questions via SBERT MPNet → few-shot prompt) | **38.52** | `11_fewshot_rag` (Azure `text-embedding-3-small-EU`) | Different encoder, same idea; GPT-4.1-mini is held constant with the main baseline |
| **CoT** (GPT-4, zero-shot: generate errors → feedback → distractor) | **30.39** | `expert + cot` (condition #4) | Our CoT adds 4-step structured reasoning (not just "generate errors") |
| **RB** (Rule-Based: 444 hand-written error rules → select 3 relevant → generate) | **27.21** | No direct replication; condition #9 is only a causal-prompt analogue | They use executable rules; we use 2,587 retrieved Eedi misconception labels |
| **Random examples** (few-shot with random irrelevant questions) | **23.56** | No direct replication; condition #7 is a random misconception-label control | Different intervention, so it must not be presented as Feng's random-example result |

**Proportional Match (PM)** is secondary reference alignment in this project. For a complete
three-distractor output, the current implementation uses:
```
PM = (maximum one-to-one matches to Eedi distractors) / 3
```
Averaged over question-runs. A human option and a generated option can each be matched at most once;
duplicating an answer cannot repeatedly collect credit for one Eedi option.

**Normalization** (Option B): Raw string match is too strict — Eedi distractors use LaTeX formatting (`\( 3 \times(2+4)-5 \)`) while the LLM outputs plain text (`3 × (2+4) − 5`). Before matching, both sides are normalized:
- Strip LaTeX delimiters `\(...\)`, `\[...\]`
- Normalize math symbols: `\times` → `×`, `\cdot` → `·`, `\div` → `÷`
- Unify whitespace and trim
- Strip extraneous punctuation

Normalized PM reduces formatting differences; it does not establish general mathematical
equivalence. Typed PM also checks supported numeric values/canonical answer keys. Optional LLM PM
judges contextual equivalence separately and is still a model estimate.

**Feng comparison caveat:** the literature PM numbers above are historical external references,
not comparable controlled results. The implementation reports `PM_raw` (trimmed raw matching),
`PM_normalized`, and `PM_typed`; `PM_exact` is not the current aggregate field name. Current
LLM-equivalence reporting is `PM_llm`. Verify the original paper's metric and setup before quoting a
direct numerical comparison; normalized or model-judged PM is not its reported exact-match score.

**Different scope:** Eedi matching asks whether generated answers resemble reference options. This
project separately estimates plausibility and checks supplied error pathways. These additional
judgments do not by themselves establish diagnostic value or a new validated behavioral instrument.

**Model:** the historical comparison describes GPT-4 (CoT, RB) and gpt-3.5-turbo (kNN).
The current grid uses Azure GPT-4.1-mini for generation and the current compact judges, and Azure
`text-embedding-3-small-EU` for retrieval. Data, model, encoder, prompt and matching differences all
confound an external PM comparison. Literature figures have not been reverified in this local audit.

### System prompts (4 levels)

The snippets below summarize prompt intent, not the complete runtime messages. The executable
source is [mcq.yaml](../src/generation/prompts/mcq.yaml); the generator appends output requirements
and optional structured-path instructions. Prompt-variant extras such as `error_category` and
`quality_notes` are allowed, but are not required core schema fields.

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

### Misconception conditioning and retrieval controls

**random** (control) — Sample five labels uniformly from the full Eedi misconception bank. This
tests whether any labels in the prompt help, independently of question relevance.

**names** (RQ5a) — Inject semantically retrieved misconception labels:
```
Target these known student misconceptions:
  - Confuses addition with multiplication
  - Forgets order of operations
  - Incorrectly applies BIDMAS

Each distractor should be designed so that a student holding that
misconception would select it.
```

**causal** (RQ5b) — Ask the model to compute a question-specific wrong answer and keep it causally
linked to a retrieved label:
```
The candidates are labels retrieved from the Eedi misconception bank. They do not include full
descriptions, so the prompt must not be interpreted as a richer human-authored taxonomy.

  - Confuses addition with multiplication
  - Forgets order of operations
  - ...

IMPORTANT: The wrong answer MUST be causally linked to the
misconception. Do NOT assign misconceptions to arbitrary wrong numbers.
```

## Evaluation Protocol

The saved full run uses the frozen `data/eedi/test_set_200.json` (200 randomly selected held-out
records), three stochastic repeats and generation temperature 0.7. This is not a newly stratified
sample. Conditions 7--10 record candidate-label provenance; condition 7 samples random labels.
The structured runner uses eight question workers and runs conditions sequentially.

| Family | Metric | Computation |
|--------|--------|-------------|
| Answer check | Incorrectness | Deterministic supported numeric/simple-equation equivalence; unknown and unusable kept separate |
| F2 | Student plausibility | Blinded GPT-4.1-mini score 0--2; keep mean and use `>= 1` only as broad screening |
| F2, optional | Path coherence | Execute supplied `faulty_step` / `reasoning_steps` without repairing the error and compare with `text` |
| F2, optional | Pathway diversity | Pairwise faulty-step judgments only among incorrect, plausible, coherent candidates; fewer than two is unavailable |
| Secondary alignment | PM raw / normalized / typed | Maximum one-to-one matching to Eedi; duplicate outputs do not inflate matches |
| Secondary, experimental | LLM PM | Optional contextual answer-equivalence judgments, followed by one-to-one matching |

ROUGE/edit/embedding similarity, misconception recovery, self-label fidelity, old binary validity
and one-shot diversity belong to historical evaluation code/artifacts, not this active compact
metric set. Behavioral functional diversity is inactive; its
[rule-level calibration history](../docs/mcq/functional-diversity/MCQ_FUNCTIONAL_DIVERSITY_MEASUREMENT.md)
is not evidence from independently frozen student profiles.

Model assignment and limits:
- **Generator**: Azure GPT-4.1-mini
- **Judge**: Azure GPT-4.1-mini, separate calls; plausibility sees no generator explanations
- **Embedder**: Azure `text-embedding-3-small-EU`

Separate calls are not separate model families and do not remove shared-model bias. The full
artifact has 62--63% unknown answers per condition and conditional pathway diversity on only
151--193 of 600 question-runs per condition. These coverage limits must accompany result claims.

Basic distractors require `text`, `target_misconception`, and `error_rationale`. Optional structured
mode adds `faulty_step` and ordered `reasoning_steps`; the structured runner additionally enforces
three items and non-blank paths. Do not add `predicted_answer` or `student_calculation` from older
smoke/derivation artifacts.

Offline entry points (run from the repository root):

```bash
./.venv/bin/python scripts/run_phase1_structured_generation.py --help
./.venv/bin/python scripts/evaluate_phase1_new_metrics.py --help
```

See the linked overviews for future model-calling commands with explicit fresh output paths.
`run_phase1_mcq.py` still combines basic generation with historical metrics; it supplies the current
condition definitions but is not the compact structured evaluation runner.

## References

- Feng et al. 2024 — RAG + error rationales for math MCQ distractor generation
- Parikh et al. 2025 (LookAlike) — grounding distractors in real student errors
- Alhazmi et al. 2024 — survey of distractor generation methods
- Madaan et al. 2023 (Self-Refine) — generate-critique-revise loop
- Puech et al. 2025 (StratL) — pedagogical steering with intent labels
- Zheng et al. 2023 — LLM-as-judge and self-preference risks; the current routing does not use distinct generator/judge model families
