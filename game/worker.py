from math import isfinite
from multiprocessing import get_context
from time import perf_counter

from contracts.models import Analysis, PublicState, SolverTimeout
from contracts.ports import Agent


def _run_analysis(sender, state, agent, deadline):
    try:
        remaining = deadline - perf_counter()
        if remaining <= 0:
            raise SolverTimeout("Da het thoi gian phan tich")
        result = agent.analyze(state, timeout_s=remaining)
        if not isinstance(result, Analysis):
            raise ValueError("Agent phai tra ve Analysis")
        if result.puzzle_id != state.puzzle_id or result.revision != state.revision:
            raise ValueError("Analysis khong thuoc public state dang phan tich")
        sender.send(("ok", result, perf_counter()))
    except SolverTimeout as error:
        sender.send(("timeout", str(error), perf_counter()))
    except Exception as error:
        try:
            sender.send(("error", error, perf_counter()))
        except Exception:
            sender.send(("error", RuntimeError(f"{type(error).__name__}: {error}"), perf_counter()))
    finally:
        sender.close()


class AnalysisJob:
    """Phan tich trong process rieng, khong sua state hay widget cua GUI."""

    def __init__(self, state: PublicState, agent: Agent, timeout_s: float = 5.0):
        if not isinstance(state, PublicState):
            raise ValueError("Worker chi nhan PublicState")
        if not callable(getattr(agent, "analyze", None)):
            raise ValueError("Agent phai co ham analyze")
        if type(timeout_s) not in (int, float) or not isfinite(timeout_s):
            raise ValueError("timeout_s phai la so huu han")
        if timeout_s <= 0:
            raise SolverTimeout("Da het thoi gian phan tich")

        self.state = state
        self.timeout_s = timeout_s
        self.agent = agent
        self._process = None
        self._receiver = None
        self._deadline = None
        self._result = None
        self._error = None
        self._started = False
        self._finished = False
        self._cancelled = False

    def start(self) -> None:
        if self._started or self._cancelled:
            raise RuntimeError("AnalysisJob chi duoc start mot lan")
        context = get_context("spawn")
        self._receiver, sender = context.Pipe(duplex=False)
        self._deadline = perf_counter() + self.timeout_s
        self._process = context.Process(
            target=_run_analysis,
            args=(sender, self.state, self.agent, self._deadline),
            daemon=True,
        )
        self._started = True
        try:
            self._process.start()
        except Exception as error:
            self._error = error
            self._finished = True
            self._close_process()
            raise
        finally:
            sender.close()

    def poll(self) -> Analysis | None:
        if self._cancelled:
            return None
        if not self._started:
            raise RuntimeError("Can start AnalysisJob truoc khi poll")
        if self._finished:
            return self._get_result()

        try:
            ready = self._receiver.poll()
        except OSError as error:
            self._error = RuntimeError(f"Worker dung ma khong tra ket qua: {error}")
            self._finished = True
            self._close_process()
            return self._get_result()

        if ready:
            try:
                kind, value, finished = self._receiver.recv()
                if finished > self._deadline or kind == "timeout":
                    self._error = SolverTimeout("Da het thoi gian phan tich")
                elif kind == "error":
                    self._error = value
                elif kind == "ok":
                    self._result = value
                else:
                    self._error = RuntimeError("Ket qua worker khong hop le")
            except (EOFError, OSError) as error:
                self._error = RuntimeError(f"Worker dung ma khong tra ket qua: {error}")
            self._finished = True
            self._close_process()
            return self._get_result()

        if not self._process.is_alive():
            self._error = RuntimeError(f"Worker dung voi exit code {self._process.exitcode}")
        elif perf_counter() >= self._deadline:
            self._error = SolverTimeout("Da het thoi gian phan tich")
        else:
            return None

        self._finished = True
        self._close_process()
        return self._get_result()

    def cancel(self) -> None:
        self._cancelled = True
        self._finished = True
        self._result = None
        self._close_process()

    def _get_result(self):
        if self._error is not None:
            raise self._error
        return self._result

    def _close_process(self):
        if self._receiver is not None:
            self._receiver.close()
            self._receiver = None
        if self._process is not None:
            if self._process.is_alive():
                self._process.terminate()
            if self._process.pid is not None:
                self._process.join(timeout=0.2)
            if self._process.is_alive():
                self._process.kill()
                self._process.join(timeout=0.2)
            if not self._process.is_alive():
                self._process.close()
            self._process = None
