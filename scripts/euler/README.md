# Euler HPC Scripts

Optional vLLM serving on ETH Euler, accessed from the laptop through SSH.
This is separate from the current Azure-backed PF `design_brief` route.
The scripts are specific to the configured account `ouyuxu`; they are not a
portable cluster installer.

## Connection

```text
laptop localhost:8000 --SSH via login node--> allocated GPU node:8000
                                            vLLM OpenAI-compatible API
```

The tunnel must remain open. Closing it does not cancel the Slurm job.

## First-time setup

From the repository root on the laptop, prepare the script destination and
copy the serving scripts using the existing Makefile target:

```bash
ssh ouyuxu@euler.ethz.ch 'mkdir -p ~/scripts/euler'
make deploy-scripts
```

Do not use `make deploy` without reviewing its exclusions: it copies the
checkout to `~/PFGenThesis` and does not exclude local dotenv files or SSH keys.
`deploy-scripts` copies only `scripts/euler/*.sh` and this README.

On the Euler **login node**, run the setup script, not `sbatch`. It installs
vLLM/OpenAI/Hugging Face packages in the scratch environment and downloads
**Qwen3-30B-A3B only**. Both serving scripts set `HF_HUB_OFFLINE=1`, so their
chosen model must already be cached before submission:

```bash
ssh ouyuxu@euler.ethz.ch
bash ~/scripts/euler/setup_env.sh

# Required separately before serving the 14B model
module load stack/2024-06 python_cuda/3.11.6
source /cluster/scratch/ouyuxu/pf-env/bin/activate
HF_HOME=/cluster/scratch/ouyuxu/hf_cache hf download Qwen/Qwen3-14B
```

The scripts assume internet access on login nodes and offline compute nodes.
Model downloads and package installation are real external operations; no
cluster availability or package compatibility is established by this README.

## Daily workflow

```bash
# On the Euler login node: log directory must exist BEFORE sbatch opens its files
ssh ouyuxu@euler.ethz.ch
mkdir -p /cluster/scratch/ouyuxu/logs
sbatch ~/scripts/euler/serve_qwen_14b.sh
# Or, with the 30B weights cached:
# sbatch ~/scripts/euler/serve_qwen.sh

squeue -u ouyuxu
# Inspect the actual job's log; RUNNING does not itself mean the API is ready
# tail -n 30 /cluster/scratch/ouyuxu/logs/vllm-JOB_ID.out
```

In a separate laptop terminal, from the repository root:

```bash
./scripts/euler/connect.sh
```

In another laptop terminal, verify readiness without generating text:

```bash
curl --fail http://localhost:8000/v1/models
```

When finished, cancel the **specific** job on Euler, then close the tunnel:

```bash
scancel JOB_ID
```

Replace `JOB_ID` with the ID from `sbatch`/`squeue`. Do not rely on the idle
watchdog to end the job.

## Actual script settings

| Setting | `serve_qwen.sh` | `serve_qwen_14b.sh` |
|---|---|---|
| Model | `Qwen/Qwen3-30B-A3B` | `Qwen/Qwen3-14B` |
| GPU request | One GPU, `gpumem:80g` | One GPU, `gpumem:40g` |
| CPU request | 16 cores | 8 cores |
| Host memory request | 4G per CPU | 4G per CPU |
| Walltime request | Four hours | Four hours |
| Partition directive | `gpu.24h,cuda13pr.24h` | None |
| Model context limit | 8,192 tokens | 8,192 tokens |
| vLLM option | `--enforce-eager` | Default execution mode |
| Port | `${VLLM_PORT:-8000}` | `${VLLM_PORT:-8000}` |
| Watchdog threshold | `${IDLE_TIMEOUT:-1800}` seconds | `${IDLE_TIMEOUT:-1800}` seconds |

GPU-memory requests are not guarantees of a particular GPU model or node.
Actual scheduling, account/shareholder overrides and scratch-retention policy
must be checked on Euler; older node lists and scheduling anecdotes are not
current availability evidence.

### Readiness and shutdown limitations

- The 30B script waits up to 300 seconds for `/v1/models` and checks whether the
  server process died. Its watchdog uses changes in the job's stdout log as
  activity, not actual request timestamps.
- The 14B script polls `/health` for up to 120 seconds but has no explicit
  failure exit if that loop expires. Its watchdog counts matching metric
  **lines**, not changes in request counts; persistent metric names can keep
  resetting the idle timer even when no new requests arrive.
- Both readiness loops use `curl` without HTTP-error checking. Verify the
  endpoint with `curl --fail` yourself. A four-hour Slurm limit is the requested
  hard stop, but a reliable "30 minutes after the last request" stop is not
  implemented.

### Overrides and tunnels

On Euler:

```bash
IDLE_TIMEOUT=3600 VLLM_PORT=8001 sbatch ~/scripts/euler/serve_qwen_14b.sh
```

`connect.sh` hardcodes both ports to 8000 and picks the first job whose name
contains `vllm`, including pending jobs; it does not select among multiple
servers. For a changed port or explicit node, open the tunnel manually on the
laptop:

```bash
ssh -N -L 127.0.0.1:8001:NODE:8001 ouyuxu@euler.ethz.ch
```

Replace `NODE` with the allocated node from `squeue` and use
`http://localhost:8001/v1` in the client. A server-side port override alone does
not update the laptop tunnel.

## Client configuration

The repository's vLLM client reads `VLLM_BASE_URL` and `VLLM_MODEL` from `.env`
or the environment. The model name must match the server chosen above. Direct
OpenAI-client use:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="none",  # these scripts do not configure API authentication
)

response = client.chat.completions.create(
    model="Qwen/Qwen3-14B",
    messages=[{"role": "user", "content": "Solve: 3x + 5 = 20"}],
    max_tokens=512,
)
print(response.choices[0].message.content)
```

This example makes an inference request. Keep access behind an authorized SSH
tunnel; the serving scripts do not configure an API key. vLLM is installed by
`setup_env.sh`, not by the laptop project's ordinary dependencies.

## Paths on Euler

| Path | Contents |
|------|----------|
| `/cluster/scratch/ouyuxu/pf-env/` | Python virtual environment |
| `/cluster/scratch/ouyuxu/hf_cache/` | Downloaded model weights |
| `/cluster/scratch/ouyuxu/logs/` | SLURM job output/error logs |

Treat scratch files as disposable. If weights or the environment have been
removed, recreate them on the login node before submitting an offline server.
Do not assume the repository deploy target installs the scratch environment.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Server does not start | Inspect `/cluster/scratch/ouyuxu/logs/vllm-JOB_ID.err`; confirm the log directory, module and cached model |
| Job remains pending | Inspect Slurm's pending reason; the 14B script requests less GPU memory but scheduling is not guaranteed |
| Tunnel cannot connect | Check the selected job, allocated node, server readiness and both tunnel ports |
| Model missing | Download the exact chosen model on the login node with `HF_HOME` set to the scratch cache |
| Port occupied | Change `VLLM_PORT` and create the matching manual tunnel |
| Job remains alive when idle | Cancel its specific Slurm job; watchdog behavior is limited as described above |

From the laptop repository root, `make logs` copies remote serving logs to
`scripts/euler/logs/`. It requires SSH/network access and is not a local test.
