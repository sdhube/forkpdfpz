import shutil
from pathlib import Path

from class_book_manifest import PdfManifestEntry
from class_pdf_path import PdfPath
from logger import logger


def move_pdf_to_no_info(entry: PdfManifestEntry):
    """Move a PDF from temp if it has no title or author."""
    p: PdfPath = PdfPath(PdfManifestEntry.file)
    pdf_path = p.path_sanitized_tmp
    file_path = Path(pdf_path)
    if not file_path.is_file():
        return
    print(f"move {pdf_path} to {p.dir_no_info}")
    shutil.move(str(file_path), str(p.path_sanitized_no_info))


def cp_pdf_from_metadata_to_normalized(entry: PdfManifestEntry, normalized_name):
    p: PdfPath = PdfPath(entry.name)
    pdf_path = p.path_sanitized_info_tmp
    file_path = Path(pdf_path)
    if not file_path.is_file():
        return
    logger.info(f"copied {pdf_path} to {p.DIR_TMPR}")
    shutil.copyfile(str(file_path), str(Path(p.DIR_TMPR).joinpath(normalized_name)))
