import shutil
from functools import partial
from pathlib import Path, PurePosixPath
from pprint import pformat

from pdfpz.actions.class_actions_book_props import BooksPropsAction
from pdfpz.actions.class_book_manifest_file_actions import cp_pdf_from_metadata_to_normalized, move_pdf_to_no_info
from pdfpz.actions.pdf_actions_info import single_pdf_info_action_with_path
from pdfpz.actions.pdf_manifest_fetch import single_pdf_action
from pdfpz.actions.pdf_sanitize_fitz import sanitize_fitz
from pdfpz.actions.pdf_sanitize_pike import sanitize_pdf
from pdfpz.core.class_book_manifest import BooksShelf, PdfManifestEntry
from pdfpz.core.class_books_collection import BooksCollection
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
        self.books_collection: BooksCollection = books_collection

    def copy_external_file_to_temp(self, entry: PdfManifestEntry):
        """Copy a PDF file to the temporary directory."""
        pdf_input_path = str(Path(self.books_collection.assets.get_legacy_base_path()).joinpath(entry.input_file))
        pdf_name = str(PurePosixPath(entry.input_file).name)
        pdf_output_path = str(Path(self.books_collection.tmp_path).joinpath(pdf_name))
        entry.file = pdf_output_path
        logger.info(f"copy {pdf_input_path} to {pdf_output_path}")
        with open(pdf_input_path, "rb") as src, open(pdf_output_path, "wb") as dst:
            shutil.copyfileobj(src, dst)

    def copy_assets_pdf_no_info(self) -> None:
        """Copy only PDFs with no metadata info to temp directory."""
        books_manifest: BooksShelf = self.books_collection.books_shelf
        for book in books_manifest.books_generator(PdfManifestEntry.has_no_metadata_info):
            self.copy_external_file_to_temp(book)
        self.save_books_collection()

    def copy_assets_pdf(self) -> None:
        """Copy all PDFs to temp directory."""
        books_manifest: BooksShelf = self.books_collection.books_shelf
        for book in books_manifest.books_generator():
            self.copy_external_file_to_temp(book)
        self.save_books_collection()

    def move_books_to_no_info(self):
        """Move PDFs with no metadata info to designated directory."""
        books_manifest: BooksShelf = self.books_collection.books_shelf
        for book in books_manifest.books_generator(PdfManifestEntry.has_no_metadata_info):
            move_pdf_to_no_info(book)

    def update_normalized_info_and_move_rename_file(self):
        """update"""
        books_manifest: BooksShelf = self.books_collection.books_shelf
        book: PdfManifestEntry = None
        for book in books_manifest.books_generator(lambda e: not e.has_no_metadata_info()):
            normalized_name = book.get_normilized_name()
            if not normalized_name:
                continue
            cp_pdf_from_metadata_to_normalized(book, normalized_name)
            book.name = normalized_name

    def load_yaml_export_db(self):
        """export to db"""
        self.books_collection.export_format("db")

    def filter_first(self):
        """Print first filtered entry and temp directory contents."""
        books_spines: BooksShelf = self.books_collection.books_spines
        logger.info(f"books_collection.books_spines = {type(self.books_collection.books_spines)}")
        if not self.books_collection.books_spines.books:
            return
        books_count = len(books_spines.books)
        logger.info(f"count={books_count}")
        first_entry: PdfManifestEntry | None = next(iter(books_spines.books), None)
        logger.info(f"first entry: {pformat(first_entry)}")

    def props_filter(self):
        """Print first filtered entry and temp directory contents."""
        books_spines: BooksShelf = self.books_collection.books_spines
        logger.info(f"books_collection.books_spines = {type(self.books_collection.books_spines)}")
        if not self.books_collection.books_spines.books:
            return
        books_count = len(books_spines.books)
        logger.info(f"count={books_count}")
        props_action: BooksPropsAction = BooksPropsAction(books_spines)
        props_action.delete_table()
        props_action.insert_valid_items_to_table()
        props_action.update_book_props_one_item()  # test with default
        # first_entry: PdfManifestEntry | None = next(iter(books_spines.books), None)
        # logger.info(f"first entry: {pformat(first_entry)}")

    def print_first_entry(self):
        """Print first entry and temp directory contents."""
        books_manifest: BooksShelf = self.books_collection.books_shelf
        logger.info(f"books_collection.books_manifest = {type(self.books_collection.books_shelf)}")
        logger.info(f"books_manifest = {type(books_manifest)}")
        books_count = len(books_manifest.books)
        logger.info(f"count={books_count}")
        first_entry: PdfManifestEntry | None = next(iter(books_manifest.books), None)
        first_entry: PdfManifestEntry = books_manifest.books[2]
        logger.info(f"first entry: {pformat(first_entry)}")
        for path in Path(self.books_collection.tmp_path).iterdir():
            info = path.stat()
            logger.info(f"source {PurePosixPath(path).name}")
            logger.info(f"{self.books_collection.tmp_path}/{path.name} {info.st_size}")

    # TODO this is actually set temp and load
    def load_collection(self, tmp_path: str = None) -> None:
        """Load books manifest into books_collection."""
        if not tmp_path:
            import tempfile

            tmp_path = tempfile.mkdtemp()

        self.books_collection.set_tmp_path(tmp_path)
        self.books_collection.load_books_collection()
        logger.info(f"loaded {len(self.books_collection.books_shelf.books)} entries")

    def update_books_collection_info_and_save(self) -> None:
        self.update_books_collection_info_no_save()
        self.save_books_collection()

    def update_books_collection_info_no_save(self) -> None:
        """Update lib info for books using threadpool."""
        logger.info("updating assets info for books")
        run_threaded_action(
            generate_manifest_items(self.books_collection.books_shelf),
            partial(single_pdf_action, tmp_path=self.books_collection.tmp_path),
        )

    def save_books_collection(self) -> None:
        logger.info("saving  assets info for books")
        self.books_collection.save_books_collection()

    def sanitize_books_didier(self) -> None:
        """Sanitize books using didier finds."""
        run_threads_books_collection_pdf_path(self.books_collection, sanitize_pdf)

    def sanitize_books_fitz_didier(self) -> None:
        """Fitz and move books using didier finds."""
        run_threads_books_collection_pdf_path(self.books_collection, sanitize_fitz)

    def sanitize_books_info(self) -> None:
        """Sanitize and embed info into PDFs."""
        run_threaded_action(
            generate_manifest_items(
                self.books_collection.books_shelf, predicate=lambda m: not m.has_no_metadata_info()
            ),
            lambda m: single_pdf_info_action_with_path(TmpPath(m.name).path_sanitized_tmp, m, sanitize_info=True),
        )
