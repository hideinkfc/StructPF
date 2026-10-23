# PF Generation Pipeline: From Grounding to Checked Task Design

> **Canonical current research record.** This document is the entry point for
> the Productive Failure (PF) generation work. It separates the research
> narrative, the implemented recommender, the role of the MCQ study, and the
> remaining work.
>
> **Updated October 15, 2026.** The current default is selected design brief ->
> bounded revision with recorded findings -> fixed-data writer. Quality checks
> no longer stop generation when a usable draft exists. D2b is complete for its agreed
> implementation scope; PF quality and learning effectiveness remain unvalidated.
> D3 now uses a content-based disclosure rule and quoted omission records. Saved
> replays show reduced hints, but not reliable removal of every disclosure. A fresh
> twenty-topic sweep produced nineteen tasks and one stop; direct assistant
> inspection still found disclosed methods/results and invalid or unclear task data.
> A later eight-design data-purpose rerun restores numerical choices in all three
> construction cases while retaining inputs in all five controls; wording limits remain.
> The subsequent frozen method comparison produced nine tasks per method, with no
> general pipeline advantage established by task-text review; student evidence is absent.
> Dated experiments below retain the policy and evidence of their own runs.

## October 14: frozen initial task-measure evaluators

### Authorized three-role calibration and full saved-task campaign

**Authorized October 14; completed computationally overnight, not human-validated.** The user
approved implementing the minimal three-role design, computational calibration
and evaluation of all saved direct/pipeline tasks. The frozen protocol is
[pf_measure_campaign_20261014.json](../../experiments/configs/pf_measure_campaign_20261014.json).
Historical generation is not restarted. The initial five-role v1 and its tests
remain preserved. The new
[three-role workflow](../../src/evaluation/pf_three_role.py) implements the later
minimal-output design with a field-local parser and deterministic dependencies.
One extra audit distinction, `start_unresolved`, prevents uncertain prerequisite
support from becoming a supported start. An unrelated shortfall does not count
as a target-related limit; it is retained explicitly.

The local deployment probes confirmed Luna and GPT-4.1. The configured endpoint
advertises Qwen and DeepSeek identifiers, but both actual non-OpenAI deployment
probes returned 404; no SwissAI credential is configured. This campaign
therefore compares two OpenAI model series, not independent model families.
References prepared autonomously are assistant/researcher-provisional, not the
user's ratings or human-reviewed ground truth. Exact checks and text evidence
can substantiate their narrow claims; neither agreement with those references
nor agreement between the two series establishes human calibration.

Development is bounded to the initial run and at most one targeted clarification
and rerun. Reserved transfer cases are evaluated once after freezing, with no
post-transfer tuning. They are reserved from this prompt development, not
claimed untouched topics: these expert texts were inspected earlier. New output
directories preserve all requests, responses, failed calls, source hashes and
calculator traces. Full-catalog evaluation includes usable historical drafts,
with source/input limitations and original generation failures shown separately.
Identical task/target/history conditions may share one assessment, but every
occurrence and experimental provenance is retained.

**Pre-full-run calibration decision.** The pack contains 13 development tasks,
seven explicitly synthetic controls, nine reserved transfer cases, and fourteen
constructed diagnostic attempts in twelve groups. These references are
assistant-provisional throughout. One prompt clarification package addressed
non-exact quotations, single-equals calculator predicates, first-step versus
completion confusion and target relevance leaking into accessibility. The
initial and revised development results are preserved separately. Raising the
completion budget from 7,000 to 12,000 is an execution-condition change, not
evidence of better educational judgment. The revised development run completed
213/213 role jobs, but exact-quote and missing-field errors still affected
individual measures.

On the nine reserved cases, Luna matches the provisional references for
alignment 8/9, validity 8/9, accessibility 9/9, limits 6/9 and invention 9/9.
The corresponding GPT-4.1 values are 7/9, 0/9, 9/9, 3/9 and 9/9. GPT-4.1's
validity failures are primarily null required fields after an aligned verdict,
not demonstrated mathematical errors. The diagnostic attempt classifications
match 12/14 for Luna and 8/14 for GPT-4.1. These are small computational checks,
not human accuracy estimates; the transfer invention cases are positive
references and cannot establish negative-case discrimination.

The single prompt-development round is now closed; no post-transfer prompt or
reference retuning is permitted. A separately versioned execution correction
(`pf-three-role-runtime/v1.1`) enforces an omitted required validity field within
the already bounded call budget, preserving the original alignment/invention
findings and all calls. It requests schema completion, never a positive verdict.
Two development cases were used only to check this correction's execution:
10/10 role jobs completed and no individual field was lost. The original
transfer outputs are not overwritten or rerun, so they are not validation of
that correction. Definitions, reference labels and prompt text remain frozen.

Full saved-task evaluation was completed as a diagnostic application with explicit
reliability flags, not a claim that all five measures are validated. Accessibility
and invention are more promising than attempt-limit coding. Limits depend on
which familiar methods the solver produced; missing a reference-known method
can cause a task-level reference mismatch even when the judge correctly reviews
the supplied work. Keep that distinction rather than tuning the solver to
manufacture failures. Human review and independent model-family replication
remain unavailable requirements for stronger claims.

### Completed results and verification (October 14--15)

The [final measured-results report](../../experiments/results/pf_measure_campaign_20261014/report_final/report.html)
contains calibration evidence, actual-data plots, historical run/method
breakdowns and a searchable task/solver/judge gallery. Its
[structured findings](../../experiments/results/pf_measure_campaign_20261014/report_final/findings.json)
retain the categorical distributions and comparison-cohort provenance.

**Coverage.** All 893 catalogued task/target/history conditions were evaluated
with two judge series on the same frozen primary solver evidence. This includes
the saved v1--v4 direct and pipeline benchmarks, the multi-theme direct run,
the recent 9+9 comparison, all sixty grounding tasks, historical pilots and
usable flagged drafts. There are 1,953 source occurrences, including copies and
mirrors, not that many independent trials. Thirty-seven conditions have no saved
target and thirty-five have no usable saved prerequisite history; these remain
explicit unknowns/skips. The sixty-four grounding conditions with name-only
resources retain the exact labels, with teaching depth unspecified.
The 867 no-text inventory records include 692 pending, seven planned, 129
failed/blocked results, thirteen unknown records, twenty-three mirrors and
three timeout events; they are not 867 independent failed exercises.

**Execution.** The full application made 5,256 model requests across 4,360 role
jobs: 4,357 completed and three returned unusable protocol responses. There
were no full-run API errors, length cutoffs or exhausted execution budgets.
The [offline verification](../../experiments/results/pf_measure_campaign_20261014/verification.json)
checks both 893-case judge coverages, all dependencies and input boundaries,
unchanged reference/catalog hashes and frozen implementation snapshots. All
660 calculator checks replayed exactly. There were 629 bounded schema-completion
requests. Individual measure evidence remains unavailable for 174 fields,
including 164 non-exact quote errors; those are not negative task verdicts.
Recorded full-run usage is 10,352,498 input tokens and 6,280,786 output tokens;
these are API-reported token counts, not a dollar-cost estimate.
Across the recorded execution/calibration/diagnostic phases there were 5,814
requests and 691 calculator checks, excluding four tiny deployment probes and
assistant/subagent usage. Two rejected initial JSON-mode calls lack token usage.

**Primary Luna judgments over 893 input conditions.**

| Measure | Yes | Partly | No | Unclear | Not assessed | Unavailable execution/evidence |
|---|---:|---:|---:|---:|---:|---:|
| Target alignment | 753 | 44 | 14 | 39 | 0 | 43 |
| Mathematical validity | 713 | 0 | 16 | 24 | 140 | 0 |
| Prior-knowledge accessibility | 853 | 0 | 0 | 36 | 0 | 4 |
| Limits of familiar approaches | 104 | 0 | 654 | 95 | 40 | 0 |
| Room for invention | 677 | 115 | 75 | 0 | 0 | 26 |

Validity's assessed denominator is 753 aligned conditions; approach limits'
denominator is 853 accessible conditions. These aggregate counts describe a
heterogeneous historical collection, not a controlled generator comparison or
student/class distribution. Accessibility is close to its ceiling: existence
of one start is a weak discriminator in this pool. A No for approach limits
means no target-related limit established among the reviewed methods, not
absence of such opportunities in the task.

**A concrete historical comparison.** In the v4 benchmark, V1/V2/V3 each have
thirty student-task texts; PIPELINE has twenty-two texts from thirty original
slots. Luna's Room-for-invention Yes/Partly/No/unavailable counts are
28/1/0/1 for V1, 29/1/0/0 for V2, 28/2/0/0 for V3 and 6/13/2/1 for PIPELINE.
This supports a more prescribed mathematical construction in that historical
pipeline arm, not a universal direct-generation advantage. The later 9+9
comparison gives Room-for-invention Yes for all nine direct and all nine
pipeline tasks. The earlier and later pipeline conditions must not be pooled
as one intervention. The report separately shows each run/cell/model.
For example, the multi-theme music condition has five fully aligned GPT-4.1
tasks versus twenty-eight GPT-5 mini tasks out of thirty each; partial alignment,
unknowns and failed evidence remain separate rather than upgrading this into an
exact historical off-target count.

**Calibration interpretation and remaining limits.** On the same 893 source
conditions, GPT-4.1 returns fully aligned for 811 and invention Yes for 832,
with no Partly verdict in either measure. It is markedly more permissive than
Luna; agreement between these two OpenAI series is not independent human
validation. The primary reserved-reference matches remain 8/9 alignment,
8/9 validity, 9/9 accessibility, 6/9 approach limits and 9/9 invention. All are
provisional-reference checks, and the invention transfer cases are positive
references. Neither the small pack nor repeat stability establishes reliable
negative-case discrimination or educational effectiveness.

The [solver-reference coverage analysis](../../experiments/results/pf_measure_campaign_20261014/solver_reference_coverage.json)
adds the missing elicitation distinction: of thirty-five reference mathematical
actions per solver, Luna covers twenty-four, partly covers three and does not
evidence eight; GPT-4.1 covers twenty-four, partly covers five and does not
evidence six. Selected reference limitation witnesses are fully present in only
one of five Luna and three of five GPT-4.1 outputs. This manual
assistant-provisional map verifies ninety-six quotations and thirty-eight
hashed solver jobs without new calls. Missing a method is not a task defect
or a judge error if the reviewed attempts otherwise succeed.

**Analysis correction, not prompt tuning.** The initial agreement aggregation
included a repeated task-judge record when evaluating the alternative solver,
inflating the primary series' task-level comparison denominator from forty to
sixty. The separate `diagnostics_analysis_v1_1.json` files correct the primary
reference table to twenty cases x two repeats per series, keeping solver
sensitivity separate. Raw replies, labels, old analyses and the once-only
reserved run are unchanged; zero new requests were made for the correction.
The final report uses that corrected aggregation.

**Disposition.** Use Luna as the primary exploratory artifact reviewer and
GPT-4.1 as a sensitivity/comparison series, not a co-equal validated rater.
Keep approach limits explicitly model/elicitation-conditional, and do not
convert supported-start counts into difficulty, diverse attempts into learning,
or these measures into a total PF score or new generation blockers. Human
reference review, genuinely independent-family replication and student evidence
are still needed for stronger claims. Prompts are frozen after the one
development clarification; no further tuning or generation was undertaken.
All 472 affected software tests, focused lint/format/compilation checks, complete
coverage verification and three-size browser/figure/search checks passed.

**v2.2 (October 15, 2026; frozen, mock-tested only, no model calls).**
Three changes, drafted in [pf_three_role_v2_2.yaml](../../src/evaluation/prompts/pf_three_role_v2_2.yaml)
and [pf_three_role_v22.py](../../src/evaluation/frozen/pf_three_role_v22.py):
(1) a fixed, task-neutral basic toolkit for the solver (guess and test, work backwards,
look for a pattern, special cases, simpler related problem, table or diagram), drafted from
Pólya's heuristics in *How to Solve It* (1945), applied identically to every task as a
shared assumption, with a control arm that omits it; (2) checked versus unchecked trials:
only a trial with a stated check counts as a method, and the number of candidates tested is
recorded as evidence; (3) explicit assumption lists, with validity downgraded to unclear
when the answer depends on an unstated reading.
Motivation: in the expert bicycle case the solver and the task judge followed different
unstated rider-speed readings (3.4 km versus about 3.27 km), and the attempt judge did not
flag the difference. The earlier claim that 3.4 km was exact holds only under the
rider-speed reading. Mock tests: 26 pass; the frozen v2 and v2.1 tests are unchanged.
Frozen at the user's request, with the prompt and toolkit hashes pinned in code so that
any in-place edit is rejected and needs a new version. The exact files are snapshotted in
[pf_three_role_v22_frozen_20261015](../../experiments/results/pf_three_role_v22_frozen_20261015/manifest.json).
One rule was left as drafted: an unstated reading downgrades a Yes to Unclear but does not
change a No. Expected effects on the judgements are predictions only, not yet measured:
more accessibility Yes from checked trials, possibly fewer approach-limit Yes because a
successful trial can occupy an attempt slot, and more validity Unclear from the
assumption rule. Accessibility was already near its ceiling (853/893 Yes), so the toolkit
risks making it less discriminating.
Not yet done: the two-arm development run (roughly 400–450 calls, awaiting approval), new
reserved cases (the current reserved set has been used), and wiring into the campaign runner.

**v2.3 draft (October 15, 2026; mock-tested only, no model calls, hash pinned, not run).**
Single change from v2.2: the solver may use the calculator iteratively, one small step at a
time, and receives each result before continuing, as a student would. Ceilings are 40 solver
model calls and 120 calculator requests per solver run; these are limits, not targets.
Per attempt, at most 10 candidate tests (values chosen by reasoning and then checked)
are allowed. Multi-candidate lists are refused as search. Calculator results are attached to
their attempts as aids. They are data for the attempt judge and never set a verdict by
themselves. The judges and the frozen v2.2 files are unchanged, so the only changed role is the
solver. Calculator results are exact (for example 3.4 km gives a gap of exactly 0; 3.0 km gives
50/3). The judge prompt does not yet say how to weigh aids. That would be a separate, tested
change, following the rule of changing one thing at a time. Files:
[pf_three_role_v2_3.yaml](../../src/evaluation/prompts/pf_three_role_v2_3.yaml),
[pf_three_role_v23.py](../../src/evaluation/frozen/pf_three_role_v23.py) and
[test_pf_three_role_v23.py](../../tests/test_pf_three_role_v23.py) (22 mock tests).

**v2.3 solver probe (October 15, 2026; three development cases, toolkit arm, solver only; no judges run).**
The first run failed on all three cases: every reply was a complete solver answer but omitted the
required `"action": "final"` key (3/3), so the parser stopped before any calculator use. The frozen
prompt was left unchanged. A narrow runtime correction (`pf-three-role-v23-runtime/v1.1`) now
accepts a reply with exactly `assumptions` and `attempts` and flags it (`action_missing`). The
failed run is retained unchanged. Rerun results: the bicycle case made 7 calculator requests in 8
model calls (intermediate walking speeds, the remaining 5 km, then the equal-arrival solve); the ship
and garden cases made no calculator requests and one call each. Findings:
(1) Assumptions now expose the rider-speed choice. The bicycle solver stated that Hady's 0.2 km/min
applies when Jasmine rides his bike, which gives 85/26 ≈ 3.27 km. The earlier v2.1 solver used 0.15
km/min and got 3.4 km. The same model can take either reading, so the assumption list is what makes
the choice visible.
(2) One request was refused as "name collision": the solver listed `x_km` both as an expression name
and as a symbol. It then reformulated and succeeded, which is the iterative loop working as designed.
(3) No candidate checks were requested, so the 10-per-attempt cap and the search refusal were not
exercised. All attempts were tagged structured, so the checked-trial path was not exercised either.
(4) Attempts 0 and 1 share one mathematical idea (equal arrival), so they are not two distinct approaches.
Model calls spent: 3 (first run) plus 10 (rerun). Not verified: correctness of the ship and garden answers.
Records: [first run](../../experiments/results/pf_solver_v23_probe_20261015/manifest.json) and
[rerun](../../experiments/results/pf_solver_v23_probe_20261015_rerun/manifest.json).

**v2.4 fix (October 15, 2026; solver only, three development cases, no judges run).**
Cause: the solver's final-answer schema was the top-level `SolverReply` schema, which forbids extra keys and has no
`action` property, while the contract text asked for `"action": "final"`. The model followed the explicit schema. The
judges did not hit this because their schemas describe sub-objects. The freeze had also covered only the YAML file, not
the generated schema text. Fix: [pf_three_role_v2_4.yaml](../../src/evaluation/prompts/pf_three_role_v2_4.yaml) (only
the final-contract wording changed from v2.3) and [pf_three_role_v24.py](../../src/evaluation/frozen/pf_three_role_v24.py), where
the final-answer schema is generated from `FinalSolverReply`, which requires `action: "final"`. The runtime tolerance for
a missing key is removed, so a missing key is now invalid. The freeze pins the prompt file and both full solver system
prompts (with and without toolkit). Mock tests: 151 pass together with the frozen v2.2 and v2.3 suites. Probe:
[pf_solver_v24_probe_20261015](../../experiments/results/pf_solver_v24_probe_20261015/manifest.json) completed on the
first call for all three cases, and every raw reply carried `action: "final"`. The bicycle run made no calculator requests
and stated the 0.2 km/min rider-speed reading as an assumption again. Calls this step: 3.

**v2.5 draft (October 15, 2026; solver and orchestration only; no model calls; not run).** Problem: the v2.4 solver
returns at most four approaches and at most six assumptions; a fifth approach makes the whole reply invalid, so a
task with several legitimate methods loses data rather than showing its variety. Duplicate ideas are also counted as
separate approaches. Change: no cap on approaches or assumptions; each approach carries a `principle` label; the solver
prompt defines same versus different approaches by the underlying mathematical principle (layout, order and numbers do
not make a new approach; a different relation does). Two solvers (Luna and GPT-4.1) run on the same target-blind input,
and both attempt lists go to one attempt judge (Luna). Code does not judge similarity; `principle_counts` reports exact
matches of normalised labels as a weak count, not a semantic judgement. Calculator requests keep their per-solver
attempt numbers; a request that points past the final list is counted, not dropped. Judges and calculator execution are
reused unchanged from v2.2 and v2.3. The rule that solvers may list any number of assumptions is applied here too,
which is a change beyond the approach cap. Files: [pf_three_role_v2_5.yaml](../../src/evaluation/prompts/pf_three_role_v2_5.yaml),
[pf_three_role_v25.py](../../src/evaluation/frozen/pf_three_role_v25.py) and
[test_pf_three_role_v25.py](../../tests/test_pf_three_role_v25.py) (23 mock tests; 88 pass across the v2.2–v2.5 suites). Pinned: prompt `59caddc8…`, toolkit solver system `108c03e6…`, no-toolkit solver system `9cd5b7c6…`.
Limitations: no run has tested whether the two solvers' principle labels agree, whether the attempt judge groups
principles reliably across solvers, or whether removing the cap changes accessibility, which is already near its ceiling
(853/893 Yes). Next: a three-case probe (expert bicycle, expert ship, garden composite area), which needs approval before
any paid call (about 12 solver calls plus calculator requests, and judge calls).

**Accessibility sensitivity run (October 15, 2026; pinned v2.5 evaluator; computational only; gate failed as
specified).** Problem: accessibility was kept as a gate, but its Yes on 853 of 858 saved conditions cannot show that it
can say No. Change: none to the evaluator. Eight synthetic cases with provisional labels were run through the pinned
v2.5 path (two solvers, one attempt judge, task judge), twice each: [config](../../experiments/configs/pf_accessibility_sensitivity_20261015.json),
[runner](../../scripts/run_pf_accessibility_sensitivity.py), [outputs](../../experiments/results/pf_accessibility_sensitivity_20261015/summary.json).
Evidence: all four cases labelled inaccessible were judged Yes in at least one repeat. The three accessible cases
were Yes in every repeat, and the restatement-only case was Yes in both. Execution: 51 judge calls and at least 32
solver calls; three task-judge responses and one solver reply were invalid (none changed an accessibility verdict).
Interpretation, not yet verified causes: (1) the gate's rule counts any supported start, and the toolkit's
guess-and-test and counting moves make many tasks look startable. Testing 1 pizza per person (ruled out by
counting pieces), counting groups of 20 out of 80, and checking 4 = 2 + 2 are all starts for a learner who can count.
My labels assumed a stricter standard, namely that the start must lead toward the target. The gate does not use that
standard. (2) The derivative case states the power rule in the task text, so "no powers" was a weak label, and one
attempt judge reply used 3 × 2^(3−1) although the saved history excludes powers. That is a probable judge miss against
`taught_as`, not yet confirmed. Limitations: labels were written by the assistant, not reviewed by a human; the set is
too small to estimate a rate. Labels were not changed after the run, so the gate fails as pre-specified. Next
implication: the gate's definition of a usable start must be decided before any tuning, and the set must be relabelled
under that definition and rerun as a new version. Nothing is validated.
**Decision (October 15, 2026, after a literature check):** the user chose the strict rule. A usable start must use
skills the learner has been taught and must move toward the target; trial-and-error or counting counts only when it
draws on those skills. Source check: Kapur, Saba and Roll (2023) and Kapur and Bielaczyc (2012) call unsuccessful
intuitive starts productive only when they draw on prior knowledge the learner has; knowledge-space theory (Doignon and
Falmagne, 1985) and expertise-reversal work (Kalyuga et al., 2003) treat solvability as a fit between a task and held
skills. Quotes were reported by a research agent and not yet checked against the primary texts. Not done yet: the
checker prompt is unchanged, the original eight labels are kept, and no rerun has happened. Strict labels were written
after the first run's results were seen, so they are not blind: [strict labels](../../experiments/configs/pf_accessibility_sensitivity_strict_labels_20261015.json)
(four no, three yes, one unclear, unclear not scored). Done after this entry: the strict-rule checker v2.6 was drafted,
pinned and run once on the strict labels (see the next entry).
**Strict-label sensitivity run of pinned v2.6 (October 15, 2026; first run of v2.6; gate failed as specified).**
Problem: the v2.5 checker says Yes to tasks the strict rule calls not startable. Change: [pf_three_role_v26.py](../../src/evaluation/frozen/pf_three_role_v26.py)
and [pf_three_role_v2_6.yaml](../../src/evaluation/prompts/pf_three_role_v2_6.yaml) change only the attempt-judge text
(strict start rule, named unlisted skill, witness rule kept). Solvers, task judge and parser are reused unchanged; the
one shared edit is an optional `system_text` argument in `run_role`, with the default path unchanged (94 mock tests
pass across v2.2 to v2.6). Pinned prompt `1fd239be…`, attempt system `e5215a04…`. Run: 8 strict-labelled cases, two
repeats, two solvers, Luna attempt and task judges, [outputs](../../experiments/results/pf_accessibility_sensitivity_strict_v26_20261015/summary.json).
Evidence: derivative and proof were No in both repeats. Percent was Yes once (one repeat counted a counting start),
hexagon Yes once. The accessible speed case was No in one repeat, because the checker judged decimal division and
substitution unlisted. Mean and unit rate were Yes in both repeats. Pass rule not met: two no-labelled cases were Yes
in one repeat each. Execution: no errors recorded in the summary; one connection error, one timeout and some invalid
task-judge replies, none of which set the accessibility verdict. Interpretation: the strict rule moves the checker
in the intended direction but is now too strict for ordinary arithmetic. Whether decimal division or substitution is a
listed skill is a definition choice, not a checker fact. Limitations: two repeats per case, eight cases, labels set
after the first run, so this is not a blind test. Next implication: decide the arithmetic convention before any
prompt change; a further change would be a new version, not a tuning round.
**Shared-baseline run of v2.7 (October 15, 2026; development round 2; gate failed; tuning stopped).** Problem: v2.6
judged decimal division and substitution unlisted for an accessible speed task. Change: [pf_three_role_v2_7.yaml](../../src/evaluation/prompts/pf_three_role_v2_7.yaml)
and [pf_three_role_v27.py](../../src/evaluation/frozen/pf_three_role_v27.py) add a shared arithmetic baseline (the four operations
on whole numbers and decimals, and substitution into a stated formula) to the attempt judge, without listing each operation.
Concepts remain listed. Pinned prompt `c6accf8b…`, attempt system `503e10d4…`; 99 mock tests pass across v2.2 to v2.7.
Run: the same eight strict labels, two repeats, [outputs](../../experiments/results/pf_accessibility_sensitivity_strict_v27_20261015/summary.json).
Evidence: the accessible speed case is now Yes in both repeats (v2.6 had one No). Derivative is No in both repeats.
Proof is No in one repeat and gave no verdict in the other (the attempt judge returned the wrong number of audits, an
execution error). Percent is Yes in one repeat and No in the other; hexagon is Yes in one and No in the other. In the
Yes repeats the judge accepted a move it also described as not narrowing the answer (counting dollar units; labelling
sides), so the "must narrow" clause was not applied consistently. Pass rule not met.
Runner correction: the error check missed a completed job with no verdict. The rule now counts that as an error. All three
summaries were regenerated from the saved job files with no model calls; the verdicts did not change for v2.5 or v2.6.
Decision: the project's limit is two development rounds without the predefined gain, so tuning stops here. Limitations:
two repeats per case make a single Yes decisive; the pass rule is strict; labels were written after the first run; eight
cases are too few for a rate. Next implication: accessibility cannot yet be shown to say No reliably. Either accept the
gate as unvalidated and report it as such, drop it as a gate, or authorise a new, separately justified protocol (more
repeats, a narrowing check that the judge must quote, and independent labels). A third round needs that authorisation.
**Decision (October 15, 2026, user):** keep the accessibility gate as it is. Its two Yes verdicts on inaccessible cases
(percent and hexagon, one repeat each in v2.7) are judge mistakes against the strict definition, and they stay in the
record. No third development round.
**Solver process check (October 15, 2026; v2.5 solvers, v2.7 attempt judge; 10 saved task inputs: 8 development, 2 transfer; no controls).** Pre-set criteria and result: completion, 10 of 10 tasks finished for both solvers (met); target-blind input, asserted in code (met); most attempts with a supported start, 37 of 53 (met overall, but two tasks fail); calculator used, 0 of 20 solver runs requested it although it was offered (not met in practice). Expert ship had no supported attempt in that single judge run: both solvers used distance = speed × time, which the history does not list (only speed = distance ÷ time). **Correction (same day, after the attempt-judge check below):** that verdict was not stable; Luna's two repeats and GPT-4.1 all accepted the same attempts as supported, so the ship finding is a judge-consistency problem, not a settled solver failure. Expert land had 3 of 4 attempts rejected for fractions and additive valuation, not listed in the history. Interpretation: the rejections may reflect thin history lists rather than poor solving. Not checked: whether the many approaches on expert consistency (10 from one solver) are distinct. Files: [run_pf_solver_check.py](../../scripts/run_pf_solver_check.py), [summary](../../experiments/results/pf_solver_check_v25_20261015/summary.json).



**Attempt-judge consistency check (October 15, 2026; v2.7 judge; same 53 saved attempts; computational only).** Question: how
reliably does the attempt judge give the same answer? Method: re-judged the frozen attempts with Luna twice more (three Luna runs in total,
counting the saved one) and GPT-4.1 once. Results: the same exact status across the three Luna runs for 79% of attempts;
the same supported-or-not call for 87%; the same call across all four runs for 68%. Accessibility (any supported attempt) agreed on 9 of 10 tasks; the
one change was expert ship. GPT-4.1 disagreed with the saved Luna run on 15 of 53 attempts, always by calling an attempt supported
where Luna did not. Interpretation: the judge is moderately consistent on clear cases and unstable on the rearrangement and
fraction moves that decide the verdict. GPT-4.1 is more lenient than Luna under the same rule. No human labels exist, so these
numbers measure consistency, not correctness. Files: [run_pf_attempt_judge_check.py](../../scripts/run_pf_attempt_judge_check.py),
[outputs](../../experiments/results/pf_attempt_judge_check_20261015/jobs).

**Full-pipeline check (October 15, 2026; pinned v2.7 pipeline; three saved tasks: expert bicycle, expert ship, garden composite area; computational only).** Question: does the whole system run cleanly and give sensible measures? Result: all three tasks completed for the task judge, both solvers and the attempt judge, with no schema errors and the dependency rules held (validity and limits not assessed where their prerequisite failed). Measures: alignment yes and validity yes on all three; invention yes on all three. Accessibility was no for expert bicycle and expert ship, yes for garden. Problem: both expert no verdicts rest on the strict rule's gaps, not on the tasks. Expert ship: the judge calls rearranging speed = distance ÷ time into distance = speed × time an unlisted step; the history does not list that rearrangement. Expert bicycle: the judge calls unit conversion (minutes to hours, metres to kilometres) unlisted; the shared arithmetic baseline agreed in v2.7 does not name unit conversion. So the strict rule is applied more narrowly than the task designers assumed, and it rejects routes a course would normally teach. Calculator: no solver or judge requested it in any run. Not fixed: changing the baseline now, after seeing these results, would be tuning on the examples; it needs a decision and a new frozen version with fresh cases. Files: [run_pf_full_evaluation_check.py](../../scripts/run_pf_full_evaluation_check.py), [summary](../../experiments/results/pf_full_evaluation_check_v27_20261015/summary.json).

**Task-judge accessibility gate (`pf-three-role/v2.8`, October 15, 2026; calibrated on sensitivity and development/control sets; computational only).** Problem: when accessibility was decided indirectly through solver attempts and the attempt judge (v2.5–v2.7), trivial solver guesses made the attempt judge flip on `percent` and `hexagon`, while the strict attempt-judge rule falsely rejected `expert_ship` (formula rearrangement) and `expert_bicycle` (unit conversion). In addition, `task_judge` in v2.2 occasionally omitted `"action": "final"` after a calculator turn because its final contract lacked a top-level `FinalTaskReply` schema. Change: [pf_three_role_v2_8.yaml](../../src/evaluation/prompts/pf_three_role_v2_8.yaml) and [pf_three_role_v28.py](../../src/evaluation/frozen/pf_three_role_v28.py) move `prior_knowledge_accessibility` into `task_judge` with a top-level `FinalTaskReply` schema requiring `action="final"`, and gate the solvers and `attempt_judge` on `accessibility == "yes"`. Both judges share a numeracy baseline (the four operations on whole numbers and decimals, standard unit conversions, basic trial/table heuristics, and direct use or rearrangement of a formula stated in `learner_context`, unless `learner_context` explicitly excludes them), while restating numbers, labelling sides without an area method, or counting objects without a percentage/ratio method is explicitly marked `no`. Pinned hashes: prompt `6c771460…`, task system `2913ac8c…`, attempt system `b73dbb07…` ([test_pf_three_role_v28.py](../../tests/test_pf_three_role_v28.py), 104 mock tests pass across v2.2–v2.8). Evidence: (1) On the 8-case strict sensitivity set (2 repeats = 16 runs, [summary](../../experiments/results/pf_accessibility_sensitivity_strict_v28_20261015/summary.json)), the gate passed (`gate_passes: true`, 0 errors): all 4 inaccessible cases (`derivative`, `proof`, `percent`, `hexagon`) were `no` in both repeats, and all 3 accessible cases (`speed`, `mean`, `unit_rate`) were `yes` in both repeats. (2) On the 20-case calibration pack (`13` development + `7` controls, [summary](../../experiments/results/pf_task_judge_accessibility_calibration_v28_20261015/summary.json)), Luna matched 20/20 provisional references (100%) and GPT-4.1 matched 19/20 (95%), with both `expert_bicycle` and `expert_ship` judged `yes` and `control_inaccessible` judged `no`. (3) On the 3-case full pipeline check ([summary](../../experiments/results/pf_full_evaluation_check_v28_20261015/summary.json)), all 3 tasks (`expert_bicycle`, `expert_ship`, `garden_composite_area__gpt41__019`) were judged `yes` on accessibility. Limitations: references and sensitivity labels are assistant-written, not human-validated, and `expert_bicycle`/`expert_ship`/`percent`/`hexagon` failure modes were already known when v2.8 was written, so this is development calibration rather than an untouched holdout test.

**Resource-and-toolkit sweep solver (`pf-three-role/v2.9`, October 15, 2026; 5-task probe; computational only).** Problem: on single-answer PF tasks (`expert_bicycle`, `expert_time_sharing`, `expert_country`), the v2.5 solvers returned only 1 approach per solver (jumping straight to the full solution) and omitted simpler single-resource and heuristic student starts. Change: [pf_three_role_v2_9.yaml](../../src/evaluation/prompts/pf_three_role_v2_9.yaml) and [pf_three_role_v29.py](../../src/evaluation/frozen/pf_three_role_v29.py) keep the calibrated v2.8 task judge and attempt judge, downgrade a `checked_trial` without `trial_count` to `unchecked_trial` instead of discarding the whole solver reply, and instruct the solver to sweep three independent parallel categories: (a) single-resource or partial-constraint approaches, (b) toolkit heuristic approaches, and (c) combined multi-resource approaches. Pinned hashes: prompt `91fa3e79…`, toolkit solver system `4d39ac1d…`, no-toolkit solver system `c7f7aadf…` ([test_pf_three_role_v29.py](../../tests/test_pf_three_role_v29.py), 107 mock tests pass across v2.2–v2.9). Evidence on 5 saved tasks ([summary](../../experiments/results/pf_full_evaluation_check_v29_20261015/summary.json)): total pooled approaches rose from **2 to 15** on `expert_bicycle` (10 Luna + 5 GPT-4.1, covering equal split, 4:3 ratio split, candidate trial comparison, and equal post-flat travel times; `familiar_approach_limits` moved from `unclear` to `yes`), from **2 to 13** on `expert_time_sharing` (10 Luna + 3 GPT-4.1; `familiar_approach_limits = yes`), from **4 to 13** on `garden_composite_area__gpt41__019` (`familiar_approach_limits = yes`), and from **2 to 12** on `expert_ship` (including both the unweighted speed average `(32+41)/2` and total distance over total time). On `expert_country`, GPT-4.1 rose from **1 to 3** approaches (proportional rounding, population per seat, minimum guarantee plus proportional allocation), while Luna hit the 12,000-token completion limit (`truncated`) writing out six-state arithmetic across many approaches. Limitations exposed by the wider sweep: (1) on multi-entity tasks like `expert_country`, an uncapped sweep can exhaust 12,000 completion tokens on reasoning models; (2) when the pooled list reaches 12–15 approaches (`expert_ship`), the attempt judge can miscount the list length (`11` reviews returned for `12` attempts) unless attempts are indexed or repaired.

**Generated-task evaluation with `pf-three-role/v2.9` (October 15, 2026; 42 generated tasks across 14 cohorts; computational only).** Question: how do the saved direct and pipeline generated tasks perform under the v2.9 evaluator (task-judge accessibility gate + two resource-sweep solvers + attempt judge)? Scope: all 18 tasks of the matched `Latest fresh method comparison` (`9` direct vs `9` pipeline across average speed, fair division, and variance), `8` tasks from `Benchmark v4` (`2` each from `V1`, `V2`, `V3`, `PIPELINE`), and `16` tasks from the Rahimi `Main30` direct-generation study (`2` from each of the 8 theme × model cells); [runner](../../scripts/run_pf_generated_v29.py), [summary](../../experiments/results/pf_generated_tasks_v29_20261015/summary.json). Findings:
1. **Direct tasks are overwhelmingly solvable by familiar prior knowledge alone:** Across the `31` directly generated tasks (`16` Main30 + `6` Benchmark v4 V1–V3 + `9` Latest Direct), **`19 / 31` (`61%`) had `meets_demands > 0`** (often `8` to `18` familiar approaches solving the entire task without needing the target concept, including `5` that were also giveaways), and **`1 / 31` was a giveaway with `meets_demands == 0` (`6 / 31` giveaways total)**. Only **`5 / 31` (`16%`)** left the construction open (`invention = yes`) while blocking familiar solutions (`meets_demands == 0` and `target_limits > 0`), with `6 / 31` gated or unclear.
2. **Pipeline tasks in the saved cohorts suffer from the same bypass (`meets_demands > 0`) plus partial giveaways:** In `Latest fresh method comparison pipeline` (`n = 9`), `7 / 9` were solved by familiar prior approaches (`meets_demands > 0`) and `2 / 9` were partial giveaways (`invention = partly`), with `0 / 9` reaching a genuine PF impasse (`meets_demands == 0` and `target_limits > 0`). In `Benchmark v4 PIPELINE` (`n = 2`), both were `invention = partly` and `meets_demands > 0`.
3. **Methodological discovery on `familiar_approach_limits`:** Under the v2.2/v2.8 aggregation rule (`"yes"` if *any* attempt has `target_limit`, regardless of whether other familiar attempts have `meets_demands`), expanding the solver in v2.9 to sweep partial single-resource starts flipped `familiar_approach_limits` from `9 / 42` `yes` (in v2.1) to `31 / 42` `yes` (in v2.9)—because on `25` of those `31` tasks, the solver generated both `1–18` complete familiar solutions (`meets_demands`) and `1–14` partial single-resource starts (`target_limit`). Thus, with a wide solver sweep, separating **any partial start fails (`target_limits > 0`)** from **no familiar approach solves the task (`meets_demands == 0` and `target_limits > 0`)** is essential to avoid crediting routine tasks that familiar methods already solve.

**Learning Commons default (October 15, 2026; code default changed, not a new experiment).** Change: [run_pf_diagnostic.py](../../scripts/run_pf_diagnostic.py) now enables Learning Commons references in the D1 call by default, with `--no-learning-commons` to opt out. A reused D1 (`--reuse-d1-root`) still disables fresh retrieval. `run_case_worker` and `run_benchmark` keep their Python defaults of `False`, so the frozen topic sweep (which calls `run_case_worker` without the flag) and other saved runs behave as before. Tests: [test_pf_diagnostic.py](../../tests/test_pf_diagnostic.py) updated to the new default; 126 tests pass across diagnostic, topic-sweep and Learning Commons suites. Evidence of the default path: one uncached case (`kerrigan_fair_division_undergrad_usa`) fetched 10 live references and completed, but that test also spent 17 model calls and added a cache entry under `experiments/results/learning_commons_queries/cache`. Limitation: `run_pf_diagnostic.py` is a tracked source file, so the source-hash check in frozen manifests (for example the topic sweep) will refuse to resume existing output directories until those manifests are regenerated under a new output directory. Not run: no new experiment was launched with references on.

**Two-round pipeline improvement with Learning Commons progression graph and D2a/D2b/D3 impasse package (October 15, 2026; 3 families × 3 repeats = 9 tasks per round; computational only).**
- **Problem traced from saved artifacts:** In the October 11 matched 9-task pipeline cohort (`Latest fresh method comparison pipeline`), only `3 / 9` tasks (`33%`) passed all five measures under `v2.9` (`0 / 9` under `v2.1`): `PROPOSE_BRIEF_SYSTEM` and `SELECT_BRIEF_SYSTEM` explicitly permitted a familiar single-resource route to settle the whole task, `loibl_variance` briefs sometimes required valid spread measures (`MAD` vs. `Variance`) to give opposite winners or omitted the clustering definition of consistency (`mathematical_validity = no`), and `WRITE_DATA_TASK_SYSTEM` included coaching sentences (`"You may calculate, draw, tabulate..."`) that dropped `room_for_invention` to `partly`. Meanwhile, Learning Commons was only queried as unfiltered text search (`grade_levels=[]`) without using its Coherence Map `/prerequisites` (`buildsTowards`) or `/learning-components` (`supports`).
- **Declared change package:**
  1. **D1 / Learning Commons graph ([learning_commons_api.py](../../scripts/learning_commons_api.py), [learning_commons_local.py](../../scripts/learning_commons_local.py)):** Added `prerequisites_for_standard`, `standards_built_towards`, and `related_standards_for_standard` to `LearningCommonsClient`, and `graph_progression_bundle` in `learning_commons_local.py` to attach the curated `v1.14.0` `target_standards`, `prerequisite_standards_builds_towards`, and `supporting_learning_components` to the shared benchmark context.
  2. **D2a / D2b / D3 prompt package ([design_briefs.yaml](../../src/generation/prompts/design_briefs.yaml), [design_data.yaml](../../src/generation/prompts/design_data.yaml)):** Required direct single-resource shortcuts to hit a concrete limitation (opposite stage-speed mean vs. whole-journey rate, equal means and equal ranges across `>= 6` observations with consistent interior clustering, or contested discrete items plus one divisible resource), required explicit domain/validity rules in `situation_and_rules`, and forbade coaching menus and procedural rubrics in D3 student wording.
  3. **Execution and validator hygiene ([design_brief_stage.py](../../scripts/design_brief_stage.py), [pf_three_role_v28.py](../../src/evaluation/frozen/pf_three_role_v28.py), [pf_three_role_v29.py](../../src/evaluation/frozen/pf_three_role_v29.py)):** Parallelized D2a proposals and solver calls, stripped non-toolkit strings from `toolkit_used` instead of dropping the solver reply, and matched `_text_v28` to `_accessibility` so extra `learning_target` quotes are recorded in `unmatched_task_quotes` when at least one verbatim task quote is present.
- **Evidence across rounds ([runner](../../scripts/run_pf_pipeline_v2_experiment.py), [Round 1 summary](../../experiments/results/pf_pipeline_lc_impasse_v2_20261015/summary.json), [Round 2 summary](../../experiments/results/pf_pipeline_lc_impasse_v3_20261015/summary.json)):**
  - **Production & D2b calculator acceptance:** `9 / 9` tasks produced and `9 / 9` D2b data proposals accepted in both Round 1 and Round 2.
  - **Five-measure `v2.9` progression (`All 5 = Yes`):** Rose from **`3 / 9` (`33%`)** in the old saved pipeline (`Valid 6/9, Invent 6/9, Limits 7/9`) to **`5 / 9` (`56%`)** in Round 1 (`Align 9/9, Access 9/9, Invent 9/9, Limits 8/9, Valid 6/9`) and **`7 / 9` (`78%`)** in Round 2 (`Align 9/9 [100%], Access 9/9 [100%], Limits 9/9 [100%], Invent 8/9 [89%], Valid 7/9 [78%]`).
  - **Comparison against Direct generation under `v2.9`:** Round 2 (`7 / 9 = 78%` All-5-Yes) exceeds `Benchmark v4 Direct V1–V3` (`1 / 6 = 17%`), `Rahimi Main30 Direct` (`5 / 16 = 31%`), `All Direct Combined` (`12 / 31 = 39%`), and the matched `Latest Direct` baseline (`6 / 9 = 67%`). Under `v2.1`, all 9 tasks in both rounds achieved `9 / 9` Alignment, `9 / 9` Mathematical validity, `9 / 9` Accessibility, and `9 / 9` Room for invention.
- **Limitations:** Because D1/D2a/D2b/D3 changes were shipped as one package, gains cannot be attributed to a single stage without an ablation. Pipeline generation uses multiple model calls per task and is not budget-matched to 1-call Direct generation. Sample size is `9` tasks (`3` families × `3` repeats), and all ratings are computational model judgments rather than blinded human reviews or student attempts.

**20-Case Learning Commons Progression Bridge ablation from Stage D1 (`pf-progression-bridge-dataset/v1`, October 16, 2026; 20 topics × 2 arms = 40 tasks; computational only).**
- **Problem:** Prior comparisons held a hand-written teacher D1 list (`fixed_d1.json`) constant across arms, which masked Stage D1's role in discovering grade-appropriate prior skills (`S_prior`) without leaking the target concept (`S_target`). In addition, passing D1's internal `falls_short_because` note (which explicitly states what extra demand the target adds) to a leakage judge conflated internal designer notes with assumed student prior knowledge.
- **Change ([build_progression_bridge_dataset.py](../../scripts/build_progression_bridge_dataset.py), [progression_bridge_dataset_v1.json](../../data/learning_commons/progression_bridge_dataset_v1.json), [run_progression_bridge_study.py](../../scripts/run_progression_bridge_study.py), [plot_progression_bridge_study.py](../../scripts/plot_progression_bridge_study.py)):**
  1. Constructed a 20-case CCSSM progression bridge dataset across Grades 5–10 (`251` CC-BY-4.0 nodes and `247` `buildsTowards`/`supports` edges in `data/learning_commons/progression_bridge_v1/`).
  2. Ran the generalized pipeline from Stage D1 without hand-written teacher priors or exclusion lists in two matched arms: **Arm A (`ungrounded`)** receiving only `{grade, subject, topic, target_concept}`, and **Arm B (`lc_grounded`)** receiving the official Learning Commons `buildsTowards` prerequisite standards ($S_{\text{prior}}$) and `supports` learning components in D1 (`GROUNDED_MAPPING`) plus the progression bundle in `shared_context` for D2a–D3.
  3. Scored **Progression Bridge Fit (`0 / 1 / 2`)** on the student-facing prior-resource fields (`resource`, `taught_as`, `student_move`) and final D3 student task, alongside `pf-three-role/v2.9` against the official grade-level prerequisite repertoire.
- **Evidence ([summary.json](../../experiments/results/pf_progression_bridge_20cases_20261016/summary.json), [figure](../../docs/status/figures/pf_progression_bridge_20cases_20261016.png)):**
  - **Completion:** `20 / 20` tasks produced and `20 / 20` fully evaluated in both arms (`40 / 40` total).
  - **Progression Bridge Fit (`0 / 1 / 2`):** Rose from mean **`1.30 / 2.00`** in `ungrounded` (`11 / 20` [`55%`] Score 2 exact bridges, `4 / 20` Score 1 loose matches, `5 / 20` [`25%`] Score 0 boundary misses) to **`1.65 / 2.00`** in `lc_grounded` (`14 / 20` [`70%`] Score 2 exact bridges, `5 / 20` Score 1 loose matches, `1 / 20` [`5%`] Score 0 boundary miss). Across the 20 paired topics, `lc_grounded` scored higher on `6` topics, `ungrounded` on `2`, and `12` tied.
  - **Boundary discipline (target leakage):** `ungrounded` leaked the target concept into Stage D1 prior knowledge on **`3 / 20` (`15%`)** topics (`8.F.B.4` two-point slope formula, `HSF-LE.A.1` successive multiplicative ratios, `HSS-CP.B.6`) and into Stage D3 student text on **`3 / 20` (`15%`)** topics. `lc_grounded` had **`0 / 20` (`0%`)** Stage D1 target leaks and **`1 / 20` (`5%`)** Stage D3 target leak (`7.RP.A.2`).
  - **Downstream `v2.9` measures (`N = 20` per arm):** `lc_grounded` improved `target_alignment` (`19/20 -> 20/20`), `mathematical_validity` (`16/20 [80%] -> 18/20 [90%]`), and `room_for_invention = yes` (`8/20 [40%] -> 11/20 [55%]`), with equal `prior_knowledge_accessibility` (`20/20`) and `all_5_yes` (`7/20` in both arms).
- **Limitations:** Single generation per topic and arm (`n = 20` pairs); all ratings are computational model judgments (`gpt-5.6-luna`), not blinded human ratings or classroom trials. Furthermore, auditing the 20 evaluation records revealed two design limitations in the initial `Progression Bridge Fit` metric: (a) checking whether an ungrounded arm matched a specific Learning Commons $S_{\text{prior}}$ code is circular when $S_{\text{prior}}$ was only shown to the grounded arm, and (b) `CASE_SPECS` in `build_progression_bridge_dataset.py` included `"rather than [prior shortcut]"` phrasing in `target_concept`, partially leaking the prior-shortcut contrast to the ungrounded arm.
- **Completed 30-Topic 3-Arm Prior-Set & Solver Trap Study (`pf_progression_bridge_30cases_3arms_20261016`, October 16, 2026; `30` topics × `3` arms = `90` tasks; computational only, Slides 37–38 in [RAHIMI_EXPERIMENT_VISUAL.html](../status/RAHIMI_EXPERIMENT_VISUAL.html), [summary_three_arm.json](../../experiments/results/pf_progression_bridge_30cases_3arms_20261016/summary_three_arm.json)):**
  - **Dataset expansion & clean input:** Expanded [progression_bridge_dataset_v1.json](../../data/learning_commons/progression_bridge_dataset_v1.json) to **`30` CCSSM progression bridges** across Grades 5–10 (`315` nodes, `317` `buildsTowards`/`supports` edges in `data/learning_commons/progression_bridge_v1/`) and stripped `"rather than [shortcut]"` contrast phrases from `target_concept` so ungrounded arms receive zero trap hints.
  - **Fair 3-arm setup:** Compared **Arm 1 (`Direct`)**, **Arm 2 (`Pipeline without LC`)**, and **Arm 3 (`Pipeline with LC`)**. Each arm outputs its proposed **prior-skill set** $\mathcal{K}_{\text{prior}} = \{k_1, \dots, k_m\}$ and student **Task $T$** (`30 / 30` tasks produced in every arm).
  - **Gate 1 (Left-to-Right Set Validity):** Each $k_i \in \mathcal{K}_{\text{prior}}$ is valid iff there is a directed prerequisite path $k_i \longrightarrow \dots \longrightarrow C_{\text{target}}$ (allowing intermediate skips, so basic prior skills are valid) and $k_i$ can be attempted on Task $T$'s quantities. Any $k_i$ that is irrelevant/unusable or a spoiler ($k_i \ge C_{\text{target}}$) is invalid. If **any** $k_i$ (or their combination) is a spoiler, or **zero** $k_i$ are valid, the run receives **Score 0 (`Invalid Prior Set`)**; otherwise the valid subset $K_{\text{valid}} \subseteq \mathcal{K}_{\text{prior}}$ advances to Gate 2.
  - **Gate 2 ($K_{\text{valid}}$-Only Solver Trap Check):** A solver restricted strictly to each $k_i \in K_{\text{valid}}$'s literal `taught_as`/`student_move` procedure (and forbidden from smuggling in pretrained target formulas) attempts Task $T$. If at least one $k_i \in K_{\text{valid}}$ (or their combination) directly solves Task $T$ and gets the right answer/winner—or fails only on an unrelated obstacle—the run receives **Score 1 (`Trap Bypassed / Off-Target`)**. If the skills in $K_{\text{valid}}$ produce concrete attempts on Task $T$ that conflict or fall short on Task $T$'s numbers for the exact reason $C_{\text{target}}$ is needed, the run receives **Score 2 (`Valid Prior Set + Productive Trap`)**.
  - **Measured 30-topic results ([summary_three_arm.json](../../experiments/results/pf_progression_bridge_30cases_3arms_20261016/summary_three_arm.json)):**
    - **Arm 1 (`Direct Generation`):** Mean **`0.700 / 2.00`** — **`6 / 30` (`20.0%`)** Score 2 productive traps, **`9 / 30` (`30.0%`)** Score 1 trap bypassed/off-target, **`15 / 30` (`50.0%`)** Score 0 invalid/spoiler prior sets (`14` individual spoiler items + `1` combined-set spoiler across `90` proposed skills; `mean_valid_skill_ratio = 0.845`). Because Direct generates `K_prior` and `Task T` in one shot without a curriculum boundary, half of its prior sets leaked the target procedure directly into `student_move` (e.g., multiplying $P(A)P(B)$ and comparing to $P(A\cap B)$ in `HSS-CP.A.2`, restricting the denominator to the subgroup in `HSS-CP.B.6`, or computing people per square meter in `HSG-MG.A.2`).
    - **Arm 2 (`Pipeline without LC`):** Mean **`1.433 / 2.00`** — **`17 / 30` (`56.7%`)** Score 2 productive traps, **`9 / 30` (`30.0%`)** Score 1 trap bypassed/off-target, **`4 / 30` (`13.3%`)** Score 0 invalid/spoiler prior sets (`4` spoiler items: two-point slope $(y_2-y_1)/(x_2-x_1)$ in `8.F.B.4` and `8.SP.A.3`, successive ratios in `HSF-LE.A.1`, and $(x+b)^2 = x^2+2bx+b^2$ matching in `HSA-SSE.B.3.b`; plus `6` irrelevant/unusable skills such as reading statistical plots when D3 only gave raw number lists; `88 / 98` valid skills, `mean_valid_skill_ratio = 0.897`).
    - **Arm 3 (`Pipeline with LC`):** Mean **`1.700 / 2.00`** — **`21 / 30` (`70.0%`)** Score 2 productive traps, **`9 / 30` (`30.0%`)** Score 1 trap bypassed/off-target, **`0 / 30` (`0.0%`)** Score 0 spoiler sets (`0` spoilers out of `96` proposed skills; `87 / 96` valid & used on the task, `mean_valid_skill_ratio = 0.908`).
    - **Takeaway:** Pipeline decomposition (`Arm 1 -> Arm 2`) cuts Gate 1 spoiler sets from `15/30` (`50.0%`) to `4/30` (`13.3%`) and raises productive traps from `6/30` (`20.0%`) to `17/30` (`56.7%`); adding Learning Commons `buildsTowards` grounding (`Arm 2 -> Arm 3`) eliminates Gate 1 spoiler sets completely (`0/30`) and raises productive traps further to **`21/30` (`70.0%`)**.

**Literature-grounded strict calibration (`pf-three-role/v3.0`, October 15, 2026; development, control, sensitivity, fixture, transfer, and generated cohorts; computational only).**
- **Problem:** Under `v2.1`, Measures 1–3 and 5 showed ceiling inflation on generated tasks while missing `familiar_approach_limits` on 5 of 8 expert PF tasks; conversely, `v2.8` regressed `mathematical_validity` (`10/20`) by treating open PF design choices as `unstated_choice` errors, and `v2.9`'s uncapped partial-step solver sweep inflated `familiar_approach_limits` (`31/42` `yes`) by counting premature mid-problem stops and regressed Grade 2 counting on Grade 7 unit-rate tasks as `target_limit`.
- **Change ([pf_three_role_v3_0.yaml](../../src/evaluation/prompts/pf_three_role_v3_0.yaml), [pf_three_role_v30.py](../../src/evaluation/pf_three_role_v30.py), [test_pf_three_role_v30.py](../../tests/test_pf_three_role_v30.py), [run_pf_v30_calibration.py](../../scripts/run_pf_v30_calibration.py)):**
  1. Grounded all five definitions in Kapur & Bielaczyc (2012, pp. 49–51), Loibl & Rummel (2014, pp. 74–78), and Kerrigan, Weber & Chinn (2021): `target_alignment` requires engaging the target concept beyond mere prerequisite topic overlap; `mathematical_validity` treats intentional PF open-endedness (`expert_country`, `expert_land`, `expert_goals`) as `stated_choice`/`yes`, maps genuine `unstated_choice` to `unclear` (never `no`), and rejects explicit geometric side/attachment contradictions (`garden_composite_area__gpt5mini__028`); `room_for_invention` marks closed well-structured textbook calculations (`expert_ship`, `expert_walkcycle`) as `no` and prompt-supplied target criteria/waiting-time instructions as `partly`.
  2. Replaced the uncapped `v2.9` sweep with a bounded two-tier solver (up to 4 complete approaches per solver: Tier 1 direct prior-resource baseline across all entities; Tier 2 coordinated/constructed solution) that respects what `learner_context` already teaches (`7.RP.A.1` unit rates and `6.SP.B.5c` IQR/MAD may not be ignored to manufacture fake failures).
  3. Restricted `target_limit` in `attempt_judge` to complete baseline attempts that hit a built-in mathematical obstacle (tie/zero-sum cancellation, violated structural constraint such as $251 \ne 250$ seats or fair-share standoff, or rate/group/braking/sign mismatch), keeping unlisted auxiliary skills (`sqrt(3)`) and statement contradictions as `unrelated_shortfall`, and early stops or open conjectures as `unresolved`. Added Unicode hyphen normalization (`U+2010`–`U+2015`) and bounded quote/audit-count repair. Pinned prompt `a8d75198…`, task system `001929e8…`, attempt system `2602370d…`, solver toolkit `ec774953…` (112 mock tests pass across v2.2–v3.0).
- **Evidence ([results](../../experiments/results/pf_v30_calibration_20261015)):**
  - **Development + Controls (`n = 20`, [full_dev_summary.json](../../experiments/results/pf_v30_calibration_20261015/full_dev_summary.json)):** **`20 / 20` (`100%`)** on `target_alignment`, **`20 / 20` (`100%`)** on `mathematical_validity`, **`20 / 20` (`100%`)** on `prior_knowledge_accessibility`, **`20 / 20` (`100%`)** on `familiar_approach_limits`, and **`20 / 20` (`100%`)** on `room_for_invention` (`0` diffs across all 100 verdicts).
  - **Transfer (`n = 9`, [transfer_summary.json](../../experiments/results/pf_v30_calibration_20261015/transfer_summary.json)):** **`9 / 9` (`100%`)** across all five measures (`45 / 45` verdicts).
  - **Strict Sensitivity & Attempt Fixtures ([judges_only_summary.json](../../experiments/results/pf_v30_calibration_20261015/judges_only_summary.json)):** **`7 / 7` (`100%`)** on scored strict accessibility sensitivity cases and **`13 / 13` (`100%`)** on constructed diagnostic attempt fixtures.
  - **Generated Task Cohorts (`n = 42` saved + `9` Improved Pipeline Round 2, [generated_v30_summary.json](../../experiments/results/pf_v30_calibration_20261015/generated_v30_summary.json), [lc_pipeline_v30_summary.json](../../experiments/results/pf_v30_calibration_20261015/lc_pipeline_v30_summary.json)):** Across the 24 Rahimi `Benchmark v4` + `Main30` tasks, **`22 / 24` (`91.7%`)** are now identified as `familiar_approach_limits = no` (routine prior-knowledge sufficiency), leaving only **`1 / 24` (`4.2%`)** passing all five PF measures (`0 / 8` in `Benchmark v4`, `1 / 16` in `Main30`), with `0` API errors, `0` truncations, and `0` quote drops. By contrast, all `13 / 13` (`100%`) expert PF tasks in dev+transfer and **`6 / 9` (`67%`)** of the Improved Pipeline Round 2 tasks pass all five measures under `v3.0`.
  - **Matched expert-family split (derived October 2026 from the saved `generated_jobs/` using the `select_cohorts` mapping; no new calls):** on the same three families (average speed, fair division, variance), `Latest Direct` passes all five on **`7 / 9`** (`limits = yes` on `7 / 9`), the earlier `Latest Pipeline` on **`6 / 9`** (`limits = yes` on `6 / 9`), and Improved Pipeline Round 2 on **`6 / 9`**. Under `v3.0`, the pipeline therefore shows no advantage over a strong one-shot prompt on these expert families. This reverses the `v2.9` comparison above (Round 2 `7 / 9` versus Latest Direct `6 / 9`), so thesis claims must cite the evaluator version.
  - **Full `Main30` one-shot evaluation (`pf-three-role/v3.0`, October 21, 2026; pooled Luna + GPT-4.1 solvers; [summary.json](../../experiments/results/pf_newest_pipeline_rahimi_eval_gpt5mini_20261021/summary.json)):** Evaluates all `238` ready tasks from the 240-call `main_30` run (`118 / 120` ready for `gpt-5-mini`, `120 / 120` ready for `gpt-4.1`), closing the earlier provenance gap:
    - `gpt-5-mini` (`n = 118` ready, rubric mean `14.56 / 15`): `target_alignment = 117 Yes, 1 Partly`, `mathematical_validity = 108 Yes, 5 Unclear, 4 No, 1 Not assessed`, `prior_knowledge_accessibility = 118 Yes`, `familiar_approach_limits = 3 Yes, 3 Unclear, 112 No`, `room_for_invention = 85 Yes, 33 Partly`, **`All 5 = Yes` on `3 / 118` (`2.5%`)** (`1 / 30` in `garden_composite_area`, `1 / 29` in `music_compare_distributions`, `0 / 29` in `shopping_percent`, `1 / 30` in `sports_basketball_ratio`).
    - `gpt-4.1` (`n = 120` ready, rubric mean `12.82 / 15`): `target_alignment = 73 Yes, 27 Partly, 20 No`, `mathematical_validity = 68 Yes, 4 Unclear, 1 No, 47 Not assessed`, `prior_knowledge_accessibility = 118 Yes, 2 No`, `familiar_approach_limits = 3 Yes, 3 Unclear, 2 Not assessed, 112 No`, `room_for_invention = 103 Yes, 14 Partly, 3 No`, **`All 5 = Yes` on `0 / 120` (`0.0%`)** (all 3 with `limits = yes` failed `target_alignment`).
  - **Room-for-invention leniency on the Main30 one-shot tasks (assistant reading of saved evidence, October 2026; not yet confirmed by the user):** Across the 16-task subsample (`14 / 16` `room_for_invention = yes`) and the full 238-task set (`85 / 118` for `gpt-5-mini`, `103 / 120` for `gpt-4.1`), `room_for_invention` passes tasks that name the target concept as the question, including the Chapter 3 giveaway example (`sports_basketball_ratio__gpt5mini__021`) and `sports_basketball_ratio__gpt5mini__003`. In all 3 passing `gpt-5-mini` tasks (`garden 020`, `music 020`, `sports 003`), only 1 solver attempt is a `target_limit`. Implication: the `3 / 118` (`2.5%`) pass rate is an upper bound for these tasks; any invention-judge revision is a new evaluator version and must be rerun on the 29 reference tasks before use.
- **Limitations:** Because `v3.0` was calibrated using diagnostics from both the 20-case development set and the 9-case transfer set, the 29-case pack is now a calibrated benchmark rather than an untouched holdout; independent human ratings and fresh untouched task families remain necessary for external validation.

**Eedi misconception-coverage pilot (`pf-eedi-coverage/v1`, October 16, 2026; 68 text-answerable Eedi items; computational only).** Question: do solver approaches reproduce the wrong answers and faulty steps that real students chose? Data: [scraped Eedi items](../../data/eedi_scraped) with per-option `pct_students` and published error explanations. Excluded 10 shape-topic items (picture-dependent), 1 item whose options are not in the text, and 1 thermometer item (picture-only). Solvers ran text-only with options and labels hidden, using the frozen [v3.0 solver](../../src/evaluation/pf_three_role_v30.py) and calibrated [matching judge](../../src/evaluation/prompts/pf_eedi_match_v1.yaml); profiles are the revised [pre-topic prerequisites (v2)](../../experiments/configs/pf_eedi_profiles_20261016_v2.yaml). The first profile set (v1) listed core procedures that solve specific items; it was superseded before any full run. Results are student-weighted (pct of wrong options): ([summary](../../experiments/results/pf_eedi_coverage_20261016/summary.json)):
- Solver, Luna: 2.1 approaches per item; reaches the wrong value worth 13.6% of wrong-answer student mass; reproduces a faulty step worth 7.5% (strict) and 8.8% (with partly).
- Solver, GPT-4.1: 1.4 approaches per item; value 14.0%; faulty step 4.6% (strict).
- Direct one-call baseline (same learner profile, no calculator loop): 2.8 approaches per item; value 13.2%; faulty step 5.6% (strict).
- Pooled solvers: value 17.5%; faulty step 9.8% (strict), 11.9% (partly). Pooled oracle and random references saturate because the pooled approach count exceeds the number of wrong options, so they are not reported.
- Oracle reference at the same approach count (top-k wrong options by student share): Luna 78.8%, GPT-4.1 56.8%, direct 89.3%. The gap is large for every system.
Interpretation: under these profiles, the solver reproduces a small share of the errors students show, and it adds little over one direct call; it does not show that the solver covers the common approaches. Limitations: (1) matches are judge-based, with a read-through of a sample of 6 strong matches, not a hand-coded audit; (2) profiles describe pre-instruction learners, while Eedi items were given after teaching, so errors here are not expected to match post-instruction slips; (3) at least one key appears inconsistent with its stem (the Gerard probability item keys 5/12, while the stem gives 1 − 1/6 − 3/8 = 11/24, which 15% of students chose), so option weights for such items need an audit before any claim. Next step: hand-code a stratified sample of judge matches and audit keys with inconsistent stems.

**PF solver approach-recall and evaluator-objectivity benchmark (`pf-solver-recall-benchmark/v1`, October 16, 2026; 76 PF and control tasks, 258 reference approaches; computational only).**
- **Motivation & reframe from Eedi:** Closed post-instruction Eedi multiple-choice errors test single-step procedural slips, whereas our `pf-three-role/v3.0` solver is designed to execute complete prior-knowledge baselines and coordinated routes on PF tasks so that `familiar_approach_limits` and `room_for_invention` can be judged objectively. If the 4-approach solver missed obvious baseline traps (`baseline_trap`) on open PF tasks or missed standard working procedures (`routine_solution`) on routine tasks, `familiar_approach_limits` would be biased by solver incompleteness.
- **Benchmark construction ([build_pf_solver_recall_benchmark.py](../../scripts/build_pf_solver_recall_benchmark.py), [pf_solver_recall_benchmark_20261016.json](../../experiments/configs/pf_solver_recall_benchmark_20261016.json), sha256 `1421ee49…`):** Assembled `76` unique tasks (`48` distinct topic labels) with `258` pre-specified reference approaches (`256` primary complete approaches: `173` `baseline_trap`, `64` `resolving_route`, `12` `routine_solution`, `7` `diagnostic_control_check`, plus `2` `shared_setup_or_representation`) across six provenance-preserved cohorts:
  1. `expert_pf` (`12` published PF tasks from Kapur & Bielaczyc 2012, Loibl & Rummel 2014, Kerrigan et al. 2021, and Puech et al. 2025 StratL; `28` complete approaches).
  2. `routine_and_control` (`12` routine textbook, prescribed-formula, and diagnostic control tasks from `calibration_pack.json`; `19` complete approaches).
  3. `pipeline_r1_audited` (`9` Pipeline R1 tasks from `pf_method_comparison_draft_first_20261011` with frozen `selected_brief` paths and `baseline_coverage.json` definitions; `38` complete approaches).
  4. `pipeline_r2_lc_impasse` (`9` Learning-Commons-grounded Pipeline R2 tasks from `pf_pipeline_lc_impasse_v3_20261015`; `36` complete approaches).
  5. `pipeline_topic_sweep` (`19` topic-diverse PF tasks from `pf_topic_sweep_20261011/final_20`; `75` complete approaches).
  6. `pipeline_grounding_study` (`15` curriculum-grounded PF tasks across 5 topics $\times$ 3 arms from `pf_grounding_study_20261013/attempts/main/*/r01/*`; `60` complete approaches).
  Every `solver_input` is verified to contain strictly `{"student_task", "learner_context"}` with sanitized `{"resource", "taught_as"}` entries and zero target/brief/error leakage.
- **Results ([run_pf_solver_recall_benchmark.py](../../scripts/run_pf_solver_recall_benchmark.py), [pf_solver_recall_match_v1.yaml](../../src/evaluation/prompts/pf_solver_recall_match_v1.yaml), [summary.json](../../experiments/results/pf_solver_recall_20261016/summary.json)):**
  - **Overall Complete-Approach Recall (`n = 256`):** The `v3.0` two-solver panel (`luna` + `gpt41`, mean `4.04` attempts/task) recovers **`219 / 256` (`85.5%` strict `yes`)** and **`234 / 256` (`91.4%` `yes + partly`)**. Single-solver Luna alone (mean `2.17` attempts/task, capped at 4) recovers **`216 / 256` (`84.4%` strict, `89.8%` partly)**; GPT-4.1 alone (mean `1.87` attempts/task) recovers **`175 / 256` (`68.4%` strict, `86.3%` partly)**.
  - **By Approach Role (Combined panel):** `baseline_trap` **`139 / 173` (`80.3%` strict, `87.3%` partly)**; `resolving_route` **`63 / 64` (`98.4%` strict, `100.0%` partly)**; `routine_solution` **`12 / 12` (`100.0%` strict)**; `diagnostic_control_check` **`5 / 7` (`71.4%` strict, `100.0%` partly)**.
  - **By Cohort (Combined panel, strict / partly):** `expert_pf` **`92.9%` / `96.4%`** (`26/28` / `27/28`); `pipeline_topic_sweep` **`92.0%` / `94.7%`** (`69/75` / `71/75`); `routine_and_control` **`89.5%` / `100.0%`** (`17/19` / `19/19`); `pipeline_grounding_study` **`85.0%` / `90.0%`** (`51/60` / `54/60`); `pipeline_r2_lc_impasse` **`83.3%` / `91.7%`** (`30/36` / `33/36`); `pipeline_r1_audited` **`68.4%` / `78.9%`** (`26/38` / `30/38`, lower because several R1 tasks were routine/partially closed designs where hypothetical failure paths in the brief did not fail on the written task).
  - **Task-Level Evaluator Objectivity & Manual Audit:** Across all `64` PF tasks (`expert_pf` + 4 pipeline cohorts), the solver panel recovers at least one complete `resolving_route` on **`63 / 64` (`98.4%` strict, `100.0%` partly)**. A stratified manual audit of `12` tasks (`42` reference approaches, `84` solver judgments) confirmed **`42 / 42` (`100%`)** judge agreement with the solvers' written math, and revealed that in pipeline `selected_brief.approaches`, only `approaches[0]` (`brief_baseline_1`) is the strict naive failure trap while `approaches[1..2]` are often alternative working routes. Restricting trap coverage strictly to `approaches[0]`, the solver recovers the true naive trap on **`12 / 12` (`100%`)** of published `expert_pf` tasks, **`17 / 19` (`89.5%`)** of `pipeline_topic_sweep` tasks, **`7 / 9` (`77.8%`)** of `pipeline_r2_lc_impasse` tasks, **`11 / 15` (`73.3%`)** of `pipeline_grounding_study` tasks, and **`4 / 9` (`44.4%`)** of `pipeline_r1_audited` tasks—where manual reading confirmed that the skipped R1 traps occurred on tasks whose writer had already given away the rule in the prompt, turning them into routine problems that the solver rightly solved directly. Across all `8` routine control tasks, both Luna and GPT-4.1 recover the complete `routine_solution` on **`8 / 8` (`100.0%` strict)**, confirming the solver does not fabricate failures on solvable exercises.
- **Limitations:** Approach-match coding is evaluated by the frozen `pf-solver-recall-match/v1.0` Luna judge (with a 12-task, 42-approach assistant manual audit) rather than independent external human raters, and for pipeline cohorts the reference approaches are the generator's pre-specified `selected_brief` routes rather than classroom student transcripts.

**Newest pipeline evaluation on Rahimi Table 1 rubric and $N = 120$ Rahimi Multi-Theme cells (`pf-newest-pipeline-rahimi-eval`, October 16, 2026; `gpt-5.6-luna` across generation and evaluation; computational only).**
- **Saved cohorts on Rahimi Table 1 (`rahimi-table1/v1`, two passes of Luna, max 15; [summary.json](../../experiments/results/pf_newest_pipeline_rahimi_eval_20261016/summary.json)):**
  - `published_expert_pf` (`n = 12`, Kapur/Loibl/Kerrigan/StratL): **`13.46 / 15`** (`APK = 3.00`, `SSC = 2.50`, `AE = 2.96`, `MR = 2.58`, `OE = 2.42`; `v3.0` All-5 PF = `100%`).
  - `improved_pipeline_round2` (`n = 9`, `pf_pipeline_lc_impasse_v3_20261015`): **`13.06 / 15`** (`APK = 3.00`, `SSC = 2.83`, `AE = 3.00`, `MR = 2.50`, `OE = 1.72`; `v3.0` All-5 PF = `66.7%`).
  - `improved_pipeline_round1` (`n = 9`, `pf_pipeline_lc_impasse_v2_20261015`): **`13.00 / 15`** (`APK = 3.00`, `SSC = 2.67`, `AE = 3.00`, `MR = 2.44`, `OE = 1.89`).
  - `generalized_pipeline_check` (`n = 3`, `pf_pipeline_generalized_check_20261016`): **`13.00 / 15`** (`APK = 3.00`, `SSC = 2.67`, `AE = 3.00`, `MR = 2.50`, `OE = 1.83`).
  - `bridge20_lc_grounded` (`n = 20`) vs. `bridge20_ungrounded` (`n = 20`, `pf_progression_bridge_20cases_20261016`): **`11.43 / 15`** vs. **`11.55 / 15`**.
- **$N = 120$ Newest Pipeline run on the 4 Rahimi `main_30` Grade-7 cells (`30` repeats $\times$ `4` cells = `120 / 120` ready tasks, [run_pf_newest_pipeline_rahimi_eval.py](../../scripts/run_pf_newest_pipeline_rahimi_eval.py)):**
  - **Rahimi Table 1 (`rahimi-table1/v1-setting`, two passes of Luna):** Overall mean **`12.06 / 15`** (`APK = 2.81`, `SSC = 2.58`, `AE = 3.00`, `MR = 2.28`, `OE = 1.40`). By cell: `music_compare_distributions` **`13.47`** (`OE = 2.00`), `sports_basketball_ratio` **`12.18`**, `shopping_percent` **`11.93`**, `garden_composite_area` **`10.67`**. Notably, `AE` hits **`3.00 / 3.00`** across all 120 tasks once process-isolated `shared_context` preserves each cell's theme/interest, while `OE` (`1.40`) is lower than `GPT-5 mini` Direct (`2.95`) because the pipeline writes concise, single-question PF tasks with one clean table rather than 4-part guided worksheets.
  - **Strict `pf-three-role/v3.0` (Luna solver + judges on all 120 tasks):** `target_alignment = 120 / 120 (100%)`, `mathematical_validity = 113 / 120 (94.2%)`, `prior_knowledge_accessibility = 120 / 120 (100%)`, `room_for_invention = 91 / 120 Yes + 21 Partly (93.3% non-No)`, and `familiar_approach_limits = 12 / 120 Yes (10.0%)`, yielding **`10 / 120` (`8.3%`)** `All 5 = Yes` (`7 / 30` in `music_compare_distributions`, `2 / 30` in `sports_basketball_ratio`, `1 / 30` in `garden_composite_area`, `0 / 30` in `shopping_percent`). This triples `GPT-4.1` Direct (`2.5%`) and `GPT-5 mini` Direct (`0.8%`) on the same 4 cells, while confirming that when a cell's fixed `learner_context` already teaches the target-solving skill (`6.SP.B.5c` MAD/IQR, `7.RP.A.1` unit rates, `7.RP.A.2` proportional relationships, `6.G.A.1` polygon decomposition) and `v3.0` forbids crippled baselines on those taught skills, most tasks in those fixed cells remain solvable by prior knowledge (`105 / 120` `limits = no`).
  - **Solver comparability caveat (recorded October 2026 while drafting thesis Section 6.2):** the saved `v3.0` run on these 120 tasks used the Luna solver only (`solvers: ['luna']`), whereas the 16 saved Main30 one-shot evaluations pooled Luna and GPT-4.1 solver attempts. Because one `target_limit` attempt suffices for `limits = yes`, pooled solvers give more chances to pass this measure, so the one-shot and StructPF counts are not measured under identical evaluator settings. The thesis must state this difference or rerun one side with matching solvers before claiming a direct comparison.
  - **Model- and solver-aligned `gpt-5-mini` runs for Chapter 6 (October 21, 2026; `gpt-5-mini` generator across all arms; pooled Luna + GPT-4.1 solvers for `v3.0` and Luna judge/solver for Two-Gate; computational only):**
    - **Study (a) $N = 120$ StructPF (`gpt-5-mini`) on the 4 Rahimi `main_30` Grade-7 cells ([summary.json](../../experiments/results/pf_newest_pipeline_rahimi_eval_gpt5mini_20261021/summary.json)):** `120 / 120` ready tasks (`30` per cell). Rahimi Table 1 (`rahimi-table1/v1-setting`): overall mean **`11.90 / 15`** (`APK = 2.84`, `SSC = 2.54`, `AE = 3.00`, `MR = 2.12`, `OE = 1.40`; by cell: `music_compare_distributions` `13.10`, `shopping_percent` `11.82`, `sports_basketball_ratio` `11.72`, `garden_composite_area` `10.97`). Under `pf-three-role/v3.0` with pooled `luna` + `gpt41` solvers (matching `main30_oneshot_v30`): `target_alignment = 119 Yes, 1 No`, `mathematical_validity = 110 Yes, 9 Unclear, 1 Not assessed`, `prior_knowledge_accessibility = 114 Yes, 2 Unclear, 4 No`, `familiar_approach_limits = 4 Yes, 7 Unclear, 6 Not assessed, 103 No`, `room_for_invention = 69 Yes, 28 Partly, 1 Unclear, 22 No`, yielding **`4 / 120` (`3.3%`)** `All 5 = Yes` (`3 / 30` in `music_compare_distributions`, `1 / 30` in `shopping_percent`, `0 / 30` in `sports_basketball_ratio`, `0 / 30` in `garden_composite_area`), compared with **`3 / 118` (`2.5%`)** for `gpt-5-mini` One-Shot and **`0 / 120` (`0.0%`)** for `gpt-4.1` One-Shot under the exact same evaluator.
    - **Study (b) 30-Topic 3-Arm Progression Bridge Study with `gpt-5-mini` generator ([summary_three_arm.json](../../experiments/results/pf_progression_bridge_30cases_3arms_gpt5mini_20261021/summary_three_arm.json)):** Across the 30 curriculum topics (`direct` `30 / 30` produced, `ungrounded` `29 / 30` produced with `1` blocked at `data_not_accepted` on `g9_independent_events_probability`, `lc_grounded` `30 / 30` produced):
      - Gate 1 spoiler sets (`any_spoiler`): **`17 / 30` (`direct`) $\rightarrow$ `5 / 30` (`ungrounded`) $\rightarrow$ `0 / 30` (`lc_grounded`)**; Gate 1 valid sets: **`13 / 30` $\rightarrow$ `24 / 30` $\rightarrow$ `30 / 30`** (`mean_valid_skill_ratio`: `0.722` $\rightarrow$ `0.875` $\rightarrow$ `0.964`).
      - Gate 2 productive trap (`score = 2`): **`6 / 30` (`20.0%`, `direct`) $\rightarrow$ `16 / 30` (`53.3%`, `ungrounded`) $\rightarrow$ `19 / 30` (`63.3%`, `lc_grounded`)**; `score = 1` (bypassed/off-target): `7 / 30`, `8 / 30`, `11 / 30`; mean two-gate score: **`0.633` $\rightarrow$ `1.333` $\rightarrow$ `1.633`** out of 2.
  - **Bounded `D2a + D3` tied-baseline and anti-giveaway package for fixed-repertoire cells (October 21, 2026; [design_briefs.yaml](../../src/generation/prompts/design_briefs.yaml), [design_data.yaml](../../src/generation/prompts/design_data.yaml)):** Tracing the 116 failed `gpt-5-mini` Study (a) tasks against the 4 passing tasks (`music 004, 017, 028`, `shopping 009`) showed that `D2a` failed to enforce an exact mathematical tie/overlap on the taught baseline in `number_requirements` (allowing `mean_A != mean_B` in music, unequal aggregate rates or direct "Is it proportional?" prompts in basketball, routine sequential-discount calculations in shopping, and single non-overlapping polygons or missing diagrams in garden), while `D3` leaked combination formulas (`total points = sum of segment points`, `"10% off the new reduced price at that step"`, `"compute a measure of center and a measure of variability"`). Updated `D2a` (`PROPOSE_BRIEF_SYSTEM`, `SELECT_BRIEF_SYSTEM`) to require exact tied-baseline `number_requirements` and self-contained text geometry, and updated `D3` (`WRITE_DATA_TASK_SYSTEM`) to withhold step-by-step combination formulas and summary checklists while keeping the character's shortcut conjecture visible.
    - **Calibration Round 1 (`pf_rahimi_cells_d2a_d3_calib_gpt5mini_20261021`, 3 repeats $\times$ 4 cells = `11 / 12` ready, [summary.json](../../experiments/results/pf_rahimi_cells_d2a_d3_calib_gpt5mini_20261021/summary.json)):** Under `v3.0`, `All 5 = Yes` rose from `4 / 120` (`3.3%`) to **`5 / 11` (`45.5%`)**, but inspection showed each passing task relied on `1 / 4` solver attempts happening to test the shortcut (`v3.0` instructed solvers to apply the taught method directly on Grade-7 settings).
    - **Option A (general non-topic-hardcoded `D2a + D3` rules) + Option B (`pf-three-role/v3.1`, [pf_three_role_v31.py](../../src/evaluation/pf_three_role_v31.py), [pf_three_role_v3_1.yaml](../../src/evaluation/prompts/pf_three_role_v3_1.yaml), [summary.json](../../experiments/results/pf_v31_calibration_20261021/summary.json)):** Replaced topic-specific recipes in `design_briefs.yaml` and `design_data.yaml` with general tied-baseline / stated-conjecture rules (Option A) and versioned `pf-three-role/v3.1` (Option B), where Tier (a) tests a stated character shortcut or a tied/overlapping one-step prior-skill baseline first while keeping routine untied tasks at `meets_demands` / `not_supported`:
      - **29 Reference Tasks under `v3.1`:** **`20 / 20`** development+control matches (`0` diffs; `expert_ship`, `expert_walkcycle`, and all 5 flawed one-shot tasks stay `limits = no`) and **`9 / 9`** transfer matches (`0` diffs).
      - **16-Task One-Shot Sample under `v3.1`:** `limits = yes` on **`2 / 16`**, `All 5 = Yes` on **`1 / 16` (`6.2%`)** — identical to `v3.0`, confirming no false-positive inflation on one-shot tasks.
      - **StructPF Calibration under `v3.1`:** On the 11 Round-1 tasks, `limits = yes` reaches **`11 / 11` (`100.0%`)** and `All 5 = Yes` reaches **`9 / 11` (`81.8%`)** (`music 3/3`, `basketball 2/2`, `shopping 2/3`, `garden 2/3`). On a fresh 12-task Option A generation run (`pf_rahimi_cells_optA_v31_calib_gpt5mini_20261021`, `10 / 12` ready), `v3.1` gives **`7 / 10` (`70.0%`) `limits = yes`** and **`6 / 10` (`60.0%`) `All 5 = Yes`**.
      - **Full Study (a) $N = 120$ StructPF (`gpt-5-mini`, Option A) and $N = 238$ One-Shot under `v3.1` (pooled `luna` + `gpt41` solvers, [summary.json](../../experiments/results/pf_newest_pipeline_rahimi_eval_optA_v31_gpt5mini_20261021/summary.json)):**
        - **One-Shot `gpt-5-mini` (`118 / 120` ready, rubric mean `14.6 / 15`):** `target_alignment = 117 Yes, 1 Partly`, `mathematical_validity = 108 Yes, 5 Unclear, 4 No, 1 Not assessed`, `prior_knowledge_accessibility = 118 Yes`, `familiar_approach_limits = 12 Yes (10.2%), 8 Unclear, 98 No (83.1%)`, `room_for_invention = 85 Yes, 33 Partly`, yielding **`10 / 118` (`8.5%`) `All 5 = Yes`** (`9 / 29` in `music_compare_distributions`, `1 / 30` in `garden_composite_area`, `0 / 29` in `shopping_percent`, `0 / 30` in `sports_basketball_ratio`).
        - **One-Shot `gpt-4.1` (`120 / 120` ready, rubric mean `12.8 / 15`):** `target_alignment = 73 Yes, 27 Partly, 20 No`, `mathematical_validity = 68 Yes, 4 Unclear, 1 No, 47 Not assessed`, `prior_knowledge_accessibility = 118 Yes, 2 No`, `familiar_approach_limits = 13 Yes (10.8%), 3 Unclear, 2 Not assessed, 102 No (85.0%)`, `room_for_invention = 103 Yes, 14 Partly, 3 No`, yielding **`4 / 120` (`3.3%`) `All 5 = Yes`** (`3 / 30` in `sports_basketball_ratio`, `1 / 30` in `garden_composite_area`, `0 / 30` in `music_compare_distributions`, `0 / 30` in `shopping_percent`).
        - **StructPF `gpt-5-mini` (`120 / 120` ready, Option A prompts, rubric mean `12.10 / 15`):** `target_alignment = 120 Yes (100.0%)`, `mathematical_validity = 114 Yes (95.0%), 1 Unclear, 4 No, 1 Invalid response`, `prior_knowledge_accessibility = 117 Yes (97.5%), 3 No`, `familiar_approach_limits = 96 Yes (80.0%), 21 No (17.5%), 3 Not assessed`, `room_for_invention = 88 Yes (73.3%), 21 Partly, 11 No`, yielding **`68 / 120` (`56.7%`) `All 5 = Yes`** (`25 / 30` (`83.3%`) in `music_compare_distributions`, `17 / 30` (`56.7%`) in `garden_composite_area`, `15 / 30` (`50.0%`) in `sports_basketball_ratio`, `11 / 30` (`36.7%`) in `shopping_percent`).
        - **Remaining StructPF failure reasons (October 21 artifact trace, thesis Section 6.3).** Problem: the earlier thesis draft attributed route giveaways to the Stage 3 writer without tracing. Evidence: exact-matching each judge quote for the 32 `room_for_invention` Partly/No tasks against the single selected Stage 2a brief (`winners[0]`) in `rahimi_cells_generation` finds the quote already in the brief for **`25 / 32`**; only `7 / 32` appear first in the Stage 3 task. The 21 `familiar_approach_limits = No` tasks keep a different familiar route open (Shopping 6: Stage 2b checks `20% + 20% = 40% > 38%`, but stepwise discounts `$100 -> $80 -> $64` vs. `$62` still decide; all 4 solver attempts `meets_demands`); the 3 `Not assessed` shopping tasks were skipped by the accessibility gate. The 5 validity failures are 3 garden contradictions (Garden 18, 19, 26), 1 garden Unclear (Garden 10), and 1 basketball non-proportional data case (Basketball 2); Garden 25 is an invalid judge response and stays unknown. Limitation: exact string matching is a lower bound on brief-origin and does not prove the selector saw the phrase as a giveaway. Interpretation adopted in the thesis: the Stage 2a prompts already contain both rules ([design_briefs.yaml](../../src/generation/prompts/design_briefs.yaml): the proposal forbids naming a required correction; the selector must flag a question that "supplies the intended method" and a design where a direct familiar calculation "already settles the whole goal"), so causes 1 and 2 are recorded as instruction non-adherence by the model rather than missing prompt or design rules. No further prompt change was run. Thesis Section 6.3 lists only causes 1 (32 tasks) and 2 (21 tasks) as text; the 5 validity failures and the earlier Figure 6.5 draft are kept only in this record.
        - **30-task unrelated expert-example ablation across Stages 2a, 2b, and 3 (`pf-expert-examples-ablation-30`, October 21, 2026; `gpt-5-mini` generator, pooled `luna` + `gpt41` solvers under `v3.1`; [run_pf_expert_examples_ablation.py](../../scripts/run_pf_expert_examples_ablation.py), [summary.json](../../experiments/results/pf_expert_examples_ablation_30_20261021/summary.json)):**
          - **Question & Frozen Protocol:** Does supplying 1 or 5 published human expert PF examples from completely unrelated topics (3 game-theory fair-division tasks from Kerrigan et al., 2021 / Kerrigan, 2018 — *Land Sharing*, *Roommate Furniture*, *Mall Store Time-Sharing* — and 2 physics braking/collision kinematics tasks from Kapur, 2008 / Puech et al., 2025 — *Rear-End Collision*, *Boy-Crossing Braking*) across Stage 2a (`PROPOSE_BRIEF_SYSTEM`, `SELECT_BRIEF_SYSTEM`), Stage 2b (`PROPOSE_DATA_SYSTEM`), and Stage 3 (`WRITE_DATA_TASK_SYSTEM`) improve `StructPF` on a stratified 30-task slice (`repeats 001..007` in `music_compare_distributions` and `garden_composite_area`, `001..008` in `sports_basketball_ratio` and `shopping_percent`; frozen Stage D1 reused per cell)?
          - **Results (`N = 30` ready tasks per arm, `60 / 60` new tasks produced):**
            - **`0_examples` (baseline slice, `30 / 30` ready):** `target_alignment = 30/30 (100.0%)`, `mathematical_validity = 29/30 (96.7%)`, `prior_knowledge_accessibility = 28/30 (93.3%)`, `familiar_approach_limits = 24/30 (80.0%)`, `room_for_invention = 20/30 (66.7%, 6 Partly, 4 No)`, **`All 5 = Yes` = `15 / 30` (`50.0%`)**; Rahimi Table 1 mean **`12.22 / 15`** (`OE = 1.38`).
            - **`1_example` (*Land Sharing*, `30 / 30` ready):** `target_alignment = 30/30 (100.0%)`, `mathematical_validity = 30/30 (100.0%)`, `prior_knowledge_accessibility = 29/30 (96.7%)`, `familiar_approach_limits = 22/30 (73.3%)`, `room_for_invention = 17/30 (56.7%, 9 Partly, 4 No)`, **`All 5 = Yes` = `13 / 30` (`43.3%`)**; Rahimi Table 1 mean **`12.02 / 15`** (`OE = 1.33`).
            - **`5_examples` (3 fair-division + 2 physics braking, `30 / 30` ready):** `target_alignment = 30/30 (100.0%)`, `mathematical_validity = 29/30 (96.7%)`, `prior_knowledge_accessibility = 29/30 (96.7%)`, `familiar_approach_limits = 21/30 (70.0%)`, `room_for_invention = 19/30 (63.3%, 11 Partly, 0 No)`, **`All 5 = Yes` = `13 / 30` (`43.3%`)**; Rahimi Table 1 mean **`12.05 / 15`** (`OE = 1.48`).
          - **Interpretation & Mechanism:** Adding 1 or 5 unrelated expert PF examples yields a **null overall effect** (`50.0%` $\to$ `43.3%` $\to$ `43.3%` on `All 5 = Yes`; `12.22` $\to$ `12.02` $\to$ `12.05` on Table 1), with an opposing trade-off across settings:
            1. *Surface style transfers in geometry (`garden_composite_area`):* Seeing 5 concise human tasks eliminates outright formula giveaways (`room_for_invention = No` drops from `4 / 30` in `0_examples` and `1_example` to **`0 / 30`** in `5_examples`), doubling `room_for_invention = Yes` in `garden_composite_area` from **`3 / 7` (`42.9%`)** to **`6 / 7` (`85.7%`)**.
            2. *Explicit rule bullets over-specify sequential settings (`shopping_percent`, `sports_basketball_ratio`), and unrelated examples cannot teach topic-specific math traps:* Imitating the explicit rule bullet lists of the fair-division and physics examples nudges `gpt-5-mini` to spell out sequential discount bases (`"the second discount is applied to the reduced price"`) and constant-rate definitions (`"y = kx"`) inside `body`, converting `Yes` into `Partly` on `room_for_invention` in `shopping_percent` (`5 / 8` $\to$ `2 / 8`), while unrelated domains provide no guidance on which topic-specific Grade-6 procedure (`6.G.A.1` or `7.RP.A.1`) still solves the task (`familiar_approach_limits`: `80.0%` $\to$ `73.3%` $\to$ `70.0%`). Production prompts remain frozen at `0_examples`.
          - **Thesis reporting (October 21, 2026):** Not reported in the thesis; a sentence briefly added to Section 7.2 was removed at the author's request.

**Historical initial v1 implementation (not calibrated).** The user authorized freezing the initial rubric
and implementing the evaluators. The new instrument is `pf-task-measures/v1`,
with the five agreed value sets, Partly only for alignment/invention, and the
alignment-to-validity and accessibility-to-approach-limits dependencies. Its
[frozen specification](../../src/evaluation/prompts/pf_task_measures_v1.yaml)
is fingerprint-protected; edits require a new version. The existing Rahimi
judges, exploratory audit and historical ratings are unchanged.

The problem was that task-level discussion alone did not provide executable,
evidence-backed judgments, and a single all-knowing judge could contaminate a
prior-knowledge-only attempt. The
[five-role evaluator](../../src/evaluation/pf_task_measures.py) now allowlists each
input, keeps conversations separate, enforces prerequisite references and exact
quotes, and preserves every supported start in the approach-limit review.
Target alignment must be Yes before validity is assessed; accessibility must be
Yes before limits are assessed. Other measures do not inherit those gates.

The mathematical and approach-limit reviewers use a bounded structured-request
loop around the existing calculator, not arbitrary Python execution. They must
still provide mathematical interpretation and arguments. The default bounds are
three model calls and sixteen calculator checks per tool-enabled role, one call
for the other roles. Failures, truncation, invalid replies and exhausted budgets
remain execution outcomes with no educational verdict; they do not erase other
measures or become No/Unclear automatically. Dependent skipped assessments show
the cause. Method counts and categorical summaries retain their actual reviewed
sets, unknowns and conditional denominators, with no summed PF score.

The [saved-case runner](../../scripts/run_pf_task_measures.py) supports a
credential-free dry run, fresh output directories, prompt/rubric snapshots,
source/code hashes, actual request/response and calculator traces, deployment
settings and separate execution-failure counts. SDK retries are disabled. The
module invocation is the verified command in this environment; direct-script
launching exposed import-path problems also present in an older runner, despite
the packages being installed. No dependency manifest or shared interpreter
configuration was changed.

**Supporting evidence.** The new
[unit/integration suite](../../tests/test_pf_task_measures.py) has 54 mocked tests,
covering all values, Partly restrictions, both skips, role isolation, calculator
rounds/budgets, source anchoring, successful alternatives, explicit failures,
frozen-file protection, runner outputs and CLI failure exit codes. A separate
real module dry run on a synthetic software-only fixture prepared all five
prompts, excluded reference labels and wrote no judgments. Software checks do
not establish judge accuracy, learner behavior or educational validity.

**Remaining work.** No real API judgment or calibration was run. Prepare the
topic-diverse calibration pack and provisional, measure-specific reference
evidence; obtain blind human review, confirm two model-family deployments and
execution settings, then run the previously bounded development/held-out
protocol. The implementation instructions and input contract are in
[PF_DESIGN_AUDIT.md](PF_DESIGN_AUDIT.md#frozen-evaluator-implementation-october-14).
The closed learner-simulation/feedback component has not been reopened.

**Evaluator architecture review (October 14, later discussion; proposal only).**
The user asked whether five judges are needed and whether a simulated student
could serve the measurement. An intermediate proposal in this discussion (five
measure judges plus a separate solver, six roles) is superseded. The revised
principle is to separate roles by what each must not see, not by measure. Only
one boundary requires a separate role: whoever produces prior-knowledge attempts
must not see the target, a solution or expected errors. Everything else may share
a context.

The proposed design has three model roles plus the existing calculator.
(1) A **prior-knowledge solver** receives only the student task and frozen
prerequisites. It writes several worked attempts and continues each as far as
those prerequisites allow, recording where it stops. It assigns no verdict.
This is the user's earlier idea (a simulated student tries the task with prior
knowledge; if it can start, it continues until the familiar approach falls
short), without a learner persona. (2) An **attempt judge** receives the task,
target, prerequisites and those frozen attempts. It decides accessibility, then
(only if Yes) limits of familiar approaches. Because it knows the target, it can
detect an attempt that silently uses the untaught concept. It must distinguish
a demonstrated mathematical limit from the solver giving up. (3) A **task judge**
receives the task, target and prerequisites, but not the attempts. It decides
target alignment, then (only if Yes) mathematical validity with the calculator,
and room for invention from the task text. Dependencies remain enforced in code.

The reason for a solver rather than a realistic simulated student: the two
attempt-based measures need checkable existence witnesses (a start exists; this
familiar approach falls short), not predictions of student frequency. The closed
pilot showed that the same unchanged task reached its intended path in 0/8
GPT-4.1 and 4/4 GPT-5.4 learner replies, and that prescribed-error prompts test
obedience. A witness the judge verifies holds regardless of which model produced
it; a missing witness establishes nothing and stays Unclear. The solver remains
model-conditional diagnostic evidence, not student behavior, and this does not
reopen the closed simulation/feedback component.

Known risk: a judge rating several measures in one call may let one verdict
colour another. The October 13 one-call Table 1 judge put AE at 3.00 for every
task and APK near 3, which is a warning, not proof, for multi-measure calls.
Mitigations: separate evidence fields per measure, code-enforced dependencies,
and per-measure checks during calibration. Any measure that tracks its neighbour
rather than its reference labels would be moved to its own judge. For judge-family
comparison, freeze one set of solver attempts and give the same attempts to both
families; varying the solver is a separate sensitivity check.

The measure definitions and values would not change; only the workflow would,
as a new versioned instrument. The v1 rubric, five-role code and saved software
results remain unchanged. This needs confirmation before implementation; no new
evaluator, task, attempt or experiment was created by this discussion.

**Draft prompts and procedure (October 14; design only, not implemented).** The
user approved the three-role design and asked for prompts and procedures. Per
task: check inputs; run the task judge and solver independently; freeze and hash
the solver output; then run the attempt judge on those frozen attempts. Missing
or empty prerequisites skip the solver and record accessibility as Unclear.
The solver makes one call without tools and returns up to four distinct attempts.
It may build new ideas from listed knowledge but must stop and name anything
unlisted. It must carry natural approaches out honestly, neither making
deliberate mistakes nor dropping a simple approach because a better one exists.
The attempt judge first checks the solver's reading of the task. It then audits
each start as supported, imported knowledge, not meaningful, misread or
unresolved, and reviews every supported attempt to its end. The task judge
assesses alignment, invention and (only after aligned) validity separately, and
also checks conclusion giveaways.

Three refinements surfaced while drafting. They would require a new instrument
version and await confirmation. (1) An approach can fall short for a reason the
target does not address, such as heavy computation or an unrelated missing
skill. v1 has no outcome for this. The draft adds *unrelated shortfall*, which
counts toward No for limits, because it shows the task's difficulty does not
route through the target. (2) Code, not the judge, would derive the
accessibility and limits verdicts from per-attempt classifications. v1 instead
rejects an inconsistent judge output, losing its evidence. (3) Each measure
section would be validated separately. A bad quote then removes only that
measure's verdict and keeps sibling findings, following the earlier
parser-correction lesson. A known risk: limits can only be found among the
solver's attempts, so a No is conditional on which approaches the solver tried.
Calibration should compare these against reference-identified familiar approaches.

**Minimal outputs (Occam's razor, same day; design only).** At the user's
request, a field is kept only if code uses it for a verdict, dependency or count,
or a reviewer needs it to check that verdict. The evaluator already records
inputs, raw responses and the calculator log, so models do not repeat them.
Solver attempts reduce to an idea label and the worked text, which ends with
an answer or the point where it stopped. Resource indices, task quotes,
stop-reason codes and a separate task restatement are dropped.
The attempt judge returns one status and one reason per attempt
(`not_supported`, `target_limit`, `unrelated_shortfall`, `meets_demands`,
`unresolved`), plus an optional argument that no start is possible. Code derives
accessibility, limits and the approach counts from these. Alignment and
invention keep a verdict, exact task quotes and a reason. Validity keeps a
verdict and reason only; the three-part check remains in the prompt. Calculator
requests reduce to purpose, values, expressions, predicate and optional symbols.
What is lost: per-approach resource mappings, categorical reasons for rejected
starts, and the code check that a validity claim rests on a supported
calculation. These remain readable in reason texts and the calculator log.

## October 12--13: authorized measurement-gap and grounding research

**Campaign protocol and status.** The user authorized bounded research to test the
"good scores, hidden problems" interpretation and compare curriculum and Learning
Commons evidence. The scope was recorded before the main runs in
[pf_overnight_research_20261013.json](../../experiments/configs/pf_overnight_research_20261013.json).
The same-task measurement audit is complete; its result is recorded below. The
separate grounding generation run is tracked independently and is not a result
about task quality until its frozen outputs are evaluated. The closed
simulated-student/feedback campaign is not reopened.

**Measurement hypothesis.** On precisely the same saved tasks, some high original
ratings may coexist with evidence-specific concerns. The earlier nine-task versus
21-task comparison cannot establish this paired claim. The new audit freezes a
score-independent sample of the v4 benchmark, retains its original ratings, and
uses two separate model series with condition/score labels withheld. Exact
mathematical contradictions, original-anchor concerns, added design criteria,
disagreements and unknowns remain separate. A stricter audit is not automatically
proof that the original rubric's score was wrong.

**Grounding hypothesis.** Keeping the learner request and current generator fixed,
curriculum evidence may improve accessible starts and preserve the discovery;
Learning Commons may add a benefit beyond that curriculum packet. The three
arms are no external evidence, curriculum evidence, and the same curriculum
evidence plus Learning Commons descriptions. Five specifications, four repeats
per arm, give 60 scheduled main generation attempts. Calibration uses distinct
specifications and tests execution, not educational quality. Retrieval is frozen,
expert lists are held out, failures are retained, and no quality-based stop gate
or unlimited retry is introduced.

The case-specific D1 prior-resource packets and learner context are fixed and
identical in all three arms. Every generation call receives the same
`SHARED BENCHMARK CONTEXT` reference-inventory wrapper; only the local and
Learning Commons evidence arrays change. A is the empty-reference control, B
adds local curriculum references, and C adds those same local references plus
Learning Commons references. This tests added reference availability during
design, not prior-resource discovery. Local evidence comes from the official
Singapore syllabus. Learning Commons uses the frozen top-three search results
without hand filtering; its grade-unfiltered results include some advanced or
off-topic standards. These remain reference data, not learner prerequisites.
Evidence lengths differ by arm, so this is not an equal-token-content
comparison. The frozen
[configuration](../../experiments/configs/pf_grounding_study_20261013.json)
and [live manifest](../../experiments/results/pf_grounding_study_20261013/manifest.json)
retain the exact records and source hashes.

An alternate [October 12 runner attempt](../../experiments/results/pf_grounding_evidence_comparison_20261012/)
is preserved separately and is **not** part of the October 13 comparison. Its
arm C supplied Learning Commons references without the local references, so its
conditions do not match the frozen A/B/C protocol above. All three calibration
calls failed with Azure `404 DeploymentNotFound` for `gpt-6-luna`; none of the
60 scheduled main attempts started. Its accounting records 15/800 requests
(including a conservative 12-request source-acquisition reserve), and its
generation summary records zero produced calibration or main tasks. This is a
deployment failure, not task-quality evidence, and its results are not pooled
with the active October 13 run.

**Corrections to the earlier proposed scorecard.** The experiment uses an
evidence-specific supplement, not a validated replacement PF score. Passing data
checks alone does not certify final-task mathematics. A target term alone need
not reveal a solution, and unaided success or a familiar successful method is
not automatically undesirable. Distinct display formats and distinct mathematical
ideas are recorded separately. No fresh learner simulations are needed for this
generation comparison. The five task specifications are statistical blocks:
four repeated generations do not create four independent target families. The
earlier 15-of-20 sign-test rule is therefore not used as a generalization gate.
Report per-specification differences, component rates and judge uncertainty.

**Research basis.** Rahimi et al.'s
[official ICLS 2026 paper](https://doi.org/10.22318/icls2026.113185) uses human
ratings, whereas the repository benchmarks use model judgments.
[CheckEval](https://arxiv.org/abs/2403.18771) and
[TICK](https://arxiv.org/abs/2410.03608) motivate decomposed evidence questions
without validating them for PF. [Moore et al.](https://arxiv.org/abs/2307.08161)
show that high question-flaw label agreement need not imply correct whole-item
classification. [Liusie et al.](https://aclanthology.org/2024.eacl-long.8/)
find advantages for comparative judgments in their settings, but
[Tripathi et al.](https://arxiv.org/abs/2504.14716) show that pairwise judges can
be more distractible even with order swapping. Accordingly, model agreement is
reported as evidence about the instrument, not human-validated educational truth.

### Same-task measurement-gap result (October 13)

**Versioned technical corrections.** Parser v1.3 preserves valid fields when
another field has a validation error, records that invalid field and its raw
data explicitly, and accepts strictly validated structured concern witnesses.
Reparsing the 136 existing responses made zero new API calls. The sidecar has
106 fully valid and two partially valid main responses, with the same zero
agreed high-score gaps. The checklist-support count changes from 9 to 10 of
54 and idea-opportunity support from 37 to 38; the original analysis remains
preserved. These are runtime corrections, not new scoring criteria or tuning
to reject direct generation.
The [v1.3 parser-correction record](../../experiments/results/pf_measurement_gap_study_20261013/analysis_v1_3/parser_correction.json)
records 70 targeted tests passed and zero new model requests.

The first grounding audit also exposed a separate input error:
the canonical catalog supplied `recently_taught`, but the inherited auditor
allowlist retained only `assumed_prior_knowledge`. The 120-request run therefore
received no usable prior-learning descriptions and returned unknown accessible
starts for every task. It cannot settle the grounding question. Its raw
requests and results are preserved in
[the original audit directory](../../experiments/results/pf_grounding_study_20261013/evidence_audit_v1_2_frozen_catalog_20261013/).
The [history adapter](../../scripts/adapt_pf_grounding_catalog.py) translates
the same frozen taught-resource descriptions into the required input shape,
without changing tasks, adding skills, or sending the generation arm to the
judge. Six repaired-input calibration judgments on the three separate generation
calibration tasks parsed successfully. A corrected 120-judgment audit of the
same 60 main tasks completed in
[a new directory](../../experiments/results/pf_grounding_study_20261013/evidence_history_corrected/).
All 120 responses were usable at least field-wise: 113 fully valid and seven
partially valid, with invalid fields retained as explicit unknowns. No new
generation or learner simulation was involved. The auditor now rejects a catalog
whose `recently_taught` history would be silently discarded; the adapter is
required before evaluating that catalog.

After generation, focused integration tests also exposed an export helper that
rejected output directories outside the repository. The helper now records
absolute paths for those directories. Existing generation snapshots and task
receipts remain unchanged; this compatibility correction does not change the
experimental results.

The frozen audit rated 54 saved Grade 7 proportional-relationship tasks from the
same v4 benchmark: all 30 V1 tasks, six each from V2 and V3, and 12 ready
PIPELINE tasks. The smaller condition samples were seeded across attempt-number
tertiles; PIPELINE sampling was conditional on readiness. This one-topic,
unequal-sample audit is not a method ranking or a cross-topic estimate.

| Audit outcome | Result |
|---|---:|
| Main judgments retained after v1.3 reparsing | 106 fully valid and two partially valid; no missing request records |
| Original Table 1 anchor-tension candidates among tasks scoring >=14/15 | 0/41 |
| Tasks with an agreed additional-property concern | 0/54 |
| Five-property checklist fully supported | 10/54 |
| Checklist unknown | 44/54 |
| Distinct mathematical-idea affordance supported | 38/54 |
| Distinct-idea affordance unknown | 16/54 |

The zero counts require two judges to flag the same property and an exact,
verified quotation from the task. They mean the frozen audit did not produce
corroborated concerns under that rule, not that the tasks were verified as
good. Sixteen tasks have a one-judge concern without agreement; these are
disputed review candidates, not confirmed issues. The five-property checklist
is a conjunction, not a validated PF score, and its unknowns are not failures.

The instrument controls limit a positive reading of the null result. GPT-4.1
matched 19/27 development and 5/6 holdout expectations after the parser
correction; GPT-5.4 matched 26/27 and 6/6. GPT-4.1 marked preserved discovery
and useful prior contrast supported in all 54 main judgments, while
GPT-5.4 gave more partial or negative statuses. The judges are two series from
the same model family, not independent human raters. One GPT-4.1 judgment also
treated a speed task missing a time value as specified and `model_recomputed`;
model mathematics claims are not deterministic proof. Exact quote fidelity was
3545/3632 after field-wise recovery, which checks whether cited text appears
in the task, not whether the
interpretation is correct.

The audit therefore does **not substantiate a broad claim that the direct tasks
are generally defective or that high original scores conceal shared PF flaws**
in this sampled setting. It also does not validate the direct tasks: many
checklist outcomes are unknown, the controls expose judge weaknesses, and no
human task adjudication or student attempts were collected. The earlier
separate-pool AI review remains exploratory case-level evidence, not a paired
confirmation. The appropriate next evidence is blinded human interpretation
of disputed tasks and, later, student work; the prompt should not be retuned to
force either a positive or negative verdict.

The [corrected report](../../experiments/results/pf_measurement_gap_study_20261013/analysis_v1_3/report.md),
[HTML report](../../experiments/results/pf_measurement_gap_study_20261013/analysis_v1_3/report.html),
[source and rating verification](../../experiments/results/pf_measurement_gap_study_20261013/verification_final.json),
[labels-hidden review pack](../../experiments/results/pf_measurement_gap_study_20261013/analysis_v1_3/review_pack_labels_hidden.html),
and [disagreement gallery](../../experiments/results/pf_measurement_gap_study_20261013/analysis_v1_3/same_task_disagreement_gallery.html)
preserve the results. A runtime/aggregation correction after collection left
the frozen prompt, task selection, and model responses unchanged and made zero
new model requests. Version 1.1 preserved unresolved mathematically dependent
concerns and exposed raw status votes; version 1.2 handles failed catalog entries
with no `task` key as zero-call input errors while retaining their scheduled
unknown judgments. The original analysis is preserved in
[analysis_original_v1](../../experiments/results/pf_measurement_gap_study_20261013/analysis_original_v1/).
The [v1.2 correction record](../../experiments/results/pf_measurement_gap_study_20261013/runtime_correction_v1_2.json)
records unchanged outcomes and prompt, no additional calls, and 57 focused tests.

### Grounding result and stopping decision (October 13)

All 60 main tasks and three execution-calibration tasks were produced using
`gpt-5.6-luna-2026-07-09`. Five Grade 8 specifications covered scientific scales,
signed products, equivalent bundle rules, mixed area units and polygon design,
with four repetitions in each of three conditions. Their broader topics had
been inspected previously; this is transfer evidence, not untouched validation.
The same stipulated D1 priors were held fixed. Only reference availability during
design changed: no evidence, local curriculum, and local curriculum plus Learning
Commons. Thus the experiment does not evaluate discovery of prior resources.

The corrected two-model audit reports the following **supported outputs out of
20 scheduled outputs per condition**. Unknowns and disagreements are the
remainder, not automatically failed tasks.

| Property | No retrieval | Curriculum | Curriculum + Learning Commons |
|---|---:|---:|---:|
| Target relevance | 10/20 | 12/20 | 5/20 |
| Accessible start | 9/20 | 11/20 | 11/20 |
| Consequential choice | 5/20 | 7/20 | 8/20 |
| Distinct mathematical-idea opportunity | 12/20 | 14/20 | 7/20 |
| Discovery preserved | 18/20 | 19/20 | 19/20 |
| Useful prior contrast | 5/20 | 11/20 | 5/20 |
| Mathematics status supported by both model judges | 2/20 | 3/20 | 2/20 |
| Five-property conjunction | 0/20 | 1/20 | 0/20 |

**Interpretation.** Curriculum has directional support gains on several
components, but the primary outcome is uninformative: only one of 60 tasks has
all five properties supported, and 59 are unresolved. Mathematical evidence
is the main bottleneck (53/60 unknown or disputed). This is a limitation of the
instrument's coverage, not evidence that 53 tasks are mathematically wrong.
Each `math_status` is a model claim. Separately, across 449 individual
arithmetic-witness checks, 196 were verified and 253 were unknown. The largest
unknown reason was an operand absent from the exact quoted task spans (173
checks); 30 had missing or inexact quotes. Other cases used unsupported syntax
or operations. A verified witness checks only its quoted arithmetic and source
grounding; it does not prove the entire task is mathematically valid.
The +5 percentage-point supported-conjunction difference for curriculum comes
from one case. Its unknown sensitivity spans -95 to +100 percentage points;
the narrower block-bootstrap interval [0, +15] does not account for those
classification unknowns and cannot establish an educational benefit.

Learning Commons did not show a consistent incremental gain: choice support
increased slightly, while supported target relevance, distinct ideas and useful
contrast decreased. These are support/uncertainty changes, not demonstrated
task-quality losses. Retrieval was grade-unfiltered and kept the top three
results without manual quality filtering; some were advanced or off-topic.
Source lengths differed across arms. The finding concerns this retrieval
bundle, not the whole Learning Commons platform.

**Separate parent-run context sensitivity (not pooled).** A second audit passed
the same subject and jurisdiction fields from the generation context in addition
to the fixed D1 resources. It used the same task texts, targets and prompt, but
had no fresh controls and is not an independent generation replicate. Its
five-property support count was 2/60 (A: 0, B: 1, C: 1), compared with 1/60
(A: 0, B: 1, C: 0) in the calibrated history-adapter comparison above. The
difference is preserved as evaluator-input sensitivity, not as an arm effect;
the results must not be pooled or selected to favor a condition. This separate
run used 120 additional model requests and is outside the canonical 861-request
campaign total. See the [context-expanded sensitivity report](../../experiments/results/pf_grounding_study_20261013/study_report.md)
and [input correction record](../../experiments/results/pf_grounding_study_20261013/evidence_audit_prior_context_corrected_20261013/input_context_correction_record.json).

**What the metric extension achieved.** The supplement separates task
properties and distinguishes missing evidence from failure; it exposes the
leniency, exact-quote and arithmetic-witness limitations that a single total
would hide. It is not yet a reliable complete PF-quality instrument. Do not
promote a generator or declare a grounding effect from these results.
The bounded campaigns stop here without another prompt-tuning round. Human
adjudication and broader domain-capable mathematics verification are the next
instrument-validation needs; student outcomes remain future work.

**Artifacts and costs.** The
[final numerical and visual comparison](../../experiments/results/pf_grounding_study_20261013/final_comparison/report.html),
[summary and block analysis](../../experiments/results/pf_grounding_study_20261013/final_comparison/summary.json),
[all 60 tasks](../../experiments/results/pf_grounding_study_20261013/tasks.html),
and [corrected labels-hidden review pack](../../experiments/results/pf_grounding_study_20261013/evidence_history_corrected/review_pack_labels_hidden.html)
are saved. The canonical campaign used 861 model requests and 5,336,367 reported
tokens: 479 generation, 136 measurement/controls, 120 context-defective grounding
audits, six repaired-input calibration audits and 120 corrected main audits.
The separate deployment-failed three-call calibration above is not pooled;
its unreturned token usage remains unavailable. Currency costs are unknown.
Eighty-one focused campaign tests, targeted Ruff and compilation pass.
Software checks do not validate educational judgments.

## October 14: Rahimi-style replication extended to four theme cells (proposed, not run)

**Question.** Does GPT-5 mini or GPT-4.1 direct PF generation show a model gap
under the Rahimi-style grade 7 ratio setting when the setting covers more themes
and two topics, rather than one basketball theme?

**What changed.** The first Rahimi-style scale-up, one theme with 100 attempts
planned per model, was stopped during the run on the user's request. Per the
user's instruction, the calibration run with one GPT-5 mini connection error and
four unfinished attempts were deleted and not replaced. The six completed
attempts remain in
[main_100](../../experiments/results/pf_rahimi_scale_comparison_20261013/main_100/)
as a superseded pilot and are not counted in the new setting.

**Proposed setting.** The [frozen config](../../experiments/configs/pf_rahimi_multi_theme_setting.json)
has four cells of 30 attempts per model, each with its own theme and grade 7 topic: sports/basketball
with ratios (7.RP.A.2, the Rahimi-matched cell), shopping with percent (7.RP.A.3), music with comparing
two data sets (7.SP.B.4), and home and garden with composite area (7.G.B.6). Each cell has its own
assumed prior knowledge. Every cell uses the same V1 prompt, which contains no topic-specific wording,
and the same five StratL examples. Judges are two passes of gpt-5.6-luna with high reasoning effort. Each
pass has its own blind IDs and seeded shuffle, sees only learner context and task text, and returns the
Table 1 scores. The final score is the mean of the two totals; a gap of 5 or more is flagged, with no third
judge. The paper's third-rater step is therefore not copied.

**Judge input revision.** The frozen rahimi-table1/v1 judge saw only grade, prior knowledge and
task text; it hid the learning target on purpose. That left SSC without its reference point (challenge
for students who have not been taught the target) and AE without the assigned student interest. Rahimi
et al. held the setting constant and blinded raters only to the model, so a trained rater knew it. The
replication therefore uses a versioned
[rahimi-table1/v1-setting](../../src/evaluation/prompts/pf_rubric_setting.yaml) prompt with
[pf_rubric_setting.py](../../src/evaluation/pf_rubric_setting.py). All 15 anchors are verbatim and
test-checked against v1. The judge additionally receives a `task_setting` block: intended PF use, the
untaught target, theme and student interest. It still never sees the model, cell ID, examples or
generation rules. The cell targets were also aligned with the official CCSS wording (checked October 13);
7.G.B.6 is explicitly restricted to its area part. v1 remains unchanged for historical results.

**Generation input check.** The frozen V1 generation prompt is unchanged and topic-neutral, so all
cells and both models share it, as in the earlier direct run. Rendering the new cells showed that their
setting rules prescribed the task form (for example, "must compare two groups of numerical data") and the
shopping interest named discounts, while the basketball cell names only a theme. The three new cells now
follow the basketball template: the setting rule names only the theme situation, the interest names only
the student interest, and the boundary fixes the prior standards. Task-form wording now appears only in
the official target, topic label and prerequisites.

**Status.** Runner built and checked without API calls: [run_pf_rahimi_multi_theme.py](../../scripts/run_pf_rahimi_multi_theme.py), with [tests](../../tests/test_pf_rahimi_multi_theme.py). The dry run builds 240 generation requests and at most 480 judge requests. A fake-API run through generation, judging and summary confirmed the deletion rule, blind mapping, mean-and-gap rule, and that a rerun makes no new calls. **Full run (October 13, 12:40 CEST).** [main_30](../../experiments/results/pf_rahimi_multi_theme_20261013/main_30/) ran 240 generations (4 cells × 2 models × 30) and 476 judge calls, with 60 concurrent workers per stage. 238 generations are ready and 237 tasks have two scored judge passes. Recorded outcomes, none replaced: one judge call returned an HTTP 500 and was deleted, leaving shopping GPT-5 mini task 005 with one score; two GPT-5 mini tasks (music 015, shopping 002) contained a valid task plus an extra field and fail the frozen validator, so they are kept as invalid and not judged. Every judgment used gpt-5.6-luna at high effort, with no truncation or parse failure. No pair of passes differed by 5 or more; the largest gap was 2. Descriptive means, one-judge-pair totals out of 15, not tested: GPT-5 mini 14.56 (SD 0.49, n 117); GPT-4.1 12.82 (SD 1.23, n 120). Two dimensions sit at the ceiling: AE is 3.00 for every cell and both models, and APK is about 3 everywhere, so neither separates the models. Judge-set limitation: both passes come from one deployment, and this run has no human rating, so it is not validation. Next implication: read the lowest-scoring tasks (GPT-4.1 garden OE 1.40, SSC 1.72) before any claim.

**What the rubric does not see (October 13 reading of the full run).** High Table 1 scores show that
direct prompting reaches the paper's rubric ceiling; they do not show good PF design. A reading of
sampled tasks (lowest, median and highest per cell and model) against the expert tasks in
[data/pf_exercises](../../data/pf_exercises/), plus text-pattern counts over all 238 ready tasks from
[audit_pf_rahimi_multi_theme_text.py](../../scripts/audit_pf_rahimi_multi_theme_text.py)
([output](../../experiments/results/pf_rahimi_multi_theme_20261013/main_30/text_pattern_audit.json)),
found six gaps. Counts are regular-expression heuristics, not human coding.

1. *The key idea is often handed over, and the higher-scoring model does it more.* GPT-5 mini questions
   say "proportional" in 24/30 basketball tasks (GPT-4.1: 0/30), usually as "decide whether ... is
   proportional", the near-verbatim wording of the untaught standard 7.RP.A.2.a; they list usable
   methods in 109/118 tasks (4/120). Garden decomposition cues (30/30 against 16/30) are weaker evidence,
   because decomposition is the stated prior knowledge (6.G.A.1), not the target; music cues name
   prior-knowledge measures (6.SP.B.5), not the 7.SP.B.4 target. Garden task
   gpt5mini-028 states the whole method as a "Hint" and scored 15/15; GPT-4.1 garden-009, with a
   similar cue, scored 10. Expert tasks ask a situational question and leave the concept unnamed.
2. *Worksheets rather than one open challenge.* 100/118 GPT-5 mini questions have three or more
   numbered or bulleted parts (median 422 words); GPT-4.1 has none (median 200). Expert tasks can be
   long (biking: 545 words) but pose one challenge. Table 1 OE rewards "many variables", so a
   multi-part worksheet can score as open-ended.
3. *Failure is rarely engineered.* Expert data make the familiar method fail (equal means and ranges;
   speed ratios that do not combine). Generated twists are sometimes inert: in basketball
   gpt5mini-021, Drill C is proportional under both the session-time and active-time reading
   (5/3 and 20/11 throughout), so the rest-break twist cannot change the decision. The same task's
   Drill B (8, 15, 22 makes in 5, 10, 15 minutes: linear, not proportional) is a good contrasting case.
4. *Target alignment is unscored.* Only 3/30 GPT-4.1 music tasks frame the data as a sample, although
   7.SP.B.4 concerns inference about populations from samples; a judge flagged the mismatch on
   29/30, and they still average 13.63. GPT-4.1 basketball-018 (15/15) is a well-built comparison of
   two shooters' mixed attempts, but it does not require deciding proportionality.
5. *Mathematical concerns do not lower scores.* Judges listed at least one concern for 111/118 GPT-5 mini
   and 108/120 GPT-4.1 tasks; 106 of the concerned GPT-5 mini tasks still score 14 or more. Most are
   minor (rounding, quartile convention, layout), but some are verified defects: gpt5mini-028 says a
   triangle sits on a long side while its 10-ft base is a short side; gpt41-019 asks for a regular
   hexagon's area (6&radic;3 m&sup2;), which needs &radic;3 beyond the stated prerequisites, and allows
   arrangement-dependent overlaps.
6. *Set-level sameness is invisible to a per-task rubric.* GPT-4.1 garden has 19 distinct titles in 30
   tasks ("Designing a Unique Garden Patio" nine times); GPT-5 mini uses "Maya" in 10/30 garden tasks.

Two rubric dimensions carry no signal here (AE 3.00 for all 237 scored tasks; APK about 3). Word count
does not explain scores within either model (r = 0.03 and -0.17), so the judges are not simply
rewarding length. A design caveat of our own: the garden cell's prior standard (6.G.A.1) already is
the decomposition method, so that target leaves little to discover for any generator. This reading
is by an AI assistant, not by an expert teacher or students.

The argument is laid out as a chain in slides 16–25 of
[RAHIMI_EXPERIMENT_VISUAL.html](../status/RAHIMI_EXPERIMENT_VISUAL.html).
Slides 17–18 now distinguish the authors' proposed learning mechanisms from
the design principles intended to support them. Both come from Kapur &
Bielaczyc (2012), p. 49; their theoretical motivation is on p. 48. Mechanism
descriptions are quoted, principle descriptions are paraphrased, and the
principle-to-mechanism mapping follows the paper. Sources are visible before
the content, rather than only in a footnote. This replaces the confusing
principles-first dot matrix without changing experiment results.

Slide 19 now bridges the literature to our generation scope: the generated
problem should offer an accessible start, opportunities to explore and explain,
and attempts that later instruction can compare. The bicycle example illustrates
why a familiar ratio shortcut can be insufficient while trial and error remains
possible. This replaces the misleading "calibrate, then make methods fail"
recipe; it does not require every familiar method to fail or claim observed
student outcomes. The example now introduces the shared bicycle, the two
friends' travel sequence and the equal-arrival goal before discussing method
limitations, with a direct link to Appendix A (journal p. 82).

Slide 20 continues the bicycle example rather than interrupting the argument
with three paper summaries. It shows a possible ratio-based first idea, the
diagrams/ratios/trial-and-error categories recorded in the 2012 study, and an
illustration of comparison during instruction. The supporting findings from
Sinha and Kapur (2021), Kapur, Saba and Roll (2023), and Loibl and Rummel (2014)
are linked beneath the corresponding panels. The 2023 finding is described
as an association, not a causal effect. Study counts, effect sizes and limits
remain in expandable details. These studies motivate our checks; they do not
validate the generated tasks or C1–C6.

Slides 16–20 cover definition, mechanisms, principles, the problem's role and
empirical findings. An earlier slide 21 introduced six task-level checks; C1–C6
were our operational interpretation, not a six-condition checklist quoted from
the paper. That version stated each as a question with a bicycle-problem example,
and slides 22 and 24 used the same names: C1 accessible start, C2 key idea left open, C3 shortcut
falls short (one plausible familiar method, not every method), C4 different
approaches, C5 attempts to compare and C6 on target and correct. The bicycle
example's handover point (3.4 km, 76 minutes for both friends) was checked by
exact calculation. Those renames replaced the earlier labels (accessible, target
withheld, engineered failure, room to invent, comparable failure, aligned and
valid) without changing any counts. The direct-generation findings and their
evidence limitations remain recorded above.

**Proposed rubric (October 14, not yet run).** The current proposal has five
measures, recorded in
[PF_DESIGN_AUDIT.md](PF_DESIGN_AUDIT.md#proposed-rubric-october-14-not-yet-run):
**Target alignment**, **Mathematical validity**, **Prior-knowledge accessibility**,
**Limits of familiar approaches** and **Room for invention**. The earlier
four-measure proposal combined alignment and correctness. The user requested
their separation, with mathematical validity assessed only when target alignment
is Yes. An off-target or unclear-alignment task therefore has validity
*Not assessed*, not No, even if its mathematics could be correct. The existing
accessibility-to-familiar-approach dependency is unchanged: measure 4 is assessed
only when measure 3 is Yes. Neither dependency is a generation stop gate, and
alignment does not newly gate accessibility or invention.

Reports use all ready tasks (N) for alignment, accessibility and invention,
aligned tasks (n_aligned) for validity, and accessible tasks (n_accessible) for
limits of familiar approaches. Show skipped assessments and their reasons,
and do not present conditional validity as correctness across all generated
tasks. These are proposed measurement rules, not new ratings or evidence.
Earlier drafts had five to nine measures; engagement was dropped because the
definition and mechanisms do not require it, and Rahimi's AE score remains a
comparability column only. Judge-concern text gives a lower bound of roughly
30–40 off-target tasks among the 238 ready tasks (27–29 GPT-4.1 music,
3–11 GPT-4.1 basketball), because no judge was asked about alignment directly.
These historical counts are not reratings under the new protocol. Slides 21–25
now separate alignment concerns from mathematical concerns and state the two
dependencies. The initial v1 judge implementation is now complete; calibration
remains pending, as recorded in the current implementation entry above.

**Measurement roles (October 14; initial implementation, not calibrated).** The problem
with one judge assessing everything is that seeing the intended solution can
contaminate an ostensibly prior-knowledge-only attempt, while a general verdict
can hide missing mathematical evidence. Following the alignment split, the
proposed responsibilities are: (1) a target-alignment reviewer that receives the
task and intended target; (2) a mathematical verifier that uses the existing
exact calculator only after alignment is Yes; (3) a prior-knowledge-only solver that
receives the student task and frozen prerequisites, but no separate target,
solution, expected errors or other verdicts; (4) a familiar-approach reviewer
that receives the frozen worked approaches, prerequisites and target only after measure 3
is Yes, and checks where an available approach falls short and how the target
resolves that limitation; and (5) a separate invention reviewer that receives
the task and target and supplies quotations and concrete approach examples.
Only the 1-to-2 and 3-to-4 dependencies pass the required prerequisite result or
evidence; unrelated roles do not see one another's judgments. These are distinct
responsibilities, not independent votes on the same question. Splitting a
measure does not itself fix how many judge instances or API calls implement it.

This implementation follows the rubric's existing evidence requirements and the
calculator's explicit unknown/unsupported outcomes; mocked software tests and a
no-call dry run have checked execution, not model judgment accuracy.
Python verifies the supplied mathematical representation, not
whether the verifier extracted the right interpretation from the task. A
relevant first attempt supports accessibility; failure to produce one does not
prove inaccessibility, and knowledge needed only for a complete solution does
not by itself refute an accessible start. This distinction also needs review
before using the audit's hexagon example as a calibration label. One worked
familiar approach falling short does not establish that all familiar approaches
fail. Two genuinely different approaches can support room for invention, but
not finding a second one cannot establish that only one exists.

**Multiple prior resources and approaches (October 14; proposed measurement
clarification).** A single selected method or frozen attempt is not a complete
description of a task's prior-knowledge opportunities. The intended learner's
taught-resource pool is fixed first: an approach can combine resources, and one
resource can support multiple approaches. Accessibility needs one evidenced,
meaningful start, not a start using every resource or success with every method.
When several plausible methods are available, the approach-limit review should
retain each method's resource mapping, limitation or success, rather than
cherry-pick a failure or reject the task after one success. The adopted name
Limits of familiar approaches and its task-level aggregation are not yet
calibrated. Room for invention still concerns meaningful choices left to the
learner; counting resources or superficial method variants is not a substitute.

The five measures and the two approved dependencies remain unchanged. Different
learner knowledge profiles would require separate contextual results and
denominators, with profiles grounded in history rather than desired pathways.
This clarification, recorded in
[PF_DESIGN_AUDIT.md](PF_DESIGN_AUDIT.md#proposed-rubric-october-14-not-yet-run),
adds no approach quota, diversity score, universal task ranking or new model
run. Possible methods remain task-opportunity evidence, not proof that learners
will actually use them.

**Metric name adopted (October 14).** The user selected **Limits of familiar
approaches**, replacing Failure of familiar approaches in the current rubric
and slides 21–23. The question now includes meaningful incomplete or suboptimal
reasoning, not only wrong answers; efficiency or generality matters only where
the task makes it consequential. Accessibility still requires at least one
meaningful start from the fixed taught-resource pool, and measure 4 is still
assessed only where accessibility is Yes. The approved row layout and connector
are preserved. This is a name and definition clarification, not a calibration
pass, rerating, new judge implementation or generation change.

**Pre-calibration working values (October 14; not calibrated or run).** The
current summary is consolidated in
[PF_DESIGN_AUDIT.md](PF_DESIGN_AUDIT.md#proposed-rubric-october-14-not-yet-run).
Use Yes, Partly, No and Unclear for Target alignment and Room for invention;
Yes, No and Unclear for Prior-knowledge accessibility; and Yes, No, Unclear and
Not assessed for Mathematical validity and Limits of familiar approaches.
Alignment requires a task-demand/target comparison;
validity requires a worked interpretation and supported exact checks;
accessibility requires a meaningful start mapped to the frozen prerequisites.
Unclear means insufficient or unresolved assessment evidence, not failure.
Not assessed means the prerequisite verdict was not Yes. API, truncation and
parser errors remain separate execution records, not educational verdicts.

For Limits of familiar approaches, the proposed task-level Yes means at least
one plausible, prerequisite-supported approach has a demonstrated limitation
that the target helps address. Preserve successful approaches alongside that
witness; a mixed case need not become No. The proposed No is explicitly scoped
to the examined approaches: each meets the actual mathematical demands and no
target-related limitation is demonstrated. It is not proof about every possible
method, lack of access to the formal formula is not by itself a limitation, and
unresolved approach evidence is Unclear rather than No when no positive witness
is available. The reviewed set and method-specific evidence must remain visible.

For Room for invention, Yes leaves the central mathematical invention open;
Partly supplies an important part of the idea or strategy but leaves a
consequential mathematical decision. No needs text evidence that the central
solution idea or route is supplied, leaving essentially routine execution. A unique answer,
a constraint such as using all the data, or failure to find a second method is
not sufficient for No. These are proposed operational meanings for discussion
before calibration, not validated aggregation rules, new scores or task ratings.

**Selective Partly category (October 14; working proposal).**
Binary values can hide a demonstrated middle case in target alignment or room
for invention. Partly should describe that task property, never uncertain
evidence, which remains Unclear. For alignment, Partly could mean a substantive
but incomplete connection to an explicitly specified target: the reviewer must
identify both the addressed and missing target elements. Mere topic overlap is
not enough, and extra requirements must not be invented to create partial
alignment. For invention, Partly could mean the task supplies an important part
of the central idea or strategy while leaving a consequential mathematical
decision to students; Yes would leave the central invention open and No would
leave essentially routine execution.

Partly is not recommended for mathematical validity, accessibility or limits
of familiar approaches. A material mathematical error is No, with its scope
recorded; incomplete verification is Unclear. Accessibility already requires
only a meaningful start, not complete solving. An incomplete familiar approach
can be a demonstrated limit (Yes); mixed successful and limited approaches are
retained separately, not relabeled Partly. Partly alignment gives mathematical
validity Not assessed under the approved Yes-only dependency. Adding the category
does not relax that dependency. These working values are now recorded in the
rubric; the slides still present the same five measures and two dependencies.
No judge has applied these values and no calibration label is validated by this
summary.

**Supplementary approach counts under discussion (October 14; proposal only).**
The categorical accessibility and familiar-approach-limit judgments need not
hide differences in their supporting evidence. A shared evidence table could
record each distinct plausible approach, the frozen prior resources it uses,
a meaningful worked start, and its demonstrated target-related limitation,
successful completion or unresolved outcome. Accessibility could then include
the number of distinct supported starts identified; the limits assessment could
include how many of the approaches reviewed have demonstrated relevant limits,
with successful and unresolved findings retained. A mere list of method names
is not evidence of an accessible start, and a different display or repeated
trial is not automatically a distinct approach.

These would be descriptive counts of identified and checked methods, not a
complete inventory, student frequencies or PF-quality scores. More starts is
not automatically better; more limited approaches is not automatically more
productive. The number of prerequisites is particularly sensitive to how
resource descriptions are split and does not measure task quality. Comparisons
would require the same search instructions and execution budget, equivalent
prerequisite conditions, reported method coverage and explicit unknowns. A
limit count must show its reviewed-method denominator; it is not an estimate
of a student's chance of failing. The recommendation is to preserve the
method-level evidence during calibration and assess whether these counts are
reproducible before adopting them as comparative outcomes. No threshold,
additional main metric, judge prompt or model run has been added.

**Room-for-invention expert reference discussion (October 14; qualitative
inspection, not calibration labels).** The
[imported consistency task](../../data/pf_exercises/puech_macina_2025_stratl_full.yaml)
supplies the data, the consistency goal and an all-data constraint, while
students construct the mathematical measure. The imported bicycle task even
supplies the physical bike-sharing plan, but leaves students to represent
the journeys, coordinate the walking/riding times and determine the handover
location. The
[curated land-division task](../../data/pf_exercises/kerrigan_weber_chinn_2021.yaml)
supplies valuations but no allocation or conflict-resolution recipe. The
imported country task supplies populations and a 250-seat total, while leaving
the integer-allocation rule and its justification open. These are concrete
examples of mathematical construction left to learners, not an observed
distribution of learner approaches.

The calibration implication is to distinguish problem definition and support
from supplying the central mathematical solution. Giving a goal, a constraint,
a physical plan or the name of the phenomenon to investigate does not by
itself imply Partly or No. A unique handover answer does not remove invention
of the mathematical model; conversely, an unspecified answer format does not
establish invention. Before judging guidance, the reviewer should identify
what is given and what consequential mathematics the learner still has to
construct. This distinction is more defensible than counting hints or target
words. The selected generation tasks are candidate positive references for
human review, not automatically four or five passes; expert collections also
contain instruction and practice tasks. No calibration set or new task
variant has been generated in this discussion.

### Expert mathematical-verification coverage (October 14)

**Local inspection, not validity ratings or judge calibration.** All five YAML collections in
[the expert-task inventory](../../data/pf_exercises/README.md) were inspected:
31 stored records, including overlapping versions, practice/posttest items and
instruction descriptions, not 31 unique PF generation tasks. Numerical
witnesses were formalized for 27 records. Four curated Loibl records lack a
concrete numerical instance: the invention table and procedural datasets are
placeholders, while the conceptual and contrasting-case records are descriptions.
Their instance-level verification is unavailable, not an invalid-task verdict.

The [saved local-check artifact](../../experiments/results/pf_expert_math_coverage_20261014/local_checks.json)
contains all 31 record entries, source and calculator hashes, assumptions,
replayable calculator requests/results and the probe script snapshot. It records
31 checks returning the expected calculator statuses: 24 holds, four fails
(three imported answer errors and one annotation error), two unsupported
function probes and one unknown missing-input probe. This counts local claims
and tool-boundary probes, not correct tasks. No LLM calls were made. An initial
generic symbolic identity probe omitted symbol declarations and correctly
returned unknown; the probe was corrected to declare real symbols before the
saved run. The calculator implementation and expert sources were not changed.

The concrete coverage includes average/segmented speed, fractions, statistics,
seat totals and remainders, sealed-bid cash conservation and own-value fairness
thresholds, conditional bicycle schedules, bird rate/schedule bounds, braking
and collision calculations, and the numerical transcription of a speed graph.
The tea task's missing observation was not filled in: observed-only statistics
and a separately labeled hypothetical missing-value witness show why the
missing-data policy affects the comparison. The bird task's flap-rate ranges
allow different winners under an explicitly declared flight/rest schedule;
that is evidence for conditional conclusions, not automatic invalidity of an
ill-structured task.

**Verified source issues remain separate from student-task validity.** The
imported consistency solution reports `12/5 = 3.2`, although `12/5 = 2.4` and
the table's actual squared-deviation sum is 16. The imported sealed-bid solution
reports `250 - 75 = 75`, although that subtraction gives 175; its stated final
settlement nevertheless conserves cash and meets each fair-share threshold.
The imported time-sharing solution values Bob's January-to-mid-July block at
$54,000, although `6*6000 + 0.5*12000 = 42000`. An end-of-July split with Bob
choosing August--December gives Bob $60,000 (above his $54,000 threshold) and
Ann $70,000 (her threshold). Thus a faulty imported answer is not proof that
the underlying task has no valid allocation. The earlier annotated consistency
claim that all means and ranges match is also false for its supplied table:
means are 14, 14, 15 and ranges are 5, 4, 8. Conflicting year labels remain
text/provenance concerns rather than failed arithmetic.

**Coverage boundary and proposed implication.** The current exact calculator
verifies supplied expressions and predicates, not task interpretation, automatic
dimensional consistency, diagram extraction, an unrestricted equation solver,
or general fairness guarantees. It does support symbolic identities and square
roots once the expressions and assumptions are supplied. A deliberate km-plus-
hours probe returns numeric holds, demonstrating why units need a separate
semantic check; `floor()` and `solve()` are explicitly unsupported. Fair cutting
needs an additive/divisible valuation model and a divider-chooser argument,
not just arithmetic on parcel totals. Physics needs justified modeling
assumptions. An invented consistency measure needs an argument that it measures
the intended property, not agreement with the source's variance formula.

The recommended verifier therefore reviews consistency of the task's data,
feasibility of the requested work under declared assumptions, and whether its
mathematical argument supports the required claims, using Python for checkable
claims. Intentional unknowns, multiple valid answers, approximate inputs and
legitimate modeling choices are not errors by themselves. If essential proof
or interpretation is unresolved, the proposed validity outcome remains Unclear
even when numerical checks hold. The approved alignment-Yes prerequisite for
mathematical validity is unchanged; this coverage inspection did not assign
alignment or conditional validity ratings. Imported answers and curated
annotations cannot be used as unquestioned calibration labels. No new main
metric, judge implementation, generation change or learner run was introduced.

The proposed next step is a small calibration with human-reviewed,
measure-specific reference judgments, including expert and contrasting task
examples without assuming expert provenance makes every measure pass. Repeat
the role-specific assessments with a second model family on that set and keep
disagreement visible rather than averaging categorical answers. Separate
held-out cases are needed before scaling. This is measurement-protocol design,
not authorization to reopen the closed learner-simulation/feedback experiments;
any constrained solver outputs would remain model-conditional diagnostic
evidence, not observed student behavior or learning.

**Calibration plan for the three-role design (October 14; supersedes the
five-role sequence; not started).** Implement the three-role workflow with
minimal outputs and mocked tests first; prepare the calibration pack in
parallel. Development uses about 13 cases: five expert generation tasks
(bicycle handover, consistency measure, seat allocation, land division,
time-sharing), two expert practice items as routine contrasts (ship and
walk-and-cycle average speed), five saved generated tasks with recorded concerns
(a GPT-4.1 music task, garden-028, garden-019, basketball-021 and a GPT-5 mini
"proportional" basketball task) and at most one labelled synthetic contrast (the
consistency task with its formula supplied). Each case is chosen for what it
probes, not for an assumed verdict. About nine held-out cases (hummingbird, tea,
goals, pizza, sealed-bid furniture, both braking tasks and two or three unused
generated tasks) are not used during development. Curated and imported versions
of the same task stay in the same set; topic overlap is unavoidable with this
expert pool. StratL imports lack prerequisites, so their frozen prerequisite
lists are researcher-specified, with provenance.

Reference judgments (a verdict and one line of evidence per measure, plus the
familiar approaches a knowledgeable reviewer expects) are written by the
researcher before any model output. They are not drafted by an LLM, to avoid
circular agreement; exact calculator checks may support them. A teacher or PF
expert reviews them blind. Disagreements are kept, and any corrected reference
records its reason before a rerun.

Development runs: two solver models on every case, frozen. Two judge families
run the task judge twice each, and the attempt judge twice each on the same
solver-A attempts. One judge family also judges solver-B attempts as a solver
sensitivity check. Reported per measure, as counts rather than kappa: agreement
with references, between families and between repeats; Unclear counts; each
disagreement classified as judge error, reference error or genuinely ambiguous;
solver coverage of reference familiar approaches and imported-knowledge
occurrences; verdict changes when the solver changes; any halo pattern; and
execution failures and cost.

Decision rules: the same judge error type in at least two development cases
allows one targeted prompt clarification. A measure that follows its neighbour
rather than its references moves to its own judge. At most one revision and one
rerun, then freeze. The frozen instrument runs once on the held-out cases with no
further changes. A measure that remains unreliable is reported as such. Only
afterward consider the 238 ready tasks. The model pair still needs confirmation;
a non-OpenAI family (for example the configured Swiss AI Qwen judge) gives
more independence than two OpenAI deployments. No run has been authorized.

**PF definition check (October 14).** Rechecking
[Kapur and Bielaczyc (2012)](../../thesis/otherpapers/Designing%20for%20Productive%20Failure.pdf)
confirms that failure of every familiar method is not a necessary task property.
Principle 3 includes failed or suboptimal approaches (journal p. 49); the bicycle
parameters deliberately obstruct the simple ratio method (p. 51), while Table 3
reports some successful PF-group problem solving (p. 63). A familiar method
reaching a correct answer therefore cannot by itself establish a defective PF
task. Initial difficulty, incomplete solutions or suboptimal reasoning must be
distinguished from banning all successful methods; later consolidation and
learning remain separate evidence requirements. The proposed measure 4 label
"No (a familiar method solves it)" was too strict and has been withdrawn from
the audit note, with its task-level No criterion and garden-009 example marked
for review rather than replaced by an uncalibrated rule. No task was rerated and
no new metric, generation change or learner experiment was introduced.

**Expert-task characteristics beyond the five measures (October 14; qualitative
inspection, not new ratings).** Reading the selected expert task texts suggests
that the rubric captures available opportunities more directly than the work
students are asked to produce. The
[imported task texts](../../data/pf_exercises/puech_macina_2025_stratl_full.yaml)
ask for a bike-handover location, invented consistency measures, or a justified
allocation of 250 seats. Constructing a plan, measure or allocation partly
overlaps Room for invention; it is not an entirely new dimension. Leaving
choices open and explicitly asking students to develop a mathematical proposal
are nevertheless different task demands.

Two less explicit features of the current measures are **explanation** and
**comparability of proposals**. The apportionment task asks students to show
their work and justify their method, not just return seat counts. Different
bicycle proposals can be checked against simultaneous arrival; different seat
allocations share a total-seat constraint while requiring an argument for
fairness. These shared criteria can make partial or competing ideas inspectable
and discussable. They do not guarantee that students will produce different
ideas or notice their limitations. Comparison of attempts with canonical
reasoning is also part of the
[Kapur and Bielaczyc lesson design](KAPUR_BIELACZYC_2012_EVIDENCE.md),
not something a worksheet alone establishes.

These are patterns in selected source texts, not universal expert-task
requirements or evidence of new learner outcomes. The
[dataset provenance note](../../data/pf_exercises/README.md) distinguishes
imported task text from curated reconstructions, placeholders and inherited
source inconsistencies. No claim here relies on all consistency-task means
and ranges being equal. The next implication is to preserve these distinctions
when judging what the five measures cover; no sixth measure, new judge,
generation change or model run has been added.

Calibration run [calibration_1](../../experiments/results/pf_rahimi_multi_theme_20261013/calibration_1/) (one attempt per cell and model, 8 generations, 16 judge calls): all 8 tasks ready, none truncated, no API errors, all 16 judgments scored at high effort on gpt-5.6-luna, and no gap of 5 or more. Only the calibration, not validation: eight tasks and two passes do not test the judge. Earlier scale-up runner ([run_pf_rahimi_scale_comparison.py](../../scripts/run_pf_rahimi_scale_comparison.py)) is superseded and single-cell.

**Limits.** Both judge passes use one deployment, so they are not independent raters. The "Luna 6"
request maps to gpt-5.6-luna, because gpt-6-luna returns 404 in this environment. The five examples are
the same in every cell and are not matched to any cell topic: they cover consistency (statistics),
apportionment, fair division and biking (rates). The four cells are a design choice, not a published
Rahimi condition.

**Next implication.** After the cells, examples and judge design are confirmed,
build the parallel runner from this config, then generate and judge. Errored
attempts are deleted and not replaced, so a cell may end below 30 ready tasks.

## October 13: frozen direct-prompt comparison with GPT-5 mini and GPT-4.1

**Question.** Do direct-prompted PF tasks from two other models show weaknesses
that paper-style ratings would not reveal? This tests a hypothesis; it was not
assumed in advance.

**Setup.** No pipeline change. Both models received the same V1 direct prompt,
learner context and target as the saved paper-setting benchmark
([prompt](../../src/generation/prompts/pf_paper_benchmark.yaml),
[config](../../experiments/configs/pf_paper_benchmark.json)). Runner:
[run_pf_direct_model_comparison.py](../../scripts/run_pf_direct_model_comparison.py).
Thirty attempts per model; all 60 were usable tasks, none truncated, none
replaced. GPT-4.1 used temperature 0. GPT-5 mini accepts no temperature setting,
as Luna in the original V1 condition. Calibration outputs (one per model) are
kept separately and not pooled.

**Audit.** The frozen evidence audit (v1.3) with the same two judges as the
54-task study: GPT-4.1 and GPT-5.4. Outcomes: 120 judgments, 119 parsed; one
GPT-4.1 judgment failed and counts as unknown.

| Property (consensus, out of 30 per model) | GPT-5 mini pass / unknown | GPT-4.1 pass / unknown |
|---|---:|---:|
| Target relevance | 24 / 6 | 29 / 1 |
| Accessible start | 30 / 0 | 29 / 1 |
| Task specification | 28 / 2 | 29 / 1 |
| Preserved discovery | 10 / 20 | 12 / 18 |
| Consequential choice | 19 / 11 | 9 / 21 |
| Distinct idea opportunities | 22 / 8 | 14 / 16 |
| Useful prior contrast | 19 / 11 | 6 / 24 |
| Mathematical support | 8 / 22 | 19 / 11 |
| Five-property conjunction | 1 / 29 | 3 / 27 |

No two-judge concern was confirmed for either model. Under the frozen rule,
GPT-5.4 "partial" findings count as unknown, not failure.

**Findings.**
- *Preserved discovery is weak for both models.* GPT-5.4 gave 12 of 30 supported
  for each model. The questions name methods: a keyword scan found a method term
  in 30 of 30 GPT-5 mini questions and 19 of 30 GPT-4.1 questions (exploratory;
  spot checks show "compute unit rates" and "use what you know about unit rates").
- *GPT-4.1 is weaker on choice and useful prior contrast, but only GPT-5.4 sees
  it.* Consequential choice: 9 of 30 versus 26 of 30 for GPT-5 mini. Useful
  contrast: 8 of 30 versus 20 of 30.
- *The GPT-4.1 judge is lenient.* It rated nearly every property supported for both
  models, including the properties GPT-5.4 found partial. A lenient judge can hide
  the same weaknesses paper-style ratings hide. Its leniency does not differ
  between the two generators.
- *No confirmed arithmetic error.* The six GPT-5 mini "arithmetic mismatches" are
  checker artifacts: the judge wrote a rounded decimal (for example 1.4667 for
  22/15), and the checker compared it exactly. Treating stated-precision rounding
  as verified would move GPT-5 mini mathematical support from 8 to 11 of 30. This
  sensitivity is not the frozen result. Most GPT-5 mini mathematics unknowns come
  from witnesses whose quotes are not exact or whose expressions do not parse.

**Limits.** Human ratings and student attempts are absent. GPT-4.1 is both a
generator and a judge. Preserved-discovery and choice differences are single-judge
findings. The rounding behavior is a known checker defect, not yet a versioned
correction.

**Next implication.** Do not claim these weaknesses until disputed tasks are read
by a human with the judges' quotes. Decide separately whether to add a third judge
outside the GPT-4.1 family and whether to version a stated-precision tolerance in
the checker.

## October 12: earlier proposed curriculum-grounding comparison

This initial proposal predates the frozen October 13 experiment above and is
retained as planning history, not as the executed protocol.

**Question raised during thesis discussion.** The user proposed testing whether
grounding generation in real curriculum evidence improves PF task design. This
is a newly scoped generation question, not a reopening of the closed
LLM-student/feedback campaign. No generation calls or implementation changes
were made for it in this discussion pass.

**What the earlier evidence does and does not show.** The
[Learning Commons paired pilot](../../experiments/results/learning_commons_pf_comparison_luna_20261009T151453Z/REVIEW.md)
already supplied local curriculum evidence to both arms; it added Learning
Commons descriptions to one arm. Both produced two of three tasks. That is
completion evidence, not a quality verdict. Assistant inspection found similar
speed-task contrasts, a disclosed spread-task conclusion, an available prior
quartile method that already answered the task, and questionable stops.
One attempt per topic and differing resource inventories do not establish
either a general benefit or absence of benefit. Older grounded recommendation
runs also preserved supplied expert lists and do not demonstrate independent
resource recovery.

**Proposed mechanism.** Retrieved evidence about previously taught mathematics
could help the generator provide an accessible start without revealing the
target discovery. It might instead add familiar terminology or unannounced
prerequisites with no educational improvement.

**Proposed bounds and controls, not a frozen executable protocol.** Compare the
latest pipeline with versus without retrieved curriculum/textbook evidence.
Keep target, grade, stated prior learning, model, other prompts and revision caps
identical. Hold expert resource lists and PF examples out of both arms. Define
whether the treatment is prior-learning evidence or target-level mathematical
references before execution; adding Learning Commons on top of existing
grounding answers a different question. Freeze retrieval, scorecard and
decision rule; use one or two separate execution-calibration cases. Each
grounded exercise is paired with an ungrounded twin from the same request. The
first proposal of three targets x three attempts (9 pairs) would require 8/9
decisive wins for a two-sided sign test at p < 0.05; the revised proposal is
five targets x four attempts (20 pairs, 40 generation attempts), requiring
15/20. Preserve failures and unresolved drafts; do not retune on the evaluation
cases or automatically launch further rounds.

**Proposed numeric scorecard (October 12 revision, after a literature review).**
Completion is reported but is not quality. Per-exercise counts: mathematical
validity (exact checks, unknowns separate), familiar method falls short
(deterministic where computable), and yes/no checks for giveaway, accessible
start and consequential choice, combined into an all-requirements pass. Simulated
learner measures over eight attempts per exercise: distinct solution-method
categories (after Kapur's RSM count; Kapur 2014; Kapur, Saba and Roll 2023;
counter-evidence in Loibl and Rummel 2014), target reached unaided, stuck rate
and designed-path coverage. Head-to-head: pairwise preference judged in both
orders (comparative judgement, Pollitt 2012; LLM pairwise evaluation, Liusie et
al. 2024 and Liu et al. 2024; position and distractor bias, Wang et al. 2023 and
Tripathi et al. 2025). Yes/no checks follow decomposed-checklist evaluation
(Lee et al. 2025; Cook et al. 2024; Moore et al. 2023), with two judges from
different model families, percent agreement plus Krippendorff's alpha or Gwet's
AC1, and a human sample. The proposed primary outcome is the all-requirements
pass, with pairwise wins and distinct methods as key secondaries. Grounding would
count as an improvement only with significantly more decisive pair wins on the
primary outcome and no loss of validity or more giveaways. No published
evaluation of generated PF problems using pairwise, checklist, solver-based or
diversity metrics was found; Rahimi et al. used human 1--3 ratings. These
references are not yet in the thesis bibliography. Even a favorable pilot would
establish design evidence only, not real-student approach diversity or learning.

The overview of the planned study is in
[THESIS_OVERVIEW.md, Section 6](../status/THESIS_OVERVIEW.md#6-curriculum-and-learning-commons-grounding-completed-pilot).
This earlier proposal is superseded by the authorized three-arm campaign above.
Its metric and significance assumptions remain historical proposals rather than
validated or implemented findings.

## Final scope: LLM-student path coverage and feedback

**Closure decision, October 11--12.** The user delegated the ending and thesis
boundary of the LLM-student component. Finish a bounded computational design
study, not a general student simulator or a learner-outcome experiment. The
contribution is a reproducible, source-quoted intended-path diagnostic plus
findings about simulator sensitivity and feedback limitations. Retain all
historical null results, including raw-attempt revision's lack of advantage.

The final [campaign protocol](../../experiments/configs/pf_path_coverage_final_20261012.json)
has two parts. First audit intended paths for the nine saved pipeline tasks
against the eight learner-role baseline attempts per task. This is retrospective:
both paths and attempts already exist. Count algorithms, insights, representations,
compound/partial paths and unexpected approaches separately, not different
formats or names as new mathematics. The assumed profile mix is a sensitivity
analysis, not a real class distribution or a calibrated forecast.

Second, one final structural intervention compares original designs, equally
resourced design-review restructuring, and coverage-informed restructuring on
three selected task-family cases. Feedback enters the design stage, not just the
finished prose. Other stage prompts and student instructions remain frozen.
The key hypothesis is that summaries of missed/reached intended actions can
guide a meaningful decision space without forcing student mistakes. The
comparison must beat design-review restructuring, not a weak generic prompt.

**Budget and stopping.** One excluded consistency calibration per arm, then
three cases per arm. Each fixed-D1, one-candidate pipeline attempt has a derived
maximum 15 stage calls; eight attempts cap generation at 120 requests.
Fresh evaluation of nine variants uses three model series/settings, three
solver/learner conditions and two repetitions: 162 calls plus 12 execution
controls. The final cap is 294 requests, one round. GPT-5.4 is a new model series
not used to form feedback, but is still the same provider lineage, not independent
human evidence. No additional paid automatic judge or open-ended search.

Both arms also receive the original task-only assessment written before the
learner diagnosis. Thus the baseline is a specific task-review intervention,
not uncritiqued regeneration. A prospective path codebook is hashed and included
in the student run's source snapshots before fresh evaluation starts. Original
versus revised path sets and their denominators are reported separately.

An exploratory gain requires supported improvements on at least two of three
cases over design-review alone, without mathematical/access regressions and
with fresh evidence of meaningful consequential approaches. A changing intended
path denominator cannot create an improvement by itself. Stop this final
campaign regardless of outcome: keep a useful diagnostic or a negative finding,
not a promoted claim without evidence. Genuine API/no-output errors remain
explicit; quality findings do not stop usable draft delivery.

**Implementation scope.** Add an optional design-feedback handoff to the existing
bounded pipeline, leaving default calls unchanged. A regression verifies selection
feedback edits the selected original design rather than whichever candidate was
most recently proposed; that tightly coupled defect was confirmed and corrected
before external coverage feedback. Implement reusable reachability/evidence
checks and profile-weight sensitivity, then document commands and thesis claims.
Software checks do not validate cognitive simulation.

**Outside this thesis component's completed boundary.** No new model training,
demographic student personas, individual human mastery inference, learned class
mixture, autonomous quality-based acceptance gate, human participant recruitment,
learning/transfer or state-of-the-art claim. Real student attempts and comparable
consolidation remain future evidence.

**Baseline coverage audit completed.** Nine source designs, 72 unique learner
attempts and 38 intended-path/reference definitions were checked, comprising
304 path-attempt classifications. The
[coverage artifact](../../experiments/results/pf_path_coverage_final_20261012/baseline_coverage.json)
preserves exact design quotations, attempt quotations, phases and unknowns.
All 24 pipeline speed attempts use whole-journey ratios and none executes the
anticipated stage-average route. All 24 consistency attempts calculate range;
none executes the intended squared-departure or signed-cancellation routes.
Valid absolute-departure/concentration alternatives appear, and division includes
local sequential-choice and blockwise-thirds solutions rather than the intended
trimming route. Missing paths are a task/simulator diagnosis hypothesis, not
incorrectness. The path audit is retrospective, not a newly independent test.
Structural calibration, prospective codebooks and final evaluation are pending.

**Final structural runs completed.** Both calibration attempts returned usable
drafts in 17 total stage calls; the six comparison attempts returned usable
drafts in 47 calls. All data-stage proposals eventually have accepted recorded
checks, but that is not an independent mathematical or educational pass.
Every stage prompt and source remains identifiable. The new prospective
codebooks contain 40 path/reference definitions across nine variants and were
hashed before the 162 fresh student requests. Twelve separate arithmetic
execution controls are correct.

The codebook author necessarily saw internal designs; its joint task observations
are retained separately from the final student-text-only review. A separate
reader sees only task, target and prior-learning specification, with no path
list, design notes, variant label or learner output. This avoids treating a
defect in an internal example as automatically a defect in the student task.
The fixed original tasks, general design-review restructuring and coverage-aware
restructuring are all evaluated; neither path-count growth nor raw stage
acceptance defines improvement.

Fresh evaluation and final task/path synthesis are running. GPT-4.1 sampling
temperature is explicitly 0.7; GPT-5.4 follows the existing API adapter's model
defaults without a temperature parameter, recorded in actual request settings.
The model-series transfer check is not an equal stochastic-control or
independent human validation.

**Fresh execution completed.** All 162 requests finish without API errors:
158 complete replies and four token cutoffs retained. GPT-5.4 completes all
54 replies, GPT-4.1 53/54 and GPT-4.1-mini 51/54. These are execution counts,
not student-fidelity rankings. Fresh usage is 90,954 input and 148,625 completion
tokens; the 12 execution controls add 2,390 and 690. The path codebook, exact task
texts and source snapshots were frozen before these attempts. Final semantic
path coding and synthesis remain pending at this point.

The separate student-text-only reviewer finds supported task mathematics in
three original and three coverage-informed variants, and two design-review
variants. The third design-review variant has a very small literal-decimal
inconsistency, not a generally infeasible exercise; this distinction must remain
visible. Both redesigned speed tasks introduce an actual adjustable rest and
route choice, unlike the fixed-rate original. The coverage variant's feasible
whole-block division does not require a universal nonatomic trimming theorem;
the internal design's unsupported general route is a separate path-coverage
limitation, not automatically a task-level invalidity.

**Initial final speed evidence.** The 54 speed responses (including solver
controls) all use aggregate distance and elapsed time successfully. Both
redesign arms now ask for an adjustable rest/route decision, but no learner
performs the intended leg-rate heuristic or a qualifying numerical trial search.
The original still elicits fixed whole-journey rates. This distinguishes improved
decision space in a task from actual method variation in this simulator cohort.
The other two task families and final synthesis are still being coded.

### Final findings and thesis boundary: component closed

**The bounded computational work is complete.** This is not a declaration that
the simulator is a realistic class or the generator produces human-validated PF.
It is a finished research component with working diagnostic/feedback entry
points, preserved experiments and a defensible limit on the claims.

1. **Designed paths are hypotheses that can be audited.** The nine-task
   retrospective map makes the difference between anticipated and actual
   mathematical actions explicit. Absent, partly executed and unsuccessful
   paths remain different from incorrect mathematics. Alternative valid methods
   are recorded rather than counted as failures to follow the design. Class
   mixtures of the two hypothetical profiles are sensitivity only; altering
   weights cannot produce a path absent in every sampled profile.
2. **Reachability depends on the simulator.** In the final fresh evaluation,
   original division's intended trimming structure is reached in 0/8 GPT-4.1
   learner replies and 4/4 GPT-5.4 learner replies. Reach means substantial
   execution, not that each application or general guarantee is correct.
   The task was unchanged. A missing path under one cohort therefore cannot
   establish a task defect or predict a real student frequency.
3. **Structural redesign can create a real decision space.** Both redesign
   arms replace the fixed-rate speed comparison with choice of route and
   maximum rest. Task-only review supports that change; all speed replies still
   use the aggregate-rate method rather than the anticipated stage-rate or
   numerical-trial paths. An actual adjustable task is not proof of more
   reasoning diversity in this simulator.
4. **Added benefit of coverage feedback is not established.** The final
   student-text-only review gives 2/3 original, 2/3 design-review and 3/3
   coverage-informed tasks meeting the predefined requirements. The margin +1
   is below +2. The sole mathematical-support difference is a tiny literal
   decimal discrepancy in the design-review division data; treating it as a
   tolerable approximation would leave 3/3 versus 3/3. Neither is evidence of
   a general advantage. Previous raw-attempt rewriting remains a separately
   recorded negative result, not overwritten.
5. **Internal-path validity and student-task validity differ.** The
   coverage-informed division task admits a feasible whole-block allocation,
   while additive block totals alone do not guarantee fractional valuations
   required by its intended trimming route. Such a missing assumption belongs
   beside the path diagnosis. The codebook author's design-aware observations
   are preserved separately from the strict task-only review; a flawed
   internal example is not automatically an impossible student task.

**Final task-only review, three cases per arm.**

| Outcome | Original | Specific design review | Review plus path coverage |
|---|---:|---:|---:|
| Mathematics supported at the stated student-task scope | 3 | 2 (one tiny exact-input discrepancy) | 3 |
| Target preserved | 3 | 3 | 3 |
| Accessible start | 3 | 3 | 3 |
| Central discovery not supplied | 3 | 3 | 3 |
| Consequential mathematical choice | 2 | 3 | 3 |
| All predefined design requirements | 2 | 2 | 3 |

These are label-hidden assistant judgments, not human ratings, a PF score or
powered inference. For the consistency family, valid mean/median-centered
absolute, squared, maximum and cutoff measures appear. A strict intended
definition can fail to match an equivalent-ranking or differently centered
alternative; those alternatives remain unexpected paths, not mathematics
errors. Path sets and normalization requirements differ across designs and
are displayed, so a changed denominator is not interpreted as improvement.
The two new speed designs have only one aggregate-rate idea enacted; its
application to a new rest maximum is a compound goal, not a second algorithm.

**End-to-end artifacts and scope.**

- [Final report](../../experiments/results/pf_path_coverage_final_20261012/final_report.html)
  displays original/design-review/coverage arms, original path audit, fresh
  GPT-4.1 versus GPT-5.4 learner reach and uncertainty.
- [Nine-task coverage](../../experiments/results/pf_path_coverage_final_20261012/baseline_report.json)
  retains all 38 source path/reference definitions and 304 matched historical
  observations, plus assumed-mixture sensitivity.
- [Prospective codebook](../../experiments/results/pf_path_coverage_final_20261012/path_codebook.json)
  and [freeze record](../../experiments/results/pf_path_coverage_final_20261012/codebook_freeze.json)
  prove the 40 final path/reference definitions preceded new attempts. They were
  not edited to match observed outcomes.
- [Strict student-task review](../../experiments/results/pf_path_coverage_final_20261012/task_ratings_student_only.json),
  three source-quoted path-coding files and
  [final interpretation](../../experiments/results/pf_path_coverage_final_20261012/final_interpretation.json)
  separate task quality, internal route assumptions, observable math and
  feedback conclusions.
- [Fresh attempts](../../experiments/results/pf_path_coverage_final_20261012/attempts/attempts.html)
  retain all 162 requests, including four token cutoffs. All 158 complete
  replies and all partial work were coded; 12 execution controls are separate.
- [Reusable coverage checks](../../src/evaluation/pf_path_coverage.py),
  [campaign entry point](../../scripts/run_pf_path_coverage_final.py) and
  [offline report](../../scripts/report_pf_path_coverage_final.py) complete the
  bounded workflow. The optional design-stage feedback hook leaves default
  generation unchanged; the global prompt package is not promoted.

**Cost and stopping.** Actual final requests are 238 of the 294 maximum:
64 generation requests (17 calibration, 47 comparison), 162 new attempt
requests and 12 execution checks. Student token usage is recorded above;
generation-stage usage is unavailable in the existing diagnostic tracer and is
not imputed. Retrospective coding and assistant reviews made no additional
paid requests. Source snapshots preserve the exact implemented conditions and
partial/error records; all model calls and evidence anchors were checked.

No more automatic model experiments follow this campaign. The thesis can claim
a computational diagnostic method and findings about prompt sensitivity,
unreached design hypotheses, model dependence and limits of feedback-based
improvement. It cannot claim realistic learners, empirical class distributions,
real student-path rates, human-validated PF superiority, learning/transfer or
state of the art. Such studies are future work, not unfinished parts of this
bounded implementation.

**Final verification.** The affected existing test invocation passes 260 tests
covering design selection, diagnostic delivery, data/writer behavior, learner
records, reference coding, matched revision and final path reporting. Targeted
Ruff, Python compilation and source/attempt-evidence checks pass. The final
results page renders all nine variant panels and the actual model-dependent
reachability chart. No failed attempt or historical result was overwritten.
The thesis method/experiment/result/discussion and entry-point documentation
were updated. `make thesis` was attempted but cannot build the PDF because
`latexmk` is absent; no available local LaTeX alternative was found. Source links,
citation keys and structural checks were verified, but this is not a successful
PDF build.

## October 11: draft-first completion policy

**Problem and agreed change.** The frozen comparison lost six intervention
outputs at design selection and one baseline output at an omission-quote check.
The user requested no quality-based blocking and chose bounded revision followed
by the latest usable draft. The hypothesis is that treating these findings as
revision feedback preserves exercise production without misreporting failed
checks as passes. This is a completion-policy package, not a measured PF-quality
improvement or an isolated prompt intervention.

```text
Design concern -> revise, at most twice -> continue with usable brief + findings
Numerical failure -> repair, at most three data calls -> continue with data + findings
Textual contradiction / unknown -> retain finding for writing and evaluation
Writer or omission issue -> revise, at most three writer calls -> retain usable draft
```

- [Design selection](../../scripts/design_brief_stage.py) always asks for a
  candidate and a concrete concern. A concern or an unusable selection reply
  triggers a revised proposal and another selection. After two revisions, an
  unresolved rejection continues with the latest usable brief, explicitly
  labelled `review_needed`. All proposal and selection attempts are retained.
- [Data checking](../../scripts/design_data_stage.py) still computes the supplied
  conditions and freezes meanings, units, roles, shapes and formulas during
  values-only repairs. A textual contradiction no longer prevents repairing a
  separate numerical failure. A usable data proposal proceeds even if those
  checks remain failed; `accepted` retains the check result, while `proceed`
  means data exist for writing. Unknowns and contradictions remain findings.
- The writer retries refusals, missing task fields and invalid omission records.
  After its budget it retains the latest nonempty title, body and question with
  `quality_findings`; invalid omission metadata are kept in `unverified_withheld`
  and the original responses, not presented as verified omissions. `ready` means
  text was produced, not that the mathematics or PF design passed evaluation.
- The CLI, diagnostic/sweep route, comparison runner and data-role replay now
  write available data rather than requiring checker acceptance. Task displays
  show unresolved draft findings. Explicit historical protocols remain historical.
- API errors, exhausted execution budgets, or absence of usable output remain
  visible execution failures. No infinite retries, invented success, or overwrite
  of the completed comparison is permitted. Future experiments need a new frozen
  directory and a request budget covering revisions; the earlier nine-call
  protocol is not a guarantee that every new-policy attempt can finish.

**Validation and limitation.** Existing software tests cover repeated selector
rejection, successful revision, numerical repair exhaustion, textual conflicts,
quote repair, retained drafts after unusable replies, genuine no-output errors,
and persisted request counts. The focused existing test run passed 368 tests,
and targeted Ruff checks passed. These use controlled model replies, not generation
or student evidence. Fresh model evidence under this policy is now recorded in the
method comparison below. Production and independently evaluated quality must
remain separate; more drafts alone are not better PF.

## October 11: starting research on LLM student attempts

**Research question.** Can independently specified LLM learners help diagnose
whether our frozen PF exercises elicit different mathematical approaches, rather
than merely recover approaches the generator or experimenter already supplied?
The user authorized repository/literature research and a bounded first diagnostic
study. Keep the PF generator and its completed comparison unchanged. An LLM's
written working is observable model output, not access to a student's cognition
or evidence of human learning.

**Starting evidence, not a new validation.** The repository's
[functional-diversity record](../mcq/functional-diversity/MCQ_FUNCTIONAL_DIVERSITY_RESEARCH_INTENT.md)
already distinguishes prescribed errors from independently specified student
states. Its historical no-options calibration recovered an instructed wrong
rule in 170/180 GPT-4.1 responses; showing options reduced recovery to 123/180
under the original prompt. These are instruction-adherence counts, not learner
fidelity. The generated-option pilot used non-independent profiles, and its
association score could be high with no generated distractor coverage. Do not
reuse that score as an open-ended PF outcome.

The [method chapter](../../thesis/sections/03-method.tex) describes simulation and
refinement as prototypes/proposals. Five MCQ ranking matches from in-sample
notebook work do not validate reasoning, knowledge limitations or PF transfer.
Primary-source verification corrected `lu2024` in
[the bibliography](../../thesis/references.bib): **Xinyi Lu and Xu Wang,
Generative Students: Using LLM-Simulated Student Profiles to Support Question
Item Evaluation**, Learning @ Scale 2024, pp. 16--27,
[DOI 10.1145/3657604.3662031](https://doi.org/10.1145/3657604.3662031).
The earlier authors and title were incorrect. Its domain is usability heuristics,
not mathematics, and its prompts ask an instructor to predict student answers.

### What is already in the repository

| Surface | What it provides | Evidence boundary / reuse decision |
|---|---|---|
| [Student profiles](../../src/simulation/student_profiles.py) | Knowledge-component maps, mastered/partial/unmastered states, Eedi-derived error descriptions, seeded profile generation | `to_prompt_block` injects `What you do instead: {err.rule}`. Retain as historical prescribed-error calibration; do not reuse that prompt as spontaneous PF reasoning. Ability-based random mastery is a model assumption, not a diagnosed learner. |
| [PF evaluator](../../src/simulation/evaluator.py) | Planned response/RSM record and evaluator interfaces | `evaluate` and `compute_diversity` raise `NotImplementedError`. Its `productive_failure` boolean has no implemented empirical meaning. The new diagnostic does not fill that field from a model opinion. |
| [Refinement notebook](../../notebooks/07_student_simulation_exercise_refinement.ipynb) | Proposed student/feedback/refinement workflow | No completed current-PF refinement or student outcome study. Keep it exploratory. |
| [Simulation notebook](../../notebooks/08_simulated_student_pipeline.ipynb) | Profile inspection, probabilistic MCQ sampling, in-sample distribution comparisons and a short LLM roleplay demonstration | The sampling function makes no LLM call and uses Eedi-linked errors. TV distance 0.242 and rank correlation 1 on five questions describe that sampler, not LLM-student fidelity. Population-mixture adjustment reuses the same quiz, not held-out PF attempts. |
| [Functional-diversity calibration](../mcq/functional-diversity/MCQ_FUNCTIONAL_DIVERSITY_MEASUREMENT.md) | Saved rule-following, visible-options and control experiments | Tests recover prescribed errors. The 30-call generated-option pilot is non-independent; high profile/choice association can coexist with zero generated-option coverage. Do not transfer its MCQ score to PF. |
| [Prior-method benchmark](PRIOR_METHODS_BENCHMARK.md) | Resource/method generation and the Liu misconception-recovery comparison | Predicted method lists are not attempted solutions. Useful origin evidence, not simulator validation. |
| [Frozen direct/pipeline comparison](../../experiments/results/pf_method_comparison_draft_first_20261011/fresh/side_by_side.html) | Identifiable student-facing tasks, explicit prior-learning records and exact mathematical checks | Reuse task text and common learner specifications; exclude design notes, source method, ratings and check evidence from learner inputs. All topics are inspected development material. |

**Notebook verification detail.** Notebook 08 cells 25--27 preserve three
displayed model replies, two visibly cut off and the third reporting `3x - 5`
before beginning a self-correction. Prompts were tightened between them and the
final prompt explicitly contains the target question's correct expansion of the
first bracket and prescribed wrong expansion of the second. Code also contains
mock/fallback answers, and the selected-letter heuristic can mistake a fragment
for a completed choice. These are anecdotal, answer-exposed roleplay outputs, not
zero demonstrated outputs and not three provenance-complete successful
simulations. There is no request ledger or matched PF validation in that notebook.

### Primary-paper research and applicability

The following is a scoped primary-source review, not an exhaustive literature
novelty claim. Public papers and official repositories were inspected without
uploading private code or student data. Preprints and published studies remain
distinct. Counts below describe each study's own setting, not our pilot.

| Primary source | What it actually studies / supports | Application to our PF investigation |
|---|---|---|
| [Lu and Wang, Generative Students (L@S 2024)](https://arxiv.org/html/2405.11591v1) | Mastered/confused/unknown knowledge components; 45 synthetic learners x 20 usability MCQs, compared with 100 college students. Aggregate item-performance correlation r=0.72. Confusion examples prescribe mappings. | Reuse explicit prerequisite profiles, paired comparisons and independent calls. Do not import confusion examples as evidence that errors emerge naturally, or claim mathematics/PF validity from an item correlation. Instructor-predictor framing is a future comparator, not implemented in this pilot. |
| [Liu et al., Novice Learner and Expert Tutor (2023)](https://arxiv.org/abs/2310.02439) | 213 Eedi questions and 482 misconception-associated choices; GPT-4 correct-solving accuracy 94.8%, specified-wrong-choice recovery 61.7%. | A strong reason to separate solving competence from misconception reproduction. Named errors/options are an auxiliary calibration condition, not the primary spontaneous attempt input. |
| [Liu et al., Do LLMs Make Mistakes Like Students? (2025 preprint)](https://arxiv.org/abs/2502.15140) | Ordinary-model likelihoods over supplied MCQ options; 3,202 items including 807 mathematics items, each with at least 50 human responses. Some unrequested wrong choices align with popular human distractors. | Include an ordinary solver baseline rather than assume personas improve realism. Existing wrong options constrain the output space; this does not establish open-ended method fidelity. |
| [Scarlatos et al., SMART (EMNLP 2025)](https://aclanthology.org/2025.emnlp-main.1274/) | Ability-conditioned short responses trained to match item-response-theory scores. Reading and programming datasets; held-out-item difficulty prediction with separate scoring. | Reuse matched learner sampling, held-out items and independent scoring. Score/difficulty alignment is not reasoning fidelity. Training metadata with generated correct solutions must not become learner input for our solution-blind task. |
| [Srivatsa et al., Can LLMs Reliably Simulate Real Students' Abilities? (2025 preprint)](https://arxiv.org/abs/2507.08232) | Eleven models, 489 text-only NAEP MCQs; no model/prompt combination aligns across all subjects/grades. Free responses and diagram/table items excluded. | Grade alone is not a sufficient learner model. This negative finding motivates prerequisite evidence and controls, not stronger orders to act ignorant. |
| [Scarlatos et al., Simulated Students in Tutoring Dialogues: Substance or Illusion? (2026)](https://arxiv.org/html/2601.04025v2) | 1,911 mathematics dialogues, with 190 human-rated turns from 38 dialogues. Evaluates dialogue acts, correctness, underlying error, language and estimated knowledge change separately. Human-rated DPO same-error score is 0.0612 despite much stronger act agreement. | Borrow the multidimensional validity framework, not an aggregate simulator score. Tutor-conditioned dialogue is not unaided PF. Some baselines use future-dialogue/oracle information; official code conditionally appends answers and solutions. |
| [Duan et al., Who Am I? (2026 preprint)](https://arxiv.org/html/2605.30051v2) | Past-history-derived profiles; 670 students, 1,775 dialogues and 66,705 QA records. Better real-utterance/behavior prediction, but same-error fidelity remains limited. | The preferred longer-term route: freeze profiles from actual pre-task evidence. We have no equivalent individual PF learner histories, so current profiles must remain hypothetical. |
| [Wang et al., BEAGLE (2026 preprint)](https://arxiv.org/html/2602.13280v2) | Python process simulation with a cognitive controller, Bayesian knowledge tracing and explicit flaw injection; 71 human raters made 852 trace classifications. Perceptual/process similarity, not causal learning validity. | Reuse bounded process observation and trajectory-level uncertainty if interactive simulation becomes necessary. Do not inject flaws or enforce process variety into the main PF attempt cohort. |
| [Do et al., Simulating Students or Sycophantic Problem Solving? (2026 preprint)](https://arxiv.org/html/2605.12748v1) | Seven models; given wrong answers followed by targeted, unrelated or generic corrective feedback. Many models change answers under almost any feedback. | Before refinement, test targeted feedback against no-feedback/repetition and generic reconsideration. Their constructed correction criterion is not observed human learning, and initial errors are supplied rather than spontaneous. |
| [Wu et al., Embracing Imperfection (2025 preprint)](https://arxiv.org/html/2505.19997v2) | Python histories -> knowledge graph -> predicted errors -> behavior-matched refined solution. Main analytical results use 15 learners; a 100-learner extension is separate. | History-grounded profile construction is useful. Selecting/refining attempts to match predicted errors would manufacture our desired diversity; do not adapt that enforcement as unbiased PF sampling. |
| [Xu et al., EduAgent (2024 preprint)](https://arxiv.org/html/2404.07963v1) | Lecture behavior, gaze/mouse activity, memory and quiz answers; experimental history prediction uses 310 real learners. A separate 705-agent cohort has no human ground truth. | Modular separation of profiles, state and actions is useful. Lecture attention is not pre-instruction mathematical reasoning; internal persona correlations are not fidelity. Do not copy demographic/ability stereotypes into profiles. |
| [Puech et al., pedagogical steering for PF (Findings ACL 2025)](https://arxiv.org/html/2410.03781v2) | 15 PF problems; preliminary 24 simulated conversations; a field study with 17 ninth-graders and 15-minute tutoring sessions. Evaluates tutor strategy and RSMs, not retention/transfer. | Closest PF bridge: code mathematical representation/solution methods and keep tutoring separate from initial generation. Section 4.5 explicitly does not assume the LLM accurately models student learning. It is not validation of our learner simulator. |
| [Yang et al., StudentSim (September 2026 preprint)](https://arxiv.org/html/2609.01591v1) | Pooled training followed by per-student adapters. The 60-learner benchmark includes only 15 mathematics learners; mathematical fidelity uses 990 held-out recorded answers. Fidelity 0.6384 versus GPT-5.4 0.6121 is candidate-answer matching. | Useful longer-term history/individual conditioning. Current target answers appear among shuffled candidate choices; generated reasoning is conditioned on already observed answers. Its 879 responsiveness records are synthetic corrections from 293 wrong-answer cases x three feedback styles, not observed human revisions. Do not treat responsiveness as learning or import the closed choice space into PF. |

**Public implementations and input hazards.**

- [umass-ml4ed/sim-student-eval](https://github.com/umass-ml4ed/sim-student-eval)
  provides separate act/correctness classifiers and simulator baselines. At the
  [inspected commit's formatter](https://github.com/umass-ml4ed/sim-student-eval/blob/4c94a33e6053fd7acf812ff122deab16dcd3c126/sim_student/prompting.py#L87-L96),
  a solvable annotation adds the correct answer, solution and option explanations.
  Both simulator prompt routes use that formatter. This is a conditional
  inference-exposure route, not proof every published condition populated it.
  The MIT code license explicitly excludes the associated dataset.
- [microsoft/StudentSim](https://github.com/microsoft/StudentSim) is MIT code;
  FoundationalASSIST data require a separate Responsible Use Agreement and are not
  redistributable under that code license. Initial-answer prompts include previous
  failed-problem keys, recent history and current candidate options; supervision
  contains answer-conditioned reasoning. Keys used only in training are not,
  by themselves, current-answer inference leakage. The inspected implementation
  also differs from the paper on revision answer-text versus letter scoring and
  two/three versus four candidates. Resolve these before reproduction.
- [EduAgent](https://github.com/EduAgent/EduAgent) is an architectural comparator,
  not a ready PF simulator. The official
  [PF task repository](https://github.com/eth-lre/Productive-Failure-Problems) and
  [StratL implementation](https://github.com/RomainPuech/StratL-Pedagogical-Steering-of-LLMs-for-Tutoring)
  support future tutoring comparisons; tutor-side solutions must not cross into
  learner inputs. No external framework, weights or dataset was installed.

**Research implication.** No inspected source establishes the exact construct we
need: solution-blind, profile-conditioned, spontaneous pre-instruction PF
attempts validated against comparable real learners. This is a gap in this scoped
review, not proof of universal novelty. Start with a small prompt-based diagnostic,
then compare history-grounded or trained simulators only when suitable evidence,
licenses and a learner-fidelity evaluation are available. Keep first-attempt
variety, adherence to a hypothetical profile, human fidelity, feedback
responsiveness and learning as separate claims.

**Bounded diagnostic, frozen before requests.** The
[probe protocol](../../experiments/configs/pf_student_probe_20261011.json) compares
an ordinary solver, a hypothetical learner with the recent prerequisite record,
and the same record with one omitted prerequisite. The gap is arithmetic mean
for consistency and Divider-Chooser for fair division; it is not a supplied
wrong procedure or a measured human mastery state. Each condition attempts the
same four saved tasks twice with GPT-4.1-mini and GPT-4.1: 48 fresh requests.
Eight separate illustrative arithmetic controls check execution first. The cap
is 56 requests, 2,400 completion tokens each, zero transport retries and one
round. Temperature is 0.7; actual settings and usage are traced. No feedback,
generator revision, rejection sampling or failed-attempt replacement is allowed.

**Where the three conditions come from.** They are an assistant design decision
for this diagnostic, informed by the literature, not an established or validated
learner taxonomy. The recent-learning records reuse the frozen learner
specifications of the expert-direction pilot, which were normalized from the
expert papers' prior-knowledge descriptions (for example Kapur and Bielaczyc's
speed, ratio, LCM/HCF and trial-and-error resources). The ordinary solver is a
control motivated by evidence that unprompted models already produce some
student-like errors. The one-omitted-prerequisite condition loosely follows Lu and
Wang's "unknown" knowledge components; which resource to omit was chosen by the
assistant, not derived from learner data.

The historical [skill-based profiles](../../src/simulation/student_profiles.py)
differ in source and mechanism: Eedi MCQ skills, mastered/partial/unmastered
levels sampled from a random ability value, and an injected
`What you do instead: {err.rule}` procedure for each unmastered skill. That
design measures whether a model follows a supplied mistake, and Eedi MCQ skills
do not cover these PF task families. The new records inject no error, but they
are binary and contain no partial understanding or misconception. A belief-level
middle ground, describing a confusion without its procedure, was proposed in the
[functional-diversity intent](../mcq/functional-diversity/MCQ_FUNCTIONAL_DIVERSITY_RESEARCH_INTENT.md)
and has not been run.

The [runner](../../scripts/run_pf_student_probe.py) and
[prompt/parser module](../../src/simulation/pf_student.py) preserve source and
input snapshots, exact requests, raw replies and explicit parse/API failures.
Dry-run input isolation and focused software checks passed before calibration
(56 tests across the probe and shared callers). Calibration and fresh generation
are separate commands so execution evidence is inspected before expanding.
Task selection is deliberately diagnostic, using one direct and one pipeline
task in each of consistency and fair division; it is not a method-ranking sample.
No student-fidelity promotion threshold is asserted without a human anchor.

**Completed execution, before method coding.** All 56 requests finished without
API errors. All eight separate arithmetic controls produced parseable responses
with the expected answer. Fresh attempts produced 42 complete parseable responses
and six invalid JSON replies; all six have `finish_reason=length` and their raw
partial work is retained. GPT-4.1-mini has 19/24 complete responses, GPT-4.1
23/24. These are execution counts, not a model-fidelity ranking. A token cutoff
must not become "the student got stuck."

Fresh requests record 27,220 input and 61,636 completion tokens; calibration adds
1,596 and 563. Summed request durations are 455.225 seconds fresh and 7.429 seconds
calibration. Prices are unverified, so no monetary cost is claimed. Actual
temperature 0.7 and 2,400-token caps, request-start/finish pairing, 56 unique
request IDs and 12 source/input snapshots were checked. No request was replaced.
The [anonymous review packet](../../experiments/results/pf_student_probe_20261011/review_packet.json)
contains only the task, written reply and execution status; its key is stored
separately. Coding is assistant review with model/profile labels hidden, not
independent human blinding.

### First PF learner-probe findings

All 48 written replies were coded from the anonymous packet before opening the
key. The [coding artifact](../../experiments/results/pf_student_probe_20261011/review_coding.json)
records applied mathematical approaches and case-specific arithmetic/feasibility
findings. Method categories were used after generation, never supplied to the
learner. The [summary](../../experiments/results/pf_student_probe_20261011/summary.json)
retains counts by task, profile and model; the
[attempt gallery](../../experiments/results/pf_student_probe_20261011/attempts.html)
shows the work, including truncated responses. This is assistant coding without
independent human agreement or a validated behavioral taxonomy.

**Observed effect: prerequisite prompts change the method.** Across the two
consistency tasks and both models, ordinary solvers explicitly use a named
variance/standard-deviation procedure in 7/8 attempts. Recent-prerequisite
learners do so in 0/8, and one-prerequisite-gap learners in 0/8. All 16
learner-role consistency attempts instead apply range; several additionally use
concentration or absolute departures. Counts record methods appearing in a
written attempt, not mutually exclusive labels or real-student frequencies.
Constructing a measure from arithmetic is permitted; absence of the word
"variance" does not prove that the underlying reasoning is novice reasoning.

One matched example on the printer task:

| Condition, same GPT-4.1 and same exercise | Actual written mathematical work |
|---|---|
| [Ordinary solver](../../experiments/results/pf_student_probe_20261011/fresh/fresh-consistency_direct-gpt41-ordinary_solver-1/result.json) | Names standard deviation and computes approximately 1.15 versus 1.63. |
| [Recent prerequisites](../../experiments/results/pf_student_probe_20261011/fresh/fresh-consistency_direct-gpt41-recent_prerequisites-1/result.json) | Computes range 4 for both, then distinguishes four central 8s from two central 8s and tests another pair of data sets. |
| [Arithmetic mean omitted](../../experiments/results/pf_student_probe_20261011/fresh/fresh-consistency_direct-gpt41-one_prerequisite_gap-1/result.json) | Computes the same ranges, then reasons about the frequency of central/extreme readings without calculating a mean. |

These are actual model responses, not illustrative students. All recommend
Printer A, but their mathematics differs. This shows why final answer diversity
would miss a useful contrast and display-format diversity would overstate one.

**Limit: an omitted prerequisite is not removed knowledge.** On the second
consistency task, 2/4 gap-profile attempts still calculate arithmetic means and
absolute departures, despite arithmetic mean being absent from the record.
The other task has 0/4 such mean calculations. A shorter recent-learning record
is not a cognitive intervention that prevents calculation or invention.
The two gap replies also miscount large departures, illustrating a written
mathematical defect, not verified resemblance to a student's error.

**Fair division exposes a different problem.** All 24 allocation attempts apply
claim-based, greedy or proportional allocation reasoning; some additionally
search whole blocks or repair a tentative split. No response implements the
simple, valid equal fraction of *every* block as its complete allocation.
There is variation within allocation construction, but different schedules are
not automatically different mathematical methods. Several completed responses
double-count assigned value, leave time unassigned, or miss a strict fair-share
threshold after rounding. For example, one recent-prerequisite reply on the
three-artist task gives B only 6 rather than the required 20/3 while claiming
an extra value from a block already entirely allocated to A.
These are inspectable defects in written model work, not evidence that the task
caused productive failure in humans.

| Assistant mathematical coding, including visible partial work | Consistency (24 requests) | Fair division (24 requests) |
|---|---:|---:|
| Written mathematics supported | 21 | 7 |
| Concrete arithmetic/claim/allocation defect | 2 | 13 |
| Overall interpretation/completion remains unknown | 1 | 4 |

This coding is not a PF score or model ranking. "Supported" does not prove an
invented criterion is the best criterion or a specific allocation procedure
works generally. A partial raw response is unknown unless a concrete defect is
already visible; some token-truncated replies therefore have a known arithmetic
defect but are still incomplete execution outputs. The one parsed
`unfinished=true` reply has correct range calculations and no completed
recommendation: do not equate that with a mathematical failure.

**Decision.** Stop this bounded first round; no prompts were tuned against its
outputs and no simulator-generated PF refinement was attempted. The pilot
establishes **prompt-sensitive written method differences**, not valid simulated
student populations. Use attempts as diagnostic material and keep the ordinary
solver comparator. Before relying on them to select or refine PF tasks, the next
research question is whether learner profiles derived from independently
collected prerequisite work/history improve fidelity to real first attempts.
Neither stricter "be wrong" instructions nor matching final-answer distributions
answers that question. Feedback-based revision remains a separate future
experiment, with neutral/no-feedback controls to detect indiscriminate answer
changing. No additional live round is started here.

The reusable input-isolation and evidence distinctions were captured in the
existing PF experiment skill and repository instructions. Final targeted
validation passes 59 tests across the probe, reporting and existing callers;
Ruff and script compilation pass. Reporting/persistence changes after execution
are separately identifiable; the saved run preserves its actual source snapshots.

### October 11: source-normalized Kapur pathway reference check

**Authorized aim, frozen before model calls.** The user approved the small check
of whether unprompted LLM attempts include pathways reported from real Grade 7
groups. The [protocol](../../experiments/configs/pf_kapur_reference_20261011.json)
uses a concise new paraphrase of the bicycle-handover scenario, verified against
the supplied paper's Appendix A (journal pp. 81--82, PDF pp. 38--39). It changes
names, supplies the remaining 5 km directly, and makes constant-rate/no-wait
assumptions explicit. Mira rides at 150 m/min and walks at 30 m/min; Leon rides
at 200 and walks at 50. The source walking estimate is 450 m in 13--15 minutes:
30 m/min is the normalized 15-minute endpoint, not an exact original measurement.
Omitting the initial shared journey and dialogue removes data-extraction and
interpretation work. This is a source-normalized task-family check, not replay
of an original classroom condition.

An independent exact check gives a feasible handover 3,400 m from the starting
point and 76 minutes for both journeys; those values are not supplied to learners
or predictors. Walking and riding ratios differ (5/3 versus 4/3), preserving a
reason a single raw-speed-ratio partition may be inadequate.

**Bounded condition.** Twenty-four learner requests: two hypothetical profiles
(usual prerequisites, ratio/proportion omitted), two existing models, six fresh
independent repetitions. Four ordinary-solver attempts and two prediction-only
calls provide distinct controls. Four separate distance/rate arithmetic checks
precede these 30 fresh requests; maximum 34 calls, one round, unchanged
learner-system prompt, temperature 0.7 and 2,400 completion tokens. Prediction
calls anticipate pathways without being given the nine reference labels; predicted
categories are not enacted attempts. No forced error or task-specific expected
method is supplied.

The paper's nine observed categories are frozen as a coding reference before
outputs: qualitative walk-more insight, complementary distances, diagram,
LCM/HCF, ratios, brute-force trial, ratio-informed trial, multiple-variable algebra
and single-variable algebra. Insights and representations must be reported
separately from algorithm diversity. A correct single-variable equation is not
called failed merely because human groups struggled with algebra. Only actual
unsuccessful intermediate work or an unfinished solution is coded as such;
mentioning possible methods is separate.

**Interpretation correction.** Earlier chat suggested that absence of failed
paths would prove the simulator too competent, and their presence would identify
generated-task weakness. Neither inference follows from one case. Absence could
reflect competence, prompt framing, a simplified task, individual versus group
interaction, or small samples; presence could be memorized/roleplayed. The
reference categories come from group discussions/artifacts (journal pp. 58--61),
not individual frequency data, and some qualitative categories were observed in
all groups. We are not fitting a real class distribution or setting a human
fidelity pass threshold. The result can inform use of the simulator, not
establish realistic learners or learning.

**Execution complete.** All four arithmetic controls return 6 minutes and all
30 fresh requests produce parseable output, without API failures. An independent
assistant reader is coding the 28 actual attempts and two predictions with
model/profile labels hidden; reference categories are visible only to that
reader. All 34 request pairs, source snapshots (including the supplied PDF),
unchanged settings and solution-blind input boundaries were verified. No
response was replaced or revised.

**Completed source-category coding.** Label-hidden assistant reading of the
28 enacted attempts and two prediction responses produced the following.
Positive categories and unsuccessful-work findings have exact saved-output
quotations. This is not independent human agreement or a realistic frequency fit.

| Documented category | Learner attempts (24) | Ordinary solver (4) | Predicted only (2) |
|---|---:|---:|---:|
| Qualitative insight: faster friend walks more | 19 | 4 | 0 |
| Complementary distances across the two journeys | 24 | 4 | 0 |
| Actual journey/partition diagram | 0 | 0 | 2 |
| LCM/HCF partition strategy | 0 | 0 | 2 |
| Ratio-based partition strategy | 0 | 0 | 2 |
| Numerical trial and checking | 6 | 0 | 2 |
| Ratio-informed trial and checking | 0 | 0 | 0 |
| Multiple-variable algebra | 0 | 0 | 0 |
| Single-variable algebra | 19 | 4 | 2 |

The learner union covers four of nine source categories, but two are insights:
actual algorithm coverage is two of six. One attempt uses both numerical trials
and later algebra, so method counts overlap. A trial grid is not a journey
diagram, and reproducing the shared partition relationship is not another
independent algorithm. The prediction union covers five categories/four
algorithms, but anticipating an approach is not enacting it.

**Observed unsuccessful work, not assumed productive failure.** Seven learner
attempts show unsuccessful intermediate work: six test distances with unequal
arrival times, one makes an algebraic fraction-conversion error and keeps an
incorrect answer despite its own unequal-time check. Of the six trial responses,
four finish correctly (one switches to algebra) and two explicitly stop
unfinished. Overall learner outcomes are 21 correct, two unfinished and one
incorrect; ordinary solvers give four correct algebraic solutions. Rejecting
trial guesses is part of a legitimate search method, not by itself evidence of
a student's conceptual failure or subsequent learning.

**Model/profile dependence.** All twelve GPT-4.1-mini learner responses use
correct single-variable algebra, regardless of ratio/proportion being omitted.
GPT-4.1's full-record learners use algebra in 5/6, trials in 2/6 (one overlap),
and finish correctly in 5/6. Its omitted-ratio learners use algebra in 2/6,
trials in 4/6 and finish correctly in 4/6. This difference is descriptive for
six repeated calls, not an empirical distribution of student states. Neither
profile produces the documented ratio-partition or LCM-partition failures.

**Coding correction retained.** Initial reading wrongly counted common-denominator
calculation while solving an equation as the LCM/HCF partition strategy.
The frozen definition required using factors/multiples to choose or test the
partition. Twenty-two attempt-level positives were removed: 17 remain explicit
LCM mentions inside algebra; five unnamed denominator-clearing cases are not
separate LCM labels. Only the two predictions anticipate the distinct strategy.
The [initial coding](../../experiments/results/pf_kapur_reference_20261011/pathway_coding_initial.json),
[corrected coding](../../experiments/results/pf_kapur_reference_20261011/pathway_coding.json)
and [verification](../../experiments/results/pf_kapur_reference_20261011/coding_verification.json)
preserve the correction without re-running models or changing evaluation to
improve the result.

**Research implication.** The binary claim "all simulated learners simply solve
like experts" is not supported here: some engage in repeated numerical attempts
and some do not finish correctly. Equally, reproducing real group pathway
distribution is not established: the enacted range remains narrow, documented
ratio/LCM approaches are absent, and predictors can name them without producing
them as attempts. The study therefore supports tentative model-path diagnostics,
not automatic attribution of a missing path to bad task design.

The normalized task, short individual responses, unvalidated profiles,
potential prior exposure and sample size remain alternative explanations.
The paper's group artifacts/discussion contained opportunities for collaboration,
representations and many transitions that these independent text calls do not
replicate. No path-frequency data were fitted, no classroom mixture was validated,
and no human learning or simulator-driven improvement follows. Stop this bounded
reference round; no forced-error prompt or new generation gate is introduced.
For later design-path evaluation, report intended paths as reached/not observed/
unknown and keep simulator limitations beside the task diagnosis.

The [reference gallery](../../experiments/results/pf_kapur_reference_20261011/reference.html),
[counts](../../experiments/results/pf_kapur_reference_20261011/summary.json)
and [exact normalized solution check](../../experiments/results/pf_kapur_reference_20261011/exact_check.json)
retain all outcomes. Fresh usage is 15,854 input and 25,927 completion tokens;
calibration adds 828 and 393. Actual models are GPT-4.1 and GPT-4.1-mini dated
2025-04-14. All 34 calls, response/source snapshots and category evidence were
verified. Focused validation passes 60 tests, Ruff and compilation; the global
generator and learner-system prompt are unchanged.

### October 11: matched attempt-informed revision pilot

**Authorized question, frozen before calls.** Does supplying simulated learner
work improve PF task design more than an ordinary, equally budgeted revision?
The user authorized the proposed six-case pilot. The
[protocol](../../experiments/configs/pf_attempt_revision_20261011.json) selects one
direct and one pipeline task per family, including adequate consistency designs
and two feasible fair-division cases. Speed includes the book-delivery timing
ambiguity and an unambiguous fixed-rate control. This is a selected development
sample, not a final or randomly sampled evaluation.

The three arms are unchanged original, task-review-only revision, and revision
with the same task review plus eight saved learner attempts. Both revisers get
the same comprehensive PF instruction, target and prior-learning specification,
model, maximum 6,000 tokens and one request. Only the latter gets learner work.
Ordinary-solver outputs, previous ratings and the earlier rejected automatic
change suggestions are excluded from feedback. Model mistakes are retained as
observations, not declared task faults; a shared instruction asks the reviser
to check task-text support. This is raw-attempt-informed rewriting with
researcher-chosen tasks/instructions, not fully autonomous or stage-specific
pipeline refinement.

Two excluded calibration tasks exercise both revision arms (four calls), then
six cases produce twelve revision calls. Fresh evaluation attempts all eighteen
versions with the same three learner/solver conditions, two models and two
independent repetitions: 216 calls plus eight arithmetic controls. Maximum total
is 240 requests, one round. All usable drafts and original replies remain;
unavailable revisions remain explicitly unavailable, never silently replaced
by original tasks.

**Predefined decision.** An exploratory advantage requires at least two more
supported, target-preserving, accessible, undisclosed tasks with consequential
choices in the attempt arm than ordinary revision, among six matched cases,
without a net loss of mathematical support or accessible starts. This conjunction
is not a validated PF score or statistical test. Report clarity-only improvement,
individual safety/disclosure regressions and coarse learner-only method evidence
separately. Assistant task review hides arm labels before observing fresh attempt
outcomes; fresh attempt coding does not use the poorly calibrated automatic
fine-method judge. No human learner behavior, learning or independent simulator
family validation is claimed.

**Execution so far.** All four excluded-case calibration revisions and all twelve
fresh revisions produced usable tasks, with no prompt changes between calibration
and development. All eight arithmetic execution controls for evaluation pass.
Fresh attempts on the eighteen versions are running; task-only assistant review
was completed with arm labels hidden before reading those outcomes. The global
generator remains unchanged: all rewrites are saved experimental variants.

**Fresh attempts completed.** All 216 evaluation requests finished without API
errors: 209 complete parseable replies and seven token cutoffs (six GPT-4.1-mini,
one GPT-4.1). Original and both revised versions received identical profiles,
two models and two fresh repetitions. The raw partial work remains retained.
Fresh evaluation usage is 133,548 input and 235,737 completion tokens; the eight
separate arithmetic controls add 1,596 and 561. Source hashes, revision request
parity and learner-input isolation were verified.

**Task-only review, before attempt coding.** Label-hidden assistant review rates
five original, six ordinary-revision and four attempt-informed tasks as meeting
the predefined design conjunction. All ordinary revisions have supported
mathematics; one informed revision's newly universal fair-division guarantee is
unknown, and another's task demand is judged narrower. These are exploratory
assistant judgments, not independently human-validated PF quality. The
[source verification](../../experiments/results/pf_attempt_revision_20261011/task_verification.json)
preserves the exact added demands and a counterexample to assuming every
additive valuation can be subdivided fairly. The given constant-rate numerical
instance remains feasible; the universal claim is the unresolved issue.

Both speed revisions clarify timing and also alter numerical data, so a later
clarity gain cannot be attributed to wording alone. The independent reader's
boundary for "invent a rule" on fixed-speed data is looser than earlier
assistant reviews; excluding both speed cases leaves the ordinary/informed
design-count difference unchanged (four versus two). This sensitivity does not
validate the underlying rubric. Coarse method and misreading coding of all 216
fresh attempts is in progress with version/model/profile labels hidden.

The two fresh revision arms each used six requests, but ordinary revision used
4,749 input and 8,823 completion tokens, versus 52,617 and 7,748 for informed
revision. Equal request/completion caps are not equal input costs. The 48 saved
learner attempts used as feedback were acquired in the preceding study, outside
this round's 240-request cap, so total-method cost must not hide acquisition.

**Fresh speed/consistency attempt findings.** Label-hidden coarse coding of all
72 speed replies finds supported whole-journey rates in every response. On the
book-delivery task, all eight learner-role attempts per version also test the
supplied unweighted-stage-speed proposal and recognise its limitation. No fresh
response misreads durations as cumulative timestamps, including the unchanged
original. Both revised tasks clarify durations, but this fresh cohort therefore
does not establish an incremental clarity benefit or superiority of
attempt-informed feedback. The earlier isolated misreading remains historical
evidence; it was not replicated in this cohort.

On the other speed task all arms again use the same whole-journey method; no
learner constructs a materially different journey or schedule. A task-review
positive for "invent a rule" wording is not confirmed as new reasoning variety
by these fresh attempts. Consistency replies still produce range comparisons,
concentration and departure measures across all arms. The attempted revisions
change method emphasis but do not, by themselves, show a general educational
gain. These are assistant-coded written outputs, not real learner diversity.
**Completed paired result: no promotion.** Label-hidden review of all eighteen
task versions gives the following separate design judgments. The task-only
reader finished before seeing fresh-attempt outcomes; all responses and
subsequent source checks remain preserved.

| Assistant task-review outcome, six cases per arm | Original | Ordinary revision | Attempt-informed revision |
|---|---:|---:|---:|
| Mathematics supported for the requested scope | 6 | 6 | 5 (1 unknown general guarantee) |
| Target preserved | 6 | 6 | 5 (1 judged narrowed) |
| Accessible start | 6 | 6 | 6 |
| Central method/conclusion not supplied | 6 | 6 | 6 |
| Consequential choice, under this reader's criterion | 5 | 6 | 6 |
| Required input clarity | 6 | 6 | 5 (1 unknown general-scope assumption) |
| All predefined design requirements | 5 | 6 | 4 |

The informed-minus-ordinary margin is -2, not the predefined +2, and mathematical
support is lower. The experiment therefore fails its exploratory continuation
rule. This does not prove a general disadvantage or statistical inferiority:
there is only one stochastic rewrite per arm and case, the sample is selected,
and task judgments are assistant readings, not validated human ratings.
The interpretation boundary on the speed tasks remains provisional; excluding
those two cases leaves four qualifying ordinary versus two informed tasks.

**What the attempts add to that conclusion.**

- **Speed:** all 48 learner-role replies across the six speed versions use the
  whole-journey rate. The 24 book-delivery learner replies also check the supplied
  shortcut; no attempt constructs a new journey or schedule. Both revision arms
  make durations explicit, but the fresh original replies already use durations
  correctly. The prior isolated timestamp misread does not recur. No extra
  clarity or approach-diversity benefit of attempt evidence is observed here.
- **Consistency:** all arms retain concentration, range and departure reasoning.
  On the manufacturing task, squared-departure methods occur in 7/8 informed,
  5/8 ordinary and 0/8 original learner-role replies. This is changed method
  emphasis, not proof of better PF; both revisions make the large-departure
  preference more concrete, and naming/priming a conceptual feature can alter
  model behavior. The original also supports multiple legitimate measures.
- **Fair division:** the informed three-artist task elicits divider/chooser
  extensions in 5/8 learner replies, but none of its eight learner replies has
  fully supported requested mathematics (five concrete defects, three unknown
  or incomplete guarantees). The task now requests a guarantee for *any*
  additive valuation without excluding indivisible value, although its supplied
  constant-rate instance is still feasible. On the four-person task, ordinary
  revision has one supported learner reply versus six informed and seven
  original, illustrating a different pattern: task-review quality and model
  execution correctness need not move together.

Across all six cases, learner-role written mathematics is supported in 43/48
original, 36/48 ordinary-revision and 37/48 informed-revision attempts. The
remaining original counts are three concrete defects/two unknown; ordinary ten
defects/two unknown; informed seven defects/four unknown. These are assistant
coding of observable calculations and constraints, not success rates of real
students, measures of productive failure, or proof that easier tasks are better.
Ordinary solver controls are recorded separately in the
[summary](../../experiments/results/pf_attempt_revision_20261011/summary.json).

**Educational finding and decision.** Simulated attempts can expose useful
questions, but supplying them does not automatically produce better PF tasks.
In this round a strong task-review-only revision is at least as useful by the
predefined design criteria, while raw attempt feedback sometimes expands the
task's demands or invites overreaction to model slips. This is a useful null/
negative result for the feedback mechanism. Stop this round; do not promote a
global generator change or tune the criteria after seeing it. A future
intervention could restrict feedback to verified task-level observations and
test that distinct package against the same strong baseline, but it is proposed,
not an automatic next run. No human attempts or learning effects are claimed.

**Clarified intent and where the loop broke (proposal, not run).** The user's
intended mechanism is a path-diversity loop: simulated learners attempt a task,
we check whether they take genuinely different mathematical paths, and that
diagnosis drives redesign. The pilot tested something narrower: raw attempts
handed to a general rewrite of finished task text. The evidence separates the
two halves of the loop. Detection worked on speed: learner-role attempts used
one whole-journey route in 48/48 diagnosis attempts and again in every pilot
version. Conversion failed: the informed reviser saw eight identical routes and
still produced a fixed-rate comparison. A suspected (not verified) cause is that
opening a speed task requires a structural change, such as Kapur's unknown
handover point, which a wording rewrite of a finished task cannot make. Careful
task reading had already flagged the same convergence, so simulation has not yet
shown information beyond review.

A faithful test would: (1) first check that the measure separates a known-diverse
task from a convergent one, using Kapur's handover task (nine observed student
methods) against the six generated speed tasks; (2) send a summarized diagnosis
(for example "all eight learners computed total distance over total time; no
decision was required") to design-level restructuring rather than raw attempts to
a text reviser, for at most two rounds; (3) count only mathematically distinct
paths, keeping validity, target, accessible start and no-giveaway checks, and
re-test with fresh learners plus a second simulator family so the task is not
tuned to one model; and (4) run the same loop driven by a task-reading diagnosis
as the control. Diversity among simulated learners must not be maximized through
ambiguity or errors.

**Designed-path coverage from saved data (no new requests).** The user's further
intent is a simulated class: do learners with some distribution of prior
knowledge actually reach the paths the design anticipated? Pipeline briefs save
those paths, so coverage can be read from the pilot's coarse assistant coding.
On the cycling-route speed task (brief `kapur_average_speed/002`), the design
anticipates averaging leg speeds, a whole-journey ratio and trial-and-error with
candidate speeds. Its eight learner-role attempts on the original took only the
whole-journey ratio (8/8); none averaged leg speeds or tried candidate speeds,
and both revisions gave the same result. On the production-line consistency task
(brief `loibl_variance/003`), the designed range-tie start was taken in 8/8 and
recognised as insufficient in 7/8; squared departures, part of the designed key
idea, appeared in 0/8. The designed "signed departures cancel" path could not be
checked because the codebook had no category for it. Coverage coding must derive
its categories from the designed paths before reading attempts.

The speed result has two explanations that simulation alone cannot separate:
the task may not elicit the naive path, or the simulated learner may be too
competent to take it, although averaging speeds is a common student response.
Both the full-record and omitted-prerequisite learners skipped it, so varying a
prompt-defined distribution does not obviously resolve this. Kapur's handover
task, where real students' failed and successful paths are documented, can show
whether a simulated class reproduces them. A class distribution itself (for
example Lu and Wang's 10 struggling, 30 average and 5 advanced learners) would be
an assumption here, so conclusions should be reported across several assumed
mixes rather than as one prediction.

The [three-way gallery](../../experiments/results/pf_attempt_revision_20261011/comparison.html)
shows every original and revised exercise, task judgments and fresh learner-only
method counts. The
[task-only ratings](../../experiments/results/pf_attempt_revision_20261011/task_ratings.json),
three anonymous attempt-coding artifacts and
[exact speed/consistency checks](../../experiments/results/pf_attempt_revision_20261011/independent_math.json)
preserve the evidence. All 16 revision and 224 student requests are counted:
240 calls, including separate calibration. Fresh revisions cost 13,572 recorded
tokens ordinary versus 60,365 informed, with an approximately eleven-fold input
token difference; that excludes historical feedback acquisition and is not
a monetary estimate. Validation passes 68 focused tests, Ruff and compilation;
request pairing, source snapshots, input isolation and all 216 coded outputs
are verified. The global PF generator and learner prompts remain unchanged.

### October 11: controlled learning-record study (frozen before requests)

**Question and scope.** The user asked to run structured research on following
the learning record. The
[new protocol](../../experiments/configs/pf_learning_record_20261011.json)
keeps four saved PF tasks, both GPT-4.1 models and all learner instructions fixed.
Compare ordinary solver, original prerequisites, one prerequisite omitted, and
one additional learned method. Consistency removes mean or adds variance/standard
deviation; fair division removes Divider-Chooser or adds Lone Divider/Last
Diminisher. Additions name learned resources, without giving formulas, algorithm
steps, task answers or instructions to use that method. Nevertheless, names can
prime the task: the experiment tests prompt responsiveness, not new learning.

There are three independent repetitions per task/model/condition: 96 fresh
requests plus eight separate arithmetic controls, maximum 104 calls and 249,600
completion tokens. Existing 0.7 temperature, 2,400-token caps, zero transport
retries and four bounded workers remain. Historical attempts are not pooled.
No learner-system or PF-generator prompt is tuned.

The hypothesis is that removing an actually used resource reduces application
and adding a learned resource increases application. Code actual mathematical
operations separately from mere terminology, presented recall, visible
construction, explicit self-described gaps, and record-bound stopping. Missing
or insufficient work remains unknown. No arbitrary learner-fidelity pass
threshold is claimed. Addition/deletion tests that change output are not proof
of human realism.

**Correction to prior screening interpretation.** The record says procedures
were not directly instructed; it explicitly permits construction from familiar
operations. Calculating an omitted mean is not automatically a knowledge-boundary
violation. Recognising the name of an unlearned method also need not be unrealistic
for a real learner. The prior "record leakage" and "artificial restraint" flags
are hypotheses to inspect, not validated faults; only explicit refusal due to
the learning record counts as record-bound stopping. This experiment uses coarse,
source-quoted assistant coding, not the poorly calibrated automated fine-method
reviewer.

Source and input snapshots, task-text-only isolation and additive resource
support were checked before calls; 11 focused probe tests and Ruff pass.
**Execution completed, before unmasking behavioral coding.** All eight arithmetic
controls were correct and complete. The 96 fresh requests finished without API
errors: 94 complete parseable replies and two token cutoffs, one per model.
Raw partial work and every request remain saved. Fresh usage records 57,396
input and 121,595 completion tokens; calibration adds 1,596 and 596. Summed
request duration is 901.582 seconds fresh and 11.956 seconds calibration, not
concurrent wall time or a monetary cost estimate.

The [anonymous packet](../../experiments/results/pf_learning_record_20261011/panel/review_packet.json)
omits model, condition, learning record and generator labels. Coarse source-quoted
coding was completed before opening the key; task family remained visible.
The [coding parser](../../src/evaluation/pf_record_adherence.py) checks exact
evidence and applied-versus-mentioned separation, not truth about cognition.
Reports will use all requests in the denominator and preserve unknowns for
insufficient partial work. No responses were replaced or prompts tuned.

**Controlled results.** Each cell below counts 12 fresh attempts: two tasks in
the family, two models, three independent repetitions. A separate assistant
reader coded all 96 outputs with condition/model labels hidden; every positive
flag has an exact quotation verified against the saved response. This verifies
traceability, not human truth or cognitive-state fidelity.

| Actual mathematical action | Prerequisite omitted | Usual prerequisites | Additional method learned | Ordinary solver |
|---|---:|---:|---:|---:|
| Consistency: computes an arithmetic average, including averaging departures | 1/12 | 8/12 | 12/12 | 11/12 |
| Consistency: calculates variance/standard deviation, named or unnamed | 0/12 | 0/12 | 12/12 | 12/12 |
| Fair division: executes a two-person Divider-Chooser subprocedure | 0/12 | 0/12 | 0/12 | 0/12 |
| Fair division: actually performs a Lone Divider/Last Diminisher-style procedure, possibly imperfectly | 0/12 | 2/12 | 7/12 (1 unknown) | 0/12 |
| Fair division: mentions an advanced method without performing it | 0/12 | 0/12 | 4/12 (1 unknown) | 1/12 |

**The supported finding is selective prompt control.** On consistency, adding
the learned method changes actual calculation from 0/12 to 12/12 in both
task/model combinations; this is not a keyword-only effect. The additional
record includes the method name but no formula or demand to use it, so direct
method priming remains an alternative explanation, not evidence of learning.
Omitting arithmetic mean reduces actual averaging from 8/12 to 1/12. The residual
case uses a median as its centre and then averages absolute departures. That is
permitted construction under the unchanged prompt, not automatically a violation
of a hard knowledge boundary.

**Fair division is a weaker result.** The usual record's two-person
Divider-Chooser is mentioned in 9/12 replies, but no reply actually performs
that two-person protocol. Removing its name therefore suppresses mentions, not
an observed executable skill; the removal test is uninformative for application.
Two usual-record replies construct an unnamed multi-person divider-and-chooser
procedure, which is permitted by familiar arithmetic. Adding the advanced methods
produces seven applied and four mention-only replies, with one truncated case
unknown after the second-reader check. Of the seven applied
replies, three have supported written mathematics and four contain concrete
allocation/arithmetic defects. Mentioning or attempting a learned method does
not establish mastery. The remaining added-arm replies also contain some defects,
so overall task performance must not be replaced by method-use counts.

**Counterfinding on forced restraint.** No attempt in this fresh study was coded
as explicitly stopping solely because the learning record forbade exploration.
Nine attempts describe a knowledge gap, with one additional partial case unknown.
Self-described gaps alone are not demonstrated artificial restraint, and the
earlier keyword-screen interpretation should not be generalized to every cohort.
Visible construction is an assistant judgment from written explanations; actual
invention versus recall cannot be inferred confidently from fluent prose.

**Research decision.** The learning record can shift which mathematical methods
are applied, strongly for these consistency tasks and incompletely for fair
division. It is not a switch that removes underlying model knowledge, and this
does not establish a realistic learner or a generally good PF feedback
instrument. Stop this bounded round without prompt tuning. A future
same-length irrelevant-resource control and comparison to real prior work would
separate topic priming, persona effects and learner fidelity. No such control,
human comparison, PF revision or learning study was conducted here.

The [results page](../../experiments/results/pf_learning_record_20261011/learning_record.html),
[source-quoted coding](../../experiments/results/pf_learning_record_20261011/record_coding.json)
and [per-task/model summary](../../experiments/results/pf_learning_record_20261011/summary.json)
preserve all outcomes. A balanced second-reader spot check, one first-repeat
output per task/model/condition cell (32 replies), agrees on prerequisite
application in 32/32, advanced-method application in 31/32, and explicit
record-bound stopping in 32/32. The sole disagreement is no-versus-unknown on a
truncated allocation response; the conservative report uses unknown and leaves
both original ratings unchanged. This is assistant agreement on a subset, not
independent human validation. The
[agreement record](../../experiments/results/pf_learning_record_20261011/coding_agreement.json)
and [adjudication](../../experiments/results/pf_learning_record_20261011/coding_adjudication.json)
preserve that uncertainty.

Full learner/software/source provenance was checked independently of behavioral
judgments: all 104 unique request pairs, 96 coded replies and their evidence,
three repeats in each of 32 task/model/condition cells, identical within-task
text and learner instructions, and execution source snapshots. Validation passes
67 targeted tests plus Ruff and compilation. The results chart and 96 linked
attempt panels were verified in the browser. No new learning-record tuning round
or PF refinement was started.

### Proposed simulator validation: is the LLM student fit for PF diagnosis? (not started)

**Purpose-specific definition.** The simulator is "good" only for a stated use:
diagnosing whether a PF task leaves room for familiar-method limits and different
mathematical approaches, and supplying evidence for revision. Fluent, student-like
prose is not the criterion. Scarlatos et al. separate correctness, error, dialogue
and knowledge-change fidelity; the position paper
[Towards Valid Student Simulation with LLMs](https://arxiv.org/abs/2601.05473)
names the competence paradox (a capable model asked to show partial knowledge)
and asks for an explicit statement of what the simulated learner can access.
Our learning record is that statement; each check below tests one claim about it.

| Validity question | Check | Baseline or control | Current evidence |
|---|---|---|---|
| Does it respect its knowledge record? | Actual application of omitted/present/added resources, not keywords | Ordinary solver and added-method control | New controlled study: averaging 8/12 usual versus 1/12 omitted; variance/SD 0/12 usual versus 12/12 explicitly taught. Fair-division application is less consistent. Prompt control is not learner fidelity. |
| Does the record's content matter, not just its presence? | Replace it with a same-length irrelevant record, and a grade-only persona | Placebo record; grade-only persona | Not tested. |
| Is it stable enough to read? | Repeat agreement on the coarse decision (familiar method only, constructs a new measure, uses an untaught formula) | Agreement expected by chance | Exact method sets matched in 11/24 and 13/24 repeat pairs (two assistant coders). Exact sets are too strict; coarse decision agreement not yet computed. |
| Does it react to task design? | Matched task pairs with a known design difference | Same simulator on both versions; ordinary solver | Not tested. Decisive for feedback use. |
| Does it resemble real learners? | Source-normalized Kapur bicycle task, coded against nine observed group categories | Ordinary solver; prediction-only prompt | Reference check completed: learners enact algebra and trials but no ratio/LCM partition or diagram; normalized individual calls do not validate real group distributions. |
| Does its feedback improve tasks? | Original versus generic revision versus attempt-informed revision | Generic revision with the same budget | Not tested; the planned revision study. |

**Task-sensitivity pairs (illustrative designs, not results).** Each pair changes
one known property of one frozen task. If learner attempts do not move in the
predicted direction, attempt-based feedback cannot be trusted for that property.

- Familiar summaries tie versus differ: with equal ranges, more attempts should
  recognise the range limit than when ranges already separate the data.
- Method disclosed versus open: naming a consistency measure should make attempts
  converge on it.
- Ambiguous versus labelled timings: the book-delivery timestamp reading should
  drop once leg durations are labelled.

This mirrors the repository's earlier known-good/known-bad controls for MCQ
diversity, applied to open PF tasks. The ordinary solver may not react the same
way; that difference is informative, not a failure.

**Human anchor available now.** Kapur and Bielaczyc coded nine
representation/solution categories from Grade 7 groups on the bicycle-handover
task ([evidence note](KAPUR_BIELACZYC_2012_EVIDENCE.md)). Report category coverage
for learner roles versus the ordinary solver versus a prediction-only prompt.
Limits: the categories are group-level without frequencies; the repository task
text is normalized, not verbatim; the published task may be memorized; one task
from one country cannot validate the simulator in general. Loibl and Kerrigan
student-method lists are curated interpretations, not verified observations, so
they are not anchors. Puech et al.'s field study coded methods during tutoring,
not unaided attempts.

**Instrument prerequisite.** Every check depends on coding methods reliably.
Assistant readers agreed on 42/48 exact method sets; the automated reviewer on
16/48. Use a small fixed codebook per task family (Kapur's nine categories for
speed), agree it on existing attempts first, and report coarse decisions where
fine labels disagree.

**First record-adherence screen (saved attempts, no new requests).** A
[keyword screen](../../scripts/screen_pf_learner_record.py) of the 216 diagnosis
attempts flags terms for reading; it is not a coding verdict. Results are in the
[screen artifact](../../experiments/results/pf_student_diagnosis_20261011/record_adherence_screen.json).

- Removing Divider-Chooser from the fair-division record removed its mention:
  20/24 attempts with the full record, 0/24 with it omitted, 0/24 for the solver.
  Named advanced allocation procedures appear in 10/24 solver and 0/48 learner
  attempts.
- On consistency, untaught terms (variance, standard deviation) occur in 24/24
  solver and 6/48 learner attempts, all six from GPT-4.1-mini. All six learner
  hits were read: none computes squared departures or a root; each mentions the
  procedure as something not yet learned, sometimes
  to justify building an absolute-deviation measure instead. Removing the mean
  roughly halved crude mean-calculation hits (16/24 to 8/24), but did not remove
  them, and one task's own text mentions the average.
- Removing ratio and proportion is uninformative for speed: neither appears even
  with the full record (0/24), so there was nothing to suppress.

Two failure modes need their own codes. **Record leakage**: the learner names
the expert procedure it is not supposed to know ("variance was not taught").
**Artificial restraint**: it stops because the record seems to forbid more,
for example concluding two batches are equally consistent "with my current
knowledge". Record statements appear in 9/48 learner consistency attempts and
0/24 solver attempts. Real learners neither know which formula they lack nor
treat the record as a rule, so both reduce realism even when behaviour looks
compliant. A gap test is informative only for a resource that the full-record
learner actually uses.

**Recommended order.** Coarse repeat agreement from saved attempts (no requests);
the Kapur anchor and the task-sensitivity pairs as one bounded round with frozen
settings; then the revision study. Placebo and grade-only controls can share
that round. Real learner attempts remain the only route to claims about students.

### Attempt-based feedback research: baseline diagnosis started, revision not started

**October 11 authorization and frozen scope.** The user authorized starting the
recommended first two steps: calibrate the attempt checklist and diagnose all 18
saved comparison tasks. The
[baseline protocol](../../experiments/configs/pf_student_diagnosis_20261011.json)
keeps simulator prompts, both models, prerequisite-only profiles, two independent
repetitions and 2,400-token caps unchanged. Speed adds an omitted ratio/proportion
prerequisite, not a desired wrong rule. A new directory preserves all 216 fresh
attempts plus eight arithmetic execution controls. A frozen
[five-finding checklist](../../src/evaluation/prompts/pf_attempt_feedback.yaml)
reviews the previous four panels (48 saved attempts) as calibration, then 18
new panels. At most 224 student requests and 22 panel reviews, 246 total requests,
are authorized in this single round; no generation revision or further tuning.

The checklist records visible starts, a familiar method reaching a recognised
limit, distinct mathematical approaches, explicitly supplied task methods, and
missing/ambiguous information. Findings require exact task/attempt quotations;
unsupported or malformed reviews remain unknown. The
[parser](../../src/evaluation/pf_attempt_feedback.py) checks evidence anchors,
not the judge's educational truth. Arithmetic slips or uncertain attribution
cannot be routed into proposed task changes. Feedback is evidence for a future
revision experiment, not automatically applied. A fresh second reader codes the
earlier 48 anonymous outputs without seeing the original ratings or keys; compare
agreement rather than declaring either reader ground truth.

**Interpretation correction.** Earlier chat called the printer task "behaving like
PF" and suggested identical speed methods would confirm no choice. The evidence
supports only a PF-relevant pattern in model output: familiar range comparison
ties and some replies seek another feature. Actual productive failure or learning
has not been established. Similarly, convergence may reflect a strong simulator
choosing the same valid route, not a rigid task. Task-text evidence is required
for a design concern, with causal attribution explicitly provisional.

**Checklist calibration findings.** The second label-hidden assistant reader
agrees with the original on mathematical status in 45/48 outputs, exact applied
method sets in 42/48, and named advanced procedures in 46/48. Neither reader is
ground truth. The separate task-panel model reviewer agrees with the original
on mathematics in 37/48, exact method sets in 16/48 and named advanced procedures
in 47/48; versus the second reader those counts are 39/48, 17/48 and 47/48.
The fine-grained automated labels are therefore not established as a dependable
diversity instrument. Keep the disagreements and broad model diagnoses for
inspection, not automatic task selection or a validated diversity score.

All four model calibration responses contain usable attempt coding but at least
one unmatched/source-misidentified quotation. The initial strict parser labelled
the whole response invalid. A separately recorded instrument correction retains
usable coding, makes each unsupported finding unknown, and excludes proposed
feedback with unverified evidence. The same four saved replies were reprocessed
without new requests, prompt tuning or replacing them. Exact quote checks establish
source fidelity, not causal/educational correctness. The
[agreement artifact](../../experiments/results/pf_student_diagnosis_20261011/checklist_calibration/agreement.json)
records every disagreement.

Two zero-request preflight failures were retained: the review trace directory was
not created before opening its log, and a relative configuration path failed
source snapshotting. Both were repaired and tested before the full run. The eight
new arithmetic execution controls pass; the 216-request diagnosis now uses four
bounded workers, with unchanged prompts/settings. No task revision occurs.
**Completed baseline attempts.** All 216 fresh student requests finished without
API errors: 211 complete parseable responses and five token cutoffs, with raw
partial work retained. GPT-4.1-mini has 105/108 complete responses, GPT-4.1
106/108. The eight execution controls are separate and all correct. Fresh usage
is 119,292 input and 205,254 completion tokens; calibration adds 1,596 and 548.
Summed request duration is 1,577.301 seconds fresh, not concurrent wall time.
No attempt was replaced or conditioned on another attempted solution.
The [attempt gallery](../../experiments/results/pf_student_diagnosis_20261011/panel/attempts.html)
and saved prompt/response records retain the whole study.

**Completed panel review and feedback check.** All 18 panels produced usable
attempt coding and checklist reviews. Twenty-seven individual evidence fields
have invalid quotations or source references; they remain explicitly unverified,
and affected findings are unknown rather than positive. This does not erase task
text or attempt records. The retained source-anchored feedback includes four
simulator-slip observations and five task-change candidates. Those are proposed
model feedback, not validated causes or automatic changes.

A subsequent parent-assistant source check of all five task candidates records:

| Candidate | Checked interpretation | Next implication |
|---|---|---|
| Book-delivery timing | One attempt subtracts leg times as cumulative timestamps; others sum durations. Task prose and leg labels allow the misreading. | A supported wording candidate: label durations explicitly, without providing the rate formula. |
| Robot final waiting | The table lists a final wait and explicitly includes all waiting; every attempt counts it. "Between sections" could be clearer, but confusion is not demonstrated. | Optional clarification, not established task failure. |
| Two walkers' stage times | The reviewer falsely assumes continuous timing means cumulative table timestamps and calls decreasing entries a contradiction. Stage durations of 6 and 4 minutes can be valid. | Reject the claimed numerical contradiction and its all-attempt invalid verdict; do not redesign valid numbers. |
| Studio collective decisions | The reviewer asks to supply a joint decision mechanism that learners are explicitly asked to devise. | Reject this as a required fix; it could remove the central unknown. Missing within-interval valuation rules remain a separate earlier finding. |
| Pre-framed speed comparison | The task supplies a whole-journey route beside another candidate route. This may constrain discovery, but can also be deliberate support. | A design tradeoff for a controlled comparison, not an automatic "no hints" rewrite. |

The [feedback check](../../experiments/results/pf_student_diagnosis_20261011/feedback_adjudication.json)
is assistant adjudication, not independent human validation. Original reviews,
including the incorrect contradiction claim, are preserved alongside the
subsequent correction. Exact evidence anchoring is necessary but insufficient:
a model can quote the right words and interpret them incorrectly.

**What we learned about attempts.** Consistency panels commonly contain familiar
range comparisons followed by concentration or departure measures; ordinary
solver controls also supply advanced methods. That mixed-panel variety is not
the same as diversity among the learner-only roles. Speed learner replies are
coded as using a whole-journey rate in all 48 learner-role attempts, sometimes
also evaluating supplied shortcuts. This is coarse model coding under a
fine-label instrument with poor calibration agreement; convergence does not
prove task rigidity or learner realism. Fair division produces different
schedules and local repairs, but some are variants of the same claim-based
procedure. Do not equate schedule variety, arbitrary errors or token cutoffs with
productive failure.

**Decision and boundary.** The first two agreed steps are complete as an
exploratory diagnosis: the checklist's fine method labels remain unreliable,
the full frozen panel is recorded, and a small set of checked feedback candidates
exists. No task or generator was changed. The next intervention, if authorized,
should test original versus generic revision versus attempt-informed revision
on a bounded subset, using fresh attempts and task-quality review. The supported
timing clarification offers a concrete starting point, but wording improvement
alone would not demonstrate more distinct approaches or learning. Do not restart
simulator tuning to manufacture mistakes.

The complete
[diagnosis gallery](../../experiments/results/pf_student_diagnosis_20261011/diagnosis.html)
and [summary](../../experiments/results/pf_student_diagnosis_20261011/summary.json)
make original model findings, unverified evidence and subsequent checks visible.
The [proposed-feedback artifact](../../experiments/results/pf_student_diagnosis_20261011/proposed_feedback.json)
is not applied to generation. Actual total requests are 246: 216 fresh attempts,
eight arithmetic controls, four saved-attempt review panels and 18 new review
panels. Review usage is 302,480 input and 73,331 completion tokens. These counts
include retained failures and calibration, and are not a monetary estimate.
Validation passes 69 targeted tests plus Ruff and script compilation. All 224
student request pairs, 22 review request pairs, source snapshots, coverage and
budgets were verified. The subsequent revision study remains proposed below.

**Question.** Does feedback grounded in LLM-student attempts improve PF tasks more
than an equally budgeted revision without attempt evidence? A secondary finding is
whether attempts reveal task problems that task-text review missed.

```text
Frozen task -> learner panel attempts -> fixed attempt checklist
  -> task problem? -> evidence-quoted feedback to the stage that caused it
  -> model slip?   -> record only, never fed back
Revised task -> fresh panel + different simulator + blind review
```

1. **Attempt checklist, calibrated first.** Read each set of attempts for:
   accessible start; a familiar method meeting its limit; distinct mathematical
   approaches; convergence on a method the task itself supplied; misreading or
   missing information. Separate simulator arithmetic slips from task-caused
   problems. Check agreement on the existing 48 coded attempts with a second
   coder before using the checklist as feedback.
2. **Baseline diagnosis.** Run the frozen panel, including the ordinary solver,
   on all 18 frozen comparison tasks. Compare attempt evidence with the earlier
   task-text judgments, for example whether speed tasks really leave no choice.
3. **Feedback and routing.** Quote what learners did, never the intended method
   or answer. Route design problems to design selection, missing limitation or
   tie data to the data stage, and ambiguity to writing, using the existing
   bounded-revision findings path. The suspected selector feedback/design pairing
   issue must be checked before feeding attempt evidence there.
4. **Matched arms.** Original; revision with generic improvement feedback and the
   same call budget; revision with attempt feedback. The generic arm separates
   "evidence helped" from "another revision pass helped".
5. **Independent re-evaluation.** Fresh attempts from the same panel and from a
   different simulator family or framing, plus label-hidden mathematics/target/
   giveaway/choice review. Predefine the gain; accessible starts and mathematical
   validity must not regress. Do not maximize failure.
6. **Stop and record.** At most two rounds. A null result, such as attempt feedback
   being no better than generic revision, is a finding.
7. **Human anchor.** Blind expert ratings of original versus revised tasks and a
   small real first-attempt collection on a few tasks, compared with simulated
   attempts. Only this step supports claims about students.

Risk: revising toward one simulator's quirks would optimize the simulator, not
the exercise. The held-out simulator, generic-revision control and human anchor
address this. Budget, success threshold and task subset must be frozen before
any requests.

**Input isolation and readout decisions.** Reuse the existing
[student-text and learner-context allowlists](../../src/evaluation/pf_rubric.py):
the simulator should see the exercise and independent prior-knowledge facts,
not its generation method, target formula, selected design, expected approaches,
numerical check evidence or ratings. An unrestricted solver control can reveal
whether a student-role instruction changes anything. Repetitions of each
task/profile must be independent rather than conversations that teach the
answer. Written calculations and explanations are the observable data.

Code the mathematical action rather than stylistic variety: averaging, range,
absolute departures, squared departures, constructing/testing a new measure;
whole-piece search, equal subdivision or a genuinely different allocation
procedure. Do not prompt these categories into the simulated attempt. Record
incomplete work and unknown classifications. A learner inventing a squared
departure measure from familiar multiplication is not automatically a profile
violation; naming an untaught formula and constructing it are different
observations. Do not maximize failure, require prescribed wrong answers, or
turn correct attempts into simulator errors by definition.

## October 11: moving from prompt tuning to method comparison

**Decision, before generation.** The user requested a higher-level research
direction rather than another tuning loop and authorized starting the comparison.
Freeze the current generator and compare strong direct generation with the
pipeline on the three existing expert directions: average speed, consistency
and fair division. The question is whether students are asked to make meaningful
mathematical choices or invent something, not whether the pipeline passes more
internal checks. Human-expert records are design anchors only; some are normalized
or reconstructed, and none are supplied as generation examples.

The [frozen protocol](../../experiments/configs/pf_method_comparison_draft_first_20261011.json)
specifies two separate calibration cases, then three repeats per direction and
method: nine fresh attempts per method. No prompt changes or follow-up tuning
are authorized in this round. The existing matched runner now preserves complete
source snapshots as well as hashes and displays unresolved internal findings.
The fixed-D1 pipeline has at most 17 requests per attempt, including schema
retries and bounded revisions; the whole round is bounded at 198 requests.

Report mathematical support, target preservation, accessible starts, disclosures
and consequential choices separately, with failures in the denominator.
Assistant review with method labels hidden is not independent human blinding.
Common final-text mathematical checks apply to both methods. This is an
exploratory comparison on inspected directions with unequal compute, not a
causal test of decomposition, a final benchmark or evidence of student learning.
Equal or lower counts of supported, target-preserving, accessible, undisclosed
tasks with consequential choices means no demonstrated pipeline advantage.
**Execution calibration.** The two calibration directions produced two direct
and two pipeline drafts in 21 requests, with no API errors or unmatched request
records. Calibration exposed a reporting defect: the paper-benchmark's strict
direct-response schema rejected pipeline metadata and counted produced drafts as
absent. The comparison now checks task-text presence for delivery and keeps the
direct-generation schema check unchanged. A flagged-draft counting/rendering
regression passes; all seven focused comparison tests and targeted Ruff pass.
This is an instrument correction, not a generation intervention. Source snapshots
identify the earlier calibration runner; generation prompts are unchanged.
**Completed generation.** The
[saved comparison](../../experiments/results/pf_method_comparison_draft_first_20261011/summary.json)
produced all nine direct and all nine pipeline drafts, with zero API errors.
Fresh generation used 9 direct requests and 78 pipeline requests. Including the
separate calibration, the campaign used 108 of its maximum 198 requests.
No failed attempts were replaced and no generation prompts were changed.

**Task-text findings.** All 18 exercises were reviewed in three anonymous
packets before opening their method keys. Family and learner knowledge remained
visible, and style could suggest the method: this is label hiding for assistant
review, not independent human blinding. Numerical inputs were transcribed from
the final text and checked with exact arithmetic and finite allocation
enumeration, applying the same checks to both methods.

| Separate outcome, out of nine attempts per method | Direct | Pipeline |
|---|---:|---:|
| Draft produced | 9 | 9 |
| Mathematical support established for the requested task | 8 | 8 |
| Mathematical interpretation or resolution still unknown | 1 | 1 |
| Target preserved | 8 | 9 |
| Accessible starting point | 9 | 9 |
| Explicit method/conclusion disclosure | 1 | 0 |
| Consequential mathematical choice or invention opportunity | 6 | 6 |
| Model requests (lower means fewer requests, not better PF) | 9 | 78 |

The predefined conjunction of supported mathematics, preserved target, accessible
start, no disclosure and a consequential choice counts five tasks per method.
This is not a validated PF score. One speed disclosure judgment is borderline
partial guidance; changing it would not change that count because all speed tasks
lack a consequential construction choice. Fewer disclosures alone is not an
approach-diversity result. Direct usage metadata records 19,890 input and 19,315
completion tokens; pipeline usage metadata is unavailable in this runner, so
neither its tokens nor a monetary cost is inferred. Summed request duration is
143.629 seconds for direct and 1,050.405 seconds for pipeline, not wall time for a
parallel deployment.

**Educational interpretation by family.**

- **Average speed:** all six tasks compare fixed journeys. Exact calculations
  confirm six ranking reversals between an unweighted average of moving-stage
  speeds and whole-journey speed, but no task asks students to choose an unknown
  handover point or design a journey. This supports useful conceptual comparisons,
  not reproduction of the expert task's construction opportunity or observed
  student methods.
- **Consistency:** all six tasks ask learners to invent a numerical measure.
  Every pair or group has equal means and ranges, verified independently. The
  [third pipeline task](../../experiments/results/pf_method_comparison_draft_first_20261011/fresh/loibl_variance/003/pipeline/result.json)
  is especially informative: mean absolute deviations of 2.5 and 2.667 favour
  Line A, whereas variances of 9.417 and 8 favour Line B. Its stated preference
  against large departures gives learners a reason to compare definitions.
  That is a verified opportunity for contrasting reasoning, not observed
  student diversity or a unique requirement to invent variance.
- **Fair division:** all six invite allocation or procedure choices, but their
  learning demands differ. The
  [first pipeline task](../../experiments/results/pf_method_comparison_draft_first_20261011/fresh/kerrigan_fair_division/001/pipeline/result.json)
  has no fair intact-block allocation among 27 possibilities, while specified
  per-hour values make fractional allocation feasible. Giving each artist one
  third of each block verifies a solution; this familiar successful method must
  not be banned just to force failure. Other tasks permit successful whole-piece
  bundles, so competing preferences do not necessarily create an unavoidable
  standoff. The
  [second direct task](../../experiments/results/pf_method_comparison_draft_first_20261011/fresh/kerrigan_fair_division/002/direct/result.json)
  has no fair indivisible assignment among 1,024 possibilities and leaves
  alternative arrangements undefined. It can support an impossibility discussion,
  but a fairness-preserving resolution remains unknown. The
  [third pipeline task](../../experiments/results/pf_method_comparison_draft_first_20261011/fresh/kerrigan_fair_division/003/pipeline/result.json)
  has valid whole-interval allocations, but does not define values within
  arbitrarily cut intervals. Additivity alone is insufficient; the fractional
  interpretation remains unknown, not silently invalid or validated.

**Decision and next implication.** No general pipeline advantage is established
in this small, inspected-topic, unequal-compute comparison. Decomposition produces
some interesting designs but uses substantially more requests, and the kind of
mathematical work differs more clearly by task family than by generation method.
Stop this generation round rather than tune another prompt. The next educational
question is whether selected consistency and fair-division tasks actually elicit
different reasoning attempts, retaining both methods as comparison conditions.
Simulated attempts would be diagnostic hypotheses; independent expert ratings
and real student attempts have not been collected. No learning or state-of-the-art
claim follows.

The [gallery](../../experiments/results/pf_method_comparison_draft_first_20261011/fresh/side_by_side.html)
shows expert design anchors, task text, unresolved internal findings and
per-task reviews. The
[assessment](../../experiments/results/pf_method_comparison_draft_first_20261011/fresh/assessment.json)
and [exact checks](../../experiments/results/pf_method_comparison_draft_first_20261011/fresh/independent_math.json)
retain all outcomes. The
[fractional feasibility checks](../../experiments/results/pf_method_comparison_draft_first_20261011/fresh/fractional_checks.json)
verify the stated equal-subdivision examples without assuming missing valuation
rules for the unresolved task. All 18 reviews/checks, 120 saved source snapshots,
and matched request starts/finishes were verified; the resolved model was
`gpt-5.6-luna` throughout. The focused software validation passes 187 tests across the
comparison and generation route, with targeted Ruff passing. Reporting-only
changes after generation do not alter the source snapshots used for the runs.

## 1. Research question

> **Can an LLM pipeline generate Productive Failure exercises that actually
> elicit multiple meaningful student approaches, rather than producing a
> polished story wrapped around a single procedure?**

A PF exercise is not just a difficult word problem. Students should have
familiar resources with which to begin and useful limits or contrasts to explore.
Not every familiar approach must fail. The task should make different approaches
visible and leave material for comparison during consolidation: subsequent
teaching that connects student attempts to the target concept.

The central design problem is therefore:

```text
What will students try?
How should the data expose the limits of those approaches?
How can we check the task before presenting it as PF?
```

## 2. What the first generator taught us

We first asked an LLM to write PF exercises directly. The generated pool was
often fluent, but the PF mechanism was unreliable:

- an intended trap disappeared because the numbers made the shortcut valid;
- a purported wrong method was actually mathematically correct;
- the narrative announced the error instead of eliciting it;
- the numbers or story were inconsistent; and
- exercises converged on one calculation despite being described as open-ended.

The historical, blind AI PF-rubric review of the 21-task pool reflected this
structural problem: Multiple
Representations and Solutions remained at 1.00/3.00 in every generation
condition. The conclusion was not that the prose needed more prompting. The
generator appeared to be doing the jobs in the wrong order. That diagnosis
motivated decomposition; it was not a causal test of generation order:

```text
old: write a story -> hope the numbers create a trap -> list mistakes
new: anticipate resources -> design the data -> verify the data -> write the task
```

The direct-generation results and examples are retained in the historical
[PF_GENERATION_FROM_PATHWAYS.md](history/PF_GENERATION_FROM_PATHWAYS.md).

## 3. The four design jobs

The expert tasks from Kapur, Loibl, Kerrigan, and Puech make four jobs
explicit:

| Job | Name | Question | Output |
|---|---|---|---|
| D1 | Anticipate | What resources will students bring? | prior-resource candidates and first moves |
| D2 | Calibrate | Which data expose the limits of those resources? | tested parameters or number sets |
| D3 | Open up | Does the prompt allow exploration? | invention or ill-structured task |
| D4 | Verify | Does the intended mechanism actually hold? | mathematical checks and optional behavioral probes |

These jobs are related but not interchangeable. Different answers alone do not
establish meaningful approach diversity. A declared limitation must be real,
while partial and successful approaches can also support conceptual comparison.
The task must remain solvable or inventible rather than simply impossible.

These are conceptual jobs, not four mandatory sequential model calls. In the
current implementation, D2a selects a design brief, D2b generates and checks
its data, and D3 writes the task. D4 describes verification work, including
checks already performed inside D2b and optional later behavioral probes.

## 4. D1 has two candidate sources

We tested two ways to obtain the prior-method space needed by D1.

```text
                       D1: source of prior methods
                                  |
             +--------------------+--------------------+
             |                                         |
 Branch A: LLM error generation             Branch B: literature grounding
 MCQ distractors and Eedi labels            curricula and expert PF papers
             |                                         |
 answer-level wrong pathways                taught resources with provenance
```

### Branch A: MCQ error generation

The MCQ study was a PF-oriented diagnostic branch, not the thesis's final
method for defining prior knowledge. It asked whether an LLM could generate a
wrong answer and an executable pathway that resembled real student errors in
Eedi.

The historical answer-matching result was useful mainly as a boundary condition:

- best PM (match to documented Eedi errors) was about 22%;
- the tested prompting conditions did not remove the fidelity/diversity trade-off;
- some outputs were fluent but not anchored to a real error; and
- structured fields such as `faulty_step` and `reasoning_steps` made a
  candidate inspectable, but did not make it reliable ground truth.

This branch produces **documented-error hypotheses**, not a complete list of
prior resources. Eedi answer choices do not reliably represent
correct-but-insufficient resources, qualitative insights, diagrams, or
algebraic attempts. Therefore MCQ output is not pasted into the PF writer and
is not the primary D1 source.

Current MCQ evaluation separates answer incorrectness, a compact model-estimated
plausibility score, and optional coherent-path checks. Eedi matching is secondary
reference alignment, not student plausibility or PF effectiveness. See the
[generation](../mcq/MCQ_GENERATION_OVERVIEW.md) and
[evaluation](../mcq/MCQ_EVALUATION_OVERVIEW.md) notes for the current contract.

### Branch B: literature grounding

The current D1 source is the grounded recommender in
[run_prior_recommendations.py](../../scripts/run_prior_recommendations.py).
It uses:

- official curriculum documents;
- open textbook chapters where a general curriculum source is needed; and
- optional teacher-supplied recently taught skills.

Curated expert-resource lists are an **evaluation holdout**. They are not
pasted into the grounded prompt and are not preserved as generation output.
The grounding corpus and its coverage limits are documented in
[data/curriculum_grounding/README.md](../../data/curriculum_grounding/README.md).

The grounded/ungrounded comparison is informative but not an apples-to-apples
accuracy study: Branch A was evaluated against answer-level Eedi matching,
whereas Branch B is compared after the fact to curated expert-resource lists.
Older grounded runs that recovered the expert list did so by transmitting
curated records. Current grounded mapping sees only curriculum or textbook
excerpts.

## 5. Current D1 implementation

Both conditions use the same output contract:

```text
resource
kind = builds_on
taught_as
student_move
falls_short_because
provenance
confidence
```

The two conditions differ only in how the resource list is obtained:

```text
same target concept + grade + subject + optional teacher skills
        |
        +--> ungrounded:
        |       model proposes resources from the description
        |       no jurisdiction, no PF branding as a task type
        |       provenance = model
        |
        +--> grounded:
                retrieve curriculum pages for skills taught before the topic
                map excerpts to taught-skill labels
                provenance = curriculum
```

After the inventory/mapping step, one separate model call adds a short
**activation** note to each resource: what objects the tool needs in order to
start, and what extra demand the target adds. It does not invent a full
student solution. `--max-resources` applies before expansion; the default cap
is 5, with stronger curriculum provenance retained before model-only
candidates.

The historical intermediate trace is in
[PRIOR_RECOMMENDATIONS_TRACE.md](PRIOR_RECOMMENDATIONS_TRACE.md). These saved
August 24 comparison artifacts used the earlier curated-record handoff:

- [GPT-4.1-mini comparison](../../experiments/results/prior_recommendations/expert_comparison_gpt41mini_capped.json)
- [GPT-5.6-luna comparison](../../experiments/results/prior_recommendations/expert_comparison_gpt56luna.json)

Both record supplied and preserved curated resources. They demonstrate historical
provenance propagation, not independent recovery against the current held-out
expert lists. Current curriculum-only mapping must be evaluated separately;
updating the code does not retroactively change these runs.

### Limitation of `student_move`

The historical expansion illustrates procedural first moves for resources such
as ratios, LCM/HCF, and trial-and-error in the Kapur case. Those records do not
cover some observed RSM categories:

- qualitative insights, such as "the faster person should walk more";
- diagrams and other representational approaches; and
- algebraic attempts.

It can also produce a plausible move that was not observed in the paper. The
current activation-note expansion has not been shown to recover all those
categories independently. Thus
`student_move` is a model-generated hypothesis about a first action, not an
observation of student behavior. See Section 5 of
[PRIOR_RECOMMENDATIONS_TRACE.md](PRIOR_RECOMMENDATIONS_TRACE.md).

## 6. D2: calibrate the numbers

When a numerical contrast is part of the design, **breaking numbers** are a
number or data choice that does two things at once:

1. **Keeps a successful path valid.** The task still has a correct solution.
2. **Makes a declared prior approach mismatch**, when the plan explicitly
   requires that contrast.

This contrast is optional. Productive Failure does not require every familiar
method to be wrong, and a drawing or explanation does not need to be forced into
a formula just to count as an approach.

```text
breaking numbers =
  valid under the intended successful path
  AND
  mismatched under the prior approaches the task is meant to problematize
```

This is not the same as making every method fail. If the intended path also
fails, the task is impossible rather than PF.

| Kind of problem | Trusted methods | Successful path |
|---|---|---|
| Regular practice | work | also works |
| Breaking-number PF | look applicable, then fail or cannot decide | remains valid or inventible |
| Impossible | fail | also fails |

Fresh generation first proposes and selects a **design brief**: a complete goal,
relationships, allowed actions, possible approaches, and learning opportunity.
The October 11 discovery-separation implementation adds internal `key_idea` and
`naive_answer` notes in v2, separately from the student-facing job. Its
[bounded comparison](#october-11-bounded-d2a-discovery-separation-experiment)
is complete and missed its promotion rule; v1 historical briefs remain readable.
The current D2b proposes concrete data and relevant conditions together, computes
feasible conditions, and repairs only numbers within three model calls. It no
longer requires quantity translation or a separate mathematical-plan review.

### October 10: bounded data-and-check loop (original routing)

The October 11 [draft-first policy](#october-11-draft-first-completion-policy)
supersedes quality-based stops in this original routing, not its recorded results.

```text
D2a: selected brief, including its original requirements
    -> D2b: purpose-labelled data + conditions + useful calculations
    -> exact calculations + quoted textual judgments
       -> failed numerical condition: numbers-only repair, then recheck
       -> essential textual contradiction/error: review for design correction
       -> unsupported/unknown condition: visible warning, continue
       -> no known essential failure: D3 writes with givens and teacher-only evidence
```

The implementation is [design_data_stage.py](../../scripts/design_data_stage.py),
with a small [response contract](../../src/generation/design_data.py),
[safe calculator](../../src/generation/design_calculator.py), and
[prompts](../../src/generation/prompts/design_data.yaml). There are no fixed
answer/challenge/realism claim categories. Conditions refer to the particular
brief; original numerical requirements cannot be omitted or made non-essential.
After the first valid proposal, code freezes quantity meanings, units, roles, data sizes,
conditions and formulas. Repairs can return only values. Invalid model replies
consume the same three-call budget; every reply, request and check is retained.

The calculator uses a restricted syntax tree, not generated Python execution.
It supports exact arithmetic, named Boolean comparisons, square roots, bounded
powers, min/max/sum/abs/len, and symbolic identities under declared assumptions.
`unit(given_quantity)` checks a declared unit string; this is metadata comparison,
not dimensional analysis of every formula. Unresolved
symbolic results remain unknown. Its verdict verifies the supplied mathematical
expression, not whether the model encoded the intended condition correctly.
Formula-to-condition alignment remains inspectable model output, not an
independent guarantee.

Uncomputed conditions retain their reason and model judgment. The existing data
call is prompted to quote relevant supplied wording, identify its source, and explain its
scope: an explicit task rule is an assumption within the exercise, not proof
of a real-world fact or a further mathematical conclusion. Computable claims
remain calculations, even when expressed in words. Mixed numerical and textual
requirements should be separated; invented 0/1 truth flags are not evidence.

Supported textual claims continue as `model_judged`, not exact verification.
Uncertain textual claims and unknown or unsupported calculations remain in
`unresolved` and `warnings`; they do not block writing even when essential.
Essential model-judged failures are recorded separately in `textual_failures`
and stop with `review_needed`: changing numbers cannot repair conflicting rules.
Essential calculated failures still enter numbers-only repair. A textual failure
takes precedence when both occur; uncertainty does not hide a numerical failure.
`accepted` means permission to continue, not that every condition was verified.
Invalid proposal schemas still consume the bounded retry budget.

Optional behavioural predictions do not block writing and are not evidence
that students will actually take those approaches. D3 receives fixed data and
teacher-only evidence, without the old mathematical-plan interface. It must not
invent missing assumptions, present unsupported conclusions as established, or
block merely because evidence is missing. Software checks do not prove that its
prose, contextual assumptions, or PF learning mechanism are valid.

This route is the default in the situation CLI, diagnostic worker and paper
benchmark. Sources, prompts and effective budgets are saved. Explicit legacy
diagnostic/benchmark settings and historical result readers remain available.
`--no-fill` selects a brief without running D2b. Resuming a new saved run
recalculates its frozen proposal; `--replan` explicitly permits a new proposal.
The resumed run records its initial proposal and initial check, while
`design_data_history` retains earlier run records separately from new attempts.
`--plan-only` applies only to historical saved mathematical plans.

#### October 10 textual-claim policy and replay checks

The [claim-policy validation summary](../../experiments/results/d2b_claim_policy_replays_20261010/final_validation_summary.json)
keeps offline replay, live calibration, and final fixed-design runs separate.
Historical inputs and outputs were not overwritten.

- Eight saved proposals passed the new continuation policy, including the earlier
  fair-division divisibility stop and model-only speed-unit stop. All eight
  deliberately altered-number inputs were repaired by mock restoration while
  preserving conditions and quantity metadata. These are zero-call software
  replays, not fresh model judgments or eight new exercises.
- Four live development calibrations used eight model calls. The first
  fair-division data proposal encoded divisibility as an invented `1` and its
  writer blocked; that artifact remains visible. Generic prompt changes prohibit
  such flags, separate mixed requirements, request verbatim fragments, and
  distinguish operation permission from guaranteed attainability. Calibration
  was also checked on speed and consistency, not only fair division.
- With the final prompt frozen, three saved designs (speed, consistency, fair
  division) produced three ready tasks using five data calls and three writer
  calls. Two extra data calls were **proposal-schema retries**, not numerical
  repairs: each first response omitted a required textual judgment. The three-call
  data budget was respected. Frozen design, context, and case snapshots were
  preserved, historical source hashes were unchanged, and independent
  recalculation matched the recorded checks.
- The final runs returned three textual `holds` judgments. Four of five quoted
  fragments match the supplied wording verbatim; the fifth changes a terminal
  comma to a period. Literal source presence does not prove logical sufficiency.
  Uncertainty, unknown calculations, and textual failures were exercised by
  software tests, not balanced live claim-judgment calibration.

The affected software suite passed 551 tests, with targeted Ruff and compilation
passing; the full suite was not run. Live continuations use frozen existing
designs with new data, not fresh end-to-end or held-out generation. The final
fair-division task still supplies threshold-marked values and proposed-allocation
received values, a PF design-quality concern. No student responses or learning
outcomes were tested.

#### October 10 quality interpretation and agreed next focus

**D2b is complete for the agreed implementation scope and can be frozen for the
next experiments.** This means data generation, calculation checking, bounded
numerical repair, textual judgments, and nonblocking uncertainty are implemented
and replay-tested. It does not mean independently validated textual judgment or
proven PF quality.

The improvement journey exposed an important distinction: the earlier review
stop concerned missing support, not a demonstrated false claim. Allowing visible
uncertainty fixed that continuation policy, but producing a task does not establish
that students have something meaningful to discover. The final prompt avoids
the observed invented divisibility flag, yet all final textual judgments are
`holds`; reliable live discrimination of supported, unsupported, and wrong claims
remains unestablished.

The following is an AI qualitative inspection, not a human rating or new
student experiment. It compares the final claim-policy replay tasks with
[Kapur's documented principles](KAPUR_BIELACZYC_2012_EVIDENCE.md#design-facts-useful-for-pf-generation)
and the expert comparisons below.

| Expert design expectation | Current gap and evidence |
|---|---|
| Accessible starts with a useful limitation, without frustration | Prior resources and approach records provide hypotheses, not learner-tested challenge calibration. Some familiar constructions can still settle the whole goal routinely. |
| Consequential mathematical construction or choice | The [final speed task](../../experiments/results/d2b_claim_policy_replays_20261010/final_live/speed/result.json) asks for fixed-journey rates, unlike the expert's unknown bike-handover point. Display freedom alone does not create a distinct mathematical decision. |
| Students discover critical features | The [final consistency task](../../experiments/results/d2b_claim_policy_replays_20261010/final_live/consistency/result.json) supports measure invention but announces equal averages and extremes. The [final fair-division task](../../experiments/results/d2b_claim_policy_replays_20261010/final_live/fair_division/result.json) supplies fair-share and successful-allocation values. These disclosures reduce the opportunity to discover the limitation or establish the result. |
| Multiple meaningful approaches | Generated approach records are predictions. No simulated or real student attempts establish distinct reasoning, failure, or engagement in these runs. Different displays of one calculation are not sufficient. |
| Attempts inform consolidation and learning | These generation runs do not collect attempts and connect them to consolidation: subsequent teaching that compares student approaches with the target concept. Learning and transfer have not been evaluated. |

Kapur does not require every approach to fail or every student to invent a named
formula. Partial and successful approaches can support useful comparison. The
Loibl reference remains a reconstruction without its complete original numerical
table; it should not be treated as an exact student-text gold standard.

**Agreed next focus:** improve the student-facing task, then evaluate actual
approaches against direct generation and expert references. Preserve necessary
assumptions and solvability; do not create difficulty by hiding needed
information or banning valid methods. The origin trace below is complete; the
refinement remains proposed work.

**D3 disclosure trace and implemented writer rule (October 10):** the trace covered six
independent pipeline designs (two per expert direction) and their eight ready
written tasks. Every solution-revealing sentence identified was copied, nearly
verbatim, from D2a `situation_and_rules` or `student_question`, or listed from
D2b values; D3 amplified one speed hint. Both consistency designs announce equal
averages and extremes and list properties of the target measure; both speed
designs require accounting for the whole journey; both fair-division designs
list trimming-procedure actions, and the final proposal lists fair-share and
verification-allocation values. One of two direct consistency tasks also
announced equal summaries, so the habit is not pipeline-only. Identification
used a keyword scan and assistant reading, not a validated disclosure measure.

Before the change, the prompts disagreed about who reads `situation_and_rules`.
D2a wrote a teacher-facing brief and put "allowed actions, and criteria for judging
an invented method" in that field; it also repeated value-dependent requirements
there. The writer had to "preserve every given value, unit, assumption,
relationship and allowed action" and received "FIXED GIVEN DATA AND CONDITIONS".
These instructions explain the copying, but the replay changes several instructions
together and does not isolate their causal effects. The earlier field-only
separation proposal would have passed these sentences through.

In the final consistency data, the mean, range and sum of signed deviations each
tie between the batches, so the data contain three impasses for familiar
methods. The text announces the first two and its "nonnegative" criterion
pre-empts the third.

The implemented writer rule is content-based. Keep the situation, raw data and units,
rules defining what is possible, the question, and a criterion only where it
defines the requested answer's form. Withhold properties students can calculate,
steps or outcomes of the planned route, and criteria answering an anticipated
approach's limitation; list them in a teacher-only field instead of omitting them
silently. For pedagogical conflicts, block only when the question cannot be posed
without them; malformed output remains a separate software blocking issue.
The caller builds task-specific do-not-state evidence from existing approach,
successful-route, learning-opportunity, requirement and condition fields. Quantities
are labelled as candidate raw data or check-only values, not universally fixed
givens. Rubric guidance remains in D2a but is removed from the fixed-design writer.
The D2a prompt now places target-method success criteria and procedure menus in
teacher fields rather than situation/rules. This alignment has software tests,
not fresh-generation evidence.

The stored Kerrigan and StratL texts give a situation, raw data and an open
question; StratL's "use all data points" shows one answer-form criterion has
expert precedent. Its invitation to design many measures remains unadopted so
approach diversity can be attributed to the task. D3 can make tasks less
revealing, not more productive: the final fair-division values describe a
competing claim abstractly instead of letting students encounter one; in the final
consistency data, counting values at the average, mean absolute deviation and
mean squared deviation reach the same decision, so the squared-deviation contrast
in the brief changes no conclusion; fixed speed journeys do not require
constructing an unknown.
These need design/data improvements beyond wording. The replay below establishes
some reduction of disclosure, not improved PF outcomes.

#### October 10 D3 disclosure implementation and replay

Implementation:

- [Writer prompt](../../src/generation/prompts/design_data.yaml) applies
  keep/withhold/block precedence to every field. It distinguishes raw observations
  from calculated or planned outcomes, answer-form requirements from target-method
  properties, and generic representation freedom from procedure-specific menus.
- [Caller and validator](../../scripts/design_data_stage.py) retain the public
  `(task, raw_text)` return interface and add teacher-only `withheld` entries with
  `kind`, `source`, `quote` and `reason`. Quantity omissions quote their complete
  descriptions. Validation establishes source/quote grounding and schema validity,
  **not** correct classification or absence of equivalent hints.
- [Writer-only replay](../../scripts/replay_pf_discovery_writer.py) preserves saved
  cases, prior context, selected briefs and D2b results, records source hashes and
  prompts, and refuses to overwrite existing JSON results before making a call.
  Historical non-ready inputs are recorded as unavailable, not repaired by D3.

Four earlier three-topic calibrations used twelve writer calls before the final
eight-task replay; all artifacts remain in the
[replay directory](../../experiments/results/d3_discovery_writer_replays_20261010).
They exposed important failures: a general answer-form distinction still let
target properties through; stronger withholding once removed all fair-division
raw data; moving the whole goal to teacher-only evidence lost a single-number
output requirement; and deleting a revealing label did not remove its numeric
result. These are development iterations on three topics, not held-out validation.
The final prompt retains mixed goal requirements and raw inputs, and explicitly
distinguishes generic permissions from target-method action menus.

The [final exact-output comparison](../../experiments/results/d3_discovery_writer_replays_20261010/latest/side_by_side.html)
contains **eight ready tasks from eight eligible writer calls**. A ninth saved run
had an earlier D2b stop and received no writing call. The three final-live cases
continue fresh attempt 001; the eight pairs must not be counted as independent
designs. GPT-5.6-luna and the requested token settings were retained; the baseline
is the historical saved output, not another old-prompt draw.

| Check or assistant observation | Final replay finding |
|---|---|
| Required raw data | Numeral coverage and direct reading retained required data, units and associations in all eight rewritten tasks. |
| Raw versus check-only selection | Seven of eight matched the [predeclared quantity expectations](../../experiments/results/d3_discovery_writer_replays_20261010/raw_quantity_checks.json). The final-live fair-division task retained marked-portion values `[4, 4, 4]`. |
| Consistency disclosures | All three tasks removed announced equal summaries and explicit target-property lists. One still gives the conceptual distinction between typical performance and consistency. |
| Fair-division disclosures | Both target-procedure action menus were removed. The final-live verification-allocation result was removed, but its planned marked-portion intermediate remains. |
| Speed disclosures | Explicit total-based checking or body advice was reduced, but the final-live question reintroduced "accounts for every part"; the two fresh tasks retain softer complete-journey guidance. |
| Software checks | 270 focused design, writer, replay, runner and diagnostic tests passed; targeted Ruff checks passed. Not educational validation. |

Exact before/after quotes and residual issues are in the
[assistant inspection](../../experiments/results/d3_discovery_writer_replays_20261010/inspection.json).
There is **partial improvement, not a reliable disclosure-free writer**.
In particular, a model's `withheld` list cannot verify itself: numeral coverage
must use independently specified raw-data expectations, and wording must be read
for paraphrased hints. Required data were retained in the final replay, but this
does not establish universal solvability or student approach diversity. A stronger
information handoff or independent disclosure check is possible next work, not
implemented here. D2b's claim policy remains unchanged.

#### October 11 data-purpose handoff and eight fixed-brief reruns

**Problem:** the twenty-topic inspection below found that supplying a successful
construction could turn "design" into "verify". D2a already asked students to
choose the objects; D2b stored its feasibility examples as unlabeled values, and
D3's necessary keep-data rule retained them. Removing every checked number would
instead destroy observation tasks.

The [data prompt](../../src/generation/prompts/design_data.yaml)
and [contract](../../src/generation/design_data.py)
now require each new quantity to have `role="given"` or `role="teacher_example"`.
The distinction is its purpose in the student's job, not whether the calculator
uses it. A budget or observed length is given; teacher-chosen dimensions that
answer an open construction are an example. Mixed-purpose quantities should be
split. Derived answers still belong in expressions, not extra quantities.

[D2b](../../scripts/design_data_stage.py) checks both roles and freezes them during
values-only repair. D3 receives only givens in its student-data section, with
example descriptions, units and values retained in separate teacher-only evidence.
The writer is explicitly permitted to pose an open construction with no numerical
givens. Historical unlabeled proposals remain readable and resume without relabeling;
offline recorded-reply replay explicitly uses the historical optional-role contract.
Fresh proposals missing a role consume the existing schema-retry budget.
The agreed numerical/textual/unknown claim policy is unchanged.

A deterministic, nonblocking writer warning reports when every numeral in one
teacher-example quantity occurs in the student text, counting repetitions.
It is a screen, not a judgment that a solution leaked: scalar values can also be
legitimate prices or counts. The shared numeral helper also keeps replay coverage
from demanding explicit teacher-example values.

**Prespecified development check:** the
[eight-case configuration](../../experiments/configs/pf_data_roles_20261011.json)
recorded expectations before calls. Gardens and ribbon measurement were inspected
as two calibration cases before the other six ran under the same frozen prompts.
All eight reuse the twenty-topic run's exact case, prior context and selected
brief, with fresh D2b data/conditions and D3 writing. No task was replaced or
manually redesigned. Both stages and numerical inputs change, so this is not
an isolated writer comparison or causal quality experiment.

| Directly inspected outcome | Result and meaning |
|---|---|
| Completion | 8 tasks from 8 attempts using 16 calls: 8 data proposals and 8 writer calls; no schema retries, numerical repairs or API errors |
| Open constructions | All 3 fraction-card, garden and box tasks leave numerical choices to students instead of supplying prepared successful objects |
| Necessary inputs | All 5 ribbon, order-constraint, token, combined-mean and causal-observation controls retain required inputs and their associations |
| Role assignments | 15 given quantities and 22 teacher-example quantities; optional sample orders and arbitrary token labels are examples even in control tasks |
| Mathematical/software checks | All 36 supplied predicates return computed `holds`; independent arithmetic/enumeration confirms the selected contrasts; all traces, source hashes and frozen inputs verified |
| Leak warnings | 2 warnings in the ordering task are coincidental matches: 5 is also a packet price and 2 is also the number of packet kinds |
| Executable validation | 160 affected tests and targeted Ruff passed; not the full repository suite or educational validation |

The [before/after gallery](../../experiments/results/pf_data_roles_20261011/frozen_8/tasks.html),
[direct inspection](../../experiments/results/pf_data_roles_20261011/frozen_8/inspection.json)
and [verification record](../../experiments/results/pf_data_roles_20261011/frozen_8/verification.json)
retain exact outputs and limitations. For example, the garden question changes
from "Use the recorded garden dimensions" to "Design two comparisons". Its
teacher examples still verify equal perimeters with areas 12 and 15, and equal
areas of 24 with perimeters 22 and 20, without supplying those dimensions.

**Meaningful residual findings:** separating example values is not a complete
information boundary. The box writer still promotes teacher-example
whole-number centimeter dimensions into student rules; the selected situation
required only positive dimensions. The fraction-card writer over-withholds
ordinary draw/cut/rearrange/label permission. The probability question explicitly
requests an equally likely sample space, and the ribbon reference-length wording
is awkward. These are preserved outputs, not silently corrected successes.
Exact quotation records cannot validate a withholding judgment, and numeral
coverage cannot validate units or associations.
The rerun supplies model-labelled givens to numeral coverage; its historical
`external_raw_quantity_manifest` label does not make these an independent role
judgment. The separate predeclared purpose expectations and direct reading support
the role assessment reported here.

The tested handoff restores the intended student choice while retaining necessary
data on this selected set. It does not establish reliable disclosure-free writing,
multiple meaningful student approaches, productive failure or learning. All cases
come from previously inspected development topics; no new D1/D2a generation,
held-out quality evaluation or student-response experiment was performed.

**Expert-standard reading of the eight reruns (assistant reading, not a rating).**
The stored expert tasks do give support: the
[StratL bike task](../../data/pf_exercises/puech_macina_2025_stratl_full.yaml)
supplies the ride-ahead-then-walk plan, and the StratL consistency task asks for
several measures that use all data points. They keep the central unknown or
invention for students: where to leave the bike, or how to measure consistency.
"No hints" is therefore not the standard; the question is whether the text does
the key reasoning for students.

| Reading | Rerun tasks | Evidence |
|---|---|---|
| Key idea left to students; a tempting approach can fail | Ribbon, combined mean, packet orders (3 of 8) | Averaging the two means gives 4, not `21/5`; reporting the ribbon leftover as `1/8` instead of half a unit is an anticipated error; a few listed orders miss the complete set of 19 |
| Instruction states the target idea; students make examples | Gardens, boxes, fraction cards (3 of 8) | "make rectangular gardens with the same perimeter but different areas", so the belief that equal fencing gives equal area is never tested |
| Text names the key idea | Tokens, screen time (2 of 8) | "Construct a complete equally likely sample space"; "Distinguish a pattern in the records from a claim that one quantity causes another." |

Four of these five disclosures are already in the frozen selected brief; the writer
added only the token request, from the brief's goal. Even the three passing tasks
are small and well-structured. The combined-mean task has the shape of the
[ship practice problem](../../data/pf_exercises/kapur_bielaczyc_2012.yaml) used
after direct instruction in Kapur and Bielaczyc's study, not their bike PF problem.
Two passing tasks also list a successful display: "repeated values" and
"coordinate grids". Writer-only fixes would leave most of these disclosures; the
selected design must keep the target claim and key idea out of the student's job.
This inference comes from eight selected development tasks, not student attempts.
Quotations were checked against the saved task and brief fields.

**Where the five giveaways enter (trace of saved inputs).** The selected and
rejected D2a proposals, the selection reasons and the saved writer requests were
compared.

| Entry point | Tasks | Evidence |
|---|---|---|
| D2a proposals: both candidates give the idea away | Boxes, screen time | Both box questions ask for boxes holding the same amount with different amounts of material; both correlation questions ask for different explanations or at least two |
| D2a selection: the giveaway beat a more open proposal | Gardens, fraction cards | The rejected garden question asked "whether one measure fixes the other"; the selector preferred the other proposal as "more directed". The rejected card question asked "Which labels can describe the same proportion of a whole?" |
| Handoff to D3: the goal is sent as student wording | Tokens | Both goals began "Construct a complete equally likely sample space"; [the writer request](../../scripts/design_data_stage.py) sends `goal` as candidate wording, and the writer must keep the goal's output requirements |

The suspected shared cause has not been tested: the brief has no field for the
idea students should discover, separate from what they must produce. The
[proposal prompt](../../src/generation/prompts/design_briefs.yaml) asks for the goal
"as what students determine or construct", so the claim "fixed perimeter need not
imply fixed area" became a goal to construct examples showing it. The question then
asks for those examples or adds a follow-up that presupposes the claim, meaning it
only makes sense once the claim is accepted. The twenty-topic sampling-bias question
first asks students to "decide whether that claim is justified" and then asks "how
could the larger survey give a misleading picture?" The selection prompt rejects
"a question that supplies the intended method" but has no matching rule for the
conclusion, and the brief path records the legacy `target_named` flag as false
without checking it.

At this point the proposed D2a change was not implemented: add internal design-note `key_idea` and
`naive_answer` fields before the goal; limit the goal and question to what
students produce; require the naive answer to remain a sensible reply that the
situation can expose; give the selector the matching rejection rule; and add both
fields to the writer's do-not-state list. Evaluate on the same eight targets with
D1 frozen, then on the other twelve sweep topics without retuning. Those topics
were inspected earlier but were not used to write the change. The later
[bounded experiment](#october-11-bounded-d2a-discovery-separation-experiment)
records implementation and comparison status separately.

These internal notes are generator information, not student text; "teacher-only"
does not mean a human teacher or teacher agent participates in generation.
The anticipated wrong answer is a hypothesis, not an observed misconception or
a requirement that every student or familiar approach must fail.

#### October 11 automated-research review and proposed experiment strategy

**Scope and status.** The user requested public automated-research repositories
and a way to improve generation while producing educational findings rather than
remaining in an indefinite prompt-tuning loop. Public README files, relevant
controller/evaluator code and primary papers were inspected. No external
repository was installed or executed, no paid generation was run, and no local
source or student data was transmitted. The strategy below is proposed, not an
implemented controller or a completed experiment.

**What the public implementations offer.** The links pin the revisions inspected
on October 11, 2026; these are implementation observations, not PF benchmarks.

| Repository | Useful mechanism | Important limitation for this thesis |
|---|---|---|
| [karpathy/autoresearch](https://github.com/karpathy/autoresearch/tree/228791fb499afffb54b46200aca536f79142f117) | Restricted edit surface, baseline, fixed-duration training trials, and a keep/discard/crash ledger | [Its protocol](https://github.com/karpathy/autoresearch/blob/228791fb499afffb54b46200aca536f79142f117/program.md) tells an external coding agent to continue indefinitely. Validation language-model loss is not educational quality, and evaluator immutability alone does not prevent misleading measurements. |
| [WecoAI/aideml](https://github.com/WecoAI/aideml/tree/60b3978ddf65b71f86eb7c64506965048a1398cf) | Bounded draft/debug/improve search, atomic-change instructions, and a saved experiment tree | [Generated code supplies the metric](https://github.com/WecoAI/aideml/blob/60b3978ddf65b71f86eb7c64506965048a1398cf/aide/agent.py); an LLM extracts it. An independently controlled PF evaluator is still needed. |
| [SakanaAI/AI-Scientist-v2](https://github.com/SakanaAI/AI-Scientist-v2/tree/96bd51617cfdbb494a9fc283af00fe090edfae48) | Separate baseline tuning, intervention search and ablation stages; an ablation changes or removes one component to investigate its contribution | Automated reports and manuscript judgments do not verify scientific conclusions. The [authors' assessment](https://arxiv.org/html/2504.08066v1#S4.SS2) identifies train/test overlap and interpretation problems. Its custom license also means public/source-available is more precise than assuming a permissive open-source license. |
| [DSPy](https://github.com/stanfordnlp/dspy/tree/f1260ff14610286cb295c7d3a5ee2cbfd0ba5cb9) with [GEPA](https://github.com/gepa-ai/gepa/tree/462e437a09be67d2acb59564cc0ea59132f5777c) | Modular LLM programs and feedback-driven prompt evolution with candidate history and stopping callbacks | Better scores remain dependent on the supplied evaluator. [GEPA's default example evaluator](https://github.com/gepa-ai/gepa/blob/462e437a09be67d2acb59564cc0ea59132f5777c/src/gepa/adapters/default_adapter/default_adapter.py) checks answer-string inclusion, which is not a PF measure. Metric-call limits do not cap all API spending. Explicit development, validation and sealed test sets are required. |

The original [AI Scientist](https://github.com/SakanaAI/AI-Scientist/tree/1de1dbc1f4ee2c5f61e9c94348d55eb51d7fa2eb)
was also inspected. Its template-driven experiment and manuscript workflow is
not a turnkey educational researcher. These repositories support borrowing
experimental discipline; they do not justify unrestricted autonomous changes or
automatic claims about students.

**Recommendation: two connected activities, not one score-maximizing loop.**

```text
Researcher fixes hypothesis, controls, outcomes and budget
                         |
Agent proposes one bounded design intervention
                         |
Matched generation -> independent checks -> retain every outcome
                         |
Record mechanism evidence, uncertainty and cost
                         |
Freeze selected version -> unseen topics -> blinded expert review
                         |
Student attempts -> common consolidation -> learning/transfer evidence
```

Development optimization may use automated feedback. Final evaluation must not
be editable by the optimizing agent or become feedback for further tuning.
Reward hacking means improving the recorded score without improving the
intended educational property; a second LLM judge is not, by itself, protection.

The current [topic-sweep runner](../../scripts/run_pf_topic_sweep.py) already
freezes source hashes and specifications, preserves failed attempts and records
calls. The [fresh-comparison runner](../../scripts/run_pf_fresh_comparison.py)
already supports repeated direct/pipeline generation with fixed context.
Reuse these rather than adopting a large autonomous-research stack immediately.
Missing work includes a campaign-wide budget, controlled intervention scheduling,
independent final evaluation and untouched final cases. GEPA can be considered
later if manual candidate search becomes the bottleneck; installing it does not
solve outcome validity.

**Questions that turn improvements into research findings.**

| Proposed comparison | Research question | Evidence and claim boundary |
|---|---|---|
| Strong direct generation versus frozen decomposed generation | Does explicit design/data separation preserve the central unknown and meaningful student choices? | Common targets, learner information and final evaluation; report costs. This tests complete methods, not decomposition alone when guidance or compute differ. |
| Current D2a versus internal-notes/discovery-preserving D2a package | Does separating the intended discovery from the student's job reduce giveaways without removing useful support? | Freeze D1, D2b policy, writer policy, model and sampling settings. Count giveaways, accessible starts, target preservation and valid final tasks. The package includes proposal, selection and handoff changes; gains cannot be attributed to the extra fields alone without a later ablation. |
| Task-text judgments versus independently produced attempts | Do tasks rated open actually elicit mathematically distinct approaches? | Code mathematical reasoning, not answer strings or different display formats. Model attempts remain simulation evidence; independently collected student attempts support a behavioral claim. |

First finish the focused D2a comparison, not simultaneous changes to task size,
D1 grounding, D2b checks and the simulator. The gardens rewrite is a candidate
design, not proof of expert-like PF: an optimization question can still collapse
to one procedure. Reduced giveaway counts with unchanged approach diversity
would be a useful negative result, not a reason to redefine the metric.

**Proposed bounded campaign.** Allow at most three development rounds on the
eight diagnostic targets. Repeat generation under frozen settings instead of
judging one lucky output; model seeds may not ensure reproducibility. Define
acceptance criteria and the total call/token/cost cap before execution, counting
generation, reflection, evaluation and retries. After two rounds without a
predefined useful gain, stop that intervention and record the result. A genuine
checker defect is a separately versioned instrument correction, not permission
to silently change the outcome definition.

Keep mathematical validity, target preservation and an accessible starting point
as non-negotiable checks; report unsupported cases as unknown rather than valid
or invalid. Report separate rates for disclosure, consequential choices and
meaningfully different approaches, plus ready tasks per attempted task and cost.
Use a common final mathematical review on direct and pipeline artifacts rather
than equating absence of a generation-time check with invalid mathematics.
Do not maximize student failure or combine everything into one unvalidated PF
score.

All twenty existing sweep topics are development material. The other twelve can
check broader coverage without retuning, but are not an untouched final test.
A possible small final design is twelve new topic/task-family specifications,
three generation methods (strong direct, current pipeline, selected improvement)
and three repeated generations per specification: 108 planned task attempts,
including unsuccessful attempts in the accounting. This is an illustrative
workload, not a powered sample-size calculation or an approved spending budget.
Keep final cases and scores out of search, and avoid near-duplicate templates or
prompt examples. If claiming decomposition benefits rather than whole-system
benefits, add a comparable-budget direct sample-and-select control. Report
differences with uncertainty accounting for outputs sharing a topic.

**Independent educational evaluation.** Calibrate task judgments with two
blinded educational reviewers, including difficult negative controls such as a
fluent one-procedure problem and a no-hints problem with missing necessary data.
Report disagreements. A simulation should see only the student task and prior
knowledge specification, not the design's predicted failure or successful route;
asking it to produce several different methods can manufacture the diversity
being measured. Treat simulation as a diagnostic hypothesis until compared with
student work.

[Yuan et al. (2026)](https://arxiv.org/abs/2601.05473) discuss valid student
simulation in a conceptual/methodological paper, not a new validation experiment.
[Sonkar and Baraniuk (2023)](https://arxiv.org/abs/2305.14507) provide controlled
evidence about difficulty reasoning from erroneous beliefs, not current-model
PF accuracy. These support caution, not a universal claim that simulation cannot
work.

For learning claims, use an ethically approved learner comparison with prior
knowledge assessment, controlled time and equivalent consolidation, meaning
subsequent teaching that connects attempts to the target concept. Measure
conceptual understanding and transfer to a new problem; consider delayed
retention. Actual design should follow the primary question: generated versus
expert PF evaluates task sources, whereas PF versus instruction-first evaluates
instructional order. Neither follows from model ratings alone.
The [Sinha and Kapur (2021) synthesis](https://doi.org/10.3102/00346543211019105)
evaluates problem solving followed by instruction; its abstract was verified via
[Crossref](https://api.crossref.org/works/10.3102/00346543211019105), not a newly
read full paper. It reinforces that exercise difficulty alone is not PF.

**Contribution and SOTA boundary.** State-of-the-art (SOTA) is a comparative
claim requiring specified contemporary baselines, common inputs, independent
outcomes and costs; this research has not established it. The previous Rahimi
reconstruction and historical model ratings do not constitute that claim. A
defensible contribution can instead explain when LLM design decomposition helps,
when the model turns learning goals into answer-revealing instructions, and when
task-quality judgments disagree with produced approaches. Independently improved
task design is valuable even if a learning study is unavailable, but then the
paper must describe design evidence rather than improved student learning.

#### October 11 bounded D2a discovery-separation experiment

**Completed: the package did not meet the improvement rule.** The protocol and
implementation notes below were recorded before generation; results follow them.
The user approved starting bounded automated research and recording meaningful
findings during the work. The local hypothesis
is that separating the intended discovery from the student-facing job, including
the proposal, selector and handoff, will reduce conclusion giveaways without
removing essential problem definitions. The saved eight-case trace above is the
motivation, not the baseline measurement for the new comparison.

**Declared intervention package.** New briefs will use `design-brief/v2`, with
internal `key_idea` and `naive_answer` before the goal and question. The latter is
an anticipated first answer, not a known student misconception or a requirement
that every approach fail. The selector will check whether that answer remains
a sensible response to the question rather than being ruled out by its wording.
The writer receives both notes as do-not-state evidence. Old v1 briefs remain
readable, and the pre-change prompt is saved unchanged as
[the baseline snapshot](../../experiments/results/pf_d2a_discovery_20261011/baseline_design_briefs.yaml).
This compares the whole package; gains cannot identify one field's contribution.

**Frozen comparison and budget, written before calls.** Reuse saved case inputs
and D1 resource inventories from the twenty-topic sweep. Regenerate D2a, D2b and
D3 in both arms using the same model, two proposals, data/writer prompts, checker,
retry policy and sampling settings. No new curriculum retrieval, simulation or
automated quality judge is part of this experiment. First run gardens and weighted
means once per arm as implementation calibration, kept separate from evidence.
Then run the eight diagnostic topics three times per arm: 48 development attempts.
Use a frozen interleaved schedule. Count failed attempts, and do not replace them.
The cap is nine API requests per attempt and 468 across calibration plus comparison,
including failed requests and format/data retries; no hidden SDK retries.
Each response is capped at 6,000 completion tokens, a worst-case total of 2,808,000
requested completion tokens. Actual usage is recorded; money cannot be reported
honestly without verified provider prices. Only one development round is authorized
here; no automatic second round or twelve-topic expansion.

**Evaluation definitions and decision, frozen before calls.** Independently of
which arm generated a task, read its exact student text for:

- **Disclosure:** does it state the mathematical method, correction or conclusion
  students are meant to develop, or presuppose that conclusion in a follow-up?
  Naming needed objects, giving necessary rules and generic representation
  permissions are not automatically disclosure.
- **Task mathematics:** are inputs, claims and required outputs consistent and
  attainable? D2b acceptance alone is not a task-level mathematical proof.
  Unsupported or undecidable cases remain unknown.
- **Accessible start:** is necessary information present and a stated familiar
  resource plausibly usable? This is a design judgment, not student evidence.
- **Consequential choice:** can a student's decision or construction change the
  mathematical work, rather than only its display? This does not measure approaches
  actually produced.

Report ready-task counts, disclosure-free ready tasks per all attempts, mathematics,
accessible starts and choices separately, with denominators and usage. A promising
development gain requires at least six additional disclosure-free ready tasks out
of 24 attempts per arm (25 percentage points), at most one fewer ready task, and no
increase in clearly invalid or missing-essential-data tasks. Unknown cases cannot
pass these checks. This is a pragmatic pilot decision rule, not a powered statistical
test or a validated PF metric. Anonymized task presentation reduces immediate
arm-label cues, but assistant review is not blinded human expert review. Preserve
every observation and classify partial or null gains honestly.

Implementation and calibration findings will be appended here as they occur.

**Implementation finding, before generation.** The v2 fields are required for
fresh intervention proposals, but historical v1 payloads retain their exact
serialized shape. Accepting unversioned model responses as v1 in the new arm would
silently bypass the intervention, so the proposal stage explicitly enforces the
chosen arm's schema. Both new notes reach the existing writer's do-not-state
evidence, not its candidate student wording; D2b and D3 prompt files are unchanged.
The first 108 targeted schema/data tests passed. Caller checks then exposed seven
software fixtures still returning v1 under the new default; those fixtures were
updated to v2 rather than weakening the schema check. This is an implementation
correction, not an educational finding or model calibration.

The affected caller/replay checks now pass: 205 targeted tests and targeted Ruff.
On the existing v1 fixture, the new writer's source list and rendered request are
exactly identical to the saved pre-change implementation. All eight frozen inputs
have usable D1 inventories (two or three resources each) and the same historical
`gpt-5.6-luna` model. Their targets often already state the desired discovery:
"fixed perimeter need not imply fixed area", or "a combined mean must account for
group sizes". That is appropriate generator context, not student wording. The
research question is therefore not whether the model can avoid seeing the
conclusion, but whether it can translate a supplied learning conclusion into a
challenge without giving that conclusion to students. This interpretation is
supported by the saved input text; its effect on outputs remains untested.

**Runner acceptance, before calibration.** The bounded runner passed 28 focused
tests. It records every request before SDK dispatch (including errors), overrides
the shared helper's timeout at the request boundary to 120 seconds, disables SDK
retries, and preserves stopped attempts on resume. Source snapshots include
transitive local imports. The task gallery hides arm labels and internal design
notes but retains the supplied target so relevance can be assessed. This is
assistant reading with reduced label cues, not independent expert blinding.

**Calibration completed, not comparative evidence.** All four scheduled attempts
produced ready tasks using twenty requests, with no API errors, unchanged frozen
inputs/sources, and the correct v1/v2 schemas. The intervention notes reached the
writer's internal evidence. Recorded usage was 55,682 input and 28,886 output
tokens; the latter includes 17,416 reasoning tokens, not an additional chargeable
token total. Both garden tasks leave the area claim unresolved; the intervention
uses an explicitly contestable conjecture. Both mean tasks are still compact
calculations, so disclosure reduction alone cannot establish stronger PF. The
tasks have feasible numerical answers (20 m fencing; combined means 13 and 6.4).
No prompt was tuned after calibration. The frozen 48-attempt development run now
proceeds, retaining every stop/error in its denominator.

**Finding during the frozen run: withholding can remove the problem itself.**
An anonymously read strip task
(`task-7ecd318362510607`) asks which supplied strips match, but supplies no
part counts or strip drawings. After recording that missing-data judgment, its
trace showed D2b assigned **all** supplied-strip counts to `teacher_example`;
the writer faithfully withheld them. New-strip construction counts should be
internal, but existing strips are essential inputs to a comparison. This is a
verified role-assignment mismatch, not a reason to edit the writer or silently
repair this run. The attempt remains in the denominator. A future intervention
must distinguish student-chosen constructions from supplied objects to compare.

**Related observation, not a causal result:** several anonymously read tasks
without a disclosed conclusion still ask for one fixed quotient or combined
mean. Generic permissions to draw, tabulate or calculate do not create substantive
student choices. Discovery preservation and open mathematical work remain
separate outcomes; this experiment must not collapse them into one quality score.
No source, prompt or evaluation definition is changed during the comparison.

**Completed development comparison.** All 48 scheduled attempts finished, with
no replacements or prompt changes. All 41 ready student tasks were read from
the arm-hidden gallery; the other seven attempts received unavailable ratings,
not disclosure-free passes. Ratings were recorded before revealing the mapping
for aggregation. The reviewer implemented the intervention, so this is reduced
label exposure, not independent blinding.

| Outcome (higher is better unless stated) | Frozen old prompt | Discovery-separation package |
|---|---:|---:|
| Scheduled attempts | 24 | 24 |
| Ready tasks | 23/24 | 18/24 |
| Disclosure-free ready tasks, before separate math checks | 12/24 (50.0%) | 14/24 (58.3%) |
| Also judged valid, accessible, and target-preserving | 11/24 | 14/24 |
| Ready tasks with a disclosed method/correction/conclusion (lower is better) | 11 | 4 |
| Ready tasks judged mathematically valid | 20 | 17 |
| Ready tasks missing essential data (lower is better) | 2 | 0 |
| Ready tasks with unresolved mathematical wording (not a pass) | 1 | 1 |
| Ready tasks with consequential mathematical choices/constructions | 14 | 9 |
| Those choices in valid, accessible tasks | 11 | 8 |
| No selected brief (not a written-task failure) | 0 | 6 |
| Blocked writer output (not an invalid written task) | 1 | 0 |

The primary gain is **two additional disclosure-free ready tasks out of 24
attempts**, or 8.3 percentage points, below the required six. The package also
loses five ready tasks, exceeding the allowed loss of one. Missing-data cases
decreased, but that guardrail alone cannot make the package pass. Even the stricter
valid-and-accessible count improves by only three, not six. Unknowns are never
accepted as mathematical passes.

**Decision: stop this round; do not promote the package as a demonstrated
improvement.** Keep the versioned code and snapshots as an experimental variant
and the negative result as research evidence. The current fresh-brief default is
still v2; retaining it in code is not evidence-backed promotion and must be
identified as experimental in subsequent runs. No second round, new-topic sweep,
or student simulation was started. A later default/promotion decision should
follow a separately approved experiment, not an automatic tuning cycle.

The topic breakdown shows why an overall percentage alone is insufficient:

| Target | Old ready / disclosure-free | Changed ready / disclosure-free |
|---|---:|---:|
| Area/perimeter | 3 / 3 | 3 / 2 |
| Fraction division | 2 / 2 | 1 / 1 |
| Fraction equivalence | 3 / 1 | 2 / 2 |
| Volume/surface material | 3 / 1 | 2 / 2 |
| Feasible choices with inequalities | 3 / 3 | 3 / 3 |
| Equally likely basic outcomes | 3 / 0 | 2 / 1 |
| Combined means | 3 / 2 | 3 / 2 |
| Association/causation | 3 / 0 | 2 / 1 |

Each cell is out of three attempts. These are already inspected development
topics, not independent transfer or held-out results.

**Educational/design findings from traces, after task reading:**

1. **Internal fields alone do not separate student-facing meaning.** All four
   remaining disclosures in changed ready tasks were already present in the
   selected brief: the garden goal says areas and perimeters can differ; the
   combined-mean goal requires checkable use of both group sizes; the dice goal
   prescribes a complete equally likely sample space; the phone-use question
   requires a different causal explanation. The selector accepted them despite
   the new criteria. This localizes remaining defects to proposal/selection rather
   than a newly invented writer leak. The package cannot isolate which component
   affected the rates.
2. **A stricter selector can reject useful support, not just giveaways.** Four
   changed stops have explicit method/conclusion demands in their proposals
   (sample space, equal-volume unequal-surface boxes, equivalent-partition
   construction, and competing causal explanations). Two fraction-division
   stops are more contestable: the selector rejects conditional wording such as
   "including any fractional final band" and permission to use partial scoops.
   Under our predefined reading, permitting partial units clarifies the requested
   measurement rather than prescribing invert-and-multiply. The selector calls
   this the key correction, while the supplied target emphasizes measuring copies
   of a fractional unit. This is an observed disagreement between the generation
   gate and the task-review standard, not proof that every rejected task was bad.
   No rejected proposal was converted into a replacement success.
3. **Data roles need to match the student's action.** The two old fraction tasks
   with missing data refer to supplied strips or a supplied shaded panel while
   withholding all example quantities. A valid internal construction proves that
   some task could work; it does not supply an object that this final question
   requires. One task's measurements should be supplied; alternatively the task
   must explicitly let students choose the starting object. Neither repair was
   applied during this run. The earlier garden ambiguity also shows a mismatch:
   fixed-fencing and equal-area comparisons need distinct conditions stated to
   students, not only separate internal examples.
4. **Removing disclosures does not automatically create open mathematical work.**
   Every ready fraction-division task and combined-mean task remains a fixed
   calculation; the changed box task's last repetition supplies both candidate
   designs instead of letting students construct them. Feasible-set tasks require
   substantive boundary/completeness reasoning, but the whole-number variant can
   be solved by enumerating choices without learning a new inequality method.
   Target relevance, target necessity, consequential choices and actually distinct
   student approaches are different claims. No student approaches were collected.
5. **A software rejection is not a mathematical rejection.** The old arm's single
   blocked writer output failed a verbatim omission-quote check. It is retained
   as a failed output, not evidence that fraction division was infeasible.

**Implication, not another authorized run:** before another prompt experiment,
align the selector's distinction between necessary task definitions and actual
method/conclusion disclosures, using the recorded disagreement cases. Separately
test whether D2b labels supplied comparison objects versus student constructions
correctly. Do not bundle these instrument/data questions into an uncontrolled
second tuning round. Independent expert reading of both ready and rejected
designs would be more informative than maximizing another model score.

**Accounting and reproducibility.** Development used 240 requests: 126 old and
114 changed. Recorded development usage was 701,131 input and 422,863 output
tokens, including 257,818 reasoning tokens within output. Calibration plus
development used 260 of the allowed 468 requests, 756,813 input and 451,749 output
tokens, including 275,234 reasoning tokens. There were no API errors or unfinished
requests. Lower request usage in the changed arm partly reflects early stops,
not automatically greater efficiency. Provider prices remain unverified, so
monetary cost is unavailable. Every call stayed within nine requests per attempt,
6,000 completion tokens per response and the 120-second request setting.

The [frozen manifest and source snapshots](../../experiments/results/pf_d2a_discovery_20261011/round1/manifest.json),
[student-task gallery](../../experiments/results/pf_d2a_discovery_20261011/round1/gallery/development/tasks.html),
[all 48 assistant ratings](../../experiments/results/pf_d2a_discovery_20261011/round1/assistant_review.json),
and [computed counts and usage](../../experiments/results/pf_d2a_discovery_20261011/round1/comparison_report.json)
preserve the evidence. The [comparison runner](../../scripts/run_pf_d2a_comparison.py)
supports bounded resumes without replacements; the
[report command](../../scripts/report_pf_d2a_comparison.py) checks complete ratings,
stale task text, source hashes and usage before aggregation:

```bash
./.venv/bin/python -m scripts.report_pf_d2a_comparison \
  --output-dir experiments/results/pf_d2a_discovery_20261011/round1 \
  --review experiments/results/pf_d2a_discovery_20261011/round1/assistant_review.json
```

All 245 directly affected software tests and targeted Ruff passed. Frozen source
and input hashes were verified after the run. No full repository suite was run.
The result supports a limited task-design finding, not student productive failure,
learning improvement, or state-of-the-art performance.

#### October 11 fresh twenty-topic generation and direct inspection

The current prompts, including the upstream discovery-preserving alignment, were
used for fresh prior-resource mapping, design selection, checked data and writing.
The [topic configuration](../../experiments/configs/pf_topic_sweep_20261011.json)
covers twenty assistant-selected mathematics topics and hypothetical learners in
Grades 5--10. It excludes the three previous writer-calibration topics, but weighted
means appear in the existing design prompt's teaching example. This is development
coverage, **not** a random sample, preregistered holdout, or matched old/new comparison.

**Setup revealed a grounding limitation before the final sample.** Three preserved
live-retrieval attempts produced one task and two stops using nineteen model calls.
Fraction equivalence had no Grade 5 USA evidence and stopped before a model call.
Area/perimeter and compound probability retrieved unrelated Grade 6 statistics
material. The probability stop also exposed exact checking of a decimal
approximation to `1/6`; the underlying fair-dice counts for sums 4, 7 and 10 are
3, 6 and 3 out of 36, so this was not proof that the idea was invalid.
See the [setup inspection](../../experiments/results/pf_topic_sweep_20261011/setup_calibration_inspection.json).

The final configuration instead froze
[forty-eight verified official prerequisite excerpts](../../experiments/configs/pf_topic_prerequisites_20261011.json),
with explicit coverage gaps. Standards ground selected prerequisite candidates,
not all teacher stipulations or actual learner knowledge. D1 still mapped and
expanded them freshly; **live curriculum retrieval accuracy was not evaluated**.
The first three final attempts were checked before continuing the other seventeen
under exactly the same prompts and inputs. No final failures were replaced.

| Recorded outcome | Final sample |
|---|---|
| Topic attempts | 20, one per configured topic |
| Written student tasks | 19; completion is not PF validation |
| Preserved stop | 1: linear growth, during data checking |
| Directly inspected outcomes | All 20, including the stop |
| Model calls | 172: 69 prior-resource, 60 design, 24 data and 19 writing calls |
| Additional setup cost | 19 calls; 191 calls including setup and final generation |
| Call errors / provenance | No final API errors; all trace pairs and frozen source hashes verified |
| Software validation | 67 targeted sweep/diagnostic tests and targeted Ruff passed |

The 24 data calls include two extra proposal calls and two values-only repair calls.
These are internal attempts, not additional independent exercises.
The [manifest](../../experiments/results/pf_topic_sweep_20261011/final_20/manifest.json),
[exact task gallery](../../experiments/results/pf_topic_sweep_20261011/final_20/tasks.html)
and [per-topic assistant inspection](../../experiments/results/pf_topic_sweep_20261011/final_20/inspection.json)
retain all outcomes, upstream records, raw calls and findings. The gallery displays
all twenty topics and inspection notes. Thirty-nine quoted passages were checked
against their exact sources; independent arithmetic, enumeration and contextual
reading support the specific mathematical observations below.

**What the direct reading found:**

| Finding | Concrete evidence |
|---|---|
| Promising construction or explanation opportunities remain | Inequalities asks for all 19 feasible packet orders rather than one answer. Circle area permits a repeatable estimated method without supplying the formula. Association/causation asks for competing explanations and further evidence. These are design opportunities, not observed student approaches. |
| A construction can become verification | Fraction equivalence supplies `1/4` and `3/12`; area/perimeter supplies both successful rectangle pairs; boxes supplies the equal-volume pair. The selected geometry and box briefs asked students to design examples, but the final tasks ask them to verify prepared examples. |
| Methods or corrective criteria still leak | Fraction addition asks for the "shared unit"; right-triangle distance requires "squares built on them"; combined means requires showing how both group sizes were used. Withholding a formula does not withhold its characteristic move or error-correction criterion. |
| Mathematical/contextual acceptance is incomplete | The sampling task surveys 90 distinct subgroup-a students from a population containing only 60, without a repeated-response rule. The systems task calls `x,y` material masses that add without loss, but calls `3x+2y=12` their total amount; the algebraic solution has literal total mass `34/7`, not 12 kg. |
| Meaning and unsupported checks need separate inspection | Percentage change gives rate `0.25` without saying it means 25%. All five checker conditions are unknown because scalar expressions receive singleton lists. Independent arithmetic gives `100 -> 125 -> 93.75` and a restoring 20% decrease for the intended rate. The warning policy correctly permits continuation; it does not certify the wording. |
| Some predictions depend on unstated modeling assumptions | Three delivery-price rows fit `3.5x` and `3x+4`, predicting 21 and 22 at size 6 under those pricing models. The table alone cannot rule out other prices at an unlisted size. |
| Practical accessibility is not established | A 3-by-5 km floor and kilometer-radius planting beds are implausible. The circle task requires templates not attached to the text and roughly 2,827 grid cells for its largest disk; the scaling task has a thirteen-column table. |

**The stopped growth case is a condition-construction conflict.** Its selected brief
requires a price crossing beyond both quoted distances. D2b additionally demands
opposite cheaper plans at those same two quotes. For two distinct linear prices,
both cannot hold. The final values cross at 7.25 km between the 2 and 8 km quotes,
and the checker correctly rejects the supplied predicate. Values-only repair
cannot satisfy the conjunction; this does not invalidate the general teaching
direction or justify silently redesigning this frozen attempt.

**Meaningful handoff insight:** removing revealing labels is insufficient when
teacher-only successful constructions have already become mandatory numerical
inputs. Keeping those values can convert "construct" into "verify"; deleting them
indiscriminately could instead destroy solvability. This motivated identifying
student givens versus teacher verification constructions before writing and
preserving consequential student choices. No such change was implemented during
this sweep; the later eight-case handoff test above records it separately.
D2b's agreed warning policy remains unchanged.

These fresh results test the current upstream and writer prompts together, but
cannot establish causal improvement without a matched baseline. Assistant reading
is neither human expert rating nor student-response evidence. Distinct approaches,
productive failure and subsequent learning still require student trials.

#### October 10 implementation calibration

Development artifacts remain separate, without replacing the October 9 results:

- [v1](../../experiments/results/d2b_data_calibration_20261010_v1/) retained an API
  rejection because the new prompt omitted the word JSON required by JSON mode.
- [v2](../../experiments/results/d2b_data_calibration_20261010_v2/) produced two
  tasks from three fresh attempts. Consistency stopped on a named Boolean
  intermediate the calculator could not yet express, not a numerical failure.
- [v3](../../experiments/results/d2b_data_calibration_20261010_v3/) again produced
  two tasks from three fresh attempts: consistency and ratio. Speed stopped on an
  essential unit declaration represented only as model judgment. All three D2b
  source-integrity checks passed. Total model calls were four for speed, four for
  consistency and five for ratio, including brief selection and successful writing;
  D1 was reused, and the three-call D2b limit was respected.
- A separate [fixed-speed-brief replay](../../experiments/results/d2b_data_calibration_20261010_v4_fixed_speed/result.json)
  after adding read-only unit checks produced a ready task in one D2b proposal
  and one writer call, with source integrity verified. It reused the stopped v3
  brief and generated new data; it is not a third fresh success in the v3 run.
  Whole-journey speed is `11/4` km/h, versus the unweighted stage-speed mean
  `5/2` km/h. The student text preserves the generated distances and times.

These are topic-diverse development checks with frozen, Learning-Commons-enabled
D1 context and the same model, not a held-out comparison or evidence of better
PF learning. The outputs still require substantive design and student-response
evaluation. Formula correctness does not establish correct interpretation of
every plain-language condition.

Focused software validation passed 621 tests, plus targeted Ruff and compilation.
An additional historical writer-only replay suite has six failures and two
passes: stored September contexts omit the `prior_contrast` field that unchanged
current writer-context code includes. That historical context mismatch was
identified and left untouched rather than altering the saved experiments.

#### October 10 saved-input replay validation

The [validation summary](../../experiments/results/d2b_framework_replays_20261010/summary.json)
records an additional iteration without overwriting v1--v4. The
[offline replay utility](../../scripts/replay_pf_design_data.py) recalculates saved
conditions and feeds recorded replies through the current loop without model
calls. It can also save explicitly labelled, altered-number inputs with
`--stress`; their offline repair uses mock replies, not model evidence.

Across eight saved results, six proposals passed current exact checks, one
retained `review_needed`, and one had no saved D2b response after its API failure.
The previously unsupported v2 consistency proposal now passes unchanged.
The v3 speed proposal remained under review under the earlier policy: adding
unit-check capability did not silently replace its saved model-only condition.
Six controlled numerical
perturbations passed after mock restoration, with conditions and units unchanged.

Five separate CLI continuations used frozen cases, prior context and selected
briefs:

| Saved input | D2b calls | Writer calls | Outcome |
|---|---:|---:|---|
| v2 consistency, previously unsupported | 0 | 1 | Ready task from unchanged numbers |
| v3 ratio, previously accepted | 0 | 1 | Ready task from unchanged numbers |
| v1 speed, API failure before data | 1 proposal | 1 | Ready task from new data for the saved brief |
| Deliberately altered v4 speed data | 1 repair | 1 | Ready task after numbers-only repair |
| v3 speed, model-only essential condition | 0 | 0 | Expected review stop; no task |

Thus four tasks were produced from five continuations using six total model
calls. In the live repair, the deliberately invalid distances `[-3, 9]` km became
`[3, 8]` km; times remained `[1, 3]` h. The model did not merely restore the old
`[2, 9]` km data. All frozen conditions still held: whole-journey speed is `11/4`
km/h, while the unweighted stage-speed mean is `17/6` km/h. This demonstrates a
live numerical repair of controlled input, not a naturally occurring proposal
failure or superiority over one-shot generation.

Replay testing exposed and fixed routing of a saved `design_data: null` run to
the legacy planner, missing support for the existing `d2` result wrapper, and
loss of earlier attempt records in resumed output. Regression tests cover direct,
diagnostic and benchmark wrappers, ordinary resume, explicit replanning and
`--no-fill`. Initial failed values and previous histories remain inspectable.

All five continuations preserved source/input hashes, the selected brief, and
prior context; their checks were independently recalculated. Case-specific
checks confirmed that all four student texts preserve the final given numbers
and units. These checks are not a general guarantee of prose fidelity or PF
quality. The current focused suite passed 642 tests, with targeted Ruff and
compilation passing; the full suite was not run. The separate historical
writer-only context mismatch above remains outside this validation scope.

To replay other saved results without model calls:

```bash
./.venv/bin/python scripts/replay_pf_design_data.py SAVED_RESULT_OR_DIRECTORY \
  --output NEW_SUMMARY.json --stress
```

Use a new output path; the utility refuses to overwrite replay artifacts.

#### October 10 fresh direct comparison after design-guidance refinement

The design-brief prompts now ask whether the simplest permitted familiar
construction already settles the whole goal, distinguish mathematical ideas
from display choices, and reserve numerical requirements for value-dependent
relationships. Direct generation received the same opportunity guidance and
self-authored weighted-average example. No expert task statement, numbers, or
solution was supplied to generation.

[run_pf_fresh_comparison.py](../../scripts/run_pf_fresh_comparison.py) reuses the
existing diagnostic worker, freezes the expert-direction pilot's teacher
repertoire, and preserves all traces, prompt snapshots and failures. This tests
fresh D2a-to-D3 generation, not fresh D1 grounding or Learning Commons retrieval.
The [run summary](../../experiments/results/pf_fresh_design_comparison_20261010/summary.json)
keeps two three-topic calibrations separate from two fresh repetitions per topic:

| Phase | Direct delivered / attempted | Pipeline delivered / attempted | Model calls |
|---|---:|---:|---:|
| Initial calibration | 3/3 | 2/3 | 18 |
| Revised calibration | 3/3 | 3/3 | 18 |
| Frozen fresh repetitions | 6/6 | 5/6 | 36 |

All phases recorded zero API errors. The fresh pipeline had one numerical repair
and one fair-division `data_review_needed` stop under the then-current policy:
continuous divisibility/no-loss was supplied as an essential noncomputed condition.
That historical stop is not proof of an
impossible task. These are development-topic repetitions, not held-out topics,
budget-matched comparisons, or a causal prompt-ablation experiment.

The [annotated side-by-side report](../../experiments/results/pf_fresh_design_comparison_20261010/fresh/side_by_side.html)
contains an AI qualitative inspection of every fresh outcome, including the stop.
[Independent mathematics](../../experiments/results/pf_fresh_design_comparison_20261010/fresh/independent_math.json)
uses exact fractions and exhaustive discrete allocation enumeration on manually
transcribed final-text inputs, separately from the generated plans.

- **Consistency:** all four fresh tasks have equal within-task means and ranges
  but different spread. Both methods now support a plausible measure-invention
  opportunity; both also disclose or direct attention to the familiar-summary
  obstacle. Absolute-deviation measures remain valid, not proof of variance
  invention. The Loibl reference is a design reconstruction without a complete
  original numerical table, not the separate Kapur (2015) StratL task.
- **Speed:** all four tasks remain fixed-rate reporting/comparison exercises,
  unlike the expert task's consequential unknown handover point. Only the first
  direct task reverses the unweighted and whole-journey rankings; the first
  pipeline task resolves a tie. Different incorrect rates without a reversed
  ranking can still support conceptual comparison, but do not establish PF.
- **Fair division:** both direct tasks have feasible discrete assignments, but
  use indivisible items rather than the continuous expert setting. The delivered
  pipeline task supplies whole-region valuations without a numerical model for
  partial regions. Under an additional proportional-subdivision assumption,
  an equal fraction of every region already guarantees a fair share. Unequal
  valuations alone do not prove the intended obstruction.

No general pipeline PF-quality advantage is established. Remaining work is
consequential speed-task construction, less pre-emptive consistency wording,
explicit fair-division permissions/valuation assumptions, and evaluation of
actual student attempts. No simulated or real student outcomes were collected.
The final targeted validation passed 250 software tests, plus Ruff and
compilation; the full suite was not run.

### Historical skeleton and mathematical-plan route

The following skeleton/plan account describes the previous route and historical
experiments; it is not an additional requirement of the current default.

A skeleton must satisfy all five requirements:

| Requirement | Meaning |
|---|---|
| Slot-only | quantities + question; no names, setting, or dialogue |
| At least one prior resource can activate | a listed prior resource has objects it can run on |
| Target is needed | the task leaves a meaningful question for the new idea without making every familiar route fail |
| Searchable | the slots are concrete enough that numbers can be substituted later |
| Held-out evaluation | the expert PF task is ground truth, not an input |

The first four are acceptance tests for a generated skeleton. The fifth is an
evaluation rule: Kapur, Loibl, and Kerrigan are not retrieved or copied.

Do not build the situation greedily from one seed method and hope the others
attach. Propose it jointly over the full D1 context. The unit being compared is
a concrete student approach, not a resource label:

```text
historical proposal calls: target + full prior-resource context + mathematical references
    -> K pedagogical design briefs, without typed quantity metadata

one judge pass over all candidates:
    recommend one brief (or none)
    explain the useful comparison between approaches
    propose number requirements with their educational purpose

translate the selected brief's quantities:
    preserve its question, approaches, and original numerical requirements

pass the encoded design to the mathematical planner:
    preserve the whole goal and conditions for later number filling
```

An approach that can succeed does not automatically make a task ordinary
practice. The compact judge compares the learning opportunities rather than
ranking the number of approach identifiers. The older activation count remains
in saved winner records for compatibility; it is not evidence of student diversity.

Brief search uses [design_brief_stage.py](../../scripts/design_brief_stage.py),
the [brief contract](../../src/generation/design_briefs.py), and
[brief prompts](../../src/generation/prompts/design_briefs.yaml).
The encoded skeleton and existing mathematical plan still use
[situation_skeletons.py](../../src/generation/situation_skeletons.py).
The selected conditions are design proposals, not yet verified constraints.
Legacy typed proposals and per-candidate judge payloads remain available for
explicit historical protocols. In the earlier typed-skeleton experiments,
GPT-5.6-luna converged on a
two-plan "which journey is faster overall" comparison family; GPT-4.1-mini
produced a thinner two-segment drill family.

### October 9 design-brief handoff (historical default)

The October 9 route separated pedagogical design from technical quantity encoding:

```text
target + D1 prior resources + separately labelled mathematical references
    -> D2a: propose short design briefs -> select one brief (or none)
    -> D2b: encode its quantities -> existing plan/review -> fill/check
    -> D3: write the task
```

The initial implementation was opt-in. On October 9 it became the default for
fresh situation, diagnostic, and paper-benchmark generation. Brief selection
remains the default, with no `--design-brief` flag needed or accepted, but the
October 10 data/check/repair loop replaced this section's downstream
translation/plan/review/fill handoff. Explicit legacy API/config settings remain
available for historical protocols, and saved-winner replanning preserves the
stored design rather than regenerating a brief. Learning Commons references
are preserved when present in D1; they are mathematical design context, not
additional assumed student knowledge.

The [brief contract](../../src/generation/design_briefs.py) contains the whole
goal, situation and allowed actions, method-open student question, resource-linked
first actions, a plausible successful route, learning opportunity, and essential
number requirements. The successful route is a hypothesis, not proof of
feasibility. The [new prompts](../../src/generation/prompts/design_briefs.yaml)
include a self-authored example, not a held-out expert task. Proposal and
selection retain the published rubric anchors but do not receive the executable
checker or typed-quantity schema.

The [handoff](../../scripts/design_brief_stage.py) adds one quantity-translation
generation call before the existing mathematical planner, not another judging
stage. Code copies the selected question, approaches, and original requirements;
the translator supplies quantities and an optional operational prior-contrast
intent when the learning opportunity depends on that numerical comparison.
It does not supply formulas or rewrite the goal. The original brief remains attached
to the winner through saving, replanning, review, repair, filling, and writing.
The existing meaning review checks the translation against the whole brief.
Unsupported mathematics stops explicitly rather than shrinking the goal.

Translation instantiates one concrete task. Choosing unspecified counts or
admissible positive inputs is not evidence of support for arbitrary-length or
signed-input families. An equivalent numerical comparison does not establish
an uncomputed score, its units, or an entire allocation procedure.

Both generation CLIs used this route automatically at the time. Omitted
paper-benchmark settings also defaulted to it; source snapshots and frozen settings
record each run's effective route. The following command now uses current D2b,
not the October 9 handoff; historical reproduction requires the saved source
snapshot and effective settings. Historical outputs are not overwritten or
relabeled.

```bash
./.venv/bin/python scripts/run_pf_diagnostic.py \
  --cases kapur_average_speed_g7_singapore --model luna \
  --proposal-k 1 --max-workers 1 --learning-commons \
  --output experiments/results/design_brief_new_run
```

Initial development artifacts are kept separately under
`experiments/results/design_brief_calibration_20261009_v1`, `_v2`, and `_v3`.
The first two v1 proposals were valid briefs, but translation over-rejected
unspecified cardinality and optional target operations. General encoding guidance
was clarified; fresh v2 speed and spread briefs translated, while fractions
stopped because zero was permitted in the count domain. A separately saved,
fixed-brief translation replay after distinguishing permitted from required
values translated that same fraction brief. These are implementation/calibration
results, not evidence of superiority to direct generation or student learning.
The first fresh full three-topic continuation used frozen Learning Commons D1
inputs and translated all three briefs, but all three stopped at the existing
meaning review. Diagnoses included a missing numerical-contrast handoff, omitted
range conditions, vague arithmetic-burden conditions, and a fraction task requiring
more independently checked decisions than the interface supports. Subsequent
handoff guidance records applicable contrast intent during technical encoding
and asks for specific numerical relationships rather than vague promises.
The stopped run is retained unchanged; no review gate was removed.

Further live trials exposed two interface defects: candidate approaches needed
explicit IDs for selection, and the translator was given a whole-skeleton schema
that invited it to regenerate approaches and requirements. Candidates now carry
stable approach IDs, and translation receives quantity-only metadata derived
from the same authoritative schema. New calls have distinct trace-stage labels.

The final pre-default calibration [verification summary](../../experiments/results/design_brief_calibration_20261009_v5/verification_summary.json)
records **one written task from two fresh full runs**. Both produced valid briefs
and quantity translations. The ratio task passed exact numerical replay
(`5 / (5 + 3) = 5/8`) but remains guided and is not demonstrated PF. Speed stopped
on review-output coverage and repair-preservation fields; that is not evidence
that its mathematics is invalid. A separate fixed spread-brief replay remained
unsupported because that brief explicitly requested a numerical standard
deviation result, rather than merely a ranking representable through variance.
It is not counted as another fresh full attempt.

All final full-run source-integrity checks passed, and all earlier variants and
stops remain preserved. The focused software validation passed 332 tests.
There is no independent human rating, simulated-student comparison, or evidence
of superiority to one-shot generation in this calibration.

### Flag-free default generation examples (October 9)

The [exact side-by-side outputs](../../experiments/results/pf_default_brief_examples_20261009/side_by_side.html)
compare fresh default-pipeline and direct single-call attempts on speed, spread,
and part-to-whole ratio. Both methods receive the same frozen D1 learner context,
selected Learning Commons descriptions, model, and self-authored design example.
Direct generation shares the design principles but requests a student exercise,
not intermediate artifacts. The pipeline proposes two briefs per topic; this is
not a budget-matched or repeated-trial comparison.

Direct generation produced **3/3 exercises**; default pipeline produced **0/3**,
despite all six brief proposals parsing successfully. Speed stopped on a missing
central numerical-contrast record. Spread stopped when the translated goal
required a numerical standard deviation rather than an open invented measure.
Ratio stopped on a general enlargement condition that the review could not
certify from bounded numerical checks. These are recorded stopping diagnoses,
not proof that every proposed task is mathematically invalid or that no faithful
encoding is possible.

The [output-specific arithmetic inspection](../../experiments/results/pf_default_brief_examples_20261009/inspection.json)
checks the three direct tasks. Speed has overall rates 16 and 18 km/h, although
those are implausible ordinary school walking speeds. The spread task has twelve
observations per printer: both means are 100, ranges are 12, and median-of-halves
quartiles are 98 and 102; variances differ at 31/3 and 34/3. It offers a plausible
invention opportunity beyond the supplied summaries. Ratio correctly gives
40 green and 24 white tiles, but supplies the correct fraction among competing
claims and is guided. These are assistant design impressions, not human ratings
or observed student approaches.

All three pipeline source-integrity checks passed. Software validation passed
339 focused tests after changing the default and removing the CLI flag.
This sample shows no pipeline improvement; it exposes ongoing goal-to-plan and
review bottlenecks. No additional prompt tuning or gate relaxation was used to
replace the stopped attempts.

The `falls_short_because` field is a design specification for those later
checks. It does not mean that every recommended resource must be broken
simultaneously.

There are two legitimate task shapes:

### Solvable but difficult

Break attractive shortcuts, but leave at least one robust route open.

Kapur's average-speed task does this:

```text
ratio shortcut       -> fails because walking and biking ratios differ
LCM/HCF shortcut     -> stalls because the chosen unit does not tile the distance
algebra attempt      -> may be beyond the learners' current skill
trial and error      -> remains possible, although inefficient
```

### Invention task

Make the familiar measures unable to distinguish the cases, so students must
invent a new measure. Loibl's consistency task uses the same mean and range
for all players; mean and range therefore fail equally, while a measure using
the distribution of all values can be invented.

The rule is:

> Challenge the particular shortcuts or summaries the task is designed to
> examine, without requiring every familiar approach to fail. In an invention
> task, selected summaries may tie while graphical, qualitative, and partial
> approaches remain useful.

#### Historical mathematical-plan route

The same skeleton admits many number sets, and the numbers decide which
contrast fires. The previous D2b used three substeps:

1. **Freeze a mathematical plan.** New plans use `math-plan/v2`: given/derived/
   unknown quantities remain in the selected skeleton, while the plan records
   only the executable target, answer rule (`largest`, `smallest`, `equal`, or
   `scalar`), units, and essential numerical constraints. Proposed approaches
   remain plain-language hypotheses; when selection names one central numerical
   prior move as checkable, the plan may add its single formula-bearing
   `prior_contrast` (see below).
   Any given quantity with `role="list"` must declare a fixed positive integer
   `list_length` in JSON; arbitrary or unspecified list lengths are refused during
   fresh planning. Fresh given quantities must explicitly declare `value_domain`
   as `"positive"` or `"positive_integer"`. Historical v1 plans retain their
   prior-path contract and older artifacts remain readable, but automatic fresh
   execution or replanning refuses missing list lengths or invalid domains.
2. **Review meaning before values.** An LLM review receives the grade and full
   assumed prior-resource context and checks whether the question, target,
   approaches, and original and judge-proposed requirements agree.
   Every requirement has a stable ID within the selected design (`original_0`,
   `judge_0`, etc.). The reviewer must account for every ID. In addition to
   numerical plan constraints, requirement coverage can cite relevant enforced
   metadata facts (`quantity_fact_refs` pointing to `unit`, `list_length`, or
   `value_domain` of declared given quantities) without redundant arithmetic
   tautologies. `answer_rule_fact_refs: ["require_unique"]` can cite enforced
   largest/smallest uniqueness, not a named winner. `plan_fact_refs` can cite
   non-empty serialized `quantities`, `target`, or `answer_rule` sections for
   value-independent declarations and definitions. Input counts must consider
   only quantities with `value_source="given"`. These plan references do not
   replace constraints on sampled numbers; their existence is checked, but their
   relevance remains a model judgment. All three reference types are optional
   and valid only for numerical coverage. Missing, duplicate,
   invalid, or unresolved coverage blocks filling in fresh and resumed runs.
   Qualitative requirements need an explanation and remain explicitly unverified;
   they must not be used to disguise an unimplemented numerical condition.
   The requirement-to-constraint and fact mapping remains an LLM semantic judgment,
   not a mathematical proof.
3. **Search only over values.** `FILL_SKELETON` returns values for given slots.
   It receives the original design context directly: the selection reason,
   judge-selected approaches, main concern, and every requirement with its
   educational purpose. This context is preserved through saving, resuming,
   and retries; filling does not depend solely on the planner's translation.
   The deterministic checker executes numerical expressions with exact SymPy
   arithmetic, validates constraints and labels, and compares the declared
   answer—not arbitrary maxima and minima.

Proposal, selection, planning, review, and filling now receive the same
[checker capability contract](../../src/generation/fill_check.py), rendered from
the evaluator's operator/function registries and allowed domains and answer rules.
It describes given-only bindings, positive inputs, exact list lengths, permitted
arithmetic, and unsupported syntax. Proposal and selection use this to judge
whether the **later** numerical plan can represent the intended task; they do not
require that later plan's fields or formulas at their own stage. Missing a native
function does not establish impossibility: equivalent supported compositions such
as `x*x` remain valid even though `x**2` is rejected. This is guidance, not a new
solver or proof that the model will interpret the contract correctly. Essential
requirements must not be dropped to obtain a passing result.

For the runner, an accepted fill therefore means: the meaning review passed and
the declared target and applicable numerical-contrast contracts are satisfied.
It does **not** mean that students will use the approaches or that they will learn.
Unsupported target mathematics, malformed formulas, missing or extra labels,
invalid constraints, and unresolved reviews stop automatic filling.

#### Optional selected numerical prior contrast

The compact selector in
[situation_skeletons.yaml](../../src/generation/prompts/situation_skeletons.yaml)
records `prior_contrast: null` unless one operational,
tempting prior move is central to the chosen design. If selected, it names the
candidate's exact `approach_id`, describes the concrete operation, and classifies
it as `numerical`, `qualitative`, or `unsupported`—not as a generic misconception.
A taught skill can be used correctly yet remain insufficient; that is not itself
a misconception. This contrast check is optional, not a universal PF criterion.
For a numerical move, `math-plan/v2` can carry one `prior_contrast` formula for
each target label for a unique `largest`/`smallest` target, or a separately
labeled path for an `equal` target. For the latter, each path needs at least two
results; labels may differ because the methods can make different comparisons.
The selector must state opposite `expected_target_equal` and
`expected_prior_equal` outcomes when it selects this equality contrast. The exact
checker evaluates all listed results in each path and verifies both declared
outcomes; it does not reduce a path to one derived scalar. The planner's semantic
review checks whether the formulas match the described move, but that alignment
remains a model judgment.

For example, attempts `[10, 20, 30]` and makes `[4, 10, 16]` have equal
consecutive input steps. The target unit rates are `2/5`, `1/2`, and `8/15`
(not all equal); the tempting additive move compares consecutive make increases
`6` and `6` (equal). The selected outcomes are therefore target `false`, prior
`true`. The checker evaluates all three rates and both increments exactly. This
is an arithmetic illustration, not model or student evidence. The reverse pair
of outcomes is also permitted when that is what the selected design specifies
and the values satisfy it. The existing unique-winner behavior for `largest` and
`smallest` remains: a matching prior decision is rejected and a prior tie differs.

Qualitative or unsupported selected moves are recorded as **unverified** in the
fill record, never as checked; their formulas are not invented. Designs with no
selected prior contrast retain the prior target-and-constraints behavior. The
checker verifies arithmetic and selected equality outcomes (or decision
disagreement for `largest`/`smallest`), not that the formulas represent the
described student move, that students will use either approach, or that the
exercise causes productive failure. Scalar targets, fewer than two comparisons
on either equality path, and formulas outside the expression language cannot
support a checked equality contrast; a numerical move that cannot be represented
must remain unsupported or unverified, not be described as checked. This change
has software regression coverage, including the three-rate/two-increment example
and selected-outcome rejection. A separate exploratory two-case run used
`gpt-4.1-mini`, `k=1`, and expert resources; its outputs are in the fresh
[calibration directory](../../experiments/results/situation_skeletons/compatibility_calibration_20260925_0036/).
Neither case produced a ready task. Kapur average speed had one valid proposal,
but the judge response was rejected because it supplied approaches while
recommending no candidate. Loibl variance selected candidate 0, but both plans
failed structure validation: the first targeted means and used unsupported
`max`/`min`; the second still targeted means and its prior-contrast labels did
not match the target labels. Neither run reached filling or writing. The records
contain two proposal, two selection, and two planning responses, but no usage or
cost metadata, so spend is unavailable.

The benchmark runner now has an opt-in `--only-condition PIPELINE` selector.
It retains the frozen four-condition manifest schedule, marks the run
`incomplete`/`not_a_benchmark`, and skips judging and comparisons while other
conditions remain unattempted; default full-run behavior is unchanged. One fresh
attempt of the saved Grade 7 case `rahimi_ratio_g7_usa_basketball` (7.RP.A.2;
model selector `luna`, GPT-5.6-Luna) was run with `--limit-per-condition 1`.
The [calibration output](../../experiments/results/pf_paper_benchmark/20260925_luna_pipeline_only_7rpa2_calibration/)
retains the full 120-slot schedule: one PIPELINE attempt was attempted and ready,
119 slots remain pending, and the manifest status is `incomplete` with
`benchmark_status: not_a_benchmark`. D1 completed in 3 model calls; D2/D3
completed in 11, with an accepted plan review, accepted fill, and ready task.

The selected prior contrast was null, so no expected equality outcomes or
prior-contrast decision were checked. The equal-rule target compared rates
`1/2`, `1/2`, and `2/3` from attempts `[10, 20, 30]` and makes `[5, 10, 20]`;
the exact checker accepted the values, which are not all equal. The selected
skeleton question itself named a “shared multiplier,” so ready status is not
evidence of target-undisclosed wording or PF quality. All 15 recorded source
hashes matched after the run; the [manifest](../../experiments/results/pf_paper_benchmark/20260925_luna_pipeline_only_7rpa2_calibration/manifest.json),
[source hashes](../../experiments/results/pf_paper_benchmark/20260925_luna_pipeline_only_7rpa2_calibration/source_hashes.json),
and [PIPELINE-001 traces](../../experiments/results/pf_paper_benchmark/20260925_luna_pipeline_only_7rpa2_calibration/attempts/PIPELINE/001/)
are retained. The pipeline trace contains no usage/cost metadata, so spend is
unavailable. No other benchmark conditions were run or judged, and this single
case is not a benchmark comparison or quality win.

After that run, the proposal, selector, reviewer, and writer prompts were
reconciled: student questions must preserve a meaningful decision or
interpretation without naming the target method; the teacher-facing plan and
answer rule retain its exact mathematics. A selector that makes a specific prior
move central must record it as numerical, qualitative, or unsupported; null
selection cannot be paired with a claim that a particular contrast is relied on.
This remains optional, and qualitative/unsupported moves are not reported as
checked.

A fresh bounded prompt pilot used `gpt-5.6-luna`, `k=1`, on the saved Grade 7
7.RP.A.2 case and one non-basketball concept. For Grade 7, the derived one-sample
config changed neither the frozen historical config nor its artifacts. The
[new PIPELINE-only output](../../experiments/results/pf_prompt_open_pilot_20260925/grade7_pipeline/)
retains the 120-slot manifest: 1/1 selected attempt was ready, 119 remain
pending, and the run is `incomplete`/`not_a_benchmark`. All nine traced model
calls finished without API errors (three D1, six D2/D3); the shell exits 1
because the intentionally partial schedule is incomplete. The selection now
records `compare_additive_changes` as a qualitative prior contrast, but its
expected equality outcomes are null and the plan has no numerical contrast.
Filling checked only the target rates `1/2`, `1/2`, and `2/5` from attempts
`[10, 20, 30]` and makes `[5, 10, 12]`; they are not all equal. The selected
subtraction move is explicitly unverified. The final question asks whether the
coach should use one shared prediction rule or treat records separately; it
does not name a rate, multiplier, or proportionality method, though “shared
prediction rule” remains broad wording. Thus this run did not exercise the
runtime `equal`-contrast path; that path has regression tests, not pilot evidence.
The [manifest](../../experiments/results/pf_prompt_open_pilot_20260925/grade7_pipeline/manifest.json),
[attempt record](../../experiments/results/pf_prompt_open_pilot_20260925/grade7_pipeline/attempts/PIPELINE/001/result.json),
and [full trace](../../experiments/results/pf_prompt_open_pilot_20260925/grade7_pipeline/attempts/PIPELINE/001/model_trace.jsonl)
are retained; all 15 recorded source hashes match the current files.

The separate
[Loibl variance run](../../experiments/results/pf_prompt_open_pilot_20260925/loibl_variance_pipeline.json)
also reached ready with accepted review and fill. It used the same model and
`k=1` through `run_situation_skeletons.py --use-expert-resources`, not the
benchmark runner or grounded D1 path. Six calls are recoverable from its
stage-by-stage raw responses; usage and cost were not captured. Its selected
numerical `compare_ranges` contrast was checked: both ranges are `9`, while the
target variances are `53/4` and `41/4`, so the second data set has the smaller
variance. The final question asks students to compare spread using all four
observations without naming variance or standard deviation. A separate
[source-hash snapshot](../../experiments/results/pf_prompt_open_pilot_20260925/loibl_source_hashes.json)
records its case, prompt, runner, and checker inputs; shared prompt and code
hashes match the Grade 7 manifest.

These are two single-sample workflow checks, not evidence that student approaches
diversified or that PF quality improved. The Grade 7 run selected a qualitative,
unverified contrast; the non-basketball run demonstrates one accepted numerical
contrast but not the `equal` answer-rule path. No human-student validation,
benchmark comparison, or cost estimate was produced. Historical benchmark
artifacts and findings remain unchanged.

#### Follow-up: checked-claim scope and additive comparisons

A later review corrected the earlier Grade 7 selection's capability rationale:
the exact checker can compare three per-row rates with two consecutive output
changes under an `equal` answer rule. For a repeated-change interpretation, the
design needs at least three paired rows and equal input intervals; the plan must
encode the interval condition. The previous pilot's actual values, attempts
`[10, 20, 30]` and makes `[5, 10, 12]`, yield rates `[1/2, 1/2, 2/5]` and
consecutive changes `[5, 2]`. Both paths are not-all-equal, so that particular
fill does not produce the selected opposite equality outcomes. Its historical
qualitative intent was never checked; no saved pilot output was changed.

The prompts now distinguish an exactly checkable arithmetic contrast from an
interpretive judgment, and require the question's factual scope to match its
answer rule. In particular, a generic claim that one rule fits finite pairs
exceeds a same-rate check; a familiar contextual unit/property can bound the
claim without giving a calculation procedure. Review is instructed to apply a
semantic counterexample test, not a lexical filter.

One fresh two-topic compatibility run used `gpt-5.6-luna`, `k=1` per case, with
new outputs under
[the pilot directory](../../experiments/results/pf_prompt_scope_pilot_20260925/).
The saved Grade 7 case was attempted once and ready. All ten traced calls
finished without API errors (three D1, seven D2/D3); the full 120-slot
PIPELINE-only manifest remains `incomplete`/`not_a_benchmark` with 119 slots
pending, so the command exits 1 for the intentionally partial schedule. The
question now asks whether the same made-shots-per-attempt pace describes all
three records and what that supports for a coach's decision; this is scoped to
the checked equal-rate property without prescribing its calculation. The checker
accepted rates `[1/2, 1/2, 2/5]`. However, selection left `prior_contrast` null
while its reason still mentions comparing rate and additive-change evidence.
No prior path or qualitative intent was recorded, so this is not counted as a
checked contrast.

The separate
[variance run](../../experiments/results/pf_prompt_scope_pilot_20260925/loibl_variance_pipeline.json)
was also ready. It used the same model and `k=1` through
`run_situation_skeletons.py --use-expert-resources`, not grounded D1. The final
question scopes the decision to which series is less spread over the four
observations without naming a variance procedure; the target variances were
`17/2` and `25/2`. The plan exactly constrained equal means, equal ranges, and
unequal variances, and filling accepted those constraints. Yet it also left
`prior_contrast` null while the selection rationale relied on the equal-range
design; no selected prior path was evaluated. Across these two fresh attempts,
there were zero selected numerical prior paths, zero explicit qualitative
intents, and two null selections. The Loibl range equality was checked as a plan
constraint, not as a selected prior-contrast record. Thus the scoped questions
were produced, but model compliance with explicit contrast selection remains
unverified.

The [Grade 7 trace](../../experiments/results/pf_prompt_scope_pilot_20260925/grade7_pipeline/attempts/PIPELINE/001/model_trace.jsonl)
and 15-source manifest hashes are retained; all 15 matched the current files.
The [Loibl source snapshot](../../experiments/results/pf_prompt_scope_pilot_20260925/loibl_source_hashes.json)
records its inputs, with shared prompt and code hashes matching the Grade 7
manifest. Usage/cost was unavailable for both cases. These runs did not test
whether students use distinct approaches, whether the model reviewer rejects
the earlier broad wording, or whether PF quality improves. No full benchmark or
new judge comparison was run; prior pilot artifacts remain untouched.

#### Proposal/selection feasibility and one fresh calibration

The saved Grade 7 selector trace
[from the preceding pilot](../../experiments/results/pf_prompt_scope_pilot_20260925/grade7_pipeline/attempts/PIPELINE/001/result.json)
made a model-generated claim that equal attempt steps plus equal made-shot steps
would effectively coincide with equal rates for the first two records. That is
not a general arithmetic fact and is not evidence about student misconceptions:
inputs `[10, 20, 30]` and outputs `[4, 10, 16]` have equal steps but rates
`2/5`, `1/2`, and `8/15`. A different claim is true: if a design additionally
requires the first two rates to be equal, equal input steps and equal output
steps force the third rate to be equal too. The actual upstream blocker was the
proposal's fixed “first two rates equal, third differs” condition when paired
with the intended equal-step contrast.

Proposal and selection prompts now invite, but do not require, a concrete D1
operation that can be a plausible yet incomplete start. For a central numerical
contrast they ask for jointly feasible conditions; the proportionality example
allows equal input/output increments with unequal rates, without making that
pattern universal. Selection is instructed to reject incompatible fixed
conditions rather than nulling a needed contrast or weakening them. Regression
tests cover the arithmetic counterexample, the incompatible combined pattern,
and these prompt contracts.

One fresh `gpt-5.6-luna`, `k=1` two-topic run is saved in
[a new output directory](../../experiments/results/pf_prompt_proposal_feasibility_20260925/).
Grade 7 was **ready (1/1)** after 11 traced calls (3 D1, 8 D2/D3; no API errors).
Selection chose numerical `compare_successive_changes`; the checker accepted
target rates `3/10`, `7/20`, `11/30` (not all equal) and prior changes `4`, `4`
(equal), with selected outcomes false/true. The question asks whether one
made-shots-per-attempt pace describes the records, not for a calculation
procedure. The frozen four-condition manifest remains incomplete/not a benchmark
with 119 pending slots; no usage/cost metadata was available.

The variance case was **not ready (0/1)**. Its selector left `prior_contrast`
null while its rationale relied on equal-mean/equal-range summaries versus
variance. The plan reviewer flagged that inconsistency; a joint repair did not
pass review, so no filling or writing occurred. The proposed question asks which
observation set is more consistent, but it was not emitted as a student task.
Across the two attempts there was one checked numerical contrast, no explicit
qualitative intent, and one null selection that was blocked before filling.
Thus the Grade 7 pattern is a positive mechanical calibration, while selection
compliance did not generalize in this small variance run.

The
[Grade 7 trace and manifest](../../experiments/results/pf_prompt_proposal_feasibility_20260925/grade7_pipeline/)
record 15/15 matching source hashes. The
[variance result](../../experiments/results/pf_prompt_proposal_feasibility_20260925/loibl_variance_pipeline.json)
and [source snapshot](../../experiments/results/pf_prompt_proposal_feasibility_20260925/loibl_source_hashes.json)
retain its blocked stages and inputs; all six source hashes match current files,
including the five shared with Grade 7. The variance runner recorded eight model
responses; usage/cost was unavailable. No benchmark was run and no student
behavior or quality improvement is claimed. Earlier pilot outputs remain
untouched.

#### Standalone frozen Rahimi Table 1 rating

The one ready Grade 7 checked-contrast task received a fresh standalone
`rahimi-table1/v1` rating from `gpt-5.6-luna`: **10/15**.
The [rating](../../experiments/results/pf_paper_benchmark/20260925_grade7_pipeline_feasibility_standalone_table1/judge_run/ratings.jsonl),
[judge manifest](../../experiments/results/pf_paper_benchmark/20260925_grade7_pipeline_feasibility_standalone_table1/judge_run/manifest.json),
and [input provenance](../../experiments/results/pf_paper_benchmark/20260925_grade7_pipeline_feasibility_standalone_table1/input/provenance.json)
are stored separately from the 120-slot partial manifest. The judge received
only the student-facing task and the frozen benchmark learner context; no
condition label, teacher notes, or proposed approaches were supplied. The frozen
v4 config and rubric source hashes match.

| Dimension | Score | Model's stated reason |
|---|---:|---|
| APK | 3 | Uses taught unit rates and rational-number operations. |
| SSC | 1 | Three small-number ratios are straightforward for learners already taught unit rates; the judge considered the challenge too low. |
| AE | 3 | Fictional Stephen Curry practice and planning context is relatable. |
| MR | 2 | Allows displays such as a table or graph but does not strongly develop several methods. |
| OE | 1 | Three fixed records and a direct common-pace decision are tightly structured. |

The judge also flagged no tolerance for “common pace” and no attempt count or
prediction rule for the next practice. These are model concerns, not verified
mathematical errors: the exact rates are checked, but tolerance and future
extrapolation are not specified. The single selected-task rating is numerically
below the frozen v4 direct means (V1 14.40, V2 14.03, V3 14.20), but it is not a
matched comparison, a human rating, or evidence about student behavior.

The next research gate is a task-design/open-endedness assessment: independently
evaluate whether the prompt supports meaningful student decisions and distinct
mathematical approaches before spending on a full rerun. More contrast arithmetic
or tuning to the frozen rubric score is not that gate.

The exploratory, paper-informed secondary protocol for that gate is documented
in [PF_DESIGN_AUDIT.md](PF_DESIGN_AUDIT.md). It supplements but does not revise
the frozen Table 1 judge; it assesses task affordances, not observed student
behavior. Its first five-task calibration had five invalid responses and no
parsable secondary findings, so it supplies no quality comparison. Version 2 added an explicit
output schema and labels model calculations `model_recomputed`, not proof. Its
bounded run parsed all nine responses, but the missing-prior control was
misclassified as `not_evidenced`. Version 3 added a distinction between meaningful
mathematical openness and display choice or generic speculation. Its disjoint
run parsed 10/10 responses (four saved tasks plus six synthetic controls) but
again misclassified absent prior-instruction history; one of 60 findings was
unknown. The v4 prompt makes missing or empty prior-knowledge history explicitly
`unknown`; v5 requires idea-level mathematical differences rather than different
operations for the same test, while allowing multiple valid approaches. V5 had
one disjoint run on four saved tasks plus six reused schema/unknown controls:
10/10 responses parsed, with 0/24 saved-task and 3/36 control finding fields
unknown. V2-004 and PIPELINE-005 remained partial, but V1-004's supported
unit-rate-versus-line-through-origin routes may still be an overbroad positive.
The reused controls also showed an average-speed openness mismatch, while the
missing-history control now returned `unknown` for prior-resource start. One
frozen-Table-1 concern-presence flag remains unadjudicated. This is a single
model-only calibration, not human agreement or repeatability evidence; v4 was
not run, and the v5 prompt remains frozen. See
[the versioned audit record](PF_DESIGN_AUDIT.md#v5-disjoint-bounded-model-calibration).
These automated results do not authorize full rejudging or establish student
behavior.

A row-license-checked v1.14.0 Learning Commons snapshot and API helpers exist.
Since 2026-10-09, `--learning-commons` optionally retrieves and caches up to ten
standard descriptions without an exact-grade filter. The existing D1 call selects
zero to three short source labels while keeping its prior-resource output separate.
Selected original descriptions reach design, planning, review, fill and writing
as mathematical references, not evidence of prior teaching. The flag is off by
default; baseline prompts and historical results remain unchanged. Offline wiring
tests and small live selection trials exist, but selection can still retain broad
headings. A [small gpt-5.6-luna paired generation pilot](../../experiments/results/learning_commons_pf_comparison_luna_20261009T151453Z/REVIEW.md)
emitted 2/3 tasks per arm, with four independently checked numerical outputs but
no clear consistent benefit in assistant inspection. Baseline's spread rejection
was questionable and context's fraction case stopped on an ambiguous requirement.
No observed student behavior or PF quality improvement is claimed. See
[the implemented flow and validation limits](LEARNING_COMMONS_DATA_FLOW.md) and
[the investigation record](KNOWLEDGE_GRAPH_OPPORTUNITY.md).

The planner has one shared corrective retry for a concrete parser, expression,
or meaning-review error. A structured reviewer diagnosis can route that correction
to the plan alone or to the selected question, quantities, and plan together.
Joint repair must preserve the original learning target, prior-resource context,
approach IDs, quantity names, value sources, domains, fixed list lengths, and
original requirements in order; it may clarify descriptions and assumptions
or add supported inputs and constraints, not delete inconvenient requirements.
The revised design is checked again for structure, supported expressions,
requirement coverage, meaning, target preservation, and resolution of the diagnosis.
An unresolved review is not acceptance. A raw `unknown` without a valid repair
diagnosis remains blocked.

Invalid proposals have a separate single correction, with the original response
and parser/resource-link errors returned to the proposal stage. Valid proposals
need no extra call. Proposal repair preserves valid unaffected metadata, but may
correct a field explicitly named by a parser or metadata error; this is different
from selected-design repair, where valid quantity metadata is immutable. Plan-only
and joint repairs share one budget rather than resetting it when the diagnosis
changes. Fill retries remain value-only and limited to three attempts. Attempts
preserve prompts, raw responses, diagnoses, and validation evidence. Accepted
revised designs reach filling and writing together; rejected revisions do not
replace the original winner. The implementation and saved-case evidence are
tracked in the [joint-repair protocol](../../experiments/results/validation/20260922_joint_repair_protocol_v1.json)
and the calibration records below.

The historical plan route and its explicit saved-winner replanning require `math-plan/v2`.
Historical resume keeps the stored contract and effective design instead of
silently changing them.
`--from-result PATH --replan` performs the shared plan/review gate without repeating
selection; it also supports `--plan-only` and skips value filling when `--no-fill`
is given. `plan_stop_stage` distinguishes structure errors, expression preflight,
actual meaning review, and acceptance; a missing review is not a reviewer rejection.
New outputs snapshot the case input used for planning. Older results without
that snapshot remain readable but are marked as having limited provenance.

The requirement-to-constraint interpretation is still an LLM judgment, not a
deterministic proof that the condition was translated correctly. Fill attempts
save exact rendered prompts and raw responses; their checks list qualitative
requirements under `unverified_requirements`. Standalone `check_fill` checks
only the numerical plan, not review coverage or educational usefulness.

Historical fills that have no frozen plan remain preserved as legacy artifacts
and are not retroactively treated as passing the new contract.

### September 22 implementation and diagnostic protocol

The source snapshot used for the v2 runs passed 139 focused
software tests (independently verified across four modules: `runner`, `skeletons`,
`fill_check`, and `pf_diagnostic`, expanding on the historical 103 baseline tests
which remain valid) plus targeted Ruff checks.

The diagnostic protocol in `scripts/run_pf_diagnostic.py` runs with explicit
experimental settings (rather than relying on CLI defaults):
- **Experimental parameters:** runs across 8 diagnostic cases from
  `experiments/configs/prior_recommendation_cases.json`, generating $K=4$ candidate
  proposals per case, with explicit execution flags `--max-workers 3` and `--model luna`.
- **Pipeline flow & semantic constraints:**
  - Performs fresh D1 retrieval and design proposal by default, recording source
    configuration hashes alongside raw traces.
  - Enforces that a proposed situation must settle one executable numerical answer
    decision (a single scalar value, or a single `largest`/`smallest` or `equal`
    decision across all compared entities). Independent multiple comparison groups
    with separate answer decisions are prohibited by the checker.
  - Open-ended student work (hypotheses, explanations, alternative representations,
    and partial routes) remains allowed, but the executable core is strictly
    focused.
  - Unsupported target mathematics cannot be replaced with fake easy arithmetic
    (e.g., reducing a fair allocation problem to a basic sum).
  - Enforces a bounded single-attempt planning correction and up to three fill
    attempts. A genuine raw `unknown` review outcome is never retried; a malformed
    `pass` (such as unverified requirements or non-empty issues) remains blocked
    pending the existing shared corrective retry, without introducing extra loop
    hierarchies.
- **Wording updates:** two topic briefs (`weighted_combined_rate_g7_singapore` and
  `additive_vs_multiplicative_g7_singapore`) received clarified target-concept and
  evaluation-note wording for the September 22 round to state rate weighting and
  asymptotic ratio behavior with scientific precision. These are modified case inputs,
  not a controlled causal test or holdout.

#### Fresh 3-case calibration v1 outcomes

A fresh 3-case calibration run (`20260922_fresh_pf_calibration_v1`) executed 36
actual model calls (across fresh D1 retrieval, proposal generation, selection, planning,
and review) recorded in
[experiments/results/validation/20260922_fresh_pf_calibration_v1/manifest.json](../../experiments/results/validation/20260922_fresh_pf_calibration_v1/manifest.json).
The run produced **12/12 valid proposals** (4 candidates per case), **3 selections**,
but **0 fills and 0 final tasks** (0/3 completion):

| Case | Observed Stop | Root Cause |
|---|---|---|
| [Average speed](../../experiments/results/validation/20260922_fresh_pf_calibration_v1/kapur_average_speed_g7_singapore/result.json) | Review blocked | Selection introduced an undefined, non-operational required margin ("different enough to matter"). The planner oscillated between `!=` and `abs(diff) > 0`, and the reviewer rejected the plan because no precise threshold was enforced. |
| [Variance](../../experiments/results/validation/20260922_fresh_pf_calibration_v1/loibl_variance_g10_nrw/result.json) | Review blocked | Reviewer cited unknown quantities rather than strictly given metadata facts in `quantity_fact_refs`, and placed non-blocking commentary into `issues: [...]`, causing the runner to treat the review as defective despite valid plan arithmetic. |
| [Fraction](../../experiments/results/validation/20260922_fresh_pf_calibration_v1/mazziotti_fraction_g5_nrw/result.json) | Plan blocked | Proposer generated two independent comparison pairs across four target labels, but the answer rule was `equal` covering only the first two labels, violating label consistency and exceeding single-decision checker limits. |

An isolated hand-picked feasibility check confirms that the arithmetic checker
accepts valid finite lists: for candidate lists $A = [1, 2, 5, 8, 9]$ and
$B = [1, 4, 5, 6, 9]$ with equal mean 5, the exact variance checker accepts
$\text{Var}(A) = 10$ and $\text{Var}(B) = 34/5 = 6.8$. This demonstrates mathematical
feasibility under the v2 contract, but is explicitly a manual verification check,
**not a generated fill or completed task**.

#### Fresh 3-case calibration v2 outcomes

A second fresh 3-case calibration run (`20260922_fresh_pf_calibration_v2`) executed
41 actual model calls recorded in
[experiments/results/validation/20260922_fresh_pf_calibration_v2/manifest.json](../../experiments/results/validation/20260922_fresh_pf_calibration_v2/manifest.json).
It produced **12/12 valid proposals** (4 candidates per case), **3 selections**, but
**0 fills and 0 final tasks** (0/3 completion).

Unlike v1, all three cases advanced past planning and preflight to reach meaning
review on both allowed planning attempts (2 plan + 2 review calls per case). The
label mismatch observed in v1 fraction planning did not recur in v2, but this reflects
a distinct newly generated proposal rather than identical fixed-design progress:

| Case | Observed Stop | Audited Diagnosis |
|---|---|---|
| [Average speed](../../experiments/results/validation/20260922_fresh_pf_calibration_v2/kapur_average_speed_g7_singapore/result.json) | Review blocked (2 attempts) | **Mixed real defect and prompt-boundary demand.** The plan genuinely omitted the coupled inequality enforcing the judge's required disagreement (the journey with larger maximum part speed having smaller overall average speed). However, the reviewer also demanded that the task directions prompt students for explanations, even though the pipeline's fixed `_intended_student_output` already mandates justified student work; the review prompt does not receive this downstream writer contract. The reviewer's demand for explicit method comparison remains a legitimate upstream design concern rather than a proven false blocker. |
| [Variance](../../experiments/results/validation/20260922_fresh_pf_calibration_v2/loibl_variance_g10_nrw/result.json) | Review blocked (2 attempts) | **Real upstream design defect.** The selected question explicitly prescribed calculating "all observations and their deviations from the common mean," directly dictating the target canonical procedure. The reviewer demanded rewording the fixed selected question to allow open-ended student exploration, which is an upstream proposal/selection defect that the math planner cannot modify. |
| [Fraction](../../experiments/results/validation/20260922_fresh_pf_calibration_v2/mazziotti_fraction_g5_nrw/result.json) | Review blocked (2 attempts) | **Interface error on pass; genuine missing conditions alongside a redundant gate demand.** The second review attempt returned a raw `pass` but cited out-of-range constraint indices (index 19 out of 19 constraints indexed 0..18 for `original_2` and `original_4`), which is an interface/zero-based indexing failure. The first review attempt identified genuine missing conditions (absent part-count-vs-winner ordering and integer-scaling constraints). However, the first review's demand for a separate uniqueness constraint was redundant: the mathematical plan's `answer_rule: "largest"` with `require_unique: true` already deterministically rejects ties in every accepted fill at execution time, exactly like number constraints; the reviewer coverage vocabulary currently lacks the capability to cite this runtime engine guarantee. |

#### Fresh 8-case diagnostic v2 outcomes

The [full-run manifest](../../experiments/results/validation/20260922_full8_pf_diagnostic_v2/manifest.json)
records eight fresh attempts using the same nine source/configuration hashes as
fresh3v2. All 73 unique actual calls each had exactly one started and finished
event with matching `(case, module, call_number)`, all using `gpt-5.6-luna`.
The run completed on September 22, 00:08:07.680511--00:13:28.018088 UTC, taking about
320 seconds. **Two of eight attempted cases produced writer-ready tasks**; this
is execution completion, not established PF quality.

| Case | Saved outcome | Valid proposals / recorded proposals | Plan / fill attempts | Actual model calls |
|---|---|---:|---:|---:|
| [Average speed](../../experiments/results/validation/20260922_full8_pf_diagnostic_v2/kapur_average_speed_g7_singapore/result.json) | Task ready | 2/4 | 1/1 | 14 |
| [Variance](../../experiments/results/validation/20260922_full8_pf_diagnostic_v2/loibl_variance_g10_nrw/result.json) | Selector recommended none | 1/4 | 0/0 | 10 |
| [Fair allocation](../../experiments/results/validation/20260922_full8_pf_diagnostic_v2/kerrigan_fair_division_undergrad_usa/result.json) | Meaning review blocked | 2/4 | 2/0 | 12 |
| [Fractions](../../experiments/results/validation/20260922_full8_pf_diagnostic_v2/mazziotti_fraction_g5_nrw/result.json) | Task ready | 4/4 | 2/1 | 15 |
| [Part-whole ratio](../../experiments/results/validation/20260922_full8_pf_diagnostic_v2/ratio_part_whole_g7_singapore/result.json) | No valid proposals | 0/4 | 0/0 | 9 |
| [Weighted combined rate](../../experiments/results/validation/20260922_full8_pf_diagnostic_v2/weighted_combined_rate_g7_singapore/result.json) | API connection failure during proposals | Unavailable: batch incomplete | 0/0 | 9 |
| [Kinematics](../../experiments/results/validation/20260922_full8_pf_diagnostic_v2/kapur_kinematics_g11_cbse/result.json) | API timeout during D1 mapping | Not reached | 0/0 | 1 |
| [Additive versus multiplicative](../../experiments/results/validation/20260922_full8_pf_diagnostic_v2/additive_vs_multiplicative_g7_singapore/result.json) | API timeout during D1 expansion | Not reached | 0/0 | 3 |

The stage counts are:

```text
8 fresh D1 attempts -> 6 completed D1
  -> 24 proposal requests; 20 recorded parsed proposal outcomes from 5 completed batches, 9 valid (2 speed, 1 variance, 2 fair, 4 fraction, 0 ratio)
  -> 4 selector calls -> 3 selected designs
  -> 5 plan calls and 4 meaning reviews -> 2 accepted plans
  -> 2 accepted fills, both on their first attempt -> 2 writer-ready tasks
```

The four weighted-rate proposal requests did not produce a complete saved
proposal batch due to connection drops, so their validity is unavailable rather
than counted as four invalid designs (do not report 9/24 or 9/32). Raw calls,
including partial responses, remain in the trace.
There were **73 actual model calls** (14, 10, 12, 15, 9, 9, 1, 3 across
the eight cases: Average speed 14, Variance 10, Fair allocation 12, Fractions 15,
Part-whole ratio 9, Weighted combined rate 9, Kinematics 1, Additive vs multiplicative 3),
all using `gpt-5.6-luna`. Four requests encountered connection or timeout failures
across three cases: two weighted-rate proposal connection drops, a kinematics D1 mapping
timeout, and an additive D1 expansion timeout. These are infrastructure failures, not
evidence that those topics cannot produce PF tasks.

The remaining stops need different interpretations:

- **Variance:** the only valid proposal used four observations per list and
  required matching means, medians, ranges, and quartiles across different multisets.
  The selector declined because the quartile convention was unspecified and
  these constraints posed potential incompatibility. This is a design-feasibility
  concern, not an observed fill failure.
- **Fair allocation:** attempt 1 failed expression preflight with malformed parentheses;
  attempt 2 reached review but was blocked. The reviewer demanded derived relations/allocation
  structure and a unique maximizer (some of which may be redundant with guaranteed
  target structure; there is no need to claim every review demand was correct).
  Its open question asks for the "fairest" allocation, while its executable answer
  fixes the allocation maximizing the least-satisfied party's relative value.
  That represents an open criterion versus fixed maximin answer mismatch, not
  proof that fair-allocation invention exercises are invalid.
- **Part-whole ratio:** all four proposals failed structural parsing. Three
  errors concern `list_length` metadata and one concerns an approach with no
  listed prior resources; their causes require contract-level inspection rather
  than assuming four mathematical failures.

The subsequent prompt refinements (indexed constraints, intended student output,
and answer-rule uniqueness references) were implemented after this frozen run and
are NOT part of these run outcomes.

The [independent quality audit](../../experiments/results/validation/20260922_full8_pf_diagnostic_v2_quality_audit.json)
reviewed both exact completed tasks using GPT-5.6 Luna High in a separate agent
context. This was an offline artifact review, not an additional traced pipeline
judge call. All eight recorded input/result/D1/trace hashes were checked.
Independent fraction arithmetic and replay through `check_fill` confirmed both
tasks satisfy their declared mathematics and constraints.

| Completed case | Exact mathematical evidence | Independent model judgment |
|---|---|---|
| Average speed | Trip B has speed 5 km/h versus A's 30/11 km/h; averaging the two leg speeds incorrectly ranks A first, 6 versus 5 km/h | Provisional: a useful conceptual contrast, but the task requests one method and is relatively structured |
| Fractions | A = 14/21 = 2/3 and B = 20/30 = 2/3 both exceed C = 11/18 | Revise: the prompt cues equivalence and may elicit routine simplification rather than varied approaches |

Neither verdict requires copying the source scenario or activating every prior
resource. The fraction case's non-expert source status is an evidence limitation,
not proof that its task is invalid. The saved `tied=false` is also not a
mathematical error: that legacy field means all target values are equal; `argmax`
correctly records the two largest fractions.

No student response diversity or learning effect has been measured. This small
development set is not a holdout, and the changed topic briefs and fresh sampling
prevent a causal improvement claim over the historical zero-completion run.
Both historical result directories were verified unchanged. Any subsequent
interface corrections are separate from these preserved v2 outcomes.

#### Post-benchmark handoff corrections and fresh3v3

The next correction supplied authoritative zero-based constraint indices and the
actual writer output contract to the reviewer. Numerical requirement coverage
can also cite `answer_rule_fact_refs: ["require_unique"]`, but only for a
largest/smallest rule that actually enforces uniqueness. This proves neither a
particular winner nor a relationship between its input values. Scalar quantities
may omit `list_length` or use null; non-null scalar lengths remain invalid.
Inspection showed the earlier rejected scalar proposals used zero, not null.

For that run, the writer invited different approaches or representations and
comparison, allowed partial attempts, and prohibited disclosing an anticipated
equality, winner, or procedure before exploration. The later September 22 D3
wording revision below removes the partial-attempt encouragement requirement.
These are prompt requirements, not verified student behavior. The parent
independently verified **152 focused software tests**
and targeted Ruff checks before the next calibration.

The [fresh3v3 manifest](../../experiments/results/validation/20260922_fresh_pf_calibration_v3/manifest.json)
records three fresh development cases, not retries merged into the eight-case
benchmark. It completed in about 145 seconds with **40 actual model calls**:

| Case | Valid proposals | Selection | Final stop | Calls |
|---|---:|---|---|---:|
| Part-whole ratio | 3/4 | One design | Meaning review after two plans | 14 |
| Variance | 4/4 | One design | Meaning review after two plans | 14 |
| Weighted combined rate | 4/4 | One design | Meaning review after two plans | 12 |

Thus 11 of 12 proposals parsed successfully, but **zero of three cases reached
filling or task writing**. All 40 calls had unique matching start/finish events;
none reported an API error. The observed bottleneck was requirement accounting:

- Ratio: the reviewer demanded separate equations proving that the two declared
  parts are two parts and that the denominator already defined as their sum is
  the whole. An unused derived label and a tautological constraint added noise.
- Variance: the final formulas were correct, but the reviewer demanded a
  numerical constraint proving the plan contains exactly two comparison data sets.
- Weighted rate: the target formula was valid, but coverage cited invalid
  derived-quantity facts and a scalar uniqueness fact. The upstream phrase
  "exact calculable quotients" also left finite-decimal versus well-defined
  division unspecified.

A separate read-only Luna audit identified these distinctions. The parent then
checked manual feasibility examples against every final saved plan constraint:
ratio parts 5 and 3 give 5/8; variance lists [1,3,5,7] and [1,4,4,7] give 5 and
9/2; weighted distances [10,6] and times [2,3] give 16/5. All three exact checks
accepted. **These manually supplied examples are not automatic fill successes,
do not resolve every textual requirement, and do not change the saved stops.**

Provenance caveat: a late concurrent YAML clarification changed the proposal
prompt file after the manifest snapshot. It clarified given versus derived list
metadata. The other eight source hashes still matched. The recorded calls
contain one consistent system prompt per stage; all 27 D2 user prompts match
the final templates, and only the proposal system text differs from the final
file. Preserve the original manifest and traces rather than describing this as
a perfectly frozen-source run. Four focused prompt-rendering checks passed
after that clarification. No completed task tested the revised writer in this run.

The final bounded correction lets the reviewer cite existing plan declarations
through `plan_fact_refs` rather than invent equations to prove them. The proposal
prompt also separates actual value restrictions from definitions and discourages
unnecessary, unspecified "exact/simple/nice" conditions. It adds no pipeline
stage, redesign loop, numerical relaxation, or retry. The parent independently
verified **159 focused tests**, Ruff lint, and Ruff formatting after this change.
Software checks establish the evidence schema and existing runtime behavior;
they do not establish reliable model use of the schema or PF exercise quality.

#### Fresh3v4: frozen-source follow-up

The [fresh3v4 manifest](../../experiments/results/validation/20260922_fresh_pf_calibration_v4/manifest.json)
records another fresh three-case development run after the plan-reference
correction, with the same three topics and no external retries. All nine recorded
source hashes matched after completion. All 39 actual calls have unique paired
start/finish events, identify `gpt-5.6-luna`, and report no API errors.

| Case | Valid proposals | Final outcome | Calls |
|---|---:|---|---:|
| Part-whole ratio | 4/4 | Expression stop on second plan; no task | 12 |
| Variance | 4/4 | Accepted fill and written task | 15 |
| Weighted combined rate | 4/4 | Review stop on second plan; no task | 12 |

This is **one mathematical task completion out of three attempts**, not evidence
of reliable generalization or three improved PF exercises. The run took about
146 seconds: 12 D1 calls, 12 proposals, three selections, six plans, four reviews,
one fill, and one writer call. All three selected cases used their single shared
planning correction.

The two remaining failures expose a persistent mismatch between reviewer
expectations and the given-input-only expression engine:

- Ratio's first plan already computes each share as `a / (a + b)`. The reviewer
  demanded separate equations for the declared derived whole. The correction
  then referenced `whole_count_by_collection`, which is not a given input and
  cannot be evaluated. The expression checker correctly stopped that correction;
  this does not establish that the original target formula was wrong.
- Weighted rate's target already computes
  `sum(rate * time) / sum(time)` with the two products expanded. Review still
  demanded separately enforced intermediate distances and totals. The correction
  added identities, and review remained blocked. The engine does not independently
  sample these derived quantities, so this is not evidence that a fill actually
  assigned them inconsistent values.

As a diagnostic only, the parent supplied values to each first plan and reran
the exact checker. Ratio counts A=[6,5], B=[14,5] give shares 3/10 and 1/2 and
satisfy its constraint. Weighted route rates/times [10,2]/[1,10] and [5,4]/[2,1]
give overall rates 30/11 and 14/3 and satisfy all 14 declared constraints; the
equal-rate averages 6 and 9/2 reverse the ranking. These manual checks establish
feasible arithmetic, not automatic pipeline completions or satisfied PF outcomes.

The new evidence-reference schema therefore did not eliminate the underlying
review misunderstanding. Further schema growth or relaxed numerical checks is
not justified by this run. Aligning review with what the engine actually samples
and evaluates remains necessary before calling the pipeline fluent across topics.
Repeated fresh generation on these development cases is not a controlled
comparison or untouched holdout evaluation.

The [independent variance quality audit](../../experiments/results/validation/20260922_fresh_pf_calibration_v4_quality_audit.json)
rates **"Which Data Set Is More Consistent?" as provisional**, not a demonstrated
PF success. The parent verified all four audited artifact hashes, the exact task
transcription, and all 22 numerical constraints. A=[2,6,6,10] and B=[2,4,8,10]
have equal means of 6 and ranges of 8; their population variances are 8 and 10,
so the target selects A as less variable. The prompt leaves the method open and
allows partial work, but presents only a small fixed-data comparison.

Actual D1 recommendations include quartiles as well as mean and range. With the
median-of-halves convention, the interquartile ranges (upper minus lower quartile)
are 4 for A and 6 for B. Thus an assumed familiar method can already select A;
matching mean and range does not force students to invent variance. This is a
legitimate alternative approach, not a reason to require every prior method to
fail. Approach use, productive failure, and learning remain unobserved. The audit
is an independent-context Luna judgment, not a separately traced API judge or
human/student validation.

At this point no further full-eight-case run was launched: two of three cases
still stopped, and the completed task had only provisional quality evidence.
The preserved full8v2 result predates these corrections.

#### Reviewer execution-contract correction

The next correction changes only the review system prompt, not the mathematical
engine or its acceptance rules. It explicitly tells the reviewer that filling
supplies only given inputs; derived and unknown declarations are not independent
numerical slots. The engine evaluates target arithmetic over those inputs and
does not solve equations for separately named derived quantities. Review must
still block genuinely missing restrictions or inconsistent independently
supplied/displayed values, but must not demand auxiliary equations for a
relationship already correctly inlined in the target.

The parent compared the prompt against the actual recorded v4 review request:
only this 13-line insertion changed. The other eight tracked source hashes
remain unchanged. All **159 focused tests** and the targeted Ruff checks pass.
No stage, schema, retry allowance, or numerical restriction was added or relaxed.

A [fixed-input development calibration](../../experiments/results/validation/20260922_fixed_input_review_calibration_v1/manifest.json)
reviewed the preserved first ratio and weighted-rate plans, the accepted variance
plan, and one synthetic negative control. The control changes the type-A share
`a/(a+b)` to the type-B share `b/(a+b)` while retaining the type-A question.
For A counts [6,5] and B counts [14,5], the correct shares are 3/10 and 1/2,
whereas the control gives 7/10 and 1/2 and reverses the selected collection.
Both formulas execute, so this tests semantic review rather than parsing.
The calibration used exactly four `gpt-5.6-luna` review requests with no automatic
retries, API errors, or inconclusive outcomes:

| Fixed input | Observed review | Meaning |
|---|---|---|
| Ratio first plan | Pass; eligible for fill | Accepts the inlined part-to-whole definition without a redundant derived-variable equation |
| Weighted-rate first plan | Pass; eligible for fill | Accepts inlined segment distances and totals without separately sampled intermediate values |
| Previously accepted variance plan | Pass; eligible for fill | Retains a valid acceptance |
| Synthetic wrong-part share | Revise; fill blocked | Explicitly identifies the type-B numerator as answering the wrong question and reversing the intended comparison |

The parent verified all 13 recorded source/input/runner hashes, paired request
traces, unchanged saved inputs, actual coverage reasons, and the production
fill-eligibility rules. This is a useful bounded check of the correction, not a
fresh-generation completion rate, judge-accuracy estimate, or PF-quality result.
It includes only one synthetic negative example and one review per input.
Unknown, unparseable, and execution-error outcomes would remain inconclusive.
The source-frozen eight-topic follow-up below was authorized after this check
and is reported separately from these fixed-input judgments.

#### September 22 fresh eight-topic follow-up (full8v3)

The [full8v3 manifest](../../experiments/results/validation/20260922_full8_pf_diagnostic_v3/manifest.json)
records one fresh run with four concurrent workers, four proposals per topic,
and no D1 reuse or external retry. It ran from 01:05:49 to 01:11:10 UTC
(about 321 seconds). All nine tracked source hashes match both the preceding
fixed-input calibration and the files checked after this run.

**Three tasks were produced from eight attempted topics.** All eight completed
D1 and selected a design; five stopped during planning or review, before filling.
There were no API errors, so infrastructure does not explain those five stops.

| Topic | Valid proposals | Plan / fill attempts | Recorded outcome |
|---|---:|---:|---|
| Average speed | 4/4 | 1 / 1 | Task ready |
| Variance | 4/4 | 2 / 0 | Review blocked |
| Fair division | 3/4 | 1 / 0 | Review blocked |
| Fractions | 4/4 | 2 / 0 | Review blocked |
| Part-whole ratio | 3/4 | 2 / 0 | Expression preflight blocked |
| Weighted combined rate | 4/4 | 1 / 1 | Task ready |
| Kinematics | 2/4 | 2 / 0 | Review blocked |
| Additive versus multiplicative comparison | 2/4 | 1 / 1 | Task ready |

The parent verified **104 paired requests** targeting `gpt-5.6-luna`: 8 D1
mapping calls, 29 resource expansions, 32 proposals, 8 selections, 12 plans,
9 reviews, 3 fills, and 3 writers. The 26 structurally valid proposals out of 32
do not imply 26 feasible or high-quality designs. Each completed case used one
fill attempt; trace counts use the `stage` field, not the runner-module name.
The frozen harness disables SDK retries; this setting is not itself included
in the trace's inferred request settings.

The same 159 focused tests and targeted lint/format checks pass after the run.
These eight topics remain development cases, not an untouched test set.
Differences from full8v2 cannot be attributed solely to the prompt correction:
the new generation is stochastic and the earlier run also had infrastructure
failures.

The [completed-task audit](../../experiments/results/validation/20260922_full8_pf_diagnostic_v3_quality_audit.json)
is a separate-context Luna High judgment, corrected after parent review, not an
additional traced API judge or human rating. The parent verified its 12 source
hashes, exact student-facing text, saved values, and all 33 declared constraints
(8 for speed, 14 for weighted rate, 11 for additive/multiplicative comparison).

| Written task | Audited status | Evidence and limitation |
|---|---|---|
| Average speed | Ready for a student-response probe | Overall speeds are 4 and 21/4 km/h; equal-weight means of segment speeds are 7 and 13/2 km/h and select the opposite route. The task leaves methods open and requests both overall speeds. The winner also follows legitimately from B covering more distance in less time. |
| Weighted combined rate | Provisional | Overall rates are 91/10 and 11/2 items/hour; equal-weight means select the opposite group. However, both groups worked 10 hours, so comparing 91 versus 55 items alone correctly decides the winner. D1 already recommends total quantity divided by total denominator, making target novelty uncertain. |
| Additive versus multiplicative comparison | Provisional | A gap of 10 with baselines 10, 20, and 40 gives ratios 2, 3/2, and 5/4. The task's checklist strongly guides the work; its requested general trend needs justification beyond three numerical examples. |

The weighted-rate verdict was downgraded during parent review because the initial
audit missed the equal-total-time shortcut. This is a valid student approach,
not an error that must be eliminated. None of the three tasks has student
responses: multiple approaches, productive failure, and learning remain untested.

The [five-stop audit](../../experiments/results/validation/20260922_full8_pf_diagnostic_v3_failure_audit.json)
preserves source hashes and selected requirements. Its causes are not one shared
parser defect:

| Stopped topic | Audited cause | Consequence |
|---|---|---|
| Variance | First attempt references target names instead of inlining them; after correction, review overstates a direction conflict in an underdefined concentration requirement | Do not blindly reverse the inequality or declare the task impossible. The numerical plan is feasible; the concentration interpretation needs clarification. |
| Fair division | Selected design requires claim counts and finding an acceptable one-to-one assignment, neither a native operation in the current evaluator; the plan substitutes a constant target and `0 == 1` | Correctly blocked as unsupported, not evidence that fair division itself is impossible. |
| Fractions | A non-multiple-denominator requirement has no native divisibility operation; the plan substitutes a positive denominator ratio equal to zero | Correctly blocked; satisfying fraction equality alone would not satisfy the selected requirements. |
| Part-whole ratio | Selection explicitly says to provide one whole amount per item, but wholes remain descriptive derived quantities; correction tries to reference them as executable inputs | Different from the fixed-input calibration's inline-only definition. The provided-whole requirement or quantity design must change upstream. |
| Kinematics | A derived signed braking acceleration is declared positive, and friction-coefficient units are left blank | Target stopping-distance arithmetic is supported. Clarifying the selected metadata requires an upstream change, not another formula-only attempt. |

For variance, a **manual diagnostic**, not an automatic fill, uses
A = [1,1,3,3,3,3,5,6] and B = [1,2,2,2,4,4,4,6]. All 40 declared constraints
pass. Both have mean 25/8, median 3, and quartiles 2 and 4. A has four interior
values near the mean; all six of B's interior values equal the quartiles.
The reviewer confused distance from the mean at selected positions with distance
to the quartile values. Its prescribed direction reversal is not established.
This witness does not prove that every accepted fill meets the informal
concentration requirement.

**Decision after that bounded iteration:** retain the current structure and stop
shared-prompt tuning. Plan correction preserves the selected quantity
declarations, so it cannot silently repair upstream metadata or change which
values are supplied. Do not add matching/divisibility solvers, weaken checks, or
quietly redesign cases to increase the completion count. The next useful work is
a student-response probe on the speed task and explicit upstream requirement
cleanup for supported designs; any redesigned benchmark condition must be
recorded separately. The pipeline is not yet reliably generalized or educationally
validated.

### September 22 checker-capability guidance and five-topic recheck

The subsequent user-approved change shares the actual checker contract with
proposal and selection, as well as planning, review, and filling. It adds no
mathematical operations, model stages, or retries. The
[protocol](../../experiments/results/validation/20260922_checker_capability_protocol_v1.json)
reuses each topic's saved full8v3 D1 context and original input, but generates
**new designs**, not repairs of the old frozen plans.

The first two-topic calibration was interrupted by two connection errors in
eight requests. An explicit retry produced ratio and fraction tasks in 18
requests. The remaining three topics produced fair-division and kinematics tasks
in 23 requests, while variance selection incorrectly demanded later-stage
`math-plan/v2` fields and claimed squaring was unsupported. All successful
development fills replayed successfully, but the fair-division task only ranked
claims for one contested piece; it did not establish a complete fair allocation.

A general correction clarified stage responsibilities and equivalent operator
composition (`x*x`, not `x**2`). All five topics were then regenerated under one
frozen version; earlier successes are **not** mixed into that final result.

| Topic | Final outcome | Meaning |
|---|---|---|
| Variance | Written; numerical replay accepted | A = `[1,4,7,10]`, B = `[1,5,6,10]`; variances 45/4 and 41/4. B has smaller spread. |
| Fair division | No valid proposals | Two empty responses; two proposals missing required approach-to-resource links. No mathematical capability verdict was reached. |
| Fractions | Review `unknown`; no fill | Common-factor requirement unenforced; requested variation across multiple generated instances unresolved. Not a verified incorrect answer. |
| Part-whole ratio | Written; numerical replay accepted | Parts 5 and 3 give 5/8 of the combined amount. |
| Kinematics | Review `unknown`; no fill | Selected situation omits physical assumptions used by its formulas; numerical requirement coverage was marked complete. |

The [final run](../../experiments/results/validation/20260922_checker_capability_full5_v2/manifest.json)
ran from **09:31:26 to 09:34:40 UTC** and produced **2 tasks from 5 topics**,
with **15 structurally valid proposals from 20**, **36 paired model requests**,
and **zero API errors**. All nine tracked production hashes matched after the
run; all original inputs and D1 payloads matched the baseline apart from the
recorded D1 origin annotation. All 11 declared constraints across the two
accepted fills passed independent replay. The final software checks passed
163 focused tests plus targeted Ruff lint/format checks.

The [audit](../../experiments/results/validation/20260922_checker_capability_recheck_audit_v2.json)
records all 85 requests across development, the explicit infrastructure retry,
and the final run. The earlier version completed four of these five topics,
whereas the final version completed two: this small development comparison is
not a causal improvement estimate or reliable generalization evidence.
The written tasks are target-relevant but simplified; the ratio task is close
to a guided textbook conversion, and the variance task permits a direct visual
comparison. No student approach diversity, productive failure, or learning has
been measured. Stop this iteration without weakening checks or tuning separately
to each remaining case.

### September 22 bounded saved-case repair calibration

The historical checker-capability guidance run remains a separate **2/5**
development result. It is not pooled with the saved-case repair calibration and
does not claim that all five original topics were rerun under repair.

The first saved-case repair run is preserved in
[saved2_v1](../../experiments/results/validation/20260922_joint_repair_saved2_v1/manifest.json),
[fair1_v1](../../experiments/results/validation/20260922_joint_repair_fair1_v1/manifest.json),
and its
[audit](../../experiments/results/validation/20260922_joint_repair_audit_v1.json).
It attempted three exact saved cases, produced **0/3 written tasks**, and made
nine paired calls with no API errors. The two fraction/kinematics cases were
blocked after one repair each. The fair-division calibration also made one
proposal correction per saved response, but its utility used a legacy selection
parser and discarded the valid modern `recommended_id` response; that is a
calibration defect, not evidence that the proposals were all invalid.

The corrected saved-case evidence is preserved in
[saved2_v2](../../experiments/results/validation/20260922_joint_repair_saved2_v2/manifest.json),
[fair1_v2](../../experiments/results/validation/20260922_joint_repair_fair1_v2/manifest.json),
and the corresponding
[audit](../../experiments/results/validation/20260922_joint_repair_audit_v2.json).
Across these **three attempted saved cases**, there were **17 paired calls and
zero API errors**, with two independently accepted fills and **2/3 written
tasks**. The current frozen implementation also passed **207 focused software
tests** and targeted Ruff lint/format checks. Independent replay passed **5
kinematics declared constraints** and **4 fair-division declared constraints**;
these software and arithmetic checks are not educational evidence.

- **Kinematics:** the accepted joint repair added the missing physical
  assumptions and preserved the derived quantities. Its writer output explicitly
  instructs students to determine reaction, braking, and combined stopping
  distances in sequence, so educational quality is provisional rather than
  evidence of open-ended PF.
- **Fractions:** the common-factor witness became structurally representable,
  but the original collection-level requirement remains unresolved: across
  generated instances, the collection must contain both matching and
  nonmatching primary shares. This is not a demand for one pair to be both
  equal and unequal. The run stopped honestly with no writer.
- **Fair division:** three of four saved proposals became structurally valid;
  modern selection chose original proposal index 1 from the filtered valid
  candidates and preserved its selection metadata. Independent replay passed
  all four declared constraints; the target relative claims were `3/5`, `1/2`,
  and `4/9`. The normalized relative-claim ranking is a chosen reference rule,
  not a uniquely mandated fair-share benchmark rule, and the written task
  covers only a standoff step rather than a complete fair allocation. Its
  educational quality is therefore provisional.

These runs preserve the original raw responses, empty payloads, prior context,
requirements, and source hashes. They are development calibration, not a
holdout, repeated-stability, student-outcome, or learning-effect evaluation.
The next generic work is to distinguish task-level from collection-level
requirements and to review student-facing openness and decision-rule
justification before launching a broader benchmark.

### September 22 saved-success replay regression check

The [saved-success audit](../../experiments/results/validation/20260922_joint_repair_others_audit_v1.json)
records a separate recheck of the five remaining completed cases:
[other2](../../experiments/results/validation/20260922_joint_repair_other2_v1/manifest.json)
and
[other3](../../experiments/results/validation/20260922_joint_repair_other3_v1/manifest.json).
All five produced written tasks with one review, one fill, and one writer call
each: **15 paired calls, zero API errors, five first-fill accepts, and 44
declared constraints passed**. The recheck reused copied inputs, D1 context,
initial plans, and winners; it did not regenerate D1 or proposals and exercised
zero repairs.

This is a **5/5 saved-success regression check**, not a new 7/8 benchmark and
not pooled with the corrected failure-repair result of 2/3 written tasks. The
historical full8 result remains **3/8**. The cases were already completed
successes, so these runs test replay, preservation, and numerical continuity
rather than repair effectiveness.

- **Variance:** the task leaves methods open, but B is visibly more
  concentrated. A visual comparison is legitimate, yet this is not evidence
  of productive failure or multiple meaningful approaches.
- **Part-whole ratio:** `5/8` is numerically valid, but equal-unit
  interpretation and the constructed whole are strongly cued, risking routine
  conversion.
- **Average speed:** the task does not provide a total-distance-over-total-time
  formula. The correct overall rates are A `8/3` and B `9/4` km/h, while
  unweighted segment-rate means tie at `7/2`; this makes it a candidate for a
  student-response probe, not validated PF.
- **Weighted combined rate:** the task asks students to develop a method and
  does not give an aggregation formula. Correct overall rates are A `9/5` and
  B `11/5` items/hour, while unweighted period-rate means are A `5` and B
  `2`; D1 prior context explicitly names total amount divided by total
  denominator as a student move, so target novelty remains uncertain.
- **Additive versus multiplicative comparison:** the task explicitly specifies
  larger-to-smaller ratios and asks for their trend (`2`, `3/2`, `5/4`), so
  the comparison method is guided. The general claim still needs
  justification beyond three numerical examples.

These are qualitative inspections, not learner evidence. The earlier 207
focused software tests and targeted Ruff checks were not rerun for this frozen
code recheck. Next work is student-facing openness and target-novelty
inspection followed by a student-response probe; collection-level
requirements still need separate verification.

### September 21 target-only implementation and calibration

The v2 implementation passed all 103 focused runner, contract, and checker tests,
with no failures, and the targeted Ruff checks. These are software checks, not
evidence that the model can reliably generate PF tasks.

A bounded calibration replanned three saved September 21 designs concurrently
using GPT-5.6-luna. It reused each original case snapshot, D1 context, selected
situation, and requirements; there was no manual redesign or upstream regeneration.
It produced **zero final tasks from three cases**, so it does not establish an
improvement in completion or educational quality.

| Saved design | Observed stop | Interpretation |
|---|---|---|
| [Average speed](../../experiments/results/validation/20260921_target_only_calibration_GICKWG/average_speed.json) | Meaning review after both allowed plan attempts | Unspecified list lengths leave fixed-index constraints incomplete. The reviewer also demanded arithmetic constraints for units already declared in quantity metadata; that is a limitation of requirement accounting, not evidence of incompatible units. |
| [Variance](../../experiments/results/validation/20260921_target_only_calibration_GICKWG/variance.json) | Empty target on the first attempt; expression preflight on the second | With unspecified list lengths, the restricted language cannot express the proposed variance calculation over every entry. The model placed an explicit unsupported explanation where executable expressions were required; it was not accepted as a formula. No meaning review occurred. |
| [Fractions](../../experiments/results/validation/20260921_target_only_calibration_GICKWG/fraction.json) | Meaning review, without a corrective retry | The original single-pair requirements demand both equal and unequal proportions. The reviewer returned unknown and the design remained blocked. |

The calibration recorded five planning responses and three meaning-review
responses; no fill or writing calls were made. The original eight-case diagnostic
artifacts remained byte-identical. A new full eight-case run was deferred because
the small calibration exposed unresolved design and representation boundaries.
The implementation is usable for further diagnostics, but automatic generation
has not been demonstrated by these runs.

### September 15 filling-handoff calibration

These runs use the familiar synthetic score example, not a topic holdout:

- [Automatic judge-to-plan attempt](../../experiments/results/validation/20260915_095541_fill_handoff_example_luna/result.json):
  the judge selected the consistency comparison. The planner reported missing
  scoring-scale information, but put its unresolved note in `required_checks`,
  which accepts strings rather than objects. Parsing stopped; no review or fill
  was run. This failure is preserved, not repaired or relabeled as a success.
- [Isolated filling attempt](../../experiments/results/validation/20260915_095742_isolated_fill_example_luna/result.json):
  one Luna call using a **hand-authored regression plan and design context**
  returned A `[4,6,6,8]` and B `[4,4,8,8]`. Both means are 6 and both ranges are
  4, satisfying the intended matching-summary conditions. Population variances
  are 2 and 4 respectively, so A has less spread by that measure. The declared
  arithmetic checks passed. This bypassed automatic selection, planning, and
  meaning review; it is not end-to-end generation success or student evidence.

## 7. D3: write the open task last

The current writer runs whenever D2b retains a usable data proposal, including
after failed checks or exhausted repairs. Failed, unknown and unsupported
conditions remain recorded findings under the
[draft-first policy](#october-11-draft-first-completion-policy); producing text
does not make those conditions pass.
It uses the [fixed-data writer prompt](../../src/generation/prompts/design_data.yaml),
not the legacy mathematical-plan writer. Its inputs are learner and prior-resource
context, candidate wording from the selected brief, supplied quantities/values,
and teacher-only task-specific evidence and checks. The writer no longer receives
rubric guidance; D2a still does. It must preserve necessary raw givens while
recording withheld discoveries, but the October 10 replays show residual numerical
and paraphrased disclosures. See the
[implementation and replay](#october-10-d3-disclosure-implementation-and-replay).

The rules below originated in the historical writer and also inform current
writing. Student attempts could inform later instructional consolidation, but
that sequence has not been evaluated in the current generation comparisons.

### September 22 research-informed wording rules

| Applied rule | Student-facing example (illustrative, not a research quotation) | Research basis and boundary |
|---|---|---|
| **Use plain, precise language.** Prefer familiar words and direct instructions; remove unnecessary formality, not necessary information. | "Explain why" rather than "Provide a justification." | [Haladyna, Downing, and Rodriguez (2002), *A Review of Multiple-Choice Item-Writing Guidelines for Classroom Assessment*](https://doi.org/10.1207/S15324818AME1503_5): clarity guidance adapted from MCQ assessment writing, not a PF wording experiment. |
| **Make the goal clear; leave the method open.** Specify the required decision, explanation, procedure, or measure without supplying target-method steps. | "Which player is more consistent? Develop a way to compare them." | [Kapur and Bielaczyc (2012), *Designing for Productive Failure*](https://doi.org/10.1080/10508406.2011.591717): students develop approaches before instruction and consolidation. The wording rule is an inference from that instructional design. |
| **Ask students to show and explain their thinking.** Request reasoning, not only an answer; invite comparison only when useful to the task. | "Show how you compared them and explain your decision." | [DeCaro, Isaacs, Bego, and Chastain (2023), *Bringing exploratory learning online: problem-solving before instruction improves remote undergraduate physics learning*](https://doi.org/10.3389/feduc.2023.1215975): the procedure explicitly emphasizes working through the activity and explaining ideas. Its wording was not tested independently; conditional comparison is our PF-informed adaptation. |

These are research-informed writing choices, not demonstrated effects of the
exact example sentences. The optional encouragement to submit unfinished attempts
is **not adopted**: it has been removed from both the writer prompt and the shared
intended-student-output guidance received by the writer and meaning reviewer.
No compulsory second method, universal ban on representation suggestions, or
rigid task template is imposed.

Our editing safeguard is separate from the literature claims: preserve all
numbers, units, relationships, assumptions, scope, requested outputs, and
mathematical meaning. If a saved design already requires a method or component
calculation, the writer must not silently delete it to make the task look more
open. Such a limitation belongs to upstream design, not wording repair.
Calibration also made two existing boundaries explicit: briefly clarify ambiguous
task terms without supplying a method, and do not announce why an anticipated
student approach will fail. Keep names consistent and identify who each condition
or competing claim applies to. These are applications of clarity and openness,
not additional research-validated rules.

The existing `title`, `body`, and `question` fields are retained and displayed
together. The body presents the situation, data, and necessary conditions; the
question carries the challenge and brief request for reasoning. Avoiding
duplicated instructions is an editorial application of clarity, not evidence
that every repetition is harmful. Contradictions or missing information needed to define the task can still
produce an explicit blocked result. Missing evidence for a claim alone must not.

The historical mathematical-plan writer received five bounded inputs:

1. **Student context:** grade, subject, topic, jurisdiction, and the assumed prior
   resources with their taught use and limitations.
2. **Target concept:** teacher-facing information used to avoid accidentally
   turning the task into a direct target-method exercise.
3. **Fixed task design:** quantities, exact values, question, frozen
   mathematical plan, and the full structured approach records (procedure,
   plausibility, resources, and limitations).
4. **Intended student output:** the question's requested product and answer rule,
   such as a justified decision or an invented measure.
5. **Design context:** the judge's selection reason, selected approaches, main
   concern, numerical requirements, and plan-review findings.

This follows the literature-informed distinction between withholding the target
procedure and withholding necessary information. Kapur and Bielaczyc (2012)
provide contextual data and ordinary mathematical vocabulary while leaving the
solution construction open; Schwartz and Martin (2004) provide graphical data
while asking students to invent a general procedure. Kapur and Rummel (2012)
also distinguish support from direct instruction in the target content. These
sources support the prompt boundary as a design inference, not as a validated
universal writer rule.

The writer must not copy teacher-facing solutions, anticipated approaches,
design notes, or review issues into the student task. It returns `ready` with
the title, body, and question, or `blocked` with explicit blocking issues.
Historical fresh and resumed runs called D3 only after an accepted fill; a blocked or
malformed writer response is saved as blocked rather than presented as a task.
The story supplies context and engagement. It should not change the fixed
mathematical mechanism.

### September 22 writer-only before/after comparison

The three rules were applied to the **seven exact saved final-writer inputs**:
the five saved-success rechecks plus repaired kinematics and fair division.
No proposals, selection, planning, meaning review, or filling were regenerated.
The deterministic fill checks were rerun locally, without model calls.

- **Preparation:** [seven frozen input checks, zero model calls](../../experiments/results/validation/20260922_writer_rules_v1/prepared/manifest.json).
- **Initial calibration:** [three writer calls](../../experiments/results/validation/20260922_writer_rules_v1/calibration/manifest.json)
  on variance, kinematics, and fair division. All returned `ready`, but variance
  omitted the meaning of "consistent" and fair division explained why a likely
  student approach could not settle the question. These outputs are retained.
- **After the general safeguard clarification:** [three calibration replays](../../experiments/results/validation/20260922_writer_rules_v2/calibration/manifest.json)
  and [four further cases with the same frozen prompt](../../experiments/results/validation/20260922_writer_rules_v2/remaining/manifest.json).
  **Seven final tasks returned `ready`; zero were blocked.** The entire exercise
  used **ten writer calls**, including the initial three; no upstream model calls.
- **Control:** the source model remained GPT-5.6-luna. Requested settings were
  temperature 0.7 and 4,000 tokens; the adapter actually sends
  `max_completion_tokens=4000` and omits temperature. Fixed writer-context
  sections, questions, answer rules, and historical artifact hashes were checked
  against the original calls. Runtime hashes match between the two revised runs.

The [side-by-side comparison](../../experiments/results/validation/20260922_writer_rules_v2/comparison.html)
shows the exact previous and new task text. The
[inspection record](../../experiments/results/validation/20260922_writer_rules_v2/comparison_audit.json)
contains per-case source paths, checks, and cautions. Content judgments below are
assistant inspection, not independent human ratings.

| Saved task | Previous words | New words | Main observation |
|---|---:|---:|---|
| Average speed | 131 | 98 | One decision/explanation request; all distance/time pairs kept. |
| Variance | 112 | 72 | Compact data; the revised output again defines consistency as less spread. |
| Part-whole ratio | 117 | 67 | Shorter, but adds an unnecessary hint to determine the combined number of units. |
| Weighted combined rate | 147 | 98 | Clear per-hour meaning; calculation and justification retained. |
| Additive versus multiplicative | 167 | 91 | Repetition removed; required ratio comparison and general trend retained. |
| Kinematics | 191 | 141 | Physical assumptions and all required component distances retained; still guided. |
| Fair division | 249 | 161 | Personal valuations and benchmark retained; still states that all three meet it. |

Across all seven tasks, student-facing text decreased from **1,114 to 728 words
(34.6% fewer)**, reducing reading length but not establishing educational quality.
Counts include title, body, question, and data; whitespace-separated tokens must
contain a letter or digit, so standalone Markdown table separators do not count.
The replay's raw `total_words` field instead counts all whitespace-separated
tokens, including Markdown separators; it is not the measure used in this table.

The unfinished-attempt encouragement is absent from all seven new outputs.
The numbers, units, and main requested outputs are retained on inspection, but
the result is **not uniformly more open**: the ratio task adds an intermediate-step
hint, kinematics and additive/multiplicative retain upstream method guidance,
and fair division still gives away the shared benchmark qualification. Its
benchmark also does not uniquely determine a recipient. The weighted-rate
design's assumed prior knowledge already contains the aggregation method.

Three final cases informed calibration; only the other four were not used for
that prompt adjustment. This is one final sample per saved case, not a fresh
seven-of-eight end-to-end result, a repeated-stability test, or evidence of
student approach diversity, productive failure, or learning.

Implementation: [writer-only replay utility](../../scripts/replay_pf_writer.py)
uses the production writer and refuses existing output directories; `--prepare-only`
checks and records inputs without loading a model client. Each live case retains
the original artifacts, fixed context, old/new tasks, prompts, raw response,
settings, and call trace. The [comparison renderer](../../scripts/render_pf_writer_comparison.py)
reads the saved results without editing their student-facing text.

### September 15 two-example D3 calibration

Using GPT-5.6-luna and the fixed design contexts (without rerunning D1, D2, or
student evaluation), the writer returned `ready` for both examples:

- [Consistency example](../../experiments/results/validation/20260915_102850_d3_two_examples_luna/consistency.json):
  preserved the two score lists and invited calculation, plotting, or another
  justified approach without naming variance.
- [Average-speed example](../../experiments/results/validation/20260915_102850_d3_two_examples_luna/average_speed.json):
  preserved the four segment lists, the equal-total-distance condition, and an
  open comparison request without giving the overall-rate formula.

Both fixed arithmetic plans were accepted before writing, and each exact writer
request and raw response was saved. This is a small calibration of prompt
following, not evidence that the tasks are productive for students or that the
writer generalizes beyond these examples.

## 8. D4: verification and the role of MCQ

D4 distinguishes three evidence channels:

1. **Deterministic calculation checking:** Does a supplied condition hold under
   the proposed values? Exact evaluation verifies that expression, not the model's
   interpretation of the design or the final prose. Unsupported operations and
   unknown results remain warnings in current D2b. Historical plan checkers could
   block unsupported targets and additionally check declared prior contrasts.
2. **Textual claim judgment:** Does supplied wording support a noncomputed claim?
   The same data model call quotes relevant evidence and explains its scope.
   Supported claims are model judgments; uncertainty warns, and a known essential
   contradiction requests design review. This is not independent verification.
3. **Optional model-consistency probe:** Given a closed version of the same
   data, does an LLM repeatedly choose the intended wrong option? This tests
   whether the error is stable for that model, not whether real students will
   make it.

MCQ generation is useful here only as a cheap, optional probe for a specific
tempting error or for generating Eedi-style `[tempting_mistake]` candidates.
Its answer choices come from the known prior procedures plus the correct
answer. The interpretation is:

```text
intended wrong option -> model recognizes the proposed trap
correct option         -> model did not fall for it
different wrong option -> another pathway may be more salient
unstable choices       -> ambiguous or model-sensitive candidate
```

Self-agreement is therefore a stability signal, not behavioral validation.
MCQ remains outside the PF-writer prompt.

### Separate final-task quality judge: paper-aligned Luna check (September 23)

The final PF-quality judge is separate from the D2 selector, mathematical
reviewer, and MCQ distractor rubric. Its
[shared prompt](../../src/evaluation/prompts/pf_rubric.yaml) restores all fifteen
scoring anchors from [Rahimi et al. (2025), Table 1, p. 2](../../thesis/otherpapers/paper_135.pdf),
verified against the PDF after whitespace normalization. It retains five
dimensions, each rated 1--3: activation of prior knowledge (APK), sweet spot
calibration or difficulty fit (SSC), affective engagement (AE), multiple
representations and solutions (MR), and open-endedness/ill-structuredness (OE).
The total is 5--15; higher means stronger ratings under this rubric, not measured
student learning. No target score distribution or published model mean is used.

The previous added rules about engineered wrong answers, named characters,
numbers of display formats, and unique numerical answers are removed.
Brief evidence accompanies each rating. The
[rating contract](../../src/evaluation/pf_rubric.py) rejects malformed or
out-of-range scores and computes the total rather than trusting a model sum.
Insufficient evidence remains `null`, with no total if any dimension is missing;
API and parsing failures retain explicit error states and no scores.
Mathematical concerns are separate model claims, not a sixth score or a
replacement for deterministic checking.

The [saved-input runner](../../scripts/run_pf_judge.py) defaults to `luna`, using
the existing client adapter. It sends only title, body, question, grade/subject/
jurisdiction, and the prior-resource names and descriptions of prior instruction.
It excludes teacher notes, target-method descriptions, proposed student moves,
claims about why they fail, and condition labels. This input policy, structured
JSON output, and missing-rating handling are our operational choices, not a
claim that the paper specified an identical protocol.
The [development notebook](../../notebooks/05_pf_evaluation_round1.ipynb) now
uses the same prompt and rating function with Luna. Its historical generator
does not record explicit prior instruction, which remains unknown rather than
invented. The [exact old notebook](../../experiments/results/validation/20260923_pf_judge_luna_v1/legacy_05_pf_evaluation_round1.ipynb)
is preserved; obsolete outputs were cleared from the revised notebook.

#### Observed smoke check, not human calibration

One frozen-prompt rating was requested for each of three saved writer outputs
and two [synthetic controls](../../experiments/configs/pf_judge_controls.json).
All **5/5 calls returned complete, schema-valid ratings**, with zero API or
parsing errors. This establishes execution and output validity only.

| Input | APK | SSC | AE | MR | OE | Total |
|---|---:|---:|---:|---:|---:|---:|
| Saved average-speed task | 3 | 2 | 2 | 2 | 1 | 10 |
| Saved consistency task | 3 | 2 | 2 | 3 | 2 | 12 |
| Saved fair-division task | 3 | 2 | 2 | 2 | 2 | 11 |
| Synthetic prescribed division, plain | 3 | 1 | 2 | 1 | 1 | 8 |
| Same division with added presentation | 2 | 1 | 2 | 1 | 1 | 7 |

The controls are illustrative tasks, not human-rated reference cases. Their
matching low MR and OE scores are useful evidence that added presentation did
not inflate those dimensions in this pair. Their different APK scores despite
identical mathematics and learner context expose inconsistent prerequisite
counting. One call per input does not establish repeatability.

Luna also made an incorrect mathematical claim: its proposed fair-division
allocation gives C Piece 3, valued at 2, although C's fair-share benchmark is
`(4 + 3 + 2) / 3 = 3`. The saved raw response is unchanged; the
[inspection record](../../experiments/results/validation/20260923_pf_judge_luna_v1/inspection.json)
flags this error. Its suggestion to specify a spread measure in the consistency
task is not automatically a valid repair: selecting a measure is part of the
intended student exploration.

The actual model selector resolved to `gpt-5.6-luna`. Requested temperature was
0.0, but the GPT-5 adapter omits temperature; the effective completion budget
was 4,000 tokens, with JSON mode and a 180-second timeout. Exact inputs, prompt,
raw responses, source hashes, and settings are retained in the
[run manifest](../../experiments/results/validation/20260923_pf_judge_luna_v1/smoke/manifest.json),
[ratings](../../experiments/results/validation/20260923_pf_judge_luna_v1/smoke/ratings.jsonl),
and [summary](../../experiments/results/validation/20260923_pf_judge_luna_v1/smoke/summary.json).
No exercises were regenerated and no prompt revision was made after seeing
these ratings. Focused validation passed 27 tests, targeted Ruff, and compilation.

```bash
./.venv/bin/python scripts/run_pf_judge.py \
  --audit experiments/results/validation/20260922_writer_rules_v2/comparison_audit.json \
  --cases kapur_average_speed_g7_singapore loibl_variance_g10_nrw \
          kerrigan_fair_division_undergrad_usa \
  --controls experiments/configs/pf_judge_controls.json \
  --model luna --output <new-output-directory>
```

Add `--dry-run` to validate and save inputs without loading a model client.
Existing output directories are refused. The original study used trained,
independent, blinded human raters; this automated smoke check does not reproduce
that procedure, its controlled topic/grade design, or its sample size. Luna also
wrote these saved tasks, so it is not a different-model evaluator. Human
agreement and independent holdout checks remain necessary before using its
ratings as validated benchmark outcomes. Student approach diversity and learning
remain separate, unmeasured outcomes.

### Paper-setting method benchmark: protocol and results (September 23)

The user approved a full **120-attempt** comparison, not another judge
calibration round. The frozen input specification is
[pf_paper_benchmark.json](../../experiments/configs/pf_paper_benchmark.json).
The run started on September 23 at 07:03 UTC, after runner validation; it did
not run during the preceding night. Artifacts are in
[20260923_luna_v1](../../experiments/results/pf_paper_benchmark/20260923_luna_v1/).
The initial technical batch used the first scheduled attempt in each condition,
not extra calibration cases. All four produced ready tasks, and PIPELINE's
14 calls had paired trace records with no API errors. These four attempts count
toward the 120; this is execution evidence, not task-quality validation.
The remaining 116 attempts used the same frozen settings. The run completed
at 09:33 UTC, approximately 150 minutes after launch, including the initial
technical batch and final judging.

| Condition | Method | Scheduled attempts |
|---|---|---:|
| V1 | Paper-style direct generation without supplied misconceptions | 30 |
| V2 | The same direct prompt with six documented Eedi misconception labels | 30 |
| V3 | The same direct prompt with six freshly Luna-inferred misconceptions | 30 |
| PIPELINE | Current prior-resource, situation, planning, review, fill/check, and writer stages | 30 |

The primary comparison is PIPELINE versus V1; V2 and V3 versus V1 are
secondary comparisons. All generating and evaluating calls use Luna, rather
than confounding generation method with model identity. This is a comparison
of complete methods, including their different selection and checking costs,
not an equal-compute test of decomposition alone.

The fixed setting follows Rahimi et al. (2025): Grade 7, proportional
relationships (7.RP.A.2), sports/basketball/Stephen Curry, and prior instruction
in unit rates (7.RP.A.1) and rational-number operations (7.NS.A.1). The official
7.NS.A.1 standard specifically covers addition/subtraction; the benchmark does
not silently expand that code to other standards. Each run receives the same
specification, without the historical seven design briefs or previous outputs.

The existing USA curriculum corpus covers statistics rather than this ratio
setting. For this controlled comparison, PIPELINE maps and expands a fixed
packet of the two official prior-standard excerpts, freshly per attempt.
It may unpack these supplied skills but may not introduce additional assumed
instruction. The excerpts, source URLs, retrieval date, and common learner
context are stored in the configuration. This controls the prior repertoire;
it is not an evaluation of curriculum retrieval accuracy.

The [direct-generation prompt](../../src/generation/prompts/pf_paper_benchmark.yaml)
is a reconstruction of the paper's six described components. It uses all
fifteen published Table 1 anchors and five short, attributed task adaptations
from the CC-BY-4.0 StratL dataset. The PDF does not supply the exact prompt or
identify its five example texts, so neither is claimed to be recovered.
The paper's prose mentions six evaluation criteria, but Table 1 contains five;
we consistently use the five published dimensions.

V1/V2/V3 retain the historical distinction in misconception input, not the
historical generation prompt. V2 uses exact Eedi mapping entries
105, 2378, 806, 2071, 2356, and 624. Two older prompt labels without exact
mapping matches are omitted rather than asserted to be verbatim Eedi entries.
V3 requests the same count, but its outputs remain model hypotheses.

The protocol retains current bounded within-pipeline repairs and forbids
manual rescue or replacement of unsuccessful attempts. A software/transport
failure is not a pedagogically rejected exercise. Thirty attempts need not
produce thirty tasks, unlike the paper's thirty completed problems per model;
both attempted and completed denominators must be reported. Prompt changes
after inspecting benchmark outcomes would require a separately identified run.

The frozen final Luna rubric rates ready student-facing tasks once in a
seeded shuffled order, using the identical fixed learner context in every
condition. It does not receive condition labels, teacher notes, predicted
student approaches, or pipeline review results. Missing ratings remain
missing. Report dimension/total scores and their uncertainty alongside
completion counts, stage failures, and computational cost. Deterministic
pipeline mathematics checks are not available for unstructured direct tasks;
those tasks must be labelled not checked, not invalid. Luna's separate
mathematical concerns are unverified claims, not equivalent checks.

The original study's GPT-4o/Phi-3 comparison and independent human-rating
procedure are not reproduced. Luna is both generator and evaluator. Neither
rubric scores nor successful pipeline checks demonstrate real student
approach diversity, productive failure, or learning.

#### Completed results

All **120 scheduled attempts** reached a recorded outcome, and all **107 ready
tasks** received exactly one complete final Luna rating. Source hashes were
unchanged. The offline audit verified identical sanitized learner inputs,
the frozen shuffled rating order, paired call traces, and no repeated final
rating requests. No unsuccessful attempts were replaced.

| Condition | Ready / attempted | Review stops | API-failed attempts | Mean total / 15 | Score SD |
|---|---:|---:|---:|---:|---:|
| V1 | 30/30 | 0 | 0 | 14.43 | 0.50 |
| V2 | 30/30 | 0 | 0 | 14.27 | 0.69 |
| V3 | 30/30 | 0 | 0 | 14.07 | 0.58 |
| PIPELINE | 17/30 | 9 | 4 | 10.47 | 1.59 |

Higher totals mean stronger **Luna rubric ratings**, not greater measured
learning. SD describes the spread of scores. Scores are conditional on
successful generation and rating; blocked and failed attempts are not zeroes.
The primary PIPELINE-minus-V1 mean difference was **-3.96 points** over
17 versus 30 rated tasks, with an exploratory 95% independent-group bootstrap
interval of **[-4.68, -3.18]**. This resamples the observed task scores 2,000
times; it does not measure human agreement or replace the paper's t-test.
Secondary differences were V2-minus-V1 **-0.17 [-0.50, 0.13]** and
V3-minus-V1 **-0.37 [-0.63, -0.10]**.

The largest primary dimension gaps were difficulty fit (PIPELINE **1.65**
versus V1 **3.00**) and openness (**1.12** versus **2.47**), each on a scale
where 3 is the strongest model rating. These results do not support a quality
advantage for the current pipeline in this setting. The judge also gave all
90 direct tasks the maximum approach-variety score, limiting its ability to
distinguish those methods on this important outcome.

The pipeline's nine stops occurred at review, before numerical filling.
Seven saved stop reasons mention requirements about variation across a
collection of tasks, which the current plan checks for only one task at a
time. The remaining reasons concern unenforced numeric/no-rounding conditions
and a non-operational "non-obvious pattern" requirement. These are recorded
review/checker limitations, not proof that nine mathematically invalid student
tasks were rejected. Four other attempts ended with API connection/timeout
errors. All 17 produced pipeline tasks had accepted deterministic fills;
this does not independently validate the final wording or pedagogical quality.

Generation made **30, 30, 60, and 424 API requests** for V1, V2, V3, and
PIPELINE respectively; lower counts mean less request cost, not equal work
per request. Final judging added **107 requests**, giving **651 in total**.
The pipeline's four API-failed attempts contain seven failed requests.
Token usage is recorded for every direct-generation and final-judge response,
but unavailable for pipeline generation, so a complete token/currency cost
comparison is unavailable. All requests specified `gpt-5.6-luna`; the 227
responses with captured model metadata reported `gpt-5.6-luna-2026-07-09`.
The pipeline adapter does not expose response-model metadata.

The judge supplied mathematical cautions for 91 tasks, including ambiguous
criteria that may be intentional in open tasks; these are not 91 confirmed
errors. Human ratings, repeat-judge reliability, and student outcomes remain
unmeasured. Next research work should inspect the pipeline's closed-task
tendency and single-task versus task-collection requirements, retaining this
run unchanged rather than adjusting prompts to improve its scores.

Artifacts: [visual comparison](../../experiments/results/pf_paper_benchmark/20260923_luna_v1/comparison.html),
[full numerical summary](../../experiments/results/pf_paper_benchmark/20260923_luna_v1/summary.json),
[attempt and trace audit](../../experiments/results/pf_paper_benchmark/20260923_luna_v1/audit.json),
and [frozen manifest](../../experiments/results/pf_paper_benchmark/20260923_luna_v1/manifest.json).
Implementation: [runner](../../scripts/run_pf_paper_benchmark.py) and
[offline report](../../scripts/report_pf_paper_benchmark.py). The targeted
runner, protocol, diagnostic, judge, and reporting checks passed **71 software
tests**; these tests are not evidence of PF effectiveness.

#### Exploratory post-benchmark pipeline revision

The v1 comparison revealed an unmatched prompt condition: direct generation
received Rahimi Table 1 anchors, while the pipeline did not. The revised
[situation prompts](../../src/generation/prompts/situation_skeletons.yaml)
give the same anchors to proposal and writing, ask for an interpretable
consequence around one checkable mathematical decision, and forbid numerical
requirements spanning multiple independently generated tasks. They keep
unrepresentable requirements blocking rather than declaring them checked.
Proposal and selection also discourage trivial repeated-input shortcuts and
ambiguous references to "one constant rule" when a shared multiplier is meant.
The checker, final judge, direct prompt, curriculum evidence, target, and grade
were not changed. This is a post-hoc, exploratory method revision, not a
pre-registered or equal-compute comparison with v1.

Two abandoned technical batches remain frozen: [v2](../../experiments/results/pf_paper_benchmark/20260923_luna_v2/)
produced 1/3 pipeline tasks, and [v3](../../experiments/results/pf_paper_benchmark/20260923_luna_v3/)
produced 3/3, but one had a repeated-input shortcut. Both batches attempted
only the first 3 of 30 scheduled tasks per condition, are incomplete, and did
not run the benchmark's final judge. Six disjoint Luna-agent checks of three v3
pipeline and three direct tasks informed the question-clarity and shortcut
corrections; these checks were not human or student observations. A separate
[five-task judge smoke check](../../experiments/results/pf_paper_benchmark/20260923_v3_v4_pilot_judge/)
rated three v3 pipeline tasks 13, 10, and 13/15 and two v4 tasks 11 and 12/15.
This small, selected calibration is not the final comparison.

The frozen [v4 run](../../experiments/results/pf_paper_benchmark/20260923_luna_v4/)
uses [six-worker configuration](../../experiments/configs/pf_paper_benchmark_v2.json).
Its first three pipeline attempts produced two checked tasks and one honest
planning stop. The remaining 108 scheduled attempts used the same source
hashes. The [saved audit](../../experiments/results/pf_paper_benchmark/20260923_luna_v4/audit.json)
confirmed intact frozen sources, no trace mismatches, the frozen blinded judge
input, and one complete rating for each of 112 ready tasks.

| Condition | Ready / attempted | v4 Luna mean / 15 | v1 Luna mean / 15 |
|---|---:|---:|---:|
| V1 | 30/30 | 14.40 | 14.43 |
| V2 | 30/30 | 14.03 | 14.27 |
| V3 | 30/30 | 14.20 | 14.07 |
| PIPELINE | 22/30 | 11.82 | 10.47 |

The pipeline produced five more tasks per thirty attempts and its mean score
among ready tasks rose by **1.35/15**. Its v4 difference from the concurrent
V1 mean was **-2.58 points** over 22 versus 30 rated tasks (exploratory
independent-group bootstrap 95% interval **[-3.06, -2.06]**), compared with
v1's difference of **-3.96 points**. The largest within-pipeline rating gain
was difficulty calibration (**1.65 to 2.32/3**), followed by approach variety
(**2.53 to 2.91/3**); openness remains low (**1.12 to 1.32/3**). APK did not
improve. These are model judgments on different ready subsets, not measured
student behavior or causal isolation of a particular prompt edit.

The v4 pipeline recorded one planning-review stop and **seven API timeouts**
(v1: nine review stops and four API failures); timeouts are technical losses,
not rejected exercises. Increased six-worker concurrency and variation
between generated attempts also limit causal interpretation. All 22 ready
pipeline tasks passed deterministic plan/fill checks, which do not validate
their student-facing pedagogy. The final [summary](../../experiments/results/pf_paper_benchmark/20260923_luna_v4/summary.json)
and [comparison](../../experiments/results/pf_paper_benchmark/20260923_luna_v4/comparison.html)
preserve denominators and ratings.
The [side-by-side exercise browser](../../experiments/results/pf_paper_benchmark/exercises_side_by_side.html)
shows every scheduled attempt from both v1 and v4 in aligned V1/V2/V3/PIPELINE
columns, with ready tasks, recorded failure states, run switching, and text
search. Each ready card also shows the frozen Luna score and its per-dimension
reasons, plus the earlier coding-agent score and rationale wherever a saved
review exists. Attempt numbers align the fixed specification only; generated
tasks are independent.

Six disjoint Luna-agent quality reviews inspected all 22 v4 ready pipeline
tasks and did not identify a high-confidence arithmetic/plan mismatch. These
are exploratory model judgments, not independent human ratings. Some tasks
offer only table/graph/display options, which are not distinct mathematical
approaches, and PIPELINE-002 may invite unsupported inference about an unseen
practice segment. The checked plans expose a stronger structural limitation:
**22/22 use an equality-of-rates answer rule**, all 22 have their first two
rates equal, and **21/22** differ in a later rate. Thus the higher approach-
variety rating (**2.91/3**) measures the judge's impression, not demonstrated
task-form or student-solution diversity. The task revisions improved this
judge's score and completion in this setting but have not established the
thesis's decisive student-outcome claim.

##### Re-rating the saved tasks with the earlier coding-agent setup

The earlier [17-task retrospective review](../../experiments/results/pf_paper_benchmark/20260923_pipeline_legacy_rubric_review.json)
used coding agents and the rubric card and calibration note in
[notebook 06](../../notebooks/06_pf_human_evaluation.ipynb), not the frozen
benchmark judge. To repeat **that** setup, six GPT-6 Luna coding agents
independently rated disjoint batches of the **22 saved v4 ready pipeline
tasks**, seeing only each student task and the shared learner context. No
tasks were regenerated or swapped. The
[22-task review](../../experiments/results/pf_paper_benchmark/20260923_pipeline_v4_legacy_rubric_review.json)
records source-text hashes, rubric-card hash, scores, and task-level evidence.

| Measure | Earlier coding review: v1, 17 ready | Same coding review: v4, 22 ready | Frozen judge: same 22 v4 tasks |
|---|---:|---:|---:|
| APK / 3 | 2.00 | 2.00 | 2.32 |
| SSC / 3 | 1.76 | 2.05 | 2.32 |
| AE / 3 | 2.00 | 2.00 | 2.95 |
| MR / 3 | 2.18 | 2.00 | 2.91 |
| OE / 3 | 1.18 | 1.50 | 1.32 |
| **Total / 15** | **9.12** | **9.55** | **11.82** |

The earlier coding-agent setup estimates only a **0.43-point increase out of
15** on the ready subsets, rather than the frozen judge's **1.35-point**
v1-to-v4 increase. On the exact same 22 v4 tasks, the frozen judge rates
**2.27 points higher** than the coding-agent review, particularly on
engagement and approach variety. These model-dependent ratings cannot
establish that students would use distinct approaches. The original
historical coding-agent model and exact review prompt were not preserved;
both retrospective reviews follow the notebook card and calibration note,
not a replicated human-rating protocol. Different ready subsets (17/30
versus 22/30) also preclude attributing the difference solely to prompt
changes.

To answer how the **other v4 conditions** score under this same earlier
rubric, six additional coding agents rated all **90 saved direct tasks**.
Tasks were assigned opaque IDs before review; each agent received five V1,
five V2, and five V3 tasks in shuffled order, with no condition labels or
frozen-judge scores. No tasks were regenerated. The
[condition-blind ratings and audit hashes](../../experiments/results/pf_paper_benchmark/20260923_v4_direct_initial_judge_review.json)
and [six batch files](../../experiments/results/pf_paper_benchmark/20260923_luna_v4_direct_legacy_batches/)
preserve the individual evidence.

| v4 condition | Ready / attempted | Initial coding-agent mean / 15 |
|---|---:|---:|
| V1: direct, no misconception input | 30/30 | 12.67 |
| V2: direct with supplied misconception labels | 30/30 | 12.60 |
| V3: infer misconceptions, then generate | 30/30 | 12.63 |
| PIPELINE | 22/30 | 9.55 |

The means for V1, V2, and V3 differ by at most **0.07 points**; this review
does not distinguish them meaningfully. The v4 pipeline's initial-rubric
mean remains lower, but pipeline and direct results condition on different
ready subsets (22 versus 30). Both studies are AI coding-agent judgments,
not human ratings or evidence of actual student approach diversity.

### Exploratory task-level reratings with Rahimi Table 1 (September 25)

The frozen [Rahimi Table 1/v1 prompt](../../src/evaluation/prompts/pf_rubric.yaml),
its [rating contract](../../src/evaluation/pf_rubric.py), and all historical
v1 ratings remain unchanged. Two separately hashed adaptations were then
tested. Both retain the five dimensions and all fifteen published anchor texts;
their added rating guidance is an operational interpretation, not Rahimi et
al.'s exact wording. Both reuse the unchanged v1 output schema and 1--3 score
semantics.

The first [v2 prompt](../../src/evaluation/prompts/pf_rubric_v2.yaml) was run
against the original
[September 23 benchmark](../../experiments/results/pf_paper_benchmark/20260923_luna_v1/),
not the later v4 generation set. The original direct-generation prompt already
included all Table 1 anchors, while the pipeline received them only after the
subsequent v4 prompt revision. Therefore this first v2 rerating is not the
matched-anchor-exposure comparison. Its frozen
[protocol](../../experiments/configs/pf_rubric_v2_rerating.json) and
[rerating artifact](../../experiments/results/pf_paper_benchmark/20260925_rahimi_table1_v2_rerating/)
are retained as exploratory history, not replaced. Before calling the model,
the runner froze all 120 attempt records and student-facing inputs with source,
prompt, code, and input hashes.
All conditions receive the same grade, learning target, prior-knowledge list,
subject, and jurisdiction; the common target is included in v2 context even
though the historical v1 judge omitted it. Only title, body, and question vary.
Condition labels, teacher plans/traces, proposed approaches, and review results
are excluded. The original v1 source hashes were verified unchanged.

An eight-task balanced calibration (two seeded selections per condition)
passed API and strict-schema checks, with one request per case. Its scores were
not used to tune the prompt; those eight ratings are included in the full
107-task result, so no task was rated twice. The other 99 ready tasks were then
rated once. All **107/107 ready tasks** received complete ratings. The
remaining **13/120 scheduled attempts** stay unscored: PIPELINE had nine review
stops and four D2/D3 failures. These failures are not zeros.

| Condition | Ready / scheduled (scored) | APK | SSC | AE | MR | OE | Total / 15 |
|---|---:|---:|---:|---:|---:|---:|---:|
| V1 | 30/30 | 2.83 | 3.00 | 3.00 | 2.60 | 2.50 | 13.93 |
| V2 | 30/30 | 2.53 | 3.00 | 3.00 | 2.73 | 2.47 | 13.73 |
| V3 | 30/30 | 2.53 | 3.00 | 2.87 | 2.67 | 2.17 | 13.23 |
| PIPELINE | 17/30 | 2.06 | 3.00 | 2.24 | 2.00 | 1.06 | 10.35 |

Each dimension mean is on its 1--3 scale; each total mean is on the five-dimension
5--15 scale, averaged over the ready tasks shown. The descriptive
PIPELINE-minus-V1 total difference is **-3.58/15** (17 versus 30 rated tasks);
this is not a confirmatory or causal result. SSC reached **3.00 on all 107
ratings**, so the v2 judge did not discriminate conditions on challenge fit in
this sample. MR scores are still model estimates of task affordances, not
observed student approaches. The
[machine-checkable audit](../../experiments/results/pf_paper_benchmark/20260925_rahimi_table1_v2_rerating/audit.json)
revalidated raw-response scores, denominators, common context, and one-call-per-
ready-task tracing.

The 107 calls used Luna (`gpt-5.6-luna-2026-07-09` in response metadata), JSON
mode, temperature 0 (omitted by the GPT-5 adapter), and a 4,000-token output
limit. The API returned **290,397 tokens** (183,147 prompt and 107,250
completion) across 107 requests, with no transport retries. A monetary cost is
not estimated because the Azure account's applicable price is not in the run
metadata.

This is a post-hoc exploratory rerating of an already inspected benchmark, not
an independent replication. Luna both generated and rated these tasks; there
are no human agreement or repeatability data, and no student behavior or
learning was observed. The original rubric results remain the historical v1
record; v2 changes only the evaluator and shared rating context, not generated
tasks or their generation conditions.

#### Clarified v2.1 interpretation on the v4 benchmark

To make the fairer prompt-exposure comparison, the separate
[v2.1 prompt](../../src/evaluation/prompts/pf_rubric_v2_1.yaml) was applied to
the frozen [v4 generation set](../../experiments/results/pf_paper_benchmark/20260923_luna_v4/).
The v4 source snapshots verify all fifteen published anchors in both the
direct-generation prompt and the revised pipeline proposal/writer prompt.
The v2.1 additions clarify rather than replace the anchors: MR considers both
representations and solution methods (a different display can be a different
representation without being a new method); OE remains anchored to complexity
and integration of variables and representations (consequential choices are
evidence, not a new requirement for a high score). These remain operational
interpretations, not verbatim paper guidance.

The [v2.1 protocol](../../experiments/configs/pf_rubric_v2_1_v4_rerating.json)
froze all 120 v4 attempts and the method-blind inputs before model calls. Each
judge input contains only title, body, question, and the common grade, target,
and prior-knowledge context. No condition labels, teacher traces/labels,
generation traces, review results, or earlier ratings are sent. The
[audit](../../experiments/results/pf_paper_benchmark/20260925_rahimi_table1_v2_1_v4_rerating/audit.json)
verified those exclusions, source hashes, raw-response schemas, and one rating
per ready task.

The balanced eight-task calibration (two per condition) passed call/schema
checks and was included in the full run. All **112/112 ready tasks** received
complete ratings; **8/120 attempts** remain unscored (one review stop and seven
generation/API failures in PIPELINE). The v4 benchmark's original v1 total
means were 14.40, 14.03, 14.20, and 11.82/15 for V1, V2, V3, and PIPELINE.

| Condition | Ready / scheduled | Original v1 total / 15 | v2.1 APK | SSC | AE | MR | OE | v2.1 total / 15 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| V1 | 30/30 | 14.40 | 2.73 | 2.97 | 2.77 | 2.97 | 2.60 | 14.03 |
| V2 | 30/30 | 14.03 | 2.47 | 3.00 | 2.90 | 2.97 | 2.67 | 14.00 |
| V3 | 30/30 | 14.20 | 2.53 | 3.00 | 2.80 | 2.90 | 2.60 | 13.83 |
| PIPELINE | 22/30 | 11.82 | 1.95 | 3.00 | 2.32 | 2.14 | 1.50 | 10.91 |

Dimension means are on the 1--3 scale; totals are on the 5--15 scale and
conditioned on the ready-task counts shown. Under this clarified interpretation,
PIPELINE still rates lower than V1 by **3.12 points/15** (22 versus 30 rated
tasks). This is a descriptive result, not a significance test, causal estimate,
or evidence of actual student approach diversity. The v2.1 rerating used 112
Luna calls and **289,881 returned tokens** (183,064 prompt; 106,817 completion),
with no transport retries; monetary cost is unavailable from Azure metadata.
Luna generated and rated these tasks, and neither human agreement nor student
outcomes were measured.

The v2.1 means point to a task-design gap rather than an omitted pipeline
bonus: relative to V1, PIPELINE is lower on APK (-0.78), AE (-0.45), MR
(-0.83), and OE (-1.10), while SSC is almost tied (+0.03) and nearly at
ceiling. For a concrete illustration, [PIPELINE-005](../../experiments/results/pf_paper_benchmark/20260923_luna_v4/attempts/PIPELINE/005/attempt.json)
asks whether one multiplier fits three rows, whereas
[V1-005](../../experiments/results/pf_paper_benchmark/20260923_luna_v4/attempts/V1/005/attempt.json)
asks students to compare three stations, choose a recommendation, and make
and defend a prediction. These two tasks illustrate a difference, not its
frequency or cause. The [frozen v4 proposal instructions](../../experiments/results/pf_paper_benchmark/20260923_luna_v4/source_snapshot/src/generation/prompts/situation_skeletons.yaml)
permit only one checked scalar, selection, or equality decision per task;
that constraint may help explain narrow questions despite the stated goal
of meaningful interpretation. A defensible improvement would expand the
pipeline's checkable student decisions while keeping its mathematical checks,
then compare newly generated tasks under a frozen, blind protocol. Grounding
and numerical verification are valuable but are not separate Rahimi Table 1
dimensions; evidence of a validity advantage would require applying the
same independent mathematics review to direct and pipeline tasks. Missing
direct-task generation traces are not evidence of invalid mathematics.

## 9. Current status and defensible claims

| Component | Status |
|---|---|
| Direct PF generation baseline | historical benchmarks and current fixed-topic comparisons available; no general superiority of either route established |
| Expert-task and prior-method grounding | implemented for the current expert cells |
| Grounded vs ungrounded D1 comparison | historical three-cell, two-model artifacts supplied/preserved curated records; current curriculum-only holdout recovery is not established by those results |
| Page-level curriculum corpus | implemented; sources and caveats recorded |
| Shared recommendation schema and resource cap | implemented and tested |
| Default D2a design-brief selection | implemented; design opportunities and proposed approaches remain model-generated hypotheses |
| D2b data/check/repair | complete and frozen for the agreed scope; three data calls including invalid replies; values-only numerical repairs; unknown/unsupported claims warn and continue; essential textual contradictions request review |
| Final D2b claim-policy evidence | eight saved proposals rechecked and eight controlled mock repairs; three fixed-design live tasks ready using five data and three writer calls, including two proposal retries and no numerical repair |
| Affected software validation | 551 tests passed with targeted Ruff and compilation in the claim-policy work; full suite not run; not educational validation |
| D3 fixed-data writer | content-based rule and grounded omission records implemented; eight saved writer replays retain raw givens but still show a fair-division intermediate and paraphrased speed advice; disclosure removal is not reliable |
| Optional Learning Commons context | implemented and retained through design, checking, and writing; the Oct. 13 fixed-D1 A/B/C pilot produced 60 tasks, but its corrected model-audit core checklist was supported for only 1/60 and remains unresolved for 59/60 |
| MCQ `[tempting_mistake]` branch | intentionally deferred |
| Fresh direct comparison before final claim policy | six direct and five pipeline tasks ready from six attempts per route; one historical unsupported-claim stop; development-topic comparison, not held-out or budget-matched validation |
| Historical skeleton/plan/review/fill route | retained for explicit legacy protocols and artifact replay; dated results above are not current-default performance estimates |
| Final PF-quality judge | frozen Rahimi Table 1/v1 remains the historical reference; exploratory v2 and anchor-preserving v2.1 reratings are separately versioned above |
| Paper-setting four-method benchmark | original runs and v1 ratings remain unchanged; v2.1 rerated the matched-anchor v4 set, scoring 112/112 ready outputs and retaining 8 non-ready attempts without scores |
| Student-attempt and learning evaluation | not run for these current comparisons; simulator code and earlier MCQ calibration do not establish generated-task PF effectiveness |

The strongest current claim is:

> Literature- and curriculum-grounded records provide a checkable, focused
> source for D1 prior resources, while ungrounded model generation provides
> plausible but unverifiable alternatives. Current D2b records exact checks of
> supplied predicates separately from quoted, model-judged textual claims and
> visible uncertainty, with bounded repair for known numerical failures.
> Neither establishes student approach diversity or a downstream PF effect;
> human or classroom validation remains necessary.

## 10. Reading order and supporting records

1. **This document** - canonical pipeline and thesis framing.
2. [PRIOR_METHODS_BENCHMARK.md](PRIOR_METHODS_BENCHMARK.md) - historical
   error-level benchmark, v5 results, and grounded comparison limitations.
3. [PRIOR_RECOMMENDATIONS_TRACE.md](PRIOR_RECOMMENDATIONS_TRACE.md) - actual
   intermediate records from a grounded and ungrounded run.
4. [KAPUR_BIELACZYC_2012_EVIDENCE.md](KAPUR_BIELACZYC_2012_EVIDENCE.md) -
   verified source evidence and observed RSMs.
5. [data/curriculum_grounding/README.md](../../data/curriculum_grounding/README.md) -
   corpus sources, retrieval, coverage, and caveats.
6. [PF_DESIGN_AUDIT.md](PF_DESIGN_AUDIT.md) - separate qualitative task audit and
   bounded calibration, not observed student behavior.
7. [LEARNING_COMMONS_DATA_FLOW.md](LEARNING_COMMONS_DATA_FLOW.md) and
   [KNOWLEDGE_GRAPH_OPPORTUNITY.md](KNOWLEDGE_GRAPH_OPPORTUNITY.md) - optional
   mathematical-context handoff and its development evidence.
8. [THESIS_STATUS.md](../status/THESIS_STATUS.md) - concise current status across
   generation, MCQ, simulation, and thesis writing.
9. [history/](history/) - superseded narrative and execution records retained for
   provenance.
