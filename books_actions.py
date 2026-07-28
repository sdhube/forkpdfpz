import shutil
from pathlib import Path, PurePosixPath
from pprint import pformat

from logger import logger
from pdf_list_parallel_threads import (
    threadpool_books_fitz_sanitize,
    threadpool_books_info,
    threadpool_books_sanitize,
    threadpool_embed_info,
)
from pdf_names_conversion import PdfPath
from PdfManifestEntry import BooksLib, BooksManifest, PdfManifestEntry
import yaml


class BooksActions:
    """Encapsulates operations on BooksLib and PDF manifest entries."""

    def __init__(self, books_lib: BooksLib):
        self.books_lib = books_lib

    def copy_to_temp(self, entry: PdfManifestEntry):
        """Copy a PDF file to the temporary directory."""
        pdf_input_path = str(Path(self.books_lib.yaml_base_path).joinpath(entry.input_file))
        pdf_name = str(PurePosixPath(entry.input_file).name)
        pdf_output_path = str(Path(self.books_lib.tmp_path).joinpath(pdf_name))
        entry.file = pdf_output_path
        print(f"copy {pdf_input_path} to {pdf_output_path}")
        with open(pdf_input_path, "rb") as src, open(pdf_output_path, "wb") as dst:
            shutil.copyfileobj(src, dst)

    def move_temp_no_title_or_author(self, entry: PdfManifestEntry):
        """Move a PDF from temp if it has no title or author."""
        p: PdfPath = PdfPath(PdfManifestEntry.file)
        pdf_path = p.path_sanitized_tmp
        file_path = Path(pdf_path)
        if not file_path.is_file():
            return
        print(f"move {pdf_path} to {p.dir_no_info}")
        shutil.move(str(file_path), str(p.path_sanitized_no_info))

    def save_books_manifest(self, manifest: BooksManifest, yaml_path: str) -> None:
        """Save a BooksManifest to a YAML file."""
        logger.info(f"yaml_path={yaml_path}")
        documents = [
            {"input_path": manifest.input_path},
            [book.to_dict() for book in manifest.books],
        ]
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.safe_dump_all(documents, f, sort_keys=False, allow_unicode=True, explicit_start=True)
        print(f"saved books manifest {yaml_path}")

    def load_books_manifest(self, yaml_path: str) -> BooksManifest:
        """Load a BooksManifest from a YAML file."""
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
            return BooksManifest(input_path=list_path.get("input_path", ""), books=parsed_books)

    def copy_yaml_pdf_no_info(self) -> None:
        """Copy only PDFs with no metadata info to temp directory."""
        books_manifest: BooksManifest = self.books_lib.books_manifest
        for book in books_manifest.books:
            if book.has_no_metadata_info():
                self.copy_to_temp(book)
        self.save_books_manifest(books_manifest, "copied.yaml")

    def copy_yaml_pdf(self) -> None:
        """Copy all PDFs to temp directory."""
        books_manifest: BooksManifest = self.books_lib.books_manifest
        for book in books_manifest.books:
            self.copy_to_temp(book)
        self.save_books_manifest(books_manifest, "copied.yaml")

    def move_to_no_info(self):
        """Move PDFs with no metadata info to designated directory."""
        books_manifest: BooksManifest = self.books_lib.books_manifest
        for book in books_manifest.books:
            if len(book.title) == 0 and len(book.author) == 0 and len(book.isbn) == 0:
                self.move_temp_no_title_or_author(book)

    def print_first_entry(self):
        """Print first entry and temp directory contents."""
        books_manifest: BooksManifest = self.books_lib.books_manifest
        print(f"books_lib.books_manifest = {type(self.books_lib.books_manifest)}")
        print(f"books_manifest = {type(books_manifest)}")
        books_count = len(books_manifest.books)
        print(f"count={books_count}")
        first_entry: PdfManifestEntry | None = next(iter(books_manifest.books), None)
        first_entry: PdfManifestEntry = books_manifest.books[2]
        print(f"first entry: {pformat(first_entry)}")
        for path in self.books_lib.tmp_path.iterdir():
            info = path.stat()
            print(f"source {PurePosixPath(path).name}")
            print(f"{self.books_lib.tmp_path}/{path.name} {info.st_size}")

    def load_manifest(self, tmp_path: str = None) -> None:
        """Load books manifest into books_lib."""
        if not tmp_path:
            # Create a temporary directory if needed
            import tempfile
            tmp_path = tempfile.mkdtemp()
        
        self.books_lib.tmp_path = tmp_path
        logger.info(f"loaded {pformat(self.books_lib)}")
        print()
        self.books_lib.books_manifest = self.load_books_manifest(self.books_lib.yaml_path)

    def update_yaml_info(self) -> None:
        """Update YAML info for books using threadpool."""
        logger.info("updating yaml info for books")
        threadpool_books_info(self.books_lib)
        self.save_books_manifest(self.books_lib.books_manifest, "files_info.yaml")

    def sanitize_didier(self) -> None:
        """Sanitize books using didier finds."""
        threadpool_books_sanitize(self.books_lib)

    def fitz_didier(self) -> None:
        """Fitz and move books using didier finds."""
        threadpool_books_fitz_sanitize(self.books_lib)

    def sanitize_info(self) -> None:
        """Sanitize and embed info into PDFs."""
        threadpool_embed_info(self.books_lib)
