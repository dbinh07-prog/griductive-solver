from contracts.models import Analysis, PublicState
from contracts.ports import Agent


class AnalysisJob:
    """Member 1: run analysis off the GUI thread with a public snapshot only."""

    def __init__(self, state: PublicState, agent: Agent, timeout_s: float = 5.0):
        self.state, self.timeout_s = state, timeout_s
        self.agent = agent

    def start(self) -> None:
        raise NotImplementedError("Member 1: start background analysis")

    def poll(self) -> Analysis | None:
        raise NotImplementedError("Member 1: pending=None; errors must remain distinguishable")

    def cancel(self) -> None:
        raise NotImplementedError("Member 1: stop job and reject stale results")
