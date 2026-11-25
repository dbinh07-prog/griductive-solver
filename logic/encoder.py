from contracts.models import CNF, Clue, PublicState
from abc import ABC, abstractmethod
from core.regions import all_cells

# A. AbstractStrategy.
class ClueStrategy(ABC):
    """Validate and encode one kind of clue."""

    @abstractmethod
    def validate_clue(self, clue: Clue, size: int) -> None:
        pass

    @abstractmethod
    def encode_clue(
        self, clue: Clue, variables: dict[str, int]
    ) -> tuple[tuple[int, ...], ...]:
        """Return the clauses for one validated clue using the board's variable IDs."""
        pass


# B. Concrete Strategies.

# 1. FactStrategy.
class FactStrategy(ClueStrategy):

    def validate_clue(self, clue: Clue, size: int) -> None:
        all_cells_from_board = all_cells(size)
        if not isinstance(clue.cells, tuple):
            raise ValueError("Clue cells must be a tuple of cell")
        if len(clue.cells) != 1:
            raise ValueError("Clue of FACT must have 1 cell")
        if not isinstance(clue.status, bool):
            raise ValueError("Clue status must be a boolean value")
        
        if clue.cells[0] not in all_cells_from_board:
            raise ValueError(f"The {clue.cells} is not in board")
    
    def encode_clue(self, clue: Clue, variables: dict[str, int]) -> tuple[tuple[int, ...]]:     # Create Clauses. 
        if not isinstance(clue, Clue):
            raise TypeError("A clue must be categorized as a Clue Class")
        return ((variables[clue.cells[0]],),) if clue.status is True else ((-variables[clue.cells[0]],),)

# 2. SameStrategy.
class SameStrategy(ClueStrategy):

    def validate_clue(self, clue: Clue, size: int) -> None:
        all_cells_from_board = all_cells(size)          # Tuple of string (A1, B1, C1, ..., A2, B2, C2, ...).
        if not isinstance(clue.cells, tuple):
            raise ValueError("Clue cells must be a tuple of cell")
        if len(clue.cells) != 2:
            raise ValueError("Clue of SAME must have 2 cells")
        
        if clue.cells[0] not in all_cells_from_board:
            raise ValueError(f"The {clue.cells[0]} is not in board")
        if clue.cells[1] not in all_cells_from_board:
            raise ValueError(f"The {clue.cells[1]} is not in board")
        if clue.cells[0] == clue.cells[1]:
            raise ValueError(f"Cells in clue are equivalent and have no value")
    

    def encode_clue(self, clue: Clue, variables: dict[str, int]) -> tuple[tuple[int, ...]]:
        if not isinstance(clue, Clue):
            raise ValueError("A clue must be categorized as a Clue class")
       
        return ((variables[clue.cells[0]], -variables[clue.cells[1]]), (-variables[clue.cells[0]], variables[clue.cells[1]]))
        

    



class CNFEncoder:
    """Member 2: automatic encoding; never import the semantic evaluator."""

    def validate_clue(self, clue: Clue, size: int) -> None:
        raise NotImplementedError("Member 2: validate clue parameters")

    def encode(self, public_state: PublicState) -> CNF:
        raise NotImplementedError("Member 2: encode public clues and proved verdicts")
