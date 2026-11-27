"""Application entry point. Use --check to verify contracts without launching GUI."""
import argparse
import importlib
import inspect


def main():
    parser = argparse.ArgumentParser(description="Griductive Solver")
    parser.add_argument("--check", action="store_true", help="verify scaffold imports only")
    args = parser.parse_args()
    if args.check:
        modules = ("contracts.models", "contracts.ports", "algorithms.dpll", "logic.encoder",
                   "logic.agent", "core.puzzle_loader", "core.regions", "core.game_engine",
                   "validation.semantics", "validation.puzzles", "game.session", "game.worker",
                   "ui.app", "ui.board_view", "ui.evidence_panel", "ui.inspector_panel",
                   "ui.trace_panel", "ui.theme", "ui.animations", "ui.clue_text",
                   "game.factory", "app_controller", "scenes.base_scene", "scenes.menu_scene",
                   "scenes.case_select_scene", "scenes.tutorial_scene", "scenes.game_scene", "experiments.runner")
        for name in modules:
            importlib.import_module(name)
        from contracts.ports import Agent, Encoder, Solver
        from algorithms.dpll import DPLLSolver
        from logic.encoder import CNFEncoder
        from logic.agent import LogicAgent
        checks = ((DPLLSolver, Solver, "solve"), (CNFEncoder, Encoder, "encode"),
                  (LogicAgent, Agent, "analyze"), (LogicAgent, Agent, "next_forced"),
                  (LogicAgent, Agent, "check_uniqueness"))
        for implementation, port, method in checks:
            if inspect.signature(getattr(implementation, method)) != inspect.signature(getattr(port, method)):
                raise TypeError(f"Contract mismatch: {implementation.__name__}.{method}")
        print(f"OK: {len(modules)} modules import; {len(checks)} API signatures match. No game/GUI implementation.")
    else:
        from ui.app import run

        run()


if __name__ == "__main__":
    main()
