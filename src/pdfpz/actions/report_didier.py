#!/usr/bin/env python3

import re
import shutil
import subprocess
import sys
from pathlib import Path

from pdfpz.core.logger import logger

KEYWORDS = [
    "/JS",
    "/JavaScript",
    "/AA",
    "/OpenAction",
    "/AcroForm",
    "/JBIG2Decode",
    "/RichMedia",
    "/Launch",
    "/EmbeddedFile",
    "/XFA",
    "/URI",
    "/Colors > 2^24",
]


def check_pdfid(pdf_file, pdfid="/tmp/pdfid.py"):
    # Run pdfid.py
    result = subprocess.run(
        [pdfid, pdf_file],
        capture_output=True,
        text=True,
        check=True,
    )

    output = result.stdout

    # One regex for all keywords
    pattern = re.compile(
        "(" + "|".join(re.escape(k) for k in KEYWORDS) + r")\s+(\d+)",
        re.MULTILINE,
    )

    matches = pattern.findall(output)

    if not matches:
        raise RuntimeError("No pdfid keywords found in output")

    bad = {}

    for keyword, count in matches:
        count = int(count)
        if count != 0:
            bad[keyword] = count

    return bad


def check_dider_move(pdf_file):
    try:
        bad = check_pdfid(pdf_file)

        if bad:
            logger.info(f"{pdf_file}: SUSPICIOUS")
            for key, value in bad.items():
                logger.info(f"  {key}: {value}")
            if len(bad) == 1:
                dest = list(bad)[0][1:]
                file_path: Path = Path(pdf_file)
                dest_dir = file_path.parent / dest
                dest_dir.mkdir(exist_ok=True)
                shutil.move(str(file_path), str(dest_dir / file_path.name))

        else:
            file_path: Path = Path(pdf_file)
            dest_dir = file_path.parent / "didier_clean"
            dest_dir.mkdir(exist_ok=True)
            shutil.move(str(file_path), str(dest_dir / file_path.name))

    except Exception as e:
        logger.info(f"Error checking {pdf_file}: {e}")
        return 2


def main():
    if len(sys.argv) != 2:
        logger.info(f"Usage: {sys.argv[0]} file.pdf")
        sys.exit(1)

    pdf_file = sys.argv[1]
    res = check_dider_move(pdf_file)
    return res


if __name__ == "__main__":
    main()
