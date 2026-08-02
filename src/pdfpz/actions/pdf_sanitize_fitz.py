import subprocess
from pathlib import Path, PurePosixPath

import fitz  # PyMuPDF

from pdfpz.core.logger import logger


def sanitize_fitz(pdf_path):
    logger.info(f"pdf_path={pdf_path}")
    src = fitz.open(pdf_path)
    p = PurePosixPath(pdf_path)
    out_stem = "".join([p.stem, "-fitz"])
    out_path = p.with_stem(out_stem)
    logger.info(f"out_path={out_path}")

    # Remove all annotations from every page — annotations aren't part
    # of the original content and are a common vector for /JS, /AA, /A actions
    for pg in src:
        annots = list(pg.annots())  # snapshot; deleting mutates the live list
        for annot in annots:
            pg.delete_annot(annot)

    # Strip /Names/JavaScript name tree
    catalog_xref = src.pdf_catalog()
    names_type, names_val = src.xref_get_key(catalog_xref, "Names")
    if names_type == "xref":
        names_xref = int(names_val.split()[0])
        if src.xref_get_key(names_xref, "JavaScript")[0] != "null":
            src.xref_set_key(names_xref, "JavaScript", "null")

    src.save(str(out_path), garbage=4, clean=True, deflate=True)

    if Path(out_path).is_file():
        result = subprocess.run(["/home/sd/.local/bin/sdpdf-scan.sh", str(out_path)], capture_output=True, text=True)
        if result.stdout:
            logger.info(f"stdout: {result.stdout.strip()}")
        if result.returncode:
            logger.info("sanitize_fitz failed")
        # scan_fitz_sanitized(str(out_path))


def fitz_remove_aa_open_action_from_catalog(src):
    # Strip document-level /AA and /OpenAction on the catalog
    catalog_xref = src.pdf_catalog()
    for key in ("AA", "OpenAction"):
        if src.xref_get_key(catalog_xref, key)[0] != "null":
            src.xref_set_key(catalog_xref, key, "null")


def sanitize_fitz_not_working(pdf_path):
    logger.info(f"pdf_path={pdf_path}")
    src = fitz.open(pdf_path)
    p = PurePosixPath(pdf_path)
    out_stem = "".join([p.stem, "-fitz"])
    out_path = p.with_stem(out_stem)
    logger.info(f"out_path={out_path}")
    dst = fitz.open()

    for pg in src:
        for key in ("AA", "JS"):
            if src.xref_get_key(pg.xref, key)[0] != "null":
                src.xref_set_key(pg.xref, key, "null")
    # Strip catalog-level /AA (document-level open/close/print actions)
    catalog_xref = src.pdf_catalog()
    if src.xref_get_key(catalog_xref, "AA")[0] != "null":
        src.xref_set_key(catalog_xref, "AA", "null")

    # Strip /Names/JavaScript tree (document-level JS, e.g. auto-run scripts)
    names_type, names_val = src.xref_get_key(catalog_xref, "Names")
    if names_type == "xref":
        names_xref = int(names_val.split()[0])
        js_type, _ = src.xref_get_key(names_xref, "JavaScript")
        if js_type != "null":
            src.xref_set_key(names_xref, "JavaScript", "null")

    pdf_bytes = src.convert_to_pdf()
    dst.insert_pdf(fitz.open("pdf", pdf_bytes))

    # not working take /AA too
    # for page in src:
    #    rect = page.rect
    #    new_page = dst.new_page(width=rect.width, height=rect.height)
    #    new_page.show_pdf_page(
    #        rect,
    #        src,
    #        page.number
    #    )

    logger.info(f"saving {out_path}")
    dst.save(str(out_path))

    dst.close()
    src.close()
