import itertools
import random
import unittest
from concurrent.futures import ThreadPoolExecutor

from algorithms.dpll import DPLLSolver
from contracts.models import CNF
from tests.test_dpll import brute_force, make_cnf, satisfies


class DPLLEdgeTests(unittest.TestCase):
    def test_nontrivial_random_cnf_against_truth_table(self):
        rng = random.Random(20261128)
        solver = DPLLSolver()
        for case in range(2000):
            count = rng.randint(3, 8)
            clauses = []
            for i in range(rng.randint(1, 35)):
                variables = rng.sample(range(1, count + 1), rng.randint(2, 3))
                clauses.append(tuple(v * rng.choice((-1, 1)) for v in variables))
            assumptions = tuple(v * rng.choice((-1, 1)) for v in rng.sample(range(1, count + 1), rng.randint(0, 2)))
            cnf = make_cnf(clauses, count)
            result = solver.solve(cnf, assumptions)
            with self.subTest(case=case):
                self.assertEqual(result.satisfiable, brute_force(cnf, assumptions))
                if result.satisfiable:
                    self.assertTrue(satisfies(cnf.clauses, dict(result.assignment), assumptions))
                    self.assertEqual(len(result.assignment), count)

    def test_reordering_and_redundant_clauses_preserve_result(self):
        rng = random.Random(137)
        solver = DPLLSolver()
        for case in range(150):
            clauses = []
            for i in range(12):
                variables = rng.sample(range(1, 6), 3)
                clauses.append(tuple(v * rng.choice((-1, 1)) for v in variables))
            cnf = make_cnf(clauses, 5)
            changed = [tuple(reversed(c)) for c in reversed(clauses)]
            changed.extend((clauses[0], (1, -1), (5, -5)))
            first = solver.solve(cnf)
            second = solver.solve(make_cnf(changed, 5))
            with self.subTest(case=case):
                self.assertEqual(first.satisfiable, second.satisfiable)
                self.assertEqual(first.assignment, second.assignment)

    def test_pigeonhole(self):
        for pigeons, holes, expected in ((3, 3, True), (4, 3, False), (5, 4, False)):
            clauses = []
            for pigeon in range(pigeons):
                clauses.append(tuple(pigeon * holes + h + 1 for h in range(holes)))
            for a, b in itertools.combinations(range(pigeons), 2):
                for hole in range(holes):
                    clauses.append((-(a * holes + hole + 1), -(b * holes + hole + 1)))
            cnf = make_cnf(clauses, pigeons * holes)
            result = DPLLSolver().solve(cnf)
            self.assertEqual(result.satisfiable, expected)
            if not expected:
                self.assertGreater(result.stats.backtracks, 1)

    def test_auxiliary_variables_are_complete_and_not_assumptions_next_call(self):
        cnf = CNF(((1, 4), (-4, 2), (5,)), (("A1", 1), ("B1", 2)), 6)
        solver = DPLLSolver()
        first = solver.solve(cnf, (-1,))
        second = solver.solve(cnf, (1,))
        self.assertTrue(first.satisfiable)
        self.assertTrue(second.satisfiable)
        self.assertEqual(len(first.assignment), 6)
        self.assertEqual(len(second.assignment), 6)
        self.assertFalse(dict(first.assignment)[1])
        self.assertTrue(dict(second.assignment)[1])

    def test_one_solver_instance_can_handle_independent_calls(self):
        solver = DPLLSolver()
        cnf = make_cnf(((1, 2), (-2, 3), (-3, 4), (4, 5)), 5)
        assumptions = ((), (1,), (-1,), (2,), (-2,), (1, -1)) * 8
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda value: solver.solve(cnf, value), assumptions))
        for values, result in zip(assumptions, results):
            self.assertEqual(result.satisfiable, brute_force(cnf, values))
            if result.satisfiable:
                self.assertTrue(satisfies(cnf.clauses, dict(result.assignment), values))
