"""Member 4: selected character, verdict buttons, current public CNF and metrics.

No rendering code is supplied in this scaffold.
"""
from contracts.models import Analysis, PublicState


class InspectorPanel:
    def __init__(self, on_submit):
        self.on_submit = on_submit

    def render(self, surface: object, public_state: PublicState,
               analysis: Analysis | None, selected_cell: str | None) -> None:
        raise NotImplementedError

    def handle_event(self, event: object) -> None:
        raise NotImplementedError
