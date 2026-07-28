from dataclasses import dataclass
from pathlib import Path
from pprint import pformat

import click

from class_book_manifest import BooksLib
from class_books_actions import BooksActions
from logger import logger


@dataclass
class BookOperations:
    """Encapsulates all book processing operations as flags."""

    copy_pdfs: bool = False
    update_yaml_info: bool = False
    move_no_info: bool = False
    sanitize_didier: bool = False
    fitz_didier: bool = False
    sanitize_info: bool = False
    sanitize_normalize_name: bool = False
    print_first: bool = False

    def get_enabled_operations(self) -> dict:
        """Return a mapping of enabled operation names to their methods.
        
        Allows callers to iterate over only the enabled operations without
        repeating if-statement chains.
        """
        return {name: getattr(self, name) for name, value in self.__dict__.items() if value}


def load_books_lib(
    yaml_path: str,
    tmp_path: str = None,
    operations: BookOperations = None,
):
    """Load books library and perform requested operations.
    
    Args:
        yaml_path: Path to the YAML manifest file
        tmp_path: Optional temporary directory path
        operations: BookOperations instance defining which operations to perform
    """
    operations = operations or BookOperations()
    
    logger.info(f"Operations to perform: {operations.get_enabled_operations().keys()}")
    books_lib: BooksLib = BooksLib.from_yaml_path(yaml_path)
    books_lib.tmp_path = str(tmp_path) or ""
    logger.info(f"loaded {pformat(books_lib)}")

    # Create BooksActions instance
    actions = BooksActions(books_lib)

    # Ensure manifest is loaded (this will set up tmp dir if needed)
    actions.load_manifest(tmp_path=tmp_path)

    # Map operation flags to BooksActions methods
    operation_map = {
        "copy_pdfs": actions.copy_yaml_pdf,
        "update_yaml_info": actions.update_books_lib_info_and_save,
        "move_no_info": actions.move_books_to_no_info,
        "sanitize_didier": actions.sanitize_books_didier,
        "fitz_didier": actions.sanitize_books_fitz_didier,
        "sanitize_info": actions.sanitize_books_info,
        "sanitize_normalize_name": actions.update_normalized_info_and_move_rename_file,
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
@click.argument("yaml_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--tmp-path", type=click.Path(path_type=Path), help="Optional temporary path.")
@click.option("--copy-pdfs", is_flag=True, default=False, help="copy pdf files from input_files to tmp")
@click.option("--update-yaml-info", is_flag=True, default=False, help="update yaml with pdf metadata")
@click.option("--move-no-info", is_flag=True, default=False, help="move pdf files from tmp if no info")
@click.option("--sanitize-didier", is_flag=True, default=False, help="sanitize and move pdf by didier finds")
@click.option("--fitz-didier", is_flag=True, default=False, help="fitz and move pdf by didier finds")
@click.option("--sanitize-info", is_flag=True, default=False, help="sanitize info into pdf")
@click.option("--sanitize-normalize-name", is_flag=True, default=False, help="normalize pdf file names")
@click.option(
    "--print-first",
    "print_first",
    is_flag=True,
    default=False,
    help="Print first entry from yaml.",
)
def main(
    yaml_path: str,
    tmp_path: Path,
    update_yaml_info: bool,
    copy_pdfs: bool,
    move_no_info: bool,
    sanitize_didier: bool,
    fitz_didier: bool,
    sanitize_info: bool,
    sanitize_normalize_name: bool,
    print_first: bool,
) -> None:
    """Process books library with specified operations."""
    operations = BookOperations(
        copy_pdfs=copy_pdfs,
        update_yaml_info=update_yaml_info,
        move_no_info=move_no_info,
        sanitize_didier=sanitize_didier,
        fitz_didier=fitz_didier,
        sanitize_info=sanitize_info,
        sanitize_normalize_name=sanitize_normalize_name,
        print_first=print_first,
    )
    load_books_lib(yaml_path, tmp_path=tmp_path, operations=operations)


if __name__ == "__main__":
    main()
# /bin/python yaml_actions.py ~/shared/gitlab_books/output.yaml --print-first
# /bin/python yaml_actions.py ~/shared/gitlab_books/output.yaml --tmp-path=/tmp/stam
# /bin/python yaml_actions.py ~/shared/gitlab_books/output.yaml  --copy-pdfs
# /bin/python yaml_actions.py copied.yml --tmp-path=/tmp/tmpijmg7hk2 --update-yaml-info
# /bin/python yaml_actions.py  files_info.yaml --tmp-path=/home/sd/tmp/1-sanitized2/ --move-no-info
# python yaml_actions.py  files_info.yaml --tmp-path=/home/sd/tmp/one_file --sanitize-didier"
# python yaml_actions.py  files_info.yaml --tmp-path=/home/sd/tmp/sanitized --sanitize-info"
# python yaml_actions.py  files_info.yaml --tmp-path=/tmp/tmp_meta/metadata/ --sanitize-normalize-name"
