from contracts.models import Analysis, PublicState, SessionMetrics, Status, SubmitResult, TraceEntry
from contracts.ports import Agent
from core.game_engine import GameEngine


class GameSession:
    """Member 1: integration only. Algorithms remain in their owners' modules."""

    def __init__(self, engine: GameEngine, agent: Agent):
        self.engine, self.agent = engine, agent
        self.trace: list[TraceEntry] = []

    def public_state(self) -> PublicState:
        raise NotImplementedError("Member 1: expose public snapshot to UI")

    def analyze(self, *, timeout_s: float = 5.0) -> Analysis:
        raise NotImplementedError("Member 1: analyze and cache by revision")

    def hint(self) -> tuple[str, Status] | None:
        raise NotImplementedError("Member 1: proved next move; do not reveal")

    def submit(self, cell: str, proposed: Status) -> SubmitResult:
        raise NotImplementedError("Member 1: verify then submit; trace accepted reveals")

    def step(self) -> SubmitResult | None:
        raise NotImplementedError("Member 1: at most one deterministic forced reveal")

    def restart(self) -> PublicState:
        raise NotImplementedError("Member 1: reset public state, trace and metrics")

    def export_trace(self, path: str) -> None:
        raise NotImplementedError("Member 1: export public trace as JSON/CSV")

    def metrics(self) -> SessionMetrics:
        raise NotImplementedError("Member 1: aggregate actual gameplay queries once")
