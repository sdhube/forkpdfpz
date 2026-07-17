from pprint import pformat
from pathlib import Path, PurePosixPath
import yaml
import click

from PdfManifestEntry import PdfManifestEntry, BooksManifest, BooksLib


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


def load_books_lib(yaml_path: str, print_first: bool):
    books_lib: BooksLib = BooksLib.from_yaml_path(yaml_path)
    print(f"loaded {pformat(books_lib)}")
    print()
    books_lib.books_manifest = load_books_manifest(books_lib.yaml_path)
    books_manifest: BooksManifest = books_lib.books_manifest
    if print_first:
        print(f"books_lib.books_manifest = {type(books_lib.books_manifest)}")
        print(f"books_manifest = {type(books_manifest)}")
        books_count = len(books_manifest.books)
        print(f"count={books_count}")
        first_entry: PdfManifestEntry | None = next(iter(books_manifest.books), None)
        print(f"first entry: {pformat(first_entry)}")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


@click.command()
@click.argument("yaml_path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--print-first",
    "print_first",
    is_flag=True,
    default=False,
    help="Print first entry from yaml.",
)
def main(yaml_path: str, print_first: bool) -> None:
    load_books_lib(yaml_path, print_first)


if __name__ == "__main__":
    main()
# /bin/python yaml_actions.py ~/shared/gitlab_books/output.yaml --print-first 