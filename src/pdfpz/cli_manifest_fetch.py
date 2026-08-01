import click

from pdfpz.actions.pdf_manifest_fetch import single_pdf_action_with_path
from pdfpz.core.class_book_manifest import PdfManifestEntry

# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


@click.command()
@click.argument("pdf_path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--print-values",
    is_flag=True,
    default=False,
    help="print values for debug",
)
def main(pdf_path: str, print_values: bool) -> None:
    entry: PdfManifestEntry = PdfManifestEntry.new_empty_manifest_entry()
    single_pdf_action_with_path(pdf_path, entry, print_values=print_values)


if __name__ == "__main__":
    main()


# python pdf_actions.py /tmp/tmp80tnmer3/ml-linearized-sanitized.pdf --legacy-info
# /bin/python pdf_actions.py  /home/sd/tmp/1-sanitized2/Concise\ Guide\ to\ Software\ Testing\ by\ Gerard\ ORegan-y2019-linearized-sanitized.pdf    --print-values
