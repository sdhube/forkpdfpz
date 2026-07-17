# --------------------------------------------------------------------------
# Data class matching the Rust `PdfManifestEntry` struct
# --------------------------------------------------------------------------

from dataclasses import dataclass


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
    # Extra field beyond the Rust struct: ISBN with hyphens/spaces stripped and
    # the check digit uppercased, for lookup/dedup use. `isbn` stays exactly
    # as it appears in the PDF text.
    isbn_normalized: str = ""
    # Extra field beyond the Rust struct: "<title>-<author>-<year>"
    book_id: str = ""
    # Extra field beyond the Rust struct: source format, currently always "pdf"
    book_type: str = "pdf"

    def to_yaml_dict(self) -> dict:
        """Serialize preserving field order and the `optimized` -> `Optimized` rename."""
        return {
            "valid_pdf": self.valid_pdf,
            "input_file": self.input_file,
            "file": self.file,
            "title": self.title,
            "author": self.author,
            "size": self.size,
            "Optimized": self.optimized,
            "isbn": self.isbn,
            "year": self.year,
            "isbn_normalized": self.isbn_normalized,
            "book_id": self.book_id,
            "book_type": self.book_type,
        }

    @classmethod
    def from_yaml_dict(cls, d: dict) -> "PdfManifestEntry":
        return cls(
            valid_pdf=d.get("valid_pdf", False),
            input_file=d.get("input_file", ""),
            file=d.get("file", ""),
            title=d.get("title", ""),
            author=d.get("author", ""),
            size=d.get("size", 0),
            optimized=d.get("Optimized", False),
            isbn=d.get("isbn", ""),
            year=d.get("year", ""),
            isbn_normalized=d.get("isbn_normalized", ""),
            book_id=d.get("book_id", ""),
            book_type=d.get("book_type", "pdf"),
        )


def new_empty_manifest_entry() -> PdfManifestEntry:
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
        year="",
        isbn_normalized="",
        book_id="",
        book_type="pdf",
    )
