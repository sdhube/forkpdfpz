# https://github.com/pikepdf/pikepdf/blob/main/README.md
# https://github.com/pikepdf/pikepdf/blob/main/docs/tutorial.md
# https://pikepdf.readthedocs.io/en/stable/topics/sanitize.html
# https://pikepdf.readthedocs.io/en/stable/topics/qpdf_json.html
import click
import pikepdf
from pathlib import Path, PurePosixPath


def additional_removals(pdf):
    """
    TODO add call to additional_removals(pdf)
    """
    # --- not in pikepdf.sanitize; done manually ---
    if "/AcroForm" in pdf.Root:
        del pdf.Root.AcroForm

    if "/StructTreeRoot" in pdf.Root:
        del pdf.Root.StructTreeRoot

    if "/OpenAction" in pdf.Root:
        del pdf.Root.OpenAction

def remove_unreferenced(pdf, out_path):
    """
    TODO add call to remove_unreferenced(pdf)
    """
    
    pdf.remove_unreferenced_resources()

    pdf.save(out_path)
    pdf.close()
    print(f"saved: {out_path}")


# --------------------------------------------------------------------------
# Public function
# --------------------------------------------------------------------------

def sanitize_pdf(pdf_path: str) -> None:
    scrubber = (
        pikepdf.sanitize.Sanitizer()
        .remove_javascript()
        .remove_attachments()
        .remove_external_access()
        .remove_multimedia()
        .remove_web_capture()
        .remove_thumbnails()
        .remove_search_index()
        .remove_private_app_data()
        .remove_collection()
    )
    p = PurePosixPath(pdf_path)
    out_stem = "".join([p.stem, "-sanitized"])
    out = p.with_stem(out_stem)
    with pikepdf.open(pdf_path) as pdf:
        scrubber.apply(pdf).save(str(out))




# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

@click.command()
@click.argument("pdf_path", type=click.Path(exists=True, dir_okay=False))
def main(pdf_path: str) -> None:
    sanitize_pdf(pdf_path)


if __name__ == "__main__":
    main()
