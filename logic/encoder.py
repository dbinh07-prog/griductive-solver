from contracts.models import CNF, Character, Clue, Region, PublicState
from abc import ABC, abstractmethod
from core.regions import all_cells, resolve_region, referenced_cells
import itertools
import math



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
        if not isinstance(clue, Clue):
            raise ValueError("A clue must have Clue Datatype")
        if not isinstance(size, int):
            raise ValueError("Size must be an integer")
        
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
        if not isinstance(clue, Clue):
            raise ValueError("A clue must have Clue Datatype")
        if not isinstance(size, int):
            raise ValueError("Size must be an integer")
        
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
    

    def encode_clue(self, clue: Clue, variables: dict[str, int]) -> tuple[tuple[int, ...], ...]:
        if not isinstance(clue, Clue):
            raise ValueError("A clue must be categorized as a Clue class")

        """return (not a or b) and (a or not b) to transform DNF into CNF"""
        return ((variables[clue.cells[0]], -variables[clue.cells[1]]), (-variables[clue.cells[0]], variables[clue.cells[1]]))
        

    
# 3. DifferentStrategy.
class DifferentStrategy(ClueStrategy):

    def validate_clue(self, clue: Clue, size: int) -> None:
        if not isinstance(clue, Clue):
            raise ValueError("A clue must have Clue Datatype")
        if not isinstance(size, int):
            raise ValueError("Size must be an integer")

        all_cells_from_board = all_cells(size)
        if not isinstance(clue.cells, tuple):
            raise ValueError("Clue cells must be a tuple of cell")
        if len(clue.cells) != 2:
            raise ValueError("Clue of DIFFERENT must have 2 cells")
        
        if clue.cells[0] not in all_cells_from_board:
            raise ValueError(f"The {clue.cells[0]} is not in board")
        if clue.cells[1] not in all_cells_from_board:
            raise ValueError(f"The {clue.cells[1]} is not in board")
        
        if clue.cells[0] == clue.cells[1]:
            raise ValueError(f"Cells in clue are equivalent and have no value")
    
    def encode_clue(self, clue: Clue, variables: dict[str, int]) -> tuple[tuple[int, ...], ...]:     # tuple[int, .....] is clauses.
        if not isinstance(clue, Clue):
            raise ValueError("Clue cells must be a tuple of cell")
        
        """return (a or b) and (not a or not b)"""
        return ((variables[clue.cells[0]], variables[clue.cells[1]]), (-variables[clue.cells[0]], -variables[clue.cells[1]]))
    
        

# 4. AtLeastStrategy.

class AtLeastStrategy(ClueStrategy):

    def validate_clue(self, clue: Clue, size: int) -> None:
        if not isinstance(clue, Clue):
            raise ValueError("A clue must have Clue Datatype")
        if not isinstance(size, int):
            raise ValueError("Size must be an integer")
        if not isinstance(clue.region, Region):
            raise ValueError("Clue region must be categorized as Region Datatype")
        
        
        current_kind = clue.region.kind
        all_cells_in_board = all_cells(size)
        if current_kind == "ROW" or current_kind == "COLUMN":
            if not isinstance(clue.region.index, int):
                raise ValueError("The index must be an integer")
            if clue.region.index <= 0 or clue.region.index > size:
                raise ValueError("The index is out of current size")

        elif current_kind == "NEIGHBORS":
            if not isinstance(clue.region.anchor, str):
                raise ValueError("Anchor must be a string")
            
            if clue.region.anchor not in all_cells_in_board:
                raise ValueError(f"{clue.region.anchor} is not valid - out of the board")
        
        elif current_kind == "EXPLICIT":
            if not isinstance(clue.region.cells, tuple):
                raise ValueError(f"{clue.region.cells} must be a tuple")
            
            for cell in clue.region.cells:
                if cell not in all_cells_in_board:
                    raise ValueError(f"{cell} not in board")
        all_neighbours = resolve_region(clue.region, size)

        if type(clue.k) is not int:
            raise ValueError("k must be an integer")
        if len(all_neighbours) < clue.k:
            raise ValueError("The total number of neighbours is lower than k -> k is not valid")
        if clue.k < 0:
            raise ValueError("k must be non-negative")
        
        
        
        
    
    def encode_clue(self, clue: Clue, variables: dict[str, int]) -> tuple[tuple[int, ...],...]:
        """We need at least k cells those are criminal -> True -> Positive value"""
        """So at most len(referenced_cells) - k cells those are innocent -> False -> Negative Value """   
        """=> Each group len(referenced_cells) - k + 1 cells, => at least 1 criminal""" 

        total_size = 0 
        for item in variables:
            total_size += 1     

        all_cells_from_clue = referenced_cells(clue, int(math.sqrt(total_size)))
        all_values_from_clue = [variables[cell] for cell in all_cells_from_clue]

        result = itertools.combinations(all_values_from_clue, r = len(all_values_from_clue) - clue.k + 1)
        return tuple(result)
    



# 5. AtMostStrategy. 
class AtMostStrategy(ClueStrategy):
    
    def validate_clue(self, clue: Clue, size: int) -> None:
        
        if not isinstance(clue, Clue):
            raise ValueError("A clue must have Clue Datatype")
        if not isinstance(size, int):
            raise ValueError("Size must be an integer")
        if not isinstance(clue.region, Region):
            raise ValueError("Clue region must be categorized as Region Datatype")
        
        current_kind = clue.region.kind
        all_cells_in_board = all_cells(size)
        if current_kind == "ROW" or current_kind == "COLUMN":
            if not isinstance(clue.region.index, int):
                raise ValueError("The index must be an integer")
            if clue.region.index <= 0 or clue.region.index > size:
                raise ValueError("The index is out of current size")

        elif current_kind == "NEIGHBORS":
            if not isinstance(clue.region.anchor, str):
                raise ValueError("Anchor must be a string")
            
            if clue.region.anchor not in all_cells_in_board:
                raise ValueError(f"{clue.region.anchor} is not valid - out of the board")
        
        elif current_kind == "EXPLICIT":
            if not isinstance(clue.region.cells, tuple):
                raise ValueError(f"{clue.region.cells} must be a tuple")
            
            for cell in clue.region.cells:
                if cell not in all_cells_in_board:
                    raise ValueError(f"{cell} not in board")
        all_neighbours = resolve_region(clue.region, size)

        if type(clue.k) is not int:
            raise ValueError("k must be an integer")
        if len(all_neighbours) < clue.k:
            raise ValueError("The total number of neighbours is lower than k -> k is not valid")
        if clue.k < 0:
            raise ValueError("k must be non-negative")
        
    
    def encode_clue(self, clue: Clue, variables: dict[str, int]) -> tuple[tuple[int, ...], ...]:
        """We need at most k criminal -> k True -> k positive"""
        """-> k + 1 items in a group, absolutely one 1 innocent"""

        total_size = 0 
        for item in variables:
            total_size += 1
        
        all_cells_from_clue = referenced_cells(clue, int(math.sqrt(total_size)))
        all_values_from_clue = [-variables[cell] for cell in all_cells_from_clue]

        result = itertools.combinations(all_values_from_clue, r = clue.k + 1)
        return tuple(result)
    

# 6. ExactlyStrategy.
class ExactStrategy(ClueStrategy):

    def validate_clue(self, clue: Clue, size: int) -> None:
        
        if not isinstance(clue, Clue):
            raise ValueError("A clue must have Clue Datatype")
        if not isinstance(size, int):
            raise ValueError("Size must be an integer")
        if not isinstance(clue.region, Region):
            raise ValueError("Clue region must be categorized as Region Datatype")
        
        current_kind = clue.region.kind
        all_cells_in_board = all_cells(size)
        if current_kind == "ROW" or current_kind == "COLUMN":
            if not isinstance(clue.region.index, int):
                raise ValueError("The index must be an integer")
            if clue.region.index <= 0 or clue.region.index > size:
                raise ValueError("The index is out of current size")

        elif current_kind == "NEIGHBORS":
            if not isinstance(clue.region.anchor, str):
                raise ValueError("Anchor must be a string")
            
            if clue.region.anchor not in all_cells_in_board:
                raise ValueError(f"{clue.region.anchor} is not valid - out of the board")
        
        elif current_kind == "EXPLICIT":
            if not isinstance(clue.region.cells, tuple):
                raise ValueError(f"{clue.region.cells} must be a tuple")
            
            for cell in clue.region.cells:
                if cell not in all_cells_in_board:
                    raise ValueError(f"{cell} not in board")
        all_neighbours = resolve_region(clue.region, size)

        if type(clue.k) is not int:
            raise ValueError("k must be an integer")
        if len(all_neighbours) < clue.k:
            raise ValueError("The total number of neighbours is lower than k -> k is not valid")
        if clue.k < 0:
            raise ValueError("k must be non-negative")
        

    def encode_clue(self, clue: Clue, variables: dict[str, int]) -> tuple[tuple[int, ...], ...]:
        """k items criminal -> k items positive"""
        """in k + 1 random items, there is at least one item innocent -> False -> Negative"""
        """in len(referenced_items) - k + 1 random items, there is at least one item criminal"""

        total_size = 0 
        for item in variables:
            total_size += 1
        
        all_cells_from_clue = referenced_cells(clue, int(math.sqrt(total_size)))

        all_values_at_least_innocent = [-variables[cell] for cell in all_cells_from_clue]
        all_values_at_most_criminal =  [variables[cell] for cell in all_cells_from_clue]

        result_innocent = itertools.combinations(all_values_at_least_innocent, r = clue.k + 1)
        result_criminal = itertools.combinations(all_values_at_most_criminal, r = len(all_cells_from_clue) - clue.k + 1)
        
        final_result = list(result_innocent)
        final_result.extend(result_criminal)
        return tuple(final_result)
    
    




# 7. ParityStrategy.
class ParityStrategy(ClueStrategy):

    def validate_clue(self, clue: Clue, size: int) -> None:
        
        if not isinstance(clue, Clue):
            raise ValueError("A clue must have Clue Datatype")
        if not isinstance(size, int):
            raise ValueError("Size must be an integer")
        if not isinstance(clue.region, Region):
            raise ValueError("Clue region must be categorized as Region Datatype")
        
        current_kind = clue.region.kind
        all_cells_in_board = all_cells(size)
        if current_kind == "ROW" or current_kind == "COLUMN":
            if not isinstance(clue.region.index, int):
                raise ValueError("The index must be an integer")
            if clue.region.index <= 0 or clue.region.index > size:
                raise ValueError("The index is out of current size")

        elif current_kind == "NEIGHBORS":
            if not isinstance(clue.region.anchor, str):
                raise ValueError("Anchor must be a string")
            
            if clue.region.anchor not in all_cells_in_board:
                raise ValueError(f"{clue.region.anchor} is not valid - out of the board")
        
        elif current_kind == "EXPLICIT":
            if not isinstance(clue.region.cells, tuple):
                raise ValueError(f"{clue.region.cells} must be a tuple")
            
            for cell in clue.region.cells:
                if cell not in all_cells_in_board:
                    raise ValueError(f"{cell} not in board")

        if type(clue.k) is not int:
            raise ValueError("k must be an integer")

        if clue.k != 0 and clue.k != 1:
            raise ValueError("k must be 0 or 1")
        

    def encode_clue(self, clue: Clue, variables: dict[str, int]) -> tuple[tuple[int, ...], ...]:
        
        total_size = 0 
        for item in variables:
            total_size += 1

        all_cells_from_clue = referenced_cells(clue, int(math.sqrt(total_size)))
        all_values_from_clue = [variables[cell] for cell in all_cells_from_clue]

        # Case 1: Criminal % 2 = 0.
        if clue.k == 0:
            final_result = []

            all_cases = itertools.product([True, False], repeat = len(all_values_from_clue))
            for case in all_cases:
                if sum(case) % 2 != clue.k:
                    current_clause = []
                    for boolean_value, cell_value in zip(list(case), all_values_from_clue):
                        if boolean_value:
                            current_clause.append(-abs(cell_value))
                        else:
                            current_clause.append(abs(cell_value))
                    final_result.append(tuple(current_clause))
            
            return tuple(final_result)
        
        # Case 2: Criminal % 2 != 0.
        else:
            final_result = []
            all_cases = itertools.product([True, False], repeat = len(all_values_from_clue))
            for case in all_cases:
                if sum(case) % 2 != clue.k:
                    current_clause = []
                    for boolean_value, cell_value in zip(list(case), all_values_from_clue):
                        if boolean_value:
                            current_clause.append(-abs(cell_value))
                        else:
                            current_clause.append(abs(cell_value))
                    final_result.append(tuple(current_clause))

            
            return tuple(final_result)
        



# 8. CountCompareStrategy.
class CountCompareStrategy(ClueStrategy):

    def validate_clue(self, clue: Clue, size: int) -> None:
        if not isinstance(clue, Clue):
            raise ValueError("A clue must have Clue Datatype")
        if type(size) is not int or size <= 0:
            raise ValueError("Size must be a positive integer")
        if clue.kind != "COUNT_COMPARE":
            raise ValueError("Clue kind must be COUNT_COMPARE")
        if not isinstance(clue.region, Region):
            raise ValueError("Clue region must have Region Datatype")
        if not isinstance(clue.other_region, Region):
            raise ValueError("Clue other_region must have Region Datatype")
        if not isinstance(clue.relation, str) or clue.relation not in ("EQ", "LT", "GT"):
            raise ValueError("Relation must be EQ, LT, or GT")

        # The shared resolver validates region kind, cells, index and anchor.
        resolve_region(clue.region, size)
        resolve_region(clue.other_region, size)

    def encode(
        self, clue: Clue, variables: dict[str, int]
    ) -> tuple[tuple[int, ...], ...]:
        if not isinstance(variables, dict) or not variables:
            raise ValueError("Variables must be a nonempty dictionary")

        size = math.isqrt(len(variables))
        if size * size != len(variables):
            raise ValueError("Variables must cover a square board")
        for variable in variables.values():
            if type(variable) is not int or variable <= 0:
                raise ValueError("Variable IDs must be positive integers")
        if len(set(variables.values())) != len(variables):
            raise ValueError("Each cell must have a distinct variable ID")

        self.validate_clue(clue, size)
        region_cells = resolve_region(clue.region, size)
        other_region_cells = resolve_region(clue.other_region, size)

        # Combine the two regions. A shared cell receives one truth value.
        cells = list(region_cells)
        for cell in other_region_cells:
            if cell not in cells:
                cells.append(cell)

        for cell in cells:
            if cell not in variables:
                raise ValueError(f"No variable ID for cell {cell!r}")

        final_result = []
        all_cases = itertools.product((True, False), repeat=len(cells))

        for case in all_cases:
            assignment = dict(zip(cells, case))
            region_count = sum(assignment[cell] for cell in region_cells)
            other_region_count = sum(assignment[cell] for cell in other_region_cells)

            if clue.relation == "EQ":
                relation_holds = region_count == other_region_count
            elif clue.relation == "LT":
                relation_holds = region_count < other_region_count
            else:
                relation_holds = region_count > other_region_count

            # Block each assignment that violates the requested relation.
            if not relation_holds:
                current_clause = []
                for cell, boolean_value in zip(cells, case):
                    variable = variables[cell]
                    if boolean_value:
                        current_clause.append(-variable)
                    else:
                        current_clause.append(variable)
                final_result.append(tuple(current_clause))

        return tuple(final_result)

    def encode_clue(
        self, clue: Clue, variables: dict[str, int]
    ) -> tuple[tuple[int, ...], ...]:
        return self.encode(clue, variables)


# Context.
class CNFEncoder:
    """Encode the public clues and proved statuses into immutable CNF."""

    def __init__(self) -> None:
        self._strategies = {
            "FACT": FactStrategy(),
            "SAME": SameStrategy(),
            "DIFFERENT": DifferentStrategy(),
            "AT_LEAST": AtLeastStrategy(),
            "AT_MOST": AtMostStrategy(),
            "EXACTLY": ExactStrategy(),
            "PARITY": ParityStrategy(),
            "COUNT_COMPARE": CountCompareStrategy(),
        }

    def _strategy_for(self, clue: Clue) -> ClueStrategy:
        if not isinstance(clue, Clue):
            raise ValueError("A clue must have Clue Datatype")
        if not isinstance(clue.kind, str) or clue.kind not in self._strategies:
            raise ValueError(f"Unsupported clue kind {clue.kind!r}")
        return self._strategies[clue.kind]

    def validate_clue(self, clue: Clue, size: int) -> None:
        if type(size) is not int or size <= 0:
            raise ValueError("Size must be a positive integer")
        strategy = self._strategy_for(clue)
        if not isinstance(clue.id, str) or not clue.id.strip():
            raise ValueError("Clue ID must be a nonempty string")

        if not isinstance(clue.cells, tuple):
            raise ValueError("Clue cells must be a tuple")
        if type(clue.status) is not bool:
            raise ValueError("Clue status must be a boolean")
        if type(clue.k) is not int:
            raise ValueError("k must be an integer, excluding bool")

        if clue.kind in ("FACT", "SAME", "DIFFERENT"):
            if clue.region is not None or clue.other_region is not None:
                raise ValueError(f"{clue.kind} does not use regions")
            if clue.relation is not None or clue.k != 0:
                raise ValueError(f"{clue.kind} requires default relation and k")
            if clue.kind != "FACT" and clue.status is not True:
                raise ValueError(f"{clue.kind} requires the default status")
        else:
            if clue.cells != () or clue.status is not True:
                raise ValueError(f"{clue.kind} requires default cells and status")
            # Validate regions for every region-based template, including PARITY.
            resolve_region(clue.region, size)
            if clue.kind == "COUNT_COMPARE":
                if clue.k != 0:
                    raise ValueError("COUNT_COMPARE requires the default k")
            elif clue.other_region is not None or clue.relation is not None:
                raise ValueError(f"{clue.kind} does not use other_region or relation")

        strategy.validate_clue(clue, size)

    def encode(self, public_state: PublicState) -> CNF:
        if not isinstance(public_state, PublicState):
            raise ValueError("Expected a PublicState instance")
        if type(public_state.size) is not int or public_state.size <= 0:
            raise ValueError("Size must be a positive integer")
        if not isinstance(public_state.proved_statuses, tuple):
            raise ValueError("Proved statuses must be a tuple")
        if not isinstance(public_state.revealed_clues, tuple):
            raise ValueError("Revealed clues must be a tuple")

        # Primary IDs depend only on board position, including unresolved cells.
        cells = all_cells(public_state.size)
        if not isinstance(public_state.characters, tuple) or not all(
            isinstance(person, Character) for person in public_state.characters
        ):
            raise ValueError("Characters must be a tuple of Character instances")
        if tuple(person.cell for person in public_state.characters) != cells:
            raise ValueError("Characters must cover the board in row-major order")
        variables = {cell: index for index, cell in enumerate(cells, start=1)}
        clauses = []
        proved_cells = set()

        for entry in public_state.proved_statuses:
            if not isinstance(entry, tuple) or len(entry) != 2:
                raise ValueError("A proved status must be a (cell, bool) pair")
            cell, status = entry
            if not isinstance(cell, str) or cell not in variables:
                raise ValueError(f"Invalid proved cell {cell!r}")
            if type(status) is not bool:
                raise ValueError("Proved statuses must be boolean values")
            if cell in proved_cells:
                raise ValueError(f"Duplicate proved cell {cell!r}")
            proved_cells.add(cell)

            variable = variables[cell]
            clauses.append((variable if status else -variable,))

        # Only the revealed_clues snapshot contributes clue clauses.
        owners = set()
        clue_ids = set()
        for entry in public_state.revealed_clues:
            if not isinstance(entry, tuple) or len(entry) != 2:
                raise ValueError("A revealed clue must be an (owner, clue) pair")
            owner, clue = entry
            if not isinstance(owner, str) or owner not in variables:
                raise ValueError(f"Invalid clue owner {owner!r}")

            self.validate_clue(clue, public_state.size)
            if owner in owners or clue.id in clue_ids:
                raise ValueError("Revealed clue owners and IDs must be distinct")
            owners.add(owner)
            clue_ids.add(clue.id)
            strategy = self._strategy_for(clue)
            clue_clauses = strategy.encode_clue(clue, variables)
            clauses.extend(tuple(clause) for clause in clue_clauses)

        return CNF(
            clauses=tuple(clauses),
            primary_variables=tuple(variables.items()),
            variable_count=len(variables),
        )

