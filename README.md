# PF Generation: LLM Pipeline for Productive Failure Exercises

> **Master Thesis** — Can an LLM pipeline with simulated-student-driven refinement generate Productive Failure exercises that approach expert quality?

## Overview

This repository contains the code, experiments, and thesis writing for a three-phase LLM pipeline:

1. **Exercise Generation** — Transforms well-structured problems into ill-structured PF exercises guided by Kapur's criteria
2. **Simulated Student Evaluation** — KC-based student profiles attempt exercises to measure RSM diversity and productive failure rates
3. **Iterative Refinement** — Feedback from simulated students improves exercise quality

## Repository Structure

```
thesis/          LaTeX source for the thesis document
src/             Core pipeline code (generation, simulation, refinement, evaluation)
data/            Data pointers and metadata (raw data not tracked)
experiments/     Experiment configurations and results
notebooks/       Exploratory analysis notebooks
scripts/         CLI entry points for running experiments
tests/           Unit and integration tests
```

## Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env
# Add your API keys to .env
```

## Running Experiments

```bash
# Run full pipeline
python scripts/run_pipeline.py --config experiments/configs/rag_fewshot.yaml

# Run baselines
python scripts/run_baselines.py --config experiments/configs/baseline_zeroshot.yaml

# Run evaluation
python scripts/run_evaluation.py --results-dir experiments/results/
```

## Data

- **StratL**: 15 expert-authored PF exercises ([Puech et al., 2025](https://doi.org/...))
- **Eedi**: 15M+ student responses with misconception labels ([Wang et al., 2021](https://doi.org/...))

See [`data/README.md`](data/README.md) for download and setup instructions.

## Building the Thesis

```bash
make thesis
```

## License

TBD
