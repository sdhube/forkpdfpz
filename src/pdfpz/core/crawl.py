from __future__ import annotations

import os
from pathlib import Path
from typing import List

from pdfpz.core.class_book_manifest import PdfManifestEntry


class PdfCrawler:
    """Crawls a top directory for PDF files and builds manifest entries."""

    def __init__(self, top_dir: str):
        self.top_dir = Path(top_dir).resolve()

    def crawl(self) -> List[PdfManifestEntry]:
        entries: List[PdfManifestEntry] = []
        for root, _dirs, files in os.walk(self.top_dir):
            for fname in files:
                if not fname.lower().endswith(".pdf"):
                    continue
                abs_path = Path(root) / fname
                rel_path = abs_path.relative_to(self.top_dir)

                entry = PdfManifestEntry.new_empty_manifest_entry()
                entry.input_file = str(abs_path)
                entry.file = str(rel_path)
                entry.name = abs_path.stem
                entries.append(entry)
        return entries
