import re
import pymupdf
from PdfManifestEntry import PdfManifestEntry

# 4-digit year, restricted to the 2010s and 2020s (2010-2029)
YEAR_PATTERN = re.compile(r"\b20[12]\d\b")

COPYRIGHT_PATTERN = re.compile(r"(^[^\n]+)\n([^\n]*©[^\n]*)$", re.M)

# ISBN_PATTERN = re.compile(r"ISBN[^\n]*$", re.M)
ISBN_PATTERN = re.compile(r"(\bISBN)(?:-1[03])?[:\s]*((?:97[89][-\s]?)?\d(?:[-\s]?\d){8}[-\s]?[\dXx])", re.IGNORECASE)


def normalize_isbn(isbn: str) -> str:
    """Strip hyphens/spaces and uppercase the trailing check digit ('x' -> 'X')."""
    return re.sub(r"[-\s]", "", isbn).upper()


def grep_copyright_line_pdf(pdf_path, entry: PdfManifestEntry, max_search_pages=5):
    # Matches: (Any characters except newline) followed by a newline,
    # followed by a line containing the copyright symbol or word.
    doc = pymupdf.open(pdf_path)
    max_pages = min(max_search_pages, len(doc))

    copyright_line = ""
    line_before = ""
    year = ""
    isbn = ""
    normalized_isbn = ""
    for page_num in range(max_pages):

        page = doc[page_num]
        page_text = page.get_text("text")
        if not page_text:
            continue
        match = COPYRIGHT_PATTERN.search(page_text)
        if match:
            line_before = match.group(1).strip()
            copyright_line = match.group(2).strip()
            m = YEAR_PATTERN.search(copyright_line)
            if m:
                year = m.group(0)

            m = ISBN_PATTERN.search(page_text)
            if m:
                isbn = m.group(2)
                normalized_isbn = normalize_isbn(isbn)
            break
    entry.year = year
    entry.title = line_before
    entry.isbn = isbn
    entry.isbn_normalized = normalized_isbn
