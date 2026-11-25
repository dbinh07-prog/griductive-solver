"""Unit tests for core.puzzle_loader, dataset integrity, and validation.puzzles."""

import copy
import itertools
import json
from pathlib import Path
import tempfile
import unittest

from contracts.models import (
    Analysis,
    CNF,
    Character,
    Clue,
    PublicState,
    Puzzle,
    Region,
    SATQuery,
    SolverStats,
    SolverTimeout,
    Status,
    Uniqueness,
)
from core.puzzle_loader import load_puzzle
from core.regions import all_cells
from validation.puzzles import validate_puzzle
from validation.semantics import evaluate_clue

_REPO_ROOT = Path(__file__).resolve().parent.parent
_EXAMPLE_3X3 = _REPO_ROOT / "puzzles" / "examples" / "example_3x3.json"
_BENCHMARK_DIR = _REPO_ROOT / "puzzles" / "benchmark"


class _BruteForceTestAgent:
    """Test-only exact semantic Agent for small boards (size <= 3)."""

    def __init__(self) -> None:
        self.last_uniqueness_state: PublicState | None = None

    def _satisfying_models(
        self, public_state: PublicState
    ) -> list[dict[str, bool]]:
        cells = all_cells(public_state.size)
        proved = dict(public_state.proved_statuses)
        clues = tuple(clue for _, clue in public_state.revealed_clues)
        models: list[dict[str, bool]] = []

        for bits in itertools.product((False, True), repeat=len(cells)):
            assignment = dict(zip(cells, bits))
            if any(assignment[c] is not val for c, val in proved.items()):
                continue
            if all(evaluate_clue(clue, assignment, public_state.size) for clue in clues):
                models.append(assignment)
        return models

    def analyze(
        self, public_state: PublicState, *, timeout_s: float = 5.0
    ) -> Analysis:
        cells = all_cells(public_state.size)
        proved = {c for c, _ in public_state.proved_statuses}
        primary = tuple((cell, idx + 1) for idx, cell in enumerate(cells))
        cnf = CNF(clauses=(), primary_variables=primary, variable_count=len(cells))

        models = self._satisfying_models(public_state)
        if not models:
            return Analysis(
                puzzle_id=public_state.puzzle_id,
                revision=public_state.revision,
                classifications=(),
                inconsistent=True,
                cnf=cnf,
                queries=(SATQuery((), False, SolverStats()),),
            )

        classifications: list[tuple[str, Status]] = []
        for cell in cells:
            if cell in proved:
                continue
            values = {model[cell] for model in models}
            if values == {True}:
                classifications.append((cell, Status.CRIMINAL))
            elif values == {False}:
                classifications.append((cell, Status.INNOCENT))
            else:
                classifications.append((cell, Status.UNKNOWN))

        return Analysis(
            puzzle_id=public_state.puzzle_id,
            revision=public_state.revision,
            classifications=tuple(classifications),
            inconsistent=False,
            cnf=cnf,
            queries=(SATQuery((), True, SolverStats()),),
        )

    def next_forced(self, analysis: Analysis) -> tuple[str, Status] | None:
        if analysis.inconsistent:
            return None
        for cell, status in analysis.classifications:
            if status in (Status.CRIMINAL, Status.INNOCENT):
                return (cell, status)
        return None

    def check_uniqueness(
        self, full_clue_state: PublicState, *, timeout_s: float = 5.0
    ) -> Uniqueness:
        self.last_uniqueness_state = full_clue_state
        models = self._satisfying_models(full_clue_state)
        if not models:
            return Uniqueness.INCONSISTENT
        if len(models) == 1:
            return Uniqueness.UNIQUE
        return Uniqueness.MULTIPLE


class _TimeoutTestAgent(_BruteForceTestAgent):
    """Test-only Agent that simulates a SolverTimeout during uniqueness."""

    def check_uniqueness(
        self, full_clue_state: PublicState, *, timeout_s: float = 5.0
    ) -> Uniqueness:
        raise SolverTimeout("Simulated timeout")


def _valid_2x2_dict() -> dict:
    return {
        "schema_version": 1,
        "id": "valid_2x2",
        "title": "Valid 2x2 Fixture",
        "size": 2,
        "characters": [
            {"cell": "A1", "name": "Ada", "profession": "Architect"},
            {"cell": "B1", "name": "Bao", "profession": "Baker"},
            {"cell": "A2", "name": "Chi", "profession": "Chemist"},
            {"cell": "B2", "name": "Duy", "profession": "Doctor"},
        ],
        "solution": {"A1": True, "B1": False, "A2": True, "B2": False},
        "clues": {
            "A1": {"id": "C01", "kind": "FACT", "cells": ["B1"], "status": False},
            "B1": {"id": "C02", "kind": "SAME", "cells": ["A1", "A2"]},
            "A2": {"id": "C03", "kind": "DIFFERENT", "cells": ["A2", "B2"]},
            "B2": {
                "id": "C04",
                "kind": "EXACTLY",
                "region": {"kind": "ROW", "index": 1},
                "k": 1,
            },
        },
        "initially_revealed": ["A1"],
    }


def _make_2x2_puzzle(
    puzzle_id: str,
    clues: tuple[tuple[str, Clue], ...],
    initially_revealed: tuple[str, ...] = ("A1",),
) -> Puzzle:
    return Puzzle(
        id=puzzle_id,
        title=puzzle_id,
        size=2,
        characters=(
            Character("A1", "Ada", "Architect"),
            Character("B1", "Bao", "Baker"),
            Character("A2", "Chi", "Chemist"),
            Character("B2", "Duy", "Doctor"),
        ),
        solution=(("A1", True), ("B1", False), ("A2", True), ("B2", False)),
        clues=clues,
        initially_revealed=initially_revealed,
    )


class PuzzleTests(unittest.TestCase):
    def _load_from_dict(self, payload: dict) -> Puzzle:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return load_puzzle(path)

    def test_reject_missing_duplicate_or_invalid_data(self):
        # Baseline valid fixture loads cleanly.
        loaded = self._load_from_dict(_valid_2x2_dict())
        self.assertEqual(loaded.id, "valid_2x2")
        self.assertEqual(loaded.size, 2)

        def mutate(fn):
            d = copy.deepcopy(_valid_2x2_dict())
            fn(d)
            return d

        bad_cases = [
            ("missing_key", mutate(lambda d: d.pop("clues"))),
            ("extra_top_key", mutate(lambda d: d.__setitem__("extra", 1))),
            ("bad_schema_version", mutate(lambda d: d.__setitem__("schema_version", 2))),
            ("bool_schema_version", mutate(lambda d: d.__setitem__("schema_version", True))),
            ("bool_size", mutate(lambda d: d.__setitem__("size", True))),
            ("zero_size", mutate(lambda d: d.__setitem__("size", 0))),
            ("missing_character", mutate(lambda d: d["characters"].pop())),
            (
                "wrong_character_order",
                mutate(
                    lambda d: d["characters"].__setitem__(
                        0, {"cell": "B1", "name": "Ada", "profession": "Architect"}
                    )
                ),
            ),
            (
                "duplicate_character_name",
                mutate(lambda d: d["characters"][1].__setitem__("name", "Ada")),
            ),
            (
                "non_alphabetical_names",
                mutate(lambda d: d["characters"][0].__setitem__("name", "Zoe")),
            ),
            ("missing_solution_cell", mutate(lambda d: d["solution"].pop("B2"))),
            ("non_bool_solution", mutate(lambda d: d["solution"].__setitem__("A1", 1))),
            ("missing_clue_owner", mutate(lambda d: d["clues"].pop("B2"))),
            (
                "duplicate_clue_id",
                mutate(lambda d: d["clues"]["B1"].__setitem__("id", "C01")),
            ),
            (
                "bool_as_counting_k",
                mutate(lambda d: d["clues"]["B2"].__setitem__("k", True)),
            ),
            (
                "out_of_bounds_counting_k",
                mutate(lambda d: d["clues"]["B2"].__setitem__("k", 3)),
            ),
            (
                "binary_duplicate_cells",
                mutate(lambda d: d["clues"]["B1"].__setitem__("cells", ["A1", "A1"])),
            ),
            (
                "unsupported_extension_kind",
                mutate(
                    lambda d: d["clues"].__setitem__(
                        "B2",
                        {
                            "id": "C04",
                            "kind": "PARITY",
                            "region": {"kind": "ROW", "index": 1},
                            "k": 0,
                        },
                    )
                ),
            ),
            (
                "duplicate_initial_cell",
                mutate(lambda d: d.__setitem__("initially_revealed", ["A1", "A1"])),
            ),
            (
                "out_of_bounds_initial_cell",
                mutate(lambda d: d.__setitem__("initially_revealed", ["C1"])),
            ),
        ]

        for label, payload in bad_cases:
            with self.subTest(case=label):
                with self.assertRaises(ValueError):
                    self._load_from_dict(payload)

        # Duplicate JSON object keys in raw JSON must also be rejected.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dup_key.json"
            raw_json = json.dumps(_valid_2x2_dict()).replace(
                '"A1": true', '"A1": true, "A1": false', 1
            )
            path.write_text(raw_json, encoding="utf-8")
            with self.assertRaises(ValueError):
                load_puzzle(path)

    def test_all_clues_true_under_declared_solution(self):
        # Schema example 3x3 loads and passes all 3 validation checks.
        example = load_puzzle(_EXAMPLE_3X3)
        agent = _BruteForceTestAgent()
        ex_res = validate_puzzle(example, agent)
        self.assertTrue(ex_res.all_clues_true)
        self.assertEqual(ex_res.complete_clues_uniqueness, Uniqueness.UNIQUE)
        self.assertTrue(ex_res.progressively_solvable)
        self.assertEqual(ex_res.issues, ())

        # Verify check_uniqueness received ALL clues and ZERO hidden solution units.
        assert agent.last_uniqueness_state is not None
        self.assertEqual(agent.last_uniqueness_state.proved_statuses, ())
        self.assertEqual(len(agent.last_uniqueness_state.revealed_clues), 9)

        # Every JSON file in puzzles/benchmark/ must load cleanly and satisfy all clues.
        bench_files = sorted(_BENCHMARK_DIR.glob("*.json"))
        self.assertGreater(len(bench_files), 0, "Expected benchmark JSON files")
        for path in bench_files:
            with self.subTest(file=path.name):
                puzzle = load_puzzle(path)
                sol = dict(puzzle.solution)
                for owner, clue in puzzle.clues:
                    self.assertTrue(
                        evaluate_clue(clue, sol, puzzle.size),
                        f"{path.name}: clue {clue.id} (owner {owner}) is False under solution",
                    )
                # Full 3-check validation for 3x3 benchmark puzzles via exact test agent.
                if puzzle.size <= 3:
                    val_res = validate_puzzle(puzzle, _BruteForceTestAgent())
                    self.assertTrue(val_res.all_clues_true, val_res.issues)
                    self.assertEqual(
                        val_res.complete_clues_uniqueness, Uniqueness.UNIQUE, val_res.issues
                    )
                    self.assertTrue(val_res.progressively_solvable, val_res.issues)

    def test_unique_does_not_imply_progressively_solvable(self):
        # Negative fixture 1: all clues true & UNIQUE complete-clue solution,
        # but stalls immediately from initially_revealed=("A1",).
        stalled_unique = _make_2x2_puzzle(
            "neg_unique_stalled",
            clues=(
                (
                    "A1",
                    Clue("C01", "AT_LEAST", region=Region("ROW", index=1), k=1),
                ),
                ("B1", Clue("C02", "FACT", cells=("B1",), status=False)),
                ("A2", Clue("C03", "FACT", cells=("A2",), status=True)),
                ("B2", Clue("C04", "FACT", cells=("B2",), status=False)),
            ),
            initially_revealed=("A1",),
        )
        res_stalled = validate_puzzle(stalled_unique, _BruteForceTestAgent())
        self.assertTrue(res_stalled.all_clues_true)
        self.assertEqual(res_stalled.complete_clues_uniqueness, Uniqueness.UNIQUE)
        self.assertFalse(res_stalled.progressively_solvable)
        self.assertGreater(len(res_stalled.issues), 0)

        # Negative fixture 2: all clues true, but MULTIPLE solutions (B2 unconstrained).
        multiple_puzzle = _make_2x2_puzzle(
            "neg_multiple",
            clues=(
                ("A1", Clue("C01", "FACT", cells=("A1",), status=True)),
                ("B1", Clue("C02", "FACT", cells=("B1",), status=False)),
                ("A2", Clue("C03", "SAME", cells=("A1", "A2"))),
                ("B2", Clue("C04", "AT_LEAST", region=Region("ROW", index=2), k=1)),
            ),
            initially_revealed=("A1",),
        )
        res_multiple = validate_puzzle(multiple_puzzle, _BruteForceTestAgent())
        self.assertTrue(res_multiple.all_clues_true)
        self.assertEqual(res_multiple.complete_clues_uniqueness, Uniqueness.MULTIPLE)
        self.assertFalse(res_multiple.progressively_solvable)

        # Negative fixture 3: INCONSISTENT clue set (false under solution + contradictory).
        inconsistent_puzzle = _make_2x2_puzzle(
            "neg_inconsistent",
            clues=(
                ("A1", Clue("C01", "FACT", cells=("A1",), status=False)),
                ("B1", Clue("C02", "FACT", cells=("A1",), status=True)),
                ("A2", Clue("C03", "FACT", cells=("A2",), status=True)),
                ("B2", Clue("C04", "FACT", cells=("B2",), status=False)),
            ),
            initially_revealed=("A1",),
        )
        res_inconsistent = validate_puzzle(inconsistent_puzzle, _BruteForceTestAgent())
        self.assertFalse(res_inconsistent.all_clues_true)
        self.assertEqual(
            res_inconsistent.complete_clues_uniqueness, Uniqueness.INCONSISTENT
        )
        self.assertFalse(res_inconsistent.progressively_solvable)

        # Timeout must propagate as SolverTimeout, never coerced to UNSAT/INCONSISTENT.
        with self.assertRaises(SolverTimeout):
            validate_puzzle(stalled_unique, _TimeoutTestAgent())


if __name__ == "__main__":
    unittest.main()