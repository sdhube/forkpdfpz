import click
import pikepdf
from pdf_select_info_source import doc_info_legacy, doc_info_xmp


def pdf_action(pdf_path, legacy_info=False):
    with pikepdf.open(pdf_path) as pdf:
        doc_info_legacy(pdf)
        doc_info_xmp(pdf)


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