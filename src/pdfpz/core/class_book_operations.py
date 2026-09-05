# class_book_operations.py contains logic and order of books operations

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class BookOperationStage(Enum):
    """The book-processing pipeline's stages, in the order they should run.

    Today's cli.py runs whichever BookOperations flags are enabled in
    operation_map's dict order -- correct, but that order is only implicit
    in a dict literal. This Enum makes it an explicit, authoritative
    sequence, and gives BookOperationState something to walk through one
    stage at a time for a future single "run the whole pipeline" cli call,
    instead of the user invoking pdfpz separately per stage as cli.py's
    own usage examples currently show.
    """

    COPY_PDFS = "copy_pdfs"
    UPDATE_ASSETS_INFO = "update_assets_info"
    MOVE_NO_INFO = "move_no_info"
    SANITIZE_DIDIER = "sanitize_didier"
    FITZ_DIDIER = "fitz_didier"
    SANITIZE_INFO = "sanitize_info"
    SANITIZE_NORMALIZE_NAME = "sanitize_normalize_name"
    LOAD_YAML_EXPORT_DB = "load_yaml_export_db"
    FILTER_FIRST = "filter_first"
    PROPS_FILTER = "props_filter"
    PRINT_FIRST = "print_first"

    @property
    def operation_flag(self) -> str:
        """The BookOperations flag name this stage corresponds to."""
        return self.value


@dataclass
class BookOperationState:
    """Skeleton for running every BookOperationStage in order from one cli
    call, instead of one stage per separate invocation. Tracks which
    stages have completed and what's next; running a stage is still
    cli.py/BooksActions' job -- this class only tracks progress through
    the sequence, it doesn't execute anything itself.
    """

    completed: List[BookOperationStage] = field(default_factory=list)

    @property
    def next_stage(self) -> Optional[BookOperationStage]:
        """The first stage (in BookOperationStage order) not yet completed,
        or None once every stage is done."""
        for stage in BookOperationStage:
            if stage not in self.completed:
                return stage
        return None

    def mark_done(self, stage: BookOperationStage) -> None:
        if stage not in self.completed:
            self.completed.append(stage)

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
    filter_first: bool = (False,)
    props_filter: bool = (False,)
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
