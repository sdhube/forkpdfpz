import concurrent.futures
import os
import sys
from typing import List

from PdfManifestEntry import PdfManifestEntry, BooksLib
from pdf_actions import single_pdf_action


def get_max_workers() -> int:
    """
    Determine max_workers based on available system cores.
    os.process_cpu_count() (3.13+) respects cgroup/affinity limits (containers, taskset),
    unlike os.cpu_count() which reports raw physical core count.
    """
    cpus = os.process_cpu_count() or os.cpu_count() or 1
    return cpus


MAX_WORKERS = get_max_workers()


def threadpool_books_info(books_lib: BooksLib, max_workers: int = MAX_WORKERS) -> None:
    """
    updates books lib with books info in parallel using threadpool
    """
    print(f"is multicore python: {sys._is_gil_enabled()}")  # False = actually running free-threaded
    manifest: List[PdfManifestEntry] = books_lib.books_manifest

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_manifest = {executor.submit(single_pdf_action, m, books_lib.tmp_path): m for m in manifest.books}

        for future in concurrent.futures.as_completed(future_to_manifest):
            try:
                print(f"finished thread{future.result()}")
            except Exception as exc:
                print(f"exception thread thread {exc}")


def threadpool_books_info(  