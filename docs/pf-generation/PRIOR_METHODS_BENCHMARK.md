# Prior-Methods Benchmark: Can an LLM Generate Real Student Methods from a Hidden Concept?

> Status: **historical v3 and v5 runs complete; preliminary model-judged evidence.**
> This file records the original result and the resulting redesign, not the current
> generation protocol. Current D1 holds curated expert lists out; current downstream
> generation uses design briefs, checked data and writing. Read
> [PF_PIPELINE.md](PF_PIPELINE.md) for implementation status and remaining PF-quality gaps.
> Companion to [PF_PIPELINE.md](PF_PIPELINE.md) (the D1
> "Anticipate" step this benchmark investigates) and to
> [MCQ_EVALUATION_OVERVIEW.md](../mcq/MCQ_EVALUATION_OVERVIEW.md) (the judge patterns reused here).
>
> Results: [experiments/results/prior_methods_benchmark/full_v3/analysis.json](../../experiments/results/prior_methods_benchmark/full_v3/analysis.json).

## 1. Research question

The PF pipeline starts from a hidden concept and proposes **prior resources** and
possible approaches (D1). Whether students actually use them is a separate
behavioral question. One candidate source investigated here was LLM generation:

```text
hidden concept  →  LLM generates candidate prior methods  →  ranked  →  human review
```

**Question:** given only a hidden concept, can the LLM produce a list of prior methods that
is both *plausible-sounding* and *real* — where "real" means it matches errors that real
students actually made, at rates real students actually made them?

This is the Liu-style difficulty applied to our pipeline: not "execute a stated wrong
procedure" (already calibrated: 94.4% rule-following, see
[MCQ_FUNCTIONAL_DIVERSITY_MEASUREMENT.md](../mcq/functional-diversity/MCQ_FUNCTIONAL_DIVERSITY_MEASUREMENT.md))
but "infer the wrong behavior a misconception implies, unprompted."

### 1.1 The Liu et al. (2023) anchor — verified findings

The reference is Liu, Sonkar, Wang, Woodhead & Baraniuk, *"Novice Learner and Expert
Tutor: Evaluating Math Reasoning Abilities of Large Language Models with Misconceptions"*
(arXiv:2310.02439; note Woodhead = Eedi, Wang = Eedi dataset author — same ecosystem as
our data). Their **novice-learner experiment** is the closest prior work:

- **Task:** given (question, misconception label, 4 answer options), pick the specific
  incorrect option the misconception implies. One call per (question, misconception) pair —
  selection, not generation.
- **Prompt:** zero-shot persona — *"You are a student with some math misconceptions...
  answer based on the given misconception. DO NOT just give the correct answer!"*
- **Results (Table 2):** GPT-4 picks the misconception-implied option at **53.4%** without
  explanations and **61.7%** with explanations; GPT-3.5 at 37.1%/42.5%. Few-shot with
  *random* examples hurt (60.0%); few-shot with *same-misconception* examples helped
  (67.9%, on a 152-item subset). Reference point: GPT-4 answers the same questions
  *correctly* at 94.8%.

**Our interpretation (not theirs):**

1. The ~33-point gap between answering correctly and selecting the implied wrong answer
   suggests a **belief → procedure translation** difficulty: the misconception label
   describes a belief, and the model must infer an executable wrong procedure, run it, and
   match it to an option. The result does not isolate that inference from execution,
   matching, or the pull toward the correct answer.
2. The few-shot pattern (random hurts, same-misconception helps) suggests the capability is
   **recognition/replay of seen error instantiations**, not simulation of unseen ones.
3. Their design **conflates this with correctness pull**: the 4 options including the
   correct answer are visible during selection. Our own calibration measured that pull
   directly — rule-following dropped from 94.4% (no options) to 68.3% (options visible,
   original prompt). Some of Liu's 62% is likely this drag, not translation failure.
4. **Liu et al. provide no method for generating prior methods** — they never asked for
   generation. Our benchmark fills that methodological gap: it tests whether overgenerate-
   then-verify routes around the belief→procedure bottleneck, and it characterizes *how*
   generation fails (paraphrase padding, correct-method leakage), which a selection task
   cannot see.

**Difficulty ladder this establishes** (each cell is one experiment):

| Task | Input | Result | Source |
|---|---|---|---|
| Execute a stated wrong procedure | question + explicit wrong rule | 94.4% (GPT-4.1-mini) | our Test 1 calibration |
| Select the misconception-implied option | question + misconception + options | 61.7% (GPT-4, 2023) | Liu et al. |
| **Generate the prior-method space** | **concept only — no question, no options, no procedure** | **unknown — this benchmark** | **this work** |

## 2. Historical intention and goal

The result sets the role of LLM generation (source C) in the D1 candidate catalog:

| Outcome | Role of source C in the pipeline |
|---|---|
| Recall and precision both pass | C is a valid primary source; human review is a safety net |
| Recall passes, precision middling | C is a recall source only; ranking + human review are load-bearing (the current overgenerate-then-rank design is validated as-is) |
| Recall fails | C cannot supply D1 methods; LLM is demoted to phrasing methods from sources A (literature) and B (Eedi) |
| Plausibility high but recall fails | Fluent confabulation: plausibility scores cannot certify method lists. Reported prominently as a warning for any judge-based filtering |

A secondary goal is a model-size datum: GPT-4.1-mini vs GPT-4.1 on the same task, extending
the calibration finding that mini followed procedural instructions *better* than full 4.1
(94.4% vs 81.1%).

### 2.1 Historical v5 curriculum-resource evaluation

The error-level protocol below is retained as a historical benchmark of concept-to-error
generation. The next benchmark used the **v5 curriculum-resource design** instead:

1. inventory tools a student was taught before the hidden concept;
2. apply each tool to the new task type and describe how it falls short.

Its reference is the curated `prior_knowledge_required` and
`expected_student_solutions`/`expected_student_rsms` lists in
[data/pf_exercises](../../data/pf_exercises), not Eedi misconception labels. The v5 coverage
judge used **expert method -> any generated method** so reference coverage was measured
directly; it runs with GPT-5.6-luna for both coverage and shortcoming-fitness judgments.
The implementation is [run_curriculum_methods.py](../../scripts/prior_methods/run_curriculum_methods.py)
and [eval_curriculum_v5.py](../../scripts/prior_methods/eval_curriculum_v5.py).

### 2.2 Preliminary full v5 run (saved historical evidence)

The saved full v5 run generated one curriculum inventory for all 10 frozen concepts with
four generator models. It produced 57 methods for GPT-4.1, 63 for GPT-4.1-mini, 74 for
GPT-5.4, and 68 for GPT-5.6-luna; Luna had one recorded step-2 conversion failure.
GPT-5.6-luna judged 262 generated methods for shortcoming fitness with zero parse failures.

Expert coverage is measurable only for the three expert-anchored concepts (33 expert
method entries in total). These are closest-concept comparisons, not matched
student-response experiments; for example, `c4_partwhole` is a ratio concept
compared with Kapur's average-speed method list:

| Generator | c4 part-whole | x_avgfreq | x_range | Overall expert entries covered |
|---|---:|---:|---:|---:|
| GPT-4.1 | 1/9 (0.111) | 1/12 (0.083) | 1/12 (0.083) | 3/33 |
| GPT-4.1-mini | 2/9 (0.222) | 4/12 (0.333) | 1/12 (0.083) | 7/33 |
| GPT-5.4 | 2/9 (0.222) | 4/12 (0.333) | 1/12 (0.083) | 7/33 |
| GPT-5.6-luna | 0/9 (0.000) | 2/12 (0.167) | 1/12 (0.083) | 3/33 |

These are **coverage indications, not validated quality scores**: the expert lists are
small and curated from published PF studies, and the coverage decision is still an LLM
judgment. Fitness was correct for 49/57 GPT-4.1 methods (0.860), 56/63 GPT-4.1-mini
methods (0.889), 65/74 GPT-5.4 methods (0.878), and 66/68 GPT-5.6-luna methods (0.971);
these rates are also preliminary because the fitness judge is not independent human
ground truth.

Run artifacts: [full_v5_all_concepts_v2](../../experiments/results/prior_methods_benchmark/full_v5_all_concepts_v2)
and [v5_eval_full_luna_v2.json](../../experiments/results/prior_methods_benchmark/v5_eval_full_luna_v2.json).

## 3. Historical error-benchmark scope rule

**A concept enters the benchmark only if real student errors with pick rates exist for it in
the scraped data.** Unanchored concepts (PF concepts 1, 2, 3, 6) are excluded — on those,
"real" reduces to the plausibility judge plus human review, which cannot validate the
generator and would only restate the judge's own opinion.

### 3.1 Construct note: prior methods are not misconceptions

The ground truth is Eedi misconception data, but D1 needs *prior methods* — the procedures
students reach for with existing knowledge. These are not the same set:

| Kind of prior method | Example (concept 5, comparing mixtures) | In Eedi ground truth? |
|---|---|---|
| Documented misconception | "500ml for 75p is best because 75 ÷ 5 = 15p sounds cheapest" | Yes — error rule + pick rate |
| Correct-but-insufficient strategy | "Compare the raw amounts; more ml is better" | **No** — the method is not wrong in general, so no quiz flags it; students who used it picked a wrong option, but the teacher explanation computes the unit rate instead of naming the strategy |
| Confabulation | Fluent-sounding method no student uses | Correctly absent |

Consequences, owned by this benchmark:

1. **Naive matching would punish the most valuable candidates.** A generated strategy like
   "compare raw totals" matches no error rule and would count against precision — yet it is
   real, dominant student behavior, and exactly what a PF trap is built to break. Matching
   therefore uses a three-way verdict (§5), and precision is computed as a non-confabulation
   rate, not as an Eedi-match rate.
2. **Recall measures only the misconception-shaped subset** of prior methods. It is reported
   as *error-recall* (§6) and must not be read as method coverage. A generated list can pass
   error-recall while containing zero strategies, which would be useless for PF design —
   strategy coverage requires separate literature/task comparison and human review,
   not this benchmark's error-recall alone.
3. **Selection is not production.** Eedi pick rates measure which wrong answer was *chosen*
   on a closed item; PF needs which methods students *produce* on an open task. Pick rates
   are a proxy for method prevalence, and are treated as such.

## 4. Benchmark data

### Core set — pipeline-relevant concepts (n = 2)

From [data/pf_hidden_concepts.json](../../data/pf_hidden_concepts.json), the two concepts
with real-data anchors:

| # | Hidden concept | Anchor quiz | Ground truth |
|---|---|---|---|
| 4 | Part-to-part vs part-to-whole ("5:3 means 5/8 of the whole, not 5/3") | `gg81` Representation of ratio, Q4/Q5 | **Pick rates only** — gg81 explanation text is OCR-corrupted (explanations reference shapes from other questions); percentages are valid |
| 5 | Comparing mixtures needs a common basis (unit rates, not raw amounts) | `e92o` Best buy problems | Clean: 15 misconception options with teacher explanations + real pick rates |

### Extended set — method-validation concepts (n = 8)

One concept per clean scraped quiz in [data/eedi_scraped/](../../data/eedi_scraped), giving
statistical mass so the verdict does not rest on n = 2. Selection rule: ≥ 18 real
(non-"No explanation") misconception explanations, clean text, school-math topic. Frozen
list (verified against the scraped data; every entry has 20 clean explanations):

| Concept ID | Hidden concept (prompt text) | Quiz |
|---|---|---|
| `x_estimation` | Overestimating requires rounding at least one number up and none down | `emnt` Estimation 3 |
| `x_orderfrac` | Ordering fractions requires a common basis (denominator or decimal), not numerator size | `e901` Order fractions 3 |
| `x_brackets` | Expanding a(b + c) requires multiplying every inside term by the outside factor | `emlb` Expand single brackets 3 |
| `x_range` | The range measures spread as max − min, not the gap between two listed numbers | `gfk1` Find and interpret the range |
| `x_revperc` | Reversing a p% change needs division by (1 ± p/100), not subtracting p% of the new value | `fso6` Reverse percentages |
| `x_onestepeq` | Solving one-step equations needs the inverse operation applied to both sides | `emcv` Solve one step linear equations 2 |
| `x_decimals` | Adding decimals requires aligning place value (decimal points), not right-aligning digits | `emkd` Written addition/subtraction of decimals |
| `x_avgfreq` | The mean from a frequency table weights values by frequency; it is not the mean of the value column | `emo8` Averages and range from a frequency table 3 |

Reserve pool (swap in listed order if a pre-run check fails, and record the swap): `e900`
Estimation 2, `el8s` Bounds of error, `emn0` Negative numbers, `emrc` Inequalities, `emt1`
Factors and multiples, then the remaining clean quizzes. Excluded: `fsqj` (9/20 options have
`No explanation`), `gg81` and `e92o` (already core anchors).

**Total: 10 concepts.** Each concept's ground-truth error set = all misconception options of
its anchor questions, each carrying {option text, explanation where clean, pick rate}. The
aggregated view is
[data/eedi_scraped/_skill_bank.json](../../data/eedi_scraped/_skill_bank.json)
(88 skills, 1,395 error rules).

### Exclusions

- Options with `No explanation` (e.g., `e92o` Q2) are excluded from *matching* but their
  pick rates still count for prevalence.
- `gg81` explanations are excluded from matching entirely (corrupted); only its pick rates
  are used.

## 5. Historical v3 protocol

> The protocol in this section describes the original Eedi-anchored error-generation
> benchmark. It is not the later v5 resource protocol described in §2.1 or the
> current teacher-facing recommender.

```text
Per concept (core + extended, 10 total):
  Generate 10 candidate prior methods × 3 repeats, prompt style = 03_pedagogical_direct
    (the best current plausibility condition from Phase 1a; do not claim it dominates 01/02)
  Each candidate: {method_name, student_thinking, worked_example}
    worked_example = the method applied to concrete numbers.
    Required because (a) matching against real error rules is far more reliable on a
    computed example than on prose, and (b) it pre-loads exactly the artifact the D4
    verification step needs. Accepted risk: more rope to be wrong may lower plausibility.

Generator input — the model receives ONLY:
  Grade level, topic, hidden concept text, and the task: list 10 prior methods a student
  who has NOT yet learned this concept would reach for, including wrong methods
  (misconceptions) AND naive but reasonable strategies that fall short.
  No misconception labels, no Eedi content, no example methods in the prompt (leakage).

Models:
  Generator: GPT-4.1-mini (main arm — the pipeline's model) AND GPT-4.1 (reference arm)
  Plausibility judge: GPT-4.1-mini, blinded (no source label, no rationale), 0–2 scale,
    same judge pattern as Phase 1a so scores stay comparable
  Matcher (candidate ↔ real error rule): GPT-4.1-mini, LLM equivalence judgment,
    same machinery as LLM-verified PM but method↔method instead of answer↔answer

Matching is a three-way verdict per candidate, not a binary match:
  (a) matches_documented_error   — equivalent to a real Eedi error rule for this concept
  (b) valid_undocumented_strategy — a correct-but-insufficient or naive-default method
      (no error rule exists because the method is not an error; see §3.1)
  (c) confabulation              — fluent text describing no real student behavior
Class (a) is judged by the matcher against Eedi. Classes (b) and (c) cannot be decided by
Eedi matching; they go to the human spot-check (§8.1) and, where available, literature
ground truth (Loibl/Puech RSM lists for the anchored concepts).

Matching input note: candidates are matched against the real error rules for the concept's
quiz (explanation text + the wrong option text + the question text as context).
```

Standard run params: `temperature=0.7`, `max_tokens` sized for 10 methods, `workers=10`.
Read results from saved JSON artifacts, not terminal scrollback. Never overwrite historical
result files; distinct `--output` per run.

The original estimate incorrectly counted 600 generated methods as 600 generation
calls and therefore estimated approximately 1,800 total calls. Generation returns
ten methods per list: the implemented v3 run used 60 generation calls, 600
plausibility judgments and 577 matching judgments (§12).

Output layout: `experiments/results/prior_methods_benchmark/<date>/`, new folder per run.

## 6. Historical planned metrics (changes recorded in §12)

Three numbers, each answering a distinct claim:

| Metric | Definition | Question it answers |
|---|---|---|
| **Error-recall @ dominant errors** | Fraction of real error rules with pick rate ≥ 10% that are covered by at least one generated method | Does the LLM surface the documented errors most students actually make? (Misconception-shaped subset only — §3.1) |
| **Non-confabulation rate** | Fraction of generated candidates in verdict class (a) or (b) — i.e., 1 − confabulation rate | Is the LLM inventing fluent non-methods? |
| **Plausibility (0–2)** | Blinded judge mean over candidates | Does the output *sound* real? (cannot certify reality) |

Error-recall is the headline metric for the misconception-shaped part of D1: the worst case
for a PF designer is missing the documented error most students will bring. The
non-confabulation rate is second — the human review gate can absorb some false positives,
but each costs reviewer time. Class (b) candidates are additionally reported **as their own
count**, because a generator that produces many valid strategies is more useful for PF
design than one that only mirrors Eedi. Plausibility is reported but never interpreted as
evidence of reality.

Report per model (mini / 4.1) and per concept set (core / extended).

## 7. Historical pre-run decision thresholds

Written before any generation call:

| Condition | Verdict |
|---|---|
| Error-recall ≥ 0.6 **and** non-confabulation ≥ 0.7 **and** plausibility ≥ 1.4 | C is a valid primary D1 source (for the misconception-shaped subset); review gate is a safety net |
| Error-recall ≥ 0.6 **and** 0.4 ≤ non-confabulation < 0.7 | C is recall-only; ranking + human review are load-bearing |
| Error-recall < 0.6 | C cannot supply D1 error methods; demote LLM to phrasing |
| Plausibility ≥ 1.4 **and** error-recall < 0.6 | Fluent confabulation — plausibility cannot certify method lists; report as a warning |

The plausibility bar (≥ 1.4) is anchored to the Phase 1a direct-condition mean (1.43–1.46).
The recall bar (0.6) matches the known-good calibration boundary used in the functional
diversity tests. No threshold is set on class (b) strategy counts — there is no ground truth
to calibrate one against; they are reported descriptively.

## 8. Known limitations

0. **Heuristic layer not covered (historical v5 limitation).** The curriculum-resource generation (v5)
   recovers topic tools (mean, range, frequency) well, but on c4 it misses general
   problem-solving heuristics the expert lists rely on (draw a diagram, trial-and-error,
   make a table, systematic listing). Decision: **not fixed in this benchmark** — it is one
   concept (Kapur's bike task, the most ill-structured of the set), the other expert tasks
   were treated as topic-tool concepts in that redesign. That decision did not
   validate inventory completeness, nor establish that a human gate caught the
   missing strategies. Current PF design still needs qualitative, diagrammatic
   and algebraic approaches considered where relevant; generated resource labels
   are not evidence of student approach diversity.

1. **Self-agreement.** Generator, judge, and matcher are the same model family. Mitigation:
   matching ground truth is human (Eedi teacher explanations), so the matcher only judges
   equivalence, not quality. **Hand-check ~50 candidates across all three verdict classes**
   (§5), not just class (a) matches: the (b)/(c) boundary — real strategy vs confabulation —
   requires independent validation. This was a proposed check, not reported
   completed human validation.
   Report agreement per class.
1b. **Construct gap (see §3.1).** The benchmark compares the misconception-shaped subset of
   D1. The implemented v3 run dropped non-confabulation (§12), so it does not
   independently bound the confabulation rate. It cannot measure coverage of
   correct-but-insufficient strategies on its Eedi tasks. Kapur's observed methods
   provide a task-specific behavioral anchor, not a representative reference for
   this ten-concept set. Selection ≠ production (§3.1.3) compounds this: even class (a) recall
   is recall of *chosen* answers, a proxy for produced methods.

### 8.1 Why this is still enough — and what closes the remaining gap

Candidate strategy ground truths considered:

| Source | What it gives | Verdict |
|---|---|---|
| Loibl/Puech RSM data (mean 2.6 RSMs per task) | Real student *production* data on open PF tasks — the actual construct | Best available but small, mostly data-comparison tasks, hand-extraction needed; kept as optional validation paragraph, not required |
| Kapur/Loibl/Kerrigan expert task analyses (`data/pf_exercises`; historical inventory described as 15 exercises) | Curated task-level method references, with source-specific anticipated/observed provenance | **Adopted as cheap extension** (see below) |
| Phase 2 simulator output | Methods that emerge from simulated students | **Rejected as validation** — circular: it would validate the generator with the thing the generator feeds. Usable only as a consistency check |
| Bug-catalog literature (Hart, VanLehn) | Documented strategies with classroom frequencies | Real but old domains, thin on ratios; background only |
| Eedi explanation text mining | Teacher explanations often describe the *strategy*, not just the error | Free (450 explanations in hand); folded into the matching step as context, not a separate tier |

**Cheap extension (adopted):** hand-extract the anticipated-method lists from the then-listed expert
PF exercises in [data/pf_exercises](../../data/pf_exercises) (most state them in design
notes), and check generated candidates against those lists on the closest-matching concepts.
~1–2 hours of manual work, no API budget, converts the strategy gap from "unmeasurable" to
"spot-checked against expert anticipation."

The original 15-exercise inventory is not a current corpus count. The directory
now contains 16 historical curated records plus a separate 15-record full
StratL import with overlaps; the imported tasks do not carry expert annotations.
See [the exercise README](../../data/pf_exercises/README.md) for current source
boundaries rather than treating all YAML records as independent expert-method evidence.

**Why the benchmark suffices for the pipeline decision anyway:** the decision is *can C be
trusted, and with how much review* — not *is C complete*. Sources A (literature) and B
(Eedi) exist precisely to cover what C misses, so C was never required to be complete, only
non-garbage. Error-recall + confabulation + plausibility answer exactly that.
This was the original rationale. The completed run dropped non-confabulation
as non-independent (§12), and neither remaining metric certifies method realism
or downstream PF quality.
2. **Core set is small (n = 2).** The extended set carries the statistical weight; the core
   set answers the pipeline-specific question. A split verdict (extended passes, core fails)
   means method generation works generally but not for ratio/proportion concepts — itself a
   reportable finding.
3. **Pick-rate threshold.** The ≥10% prevalence cutoff for "dominant" errors is a design
   choice; real errors below it exist but matter less for D1. Report the recall curve at 5%
   and 15% as sensitivity checks.
4. **One prompt style.** 03_pedagogical_direct only. Prompt variation is out of scope — the
   Phase 1a ceiling finding applies here: more prompting is not expected to buy the mechanism.

## 9. What this experiment does not test

- Whether the *exercise* built from these methods is any good (that is the PF pool evaluation).
- Whether simulated students produce these methods unprompted (that is Gate A in
  [MCQ_FUNCTIONAL_DIVERSITY_RESEARCH_INTENT.md](../mcq/functional-diversity/MCQ_FUNCTIONAL_DIVERSITY_RESEARCH_INTENT.md) —
  a different arm of the same question).
- Whether sources A (literature) and B (Eedi) are *sufficient* without C — the benchmark only
  measures whether C is *valid*.

## 10. Historical working conventions

- Interpreter `./.venv/bin/python`; `ruff check` and `py_compile` before any live API call
- Azure config via `scripts/run_azure_mcq_plausibility.load_azure_config()`; `.env.local` at repo root
- Report `unknown` and unmatched candidates honestly; never silently convert them to zero
- Pre-registered thresholds above are not adjustable after seeing results

## 11. Data artifacts (built before any generation call)

Ground-truth packages — one JSON per concept, built from `data/eedi_scraped/`:

```text
experiments/data/prior_methods_benchmark/<concept_id>.json

{
  "concept_id": "c5_commonbasis",
  "concept_text": "...",                    // prompt text from §4
  "anchor": {"quiz": "e92o", "questions": [1, 3, 4]},
  "dominant_errors": [                      // recall denominator: pick rate >= 10%
    {"option_text": "...", "explanation": "...", "pct_students": 57, "question": 1}
  ],
  "all_errors": [ ... ],
  "excluded": [{"question": 2, "reason": "No explanation"}],
  "prevalence_note": "gg81 rows: pick rates only, explanations corrupted"
}
```

Sensitivity denominators at ≥5% and ≥15% prevalence are computed from the same file.

Expert-anticipated method lists (the strategy extension, §8.1): hand-extracted from
`expected_student_solutions` in [data/pf_exercises](../../data/pf_exercises) (the expert
YAMLs already carry structured lists with why-fails notes, e.g. Loibl's 6 anticipated
methods) into `experiments/data/prior_methods_benchmark/expert_anticipated.json`, each
method typed `correct_but_insufficient` / `partial_canonical` / `misconception`. Used
descriptively: does the generator's class (b)/(c) output on the closest-matching concepts
contain anything like these? No thresholds; reported as a table.

Historical pre-run checklist (kept as the original plan, not a current to-do list;
the saved v3 and v5 outputs below establish that those runs completed):

- [ ] Build the 10 ground-truth JSON packages from `data/eedi_scraped/`
- [ ] Hand-extract `expert_anticipated.json`
- [ ] Freeze the generation prompt text (§5) in `src/generation/prompts/` as a new entry
- [ ] `ruff check` + `py_compile` on the runner before any live call
- [ ] Record any extended-set swaps (§4 reserve rule) in this file

---

## 12. Results (full run, v3) — completed 2026-08-22

60 generation calls (10 concepts × 2 models × 3 repeats), 600 plausibility judgments,
577 matching judgments; 0 contract/parse/request failures anywhere.

| Metric | GPT-4.1 (ext) | mini (ext) | Read |
|---|---|---|---|
| Plausibility (0–2) | 1.86 | 1.83 | methods sound plausible to the model judge; not observed student behavior |
| Error-recall @ ≥10% (pooled) | 0.269 | 0.202 | low |
| Recall per single list | 0.173 | 0.148 | what a user actually sees |
| Distinct / matched | 0.37 | 0.28 | ~3–4 methods restate one error |
| Repeat stability (Jaccard) | 0.48 | 0.61 | half the found errors change per run |

**Non-confabulation was dropped** as a metric: it was nearly identical to plausibility
(confabulation was defined as `no match AND plausibility == 0`), so it was the same judge's
opinion counted twice, not an independent signal.

**Two structural findings:**

1. **Instance-padding.** The generator enumerates positional variants of one underlying
   misconception ("multiply only the first term", "multiply only the second term", …).
   In-prompt merge rules (v4: rule/belief/failure_mode schema + explicit merge instruction)
   raised the *language* abstraction but did **not** stop the positional duplication — both
   models still emit "first"/"last" as separate rules. Instruction-level constraints do not
   self-enforce; deduplication needs a post-hoc merge pass.

2. **Construct mismatch (the decisive one).** The generator was asked for prior methods but
   produced *error types* (designer's diagnostic labels) rather than *curriculum tools*
   (taught resources students correctly execute). See §13.

## 13. The construct fix: prior methods are resources, not errors

The run exposed that "prior method" was underspecified. Three levels must be separated:

| Level | Example (x_brackets) | Status |
|---|---|---|
| Prior method (resource) | "evaluate inside the brackets first, then multiply" (order of operations) | taught, correct, falls short here |
| Improvised move | "just add everything" | what a student does when the tool stalls |
| Documented error | "multiplied only the first term" | the wreckage Eedi records |

The revised D1 target is the **resource** level: tools taught earlier that can
provide accessible starts, with limitations where relevant. A PF task need not
break every valid method. This is the resources-vs-deficit distinction of
diSessa~\cite{disessa1993epistemology} (knowledge-in-pieces: learning re-organizes which
intuitive fragments fire, rather than replacing wrong beliefs) and
Hammer~\cite{hammer2000resources} (instruction should activate productive prior resources).
Eedi supplies documented error hypotheses for later response analysis, not validation
of a PF simulation or a complete D1 resource inventory. The
correct D1 anchor is the `prior_knowledge_required` + `expected_student_solutions` fields in
[data/pf_exercises](../../data/pf_exercises), already extracted to
[expert_anticipated.json](../../experiments/data/prior_methods_benchmark/expert_anticipated.json)
(24 expert-listed methods across 4 exercises).

**Redesign (curriculum-anchored recommendation), implemented 2026-08-24:**

```text
concept → "what was taught before this concept?"   (curriculum recall — checkable)
        → "which of these tools would a student reach for here?"  (transfer judgment)
        → "what does each give on this kind of task, and how does it fall short?"
          (forward execution — the 94% regime, not the 62% regime)
```

The 94%/62% comparison motivated the redesign, but those calibration tasks do
not validate resource expansion, curriculum mapping or student behavior.

The implementation is in
[run_prior_recommendations.py](../../scripts/run_prior_recommendations.py).
In the August 24 implementation, the grounded condition retrieved page-level
curriculum evidence, added matching curated records, and preserved applicable
curated resources before expanding them into first moves and shortcomings.
The ungrounded condition had no external evidence. Both emitted the shared
`prior-method-recommendations/v1` schema.

The functional comparison is stored in
`experiments/results/prior_recommendations/expert_comparison_gpt41mini_final.json`.
The intermediate generation stages for one real case are shown in
[PRIOR_RECOMMENDATIONS_TRACE.md](PRIOR_RECOMMENDATIONS_TRACE.md).
Across the three topic-diverse cells, grounded outputs recovered the paper/course
resources for average speed, variance, and fair division with explicit provenance;
ungrounded outputs had model-only provenance and did not recover the complete expert
resource sets. Because the historical grounded runner supplied and preserved those
curated records, this demonstrates provenance propagation, not independent expert
recovery or human validation.

**Current boundary:** grounded mapping now sees only curriculum/textbook excerpts,
with expert records held out. Expansion adds the objects a resource needs to
start and the target's additional demand, not a full student solution. The default
cap is five resources before expansion. Optional Learning Commons reference
selection uses v2 of the recommendation schema; baseline output remains v1.
These implementation changes and the completed, bounded D2b scope are recorded
in [PF_PIPELINE.md](PF_PIPELINE.md). Neither the historical resource benchmarks
nor the current software checks demonstrate PF quality or student learning.
