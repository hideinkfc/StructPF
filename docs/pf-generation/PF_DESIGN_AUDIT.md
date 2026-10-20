# Exploratory PF Design Audit

> **Current supporting audit, historical calibration evidence.** The loader still
> uses exploratory v5; its saved model-only calibrations below are not ratings
> of the October 10 design-brief/data-loop tasks. Read
> [PF_PIPELINE.md](PF_PIPELINE.md) for current generation status and quality gaps.

## Purpose and paper provenance

`pf-design-audit/exploratory-v5` is the current **secondary design audit**, not a
revision or replacement of the frozen `rahimi-table1/v1` rating. Its first
version is archived in `src/evaluation/prompts/pf_design_audit.yaml`, and v1-v3
remain preserved as versioned prompt files; v4 is also archived. Rahimi et al. (2025),
*Small vs. Large Language Models: Comparing Language Models in Generating
Productive Failure Math Problems*, Table 1, p. 2, remains the paper-aligned
five-dimension rating used for the benchmark. The original prompt, parser,
historical judgments, and benchmark sources remain unchanged.

This audit adds qualitative evidence for questions that the Table 1 scores do
not isolate: whether a task connects to the lesson target, offers a plausible
start from taught prior resources, makes a useful limit of a familiar approach
available for exploration, supports mathematically distinct approaches, and
leaves meaningful room for student decisions. It draws on Kapur and Bielaczyc's
(2012) mechanisms of activating and differentiating prior knowledge, attending
to critical features, explaining those features, and organizing them toward the
target concept (*The Journal of the Learning Sciences*, 21(1), 45-83,
[doi:10.1080/10508406.2011.591717](https://doi.org/10.1080/10508406.2011.591717),
pp. 49-50). Their design principles also motivate considering challenge,
insufficient-but-usable prior resources, multiple methods, and comparison of
failed or suboptimal starts with canonical reasoning.

Neither paper licenses a default preference for one generation method. A
well-grounded prior-method start or a useful, mathematically valid contrast can
count as evidence for any task when it is visible in that task and its shared
learner context. A plan's claim is not evidence that the student task provides
the claimed opportunity. This audit also treats schema-valid output as distinct
from a reliable judgment: the earlier frozen-judge smoke had 5/5 valid responses
but inconsistent prerequisite ratings on identical-math controls and a false
fair-division correction ([observed smoke record](PF_PIPELINE.md#observed-smoke-check-not-human-calibration)).

## Protocol

- The model receives only the same learning target, learner context, and
  allowlisted student-facing title/body/question for each task. Condition labels,
  teacher-facing claims, proposed approaches, traces, and frozen ratings are
  kept out of the model input. Cases are shuffled with a recorded seed.
- Five qualitative findings are reported independently: target relevance, a
  plausible prior-resource start, a useful contrast, mathematical approach
  diversity, and task openness. `supported`, `partial`, `not_evidenced`, and
  `unknown` each require concrete evidence. There is no numeric score, total,
  weighting, ranking, or preferred-method language.
- A table, graph, equation, or written explanation does not count as another
  mathematical approach when it expresses the same reasoning. A route is a
  **task-affordance hypothesis**, not evidence that students will use it.
  No student work or behavior is supplied, so the audit cannot establish
  observed approach diversity, failure, engagement, or learning.
- Approach diversity requires concrete evidence of a difference in mathematical
  idea, not merely different operation symbols or wording for the same test.
  For example, division-based unit rates and multiplication-based equivalent
  scaling may express the same constant-ratio idea. Multiple valid approaches
  are not a defect; when the task does not clearly support two distinct ideas,
  retain `partial` or `unknown` rather than claiming `supported`.
- Openness requires a consequential mathematical choice or invention (such as a
  criterion, assumptions, data, model, conjecture, or strategy that changes the
  reasoning or conclusion). Choosing a display for the same fixed calculation or
  speculating generically about a fixed yes/no result is insufficient. A unique
  numerical answer alone does not make a task closed.
- For prior-resource starts, missing or empty `assumed_prior_knowledge` is
  `unknown`: missing history does not establish that learners were taught
  nothing. `not_evidenced` is reserved for contexts with enough supplied history
  to assess a start, where the task constrains or omits one.
- The task-text mathematics review is separate and uses `model_recomputed`,
  `unknown`, or `concern`. `model_recomputed` is the model's own report, not
  proof or deterministic verification. It does not infer correctness from the
  presence of a pipeline plan or an error from its absence. A recorded trace, when
  present, is a separate post-hoc evidence channel, never an input to the audit
  or part of a total. A saved checker's acceptance is recorded as an acceptance,
  not upgraded to proof or independent verification. Missing trace is
  `unavailable`, not a failed task.
- The report retains each task's frozen Table 1 judgment. It flags only
  predeclared endpoint tensions for the overlapping MR/OE ideas and differences
  in mathematical-concern presence. These are prompts for human review, not
  score conversions or adjudicated disagreements; no cross-protocol total is
  comparable.

## Proposed rubric (October 14, not yet run)

The heading above is retained for historical links. The initial v1 definitions
remain frozen; the current three-role workflow is `pf-three-role/v2.1`.
Computational development and reserved-transfer checks have now run with
assistant-provisional references, not human-reviewed gold. See the
[authorized campaign and calibration limits](PF_PIPELINE.md#authorized-three-role-calibration-and-full-saved-task-campaign).
The earlier five-role implementation below is preserved, not silently replaced.
The [completed campaign report](../../experiments/results/pf_measure_campaign_20261014/report_final/report.html)
covers all 893 saved input conditions. Primary accessibility and invention
judgments are promising as exploratory evidence; familiar-approach limits
remain strongly conditional on which methods the solver supplies. No measure
has human validation, and no aggregate PF-quality score is justified.

This frozen initial, pre-calibration rubric has five measures. Each asks one
question with a fixed set of
answers, and each answer must come with evidence: a quotation from the
student-facing text, an exact calculation, or a worked step. *Unclear* is never
counted as a failure. The proposal came from a manual reading of the October 13
multi-theme direct-generation run ([PF_PIPELINE.md](PF_PIPELINE.md)).
The versioned prompts and five evaluator roles are now implemented as
`pf-task-measures/v1`. That five-role instrument has no real reference-case
calibration; the subsequent three-role computational campaign is separate.
Neither has human validation.
The working values below consolidate the October 14 discussion. Partly is used
only for target alignment and room for invention; it describes demonstrated
partial fulfilment, not uncertain evidence.

### 1. Target alignment

**Question:** Does the task's central mathematical challenge address the intended
target concept?

**Answers:** Yes · Partly · No · Unclear

- **Yes:** the central mathematical work addresses the stated target.
- **Partly:** the task substantively addresses an explicitly specified target
  element but misses another required element. Identify both; do not invent
  extra requirements or treat mere topic overlap as partial alignment.
- **No:** the central mathematical work addresses a different concept.
- **Unclear:** the target or its connection to the task cannot be established.

**Evidence:** quote the intended target and the relevant student-facing demand,
and explain how the mathematical work connects to, or departs from, that target.
Naming the target or requiring its formal formula is not necessary. A valid
alternative method does not by itself make a task off target.

**Example:** 27 of 30 GPT-4.1 music tasks were flagged as off target by both
earlier judges: they never present the data as a sample, although 7.SP.B.4
concerns samples. This historical judge-flag count is a lower bound, not a
completed assessment with this new measure.

### 2. Mathematical validity

**Question:** For an aligned task, is the mathematics correct?

**Answers:** Yes · No (mathematical error) · Unclear · Not assessed
(measure 1 is not Yes)

- **Yes:** a worked interpretation, supported checks and mathematical argument
  establish consistent givens, feasible requirements and justified claims.
- **No:** a mathematical error, contradiction or unjustified claim is
  demonstrated. Intentional exploration of impossibility is not an erroneous
  demand merely because no construction exists.
- **Unclear:** an essential interpretation, calculation or argument cannot be
  established.
- **Not assessed:** target alignment is Partly, No or Unclear.

**Evidence:** a worked mathematical interpretation and exact checks with the
Python tool ([design_calculator.py](../../src/generation/design_calculator.py)).
The tool checks the supplied expressions, not whether the agent interpreted
the task correctly. Unknown or unsupported calculations are not evidence of an
error.

Coverage inspection across the expert collections found that exact numerical
checks are available across their concrete task families, but full verification
also needs task interpretation, assumptions and sometimes a proof. Review data
consistency, feasibility of the requested mathematical work and support for the
required claims; multiple answers or intentional unknowns are not errors by
themselves. A feasible example is not proof of a general guarantee. Essential
unresolved reasoning remains Unclear even when numerical checks hold. Imported
solution errors and curated annotation errors are recorded separately from
student-task validity; see the
[local coverage record](PF_PIPELINE.md#expert-mathematical-verification-coverage-october-14)
and [replayable checks](../../experiments/results/pf_expert_math_coverage_20261014/local_checks.json).

**Example:** garden gpt5mini-028 has a recorded mathematical concern: a triangle
sits on a "long side" whose stated base is a short side. Under this protocol,
its mathematical validity would be assessed only after target alignment is Yes;
the historical concern is not a completed conditional rating.

### 3. Prior-knowledge accessibility

**Question:** Can a student make a first attempt using only the listed prior knowledge?

**Answers:** Yes · No (too hard to start) · Unclear

- **Yes:** at least one meaningful mathematical start is demonstrated using
  only the declared prerequisites.
- **No:** concrete evidence establishes that even a meaningful start requires
  unavailable knowledge.
- **Unclear:** no supported start or inaccessibility has been established, or
  the prerequisite information is insufficient.

**Evidence:** a meaningful written first step that uses only the listed prior
knowledge. A No requires evidence that even a meaningful start needs unavailable
knowledge. Failing to produce a step, or lacking knowledge needed only for a
complete solution, does not establish No.

Treat the prerequisites as a fixed pool of taught resources, not as one method.
An approach may combine several resources, and a resource may support several
approaches. One supported meaningful start is enough for Yes; every listed
resource and every possible approach need not be used. Map the demonstrated
steps to the resources they require, without adding knowledge retrospectively.

**Example requiring review:** garden gpt41-019's hexagon area needs √3, which the
stated prerequisites do not supply. That is a concern about completing the
solution, not by itself proof that students cannot make a meaningful start.

### 4. Limits of familiar approaches

**Question:** Once a start is possible, does a plausible approach based on the
stated prior knowledge reveal a meaningful limitation that the target concept
helps address?

**Answers:** Yes · No · Unclear · Not assessed
(measure 3 is not Yes)

- **Yes:** at least one plausible, prerequisite-supported approach has a
  demonstrated target-related limitation. A successful alternative is retained
  alongside it and does not negate that finding.
- **No:** the examined approaches meet the actual mathematical demands without
  a demonstrated target-related limitation. This verdict concerns only the
  approaches checked, not every possible method.
- **Unclear:** no positive limitation witness is available and essential
  approach plausibility, mathematical outcome or connection to the target
  remains unresolved.
- **Not assessed:** prior-knowledge accessibility is No or Unclear.

**Evidence:** the familiar approach is worked with the task's own numbers, its
limitation is demonstrated, and the target concept is shown to help address it.
A limitation may be an incorrect result, an incomplete solution or reasoning
that cannot justify the conclusion required by the task. Inefficiency or limited
generality counts only when consequential for the task, not merely because a
canonical method is shorter. Mathematical claims are checked exactly where
supported by the tool.
If one familiar approach falls short and another succeeds, retain both findings;
the positive limitation witness supports the proposed Yes while the successful
alternative remains visible. Do not require every familiar approach to fail.
A successful familiar method is not sufficient on its own for a No: PF includes
comparison of failed or suboptimal approaches, and some learners can solve a PF
problem before instruction. The working aggregation rule still needs calibration.

When multiple plausible approaches are available from the same frozen resource
pool, preserve approach-specific findings and the resources each approach uses.
Do not choose only a failing route, discard a successful route, or treat several
attempts at the same mathematical method as distinct approaches. The adopted
name **Limits of familiar approaches** broadens the question beyond wrong
answers; its operational definition and task-level aggregation still need
calibration. No approach-count threshold is specified.

**Examples:** in the bicycle problem, a speed-ratio split ignores walking time,
because the ratios differ (4:3 and 5:3); total travel time resolves this. Garden
gpt41-009 was previously proposed as a No because a familiar method solves it
directly. That observation alone does not justify No under the clarified
interpretation; the example needs review.

### 5. Room for invention

**Question:** What central mathematical work remains for students to construct,
and how much of that construction does the task already supply?

**Answers:** Yes · Partly · No · Unclear

- **Yes:** the central mathematical invention remains open, with a
  consequential choice about an idea, approach, criterion or assumption.
- **Partly:** the task supplies an important part of the central idea or
  strategy but leaves a consequential mathematical decision to students.
- **No:** the central idea or route is supplied, leaving essentially routine
  execution.
- **Unclear:** the remaining choices cannot be shown to be mathematically
  meaningful, or the degree of prescription is ambiguous.

**Restriction evidence:** Gives away the central idea · Prescribes the approach.
More than one restriction may apply; judge whether it removes the central
invention (No) or leaves a meaningful part (Partly).

**Evidence:** a quotation for each given-away concept or prescribed method, and
concrete examples of meaningfully different approaches where available. A
unique answer, legitimate constraint such as using all data, or failure to find
a second approach does not by itself establish No. The earlier *Only one
approach possible* label is not a standalone negative criterion.

Distinguish the supplied problem definition from the mathematical solution:
the expert bicycle task supplies a bike-sharing plan but not the model needed
to find its handover point; the consistency task supplies a goal and all-data
constraint but not a measure. These supports do not automatically imply Partly.
Identify the consequential mathematical construction still required before
judging how much guidance supplies it.

For the intended learners, approach examples must be supported by the same
declared resource pool used for accessibility. Several prerequisites, displays
or procedural variants do not automatically establish room for invention.
This remains an assessment of the choices left by the task, not an observed
frequency of student approaches or a new diversity score.

**Examples:** 24 of 30 GPT-5 mini basketball questions ask whether a relationship
is "proportional"; that historical keyword count is not a No verdict by itself.
Judge the full demand and whether it supplies the central mathematical
conclusion or route. Shopping gpt41-001: both earlier judges found it "mainly
supports variants of one computational method"; that is a diversity concern,
not automatic evidence that the task removes central invention.

## Conditional assessment and denominators

There are two dependencies, not one chain through all five measures:

- **Target alignment (1) -> Mathematical validity (2):** assess measure 2 only
  when measure 1 is Yes. Partly, No or Unclear gives **Not assessed**, never No. An off-target
  task may contain correct mathematics, but that correctness is outside this
  conditional measurement.
- **Prior-knowledge accessibility (3) -> Limits of familiar approaches (4):**
  assess measure 4 only when measure 3 is Yes. Otherwise record **Not assessed**,
  never No. An approach that cannot be started says nothing about how it would fail.
  **Decision (October 15, 2026): accessibility is a gate, not a reported outcome.**
  The saved run gave Yes on 853 of 858 conditions with a prior-knowledge list, and
  the primary judge missed the only inaccessible test case. Its verdict therefore
  decides whether limits are assessed and flags unusable inputs; it is not reported as
  a measured difference between tasks. Its ability to say No is tested separately by
  a labelled sensitivity set before any broader use. Status (October 15, 2026): in
  `pf-three-role/v2.8`, accessibility is evaluated directly by the task judge as a gate before
  solvers run. On development calibration (`pf_accessibility_sensitivity_strict_v28_20261015`
  and `pf_task_judge_accessibility_calibration_v28_20261015`), Luna matched 8/8 strict
  sensitivity cases across two repeats (`gate_passes: true`) and 20/20 development/control
  references (GPT-4.1: 19/20); see [PF_PIPELINE.md](./PF_PIPELINE.md).
- Measures 1, 3 and 5 are assessed over all ready tasks (N). Mathematical
  validity uses the aligned tasks (n_aligned); limits of familiar approaches
  uses the accessible tasks (n_accessible). Show each conditional measure's
  Not assessed count separately, including whether its prerequisite was Partly
  (alignment only), No or Unclear.
- No dependency on alignment or mathematical validity is added to measures 3
  or 5. These are assessment rules, not generation stop gates.
- Conditional rates for different generators or judges may cover different
  task sets. Report the denominators and alignment/accessibility rates alongside
  them; a high validity rate among aligned tasks is not a validity rate for all
  produced tasks.

The accessibility-to-limits link follows Kapur and Bielaczyc, who describe the
sweet spot as tasks that are "challenged yet not frustrated" (2012, p. 50).
Measure 3 is *not frustrated*; measure 4 is *challenged*. The alignment-to-validity
dependency is our chosen assessment scope, not a claim that off-target tasks
must be mathematically wrong.

A derived count, not a sixth measure: **sweet-spot tasks** are those where
measures 3 and 4 are both Yes. Its denominator is N, so it can be compared across
models. This does not establish alignment or validity.

## Reporting rules

- No total, weighting or ranking. Each measure reports its count per answer.
- Partly records demonstrated partial fulfilment; Unclear records insufficient
  or unresolved assessment evidence; Not assessed records the dependency rule.
  API errors, truncation and parser failures are separate execution outcomes,
  not educational verdicts.
- Fix the intended learner's knowledge pool before assessment. If separate
  knowledge profiles are deliberately compared, report accessibility and
  approach-limit findings with their profile-specific denominators; do not
  silently pool them into an unconditional task verdict. Profiles must come
  from prerequisite/history evidence, not the desired generated approaches.
- Attempt counts (*k* of *N*) come from solution-blind simulated or real students.
  Simulated attempts remain diagnostic model outputs, not evidence of student
  behavior or learning.
- Text judgments predict student behavior. They must be calibrated against human
  ratings before use.

**Supplementary approach evidence, not additional main scores:** retain the
number of distinct meaningful starts identified and a method-level table of
the prerequisites used, worked steps, demonstrated limitations, successes and
unresolved findings. Show the number of approaches reviewed alongside any limit
count. These are identified-method counts, not a complete inventory or student
failure probabilities; more is not automatically better. Their reproducibility
must be checked during calibration before using them for comparisons.

## Relation to Rahimi Table 1

| Measure | Table 1 dimension |
|---|---|
| Target alignment | none |
| Mathematical validity | none |
| Prior-knowledge accessibility | APK; the "not frustrated" half of SSC |
| Limits of familiar approaches | the "challenging" half of SSC |
| Room for invention | OE's "single path" anchor; MR's "wide range of methods" |

Affective engagement is not part of the rubric; it is reported only as a
comparability column. Also left out on purpose: APK's count of prerequisite
concepts, OE's "multiple variables" anchor and the summed total. Table 1 scores
stay reported alongside.

Why this differs from Table 1: each measure asks one question about what the task
makes students do, and answers keep the failure direction. Table 1 mixes ideas
within one level and scores opposite failures the same way ("too easy or too
difficult" is a single 1).

## Earlier names

The earlier four-measure proposal combined correctness and alignment under
Mathematical validity. The October 14 revision separates Target alignment from
Mathematical validity, conditions validity on alignment, and renumbers the
remaining measures without changing historical results.
Right mathematics became Mathematical validity. Accessible start became
Prior-knowledge accessibility. Familiar methods fall short became Failure of
familiar approaches, then Limits of familiar approaches on October 14 to include
incomplete or suboptimal reasoning without requiring every method to fail.
Nothing given away and Varied approaches became Room for
invention. Initial failure is reported as the attempt count of measure 4. Engaging
context was removed; the reasons are in [PF_PIPELINE.md](PF_PIPELINE.md).

## Current three-role evaluator

The current prompts are the preserved
[v2 base](../../src/evaluation/prompts/pf_three_role_v2.yaml) plus the single
[v2.1 development clarification](../../src/evaluation/prompts/pf_three_role_v2_1.yaml).
The [implementation](../../src/evaluation/pf_three_role.py) separates a
target-blind solver from an attempt judge and a task-text judge. The attempt
judge's minimal per-attempt statuses determine accessibility and approach limits
in code. Its original attempts and validation errors remain visible.
An uncertain start (`start_unresolved`) is not a supported start.
The v2 operational No for approach limits also retains an explicitly demonstrated
unrelated shortfall: the method may fall short, but not in a way the target
addresses. This is not a claim that it solved the task or that the task is poor PF.
That refinement is recorded separately from the preserved v1 wording.

The task judge assesses alignment, invention and conditional mathematical
validity. The runtime can request a missing required validity section within
the original three-call budget, with the original text findings locked.
This is schema completion, not a request to improve a verdict. Raw original
and follow-up replies remain recorded. The reserved calibration outputs were
not rerun after this execution correction.

The [campaign runner](../../scripts/run_pf_measure_campaign.py) uses parallel
saved jobs, input/prompt/source hashes and strict resume checks. Development
repeats and two judge series share the same frozen primary solver work; a second
solver is a separate sensitivity check. Missing source history/targets remain
unknown rather than fabricated. Source resource labels without a teaching-depth
description are preserved exactly, with the unspecified scope logged.
Source solutions, reference labels, generating methods and desired errors are
not judge inputs.

Example for a new catalog run:

```bash
./.venv/bin/python -m scripts.run_pf_measure_campaign \
  --phase all \
  --catalog experiments/results/pf_measure_campaign_20261014/catalog.json \
  --output experiments/results/pf_measure_campaign_20261014/new_run \
  --workers 24
```

The current deployments are Luna and GPT-4.1: two OpenAI series, not independent
model families. Actual parameters and snapshots are recorded per run.
Completed jobs are not silently replaced, including errors; a changed prompt,
model, budget or input requires a new output directory. Diagnostic calibration
does not authorize a summed score, learner frequency estimate or quality gate.

## Frozen evaluator implementation (October 14)

The machine-readable specification and role instructions are frozen in
[pf_task_measures_v1.yaml](../../src/evaluation/prompts/pf_task_measures_v1.yaml).
The loader checks its SHA-256 fingerprint and rejects in-place edits: a changed
rubric needs a new version. This does not mean the instrument has been calibrated.
The older Rahimi and exploratory-audit prompts remain unchanged.

[pf_task_measures.py](../../src/evaluation/pf_task_measures.py) implements strict
output contracts for all five responsibilities, exact task/target quote checks,
prerequisite-index checks and deterministic dependency skips. Each role starts
with a separate conversation. The prerequisite-only solver receives no separate
target, source solution, desired errors or other verdicts; the approach-limit
reviewer receives its frozen supported starts and must review every one.
Reference labels and generation metadata are not judge inputs.

Mathematical validity and approach-limit review can request structured
calculations through the existing exact calculator, see their recorded results,
and then return their judgment. No arbitrary Python is executed. The defaults
are at most three model calls and sixteen checks per calculator-enabled role;
other roles use one model call. These are execution limits, not quality or
approach-count thresholds. Unknown/unsupported results remain explicit, and
mathematical interpretation and proof remain model judgments.

API failures, invalid responses, truncation and exhausted budgets retain their
raw call records and have no educational verdict. Unrelated measures still run.
Dependent skips preserve the prerequisite value or execution failure that caused
them. Supplementary method counts are derived from the structured evidence; an
unavailable assessment is not silently counted as zero. Summaries show all task
counts, aligned/accessibility denominators and execution failures separately.

The saved-case runner is
[run_pf_task_measures.py](../../scripts/run_pf_task_measures.py). Its input is a
JSON list, or an object with a `cases` list. Each entry requires `case_id`,
`learning_target`, `learner_context` and exactly one of `student_task` (text)
or `task` (student-facing title/body/question). Prerequisites use the existing
`assumed_prior_knowledge` resource/taught_as format. History supplied only as
`recently_taught` is rejected rather than discarded; adapt it first.

Prepare a run without credentials or model calls:

```bash
./.venv/bin/python -m scripts.run_pf_task_measures \
  --cases path/to/cases.json \
  --output experiments/results/pf_task_measures_v1_prepared \
  --dry-run
```

Use a new output directory for every run. The manifest records source/code
hashes, normalized inputs, all system prompts, requested/effective settings and
execution budgets. The rubric snapshot is preserved with it. An actual run adds
one case record per task and a per-measure summary. SDK retries are disabled;
the CLI exits nonzero if role executions fail, while retaining usable results.
Missing API token-usage metadata is unavailable, not zero.

The initial software checks use mocked replies and explicitly synthetic fixtures,
not human reference labels. The real module entry point has also passed a
no-network dry run. Calibration cases, model-family agreement, human review and
held-out evaluation remain pending. Confirm deployments and budgets before
removing `--dry-run`; one invocation evaluates one judge cohort, not two
independent raters.

## Bounded initial calibration

This historical section concerns the earlier exploratory design audit, not
`pf-task-measures/v1`.

The initial v1 calibration was capped at five saved tasks: the first ready and
Table 1-scored v4 task from each of V1, V2, V3, and PIPELINE, plus the
2026-09-25 checked Grade 7 pilot. The selection is internally balanced and
randomly ordered; the judge sees none of those labels. `--per-condition` accepts
only 1 or 2. `--offset-per-condition` accepts 0 through 3; offset 3 selects the
fourth eligible saved case. The default remains offset 2. The runner excludes the
checked pilot, so the v3 and v5 calibrations did not reuse the v1 or v2 saved-task
samples. Topic-diverse synthetic controls in
`experiments/configs/pf_design_audit_controls.json` include prescribed
equal-sharing, spread-of-scores, and fixed-rate/display-choice negatives, an
underspecified percentages unknown, an intentionally open consistency task, and
a determinate-answer average-speed task. They are not human-rated gold labels.
The runner permits this fixed six-case set only with the explicit
`--include-synthetic-controls` flag; control purposes and illustrative signals
stay out of model inputs.

Inspect the disjoint fourth-ready v5 selection without making model calls:

```sh
./.venv/bin/python scripts/run_pf_design_audit.py \
  --dry-run \
  --offset-per-condition 3 \
  --include-synthetic-controls \
  --output experiments/results/pf_design_audit/v5_fourth_ready_preflight_new
```

Use a new output directory: `--dry-run` avoids model calls but still writes a
manifest and input records. Commands below record historical runs, not invitations
to overwrite them. The current loader always selects v5; the v2/v3 commands
do not restore their earlier prompts.

V3 preserved the exact nested approach-object schema and clarified the difference
between meaningful openness and display freedom or generic speculation. V4 made
absent learner history explicitly unknown; v5 requires idea-level mathematical
differences for approach-diversity support while allowing multiple valid methods.
It does not encode a verdict for a particular task. Neither a
`model_recomputed` assessment nor saved checker acceptance is proof. The v2 and
v3 attempts and raw responses are historical and remain unchanged. V2 used four
disjoint saved tasks plus five synthetic controls:

```sh
./.venv/bin/python scripts/run_pf_design_audit.py \
  --offset-per-condition 1 \
  --include-synthetic-controls \
  --output experiments/results/pf_design_audit/20260925_v2_bounded_calibration
```

V3 used offset 2 with the six controls. V4 addressed the missing-history failure
observed in v2 and again in v3; v5 added the idea-level route distinction noted
in review. V5's single bounded model run is recorded below. The fixed controls
are reused schema/unknown smoke, not independent validation. None of these
automated runs is human validation, test-retest evidence, a full benchmark, or
evidence of student behavior.

## v1 calibration record

The fixed first run attempted five tasks, produced zero schema-valid scores,
zero valid `unknown` ratings, and five invalid responses across five model-call
invocations. The judge received condition-blind inputs with shared target and
learner context. Returned approach lists used inconsistent string/object
shapes, so the parser rejected them. This is an output-contract stability
failure, **not** evidence for or against any task or generation condition.
The v1 raw artifact may label a saved fill-check acceptance `checked`; read it
only as the status recorded by that earlier checker. It is not independent
confirmation or mathematical proof. V2 uses `accepted_recorded` instead.

The [summary](../../experiments/results/pf_design_audit/20260925_initial_calibration/summary.json),
[manifest and saved inputs](../../experiments/results/pf_design_audit/20260925_initial_calibration/manifest.json),
and [raw responses](../../experiments/results/pf_design_audit/20260925_initial_calibration/ratings.jsonl)
retain the attempted run. Frozen Table 1 scores are available for context, but
no disagreement can be assessed because there are no valid secondary findings;
zero flags must not be read as agreement. The first output-schema version is not
stable enough for a larger run. Do not rerun or tune against these same five
tasks.

## v2 bounded calibration record

The disjoint v2 run attempted nine inputs (four saved tasks and five synthetic
controls) in nine model-call invocations. All nine responses parsed; zero cases
were wholly `unknown` and zero responses failed. Three of 54 individual finding
fields were `unknown` (5.6%): target relevance, useful contrast, and approach
diversity on the underspecified percentages control. However, that control's
missing prior instruction was labeled `not_evidenced`, not `unknown`; treat this
as a model-rationale limitation, not a validated finding.

The inputs were condition-blind by construction: all four benchmark tasks shared
target/context, explicit condition labels and teacher-facing wrapper metadata
were absent, and synthetic-control labels/signals were not supplied. The exact
input hashes and per-case model rationales are in the
[summary](../../experiments/results/pf_design_audit/20260925_v2_bounded_calibration/summary.json),
[manifest](../../experiments/results/pf_design_audit/20260925_v2_bounded_calibration/manifest.json),
and [raw responses](../../experiments/results/pf_design_audit/20260925_v2_bounded_calibration/ratings.jsonl).

Key rationales: the judge marked the intentionally open consistency task as
open and recomputed its equal means/ranges without treating the unspecified
spread measure as an error. It found the PIPELINE task's three rates all equal
to one-half, so it marked useful contrast `not_evidenced` despite finding
possible routes; this is a task-affordance judgment, not observed student
behavior. The equal-sharing control's arithmetic was recomputed as 24 / 6 = 4.
Three predeclared cross-protocol review flags were produced: two concern-
presence differences (V2 and V3) and one PIPELINE OE/open-task tension. These
are not adjudicated disagreements or a method win. No full rejudging or prompt tuning was performed.

## v3 disjoint bounded calibration record

V3 attempted four third-ready saved tasks (V1-003, V2-003, V3-003, and
PIPELINE-004) plus all six predeclared synthetic controls: 10 inputs and 10 model
calls. All 10 responses parsed as scored; none was a whole-case `unknown` or a
failure. One of 60 individual finding fields was `unknown` (useful contrast on
the percentages control). This parse success is not evidence of judge validity.

The command used at the time was:

```sh
./.venv/bin/python scripts/run_pf_design_audit.py \
  --offset-per-condition 2 \
  --include-synthetic-controls \
  --output experiments/results/pf_design_audit/20260925_v3_bounded_calibration
```

The manifest and ratings preserve the exact v3 system prompt, blind inputs,
hashes, and responses. The current loader selects v5; rerunning that command now
would not reproduce the v3 model call.

The calibration did correctly mark the narrow water-use yes/no/display task's
approach diversity and openness `not_evidenced`, and it marked the intentionally
open consistency task's openness `supported`. For the determinate-answer
average-speed task, approach diversity was `supported` while openness was
`not_evidenced`; this is consistent with the rule that unique answers alone do
not determine openness.

One known status misclassification remained: for the percentages control, the model labeled
`prior_resource_start` `not_evidenced` even though the learner context supplies no
prior-instruction history. The input did not justify that inference. V4 makes
this case explicitly `unknown`; v5 retains that rule. The open
consistency task's unspecified criterion was treated as intended learner
invention, not automatically as a defect. V3-003 was marked open because its
task explicitly invites learners to create data or a scoring pattern; this is
evidence in the task text, not evidence of student use.

The saved-task inputs shared the target and learner context, and the manifest
confirms that no condition labels, teacher-facing claims, trace, frozen rating,
or synthetic-control metadata entered model inputs. Three concern-presence
differences from the frozen Table 1 judge (V2-003, V3-003, PIPELINE-004) are
human-review flags only, not adjudicated disagreements. Totals across protocols
are not comparable. Full model rationales, raw responses, saved blind inputs,
and hashes are in the
[summary](../../experiments/results/pf_design_audit/20260925_v3_bounded_calibration/summary.json),
[manifest](../../experiments/results/pf_design_audit/20260925_v3_bounded_calibration/manifest.json),
and [ratings](../../experiments/results/pf_design_audit/20260925_v3_bounded_calibration/ratings.jsonl).
For PIPELINE-004, the exact `official:{standard_id}` mapping matched both saved
benchmark IDs with no unexpected IDs; the recorded checker acceptance remains
separate from the task-text review and is not independent verification.

This one-call-per-task, fully automated calibration has no human agreement or
repeatability evidence and cannot establish student behavior or condition-level
quality. The synthetic controls are illustrative checks, not gold ratings.

## v5 disjoint bounded model calibration

Before any model calls, the selector was extended to offset 3 and tested; the
preflight selected V3-004, V1-004, V2-004, and PIPELINE-005. The v5 prompt was
then frozen. The one run attempted these four blinded saved tasks plus the same
six controls used in earlier runs: 10 inputs and 10 `gpt-5.6-luna` calls. All
10 responses were scored, with zero failed or whole-case unknown responses.
Among the six findings per saved task, 0/24 were unknown; among the six reused
controls, 3/36 were unknown (prior-resource start, useful contrast, and approach
diversity for the underspecified percentages control), or 3/60 fields overall.
The four saved task IDs and response-level rationales are preserved verbatim.

Command used:

```sh
./.venv/bin/python scripts/run_pf_design_audit.py \
  --offset-per-condition 3 \
  --include-synthetic-controls \
  --output experiments/results/pf_design_audit/20260925_v5_fourth_ready_calibration
```

The run was condition-blind: the manifest confirms shared benchmark target and
learner context, only the three allowlisted task fields, and no condition label,
teacher claim, trace, frozen score, or synthetic-control metadata in judge input.
The exact v5 prompt hash matches the preflight and post-run source; frozen Table 1
prompt/parser hashes also match. One predeclared concern-presence flag for V1-004
remains a human-review candidate, not an adjudicated disagreement. PIPELINE-005's curriculum trace mapped both
`official:{standard_id}` entries exactly to the benchmark IDs. Its checker result
is only `accepted_recorded`, separate from task-text review and not proof.

The idea-level distinction worked on some cases: V3-004's constant-ratio route
versus additive-change-plus-initial-value route was `supported`, while V2-004 and
PIPELINE-005 remained `partial` without claimed routes. However, V1-004 remains
a **possible overbroad positive**: the model called a constant-unit-rate test
and a line-through-the-origin test distinct ideas, although these may be
equivalent characterizations of the same proportional relationship. This is a
human-review concern, not an adjudicated false positive. No case-specific verdict
was added to the prompt.

Reused-control smoke findings are mixed, not validation: the narrow display-only
water task was not marked open, and the intentionally open consistency task was
marked open. The missing-history percentage control now reports prior-resource
`unknown`, but target relevance and openness were `partial`; the determinate
average-speed control's illustrative partial-openness signal was instead rated
`not_evidenced`. These discrepancies are diagnostic only because control signals
are not human gold labels.

### Read-only rationale caveats

The following are review findings from the saved v5 rationales, not adjudicated
human verdicts:

| Case evidence | Finding | Caveat |
|---|---|---|
| [PIPELINE-005 rating](../../experiments/results/pf_design_audit/20260925_v5_fourth_ready_calibration/ratings.jsonl#L10) | `useful_contrast: supported` because the first two rates match and the third differs. | Applying the taught unit-rate method across all rows already answers whether one constant multiplier fits. The inferred insufficiency of that prior resource is weak and possibly false. |
| [V1-004 rating](../../experiments/results/pf_design_audit/20260925_v5_fourth_ready_calibration/ratings.jsonl#L3) | `approach_diversity: supported`; a line-through-origin route is attributed to prior “Unit rates (7.RP.A.1).” | Line-through-origin is part of the target concept (7.RP.A.2), not the supplied prior repertoire. This is methodological overreach in route provenance; the two routes may also be equivalent characterizations of proportionality. |
| [V3-004 rating](../../experiments/results/pf_design_audit/20260925_v5_fourth_ready_calibration/ratings.jsonl#L1) | `mathematics_review.status: model_recomputed` with a nonempty `concerns` list. | The model flags an ambiguity in “one consistent multiplicative pattern” but does not align the status with its concern. Schema validity did not catch this semantic inconsistency. |

Do not use this audit as a winner metric until blinded human or held-out agreement
addresses these construct and evidence-attribution issues. The raw v5 artifact
is preserved unchanged.

The [summary](../../experiments/results/pf_design_audit/20260925_v5_fourth_ready_calibration/summary.json),
[manifest and blinded inputs](../../experiments/results/pf_design_audit/20260925_v5_fourth_ready_calibration/manifest.json),
and [raw ratings](../../experiments/results/pf_design_audit/20260925_v5_fourth_ready_calibration/ratings.jsonl)
retain counts, hashes, model rationales, and trace provenance. The v5 protocol has
one bounded model-only calibration, not human agreement or repeatability
evidence; do not revise it against these results or treat the reused controls as
independent validation.
