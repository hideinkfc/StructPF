#!/bin/bash
#
# One-time setup: creates Python venv and downloads the model.
# Run this DIRECTLY on the login node (NOT via sbatch — compute nodes have no internet).
#
# Usage: bash ~/scripts/euler/setup_env.sh

set -euo pipefail

LOG_DIR="/cluster/scratch/ouyuxu/logs"
VENV_DIR="/cluster/scratch/ouyuxu/pf-env"
HF_CACHE="/cluster/scratch/ouyuxu/hf_cache"
MODEL="Qwen/Qwen3-30B-A3B"

mkdir -p "$LOG_DIR" "$HF_CACHE"

echo "=== Setting up environment ==="
echo "Time: $(date)"
echo "Node: $(hostname) (login node — has internet)"

# Load Python with CUDA
module load stack/2024-06 python_cuda/3.11.6

# Create venv if not exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at $VENV_DIR..."
    python -m venv "$VENV_DIR"
else
    echo "Venv already exists at $VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# Install packages
echo "Installing vLLM and dependencies..."
pip install --upgrade pip
pip install vllm openai huggingface_hub

# Download model
echo ""
echo "Downloading model: $MODEL (this may take a while ~60GB)..."
export HF_HOME="$HF_CACHE"
hf download "$MODEL"

echo ""
echo "=== Setup complete ==="
echo "Venv:  $VENV_DIR"
echo "Model: $HF_CACHE"
echo "Time:  $(date)"
echo ""
echo "You can now run: sbatch ~/scripts/euler/serve_qwen.sh"
