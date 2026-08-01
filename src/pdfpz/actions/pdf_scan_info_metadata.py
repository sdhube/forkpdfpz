"""
pdf_select_info_source.py
"""

import re

import pikepdf

from pdfpz.core.class_book_manifest import PdfManifestEntry
from pdfpz.actions.pdf_scan_info_pages import YEAR_PATTERN

COPYRIGHT_WORD_PATTERN = re.compile(r"(?:©|copyright)\s*(.*)", re.IGNORECASE)


class PdfInfoExtractor:
    """Extracts bibliographic metadata (title/author/year/isbn/...) from a PDF's
    legacy DocInfo dict and XMP stream, writing the results onto a bound
    ``PdfManifestEntry``.
    """

    LEGACY_FIELDS = {"/Title": "title", "/Author": "author"}
    XMP_FIELDS = {
        "dc:title": "title",
        "dc:creator": "author",
        "dc:date": "year",
        "dc:publisher": "Publisher",
        "prism:isbn": "isbn",
        "prism:publicationDate": "Publication date",
    }

    def __init__(self, entry: PdfManifestEntry):
        self.entry = entry

    @classmethod
    def for_entry(cls, entry: PdfManifestEntry) -> "PdfInfoExtractor":
        """Creational: bind a PdfInfo to an existing manifest entry."""
        return cls(entry)

    @classmethod
    def blank(cls) -> "PdfInfoExtractor":
        """Creational: bind a PdfInfo to a fresh, empty manifest entry."""
        return cls(PdfManifestEntry.new_empty_manifest_entry())

    def from_legacy_docinfo(self, pdf: pikepdf.Pdf) -> PdfManifestEntry:
        """Populate the entry from the legacy /Info trailer dict, then resolve a copyright-as-author false positive."""
        if "/Info" in pdf.trailer:
            [self._apply_legacy_field(key, value) for key, value in pdf.trailer.Info.items()]
        self._resolve_author_as_copyright()
        return self.entry

    def from_xmp(self, pdf: pikepdf.Pdf) -> PdfManifestEntry:
        """Populate the entry from XMP bibliographic fields, then normalize author/year."""
        with pdf.open_metadata() as meta:
            [setattr(self.entry, label, str(meta[key])) for key, label in self.XMP_FIELDS.items() if meta.get(key)]
        self._resolve_author_as_copyright()
        self._normalize_year()
        return self.entry

    def _apply_legacy_field(self, key, value) -> None:
        """Private: write one legacy DocInfo key onto the entry, if it's one we track."""
        wanted_substrings = ("title", "author", "isbn", "year")
        if key in self.LEGACY_FIELDS and any(w in str(key).lower() for w in wanted_substrings):
            setattr(self.entry, self.LEGACY_FIELDS[key], str(value))

    def _resolve_author_as_copyright(self) -> None:
        """Private: if `author` actually holds a copyright notice, move its year into `year` and clear author."""
        if not (m := COPYRIGHT_WORD_PATTERN.search(self.entry.author)):
            return
        if my := YEAR_PATTERN.search(m.group(1)):
            self.entry.year = my.group(0)
        self.entry.author = ""

    def _normalize_year(self) -> None:
        """Private: trim `year` down to just its leading 4-digit year, if one is found."""
        if my := YEAR_PATTERN.search(self.entry.year):
            self.entry.year = my.group(0)


# --------------------------------------------------------------------------
# Backward-compatible functional wrappers — pdf_manifest_actions.py imports
# these two by name, so their signatures stay stable while PdfInfo becomes
# the shared implementation underneath.
# --------------------------------------------------------------------------


def fill_entry_by_doc_info_legacy(pdf: pikepdf.Pdf, entry: PdfManifestEntry) -> None:
    PdfInfoExtractor.for_entry(entry).from_legacy_docinfo(pdf)


def fill_entry_by_doc_info_xmp(pdf: pikepdf.Pdf, entry: PdfManifestEntry) -> None:
    PdfInfoExtractor.for_entry(entry).from_xmp(pdf)


# python pdf_actions.py /tmp/tmp80tnmer3/ml-linearized-sanitized.pdf --legacy-info
