from pathlib import PurePosixPath, Path

import yaml

from pdfpz.core.logger import logger
from pdfpz.core.assets import Asset
from pdfpz.core.class_book_manifest import PdfManifestEntry


class AssetsLegacy(Asset):
    """A YAML-backed asset representing the books manifest.

    Constructed with everything needed to load and save it: legacy_file_path
    (the file), legacy_base_path/legacy_file_name (its split components),
    and input_path/books if there's data to save. load_assets() reads
    legacy_file_path and populates input_path/books from the file;
    save_assets() writes input_path/books to legacy_file_path.
    BooksCollection doesn't need to know the manifest's yaml document
    shape (or touch PdfManifestEntry.to_dict()/from_dict() itself) at
    all -- only this class does.
    """

    def __init__(
        self,
        persistance_path: str = "",
        input_path: str = "",
        books=None,
    ):

        Asset(self, persistance_path)
        py = PurePosixPath(persistance_path)
        dy = py.parent
        dn = py.name

        self.legacy_base_path = str(dy)
        self.legacy_file_name = str(dn)
        self.input_path = input_path
        self.books = list(books) if books else []

    def load_assets(self) -> None:
        p: Path = Path(self.persistence_path)
        if not p.is_file():
            logger.info(f"{self.assets.legacy_file_path} is not a file")
            return

        with open(self.persistence_path, "r", encoding="utf-8") as f:
            documents = list(yaml.safe_load_all(f))
            self.input_path = documents[0].get("input_path", "")
            self.books = [PdfManifestEntry.from_dict(book) for book in documents[1]]

    def save_assets(self) -> None:
        documents = [{"input_path": self.input_path}, [book.to_dict() for book in self.books]]
        with open(self.persistence_path, "w", encoding="utf-8") as f:
            yaml.safe_dump_all(documents, f, sort_keys=False, allow_unicode=True, explicit_start=True)
