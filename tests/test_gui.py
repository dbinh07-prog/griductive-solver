"""Member 4 GUI mock fixtures, stubs, and unit tests."""
import ast
from contextlib import ExitStack
from dataclasses import replace
import os
from pathlib import Path
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from app_controller import AppController, TerminalState
from contracts.models import (
    Analysis,
    Character,
    CNF,
    Clue,
    PublicState,
    Region,
    SATQuery,
    SessionMetrics,
    SolverStats,
    SolverTimeout,
    Status,
    SubmitResult,
    TraceEntry,
    VerdictResult,
)
from ui import theme
from ui.board_view import BoardView
from ui.clue_text import clue_formatters, describe_clue
from ui.evidence_panel import EvidencePanel
from ui.inspector_panel import InspectorPanel
from ui.theme import compute_game_layout
from ui.trace_panel import TracePanel


_ROOT = Path(__file__).resolve().parent.parent
_ORIG_GET_FONT = theme.get_font
_FONT_TARGETS = (
    "ui.theme.get_font",
    "ui.board_view.get_font",
    "ui.evidence_panel.get_font",
    "ui.inspector_panel.get_font",
    "ui.trace_panel.get_font",
    "scenes.game_scene.get_font",
)


class _FontSpy:
    def __init__(self, font: pygame.font.Font, log: list[str]) -> None:
        self._font, self._log = font, log

    def render(self, text: str, antialias: bool, color, background=None):
        self._log.append(str(text))
        return self._font.render(text, antialias, color, background)

    def __getattr__(self, name: str):
        return getattr(self._font, name)


def _capture_rendered_text(draw_fn) -> list[str]:
    log: list[str] = []

    def spy_font(size: int, *, bold: bool = False, mono: bool = False):
        return _FontSpy(_ORIG_GET_FONT(size, bold=bold, mono=mono), log)

    with ExitStack() as stack:
        for target in _FONT_TARGETS:
            stack.enter_context(patch(target, side_effect=spy_font))
        draw_fn()
    return log


def _click(pos: tuple[int, int]) -> pygame.event.Event:
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": pos})


def _wheel(y: int, pos: tuple[int, int]) -> pygame.event.Event:
    return pygame.event.Event(pygame.MOUSEWHEEL, {"y": y, "pos": pos})


def _grid_cells(size: int) -> tuple[str, ...]:
    return tuple(f"{chr(65 + c)}{r}" for r in range(1, size + 1) for c in range(size))


def stub_referenced_cells(clue: Clue, size: int) -> tuple[str, ...]:
    """Resolve cells referenced by a public clue using grid geometry only."""
    cells = list(clue.cells)
    reg = clue.region
    if reg is not None:
        kind = reg.kind.upper()
        if kind == "ROW" and 1 <= reg.index <= size:
            cells.extend(f"{chr(65 + c)}{reg.index}" for c in range(size))
        elif kind == "COLUMN" and 1 <= reg.index <= size:
            cells.extend(f"{chr(65 + reg.index - 1)}{r}" for r in range(1, size + 1))
        elif kind == "NEIGHBORS" and len(reg.anchor) >= 2 and reg.anchor[1:].isdigit():
            c0, r0 = ord(reg.anchor[0].upper()) - 65, int(reg.anchor[1:]) - 1
            cells.extend(
                f"{chr(65 + c0 + dc)}{r0 + dr + 1}"
                for dr in (-1, 0, 1)
                for dc in (-1, 0, 1)
                if (dr or dc) and 0 <= r0 + dr < size and 0 <= c0 + dc < size
            )
        elif kind == "EXPLICIT":
            cells.extend(reg.cells)
    return tuple(dict.fromkeys(cells))


def make_mock_public_state(size: int, revealed_count: int = 1, long_names: bool = False) -> PublicState:
    """Create a synthetic PublicState snapshot with zero hidden solution fields."""
    cells = _grid_cells(size)
    chars = tuple(
        Character(
            cell=c,
            name=f"Alexandria Montgomery-Vance {c} ({i + 1})" if long_names else f"Resident {c}",
            profession=f"Senior Forensic Cryptographer {c}" if long_names else f"Analyst {i + 1}",
        )
        for i, c in enumerate(cells)
    )
    proved: list[tuple[str, bool]] = []
    clues: list[tuple[str, Clue]] = []
    count = max(0, min(revealed_count, len(cells)))
    for i in range(count):
        c, crim = cells[i], (i % 2 == 1)
        proved.append((c, crim))
        if long_names:
            cl = Clue(f"clue_{c}", "EXACTLY", (c,), crim, Region("EXPLICIT", cells=cells[: min(len(cells), size + 2)]), 1)
        elif i % 3 == 0:
            cl = Clue(f"clue_{c}", "EXACTLY", (c,), crim, Region("ROW", index=(i // size) + 1), 1)
        elif i % 3 == 1:
            cl = Clue(f"clue_{c}", "AT_LEAST", (c,), crim, Region("NEIGHBORS", anchor=c), 1)
        else:
            cl = Clue(f"clue_{c}", "DIFFERENT", (c, cells[(i + 1) % len(cells)]), crim)
        clues.append((c, cl))
    title = f"Synthetic Long-Title Case Study {size}x{size} Extended" if long_names else f"Mock Case {size}x{size}"
    return PublicState(f"mock_{size}x{size}", title, size, chars, tuple(proved), tuple(clues), revision=count)


def make_mock_analysis(
    state: PublicState,
    forced: dict[str, Status] | None = None,
    inconsistent: bool = False,
) -> Analysis:
    """Create a synthetic Analysis derived solely from public state."""
    proved = dict(state.proved_statuses)
    forced_map = forced or {}
    cls = tuple(
        (
            ch.cell,
            (Status.CRIMINAL if proved[ch.cell] else Status.INNOCENT)
            if ch.cell in proved
            else forced_map.get(ch.cell, Status.UNKNOWN),
        )
        for ch in state.characters
    )
    prim = tuple((ch.cell, i + 1) for i, ch in enumerate(state.characters))
    cnf = CNF(((-1, 2), (1, -2)), prim, max(len(prim), 2))
    q = SATQuery((1,), not inconsistent, SolverStats(2, 6, 0, 0.75))
    return Analysis(state.puzzle_id, state.revision, cls, inconsistent, cnf, (q,))


class StubAnalysisJob:
    """Stub async job simulating pending, valid, stale, timeout, error, and cancel."""

    def __init__(self, state: PublicState, agent=None, timeout_s: float = 5.0, *, outcome=None) -> None:
        self.state, self.agent, self.timeout_s, self.outcome = state, agent, timeout_s, outcome
        self.started = False
        self.cancelled = False

    def start(self) -> None:
        self.started = True

    def cancel(self) -> None:
        self.cancelled = True

    def poll(self) -> Analysis | None:
        if self.cancelled or self.outcome == "PENDING":
            return None
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        if isinstance(self.outcome, type) and issubclass(self.outcome, BaseException):
            raise self.outcome("stub failure")
        if isinstance(self.outcome, Analysis):
            return self.outcome
        return make_mock_analysis(self.state)


class StubSession:
    """In-memory session stub driven strictly by public models."""

    def __init__(self, initial_state: PublicState, analysis: Analysis | None = None) -> None:
        self.agent = None
        self._init_state, self._state = initial_state, initial_state
        self._init_analysis, self.last_analysis = analysis, analysis
        self._forced: dict[str, Status] = {}
        if analysis is not None:
            proved = {c for c, _ in initial_state.proved_statuses}
            self._forced = {c: s for c, s in analysis.classifications if c not in proved and s != Status.UNKNOWN}
        self._metrics = SessionMetrics()
        self.trace: list[TraceEntry] = []
        self.step_calls = 0

    def public_state(self) -> PublicState:
        return self._state

    def analyze(self, *, timeout_s: float = 5.0) -> Analysis:
        if self.last_analysis is None:
            self.last_analysis = make_mock_analysis(self._state, self._forced)
        return self.last_analysis

    def hint(self) -> tuple[str, Status] | None:
        proved = {c for c, _ in self._state.proved_statuses}
        return next(((c, s) for c, s in self._forced.items() if c not in proved), None)

    def _reveal(self, cell: str, status: Status) -> SubmitResult:
        is_crim = status == Status.CRIMINAL
        active_ids = tuple(cl.id for _, cl in self._state.revealed_clues)
        clue = Clue(f"clue_{cell}", "FACT", (cell,), is_crim)
        new_state = replace(
            self._state,
            proved_statuses=self._state.proved_statuses + ((cell, is_crim),),
            revealed_clues=self._state.revealed_clues + ((cell, clue),),
            revision=self._state.revision + 1,
        )
        queries = (SATQuery((1,), True, SolverStats(2, 6, 0, 0.7)),)
        self.trace.append(TraceEntry(len(self.trace) + 1, self._state.revision, active_ids, cell, status, queries, clue.id))
        self._state = new_state
        self.last_analysis = make_mock_analysis(new_state, self._forced)
        m = self._metrics
        self._metrics = SessionMetrics(len(new_state.characters), 2, 4, m.sat_calls + 1, m.decisions + 2, m.propagations + 6, m.backtracks, m.deduction_steps + 1, m.sat_runtime_ms + 0.7)
        return SubmitResult(VerdictResult.ACCEPTED, new_state, clue)

    def submit(self, cell: str, proposed: Status) -> SubmitResult:
        if cell in dict(self._state.proved_statuses):
            return SubmitResult(VerdictResult.ALREADY_REVEALED, self._state)
        if self.last_analysis is not None and self.last_analysis.inconsistent:
            return SubmitResult(VerdictResult.INCONSISTENT, self._state)
        forced = self._forced.get(cell)
        if forced == proposed:
            return self._reveal(cell, proposed)
        if forced is not None:
            return SubmitResult(VerdictResult.CONTRADICTED, self._state)
        return SubmitResult(VerdictResult.NOT_PROVABLE, self._state)

    def step(self) -> SubmitResult | None:
        self.step_calls += 1
        move = self.hint()
        return None if move is None else self._reveal(*move)

    def restart(self) -> PublicState:
        self._state, self.last_analysis, self._metrics = self._init_state, self._init_analysis, SessionMetrics()
        self.trace.clear()
        return self._state

    def export_trace(self, path: str) -> None:
        Path(path).write_text(f"steps={len(self.trace)}\n", encoding="utf-8")

    def metrics(self) -> SessionMetrics:
        return self._metrics


class GUITests(unittest.TestCase):
    """Focused headless verification suite for Member 4 GUI contracts."""

    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.font.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def test_callbacks_use_shared_cell_and_status_types(self) -> None:
        surf = pygame.Surface((1280, 720))
        st = make_mock_public_state(3, revealed_count=1)
        an = make_mock_analysis(st, forced={"B1": Status.INNOCENT})

        cells: list[str] = []
        bv = BoardView(cells.append)
        bv.set_rect(pygame.Rect(280, 100, 560, 400))
        bv.render(surf, st, None, ())
        bv.handle_event(_click(bv._card_rects["A1"].center))
        self.assertEqual(cells, ["A1"])
        self.assertIsInstance(cells[0], str)

        clues: list[str] = []
        ep = EvidencePanel(clues.append)
        ep.set_rect(pygame.Rect(10, 100, 260, 400))
        ep.render(surf, st, None)
        ep.handle_event(_click(ep._item_rects[0][0].center))
        self.assertEqual(clues, ["clue_A1"])
        self.assertIsInstance(clues[0], str)

        verdicts: list[tuple[str, Status]] = []
        ip = InspectorPanel(lambda c, s: verdicts.append((c, s)))
        ip.set_rect(pygame.Rect(850, 100, 320, 400))
        ip.render(surf, st, an, "B1")
        ip.handle_event(_click(ip._btn_criminal.rect.center))
        ip.handle_event(_click(ip._btn_innocent.rect.center))
        self.assertEqual(verdicts, [("B1", Status.CRIMINAL), ("B1", Status.INNOCENT)])

        steps: list[int] = []
        tp = TracePanel(steps.append)
        tp.set_rect(pygame.Rect(10, 510, 1260, 180))
        tp.render(surf, (TraceEntry(1, 1, ("clue_A1",), "B1", Status.INNOCENT, an.queries, "clue_B1"),))
        tp.handle_event(_click(tp._step_rects[0][0].center))
        self.assertEqual(steps, [1])
        self.assertIs(type(steps[0]), int)

        ctrl = AppController(
            lambda _p: StubSession(st, an),
            worker_factory=lambda s, a, t: StubAnalysisJob(s, a, t, outcome="PENDING"),
            referenced_cells_fn=stub_referenced_cells,
        )
        ctrl.load_case("mock")
        ctrl.select_cell("A1")
        self.assertEqual((ctrl.selected_clue_id, ctrl.highlighted_cells), ("clue_A1", ("A1", "B1", "C1")))
        ctrl.select_cell("B1")
        self.assertEqual((ctrl.selected_clue_id, ctrl.highlighted_cells), (None, ()))
        ctrl.close()

        self.assertEqual(set(clue_formatters.keys()), {"FACT", "SAME", "DIFFERENT", "EXACTLY", "AT_LEAST", "AT_MOST", "PARITY", "COUNT_COMPARE"})
        cases = (
            (Clue("c1", "FACT", ("A1",), True), "A1 is Criminal."),
            (Clue("c2", "SAME", ("A1", "B2")), "same status"),
            (Clue("c3", "DIFFERENT", ("B1", "C1")), "different statuses"),
            (Clue("c4", "EXACTLY", region=Region("ROW", index=2), k=1), "Exactly 1 Criminal in Row 2."),
            (Clue("c5", "AT_LEAST", region=Region("COLUMN", index=2), k=2), "At least 2 Criminals in Column B."),
            (Clue("c6", "AT_MOST", region=Region("NEIGHBORS", anchor="B2"), k=1), "Neighbors of B2"),
            (Clue("c7", "EXACTLY", region=Region("EXPLICIT", cells=("A1", "B2")), k=1), "Cells (A1, B2)"),
        )
        for clue, expected in cases:
            txt = describe_clue(clue, 3)
            self.assertIn(expected, txt)
            self.assertTrue(txt.isascii())

    def test_hidden_clues_are_never_rendered(self) -> None:
        surf = pygame.Surface((1280, 720))
        st = make_mock_public_state(3, revealed_count=1)
        an = make_mock_analysis(st, forced={"B2": Status.CRIMINAL})

        bv, ep, ip = BoardView(lambda _c: None), EvidencePanel(lambda _c: None), InspectorPanel(lambda _c, _s: None)
        bv.set_rect(pygame.Rect(280, 100, 560, 400))
        ep.set_rect(pygame.Rect(10, 100, 260, 400))
        ip.set_rect(pygame.Rect(850, 100, 320, 400))

        bv.render(surf, st, "B2", ())
        bv.handle_event(pygame.event.Event(pygame.MOUSEMOTION, {"pos": bv._card_rects["B2"].center}))
        board_txt = _capture_rendered_text(lambda: bv.render(surf, st, "B2", ()))
        self.assertFalse(any("CRIMINAL" in t or "[!]" in t or "clue_B2" in t for t in board_txt))
        self.assertTrue(any("[?] SEALED" in t for t in board_txt))

        ev_txt = _capture_rendered_text(lambda: ep.render(surf, st, None))
        self.assertFalse(any("B2" in t or "clue_B2" in t for t in ev_txt))

        ip.handle_event(pygame.event.Event(pygame.MOUSEMOTION, {"pos": (900, 200)}))
        insp_txt = _capture_rendered_text(lambda: ip.render(surf, st, an, "B2"))
        self.assertIn("[?] FACE-DOWN", insp_txt)
        self.assertFalse(any("Revealed Clue" in t or "CRIMINAL" in t or "clue_B2" in t for t in insp_txt))

        forbidden = {"core.puzzle_loader", "core.game_engine", "algorithms", "logic", "json", "validation", "experiments"}
        gui_files = list((_ROOT / "ui").glob("*.py")) + list((_ROOT / "scenes").glob("*.py")) + [_ROOT / "app_controller.py"]
        for path in gui_files:
            src = path.read_text(encoding="utf-8")
            self.assertNotIn("example_3x3", src)
            for node in ast.walk(ast.parse(src, filename=str(path))):
                names = (
                    [a.name for a in node.names]
                    if isinstance(node, ast.Import)
                    else ([node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
                )
                for mod in names:
                    self.assertNotIn(mod, forbidden, msg=path.name)
                    self.assertNotIn(mod.split(".")[0], forbidden, msg=path.name)
                if isinstance(node, ast.ImportFrom) and node.module == "contracts.models":
                    self.assertNotIn("Puzzle", {a.name for a in node.names}, msg=path.name)
                if isinstance(node, ast.Attribute) and node.attr == "Puzzle":
                    self.fail(f"{path.name}: accessed .Puzzle")

    def test_long_content_resize_and_scroll(self) -> None:
        for w, h in ((1280, 720), (1024, 640)):
            lay = compute_game_layout(w, h)
            rects = (lay.header, lay.toolbar, lay.evidence, lay.board, lay.inspector, lay.trace, lay.status_bar)
            bounds = pygame.Rect(0, 0, w, h)
            for i, r in enumerate(rects):
                self.assertTrue(r.width > 0 and r.height > 0 and bounds.contains(r))
                for other in rects[i + 1 :]:
                    self.assertFalse(r.colliderect(other))

        for size in (3, 4, 5):
            st = make_mock_public_state(size, revealed_count=size * size - 1, long_names=True)
            ctrl = AppController(
                lambda _p, s=st: StubSession(s, make_mock_analysis(s)),
                worker_factory=StubAnalysisJob,
                referenced_cells_fn=stub_referenced_cells,
            )
            ctrl.load_case(f"mock_{size}")
            ctrl.update(0.05)
            ctrl.render(pygame.Surface((1280, 720)))
            ctrl.on_resize(1024, 640)
            ctrl.render(pygame.Surface((1024, 640)))
            ctrl.close()

        surf = pygame.Surface((1024, 640))
        long_st = make_mock_public_state(5, revealed_count=15, long_names=True)
        ep = EvidencePanel(lambda _c: None)
        ep.set_rect(pygame.Rect(10, 100, 250, 260))
        ep.render(surf, long_st, None)
        self.assertGreater(ep._max_scroll, 0)
        ep.handle_event(_wheel(-1, ep._rect.center))
        self.assertGreater(ep._scroll_y, 0)
        ep.handle_event(_wheel(1, ep._rect.center))
        self.assertEqual(ep._scroll_y, 0)

        tp = TracePanel(lambda _s: None)
        tp.set_rect(pygame.Rect(10, 420, 980, 160))
        an = make_mock_analysis(long_st)
        an = replace(an, queries=tuple(an.queries[0] for _ in range(6)))
        entries = tuple(
            TraceEntry(i + 1, i + 1, tuple(f"clue_{c}" for c in _grid_cells(4)[:4]), _grid_cells(5)[i], Status.INNOCENT, an.queries, f"clue_{i}")
            for i in range(10)
        )
        tp.render(surf, entries)
        tp.handle_event(_wheel(-1, tp._trace_left_rect.center))
        self.assertGreater(tp._scroll_y, 0)
        tp.handle_event(_wheel(-1, tp._trace_right_rect.center))
        self.assertGreater(tp._detail_scroll_y, 0)

        kb_an = replace(an, cnf=CNF(tuple((i + 1, -(i + 2)) for i in range(18)), an.cnf.primary_variables, an.cnf.variable_count))
        tp.set_context(kb_an, SessionMetrics())
        tp.set_active_tab("kb")
        tp.render(surf, entries)
        tp.handle_event(_wheel(-1, tp._rect.center))
        self.assertGreater(tp._scroll_y, 0)

    def test_pause_restart_and_terminal_states(self) -> None:
        st = make_mock_public_state(3, revealed_count=1)
        an = make_mock_analysis(st, forced={"B1": Status.INNOCENT, "C1": Status.CRIMINAL})
        sess = StubSession(st, an)
        jobs: list[StubAnalysisJob] = []
        outcomes: list[object] = [an, "PENDING", "PENDING", "PENDING"]

        def make_job(state, agent, timeout_s):
            job = StubAnalysisJob(state, agent, timeout_s, outcome=outcomes.pop(0) if outcomes else None)
            jobs.append(job)
            return job

        ctrl = AppController(lambda _p: sess, worker_factory=make_job, referenced_cells_fn=stub_referenced_cells)
        ctrl.load_case("mock_1")
        ctrl.update(0.05)
        ctrl.toggle_auto()
        ctrl.pause()
        self.assertFalse(ctrl.auto_running)
        ctrl.update(2.0)
        self.assertEqual((sess.step_calls, ctrl.trace_entries), (0, ()))

        ctrl.submit_verdict("B1", Status.INNOCENT)
        old_job, old_gen = jobs[-1], ctrl._job_generation
        ctrl.restart()
        self.assertTrue(old_job.cancelled)
        self.assertEqual(ctrl.trace_entries, ())
        self.assertFalse(ctrl._is_job_current(old_gen, st.puzzle_id, st.revision))

        ctrl.load_case("mock_2")
        self.assertTrue(jobs[2].cancelled)
        ctrl._job = StubAnalysisJob(st, outcome=replace(make_mock_analysis(st, inconsistent=True), revision=99))
        ctrl.update(0.05)
        self.assertIsNone(ctrl.analysis)
        self.assertEqual(ctrl.terminal_state, TerminalState.NONE)
        ctrl.close()

        surf = pygame.Surface((1280, 720))
        solved_st = make_mock_public_state(2, revealed_count=4)
        terminal_cases = (
            (solved_st, None, TerminalState.SOLVED, "Case Solved"),
            (st, make_mock_analysis(st), TerminalState.UNKNOWN, "UNKNOWN"),
            (st, make_mock_analysis(st, inconsistent=True), TerminalState.INCONSISTENT, "INCONSISTENT"),
            (st, SolverTimeout("limit"), TerminalState.TIMEOUT, "Solver Timeout"),
            (st, RuntimeError("boom"), TerminalState.ERROR, "Runtime Error"),
        )
        for state, out, expected_term, expected_label in terminal_cases:
            ctrl = AppController(
                lambda _p, s=state: StubSession(s),
                worker_factory=lambda s, a, t, o=out: StubAnalysisJob(s, a, t, outcome=o),
            )
            ctrl.load_case("term")
            ctrl.update(0.05)
            self.assertEqual(ctrl.terminal_state, expected_term)
            rendered = _capture_rendered_text(lambda c=ctrl: c.render(surf))
            self.assertTrue(any(expected_label in line for line in rendered), msg=expected_label)
            ctrl.close()


if __name__ == "__main__":
    unittest.main()
