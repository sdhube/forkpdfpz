import concurrent.futures
import os
import sys
from typing import List, Callable, Any
from pathlib import Path

from class_book_manifest import BooksLib, PdfManifestEntry
from class_tmp_path import TmpPath
from logger import logger
from pdf_actions_info import single_pdf_info_action_with_path
from pdf_manifest_actions import single_pdf_action
from pdf_sanitize_fitz import sanitize_fitz
from pdf_sanitize_pike import sanitize_pdf


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


def run_threads_predicate(items: List[Any], func: Callable[[Any], Any], max_workers: int = MAX_WORKERS) -> None:
    """Run `func(item)` for each item in `items` in parallel using a ThreadPoolExecutor.

    - items: iterable of inputs to pass to func
    - func: callable that accepts a single argument
    - max_workers: number of worker threads to use
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_item = {executor.submit(func, item): item for item in items}
        run_and_report(future_to_item)


def threadpool_embed_info(books_lib: BooksLib, max_workers: int = MAX_WORKERS) -> None:
    """
    updates books lib with books info in parallel using threadpool
    """
    manifest: List[PdfManifestEntry] = books_lib.books_manifest

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for m in manifest.books:
            if m.has_no_metadata_info():
                logger.info(f"has no metadata info {m.name} ")
        for m in manifest.books:
            if not m.has_no_metadata_info():
                logger.info(f"has metadata info {m.name} ")

        future_to_manifest = {
            executor.submit(
                single_pdf_info_action_with_path, TmpPath(m.name).path_sanitized_tmp, m, sanitize_info=True
            ): m
            for m in manifest.books
            if not m.has_no_metadata_info()
        }

        run_and_report(future_to_manifest)


def threadpool_books_info(books_lib: BooksLib, max_workers: int = MAX_WORKERS) -> None:
    """
    updates books lib with books info in parallel using threadpool
    """
    print(f"is multicore python: {sys._is_gil_enabled()}")  # False = actually running free-threaded
    manifest: List[PdfManifestEntry] = books_lib.books_manifest

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_manifest = {executor.submit(single_pdf_action, m, books_lib.tmp_path): m for m in manifest.books}

        run_and_report(future_to_manifest)


def threadpool_books_sanitize(books_lib: BooksLib, max_workers: int = MAX_WORKERS) -> None:
    """ """
    manifest: List[PdfManifestEntry] = books_lib.books_manifest

    dir_path = books_lib.tmp_path
    pdf_paths = list_pdf_files(dir_path)
    pdf_files = [str(p) for p in pdf_paths]

    # Use the generic thread runner helper
    run_threads_predicate(pdf_files, sanitize_pdf, max_workers=max_workers)


def threadpool_books_fitz_sanitize(books_lib: BooksLib, max_workers: int = MAX_WORKERS) -> None:
    """ """
    manifest: List[PdfManifestEntry] = books_lib.books_manifest

    dir_path = books_lib.tmp_path
    pdf_paths = list_pdf_files(dir_path)
    print(f"pdf_files={[str(p) for p in pdf_paths]}")
    pdf_files = [str(p) for p in pdf_paths]

    # Use the same generic helper for the fitz-based sanitizer
    run_threads_predicate(pdf_files, sanitize_fitz, max_workers=max_workers)
