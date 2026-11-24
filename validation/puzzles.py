from dataclasses import dataclass
from contracts.models import Puzzle, Uniqueness
from contracts.ports import Agent


@dataclass(frozen=True)
class ValidationResult:
    all_clues_true: bool
    complete_clues_uniqueness: Uniqueness
    progressively_solvable: bool
    issues: tuple[str, ...]


def validate_puzzle(puzzle: Puzzle, agent: Agent) -> ValidationResult:
    """Member 3: offline diagnostics; never called from Hint to expose hidden clues."""
    raise NotImplementedError("Member 3: separate truth, uniqueness, progressive solve checks")
