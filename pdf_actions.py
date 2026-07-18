
from dataclasses import fields
from pathlib import Path

import click
import pikepdf
import yaml

from pprint import  pformat
from pdf_manifest_info_sources import doc_info_legacy, doc_info_xmp
from pdf_scan_info_functions import grep_copyright_line_pdf 
from PdfManifestEntry import PdfManifestEntry
#--------------------------------------------
# public functions 
#
#--------------------------------------------

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






def single_pdf_action(pdf_path, entry: PdfManifestEntry, legacy_info=False):
    entry_doc: PdfManifestEntry =  PdfManifestEntry.new_empty_manifest_entry()
    entry_xmp: PdfManifestEntry = PdfManifestEntry.new_empty_manifest_entry()
    entry_content: PdfManifestEntry = PdfManifestEntry.new_empty_manifest_entry()
    with pikepdf.open(pdf_path) as pdf:
        doc_info_legacy(pdf, entry_doc)
        update_manifest_info_empty_fields(entry, entry_doc)
        print(pformat(entry))
        doc_info_xmp(pdf, entry_xmp)
        update_manifest_info_empty_fields(entry, entry_xmp)
        print(pformat(entry))
        grep_copyright_line_pdf(pdf_path, entry_content)
        update_manifest_info_empty_fields(entry, entry_content)
        print(pformat(entry))
    # write_entry_to_yaml(entry=entry, yaml_path="files.yaml")

# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

@click.command()
@click.argument("pdf_path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--legacy-info",
    "legacy_info",
    is_flag=True,
    default=False,
    help="Enable legacy info mode (sets legacy_co_info to True).",
)
def main(pdf_path: str, legacy_info: bool) -> None:
    entry: PdfManifestEntry = PdfManifestEntry.new_empty_manifest_entry()
    single_pdf_action(pdf_path, entry, legacy_info=legacy_info)


if __name__ == "__main__":
    main()


# python pdf_actions.py /tmp/tmp80tnmer3/ml-linearized-sanitized.pdf --legacy-info