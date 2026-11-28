"""Unit tests for core.regions and validation.semantics."""

import ast
import itertools
from pathlib import Path
import unittest

from contracts.models import Clue, Region
from core.regions import all_cells, referenced_cells, resolve_region
from validation.semantics import evaluate_clue


def _make_count_compare(
    clue_id: str,
    region: Region | None,
    other_region: Region | None,
    relation: str | None,
    *,
    k: int = 0,
) -> Clue:
    return Clue(
        id=clue_id,
        kind="COUNT_COMPARE",
        region=region,
        other_region=other_region,
        relation=relation,
        k=k,
    )


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
        self.assertEqual(
            referenced_cells(Clue("c6", "PARITY", region=Region("ROW", index=1), k=0), 3),
            ("A1", "B1", "C1"),
        )
        self.assertEqual(
            referenced_cells(Clue("c7", "PARITY", region=Region("EXPLICIT", cells=()), k=1), 3),
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
            Clue("b16", "PARITY", region=Region("ROW", index=1), k=True),
            Clue("b17", "COUNT_COMPARE", region=Region("ROW", index=1), k=0),
            Clue("b18", "UNKNOWN_EXTENSION", region=Region("ROW", index=1), k=0),
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

    def test_parity_truth_table_and_empty_region(self):
        cells = all_cells(2)  # ("A1", "B1", "A2", "B2")
        row1 = Region("ROW", index=1)  # ("A1", "B1")
        neighbors_a1 = Region("NEIGHBORS", anchor="A1")  # ("B1", "A2", "B2")
        single_a1 = Region("EXPLICIT", cells=("A1",))
        empty = Region("EXPLICIT", cells=())

        row1_even = Clue("p1", "PARITY", region=row1, k=0)
        row1_odd = Clue("p2", "PARITY", region=row1, k=1)
        nbr_even = Clue("p3", "PARITY", region=neighbors_a1, k=0)
        nbr_odd = Clue("p4", "PARITY", region=neighbors_a1, k=1)
        single_even = Clue("p5", "PARITY", region=single_a1, k=0)
        single_odd = Clue("p6", "PARITY", region=single_a1, k=1)
        empty_even = Clue("p7", "PARITY", region=empty, k=0)
        empty_odd = Clue("p8", "PARITY", region=empty, k=1)

        for bits in itertools.product((False, True), repeat=4):
            assignment = dict(zip(cells, bits))
            with self.subTest(assignment=assignment):
                row1_count = int(assignment["A1"]) + int(assignment["B1"])
                nbr_count = (
                    int(assignment["B1"]) + int(assignment["A2"]) + int(assignment["B2"])
                )
                self.assertEqual(evaluate_clue(row1_even, assignment, 2), row1_count % 2 == 0)
                self.assertEqual(evaluate_clue(row1_odd, assignment, 2), row1_count % 2 == 1)
                self.assertEqual(evaluate_clue(nbr_even, assignment, 2), nbr_count % 2 == 0)
                self.assertEqual(evaluate_clue(nbr_odd, assignment, 2), nbr_count % 2 == 1)
                # Single cell: even forces Innocent, odd forces Criminal
                self.assertEqual(evaluate_clue(single_even, assignment, 2), not assignment["A1"])
                self.assertEqual(evaluate_clue(single_odd, assignment, 2), assignment["A1"])
                # Empty region: count is 0 -> even True, odd False
                self.assertTrue(evaluate_clue(empty_even, assignment, 2))
                self.assertFalse(evaluate_clue(empty_odd, assignment, 2))

    def test_count_compare_truth_table_and_validation(self):
        cells = all_cells(2)  # ("A1", "B1", "A2", "B2")
        row1 = Region("ROW", index=1)  # ("A1", "B1")
        col1 = Region("COLUMN", index=1)  # ("A1", "A2") -- overlaps at A1
        row2 = Region("ROW", index=2)  # ("A2", "B2") -- disjoint from row1
        only_a1 = Region("EXPLICIT", cells=("A1",))  # subset of row1
        empty = Region("EXPLICIT", cells=())

        # referenced_cells deduplicates overlap and sorts row-major
        self.assertEqual(
            referenced_cells(_make_count_compare("cc_ref", col1, row1, "EQ"), 2),
            ("A1", "B1", "A2"),
        )
        self.assertEqual(
            referenced_cells(_make_count_compare("cc_empty", empty, empty, "EQ"), 2),
            (),
        )

        # Exhaustive truth-table checks on 2x2
        for left, right in (
            (row1, col1),
            (row1, row2),
            (row1, only_a1),
            (row1, row1),
            (empty, empty),
        ):
            left_cells = resolve_region(left, 2)
            right_cells = resolve_region(right, 2)
            clue_eq = _make_count_compare("cc_eq", left, right, "EQ")
            clue_lt = _make_count_compare("cc_lt", left, right, "LT")
            clue_gt = _make_count_compare("cc_gt", left, right, "GT")
            clue_gt_swapped = _make_count_compare("cc_swap", right, left, "GT")

            for bits in itertools.product((False, True), repeat=4):
                assignment = dict(zip(cells, bits))
                lc = sum(int(assignment[c]) for c in left_cells)
                rc = sum(int(assignment[c]) for c in right_cells)
                with self.subTest(left=left, right=right, assignment=assignment):
                    self.assertEqual(evaluate_clue(clue_eq, assignment, 2), lc == rc)
                    self.assertEqual(evaluate_clue(clue_lt, assignment, 2), lc < rc)
                    self.assertEqual(evaluate_clue(clue_gt, assignment, 2), lc > rc)
                    # Symmetry: LT(L, R) == GT(R, L)
                    self.assertEqual(
                        evaluate_clue(clue_lt, assignment, 2),
                        evaluate_clue(clue_gt_swapped, assignment, 2),
                    )

        # Invalid COUNT_COMPARE inputs raise ValueError
        assignment = {"A1": True, "B1": False, "A2": False, "B2": True}
        bad_cc_clues = [
            _make_count_compare("bad1", row1, col1, "LE"),
            _make_count_compare("bad2", row1, col1, None),
            _make_count_compare("bad3", row1, None, "EQ"),
            _make_count_compare("bad4", None, col1, "EQ"),
            _make_count_compare("bad5", row1, col1, "EQ", k=1),
            _make_count_compare("bad6", row1, col1, "EQ", k=True),
        ]
        for bad_clue in bad_cc_clues:
            with self.subTest(bad_clue=bad_clue):
                with self.assertRaises(ValueError):
                    evaluate_clue(bad_clue, assignment, 2)

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
