from pprint import pformat
import yaml

import click

from PdfManifestEntry import PdfManifestEntry, BooksManifest


def load_books_manifest(yaml_path: str) -> BooksManifest:
    with open(yaml_path, "r", encoding="utf-8") as f:
        # safe_load_all handles the document separator (---) safely
        documents = list(yaml.safe_load_all(f))
        
        list_path = documents[0]   # Contains {'input_path': '/mnt/shared/gitlab_books'}
        books_list = documents[1]  # Contains your array of PDF dictionaries
        
        # Parse the raw dictionary structures into formal BookEntry objects
        parsed_books = [PdfManifestEntry.from_dict(book) for book in books_list]
        
        # Instantiate and return the cohesive BooksManifest object
        return BooksManifest(
            input_path=list_path.get("input_path", ""),
            books=parsed_books
        )


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
    books_manifest: BooksManifest = load_books_manifest(yaml_path)
    print(f"loaded {books_manifest.input_path}")
    if print_first:
        books_count = len(books_manifest.books)
        print(f"count={books_count}")

        first_entry: PdfManifestEntry | None = next(iter(books_manifest.books), None)
        print(f"first entry: {pformat(first_entry)}")


if __name__ == "__main__":
    main()
# /bin/python yaml_actions.py ~/shared/gitlab_books/output.yaml --print-first 