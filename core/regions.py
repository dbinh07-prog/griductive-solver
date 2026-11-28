from contracts.models import Clue, Region

_BINARY_KINDS = frozenset({"SAME", "DIFFERENT"})
_COUNTING_KINDS = frozenset({"EXACTLY", "AT_LEAST", "AT_MOST"})


def _is_strict_int(value : object) -> bool:
    
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_size(size : int) -> None:
    
    if _is_strict_int(size) and 1 <= size <= 26:
        return None
    else :
        raise ValueError(f"Board size must be an int in [1, 26], got {size!r}")
    
    
def _parse_cell(cell : str, size : int) -> tuple[int, int]:
    
    #Validate cell
    if not isinstance(cell, str) or len(cell) < 2:
        raise ValueError(f"Invalid cell identifier: {cell!r}")
    
    #Validate column char
    col_ch = cell[0]
    
    if not ('A' <= col_ch <= "Z"):
        raise ValueError(f"Invalid column in cell {cell!r}")
    
    col = ord(col_ch) - ord("A") + 1
    
    if col > size:
        raise ValueError(f"Column out of bounds for size {size}: {cell!r}")
    
    #Validate row string
    row_str = cell[1:]
    
    if not (row_str.isascii() and row_str.isdigit()) or row_str.startswith("0"):
        raise ValueError(f"Invalid row in cell {cell!r}")
    
    row = int(row_str)
    
    if not (1 <= row <= size):
        raise ValueError(f"Row out of bounds for size {size}: {cell!r}")
    
    return (row, col)
    

def _format_cell(row : int, col : int) -> str:
    
    return f"{chr(ord('A') + col - 1)}{row}"


def all_cells(size: int) -> tuple[str, ...]:
    
    _validate_size(size)
    
    return tuple(
        _format_cell(row, col)
        for row in range(1, size + 1)
        for col in range(1, size + 1)
    )


def resolve_region(region: Region, size: int) -> tuple[str, ...]:
    
    _validate_size(size)
    
    if not isinstance(region, Region):
        raise ValueError(f"Expected Region instance, got {type(region).__name__}")
    
    if region.kind == "ROW":
        
        if region.anchor != "" or region.cells != ():
            raise ValueError(f"ROW region must not set anchor or cells: {region!r}")

        if not _is_strict_int(region.index) or not (1 <= region.index <= size):
            raise ValueError(
                f"ROW index must be an int in [1, {size}], got {region.index!r}"
            )
        
        return tuple(_format_cell(region.index, col) for col in range(1, size + 1))
    
    if region.kind == "COLUMN":
        
        if region.anchor != "" or region.cells != ():
            raise ValueError(f"COLUMN region must not set anchor or cells: {region!r}")

        if not _is_strict_int(region.index) or not (1 <= region.index <= size):
                    raise ValueError(
                        f"COLUMN index must be an int in [1, {size}], got {region.index!r}"
                    )
                    
        return tuple(_format_cell(row, region.index) for row in range(1, size + 1))

    if region.kind == "NEIGHBORS":
        
        if not _is_strict_int(region.index) or region.index != 0 or region.cells != ():
            raise ValueError(f"NEIGHBORS region must not set index or cells: {region!r}")
        
        anchor_row, anchor_col = _parse_cell(region.anchor, size)
        
        neighbors : list[str] = []
        
        for dr in (-1, 0, 1):
            
            for dc in (-1, 0, 1):
                
                if dr == 0 and dc == 0:
                    continue
                nr, nc = anchor_row + dr, anchor_col + dc
                
                if 1 <= nr <= size and 1 <= nc <= size :
                    neighbors.append(_format_cell(nr, nc))
                
        return tuple(neighbors)    
    
    if region.kind == "EXPLICIT":
        
        if not _is_strict_int(region.index) or region.index != 0 or region.anchor != "":
            raise ValueError(f"EXPLICIT region must not set index or anchor: {region!r}")

        if not isinstance(region.cells, tuple):
            raise ValueError(
                f"EXPLICIT region cells must be a tuple, got {type(region.cells).__name__}"
            )
        
        seen : set[str] = set()
        parsed : list[tuple[tuple[int, int], str]] = []
        
        for cell in region.cells:
            
            coord = _parse_cell(cell, size)
            
            if cell in seen:
                raise ValueError(f"Duplicate cell in EXPLICIT region: {cell!r}")
        
            seen.add(cell)
            parsed.append((coord, cell))
            
        parsed.sort(key = lambda item : item[0])
        
        return tuple(cell for _, cell in parsed)
    
    raise ValueError(f"Unsupported region kind : {region.kind!r}")
        
        
def referenced_cells(clue: Clue, size: int) -> tuple[str, ...]:
    
    _validate_size(size)
    
    if not isinstance(clue, Clue):
        raise ValueError(f"Expected Clue instance, got {type(clue).__name__}")

    if clue.kind == "COUNT_COMPARE":
        if clue.cells != () or clue.status is not True or type(clue.k) is not int or clue.k != 0:
            raise ValueError("COUNT_COMPARE requires default cells, status and k")
        if not isinstance(clue.relation, str) or clue.relation not in ("EQ", "LT", "GT"):
            raise ValueError("COUNT_COMPARE relation must be EQ, LT or GT")
        left = resolve_region(clue.region, size)
        right = resolve_region(clue.other_region, size)
        cells = set(left) | set(right)
        return tuple(cell for cell in all_cells(size) if cell in cells)

    if clue.other_region is not None or clue.relation is not None:
        raise ValueError(f"{clue.kind} does not use other_region or relation")

    if clue.kind == "PARITY":
        if clue.cells != () or clue.status is not True:
            raise ValueError("PARITY requires default cells and status")
        if type(clue.k) is not int or clue.k not in (0, 1):
            raise ValueError("PARITY k must be 0 (even) or 1 (odd)")
        return resolve_region(clue.region, size)

    if clue.kind == "FACT":
        
        if not isinstance(clue.cells, tuple) or len(clue.cells) != 1:
            raise ValueError(f"FACT clue requires exactly 1 cell, got {clue.cells!r}")
        
        if not isinstance(clue.status, bool):
            raise ValueError(f"FACT status must be a bool, got {clue.status!r}")
        
        if clue.region is not None or not _is_strict_int(clue.k) or clue.k != 0:
            raise ValueError(f"FACT clue must not set region or k: {clue!r}")
        
        _parse_cell(clue.cells[0], size)
        
        return (clue.cells[0],)
    
    if clue.kind in _BINARY_KINDS:
        
        if not isinstance(clue.cells, tuple) or len(clue.cells) != 2:
            raise ValueError(
                f"{clue.kind} clue requires exactly 2 cells, got {clue.cells!r}"
            )
        
        if clue.region is not None or not _is_strict_int(clue.k) or clue.k != 0:
            raise ValueError(f"{clue.kind} clue must not set region or k: {clue!r}")
        
        if clue.status is not True:
            raise ValueError(f"{clue.kind} clue must keep default status=True: {clue!r}")
        
        a,b = clue.cells
        coord_a = _parse_cell(a, size)
        coord_b = _parse_cell(b, size)
        
        if a == b:
            raise ValueError(f"{clue.kind} clue requires two distinct cells, got {a!r}")
        
        return (a,b) if coord_a < coord_b else (b,a)
    
    if clue.kind in _COUNTING_KINDS:   
        
        if clue.cells != () or clue.status is not True:
            raise ValueError(
                f"{clue.kind} clue must not set cells or non-default status: {clue!r}"
            )
            
        if clue.region is None:
            raise ValueError(f"{clue.kind} clue requires a region")
        
        if not _is_strict_int(clue.k):
            raise ValueError(f"{clue.kind} clue k must be a strict int, got {clue.k!r}")
        
        cells = resolve_region(clue.region, size)
        
        if not (0 <= clue.k <= len(cells)):
            raise ValueError(
                f"{clue.kind} clue k={clue.k} out of bounds for region of size {len(cells)}"
            )
        
        return cells

    raise ValueError(f"Unsupported clue kind: {clue.kind!r}")
