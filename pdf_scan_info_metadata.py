"""
pdf_select_info_source.py
"""

import re

import pikepdf

from PdfManifestEntry import PdfManifestEntry
from pdf_scan_info_pages import YEAR_PATTERN

COPYRIGHT_WORD_PATTERN = re.compile(r"(?:©|copyright)\s*(.*)", re.IGNORECASE)


def handle_author_is_copyright(entry: PdfManifestEntry):
    m = COPYRIGHT_WORD_PATTERN.search(entry.author)
    if m:
        print(f"found match to copyright {m.group(1)}")
        my = YEAR_PATTERN.search(m.group(1))
        if my:
            entry.year = my.group(0)
        entry.author = ""
    else:
        # print("no match to copyright")
        pass


def doc_info_legacy(pdf: pikepdf.Pdf, entry: PdfManifestEntry):
    # legacy DocInfo dict lives in the trailer, not pdf.Root — remove it outright
    # --- DocInfo: report then remove ---
    wanted_substrings = ("title", "author", "isbn", "year")
    fields_to_check = {
        "/Title": "title",
        "/Author": "author",
    }

    if "/Info" in pdf.trailer:
        for key, value in pdf.trailer.Info.items():
            if any(w in str(key).lower() for w in wanted_substrings):
                if key not in fields_to_check:
                    print(f"{key} not supported")
                    continue
                manifest_key = fields_to_check[key]
                setattr(entry, manifest_key, str(value))
    handle_author_is_copyright(entry)


def doc_info_xmp(pdf: pikepdf.Pdf, entry: PdfManifestEntry):
    # --- inspect XMP for bibliographic fields before wiping it ---
    fields_to_check = {
        "dc:title": "title",
        "dc:creator": "author",
        "dc:date": "year",
        "dc:publisher": "Publisher",
        "prism:isbn": "isbn",
        "prism:publicationDate": "Publication date",
    }

    with pdf.open_metadata() as meta:
        found = {label: meta.get(key) for key, label in fields_to_check.items() if meta.get(key)}
        if found:
            for label, value in found.items():
                # print(f"  {label}: {value}")
                setattr(entry, label, str(value))
        else:
            # print("No title/author/date/ISBN found in XMP metadata.")
            pass
    handle_author_is_copyright(entry)
    my = YEAR_PATTERN.search(entry.year)
    if my:
        entry.year = my.group(0)


# python pdf_actions.py /tmp/tmp80tnmer3/ml-linearized-sanitized.pdf --legacy-info
