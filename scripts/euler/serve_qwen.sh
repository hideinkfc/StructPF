#!/bin/bash
#SBATCH --job-name=vllm-qwen3
#SBATCH --output=/cluster/scratch/ouyuxu/logs/vllm-%j.out
#SBATCH --error=/cluster/scratch/ouyuxu/logs/vllm-%j.err
#SBATCH --time=4:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem-per-cpu=4G
#SBATCH --gpus=1
#SBATCH --gres=gpumem:80g
#SBATCH --partition=gpu.24h,cuda13pr.24h
#
# Serves Qwen3-30B-A3B via vLLM with an idle timeout watchdog.
# Model is ~60GB at fp16, needs A100-80GB or RTX Pro 6000 (96GB).
# The server auto-shuts down after IDLE_TIMEOUT seconds of no activity.
#
# Usage: sbatch serve_qwen.sh
# Override idle timeout: IDLE_TIMEOUT=3600 sbatch serve_qwen.sh

set -euo pipefail

# --- Configuration ---
IDLE_TIMEOUT=${IDLE_TIMEOUT:-1800}  # Default: 30 minutes
PORT=${VLLM_PORT:-8000}
MODEL="Qwen/Qwen3-30B-A3B"
MAX_MODEL_LEN=8192
LOG_DIR="/cluster/scratch/ouyuxu/logs"

# --- Setup ---
module load stack/2024-06 python_cuda/3.11.6
source /cluster/scratch/ouyuxu/pf-env/bin/activate
export HF_HOME=/cluster/scratch/ouyuxu/hf_cache
export HF_HUB_OFFLINE=1

mkdir -p "$LOG_DIR"

echo "================================================"
echo "Job ID:        $SLURM_JOB_ID"
echo "Node:          $(hostname)"
echo "GPUs:          $CUDA_VISIBLE_DEVICES"
echo "Model:         $MODEL"
echo "Port:          $PORT"
echo "Idle timeout:  ${IDLE_TIMEOUT}s"
echo "Start time:    $(date)"
echo "================================================"

# --- Start vLLM server in background ---
vllm serve "$MODEL" \
    --port "$PORT" \
    --max-model-len "$MAX_MODEL_LEN" \
    --enforce-eager &

VLLM_PID=$!
echo "vLLM PID: $VLLM_PID"

# --- Wait for server readiness ---
echo "Waiting for server to start..."
MAX_WAIT=300  # 5 minutes max for model loading
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -s "http://localhost:$PORT/v1/models" > /dev/null 2>&1; then
        echo "Server ready after ${WAITED}s!"
        break
    fi
    if ! kill -0 $VLLM_PID 2>/dev/null; then
        echo "ERROR: vLLM process died during startup"
        exit 1
    fi
    sleep 5
    WAITED=$((WAITED + 5))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "ERROR: Server did not start within ${MAX_WAIT}s"
    kill $VLLM_PID 2>/dev/null
    exit 1
fi

# --- Idle watchdog ---
echo "Starting idle watchdog (timeout: ${IDLE_TIMEOUT}s)..."
LAST_ACTIVITY=$(date +%s)
PREV_LOG_SIZE=$(wc -c < "$LOG_DIR/vllm-${SLURM_JOB_ID}.out" 2>/dev/null || echo "0")

while kill -0 $VLLM_PID 2>/dev/null; do
    sleep 60  # Check every minute

    NOW=$(date +%s)
    CURRENT_LOG_SIZE=$(wc -c < "$LOG_DIR/vllm-${SLURM_JOB_ID}.out" 2>/dev/null || echo "0")

    # If log size changed, there was activity
    if [ "$CURRENT_LOG_SIZE" != "$PREV_LOG_SIZE" ]; then
        LAST_ACTIVITY=$NOW
        PREV_LOG_SIZE=$CURRENT_LOG_SIZE
    fi

    IDLE_TIME=$((NOW - LAST_ACTIVITY))
    if [ $IDLE_TIME -ge $IDLE_TIMEOUT ]; then
        echo ""
        echo "================================================"
        echo "Idle for ${IDLE_TIME}s (threshold: ${IDLE_TIMEOUT}s)"
        echo "Shutting down at $(date)"
        echo "================================================"
        kill $VLLM_PID
        wait $VLLM_PID 2>/dev/null
        exit 0
    fi
done

echo "vLLM process exited unexpectedly at $(date)"
exit 1
