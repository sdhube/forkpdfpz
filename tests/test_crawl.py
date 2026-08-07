from pathlib import Path

from pdfpz.core.crawl import PdfCrawler


def _touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("")


def test_crawl_finds_pdfs_recursively_case_insensitive(tmp_path):
    _touch(tmp_path / "a.pdf")
    _touch(tmp_path / "sub" / "b.PDF")
    _touch(tmp_path / "notpdf.txt")

    crawler = PdfCrawler(str(tmp_path))
    entries = crawler.crawl()

    names = sorted(e.name for e in entries)
    files = sorted(e.file for e in entries)
    assert names == ["a", "b"]
    assert files == ["a.pdf", str(Path("sub") / "b.PDF")]


def test_crawl_empty_dir_returns_empty_list(tmp_path):
    crawler = PdfCrawler(str(tmp_path))
    assert crawler.crawl() == []


def test_crawl_sets_defaults_besides_name_and_file(tmp_path):
    _touch(tmp_path / "book.pdf")
    entries = PdfCrawler(str(tmp_path)).crawl()
    assert len(entries) == 1
    e = entries[0]
    assert e.name == "book"
    assert e.file == "book.pdf"
    assert e.input_file == str(tmp_path / "book.pdf")
    assert e.valid_pdf is False
    assert e.title == ""
    assert e.size == 0
