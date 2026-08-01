from dataclasses import fields
from pathlib import Path
from pprint import pformat

import pikepdf
import yaml

from pdfpz.actions.pdf_scan_info_metadata import fill_entry_by_doc_info_legacy, fill_entry_by_doc_info_xmp
from pdfpz.actions.pdf_scan_info_pages import grep_copyright_line_pdf, grep_doi_line_pdf, normalize_isbn
from pdfpz.actions.pdf_scan_info_web import google_book_info_by_isbn, open_library_book_info_by_isbn
from pdfpz.core.class_book_manifest import PdfManifestEntry
from pdfpz.core.class_tmp_path import TmpPath
from pdfpz.core.logger import logger

# --------------------------------------------
# public functions
#
# --------------------------------------------


def write_entry_to_yaml(entry: PdfManifestEntry, yaml_path: str) -> None:
    """Add/update `entry` (keyed by its 'file' name) in a YAML manifest file."""
    path = Path(yaml_path)

    manifest: list[dict] = []
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
            if isinstance(loaded, list):
                manifest = loaded

    # Update the entry for this file (remove old data for it) then re-add it
    # in its correct alphabetical slot by title, rather than tacking it on
    # at the end of the list.
    manifest = [e for e in manifest if e.get("file") != entry.file]
    manifest.append(entry.to_yaml_dict())
    manifest.sort(key=lambda e: (e.get("title") or "").lower())

    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(manifest, f, sort_keys=False, allow_unicode=True)


def update_manifest_info_empty_fields(
    manifest_object: PdfManifestEntry,
    info_source: PdfManifestEntry,
) -> PdfManifestEntry:
    """
    Update empty  manifest info with values from PdfManifestEntry
    """
    for f in fields(manifest_object):
        name = f.name
        value = getattr(manifest_object, name)
        new_value = getattr(info_source, name)
        if not isinstance(value, str):
            continue
        if (not len(value)) and len(new_value):
            setattr(manifest_object, name, new_value)


def single_pdf_action(entry: PdfManifestEntry, tmp_path: str = None, do_return_title_for_futures=True):
    p: TmpPath = TmpPath(entry.name)
    if res := single_pdf_action_with_path(p.path_sanitized_tmp, entry):
        return res

    if do_return_title_for_futures:
        return entry.file, entry.title


# TODO TO move this function PdfInfoExtractor
def single_pdf_action_with_path(pdf_path, entry: PdfManifestEntry, print_values=False):
    if not Path(pdf_path).exists():
        logger.info(f"{pdf_path} not exist")
        return f"pdf not found {str(pdf_path)}"
    entry_doc: PdfManifestEntry = PdfManifestEntry.new_empty_manifest_entry()
    entry_xmp: PdfManifestEntry = PdfManifestEntry.new_empty_manifest_entry()
    entry_content: PdfManifestEntry = PdfManifestEntry.new_empty_manifest_entry()
    entry_google: PdfManifestEntry = PdfManifestEntry.new_empty_manifest_entry()
    entry_doi: PdfManifestEntry = PdfManifestEntry.new_empty_manifest_entry()

    grep_doi_line_pdf(pdf_path, entry_doi, print_values=print_values)
    if entry_doi.isbn:
        entry_doi.isbn_normalized = normalize_isbn(entry_doi.isbn)
    update_manifest_info_empty_fields(entry, entry_doi)
    if print_values:
        logger.info(f"doi: {pformat(entry)}")

    # TODO no need to continue if entry is filled
    with pikepdf.open(pdf_path) as pdf:
        fill_entry_by_doc_info_legacy(pdf, entry_doc)
        entry_doc.scan_blacklisted_values()
        update_manifest_info_empty_fields(entry, entry_doc)
        if print_values:
            logger.info(f"legacy: {pformat(entry)}")
        fill_entry_by_doc_info_xmp(pdf, entry_xmp)
        entry_xmp.scan_blacklisted_values()
        update_manifest_info_empty_fields(entry, entry_xmp)
        if print_values:
            logger.info(f"xmp: {pformat(entry)}")
        grep_copyright_line_pdf(pdf_path, entry_content, print_values)
        entry_content.scan_blacklisted_values()
        update_manifest_info_empty_fields(entry, entry_content)
        if print_values:
            logger.info(f"grep copyright {pformat(entry)}")
        if entry.isbn_normalized and (not len(entry.title) or not len(entry.author)):
            if google_book_info_by_isbn(entry.isbn_normalized, entry_google):
                logger.info("google info failed")
                open_library_book_info_by_isbn(entry.isbn_normalized, entry_google)

            if not entry_google.author or not entry_google.title:
                logger.info(f"invalid google info {entry_google}")
            update_manifest_info_empty_fields(entry, entry_google)
            if entry_google.title and entry.title != entry_google.title:
                entry.title = entry_google.title
            if entry_google.author and entry_google.author != entry.author:
                entry.author = entry_google.author

            if print_values:
                logger.info(f"update_google {pformat(entry)}")

    # write_entry_to_yaml(entry=entry, yaml_path="single_pdf.yaml")
