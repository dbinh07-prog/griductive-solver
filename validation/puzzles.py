from dataclasses import dataclass

from contracts.models import (
    PublicState,
    Puzzle,
    Uniqueness,
    VerdictResult,
)

from contracts.ports import Agent
from core.game_engine import GameEngine
from core.regions import all_cells
from validation.semantics import evaluate_clue


@dataclass(frozen=True)
class ValidationResult:
    all_clues_true: bool
    complete_clues_uniqueness: Uniqueness
    progressively_solvable: bool
    issues: tuple[str, ...]


def validate_puzzle(puzzle: Puzzle, agent: Agent, *, timeout_s : float = 5.0) -> ValidationResult:
    
    if not isinstance(puzzle, Puzzle):
        raise ValueError(f"Expected Puzzle instance, got {type(puzzle).__name__}")
    
    if isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float)) or timeout_s <= 0:
        raise ValueError(f"timeout_s must be a positive number, got {timeout_s!r}")
    
    issues : list[str] = []
    
    # Independent semantic truth check against declared
    solution_map = dict(puzzle.solution)
    all_clues_true = True

    for owner, clue in puzzle.clues:
        try:
            is_true = evaluate_clue(clue, solution_map, puzzle.size)
        except ValueError as exc:
            all_clues_true = False
            issues.append(f"Clue {clue.id} (owner {owner}) invalid: {exc}")
            continue
        if not is_true:
            all_clues_true = False
            issues.append(
                f"Clue {clue.id} (owner {owner}) evaluates False under declared solution"
            )
        
    # Offline complete-clue uniqueness with ZERO hidden solution units.
    full_clue_state = PublicState(
        puzzle_id=puzzle.id,
        title=puzzle.title,
        size=puzzle.size,
        characters=puzzle.characters,
        proved_statuses=(),
        revealed_clues=puzzle.clues,
        revision=0,
    )
    
    # Note: SolverTimeout must propagate rather than being coerced to UNSAT/INCONSISTENT.
    complete_clues_uniqueness = agent.check_uniqueness(
        full_clue_state, timeout_s=timeout_s
    )
    if complete_clues_uniqueness is not Uniqueness.UNIQUE:
        issues.append(
            f"Complete clue set uniqueness is {complete_clues_uniqueness.value}, expected UNIQUE"
        )
    
    # Progressive no-guess solvability starting strictly from initially_revealed.
    engine = GameEngine(puzzle)
    ordered_cells = all_cells(puzzle.size)
    max_steps = len(ordered_cells) + 1
    progressively_solvable = False

    for _ in range(max_steps):
        if engine.is_solved():
            progressively_solvable = True
            break

        state = engine.public_state()
        analysis = agent.analyze(state, timeout_s = timeout_s)
        if analysis.inconsistent:
            issues.append(
                f"Progressive solve became INCONSISTENT at revision {state.revision}"
            )
            break
        
        forced = agent.next_forced(analysis)
        
        if forced is None:
            proved_cells = {c for c, _ in state.proved_statuses}
            unresolved = [c for c in ordered_cells if c not in proved_cells]
            issues.append(
                f"Progressive solve stalled at revision {state.revision} "
                f"(unresolved={unresolved})"
            )
            break
        
        cell, proposed = forced
        submit = engine.submit_verdict(cell, proposed, analysis)
        
        if submit.result is not VerdictResult.ACCEPTED:
            issues.append(
                f"Progressive solve rejected forced move {cell}={proposed.value} "
                f"at revision {state.revision}: {submit.result.value}"
            )
            break
        
    return ValidationResult(
        all_clues_true=all_clues_true,
        complete_clues_uniqueness=complete_clues_uniqueness,
        progressively_solvable=progressively_solvable,
        issues=tuple(issues),
    )
    
    
