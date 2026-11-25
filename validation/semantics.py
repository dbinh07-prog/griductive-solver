from collections.abc import Mapping

from contracts.models import Clue
from core.regions import all_cells, referenced_cells, resolve_region


def evaluate_clue(clue: Clue, assignment: dict[str, bool], size: int) -> bool:
    
    expected_cells = set(all_cells(size))
    
    if not isinstance(assignment, Mapping):
        raise ValueError(
            f"Assignment must be a mapping of cell -> bool, got {type(assignment).__name__}"
        )
    
    if set(assignment.keys()) != expected_cells:
        missing = sorted(expected_cells - set(assignment.keys()))
        extra = sorted(set(assignment.keys()) - expected_cells)
        raise ValueError(
            f"Assignment keys must match exact {size}x{size} board "
                        f"(missing={missing}, extra={extra})"
        )
    
    for cell, value in assignment.items():
        if not isinstance(value, bool):
            raise ValueError(
                f"Assignment for cell {cell!r} must be a strict bool, got {value!r}"
            )

    # Validate clue structure, kind, cells/region, and k bounds.
    referenced_cells(clue,size)
    
    if clue.kind == "FACT":
        return assignment[clue.cells[0]] is clue.status
    
    if clue.kind == "SAME":
        a,b = clue.cells
        return assignment[a] == assignment[b]
    
    if clue.kind == "DIFFERENT":
        a,b = clue.cells
        return assignment[a] != assignment[b]
    
    if clue.kind in ("EXACTLY", "AT_LEAST", "AT_MOST"):
        
        assert clue.region is not None
        
        region_cells = resolve_region(clue.region, size)
        criminal_count = sum(1 for cell in region_cells if assignment[cell])

        if clue.kind == "EXACTLY":
            return criminal_count == clue.k
        
        if clue.kind == "AT_LEAST":
            return criminal_count >= clue.k
        
        if clue.kind == "AT_MOST":
            return criminal_count <= clue.k
        
    raise ValueError(f"Unsupported clue kind: {clue.kind!r}")
