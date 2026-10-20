"""Run the clarified v2 interpretation on the frozen v4 benchmark tasks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rerate_pf_paper_benchmark_v2 as runner  # noqa: E402
from src.evaluation import pf_rubric_v2_1 as rubric  # noqa: E402

PROTOCOL_PATH = ROOT / "experiments/configs/pf_rubric_v2_1_v4_rerating.json"
DEFAULT_OUTPUT = ROOT / (
    "experiments/results/pf_paper_benchmark/20260925_rahimi_table1_v2_1_v4_rerating"
)


def _load_protocol(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    protocol = json.loads(raw)
    if not isinstance(protocol, dict):
        raise ValueError("Rerating protocol must be a JSON object")
    if protocol.get("schema_version") != "rahimi-table1-rerating/v2.1":
        raise ValueError("Unsupported v2.1 rerating protocol")
    if tuple(protocol.get("conditions", ())) != runner.CONDITIONS:
        raise ValueError("Protocol conditions must match the frozen four-condition benchmark")
    if protocol.get("rubric_version") != "rahimi-table1/v2.1":
        raise ValueError("Protocol must select rahimi-table1/v2.1")
    if protocol.get("prompt_path") != "src/evaluation/prompts/pf_rubric_v2_1.yaml":
        raise ValueError("Protocol prompt path does not identify the clarified v2.1 prompt")
    if protocol.get("model_selector") != "luna":
        raise ValueError("The frozen model selector must be luna")
    settings = protocol.get("requested_settings", {})
    if settings.get("temperature") != 0.0 or settings.get("max_tokens") != 4000:
        raise ValueError("The v2.1 model settings differ from the frozen protocol")
    if protocol.get("expected_attempts_per_condition") != 30:
        raise ValueError("The v4 benchmark has exactly 30 scheduled attempts per condition")
    if protocol.get("source_run") != "experiments/results/pf_paper_benchmark/20260923_luna_v4":
        raise ValueError("The protocol must select the frozen September 23 v4 run")
    return protocol, raw


def _source_files() -> dict[str, Path]:
    return {
        "scripts/rerate_pf_paper_benchmark_v2_1.py": Path(__file__).resolve(),
        "scripts/rerate_pf_paper_benchmark_v2.py": Path(runner.__file__).resolve(),
        "src/evaluation/pf_rubric_v2_1.py": Path(rubric.__file__).resolve(),
        "src/evaluation/prompts/pf_rubric_v2_1.yaml": rubric.PROMPT_PATH,
        "src/evaluation/pf_rubric_v2.py": ROOT / "src/evaluation/pf_rubric_v2.py",
        "src/evaluation/prompts/pf_rubric_v2.yaml": ROOT
        / "src/evaluation/prompts/pf_rubric_v2.yaml",
        "src/evaluation/pf_rubric.py": ROOT / "src/evaluation/pf_rubric.py",
        "src/evaluation/prompts/pf_rubric.yaml": ROOT / "src/evaluation/prompts/pf_rubric.yaml",
        "scripts/prior_methods/common.py": ROOT / "scripts/prior_methods/common.py",
        "scripts/run_pf_diagnostic.py": ROOT / "scripts/run_pf_diagnostic.py",
    }


runner._load_protocol = _load_protocol
runner._source_files = _source_files
runner.PROMPT_PATH = rubric.PROMPT_PATH
runner.DIMENSIONS = rubric.DIMENSIONS
runner.judge_input = rubric.judge_input
runner.load_prompt = rubric.load_prompt
runner.parse_rating = rubric.parse_rating
runner.student_task_text = rubric.student_task_text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument(
        "--prepare",
        action="store_true",
        help="Freeze v4 task inputs and hashes; make no API calls.",
    )
    modes.add_argument(
        "--calibrate",
        action="store_true",
        help="Run the balanced API/schema calibration.",
    )
    modes.add_argument(
        "--run",
        action="store_true",
        help="Rate all remaining ready v4 tasks after calibration.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--retry-interrupted", action="store_true")
    args = parser.parse_args()

    if args.prepare:
        manifest = runner.prepare_run(args.output, protocol_path=PROTOCOL_PATH)
        print(
            json.dumps(
                {
                    "status": manifest["status"],
                    "output": str(args.output.resolve()),
                    "scheduled": manifest["case_count"],
                    "ready": manifest["eligible_count"],
                    "calibration_case_ids": manifest["calibration"]["case_ids"],
                    "inputs_sha256": manifest["inputs_sha256"],
                    "prompt_sha256": manifest["prompt_sha256"],
                },
                indent=2,
            )
        )
        return
    if args.calibrate:
        summary = runner.run_calibration(args.output)
        print(json.dumps(summary, indent=2))
        if summary["status"] != "passed":
            raise SystemExit(2)
        return
    summary = runner.run_full(args.output, retry_interrupted=args.retry_interrupted)
    print(json.dumps(summary, indent=2))
    if (
        summary["overall_denominators"]["complete_five_dimension_scores"]
        < summary["overall_denominators"]["ready"]
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
