"""PF exercise generator using Kapur's five criteria of ill-structuredness."""

from dataclasses import dataclass


@dataclass
class PFExercise:
    """A generated Productive Failure exercise."""
    seed_problem: str
    generated_exercise: str
    criteria_scores: dict
    metadata: dict


class ExerciseGenerator:
    """Generates ill-structured PF exercises from well-structured seed problems."""

    def __init__(self, config: dict):
        self.config = config

    def generate(self, seed_problem: str, examples: list[str] | None = None) -> PFExercise:
        """Generate a PF exercise from a seed problem."""
        raise NotImplementedError("TODO: Implement generation logic")
