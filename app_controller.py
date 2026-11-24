from contracts.models import Status


class AppController:
    """Member 4: navigation and input; Member 1 provides session_factory."""

    def __init__(self, session_factory):
        self.session_factory = session_factory

    def show_menu(self) -> None:
        raise NotImplementedError

    def show_case_select(self) -> None:
        raise NotImplementedError

    def show_tutorial(self) -> None:
        raise NotImplementedError

    def load_case(self, path: str) -> None:
        raise NotImplementedError

    def select_cell(self, cell: str) -> None:
        raise NotImplementedError

    def select_clue(self, clue_id: str) -> None:
        raise NotImplementedError

    def submit_verdict(self, cell: str, proposed: Status) -> None:
        raise NotImplementedError

    def hint(self) -> None:
        raise NotImplementedError

    def next_step(self) -> None:
        raise NotImplementedError

    def toggle_auto(self) -> None:
        raise NotImplementedError

    def pause(self) -> None:
        raise NotImplementedError

    def restart(self) -> None:
        raise NotImplementedError

    def update(self, dt: float) -> None:
        raise NotImplementedError

    def handle_event(self, event: object) -> None:
        raise NotImplementedError

    def render(self, surface: object) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError
