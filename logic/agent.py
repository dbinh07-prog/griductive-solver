from contracts.models import Analysis, PublicState, Status, Uniqueness, SATQuery, SolverStats, SolverTimeout, CNF
from contracts.ports import Encoder, Solver
import time

class LogicAgent:
    def __init__(self, encoder: Encoder, solver: Solver):
        self.encoder = encoder
        self.solver = solver

    def analyze(self, public_state: PublicState, *, timeout_s: float | int = 5.0) -> Analysis:
        if not isinstance(public_state, PublicState):
            raise ValueError("Public State cannot be processed as wrong datatype")
        
        if not isinstance(timeout_s, (float, int)) or isinstance(timeout_s, bool) or timeout_s <= 0:
            raise ValueError("Timeout must be a positive float or int")
        
        deadline = time.monotonic() + float(timeout_s)

        current_cnf = self.encoder.encode(public_state)     # CNF at that time. 

        def remaining_timeout() -> float:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise SolverTimeout("Timeout")
            return remaining
        
        base_result = self.solver.solve(current_cnf, assumptions = (), timeout_s = remaining_timeout())
        base_query = SATQuery(
            assumptions = (),
            satisfiable = base_result.satisfiable,
            stats = base_result.stats
        )


        if not base_result.satisfiable:
            return Analysis(
                puzzle_id = public_state.puzzle_id,
                revision = public_state.revision,
                classifications = (),
                inconsistent = True,
                cnf = current_cnf, 
                queries = (base_query,)
            )


        all_queries: list[SATQuery] = [base_query]
        classifications: list[tuple[str, Status]] = []
        proved_cells = {cell for cell, _ in public_state.proved_statuses}

        for cell, variable in current_cnf.primary_variables:
            if cell in proved_cells:
                continue 
            criminal_result = self.solver.solve(
                current_cnf, assumptions = (variable,), timeout_s = remaining_timeout()
            )
            all_queries.append(
                SATQuery(
                    assumptions = (variable,),
                    satisfiable = criminal_result.satisfiable,
                    stats = criminal_result.stats
                )
            )

            innocent_result = self.solver.solve(current_cnf, assumptions = (-variable,), timeout_s = remaining_timeout())
            all_queries.append(
                SATQuery(
                    assumptions = (-variable,),
                    satisfiable = innocent_result.satisfiable,
                    stats = innocent_result.stats,
                )
            )

            if criminal_result.satisfiable and innocent_result.satisfiable:
                status = Status.UNKNOWN
            elif criminal_result.satisfiable and not innocent_result.satisfiable:
                status = Status.CRIMINAL
            
            elif not criminal_result.satisfiable and innocent_result.satisfiable:
                status = Status.INNOCENT
            
            else:
                raise ValueError(f"Both assumptions are UNSAT for cell {cell}")
            
            
            classifications.append((cell, status))

        return Analysis(
            puzzle_id = public_state.puzzle_id,
            revision = public_state.revision,
            classifications = tuple(classifications),
            inconsistent = False, 
            cnf = current_cnf,
            queries = tuple(all_queries)
        )



    def next_forced(self, analysis: Analysis) -> tuple[str, Status] | None:
        """If inconsistent -> Return None as contradictions"""
        if analysis.inconsistent is True:
            return None
        else:
            for cell, status in analysis.classifications:
                if status in (Status.CRIMINAL, Status.INNOCENT):
                    return (cell, status)
            return None


        

    def check_uniqueness(self, full_clue_state: PublicState, *, timeout_s: float = 5.0) -> Uniqueness:

        if not isinstance(full_clue_state, PublicState):
            raise ValueError("Full clue state must be a PublicState Datatype")
        if not isinstance(timeout_s, float) or timeout_s <= 0:
            raise ValueError("Timeout_s must be a positive float")
        
        deadline = time.monotonic() + float(timeout_s)
        cnf = self.encoder.encode(full_clue_state)

        remaining = deadline - time.monotonic()

        if remaining <= 0:
            raise SolverTimeout("Timeout")
        
        first = self.solver.solve(cnf, assumptions = (), timeout_s = remaining)
        if not first.satisfiable:
            return Uniqueness.INCONSISTENT
        assignment_map = dict(first.assignment)
        blocking_clause = tuple(
            -item if assignment_map[item] else item
            for _, item in cnf.primary_variables
        )
        blocked_cnf = CNF(
            clauses = cnf.clauses + (blocking_clause,),
            primary_variables = cnf.primary_variables,
            variable_count = cnf.variable_count
        )


        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise SolverTimeout("Timeout")
        second = self.solver.solve(blocked_cnf, assumptions = (), timeout_s = remaining)

        return Uniqueness.MULTIPLE if second.satisfiable else Uniqueness.UNIQUE
    
