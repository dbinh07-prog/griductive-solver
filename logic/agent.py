from contracts.models import Analysis, PublicState, Status, Uniqueness
from contracts.ports import Encoder, Solver


class LogicAgent:
    def __init__(self, encoder: Encoder, solver: Solver):
        self.encoder = encoder
        self.solver = solver

    def analyze(self, public_state: PublicState, *, timeout_s: float = 5.0) -> Analysis:
        raise NotImplementedError("Member 2: consistency and entailment queries")
    

    

    def next_forced(self, analysis: Analysis) -> tuple[str, Status] | None:
        """If inconsistent -> Return None as contradictions"""
        if analysis.inconsistent is True:
            return None
        else:
            for cell, status in analysis.classifications:
                if status in (Status.CRIMINAL, Status.INNOCENT):
                    return (cell, status)
            return None

    def check_uniqueness(self, full_clue_state: PublicState, *, timeout_s: float = 5.0) -> Uniqueness:
        raise NotImplementedError("Member 2: offline complete-clue uniqueness check")
