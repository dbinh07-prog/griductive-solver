class BaseScene:
    """Member 4: replace object types with the selected GUI framework types."""

    def __init__(self, controller):
        self.controller = controller

    def on_enter(self) -> None:
        raise NotImplementedError

    def handle_event(self, event: object) -> None:
        raise NotImplementedError

    def update(self, dt: float) -> None:
        raise NotImplementedError

    def render(self, surface: object) -> None:
        raise NotImplementedError

    def on_exit(self) -> None:
        raise NotImplementedError
