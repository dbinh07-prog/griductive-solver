from algorithms.dpll import DPLLSolver
from core.game_engine import GameEngine
from core.puzzle_loader import load_puzzle
from logic.agent import LogicAgent
from logic.encoder import CNFEncoder

from .session import GameSession


def create_session(puzzle_path: str) -> GameSession:
    """Ghep cac module; Puzzle chi duoc dua vao engine."""
    puzzle = load_puzzle(puzzle_path)
    engine = GameEngine(puzzle)
    encoder = CNFEncoder()
    solver = DPLLSolver()
    agent = LogicAgent(encoder, solver)
    return GameSession(engine, agent)
