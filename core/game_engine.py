from contracts.models import (
    Analysis,
    Character,
    Clue,
    PublicState,
    Puzzle,
    Status,
    SubmitResult,
    VerdictResult,
)

from core.regions import all_cells




class GameEngine:
    

    def __init__(self, puzzle: Puzzle):
        if not isinstance(puzzle, Puzzle):
            raise ValueError(f"Expected Puzzle instance, got {type(puzzle).__name__}")
        
        ordered_cells = all_cells(puzzle.size)
        expected_set = set(ordered_cells)
        
        # Validate characters converge and canonicalize to row-major tuple
        
        char_map : dict[str, Character] = {}
        
        for ch in puzzle.characters:
            
            if not isinstance(ch, Character):
                raise ValueError(f"Invalid Character entry: {ch!r}")
            
            if ch.cell not in expected_set or ch.cell in char_map:
                raise ValueError(f"Invalid or duplicate character cell: {ch.cell!r}")

            char_map[ch.cell] = ch
        
        if len(char_map) != len(ordered_cells):
            raise ValueError("Puzzle characters do not cover all board cells")
        
        # Validate private solution map
        solution_map : dict[str, bool] = {}
        
        for cell, val in puzzle.solution:
            
            if cell not in expected_set or cell in solution_map:
                raise ValueError(f"Invalid or duplicate solution cell: {cell!r}")
            
            if not isinstance(val, bool): 
                raise ValueError(
                    f"Solution value for {cell!r} must be a strict bool, got {val!r}"
                )
            
            solution_map[cell] = val
        
        if len(solution_map) != len(ordered_cells):
            raise ValueError("Puzzle solution does not cover all board cells")
        
        # Validate private clues map.
        clue_map: dict[str, Clue] = {}
        
        for cell, clue in puzzle.clues:
            
            if cell not in expected_set or cell in clue_map:
                raise ValueError(f"Invalid or duplicate clue owner cell: {cell!r}")
            
            if not isinstance(clue, Clue):
                raise ValueError(f"Invalid Clue entry for owner {cell!r}: {clue!r}")
            
            clue_map[cell] = clue
        
        if len(clue_map) != len(ordered_cells):
            raise ValueError("Puzzle clues do not cover all board cells")
        
        # Validate initially_revealed cells.
        initial_set: set[str] = set()
        
        for cell in puzzle.initially_revealed:
            
            if cell not in expected_set or cell in initial_set:
                raise ValueError(f"Invalid or duplicate initially_revealed cell: {cell!r}")
            
            initial_set.add(cell)
        
        self._puzzle = puzzle
        self._ordered_cells: tuple[str, ...] = ordered_cells
        
        self._characters: tuple[Character, ...] = tuple(
            char_map[cell] for cell in ordered_cells
        )
        
        self._solution_map: dict[str, bool] = solution_map
        self._clue_map: dict[str, Clue] = clue_map
        self._initial_revealed: frozenset[str] = frozenset(initial_set)
        self._revealed: set[str] = set(initial_set)
        self._revision: int = 0

        
    def public_state(self) -> PublicState:
        
        proved_statuses = tuple(
            (cell, self._solution_map[cell])
            for cell in self._ordered_cells
            if cell in self._revealed
        )
        
        revealed_clues = tuple(
            (cell, self._clue_map[cell])
            for cell in self._ordered_cells
            if cell in self._revealed
        )
        
        return PublicState(
            puzzle_id = self._puzzle.id,
            title = self._puzzle.title,
            size = self._puzzle.size,
            characters = self._characters,
            proved_statuses = proved_statuses,
            revealed_clues = revealed_clues,
            revision = self._revision,
        )
        
        
    def restart(self) -> PublicState:
        
        self._revealed = set(self._initial_revealed)
        self._revision += 1
        return self.public_state()


    def submit_verdict(self, cell: str, proposed: Status, analysis: Analysis) -> SubmitResult:
        
        # Input & freshness validation
        
        if not isinstance(cell, str) or cell not in self._solution_map:
            raise ValueError(f"Unknown cell {cell!r} for puzzle {self._puzzle.id!r}")
        
        if not isinstance(proposed, Status) or proposed not in (
            Status.CRIMINAL,
            Status.INNOCENT,
        ):
            raise ValueError(
                f"Proposed verdict must be Status.CRIMINAL or Status.INNOCENT, got {proposed!r}"
            )
        
        if not isinstance(analysis, Analysis):
            raise ValueError(f"Expected Analysis instance, got {type(analysis).__name__}")
        
        if analysis.puzzle_id != self._puzzle.id:
            raise ValueError(
                f"Analysis puzzle_id {analysis.puzzle_id!r} does not match "
                f"engine puzzle {self._puzzle.id!r}"
            )
            
        if analysis.revision != self._revision:
            raise ValueError(
                f"Stale analysis revision {analysis.revision}; expected {self._revision}"
            )
            
        # Already revealed cell -> not state change
        if cell in self._revealed:
            return SubmitResult(
                result = VerdictResult.ALREADY_REVEALED,
                new_public_state = self.public_state(),
                revealed_clue = None,
            )
            
        # Inconsistent KB -> no reveal, no state change
        if analysis.inconsistent:
            return SubmitResult(
                result = VerdictResult.INCONSISTENT,
                new_public_state = self.public_state(),
                revealed_clue = None,
            )
        
        # Inspect entailment classification for this unresolved cell
        classifications : dict[str, Status] = {}
        
        for c, status in analysis.classifications:
            
            if c in classifications:
                raise ValueError(
                    f"Duplicate cell {c!r} in analysis.classifications"
                )
            
            if not isinstance(status, Status):
                raise ValueError(
                    f"Invalid classification {status!r} for cell {c!r}"
                )
                
            classifications[c] = status
        
        if cell not in classifications:
            raise ValueError(
                f"Unresolved cell {cell!r} missing from analysis.classifications"
            )
        
        entailed = classifications[cell]
        
        if entailed is Status.UNKNOWN:
            return SubmitResult(
                result = VerdictResult.NOT_PROVABLE,
                new_public_state = self.public_state(),
                revealed_clue = None,
            )
        
        if entailed is not proposed:
            return SubmitResult(
                result = VerdictResult.CONTRADICTED,
                new_public_state = self.public_state(),
                revealed_clue = None,
            )        
        
        # Entailed matches proposed; cross-check private ground truth
        expected_status = (
            Status.CRIMINAL if self._solution_map[cell] else Status.INNOCENT
        )
        
        if proposed is not expected_status:
            return SubmitResult(
                result = VerdictResult.INCONSISTENT,
                new_public_state = self.public_state(),
                revealed_clue = None,
            )
            
        # Accepted : publish both status and owner's clue, and advance revision
        self._revealed.add(cell)
        self._revision += 1
        
        return SubmitResult(
            result = VerdictResult.ACCEPTED,
            new_public_state = self.public_state(),
            revealed_clue = self._clue_map[cell],
        )
        

    def is_solved(self) -> bool:
        return len(self._revealed) == len(self._ordered_cells)
