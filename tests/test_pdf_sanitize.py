# tests/test_pdf_sanitize.py
# PYTHONPATH=./ pytest tests/test_pdf_sanitize.py


import pytest
import shutil
import tempfile
from pathlib import Path

from pdf_sanitize import sanitize_pdf


@pytest.fixture
def source_pdf_folder():
    return "pdfs"


@pytest.fixture
def source_pdf(source_pdf_folder):
    return Path(__file__).parent.parent / source_pdf_folder / "ml-linearized.pdf"


@pytest.fixture
def source_base_stem_pdf(source_pdf):
    return source_pdf.stem


@pytest.fixture
def tmp_dir(source_pdf_folder, source_pdf):
    
    flat_tmp_path = tempfile.mkdtemp()
    shallow_tmp = Path(flat_tmp_path)
    pdfs_dir = shallow_tmp
    shutil.copy(source_pdf, pdfs_dir / source_pdf.name)
    return shallow_tmp


def test_sanitize(tmp_dir, source_pdf_folder, source_base_stem_pdf):
    pdf_path = tmp_dir / f"{source_base_stem_pdf}.pdf"
    sanitize_pdf(str(pdf_path))

    sanitized_path = tmp_dir / f"{source_base_stem_pdf}-sanitized.pdf"
    assert sanitized_path.exists()
    assert sanitized_path.stat().st_size > 0
