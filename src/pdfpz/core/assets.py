from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import PurePosixPath

from pdfpz.core.logger import logger
from pdfpz.core.class_book_manifest import POLICIES


class Assets(ABC):
    """Base class for a file-backed asset with a load/save pair.

    Subclasses own one on-disk format (e.g. YAML) and how their held data
    maps to/from it. The path is set once via `set_persistence_path()` and
    then reused by both `load_assets()` and `save_assets()`, rather than
    being passed to each call.

    State (`_persistence_path`, `_input_path`, `_entries`) is private:
    callers -- including subclasses' own load_assets()/save_assets() --
    reach it only through the get_*/set_* methods below, never by reading
    or writing the underscore-prefixed attributes directly.
    """

    def __init__(self, persistence_path):
        self._persistence_path = str(PurePosixPath(persistence_path))
        self._input_path = ""
        self._entries = None

    def get_persistence_path(self) -> str:
        return self._persistence_path

    def set_persistence_path(self, persistence_path: str) -> None:
        self._persistence_path = persistence_path

    def get_input_path(self) -> str:
        return self._input_path

    def set_input_path(self, input_path: str) -> None:
        self._input_path = input_path

    def get_entries(self):
        return self._entries

    def set_entries(self, entries) -> None:
        self._entries = entries
        logger.info(f"have set {len(self._entries)} entries")

    @abstractmethod
    def load_assets(self):
        """Load this asset's data"""
        raise NotImplementedError

    @abstractmethod
    def save_assets(self) -> None:
        """Save this asset's current data"""
        raise NotImplementedError


def assets_pathname_to_type(name: str) -> str:
    p = PurePosixPath(name).suffix.strip(".")
    if p not in POLICIES:
        logger.error(f"{p} {name} is not supported as persistent")
        return
    return p
