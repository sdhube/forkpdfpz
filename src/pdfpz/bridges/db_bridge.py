from __future__ import annotations

from pathlib import Path
from typing import List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .db_schema import Base, BookOrm
from pdfpz.core.class_book_manifest import PdfManifestEntry
from pdfpz.core.assets import Assets
from pdfpz.core.logger import logger

DB_NAME = "books_db"
DB_FILE = f"{DB_NAME}.sqlite"
DB_URL = f"sqlite:///{DB_FILE}"

engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)


class AssetsDb(Assets):
    """A SQLite-backed asset representing the books manifest.

    Mirrors AssetsLegacy's contract (load_assets()/save_assets() reading
    and writing get_entries()/get_persistence_path()) but persists through
    the books table via this module's own is_exist()/create_db()/
    load_all()/merge_to_db() -- it owns no SQL itself, same as
    AssetsLegacy owns no yaml.safe_load beyond its own load/save pair.

    Unlike AssetsLegacy's yaml documents, the books table has nowhere to
    hold a top-level input_path, so it isn't round-tripped here -- callers
    that need it can still set_input_path()/get_input_path() themselves,
    it just won't survive a save_assets()/load_assets() round trip.
    """

    def __init__(self, persistence_path: str = DB_FILE, input_path: str = ""):
        super().__init__(persistence_path)
        self.set_input_path(input_path)

    def load_assets(self) -> None:
        """Load every entry currently in the database. A missing database
        means "nothing saved yet" -- same no-op AssetsLegacy.load_assets()
        does for a missing yaml file -- rather than an error."""
        if not is_exist():
            logger.info(f"{self.get_persistence_path()} does not exist")
            return
        self.set_entries(load_all())
        logger.info(f"loaded from {self.get_persistence_path()}")

    def save_assets(self) -> None:
        """Merge this asset's current entries into the database by name,
        creating the schema first if needed. Uses merge_to_db() rather than
        save() so a repeat save doesn't try to re-insert entries already in
        the database and violate books.name's unique constraint."""
        if not is_exist():
            create_db()
        merge_to_db(self.get_entries() or [])
        logger.info(f"saved to {self.get_persistence_path()}")


def is_exist() -> bool:
    """Return True if the database file already exists."""
    return Path(DB_FILE).exists()


def create_db() -> None:
    """Create an empty database schema."""
    Base.metadata.create_all(engine)


def _entry_to_book(entry: PdfManifestEntry) -> BookOrm:
    return BookOrm(
        valid_pdf=entry.valid_pdf,
        file=entry.file,
        input_file=entry.input_file,
        title=entry.title,
        author=entry.author,
        size=entry.size,
        optimized=entry.optimized,
        year=entry.year,
        isbn=entry.isbn,
        name=entry.name,
        isbn_normalized=entry.isbn_normalized,
        book_id=entry.book_id,
        book_type=entry.book_type,
    )


def _book_to_entry(book: BookOrm) -> PdfManifestEntry:
    entry = PdfManifestEntry.new_empty_manifest_entry()
    for field in (
        "valid_pdf",
        "file",
        "input_file",
        "title",
        "author",
        "size",
        "optimized",
        "year",
        "isbn",
        "name",
        "isbn_normalized",
        "book_id",
        "book_type",
    ):
        setattr(entry, field, getattr(book, field))
    return entry


def load_all() -> List[PdfManifestEntry]:
    """Return every entry currently stored in the database."""
    session = Session()
    try:
        return [_book_to_entry(b) for b in session.query(BookOrm).all()]
    finally:
        session.close()


def save(entries: List[PdfManifestEntry]) -> None:
    """Save a list of manifest entries into the database (no dedup check)."""
    session = Session()
    try:
        session.add_all(_entry_to_book(e) for e in entries)
        session.commit()
    finally:
        session.close()


def merge_to_db(entries: List[PdfManifestEntry]) -> int:
    """Add entries whose name isn't already in the database. Returns count added."""
    session = Session()
    try:
        existing_names = {row[0] for row in session.query(BookOrm.name).all()}
        new_books = []
        seen = set()
        for e in entries:
            if e.name in existing_names or e.name in seen:
                continue
            new_books.append(_entry_to_book(e))
            seen.add(e.name)

        if new_books:
            session.add_all(new_books)
            session.commit()

        return len(new_books)
    finally:
        session.close()
