---
name: pf-experiment-loop
description: Plan, run, evaluate and record a bounded PF pipeline experiment so every prompt or stage change yields a better generator or a recorded finding. Use when fixing a generation defect, proposing reruns or sweeps, comparing direct and pipeline generation, automating variant search, or deciding whether to keep tuning.
---

# Bounded PF Experiments

Use this skill to avoid an indefinite prompt-tuning loop. Each change answers an
educational design question, under frozen conditions, within a stated budget.
A null or negative result is a finding to record, not a reason to redefine the
outcome. Follow the [project instructions](../../copilot-instructions.md) for
communication and the canonical record in
[PF_PIPELINE.md](../../../docs/pf-generation/PF_PIPELINE.md).

## Procedure

1. **Start from saved evidence.** Quote the defect from a saved task, brief or
   request. Do not start from a general impression.
2. **Trace where it entered before editing.** Compare the stage inputs and
   outputs: D1 resources, D2a proposals and selection, D2b data roles, the
   writer request, and the final task. Fix the stage that introduced the defect.
3. **State the hypothesis before running.** Write the educational mechanism,
   the observable change you expect, and what would count as no change or a
   regression.
4. **Change one thing, or declare a package.** If several prompt/schema changes
   ship together, say that a gain cannot be attributed to any single part
   without a later ablation, meaning a run that removes one part.
5. **Freeze everything else.** Model and sampling settings, upstream outputs,
   other stages' prompts, evaluation definitions, case set and budget. Use a
   new output directory with source hashes, as in
   [run_pf_topic_sweep.py](../../../scripts/run_pf_topic_sweep.py). Never
   overwrite earlier results.
6. **Calibrate small.** Run one or two cases to catch implementation defects
   only. Calibration is not validation; do not tune toward those cases.
7. **Run with repeats and keep failures.** Generate more than one output per
   case, count stops and invalid outputs in the denominator, and do not replace
   failed attempts. Bounded in-attempt revisions belong to the same attempt;
   retain every request and response, including the original rejected draft.
8. **Evaluate with predefined outcomes, separately.** Evaluation checks first:
   mathematical validity, target preserved, accessible start. Keep unsupported
   cases `unknown`. Then report disclosure, consequential student choices and
   distinct approaches as separate rates, with ready tasks per attempt and model
   calls. Quality findings are revision feedback, not generation stop gates:
   after bounded revisions return the latest usable draft with unresolved
   findings. Ready means produced, not validated. When reading outputs manually,
   hide which version produced them.
9. **Decide and stop.** Keep, revert, or stop the intervention. Allow at most
   three development rounds; stop after two rounds without the predefined gain.
   A genuine checker defect is a separately versioned instrument correction.
10. **Record it.** Add problem, change, evidence, limitations and next
    implication to PF_PIPELINE.md, with a short pointer in
    [THESIS_STATUS.md](../../../docs/status/THESIS_STATUS.md). Record null
    results with the same care.
11. **Promote only frozen versions.** Untouched final topics are evaluated once,
    then reviewed independently. Student claims need student attempts.

## Case-set roles

| Role | Cases | Rule |
|---|---|---|
| Development | The fixed-brief targets in [pf_data_roles_20261011.json](../../../experiments/configs/pf_data_roles_20261011.json) and every topic in [pf_topic_sweep_20261011.json](../../../experiments/configs/pf_topic_sweep_20261011.json) | Already inspected; feedback allowed |
| Transfer check | Sweep topics not used to write the change | Run without retuning; still not an untouched test |
| Final | New topic/task-family specifications | Never used in search; no near-duplicates in prompt examples |

## Evidence ladder

Report each claim at the level the evidence reached:

```text
software tests -> deterministic math checks -> model judgments
  -> assistant reading -> blinded expert ratings
  -> simulated attempts (diagnostic only)
  -> observed student attempts -> learning/transfer after consolidation
```

Task-generation improvement is a design claim. Approach diversity needs
attempts. Learning effects need a learner study with equivalent consolidation.
State-of-the-art needs named contemporary baselines, common inputs, independent
outcomes and costs.

## Reading a task against the PF standard

- Expert tasks give support but keep the central unknown or key idea for
  students. "No hints" is not the standard.
- Check conclusion giveaways as well as method hints: stating the target claim
  as the student's job, or asking a follow-up that only makes sense once the
  claim is accepted.
- Not every familiar method must fail. Do not maximize student failure.
- Different answers or display formats are not different approaches; compare
  the mathematical reasoning.

Teaching example (illustrative, not a run result):

```text
Giveaway: "Make gardens with the same perimeter but different areas."
Open:     "Which garden design gives the most growing space for this fence?"
```

The open version still needs checking: it can collapse to one procedure.

## Wrong versus right

**Wrong:** Edit the writer prompt, regenerate the garden task once, judge it
better, then edit again for the box task. The giveaway came from the selected
design, so writer edits cannot remove it, and one lucky output proves nothing.

**Right:** Trace shows the design proposal and selector introduced the
giveaway. Change design-brief proposal, selection and handoff as one declared
package. Freeze D1 and the other stages, run development targets with repeats
for both versions, read tasks with arm labels hidden, and record the outcome even
if null. Label hiding is not independent human blinding. Run transfer topics
without retuning only when the agreed continuation rule permits it.

## Automation boundaries

The LLM-student/path-coverage/feedback thesis component is closed as a bounded
computational pilot in the canonical record. Do not automatically resume tuning
because intended paths were not observed; a new experiment needs a newly scoped
question, frozen protocol and authorization.

An agent may propose, run and record bounded variants inside a fixed change
surface. It must not edit evaluation definitions, final cases or promotion
decisions, and an LLM judge score is never the sole objective. Public
automated-research systems and their limits are reviewed in
[PF_PIPELINE.md](../../../docs/pf-generation/PF_PIPELINE.md#october-11-automated-research-review-and-proposed-experiment-strategy).

## Learnings

- Verify learner history in the actual serialized API input, not only in the
  task catalog. A `recently_taught` list can disappear when an evaluator
  allowlists only `assumed_prior_knowledge`; reject that mismatch or translate
  the same frozen history explicitly. Preserve an affected run and version
  the corrected-input audit without regenerating its tasks.
- A malformed audit field must not erase valid sibling findings. Keep
  field-local validation errors and raw values, classify that field as unknown,
  and record parser corrections separately from frozen prompts and responses.
  Verified arithmetic or exact quotations establish their narrow checks, not
  complete task mathematics or the educational interpretation.
- Repeated generations within a task specification are not independent
  task-family observations. Report matched per-specification differences and
  block uncertainty, and keep unknown sensitivity separate from sampling
  intervals. A high unknown rate can make a composite uninformative without
  showing that the tasks are bad.
- Use registered agent results and peer `write_agent` for research coordination.
  Host-session `send_message` starts another turn; it is not a passive progress
  notification and can create competing runs or edits. If a parent ID cannot
  be addressed, return the result rather than rerouting progress to a host chat.
- Intended-path reach is conditional on model, profile, task and definition:
  a different model series can enact a route absent in the original cohort.
  Freeze path actions before collecting attempts, report unchanged versus revised
  denominators separately, and keep unexpected valid methods. A specific task-only
  review must be shared by both design-feedback arms; an absent method or more
  path names does not establish an educational improvement.
- For designed-path coverage, distinguish algorithm, insight and representation
  categories, and match the actual mathematical action rather than its name.
  Clearing an algebraic equation with an LCM denominator is not the LCM-based
  partition strategy documented in student work. A normalized individual attempt
  cannot validate a distribution measured from collaborative group exploration;
  missing paths alone do not identify task faults or simulator competence.
- Compare attempt-informed rewriting against a strong task-review-only rewrite
  with identical instructions and request caps. Raw attempts can cause demand
  expansion (for example a universal fairness guarantee without value-divisibility
  assumptions) rather than better PF. Report additional feedback input/acquisition
  costs and test task quality separately from model-attempt correctness.
- Attempt-based feedback needs both task and attempt evidence before suggesting
  a task change. Exact quotations verify source fidelity, not the interpretation:
  continuous timing does not automatically make stage durations cumulative
  timestamps, and asking learners to devise a rule is not a missing supplied rule.
  Calibrate fine method coding separately; preserve disputed findings rather
  than turning model-review labels into automatic revision targets.
- For learner-attempt experiments, freeze prerequisite/history evidence independently
  of desired approaches and supply only student task text plus that evidence.
  A prompt that tells a learner to average speeds incorrectly tests prescribed-error
  obedience, not spontaneous PF behaviour; keep it as a separate calibration arm.
- Compare learner prompts with an ordinary solver and retain all independent
  repetitions, including correct, unfinished and token-truncated outputs.
  A cutoff is an execution limit, not productive failure; naming a new formula
  and constructing it from familiar arithmetic are different observations.
  Aggregate answer matching, written-work variety, human fidelity and learning
  require different evidence; follow the canonical LLM-student research record.
- A rejected design or a malformed omission quote must not erase usable task
  text. Revise within a fixed budget, then keep the draft with unresolved findings
  and original responses; never convert a failed check into mathematical success.
  Genuine API failures or no usable output remain execution errors, not blank
  success-shaped exercises.
- Writer-only fixes left most disclosures because four of five came from the
  selected design. Trace the entry stage before choosing what to edit.
- Optimizing a model-judged score invites reward hacking: the score improves
  while the educational property does not. Keep independent final evaluation.
- Information hidden from students is generator-internal. Call it "internal
  design notes" or an "internal example"; the pipeline has no human teacher or
  teacher agent, even though code uses `teacher_example`.
- Audit rejected proposals against the same task standard as accepted outputs.
  "A partial scoop is allowed" can define the requested measurement without
  prescribing a division algorithm. A selector that calls necessary support a
  giveaway can lower output rates without improving educational quality; preserve
  the disagreement rather than counting every stop as a correct rejection.
- Assign data roles from the student's action, not the presence of an internal
  example. Counts on supplied strips are givens for comparing those strips;
  counts for a strip students must construct are internal feasibility examples.
  Withholding both can leave a mathematically checked design with no usable task.
- Discovery-free wording is not open mathematical work. A fixed combined-mean
  calculation with permission to draw or tabulate may still offer no consequential
  student choice. Track readiness, disclosure, mathematics and choices separately,
  and do not treat fewer calls caused by early stops as automatic efficiency.
