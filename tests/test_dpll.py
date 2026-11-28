import itertools
import random
import unittest
from unittest.mock import patch

from algorithms.dpll import DPLLSolver
from contracts.models import CNF, SolverTimeout


def make_cnf(clauses, count):
    primary = tuple((f"P{i}", i) for i in range(1, count + 1))
    return CNF(tuple(tuple(c) for c in clauses), primary, count)


def satisfies(clauses, assignment, assumptions=()):
    for literal in assumptions:
        if assignment[abs(literal)] != (literal > 0):
            return False
    for clause in clauses:
        if not any(assignment[abs(lit)] == (lit > 0) for lit in clause):
            return False
    return True


def brute_force(cnf, assumptions=()):
    for values in itertools.product((False, True), repeat=cnf.variable_count):
        assignment = dict(zip(range(1, cnf.variable_count + 1), values))
        if satisfies(cnf.clauses, assignment, assumptions):
            return True
    return False


class DPLLTests(unittest.TestCase):

    def setUp(self):
        self.solver = DPLLSolver()

    def check_answer(self, cnf, assumptions=()):
        result = self.solver.solve(cnf, assumptions)
        self.assertEqual(result.satisfiable, brute_force(cnf, assumptions))
        self.assertGreaterEqual(result.stats.runtime_ms, 0)
        if result.satisfiable:
            model = dict(result.assignment)
            self.assertEqual(list(model), list(range(1, cnf.variable_count + 1)))
            self.assertTrue(all(type(v) is bool for v in model.values()))
            self.assertTrue(satisfies(cnf.clauses, model, assumptions))
        else:
            self.assertEqual(result.assignment, ())
        return result

    def test_empty_formula_and_empty_clause(self):
        result = self.check_answer(make_cnf((), 0))
        self.assertTrue(result.satisfiable)
        self.assertEqual(result.assignment, ())
        self.assertEqual(result.stats.decisions, 0)
        self.assertFalse(self.check_answer(make_cnf(((),), 2)).satisfiable)


    def test_sat_returns_complete_model(self):
        result = self.check_answer(make_cnf(((2,),), 5))
        self.assertEqual(result.assignment, ((1, False), (2, True), (3, False), (4, False), (5, False)))


    def test_unsat_and_unit_conflict(self):
        self.assertFalse(self.check_answer(make_cnf(((1,), (-1,)), 1)).satisfiable)
        result = self.check_answer(make_cnf(((1,), (-1, 2), (-2, 3), (-3, 4)), 4))
        self.assertEqual(result.stats.propagations, 4)
        self.assertEqual(result.stats.decisions, 0)


    def test_branching_and_backtracking(self):
        result = self.check_answer(make_cnf(((1, 2), (1, -2)), 2))
        self.assertTrue(dict(result.assignment)[1])
        self.assertEqual(result.stats.decisions, 1)
        self.assertEqual(result.stats.backtracks, 1)
        result = self.check_answer(make_cnf(((1, 2), (1, -2), (-1, 2), (-1, -2)), 2))
        self.assertFalse(result.satisfiable)
        self.assertEqual(result.stats.backtracks, 2)


    def test_assumptions_do_not_mutate_cnf(self):
        cnf = make_cnf(((1, 2), (2, -2)), 3)
        before = repr(cnf)
        self.assertTrue(self.check_answer(cnf, (-1,)).satisfiable)
        self.assertFalse(self.check_answer(cnf, (-1, -2)).satisfiable)
        self.assertFalse(self.check_answer(cnf, (1, -1)).satisfiable)
        self.assertEqual(repr(cnf), before)
        self.assertEqual(self.solver.solve(cnf).assignment, self.solver.solve(cnf).assignment)


    def test_timeout_is_not_unsat(self):
        for budget in (0, -1):
            with self.subTest(budget=budget), self.assertRaises(SolverTimeout):
                self.solver.solve(make_cnf(((1,),), 1), timeout_s=budget)
        with patch("algorithms.dpll.perf_counter", side_effect=(0.0, 0.0, 2.0)):
            with self.assertRaises(SolverTimeout):
                self.solver.solve(make_cnf(((1,),), 1), timeout_s=1)

    def test_duplicate_and_tautology(self):
        result = self.check_answer(make_cnf(((1, 1), (2, -2), (-1, 2, 2)), 2))
        self.assertEqual(result.stats.propagations, 2)

    def test_deterministic(self):
        cnf = make_cnf(((2, 1), (-2, 3)), 3)
        first = self.solver.solve(cnf)
        second = self.solver.solve(make_cnf(tuple(reversed(cnf.clauses)), 3))
        self.assertEqual(first.assignment, second.assignment)
        self.assertEqual(first.stats.decisions, second.stats.decisions)
        self.assertEqual(first.stats.propagations, second.stats.propagations)

    def test_auxiliary_variables(self):
        cnf = CNF(((1, 3), (-3, 2), (4,)), (("A1", 1), ("B1", 2)), 4)
        self.check_answer(cnf)

    def test_bad_timeout(self):
        for budget in (True, None, "1", float("nan"), float("inf")):
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                self.solver.solve(make_cnf((), 0), timeout_s=budget)

    def test_bad_literals(self):
        for literal in (0, True, 1.5, "1", 3, -3):
            with self.subTest(literal=literal), self.assertRaises(ValueError):
                self.solver.solve(make_cnf(((literal,),), 2))
        with self.assertRaises(ValueError):
            self.solver.solve(make_cnf((), 2), (True,))

    def test_bad_cnf(self):
        bad = (
            None, CNF((), (), True), CNF((), (), -1), CNF([], (), 0),
            CNF(([1],), (), 1), CNF((), (("A1", 1), ("B1", 1)), 1),
            CNF((), (("A1", -1),), 1), CNF((), (("A1", 1), ("A1", 2)), 2),
        )
        for cnf in bad:
            with self.subTest(cnf=cnf), self.assertRaises(ValueError):
                self.solver.solve(cnf)

    def test_all_small_formulas(self):
        clauses = []
        for signs in itertools.product((-1, 0, 1), repeat=2):
            clauses.append(tuple((i + 1) * sign for i, sign in enumerate(signs) if sign))
        for length in range(5):
            for formula in itertools.combinations(clauses, length):
                self.check_answer(make_cnf(formula, 2))

    def test_random_formulas(self):
        rng = random.Random(27)
        for i in range(400):
            count = rng.randint(1, 5)
            clauses = []
            for j in range(rng.randint(0, 16)):
                clause = []
                for k in range(rng.randint(0, 4)):
                    clause.append(rng.choice((-1, 1)) * rng.randint(1, count))
                clauses.append(tuple(clause))
            assumptions = tuple(rng.choice((-1, 1)) * rng.randint(1, count) for _ in range(rng.randint(0, 2)))
            with self.subTest(case=i):
                self.check_answer(make_cnf(clauses, count), assumptions)
