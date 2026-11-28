import csv
import json
from dataclasses import asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter, sleep
import unittest
from unittest.mock import patch

from contracts.models import Clue, SolverTimeout, Status, VerdictResult
from game.session import GameSession
from tests.member1_data import SampleAgent, SampleEngine, SlowAgent, WrongStateAgent


class IntegrationTests(unittest.TestCase):

    def setUp(self):
        self.engine = SampleEngine()
        self.agent = SampleAgent()
        self.session = GameSession(self.engine, self.agent)
        self.addCleanup(self.session.cancel_analysis)

    def wait_analysis(self, session):
        deadline = perf_counter() + 8
        while perf_counter() < deadline:
            result = session.poll_analysis()
            if result is not None:
                return result
            sleep(0.01)
        self.fail("Worker khong tra ket qua")

    def test_public_only_end_to_end_pipeline(self):
        while not self.engine.is_solved():
            result = self.session.step()
            self.assertEqual(result.result, VerdictResult.ACCEPTED)
        self.assertEqual([e.cell for e in self.session.trace], ["B1", "A2", "B2"])
        self.assertEqual(self.session.metrics().sat_calls, 15)
        self.assertEqual(self.session.metrics().deduction_steps, 3)
        self.assertIsNone(self.session.step())
        for state in self.agent.seen_states:
            self.assertNotIn("solution", asdict(state))
            self.assertEqual(set(dict(state.proved_statuses)), set(dict(state.revealed_clues)))


    def test_hint_does_not_reveal(self):
        before = self.session.public_state()
        self.assertEqual(self.session.hint(), ("B1", Status.INNOCENT))
        self.assertEqual(self.session.public_state(), before)
        self.assertEqual(self.engine.submit_calls, 0)
        self.assertEqual(self.session.trace, [])


    def test_unknown_and_inconsistent_stop_auto(self):
        for mode in ("unknown", "inconsistent"):
            engine = SampleEngine(mode)
            session = GameSession(engine, SampleAgent())
            self.addCleanup(session.cancel_analysis)
            before = engine.public_state()
            self.assertIsNone(session.hint())
            self.assertIsNone(session.step())
            result = session.submit("B1", Status.INNOCENT)
            expected = VerdictResult.INCONSISTENT if mode == "inconsistent" else VerdictResult.NOT_PROVABLE
            self.assertEqual(result.result, expected)
            self.assertEqual(engine.public_state(), before)
            self.assertEqual(engine.submit_calls, 0)


    def test_trace_contains_actual_queries(self):
        analysis = self.session.analyze()
        self.session.submit("B1", Status.INNOCENT)
        entry = self.session.trace[0]
        self.assertEqual(entry.active_clue_ids, ("C01",))
        self.assertEqual(entry.sat_queries, analysis.queries)
        self.assertEqual(entry.revealed_clue_id, "C02")
        self.assertEqual(entry.sat_queries[0].assumptions, ())
        self.assertFalse(next(q for q in entry.sat_queries if q.assumptions == (2,)).satisfiable)


    def test_metrics_count_initial_analysis_once(self):
        first = self.session.analyze()
        for i in range(4):
            self.assertIs(self.session.analyze(), first)
            self.session.hint()
            self.session.metrics()
        self.assertEqual(self.agent.analyze_calls, 1)
        metrics = self.session.metrics()
        self.assertEqual(metrics.sat_calls, len(first.queries))
        self.assertEqual(metrics.decisions, sum(q.stats.decisions for q in first.queries))
        self.assertEqual(metrics.propagations, sum(q.stats.propagations for q in first.queries))
        self.assertAlmostEqual(metrics.sat_runtime_ms, sum(q.stats.runtime_ms for q in first.queries))


    def test_old_worker_result_is_discarded(self):
        session = GameSession(self.engine, SlowAgent(1))
        self.addCleanup(session.cancel_analysis)
        job = session.start_analysis(timeout_s=5)
        session.restart()
        self.assertIsNone(job.poll())
        self.assertIsNone(session.poll_analysis())
        self.assertEqual(session.metrics().sat_calls, 0)
        self.assertEqual(session.trace, [])

    def test_wrong_verdict_does_not_reveal(self):
        before = self.session.public_state()
        result = self.session.submit("B1", Status.CRIMINAL)
        self.assertEqual(result.result, VerdictResult.CONTRADICTED)
        self.assertEqual(self.engine.public_state(), before)
        self.assertEqual(self.engine.submit_calls, 0)
        self.assertEqual(self.session.trace, [])

    def test_correct_guess_is_rejected(self):
        before = self.session.public_state()
        result = self.session.submit("A2", Status.CRIMINAL)
        self.assertEqual(result.result, VerdictResult.NOT_PROVABLE)
        self.assertEqual(self.engine.public_state(), before)

    def test_already_revealed_does_not_analyze(self):
        result = self.session.submit("A1", Status.CRIMINAL)
        self.assertEqual(result.result, VerdictResult.ALREADY_REVEALED)
        self.assertEqual(self.agent.analyze_calls, 0)

    def test_bad_submit(self):
        for cell, verdict in (("Z9", Status.CRIMINAL), ("B1", Status.UNKNOWN), ("B1", "INNOCENT")):
            with self.subTest(cell=cell, verdict=verdict), self.assertRaises(ValueError):
                self.session.submit(cell, verdict)
        self.assertEqual(self.agent.analyze_calls, 0)

    def test_pending_metrics_are_unknown(self):
        self.assertIsNone(self.session.metrics().active_clauses)
        self.session.analyze()
        self.assertEqual(self.session.metrics().active_clauses, 2)
        self.session.step()
        self.assertIsNone(self.session.metrics().active_clauses)
        self.assertIsNone(self.session.metrics().auxiliary_variables)
        self.session.analyze()
        self.assertEqual(self.session.metrics().active_clauses, 4)

    def test_restart_resets_metrics_and_trace(self):
        before = self.session.public_state()
        self.session.step()
        state = self.session.restart()
        self.assertGreater(state.revision, before.revision)
        self.assertEqual(state.proved_statuses, before.proved_statuses)
        self.assertEqual(state.revealed_clues, before.revealed_clues)
        self.assertEqual(self.session.metrics().sat_calls, 0)
        self.assertEqual(self.session.trace, [])
        self.assertEqual(self.session.hint(), ("B1", Status.INNOCENT))

    def test_cache_uses_full_public_snapshot(self):
        self.session.analyze()
        self.engine._clues["A1"] = Clue("C01", "FACT", ("B2",), False)
        self.assertEqual(self.session.hint(), ("B2", Status.INNOCENT))
        self.assertEqual(self.agent.analyze_calls, 2)

    def test_hidden_changes_do_not_change_public_analysis(self):
        first = self.session.analyze()
        self.engine._solution["A2"] = False
        self.engine._clues["B2"] = Clue("SECRET_CLUE", "FACT", ("A2",), False)
        self.assertIs(self.session.analyze(), first)
        self.assertEqual(self.agent.analyze_calls, 1)

    def test_bad_analysis_is_not_cached(self):
        session = GameSession(self.engine, WrongStateAgent())
        with self.assertRaises(ValueError):
            session.analyze()
        self.assertEqual(session.metrics().sat_calls, 0)

    def test_missing_classifications(self):
        result = self.agent.analyze(self.engine.public_state())
        with patch.object(self.agent, "analyze", return_value=replace(result, classifications=())):
            with self.assertRaises(ValueError):
                self.session.analyze()
        self.assertEqual(self.session.metrics().sat_calls, 0)

    def test_bad_next_move(self):
        with patch.object(self.agent, "next_forced", return_value=("A2", Status.CRIMINAL)):
            with self.assertRaises(ValueError):
                self.session.hint()
        self.assertEqual(self.engine.submit_calls, 0)

    def test_export_public_trace(self):
        self.session.step()
        with TemporaryDirectory() as directory:
            output = Path(directory)
            self.session.export_trace(str(output / "trace.json"))
            self.session.export_trace(str(output / "trace.csv"))
            text = (output / "trace.json").read_text(encoding="utf-8")
            data = json.loads(text)
            self.assertEqual(data["steps"][0]["verdict"], "INNOCENT")
            self.assertNotIn("solution", text)
            self.assertNotIn("C03", text)
            self.assertNotIn("C04", text)
            with (output / "trace.csv").open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(json.loads(rows[0]["active_clue_ids"]), ["C01"])
            self.assertEqual(len(json.loads(rows[0]["sat_queries"])), 7)
            with self.assertRaises(ValueError):
                self.session.export_trace(str(output / "trace.txt"))

    def test_async_analysis_is_cached(self):
        job = self.session.start_analysis(timeout_s=5)
        self.assertIs(self.session.start_analysis(timeout_s=5), job)
        analysis = self.wait_analysis(self.session)
        self.assertIs(self.session.analyze(), analysis)
        self.assertIs(self.session.poll_analysis(), analysis)
        self.assertIsNone(self.session.start_analysis())
        self.assertEqual(self.session.metrics().sat_calls, 7)
        self.assertEqual(self.agent.analyze_calls, 0)

    def test_external_state_change_discards_job(self):
        self.session.start_analysis(timeout_s=5)
        self.engine.restart()
        self.assertIsNone(self.session.poll_analysis())
        self.assertEqual(self.session.metrics().sat_calls, 0)

    def test_bad_timeout(self):
        for budget in (True, float("inf"), "5"):
            with self.assertRaises(ValueError):
                self.session.analyze(timeout_s=budget)
        with self.assertRaises(SolverTimeout):
            self.session.start_analysis(timeout_s=0)

    def test_slow_synchronous_agent_is_not_cached_after_deadline(self):
        session = GameSession(self.engine, SlowAgent(0.02))
        with self.assertRaises(SolverTimeout):
            session.analyze(timeout_s=0.005)
        self.assertEqual(session.metrics().sat_calls, 0)

    def test_bad_primary_mapping(self):
        result = self.agent.analyze(self.engine.public_state())
        bad_cnf = replace(result.cnf, primary_variables=tuple(reversed(result.cnf.primary_variables)))
        with patch.object(self.agent, "analyze", return_value=replace(result, cnf=bad_cnf)):
            with self.assertRaises(ValueError):
                self.session.analyze()
