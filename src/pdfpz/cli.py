from dataclasses import dataclass
from pathlib import Path

import click

from pdfpz.actions.class_books_actions import BooksActions
from pdfpz.core.class_books_collection import BooksCollection
from pdfpz.core.logger import logger


@dataclass
class BookOperations:
    """Encapsulates all book processing operations as flags."""

    copy_pdfs: bool = False
    update_assets_info: bool = False
    move_no_info: bool = False
    sanitize_didier: bool = False
    fitz_didier: bool = False
    sanitize_info: bool = False
    sanitize_normalize_name: bool = False
    load_yaml_export_db: bool = False
    filter_first: bool = (False,)
    props_filter: bool = (False,)
    print_first: bool = False

    # pythonic replacing repited if statements with dictionary
    def get_enabled_operations(self) -> dict:
        """Return a mapping of enabled operation names to their methods.
        Allows callers to iterate over only the enabled operations without
        repeating if-statement chains.
        """
        return {name: getattr(self, name) for name, value in self.__dict__.items() if value}


def load_books_collection_and_operate(
    persistence_file_path: str,
    tmp_path: str | None = None,
    operations: BookOperations | None = None,
) -> None:
    """Load books library and perform requested operations.

    Args:
        persistence_file_path: Path to YAML/DB file
        tmp_path: Optional temporary directory path
        operations: BookOperations instance defining which operations to perform
    """
    operations = operations or BookOperations()

    logger.info(f"Operations to perform: {operations.get_enabled_operations().keys()}")
    logger.info(f"initializing BooksCollection from legacy_path {persistence_file_path}")
    books_collection: BooksCollection = BooksCollection.from_persistence_file_path(persistence_file_path)
    books_collection.set_tmp_path(tmp_path)

    # Create BooksActions instance
    actions = BooksActions(books_collection)

    # Ensure collection is loaded (this will set up tmp dir if needed)
    actions.load_collection(tmp_path=tmp_path)

    # Map operation flags to BooksActions methods
    operation_map = {
        "copy_pdfs": actions.copy_assets_pdf,
        "update_assets_info": actions.update_books_collection_info_and_save,
        "move_no_info": actions.move_books_to_no_info,
        "sanitize_didier": actions.sanitize_books_didier,
        "fitz_didier": actions.sanitize_books_fitz_didier,
        "sanitize_info": actions.sanitize_books_info,
        "sanitize_normalize_name": actions.update_normalized_info_and_move_rename_file,
        "load_yaml_export_db": actions.load_yaml_export_db,
        "filter_first": actions.filter_first,
        "props_filter": actions.props_filter,
        "print_first": actions.print_first_entry,
    }

    # Execute all enabled operations
    for operation_name, operation_func in operation_map.items():
        if getattr(operations, operation_name):
            logger.info(f"Executing: {operation_name}")
            operation_func()


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


@click.command()
@click.argument("persistence_file_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--tmp-path", type=click.Path(path_type=Path), default=None, help="Optional temporary path.")
@click.option("--copy-pdfs", is_flag=True, default=False, help="copy pdf files from input_files to tmp")
@click.option("--update-assets-info", is_flag=True, default=False, help="update yaml with pdf metadata")
@click.option("--move-no-info", is_flag=True, default=False, help="move pdf files from tmp if no info")
@click.option("--sanitize-didier", is_flag=True, default=False, help="sanitize and move pdf by didier finds")
@click.option("--fitz-didier", is_flag=True, default=False, help="fitz and move pdf by didier finds")
@click.option("--sanitize-info", is_flag=True, default=False, help="sanitize info into pdf")
@click.option("--sanitize-normalize-name", is_flag=True, default=False, help="normalize pdf file names")
@click.option("--load-yaml-export-db", is_flag=True, default=False, help="load yaml export db")
@click.option("--filter-first", is_flag=True, default=False, help="print first filtered")
@click.option("--props-filter", is_flag=True, default=False, help="do props filter")
@click.option(
    "--print-first",
    "print_first",
    is_flag=True,
    default=False,
    help="Print first entry from legacy_file.",
)
def main(**kwargs) -> None:
    """Process books library with specified operations.

    Uses **kwargs to handle all click parameters, reducing boilerplate and making
    it easier to add new operations without modifying the main signature.
    """
    # Extract positional and optional arguments
    persistence_file_path: Path = kwargs.pop("persistence_file_path")
    tmp_path: Path | None = kwargs.pop("tmp_path")

    # Create BookOperations from remaining kwargs (operation flags)
    operations = BookOperations(**kwargs)

    load_books_collection_and_operate(
        str(persistence_file_path), tmp_path=str(tmp_path) if tmp_path else None, operations=operations
    )


if __name__ == "__main__":
    main()
# pdfpz ~/shared/gitlab_books/output.yaml --print-first
# pdfpz ~/shared/gitlab_books/output.yaml --tmp-path=/tmp/stam
# pdfpz ~/shared/gitlab_books/output.yaml  --copy-pdfs
# pdfpz copied.yml --tmp-path=/tmp/tmpijmg7hk2 --update-yaml-info
# pdfpz  files_info.yaml --tmp-path=/home/sd/tmp/1-sanitized2/ --move-no-info
# pdfpz  files_info.yaml --tmp-path=/home/sd/tmp/one_file --sanitize-didier"
# pdfpz  files_info.yaml --tmp-path=/home/sd/tmp/sanitized --sanitize-info"
# pdfpz  files_info.yaml --tmp-path=/tmp/tmp_meta/metadata/ --sanitize-normalize-name"
# pdfpz  files_uuid.yaml --tmp-path=/tmp/tmp_meta/metadata/ --load-yaml-export-db
# PYTHONPATH=src python3 -m pdfpz.cli    books_db.db --tmp-path=/tmp/tmp_meta/metadata/ --filter-first
# PYTHONPATH=src python3 -m pdfpz.cli    books_db.db --tmp-path=/tmp/tmp_meta/metadata/ --props-filter
