.PHONY: thesis clean test lint run

# Build thesis PDF
thesis:
	cd thesis && tectonic main.tex

# Clean LaTeX build artifacts
clean:
	cd thesis && latexmk -C

# Run tests
test:
	pytest tests/ -v

# Lint code
lint:
	ruff check src/ scripts/ tests/
	ruff format --check src/ scripts/ tests/

# Format code
format:
	ruff format src/ scripts/ tests/

# Run full pipeline (override CONFIG= to use different config)
CONFIG ?= experiments/configs/rag_fewshot.yaml
run:
	python scripts/run_pipeline.py --config $(CONFIG)

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
