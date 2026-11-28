from dataclasses import dataclass
from enum import Enum


class Status(str, Enum):
    CRIMINAL = "CRIMINAL"
    INNOCENT = "INNOCENT"
    UNKNOWN = "UNKNOWN"


class VerdictResult(str, Enum):
    ACCEPTED = "ACCEPTED"
    NOT_PROVABLE = "NOT_PROVABLE"
    CONTRADICTED = "CONTRADICTED"
    INCONSISTENT = "INCONSISTENT"
    ALREADY_REVEALED = "ALREADY_REVEALED"


class Uniqueness(str, Enum):
    UNIQUE = "UNIQUE"
    MULTIPLE = "MULTIPLE"
    INCONSISTENT = "INCONSISTENT"


class SolverTimeout(TimeoutError):
    """Timeout is not UNSAT and must never justify a verdict."""


@dataclass(frozen=True)
class Character:
    cell: str
    name: str
    profession: str


@dataclass(frozen=True)
class Region:
    kind: str  # ROW / COLUMN / NEIGHBORS / EXPLICIT
    index: int = 0  # ROW/COLUMN: one-based
    anchor: str = ""  # NEIGHBORS
    cells: tuple[str, ...] = ()  # EXPLICIT: distinct valid cells


@dataclass(frozen=True)
class Clue:
    id: str
    kind: str  # Six core templates; member 2 selects and specifies extensions later.
    cells: tuple[str, ...] = ()  # FACT: 1; binary templates: 2
    status: bool = True  # FACT: True = Criminal
    region: Region | None = None  # core counting clues
    k: int = 0  # core count; extension-specific fields are not frozen yet


@dataclass(frozen=True)
class PublicState:
    puzzle_id: str
    title: str
    size: int
    characters: tuple[Character, ...]  # row-major; names alphabetical
    proved_statuses: tuple[tuple[str, bool], ...] = ()
    revealed_clues: tuple[tuple[str, Clue], ...] = ()  # (owner, clue)
    revision: int = 0


@dataclass(frozen=True)
class Puzzle:
    """Private data: only loader/validator/GameEngine may receive this object."""
    id: str
    title: str
    size: int
    characters: tuple[Character, ...]
    solution: tuple[tuple[str, bool], ...]
    clues: tuple[tuple[str, Clue], ...]
    initially_revealed: tuple[str, ...]


@dataclass(frozen=True)
class CNF:
    clauses: tuple[tuple[int, ...], ...]
    primary_variables: tuple[tuple[str, int], ...]  # row-major IDs 1..N*N
    variable_count: int  # all primary and auxiliary variables


@dataclass(frozen=True)
class SolverStats:
    decisions: int = 0
    propagations: int = 0
    backtracks: int = 0
    runtime_ms: float = 0.0


@dataclass(frozen=True)
class SATResult:
    satisfiable: bool
    assignment: tuple[tuple[int, bool], ...]  # SAT: complete; UNSAT: empty
    stats: SolverStats


@dataclass(frozen=True)
class SATQuery:
    assumptions: tuple[int, ...]
    satisfiable: bool
    stats: SolverStats


@dataclass(frozen=True)
class Analysis:
    puzzle_id: str
    revision: int
    classifications: tuple[tuple[str, Status], ...]  # unresolved cells, row-major
    inconsistent: bool
    cnf: CNF
    queries: tuple[SATQuery, ...]  # includes initial consistency query


@dataclass(frozen=True)
class TraceEntry:
    step: int
    revision: int
    active_clue_ids: tuple[str, ...]  # BEFORE the accepted reveal
    cell: str
    verdict: Status
    sat_queries: tuple[SATQuery, ...]
    revealed_clue_id: str


@dataclass(frozen=True)
class SubmitResult:
    result: VerdictResult
    new_public_state: PublicState
    revealed_clue: Clue | None = None


@dataclass(frozen=True)
class SessionMetrics:
    primary_variables: int = 0
    auxiliary_variables: int | None = None  # None until the current state is analyzed
    active_clauses: int | None = None
    sat_calls: int = 0
    decisions: int = 0
    propagations: int = 0
    backtracks: int = 0
    deduction_steps: int = 0
    sat_runtime_ms: float = 0.0
