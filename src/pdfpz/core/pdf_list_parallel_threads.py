import concurrent.futures
import os
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, List

from pdfpz.core.class_books_collection import BooksCollection, BooksShelf, PdfManifestEntry
from pdfpz.core.logger import logger

# ------------------------------------------------------------------------------
# helpers functions
# ------------------------------------------------------------------------------


def get_max_workers() -> int:
    """
    Determine max_workers based on available system cores.
    os.process_cpu_count() (3.13+) respects cgroup/affinity limits (containers, taskset),
    unlike os.cpu_count() which reports raw physical core count.
    """
    cpus = os.process_cpu_count() or os.cpu_count() or 1
    return cpus


MAX_WORKERS = get_max_workers()


def list_pdf_files(dir_path: Path) -> List[Path]:
    """Return a sorted list of PDF Path objects in dir_path."""
    return sorted(Path(dir_path).glob("*.pdf"))


def run_and_report(future_to_item: dict) -> None:
    """Wait for futures and log results or exceptions.

    This consolidates the repeated pattern used in the threadpool helper functions.
    """
    for future in concurrent.futures.as_completed(future_to_item):
        try:
            logger.info(f"finished thread: {future.result()}")
        except Exception as exc:
            logger.warning(f"exception in thread: {exc}")


# ------------------------------
# public functions
# ------------------------------


# pythonic threaded action_function on list of items
def run_threaded_action(
    items: Iterable[Any], action_func: Callable[[Any], Any], max_workers: int = MAX_WORKERS
) -> None:
    """Run `action_func(item)` for each item in `items` in parallel using a ThreadPoolExecutor.

    - items: iterable of inputs to pass to func (a list or a generator both work)
    - action_func: callable that accepts a single argument
    - max_workers: number of worker threads to use
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_item = {executor.submit(action_func, item): item for item in items}
        run_and_report(future_to_item)


# pythonic  createing generator with optional if condition over items
def generate_manifest_items(
    manifest: BooksShelf,
    predicate: Callable[[PdfManifestEntry], bool] = lambda m: True,
) -> Iterator[PdfManifestEntry]:
    """Yield manifest entries matching `predicate` (default: every entry, unfiltered)."""
    return (m for m in manifest.books if predicate(m))


# pythonic running function over books_collection with direct path files
def run_threads_books_collection_pdf_path(
    books_collection: BooksCollection, action_function: Callable[[str], Any], max_workers: int = MAX_WORKERS
) -> None:
    """Run `action_function` on every PDF file path found in books_collection.tmp_path using the generic thread runner.

    - books_collection: BooksCollection instance containing the tmp_path where PDFs reside
    - action_function: callable that accepts a single argument (file path as str)
    - max_workers: number of worker threads to use
    """
    dir_path = books_collection.tmp_path
    pdf_paths = list_pdf_files(dir_path)
    pdf_files = [str(p) for p in pdf_paths]

    run_threaded_action(pdf_files, action_function, max_workers=max_workers)
