import click
import re
import pymupdf
from class_book_manifest import PdfManifestEntry
from pdf_scan_info_web import doi_book_info_by_link


# 4-digit year, restricted to the 2010s and 2020s (2010-2029)
YEAR_PATTERN = re.compile(r"\b20[12]\d\b")

COPYRIGHT_PATTERN = re.compile(r"(^[^\n]+)\n([^\n]*©[^\n]*)$", re.M)

# ISBN_PATTERN = re.compile(r"ISBN[^\n]*$", re.M)
ISBN_PATTERN = re.compile(r"(\bISBN)(?:-1[03])?[:\s]*((?:97[89][-\s]?)?\d(?:[-\s]?\d){8}[-\s]?[\dXx])", re.IGNORECASE)
ISBN_PATTERN = re.compile(
    r"(\bISBN)(?:-1[03])?(?:\s*:\s*)?(?:\s*\([^)]*\))?\s*:?\s*"
    r"((?:97[89][-\s]?)?\d(?:[-\s]?\d){8,11}[-\s]?[\dXx]?)\s*",
    re.IGNORECASE,
)

BY_PATTERN = re.compile(r"\bBy\s+(.*)$", re.IGNORECASE)
# TODO   BY_PATTERN = re.compile(r"(\bBy\s+|[:\-—–]\s*)(.*$)", re.IGNORECASE)

DOI_PATTERN = re.compile(r"https?://doi\.org/\S+")


def normalize_isbn(isbn: str) -> str:
    """Strip hyphens/spaces and uppercase the trailing check digit ('x' -> 'X')."""
    return re.sub(r"[-\s]", "", isbn).upper()


def grep_copyright_line_pdf(pdf_path, entry: PdfManifestEntry, print_values: bool = False, max_search_pages=5):
    # Matches: (Any characters except newline) followed by a newline,
    # followed by a line containing the copyright symbol or word.
    doc = pymupdf.open(pdf_path)
    max_pages = min(max_search_pages, len(doc))
    author = ""
    copyright_line = ""
    line_before = ""
    year = ""
    isbn = ""
    normalized_isbn = ""
    title = ""
    for page_num in range(max_pages):
        page = doc[page_num]
        page_text = page.get_text("text")
        if not page_text:
            continue
        match = COPYRIGHT_PATTERN.search(page_text)
        if match:
            line_before = match.group(1).strip()
            print(f"line before={line_before}")
            m = BY_PATTERN.search(line_before)
            if m:
                print(f"by pattern  found {line_before}")
                author = m.group(1).strip()
            else:
                print(f"by pattern not found {line_before}")
                title = line_before
            copyright_line = match.group(2).strip()
            m = YEAR_PATTERN.search(copyright_line)
            if m:
                year = m.group(0)
            m = BY_PATTERN.search(copyright_line)
            if m and not author:
                print(f"by pattern  found in copyright line {line_before}")
                author = m.group(1).strip()

            m = ISBN_PATTERN.search(page_text)
            if m:
                isbn = m.group(2)
                normalized_isbn = normalize_isbn(isbn)
            break
    entry.author = author
    entry.year = year
    entry.title = title
    entry.isbn = str(isbn).rstrip()
    entry.isbn_normalized = normalized_isbn
    if print_values:
        print(f"year={entry.year}, isbn={entry.isbn} title={entry.title} normalized_isbn={normalized_isbn}")


def grep_doi_line_pdf(pdf_path, entry: PdfManifestEntry, print_values: bool = False, max_search_pages=5):
    # Matches: (Any characters except newline) followed by a newline,
    # followed by a line containing the copyright symbol or word.
    doc = pymupdf.open(pdf_path)
    max_pages = min(max_search_pages, len(doc))
    for page_num in range(max_pages):
        page = doc[page_num]
        page_text = page.get_text("text")
        if not page_text:
            continue
        match = DOI_PATTERN.search(page_text)
        if match:
            doi_link = match.group()
            doi_book_info_by_link(doi_link, entry)
    if print_values:
        print(f"year={entry.year}, isbn={entry.isbn} title={entry.title} isbn={entry.isbn}")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


@click.command()
@click.argument("pdf_path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--print-values",
    is_flag=True,
    default=False,
    help="print values found",
)
def main(pdf_path: str, print_values: bool) -> None:
    entry: PdfManifestEntry = PdfManifestEntry.new_empty_manifest_entry()
    grep_copyright_line_pdf(pdf_path, entry, print_values=print_values)


if __name__ == "__main__":
    main()


# python pdf_actions.py /tmp/tmp80tnmer3/ml-linearized-sanitized.pdf --legacy-info
