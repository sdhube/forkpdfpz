import shutil
from pathlib import Path

from pdfpz.core.class_book_manifest import PdfManifestEntry
from pdfpz.core.class_tmp_path import TmpPath
from pdfpz.core.logger import logger


def move_pdf_to_no_info(entry: PdfManifestEntry):
    """Move a PDF from temp if it has no title or author."""
    p: TmpPath = TmpPath(PdfManifestEntry.file)
    pdf_path = p.path_sanitized_tmp
    file_path = Path(pdf_path)
    if not file_path.is_file():
        return
    logger.info(f"move {pdf_path} to {p.dir_no_info}")
    shutil.move(str(file_path), str(p.path_sanitized_no_info))


def cp_pdf_from_metadata_to_normalized(entry: PdfManifestEntry, normalized_name):
    p: TmpPath = TmpPath(entry.name)
    pdf_path = p.path_sanitized_info_tmp
    file_path = Path(pdf_path)
    if not file_path.is_file():
        return
    logger.info(f"copied {pdf_path} to {p.DIR_TMP_MAP['renamed']}")
    shutil.copyfile(str(file_path), str(Path(p.DIR_TMP_MAP["renamed"]).joinpath(normalized_name)))
