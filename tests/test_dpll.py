"""Member 1: test placeholders only. Write tests, then remove skip."""
import unittest


@unittest.skip("Scaffold only: implement these tests before removing skip")
class DPLLTests(unittest.TestCase):

    def test_empty_formula_and_empty_clause(self):
        raise NotImplementedError


    def test_sat_returns_complete_model(self):
        raise NotImplementedError


    def test_unsat_and_unit_conflict(self):
        raise NotImplementedError


    def test_branching_and_backtracking(self):
        raise NotImplementedError


    def test_assumptions_do_not_mutate_cnf(self):
        raise NotImplementedError


    def test_timeout_is_not_unsat(self):
        raise NotImplementedError
