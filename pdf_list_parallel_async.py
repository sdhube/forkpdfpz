"""
Solution 3 — Parallel via asyncio ("promises").
Python's analog to JS Promise/async-await: each entry becomes an
asyncio.Task (an awaitable, conceptually the same as a Promise), and
asyncio.gather(*tasks) awaits all of them concurrently — the direct
equivalent of Promise.all([...]).

enrich_entry_data() is a plain blocking function (PDF parsing, network
calls, etc.), so it's offloaded via asyncio.to_thread — this actually runs
it on a real OS thread under the hood, which is what lets it run
concurrently at all; awaiting a blocking call directly would block the
entire event loop and defeat the purpose.

CONCURRENCY below controls how many tasks may run at once, via an
asyncio.Semaphore (the asyncio equivalent of ThreadPoolExecutor's
max_workers).
"""

import asyncio
import dataclasses

from common import (
    PdfManifest, load_entries, enrich_entry_data,
    manifest_to_entry_dict, write_header, append_entry,
)

INPUT_FILE = "input.yaml"
OUTPUT_FILE = "output_parallel_async.yaml"
CONCURRENCY = 10  # <-- controls how many entries are "in flight" at once


async def process_one(manifest: PdfManifest, out, write_lock: asyncio.Lock,
                       semaphore: asyncio.Semaphore) -> None:
    async with semaphore:  # caps how many entries run concurrently
        try:
            enriched = await asyncio.to_thread(enrich_entry_data, manifest)
            entry = manifest_to_entry_dict(enriched, status="done")
        except Exception as exc:
            entry = manifest_to_entry_dict(manifest, status="error", error_msg=str(exc))

    async with write_lock:  # file writes still need to be serialized
        append_entry(out, entry)


async def process_all_async(input_path: str, output_path: str, concurrency: int = CONCURRENCY) -> None:
    manifests = load_entries(input_path, PdfManifest)
    write_lock = asyncio.Lock()
    semaphore = asyncio.Semaphore(concurrency)

    with open(output_path, "w", encoding="utf-8") as out:
        write_header(out)

        # One asyncio.Task per entry — each is a "promise" that starts
        # running immediately; gather() is Promise.all().
        tasks = [
            asyncio.create_task(process_one(m, out, write_lock, semaphore))
            for m in manifests
        ]
        await asyncio.gather(*tasks)


def process_all(input_path: str, output_path: str, concurrency: int = CONCURRENCY) -> None:
    asyncio.run(process_all_async(input_path, output_path, concurrency))


def main():
    process_all(INPUT_FILE, OUTPUT_FILE, concurrency=CONCURRENCY)


if __name__ == "__main__":
    main()
