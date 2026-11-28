from time import perf_counter, sleep
import unittest
from unittest.mock import Mock, patch

from contracts.models import SolverTimeout
from game.worker import AnalysisJob
from tests.member1_data import (
    ErrorAgent, ExitAgent, LargeResultAgent, SampleAgent, SampleEngine,
    SlowAgent, WrongStateAgent,
)


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.state = SampleEngine().public_state()

    def make_job(self, agent, budget=5):
        job = AnalysisJob(self.state, agent, budget)
        self.addCleanup(job.cancel)
        job.start()
        return job

    def wait_result(self, job):
        deadline = perf_counter() + 8
        while perf_counter() < deadline:
            result = job.poll()
            if result is not None:
                return result
            sleep(0.01)
        self.fail("Worker khong dung trong thoi gian cho")

    def test_result(self):
        job = self.make_job(SampleAgent())
        result = self.wait_result(job)
        self.assertEqual(result.puzzle_id, self.state.puzzle_id)
        self.assertEqual(result.revision, self.state.revision)
        self.assertIs(job.poll(), result)

    def test_pending_and_cancel(self):
        job = self.make_job(SlowAgent(2))
        self.assertIsNone(job.poll())
        job.cancel()
        job.cancel()
        self.assertIsNone(job.poll())

    def test_timeout(self):
        job = self.make_job(SlowAgent(2), budget=0.1)
        with self.assertRaises(SolverTimeout):
            self.wait_result(job)

    def test_error_is_not_unsat(self):
        job = self.make_job(ErrorAgent())
        with self.assertRaisesRegex(ValueError, "Loi agent"):
            self.wait_result(job)

    def test_wrong_state(self):
        job = self.make_job(WrongStateAgent())
        with self.assertRaisesRegex(ValueError, "public state"):
            self.wait_result(job)

    def test_worker_exit(self):
        job = self.make_job(ExitAgent())
        with self.assertRaises(RuntimeError):
            self.wait_result(job)

    def test_large_result_does_not_block_on_join(self):
        job = self.make_job(LargeResultAgent())
        self.assertEqual(len(self.wait_result(job).queries), 4000)

    def test_start_once(self):
        job = self.make_job(SampleAgent())
        with self.assertRaises(RuntimeError):
            job.start()

    def test_cancel_before_start(self):
        job = AnalysisJob(self.state, SampleAgent())
        job.cancel()
        self.assertIsNone(job.poll())
        with self.assertRaises(RuntimeError):
            job.start()

    def test_poll_before_start(self):
        job = AnalysisJob(self.state, SampleAgent())
        with self.assertRaises(RuntimeError):
            job.poll()
        job.cancel()

    def test_bad_inputs(self):
        with self.assertRaises(ValueError):
            AnalysisJob(object(), SampleAgent())
        with self.assertRaises(ValueError):
            AnalysisJob(self.state, object())
        with self.assertRaises(ValueError):
            AnalysisJob(self.state, SampleAgent(), True)
        with self.assertRaises(SolverTimeout):
            AnalysisJob(self.state, SampleAgent(), 0)

    def test_late_poll_accepts_result_completed_before_deadline(self):
        job = self.make_job(SampleAgent())
        job._process.join(timeout=3)
        self.assertFalse(job._process.is_alive())
        with patch("game.worker.perf_counter", return_value=job._deadline + 1):
            result = job.poll()
        self.assertEqual(result.puzzle_id, self.state.puzzle_id)

    def test_start_failure_closes_handles(self):
        with patch("game.worker.get_context") as get_context:
            context = get_context.return_value
            receiver = Mock()
            sender = Mock()
            context.Pipe.return_value = (receiver, sender)
            process = context.Process.return_value
            process.start.side_effect = RuntimeError("Cannot start worker")
            process.pid = None
            process.is_alive.return_value = False
            job = AnalysisJob(self.state, SampleAgent())
            with self.assertRaisesRegex(RuntimeError, "Cannot start"):
                job.start()
            receiver.close.assert_called_once()
            sender.close.assert_called_once()
            with self.assertRaises(RuntimeError):
                job.poll()
            job.cancel()
