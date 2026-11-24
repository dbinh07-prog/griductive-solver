"""Member 2: test placeholders only. Write tests, then remove skip."""
import unittest


@unittest.skip("Scaffold only: implement these tests before removing skip")
class AgentTests(unittest.TestCase):

    def test_base_kb_inconsistent(self):
        raise NotImplementedError


    def test_forced_and_unknown_classification(self):
        raise NotImplementedError


    def test_deterministic_next_move(self):
        raise NotImplementedError


    def test_uniqueness_blocks_only_primary_variables(self):
        raise NotImplementedError


    def test_deadline_covers_entire_analysis(self):
        raise NotImplementedError
