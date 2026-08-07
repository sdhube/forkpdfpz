from dataclasses import dataclass

from pdfpz.bridges.assets_legacy import AssetsLegacy
from pdfpz.core.assets import Assets
from pdfpz.bridges.db_bridge import AssetsDb
from pdfpz.core.class_book_manifest import BooksShelf, PdfManifestEntry
from pdfpz.core.crawl import PdfCrawler
from pdfpz.core.logger import logger
from pdfpz.core.merge import merge as merge_entries


@dataclass
class BooksCollection:
    books_manifest: BooksShelf | None
    tmp_path: str
    assets: Assets

    @classmethod
    def from_db(cls, _legacy_file_path: str) -> BooksCollection:
        return cls(
            books_manifest=None,
            tmp_path="",
            assets=AssetsDb(),
        )

    @classmethod
    def from_legacy_path(cls, _legacy_file_path: str) -> BooksCollection:
        return cls(
            books_manifest=None,
            tmp_path="",
            assets=AssetsLegacy(persistance_path=_legacy_file_path),
        )

    @classmethod
    def from_entries(cls, _books_manifests: BooksShelf) -> BooksCollection:
        return cls(
            books_manifest=_books_manifests,
            tmp_path="",
            assets=AssetsLegacy(persistance_path="out.yaml"),
        )

    def save_books_collection(self):
        self.save_books_legacy_manifest()

    def save_books_legacy_manifest(self) -> None:
        """Save this collection's books_manifest via its AssetsLegacy -- all
        the yaml document shape/PdfManifestEntry.to_dict() knowledge lives
        on AssetsLegacy now, not here."""
        if self.books_manifest is None:
            raise ValueError("BooksCollection.save_books_legacy_manifest: no books_manifest to save")
        if not self.assets.books_manifest:
            self.assets.books_manifest = self.books_manifest
        self.assets.save_assets()
        logger.info(f"saved books manifest {self.assets.persistence_path}")

    def set_tmp_path(self, tmp_path: str):
        self.tmp_path = str(tmp_path) if tmp_path else ""

    def load_books_collection(self) -> None:
        """Load this collection's books_manifest via its AssetsLegacy -- all
        the yaml document shape/PdfManifestEntry.from_dict() knowledge lives
        on AssetsLegacy now, not here."""
        self.assets.load_assets()
        self.books_manifest = BooksShelf(books=self.assets.assets)
        logger.info(f"loaded books manifest {self.assets.persistence_path}")

    def crawl_and_merge(self, top_dir: str) -> list[PdfManifestEntry]:
        """Crawl top_dir for PDFs and merge new-by-name entries into
        books_manifest. Moved here from pdftui's BooksSpine -- crawling and
        merging operate purely on the in-memory books list, independent of
        which Asset backend (if any) this collection is persisted through."""
        crawler = PdfCrawler(top_dir)
        crawled_entries = crawler.crawl()

        existing_books = self.books_manifest.books if self.books_manifest else []
        merged_books = merge_entries(existing_books, crawled_entries)
        self.books_manifest = BooksShelf(books=merged_books)

        return crawled_entries
