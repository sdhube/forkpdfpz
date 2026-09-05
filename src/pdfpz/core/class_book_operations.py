# class_book_operations.py contains logic and order of books operations

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar, Dict, List, Optional


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
    order.

    Each member's init tuple is (operation_flag, next_operation_flag):
    the next stage is set at initialization time as a second parameter,
    right alongside the member it belongs to, rather than computed by
    walking canonical order on demand. It's the *next stage's
    operation_flag string*, not that stage's Enum member directly --
    referencing a member by name only works once it's already been
    assigned earlier in this same class body (Enum member objects don't
    exist yet during body execution; each name is still just the plain
    tuple on its right-hand side at that point), so members are declared
    in *reverse* pipeline order (K_PRINT_FIRST first, A_COPY_PDFS last)
    and each next_operation_flag reads the previous line's own flag
    straight off it (K_PRINT_FIRST[0]) instead of retyping that string a
    second time. canonical_order() resolves the chain of flag strings
    back to actual members. The first-declared (last-run) stage's tuple
    omits it, so its next_operation_flag stays None (end of the chain).
    """

    # Declared (not assigned) here so Enum's metaclass never mistakes it
    # for a member candidate -- only assigned *names* in this body get
    # treated that way, and a bare annotation assigns nothing. The actual
    # value is set once, after this class is fully built, inside
    # BookOperationPlan (see there for why).
    _canonical_order_cache: ClassVar[List["BookOperationStage"]]

    def __init__(self, operation_flag: str, next_operation_flag: Optional[str] = None) -> None:
        self._operation_flag = operation_flag
        self._next_operation_flag = next_operation_flag

    K_PRINT_FIRST = ("print_first",)
    J_PROPS_FILTER = ("props_filter", K_PRINT_FIRST[0])
    I_FILTER_FIRST = ("filter_first", J_PROPS_FILTER[0])
    H_LOAD_YAML_EXPORT_DB = ("load_yaml_export_db", I_FILTER_FIRST[0])
    G_SANITIZE_NORMALIZE_NAME = ("sanitize_normalize_name", H_LOAD_YAML_EXPORT_DB[0])
    F_SANITIZE_INFO = ("sanitize_info", G_SANITIZE_NORMALIZE_NAME[0])
    E_FITZ_DIDIER = ("fitz_didier", F_SANITIZE_INFO[0])
    D_SANITIZE_DIDIER = ("sanitize_didier", E_FITZ_DIDIER[0])
    C_MOVE_NO_INFO = ("move_no_info", D_SANITIZE_DIDIER[0])
    B_UPDATE_ASSETS_INFO = ("update_assets_info", C_MOVE_NO_INFO[0])
    A_COPY_PDFS = ("copy_pdfs", B_UPDATE_ASSETS_INFO[0])

    @property
    def operation_flag(self) -> str:
        """The BookOperations flag name this stage corresponds to."""
        return self._operation_flag

    @classmethod
    def canonical_order(cls) -> List["BookOperationStage"]:
        """Every stage in actual pipeline-run order (A_COPY_PDFS first,
        K_PRINT_FIRST last) -- the order to use wherever pipeline order
        matters (BookOperationPlan.stages, BookOperationState's default).
        list(BookOperationStage) itself does NOT give you this: members
        are declared K_PRINT_FIRST..A_COPY_PDFS (reverse -- see class
        docstring), so Enum's own iteration order is backwards from
        pipeline order. This is the one place that resolves the
        next_operation_flag chain into real members and is the
        authoritative pipeline order everything else should read from.

        Cached (built once, right after the class body below, by
        _resolve_canonical_order()) rather than re-walked on every call:
        the chain is fixed at class-definition time and never changes
        afterward, so re-building the flag->stage dict and re-walking all
        11 members on every BookOperationPlan.stages / BookOperationState()
        call (i.e. every single planned run) would be pure repeated work
        for the exact same answer every time. A list copy is still
        returned each call so a caller mutating their copy can't corrupt
        the cache."""
        return list(cls._canonical_order_cache)

    @classmethod
    def _resolve_canonical_order(cls) -> List["BookOperationStage"]:
        """Walk each member's next_operation_flag from A_COPY_PDFS to the
        end, resolving that chain of flag strings into actual members.
        Runs exactly once -- see the assignment to
        BookOperationStage._canonical_order_cache inside BookOperationPlan
        -- caching the answer for canonical_order() to hand back."""
        by_flag = {stage.operation_flag: stage for stage in cls}
        stages = []
        stage = cls.A_COPY_PDFS
        while stage is not None:
            stages.append(stage)
            stage = by_flag[stage._next_operation_flag] if stage._next_operation_flag else None
        return stages


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

    # Resolved exactly once, right here at BookOperationPlan's own
    # class-definition time -- not lazily inside canonical_order() --
    # since BookOperationStage's chain can't change after that class is
    # defined, so there's nothing to recompute later; canonical_order()
    # just hands back a copy of this. Set here (this class actually uses
    # BookOperationStage.canonical_order(), in .stages below) rather than
    # as a bare module-level statement after BookOperationStage itself.
    BookOperationStage._canonical_order_cache = BookOperationStage._resolve_canonical_order()

    operations: BookOperations

    @property
    def stages(self) -> List[BookOperationStage]:
        """The requested stages only (operations' enabled flags), in
        BookOperationStage's canonical run order -- not operations' own
        __dict__ order, which get_enabled_operations() uses today, and
        not list(BookOperationStage)'s declaration order either (see
        BookOperationStage.canonical_order)."""
        return [stage for stage in BookOperationStage.canonical_order() if getattr(self.operations, stage.operation_flag)]

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

    stages: List[BookOperationStage] = field(default_factory=lambda: BookOperationStage.canonical_order())
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
    def all_stages(cls) -> List[BookOperations]:
        """One BookOperations per BookOperationStage, in canonical run
        order, each with only that single stage's flag enabled -- for
        running the whole pipeline one operation at a time from a single
        cli call (for ops in BookOperations.all_stages(): ...), instead
        of a single BookOperations with every flag on at once."""
        return [cls(**{stage.operation_flag: True}) for stage in BookOperationStage.canonical_order()]

    def plan(self) -> BookOperationPlan:
        """This BookOperations' requested stages, in canonical
        BookOperationStage order -- see BookOperationPlan."""
        return BookOperationPlan(self)
