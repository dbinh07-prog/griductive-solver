from contracts.models import Analysis, PublicState, Puzzle, Status, SubmitResult


class GameEngine:
    """Member 3: owns private puzzle; never give it to the agent or GUI."""

    def __init__(self, puzzle: Puzzle):
        self._puzzle = puzzle

    def public_state(self) -> PublicState:
        raise NotImplementedError("Member 3: immutable public snapshot")

    def restart(self) -> PublicState:
        raise NotImplementedError("Member 3: publish initial statuses AND clues")

    def submit_verdict(self, cell: str, proposed: Status, analysis: Analysis) -> SubmitResult:
        raise NotImplementedError("Member 3: validate revision/entailment before reveal")

    def is_solved(self) -> bool:
        raise NotImplementedError("Member 3: all statuses proved")
