from __future__ import annotations

from dataclasses import dataclass

from pdfpz.bridges.assets_legacy import AssetsLegacy
from pdfpz.bridges.db_bridge import AssetsDb
from pdfpz.core.assets import Assets, assets_pathname_to_type
from pdfpz.core.class_book_manifest import BooksShelf, PdfManifestEntry
from pdfpz.core.crawl import PdfCrawler
from pdfpz.core.logger import logger
from pdfpz.core.merge import merge as merge_entries


@dataclass
class BooksCollection:
    books_shelf: BooksShelf | None
    tmp_path: str
    assets: Assets
    policy: str

    @classmethod
    def from_persistence_file_path(cls, persistence_file_path):
        ext = assets_pathname_to_type(persistence_file_path)
        if ext == "db":
            return BooksCollection.from_db(persistence_file_path)
        if ext == "yaml":
            return BooksCollection.from_legacy_path(persistence_file_path)
        logger.error(f"{persistence_file_path} not supported")

    @classmethod
    def from_db(cls, _legacy_file_path: str) -> BooksCollection:
        return cls(books_manifest=None, tmp_path="", assets=AssetsDb(), policy="db")

    @classmethod
    def from_legacy_path(cls, _legacy_file_path: str) -> BooksCollection:
        return cls(
            books_manifest=None, tmp_path="", assets=AssetsLegacy(persistance_path=_legacy_file_path), policy="yaml"
        )

    @classmethod
    def from_entries(cls, _books_manifests: BooksShelf) -> BooksCollection:
        """NOT USED YET"""
        return cls(
            books_manifest=_books_manifests,
            tmp_path="",
            assets=AssetsLegacy(persistance_path="out.yaml"),
        )

    def export_format(self, format: str):
        assets: Assets = None
        if format == "db":
            assets = AssetsDb()
        assets.set_entries(self.books_shelf.books)
        assets.save_assets()

    def save_books_collection(self, policy="yaml"):
        if self.policy == "yaml" and policy == self.policy:
            self.save_books_legacy_manifest()
        if self.policy == "yaml" and policy == "db":
            self.export_format("db")

    def save_books_legacy_manifest(self) -> None:
        """Save this collection's books_manifest via its AssetsLegacy -- all
        the yaml document shape/PdfManifestEntry.to_dict() knowledge lives
        on AssetsLegacy now, not here."""
        if self.books_shelf is None:
            raise ValueError("BooksCollection.save_books_legacy_manifest: no books_manifest to save")
        if not self.assets.get_entries():
            self.assets.set_entries(self.books_shelf.books)
        self.assets.save_assets()
        logger.info(f"saved books manifest {self.assets.get_persistence_path()}")

    def set_tmp_path(self, tmp_path: str):
        self.tmp_path = str(tmp_path) if tmp_path else ""

    def load_books_collection(self) -> None:
        """Load this collection's books_manifest via its AssetsLegacy -- all
        the yaml document shape/PdfManifestEntry.from_dict() knowledge lives
        on AssetsLegacy now, not here."""
        self.assets.load_assets()
        self.books_shelf = BooksShelf(books=self.assets.get_entries())
        logger.info(f"loaded books manifest {self.assets.get_persistence_path()}")

    def crawl_and_merge(self, top_dir: str) -> list[PdfManifestEntry]:
        """Crawl top_dir for PDFs and merge new-by-name entries into
        books_manifest. Moved here from pdftui's BooksSpine -- crawling and
        merging operate purely on the in-memory books list, independent of
        which Asset backend (if any) this collection is persisted through."""
        crawler = PdfCrawler(top_dir)
        crawled_entries = crawler.crawl()

        existing_books = self.books_shelf.books if self.books_shelf else []
        merged_books = merge_entries(existing_books, crawled_entries)
        self.books_shelf = BooksShelf(books=merged_books)

        return crawled_entries
