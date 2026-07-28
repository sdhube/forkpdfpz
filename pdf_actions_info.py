from pathlib import Path

import click
import pikepdf

from logger import logger
from class_pdf_path import PdfPath
from pdf_sanitize_info import del_info, pdf_update_metadata
from PdfManifestEntry import MANIFEST_TO_XMP_FIELDS, PdfManifestEntry

# --------------------------------------------
# public functions
#
# --------------------------------------------


def single_pdf_info_action_with_path(pdf_path, entry: PdfManifestEntry, sanitize_info=False):
    logger.info("enter single_pdf_info_action_with_path")
    if not Path(pdf_path).exists():
        return f"pdf not found {str(pdf_path)}"

    p: PdfPath = PdfPath(pdf_path)
    if sanitize_info:
        del_info(p)
        pdf_update_metadata(p, entry)


def get_input_file(p: PdfPath) -> str:
    """Read the custom info_file value back out of a PDF's XMP metadata.

    Args:
        p: PdfPath object with file paths

    Returns:
        The stored info_file string, or "" if the custom field isn't
        present (e.g. the PDF was never processed by pdf_update_metadata,
        or info_file wasn't set on the manifest entry at the time).
    """
    xmp_key = MANIFEST_TO_XMP_FIELDS["input_file"]
    with pikepdf.open(p.path_sanitized_info_tmp) as doc:
        meta = doc.open_metadata()
        return meta.get(xmp_key, "")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


@click.command()
@click.argument("pdf_path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--sanitize-info",
    is_flag=True,
    default=False,
    help="sanitize info",
)
def main(pdf_path: str, sanitize_info: bool) -> None:
    entry: PdfManifestEntry = PdfManifestEntry.new_empty_manifest_entry()
    entry.author = "test author"
    entry.isbn = "123456"
    entry.title = "test title"
    entry.input_file = "/tmp/test.pdf"
    single_pdf_info_action_with_path(pdf_path, entry, sanitize_info=sanitize_info)
    p: PdfPath = PdfPath(pdf_path)
    print(f"input file field ={get_input_file(p)}")


if __name__ == "__main__":
    main()


# python pdf_actions_info.py  /home/sd/tmp/one-file/orig/socket_cpp_.pdf --sanitize-info
# exiftool -a -G1  /tmp/metadata/socket_cpp_.pdf
# pdfinfo /tmp/metadata/socket_cpp_.pdf
