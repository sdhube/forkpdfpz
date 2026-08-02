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

from pdfpz.actions.pdf_actions_file import save_tmp_mv_on_source
from pdfpz.actions.pdf_sanitize_fitz import sanitize_fitz
from pdfpz.core.class_tmp_path import TmpPath
from pdfpz.core.logger import logger


def normalize_pdf_and_check_warnings__NOT_WORKING(pdf_path: str):
    pname: PurePosixPath = PurePosixPath(pdf_path).name
    tmpfile: Path = Path("/tmp/").joinpath(pname)

    command = ["qpdf", "--qdf", "--object-streams=disable", str(pdf_path), str(tmpfile)]

    logger.info(f"[*] Inflating streams: {' '.join(command)}")

    # Run qpdf and capture both standard output and structural errors
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    # qpdf Exit Codes: 0 = Success, 3 = Completed with warnings, Other = Fatal error
    if result.returncode == 3:
        logger.info("\n[!] Warning: qpdf completed structural extraction but found issues:")
        logger.info(result.stderr)
    elif result.returncode != 0:
        logger.info(f"\n[X] Fatal Error (Exit Code {result.returncode}):")
        logger.info(result.stderr)
        return False
    else:
        logger.info("\n[+] Success: Streams inflated cleanly with zero warnings.")

    # Check if specific deflate/inflate indicators are hidden in stderr
    if "inflate" in result.stderr.lower() or "stream" in result.stderr.lower():
        logger.info("[!] Detected specific compression anomalies during extraction.")
        command = [
            "qpdf",
            "--stream_data=compress",
            str(tmpfile),
            str(pdf_path),
        ]

        logger.info(f"[*] recompress: {' '.join(command)}")

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
    pc: TmpPath = TmpPath.from_pdf_path(pdf_path)
    logger.info(f"sanitizing {pdf_path}")
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
                logger.info(f"stdout: {result.stdout.strip()}")
            if result.returncode:
                logger.info("sanitize_pike_pdf failed")
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
