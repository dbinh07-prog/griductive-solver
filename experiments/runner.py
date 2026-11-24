from dataclasses import dataclass


@dataclass(frozen=True)
class ExperimentConfig:
    suite: str = "puzzles/benchmark"
    output: str = "outputs/experiments"
    timeout_s: float = 10.0
    repeats: int = 3


def run_experiments(config: ExperimentConfig) -> None:
    """Member 3: identical case set, retained error/timeout rows, actual metrics."""
    raise NotImplementedError("Member 3: implement benchmark runner; docs/EXPERIMENTS.md")
