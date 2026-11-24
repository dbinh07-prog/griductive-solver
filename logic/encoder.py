from contracts.models import CNF, Clue, PublicState


class CNFEncoder:
    """Member 2: automatic encoding; never import the semantic evaluator."""

    def validate_clue(self, clue: Clue, size: int) -> None:
        raise NotImplementedError("Member 2: validate clue parameters")

    def encode(self, public_state: PublicState) -> CNF:
        raise NotImplementedError("Member 2: encode public clues and proved verdicts")
