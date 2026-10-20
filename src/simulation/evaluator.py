"""Evaluator that runs simulated students against PF exercises."""

from dataclasses import dataclass

from src.simulation.student_profiles import StudentProfile


@dataclass
class SimulationResult:
    """Result of a simulated student attempting a PF exercise."""

    profile: StudentProfile
    response: str
    rsm_category: str
    productive_failure: bool


class SimulatedStudentEvaluator:
    """Runs KC-based student profiles against generated exercises."""

    def __init__(self, config: dict):
        self.config = config

    def evaluate(self, exercise: str, profiles: list[StudentProfile]) -> list[SimulationResult]:
        """Simulate student attempts on a PF exercise."""
        raise NotImplementedError("TODO: Implement simulation logic")

    def compute_diversity(self, results: list[SimulationResult]) -> float:
        """Compute RSM diversity from simulation results."""
        raise NotImplementedError("TODO: Implement diversity computation")
