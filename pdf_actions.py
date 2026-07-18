
from dataclasses import fields
from pathlib import Path,PurePath

import click
import pikepdf
import yaml

from pprint import pformat
from pdf_names_conversion import path_linearized_sanitized
from pdf_scan_info_blacklist_values import is_value_containing_blacklisted_terms
from pdf_scan_info_metadata import doc_info_legacy, doc_info_xmp
from pdf_scan_info_pages import grep_copyright_line_pdf
from pdf_scan_info_google_books import google_book_info_by_isbn, open_library_book_info_by_isbn 

from PdfManifestEntry import PdfManifestEntry


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
    pdf_path = path_linearized_sanitized(entry.file, tmp_path) 
    if not entry.name:
        entry.name = str(PurePath(pdf_path).name)
    if res := single_pdf_action_with_path(pdf_path, entry):
        return res
    
    if do_return_title_for_futures:
        return entry.file, entry.title
    
    
def single_pdf_action_with_path(pdf_path, entry: PdfManifestEntry, print_values=False):
    entry_doc: PdfManifestEntry = PdfManifestEntry.new_empty_manifest_entry()
    entry_xmp: PdfManifestEntry = PdfManifestEntry.new_empty_manifest_entry()
    entry_content: PdfManifestEntry = PdfManifestEntry.new_empty_manifest_entry()
    entry_google: PdfManifestEntry = PdfManifestEntry.new_empty_manifest_entry()
    if not Path(pdf_path).exists():
        return f"pdf not found {str(pdf_path)}"
    with pikepdf.open(pdf_path) as pdf:
        doc_info_legacy(pdf, entry_doc)
        entry_doc.scan_blacklisted_values() 
        update_manifest_info_empty_fields(entry, entry_doc)
        if print_values:
            print(f"legacy: {pformat(entry)}")
        doc_info_xmp(pdf, entry_xmp)
        entry_xmp.scan_blacklisted_values()
        update_manifest_info_empty_fields(entry, entry_xmp)
        if print_values:
            print(f"xmp: {pformat(entry)}")
        grep_copyright_line_pdf(pdf_path, entry_content, print_values)
        entry_content.scan_blacklisted_values()
        update_manifest_info_empty_fields(entry, entry_content)
        if print_values:
            print(f"grep copyright {pformat(entry)}")
        if entry.isbn_normalized and not entry.title:
            if google_book_info_by_isbn(entry.isbn_normalized,entry_google):
                open_library_book_info_by_isbn(entry.isbn_normalized,entry_google)
 
            update_manifest_info_empty_fields(entry, entry_google)
            if print_values:
                print(f"update_google {pformat(entry)}")
 
    # write_entry_to_yaml(entry=entry, yaml_path="single_pdf.yaml")

# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


@click.command()
@click.argument("pdf_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--print-values", is_flag=True, default=False, help="print values for debug",)
def main(pdf_path: str, print_values: bool) -> None:
    entry: PdfManifestEntry = PdfManifestEntry.new_empty_manifest_entry()
    single_pdf_action_with_path(pdf_path, entry, print_values=print_values)


if __name__ == "__main__":
    main()


# python pdf_actions.py /tmp/tmp80tnmer3/ml-linearized-sanitized.pdf --legacy-info
