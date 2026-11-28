import unittest
from unittest.mock import patch

from algorithms.dpll import DPLLSolver
from game.factory import create_session
from tests.member1_data import SampleAgent, SampleEngine


class FactoryTests(unittest.TestCase):
    def test_composition_keeps_private_puzzle_in_engine(self):
        private_puzzle = object()
        engine = SampleEngine()
        encoder = object()
        agent = SampleAgent()
        with patch("game.factory.load_puzzle", return_value=private_puzzle) as loader, \
             patch("game.factory.GameEngine", return_value=engine) as engine_class, \
             patch("game.factory.CNFEncoder", return_value=encoder), \
             patch("game.factory.LogicAgent", return_value=agent) as agent_class:
            session = create_session("test.json")
        loader.assert_called_once_with("test.json")
        engine_class.assert_called_once_with(private_puzzle)
        args = agent_class.call_args.args
        self.assertIs(args[0], encoder)
        self.assertIsInstance(args[1], DPLLSolver)
        self.assertNotIn(private_puzzle, args)
        self.assertIs(session.engine, engine)
        self.assertIs(session.agent, agent)

    def test_loader_error_is_not_hidden(self):
        with patch("game.factory.load_puzzle", side_effect=ValueError("Bad puzzle")), \
             patch("game.factory.GameEngine") as engine_class:
            with self.assertRaisesRegex(ValueError, "Bad puzzle"):
                create_session("bad.json")
        engine_class.assert_not_called()

    def test_unfinished_module_does_not_use_fake_backend(self):
        with patch("game.factory.load_puzzle", return_value=object()), \
             patch("game.factory.GameEngine", return_value=SampleEngine()), \
             patch("game.factory.CNFEncoder", side_effect=NotImplementedError("Encoder chua xong")):
            with self.assertRaises(NotImplementedError):
                create_session("test.json")
