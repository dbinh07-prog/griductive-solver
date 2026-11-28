from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import multiprocessing
from multiprocessing.connection import Connection
import os
from pathlib import Path
import platform
import statistics
import sys
import time

from contracts.models import PublicState, SolverTimeout, VerdictResult
from core.game_engine import GameEngine
from core.puzzle_loader import load_puzzle

CSV_COLUMNS: tuple[str, ...] = (
    "case_id",
    "size",
    "configuration",
    "repeat",
    "status",
    "primary_variables",
    "auxiliary_variables",
    "active_clause_peak",
    "complete_clue_clauses",
    "sat_calls",
    "decisions",
    "propagations",
    "backtracks",
    "deduction_steps",
    "play_runtime_ms",
    "total_runtime_ms",
    "uniqueness",
    "error",
)


@dataclass(frozen=True)
class ExperimentConfig:
    suite: str = "puzzles/benchmark"
    output: str = "outputs/experiments"
    timeout_s: float = 10.0
    repeats: int = 3
    configuration: str = "dpll_baseline"
    case_timeout_s: float | None = None
    use_subprocess: bool = True


def _build_pipeline(configuration: str):
    """Instantiate self-implemented encoder, DPLL solver, and logic agent."""
    from algorithms.dpll import DPLLSolver
    from logic.agent import LogicAgent
    from logic.encoder import CNFEncoder

    if configuration == "dpll_baseline":
        encoder = CNFEncoder()
        solver = DPLLSolver()
        return encoder, LogicAgent(encoder, solver)

    raise ValueError(f"Unsupported solver configuration: {configuration!r}")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _discover_cases(suite_path: Path) -> list[Path]:
    if suite_path.is_file():
        return [suite_path]
    if not suite_path.is_dir():
        raise FileNotFoundError(f"Experiment suite path does not exist: {suite_path}")
    cases = sorted(suite_path.rglob("*.json"))
    if not cases:
        raise ValueError(f"No puzzle JSON files found in suite: {suite_path}")
    return cases


def _blank_row(case_id: str, configuration: str, repeat: int) -> dict[str, str]:
    row = {col: "" for col in CSV_COLUMNS}
    row["case_id"] = case_id
    row["configuration"] = configuration
    row["repeat"] = str(repeat)
    return row


def _execute_single_case(
    puzzle_path: str,
    configuration: str,
    repeat: int,
    timeout_s: float,
    case_timeout_s: float,
) -> dict[str, str]:
    path = Path(puzzle_path)
    row = _blank_row(path.stem, configuration, repeat)
    total_start = time.perf_counter()
    case_deadline = total_start + case_timeout_s

    try:
        puzzle = load_puzzle(path)
        row["case_id"] = puzzle.id
        row["size"] = str(puzzle.size)

        encoder, agent = _build_pipeline(configuration)
        engine = GameEngine(puzzle)

        primary_variables: int | None = None
        auxiliary_peak: int | None = None
        active_clause_peak: int | None = None
        sat_calls = 0
        decisions = 0
        propagations = 0
        backtracks = 0
        deduction_steps = 0
        gameplay_status = ""
        gameplay_error = ""

        # Play runtime starts immediately BEFORE the first analyze().
        play_start = time.perf_counter()
        max_steps = puzzle.size * puzzle.size + 1

        try:
            for _ in range(max_steps):
                if engine.is_solved():
                    gameplay_status = "SOLVED"
                    break

                remaining = min(timeout_s, case_deadline - time.perf_counter())
                if remaining <= 0:
                    raise SolverTimeout("Whole-case deadline exceeded during gameplay")

                state = engine.public_state()
                analysis = agent.analyze(state, timeout_s=remaining)

                cnf = analysis.cnf
                primary_count = len(cnf.primary_variables)
                aux_count = cnf.variable_count - primary_count
                clause_count = len(cnf.clauses)

                primary_variables = primary_count
                auxiliary_peak = (
                    aux_count
                    if auxiliary_peak is None
                    else max(auxiliary_peak, aux_count)
                )
                active_clause_peak = (
                    clause_count
                    if active_clause_peak is None
                    else max(active_clause_peak, clause_count)
                )

                # Sum every executed gameplay SAT query once (including consistency query).
                sat_calls += len(analysis.queries)
                for query in analysis.queries:
                    decisions += query.stats.decisions
                    propagations += query.stats.propagations
                    backtracks += query.stats.backtracks

                if analysis.inconsistent:
                    gameplay_status = "INCONSISTENT"
                    break

                forced = agent.next_forced(analysis)
                if forced is None:
                    gameplay_status = "UNKNOWN"
                    break

                cell, verdict = forced
                submit = engine.submit_verdict(cell, verdict, analysis)
                if submit.result is VerdictResult.ACCEPTED:
                    deduction_steps += 1
                    continue

                if submit.result is VerdictResult.INCONSISTENT:
                    gameplay_status = "INCONSISTENT"
                    gameplay_error = f"Engine rejected {cell}={verdict.value}: INCONSISTENT"
                else:
                    gameplay_status = "ERROR"
                    gameplay_error = (
                        f"Unexpected submit outcome for {cell}={verdict.value}: "
                        f"{submit.result.value}"
                    )
                break
            else:
                gameplay_status = "ERROR"
                gameplay_error = "Exceeded maximum board steps without terminating"

        except SolverTimeout as exc:
            play_end = time.perf_counter()
            row["status"] = "TIMEOUT"
            row["play_runtime_ms"] = f"{(play_end - play_start) * 1000.0:.3f}"
            row["total_runtime_ms"] = f"{(play_end - total_start) * 1000.0:.3f}"
            if primary_variables is not None:
                row["primary_variables"] = str(primary_variables)
            if auxiliary_peak is not None:
                row["auxiliary_variables"] = str(auxiliary_peak)
            if active_clause_peak is not None:
                row["active_clause_peak"] = str(active_clause_peak)
            row["error"] = str(exc) or "SolverTimeout"
            return row

        play_end = time.perf_counter()
        row["play_runtime_ms"] = f"{(play_end - play_start) * 1000.0:.3f}"
        row["status"] = gameplay_status
        row["error"] = gameplay_error
        if primary_variables is not None:
            row["primary_variables"] = str(primary_variables)
        if auxiliary_peak is not None:
            row["auxiliary_variables"] = str(auxiliary_peak)
        if active_clause_peak is not None:
            row["active_clause_peak"] = str(active_clause_peak)
        row["sat_calls"] = str(sat_calls)
        row["decisions"] = str(decisions)
        row["propagations"] = str(propagations)
        row["backtracks"] = str(backtracks)
        row["deduction_steps"] = str(deduction_steps)

        # Separate offline phase: complete-clue encoding and uniqueness (zero solution units).
        full_clue_state = PublicState(
            puzzle_id=puzzle.id,
            title=puzzle.title,
            size=puzzle.size,
            characters=puzzle.characters,
            proved_statuses=(),
            revealed_clues=puzzle.clues,
            revision=0,
        )
        full_cnf = encoder.encode(full_clue_state)
        row["complete_clue_clauses"] = str(len(full_cnf.clauses))
        if primary_variables is None:
            row["primary_variables"] = str(len(full_cnf.primary_variables))
        if auxiliary_peak is None:
            row["auxiliary_variables"] = str(
                full_cnf.variable_count - len(full_cnf.primary_variables)
            )

        remaining_offline = min(timeout_s, case_deadline - time.perf_counter())
        if remaining_offline <= 0:
            raise SolverTimeout("Whole-case deadline exceeded before uniqueness check")

        uniqueness = agent.check_uniqueness(
            full_clue_state, timeout_s=remaining_offline
        )
        row["uniqueness"] = uniqueness.value
        row["total_runtime_ms"] = f"{(time.perf_counter() - total_start) * 1000.0:.3f}"
        return row

    except SolverTimeout as exc:
        row["status"] = "TIMEOUT"
        row["total_runtime_ms"] = f"{(time.perf_counter() - total_start) * 1000.0:.3f}"
        row["error"] = str(exc) or "SolverTimeout"
        return row

    except Exception as exc:
        row["status"] = "ERROR"
        row["total_runtime_ms"] = f"{(time.perf_counter() - total_start) * 1000.0:.3f}"
        row["error"] = f"{type(exc).__name__}: {exc}"
        return row


def _worker_entry(
    conn: Connection,
    puzzle_path: str,
    configuration: str,
    repeat: int,
    timeout_s: float,
    case_timeout_s: float,
) -> None:
    try:
        row = _execute_single_case(
            puzzle_path, configuration, repeat, timeout_s, case_timeout_s
        )
        conn.send(row)
    except Exception as exc:
        fallback = _blank_row(Path(puzzle_path).stem, configuration, repeat)
        fallback["status"] = "ERROR"
        fallback["error"] = f"{type(exc).__name__}: {exc}"
        try:
            conn.send(fallback)
        except OSError:
            pass
    finally:
        conn.close()


def _run_case_isolated(
    puzzle_path: Path,
    configuration: str,
    repeat: int,
    timeout_s: float,
    case_timeout_s: float,
) -> dict[str, str]:
    ctx = multiprocessing.get_context("spawn")
    parent_conn, child_conn = ctx.Pipe(duplex=False)
    proc = ctx.Process(
        target=_worker_entry,
        args=(
            child_conn,
            str(puzzle_path),
            configuration,
            repeat,
            timeout_s,
            case_timeout_s,
        ),
    )
    wall_start = time.perf_counter()
    proc.start()
    child_conn.close()

    # Drain result from pipe BEFORE calling proc.join() to prevent pipe buffer deadlock.
    grace_s = max(case_timeout_s + 2.0, timeout_s + 2.0)
    row: dict[str, str] | None = None
    timed_out = False

    try:
        if parent_conn.poll(grace_s):
            try:
                row = parent_conn.recv()
            except EOFError:
                row = None
        else:
            timed_out = True
    finally:
        parent_conn.close()

    if timed_out:
        proc.terminate()
        proc.join(timeout=2.0)
        if proc.is_alive():
            proc.kill()
            proc.join(timeout=2.0)
        elapsed_ms = (time.perf_counter() - wall_start) * 1000.0
        timeout_row = _blank_row(puzzle_path.stem, configuration, repeat)
        timeout_row["status"] = "TIMEOUT"
        timeout_row["total_runtime_ms"] = f"{elapsed_ms:.3f}"
        timeout_row["error"] = f"Hard subprocess timeout exceeded ({case_timeout_s:.2f}s)"
        return timeout_row

    proc.join(timeout=2.0)
    if proc.is_alive():
        proc.terminate()
        proc.join(timeout=2.0)

    if row is not None:
        return row

    elapsed_ms = (time.perf_counter() - wall_start) * 1000.0
    err_row = _blank_row(puzzle_path.stem, configuration, repeat)
    err_row["status"] = "ERROR"
    err_row["total_runtime_ms"] = f"{elapsed_ms:.3f}"
    err_row["error"] = f"Worker exited without result (exitcode={proc.exitcode})"
    return err_row


def _build_summary(rows: list[dict[str, str]]) -> dict[str, object]:
    groups: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        key = f"{row['configuration']}|size={row['size'] or 'unknown'}"
        groups.setdefault(key, []).append(row)

    summary_groups: dict[str, object] = {}
    for key, group_rows in sorted(groups.items()):
        status_counts: dict[str, int] = {}
        for r in group_rows:
            st = r["status"]
            status_counts[st] = status_counts.get(st, 0) + 1

        solved = [r for r in group_rows if r["status"] == "SOLVED"]

        def _metric_stats(col: str) -> dict[str, float] | None:
            vals = [float(r[col]) for r in solved if r[col] != ""]
            if not vals:
                return None
            return {
                "mean": round(statistics.mean(vals), 3),
                "median": round(statistics.median(vals), 3),
                "max": round(max(vals), 3),
            }

        summary_groups[key] = {
            "total_runs": len(group_rows),
            "status_counts": status_counts,
            "solved_play_runtime_ms": _metric_stats("play_runtime_ms"),
            "solved_sat_calls": _metric_stats("sat_calls"),
            "solved_decisions": _metric_stats("decisions"),
            "solved_propagations": _metric_stats("propagations"),
            "solved_backtracks": _metric_stats("backtracks"),
            "solved_deduction_steps": _metric_stats("deduction_steps"),
        }
    return {"total_rows": len(rows), "groups": summary_groups}


def run_experiments(config: ExperimentConfig) -> None:
    """Member 3: identical case set, retained error/timeout rows, actual metrics."""
    if isinstance(config.timeout_s, bool) or config.timeout_s <= 0:
        raise ValueError(f"timeout_s must be positive, got {config.timeout_s!r}")
    if isinstance(config.repeats, bool) or not isinstance(config.repeats, int) or config.repeats < 1:
        raise ValueError(f"repeats must be a positive int, got {config.repeats!r}")

    case_timeout_s = (
        config.case_timeout_s
        if config.case_timeout_s is not None
        else max(config.timeout_s * 5.0, 30.0)
    )
    if isinstance(case_timeout_s, bool) or case_timeout_s <= 0:
        raise ValueError(f"case_timeout_s must be positive, got {case_timeout_s!r}")

    suite_path = Path(config.suite)
    output_dir = Path(config.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    case_files = _discover_cases(suite_path)

    manifest = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "suite": str(suite_path),
        "configuration": config.configuration,
        "timeout_s": config.timeout_s,
        "case_timeout_s": case_timeout_s,
        "repeats": config.repeats,
        "use_subprocess": config.use_subprocess,
        "cases": [
            {
                "file": str(p.relative_to(suite_path)) if suite_path.is_dir() else p.name,
                "sha256": _sha256_file(p),
            }
            for p in case_files
        ],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    rows: list[dict[str, str]] = []
    for case_path in case_files:
        for repeat in range(1, config.repeats + 1):
            if config.use_subprocess:
                row = _run_case_isolated(
                    case_path,
                    config.configuration,
                    repeat,
                    config.timeout_s,
                    case_timeout_s,
                )
            else:
                row = _execute_single_case(
                    str(case_path),
                    config.configuration,
                    repeat,
                    config.timeout_s,
                    case_timeout_s,
                )
            rows.append(row)

    csv_path = output_dir / "results.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(CSV_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)

    summary = _build_summary(rows)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )