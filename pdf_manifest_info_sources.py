"""
pdf_select_info_source.py

Merges multiple "info source" results into a single PdfManifestEntry.

Workflow:
    1. Start from an empty manifest_object (new_empty_manifest_entry()).
    2. For each info source available (filename parsing, PDF metadata,
       ISBN lookup, OCR, etc.), build a PdfManifestEntry with whatever
       fields that source was able to determine, and call
       append_info_source(manifest_object, info_source).
    3. Empty fields on manifest_object are simply filled in from the
       info source. Non-empty fields are reconciled via
       update_old_by_new(), which currently just keeps the existing
       value if it agrees with the new one (a true conflict-resolution
       policy can be layered in later).
"""

from PdfManifestEntry import PdfManifestEntry, new_empty_manifest_entry
import pikepdf

from pdf_update_manifest import append_info_source




def doc_info_legacy(pdf: pikepdf.Pdf, entry: PdfManifestEntry):
    # legacy DocInfo dict lives in the trailer, not pdf.Root — remove it outright
    # --- DocInfo: report then remove ---
    wanted_substrings = ("title", "author", "isbn", "year")
    fields_to_check = {
        "/Title": "title",
        "/Author": "author",
    }

    if "/Info" in pdf.trailer:
        for key, value in pdf.trailer.Info.items():
            if any(w in str(key).lower() for w in wanted_substrings):
                if  key not in fields_to_check:
                    print(f"{key} not supported")
                    continue 
                manifest_key = fields_to_check[key]
                setattr(entry, manifest_key, str(value))


def doc_info_xmp(pdf: pikepdf.Pdf, entry: PdfManifestEntry):
    # --- inspect XMP for bibliographic fields before wiping it ---
    fields_to_check = {
        "dc:title": "title",
        "dc:creator": "author",
        "dc:date": "year",
        "dc:publisher": "Publisher",
        "prism:isbn": "isbn",
        "prism:publicationDate": "Publication date",
    }

    with pdf.open_metadata() as meta:
        found = {
            label: meta.get(key)
            for key, label in fields_to_check.items()
            if meta.get(key)
        }
        if found:
            for label, value in found.items():
                # print(f"  {label}: {value}")
                setattr(entry, label, str(value)) 
        else:
            print("No title/author/date/ISBN found in XMP metadata.")


if __name__ == "__main__":
    # Small smoke test / usage example.
    manifest = new_empty_manifest_entry()

    from_filename = PdfManifestEntry(
        valid_pdf=True,
        file="clean-code.pdf",
        title="Clean Code",
        author="",
        size=0,
        optimized=False,
        isbn="",
        year="2008",
    )

    from_metadata = PdfManifestEntry(
        valid_pdf=True,
        file="",
        title="Clean Code",
        author="Robert C. Martin",
        size=4_200_000,
        optimized=True,
        isbn="978-0-13-235088-4",
        year="2008",
    )

    manifest = append_info_source(manifest, from_filename)
    manifest = append_info_source(manifest, from_metadata)

    print(manifest)
# python pdf_actions.py /tmp/tmp80tnmer3/ml-linearized-sanitized.pdf --legacy-info