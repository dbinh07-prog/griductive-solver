import csv
import json
from dataclasses import asdict
from math import isfinite
from pathlib import Path
from time import perf_counter

from contracts.models import Analysis, PublicState, SessionMetrics, Status, SubmitResult, TraceEntry
from contracts.models import CNF, VerdictResult, SolverTimeout
from contracts.ports import Agent
from core.game_engine import GameEngine
from game.worker import AnalysisJob


class GameSession:
    """Noi engine va agent; chi xu ly public state o phia suy luan."""

    def __init__(self, engine: GameEngine, agent: Agent):
        self.engine = engine
        self.agent = agent
        self.trace: list[TraceEntry] = []
        self._analysis = None
        self._analysis_state = None
        self._job = None
        self._job_state = None
        self._sat_calls = 0
        self._decisions = 0
        self._propagations = 0
        self._backtracks = 0
        self._sat_runtime_ms = 0.0

    def public_state(self) -> PublicState:
        state = self.engine.public_state()
        if not isinstance(state, PublicState):
            raise ValueError("Engine phai tra ve PublicState")
        return state

    def analyze(self, *, timeout_s: float = 5.0) -> Analysis:
        self._check_timeout(timeout_s)
        state = self.public_state()
        if self._has_analysis(state):
            return self._analysis

        self.cancel_analysis()
        deadline = perf_counter() + timeout_s
        analysis = self.agent.analyze(state, timeout_s=timeout_s)
        if perf_counter() >= deadline:
            raise SolverTimeout("Da het thoi gian phan tich")
        self._save_analysis(state, analysis)
        return analysis

    def hint(self) -> tuple[str, Status] | None:
        if self.engine.is_solved():
            return None
        analysis = self.analyze()
        if analysis.inconsistent:
            return None
        move = self.agent.next_forced(analysis)
        self._check_move(move, analysis)
        return move

    def submit(self, cell: str, proposed: Status) -> SubmitResult:
        state = self.public_state()
        cells = {character.cell for character in state.characters}
        if type(cell) is not str or cell not in cells:
            raise ValueError("Cell khong ton tai")
        if not isinstance(proposed, Status) or proposed == Status.UNKNOWN:
            raise ValueError("Verdict phai la Status.CRIMINAL hoac Status.INNOCENT")
        if cell in dict(state.proved_statuses):
            return SubmitResult(VerdictResult.ALREADY_REVEALED, state)

        analysis = self.analyze()
        if state != self.public_state():
            raise ValueError("Public state da thay doi, can phan tich lai")
        if analysis.inconsistent:
            return SubmitResult(VerdictResult.INCONSISTENT, state)
        forced = dict(analysis.classifications)[cell]
        if forced == Status.UNKNOWN:
            return SubmitResult(VerdictResult.NOT_PROVABLE, state)
        if forced != proposed:
            return SubmitResult(VerdictResult.CONTRADICTED, state)
        result = self.engine.submit_verdict(cell, proposed, analysis)
        self._check_submit_result(state, cell, proposed, result)

        if result.result == VerdictResult.ACCEPTED:
            entry = TraceEntry(
                step=len(self.trace) + 1,
                revision=state.revision,
                active_clue_ids=tuple(clue.id for owner, clue in state.revealed_clues),
                cell=cell,
                verdict=proposed,
                sat_queries=analysis.queries,
                revealed_clue_id=result.revealed_clue.id,
            )
            self.trace.append(entry)
            self._analysis = None
            self._analysis_state = None
            self.cancel_analysis()
        return result

    def step(self) -> SubmitResult | None:
        move = self.hint()
        if move is None:
            return None
        cell, proposed = move
        return self.submit(cell, proposed)

    def restart(self) -> PublicState:
        before = self.public_state()
        self.cancel_analysis()
        state = self.engine.restart()
        if not isinstance(state, PublicState) or state != self.public_state():
            raise ValueError("Engine.restart phai tra ve public state moi")
        if state.puzzle_id != before.puzzle_id or state.revision <= before.revision:
            raise ValueError("Restart phai giu puzzle_id va tang revision")

        self.trace.clear()
        self._analysis = None
        self._analysis_state = None
        self._sat_calls = 0
        self._decisions = 0
        self._propagations = 0
        self._backtracks = 0
        self._sat_runtime_ms = 0.0
        return state

    def export_trace(self, path: str) -> None:
        output = Path(path)
        if output.suffix.lower() not in (".json", ".csv"):
            raise ValueError("Trace chi ho tro file .json hoac .csv")
        rows = []
        for entry in self.trace:
            row = asdict(entry)
            row["verdict"] = entry.verdict.value
            rows.append(row)

        if output.suffix.lower() == ".json":
            data = {
                "schema_version": 1,
                "puzzle_id": self.public_state().puzzle_id,
                "metrics": asdict(self.metrics()),
                "steps": rows,
            }
            with output.open("w", encoding="utf-8") as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        else:
            fields = ("step", "revision", "active_clue_ids", "cell", "verdict",
                      "sat_queries", "revealed_clue_id")
            with output.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                for row in rows:
                    row["active_clue_ids"] = json.dumps(row["active_clue_ids"], ensure_ascii=False)
                    row["sat_queries"] = json.dumps(row["sat_queries"], ensure_ascii=False, allow_nan=False)
                    writer.writerow(row)

    def metrics(self) -> SessionMetrics:
        state = self.public_state()
        auxiliary_variables = None
        active_clauses = None
        if self._has_analysis(state):
            cnf = self._analysis.cnf
            auxiliary_variables = cnf.variable_count - len(cnf.primary_variables)
            active_clauses = len(cnf.clauses)
        return SessionMetrics(
            primary_variables=len(state.characters),
            auxiliary_variables=auxiliary_variables,
            active_clauses=active_clauses,
            sat_calls=self._sat_calls,
            decisions=self._decisions,
            propagations=self._propagations,
            backtracks=self._backtracks,
            deduction_steps=len(self.trace),
            sat_runtime_ms=self._sat_runtime_ms,
        )

    def start_analysis(self, *, timeout_s: float = 5.0) -> AnalysisJob | None:
        self._check_timeout(timeout_s)
        state = self.public_state()
        if self._has_analysis(state):
            return None
        if self._job is not None and self._job_state == state:
            return self._job

        self.cancel_analysis()
        job = AnalysisJob(state, self.agent, timeout_s)
        job.start()
        self._job = job
        self._job_state = state
        return job

    def poll_analysis(self) -> Analysis | None:
        state = self.public_state()
        if self._job is None:
            return self._analysis if self._has_analysis(state) else None
        if self._job_state != state:
            self.cancel_analysis()
            return None

        try:
            analysis = self._job.poll()
        except Exception:
            self.cancel_analysis()
            raise
        if analysis is None:
            return None

        job_state = self._job_state
        self.cancel_analysis()
        self._save_analysis(job_state, analysis)
        return analysis

    def cancel_analysis(self) -> None:
        if self._job is not None:
            self._job.cancel()
        self._job = None
        self._job_state = None

    def accept_analysis(self, analysis: Analysis) -> Analysis:
        """Nhan ket qua tu worker do controller quan ly, khong chay SAT lai."""
        state = self.public_state()
        if self._has_analysis(state) and self._analysis is analysis:
            return analysis
        self._save_analysis(state, analysis)
        self.cancel_analysis()
        return analysis

    def _check_timeout(self, timeout_s):
        if type(timeout_s) not in (int, float) or not isfinite(timeout_s):
            raise ValueError("timeout_s phai la so huu han")
        if timeout_s <= 0:
            raise SolverTimeout("Da het thoi gian phan tich")

    def _has_analysis(self, state):
        return self._analysis is not None and self._analysis_state == state

    def _save_analysis(self, state, analysis):
        if state != self.public_state():
            raise ValueError("Ket qua phan tich da cu")
        self._check_analysis(state, analysis)
        self._analysis = analysis
        self._analysis_state = state
        for query in analysis.queries:
            self._sat_calls += 1
            self._decisions += query.stats.decisions
            self._propagations += query.stats.propagations
            self._backtracks += query.stats.backtracks
            self._sat_runtime_ms += query.stats.runtime_ms

    def _check_analysis(self, state, analysis):
        if not isinstance(analysis, Analysis):
            raise ValueError("Agent phai tra ve Analysis")
        if analysis.puzzle_id != state.puzzle_id or analysis.revision != state.revision:
            raise ValueError("Analysis khong khop puzzle_id hoac revision")
        if type(analysis.inconsistent) is not bool:
            raise ValueError("inconsistent phai la bool")
        if not isinstance(analysis.cnf, CNF):
            raise ValueError("Analysis phai co CNF")
        expected_mapping = tuple((person.cell, i + 1) for i, person in enumerate(state.characters))
        if analysis.cnf.primary_variables != expected_mapping:
            raise ValueError("Primary mapping phai khop board theo row-major")
        if type(analysis.cnf.variable_count) is not int or analysis.cnf.variable_count < len(expected_mapping):
            raise ValueError("Tong so bien khong duoc nho hon so primary variables")
        if type(analysis.queries) is not tuple or type(analysis.classifications) is not tuple:
            raise ValueError("Queries va classifications phai la tuple")
        if len(analysis.queries) == 0 or analysis.queries[0].assumptions != ():
            raise ValueError("Analysis phai co consistency query dau tien")
        if analysis.queries[0].satisfiable == analysis.inconsistent:
            raise ValueError("Consistency query khong khop inconsistent")

        if analysis.inconsistent:
            if len(analysis.classifications) != 0:
                raise ValueError("KB mau thuan khong duoc co verdict")
        else:
            known = dict(state.proved_statuses)
            expected = [person.cell for person in state.characters if person.cell not in known]
            actual = [cell for cell, status in analysis.classifications]
            if actual != expected:
                raise ValueError("Can phan loai du unresolved cells theo row-major")
            for cell, status in analysis.classifications:
                if not isinstance(status, Status):
                    raise ValueError("Classification phai la Status")

        for query in analysis.queries:
            if type(query.satisfiable) is not bool:
                raise ValueError("Ket qua SAT query phai la bool")
            for value in (query.stats.decisions, query.stats.propagations, query.stats.backtracks):
                if type(value) is not int or value < 0:
                    raise ValueError("SAT counter phai la so nguyen khong am")
            runtime = query.stats.runtime_ms
            if type(runtime) not in (int, float) or not isfinite(runtime) or runtime < 0:
                raise ValueError("SAT runtime khong hop le")

    def _check_move(self, move, analysis):
        if move is None:
            return
        if type(move) is not tuple or len(move) != 2:
            raise ValueError("Forced move phai la cap (cell, Status)")
        cell, proposed = move
        if not isinstance(proposed, Status) or proposed == Status.UNKNOWN:
            raise ValueError("Agent khong duoc doan verdict UNKNOWN")
        if dict(analysis.classifications).get(cell) != proposed:
            raise ValueError("Move khong nam trong cac verdict da chung minh")

    def _check_submit_result(self, before, cell, proposed, result):
        if not isinstance(result, SubmitResult) or not isinstance(result.result, VerdictResult):
            raise ValueError("Engine phai tra ve SubmitResult hop le")
        after = self.public_state()
        if result.new_public_state != after:
            raise ValueError("SubmitResult khong khop state cua engine")
        if result.result != VerdictResult.ACCEPTED:
            if before != after or result.revealed_clue is not None:
                raise ValueError("Verdict bi tu choi khong duoc sua state hay reveal clue")
            return

        if after.puzzle_id != before.puzzle_id or after.revision <= before.revision:
            raise ValueError("Reveal phai giu puzzle_id va tang revision")
        if result.revealed_clue is None:
            raise ValueError("ACCEPTED phai tra ve clue moi")
        expected_statuses = dict(before.proved_statuses)
        expected_statuses[cell] = proposed == Status.CRIMINAL
        expected_clues = dict(before.revealed_clues)
        expected_clues[cell] = result.revealed_clue
        if dict(after.proved_statuses) != expected_statuses or dict(after.revealed_clues) != expected_clues:
            raise ValueError("Moi submit chi duoc reveal dung mot card")
        if after.characters != before.characters or after.size != before.size or after.title != before.title:
            raise ValueError("Reveal khong duoc thay doi thong tin puzzle")
