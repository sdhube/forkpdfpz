# class_book_operations.py contains logic and order of books operations

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar

from pdfpz.adapters.db_bridge import Session, engine
from pdfpz.adapters.db_schema import Base, BookOperationStateOrm
from pdfpz.application.class_actions_books import BooksActions
from pdfpz.domain.class_books_collection import BooksCollection
from pdfpz.utils.logger import logger


class BookOperationStage(Enum):
    """The book-processing pipeline's stages, in run order.

    Member names are prefixed A_/B_/C_/... to make that order explicit
    (A_COPY_PDFS runs before B_UPDATE_ASSETS_INFO, etc).

    Each member's init tuple is (operation_flag, next_operation_flag).
    Members are declared in *reverse* pipeline order (K_FILTER_FIRST
    first, A_COPY_PDFS last) because a member can only reference an
    already-assigned sibling's flag string, not its Enum object (which
    doesn't exist yet during class-body execution). canonical_order()
    resolves this flag-string chain back into real members, starting
    from A_COPY_PDFS. The first-declared (last-run) stage has no
    next_operation_flag, ending the chain.
    """

    # Declared (not assigned) so Enum's metaclass doesn't treat it as a
    # member candidate. Actual value is set once, after this class body,
    # inside BookOperationPlan (see there for why).
    _canonical_order_cache: ClassVar[list[BookOperationStage]]

    def __init__(self, operation_flag: str, next_operation_flag: str | None = None) -> None:
        self._operation_flag = operation_flag
        self._next_operation_flag = next_operation_flag

    # DO NOT DELETE COMMENT # L_PRINT_FIRST = ("print_first",)
    K_FILTER_FIRST = ("filter_first",)
    J_PROPS_FILTER = ("props_filter", K_FILTER_FIRST[0])
    I_SANITIZE_PS = ("sanitize_ps", J_PROPS_FILTER[0])
    H_LOAD_YAML_EXPORT_DB = ("export_books_to_db", I_SANITIZE_PS[0])
    G_SANITIZE_NORMALIZE_NAME = ("sanitize_normalize_name", H_LOAD_YAML_EXPORT_DB[0])
    F_SANITIZE_INFO = ("sanitize_info", G_SANITIZE_NORMALIZE_NAME[0])
    # keep this comment # E_FITZ_DIDIER = ("fitz_didier", )
    D_UPDATE_ASSETS_INFO = ("update_assets_info", F_SANITIZE_INFO[0])
    # keep this comment # C_MOVE_NO_INFO = ("move_no_info", )
    B_SANITIZE_PIKE = ("sanitize_pike", D_UPDATE_ASSETS_INFO[0])
    A_COPY_PDFS = ("copy_pdfs", B_SANITIZE_PIKE[0])

    @property
    def operation_flag(self) -> str:
        """The BookOperations flag name this stage corresponds to."""
        return self._operation_flag

    @classmethod
    def canonical_order(cls) -> list[BookOperationStage]:
        """Every stage in pipeline-run order (A_COPY_PDFS first,
        K_FILTER_FIRST last). list(BookOperationStage) does NOT give
        you this -- members are declared in reverse (see class
        docstring). Cached at class-definition time by
        _resolve_canonical_order(); returns a copy so callers can't
        mutate the cache."""
        return list(cls._canonical_order_cache)

    @classmethod
    def _resolve_canonical_order(cls) -> list[BookOperationStage]:
        """Walk each member's next_operation_flag from A_COPY_PDFS
        onward, resolving the flag-string chain into real members.
        Runs once; see BookOperationPlan for the cache assignment."""
        by_flag = {stage.operation_flag: stage for stage in cls}
        stages = []
        stage = cls.A_COPY_PDFS
        while stage is not None:
            stages.append(stage)
            stage = by_flag[stage._next_operation_flag] if stage._next_operation_flag else None
        return stages


class BookOperationStatus(Enum):
    """One BookOperationStage's progress within a BookOperationState
    run -- richer than a flat done/not-done list, so a stage that's
    never been attempted, one in progress, and one that failed and may
    need a retry can all be told apart."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"

    @property
    def is_terminal(self) -> bool:
        """Whether nothing is left to do for this stage -- DONE and
        SKIPPED count; PENDING/RUNNING/FAILED don't (FAILED stays
        non-terminal so it can be retried)."""
        return self in (BookOperationStatus.DONE, BookOperationStatus.SKIPPED)


@dataclass
class BookOperationPlan:
    """Bridges BookOperations (which stages a caller asked for, as
    flags) with BookOperationStage (the order they run in), producing
    the ordered subset of stages a run should walk through."""

    # Resolved once, here, at BookOperationPlan's own class-definition
    # time, since BookOperationStage's chain never changes afterward.
    BookOperationStage._canonical_order_cache = BookOperationStage._resolve_canonical_order()

    # Cached by run_plan() the first time it builds an operations_map,
    # so later run_plan() calls reuse it instead of re-running
    # initialize_and_return_operations_map() (which reloads
    # BooksCollection from disk) on every call.
    _operations_map_cache: ClassVar[dict[str, Callable[[], None]] | None] = None

    operations: BookOperations

    @property
    def stages(self) -> list[BookOperationStage]:
        """The requested stages only (operations' enabled flags), in
        canonical run order -- not operations' own __dict__ order."""
        return [
            stage for stage in BookOperationStage.canonical_order() if getattr(self.operations, stage.operation_flag)
        ]

    def new_state(self) -> BookOperationState:
        """A fresh BookOperationState scoped to this plan's stages,
        every one starting PENDING."""
        return BookOperationState(stages=self.stages)

    @classmethod
    def run_plan(
        cls,
        persistence_file_path: str,
        tmp_path: str | None = None,
        first_stage: BookOperationStage | None = None,
        operation_map: dict[str, Callable[[], None]] | None = None,
    ) -> BookOperationState:
        """cli.py's single entry point for running the pipeline in one
        call (see Docs/api-cli-hl.md). Builds BookOperations (every
        flag True, or only first_stage onward), plans it, creates a
        BookOperationState, and runs the next_stage/call/mark_done
        loop internally.

        Builds operation_map itself via
        initialize_and_return_operations_map() when not passed,
        caching it in _operations_map_cache for later calls. An
        explicit operation_map bypasses and refreshes that cache.

        DB-backed resumability (resume_plan(), load_from_db(), the
        book_operation_state table) isn't implemented yet.
        """
        if operation_map is not None:
            cls._operations_map_cache = operation_map
        elif cls._operations_map_cache is None:
            cls._operations_map_cache = initialize_and_return_operations_map(persistence_file_path, tmp_path)
        operation_map = cls._operations_map_cache

        order = BookOperationStage.canonical_order()
        stages_to_run = order if first_stage is None else order[order.index(first_stage) :]
        operations = BookOperations(**{stage.operation_flag: True for stage in stages_to_run})
        state = operations.plan().new_state()
        while not state.is_finished():
            stage = state.next_stage
            operation_map[stage.operation_flag]()
            state.mark_done(stage)
        return state

    @classmethod
    def resume_plan(
        cls,
        persistence_file_path: str,
        tmp_path: str | None = None,
        operation_map: dict[str, Callable[[], None]] | None = None,
    ) -> BookOperationState:
        """Resume a previously interrupted pipeline run.

        Reads book_operation_state for persistence_file_path, rebuilds
        BookOperationState via load_from_db(), then continues the
        next_stage/call/mark_done loop from where it stopped.
        Falls back to a full run when no saved rows exist.
        """
        if operation_map is not None:
            cls._operations_map_cache = operation_map
        elif cls._operations_map_cache is None:
            cls._operations_map_cache = initialize_and_return_operations_map(persistence_file_path, tmp_path)
        operation_map = cls._operations_map_cache

        state = BookOperationState.load_from_db()
        logger.info(f"resume_plan: resuming from {state.next_stage} for {persistence_file_path}")
        while not state.is_finished():
            stage = state.next_stage
            operation_map[stage.operation_flag]()
            state.mark_done(stage)
        return state


@dataclass
class BookOperationState:
    """Tracks each requested BookOperationStage's BookOperationStatus
    and what's next, for running the whole pipeline from one call
    instead of one stage per invocation. Running a stage is still
    cli.py/BooksActions' job -- this only tracks progress.

    Defaults to every BookOperationStage so callers that want the full
    sequence don't need a BookOperationPlan -- pass stages=plan.stages
    (or use BookOperationPlan.new_state()) to scope to a subset.
    """

    stages: list[BookOperationStage] = field(default_factory=lambda: BookOperationStage.canonical_order())
    status: dict[BookOperationStage, BookOperationStatus] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # pythonic: fill in any stage the caller didn't already set a status for
        for stage in self.stages:
            self.status.setdefault(stage, BookOperationStatus.PENDING)

    @property
    def next_stage(self) -> BookOperationStage | None:
        """The first of self.stages whose status isn't terminal yet,
        or None once every stage is."""
        for stage in self.stages:
            if not self.status[stage].is_terminal:
                return stage
        return None

    def mark(
        self,
        stage: BookOperationStage,
        status: BookOperationStatus,
    ) -> None:
        """Set stage's status in memory and upsert the book_operation_state row in the DB."""
        self.status[stage] = status
        _upsert_stage_status(stage, status)

    def mark_done(self, stage: BookOperationStage) -> None:
        """Shorthand for mark(stage, BookOperationStatus.DONE)."""
        self.mark(stage, BookOperationStatus.DONE)

    def is_finished(self) -> bool:
        return self.next_stage is None

    @classmethod
    def load_from_db(cls) -> BookOperationState:
        """Reconstruct a BookOperationState from book_operation_state rows.

        Every BookOperationStage in canonical order is included; stages
        with no saved row default to PENDING. Falls back to an all-PENDING
        full-pipeline state when no rows exist (same as a fresh run).
        """
        all_stages = BookOperationStage.canonical_order()
        with Session() as session:
            rows = session.query(BookOperationStateOrm).all()
        saved = {row.stage: BookOperationStatus[row.status] for row in rows}
        status = {stage: saved.get(stage.name, BookOperationStatus.PENDING) for stage in all_stages}
        return cls(stages=all_stages, status=status)


@dataclass
class BookOperations:
    """Encapsulates all book processing operations as flags."""

    copy_pdfs: bool = False
    update_assets_info: bool = False
    move_no_info: bool = False
    sanitize_pike: bool = False
    fitz_didier: bool = False
    sanitize_info: bool = False
    sanitize_normalize_name: bool = False
    export_books_to_db: bool = False
    sanitize_ps: bool = False
    filter_first: bool = False
    props_filter: bool = False
    print_first: bool = False

    # pythonic replacing repited if statements with dictionary
    def get_enabled_operations(self) -> dict:
        """Return a mapping of enabled operation names to their methods."""
        return {name: getattr(self, name) for name, value in self.__dict__.items() if value}

    @classmethod
    def all_stages(cls) -> list[BookOperations]:
        """One BookOperations per BookOperationStage, in canonical
        order, each with only that stage's flag enabled."""
        return [cls(**{stage.operation_flag: True}) for stage in BookOperationStage.canonical_order()]

    def plan(self) -> BookOperationPlan:
        """This BookOperations' requested stages, in canonical order."""
        return BookOperationPlan(self)


# Maps each BookOperationStage's operation_flag to the BooksActions method
# name that implements it. Keyed by flag rather than by BookOperationStage
# member so a mistake here is one wrong dict value, not a second
# independently-ordered copy of the stage chain.
_OPERATION_FLAG_TO_ACTIONS_METHOD = {
    "copy_pdfs": "copy_assets_pdf",
    "sanitize_pike": "sanitize_books_pike",
    "update_assets_info": "update_books_collection_info_and_save",
    "sanitize_info": "sanitize_books_info",
    "sanitize_normalize_name": "update_normalized_info_and_move_rename_file",
    "export_books_to_db": "export_books_to_db",
    "sanitize_ps": "sanitize_ps",
    "props_filter": "props_filter",
    "filter_first": "filter_first",
}


def _upsert_stage_status(
    stage: BookOperationStage,
    status: BookOperationStatus,
) -> None:
    """Upsert one book_operation_state row (create table if missing)."""
    from datetime import datetime, timezone

    Base.metadata.create_all(engine, tables=[BookOperationStateOrm.__table__])
    with Session() as session:
        row = session.get(BookOperationStateOrm, stage.name)
        if row is None:
            row = BookOperationStateOrm(
                stage=stage.name,
                status=status.name,
                updated_at=datetime.now(timezone.utc),
            )
            session.add(row)
        else:
            row.status = status.name
            row.updated_at = datetime.now(timezone.utc)
        session.commit()


def initialize_and_return_operations_map(
    persistence_file_path: str, tmp_path: str | None
) -> dict[str, Callable[[], None]]:
    """Build the {operation_flag: bound BooksActions method} map that
    BookOperationPlan.run_plan()/resume_plan() call into. Built off
    BookOperationStage.canonical_order() so it can't drift from that
    authoritative order.

    Only flags canonical_order() yields end up in the map --
    move_no_info, fitz_didier, print_first don't (they're no longer
    wired into the pipeline).
    """
    logger.info(f"initializing BooksCollection from legacy_path {persistence_file_path}")
    books_collection: BooksCollection = BooksCollection.from_persistence_file_path(persistence_file_path)
    books_collection.set_tmp_path(tmp_path)
    actions: BooksActions = BooksActions(books_collection)
    # Ensure collection is loaded (this will set up tmp dir if needed)
    actions.load_collection(tmp_path=tmp_path)

    return {
        stage.operation_flag: getattr(actions, _OPERATION_FLAG_TO_ACTIONS_METHOD[stage.operation_flag])
        for stage in BookOperationStage.canonical_order()
    }
