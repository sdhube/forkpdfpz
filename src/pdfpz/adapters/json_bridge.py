from __future__ import annotations

import json
from pathlib import Path
from typing import List

from pdfpz.core.class_book_manifest import PdfManifestEntry

# to_dict() maps optimized -> "Optimized"; reverse that on load.
_DICT_TO_FIELD = {
    "valid_pdf": "valid_pdf",
    "input_file": "input_file",
    "file": "file",
    "title": "title",
    "author": "author",
    "size": "size",
    "Optimized": "optimized",
    "isbn": "isbn",
    "name": "name",
    "year": "year",
    "isbn_normalized": "isbn_normalized",
    "book_id": "book_id",
    "book_type": "book_type",
}


def is_exist(path: str) -> bool:
    return Path(path).exists()


def entry_from_dict(d: dict) -> PdfManifestEntry:
    entry = PdfManifestEntry.new_empty_manifest_entry()
    for key, field in _DICT_TO_FIELD.items():
        if key in d:
            setattr(entry, field, d[key])
    return entry


def load(path: str) -> List[PdfManifestEntry]:
    """Read a books manifest JSON file. Missing file -> empty list."""
    p = Path(path)
    if not p.exists():
        return []
    with open(p, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [entry_from_dict(d) for d in raw]


def save(path: str, entries: List[PdfManifestEntry]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump([e.to_dict() for e in entries], f, indent=2, ensure_ascii=False)
