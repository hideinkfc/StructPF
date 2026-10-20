# PF Generation: Productive Failure Exercise Research

This master's thesis asks whether an LLM pipeline can generate Productive
Failure (PF) exercises that elicit multiple meaningful student approaches,
rather than polished stories around one procedure.

## Current scope

The implemented default generator first anticipates students' prior resources,
selects a task design (`D2a`), checks and, when needed, repairs its numerical
data (`D2b`), then writes the student task (`D3`). It uses the `design_brief`
route, not the older situation-skeleton, mathematical-plan and number-fill
route. The historical route remains in code and saved experiments; the
diagnostic CLI does not expose a switch back to it.

D2b uses a restricted exact calculator and at most three data-model calls,
including invalid proposal retries. Once a proposal is valid, repairs may
change only values, not conditions or the selected design. Known numerical
failures trigger bounded repair; textual conflicts and uncertain claims remain
findings. After bounded selection/data/writer revisions, usable drafts are
delivered with unresolved findings rather than blocked on quality. Mathematical
acceptance, draft availability and educational validity are separate.

D2b is frozen for the agreed implemented scope. Its software checks and saved
pilots are not proof of PF quality. Representation/solution diversity,
open-endedness, mathematical validity and actual student approaches remain the
research outcomes. The simulation/feedback component now has reproducible
solution-blind attempt runners, operational intended-path audits and bounded
matched revision pilots. These are computational diagnostic studies, not a
validated generate -> simulate -> learn system. The old notebook/evaluator
prototype interfaces remain historical and incomplete; use the experiment
entry points below, not those stubs.

MCQ distractors are a separate design instrument, not the final PF outcome.
Their basic fields are `text`, `target_misconception` and `error_rationale`;
optional structured pathways add `faulty_step` and `reasoning_steps`.

Read the canonical notes instead of treating historical scores as current
validation:

- [PF pipeline and evidence](docs/pf-generation/PF_PIPELINE.md)
- [MCQ generation](docs/mcq/MCQ_GENERATION_OVERVIEW.md) and
  [MCQ evaluation](docs/mcq/MCQ_EVALUATION_OVERVIEW.md)
- [Documentation index](docs/README.md)

## Repository structure

| Directory | Contents |
|---|---|
| `src/generation/` | MCQ and PF generators, design briefs, data checks, retrieval and prompts |
| `src/evaluation/` | Answer checks, pathway metrics, PF rubrics and design audits |
| `src/simulation/`, `src/refinement/` | Solution-blind learner prompts and historical profile/refinement prototypes |
| `scripts/` | Current experiment, replay, calibration and reporting entry points |
| `data/` | Local datasets, expert-task transcriptions and grounding artifacts; some inputs are untracked |
| `experiments/` | Configurations, saved evidence and source/prompt snapshots |
| `notebooks/` | Historical experiments, inspection and simulation prototypes |
| `tests/` | Software checks, not student-behavior validation |
| `docs/`, `thesis/` | Research records and LaTeX thesis |

## Setup

Use Python >=3.10 and run commands from the repository root. Reuse an existing
environment; for a new checkout:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -e ".[dev]"
test -e .env || cp .env.example .env
```

Review the template before use, fill in only the services needed, and never
overwrite existing credentials. Python helpers load dotenv files; do not assume
the template is a shell script.

- Default PF runs use Azure: `AZURE_OPENAI_BASE_URL`,
  `AZURE_OPENAI_API_KEY` and the relevant deployment variable, for example
  `AZURE_OPENAI_LUNA_MODEL`. PF helpers load `.env.local` or use exported values.
  Curriculum embeddings use `text-embedding-3-small-EU` on the same Azure endpoint.
- Swiss AI MCQ generation uses `CSCS_SERVING_API`; optional
  `SWISSAI_BASE_URL` and model-role overrides are read by
  [config.py](src/utils/config.py). Some MCQ conditions also need Azure embeddings.
- Euler/vLLM is optional, not required by the default PF route. See
  [Euler setup](scripts/euler/README.md) for its separate GPU environment.
- Learning Commons API context is opt-in and requires
  `LEARNING_COMMONS_API_KEY` on a cache miss; the curated
  [local snapshot](data/learning_commons/README.md) works offline.

## Commands

These inspection commands do not call models:

```bash
./.venv/bin/python scripts/lookup_curriculum_grounding.py --list
./.venv/bin/python scripts/run_prior_recommendations.py --list-cases
./.venv/bin/python scripts/run_pf_diagnostic.py --help
./.venv/bin/python -m scripts.run_basic_glm_correctness_pilot
```

The last command checks the saved historical ten-question basic GLM pilot; it
does not regenerate it. Its `--run` option makes model calls and overwrites that
pilot path, so do not use it to replace historical evidence inadvertently.

The following examples **make model calls** and require local inputs and service
configuration:

```bash
# One-case current PF diagnostic; default route is design_brief
./.venv/bin/python scripts/run_pf_diagnostic.py \
  --cases kapur_average_speed_g7_singapore --model luna --max-workers 1 --proposal-k 4

# Grounded/ungrounded prior-resource comparison against held-out expert lists
./.venv/bin/python scripts/run_prior_recommendations.py --compare-expert --model gpt41mini

# Small structured MCQ generation run, without the historical judge pipeline
./.venv/bin/python scripts/run_phase1_structured_generation.py \
  --condition 02_expert_direct --viable-only --n 2 --runs 1 --workers 1 \
  --results-dir experiments/results/phase1_mcq/new_structured_run
```

PF diagnostics save a timestamped directory under
`experiments/results/validation/` with per-case outputs and model-call traces.
Use a fresh output path for new evidence. `--reuse-d1-root` reuses an earlier
run's prior-resource output; label that condition explicitly rather than calling
it a fresh end-to-end run.

### LLM-student and intended-path research

The [canonical closure and evidence](docs/pf-generation/PF_PIPELINE.md#final-scope-llm-student-path-coverage-and-feedback)
defines the thesis boundary. The diagnostic asks whether mathematical actions
anticipated in a saved design are actually reached in model outputs. It retains
not-observed and unknown cases and unexpected valid approaches; it does not infer
human classroom probabilities or treat missing paths as task defects.

Offline reports over the saved artifacts (no model calls):

```bash
./.venv/bin/python scripts/report_pf_kapur_reference.py \
  --output experiments/results/pf_kapur_reference_20261011
./.venv/bin/python scripts/report_pf_attempt_revision.py \
  --output experiments/results/pf_attempt_revision_20261011
./.venv/bin/python scripts/report_pf_path_coverage_final.py \
  --output experiments/results/pf_path_coverage_final_20261012 --phase baseline
./.venv/bin/python scripts/report_pf_path_coverage_final.py \
  --output experiments/results/pf_path_coverage_final_20261012 --phase final
```

The final campaign source/feedback snapshots, prospective codebooks and fresh
attempts are kept separately. The completed component is a bounded computational
study: path coverage is model-conditional and an added advantage of coverage
feedback is not established. Real student/class distributions and learning remain
outside its evidence. Its model-call runner refuses to overwrite an
existing phase. It is a one-round research protocol, not an automatic tuning
service. Re-running an experiment needs a newly identified output directory
and a budget covering every stage/retry, not a silent replacement of failures.

Focused software checks:

```bash
./.venv/bin/python -m pytest -q \
  tests/test_pf_student_probe.py tests/test_pf_path_coverage.py \
  tests/test_pf_kapur_reference.py tests/test_pf_attempt_revision.py
```

The existing `make run` target still references absent `scripts/run_pipeline.py`
and `rag_fewshot.yaml`; it is not a working entry point. There are also no
`run_baselines.py` or `run_evaluation.py` scripts in the current checkout.

## Data and provenance

- [Expert PF tasks](data/pf_exercises/README.md): paper-derived curated records
  and the separate fifteen-record StratL import; they overlap and are not all
  original, fully specified PF generation tasks.
- [Curriculum grounding](data/curriculum_grounding/README.md): official-document
  excerpts, textbook proxies, translations and held-out expert resources.
- [Learning Commons](data/learning_commons/README.md): curated graph candidates
  and optional remote reference context, not evidence of students' prior learning.
- Eedi inputs are expected under `data/eedi/`; selected scraped quiz data live
  under `data/eedi_scraped/`. See the MCQ notes for exact input files and limits.

## Validation and thesis build

```bash
./.venv/bin/python -m pytest -q tests/test_basic_glm_correctness.py
source .venv/bin/activate
make test                  # full existing test suite
make lint                  # existing Ruff lint/format checks
make thesis                # requires latexmk and a LaTeX installation
```

## License

No repository-wide license is declared. Dataset licenses and source
attributions remain separate; preserve them when reusing artifacts.
