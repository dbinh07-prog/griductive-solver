from dataclasses import replace
from itertools import product
from pathlib import Path
import unittest

from algorithms.dpll import DPLLSolver
from contracts.models import Character, Clue, PublicState, Region
from core.game_engine import GameEngine
from core.puzzle_loader import load_puzzle
from core.regions import all_cells, resolve_region
from logic.encoder import CNFEncoder
from validation.semantics import evaluate_clue


def make_state(clues=(), known=(), size=2):
    cells = all_cells(size)
    characters = tuple(Character(c, f"Person {i:02d}", "Tester") for i, c in enumerate(cells))
    return PublicState("encoder_test", "Encoder test", size, characters,
                       tuple(known), tuple(zip(cells, clues)))


def check_equivalent(test, clues, known=(), size=2):
    state = make_state(clues, known, size)
    before = repr(state)
    cnf = CNFEncoder().encode(state)
    cells = all_cells(size)
    test.assertEqual(cnf.primary_variables, tuple((c, i + 1) for i, c in enumerate(cells)))
    test.assertGreaterEqual(cnf.variable_count, len(cells))
    for bits in product((False, True), repeat=len(cells)):
        assignment = dict(zip(cells, bits))
        expected = all(evaluate_clue(c, assignment, size) for c in clues)
        expected = expected and all(assignment[c] == value for c, value in known)
        if cnf.variable_count == len(cells):
            actual = all(any(bits[abs(lit) - 1] == (lit > 0) for lit in clause) for clause in cnf.clauses)
        else:
            assumptions = tuple(i + 1 if value else -(i + 1) for i, value in enumerate(bits))
            actual = DPLLSolver().solve(cnf, assumptions).satisfiable
        test.assertEqual(actual, expected, (clues, bits, cnf))
    test.assertEqual(repr(state), before)
    return cnf


class EncoderTests(unittest.TestCase):

    def test_six_core_templates_against_independent_semantics(self):
        clues = (
            Clue("F", "FACT", ("A1",), False),
            Clue("S", "SAME", ("A1", "B2")),
            Clue("D", "DIFFERENT", ("B1", "A2")),
            Clue("E", "EXACTLY", region=Region("ROW", index=1), k=1),
            Clue("L", "AT_LEAST", region=Region("COLUMN", index=1), k=1),
            Clue("M", "AT_MOST", region=Region("NEIGHBORS", anchor="A1"), k=1),
        )
        for clue in clues:
            with self.subTest(kind=clue.kind):
                check_equivalent(self, (clue,))


    def test_cardinality_boundaries_and_empty_region(self):
        regions = (Region("ROW", index=1), Region("COLUMN", index=2),
                   Region("NEIGHBORS", anchor="A1"),
                   Region("EXPLICIT", cells=("B2", "A1")), Region("EXPLICIT"))
        for region in regions:
            for kind in ("EXACTLY", "AT_LEAST", "AT_MOST"):
                for k in range(len(resolve_region(region, 2)) + 1):
                    with self.subTest(region=region, kind=kind, k=k):
                        check_equivalent(self, (Clue("C", kind, region=region, k=k),))


    def test_auxiliary_projection(self):
        check_equivalent(self, (
            Clue("S", "SAME", ("A1", "B2")),
            Clue("D", "DIFFERENT", ("B1", "A2")),
            Clue("E", "EXACTLY", region=Region("ROW", index=1), k=1),
        ), (("A1", True),))


    def test_hidden_clues_are_excluded(self):
        path = Path(__file__).resolve().parents[1] / "puzzles/examples/example_3x3.json"
        puzzle = load_puzzle(path)
        first = GameEngine(puzzle).public_state()
        secret = list(puzzle.clues)
        secret[-1] = (secret[-1][0], Clue("SECRET", "FACT", ("B2",), False))
        second = GameEngine(replace(puzzle, clues=tuple(secret))).public_state()
        self.assertEqual(first, second)
        self.assertEqual(CNFEncoder().encode(first), CNFEncoder().encode(second))

    def test_invalid_clues_and_snapshots(self):
        bad = (
            Clue("C", "FACT", ("Z1",)), Clue("C", "SAME", ("A1", "A1")),
            Clue("C", "EXACTLY", region=Region("ROW", index=True), k=1),
            Clue("C", "EXACTLY", region=Region("ROW", index=1), k=True),
            Clue("C", "AT_MOST", region=Region("EXPLICIT", cells=("A1", "A1")), k=1),
            Clue("C", "UNKNOWN_KIND"), Clue("", "FACT", ("A1",)),
        )
        encoder = CNFEncoder()
        for clue in bad:
            with self.subTest(clue=clue), self.assertRaises(ValueError):
                encoder.encode(make_state((clue,)))
        state = make_state((Clue("C", "FACT", ("A1",)),))
        malformed = (
            replace(state, characters=()),
            replace(state, proved_statuses=(("A1", True), ("A1", False))),
            replace(state, revealed_clues=state.revealed_clues * 2),
            replace(state, proved_statuses=(("A1", 1),)),
        )
        for value in malformed:
            with self.assertRaises(ValueError):
                encoder.encode(value)
