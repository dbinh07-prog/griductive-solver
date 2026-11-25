"""Unit tests for core.game_engine.GameEngine."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
import unittest

from contracts.models import (
    Analysis,
    CNF,
    Character,
    Clue,
    PublicState,
    Puzzle,
    SATQuery,
    SolverStats,
    Status,
    VerdictResult,
)
from core.game_engine import GameEngine
from core.regions import all_cells


def _make_sample_puzzle(
    puzzle_id: str = "test_2x2",
    initially_revealed: tuple[str, ...] = ("A1",),
) -> Puzzle:
    characters = (
        Character("A1", "Ada", "Architect"),
        Character("B1", "Bao", "Baker"),
        Character("A2", "Chi", "Chemist"),
        Character("B2", "Duy", "Doctor"),
    )
    solution = (
        ("A1", True),
        ("B1", False),
        ("A2", True),
        ("B2", False),
    )
    clues = (
        ("A1", Clue("C01", "FACT", cells=("B1",), status=False)),
        ("B1", Clue("C02", "FACT", cells=("A2",), status=True)),
        ("A2", Clue("C03", "FACT", cells=("B2",), status=False)),
        ("B2", Clue("C04", "FACT", cells=("A1",), status=True)),
    )
    return Puzzle(
        id=puzzle_id,
        title="Test 2x2 Case",
        size=2,
        characters=characters,
        solution=solution,
        clues=clues,
        initially_revealed=initially_revealed,
    )


def _make_analysis(
    state: PublicState,
    overrides: dict[str, Status] | None = None,
    *,
    inconsistent: bool = False,
    puzzle_id: str | None = None,
    revision: int | None = None,
) -> Analysis:
    revealed = {cell for cell, _ in state.proved_statuses}
    mapping = overrides or {}
    cells = all_cells(state.size)
    primary = tuple((cell, idx + 1) for idx, cell in enumerate(cells))
    cnf = CNF(clauses=(), primary_variables=primary, variable_count=len(cells))

    if inconsistent:
        classifications: tuple[tuple[str, Status], ...] = ()
        queries = (SATQuery(assumptions=(), satisfiable=False, stats=SolverStats()),)
    else:
        classifications = tuple(
            (cell, mapping.get(cell, Status.UNKNOWN))
            for cell in cells
            if cell not in revealed
        )
        queries = (SATQuery(assumptions=(), satisfiable=True, stats=SolverStats()),)

    return Analysis(
        puzzle_id=state.puzzle_id if puzzle_id is None else puzzle_id,
        revision=state.revision if revision is None else revision,
        classifications=classifications,
        inconsistent=inconsistent,
        cnf=cnf,
        queries=queries,
    )


def _assert_deeply_immutable(test_case: unittest.TestCase, obj: object) -> None:
    test_case.assertNotIsInstance(obj, (dict, list, set))
    if isinstance(obj, tuple):
        for item in obj:
            _assert_deeply_immutable(test_case, item)
    elif is_dataclass(obj):
        for f in fields(obj):
            _assert_deeply_immutable(test_case, getattr(obj, f.name))


class EngineTests(unittest.TestCase):
    def test_initial_cards_publish_status_and_clue(self):
        puzzle = _make_sample_puzzle(initially_revealed=("A1", "B2"))
        engine = GameEngine(puzzle)
        state = engine.public_state()

        self.assertEqual(state.puzzle_id, "test_2x2")
        self.assertEqual(state.revision, 0)
        self.assertEqual(state.proved_statuses, (("A1", True), ("B2", False)))
        self.assertEqual(
            tuple(owner for owner, _ in state.revealed_clues),
            ("A1", "B2"),
        )
        self.assertEqual(
            tuple(clue.id for _, clue in state.revealed_clues),
            ("C01", "C04"),
        )
        self.assertFalse(engine.is_solved())

    def test_reject_leaves_state_unchanged(self):
        puzzle = _make_sample_puzzle(initially_revealed=("A1",))
        engine = GameEngine(puzzle)
        before = engine.public_state()

        # 1. NOT_PROVABLE even when proposed verdict matches hidden solution (B1 is False).
        analysis_unknown = _make_analysis(before, {"B1": Status.UNKNOWN})
        res_lucky_guess = engine.submit_verdict("B1", Status.INNOCENT, analysis_unknown)
        self.assertEqual(res_lucky_guess.result, VerdictResult.NOT_PROVABLE)
        self.assertIsNone(res_lucky_guess.revealed_clue)
        self.assertEqual(res_lucky_guess.new_public_state, before)
        self.assertEqual(engine.public_state(), before)

        # 2. NOT_PROVABLE when proposed verdict disagrees with hidden solution.
        res_wrong_guess = engine.submit_verdict("B1", Status.CRIMINAL, analysis_unknown)
        self.assertEqual(res_wrong_guess.result, VerdictResult.NOT_PROVABLE)
        self.assertIsNone(res_wrong_guess.revealed_clue)
        self.assertEqual(engine.public_state(), before)

        # 3. CONTRADICTED when opposite verdict is entailed.
        analysis_b1_innocent = _make_analysis(before, {"B1": Status.INNOCENT})
        res_contradicted = engine.submit_verdict("B1", Status.CRIMINAL, analysis_b1_innocent)
        self.assertEqual(res_contradicted.result, VerdictResult.CONTRADICTED)
        self.assertIsNone(res_contradicted.revealed_clue)
        self.assertEqual(res_contradicted.new_public_state, before)
        self.assertEqual(engine.public_state(), before)

        # 4. INCONSISTENT when analysis reports inconsistent KB.
        analysis_inconsistent = _make_analysis(before, inconsistent=True)
        res_inconsistent = engine.submit_verdict("B1", Status.INNOCENT, analysis_inconsistent)
        self.assertEqual(res_inconsistent.result, VerdictResult.INCONSISTENT)
        self.assertIsNone(res_inconsistent.revealed_clue)
        self.assertEqual(res_inconsistent.new_public_state, before)
        self.assertEqual(engine.public_state(), before)

        # 5. ALREADY_REVEALED when submitting an initially revealed cell.
        res_already = engine.submit_verdict("A1", Status.CRIMINAL, analysis_unknown)
        self.assertEqual(res_already.result, VerdictResult.ALREADY_REVEALED)
        self.assertIsNone(res_already.revealed_clue)
        self.assertEqual(res_already.new_public_state, before)
        self.assertEqual(engine.public_state(), before)

    def test_accepted_reveal_adds_status_and_clue(self):
        puzzle = _make_sample_puzzle(initially_revealed=("A1",))
        engine = GameEngine(puzzle)

        steps = (
            ("B1", Status.INNOCENT, "C02"),
            ("A2", Status.CRIMINAL, "C03"),
            ("B2", Status.INNOCENT, "C04"),
        )
        for expected_rev, (cell, verdict, expected_clue_id) in enumerate(steps, start=1):
            state = engine.public_state()
            analysis = _make_analysis(state, {cell: verdict})
            result = engine.submit_verdict(cell, verdict, analysis)

            self.assertEqual(result.result, VerdictResult.ACCEPTED)
            self.assertIsNotNone(result.revealed_clue)
            assert result.revealed_clue is not None
            self.assertEqual(result.revealed_clue.id, expected_clue_id)
            self.assertEqual(result.new_public_state.revision, expected_rev)
            self.assertIn(cell, dict(result.new_public_state.proved_statuses))
            self.assertIn(cell, dict(result.new_public_state.revealed_clues))

        self.assertTrue(engine.is_solved())
        final_state = engine.public_state()
        self.assertEqual(final_state.proved_statuses, puzzle.solution)
        self.assertEqual(final_state.revealed_clues, puzzle.clues)

    def test_snapshot_is_immutable_and_public_only(self):
        puzzle = _make_sample_puzzle(initially_revealed=("A1",))
        engine = GameEngine(puzzle)
        state = engine.public_state()

        # PublicState is frozen and contains no mutable nested containers.
        with self.assertRaises(FrozenInstanceError):
            state.revision = 999  # type: ignore[misc]
        _assert_deeply_immutable(self, state)

        # PublicState must not leak hidden solution or unrevealed clues.
        self.assertFalse(hasattr(state, "solution"))
        self.assertFalse(hasattr(state, "clues"))
        self.assertEqual(len(state.proved_statuses), 1)
        self.assertEqual(len(state.revealed_clues), 1)
        self.assertNotIn("B1", dict(state.proved_statuses))
        self.assertNotIn("B1", dict(state.revealed_clues))

    def test_stale_analysis_and_restart(self):
        puzzle = _make_sample_puzzle(initially_revealed=("A1",))
        engine = GameEngine(puzzle)

        state0 = engine.public_state()
        analysis0 = _make_analysis(state0, {"B1": Status.INNOCENT, "A2": Status.CRIMINAL})

        # Accept B1 -> revision becomes 1.
        res = engine.submit_verdict("B1", Status.INNOCENT, analysis0)
        self.assertEqual(res.result, VerdictResult.ACCEPTED)
        self.assertEqual(res.new_public_state.revision, 1)

        # Reusing revision 0 analysis must raise ValueError.
        with self.assertRaises(ValueError):
            engine.submit_verdict("A2", Status.CRIMINAL, analysis0)

        # Mismatched puzzle_id must raise ValueError.
        state1 = engine.public_state()
        wrong_puzzle_analysis = _make_analysis(
            state1, {"A2": Status.CRIMINAL}, puzzle_id="other_puzzle"
        )
        with self.assertRaises(ValueError):
            engine.submit_verdict("A2", Status.CRIMINAL, wrong_puzzle_analysis)

        # Restart resets progress back to initial cards and advances revision (1 -> 2).
        restarted = engine.restart()
        self.assertEqual(restarted.revision, 2)
        self.assertEqual(restarted.proved_statuses, (("A1", True),))
        self.assertEqual(tuple(owner for owner, _ in restarted.revealed_clues), ("A1",))
        self.assertFalse(engine.is_solved())

        # Analysis from pre-restart revision 1 must be rejected as stale.
        stale_pre_restart = _make_analysis(state1, {"B1": Status.INNOCENT})
        with self.assertRaises(ValueError):
            engine.submit_verdict("B1", Status.INNOCENT, stale_pre_restart)

    def test_input_validation_and_proof_solution_mismatch(self):
        puzzle = _make_sample_puzzle(initially_revealed=("A1",))
        engine = GameEngine(puzzle)
        state = engine.public_state()
        analysis = _make_analysis(state, {"B1": Status.INNOCENT})

        # Bad cell, Status.UNKNOWN, and raw string verdict raise ValueError.
        with self.assertRaises(ValueError):
            engine.submit_verdict("Z9", Status.INNOCENT, analysis)
        with self.assertRaises(ValueError):
            engine.submit_verdict("B1", Status.UNKNOWN, analysis)
        with self.assertRaises(ValueError):
            engine.submit_verdict("B1", "INNOCENT", analysis)  # type: ignore[arg-type]

        # Missing unresolved cell from analysis.classifications raises ValueError.
        incomplete_analysis = Analysis(
            puzzle_id=state.puzzle_id,
            revision=state.revision,
            classifications=(("A2", Status.UNKNOWN),),
            inconsistent=False,
            cnf=analysis.cnf,
            queries=analysis.queries,
        )
        with self.assertRaises(ValueError):
            engine.submit_verdict("B1", Status.INNOCENT, incomplete_analysis)

        # Entailed verdict contradicting private solution returns INCONSISTENT without reveal.
        corrupt_analysis = _make_analysis(state, {"B1": Status.CRIMINAL})
        res = engine.submit_verdict("B1", Status.CRIMINAL, corrupt_analysis)
        self.assertEqual(res.result, VerdictResult.INCONSISTENT)
        self.assertIsNone(res.revealed_clue)
        self.assertEqual(engine.public_state(), state)


if __name__ == "__main__":
    unittest.main()