"""Member 1 with 2/3: test placeholders only. Write tests, then remove skip."""
import unittest


@unittest.skip("Scaffold only: implement these tests before removing skip")
class IntegrationTests(unittest.TestCase):

    def test_public_only_end_to_end_pipeline(self):
        raise NotImplementedError


    def test_hint_does_not_reveal(self):
        raise NotImplementedError


    def test_unknown_and_inconsistent_stop_auto(self):
        raise NotImplementedError


    def test_trace_contains_actual_queries(self):
        raise NotImplementedError


    def test_metrics_count_initial_analysis_once(self):
        raise NotImplementedError


    def test_old_worker_result_is_discarded(self):
        raise NotImplementedError
