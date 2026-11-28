from math import isfinite
from time import perf_counter

from contracts.models import CNF, SATResult, SolverStats, SolverTimeout


class DPLLSolver:
    """DPLL: chon bien nho nhat, thu False truoc True."""

    def solve(self, cnf: CNF, assumptions: tuple[int, ...] = (), *, timeout_s: float = 5.0) -> SATResult:
        started = perf_counter()
        self._check_timeout(timeout_s)
        deadline = started + timeout_s
        self._check_cnf(cnf, assumptions, deadline)
        clauses = self._prepare_clauses(cnf.clauses, assumptions, deadline)
        counts = {"decisions": 0, "propagations": 0, "backtracks": 0}
        assignment = self._search(clauses, {}, counts, deadline)

        model = []
        if assignment is not None:
            for variable in range(1, cnf.variable_count + 1):
                self._check_deadline(deadline)
                model.append((variable, assignment.get(variable, False)))

        self._check_deadline(deadline)
        stats = SolverStats(
            decisions=counts["decisions"],
            propagations=counts["propagations"],
            backtracks=counts["backtracks"],
            runtime_ms=(perf_counter() - started) * 1000,
        )
        return SATResult(assignment is not None, tuple(model), stats)

    def _check_timeout(self, timeout_s):
        if type(timeout_s) not in (int, float) or not isfinite(timeout_s):
            raise ValueError("timeout_s phai la so huu han")
        if timeout_s <= 0:
            raise SolverTimeout("Da het thoi gian giai SAT")

    def _check_deadline(self, deadline):
        if perf_counter() >= deadline:
            raise SolverTimeout("Da het thoi gian giai SAT")

    def _check_cnf(self, cnf, assumptions, deadline):
        if not isinstance(cnf, CNF):
            raise ValueError("cnf phai la CNF")
        if type(cnf.variable_count) is not int or cnf.variable_count < 0:
            raise ValueError("variable_count phai la so nguyen khong am")
        if type(cnf.clauses) is not tuple or type(assumptions) is not tuple:
            raise ValueError("clauses va assumptions phai la tuple")

        for clause in cnf.clauses:
            self._check_deadline(deadline)
            if type(clause) is not tuple:
                raise ValueError("Moi clause phai la tuple")
            for literal in clause:
                self._check_literal(literal, cnf.variable_count)
                self._check_deadline(deadline)
        for literal in assumptions:
            self._check_literal(literal, cnf.variable_count)
            self._check_deadline(deadline)

        if type(cnf.primary_variables) is not tuple:
            raise ValueError("primary_variables phai la tuple")
        cells = set()
        variables = set()
        for entry in cnf.primary_variables:
            self._check_deadline(deadline)
            if type(entry) is not tuple or len(entry) != 2:
                raise ValueError("Mapping phai gom cac cap (cell, variable)")
            cell, variable = entry
            if type(cell) is not str or not cell or cell in cells:
                raise ValueError("Cell trong mapping khong hop le hoac bi trung")
            self._check_literal(variable, cnf.variable_count)
            if variable < 0 or variable in variables:
                raise ValueError("Primary variable phai duong va khong trung")
            cells.add(cell)
            variables.add(variable)

    def _check_literal(self, literal, variable_count):
        if type(literal) is not int or literal == 0 or abs(literal) > variable_count:
            raise ValueError("Literal phai khac 0 va nam trong variable_count")

    def _literal_order(self, literal):
        return abs(literal), literal

    def _prepare_clauses(self, clauses, assumptions, deadline):
        result = []
        for clause in clauses:
            self._check_deadline(deadline)
            literals = set(clause)
            tautology = False
            for literal in literals:
                self._check_deadline(deadline)
                if -literal in literals:
                    tautology = True
                    break
            if not tautology:
                result.append(tuple(sorted(literals, key=self._literal_order)))

        for literal in assumptions:
            self._check_deadline(deadline)
            result.append((literal,))
        return tuple(result)

    def _reduce(self, clauses, assignment, deadline):
        result = []
        for clause in clauses:
            self._check_deadline(deadline)
            remaining = []
            satisfied = False
            for literal in clause:
                self._check_deadline(deadline)
                variable = abs(literal)
                if variable not in assignment:
                    remaining.append(literal)
                elif assignment[variable] == (literal > 0):
                    satisfied = True
                    break
            if satisfied:
                continue
            if len(remaining) == 0:
                return None
            result.append(tuple(remaining))
        return tuple(result)

    def _propagate(self, clauses, assignment, counts, deadline):
        while True:
            self._check_deadline(deadline)
            clauses = self._reduce(clauses, assignment, deadline)
            if clauses is None:
                return None

            units = set()
            for clause in clauses:
                if len(clause) == 1:
                    units.add(clause[0])
            if len(units) == 0:
                return clauses

            for literal in sorted(units, key=self._literal_order):
                self._check_deadline(deadline)
                variable = abs(literal)
                value = literal > 0
                if variable in assignment:
                    if assignment[variable] != value:
                        return None
                else:
                    assignment[variable] = value
                    counts["propagations"] += 1

    def _search(self, clauses, assignment, counts, deadline):
        clauses = self._propagate(clauses, assignment, counts, deadline)
        if clauses is None:
            return None
        if len(clauses) == 0:
            return assignment

        variable = None
        for clause in clauses:
            self._check_deadline(deadline)
            for literal in clause:
                candidate = abs(literal)
                if variable is None or candidate < variable:
                    variable = candidate

        counts["decisions"] += 1
        for value in (False, True):
            self._check_deadline(deadline)
            branch = assignment.copy()
            branch[variable] = value
            result = self._search(clauses, branch, counts, deadline)
            if result is not None:
                return result
            counts["backtracks"] += 1
        return None
