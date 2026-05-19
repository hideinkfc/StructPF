.PHONY: thesis clean test lint run

# Build thesis PDF
thesis:
	cd thesis && latexmk -pdf main.tex

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
