from abc import ABC, abstractmethod


class Asset(ABC):
    """Base class for a file-backed asset with a load/save pair.

    Subclasses own one on-disk format (e.g. YAML) and how their held data
    maps to/from it. The path is set once via `set_yaml_path()` and then
    reused by both `load_assets()` and `save_assets()`, rather than being
    passed to each call.
    """

    def __init__(self, *assets):
        self.assets = list(assets)
        self.yaml_path = None

    def set_yaml_path(self, yaml_path: str) -> None:
        self.yaml_path = yaml_path

    @abstractmethod
    def load_assets(self):
        """Load this asset's data from self.yaml_path and return it."""
        raise NotImplementedError

    @abstractmethod
    def save_assets(self) -> None:
        """Save this asset's current data to self.yaml_path."""
        raise NotImplementedError
