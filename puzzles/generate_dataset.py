"""Seeded constructive generator for the Griductive benchmark puzzle dataset.

Generates schema v1 JSON puzzles (3x3, 4x4, 5x5) using only the 6 core clue
templates and 4 core region types, certified against three independent checks:
  1. All clues evaluate True under `solution` via `validation.semantics.evaluate_clue`.
  2. Complete clue set (with ZERO initial status units) has a UNIQUE solution.
  3. Puzzle is progressively solvable without guessing from `initially_revealed`.

Usage (run from `griductive-solver/`):
    python -m puzzles.generate_dataset
    python -m puzzles.generate_dataset --output puzzles/benchmark --seed 2026
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path

from contracts.models import Clue, Region
from core.regions import all_cells, referenced_cells, resolve_region
from validation.semantics import evaluate_clue

# 25 strictly alphabetical display names (A..Y) for boards up to 5x5.
_ALPHABETICAL_NAMES: tuple[str, ...] = (
    "Ada",
    "Bao",
    "Chi",
    "Duy",
    "Ella",
    "Finn",
    "Gia",
    "Hana",
    "Iris",
    "Jude",
    "Kien",
    "Linh",
    "Minh",
    "Nora",
    "Omar",
    "Phuc",
    "Quynh",
    "Ryan",
    "Sara",
    "Tuan",
    "Una",
    "Vy",
    "Wren",
    "Xuan",
    "Yuna",
)

_PROFESSIONS: tuple[str, ...] = (
    "Architect",
    "Baker",
    "Chemist",
    "Doctor",
    "Engineer",
    "Florist",
    "Guide",
    "Historian",
    "Illustrator",
    "Journalist",
    "Keeper",
    "Lawyer",
    "Mechanic",
    "Nurse",
    "Optician",
    "Pilot",
    "Ranger",
    "Scientist",
    "Sculptor",
    "Tailor",
    "Teacher",
    "Umpire",
    "Vet",
    "Weaver",
    "Writer",
)

_COUNTING_KINDS: tuple[str, ...] = ("EXACTLY", "AT_LEAST", "AT_MOST")
_BINARY_KINDS: tuple[str, ...] = ("SAME", "DIFFERENT")


@dataclass(frozen=True)
class PuzzleSpec:
    puzzle_id: str
    title: str
    size: int
    difficulty: str
    initial_count: int
    max_facts: int
    allowed_kinds: tuple[str, ...]
    allow_synergy_setup: bool
    seed_offset: int


DEFAULT_SUITE_SPECS: tuple[PuzzleSpec, ...] = (
    # 8 x 3x3 puzzles (2 Easy, 3 Medium, 3 Hard)
    PuzzleSpec("bench_3x3_01_easy", "3x3 Case 01 — Easy", 3, "easy", 2, 2, ("FACT", "SAME", "DIFFERENT", "EXACTLY", "AT_LEAST", "AT_MOST"), False, 101),
    PuzzleSpec("bench_3x3_02_easy", "3x3 Case 02 — Easy", 3, "easy", 2, 1, ("FACT", "SAME", "DIFFERENT", "EXACTLY", "AT_LEAST", "AT_MOST"), False, 102),
    PuzzleSpec("bench_3x3_03_medium", "3x3 Case 03 — Medium", 3, "medium", 1, 0, ("SAME", "DIFFERENT", "EXACTLY", "AT_LEAST", "AT_MOST"), True, 103),
    PuzzleSpec("bench_3x3_04_medium", "3x3 Case 04 — Medium", 3, "medium", 1, 0, ("SAME", "DIFFERENT", "EXACTLY", "AT_LEAST", "AT_MOST"), True, 104),
    PuzzleSpec("bench_3x3_05_medium", "3x3 Case 05 — Medium", 3, "medium", 1, 0, ("SAME", "DIFFERENT", "EXACTLY", "AT_LEAST", "AT_MOST"), True, 105),
    PuzzleSpec("bench_3x3_06_hard", "3x3 Case 06 — Hard", 3, "hard", 1, 0, ("EXACTLY", "AT_LEAST", "AT_MOST", "SAME", "DIFFERENT"), True, 106),
    PuzzleSpec("bench_3x3_07_hard", "3x3 Case 07 — Hard", 3, "hard", 1, 0, ("EXACTLY", "AT_LEAST", "AT_MOST"), True, 107),
    PuzzleSpec("bench_3x3_08_hard", "3x3 Case 08 — Hard", 3, "hard", 1, 0, ("EXACTLY", "AT_LEAST", "AT_MOST"), True, 108),
    # 6 x 4x4 puzzles (2 Easy, 2 Medium, 2 Hard)
    PuzzleSpec("bench_4x4_01_easy", "4x4 Case 01 — Easy", 4, "easy", 2, 2, ("FACT", "SAME", "DIFFERENT", "EXACTLY", "AT_LEAST", "AT_MOST"), False, 201),
    PuzzleSpec("bench_4x4_02_easy", "4x4 Case 02 — Easy", 4, "easy", 2, 1, ("FACT", "SAME", "DIFFERENT", "EXACTLY", "AT_LEAST", "AT_MOST"), False, 202),
    PuzzleSpec("bench_4x4_03_medium", "4x4 Case 03 — Medium", 4, "medium", 2, 0, ("SAME", "DIFFERENT", "EXACTLY", "AT_LEAST", "AT_MOST"), True, 203),
    PuzzleSpec("bench_4x4_04_medium", "4x4 Case 04 — Medium", 4, "medium", 1, 0, ("SAME", "DIFFERENT", "EXACTLY", "AT_LEAST", "AT_MOST"), True, 204),
    PuzzleSpec("bench_4x4_05_hard", "4x4 Case 05 — Hard", 4, "hard", 1, 0, ("EXACTLY", "AT_LEAST", "AT_MOST", "SAME", "DIFFERENT"), True, 205),
    PuzzleSpec("bench_4x4_06_hard", "4x4 Case 06 — Hard", 4, "hard", 1, 0, ("EXACTLY", "AT_LEAST", "AT_MOST"), True, 206),
    # 4 x 5x5 puzzles (1 Easy, 2 Medium, 1 Hard)
    PuzzleSpec("bench_5x5_01_easy", "5x5 Case 01 — Easy", 5, "easy", 2, 2, ("FACT", "SAME", "DIFFERENT", "EXACTLY", "AT_LEAST", "AT_MOST"), False, 301),
    PuzzleSpec("bench_5x5_02_medium", "5x5 Case 02 — Medium", 5, "medium", 2, 0, ("SAME", "DIFFERENT", "EXACTLY", "AT_LEAST", "AT_MOST"), True, 302),
    PuzzleSpec("bench_5x5_03_medium", "5x5 Case 03 — Medium", 5, "medium", 2, 0, ("SAME", "DIFFERENT", "EXACTLY", "AT_LEAST", "AT_MOST"), True, 303),
    PuzzleSpec("bench_5x5_04_hard", "5x5 Case 04 — Hard", 5, "hard", 1, 0, ("EXACTLY", "AT_LEAST", "AT_MOST", "SAME", "DIFFERENT"), True, 304),
)


# ---------------------------------------------------------------------------
# Internal offline constraint solver (used strictly for dataset generation &
# certification — never imported by production logic/solver modules).
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _CompiledClue:
    kind: str
    cells: tuple[int, ...]
    status: bool
    k: int


def _compile_clues(clues: list[Clue], cell_to_idx: dict[str, int], size: int) -> list[_CompiledClue]:
    compiled: list[_CompiledClue] = []
    for clue in clues:
        if clue.kind == "FACT":
            compiled.append(_CompiledClue("FACT", (cell_to_idx[clue.cells[0]],), clue.status, 0))
        elif clue.kind in _BINARY_KINDS:
            a, b = clue.cells
            compiled.append(_CompiledClue(clue.kind, (cell_to_idx[a], cell_to_idx[b]), True, 0))
        elif clue.kind in _COUNTING_KINDS:
            assert clue.region is not None
            rcells = tuple(cell_to_idx[c] for c in resolve_region(clue.region, size))
            compiled.append(_CompiledClue(clue.kind, rcells, True, clue.k))
        else:
            raise ValueError(f"Unsupported clue kind in generator: {clue.kind!r}")
    return compiled


def _propagate(compiled: list[_CompiledClue], assign: list[int]) -> bool:
    """In-place constraint propagation. assign[i]: -1=unknown, 0=False, 1=True."""
    changed = True
    while changed:
        changed = False
        for c in compiled:
            kind = c.kind
            if kind == "FACT":
                idx = c.cells[0]
                want = 1 if c.status else 0
                cur = assign[idx]
                if cur == -1:
                    assign[idx] = want
                    changed = True
                elif cur != want:
                    return False
            elif kind == "SAME":
                a, b = c.cells
                va, vb = assign[a], assign[b]
                if va != -1 and vb != -1:
                    if va != vb:
                        return False
                elif va != -1:
                    assign[b] = va
                    changed = True
                elif vb != -1:
                    assign[a] = vb
                    changed = True
            elif kind == "DIFFERENT":
                a, b = c.cells
                va, vb = assign[a], assign[b]
                if va != -1 and vb != -1:
                    if va == vb:
                        return False
                elif va != -1:
                    assign[b] = 1 - va
                    changed = True
                elif vb != -1:
                    assign[a] = 1 - vb
                    changed = True
            else:
                t_count = 0
                unknowns: list[int] = []
                for idx in c.cells:
                    v = assign[idx]
                    if v == 1:
                        t_count += 1
                    elif v == -1:
                        unknowns.append(idx)
                u_count = len(unknowns)
                k = c.k
                if kind == "EXACTLY":
                    if t_count > k or t_count + u_count < k:
                        return False
                    if u_count > 0:
                        if t_count == k:
                            for idx in unknowns:
                                assign[idx] = 0
                            changed = True
                        elif t_count + u_count == k:
                            for idx in unknowns:
                                assign[idx] = 1
                            changed = True
                elif kind == "AT_LEAST":
                    if t_count + u_count < k:
                        return False
                    if u_count > 0 and t_count + u_count == k:
                        for idx in unknowns:
                            assign[idx] = 1
                        changed = True
                elif kind == "AT_MOST":
                    if t_count > k:
                        return False
                    if u_count > 0 and t_count == k:
                        for idx in unknowns:
                            assign[idx] = 0
                        changed = True
    return True


def _pick_branch_var(compiled: list[_CompiledClue], assign: list[int]) -> int:
    """Pick an unknown variable appearing in the tightest active constraint."""
    best_var = -1
    best_score = (10**9, -1)
    freq = [0] * len(assign)
    min_slack = [10**9] * len(assign)
    for c in compiled:
        unknowns = [i for i in c.cells if assign[i] == -1]
        u_len = len(unknowns)
        if u_len == 0:
            continue
        for i in unknowns:
            freq[i] += 1
            if u_len < min_slack[i]:
                min_slack[i] = u_len
    for i, v in enumerate(assign):
        if v == -1:
            score = (min_slack[i], -freq[i])
            if score < best_score:
                best_score = score
                best_var = i
    return best_var


def _find_solutions(
    compiled: list[_CompiledClue],
    num_vars: int,
    fixed: dict[int, bool],
    *,
    limit: int = 2,
    node_budget: int = 50_000,
) -> tuple[list[tuple[bool, ...]], bool]:
    """Return (models_up_to_limit, budget_exhausted)."""
    init = [-1] * num_vars
    for idx, val in fixed.items():
        init[idx] = 1 if val else 0

    models: list[tuple[bool, ...]] = []
    nodes = 0
    exhausted = False

    def dfs(state: list[int]) -> None:
        nonlocal nodes, exhausted
        if len(models) >= limit or exhausted:
            return
        nodes += 1
        if nodes > node_budget:
            exhausted = True
            return
        if not _propagate(compiled, state):
            return
        var = _pick_branch_var(compiled, state)
        if var == -1:
            models.append(tuple(v == 1 for v in state))
            return
        for branch_val in (1, 0):
            nxt = state.copy()
            nxt[var] = branch_val
            dfs(nxt)
            if len(models) >= limit or exhausted:
                return

    dfs(init)
    return models, exhausted


def _entailed_unknowns(
    compiled: list[_CompiledClue],
    num_vars: int,
    proved_idx: dict[int, bool],
    solution_idx: tuple[bool, ...],
    *,
    node_budget: int = 8_000,
) -> list[int]:
    """Return indices of currently unknown cells mathematically entailed by KB."""
    base = [-1] * num_vars
    for idx, val in proved_idx.items():
        base[idx] = 1 if val else 0

    if not _propagate(compiled, base):
        return []

    entailed: list[int] = []
    still_unknown: list[int] = []
    for i in range(num_vars):
        if i in proved_idx:
            continue
        if base[i] != -1:
            entailed.append(i)
        else:
            still_unknown.append(i)

    # Check multi-clue entailment via refutation: KB ∧ (var != solution[var]) UNSAT.
    for i in still_unknown:
        refute_fixed = {j: (base[j] == 1) for j in range(num_vars) if base[j] != -1}
        refute_fixed[i] = not solution_idx[i]
        models, exhausted = _find_solutions(
            compiled, num_vars, refute_fixed, limit=1, node_budget=node_budget
        )
        if not exhausted and len(models) == 0:
            entailed.append(i)

    return entailed


# ---------------------------------------------------------------------------
# Candidate clue generation (6 core templates x 4 core regions)
# ---------------------------------------------------------------------------

def _all_standard_regions(size: int, cells: tuple[str, ...]) -> list[Region]:
    regions: list[Region] = []
    for idx in range(1, size + 1):
        regions.append(Region(kind="ROW", index=idx))
        regions.append(Region(kind="COLUMN", index=idx))
    for anchor in cells:
        regions.append(Region(kind="NEIGHBORS", anchor=anchor))
    return regions


def _sample_explicit_regions(
    rng: random.Random,
    cells: tuple[str, ...],
    unknown_cells: list[str],
    proved_cells: list[str],
    size: int,
    count: int = 24,
) -> list[Region]:
    regions: list[Region] = []
    seen: set[tuple[str, ...]] = set()
    min_sz = 2
    max_sz = min(size + 1, max(3, size))
    for _ in range(count * 3):
        if len(regions) >= count:
            break
        r_len = rng.randint(min_sz, max_sz)
        picked: set[str] = set()
        if unknown_cells:
            n_unk = rng.randint(1, min(len(unknown_cells), r_len))
            picked.update(rng.sample(unknown_cells, n_unk))
        if len(picked) < r_len and proved_cells:
            need = min(len(proved_cells), r_len - len(picked))
            picked.update(rng.sample(proved_cells, need))
        if len(picked) < r_len:
            rem = [c for c in cells if c not in picked]
            picked.update(rng.sample(rem, min(len(rem), r_len - len(picked))))
        reg = Region(kind="EXPLICIT", cells=tuple(sorted(picked)))
        canonical = resolve_region(reg, size)
        if len(canonical) >= 2 and canonical not in seen:
            seen.add(canonical)
            regions.append(Region(kind="EXPLICIT", cells=canonical))
    return regions


def _make_true_candidates(
    rng: random.Random,
    size: int,
    cells: tuple[str, ...],
    solution: dict[str, bool],
    proved_set: set[str],
    allowed_kinds: tuple[str, ...],
    used_signatures: set[tuple],
    *,
    allow_facts: bool,
    target_cells: list[str] | None = None,
) -> list[Clue]:
    """Generate a diverse list of valid, true candidate clues."""
    unknown_cells = [c for c in cells if c not in proved_set]
    proved_cells = [c for c in cells if c in proved_set]
    focus = target_cells if target_cells is not None else unknown_cells
    focus_set = set(focus)

    candidates: list[Clue] = []
    local_seen: set[tuple] = set()

    def add_candidate(clue: Clue) -> None:
        sig = (
            clue.kind,
            clue.cells,
            clue.status,
            clue.region,
            clue.k,
        )
        if sig in used_signatures or sig in local_seen:
            return
        if not evaluate_clue(clue, solution, size):
            return
        local_seen.add(sig)
        candidates.append(clue)

    if allow_facts and "FACT" in allowed_kinds:
        for cell in focus:
            add_candidate(Clue(id="TMP", kind="FACT", cells=(cell,), status=solution[cell]))

    if "SAME" in allowed_kinds or "DIFFERENT" in allowed_kinds:
        # Pair each focus cell with proved cells (direct propagation) and other unknown cells (synergy).
        pair_pool: list[tuple[str, str]] = []
        for u in focus:
            for p in proved_cells:
                if u != p:
                    pair_pool.append((p, u))
            for other in unknown_cells:
                if u < other:
                    pair_pool.append((u, other))
        rng.shuffle(pair_pool)
        for a, b in pair_pool[:60]:
            same_val = solution[a] == solution[b]
            kind = "SAME" if same_val else "DIFFERENT"
            if kind in allowed_kinds:
                add_candidate(Clue(id="TMP", kind=kind, cells=(a, b)))

    counting_allowed = [k for k in _COUNTING_KINDS if k in allowed_kinds]
    if counting_allowed:
        std_regions = _all_standard_regions(size, cells)
        exp_regions = _sample_explicit_regions(rng, cells, focus, proved_cells, size, count=24)
        all_regions = std_regions + exp_regions
        rng.shuffle(all_regions)

        for region in all_regions:
            rcells = resolve_region(region, size)
            if focus_set and not (focus_set.intersection(rcells)):
                continue
            true_count = sum(1 for c in rcells if solution[c])
            r_len = len(rcells)
            if "EXACTLY" in counting_allowed:
                add_candidate(Clue(id="TMP", kind="EXACTLY", region=region, k=true_count))
            if "AT_LEAST" in counting_allowed and true_count > 0:
                # Tight bound (true_count) is strongest; also include true_count - 1 for multi-clue variety.
                add_candidate(Clue(id="TMP", kind="AT_LEAST", region=region, k=true_count))
                if true_count >= 2:
                    add_candidate(Clue(id="TMP", kind="AT_LEAST", region=region, k=true_count - 1))
            if "AT_MOST" in counting_allowed and true_count < r_len:
                add_candidate(Clue(id="TMP", kind="AT_MOST", region=region, k=true_count))
                if true_count + 1 < r_len:
                    add_candidate(Clue(id="TMP", kind="AT_MOST", region=region, k=true_count + 1))

    rng.shuffle(candidates)
    return candidates


def _clue_signature(clue: Clue) -> tuple:
    return (clue.kind, clue.cells, clue.status, clue.region, clue.k)


# ---------------------------------------------------------------------------
# Constructive wave generator & 3-way certifier
# ---------------------------------------------------------------------------

def _generate_balanced_solution(rng: random.Random, cells: tuple[str, ...]) -> dict[str, bool]:
    n = len(cells)
    lo = max(2, int(round(n * 0.35)))
    hi = min(n - 2, int(round(n * 0.65)))
    num_criminals = rng.randint(lo, hi)
    criminals = set(rng.sample(cells, num_criminals))
    return {c: (c in criminals) for c in cells}


def _certify_puzzle(
    size: int,
    cells: tuple[str, ...],
    solution: dict[str, bool],
    clues_by_owner: dict[str, Clue],
    initially_revealed: tuple[str, ...],
) -> tuple[bool, int]:
    """Verify all 3 mandatory properties; returns (ok, progressive_waves)."""
    if set(clues_by_owner.keys()) != set(cells):
        return False, 0

    # 1. Independent semantic truth check for every clue.
    for clue in clues_by_owner.values():
        referenced_cells(clue, size)
        if not evaluate_clue(clue, solution, size):
            return False, 0

    cell_to_idx = {c: i for i, c in enumerate(cells)}
    sol_idx = tuple(solution[c] for c in cells)
    all_compiled = _compile_clues([clues_by_owner[c] for c in cells], cell_to_idx, size)

    # 2. Complete-clue uniqueness with ZERO initial status units.
    models, exhausted = _find_solutions(all_compiled, len(cells), {}, limit=2, node_budget=100_000)
    if exhausted or len(models) != 1 or models[0] != sol_idx:
        return False, 0

    # 3. Progressive solvability from initially_revealed (statuses + clues).
    proved_idx: dict[int, bool] = {cell_to_idx[c]: solution[c] for c in initially_revealed}
    revealed_owners: set[str] = set(initially_revealed)
    waves = 0

    while len(proved_idx) < len(cells):
        active_clues = [clues_by_owner[c] for c in cells if c in revealed_owners]
        active_compiled = _compile_clues(active_clues, cell_to_idx, size)
        newly_entailed = _entailed_unknowns(
            active_compiled, len(cells), proved_idx, sol_idx, node_budget=15_000
        )
        if not newly_entailed:
            return False, waves
        waves += 1
        for idx in newly_entailed:
            proved_idx[idx] = sol_idx[idx]
            revealed_owners.add(cells[idx])

    return True, waves


def generate_puzzle(spec: PuzzleSpec, base_seed: int, max_attempts: int = 80) -> tuple[dict, dict]:
    """Generate one certified schema v1 puzzle dict and its generation stats."""
    cells = all_cells(spec.size)
    cell_to_idx = {c: i for i, c in enumerate(cells)}
    num_vars = len(cells)

    for attempt in range(max_attempts):
        rng = random.Random(base_seed * 1009 + spec.seed_offset * 97 + attempt)
        solution = _generate_balanced_solution(rng, cells)
        sol_idx = tuple(solution[c] for c in cells)

        init_cells = tuple(sorted(rng.sample(cells, spec.initial_count), key=lambda c: cell_to_idx[c]))
        proved_set: set[str] = set(init_cells)
        proved_idx: dict[int, bool] = {cell_to_idx[c]: solution[c] for c in init_cells}

        clues_by_owner: dict[str, Clue] = {}
        unassigned_owners: list[str] = list(init_cells)
        used_signatures: set[tuple] = set()
        kind_counts: dict[str, int] = {}
        region_counts: dict[str, int] = {}
        facts_used = 0
        failed = False

        # Phase 1: Constructive progressive waves until all N*N cells are proved.
        while len(proved_set) < num_vars:
            if not unassigned_owners:
                failed = True
                break
            owner = unassigned_owners.pop(0)
            must_force = len(unassigned_owners) == 0

            active_list = list(clues_by_owner.values())
            active_compiled = _compile_clues(active_list, cell_to_idx, spec.size)

            allow_facts = facts_used < spec.max_facts and "FACT" in spec.allowed_kinds
            cands = _make_true_candidates(
                rng,
                spec.size,
                cells,
                solution,
                proved_set,
                spec.allowed_kinds,
                used_signatures,
                allow_facts=allow_facts,
            )

            # Fallback pool if strict profile ran dry on a tight frontier.
            fallback_kinds = ("EXACTLY", "AT_LEAST", "AT_MOST", "SAME", "DIFFERENT")
            if must_force and not cands:
                cands = _make_true_candidates(
                    rng,
                    spec.size,
                    cells,
                    solution,
                    proved_set,
                    fallback_kinds,
                    used_signatures,
                    allow_facts=False,
                )

            best_choice: tuple[Clue, list[int]] | None = None
            best_score: tuple | None = None

            # Evaluate a bounded sample for speed (especially on 5x5).
            sample_limit = 36 if spec.size <= 4 else 28
            for cand in cands[:sample_limit]:
                trial_compiled = active_compiled + _compile_clues([cand], cell_to_idx, spec.size)
                forced = _entailed_unknowns(
                    trial_compiled, num_vars, proved_idx, sol_idx, node_budget=4_000
                )
                n_forced = len(forced)
                if must_force and n_forced == 0:
                    continue
                if not must_force and n_forced == 0 and not spec.allow_synergy_setup:
                    continue

                # Favor smaller forced increments (deeper chains) + diverse kinds/regions.
                # For hard puzzles, slightly prefer counting clues over binary clues.
                k_used = kind_counts.get(cand.kind, 0)
                r_used = region_counts.get(cand.region.kind, 0) if cand.region else 0
                is_fact_pen = 1 if cand.kind == "FACT" else 0
                hard_binary_pen = 1 if (spec.difficulty == "hard" and cand.kind in _BINARY_KINDS) else 0
                # Ideal forced count is 1..2; 0 only allowed as synergy setup when other owners wait.
                if n_forced == 0:
                    # Prefer synergy clues that touch >= 2 unknown cells.
                    unk_touch = sum(1 for c in referenced_cells(cand, spec.size) if c not in proved_set)
                    if unk_touch < 2:
                        continue
                    force_pen = 2
                else:
                    force_pen = abs(n_forced - 1)

                score = (is_fact_pen, hard_binary_pen, force_pen, k_used, r_used, rng.random())
                if best_score is None or score < best_score:
                    best_score = score
                    best_choice = (cand, forced)

            # Second chance if restricted sample didn't find a forcing clue when must_force=True.
            if best_choice is None and must_force:
                broad_cands = _make_true_candidates(
                    rng,
                    spec.size,
                    cells,
                    solution,
                    proved_set,
                    fallback_kinds + ("FACT",),
                    used_signatures,
                    allow_facts=(facts_used < max(1, spec.max_facts)),
                )
                for cand in broad_cands[:60]:
                    trial_compiled = active_compiled + _compile_clues([cand], cell_to_idx, spec.size)
                    forced = _entailed_unknowns(
                        trial_compiled, num_vars, proved_idx, sol_idx, node_budget=6_000
                    )
                    if forced:
                        best_choice = (cand, forced)
                        break

            if best_choice is None:
                failed = True
                break

            chosen_clue, forced_indices = best_choice
            clues_by_owner[owner] = chosen_clue
            used_signatures.add(_clue_signature(chosen_clue))
            kind_counts[chosen_clue.kind] = kind_counts.get(chosen_clue.kind, 0) + 1
            if chosen_clue.region is not None:
                region_counts[chosen_clue.region.kind] = region_counts.get(chosen_clue.region.kind, 0) + 1
            if chosen_clue.kind == "FACT":
                facts_used += 1

            for idx in forced_indices:
                cell = cells[idx]
                if cell not in proved_set:
                    proved_set.add(cell)
                    proved_idx[idx] = sol_idx[idx]
                    unassigned_owners.append(cell)

        if failed or len(proved_set) != num_vars:
            continue

        # Phase 2: Fill remaining owner slots & guarantee complete-clue UNIQUE
        # (with ZERO initial status units!).
        remaining_owners = [c for c in cells if c not in clues_by_owner]
        rng.shuffle(remaining_owners)

        for owner in remaining_owners:
            current_compiled = _compile_clues(list(clues_by_owner.values()), cell_to_idx, spec.size)
            models, exhausted = _find_solutions(current_compiled, num_vars, {}, limit=2, node_budget=30_000)

            chosen: Clue | None = None
            if not exhausted and len(models) >= 2:
                # Find cells that differ between the true solution and the competing model.
                alt_model = models[1] if models[0] == sol_idx else models[0]
                diff_cells = [cells[i] for i in range(num_vars) if alt_model[i] != sol_idx[i]]

                close_cands = _make_true_candidates(
                    rng,
                    spec.size,
                    cells,
                    solution,
                    set(cells) - set(diff_cells),
                    spec.allowed_kinds,
                    used_signatures,
                    allow_facts=(facts_used < spec.max_facts),
                    target_cells=diff_cells,
                )
                if not close_cands:
                    close_cands = _make_true_candidates(
                        rng,
                        spec.size,
                        cells,
                        solution,
                        set(cells) - set(diff_cells),
                        ("EXACTLY", "AT_LEAST", "AT_MOST", "SAME", "DIFFERENT", "FACT"),
                        used_signatures,
                        allow_facts=True,
                        target_cells=diff_cells,
                    )

                # Pick a true clue that rules out the competing model!
                alt_assignment = {cells[i]: alt_model[i] for i in range(num_vars)}
                for cand in close_cands:
                    if not evaluate_clue(cand, alt_assignment, spec.size):
                        chosen = cand
                        break

            if chosen is None:
                # Already unique (or fallback): pick a diverse thematic true clue.
                filler_cands = _make_true_candidates(
                    rng,
                    spec.size,
                    cells,
                    solution,
                    set(),
                    spec.allowed_kinds,
                    used_signatures,
                    allow_facts=False,
                    target_cells=list(cells),
                )
                if not filler_cands:
                    filler_cands = _make_true_candidates(
                        rng,
                        spec.size,
                        cells,
                        solution,
                        set(),
                        ("EXACTLY", "AT_LEAST", "AT_MOST", "SAME", "DIFFERENT"),
                        used_signatures,
                        allow_facts=False,
                        target_cells=list(cells),
                    )
                if filler_cands:
                    filler_cands.sort(
                        key=lambda c: (
                            kind_counts.get(c.kind, 0),
                            region_counts.get(c.region.kind, 0) if c.region else 0,
                            rng.random(),
                        )
                    )
                    chosen = filler_cands[0]

            if chosen is None:
                failed = True
                break

            clues_by_owner[owner] = chosen
            used_signatures.add(_clue_signature(chosen))
            kind_counts[chosen.kind] = kind_counts.get(chosen.kind, 0) + 1
            if chosen.region is not None:
                region_counts[chosen.region.kind] = region_counts.get(chosen.region.kind, 0) + 1
            if chosen.kind == "FACT":
                facts_used += 1

        if failed or len(clues_by_owner) != num_vars:
            continue

        # Assign canonical sequential clue IDs C01..C{N*N} in row-major owner order.
        final_clues: dict[str, Clue] = {}
        for idx, owner in enumerate(cells, start=1):
            c = clues_by_owner[owner]
            final_clues[owner] = Clue(
                id=f"C{idx:02d}",
                kind=c.kind,
                cells=c.cells,
                status=c.status,
                region=c.region,
                k=c.k,
            )

        ok, waves = _certify_puzzle(spec.size, cells, solution, final_clues, init_cells)
        if not ok:
            continue

        # Enforce minimum wave depth so puzzles aren't 1-step trivial.
        min_waves = 2 if spec.size == 3 else 3
        if waves < min_waves and attempt < max_attempts - 10:
            continue

        puzzle_json = _serialize_puzzle(spec, cells, solution, final_clues, init_cells, rng)
        stats = {
            "id": spec.puzzle_id,
            "size": spec.size,
            "difficulty": spec.difficulty,
            "initial": len(init_cells),
            "waves": waves,
            "kinds": dict(sorted(kind_counts.items())),
            "regions": dict(sorted(region_counts.items())),
            "attempts": attempt + 1,
        }
        return puzzle_json, stats

    raise RuntimeError(f"Failed to generate certified puzzle {spec.puzzle_id} in {max_attempts} attempts")


def _serialize_region(region: Region) -> dict:
    if region.kind in ("ROW", "COLUMN"):
        return {"kind": region.kind, "index": region.index}
    if region.kind == "NEIGHBORS":
        return {"kind": "NEIGHBORS", "anchor": region.anchor}
    if region.kind == "EXPLICIT":
        return {"kind": "EXPLICIT", "cells": list(region.cells)}
    raise ValueError(f"Unsupported region kind: {region.kind!r}")


def _serialize_clue(clue: Clue) -> dict:
    if clue.kind == "FACT":
        return {"id": clue.id, "kind": "FACT", "cells": list(clue.cells), "status": clue.status}
    if clue.kind in _BINARY_KINDS:
        return {"id": clue.id, "kind": clue.kind, "cells": list(clue.cells)}
    if clue.kind in _COUNTING_KINDS:
        assert clue.region is not None
        return {
            "id": clue.id,
            "kind": clue.kind,
            "region": _serialize_region(clue.region),
            "k": clue.k,
        }
    raise ValueError(f"Unsupported clue kind: {clue.kind!r}")


def _serialize_puzzle(
    spec: PuzzleSpec,
    cells: tuple[str, ...],
    solution: dict[str, bool],
    clues_by_owner: dict[str, Clue],
    initially_revealed: tuple[str, ...],
    rng: random.Random,
) -> dict:
    profs = list(_PROFESSIONS[: len(cells)])
    rng.shuffle(profs)
    characters = [
        {"cell": cell, "name": _ALPHABETICAL_NAMES[i], "profession": profs[i]}
        for i, cell in enumerate(cells)
    ]
    return {
        "schema_version": 1,
        "id": spec.puzzle_id,
        "title": spec.title,
        "size": spec.size,
        "characters": characters,
        "solution": {cell: solution[cell] for cell in cells},
        "clues": {cell: _serialize_clue(clues_by_owner[cell]) for cell in cells},
        "initially_revealed": list(initially_revealed),
    }


def _write_json_lf(path: Path, payload: dict) -> str:
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    data = text.encode("utf-8")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def generate_suite(output_dir: Path, base_seed: int = 2026) -> list[dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []

    for spec in DEFAULT_SUITE_SPECS:
        payload, stats = generate_puzzle(spec, base_seed=base_seed)
        out_path = output_dir / f"{spec.puzzle_id}.json"
        sha256 = _write_json_lf(out_path, payload)
        stats["file"] = out_path.name
        stats["sha256"] = sha256[:12]
        results.append(stats)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate certified Griductive benchmark puzzles.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("puzzles/benchmark"),
        help="Target directory for generated benchmark JSON files.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=2026,
        help="Master deterministic seed.",
    )
    args = parser.parse_args()

    results = generate_suite(args.output, base_seed=args.seed)
    print(f"Generated and certified {len(results)} puzzles in {args.output}:")
    print(f"{'ID':<22} {'Size':>4} {'Diff':<7} {'Init':>4} {'Waves':>5}  {'Kinds & Regions'}")
    print("-" * 88)
    for r in results:
        print(
            f"{r['id']:<22} {r['size']}x{r['size']}  {r['difficulty']:<7} "
            f"{r['initial']:>4} {r['waves']:>5}  kinds={r['kinds']} regions={r['regions']}"
        )


if __name__ == "__main__":
    main()
