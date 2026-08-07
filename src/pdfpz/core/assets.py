from abc import ABC, abstractmethod
from pathlib import PurePosixPath

from pdfpz.core.logger import logger


class Assets(ABC):
    """Base class for a file-backed asset with a load/save pair.

    Subclasses own one on-disk format (e.g. YAML) and how their held data
    maps to/from it. The path is set once via `set_legacy_path()` and then
    reused by both `load_assets()` and `save_assets()`, rather than being
    passed to each call.
    """

    def __init__(self, persistence_path):
        self.assets = None
        py = PurePosixPath(persistence_path)
        self.persistence_path = str(py)

    def set_persistence_path(self, legacy_path: str) -> None:
        self.persistence_path = legacy_path

    def set_input_path(self, _input_path: str) -> None:
        self.input_path = self.input_path

    def set_assets(self, assets_list):
        self.assets = assets_list
        logger.info(f"have set  {len(self.assets)} assets")

    @abstractmethod
    def load_assets(self):
        """Load this asset's data"""
        raise NotImplementedError

    @abstractmethod
    def save_assets(self) -> None:
        """Save this asset's current data"""
        raise NotImplementedError
