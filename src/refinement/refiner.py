"""Self-Refine loop for iterative PF exercise improvement."""


class ExerciseRefiner:
    """Iteratively refines PF exercises based on simulated student feedback."""

    def __init__(self, config: dict, max_iterations: int = 3):
        self.config = config
        self.max_iterations = max_iterations

    def refine(self, exercise: str, feedback: dict) -> str:
        """Refine an exercise based on simulation feedback."""
        raise NotImplementedError("TODO: Implement refinement logic")

    def should_stop(self, iteration: int, scores: list[float]) -> bool:
        """Determine if refinement should stop (convergence or max iterations)."""
        if iteration >= self.max_iterations:
            return True
        if len(scores) >= 2 and abs(scores[-1] - scores[-2]) < 0.01:
            return True
        return False
