from collections.abc import Callable

from contracts.models import Clue, Region


def describe_region(region: Region, size: int) -> str:
    kind = region.kind.upper()
    if kind == "ROW":
        return f"Row {region.index}"
    if kind == "COLUMN":
        col = chr(64 + region.index) if 1 <= region.index <= 26 else str(region.index)
        return f"Column {col}"
    if kind == "NEIGHBORS":
        anchor = region.anchor or "?"
        return f"Neighbors of {anchor}"
    if kind == "EXPLICIT":
        if not region.cells:
            return "Empty cell list"
        return f"Cells ({', '.join(region.cells)})"
    return f"{region.kind} region"


def _criminal_noun(count: int) -> str:
    return "Criminal" if count == 1 else "Criminals"


def _format_fact(clue: Clue, size: int) -> str:
    cell = clue.cells[0] if clue.cells else "?"
    label = "Criminal" if clue.status else "Innocent"
    return f"{cell} is {label}."


def _format_same(clue: Clue, size: int) -> str:
    if len(clue.cells) >= 2:
        return f"{clue.cells[0]} and {clue.cells[1]} have the same status."
    return f"Cells {', '.join(clue.cells)} have the same status."


def _format_different(clue: Clue, size: int) -> str:
    if len(clue.cells) >= 2:
        return f"{clue.cells[0]} and {clue.cells[1]} have different statuses."
    return f"Cells {', '.join(clue.cells)} have different statuses."


def _format_exactly(clue: Clue, size: int) -> str:
    target = describe_region(clue.region, size) if clue.region else "target region"
    return f"Exactly {clue.k} {_criminal_noun(clue.k)} in {target}."


def _format_at_least(clue: Clue, size: int) -> str:
    target = describe_region(clue.region, size) if clue.region else "target region"
    return f"At least {clue.k} {_criminal_noun(clue.k)} in {target}."


def _format_at_most(clue: Clue, size: int) -> str:
    target = describe_region(clue.region, size) if clue.region else "target region"
    return f"At most {clue.k} {_criminal_noun(clue.k)} in {target}."


def _format_parity(clue: Clue, size: int) -> str:
    target = describe_region(clue.region, size)
    parity = "even" if clue.k == 0 else "odd"
    return f"An {parity} number of Criminals in {target}."


def _format_compare(clue: Clue, size: int) -> str:
    left = describe_region(clue.region, size)
    right = describe_region(clue.other_region, size)
    relation = {"EQ": "equals", "LT": "is less than", "GT": "is greater than"}[clue.relation]
    return f"The number of Criminals in {left} {relation} the number in {right}."


clue_formatters: dict[str, Callable[[Clue, int], str]] = {
    "FACT": _format_fact,
    "SAME": _format_same,
    "DIFFERENT": _format_different,
    "EXACTLY": _format_exactly,
    "AT_LEAST": _format_at_least,
    "AT_MOST": _format_at_most,
    "PARITY": _format_parity,
    "COUNT_COMPARE": _format_compare,
}


def describe_clue(clue: Clue, size: int) -> str:
    formatter = clue_formatters.get(clue.kind.upper())
    if formatter is not None:
        return formatter(clue, size)

    # Extension templates are not frozen yet; expose raw public fields safely.
    parts = [clue.kind]
    if clue.cells:
        parts.append(f"cells=({', '.join(clue.cells)})")
    if clue.region is not None:
        parts.append(describe_region(clue.region, size))
    if clue.region is not None or clue.k:
        parts.append(f"k={clue.k}")
    return " | ".join(parts)
