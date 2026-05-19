#!/bin/bash
#SBATCH --job-name=vllm-qwen3-14b
#SBATCH --output=/cluster/scratch/ouyuxu/logs/vllm-%j.out
#SBATCH --error=/cluster/scratch/ouyuxu/logs/vllm-%j.err
#SBATCH --time=4:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem-per-cpu=4G
#SBATCH --gpus=1
#SBATCH --gres=gpumem:40g
#
# Serves Qwen3-14B via vLLM with an idle timeout watchdog.
# Model is ~28GB at fp16, fits on A100-40GB nodes.
# The server auto-shuts down after IDLE_TIMEOUT seconds of no activity.
#
# Usage: sbatch serve_qwen_14b.sh
# Override idle timeout: IDLE_TIMEOUT=3600 sbatch serve_qwen_14b.sh

set -euo pipefail

# --- Configuration ---
IDLE_TIMEOUT=${IDLE_TIMEOUT:-1800}  # Default: 30 minutes
PORT=${VLLM_PORT:-8000}
MODEL="Qwen/Qwen3-14B"
MAX_MODEL_LEN=8192

# --- Environment ---
module load stack/2024-06 python_cuda/3.11.6
source /cluster/scratch/ouyuxu/pf-env/bin/activate
export HF_HOME=/cluster/scratch/ouyuxu/hf_cache
export HF_HUB_OFFLINE=1

echo "=== Job Info ==="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $(hostname)"
echo "GPU: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader)"
echo "Model: $MODEL"
echo "Port: $PORT"
echo "Idle timeout: ${IDLE_TIMEOUT}s"
echo "================"

# --- Start vLLM ---
vllm serve "$MODEL" \
    --port "$PORT" \
    --max-model-len "$MAX_MODEL_LEN" &

VLLM_PID=$!

# --- Wait for server to be ready ---
echo "Waiting for vLLM to start..."
for i in $(seq 1 120); do
    if curl -s "http://localhost:${PORT}/health" > /dev/null 2>&1; then
        echo "vLLM is ready! (took ${i}s)"
        break
    fi
    sleep 1
done

# --- Idle timeout watchdog ---
LAST_ACTIVITY=$(date +%s)

while kill -0 $VLLM_PID 2>/dev/null; do
    # Check if there's been recent activity via the metrics endpoint
    CURRENT_REQUESTS=$(curl -s "http://localhost:${PORT}/metrics" 2>/dev/null | grep -c "vllm:request" || echo "0")

    if [ "$CURRENT_REQUESTS" != "0" ]; then
        LAST_ACTIVITY=$(date +%s)
    fi

    NOW=$(date +%s)
    IDLE_TIME=$((NOW - LAST_ACTIVITY))

    if [ $IDLE_TIME -ge $IDLE_TIMEOUT ]; then
        echo "Idle timeout reached (${IDLE_TIME}s). Shutting down."
        kill $VLLM_PID
        wait $VLLM_PID 2>/dev/null
        exit 0
    fi

    sleep 30
done

echo "vLLM process exited."
