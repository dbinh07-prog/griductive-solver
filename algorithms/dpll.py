from contracts.models import CNF, SATResult


class DPLLSolver:
    """Member 1: unit propagation, conflict detection, branching and backtracking."""

    def solve(self, cnf: CNF, assumptions: tuple[int, ...] = (), *, timeout_s: float = 5.0) -> SATResult:
        raise NotImplementedError("Member 1: implement DPLL; docs/members/01-leader.md")
