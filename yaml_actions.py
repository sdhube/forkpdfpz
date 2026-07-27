import shutil
import tempfile
from pathlib import Path, PurePosixPath
from pprint import pformat

import click
import yaml

from logger import logger
from pdf_list_parallel_threads import (
    threadpool_books_fitz_sanitize,
    threadpool_books_info,
    threadpool_books_sanitize,
    threadpool_embed_info,
)
from pdf_names_conversion import PdfPath
from PdfManifestEntry import BooksLib, BooksManifest, PdfManifestEntry


def tmp_dir() -> Path:
    flat_tmp_path = tempfile.mkdtemp()
    shallow_tmp = Path(flat_tmp_path)
    return shallow_tmp


# -----------------------------------------
# public functions
# ------------------------------------------


def copy_to_temp(books_lib: BooksLib, entry: PdfManifestEntry):
    pdf_input_path = str(Path(books_lib.yaml_base_path).joinpath(entry.input_file))
    pdf_name = str(PurePosixPath(entry.input_file).name)
    pdf_output_path = str(Path(books_lib.tmp_path).joinpath(pdf_name))
    entry.file = pdf_output_path
    print(f"copy {pdf_input_path} to {pdf_output_path}")
    with open(pdf_input_path, "rb") as src, open(pdf_output_path, "wb") as dst:
        shutil.copyfileobj(src, dst)


def move_temp_no_title_or_author(books_lib: BooksLib, entry: PdfManifestEntry):
    p: PdfPath = PdfPath(PdfManifestEntry.file)
    pdf_path = p.path_sanitized_tmp
    file_path = Path(pdf_path)
    if not file_path.is_file():
        return
    print(f"move {pdf_path} to {p.dir_no_info}")
    shutil.move(str(file_path), str(p.path_sanitized_no_info))


def save_books_manifest(manifest: BooksManifest, yaml_path: str) -> None:
    logger.info(f"yaml_path={yaml_path}")
    documents = [
        {"input_path": manifest.input_path},
        [book.to_dict() for book in manifest.books],
    ]
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump_all(documents, f, sort_keys=False, allow_unicode=True, explicit_start=True)
    print(f"saved books manifest {yaml_path}")


def load_books_manifest(yaml_path: str) -> BooksManifest:
    p: Path = Path(yaml_path)
    if not p.is_file():
        print(f"{yaml_path} is not a file")
        return None
    logger.info(f"yaml_path={yaml_path}")
    with open(yaml_path, "r", encoding="utf-8") as f:
        # safe_load_all handles the document separator (---) safely
        documents = list(yaml.safe_load_all(f))
        list_path = documents[0]  # Contains {'input_path': '/mnt/shared/gitlab_books'}
        books_list = documents[1]  # Contains your array of PDF dictionaries

        parsed_books = [PdfManifestEntry.from_dict(book) for book in books_list]
        logger.info(f"loaded books manifest {yaml_path}")
        return BooksManifest(input_path=list_path.get("input_path", ""), books=parsed_books)


def load_books_lib(
    yaml_path: str,
    tmp_path: str = None,
    update_yaml_info: bool = False,
    copy_pdfs: bool = False,
    move_no_info: bool = False,
    sanitize_didier: bool = False,
    fitz_didier: bool = False,
    sanitize_info: bool = False,
    print_first: bool = False,
):
    logger.info(f"sanitize_info={sanitize_info}")
    books_lib: BooksLib = BooksLib.from_yaml_path(yaml_path)
    if not tmp_path:
        tmp_path = tmp_dir()
    books_lib.tmp_path = tmp_path
    logger.info(f"loaded {pformat(books_lib)}")
    print()
    books_lib.books_manifest = load_books_manifest(books_lib.yaml_path)
    books_manifest: BooksManifest = books_lib.books_manifest
    if copy_pdfs:
        copy_yaml_pdf(books_lib)
    if print_first:
        print(f"books_lib.books_manifest = {type(books_lib.books_manifest)}")
        print(f"books_manifest = {type(books_manifest)}")
        books_count = len(books_manifest.books)
        print(f"count={books_count}")
        first_entry: PdfManifestEntry | None = next(iter(books_manifest.books), None)
        first_entry: PdfManifestEntry = books_manifest.books[2]
        print(f"first entry: {pformat(first_entry)}")
        if copy_pdfs:
            copy_to_temp(books_lib, first_entry)
        for path in books_lib.tmp_path.iterdir():
            info = path.stat()
            print(f"source {PurePosixPath(path).name}")
            print(f"{books_lib.tmp_path}/{path.name} {info.st_size}")
    if update_yaml_info:
        logger.info("updating yaml info for books")
        threadpool_books_info(books_lib)
        save_books_manifest(books_lib.books_manifest, "files_info.yaml")
    if move_no_info:
        move_to_no_info(books_lib)
    if sanitize_didier:
        threadpool_books_sanitize(books_lib)
    if fitz_didier:
        threadpool_books_fitz_sanitize(books_lib)
    if sanitize_info:
        threadpool_embed_info(books_lib)
    else:
        logger.info("not doing sanitize_info")


def copy_yaml_pdf_no_info(books_lib: BooksLib) -> None:
    books_manifest: BooksManifest = books_lib.books_manifest
    for book in books_manifest.books:
        if book.has_no_metadata_info():
            copy_to_temp(books_lib, book)
    save_books_manifest(books_manifest, "copied.yaml")


def copy_yaml_pdf(books_lib: BooksLib) -> None:
    books_manifest: BooksManifest = books_lib.books_manifest
    for book in books_manifest.books:
        copy_to_temp(books_lib, book)
    save_books_manifest(books_manifest, "copied.yaml")


def move_to_no_info(books_lib: BooksLib):
    books_manifest: BooksManifest = books_lib.books_manifest
    for book in books_manifest.books:
        if len(book.title) == 0 and len(book.author) == 0 and len(book.isbn) == 0:
            move_temp_no_title_or_author(books_lib, book)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


@click.command()
@click.argument("yaml_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--tmp-path", type=click.Path(path_type=Path), help="Optional temporary path.")
@click.option("--copy-pdfs", is_flag=True, default=False, help="copy pdf files from input_files to tmp")
@click.option("--update-yaml-info", is_flag=True, default=False, help="copy pdf files from input_files to tmp")
@click.option("--move-no-info", is_flag=True, default=False, help="move pdf files from tmp if no info")
@click.option("--sanitize-didier", is_flag=True, default=False, help="sanitize and move pdf by didier finds")
@click.option("--fitz-didier", is_flag=True, default=False, help="fitz and move pdf by didier finds")
@click.option("--sanitize-info", is_flag=True, default=False, help="sanitize info into pdf")
@click.option(
    "--print-first",
    "print_first",
    is_flag=True,
    default=False,
    help="Print first entry from yaml.",
)
def main(
    yaml_path: str,
    tmp_path: str,
    update_yaml_info: bool,
    copy_pdfs: bool,
    move_no_info: bool,
    sanitize_didier: bool,
    fitz_didier: bool,
    sanitize_info: bool,
    print_first: bool,
) -> None:
    load_books_lib(
        yaml_path,
        tmp_path=tmp_path,
        update_yaml_info=update_yaml_info,
        copy_pdfs=copy_pdfs,
        move_no_info=move_no_info,
        sanitize_didier=sanitize_didier,
        fitz_didier=fitz_didier,
        sanitize_info=sanitize_info,
        print_first=print_first,
    )


if __name__ == "__main__":
    main()
# /bin/python yaml_actions.py ~/shared/gitlab_books/output.yaml --print-first
# /bin/python yaml_actions.py ~/shared/gitlab_books/output.yaml --tmp-path=/tmp/stam
# /bin/python yaml_actions.py ~/shared/gitlab_books/output.yaml  --copy-pdfs
# /bin/python yaml_actions.py copied.yml --tmp-path=/tmp/tmpijmg7hk2 --update-yaml-info
# /bin/python yaml_actions.py  files_info.yaml --tmp-path=/home/sd/tmp/1-sanitized2/ --move-no-info
# python yaml_actions.py  files_info.yaml --tmp-path=/home/sd/tmp/one_file --sanitize-didier"
# python yaml_actions.py  files_info.yaml --tmp-path=/home/sd/tmp/sanitized --sanitize-info"
