# https://github.com/pikepdf/pikepdf/blob/main/README.md
# https://github.com/pikepdf/pikepdf/blob/main/docs/tutorial.md
# https://pikepdf.readthedocs.io/en/stable/topics/sanitize.html
# https://pikepdf.readthedocs.io/en/stable/topics/qpdf_json.html
import click
import pikepdf
from pathlib import Path, PurePosixPath


def additional_removals(pdf):
    # --- not in pikepdf.sanitize; done manually ---
    if "/AcroForm" in pdf.Root:
        del pdf.Root.AcroForm

    if "/StructTreeRoot" in pdf.Root:
        del pdf.Root.StructTreeRoot

    if "/OpenAction" in pdf.Root:
        del pdf.Root.OpenAction


def legacy_doc_info(pdf):
    # legacy DocInfo dict lives in the trailer, not pdf.Root — remove it outright
    # --- DocInfo: report then remove ---
    wanted_substrings = ("title", "author", "isbn", "year")

    if "/Info" in pdf.trailer:
        print("DocInfo fields found before removal:")
        for key, value in pdf.trailer.Info.items():
            if any(w in str(key).lower() for w in wanted_substrings):
                print(f"  {key}: {value}")
        del pdf.trailer.Info
        print("DocInfo removed.")
    else:
        print("No DocInfo present.")

    # --- inspect XMP for bibliographic fields before wiping it ---
    fields_to_check = {
        "dc:title": "Title",
        "dc:creator": "Author(s)",
        "dc:date": "Date",
        "dc:publisher": "Publisher",
        "prism:isbn": "ISBN",
        "prism:publicationDate": "Publication date",
    }

    with pdf.open_metadata() as meta:
        found = {
            label: meta.get(key)
            for key, label in fields_to_check.items()
            if meta.get(key)
        }
        if found:
            print("XMP metadata found before removal:")
            for label, value in found.items():
                print(f"  {label}: {value}")
        else:
            print("No title/author/date/ISBN found in XMP metadata.")
        meta.clear()


def remove_unreferenced(pdf):
    pdf.remove_unreferenced_resources()

    pdf.save(out_path)
    pdf.close()
    print(f"saved: {out_path}")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

@click.command()
@click.argument("pdf_path", type=click.Path(exists=True, dir_okay=False))
def main(pdf_path: str) -> None:
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


if __name__ == "__main__":
    main()
