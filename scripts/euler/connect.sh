#!/bin/bash
# connect.sh — Helper to find your running vLLM server and set up a tunnel.
#
# Usage (from your laptop):
#   ./scripts/euler/connect.sh
#
# This will:
#   1. Find your running vLLM job on Euler
#   2. Show the node and port
#   3. Open an SSH tunnel so you can access it at localhost:8000

set -euo pipefail

EULER_USER="ouyuxu"
EULER_HOST="euler.ethz.ch"
LOCAL_PORT=8000
REMOTE_PORT=8000

echo "Looking for running vLLM jobs..."
JOB_INFO=$(ssh "${EULER_USER}@${EULER_HOST}" "squeue -u $EULER_USER -h -o '%T %N %j' 2>/dev/null | grep -i vllm | head -1" || true)

if [ -z "$JOB_INFO" ]; then
    echo "No running vLLM job found."
    echo ""
    echo "Start one with:"
    echo "  ssh ${EULER_USER}@${EULER_HOST} 'sbatch ~/scripts/euler/serve_qwen.sh'"
    exit 1
fi

STATE=$(echo "$JOB_INFO" | awk '{print $1}')
NODE=$(echo "$JOB_INFO" | awk '{print $2}')

if [ "$STATE" != "RUNNING" ]; then
    echo "Job is $STATE (node not yet assigned). Wait and retry."
    exit 1
fi

echo "Found job RUNNING on node: $NODE"

echo ""
echo "Setting up SSH tunnel: localhost:$LOCAL_PORT → $NODE:$REMOTE_PORT"
echo "Press Ctrl+C to close the tunnel."
echo ""
echo "Test with:"
echo "  curl http://localhost:$LOCAL_PORT/v1/models"
echo ""
echo "Use in Python:"
echo "  from openai import OpenAI"
echo "  client = OpenAI(base_url='http://localhost:$LOCAL_PORT/v1', api_key='none')"
echo ""

ssh -N -L "${LOCAL_PORT}:${NODE}:${REMOTE_PORT}" "${EULER_USER}@${EULER_HOST}"
