"""Member 3: test placeholders only. Write tests, then remove skip."""
import unittest


@unittest.skip("Scaffold only: implement these tests before removing skip")
class EngineTests(unittest.TestCase):

    def test_initial_cards_publish_status_and_clue(self):
        raise NotImplementedError


    def test_reject_leaves_state_unchanged(self):
        raise NotImplementedError


    def test_accepted_reveal_adds_status_and_clue(self):
        raise NotImplementedError


    def test_snapshot_is_immutable_and_public_only(self):
        raise NotImplementedError


    def test_stale_analysis_and_restart(self):
        raise NotImplementedError
