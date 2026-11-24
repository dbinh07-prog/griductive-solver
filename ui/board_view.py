"""Member 4: board, row/column coordinates, character cards, reveal animation.

Receive PublicState only. Never open puzzle JSON or inspect hidden labels.
No rendering code is supplied in this scaffold.
"""
from contracts.models import PublicState


class BoardView:
    def __init__(self, on_select):
        self.on_select = on_select

    def render(self, surface: object, public_state: PublicState,
               selected_cell: str | None, highlighted_cells: tuple[str, ...]) -> None:
        raise NotImplementedError

    def handle_event(self, event: object) -> None:
        raise NotImplementedError
