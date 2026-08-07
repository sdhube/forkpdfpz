from __future__ import annotations

from typing import List

from pdfpz.core.class_book_manifest import PdfManifestEntry


def merge(main_entries: List[PdfManifestEntry], additional_entries: List[PdfManifestEntry]) -> List[PdfManifestEntry]:
    """Return main_entries with only the new-by-name entries from additional_entries appended.

    main_entries names are assumed unique. additional_entries may repeat
    names already present in main_entries (skipped) or introduce new ones
    (appended, first occurrence wins if additional_entries itself has dupes).
    """
    existing_names = {e.name for e in main_entries}
    merged = list(main_entries)

    for entry in additional_entries:
        if entry.name in existing_names:
            continue
        merged.append(entry)
        existing_names.add(entry.name)

    return merged
