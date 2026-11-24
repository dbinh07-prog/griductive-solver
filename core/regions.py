from contracts.models import Clue, Region


def all_cells(size: int) -> tuple[str, ...]:
    """Member 3: row-major order A1,B1,...,A2,B2,... ."""
    raise NotImplementedError("Member 3: implement canonical cell order")


def resolve_region(region: Region, size: int) -> tuple[str, ...]:
    """Member 3: neighbors include diagonals, exclude anchor."""
    raise NotImplementedError("Member 3: implement and validate regions")


def referenced_cells(clue: Clue, size: int) -> tuple[str, ...]:
    """Member 3: core references; extend after member 2 selects extension semantics."""
    raise NotImplementedError("Member 3: return distinct referenced cells")
