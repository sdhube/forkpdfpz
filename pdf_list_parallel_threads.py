"""
Solution 2 — Parallel via ThreadPoolExecutor.
Multiple entries enriched concurrently across MAX_WORKERS threads. Each
result is written+flushed to output.yaml the moment it completes (order on
disk = completion order, not input order), synchronized by a Lock since
multiple threads share one file handle.

Tune concurrency by changing MAX_WORKERS below (or pass a different value
into process_all).
"""

import concurrent.futures
import threading

from common import (
    PdfManifest, load_entries, enrich_entry_data,
    manifest_to_entry_dict, write_header, append_entry,
)

INPUT_FILE = "input.yaml"
OUTPUT_FILE = "output_parallel_threads.yaml"
MAX_WORKERS = 10  # <-- controls how many entries are processed concurrently


def process_all(input_path: str, output_path: str, max_workers: int = MAX_WORKERS) -> None:
    manifests = load_entries(input_path, PdfManifest)
    write_lock = threading.Lock()

    with open(output_path, "w", encoding="utf-8") as out:
        write_header(out)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_manifest = {
                executor.submit(enrich_entry_data, m): m for m in manifests
            }

            for future in concurrent.futures.as_completed(future_to_manifest):
                original = future_to_manifest[future]
                try:
                    enriched = future.result()
                    entry = manifest_to_entry_dict(enriched, status="done")
                except Exception as exc:
                    entry = manifest_to_entry_dict(original, status="error", error_msg=str(exc))

                append_entry(out, entry, write_lock=write_lock)


def main():
    process_all(INPUT_FILE, OUTPUT_FILE, max_workers=MAX_WORKERS)


if __name__ == "__main__":
    main()
