from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Optional

from src.pdfpz.core.assets import Asset
from src.pdfpz.core.assets_legacy import AssetsLegacy
from src.pdfpz.core.class_book_manifest import BooksShelf, PdfManifestEntry
from src.pdfpz.core.logger import logger


@dataclass
class BooksCollection:
    legacy_file_path: str
    input_path: str
    legacy_base_path: str
    sqlite_path: str
    legacy_file_name: str
    books_manifest: Optional[BooksShelf]
    tmp_path: str
    assets: Asset

    @classmethod
    def from_legacy_path(cls, _legacy_file_path: str) -> BooksCollection:
        py = PurePosixPath(_legacy_file_path)
        dy = py.parent
        db = py.name
        return cls(
            legacy_file_path=str(py),
            input_path="",
            legacy_base_path=str(dy),
            sqlite_path="",
            legacy_file_name=db,
            books_manifest=None,
            tmp_path="",
            assets=AssetsLegacy(),
        )

    def save_books_collection(self):
        self.save_books_legacy_manifest()

    def save_books_legacy_manifest(self) -> None:
        """Save this collection's books_manifest to legacy path."""
        if self.books_manifest is None:
            raise ValueError("BooksCollection.save_books_manifest: no books_manifest to save")
        logger.info(f"legacy_file_path_path={self.legacy_file_path}")
        self.asset.save_assets()
        logger.info(f"saved books manifest {self.legacy_file_path}")

    def set_tmp_path(self, tmp_path: str):
        self.tmp_path = str(tmp_path) if tmp_path else ""
        self.tmp_path = tmp_path

    def load_books_manifest(self) -> None:
        """Load a BooksShelf from a legacy file."""
        asset = AssetsLegacy()
        asset.set_legacy_path(self.legacy_file_name)

        p: Path = Path(self.assets.legacy_path)
        if not p.is_file():
            logger.info(f"{self.assets.legacy_path} is not a file")
            return None
        logger.info(f"legacy_path={self.assets.legacy_path}")
        documents = asset.load_assets()
        logger.info(f"self.input_path brefore = {self.input_path}")
        self.input_path = documents[0]  # Contains {'input_path': '/mnt/shared/gitlab_books'}
        logger.info(f"self.input_path after = {self.input_path}")

        parsed_books = [PdfManifestEntry.from_dict(book) for book in documents[1]]
        logger.info(f"loaded books manifest {self.legacy_file_name}")
        self.books_manifest = BooksShelf(books=parsed_books)
