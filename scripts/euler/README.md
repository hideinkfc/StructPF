# Euler HPC Scripts

Scripts for running vLLM model inference on ETH Euler cluster.

## Architecture

```
Your Laptop                     Euler Cluster
┌──────────┐    SSH tunnel     ┌──────────────┐      SLURM      ┌──────────────┐
│  Python   │◄────────────────►│  Login Node  │────────────────►│  GPU Node    │
│  code     │  localhost:8000  │              │                  │  vLLM:8000   │
└──────────┘                   └──────────────┘                  └──────────────┘
                                      │              ┌──────────────────────┐
                                      └──────────────┤  /cluster/scratch/   │
                                                     │  - pf-env/           │
                                                     │  - hf_cache/         │
                                                     │  - logs/             │
                                                     └──────────────────────┘
```

## Quick Start

### First time setup (run once)

```bash
# SSH into Euler and run DIRECTLY on login node (needs internet)
ssh ouyuxu@euler.ethz.ch
bash ~/scripts/euler/setup_env.sh
```

> **Important:** Run on the login node, NOT via `sbatch`. Compute nodes have no internet access.

This creates the Python venv and downloads models. To download Qwen3-14B separately:

```bash
source /cluster/scratch/ouyuxu/pf-env/bin/activate
module load stack/2024-06 python_cuda/3.11.6
HF_HOME=/cluster/scratch/ouyuxu/hf_cache hf download Qwen/Qwen3-14B
```

### Daily workflow

```bash
# 1. Start the server (from Euler login node)
ssh ouyuxu@euler.ethz.ch
sbatch ~/scripts/euler/serve_qwen_14b.sh   # 14B — faster to schedule
# Or: sbatch ~/scripts/euler/serve_qwen.sh  # 30B — needs 80GB node

# 2. Check it's running
squeue -u ouyuxu
# Wait ~2 min for model to load

# 3. Connect from your laptop (opens SSH tunnel)
./scripts/euler/connect.sh

# 4. Use the API at localhost:8000
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-14B",
    "messages": [{"role": "user", "content": "What is 2+2?"}]
  }'

# 5. Stop working — server auto-kills after 30 min idle
#    Or kill immediately:
scancel <job_id>
```

## Scripts

| Script | Purpose |
|--------|---------|
| `setup_env.sh` | One-time: create venv + download model |
| `serve_qwen.sh` | Start vLLM server — Qwen3-30B-A3B (needs 80GB GPU) |
| `serve_qwen_14b.sh` | Start vLLM server — Qwen3-14B (fits on 40GB GPU) |
| `connect.sh` | Find running server + open SSH tunnel from laptop |

## Models

| Model | Size | GPU Requirement | Nodes |
|-------|------|-----------------|-------|
| Qwen/Qwen3-30B-A3B | ~60GB fp16 | A100-80GB | eu-a65-05/06/07, eu-ts-01/02 |
| Qwen/Qwen3-14B | ~28GB fp16 | A100-40GB | eu-a65-02/03/04 |

> **Tip:** The 14B model is recommended for daily use — 40GB nodes have better availability on the `gpupr.4h` shareholder partition.

## Configuration

### serve_qwen.sh (30B model)

| Variable | Default | Description |
|----------|---------|-------------|
| `IDLE_TIMEOUT` | 1800 (30 min) | Seconds of inactivity before shutdown |
| `VLLM_PORT` | 8000 | Port for the OpenAI-compatible API |
| `--time` | 4:00:00 | Max walltime (hard cap) |
| `--gres=gpumem` | 80g | Min GPU memory (A100-80GB) |
| `--cpus-per-task` | 16 | CPU cores |

### serve_qwen_14b.sh (14B model)

| Variable | Default | Description |
|----------|---------|-------------|
| `IDLE_TIMEOUT` | 1800 (30 min) | Seconds of inactivity before shutdown |
| `VLLM_PORT` | 8000 | Port for the OpenAI-compatible API |
| `--time` | 4:00:00 | Max walltime (hard cap) |
| `--gres=gpumem` | 40g | Min GPU memory (A100-40GB) |
| `--cpus-per-task` | 8 | CPU cores |

Override idle timeout:
```bash
IDLE_TIMEOUT=3600 sbatch scripts/euler/serve_qwen_14b.sh  # 1 hour
```

### Using in Python

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="none",  # no auth needed
)

response = client.chat.completions.create(
    model="Qwen/Qwen3-14B",  # or "Qwen/Qwen3-30B-A3B" if using the 30B script
    messages=[{"role": "user", "content": "Solve: 3x + 5 = 20"}],
    max_tokens=512,
)
print(response.choices[0].message.content)
```

## Cluster Info

- **Shareholder group:** `es_sachan`
- **Partition:** `gpupr.4h` (auto-assigned by scheduler, overrides `--partition`)
- **Max walltime:** 4 hours (shareholder limit)
- **Available GPUs:** A100-40GB (eu-a65-02/03/04), A100-80GB (eu-a65-05/06/07, eu-ts-01/02)

## Paths on Euler

| Path | Contents |
|------|----------|
| `/cluster/scratch/ouyuxu/pf-env/` | Python virtual environment |
| `/cluster/scratch/ouyuxu/hf_cache/` | Downloaded model weights |
| `/cluster/scratch/ouyuxu/logs/` | SLURM job output/error logs |

> **Note:** Scratch files are auto-deleted after ~2 weeks of no access.
> Re-run `setup_env.sh` if the model gets cleaned up.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Server doesn't start | Check `logs/vllm-<id>.err` for OOM or CUDA errors |
| Job pending forever | Use `serve_qwen_14b.sh` (40GB nodes have more availability) |
| Can't connect via tunnel | Ensure job is RUNNING, check node name matches |
| Model not found | Re-download: `hf download Qwen/Qwen3-14B` (scratch auto-deletes after ~2 weeks) |
| Port already in use | Set `VLLM_PORT=8001 sbatch serve_qwen_14b.sh` |
| `huggingface-cli` errors | Use `hf` command instead (CLI was renamed) |
