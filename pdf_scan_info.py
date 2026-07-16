"""
copyright_scanner.py

Fallback scanner (when PDF metadata is missing/unreliable) that uses PyMuPDF
to read VISIBLE TEXT on the first N pages of a PDF, finds every "©" /
"Copyright" occurrence, and pulls the surrounding lines as context to guess
title / author / year / ISBN. The result is written as a PdfManifestEntry
into a YAML manifest file.

Usage:
    python copyright_scanner.py somefile.pdf
    python copyright_scanner.py somefile.pdf --pages 5 --context 7 --yaml-out manifest.yaml

As a library:
    from copyright_scanner import scan_copyright, build_manifest_entry, write_entry_to_yaml
    results = scan_copyright("somefile.pdf", max_pages=5, context_lines=7)
    entry = build_manifest_entry("somefile.pdf", results)
    write_entry_to_yaml(entry, "manifest.yaml")

    # Or in one call:
    from copyright_scanner import scan_pdf_content_for_info
    entry = scan_pdf_content_for_info("somefile.pdf", "manifest.yaml")
"""

import re
from pathlib import Path

from PdfManifestEntry import PdfManifestEntry
import click
import fitz  # PyMuPDF
import yaml

from pdf_actions import write_entry_to_yaml

# Matches "©", "(c)", or the word "Copyright" (case-insensitive)
COPYRIGHT_PATTERN = re.compile(r"©|\(c\)|\bcopyright\b", re.IGNORECASE)

# 4-digit year, restricted to the 2010s and 2020s (2010-2029)
YEAR_PATTERN = re.compile(r"\b20[12]\d\b")

# Heuristic for an author line: "by <Name>", or "<Name>, <Name> and <Name>"
AUTHOR_HINT_PATTERN = re.compile(
    r"\bby\s+([A-Z][a-zA-Z.\-']+(?:\s+[A-Z][a-zA-Z.\-']+){0,3})", re.IGNORECASE
)
# A line that looks like "Firstname Lastname" (title-case, 2-5 words, no sentence punctuation)
NAME_LIKE_PATTERN = re.compile(
    r"^[A-Z][a-zA-Z.\-']+(?:\s+[A-Z][a-zA-Z.\-']+){1,4}$"
)
# ISBN-10 or ISBN-13, with or without hyphens/spaces, optionally prefixed by "ISBN"
ISBN_PATTERN = re.compile(
    r"\bISBN(?:-1[03])?[:\s]*((?:97[89][-\s]?)?\d(?:[-\s]?\d){8}[-\s]?[\dXx])",
    re.IGNORECASE,
)


# --------------------------------------------------------------------------
# Text scanning
# --------------------------------------------------------------------------

def _page_lines(page: "fitz.Page") -> list[str]:
    """Return the visible text of a page as a list of non-empty stripped lines."""
    text = page.get_text("text")
    return [line.strip() for line in text.splitlines() if line.strip()]


def _guess_year(context: list[str]) -> str | None:
    for line in context:
        m = YEAR_PATTERN.search(line)
        if m:
            return m.group(0)
    return None


def _guess_author(context: list[str]) -> str | None:
    for line in context:
        m = AUTHOR_HINT_PATTERN.search(line)
        if m:
            return m.group(1).strip()
    for line in context:
        if NAME_LIKE_PATTERN.match(line) and not COPYRIGHT_PATTERN.search(line):
            return line
    return None


def _guess_isbn(context: list[str]) -> str | None:
    for line in context:
        m = ISBN_PATTERN.search(line)
        if m:
            return m.group(1).strip()
    return None


def _normalize_isbn(isbn: str) -> str:
    """Strip hyphens/spaces and uppercase the trailing check digit ('x' -> 'X')."""
    return re.sub(r"[-\s]", "", isbn).upper()


def _guess_title(first_page_lines: list[str]) -> str | None:
    for line in first_page_lines[:8]:
        if COPYRIGHT_PATTERN.search(line):
            continue
        if YEAR_PATTERN.fullmatch(line.strip()):
            continue
        if 3 <= len(line) <= 120:
            return line
    return None


def scan_copyright(pdf_path: str, max_pages: int = 5, context_lines: int = 7) -> list[dict]:
    """
    Scan the first `max_pages` pages of a PDF for copyright markers.

    Returns a list of dicts, one per match, each containing:
        page, line_number, copyright_line, context (list[str]),
        year_guess, author_guess, title_guess, isbn_guess
    """
    results: list[dict] = []

    with fitz.open(pdf_path) as doc:
        num_pages = min(max_pages, doc.page_count)
        first_page_lines = _page_lines(doc[0]) if num_pages > 0 else []
        title_guess = _guess_title(first_page_lines)

        for page_index in range(num_pages):
            lines = _page_lines(doc[page_index])
            for i, line in enumerate(lines):
                if not COPYRIGHT_PATTERN.search(line):
                    continue

                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                context = lines[start:end]

                results.append(
                    {
                        "page": page_index + 1,
                        "line_number": i + 1,
                        "copyright_line": line,
                        "context": context,
                        "year_guess": _guess_year(context),
                        "author_guess": _guess_author(context),
                        "title_guess": title_guess,
                        "isbn_guess": _guess_isbn(context),
                    }
                )

    return results


def _pick_best_match(results: list[dict]) -> dict | None:
    """Prefer a match where title/author/year were all resolved; else take the first match."""
    if not results:
        return None
    for r in results:
        if r["title_guess"] and r["author_guess"] and r["year_guess"]:
            return r
    return results[0]


# --------------------------------------------------------------------------
# Manifest entry construction + YAML I/O
# --------------------------------------------------------------------------

def build_manifest_entry(pdf_path: str, max_pages: int = 5, context_lines: int = 7) -> PdfManifestEntry:
    """Open the PDF, scan it, and build a PdfManifestEntry (never raises on a bad/unreadable PDF)."""
    path = Path(pdf_path)
    size = path.stat().st_size if path.exists() else 0

    try:
        with fitz.open(pdf_path) as doc:
            valid_pdf = doc.is_pdf
            optimized = bool(doc.is_fast_webaccess)
    except Exception:
        # File exists but PyMuPDF couldn't open/parse it as a valid PDF.
        return PdfManifestEntry(
            valid_pdf=False,
            file=path.name,
            title="",
            author="",
            size=size,
            optimized=False,
            isbn="",
            year="",
        )

    results = scan_copyright(pdf_path, max_pages=max_pages, context_lines=context_lines)
    best = _pick_best_match(results)
    raw_isbn = best["isbn_guess"] if best and best["isbn_guess"] else ""
    title = best["title_guess"] if best and best["title_guess"] else ""
    author = best["author_guess"] if best and best["author_guess"] else ""
    year = best["year_guess"] if best and best["year_guess"] else ""

    return PdfManifestEntry(
        valid_pdf=valid_pdf,
        file=path.name,
        title=title,
        author=author,
        size=size,
        optimized=optimized,
        isbn=raw_isbn,
        year=year,
        isbn_normalized=(_normalize_isbn(raw_isbn) if raw_isbn else ""),
        book_id=f"{title}-{author}-{year}",
    )


# --------------------------------------------------------------------------
# Public functions
# --------------------------------------------------------------------------

def scan_pdf_content_for_info(
    pdf_path: str,
    yaml_path: str,
    max_pages: int = 5,
    context_lines: int = 7,
    write: bool = True,
) -> PdfManifestEntry:
    """
    Build a PdfManifestEntry for `pdf_path` and either write it into the YAML
    manifest at `yaml_path` (default) or just return it without touching disk.

    write=True  -> builds the entry, writes/updates it in the YAML manifest, returns it.
    write=False -> builds the entry and returns it only; no file is written.
    """
    entry = build_manifest_entry(pdf_path, max_pages=max_pages, context_lines=context_lines)
    if write:
        write_entry_to_yaml(entry, yaml_path)
    return entry


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

@click.command()
@click.argument("pdf_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--pages", type=int, default=5, show_default=True, help="Number of leading pages to scan.")
@click.option("--context", type=int, default=7, show_default=True, help="Lines of context around each match.")
@click.option(
    "--yaml-out",
    type=click.Path(dir_okay=False),
    default="manifest.yaml",
    show_default=True,
    help="YAML manifest file to add this PDF's entry to (created if missing).",
)
@click.option(
    "--write/--no-write",
    default=True,
    show_default=True,
    help="Write the entry into the YAML manifest. Use --no-write to only print the entry.",
)
def main(pdf_path: str, pages: int, context: int, yaml_out: str, write: bool) -> None:
    """Scan a PDF's first pages for copyright info and record it in a YAML manifest."""
    entry = scan_pdf_content_for_info(pdf_path, yaml_out, max_pages=pages, context_lines=context, write=write)
    if write:
        click.echo(f"Added '{entry.file}' to {yaml_out}")
    else:
        click.echo(yaml.safe_dump(entry.to_yaml_dict(), sort_keys=False, allow_unicode=True))


if __name__ == "__main__":
    main()
# Example: python pdf_scan_info.py  /tmp/tmp80tnmer3/ml-linearized-sanitized.pdf --yaml-out=/tmp/tmp80tnmer3/files.yml