"""Embedding-based diversity scoring."""


class DiversityScorer:
    """Computes diversity of RSMs using sentence embeddings."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name

    def score(self, responses: list[str]) -> float:
        """Compute pairwise diversity score over responses."""
        raise NotImplementedError("TODO: Implement diversity scoring")
