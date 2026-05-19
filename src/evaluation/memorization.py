"""Memorization detection via n-gram overlap."""


class MemorizationChecker:
    """Detects memorization by checking n-gram overlap with retrieval pool."""

    def __init__(self, n: int = 5):
        self.n = n

    def check(self, generated: str, reference_pool: list[str]) -> float:
        """Compute max n-gram overlap between generated text and reference pool."""
        raise NotImplementedError("TODO: Implement memorization check")
