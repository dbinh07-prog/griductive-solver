"""Test-only six-core adapter. Never used by game.factory or the shipped GUI.

This independently tests member 1's DPLL/session with the real engine on
six-core puzzles. Production integration tests also cover extension puzzles.
It is not a production fallback.
"""
from itertools import combinations
from time import perf_counter

from contracts.models import CNF, PublicState, Uniqueness
from core.regions import all_cells, referenced_cells
from tests.member1_data import SampleAgent


CORE_CLUE_KINDS = frozenset({"FACT", "SAME", "DIFFERENT", "EXACTLY", "AT_LEAST", "AT_MOST"})


class CoreTestEncoder:
    def encode(self, state):
        primary = tuple((c, i + 1) for i, c in enumerate(all_cells(state.size)))
        mapping = dict(primary)
        clauses = []
        for owner, clue in state.revealed_clues:
            if clue.kind not in CORE_CLUE_KINDS:
                raise ValueError(f"Core test encoder does not support {clue.kind}")
            cells = referenced_cells(clue, state.size)
            variables = tuple(mapping[c] for c in cells)
            if clue.kind == "FACT":
                clauses.append((variables[0] if clue.status else -variables[0],))
            elif clue.kind == "SAME":
                a, b = variables
                clauses.extend(((-a, b), (a, -b)))
            elif clue.kind == "DIFFERENT":
                a, b = variables
                clauses.extend(((a, b), (-a, -b)))
            else:
                if clue.kind in ("AT_MOST", "EXACTLY"):
                    clauses.extend(tuple(-v for v in group) for group in combinations(variables, clue.k + 1))
                if clue.kind in ("AT_LEAST", "EXACTLY"):
                    clauses.extend(tuple(group) for group in combinations(variables, len(variables) - clue.k + 1))
        for cell, value in state.proved_statuses:
            clauses.append((mapping[cell] if value else -mapping[cell],))
        return CNF(tuple(clauses), primary, len(primary))


class CoreTestAgent(SampleAgent):
    def __init__(self):
        super().__init__()
        self.encoder = CoreTestEncoder()

    def check_uniqueness(self, state, *, timeout_s=5.0):
        if state.proved_statuses:
            raise ValueError("Test uniqueness must not receive hidden solution units")
        deadline = perf_counter() + timeout_s
        cnf = self.encoder.encode(state)
        first = self.solver.solve(cnf, timeout_s=deadline - perf_counter())
        if not first.satisfiable:
            return Uniqueness.INCONSISTENT
        model = dict(first.assignment)
        blocking = tuple(-v if model[v] else v for cell, v in cnf.primary_variables)
        second = self.solver.solve(CNF(cnf.clauses + (blocking,), cnf.primary_variables, cnf.variable_count),
                                   timeout_s=deadline - perf_counter())
        return Uniqueness.MULTIPLE if second.satisfiable else Uniqueness.UNIQUE


class ImmediateTestJob:
    def __init__(self, state, agent, timeout_s):
        self.state, self.agent, self.timeout_s = state, agent, timeout_s
        self.result = None

    def start(self):
        self.result = self.agent.analyze(self.state, timeout_s=self.timeout_s)

    def poll(self):
        return self.result

    def cancel(self):
        self.result = None
