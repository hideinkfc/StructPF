"""LLM-as-judge evaluation on Kapur's five criteria."""


class LLMJudge:
    """Independent LLM judge for exercise quality (different model from in-loop judge)."""

    def __init__(self, config: dict):
        self.config = config

    def judge(self, exercise: str) -> dict:
        """Rate exercise on Kapur's 5 criteria using Likert scale."""
        raise NotImplementedError("TODO: Implement LLM judge")
