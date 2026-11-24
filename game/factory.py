from .session import GameSession


def create_session(puzzle_path: str) -> GameSession:
    """Member 1: compose loader -> engine and encoder + solver -> agent -> session.

    Controller calls this factory; views never receive the private Puzzle.
    """
    raise NotImplementedError("Member 1: composition root after modules are available")
