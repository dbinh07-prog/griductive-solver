"""Member 4: public clue list and selection; use core.regions.referenced_cells.

No rendering code is supplied in this scaffold.
"""
from contracts.models import PublicState


class EvidencePanel:
    def __init__(self, on_select_clue):
        self.on_select_clue = on_select_clue

    def render(self, surface: object, public_state: PublicState, selected_clue_id: str | None) -> None:
        raise NotImplementedError

    def handle_event(self, event: object) -> None:
        raise NotImplementedError
