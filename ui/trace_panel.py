"""Member 4: deduction history with active clue IDs and actual SAT queries.

No rendering code is supplied in this scaffold.
"""
from contracts.models import TraceEntry


class TracePanel:
    def __init__(self, on_select_step):
        self.on_select_step = on_select_step

    def render(self, surface: object, entries: tuple[TraceEntry, ...]) -> None:
        raise NotImplementedError

    def handle_event(self, event: object) -> None:
        raise NotImplementedError
