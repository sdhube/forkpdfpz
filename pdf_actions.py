import click
import pikepdf
from pprint import  pformat
from pdf_select_info_source import doc_info_legacy, doc_info_xmp
from PdfManifestEntry import PdfManifestEntry, new_empty_manifest_entry

def pdf_action(pdf_path, legacy_info=False):
    with pikepdf.open(pdf_path) as pdf:
        entry: PdfManifestEntry = new_empty_manifest_entry()
        doc_info_legacy(pdf, entry)
        print(pformat(entry))
        entry: PdfManifestEntry = new_empty_manifest_entry()
        doc_info_xmp(pdf, entry)
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