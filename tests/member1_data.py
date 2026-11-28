"""Du lieu gia chi dung trong test; khong thay module cua nguoi 2/3."""
from dataclasses import replace
from os import _exit
from time import sleep

from algorithms.dpll import DPLLSolver
from contracts.models import (
    Analysis, Character, Clue, CNF, PublicState, SATQuery, SolverStats,
    Status, SubmitResult, VerdictResult,
)


class SampleEngine:
    def __init__(self, mode="chain", puzzle_id="test_case"):
        self._puzzle_id = puzzle_id
        self._characters = (
            Character("A1", "Ada", "Architect"), Character("B1", "Bao", "Baker"),
            Character("A2", "Chi", "Doctor"), Character("B2", "Duy", "Designer"),
        )
        self._solution = {"A1": True, "B1": False, "A2": True, "B2": False}
        self._clues = {
            "A1": Clue("C01", "FACT", ("B1",), False),
            "B1": Clue("C02", "FACT", ("A2",), True),
            "A2": Clue("C03", "FACT", ("B2",), False),
            "B2": Clue("C04", "FACT", ("A1",), True),
        }
        if mode == "unknown":
            self._clues["A1"] = Clue("C01", "FACT", ("A1",), True)
        elif mode == "inconsistent":
            self._clues["A1"] = Clue("C01", "FACT", ("A1",), False)
        self._revision = 0
        self.submit_calls = 0
        self.restart()

    def public_state(self):
        cells = [p.cell for p in self._characters if p.cell in self._opened]
        return PublicState(
            self._puzzle_id, "Test case", 2, self._characters,
            tuple((c, self._solution[c]) for c in cells),
            tuple((c, self._clues[c]) for c in cells), self._revision,
        )

    def restart(self):
        self._opened = {"A1"}
        self._revision += 1
        return self.public_state()

    def is_solved(self):
        return len(self._opened) == len(self._characters)

    def submit_verdict(self, cell, proposed, analysis):
        self.submit_calls += 1
        state = self.public_state()
        if analysis.puzzle_id != state.puzzle_id or analysis.revision != state.revision:
            raise ValueError("Analysis cu")
        forced = dict(analysis.classifications)[cell]
        if analysis.inconsistent:
            return SubmitResult(VerdictResult.INCONSISTENT, state)
        if forced == Status.UNKNOWN:
            return SubmitResult(VerdictResult.NOT_PROVABLE, state)
        if forced != proposed:
            return SubmitResult(VerdictResult.CONTRADICTED, state)
        if self._solution[cell] != (proposed == Status.CRIMINAL):
            return SubmitResult(VerdictResult.INCONSISTENT, state)
        self._opened.add(cell)
        self._revision += 1
        return SubmitResult(VerdictResult.ACCEPTED, self.public_state(), self._clues[cell])


class SampleEncoder:
    """Chi ho tro FACT de test ghep DPLL; khong phai encoder nop bai."""
    def encode(self, state):
        primary = tuple((p.cell, i + 1) for i, p in enumerate(state.characters))
        mapping = dict(primary)
        clauses = []
        for owner, clue in state.revealed_clues:
            if clue.kind != "FACT":
                raise ValueError("Test fixture chi ho tro FACT")
            variable = mapping[clue.cells[0]]
            clauses.append((variable if clue.status else -variable,))
        for cell, value in state.proved_statuses:
            variable = mapping[cell]
            clauses.append((variable if value else -variable,))
        return CNF(tuple(clauses), primary, len(primary))


class SampleAgent:
    """Agent toi thieu trong test; nguoi 2 van tu lam LogicAgent that."""
    def __init__(self):
        self.encoder = SampleEncoder()
        self.solver = DPLLSolver()
        self.analyze_calls = 0
        self.seen_states = []

    def analyze(self, state, *, timeout_s=5.0):
        self.analyze_calls += 1
        self.seen_states.append(state)
        cnf = self.encoder.encode(state)
        base = self.solver.solve(cnf, timeout_s=timeout_s)
        queries = [SATQuery((), base.satisfiable, base.stats)]
        labels = []
        if base.satisfiable:
            known = dict(state.proved_statuses)
            for cell, variable in cnf.primary_variables:
                if cell in known:
                    continue
                innocent = self.solver.solve(cnf, (-variable,), timeout_s=timeout_s)
                criminal = self.solver.solve(cnf, (variable,), timeout_s=timeout_s)
                queries.append(SATQuery((-variable,), innocent.satisfiable, innocent.stats))
                queries.append(SATQuery((variable,), criminal.satisfiable, criminal.stats))
                status = Status.UNKNOWN
                if not innocent.satisfiable:
                    status = Status.CRIMINAL
                elif not criminal.satisfiable:
                    status = Status.INNOCENT
                labels.append((cell, status))
        return Analysis(state.puzzle_id, state.revision, tuple(labels), not base.satisfiable, cnf, tuple(queries))

    def next_forced(self, analysis):
        for cell, status in analysis.classifications:
            if status != Status.UNKNOWN:
                return cell, status
        return None


class SlowAgent(SampleAgent):
    def __init__(self, delay=0.3):
        super().__init__()
        self.delay = delay

    def analyze(self, state, *, timeout_s=5.0):
        sleep(self.delay)
        return super().analyze(state, timeout_s=timeout_s)


class ErrorAgent(SampleAgent):
    def analyze(self, state, *, timeout_s=5.0):
        raise ValueError("Loi agent trong test")


class WrongStateAgent(SampleAgent):
    def analyze(self, state, *, timeout_s=5.0):
        return replace(super().analyze(state, timeout_s=timeout_s), puzzle_id="other_case")


class ExitAgent(SampleAgent):
    def analyze(self, state, *, timeout_s=5.0):
        _exit(7)


class LargeResultAgent(SampleAgent):
    def analyze(self, state, *, timeout_s=5.0):
        result = super().analyze(state, timeout_s=timeout_s)
        queries = []
        for i in range(4000):
            queries.append(SATQuery((), True, SolverStats(runtime_ms=i / 1000)))
        return replace(result, queries=tuple(queries))
