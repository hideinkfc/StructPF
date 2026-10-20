# StructPF: Pedagogically Sound Productive Failure Task Generation with LLMs

**StructPF** is the research codebase and ETH Master's Thesis repository for generating and evaluating **Productive Failure (PF)** mathematics tasks with Large Language Models.

Instead of asking an LLM to write a story problem and pick its numbers in a single prompt, **StructPF** mirrors how human PF designers work across three checked stages:

1. **Stage 1 — Prerequisite Grounding (`D1`):** Queries the Learning Commons Knowledge Graph (`buildsTowards` prerequisite standards and `supports` learning components) or official curriculum excerpts to list what students already know without leaking the target formula.
2. **Stage 2 — Problem Design & Calculator Verification (`D2a` / `D2b`):** Proposes candidate design briefs (`D2a`) and verifies concrete numbers in a Python SymPy calculator (`D2b`, up to 2 repair rounds) so the intended solution works while familiar shortcuts fall short.
3. **Stage 3 — Open Student Task Writing (`D3`):** Turns the verified setup and numbers into an open student-facing PF problem while withholding internal design notes and grading rubrics.

Generated and human-designed tasks are evaluated with our **requirement-based evaluation framework (`pf-three-role/v3.0`)**, which tests five task-design measures (**Target Alignment**, **Mathematical Validity**, **Prior-Knowledge Accessibility**, **Limits of Familiar Approaches** via a target-blind **Prior-Knowledge Solver** and **Attempt Judge**, and **Room for Invention**) alongside **Gate 1 & Gate 2** progression checks.

---

## 1. Quickstart Setup

Requires **Python $\ge 3.10$**. From the repository root, run:

```bash
make setup
```

This creates `.venv`, installs the package and development tools (`pytest`, `ruff`, `sympy`, `matplotlib`), and copies `.env.example` to `.env` if no `.env` file exists yet.

All API keys and model names are managed in the single central `.env` file at the repository root:

```ini
# 1. Azure OpenAI Deployments (Default for StructPF generation & evaluation)
AZURE_OPENAI_BASE_URL=https://your-resource.services.ai.azure.com/openai/v1
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_LUNA_MODEL=gpt-5.6-luna
AZURE_OPENAI_GPT54_MODEL=gpt-5.4
AZURE_OPENAI_GPT41_MODEL=gpt-4.1
AZURE_OPENAI_GPT41_MINI_MODEL=gpt-4.1-mini

# 2. Learning Commons Knowledge Graph API (Optional; offline snapshot in data/learning_commons/)
LEARNING_COMMONS_API_KEY=your-learning-commons-key-here

# 3. Swiss AI Platform (Optional; used by MCQ distractor experiments)
CSCS_SERVING_API=sk-your-api-key-here
SWISSAI_JUDGE_MODEL=Qwen/Qwen3.5-27B
```

To see all shortcut commands at any time:

```bash
make help
```

## 2. Interactive Demo & Everyday Commands (`make` & `structpf` CLI)

### 2.0 End-to-End Jupyter Notebook Showcase

For an interactive, pre-executed walkthrough with rendered tables, student task cards, `SymPy` calculator checks, solver attempts, and benchmark charts, open **[notebooks/09_structpf_showcase_demo.ipynb](notebooks/09_structpf_showcase_demo.ipynb)**:

- **Use Case 1 — Curriculum-to-Classroom PF Task Authoring:** Traces **Grade 6 Polygon Area (`6.G.A.1`)** across Stage 1 Learning Commons retrieval, Stage 2a design-brief selection, Stage 2b `SymPy` calculator verification, and Stage 3 open student task writing.
- **Use Case 2 — Screening Out `"15 / 15"` Impostor Tasks:** Compares one-shot tasks (including a $15.0 / 15$ rubric task with a geometric contradiction) against expert and `StructPF` tasks across all five `pf-three-role/v3.0` measures.
- **Use Case 3 — Diagnosing & Repairing a Draft Problem:** Runs the **Gate 1 & Gate 2** progression checks across 30 topics and demonstrates live `SymPy` calculator repair on a shortcut-solvable linear-function draft.

You can also run all workflows from the terminal using either `make` shortcuts or `./.venv/bin/python scripts/structpf.py` (installed as `.venv/bin/structpf` after `make setup`).

### 2.1 Browse Topics and Benchmark Cases (Offline)

List all **30 Learning Commons Progression Bridge topics** (Grades 5–10), **8 Classic PF benchmark cases**, and **4 Grade 7 Multi-Theme cells**:

```bash
# List everything
make list

# Filter by grade or keyword
make list GRADE=6
make list SEARCH=polygon

# Or call the CLI directly
./.venv/bin/python scripts/structpf.py list --dataset lc30 --grade 8
```

### 2.2 Generate a PF Task (`StructPF` or `One-Shot`)

Generate a task for any built-in case ID or for your own custom topic:

```bash
# 1. Generate a StructPF task for a built-in Learning Commons topic (Grade 6 polygon area, 6.G.A.1)
make generate CASE=g6_polygon_area_decomposition

# 2. Generate and immediately run the 5-measure v3.0 evaluator
./.venv/bin/python scripts/structpf.py generate \
  --case g6_polygon_area_decomposition \
  --model luna \
  --evaluate

# 3. Compare StructPF (with Learning Commons graph) vs. Ungrounded vs. One-Shot on the same topic
./.venv/bin/python scripts/structpf.py generate --case g8_linear_function_rate_and_initial_value --mode structpf --grounding lc
./.venv/bin/python scripts/structpf.py generate --case g8_linear_function_rate_and_initial_value --mode structpf --grounding none
./.venv/bin/python scripts/structpf.py generate --case g8_linear_function_rate_and_initial_value --mode oneshot

# 4. Generate a task for a custom topic on the fly (with optional Common Core standard code)
./.venv/bin/python scripts/structpf.py generate \
  --grade 7 \
  --standard 7.RP.A.2 \
  --topic "proportional relationships" \
  --target "Recognize and represent proportional relationships between quantities"
```

Each generation run prints the **Stage 1 prior skills**, **Stage 2b calculator check**, and **Stage 3 student-facing task** in the terminal and saves `result.json`, `student_task.md`, and `model_calls.jsonl` under `experiments/results/runs/<timestamp>_<case>_<mode>/`.

### 2.3 Evaluate or Inspect Any Saved Task

```bash
# Full 5-measure evaluation (Task Judge + Prior-Knowledge Solver + Attempt Judge, v3.0)
make evaluate RUN=experiments/results/runs/<your_run_folder>

# Fast 4-measure Task Judge + SymPy calculator check (skips the solver)
make evaluate RUN=experiments/results/runs/<your_run_folder> EVAL=task-only

# Two-Gate Progression Check (Gate 1 K_prior validity + Gate 2 shortcut failure)
make evaluate RUN=experiments/results/runs/<your_run_folder> EVAL=gates

# 5-Dimension Surface Rubric Judge (Rahimi et al., 2025 baseline)
make evaluate RUN=experiments/results/runs/<your_run_folder> EVAL=rubric

# Inspect any saved run directory offline (no API calls)
make inspect RUN=experiments/results/runs/<your_run_folder>
```

### 2.4 Render Figures, Build Thesis, and Run Tests

```bash
make figures               # Render all thesis figures into thesis/figures/ (or CHAPTER=3)
make thesis                # Compile thesis/main.pdf with tectonic
make test                  # Run the pytest test suite
make lint                  # Run ruff linter and format check
make format                # Auto-format code with ruff
```

---

## 3. Repository Structure

| Directory | Contents |
|---|---|
| `scripts/structpf.py` | Unified CLI entry point (`list`, `generate`, `evaluate`, `inspect`, `figures`) |
| `notebooks/09_structpf_showcase_demo.ipynb` | Pre-executed showcase notebook walking through all 3 generation, evaluation, and repair use cases |
| `src/generation/` | Stage 1–3 generators, design briefs (`D2a`), SymPy calculator (`D2b`), retrieval, and YAML prompts |
| `src/evaluation/` | Three-role requirement evaluator (`v3.0`), 5-measure parser, 5D rubric judge, and MCQ metrics |
| `src/evaluation/frozen/` | Frozen evaluator versions `v2.2`–`v2.9`, kept byte-identical to reproduce earlier runs |
| `src/simulation/`, `src/refinement/` | Solution-blind learner prompts and historical profile/refinement prototypes |
| `scripts/` | Benchmark runners, replay tools, figure renderers (`render_fig*.py`), and `scripts/archive/` |
| `data/` | Learning Commons progression snapshot (`30` topics), classic PF tasks, and grounding excerpts |
| `experiments/` | Frozen experiment configurations (`experiments/configs/`) and local run outputs (`experiments/results/`) |
| `thesis/` | Master's thesis LaTeX sources (`sections/`), rendered figures (`figures/`), and compiled `main.pdf` |
| `docs/` | Detailed research logs ([PF_PIPELINE.md](docs/pf-generation/PF_PIPELINE.md), [MCQ_GENERATION_OVERVIEW.md](docs/mcq/MCQ_GENERATION_OVERVIEW.md), [MCQ_EVALUATION_OVERVIEW.md](docs/mcq/MCQ_EVALUATION_OVERVIEW.md), [docs/README.md](docs/README.md)) |
| `tests/` | Unit and regression tests for generators, calculators, evaluators, and dataset schemas |

---

## 4. Reproducing Full Thesis Benchmarks

In addition to single-case runs via `structpf`, the batch runners in `scripts/` reproduce each thesis study:

```bash
# Chapter 3: 4-Topic x 2-Model x 30-Run One-Shot Multi-Theme Study (240 runs)
./.venv/bin/python scripts/run_pf_rahimi_multi_theme.py --help

# Chapter 6: Evaluator v3.0 Calibration & Solver Recall Benchmark (15 expert PF tasks)
./.venv/bin/python scripts/run_pf_v30_calibration.py --help
./.venv/bin/python scripts/run_pf_solver_recall_benchmark.py --help

# Chapter 7: 30-Topic 3-Arm Progression Bridge Study (One-Shot vs. Ungrounded StructPF vs. LC-Grounded StructPF)
./.venv/bin/python scripts/run_progression_bridge_study.py --help

# Offline reports over saved LLM-student / path-coverage pilots (no API calls)
./.venv/bin/python scripts/report_pf_kapur_reference.py --output experiments/results/pf_kapur_reference_20261011
./.venv/bin/python scripts/report_pf_attempt_revision.py --output experiments/results/pf_attempt_revision_20261011
./.venv/bin/python scripts/report_pf_path_coverage_final.py --output experiments/results/pf_path_coverage_final_20261012 --phase final
```

## License

No repository-wide license is declared. Dataset licenses (such as CC BY 4.0 for the Learning Commons Knowledge Graph) and source attributions remain separate; preserve them when reusing artifacts.

