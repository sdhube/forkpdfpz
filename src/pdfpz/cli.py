from pathlib import Path

import click

from pdfpz.core.class_book_operations import BookOperationPlan, BookOperations, initialize_and_return_operations_map
from pdfpz.core.logger import logger


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
    operation_map = initialize_and_return_operations_map(persistence_file_path, tmp_path)
 
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
@click.option(
    "--run-all",
    is_flag=True,
    default=False,
    help="Run every pipeline stage in canonical order via BookOperationPlan.run_plan().",
)
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
    run_all: bool = kwargs.pop("run_all")

    if run_all:
        BookOperationPlan.run_plan(str(persistence_file_path), tmp_path=str(tmp_path) if tmp_path else None)
        return

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
# pdfpz  files_info.yaml --tmp-path=/home/sd/tmp/one_file --sanitize-pike"
# pdfpz  files_info.yaml --tmp-path=/home/sd/tmp/sanitized --sanitize-info"
# pdfpz  files_info.yaml --tmp-path=/tmp/tmp_meta/metadata/ --sanitize-normalize-name"
# pdfpz  files_uuid.yaml --tmp-path=/tmp/tmp_meta/metadata/ --load-yaml-export-db
# PYTHONPATH=src python3 -m pdfpz.cli    books_db.db --tmp-path=/tmp/tmp_meta/metadata/ --filter-first
# PYTHONPATH=src python3 -m pdfpz.cli    books_db.db --tmp-path=/tmp/tmp_meta/metadata/ --props-filter
# pdfpz  files_info.yaml --tmp-path=/tmp/tmp_meta/metadata/ --run-all
