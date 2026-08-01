import shutil
from functools import partial
from pathlib import Path, PurePosixPath
from pprint import pformat

import yaml

from pdfpz.actions.class_book_manifest_file_actions import cp_pdf_from_metadata_to_normalized, move_pdf_to_no_info
from pdfpz.actions.pdf_actions_info import single_pdf_info_action_with_path
from pdfpz.actions.pdf_manifest_fetch import single_pdf_action
from pdfpz.actions.pdf_sanitize_fitz import sanitize_fitz
from pdfpz.actions.pdf_sanitize_pike import sanitize_pdf
from pdfpz.core.class_book_manifest import BooksCollection, BooksShelf, PdfManifestEntry
from pdfpz.core.class_tmp_path import TmpPath
from pdfpz.core.logger import logger
from pdfpz.core.pdf_list_parallel_threads import (
    generate_manifest_items,
    run_threaded_action,
    run_threads_books_collection_pdf_path,
)


class BooksActions:
    """Encapsulates operations on BooksCollection and PDF manifest entries."""

    def __init__(self, books_collection: BooksCollection):
        self.books_collection = books_collection

    def copy_external_file_to_temp(self, entry: PdfManifestEntry):
        """Copy a PDF file to the temporary directory."""
        pdf_input_path = str(Path(self.books_collection.yaml_base_path).joinpath(entry.input_file))
        pdf_name = str(PurePosixPath(entry.input_file).name)
        pdf_output_path = str(Path(self.books_collection.tmp_path).joinpath(pdf_name))
        entry.file = pdf_output_path
        print(f"copy {pdf_input_path} to {pdf_output_path}")
        with open(pdf_input_path, "rb") as src, open(pdf_output_path, "wb") as dst:
            shutil.copyfileobj(src, dst)

    @staticmethod
    def load_books_manifest(yaml_path: str) -> BooksShelf:
        """Load a BooksShelf from a YAML file.

        Doesn't touch instance state, so it's a staticmethod -- callable as
        BooksActions.load_books_manifest(path) without needing a BooksCollection.
        save_books_manifest now lives on BooksCollection (not BooksShelf), so
        this and BooksCollection.save_books_manifest are no longer a matched
        pair on the same class -- self.books_lib below still assigns this
        method's result to self.books_lib.books_manifest the same way it
        always has, though.
        """
        p: Path = Path(yaml_path)
        if not p.is_file():
            print(f"{yaml_path} is not a file")
            return None
        logger.info(f"yaml_path={yaml_path}")
        with open(yaml_path, "r", encoding="utf-8") as f:
            # safe_load_all handles the document separator (---) safely
            documents = list(yaml.safe_load_all(f))
            list_path = documents[0]  # Contains {'input_path': '/mnt/shared/gitlab_books'}
            books_list = documents[1]  # Contains your array of PDF dictionaries

            parsed_books = [PdfManifestEntry.from_dict(book) for book in books_list]
            logger.info(f"loaded books manifest {yaml_path}")
            # list_path['input_path'] is read but not threaded anywhere yet --
            # BooksShelf no longer carries input_path (it moved to
            # BooksCollection), and wiring it onto self.books_lib.input_path
            # here is a separate "load" phase, not done in this change.
            return BooksShelf(books=parsed_books)

    def copy_yaml_pdf_no_info(self) -> None:
        """Copy only PDFs with no metadata info to temp directory."""
        books_manifest: BooksShelf = self.books_collection.books_manifest
        for book in books_manifest.books_generator(PdfManifestEntry.has_no_metadata_info):
            self.copy_external_file_to_temp(book)
        self.save_books_collection_yaml()

    def copy_yaml_pdf(self) -> None:
        """Copy all PDFs to temp directory."""
        books_manifest: BooksShelf = self.books_collection.books_manifest
        for book in books_manifest.books_generator():
            self.copy_external_file_to_temp(book)
        self.save_books_collection_yaml()

    def move_books_to_no_info(self):
        """Move PDFs with no metadata info to designated directory."""
        books_manifest: BooksShelf = self.books_collection.books_manifest
        for book in books_manifest.books_generator(PdfManifestEntry.has_no_metadata_info):
            move_pdf_to_no_info(book)

    def update_normalized_info_and_move_rename_file(self):
        """update"""
        books_manifest: BooksShelf = self.books_collection.books_manifest
        book: PdfManifestEntry = None
        for book in books_manifest.books_generator(lambda e: not e.has_no_metadata_info()):
            normalized_name = book.get_normilized_name()
            if not normalized_name:
                continue
            cp_pdf_from_metadata_to_normalized(book, normalized_name)
            book.name = normalized_name

    def print_first_entry(self):
        """Print first entry and temp directory contents."""
        books_manifest: BooksShelf = self.books_collection.books_manifest
        print(f"books_lib.books_manifest = {type(self.books_collection.books_manifest)}")
        print(f"books_manifest = {type(books_manifest)}")
        books_count = len(books_manifest.books)
        print(f"count={books_count}")
        first_entry: PdfManifestEntry | None = next(iter(books_manifest.books), None)
        first_entry: PdfManifestEntry = books_manifest.books[2]
        print(f"first entry: {pformat(first_entry)}")
        for path in Path(self.books_collection.tmp_path).iterdir():
            info = path.stat()
            print(f"source {PurePosixPath(path).name}")
            print(f"{self.books_collection.tmp_path}/{path.name} {info.st_size}")

    # TODO this is actually set temp and load
    def load_manifest(self, tmp_path: str = None) -> None:
        """Load books manifest into books_lib."""
        if not tmp_path:
            # Create a temporary directory if needed
            import tempfile

            tmp_path = tempfile.mkdtemp()

        self.books_collection.tmp_path = tmp_path
        logger.info(f"loaded {pformat(self.books_collection)}")
        print()
        self.books_collection.books_manifest = self.load_books_manifest(self.books_collection.yaml_path)

    def update_books_collection_info_and_save(self) -> None:
        self.update_books_lib_info_no_save()
        self.save_books_collection_yaml()

    def update_books_lib_info_no_save(self) -> None:
        """Update lib info for books using threadpool."""
        logger.info("updating yaml info for books")
        run_threaded_action(
            generate_manifest_items(self.books_collection.books_manifest),
            partial(single_pdf_action, tmp_path=self.books_collection.tmp_path),
        )

    def save_books_collection_yaml(self) -> None:
        logger.info("saving  yaml info for books")
        self.books_collection.save_books_manifest()

    def sanitize_books_didier(self) -> None:
        """Sanitize books using didier finds."""
        run_threads_books_collection_pdf_path(self.books_collection, sanitize_pdf)

    def sanitize_books_fitz_didier(self) -> None:
        """Fitz and move books using didier finds."""
        run_threads_books_collection_pdf_path(self.books_collection, sanitize_fitz)

    def sanitize_books_info(self) -> None:
        """Sanitize and embed info into PDFs."""
        run_threaded_action(
            generate_manifest_items(self.books_collection.books_manifest, predicate=lambda m: not m.has_no_metadata_info()),
            lambda m: single_pdf_info_action_with_path(TmpPath(m.name).path_sanitized_tmp, m, sanitize_info=True),
        )
