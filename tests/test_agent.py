import unittest
from unittest.mock import Mock, patch

from algorithms.dpll import DPLLSolver
from contracts.models import Clue, CNF, Region, SATResult, SolverStats, SolverTimeout, Status, Uniqueness
from logic.agent import LogicAgent
from logic.encoder import CNFEncoder
from tests.test_encoder import make_state


class AgentTests(unittest.TestCase):

    def setUp(self):
        self.agent = LogicAgent(CNFEncoder(), DPLLSolver())

    def test_base_kb_inconsistent(self):
        state = make_state((Clue("F", "FACT", ("A1",), False),), (("A1", True),))
        result = self.agent.analyze(state)
        self.assertTrue(result.inconsistent)
        self.assertEqual(result.classifications, ())
        self.assertEqual(len(result.queries), 1)
        self.assertIsNone(self.agent.next_forced(result))
        conflict = make_state((Clue("T", "FACT", ("A1",), True), Clue("F", "FACT", ("A1",), False)))
        self.assertEqual(self.agent.check_uniqueness(conflict), Uniqueness.INCONSISTENT)


    def test_forced_and_unknown_classification(self):
        for kind, expected in (("SAME", Status.CRIMINAL), ("DIFFERENT", Status.INNOCENT)):
            result = self.agent.analyze(make_state((Clue("C", kind, ("A1", "B1")),), (("A1", True),)))
            self.assertEqual(dict(result.classifications)["B1"], expected)
            self.assertEqual(dict(result.classifications)["A2"], Status.UNKNOWN)
            self.assertEqual(len(result.queries), 7)
        # A satisfying model is not a proof of either member of the row.
        result = self.agent.analyze(make_state((Clue("E", "EXACTLY", region=Region("ROW", index=1), k=1),)))
        self.assertTrue(all(status == Status.UNKNOWN for cell, status in result.classifications))


    def test_deterministic_next_move(self):
        state = make_state((Clue("L", "FACT", ("B2",)), Clue("F", "FACT", ("B1",), False)))
        first = self.agent.analyze(state)
        second = self.agent.analyze(state)
        self.assertEqual(first.classifications, second.classifications)
        self.assertEqual(self.agent.next_forced(first), ("B1", Status.INNOCENT))


    def test_uniqueness_blocks_only_primary_variables(self):
        encoder = Mock()
        encoder.encode.return_value = CNF(((1,),), (("A1", 1),), 2)
        solver = Mock()
        solver.solve.side_effect = (
            SATResult(True, ((1, True), (2, False)), SolverStats()),
            SATResult(False, (), SolverStats()),
        )
        self.assertEqual(LogicAgent(encoder, solver).check_uniqueness(make_state(), timeout_s=1), Uniqueness.UNIQUE)
        blocked = solver.solve.call_args_list[1].args[0]
        self.assertEqual(blocked.clauses[-1], (-1,))
        self.assertEqual(blocked.variable_count, 2)
        self.assertEqual(self.agent.check_uniqueness(make_state((Clue("F", "FACT", ("A1",)),))), Uniqueness.MULTIPLE)
        pinned = tuple(Clue(f"F{i}", "FACT", (cell,), bool(i % 2)) for i, cell in enumerate(("A1", "B1", "A2", "B2")))
        self.assertEqual(self.agent.check_uniqueness(make_state(pinned)), Uniqueness.UNIQUE)
        with self.assertRaises(ValueError):
            self.agent.check_uniqueness(make_state(known=(("A1", True),)))


    def test_deadline_covers_entire_analysis(self):
        solver = Mock()
        solver.solve.return_value = SATResult(True, ((1, True), (2, False), (3, False), (4, False)), SolverStats())
        agent = LogicAgent(CNFEncoder(), solver)
        with patch("logic.agent.time.monotonic", side_effect=(0, 0.2, 0.4, 0.6, 0.8, 1.2)):
            with self.assertRaises(SolverTimeout):
                agent.analyze(make_state(), timeout_s=1)
        budgets = [call.kwargs["timeout_s"] for call in solver.solve.call_args_list]
        self.assertEqual(len(budgets), 4)
        self.assertEqual(budgets, sorted(budgets, reverse=True))

    def test_invalid_budgets_and_impossible_query_pair(self):
        for value in (True, float("inf"), float("nan"), "1"):
            for method in (self.agent.analyze, self.agent.check_uniqueness):
                with self.assertRaises(ValueError):
                    method(make_state(), timeout_s=value)
        for method in (self.agent.analyze, self.agent.check_uniqueness):
            with self.assertRaises(SolverTimeout):
                method(make_state(), timeout_s=0)
        solver = Mock()
        solver.solve.side_effect = (SATResult(True, (), SolverStats()), SATResult(False, (), SolverStats()), SATResult(False, (), SolverStats()))
        with self.assertRaises(ValueError):
            LogicAgent(CNFEncoder(), solver).analyze(make_state())
