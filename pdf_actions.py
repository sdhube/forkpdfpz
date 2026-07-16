
import click
import pikepdf
from pprint import  pformat
from pdf_manifest_info_sources import doc_info_legacy, doc_info_xmp
from pdf_scan_info_functions import grep_copyright_line_pdf 
from pdf_update_manifest import append_info_source, update_manifest_info_empty_fields
from PdfManifestEntry import PdfManifestEntry, new_empty_manifest_entry

def pdf_action(pdf_path, legacy_info=False):
    entry: PdfManifestEntry = new_empty_manifest_entry()
    entry_doc: PdfManifestEntry = new_empty_manifest_entry()
    entry_xmp: PdfManifestEntry = new_empty_manifest_entry()
    entry_content: PdfManifestEntry = new_empty_manifest_entry()
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
    pdf_action(pdf_path, legacy_info=legacy_info)


if __name__ == "__main__":
    main()


# python pdf_actions.py /tmp/tmp80tnmer3/ml-linearized-sanitized.pdf --legacy-info