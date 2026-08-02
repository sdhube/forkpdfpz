# --------------------------------------------------------------------------
# Data class matching the Rust `PdfManifestEntry` struct
# --------------------------------------------------------------------------

import re
from dataclasses import asdict, dataclass, field
from pathlib import PurePosixPath
from typing import List, Optional

from pdfpz.core.assets_yaml import AssetsYaml
from pdfpz.core.logger import logger

# Compiled once upon module import
BLACKLIST_REGEX = re.compile(r"www|https|\.pdf|\bnone\b", re.IGNORECASE)
INVALID_FILENAME_CHARS_REGEX = re.compile(r"[^\w\s.-]|[\[\]{}()]")
MULTIPLE_SPACES_REGEX = re.compile(r"\s+")
SPACES_REGEX = re.compile(r"\s")
MULTIPLE_DASHES_REGEX = re.compile(r"-{3,}")


def is_value_containing_blacklisted_terms(text: str) -> bool:
    return bool(BLACKLIST_REGEX.search(text))


@dataclass
class PdfManifestEntry:
    valid_pdf: bool
    file: str
    input_file: str
    title: str
    author: str
    size: int
    optimized: bool
    year: str
    isbn: str
    name: str
    # Extra field beyond the Rust struct: ISBN with hyphens/spaces stripped and
    # the check digit uppercased, for lookup/dedup use. `isbn` stays exactly
    # as it appears in the PDF text.
    isbn_normalized: str = ""
    # Extra field beyond the Rust struct: "<title>-<author>-<year>"
    book_id: str = ""
    # Extra field beyond the Rust struct: source format, currently always "pdf"
    book_type: str = "pdf"

    def get_normilized_name(self):
        if not self.title:
            return None
        normalized = "--".join(str(p) for p in (self.title, self.author, self.year) if p)
        normalized = INVALID_FILENAME_CHARS_REGEX.sub("-", normalized)

        # Collapse multiple spaces
        normalized = MULTIPLE_SPACES_REGEX.sub(" ", normalized).strip()
        normalized = SPACES_REGEX.sub("-", normalized)
        normalized = normalized.strip(" .-")
        normalized = MULTIPLE_DASHES_REGEX.sub("--", normalized)

        normalized = f"{normalized}.pdf"
        # Remove trailing spaces and dots (Windows)
        return normalized

    def scan_blacklisted_values(self):
        if is_value_containing_blacklisted_terms(self.title):
            self.title = ""

        if is_value_containing_blacklisted_terms(self.author):
            self.author = ""

    def _asdict_with_optimized_rename(self) -> dict:
        """Return a dict built from the dataclass with `optimized` renamed to `Optimized`.

        The dict is constructed in a stable, explicit key order to preserve the
        same ordering used previously when writing legacy asset file (useful for diffs/readability).
        """
        raw = asdict(self)
        ordered_keys = [
            "valid_pdf",
            "input_file",
            "file",
            "title",
            "author",
            "size",
            "Optimized",
            "isbn",
            "name",
            "year",
            "isbn_normalized",
            "book_id",
            "book_type",
        ]
        out = {}
        for k in ordered_keys:
            if k == "Optimized":
                out[k] = raw.get("optimized")
            else:
                out[k] = raw.get(k)
        return out

    def to_dict(self) -> dict:
        """Return a plain dict representation of the entry.

        Uses dataclasses.asdict() under the hood and performs a small key rename
        so callers continue to see `Optimized` (capital O) rather than `optimized`.
        """
        return self._asdict_with_optimized_rename()

    @classmethod
    def from_dict(cls, d: dict) -> "PdfManifestEntry":
        return cls(
            valid_pdf=d.get("valid_pdf", False),
            input_file=d.get("input_file", ""),
            file=d.get("file", ""),
            title=d.get("title", ""),
            author=d.get("author", ""),
            size=d.get("size", 0),
            optimized=d.get("Optimized", False),
            isbn=d.get("isbn", ""),
            name=d.get("name", ""),
            year=d.get("year", ""),
            isbn_normalized=d.get("isbn_normalized", ""),
            book_id=d.get("book_id", ""),
            book_type=d.get("book_type", "pdf"),
        )

    @classmethod
    def new_empty_manifest_entry(cls) -> PdfManifestEntry:
        """Return a PdfManifestEntry with every field at its 'empty' value."""
        return PdfManifestEntry(
            valid_pdf=False,
            input_file="",
            file="",
            title="",
            author="",
            size=0,
            optimized=False,
            isbn="",
            name="",
            year="",
            isbn_normalized="",
            book_id="",
            book_type="pdf",
        )

    def has_no_metadata_info(self):
        return len(self.title) == 0 and len(self.author) == 0 and len(self.isbn) == 0


@dataclass
class BooksShelf:
    books: List[PdfManifestEntry] = field(default_factory=list)

    def books_generator(self, predicate):
        predicate = predicate or (lambda _: True)
        yield from (book for book in self.books if predicate(book))


@dataclass
class BooksCollection:
    legacy_file_path: str
    input_path: str
    legacy_base_path: str
    sqlite_path: str
    legacy_file_name: str
    books_manifest: Optional[BooksShelf]
    tmp_path: str

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
        )

    def save_books_legacy_manifest(self) -> None:
        """Save this collection's books_manifest to legacy path."""
        if self.books_manifest is None:
            raise ValueError("BooksCollection.save_books_manifest: no books_manifest to save")
        logger.info(f"legacy_file_path_path={self.legacy_file_path}")
        documents = [
            {"input_path": self.input_path},
            [book.to_dict() for book in self.books_manifest.books],
        ]
        asset = AssetsYaml(*documents)
        asset.set_yaml_path(self.legacy_file_path)
        asset.save_assets()
        logger.info(f"saved books manifest {self.legacy_file_path}")


pdf_manifest_schema = """ {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Book Metadata",
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "valid_pdf": {"type": "boolean"},
            "input_file": {"type": "string"},
            "file": {"type": "string"},
            "title": {"type": "string"},
            "author": {"type": "string"},
            "size": {"type": "integer", "minimum": 0},
            "Optimized": {"type": "boolean"},
            "isbn": {"type": "string"},
            "name": {"type": "string"},
            "year": {"type": "string"},
            "isbn_normalized": {"type": "string"},
            "book_id": {"type": "string"},
            "book_type": {"type": "string"},
        },
        "required": [
            "valid_pdf",
            "input_file",
            "file",
            "title",
            "author",
            "size",
            "Optimized",
            "isbn",
            "name",
            "year",
            "isbn_normalized",
            "book_id",
            "book_type",
        ],
        "additionalProperties": false,
    },
}
"""

# Mapping of PdfManifestEntry fields to legacy Document Information Dictionary
# keys. NOTE: isbn->/Keywords, year->/CreationDate, and info_file->/InfoFile
# are a repurposing/extension of docinfo for this application's own use, not
# the standard PDF/XMP meaning of those keys — so they are written straight
# to docinfo rather than through pikepdf's XMP<->docinfo autosync (which
# pairs /Keywords with pdf:Keywords and /CreationDate with xmp:CreateDate,
# not with dc:identifier/dc:date, and has no mapping at all for a custom key
# like /InfoFile).
MANIFEST_TO_PDF_FIELDS = {
    "title": "/Title",
    "author": "/Author",
    "isbn": "/Keywords",
    "year": "/CreationDate",
    "input_file": "/InputFile",
}

# Mapping of PdfManifestEntry fields to XMP fields. info_file has no
# standard dc:/pdf:/xmp: equivalent, so it's stored under the custom
# pdfsan: namespace registered above.

PDFSAN_XMP_PREFIX = "pdfsan"
MANIFEST_TO_XMP_FIELDS = {
    "title": "dc:title",
    "author": "dc:creator",
    "isbn": "dc:identifier",
    "year": "dc:date",
    "name": "dc:coverage",
    "input_file": f"{PDFSAN_XMP_PREFIX}:InputFile",
}
