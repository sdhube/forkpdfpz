from pprint import pformat
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import yaml
import click

from PdfManifestEntry import PdfManifestEntry, BooksManifest, BooksLib


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
    with open(pdf_input_path, 'rb') as src, open(pdf_output_path, 'wb') as dst:
        shutil.copyfileobj(src, dst)


def save_books_manifest(manifest: BooksManifest, yaml_path: str) -> None:
    print(f"yaml_path={yaml_path}")
    documents = [
        {"input_path": manifest.input_path},
        [book.to_dict() for book in manifest.books],
    ]
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump_all(
            documents, f, sort_keys=False, allow_unicode=True, explicit_start=True
        )
    print(f"saved books manifest {yaml_path}")


def load_books_manifest(yaml_path: str) -> BooksManifest:
    p: Path = Path(yaml_path)
    if not p.is_file():
        print(f"{yaml_path} is not a file")
        return None
    print(f"yaml_path={yaml_path}")    
    with open(yaml_path, "r", encoding="utf-8") as f:
        # safe_load_all handles the document separator (---) safely
        documents = list(yaml.safe_load_all(f))
        list_path = documents[0]   # Contains {'input_path': '/mnt/shared/gitlab_books'}
        books_list = documents[1]  # Contains your array of PDF dictionaries

        parsed_books = [PdfManifestEntry.from_dict(book) for book in books_list]
        print(f"loaded books manifest {yaml_path}")
        return BooksManifest(
            input_path=list_path.get("input_path", ""),
            books=parsed_books
        )


def load_books_lib(yaml_path: str, tmp_path: str = None, print_first: bool = False):
    books_lib: BooksLib = BooksLib.from_yaml_path(yaml_path)
    if not tmp_path:
        tmp_path = tmp_dir()
    books_lib.tmp_path = tmp_path
    print(f"loaded {pformat(books_lib)}")
    print()
    books_lib.books_manifest = load_books_manifest(books_lib.yaml_path)
    books_manifest: BooksManifest = books_lib.books_manifest
    copy_yaml_pdf(books_lib)
    if print_first:
        print(f"books_lib.books_manifest = {type(books_lib.books_manifest)}")
        print(f"books_manifest = {type(books_manifest)}")
        books_count = len(books_manifest.books)
        print(f"count={books_count}")
        first_entry: PdfManifestEntry | None = next(iter(books_manifest.books), None)
        first_entry: PdfManifestEntry = books_manifest.books[2]
        print(f"first entry: {pformat(first_entry)}")
        copy_to_temp(books_lib, first_entry)
        for path in books_lib.tmp_path.iterdir():
            info = path.stat()
            print(f"source {PurePosixPath(path).name}")
            print(f"{books_lib.tmp_path}/{path.name} {info.st_size}")


def copy_yaml_pdf(books_lib: BooksLib) -> None:
    books_manifest: BooksManifest = books_lib.books_manifest
    for book in books_manifest.books:
        copy_to_temp(books_lib, book)
    save_books_manifest(books_manifest, "copied.yml")
     
# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


@click.command()
@click.argument("yaml_path", type=click.Path(exists=True, dir_okay=False))
@click.option('--tmp-path', type=click.Path(path_type=Path), help='Optional temporary path.')
@click.option(
    "--print-first",
    "print_first",
    is_flag=True,
    default=False,
    help="Print first entry from yaml.",
)
def main(yaml_path: str, tmp_path, print_first: bool) -> None:
    load_books_lib(yaml_path, tmp_path=tmp_path, print_first=print_first)


if __name__ == "__main__":
    main()
# /bin/python yaml_actions.py ~/shared/gitlab_books/output.yaml --print-first 
# /bin/python yaml_actions.py ~/shared/gitlab_books/output.yaml --tmp-path=/tmp/stam
