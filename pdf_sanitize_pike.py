# https://github.com/pikepdf/pikepdf/blob/main/README.md
# https://github.com/pikepdf/pikepdf/blob/main/docs/tutorial.md
# https://pikepdf.readthedocs.io/en/stable/topics/sanitize.html
# https://pikepdf.readthedocs.io/en/stable/topics/qpdf_json.html
# https://pikepdf.readthedocs.io/en/latest/api/main.html#pikepdf.Pdf.save


import subprocess
from pathlib import Path, PurePosixPath

import click
import fitz
import pikepdf

from pdf_sanitize_fitz import sanitize_fitz
from pdf_actions_file import save_tmp_mv_on_source
from pdf_names_conversion import PdfPath


# --- moved from sanitize_second_pass.py -------------------------------------------------
def deep_purge_aa(obj) -> int:
    """Recursively walks through any PDF structural object type to delete /AA tags."""
    count = 0

    # Case 1: Handle Dictionaries (Where keys live)
    if isinstance(obj, pikepdf.Dictionary):
        # Target variations of the target key name
        for target in ["/AA", "AA", pikepdf.Name.AA]:
            if target in obj:
                try:
                    del obj[target]
                    count += 1
                except KeyError:
                    pass

        # Recursively search down through every value inside this dictionary
        for key in list(obj.keys()):
            count += deep_purge_aa(obj[key])

    # Case 2: Handle Arrays/Lists (Annotations are often stored in these)
    elif isinstance(obj, pikepdf.Array):
        for item in obj:
            count += deep_purge_aa(item)

    return count


def ultra_sanitize_pdf(pdf) -> None:
    """Scans all objects globally and cleanses nested dictionary/array layers."""

    total_purged = 0

    # Walk through the low-level object index table
    for obj_idx in list(pdf.objects):
        try:
            obj = pdf.get_object(obj_idx)
            total_purged += deep_purge_aa(obj)
        except Exception:
            continue  # Skip encrypted or broken raw bytes streams

    if total_purged > 0:
        # Drop unlinked structural fragments
        pdf.remove_unreferenced_resources()
        # Rewrite file entirely to break incremental logs
        print(f"Success! Recursively purged {total_purged} hidden '/AA' references.")
# ----------------------------------------------------------------------------------------


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
    ultra_sanitize_pdf(pdf)


def remove_unreferenced(pdf, out_path):
    """
    TODO add call to remove_unreferenced(pdf)
    """

    pdf.remove_unreferenced_resources()

    pdf.save(out_path)
    pdf.close()
    print(f"saved: {out_path}")


def remove_unreferenced_no_save(pdf):
    """
    TODO add call to remove_unreferenced(pdf)
    """

    pdf.remove_unreferenced_resources()


def remove_annots_rewrite_fitz_misses_annots(pdf_path):
    print("entring remove_annots_rewrite")
    print(f"pdf_path={pdf_path}")
    p = PurePosixPath(pdf_path)
    out_stem = "".join([p.stem, "-fitz"])
    out_path = p.with_stem(out_stem)
    print(f"out_path={out_path}")

    # Remove all annotations from every page — annotations aren't part
    # of the original content and are a common vector for /JS, /AA, /A actions
    annot_deleted = False
    with fitz.open(pdf_path) as src:
        for pg in src:
            annots = list(pg.annots())  # snapshot; deleting mutates the live list
            if not annot_deleted and len(annots):
                print(f"{pdf_path} annot detected")
            for annot in annots:
                pg.delete_annot(annot)
                annot_deleted = True

        if annot_deleted:
            print(f"{pdf_path} annot deleted ")
            save_tmp_mv_on_source(src, pdf_path, **{"garbage": 4, "clean": True, "deflate": True})
        # src.save(str(out_path), garbage=4, clean=True, deflate=False)


def remove_annots_rewrite(pdf_path):
    # print("entring remove_annots_rewrite")
    # print(f"pdf_path={pdf_path}")
    # p = PurePosixPath(pdf_path)
    # out_stem = "".join([p.stem, "-annots"])
    # out_path = p.with_stem(out_stem)
    # print(f"out_path={out_path}")

    # Remove all annotations from every page — annotations aren't part
    # of the original content and are a common vector for /JS, /AA, /A actions
    annot_deleted = False
    with pikepdf.open(pdf_path) as src:
        for pg in src.pages:
            if "/Annots" in pg:
                if not annot_deleted:
                    print(f"{pdf_path} annot detected")
                del pg.Annots
                annot_deleted = True

        if annot_deleted:
            print(f"{pdf_path} annot deleted ")
            save_tmp_mv_on_source(
                src, pdf_path, recompress_flate=True
            )  # TODO look at pikepdf.readthedocs.io pike.pdf.save


def pdf_stream_complete_rewrite(pdf_path: str) -> None:
    with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
        if any("input stream is complete but output may still be valid" in w for w in pdf.check_pdf_syntax()):
            save_tmp_mv_on_source(
                pdf, pdf_path, recompress_flate=True
            )  # TODO , garbage=pikepdf.GarbageStream.all, clean=True,linear=True)
            # pdf.save(pdf_path, recompress_flate=True)
            print(f"{pdf_path} PDF streams fixed successfully!")


def normalize_pdf_and_check_warnings__NOT_WORKING(pdf_path: str):
    pname: PurePosixPath = PurePosixPath(pdf_path).name
    tmpfile: Path = Path("/tmp/").joinpath(pname)

    command = ["qpdf", "--qdf", "--object-streams=disable", str(pdf_path), str(tmpfile)]

    print(f"[*] Inflating streams: {' '.join(command)}")

    # Run qpdf and capture both standard output and structural errors
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    # qpdf Exit Codes: 0 = Success, 3 = Completed with warnings, Other = Fatal error
    if result.returncode == 3:
        print("\n[!] Warning: qpdf completed structural extraction but found issues:")
        print(result.stderr)
    elif result.returncode != 0:
        print(f"\n[X] Fatal Error (Exit Code {result.returncode}):")
        print(result.stderr)
        return False
    else:
        print("\n[+] Success: Streams inflated cleanly with zero warnings.")

    # Check if specific deflate/inflate indicators are hidden in stderr
    if "inflate" in result.stderr.lower() or "stream" in result.stderr.lower():
        print("[!] Detected specific compression anomalies during extraction.")
        command = [
            "qpdf",
            "--stream_data=compress",
            str(tmpfile),
            str(pdf_path),
        ]

        print(f"[*] recompress: {' '.join(command)}")

        # Run qpdf and capture both standard output and structural errors
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # tmpfile.unlink(missing_ok=True)

    return True


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

    #  normalize_pdf_and_check_warnings(pdf_path)   # for  slatkin pdf
    pdf_stream_complete_rewrite(pdf_path)
    remove_annots_rewrite(pdf_path)
    pc: PdfPath = PdfPath.from_pdf_path(pdf_path)
    print(f"sanitizing {pdf_path}")
    with pikepdf.open(pdf_path) as pdf:
        additional_removals(pdf)
        scrubber.apply(pdf)
        remove_unreferenced_no_save(pdf)
        pdf.save(pc.path_sanitized_tmp, object_stream_mode=pikepdf.ObjectStreamMode.generate)
        if Path(pc.path_sanitized_tmp).is_file():
            result = subprocess.run(
                ["/home/sd/.local/bin/sdpdf-scan.sh", pc.path_sanitized_tmp], capture_output=True, text=True
            )
            if result.stdout:
                print(f"stdout: {result.stdout.strip()}")
            if result.returncode:
                print("sanitize_pike_pdf failed")
                sanitize_fitz(pc.path_sanitized_tmp)

    # check_dider_move(str(out))


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


@click.command()
@click.argument("pdf_path", type=click.Path(exists=True, dir_okay=False))
def main(pdf_path: str) -> None:
    sanitize_pdf(pdf_path)


if __name__ == "__main__":
    main()
