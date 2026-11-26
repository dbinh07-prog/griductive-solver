"""Application controller coordinating scene navigation, session state, and background analysis."""
from collections.abc import Callable
from enum import Enum
from pathlib import Path

from contracts.models import (
    Analysis,
    Clue,
    PublicState,
    SessionMetrics,
    SolverTimeout,
    Status,
    SubmitResult,
    TraceEntry,
    VerdictResult,
)
from game.worker import AnalysisJob
from scenes.base_scene import BaseScene
from ui.animations import AnimationManager
from ui.inspector_panel import FeedbackMessage
from ui.theme import play_flip_sound


class TerminalState(str, Enum):
    NONE = "NONE"
    SOLVED = "SOLVED"
    UNKNOWN = "UNKNOWN"
    INCONSISTENT = "INCONSISTENT"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


class AppController:
    """Member 4: navigation, input handling, async analysis polling, and game controls."""

    def __init__(
        self,
        session_factory,
        *,
        worker_factory=None,
        referenced_cells_fn: Callable[[Clue, int], tuple[str, ...]] | None = None,
    ) -> None:
        self.session_factory = session_factory
        self._worker_factory = worker_factory or AnalysisJob
        self._referenced_cells_fn = referenced_cells_fn
        self._analysis_timeout_s = 5.0

        self._session = None
        self._public_state: PublicState | None = None
        self._analysis: Analysis | None = None
        self._scene: BaseScene | None = None
        self._previous_scene: BaseScene | None = None
        self._window_size = (1280, 720)

        self._job = None
        self._generation = 0
        self._job_generation = 0
        self._job_puzzle_id = ""
        self._job_revision = -1
        self._is_loading = False

        self._selected_cell: str | None = None
        self._selected_clue_id: str | None = None
        self._highlighted_cells: tuple[str, ...] = ()
        self._feedback: FeedbackMessage | None = None
        self._hint_move: tuple[str, Status] | None = None
        self._no_forced_message: str | None = None
        self._selected_trace_step: int | None = None

        self._auto_running = False
        self._auto_speed = 1.0
        self._auto_timer = 0.0
        self._muted = False
        self._terminal_state = TerminalState.NONE
        self._status_message = ""
        self._should_quit = False
        self._animations = AnimationManager()

    @property
    def public_state(self) -> PublicState | None:
        return self._public_state

    @property
    def analysis(self) -> Analysis | None:
        return self._analysis

    @property
    def metrics(self) -> SessionMetrics | None:
        if self._session is None:
            return None
        try:
            current = self._session.metrics()
        except (NotImplementedError, AttributeError):
            return None
        if current is None:
            return None
        if self._analysis is None and current == SessionMetrics():
            return None
        return current

    @property
    def trace_entries(self) -> tuple[TraceEntry, ...]:
        if self._session is None:
            return ()
        return tuple(getattr(self._session, "trace", ()))

    @property
    def selected_cell(self) -> str | None:
        return self._selected_cell

    @property
    def selected_clue_id(self) -> str | None:
        return self._selected_clue_id

    @property
    def highlighted_cells(self) -> tuple[str, ...]:
        return self._highlighted_cells

    @property
    def feedback(self) -> FeedbackMessage | None:
        return self._feedback

    @property
    def hint_move(self) -> tuple[str, Status] | None:
        return self._hint_move

    @property
    def no_forced_message(self) -> str | None:
        return self._no_forced_message

    @property
    def auto_running(self) -> bool:
        return self._auto_running

    @property
    def auto_speed(self) -> float:
        return self._auto_speed

    @property
    def muted(self) -> bool:
        return self._muted

    @property
    def is_loading(self) -> bool:
        return self._is_loading

    @property
    def terminal_state(self) -> TerminalState:
        return self._terminal_state

    @property
    def status_message(self) -> str:
        return self._status_message

    @property
    def selected_trace_step(self) -> int | None:
        return self._selected_trace_step

    @property
    def animations(self) -> AnimationManager:
        return self._animations

    @property
    def should_quit(self) -> bool:
        return self._should_quit

    @property
    def scene(self) -> BaseScene | None:
        return self._scene

    def show_menu(self) -> None:
        from scenes.menu_scene import MenuScene

        self.pause()
        self._cancel_job()
        self._generation += 1
        self._status_message = ""
        self._previous_scene = None
        self._switch_scene(MenuScene(self))

    def show_case_select(self) -> None:
        from scenes.case_select_scene import CaseSelectScene

        self.pause()
        self._cancel_job()
        self._generation += 1
        self._status_message = ""
        self._previous_scene = None
        self._switch_scene(CaseSelectScene(self))

    def show_tutorial(self) -> None:
        from scenes.tutorial_scene import TutorialScene

        self.pause()
        if self._scene is not None and not isinstance(self._scene, TutorialScene):
            self._previous_scene = self._scene
        tutorial = TutorialScene(self)
        self._scene = tutorial
        tutorial.on_enter()
        tutorial.on_resize(*self._window_size)

    def return_from_tutorial(self) -> None:
        if self._previous_scene is None:
            self.show_menu()
            return
        if self._scene is not None:
            self._scene.on_exit()
        self._scene = self._previous_scene
        self._previous_scene = None
        self._scene.on_resize(*self._window_size)

    def load_case(self, path: str) -> None:
        from scenes.game_scene import GameScene

        self.pause()
        self._cancel_job()
        self._generation += 1

        try:
            sess = self.session_factory(path)
            state = sess.public_state()
        except SolverTimeout as exc:
            self._terminal_state = TerminalState.TIMEOUT
            self._status_message = f"Solver timed out while loading case: {exc or 'timeout'}."
            self._feedback = FeedbackMessage("TIMEOUT", "Solver Timeout", self._status_message)
            return
        except Exception as exc:
            self._terminal_state = TerminalState.ERROR
            self._status_message = f"Failed to load case: {exc}"
            self._feedback = FeedbackMessage("ERROR", "Load Error", self._status_message)
            return

        self._reset_view_state()
        self._session = sess
        self._public_state = state
        self._previous_scene = None
        self._status_message = f"Loaded {state.title} ({state.size}x{state.size})."
        self._switch_scene(GameScene(self))

        if self._is_solved(state):
            self._terminal_state = TerminalState.SOLVED
            self._status_message = f"Solved in {len(self.trace_entries)} deduction steps."
        else:
            self._start_analysis()

    def select_cell(self, cell: str) -> None:
        self._selected_cell = cell
        if self._public_state is None:
            self._selected_clue_id = None
            self._highlighted_cells = ()
            return

        proved = dict(self._public_state.proved_statuses)
        if cell not in proved:
            self._selected_clue_id = None
            self._highlighted_cells = ()
            return

        clue = next((cl for owner, cl in self._public_state.revealed_clues if owner == cell), None)
        if clue is None:
            self._selected_clue_id = None
            self._highlighted_cells = ()
            return
        self.select_clue(clue.id)

    def select_clue(self, clue_id: str) -> None:
        if self._public_state is None:
            self._selected_clue_id = None
            self._highlighted_cells = ()
            return

        clue = next((cl for _, cl in self._public_state.revealed_clues if cl.id == clue_id), None)
        if clue is None:
            self._selected_clue_id = None
            self._highlighted_cells = ()
            return
        self._selected_clue_id = clue.id
        self._highlighted_cells = self._resolve_referenced_cells(clue, self._public_state.size)

    def submit_verdict(self, cell: str, proposed: Status) -> None:
        if self._session is None or self._public_state is None:
            return
        if proposed not in (Status.CRIMINAL, Status.INNOCENT):
            self._feedback = FeedbackMessage(
                "ERROR",
                "Invalid Verdict",
                "Only CRIMINAL or INNOCENT verdicts can be submitted.",
            )
            return

        try:
            outcome = self._session.submit(cell, proposed)
        except SolverTimeout as exc:
            self.pause()
            self._terminal_state = TerminalState.TIMEOUT
            self._status_message = f"Solver timed out during verdict check: {exc or 'timeout'}."
            self._feedback = FeedbackMessage("TIMEOUT", "Solver Timeout", self._status_message)
            return
        except Exception as exc:
            self.pause()
            self._terminal_state = TerminalState.ERROR
            self._status_message = f"Verdict check failed: {exc}"
            self._feedback = FeedbackMessage("ERROR", "Submission Error", self._status_message)
            return

        self._apply_submit_result(cell, proposed, outcome)

    def hint(self) -> None:
        if self._session is None or self._public_state is None:
            return
        if self._is_solved(self._public_state):
            self._hint_move = None
            self._no_forced_message = "Puzzle is already solved."
            self._status_message = self._no_forced_message
            return

        try:
            move = self._session.hint()
        except SolverTimeout as exc:
            self.pause()
            self._terminal_state = TerminalState.TIMEOUT
            self._status_message = f"Solver timed out while computing hint: {exc or 'timeout'}."
            self._feedback = FeedbackMessage("TIMEOUT", "Solver Timeout", self._status_message)
            return
        except Exception as exc:
            self.pause()
            self._terminal_state = TerminalState.ERROR
            self._status_message = f"Hint failed: {exc}"
            self._feedback = FeedbackMessage("ERROR", "Hint Error", self._status_message)
            return

        if move is not None:
            h_cell, h_status = move
            self._hint_move = (h_cell, h_status)
            self._no_forced_message = None
            self.select_cell(h_cell)
            self._animations.trigger_pulse(h_cell)
            self._status_message = f"Hint: {h_cell} is forced {h_status.value}."
            return

        self._hint_move = None
        known = self._current_analysis()
        if (known is not None and known.inconsistent) or (
            self._terminal_state == TerminalState.INCONSISTENT
        ):
            self._no_forced_message = "Knowledge base is inconsistent (UNSAT)."
            self._terminal_state = TerminalState.INCONSISTENT
            self.pause()
        else:
            self._no_forced_message = "No forced move available from current public evidence."
            if known is not None and not known.inconsistent:
                self._terminal_state = TerminalState.UNKNOWN
                self.pause()
        self._status_message = self._no_forced_message

    def next_step(self) -> None:
        if self._session is None or self._public_state is None:
            return
        if self._is_solved(self._public_state):
            self.pause()
            self._terminal_state = TerminalState.SOLVED
            self._status_message = f"Solved in {len(self.trace_entries)} deduction steps."
            return

        try:
            outcome = self._session.step()
        except SolverTimeout as exc:
            self.pause()
            self._terminal_state = TerminalState.TIMEOUT
            self._status_message = f"Solver timed out during step: {exc or 'timeout'}."
            self._feedback = FeedbackMessage("TIMEOUT", "Solver Timeout", self._status_message)
            return
        except Exception as exc:
            self.pause()
            self._terminal_state = TerminalState.ERROR
            self._status_message = f"Step failed: {exc}"
            self._feedback = FeedbackMessage("ERROR", "Step Error", self._status_message)
            return

        if outcome is None:
            self.pause()
            known = self._current_analysis()
            if self._is_solved(self._public_state):
                self._terminal_state = TerminalState.SOLVED
                self._status_message = f"Solved in {len(self.trace_entries)} deduction steps."
            elif (known is not None and known.inconsistent) or (
                self._terminal_state == TerminalState.INCONSISTENT
            ):
                self._terminal_state = TerminalState.INCONSISTENT
                self._status_message = "Knowledge base is inconsistent (UNSAT)."
                self._feedback = FeedbackMessage(
                    "INCONSISTENT",
                    "Inconsistent Knowledge Base",
                    self._status_message,
                )
            else:
                self._terminal_state = TerminalState.UNKNOWN
                self._no_forced_message = "No forced move available from current public evidence."
                self._status_message = self._no_forced_message
            return

        self._apply_submit_result(None, None, outcome)

    def toggle_auto(self) -> None:
        if self._session is None or self._public_state is None:
            return
        if self._auto_running:
            self.pause()
            return
        if self._terminal_state != TerminalState.NONE:
            return
        self._auto_running = True
        self._auto_timer = 0.0
        self._status_message = f"Auto Solve running at {self._auto_speed:g}x."

    def pause(self) -> None:
        self._auto_running = False
        self._auto_timer = 0.0

    def restart(self) -> None:
        if self._session is None:
            return
        self.pause()
        self._cancel_job()
        self._generation += 1
        self._reset_view_state()

        try:
            self._public_state = self._session.restart()
        except SolverTimeout as exc:
            self._terminal_state = TerminalState.TIMEOUT
            self._status_message = f"Solver timed out during restart: {exc or 'timeout'}."
            self._feedback = FeedbackMessage("TIMEOUT", "Solver Timeout", self._status_message)
            return
        except Exception as exc:
            self._terminal_state = TerminalState.ERROR
            self._status_message = f"Restart failed: {exc}"
            self._feedback = FeedbackMessage("ERROR", "Restart Error", self._status_message)
            return

        self._status_message = "Case restarted."
        if self._is_solved(self._public_state):
            self._terminal_state = TerminalState.SOLVED
        else:
            self._start_analysis()

    def toggle_mute(self) -> None:
        self._muted = not self._muted

    def set_auto_speed(self, speed: float) -> None:
        self._auto_speed = max(0.25, min(8.0, float(speed)))

    def select_trace_step(self, step: int | None) -> None:
        self._selected_trace_step = step

    def export_trace(self, path: str) -> None:
        if self._session is None:
            self._status_message = "No active session to export trace."
            return
        try:
            self._session.export_trace(path)
            self._status_message = f"Exported trace to {path}."
        except Exception as exc:
            self._feedback = FeedbackMessage("ERROR", "Export Error", f"Failed to export trace: {exc}")
            self._status_message = f"Failed to export trace: {exc}"

    def export_public_cnf(self, path: str) -> None:
        if self._analysis is None:
            self._status_message = "Public CNF is not available yet."
            self._feedback = FeedbackMessage("INFO", "Public CNF Unavailable", self._status_message)
            return

        cnf = self._analysis.cnf
        lines = [
            f"c puzzle_id={self._analysis.puzzle_id} revision={self._analysis.revision}",
        ]
        for cell, var_id in cnf.primary_variables:
            lines.append(f"c var {var_id} {cell}")
        lines.append(f"p cnf {cnf.variable_count} {len(cnf.clauses)}")
        for clause in cnf.clauses:
            lits = " ".join(str(lit) for lit in clause)
            lines.append(f"{lits} 0" if lits else "0")

        try:
            Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
            self._status_message = f"Exported public CNF to {path}."
        except OSError as exc:
            self._feedback = FeedbackMessage("ERROR", "Export Error", f"Failed to export CNF: {exc}")
            self._status_message = f"Failed to export CNF: {exc}"

    def update(self, dt: float) -> None:
        self._animations.update(dt)
        self._poll_analysis()

        if (
            self._auto_running
            and not self._is_loading
            and self._terminal_state == TerminalState.NONE
            and dt > 0
        ):
            self._auto_timer += dt
            interval = 0.65 / max(0.25, self._auto_speed)
            if self._auto_timer >= interval:
                self._auto_timer = 0.0
                self.next_step()

        if self._scene is not None:
            self._scene.update(dt)

    def handle_event(self, event: object) -> None:
        if self._scene is not None:
            self._scene.handle_event(event)

    def render(self, surface: object) -> None:
        if self._scene is not None:
            self._scene.render(surface)

    def on_resize(self, width: int, height: int) -> None:
        self._window_size = (width, height)
        if self._scene is not None:
            self._scene.on_resize(width, height)

    def close(self) -> None:
        self.pause()
        self._cancel_job()
        # Bump generation so any in-flight poll outside the loop is invalidated.
        self._generation += 1
        if self._scene is not None:
            self._scene.on_exit()
        self._should_quit = True

    def _switch_scene(self, scene: BaseScene) -> None:
        if self._scene is not None:
            self._scene.on_exit()
        self._scene = scene
        scene.on_enter()
        scene.on_resize(*self._window_size)

    def _reset_view_state(self) -> None:
        self._analysis = None
        self._selected_cell = None
        self._selected_clue_id = None
        self._highlighted_cells = ()
        self._feedback = None
        self._hint_move = None
        self._no_forced_message = None
        self._selected_trace_step = None
        self._terminal_state = TerminalState.NONE
        self._animations.clear()

    def _is_solved(self, state: PublicState | None) -> bool:
        return state is not None and state.size > 0 and len(state.proved_statuses) >= state.size * state.size

    def _resolve_referenced_cells(self, clue: Clue, size: int) -> tuple[str, ...]:
        try:
            if self._referenced_cells_fn is not None:
                return tuple(self._referenced_cells_fn(clue, size))
            # Lazy import avoids hard dependency before core.regions is implemented.
            from core.regions import referenced_cells

            return tuple(referenced_cells(clue, size))
        except (ImportError, NotImplementedError, ValueError, TypeError):
            return ()

    def _cancel_job(self) -> None:
        if self._job is not None:
            try:
                self._job.cancel()
            except NotImplementedError:
                pass
            self._job = None
        self._is_loading = False

    def _start_analysis(self) -> None:
        self._cancel_job()
        if self._public_state is None or self._session is None:
            return

        agent = getattr(self._session, "agent", None)
        try:
            job = self._worker_factory(self._public_state, agent, self._analysis_timeout_s)
            job.start()
        except NotImplementedError:
            self._job = None
            self._is_loading = False
            return
        except SolverTimeout as exc:
            self.pause()
            self._terminal_state = TerminalState.TIMEOUT
            self._status_message = f"Solver timed out: {exc or 'analysis exceeded limit'}."
            self._feedback = FeedbackMessage("TIMEOUT", "Solver Timeout", self._status_message)
            return
        except Exception as exc:
            self.pause()
            self._terminal_state = TerminalState.ERROR
            self._status_message = f"Analysis failed: {exc}"
            self._feedback = FeedbackMessage("ERROR", "Analysis Error", self._status_message)
            return

        self._job = job
        self._job_generation = self._generation
        self._job_puzzle_id = self._public_state.puzzle_id
        self._job_revision = self._public_state.revision
        self._is_loading = True

    def _current_analysis(self) -> Analysis | None:
        if self._analysis is not None:
            return self._analysis
        if self._session is None or self._public_state is None:
            return None
        cand = getattr(self._session, "last_analysis", None)
        if (
            isinstance(cand, Analysis)
            and cand.puzzle_id == self._public_state.puzzle_id
            and cand.revision == self._public_state.revision
        ):
            return cand
        return None

    def _is_job_current(self, generation: int, puzzle_id: str, revision: int) -> bool:
        if self._public_state is None:
            return False
        return (
            generation == self._generation
            and puzzle_id == self._public_state.puzzle_id
            and revision == self._public_state.revision
        )

    def _poll_analysis(self) -> None:
        if self._job is None:
            return
        job = self._job
        gen = self._job_generation
        pid = self._job_puzzle_id
        rev = self._job_revision

        try:
            result = job.poll()
        except SolverTimeout as exc:
            self._job = None
            self._is_loading = False
            if not self._is_job_current(gen, pid, rev):
                return
            self.pause()
            self._terminal_state = TerminalState.TIMEOUT
            self._status_message = f"Solver timed out: {exc or 'analysis exceeded limit'}."
            self._feedback = FeedbackMessage("TIMEOUT", "Solver Timeout", self._status_message)
            return
        except Exception as exc:
            self._job = None
            self._is_loading = False
            if not self._is_job_current(gen, pid, rev):
                return
            self.pause()
            self._terminal_state = TerminalState.ERROR
            self._status_message = f"Analysis error: {exc}"
            self._feedback = FeedbackMessage("ERROR", "Analysis Error", self._status_message)
            return

        if result is None:
            return

        self._job = None
        self._is_loading = False
        if not self._is_job_current(gen, pid, rev):
            return
        if result.puzzle_id != self._public_state.puzzle_id or result.revision != self._public_state.revision:
            return

        self._analysis = result
        proved = {c for c, _ in self._public_state.proved_statuses}
        has_forced = any(
            c not in proved and st in (Status.CRIMINAL, Status.INNOCENT)
            for c, st in result.classifications
        )
        if self._is_solved(self._public_state):
            self.pause()
            self._terminal_state = TerminalState.SOLVED
            self._status_message = f"Solved in {len(self.trace_entries)} deduction steps."
        elif result.inconsistent:
            self.pause()
            self._terminal_state = TerminalState.INCONSISTENT
            self._status_message = "Knowledge base is inconsistent (UNSAT)."
            self._feedback = FeedbackMessage("INCONSISTENT", "Inconsistent Knowledge Base", self._status_message)
        elif not has_forced:
            self.pause()
            self._terminal_state = TerminalState.UNKNOWN
            self._status_message = "No forced moves remain from current public evidence (UNKNOWN)."
        else:
            self._terminal_state = TerminalState.NONE

    def _find_revealed_cell(
        self,
        prev_state: PublicState,
        new_state: PublicState,
        fallback_cell: str | None,
    ) -> str | None:
        if fallback_cell is not None:
            return fallback_cell
        old_cells = {c for c, _ in prev_state.proved_statuses}
        for c, _ in new_state.proved_statuses:
            if c not in old_cells:
                return c
        trace = self.trace_entries
        return trace[-1].cell if trace else None

    def _apply_submit_result(
        self,
        cell: str | None,
        proposed: Status | None,
        outcome: SubmitResult,
    ) -> None:
        prev_state = self._public_state
        if prev_state is None:
            return

        if outcome.result == VerdictResult.ACCEPTED:
            target_cell = self._find_revealed_cell(prev_state, outcome.new_public_state, cell)
            self._public_state = outcome.new_public_state
            self._analysis = None
            self._hint_move = None
            self._no_forced_message = None

            if target_cell is not None:
                self._animations.trigger_flip(target_cell)
                play_flip_sound(muted=self._muted)
                self._selected_cell = target_cell
                if outcome.revealed_clue is not None:
                    self._selected_clue_id = outcome.revealed_clue.id
                    self._highlighted_cells = self._resolve_referenced_cells(
                        outcome.revealed_clue,
                        outcome.new_public_state.size,
                    )
                else:
                    self.select_cell(target_cell)
            else:
                play_flip_sound(muted=self._muted)

            if self.trace_entries:
                self._selected_trace_step = self.trace_entries[-1].step

            verdict_str = proposed.value if proposed is not None else self._verdict_label(target_cell)
            clue_note = f" Revealed {outcome.revealed_clue.id}." if outcome.revealed_clue is not None else ""
            detail = f"{target_cell or 'Card'} confirmed as {verdict_str}.{clue_note}"
            self._feedback = FeedbackMessage("ACCEPTED", "Verdict Accepted", detail)

            if self._is_solved(self._public_state):
                self.pause()
                self._cancel_job()
                self._terminal_state = TerminalState.SOLVED
                self._status_message = f"Solved in {len(self.trace_entries)} deduction steps."
            else:
                self._terminal_state = TerminalState.NONE
                self._status_message = detail
                self._start_analysis()
            return

        if outcome.result == VerdictResult.NOT_PROVABLE:
            if cell is not None:
                self._animations.trigger_reject(cell)
            self._feedback = FeedbackMessage(
                "NOT_PROVABLE",
                "Not Provable",
                "Not enough public evidence to force this verdict.",
            )
            self._status_message = "Verdict rejected: not enough public evidence."
            return

        if outcome.result == VerdictResult.CONTRADICTED:
            if cell is not None:
                self._animations.trigger_reject(cell)
            self._feedback = FeedbackMessage(
                "CONTRADICTED",
                "Contradicted Verdict",
                "Contradicted: opposite verdict is already forced by public evidence.",
            )
            self._status_message = "Verdict rejected: opposite verdict is already forced."
            return

        if outcome.result == VerdictResult.INCONSISTENT:
            self.pause()
            self._terminal_state = TerminalState.INCONSISTENT
            self._status_message = "Knowledge base is inconsistent (UNSAT)."
            self._feedback = FeedbackMessage(
                "INCONSISTENT",
                "Inconsistent Knowledge Base",
                self._status_message,
            )
            return

        if outcome.result == VerdictResult.ALREADY_REVEALED:
            detail = f"{cell or 'Card'} has already been revealed."
            self._feedback = FeedbackMessage("ALREADY_REVEALED", "Already Revealed", detail)
            self._status_message = detail

    def _verdict_label(self, cell: str | None) -> str:
        if cell is None or self._public_state is None:
            return "PROVED"
        proved = dict(self._public_state.proved_statuses)
        if cell in proved:
            return Status.CRIMINAL.value if proved[cell] else Status.INNOCENT.value
        return "PROVED"
