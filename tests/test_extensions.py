from itertools import product
from pathlib import Path
import unittest

from contracts.models import Clue, Region, Relation, Uniqueness, VerdictResult
from core.puzzle_loader import load_puzzle
from core.regions import all_cells, referenced_cells
from game.factory import create_session
from logic.encoder import CNFEncoder
from tests.test_encoder import check_equivalent
from ui.clue_text import describe_clue
from validation.puzzles import validate_puzzle


class ExtensionTests(unittest.TestCase):

    def test_selected_extension_one_matches_independent_semantics(self):
        regions = (Region("ROW", index=1), Region("COLUMN", index=2), Region("NEIGHBORS", anchor="A1"),
                   Region("EXPLICIT", cells=("A1", "B2")), Region("EXPLICIT"))
        for region in regions:
            for parity in (0, 1):
                with self.subTest(region=region, parity=parity):
                    check_equivalent(self, (Clue("P", "PARITY", region=region, k=parity),))


    def test_selected_extension_two_matches_independent_semantics(self):
        cells = all_cells(2)
        regions = [Region("EXPLICIT", cells=tuple(c for c, bit in zip(cells, bits) if bit))
                   for bits in product((False, True), repeat=4)]
        # Covers disjoint, overlapping, equal, empty and differently sized regions.
        for left in regions:
            for right in regions:
                for relation in Relation:
                    with self.subTest(left=left, right=right, relation=relation):
                        check_equivalent(self, (Clue("C", "COUNT_COMPARE", region=left,
                                                    other_region=right, relation=relation),))


    def test_selected_extensions_public_entailment_and_visualization(self):
        path = Path(__file__).resolve().parents[1] / "puzzles/examples/example_extensions_3x3.json"
        puzzle = load_puzzle(path)
        session = create_session(str(path))
        check = validate_puzzle(puzzle, session.agent)
        self.assertTrue(check.all_clues_true)
        self.assertEqual(check.complete_clues_uniqueness, Uniqueness.UNIQUE)
        self.assertTrue(check.progressively_solvable)
        comparison = dict(puzzle.clues)["A1"]
        self.assertEqual(referenced_cells(comparison, 3), ("A1", "B1", "C1"))
        self.assertIn("equals", describe_clue(comparison, 3))
        self.assertIn("odd", describe_clue(dict(puzzle.clues)["C2"], 3))
        while not session.engine.is_solved():
            self.assertEqual(session.step().result, VerdictResult.ACCEPTED)
        self.assertEqual(len(session.trace), 8)

    def test_invalid_extension_fields(self):
        left = Region("ROW", index=1)
        bad = (Clue("P", "PARITY", region=left, k=True), Clue("P", "PARITY", region=left, k=2),
               Clue("C", "COUNT_COMPARE", region=left, relation=Relation.EQ),
               Clue("C", "COUNT_COMPARE", region=left, other_region=left, relation="BAD"),
               Clue("C", "COUNT_COMPARE", region=left, other_region=left, relation=True))
        for clue in bad:
            with self.subTest(clue=clue), self.assertRaises(ValueError):
                CNFEncoder().validate_clue(clue, 2)
