"""
Solution 1 — Sequential / iterative.
One thread, one entry at a time. Each entry is enriched then immediately
flushed to output.yaml before moving to the next. Simplest, most predictable
disk-write ordering (matches input order exactly), no concurrency to reason
about — at the cost of total runtime = sum of every entry's processing time.
"""

from common import (
    PdfManifest, load_entries, enrich_entry_data,
    manifest_to_entry_dict, write_header, append_entry,
)

INPUT_FILE = "input.yaml"
OUTPUT_FILE = "output_sequential.yaml"


def process_all(input_path: str, output_path: str) -> None:
    manifests = load_entries(input_path, PdfManifest)

    with open(output_path, "w", encoding="utf-8") as out:
        write_header(out)

        for m in manifests:
            try:
                enriched = enrich_entry_data(m)
                entry = manifest_to_entry_dict(enriched, status="done")
            except Exception as exc:
                entry = manifest_to_entry_dict(m, status="error", error_msg=str(exc))

            append_entry(out, entry)  # no lock needed: single thread


def main():
    process_all(INPUT_FILE, OUTPUT_FILE)


if __name__ == "__main__":
    main()
