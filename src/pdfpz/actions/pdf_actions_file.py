import shutil
from pathlib import Path, PurePosixPath

from pdfpz.core.logger import logger


def save_tmp_mv_on_source(src, pdf_path: str, **kwargs):
    pname: PurePosixPath = PurePosixPath(pdf_path).name
    tmpfile: Path = Path("/tmp/").joinpath(pname)
    logger.info(f"saving tmpfile to {tmpfile}")
    src.save(str(tmpfile), **kwargs)
    shutil.move(str(tmpfile), str(pdf_path))
