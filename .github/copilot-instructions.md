# Project Guidelines

## Working Agreement

- Treat this repository as thesis research code: preserve experimental provenance and distinguish historical results, current pilot evidence, and proposed work.
- Establish a run's experimental condition from its saved inputs, retrieval records, prompts, and source snapshots, not today's implementation. For example, a historical run that supplied and preserved curated expert resources is not independent expert-list recovery merely because current code now holds those resources out.
- Record meaningful improvement journeys and insights in the nearest existing project Markdown note as they happen, without waiting for a separate documentation request. Include the original problem, change or decision, supporting evidence, remaining limitations, and next implication; distinguish proposals from completed work and preserve historical results. For PF research, use [PF_PIPELINE.md](../docs/pf-generation/PF_PIPELINE.md) as the canonical record rather than creating competing status notes.
- Do not make the user repeat context already present in this file, the repository notes, or the project documents. Check those sources first.
- Think before editing. Identify the concrete file/symbol/behavior, state one local hypothesis and one cheap check, then make the smallest useful edit once the path is clear.
- Prefer implementation over a plan when the request is actionable. Ask only when an ambiguity is genuinely blocking or would change the research meaning.
- Keep changes surgical. Reuse the repository's existing APIs and patterns. Do not refactor unrelated code, revert user changes, commit, or create branches unless explicitly requested.
- Use the available patch or edit tool for manual edits; the tool set can change between turns. Preserve existing formatting and public interfaces. Default to ASCII and avoid comments unless they explain non-obvious logic.
- After the first substantive edit, run the narrowest relevant executable check immediately. Repair and rerun the same check before widening scope.
- For expensive model calls, test a small representative calibration first. Do not tune prompts to one synthetic example or silently present calibration as validation.
- Treat every PF prompt or stage change as a bounded experiment, not open-ended tuning: trace which stage introduced the defect from saved artifacts, state the expected change first, freeze everything else, repeat generation, keep failures, and stop after the agreed rounds. Follow the [pf-experiment-loop skill](skills/pf-experiment-loop/SKILL.md).
- Treat `unknown`, unsupported, missing-path, and failed-parse cases honestly; do not silently convert them to incorrect or failed.
- PF generation uses bounded revision followed by the latest usable draft, not quality-based stop gates. Record unresolved selection, mathematics, and omission findings separately; a produced draft is not a validation pass. Keep genuine API errors, exhausted execution budgets, and absence of usable output explicit. Do not add new quality blockers or indefinite retries without approval.

## Communication

- Apply these communication guidelines across tasks and skills. Adapt suggested response templates to the user's question while preserving any required output format.
- **Give a compact, visually structured layout with 1–2 crisp sentences per section.** Organize substantive replies into 2–3 short sections with clear bold headings (such as **Verdict**, **Why It Works**, **Limitations**), and keep each section to 1–2 fluent sentences (~120–180 words total for a standard question). Never pad sentences or repeat what the diagram already shows.
- **Lead with the plain-English answer.** State the conclusion and the single most important reason in the opening section, weaving in the 1–2 decisive numbers naturally.
- **Keep caveats to one sentence in one place.** State evidence boundaries once inside **Limitations** rather than repeating disclaimers across paragraphs.
- Follow the user's requested scope and order. When they ask several numbered questions, answer each in that order with its own clear heading and 1–2 fluent sentences. Do not expand a discussion of one step into an unsolicited plan for the whole pipeline.
- Start with what happens in the student's task or the user's situation, not internal stage names, schema fields, or validator terminology. Introduce implementation details only after the concept is clear.
- When explaining a method or idea, work through one small numerical example where useful. For a reframe, place the mistaken interpretation next to the correct one. Use before/after comparisons rather than a long survey, and stop once the point is clear.
- For implementation work, give a brief progress update before edits, explain the local decision, then finish with changed files, validation, and remaining limitations.
- Separate what is implemented, what is preliminary evidence, and what has not been run yet.
- For bugs and research findings, distinguish observed behavior, suspected causes, and verified causes. A rejected output may expose a checker limitation rather than a bad task; state which interpretation the evidence supports.
- When a decision is needed, show options with their practical benefit, cost or risk, and your recommendation. Ask one focused question only if the choice is genuinely needed; do not reopen an already approved decision.
- Explain necessary unfamiliar terms briefly when first used. Prefer familiar wording over introducing a technical term and then interrupting the explanation to define it.
- Prefer a plain-English name over jargon. Do not invent shorthand for a concept used only once; write it out instead.
- Say what each reported number counts. For performance measures, also explain whether higher or lower is better; do not invent a quality threshold for a simple count.
- Keep raw identifiers, payloads, and schema details out of the main explanation unless requested or necessary to answer the question. Make precise technical details available separately rather than replacing the explanation with them.
- When reviewing code, lead with findings ordered by severity and include clickable file references; keep summaries secondary.
- Use workspace-relative Markdown links for files, and cite only the 1–2 files that matter most for the answer. Do not use broken citation formats or refer vaguely to line numbers.
- When the user corrects the tone or clarity, apply that feedback in the next reply rather than merely promising a change or defending a skill's template.
- Do not add motivational filler, generic reassurance, or a closing "if you want" sentence.

## Visual Explanations

- Use the [visual-explain skill](skills/visual-explain/SKILL.md) for non-trivial conceptual explanations, findings, brainstorming, pipeline status, and decisions.
- The user finds both long explanations and over-compressed fragments difficult to follow. Keep explanations short, but prioritize complete sentences and clear connections over a fixed word count. Keep diagram labels short too; a wall of text inside boxes is not a visual explanation.
- Choose the shape that shows the mechanism: diagrams for relationships and workflows, plots for measured trends, and annotated examples for mathematics. Use tables for brief comparisons, not as the default for a long process or data trace. A simple factual answer needs no diagram.
- When a graphical explanation is requested, prefer a readable rendered diagram to a dense table or elaborate ASCII layout. Put exact fields and code hooks in optional details or linked artifacts when they would clutter the main picture.
- Prefer one clear visual per idea and explain its conclusion briefly in text. Do not repeat the same information as a diagram, table, and long explanation.
- Use real plots or screenshots for actual experiment or interface evidence; do not invent decorative visuals or make a simple answer elaborate.
- Distinguish teaching examples from measured results. Label synthetic or illustrative scores visibly in any figure that uses them; a clean presentation must not hide their provenance. Software tests, model judgments, and observed student behavior are different kinds of evidence.
- For this thesis, prioritize visuals that clarify direct versus decomposed PF generation, the MCQ-to-PF pathway, metric roles, and experimental conditions.

## Thesis Writing Style

When structuring, drafting, or editing the master's thesis (`thesis/**`) or thesis-facing documentation, follow the full guide in [THESIS_WRITING_GUIDE.md](../docs/status/THESIS_WRITING_GUIDE.md) and the reference style of `2024____JupyRecSys_Ouyu_Selin.pdf`:

- **Pre-LLM human academic quality:** Write a structured, logically coherent thesis where each chapter and subsection teaches the reader a clear idea in natural, connected paragraphs. Keep sections compact and informative, free of fancy filler words or AI buzzwords (*"delve"*, *"tapestry"*, *"leveraging"*, *"paradigm shift"*, *"holistic framework"*), and avoid disconnected bullet dumps.
- **Direct, explanatory `"we"` voice:** Justify every design choice with its practical purpose before naming technical components (*"We have chosen X because we want to analyze Y"*, *"In order to reduce X and obtain more accurate results, we also..."*).
- **Introduction pattern:** Start from a concrete observation about real practice, explain in two plain sentences why the simple baseline falls short (*"While X could be employed..., the success is dependent on... An alternative approach would be..."*), and end with crisp, single-sentence numbered goals (`G1–G3` or `RQ1–RQ3`).
- **Related Work pattern:** For each prior system or baseline, explain how its mechanism works in 3–4 sentences, state its practical limitation (*"However, ... Additionally, ..."*), and close with a short side-by-side synthesis paragraph (*"While A offers..., in contrast, B..."*) that motivates our design.
- **Method subsection pattern:** Open with 1–2 sentences stating what problem the step solves and why, include a simple input-to-output process diagram (`Fig. 1, Fig. 2, ...`), and walk through the diagram linearly (*"An illustration of the entire process is shown in Figure X. Every single case undergoes this process, which has two parts. First, ... The second part entails ... Finally, ..."*).
- **Evaluation & Results pattern:** Explain *why* the evaluation dataset is constructed the way it is before reporting numbers; after each results table, explain the mathematical/structural reason why the metrics behave that way, and contrast concrete high-scoring cases against concrete low-scoring cases to explain why the hard cases failed.
- **ETH LRE figure and diagram style (*MathDial* & *StratL*):** Follow the visual conventions in [plot_eth_style_samples.py](../scripts/plot_eth_style_samples.py) and [docs/status/figures/eth_samples/](../docs/status/figures/eth_samples/)—dashed stage containers with semantic pastel fills (`#DAE8FC` blue, `#FFF2CC` yellow, `#D5E8D4` green, `#F8CECC` red) and embedded worked math examples for diagrams ([eth_sample_1_structpf_diagram.png](../docs/status/figures/eth_samples/eth_sample_1_structpf_diagram.png)), and the multi-hue academic palette (`#C44E52` red, `#DD8452` orange, `#55A868` green, `#4C72B0` steel blue) with open top/right spines and top-centered framed legends for charts ([eth_sample_2_grounding_3arms.png](../docs/status/figures/eth_samples/eth_sample_2_grounding_3arms.png), [eth_sample_3_solver_recall.png](../docs/status/figures/eth_samples/eth_sample_3_solver_recall.png)).

## Thesis Context

The central research question is whether an LLM pipeline can generate Productive Failure exercises that actually elicit multiple meaningful student approaches and productive failure, rather than merely producing polished stories around one procedure.

The pipeline has three broad stages:

1. Generate PF exercises.
2. Evaluate them with simulated students and knowledge-component profiles.
3. Refine the exercises using the observed responses.

Stage 1 is currently implemented as D1 prior resources, D2a design-brief proposal and selection, D2b checked data with bounded repair, and D3 student-task writing. Stages 2 and 3 are not validated: simulated attempts are diagnostic hypotheses, and no real student attempts or learning outcomes have been collected.

For LLM-student research, freeze profiles from prerequisite/history evidence rather than generated approaches or desired mistakes. Keep solutions, target formulas, expected errors and generation ratings outside learner inputs, and include an ordinary-solver control. Written attempts are model outputs, not access to cognition; prescribed-error recovery and non-LLM answer sampling do not validate a learner simulator. Treat truncation as an execution limitation, never as student failure or learning.

The LLM-student/path-coverage/feedback component is closed as a bounded computational pilot. Intended-path coverage is a model-conditional diagnostic with source quotations and unknowns, not a real class distribution, task-quality gate or learning score. Do not automatically restart tuning; preserve the recorded feedback null results and require a newly authorized question/protocol for further experiments. See PF_PIPELINE.md for the final evidence and thesis boundaries.

The PF quality standard is not "no hints". Expert tasks give support but leave the central unknown or key idea for students. Check for conclusion giveaways (stating the target claim as the student's job, or follow-up questions that presuppose it) as well as method hints. Not every familiar method must fail.

Audit rejected designs as well as ready tasks: permission to use partial units may define the problem rather than reveal a solution. Assign `given` versus `teacher_example` from what students must compare or choose; do not withhold a supplied comparison object merely because an internal example verifies it. Fewer ready tasks or fewer calls due to early stops is not automatically better PF generation.

Information the generator withholds from students is internal design information. Call it "internal design notes" or an "internal example"; the pipeline has no human teacher or teacher agent, even though code uses names such as `teacher_example`.

The MCQ stage is a design instrument for discovering concrete, plausible student error pathways that can guide PF exercise generation. It is not the final thesis contribution and should not be evaluated only by how closely it copies Eedi answer strings.

The decisive PF outcomes are representation/solution diversity, open-endedness, mathematical validity, and whether real or simulated students actually produce distinct approaches. A better distractor score alone is not evidence of a better PF exercise.

The thesis aims for both a strong generator and educational findings about how LLMs handle PF design. A clearly recorded null result, such as fewer giveaways without more distinct approaches, is a contribution. Do not claim state-of-the-art without named contemporary baselines, common inputs, independent outcomes and costs, or learning effects without a learner study.

See [PF_PIPELINE.md](../docs/pf-generation/PF_PIPELINE.md), [MCQ_GENERATION_OVERVIEW.md](../docs/mcq/MCQ_GENERATION_OVERVIEW.md), and [MCQ_EVALUATION_OVERVIEW.md](../docs/mcq/MCQ_EVALUATION_OVERVIEW.md) for the current research framing.

## MCQ Evaluation Decisions

Use the smallest defensible metric set:

- **Incorrectness:** deterministic answer-level check; parseable and not equivalent to the correct answer.
- **Student plausibility:** separate compact 0--2 LLM-estimated score inspired by Feng; retain the continuous score and treat `score >= 1` only as a broad screening flag, not as human-validated evidence.
- **Path coherence:** optional check that supplied structured steps reach the distractor. Use it when a pathway is used for PF design or diversity claims, not as a universal requirement for every wrong answer.
- **Pathway diversity:** compare distinct faulty steps, not answer strings. Report it only over candidates with usable coherent paths; otherwise report that it is unavailable.
- **PM:** one-to-one raw/normalized/typed matching against Eedi, retained only as secondary reference alignment.

The current generator supports a basic distractor object with `text`, `target_misconception`, and `error_rationale`, and an optional structured object that adds `faulty_step` and `reasoning_steps`. The structured form is the relevant form for PF pathway experiments. Do not add `predicted_answer` or `student_calculation` unless the schema is deliberately changed and documented.

The historical 10-question pilot is stored in `experiments/results/phase1_mcq/basic_glm_correctness_pilot.json` in the basic format. The older `structured_path_smoke.json` is not authoritative for the current schema. The current viable pilot pool is numeric/equation-focused; a full pathway-to-PF run is still future work.

Do not overfit judge prompts or calibration to a single time, decimal, ratio, or arithmetic example. Use topic-diverse development and holdout cases, keep the judge's limitations visible, and prefer a useful negative result over a forced perfect calibration score.

## Repository Workflow

- Python requirement: `>=3.10`; use the project interpreter at `./.venv/bin/python` when available.
- Focused MCQ tests: `./.venv/bin/python -m pytest -q tests/test_basic_glm_correctness.py`
- Full tests: `make test` or `./.venv/bin/python -m pytest tests/ -v`
- Lint/format checks: `make lint`
- Thesis build: `make thesis`
- Compile a touched Python script: `./.venv/bin/python -m py_compile path/to/file.py`
- Keep reusable implementation in `src/` or `scripts/`; use notebooks for exploration, inspection, and figures. Be alert to stale notebook imports and reload modules after code changes.
- When changing a research decision, update the nearest project note and remove stale claims instead of adding another competing explanation.
- Keep model outputs and calibration artifacts identifiable. Do not overwrite historical results without an explicit reason.
