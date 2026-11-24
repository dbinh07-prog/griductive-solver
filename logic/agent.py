from contracts.models import Analysis, PublicState, Status, Uniqueness
from contracts.ports import Encoder, Solver


class LogicAgent:
    """Member 2: receives only public state; never a Puzzle/GameEngine/path."""

    def __init__(self, encoder: Encoder, solver: Solver):
        self.encoder = encoder
        self.solver = solver

    def analyze(self, public_state: PublicState, *, timeout_s: float = 5.0) -> Analysis:
        raise NotImplementedError("Member 2: consistency and entailment queries")

    def next_forced(self, analysis: Analysis) -> tuple[str, Status] | None:
        raise NotImplementedError("Member 2: choose first forced unresolved cell")

    def check_uniqueness(self, full_clue_state: PublicState, *, timeout_s: float = 5.0) -> Uniqueness:
        raise NotImplementedError("Member 2: offline complete-clue uniqueness check")
