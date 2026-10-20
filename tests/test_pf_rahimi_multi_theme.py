import json
from pathlib import Path

from openai import OpenAIError

from scripts import run_pf_rahimi_multi_theme as runner
from src.evaluation import pf_rubric_setting

CONFIG = Path("experiments/configs/pf_rahimi_multi_theme_setting.json")


READY = '{"status": "ready", "title": "T", "body": "B", "question": "Q"}'


class FakeAPI:
    """Stands in for the OpenAI client; fails for chosen call numbers."""

    def __init__(self, fail_on=(), content=READY):
        self.calls = 0
        self.fail_on = set(fail_on)
        self.content = content
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        self.calls += 1
        if self.calls in self.fail_on:
            raise OpenAIError("connection dropped")
        message = type("M", (), {"content": self.content})
        choice = type("C", (), {"message": message, "finish_reason": "stop"})
        return type("R", (), {"choices": [choice], "model": "fake"})


def config():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_api_error_is_deleted_logged_and_never_retried(tmp_path):
    cfg = config()
    cell = cfg["cells"][0]
    ledger = runner.Ledger(tmp_path)
    api = FakeAPI(fail_on={1})
    runner.generate_one(api, tmp_path, ledger, cfg, cell, "gpt-4.1", 1, "S", "U")
    assert not (tmp_path / "attempts" / "sports_basketball_ratio__gpt41__001.json").exists()
    lines = (tmp_path / "deleted_api_errors.jsonl").read_text(encoding="utf-8").splitlines()
    log = [json.loads(line) for line in lines]
    assert log[0]["key"] == "sports_basketball_ratio__gpt41__001"
    assert "OpenAIError" in log[0]["error"] or "connection dropped" in log[0]["error"]
    runner.generate_one(api, tmp_path, runner.Ledger(tmp_path), cfg, cell, "gpt-4.1", 1, "S", "U")
    assert api.calls == 1


def test_non_ready_output_is_kept_as_a_result(tmp_path):
    cfg = config()
    api = FakeAPI(content="not json")
    runner.generate_one(api, tmp_path, runner.Ledger(tmp_path), cfg, cfg["cells"][0],
                        "gpt-5-mini", 2, "S", "U")
    path = tmp_path / "attempts" / "sports_basketball_ratio__gpt5mini__002.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["status"] != "ready"


def test_each_judge_pass_gets_its_own_order_and_blind_ids():
    cfg = config()
    keys = [runner.task_key(c["cell_id"], m, i) for c in cfg["cells"]
            for m in cfg["models"] for i in range(1, 31)]
    plan = runner.blind_plan(cfg["rater"]["judges"], keys)
    first, second = (plan[j["judge_id"]] for j in cfg["rater"]["judges"])
    assert set(first.values()) == set(second.values()) == set(keys)
    assert set(first).isdisjoint(second)
    assert list(first.values()) != list(second.values())
    assert len(first) == len(keys) == 240


def test_final_score_is_mean_gap_is_flagged_and_missing_is_not_zero(tmp_path):
    cfg = config()
    key = "sports_basketball_ratio__gpt41__001"
    ready = {key: {"key": key, "cell_id": "sports_basketball_ratio", "model_requested": "gpt-4.1"}}
    plan = {"luna-judge-1": {"m-a": key}, "luna-judge-2": {"m-b": key}}

    def write(judge, blind, total):
        path = tmp_path / "judgments" / judge / f"{blind}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        scores = None if total is None else {"TOTAL": total}
        path.write_text(json.dumps({"status": "scored" if total else "insufficient_evidence",
                                    "scores": scores}), encoding="utf-8")

    write("luna-judge-1", "m-a", 12)
    write("luna-judge-2", "m-b", 6)
    result = runner.aggregate(tmp_path, cfg, plan, ready)["tasks"][key]
    assert result["final"] == 9 and result["gap"] == 6 and result["flag_gap_5"] is True

    write("luna-judge-2", "m-b", None)
    result = runner.aggregate(tmp_path, cfg, plan, ready)["tasks"][key]
    assert result["status"] == "incomplete" and result["final"] is None


def test_judge_message_never_reveals_cell_model_or_examples():
    cfg = config()
    cell = cfg["cells"][2]
    task = {"status": "ready", "title": "T", "body": "B", "question": "Q"}
    text = pf_rubric_setting.judge_input(
        pf_rubric_setting.student_task_text(task), cell["case"], cell["learner_context"]
    )
    for hidden in (cell["cell_id"], "gpt-4.1", "gpt-5-mini", "puech2025", "Eedi"):
        assert hidden not in text
    system, user = runner.cell_messages(cell, runner.bench.load_prompt(runner.GEN_PROMPT))
    assert system and user
