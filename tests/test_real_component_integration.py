from dataclasses import replace
import csv
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter, sleep
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from app_controller import AppController, TerminalState
from contracts.models import PublicState, Status, Uniqueness, VerdictResult
from core.game_engine import GameEngine
from core.puzzle_loader import load_puzzle
from game.session import GameSession
from game.factory import create_session
from ui import theme
from tests.core_integration_data import CoreTestAgent, ImmediateTestJob
from tests.member1_data import ErrorAgent

ROOT = Path(__file__).resolve().parents[1]


class RealComponentIntegrationTests(unittest.TestCase):
    def setUp(self):
        theme.reset_runtime_caches()
        pygame.init()
        pygame.display.set_mode((1280, 720))

    def tearDown(self):
        theme.reset_runtime_caches()
        pygame.quit()

    def make_session(self, path=None):
        path = path or ROOT / "puzzles/examples/example_3x3.json"
        return GameSession(GameEngine(load_puzzle(path)), CoreTestAgent())

    def wait_controller(self, controller):
        deadline = perf_counter() + 8
        while controller.is_loading and perf_counter() < deadline:
            controller.update(0.01)
            sleep(0.01)
        self.assertFalse(controller.is_loading)

    def solve(self, session):
        while not session.engine.is_solved():
            if len(session.trace) >= len(session.public_state().characters):
                self.fail("Progressive solve did not terminate")
            before = session.public_state()
            result = session.step()
            self.assertIsNotNone(result)
            self.assertEqual(result.result, VerdictResult.ACCEPTED)
            self.assertEqual(session.trace[-1].active_clue_ids,
                             tuple(clue.id for owner, clue in before.revealed_clues))
        return session

    def test_real_engine_with_member1_session_and_dpll(self):
        session = self.solve(self.make_session())
        self.assertEqual(len(session.trace), 8)
        self.assertEqual(session.metrics().sat_calls, 80)
        self.assertIsNone(session.hint())

    def test_all_benchmark_cases_with_real_dpll_and_engine(self):
        paths = sorted((ROOT / "puzzles/benchmark").glob("*.json"))
        self.assertEqual(len(paths), 18)
        for path in paths:
            with self.subTest(case=path.name):
                puzzle = load_puzzle(path)
                agent = CoreTestAgent()
                full = PublicState(puzzle.id, puzzle.title, puzzle.size, puzzle.characters,
                                   revealed_clues=puzzle.clues)
                self.assertEqual(agent.check_uniqueness(full), Uniqueness.UNIQUE)
                session = self.solve(GameSession(GameEngine(puzzle), agent))
                self.assertEqual(dict(session.public_state().proved_statuses), dict(puzzle.solution))

    def test_all_benchmark_cases_with_production_pipeline(self):
        for path in sorted((ROOT / "puzzles/benchmark").glob("*.json")):
            with self.subTest(case=path.name):
                puzzle = load_puzzle(path)
                session = create_session(str(path))
                full = PublicState(puzzle.id, puzzle.title, puzzle.size, puzzle.characters,
                                   revealed_clues=puzzle.clues)
                self.assertEqual(session.agent.check_uniqueness(full), Uniqueness.UNIQUE)
                self.solve(session)
                self.assertEqual(dict(session.public_state().proved_statuses), dict(puzzle.solution))
                self.assertEqual(session.metrics().deduction_steps,
                                 puzzle.size ** 2 - len(puzzle.initially_revealed))

    def test_external_analysis_is_counted_once(self):
        session = self.make_session()
        result = session.agent.analyze(session.public_state())
        self.assertIs(session.accept_analysis(result), result)
        self.assertIs(session.accept_analysis(result), result)
        self.assertEqual(session.metrics().sat_calls, len(result.queries))
        session.hint()
        self.assertEqual(session.agent.analyze_calls, 1)

    def test_wrong_or_old_external_analysis_is_rejected(self):
        session = self.make_session()
        result = session.agent.analyze(session.public_state())
        with self.assertRaises(ValueError):
            session.accept_analysis(replace(result, puzzle_id="wrong"))
        session.restart()
        with self.assertRaises(ValueError):
            session.accept_analysis(result)
        self.assertEqual(session.metrics().sat_calls, 0)

    def test_controller_worker_handoff_does_not_recompute_sat(self):
        session = self.make_session()
        controller = AppController(lambda path: session, worker_factory=ImmediateTestJob)
        self.addCleanup(controller.close)
        controller.load_case("test_case")
        controller.update(0)
        self.assertEqual(session.agent.analyze_calls, 1)
        self.assertEqual(session.metrics().sat_calls, 17)
        controller.hint()
        self.assertEqual(session.agent.analyze_calls, 1)
        controller.submit_verdict("B1", Status.CRIMINAL)
        self.assertEqual(session.agent.analyze_calls, 1)
        self.assertEqual(controller.feedback.kind, "CONTRADICTED")
        controller.submit_verdict("B1", Status.INNOCENT)
        controller.update(0)
        self.assertEqual(session.agent.analyze_calls, 2)
        self.assertEqual(session.metrics().sat_calls, 32)
        controller.render(pygame.display.get_surface())

    def test_controller_renders_real_initial_states_at_all_board_sizes(self):
        for size in (3, 4, 5):
            path = next((ROOT / "puzzles/benchmark").glob(f"bench_{size}x{size}_*.json"))
            controller = AppController(lambda value: self.make_session(value), worker_factory=ImmediateTestJob)
            try:
                controller.load_case(str(path))
                controller.update(0)
                self.assertNotEqual(controller.terminal_state, TerminalState.ERROR)
                controller.render(pygame.display.get_surface())
            finally:
                controller.close()

    def test_selecting_another_cell_clears_previous_verdict_feedback(self):
        controller = AppController(lambda path: self.make_session(), worker_factory=ImmediateTestJob)
        self.addCleanup(controller.close)
        controller.load_case("test_case")
        controller.update(0)
        controller.select_cell("B1")
        controller.submit_verdict("B1", Status.CRIMINAL)
        self.assertEqual(controller.feedback.kind, "CONTRADICTED")
        before = controller.public_state
        controller.select_cell("A2")
        self.assertIsNone(controller.feedback)
        self.assertEqual(controller.public_state, before)

    def test_export_dialog_saves_real_trace_and_public_cnf(self):
        controller = AppController(lambda path: self.make_session(), worker_factory=ImmediateTestJob)
        self.addCleanup(controller.close)
        controller.load_case("test_case")
        controller.update(0)
        controller.next_step()
        controller.update(0)
        scene = controller._scene
        before = controller.public_state
        calls = controller.metrics.sat_calls
        with TemporaryDirectory() as folder:
            for suffix in ("json", "csv", "cnf"):
                path = Path(folder) / f"kiểm tra file.{suffix}"
                controller.toggle_auto()
                self.assertTrue(controller.auto_running)
                with patch("scenes.game_scene.choose_file", return_value=str(path)):
                    if suffix == "cnf":
                        scene._handle_export_cnf()
                    else:
                        scene._handle_export_trace()
                self.assertFalse(controller.auto_running)
                self.assertTrue(path.is_file())
                if suffix == "json":
                    data = json.loads(path.read_text(encoding="utf-8"))
                    self.assertEqual(data["steps"][0]["cell"], "B1")
                    self.assertNotIn("solution", data)
                elif suffix == "csv":
                    with path.open(encoding="utf-8-sig", newline="") as stream:
                        rows = list(csv.DictReader(stream))
                    self.assertEqual(len(rows), 1)
                    self.assertEqual(rows[0]["cell"], "B1")
                else:
                    self.assertIn("p cnf 9 ", path.read_text(encoding="utf-8"))
        self.assertEqual(controller.public_state, before)
        self.assertEqual(controller.metrics.sat_calls, calls)

    def test_cancelled_and_failed_dialogs_do_not_replace_active_case(self):
        from scenes.case_select_scene import CaseSelectScene

        controller = AppController(lambda path: self.make_session(), worker_factory=ImmediateTestJob)
        self.addCleanup(controller.close)
        controller.load_case("test_case")
        controller.update(0)
        scene = controller._scene
        before = controller.public_state
        with patch("scenes.game_scene.choose_file", return_value=""), \
                patch.object(controller, "export_trace") as export:
            scene._handle_export_trace()
            export.assert_not_called()
        self.assertEqual(scene._export_error, "")
        selector = CaseSelectScene(controller)
        with patch("scenes.case_select_scene.choose_file", return_value=""), \
                patch.object(controller, "load_case") as load:
            selector.open_file_dialog()
            load.assert_not_called()
        with patch("scenes.case_select_scene.choose_file", side_effect=OSError("dialog error")):
            selector.open_file_dialog()
        self.assertIn("dialog error", selector._local_error)
        self.assertEqual(controller.public_state, before)

    def test_application_can_render_and_close_twice(self):
        from ui.app import run
        events = [[], [pygame.event.Event(pygame.QUIT)], [], [pygame.event.Event(pygame.QUIT)]]
        with patch("pygame.event.get", side_effect=events):
            run()
            run()

    def test_real_process_handoff_and_rapid_case_reload(self):
        controller = AppController(lambda path: self.make_session(path))
        self.addCleanup(controller.close)
        first = ROOT / "puzzles/examples/example_3x3.json"
        second = next((ROOT / "puzzles/benchmark").glob("bench_4x4_*.json"))
        controller.load_case(str(first))
        self.wait_controller(controller)
        self.assertEqual(controller.metrics.sat_calls, 17)
        self.assertNotEqual(controller.terminal_state, TerminalState.ERROR)
        controller.hint()
        self.assertEqual(controller.metrics.sat_calls, 17)
        controller.restart()
        controller.load_case(str(second))
        self.wait_controller(controller)
        self.assertEqual(controller.public_state.puzzle_id, load_puzzle(second).id)
        self.assertEqual(controller.public_state.size, 4)
        self.assertEqual(controller.metrics.deduction_steps, 0)
        self.assertNotEqual(controller.terminal_state, TerminalState.ERROR)

    def test_worker_error_is_visible_without_revealing_cards(self):
        engine = GameEngine(load_puzzle(ROOT / "puzzles/examples/example_3x3.json"))
        session = GameSession(engine, ErrorAgent())
        controller = AppController(lambda path: session)
        self.addCleanup(controller.close)
        before = session.public_state()
        controller.load_case("test_case")
        self.wait_controller(controller)
        self.assertEqual(controller.terminal_state, TerminalState.ERROR)
        self.assertEqual(controller.public_state, before)
        self.assertEqual(session.metrics().sat_calls, 0)
        self.assertEqual(session.trace, [])

    def test_production_gui_autosolves_extension_case(self):
        controller = AppController(create_session)
        self.addCleanup(controller.close)
        path = ROOT / "puzzles/examples/example_extensions_3x3.json"
        controller.load_case(str(path))
        self.wait_controller(controller)
        self.assertEqual(controller.terminal_state, TerminalState.NONE)
        self.assertEqual(controller.metrics.sat_calls, 17)
        controller.hint()
        self.assertEqual(controller.metrics.sat_calls, 17)
        controller.toggle_auto()
        deadline = perf_counter() + 10
        while controller.terminal_state == TerminalState.NONE and perf_counter() < deadline:
            controller.update(0.6)
            sleep(0.01)
        self.assertEqual(controller.terminal_state, TerminalState.SOLVED)
        self.assertEqual(len(controller.trace_entries), 8)
        self.assertEqual(controller.metrics.sat_calls, 80)
        controller.render(pygame.display.get_surface())
