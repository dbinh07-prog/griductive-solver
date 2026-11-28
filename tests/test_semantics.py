"""Unit tests for core.regions and validation.semantics."""

import ast
import itertools
from pathlib import Path
import unittest

from contracts.models import Clue, Region
from core.regions import all_cells, referenced_cells, resolve_region
from validation.semantics import evaluate_clue


class SemanticsTests(unittest.TestCase):
    def test_all_cells_row_major_and_validation(self):
        self.assertEqual(all_cells(1), ("A1",))
        self.assertEqual(all_cells(2), ("A1", "B1", "A2", "B2"))
        self.assertEqual(
            all_cells(3),
            ("A1", "B1", "C1", "A2", "B2", "C2", "A3", "B3", "C3"),
        )
        cells_10 = all_cells(10)
        self.assertEqual(len(cells_10), 100)
        self.assertEqual(cells_10[0], "A1")
        self.assertEqual(cells_10[9], "J1")
        self.assertEqual(cells_10[10], "A2")
        self.assertEqual(cells_10[-1], "J10")

        for bad_size in (0, -1, 27, True, False, "3", None):
            with self.subTest(bad_size=bad_size):
                with self.assertRaises(ValueError):
                    all_cells(bad_size)  # type: ignore[arg-type]

    def test_four_regions_and_diagonal_neighbors(self):
        # ROW and COLUMN (1-based)
        self.assertEqual(resolve_region(Region("ROW", index=1), 3), ("A1", "B1", "C1"))
        self.assertEqual(resolve_region(Region("ROW", index=2), 3), ("A2", "B2", "C2"))
        self.assertEqual(resolve_region(Region("COLUMN", index=1), 3), ("A1", "A2", "A3"))
        self.assertEqual(resolve_region(Region("COLUMN", index=3), 3), ("C1", "C2", "C3"))

        # NEIGHBORS: corner=3, edge=5, interior=8 on 3x3; anchor excluded; row-major
        self.assertEqual(
            resolve_region(Region("NEIGHBORS", anchor="A1"), 3),
            ("B1", "A2", "B2"),
        )
        self.assertEqual(
            resolve_region(Region("NEIGHBORS", anchor="B1"), 3),
            ("A1", "C1", "A2", "B2", "C2"),
        )
        self.assertEqual(
            resolve_region(Region("NEIGHBORS", anchor="B2"), 3),
            ("A1", "B1", "C1", "A2", "C2", "A3", "B3", "C3"),
        )
        self.assertNotIn("B2", resolve_region(Region("NEIGHBORS", anchor="B2"), 3))
        self.assertEqual(resolve_region(Region("NEIGHBORS", anchor="A1"), 1), ())

        # EXPLICIT: sorted row-major; empty allowed
        self.assertEqual(
            resolve_region(Region("EXPLICIT", cells=("C2", "A1", "B1")), 3),
            ("A1", "B1", "C2"),
        )
        self.assertEqual(resolve_region(Region("EXPLICIT", cells=()), 3), ())

        # Multi-digit row ordering (A2 before A10)
        self.assertEqual(
            resolve_region(Region("EXPLICIT", cells=("A10", "A2", "B1")), 10),
            ("B1", "A2", "A10"),
        )

    def test_region_validation_errors(self):
        bad_regions = [
            Region("ROW", index=0),
            Region("ROW", index=4),
            Region("ROW", index=True),
            Region("ROW", index=1, anchor="A1"),
            Region("ROW", index=1, cells=("A1",)),
            Region("COLUMN", index=0),
            Region("COLUMN", index=4),
            Region("COLUMN", index=False),
            Region("COLUMN", index=1, anchor="A1"),
            Region("NEIGHBORS", anchor=""),
            Region("NEIGHBORS", anchor="a1"),
            Region("NEIGHBORS", anchor="A01"),
            Region("NEIGHBORS", anchor="A+1"),
            Region("NEIGHBORS", anchor="A 1"),
            Region("NEIGHBORS", anchor="D1"),
            Region("NEIGHBORS", anchor="A4"),
            Region("NEIGHBORS", anchor="A1", index=1),
            Region("NEIGHBORS", anchor="A1", cells=("B1",)),
            Region("EXPLICIT", cells=("A1", "A1")),
            Region("EXPLICIT", cells=("D1",)),
            Region("EXPLICIT", cells=("A1",), index=1),
            Region("EXPLICIT", cells=("A1",), anchor="A1"),
            Region("EXPLICIT", cells=["A1"]),  # type: ignore[arg-type]
            Region("DIAGONAL", index=1),
        ]
        for region in bad_regions:
            with self.subTest(region=region):
                with self.assertRaises(ValueError):
                    resolve_region(region, 3)

        with self.assertRaises(ValueError):
            resolve_region("ROW", 3)  # type: ignore[arg-type]

    def test_referenced_cells_and_clue_validation(self):
        self.assertEqual(
            referenced_cells(Clue("c1", "FACT", cells=("B2",), status=False), 3),
            ("B2",),
        )
        self.assertEqual(
            referenced_cells(Clue("c2", "SAME", cells=("C1", "A2")), 3),
            ("C1", "A2"),
        )
        self.assertEqual(
            referenced_cells(Clue("c3", "DIFFERENT", cells=("A2", "C1")), 3),
            ("C1", "A2"),
        )
        self.assertEqual(
            referenced_cells(Clue("c4", "EXACTLY", region=Region("ROW", index=2), k=2), 3),
            ("A2", "B2", "C2"),
        )
        self.assertEqual(
            referenced_cells(Clue("c5", "AT_LEAST", region=Region("EXPLICIT", cells=()), k=0), 3),
            (),
        )

        bad_clues = [
            Clue("b1", "FACT", cells=()),
            Clue("b2", "FACT", cells=("A1", "B1")),
            Clue("b3", "FACT", cells=("D1",)),
            Clue("b4", "FACT", cells=("A1",), k=1),
            Clue("b5", "FACT", cells=("A1",), region=Region("ROW", index=1)),
            Clue("b6", "SAME", cells=("A1",)),
            Clue("b7", "SAME", cells=("A1", "A1")),
            Clue("b8", "DIFFERENT", cells=("A1", "B1"), status=False),
            Clue("b9", "DIFFERENT", cells=("A1", "B1"), k=1),
            Clue("b10", "EXACTLY", region=None, k=0),
            Clue("b11", "EXACTLY", region=Region("ROW", index=1), k=-1),
            Clue("b12", "EXACTLY", region=Region("ROW", index=1), k=4),
            Clue("b13", "AT_LEAST", region=Region("ROW", index=1), k=True),
            Clue("b14", "AT_MOST", region=Region("ROW", index=1), cells=("A1",), k=1),
            Clue("b15", "PARITY", region=Region("ROW", index=1), k=2),
            Clue("b16", "COUNT_COMPARE", region=Region("ROW", index=1), k=0),
        ]
        for clue in bad_clues:
            with self.subTest(clue=clue):
                with self.assertRaises(ValueError):
                    referenced_cells(clue, 3)

    def test_six_core_truth_tables(self):
        cells = all_cells(2)  # ("A1", "B1", "A2", "B2")
        row1 = Region("ROW", index=1)  # ("A1", "B1")
        neighbors_a1 = Region("NEIGHBORS", anchor="A1")  # ("B1", "A2", "B2")

        fact_true = Clue("f1", "FACT", cells=("A1",), status=True)
        fact_false = Clue("f2", "FACT", cells=("B2",), status=False)
        same = Clue("s1", "SAME", cells=("A1", "B1"))
        diff = Clue("d1", "DIFFERENT", cells=("A1", "A2"))
        exactly_1 = Clue("e1", "EXACTLY", region=row1, k=1)
        at_least_2 = Clue("al2", "AT_LEAST", region=neighbors_a1, k=2)
        at_most_1 = Clue("am1", "AT_MOST", region=neighbors_a1, k=1)

        for bits in itertools.product((False, True), repeat=4):
            assignment = dict(zip(cells, bits))
            with self.subTest(assignment=assignment):
                self.assertEqual(evaluate_clue(fact_true, assignment, 2), assignment["A1"])
                self.assertEqual(evaluate_clue(fact_false, assignment, 2), not assignment["B2"])
                self.assertEqual(
                    evaluate_clue(same, assignment, 2),
                    assignment["A1"] == assignment["B1"],
                )
                self.assertEqual(
                    evaluate_clue(diff, assignment, 2),
                    assignment["A1"] != assignment["A2"],
                )
                row1_count = int(assignment["A1"]) + int(assignment["B1"])
                self.assertEqual(evaluate_clue(exactly_1, assignment, 2), row1_count == 1)

                nbr_count = (
                    int(assignment["B1"]) + int(assignment["A2"]) + int(assignment["B2"])
                )
                self.assertEqual(evaluate_clue(at_least_2, assignment, 2), nbr_count >= 2)
                self.assertEqual(evaluate_clue(at_most_1, assignment, 2), nbr_count <= 1)

    def test_empty_region_k_zero_and_assignment_validation(self):
        assignment = {"A1": True, "B1": False, "A2": False, "B2": True}
        empty_region = Region("EXPLICIT", cells=())
        for kind in ("EXACTLY", "AT_LEAST", "AT_MOST"):
            with self.subTest(kind=kind):
                clue = Clue(f"empty_{kind}", kind, region=empty_region, k=0)
                self.assertTrue(evaluate_clue(clue, assignment, 2))

        valid_clue = Clue("c", "FACT", cells=("A1",), status=True)
        bad_assignments = [
            {"A1": True, "B1": False, "A2": False},  # missing B2
            {"A1": True, "B1": False, "A2": False, "B2": True, "C1": False},  # extra C1
            {"A1": 1, "B1": False, "A2": False, "B2": True},  # non-bool int
            {"A1": "True", "B1": False, "A2": False, "B2": True},  # non-bool str
            [("A1", True), ("B1", False), ("A2", False), ("B2", True)],  # not Mapping
        ]
        for bad in bad_assignments:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    evaluate_clue(valid_clue, bad, 2)  # type: ignore[arg-type]

    def test_semantics_has_no_forbidden_imports(self):
        semantics_path = Path(__file__).resolve().parent.parent / "validation" / "semantics.py"
        tree = ast.parse(semantics_path.read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)

        forbidden_prefixes = ("logic", "algorithms", "ui", "scenes", "game")
        for mod in imported:
            self.assertFalse(
                mod.startswith(forbidden_prefixes),
                f"Forbidden import in validation/semantics.py: {mod}",
            )


if __name__ == "__main__":
    unittest.main()
