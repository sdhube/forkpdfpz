from abc import ABC, abstractmethod


class Asset(ABC):
    """Base class for a file-backed asset with a load/save pair.

    Subclasses own one on-disk format (e.g. YAML) and how their held data
    maps to/from it; `path` is passed per-call rather than fixed at
    construction, since the same asset content is sometimes written to a
    fresh path (or re-loaded from a different one) than it started with.
    """

    def __init__(self, *assets):
        self.assets = list(assets)

    @abstractmethod
    def load(self, path: str):
        """Load this asset's data from `path` and return it."""
        raise NotImplementedError

    @abstractmethod
    def save(self, path: str) -> None:
        """Save this asset's current data to `path`."""
        raise NotImplementedError
