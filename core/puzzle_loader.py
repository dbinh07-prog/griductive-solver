import json
from pathlib import Path

from contracts.models import Character, Clue, Puzzle, Region
from core.regions import all_cells, referenced_cells

_REQUIRED_TOP_KEYS = frozenset(
    {
        "schema_version",
        "id",
        "title",
        "size",
        "characters",
        "solution",
        "clues",
        "initially_revealed",
    }
)

_CHARACTER_KEYS = frozenset({"cell", "name", "profession"})
_FACT_KEYS = frozenset({"id", "kind", "cells", "status"})
_BINARY_KEYS = frozenset({"id", "kind", "cells"})
_COUNTING_KEYS = frozenset({"id", "kind", "region", "k"})
_BINARY_KINDS = frozenset({"SAME", "DIFFERENT"})
_COUNTING_KINDS = frozenset({"EXACTLY", "AT_LEAST", "AT_MOST"})

def _is_strict_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _require_non_empty_str(value: object, field_name: str) -> str:
    
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string, got {value!r}")
    
    return value


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    
    result : dict[str, object] = {}
    
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key : {key!r}")
        result[key] = value

    return result 


def _parse_region(raw_region : object) -> Region:
    
    if not isinstance(raw_region, dict):
        raise ValueError(
            f"Region must be a JSON object, got {type(raw_region).__name__}"
        )
        
    kind = raw_region.get("kind")
    
    if not isinstance(kind, str):
        raise ValueError(f"Region kind must be a string, got {kind!r}")
    
    keys = set(raw_region.keys())
    
    if kind in ("ROW", "COLUMN"):
        
        if keys != {"kind", "index"}:
            raise ValueError(
                f"{kind} region must have exact keys {{'kind', 'index'}}, got {sorted(keys)}"
            )
        
        index = raw_region["index"]     
        
        if not  _is_strict_int(index):
            raise ValueError(f"{kind} region index must be a strict int, got {index!r}")
        
        return Region(kind = kind, index = index)
    
    if kind == "NEIGHBORS":
        
        if keys != {"kind", "anchor"}:
            raise ValueError(
                f"NEIGHBORS region must have exact keys {{'kind', 'anchor'}}, got {sorted(keys)}"
            )
        
        anchor = raw_region["anchor"]
        
        if not isinstance(anchor, str):
            raise ValueError(f"NEIGHBORS anchor must be a string, got {anchor!r}")
        
        return Region(kind = "NEIGHBORS", anchor = anchor)
    
    if kind == "EXPLICIT":
        
        if keys != {"kind", "cells"}:
            raise ValueError(
                f"EXPLICIT region must have exact keys {{'kind', 'cells'}}, got {sorted(keys)}"
            )
            
        raw_cells = raw_region["cells"]
        
        if not isinstance(raw_cells, list) or not all(
            isinstance(c, str) for c in raw_cells
        ):
            raise ValueError(
                f"EXPLICIT region cells must be a list of strings, got {raw_cells!r}"
            )
        
        return Region(kind = "EXPLICIT", cells = tuple(raw_cells))
    
    raise ValueError(f"Unsupported region kind: {kind!r}")
    

def _parse_clue(owner : str, raw_clue : object, size : int) -> Clue:
    
    if not isinstance(raw_clue, dict):
        raise ValueError(
            f"Clue for owner {owner!r} must be a JSON object, got {type(raw_clue).__name__}"
        )
        
    clue_id = _require_non_empty_str(raw_clue.get("id"), f"clues[{owner!r}].id")
    kind = raw_clue.get("kind")
    
    if not isinstance(kind, str):
        raise ValueError(
            f"clues[{owner!r}].kind must be a string, got {kind!r}"
        )
        
    keys = set(raw_clue.keys())
    
    if kind == "FACT":
        if keys != _FACT_KEYS:
            raise ValueError(
                f"FACT clue {clue_id!r} must have exact keys {sorted(_FACT_KEYS)}, got {sorted(keys)}"
            )
            
        raw_cells = raw_clue["cells"]
        status = raw_clue["status"]
    
        if not isinstance(raw_cells, list) or len(raw_cells) != 1 or not isinstance(raw_cells[0], str):
            raise ValueError(
                f"FACT clue {clue_id!r} cells must be a 1-element list of strings, got {raw_cells!r}"
            )
    
        if not isinstance(status, bool):
            raise ValueError(
                f"FACT clue {clue_id!r} status must be a strict bool, got {status!r}"
            )
    
        clue = Clue(id = clue_id, kind = "FACT", cells = (raw_cells[0],), status = status)
    
    elif kind in _BINARY_KINDS:
        
        if keys != _BINARY_KEYS:
            raise ValueError(
                f"{kind} clue {clue_id!r} must have exact keys {sorted(_BINARY_KEYS)}, got {sorted(keys)}"
            )
        
        raw_cells = raw_clue["cells"]
        
        if(
            not isinstance(raw_cells, list)
            or len(raw_cells) != 2
            or not all(isinstance(c, str) for c in raw_cells)
        ):
            raise ValueError(
                f"{kind} clue {clue_id!r} cells must be a 2-element list of strings, got {raw_cells!r}"
            )
            
        clue = Clue(id = clue_id, kind = kind, cells = (raw_cells[0], raw_cells[1]))
        
    elif kind in _COUNTING_KINDS:
        
        if keys != _COUNTING_KEYS:
            raise ValueError(
                f"{kind} clue {clue_id!r} must have exact keys {sorted(_COUNTING_KEYS)}, got {sorted(keys)}"
            )
            
        k = raw_clue["k"]
        
        if not _is_strict_int(k):
            raise ValueError(
                f"{kind} clue {clue_id!r} k must be a strict int (bool forbidden), got {k!r}"
            )
        
        region = _parse_region(raw_clue["region"])
        clue = Clue(id = clue_id, kind = kind, region = region, k = k)
        
    
    else :
        raise ValueError(f"Unsupported clue kind {kind!r} in clue {clue_id!r}")    
    
    # Validate cell coordinates, distinct binary operands, region validity, and 0 <= k <= |R|.
    referenced_cells(clue, size)
    return clue

    
def load_puzzle(path: str | Path) -> Puzzle:
    
    puzzle_path = Path(path)
    raw_text = puzzle_path.read_text(encoding = "utf-8")
    data = json.loads(raw_text, object_pairs_hook = _reject_duplicate_json_keys)
    
    if not isinstance(data, dict):
        raise ValueError(
            f"Puzzle JSON top-level must be an object, got {type(data).__name__}"
        )
    
    top_keys = set(data.keys())
    
    if top_keys != _REQUIRED_TOP_KEYS:
        missing = sorted(_REQUIRED_TOP_KEYS - top_keys)
        extra = sorted(top_keys - _REQUIRED_TOP_KEYS)
        raise ValueError(
            f"Invalid top-level keys (missing={missing}, extra={extra})"
        )
    
    schema_version = data["schema_version"]
    
    if not _is_strict_int(schema_version) or schema_version != 1:
        raise ValueError(
            f"Unsupported schema_version: expected integer 1, got {schema_version!r}"
        )
    
    puzzle_id = _require_non_empty_str(data["id"], "id")
    title = _require_non_empty_str(data["title"], "title")
    
    size = data["size"]
    expected_cells = all_cells(size)
    expected_cell_set = set(expected_cells)
    cell_rank = {cell : idx for idx, cell in enumerate(expected_cells)}
    
    # characters
    
    raw_chars = data["characters"]
    
    if not isinstance(raw_chars, list) or len(raw_chars) != len(expected_cells):
        raise ValueError(
            f"characters must be a list of length {len(expected_cells)}, "
            f"got {type(raw_chars).__name__}"
            + (f" of length {len(raw_chars)}" if isinstance(raw_chars, list) else "")
        )
        
    characters : list[Character] = []
    seen_names_folded : set[str] = set()
    prev_name_folded : str | None = None

    for idx, entry in enumerate(raw_chars):
        if not isinstance(entry, dict):
            raise ValueError(
                f"characters[{idx}] must be an object, got {type(entry).__name__}"
            )

        if set(entry.keys()) != _CHARACTER_KEYS:
            raise ValueError(
                f"characters[{idx}] must have exact keys {sorted(_CHARACTER_KEYS)}, "
                f"got {sorted(entry.keys())}"
            )
            
        cell = _require_non_empty_str(entry["cell"], f"characters[{idx}].cell")
        name = _require_non_empty_str(entry["name"], f"characters[{idx}].name")
        profession = _require_non_empty_str(
            entry["profession"], f"characters[{idx}].profession"
        )
        
        expected_cell = expected_cells[idx]
        
        if cell != expected_cell:
            raise ValueError(
                f"characters[{idx}].cell must be {expected_cell!r} (canonical row-major order), "
                f"got {cell!r}"
            )
        
        name_folded = name.casefold()
        
        if name_folded in seen_names_folded:
            raise ValueError(f"Duplicate character name: {name!r}")
        
        if prev_name_folded is not None and name_folded < prev_name_folded:
            raise ValueError(
                f"Character names must be alphabetically sorted in row-major order: "
                f"{name!r} appeared after {characters[-1].name!r}"
            )
            
        seen_names_folded.add(name_folded)
        prev_name_folded = name_folded
        characters.append(Character(cell = cell, name = name, profession = profession))

    # solution

    raw_solution = data["solution"]

    if not isinstance(raw_solution, dict):
        raise ValueError(
            f"solution must be a JSON object, got {type(raw_solution).__name__}"
        )

    sol_keys = set(raw_solution.keys())

    if sol_keys != expected_cell_set:
        missing = sorted(expected_cell_set - sol_keys)
        extra = sorted(sol_keys - expected_cell_set)
        raise ValueError(
            f"solution keys must match exact {size}x{size} board "
            f"(missing={missing}, extra={extra})"
        )

    solution_pairs : list[tuple[str, bool]] = []
    for cell in expected_cells:
        val = raw_solution[cell]
        if not isinstance(val, bool):
            raise ValueError(
                f"solution[{cell!r}] must be a strict bool, got {val!r}"
            )

        solution_pairs.append((cell, val))

    # clues

    raw_clues = data["clues"]

    if not isinstance(raw_clues, dict):
        raise ValueError(
            f"clues must be a JSON object, got {type(raw_clues).__name__}"
        )

    clue_keys = set(raw_clues.keys())

    if clue_keys != expected_cell_set:
        missing = sorted(expected_cell_set - clue_keys)
        extra = sorted(clue_keys - expected_cell_set)
        raise ValueError(
            f"clues owner keys must match exact {size}x{size} board "
            f"(missing={missing}, extra={extra})"
        )

    seen_clue_ids: set[str] = set()
    clue_pairs: list[tuple[str, Clue]] = []

    for cell in expected_cells:
        clue = _parse_clue(cell, raw_clues[cell], size)

        if clue.id in seen_clue_ids:
            raise ValueError(f"Duplicate clue id: {clue.id!r}")

        seen_clue_ids.add(clue.id)

        clue_pairs.append((cell, clue))

    # Initially Revealed

    raw_initial = data["initially_revealed"]

    if not isinstance(raw_initial, list):
        raise ValueError(
            f"initially_revealed must be a list, got {type(raw_initial).__name__}"
        )

    seen_initial: set[str] = set()
    initial_cells: list[str] = []

    for item in raw_initial:
        if not isinstance(item, str) or item not in expected_cell_set:
            raise ValueError(
                f"Invalid cell in initially_revealed for size {size}: {item!r}"
            )

        if item in seen_initial:
            raise ValueError(f"Duplicate cell in initially_revealed: {item!r}")
        seen_initial.add(item)

        initial_cells.append(item)

    initial_cells.sort(key=lambda c: cell_rank[c])

    return Puzzle(
        id = puzzle_id,
        title = title,
        size = size,
        characters = tuple(characters),
        solution = tuple(solution_pairs),
        clues = tuple(clue_pairs),
        initially_revealed = tuple(initial_cells),
    )