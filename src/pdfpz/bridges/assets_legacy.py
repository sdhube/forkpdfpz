from __future__ import annotations
from pathlib import Path, PurePosixPath

import yaml

from pdfpz.core.assets import Assets
from pdfpz.core.class_book_manifest import PdfManifestEntry
from pdfpz.core.logger import logger


class AssetsLegacy(Assets):
    """A YAML-backed asset representing the books manifest.

    Constructed with everything needed to load and save it: persistence_path
    (the file) and input_path/entries if there's data to save.
    load_assets() reads persistence_path and populates input_path/entries
    from the file; save_assets() writes input_path/entries to
    persistence_path. BooksCollection doesn't need to know the manifest's
    yaml document shape (or touch PdfManifestEntry.to_dict()/from_dict()
    itself) at all -- only this class does.

    `_legacy_base_path`/`_legacy_file_name` are private, derived once from
    persistence_path in __init__, and reachable only via
    get_legacy_base_path()/get_legacy_file_name() -- like the base class's
    state, callers never read these attributes directly.
    """

    def __init__(
        self,
        persistance_path: str = "",
        input_path: str = "",
    ):
        super().__init__(persistance_path)
        py = PurePosixPath(persistance_path)
        self._legacy_base_path = str(py.parent)
        self._legacy_file_name = str(py.name)
        self.set_input_path(input_path)

    def get_legacy_base_path(self) -> str:
        return self._legacy_base_path

    def get_legacy_file_name(self) -> str:
        return self._legacy_file_name

    def load_assets(self) -> None:
        persistence_path = self.get_persistence_path()
        p = Path(persistence_path)
        if not p.is_file():
            logger.info(f"{persistence_path} is not a file")
            return

        with open(persistence_path, "r", encoding="utf-8") as f:
            documents = list(yaml.safe_load_all(f))
            self.set_input_path(documents[0].get("input_path", ""))
            entries = [PdfManifestEntry.from_dict(book) for book in documents[1]]
            self.set_entries(entries)
            logger.info(f"loaded from {persistence_path}")

    def save_assets(self) -> None:
        persistence_path = self.get_persistence_path()
        documents = [
            {"input_path": self.get_input_path()},
            [book.to_dict() for book in self.get_entries() or []],
        ]
        with open(persistence_path, "w", encoding="utf-8") as f:
            yaml.safe_dump_all(documents, f, sort_keys=False, allow_unicode=True, explicit_start=True)
