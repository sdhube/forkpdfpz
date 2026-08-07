from __future__ import annotations

from pathlib import Path
from typing import List

from pdfpz.core.class_books_collection import BooksCollection
from pdfpz.core.class_book_manifest import BooksShelf, PdfManifestEntry


def is_exist(path: str) -> bool:
    return Path(path).exists()


def load(path: str) -> List[PdfManifestEntry]:
    """Load a 2-document books YAML file (header doc + books list doc)
    and return the books list. Missing file -> empty list.

    Delegates to pdfpz's BooksCollection.load_books_collection(), which
    reads the same 2-document format for the same PdfManifestEntry list
    -- so this module doesn't keep a second, independent yaml parser in
    sync with it.

    Callers running under a curses TUI should wrap this call in their
    own stdout/stderr protection (e.g. pdftui.tui_protect.protected());
    that's a TUI-side concern, not something this bridge should own.
    """
    if not is_exist(path):
        return []

    collection = BooksCollection.from_legacy_path(path)
    collection.load_books_collection()
    return collection.books_manifest.books if collection.books_manifest else []


def save(input_path: str, books_list: List[PdfManifestEntry], output_path: str = "saved.yaml") -> None:
    """Save books_list as a 2-document YAML file: header (input_path) + books list.

    Delegates to pdfpz's BooksCollection.save_books_collection() for the
    same reason. Nothing here persists a BooksCollection across calls
    today, so this builds a one-off one around output_path/input_path/
    books_list each time.
    """
    collection = BooksCollection.from_legacy_path(output_path)
    collection.assets.input_path = input_path
    collection.books_manifest = BooksShelf(books=list(books_list))
    collection.save_books_collection()
