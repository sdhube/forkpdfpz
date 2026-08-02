from __future__ import annotations

from pathlib import Path
from typing import List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .db_schema import Base, BookOrm
from pdfpz.core.class_book_manifest import PdfManifestEntry

DB_NAME = "books_db"
DB_FILE = f"{DB_NAME}.sqlite"
DB_URL = f"sqlite:///{DB_FILE}"

engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)


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
