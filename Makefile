.PHONY: help setup list generate evaluate inspect figures thesis clean test lint format deploy deploy-scripts logs

PYTHON ?= ./.venv/bin/python
CASE   ?= g6_polygon_area_decomposition
MODEL  ?= luna
MODE   ?= structpf
GROUND ?= auto
EVAL   ?= v30
RUN    ?=

# Show available commands
help:
	@echo "StructPF — Quick Commands"
	@echo "--------------------------------------------------------------------------------"
	@echo "  make setup                             Create .venv, install deps, and init .env.local"
	@echo "  make list [GRADE=7] [SEARCH=area]      List built-in topics and benchmark cases"
	@echo "  make generate CASE=<id> [MODEL=luna]   Generate a PF task (MODE=structpf|oneshot)"
	@echo "  make evaluate RUN=<dir> [EVAL=v30]     Evaluate a saved run (EVAL=v30|task-only|gates|rubric)"
	@echo "  make inspect  RUN=<dir>                Print Stage 1-3 outputs of a saved run (offline)"
	@echo "  make figures  [CHAPTER=3]              Render thesis figures into thesis/figures/"
	@echo "  make thesis                            Build thesis/main.pdf with tectonic"
	@echo "  make test                              Run pytest suite"
	@echo "  make lint                              Run ruff linter and format check"
	@echo "  make format                            Auto-format Python code with ruff"
	@echo "--------------------------------------------------------------------------------"

# Create virtual environment and .env.local template if missing
setup:
	test -d .venv || python3 -m venv .venv
	$(PYTHON) -m pip install -e ".[dev]"
	test -e .env.local || test -e .env || cp .env.example .env.local

# Browse available topics and cases (offline)
list:
	$(PYTHON) scripts/structpf.py list $(if $(DATASET),--dataset $(DATASET),) $(if $(GRADE),--grade $(GRADE),) $(if $(SEARCH),--search "$(SEARCH)",)

# Generate a PF task (defaults: CASE=g6_polygon_area_decomposition, MODE=structpf, MODEL=luna)
generate:
	$(PYTHON) scripts/structpf.py generate --case $(CASE) --mode $(MODE) --grounding $(GROUND) --model $(MODEL) $(if $(OUTPUT),--output $(OUTPUT),)

# Evaluate a generated run directory or task JSON (EVAL=v30|task-only|gates|rubric)
evaluate:
	@test -n "$(RUN)" || (echo "Usage: make evaluate RUN=experiments/results/... [EVAL=v30|task-only|gates|rubric]" && exit 1)
	$(PYTHON) scripts/structpf.py evaluate --run "$(RUN)" --mode $(EVAL) --judge-model $(MODEL) $(if $(CASE_HINT),--case $(CASE_HINT),)

# Inspect a saved run directory offline
inspect:
	@test -n "$(RUN)" || (echo "Usage: make inspect RUN=experiments/results/..." && exit 1)
	$(PYTHON) scripts/structpf.py inspect --run "$(RUN)"

# Render thesis figures (all chapters, or CHAPTER=1..5)
figures:
	$(PYTHON) scripts/structpf.py figures $(if $(CHAPTER),--chapter $(CHAPTER),)

# Build thesis PDF
thesis:
	cd thesis && tectonic main.tex

# Remove LaTeX build artifacts (keeps main.pdf and figures)
clean:
	cd thesis && rm -f *.aux *.log *.out *.toc *.lof *.lot *.bbl *.blg *.fls *.fdb_latexmk *.synctex.gz

# Run tests
test:
	$(PYTHON) -m pytest tests/ -v

# Lint code
lint:
	./.venv/bin/ruff check src/ scripts/ tests/
	./.venv/bin/ruff format --check src/ scripts/ tests/

# Format code
format:
	./.venv/bin/ruff format --exclude src/evaluation/frozen src/ scripts/ tests/

# --- Euler ---
EULER_USER := ouyuxu
EULER_HOST := euler.ethz.ch
EULER_DIR  := /cluster/home/$(EULER_USER)/PFGenThesis

# Sync code to Euler via rsync (fast, no git needed)
deploy:
	rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='.venv' \
		--exclude='*.pdf' --exclude='thesis/' --exclude='notebooks/' \
		./ $(EULER_USER)@$(EULER_HOST):$(EULER_DIR)/

# Deploy just the euler scripts
deploy-scripts:
	scp scripts/euler/*.sh scripts/euler/README.md \
		$(EULER_USER)@$(EULER_HOST):/cluster/home/$(EULER_USER)/scripts/euler/

# Pull logs from Euler
logs:
	@mkdir -p scripts/euler/logs
	rsync -avz $(EULER_USER)@$(EULER_HOST):/cluster/scratch/$(EULER_USER)/logs/ scripts/euler/logs/
