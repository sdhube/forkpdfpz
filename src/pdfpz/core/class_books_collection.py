from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from pdfpz.core.assets import Asset
from pdfpz.core.assets_legacy import AssetsLegacy
from pdfpz.core.class_book_manifest import BooksShelf
from pdfpz.core.logger import logger


@dataclass
class BooksCollection:
    sqlite_path: str
    books_manifest: BooksShelf | None
    tmp_path: str
    assets: Asset

    @classmethod
    def from_legacy_path(cls, _legacy_file_path: str) -> BooksCollection:
        py = PurePosixPath(_legacy_file_path)
        dy = py.parent
        db = py.name
        return cls(
            sqlite_path="",
            books_manifest=None,
            tmp_path="",
            assets=AssetsLegacy(
                legacy_file_path=str(py),
                legacy_base_path=str(dy),
                legacy_file_name=db,
            ),
        )

    def save_books_collection(self):
        self.save_books_legacy_manifest()

    def save_books_legacy_manifest(self) -> None:
        """Save this collection's books_manifest via its AssetsLegacy -- all
        the yaml document shape/PdfManifestEntry.to_dict() knowledge lives
        on AssetsLegacy now, not here."""
        if self.books_manifest is None:
            raise ValueError("BooksCollection.save_books_legacy_manifest: no books_manifest to save")
        self.assets.books = self.books_manifest.books
        self.assets.save_assets()
        logger.info(f"saved books manifest {self.assets.legacy_file_path}")

    def set_tmp_path(self, tmp_path: str):
        self.tmp_path = str(tmp_path) if tmp_path else ""

    def load_books_collection(self) -> None:
        """Load this collection's books_manifest via its AssetsLegacy -- all
        the yaml document shape/PdfManifestEntry.from_dict() knowledge lives
        on AssetsLegacy now, not here."""
        p: Path = Path(self.assets.legacy_file_path)
        if not p.is_file():
            logger.info(f"{self.assets.legacy_file_path} is not a file")
            return
        self.assets.load_assets()
        self.books_manifest = BooksShelf(books=self.assets.books)
        logger.info(f"loaded books manifest {self.assets.legacy_file_path}")
