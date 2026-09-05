# class_book_operations.py contains logic and order of books operations

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class BookOperationStage(Enum):
    """The book-processing pipeline's stages, in the order they should run.

    Today's cli.py runs whichever BookOperations flags are enabled in
    operation_map's dict order -- correct, but that order is only implicit
    in a dict literal. This Enum makes it an explicit, authoritative
    sequence, and gives BookOperationState something to walk through one
    stage at a time for a future single "run the whole pipeline" cli call,
    instead of the user invoking pdfpz separately per stage as cli.py's
    own usage examples currently show.

    Member names are prefixed A_/B_/C_/... to spell out that order
    directly in the name itself (A_COPY_PDFS runs before
    B_UPDATE_ASSETS_INFO, and so on) -- not just implicit in definition
    order. .value stays the plain operation_flag string (e.g. "copy_pdfs")
    since that's the actual BookOperations field name.
    """

    A_COPY_PDFS = "copy_pdfs"
    B_UPDATE_ASSETS_INFO = "update_assets_info"
    C_MOVE_NO_INFO = "move_no_info"
    D_SANITIZE_DIDIER = "sanitize_didier"
    E_FITZ_DIDIER = "fitz_didier"
    F_SANITIZE_INFO = "sanitize_info"
    G_SANITIZE_NORMALIZE_NAME = "sanitize_normalize_name"
    H_LOAD_YAML_EXPORT_DB = "load_yaml_export_db"
    I_FILTER_FIRST = "filter_first"
    J_PROPS_FILTER = "props_filter"
    K_PRINT_FIRST = "print_first"

    @property
    def operation_flag(self) -> str:
        """The BookOperations flag name this stage corresponds to."""
        return self.value

    @property
    def next_stage(self) -> Optional["BookOperationStage"]:
        """The stage that runs right after this one in canonical order, or
        None if this is the last stage -- lets a caller walk the pipeline
        stage-by-stage (stage = stage.next_stage) without going through
        BookOperationState, which additionally skips stages that aren't
        part of a particular run's plan or are already done."""
        stages = list(BookOperationStage)
        idx = stages.index(self) + 1
        return stages[idx] if idx < len(stages) else None


class BookOperationStatus(Enum):
    """One BookOperationStage's progress within a single run of
    BookOperationState -- richer than a flat "completed or not" list, so
    a future single-cli-call runner can tell a stage that's never been
    attempted apart from one that's in progress or one that failed and
    may need a retry, instead of cli.py's current all-or-nothing flags
    (a stage either ran to completion in that invocation, or the flag
    was never passed at all).
    """

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"

    @property
    def is_terminal(self) -> bool:
        """Whether this status means "nothing left to do for this stage"
        -- DONE and SKIPPED count, PENDING/RUNNING/FAILED don't (FAILED
        stays non-terminal since a future runner may want to retry it)."""
        return self in (BookOperationStatus.DONE, BookOperationStatus.SKIPPED)


@dataclass
class BookOperationPlan:
    """Bridges BookOperations (which stages a caller asked for, as flags)
    with BookOperationStage (the canonical order they run in), producing
    the ordered subset of stages a single cli call should walk through
    one by one -- still just a skeleton: computing that ordered subset is
    this class's job, actually calling BooksActions' methods for each
    stage stays cli.py/BooksActions' job, same as today's operation_map.
    """

    operations: BookOperations

    @property
    def stages(self) -> List[BookOperationStage]:
        """The requested stages only (operations' enabled flags), in
        BookOperationStage's canonical order -- not operations' own
        __dict__ order, which get_enabled_operations() uses today."""
        return [stage for stage in BookOperationStage if getattr(self.operations, stage.operation_flag)]

    def new_state(self) -> BookOperationState:
        """A fresh BookOperationState scoped to just this plan's stages,
        every one starting PENDING."""
        return BookOperationState(stages=self.stages)


@dataclass
class BookOperationState:
    """Skeleton for running every requested BookOperationStage in order
    from one cli call, instead of one stage per separate invocation.
    Tracks each stage's BookOperationStatus and what's next; running a
    stage is still cli.py/BooksActions' job -- this class only tracks
    progress through the sequence, it doesn't execute anything itself.

    Defaults to every BookOperationStage (not just a requested subset) so
    existing callers that only care about the full canonical sequence
    don't need a BookOperationPlan -- pass stages=plan.stages (or build
    via BookOperationPlan.new_state()) to scope it to what was actually
    requested.
    """

    stages: List[BookOperationStage] = field(default_factory=lambda: list(BookOperationStage))
    status: Dict[BookOperationStage, BookOperationStatus] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # pythonic: fill in any stage the caller didn't already set a status for
        for stage in self.stages:
            self.status.setdefault(stage, BookOperationStatus.PENDING)

    @property
    def next_stage(self) -> Optional[BookOperationStage]:
        """The first of self.stages (in order) whose status isn't terminal
        yet (DONE/SKIPPED), or None once every stage is."""
        for stage in self.stages:
            if not self.status[stage].is_terminal:
                return stage
        return None

    def mark(self, stage: BookOperationStage, status: BookOperationStatus) -> None:
        """Set stage's status -- e.g. mark(stage, BookOperationStatus.RUNNING)
        before running it, then mark(stage, BookOperationStatus.DONE) or
        ...FAILED after, once a runner actually calls into BooksActions."""
        self.status[stage] = status

    def mark_done(self, stage: BookOperationStage) -> None:
        """Convenience shorthand for mark(stage, BookOperationStatus.DONE)."""
        self.mark(stage, BookOperationStatus.DONE)

    def is_finished(self) -> bool:
        return self.next_stage is None


@dataclass
class BookOperations:
    """Encapsulates all book processing operations as flags."""

    copy_pdfs: bool = False
    update_assets_info: bool = False
    move_no_info: bool = False
    sanitize_didier: bool = False
    fitz_didier: bool = False
    sanitize_info: bool = False
    sanitize_normalize_name: bool = False
    load_yaml_export_db: bool = False
    filter_first: bool = False
    props_filter: bool = False
    print_first: bool = False

    # pythonic replacing repited if statements with dictionary
    def get_enabled_operations(self) -> dict:
        """Return a mapping of enabled operation names to their methods.
        Allows callers to iterate over only the enabled operations without
        repeating if-statement chains.
        """
        return {name: getattr(self, name) for name, value in self.__dict__.items() if value}

    @classmethod
    def all_stages(cls) -> BookOperations:
        """Build a BookOperations with every BookOperationStage enabled --
        the "run everything, in order, from one cli call" skeleton this
        class provides for cli.py to eventually wire up as a single flag,
        instead of the caller enabling each stage's flag individually."""
        return cls(**{stage.operation_flag: True for stage in BookOperationStage})

    def plan(self) -> BookOperationPlan:
        """This BookOperations' requested stages, in canonical
        BookOperationStage order -- see BookOperationPlan."""
        return BookOperationPlan(self)
